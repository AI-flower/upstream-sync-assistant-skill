#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (  # noqa: E402
    ConfigError,
    EXIT_CONFIG,
    EXIT_HARD_STOP,
    load_config,
    print_json,
    require_fields,
    resolve_repo_root,
    run_git,
)


REQUIRED_FIELDS = (
    "git.upstream_remote",
    "git.write_remote",
    "git.mirror_branch",
    "git.integration_branch",
    "git.sync_branch_prefix",
    "policy.require_clean_worktree",
    "policy.require_confirmation_for_push",
    "policy.require_confirmation_for_mirror_branch_change",
    "policy.block_push_to_upstream",
    "validation.post_merge_checks",
    "validation.manual_checks",
    "reporting.output_dir",
)


def evaluate_repo(repo_root: str | Path, config_path: str | Path | None = None) -> tuple[dict, int]:
    repo_root = resolve_repo_root(repo_root)
    try:
        config = load_config(repo_root, config_path)
    except ConfigError as error:
        return {
            "repo_root": str(repo_root),
            "status": "config-error",
            "hard_stops": [{"code": "config_error", "message": str(error)}],
            "warnings": [],
        }, EXIT_CONFIG

    missing = require_fields(config, REQUIRED_FIELDS)
    if missing:
        return {
            "repo_root": str(repo_root),
            "status": "config-error",
            "hard_stops": [{"code": "missing_fields", "message": ", ".join(missing)}],
            "warnings": [],
        }, EXIT_CONFIG

    git_cfg = config["git"]
    policy_cfg = config["policy"]
    sync_cfg = config.get("sync", {})
    hard_stops: list[dict] = []
    warnings: list[dict] = []
    current_branch = run_git(repo_root, ["branch", "--show-current"])

    remotes = set(filter(None, run_git(repo_root, ["remote"]).splitlines()))
    for remote_key in ("upstream_remote", "write_remote"):
        remote_name = git_cfg[remote_key]
        if remote_name not in remotes:
            hard_stops.append({"code": "missing_remote", "message": f"Remote '{remote_name}' not found"})

    local_branches = set(
        filter(None, run_git(repo_root, ["for-each-ref", "refs/heads", "--format=%(refname:short)"]).splitlines())
    )
    for branch_key in ("mirror_branch", "integration_branch"):
        branch_name = git_cfg[branch_key]
        if branch_name not in local_branches:
            hard_stops.append({"code": "missing_branch", "message": f"Branch '{branch_name}' not found"})

    dirty_entries = [
        entry
        for entry in run_git(repo_root, ["status", "--porcelain"]).splitlines()
        if not is_ignorable_dirty_entry(entry)
    ]
    if policy_cfg.get("require_clean_worktree", True) and dirty_entries:
        hard_stops.append({"code": "dirty_worktree", "message": "Worktree is not clean"})

    mirror_branch = git_cfg["mirror_branch"]
    upstream_ref = f"{git_cfg['upstream_remote']}/{mirror_branch}"
    upstream_exists = run_git(repo_root, ["show-ref", "--verify", f"refs/remotes/{upstream_ref}"], check=False)
    if not upstream_exists:
        hard_stops.append({"code": "missing_upstream_ref", "message": f"Remote ref '{upstream_ref}' not found"})
        ahead = behind = 0
    else:
        ahead = int(run_git(repo_root, ["rev-list", "--count", f"{upstream_ref}..{mirror_branch}"]))
        behind = int(run_git(repo_root, ["rev-list", "--count", f"{mirror_branch}..{upstream_ref}"]))

    if ahead > 0:
        hard_stops.append(
            {
                "code": "mirror_polluted",
                "message": f"Mirror branch '{mirror_branch}' is ahead of '{upstream_ref}' by {ahead} commit(s)",
            }
        )
    elif behind > 0:
        warnings.append(
            {
                "code": "mirror_behind",
                "message": f"Mirror branch '{mirror_branch}' is behind '{upstream_ref}' by {behind} commit(s)",
            }
        )

    cadence_days = sync_cfg.get("cadence_days")
    if cadence_days is not None and upstream_exists:
        merge_base = run_git(repo_root, ["merge-base", git_cfg["integration_branch"], upstream_ref])
        merge_base_ts = int(run_git(repo_root, ["show", "-s", "--format=%ct", merge_base]))
        upstream_ahead = int(run_git(repo_root, ["rev-list", "--count", f"{git_cfg['integration_branch']}..{upstream_ref}"]))
        lag_days = (datetime.now(timezone.utc).timestamp() - merge_base_ts) / 86400
        if upstream_ahead > 0 and lag_days >= cadence_days:
            warnings.append(
                {
                    "code": "cadence_exceeded",
                    "message": (
                        f"Integration branch diverged from upstream for about {lag_days:.1f} days "
                        f"and is missing {upstream_ahead} upstream commit(s)"
                    ),
                }
            )

    for freeze_window in sync_cfg.get("freeze_windows", []):
        branches = freeze_window.get("branches", [])
        if git_cfg["integration_branch"] in branches or current_branch in branches:
            warnings.append(
                {
                    "code": "freeze_window_active",
                    "message": (
                        f"Freeze window '{freeze_window.get('name', 'unnamed-freeze')}' applies to "
                        f"'{git_cfg['integration_branch']}'"
                    ),
                }
            )

    result = {
        "repo_root": str(repo_root),
        "status": "hard-stop" if hard_stops else "ok",
        "current_branch": current_branch,
        "mirror": {
            "branch": mirror_branch,
            "upstream_ref": upstream_ref,
            "ahead": ahead,
            "behind": behind,
        },
        "hard_stops": hard_stops,
        "warnings": warnings,
        "dirty_entries": dirty_entries,
    }
    return result, EXIT_HARD_STOP if hard_stops else 0


def is_ignorable_dirty_entry(entry: str) -> bool:
    if ".upstream-sync.yml" in entry:
        return True
    if ".upstream-sync/" in entry:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run upstream sync preflight checks against a target repository.")
    parser.add_argument("--repo", default=".", help="Path inside the target git repository")
    parser.add_argument("--config", default=None, help="Optional path to .upstream-sync.yml")
    args = parser.parse_args()

    result, exit_code = evaluate_repo(args.repo, args.config)
    print_json(result)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
