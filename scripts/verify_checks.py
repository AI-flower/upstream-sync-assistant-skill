#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import EXIT_VERIFY_FAILED, load_config, print_json, read_json, resolve_repo_root, run_shell, write_json  # noqa: E402


def run_checks(repo_root: str | Path, run_dir: str | Path, config_path: str | Path | None = None) -> tuple[dict, int]:
    repo_root = resolve_repo_root(repo_root)
    run_dir = Path(run_dir)
    config = load_config(repo_root, config_path)
    _ = read_json(run_dir / "context.json")

    checks = []
    failed = False
    for command in config["validation"]["post_merge_checks"]:
        completed = run_shell(repo_root, command)
        checks.append(
            {
                "command": command,
                "exit_code": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            }
        )
        if completed.returncode != 0:
            failed = True

    result = {
        "passed": not failed,
        "checks": checks,
        "manual_checks": config["validation"].get("manual_checks", []),
    }
    write_json(run_dir / "verify.json", result)
    return result, EXIT_VERIFY_FAILED if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run configured verification checks for an upstream sync run.")
    parser.add_argument("--repo", default=".", help="Path inside the target git repository")
    parser.add_argument("--run-dir", required=True, help="Path to the run directory")
    parser.add_argument("--config", default=None, help="Optional path to .upstream-sync.yml")
    args = parser.parse_args()

    result, exit_code = run_checks(args.repo, args.run_dir, args.config)
    print_json(result)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
