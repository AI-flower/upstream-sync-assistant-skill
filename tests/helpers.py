from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def git(cwd: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def init_basic_repo() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmp = tempfile.TemporaryDirectory()
    repo = Path(tmp.name) / "repo"
    repo.mkdir(parents=True)
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Test User")
    git(repo, "config", "user.email", "test@example.com")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "initial")
    return tmp, repo


def create_sync_fixture() -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    upstream_bare = root / "upstream.git"
    origin_bare = root / "origin.git"
    source = root / "source"
    work = root / "work"

    git(root, "init", "--bare", str(upstream_bare))
    git(root, "init", "--bare", str(origin_bare))

    source.mkdir()
    git(source, "init", "-b", "main")
    git(source, "config", "user.name", "Test User")
    git(source, "config", "user.email", "test@example.com")
    (source / "README.md").write_text("base\n", encoding="utf-8")
    git(source, "add", "README.md")
    git(source, "commit", "-m", "initial")
    git(source, "remote", "add", "origin", str(upstream_bare))
    git(source, "push", "origin", "main")

    git(root, "clone", str(upstream_bare), str(work))
    git(work, "remote", "rename", "origin", "upstream")
    git(work, "remote", "add", "origin", str(origin_bare))
    git(work, "config", "user.name", "Test User")
    git(work, "config", "user.email", "test@example.com")
    git(work, "push", "origin", "main")
    git(work, "checkout", "-b", "yl-main")
    (work / "internal.txt").write_text("internal\n", encoding="utf-8")
    git(work, "add", "internal.txt")
    git(work, "commit", "-m", "internal change")
    git(work, "push", "-u", "origin", "yl-main")
    git(work, "checkout", "main")
    git(work, "branch", "--set-upstream-to", "upstream/main", "main")
    return tmp, source, work


def advance_upstream(source: Path, path: str = "upstream.txt", content: str = "upstream\n") -> None:
    target = source / path
    target.write_text(content, encoding="utf-8")
    git(source, "add", path)
    git(source, "commit", "-m", f"update {path}")
    git(source, "push", "origin", "main")


def write_config(
    repo: Path,
    post_merge_checks: list[str] | None = None,
    extra_sync: str = "",
    reporting_extra: str = "",
) -> Path:
    checks = post_merge_checks or ['python3 -c "print(\'ok\')"']
    rendered_checks = "\n".join([f"    - {item}" for item in checks])
    config = f"""version: 1

git:
  upstream_remote: upstream
  write_remote: origin
  mirror_branch: main
  integration_branch: yl-main
  sync_branch_prefix: sync/upstream-

policy:
  require_clean_worktree: true
  require_confirmation_for_push: true
  require_confirmation_for_mirror_branch_change: true
  block_push_to_upstream: true

sync:
  cadence_days: 7
{extra_sync}

analysis:
  high_risk_paths:
    - src
  high_risk_files:
    - README.md
  infra_keywords:
    - readme

validation:
  post_merge_checks:
{rendered_checks}
  manual_checks:
    - manual flow

reporting:
  output_dir: docs/upstream-sync/reports
{reporting_extra}
"""
    config_path = repo / ".upstream-sync.yml"
    config_path.write_text(config, encoding="utf-8")
    return config_path
