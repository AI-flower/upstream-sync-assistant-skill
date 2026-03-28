#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import load_config, print_json, read_json, resolve_repo_root, shorten_sha, write_markdown  # noqa: E402


def render_reports(repo_root: str | Path, run_dir: str | Path, config_path: str | Path | None = None) -> dict:
    repo_root = resolve_repo_root(repo_root)
    run_dir = Path(run_dir)
    config = load_config(repo_root, config_path)
    context = read_json(run_dir / "context.json")
    git_facts = read_json(run_dir / "git-facts.json") if (run_dir / "git-facts.json").exists() else {}
    merge = read_json(run_dir / "merge.json") if (run_dir / "merge.json").exists() else {}
    verify = read_json(run_dir / "verify.json") if (run_dir / "verify.json").exists() else {}

    risk_report = build_risk_report(context, git_facts, merge, verify)
    pr_draft = build_pr_draft(repo_root, config, context, git_facts, merge, verify)

    risk_path = run_dir / "risk-report.md"
    pr_path = run_dir / "pr-draft.md"
    write_markdown(risk_path, risk_report)
    write_markdown(pr_path, pr_draft)

    return {
        "risk_report": str(risk_path),
        "pr_draft": str(pr_path),
    }


def build_risk_report(context: dict, git_facts: dict, merge: dict, verify: dict) -> str:
    lines = [
        "# Risk Report",
        "",
        f"- Sync branch: `{context['sync_branch']}`",
        f"- Mirror target: `{context['mirror_target_ref']}`",
        f"- Range: `{shorten_sha(context['from_sha'])}..{shorten_sha(context['to_sha'])}`",
        f"- Upstream commits: `{git_facts.get('commit_count', 0)}`",
    ]

    if git_facts.get("high_risk_path_hits"):
        lines.extend(["", "## High-Risk Paths", *[f"- `{path}`" for path in git_facts["high_risk_path_hits"]]])
    if git_facts.get("high_risk_file_hits"):
        lines.extend(["", "## High-Risk Files", *[f"- `{path}`" for path in git_facts["high_risk_file_hits"]]])
    if git_facts.get("infra_keyword_hits"):
        lines.extend(["", "## Infrastructure Keywords", *[f"- `{item}`" for item in git_facts["infra_keyword_hits"]]])

    lines.extend(
        [
            "",
            "## Merge Outcome",
            f"- Merged: `{merge.get('merged', False)}`",
        ]
    )
    if merge.get("conflicts"):
        lines.extend([*[f"- Conflict: `{path}`" for path in merge["conflicts"]]])

    lines.extend(["", "## Verification"])
    for check in verify.get("checks", []):
        lines.append(f"- `{check['command']}` -> exit `{check['exit_code']}`")
    for manual_check in verify.get("manual_checks", []):
        lines.append(f"- Manual: {manual_check}")
    return "\n".join(lines)


def build_pr_draft(repo_root: Path, config: dict, context: dict, git_facts: dict, merge: dict, verify: dict) -> str:
    integration_branch = config["git"]["integration_branch"]
    title = f"sync: merge {context['mirror_target_ref']} into {integration_branch}"
    template_path = config.get("reporting", {}).get("pr_template")
    placeholders = build_placeholders(title, context, git_facts, merge, verify)
    if template_path:
        candidate = (repo_root / template_path).resolve()
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").format(**placeholders)

    lines = [
        f"# {title}",
        "",
        "## Summary",
        f"- Sync branch: `{context['sync_branch']}`",
        f"- Upstream range: `{shorten_sha(context['from_sha'])}..{shorten_sha(context['to_sha'])}`",
        f"- Upstream commits included: `{git_facts.get('commit_count', 0)}`",
        "",
        "## Notable Changes",
    ]
    commits = git_facts.get("commits", [])[:10]
    if commits:
        lines.extend([f"- `{shorten_sha(item['sha'])}` {item['subject']}" for item in commits])
    else:
        lines.append("- No upstream commits recorded in the collected facts.")

    lines.extend(["", "## Risk Notes"])
    if git_facts.get("high_risk_path_hits") or git_facts.get("high_risk_file_hits") or git_facts.get("infra_keyword_hits"):
        for item in git_facts.get("high_risk_path_hits", []):
            lines.append(f"- High-risk path changed: `{item}`")
        for item in git_facts.get("high_risk_file_hits", []):
            lines.append(f"- High-risk file changed: `{item}`")
        for item in git_facts.get("infra_keyword_hits", []):
            lines.append(f"- Infrastructure keyword hit: `{item}`")
    else:
        lines.append("- No configured high-risk hits detected.")

    lines.extend(["", "## Merge"])
    lines.append(f"- Merge succeeded: `{merge.get('merged', False)}`")
    for conflict in merge.get("conflicts", []):
        lines.append(f"- Conflict: `{conflict}`")

    lines.extend(["", "## Verification"])
    for check in verify.get("checks", []):
        lines.append(f"- `{check['command']}` -> exit `{check['exit_code']}`")
    for manual in verify.get("manual_checks", []):
        lines.append(f"- Manual follow-up: {manual}")
    lines.extend(["", "## Next Steps", "- Review high-risk hits", "- Resolve any remaining manual checks"])
    return "\n".join(lines)


def build_placeholders(title: str, context: dict, git_facts: dict, merge: dict, verify: dict) -> dict:
    return {
        "title": title,
        "sync_branch": context["sync_branch"],
        "mirror_target_ref": context["mirror_target_ref"],
        "upstream_range": f"{shorten_sha(context['from_sha'])}..{shorten_sha(context['to_sha'])}",
        "commit_count": git_facts.get("commit_count", 0),
        "notable_changes": render_bullets(
            [f"`{shorten_sha(item['sha'])}` {item['subject']}" for item in git_facts.get("commits", [])[:10]]
        ),
        "high_risk_paths": render_bullets([f"`{item}`" for item in git_facts.get("high_risk_path_hits", [])]),
        "high_risk_files": render_bullets([f"`{item}`" for item in git_facts.get("high_risk_file_hits", [])]),
        "infra_keyword_hits": render_bullets([f"`{item}`" for item in git_facts.get("infra_keyword_hits", [])]),
        "merge_conflicts": render_bullets([f"`{item}`" for item in merge.get("conflicts", [])]),
        "verification_checks": render_bullets(
            [f"`{item['command']}` -> exit `{item['exit_code']}`" for item in verify.get("checks", [])]
        ),
        "manual_checks": render_bullets([str(item) for item in verify.get("manual_checks", [])]),
    }


def render_bullets(items: list[str]) -> str:
    if not items:
        return "- None"
    return "\n".join([f"- {item}" for item in items])


def main() -> int:
    parser = argparse.ArgumentParser(description="Render markdown reports from upstream sync run artifacts.")
    parser.add_argument("--repo", default=".", help="Path inside the target git repository")
    parser.add_argument("--run-dir", required=True, help="Path to the run directory")
    parser.add_argument("--config", default=None, help="Optional path to .upstream-sync.yml")
    args = parser.parse_args()

    result = render_reports(args.repo, args.run_dir, args.config)
    print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
