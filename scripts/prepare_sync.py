#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import create_run_dir, load_config, print_json, resolve_repo_root, run_git, write_json  # noqa: E402


def prepare_sync(repo_root: str | Path, config_path: str | Path | None = None, run_id: str | None = None) -> dict:
    repo_root = resolve_repo_root(repo_root)
    config = load_config(repo_root, config_path)
    git_cfg = config["git"]

    run_git(repo_root, ["fetch", git_cfg["upstream_remote"]])
    run_dir = create_run_dir(repo_root, run_id)

    branch_name = build_sync_branch_name(git_cfg["sync_branch_prefix"])
    existing = set(
        filter(None, run_git(repo_root, ["for-each-ref", "refs/heads", "--format=%(refname:short)"]).splitlines())
    )
    while branch_name in existing:
        branch_name = build_sync_branch_name(git_cfg["sync_branch_prefix"], include_seconds=True)

    run_git(repo_root, ["checkout", "-b", branch_name, git_cfg["integration_branch"]])
    mirror_target_ref = f"{git_cfg['upstream_remote']}/{git_cfg['mirror_branch']}"
    to_sha = run_git(repo_root, ["rev-parse", mirror_target_ref])
    from_sha = run_git(repo_root, ["merge-base", git_cfg["integration_branch"], mirror_target_ref])

    context = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "run_dir": str(run_dir),
        "mirror_target_ref": mirror_target_ref,
        "integration_branch": git_cfg["integration_branch"],
        "sync_branch": branch_name,
        "from_sha": from_sha,
        "to_sha": to_sha,
    }
    write_json(run_dir / "context.json", context)
    return context


def build_sync_branch_name(prefix: str, include_seconds: bool = False) -> str:
    fmt = "%Y-%m-%d-%H%M%S" if include_seconds else "%Y-%m-%d-%H%M"
    return f"{prefix}{datetime.now(timezone.utc).strftime(fmt)}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local upstream sync branch and run directory.")
    parser.add_argument("--repo", default=".", help="Path inside the target git repository")
    parser.add_argument("--config", default=None, help="Optional path to .upstream-sync.yml")
    parser.add_argument("--run-id", default=None, help="Optional explicit run directory identifier")
    args = parser.parse_args()

    context = prepare_sync(args.repo, args.config, args.run_id)
    print_json(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
