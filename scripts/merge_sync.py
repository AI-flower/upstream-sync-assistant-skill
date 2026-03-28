#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import EXIT_CONFLICT, print_json, read_json, resolve_repo_root, run_git, write_json  # noqa: E402


def perform_merge(repo_root: str | Path, run_dir: str | Path) -> tuple[dict, int]:
    repo_root = resolve_repo_root(repo_root)
    run_dir = Path(run_dir)
    context = read_json(run_dir / "context.json")

    run_git(repo_root, ["checkout", context["sync_branch"]])
    result = subprocess.run(
        ["git", "merge", "--no-edit", context["mirror_target_ref"]],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    conflict_files = [line for line in run_git(repo_root, ["diff", "--name-only", "--diff-filter=U"], check=False).splitlines() if line]
    merge_result = {
        "sync_branch": context["sync_branch"],
        "mirror_target_ref": context["mirror_target_ref"],
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "conflicts": conflict_files,
    }

    if result.returncode == 0:
        merge_result["merged"] = True
        merge_result["head_sha"] = run_git(repo_root, ["rev-parse", "HEAD"])
        write_json(run_dir / "merge.json", merge_result)
        return merge_result, 0

    merge_result["merged"] = False
    write_json(run_dir / "merge.json", merge_result)
    if conflict_files:
        return merge_result, EXIT_CONFLICT
    return merge_result, 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge upstream into the prepared local sync branch.")
    parser.add_argument("--repo", default=".", help="Path inside the target git repository")
    parser.add_argument("--run-dir", required=True, help="Path to the run directory")
    args = parser.parse_args()

    result, exit_code = perform_merge(args.repo, args.run_dir)
    print_json(result)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
