from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

EXIT_OK = 0
EXIT_CONFIG = 10
EXIT_HARD_STOP = 20
EXIT_CONFLICT = 30
EXIT_VERIFY_FAILED = 40


class SkillError(RuntimeError):
    pass


class ConfigError(SkillError):
    pass


class GitCommandError(SkillError):
    def __init__(self, args: Sequence[str], returncode: int, stderr: str):
        super().__init__(f"git {' '.join(args)} failed with exit code {returncode}: {stderr.strip()}")
        self.args_list = list(args)
        self.returncode = returncode
        self.stderr = stderr


def resolve_repo_root(repo_path: str | Path) -> Path:
    repo = Path(repo_path).expanduser().resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitCommandError(["rev-parse", "--show-toplevel"], result.returncode, result.stderr)
    return Path(result.stdout.strip()).resolve()


def run_git(repo_root: str | Path, args: Sequence[str], check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=Path(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise GitCommandError(args, result.returncode, result.stderr)
    return result.stdout.strip()


def run_shell(repo_root: str | Path, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=Path(repo_root),
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )


def create_run_dir(repo_root: str | Path, run_id: str | None = None) -> Path:
    repo_root = Path(repo_root)
    run_name = run_id or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    run_dir = repo_root / ".upstream-sync" / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_markdown(path: str | Path, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_yaml(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(data).rstrip() + "\n", encoding="utf-8")


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))


def shorten_sha(sha: str) -> str:
    return sha[:8]


def load_config(repo_root: str | Path, config_path: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(repo_root)
    config_file = Path(config_path).expanduser().resolve() if config_path else repo_root / ".upstream-sync.yml"
    if not config_file.exists():
        raise ConfigError(f"Config file not found: {config_file}")
    return parse_yaml_subset(config_file.read_text(encoding="utf-8"))


def parse_yaml_subset(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ConfigError("Top-level config must be a mapping")
        return data
    except json.JSONDecodeError:
        pass

    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        stripped = raw.lstrip(" ")
        if stripped.startswith("#"):
            continue
        indent = len(raw) - len(stripped)
        if indent % 2 != 0:
            raise ConfigError("YAML subset parser requires two-space indentation")
        lines.append((indent, stripped))

    if not lines:
        return {}

    parsed, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise ConfigError("Unexpected trailing content in config")
    if not isinstance(parsed, dict):
        raise ConfigError("Top-level config must be a mapping")
    return parsed


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index

    current_indent, current_line = lines[index]
    if current_indent != indent:
        raise ConfigError(f"Invalid indentation near: {current_line}")

    if current_line.startswith("- "):
        items: list[Any] = []
        while index < len(lines):
            line_indent, line = lines[index]
            if line_indent != indent or not line.startswith("- "):
                break
            item_text = line[2:].strip()
            index += 1
            if item_text:
                inline_mapping = _parse_inline_mapping(item_text)
                if inline_mapping is not None:
                    if index < len(lines) and lines[index][0] > indent:
                        item, index = _parse_block(lines, index, indent + 2)
                        if not isinstance(item, dict):
                            raise ConfigError("Inline mapping list item must continue with a mapping block")
                        inline_mapping.update(item)
                    items.append(inline_mapping)
                else:
                    items.append(_parse_scalar(item_text))
            else:
                item, index = _parse_block(lines, index, indent + 2)
                items.append(item)
        return items, index

    mapping: dict[str, Any] = {}
    while index < len(lines):
        line_indent, line = lines[index]
        if line_indent != indent or line.startswith("- "):
            break
        if ":" not in line:
            raise ConfigError(f"Invalid mapping entry: {line}")
        key, rest = line.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        index += 1
        if rest:
            mapping[key] = _parse_scalar(rest)
            continue
        if index >= len(lines) or lines[index][0] <= indent:
            mapping[key] = {}
            continue
        value, index = _parse_block(lines, index, indent + 2)
        mapping[key] = value
    return mapping, index


def _parse_scalar(value: str) -> Any:
    if value in {"true", "false"}:
        return value == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _parse_inline_mapping(value: str) -> dict[str, Any] | None:
    if ":" not in value:
        return None
    key, rest = value.split(":", 1)
    key = key.strip()
    rest = rest.strip()
    if not key:
        return None
    if not rest:
        return {key: {}}
    return {key: _parse_scalar(rest)}


def require_fields(config: dict[str, Any], fields: Sequence[str]) -> list[str]:
    missing: list[str] = []
    for dotted in fields:
        cursor: Any = config
        for part in dotted.split("."):
            if not isinstance(cursor, dict) or part not in cursor:
                missing.append(dotted)
                break
            cursor = cursor[part]
    return missing


def render_yaml(data: Any, indent: int = 0) -> str:
    if isinstance(data, dict):
        lines: list[str] = []
        for key, value in data.items():
            prefix = " " * indent + f"{key}:"
            if isinstance(value, (dict, list)):
                lines.append(prefix)
                lines.append(render_yaml(value, indent + 2))
            else:
                lines.append(prefix + f" {render_scalar(value)}")
        return "\n".join(lines)
    if isinstance(data, list):
        lines = []
        for item in data:
            prefix = " " * indent + "-"
            if isinstance(item, (dict, list)):
                lines.append(prefix)
                lines.append(render_yaml(item, indent + 2))
            else:
                lines.append(prefix + f" {render_scalar(item)}")
        return "\n".join(lines)
    return " " * indent + render_scalar(data)


def render_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if text == "" or re.search(r"[:#\n]", text):
        escaped = text.replace("'", "''")
        return f"'{escaped}'"
    return text
