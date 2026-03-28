#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import load_config, print_json, read_json, resolve_repo_root, run_git, write_json  # noqa: E402


def collect_git_facts(repo_root: str | Path, run_dir: str | Path, config_path: str | Path | None = None) -> dict:
    repo_root = resolve_repo_root(repo_root)
    run_dir = Path(run_dir)
    config = load_config(repo_root, config_path)
    context = read_json(run_dir / "context.json")
    analysis_cfg = config.get("analysis", {})

    commit_rows = run_git(
        repo_root,
        ["log", "--no-merges", "--format=%H|%s", f"{context['from_sha']}..{context['to_sha']}"],
    ).splitlines()
    commits = []
    commit_text = []
    for row in commit_rows:
        if not row:
            continue
        sha, subject = row.split("|", 1)
        commits.append({"sha": sha, "subject": subject})
        commit_text.append(subject.lower())

    diff_rows = run_git(repo_root, ["diff", "--name-status", f"{context['from_sha']}..{context['to_sha']}"]).splitlines()
    changed_files: list[str] = []
    deleted_files: list[str] = []
    renamed_files: list[dict] = []
    for row in diff_rows:
        if not row:
            continue
        parts = row.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            renamed_files.append({"from": parts[1], "to": parts[2]})
            changed_files.append(parts[2])
            continue
        path = parts[-1]
        changed_files.append(path)
        if status == "D":
            deleted_files.append(path)

    high_risk_paths = analysis_cfg.get("high_risk_paths", [])
    high_risk_files = analysis_cfg.get("high_risk_files", [])
    infra_keywords = [keyword.lower() for keyword in analysis_cfg.get("infra_keywords", [])]

    path_hits = sorted({path for path in changed_files for prefix in high_risk_paths if path.startswith(prefix)})
    file_hits = sorted(
        {
            path
            for path in changed_files
            for flagged in high_risk_files
            if path == flagged or Path(path).name == Path(flagged).name
        }
    )

    search_space = " ".join(changed_files + commit_text).lower()
    infra_hits = sorted({keyword for keyword in infra_keywords if keyword in search_space})

    result = {
        "from_sha": context["from_sha"],
        "to_sha": context["to_sha"],
        "commit_count": len(commits),
        "commits": commits,
        "changed_files": changed_files,
        "deleted_files": deleted_files,
        "renamed_files": renamed_files,
        "high_risk_path_hits": path_hits,
        "high_risk_file_hits": file_hits,
        "infra_keyword_hits": infra_hits,
    }
    write_json(run_dir / "git-facts.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect structured git facts for an upstream sync run.")
    parser.add_argument("--repo", default=".", help="Path inside the target git repository")
    parser.add_argument("--run-dir", required=True, help="Path to the run directory")
    parser.add_argument("--config", default=None, help="Optional path to .upstream-sync.yml")
    args = parser.parse_args()

    result = collect_git_facts(args.repo, args.run_dir, args.config)
    print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
