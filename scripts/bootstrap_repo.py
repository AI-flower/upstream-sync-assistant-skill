#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import print_json, resolve_repo_root, run_git, write_yaml  # noqa: E402


def inspect_repository(repo_root: str | Path) -> dict:
    repo_root = resolve_repo_root(repo_root)
    remotes = [line.strip() for line in run_git(repo_root, ["remote"]).splitlines() if line.strip()]
    current_branch = run_git(repo_root, ["branch", "--show-current"])

    branch_rows = run_git(
        repo_root,
        ["for-each-ref", "refs/heads", "--format=%(refname:short)|%(upstream:short)|%(objectname)"],
    ).splitlines()
    branches = []
    for row in branch_rows:
        if not row:
            continue
        name, upstream, sha = row.split("|", 2)
        branches.append({"name": name, "upstream": upstream, "sha": sha})

    candidates = {
        "upstream_remote": infer_upstream_remote(remotes),
        "write_remote": infer_write_remote(remotes, branches, current_branch),
    }

    upstream_remote = candidates["upstream_remote"]["value"]
    write_remote = candidates["write_remote"]["value"]
    mirror_branch = infer_mirror_branch(branches, upstream_remote)
    candidates["mirror_branch"] = mirror_branch
    candidates["integration_branch"] = infer_integration_branch(
        branches,
        current_branch,
        mirror_branch["value"],
        write_remote,
    )

    return {
        "repo_root": str(repo_root),
        "current_branch": current_branch,
        "remotes": remotes,
        "branches": branches,
        "candidates": candidates,
    }


def infer_upstream_remote(remotes: list[str]) -> dict:
    if "upstream" in remotes:
        return {"value": "upstream", "confidence": "high"}
    if len(remotes) == 1:
        return {"value": remotes[0], "confidence": "medium"}
    return {"value": remotes[0] if remotes else "", "confidence": "low"}


def infer_write_remote(remotes: list[str], branches: list[dict], current_branch: str) -> dict:
    if "origin" in remotes:
        return {"value": "origin", "confidence": "high"}
    for branch in branches:
        if branch["name"] == current_branch and branch["upstream"]:
            remote_name = branch["upstream"].split("/", 1)[0]
            return {"value": remote_name, "confidence": "medium"}
    return {"value": remotes[0] if remotes else "", "confidence": "low"}


def infer_mirror_branch(branches: list[dict], upstream_remote: str) -> dict:
    preferred = [f"{upstream_remote}/main", f"{upstream_remote}/master"]
    for branch in branches:
        if branch["upstream"] in preferred:
            return {"value": branch["name"], "confidence": "high"}
    for candidate in ("main", "master"):
        for branch in branches:
            if branch["name"] == candidate:
                return {"value": candidate, "confidence": "medium"}
    return {"value": branches[0]["name"] if branches else "", "confidence": "low"}


def infer_integration_branch(branches: list[dict], current_branch: str, mirror_branch: str, write_remote: str) -> dict:
    ranked: list[tuple[int, dict]] = []
    for branch in branches:
        name = branch["name"]
        if name == mirror_branch:
            continue
        score = 0
        upstream_remote = branch["upstream"].split("/", 1)[0] if branch["upstream"] else ""
        if upstream_remote == write_remote:
            score += 6
        if "/" not in name:
            score += 2
        lowered = name.lower()
        if lowered in {"develop", "development", "staging", "release", "yl-main"}:
            score += 8
        if lowered.endswith("main"):
            score += 7
        if "release" in lowered or "staging" in lowered or "develop" in lowered:
            score += 5
        if name == current_branch and upstream_remote == write_remote:
            score += 1
        ranked.append((score, branch))

    if not ranked:
        return {"value": mirror_branch, "confidence": "low"}

    ranked.sort(key=lambda item: (item[0], item[1]["name"]), reverse=True)
    best_score, best_branch = ranked[0]
    confidence = "high" if best_score >= 10 else "medium" if best_score >= 6 else "low"
    return {"value": best_branch["name"], "confidence": confidence}


def write_bootstrap_config(
    repo_root: str | Path,
    overrides: dict | None = None,
    output_path: str | Path | None = None,
) -> Path:
    repo_root = resolve_repo_root(repo_root)
    details = inspect_repository(repo_root)
    candidates = details["candidates"]
    overrides = overrides or {}

    config = {
        "version": 1,
        "git": {
            "upstream_remote": overrides.get("upstream_remote", candidates["upstream_remote"]["value"]),
            "write_remote": overrides.get("write_remote", candidates["write_remote"]["value"]),
            "mirror_branch": overrides.get("mirror_branch", candidates["mirror_branch"]["value"]),
            "integration_branch": overrides.get("integration_branch", candidates["integration_branch"]["value"]),
            "sync_branch_prefix": overrides.get("sync_branch_prefix", "sync/upstream-"),
        },
        "policy": {
            "require_clean_worktree": True,
            "require_confirmation_for_push": True,
            "require_confirmation_for_mirror_branch_change": True,
            "block_push_to_upstream": True,
        },
        "sync": {
            "cadence_days": overrides.get("cadence_days", 7),
        },
        "analysis": {
            "high_risk_paths": overrides.get("high_risk_paths", []),
            "high_risk_files": overrides.get("high_risk_files", []),
            "infra_keywords": overrides.get(
                "infra_keywords",
                ["package.json", "yarn.lock", "pod", "gradle", "docker", "migration", "env"],
            ),
            "customizations_registry": overrides.get(
                "customizations_registry",
                "docs/upstream-sync/customizations.md",
            ),
        },
        "validation": {
            "post_merge_checks": overrides.get("post_merge_checks", []),
            "manual_checks": overrides.get("manual_checks", ["core login flow", "core session flow"]),
        },
        "reporting": {
            "output_dir": overrides.get("output_dir", "docs/upstream-sync/reports"),
        },
    }
    if overrides.get("pr_template"):
        config["reporting"]["pr_template"] = overrides["pr_template"]
    if overrides.get("freeze_windows"):
        config["sync"]["freeze_windows"] = overrides["freeze_windows"]

    target = Path(output_path).expanduser().resolve() if output_path else repo_root / ".upstream-sync.yml"
    write_yaml(target, config)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a repository and infer upstream sync configuration candidates.")
    parser.add_argument("--repo", default=".", help="Path inside the target git repository")
    parser.add_argument("--write-config", action="store_true", help="Write an inferred .upstream-sync.yml file")
    parser.add_argument("--output", default=None, help="Optional path for the generated config file")
    parser.add_argument("--integration-branch", default=None, help="Override integration branch in generated config")
    parser.add_argument("--sync-branch-prefix", default="sync/upstream-", help="Override sync branch prefix in generated config")
    parser.add_argument(
        "--post-merge-check",
        action="append",
        default=None,
        help="Add a post-merge verification command when writing config",
    )
    args = parser.parse_args()

    if args.write_config:
        target = write_bootstrap_config(
            args.repo,
            {
                "integration_branch": args.integration_branch,
                "sync_branch_prefix": args.sync_branch_prefix,
                "post_merge_checks": args.post_merge_check or [],
            },
            args.output,
        )
        print_json({"config_path": str(target)})
        return 0

    result = inspect_repository(args.repo)
    print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
