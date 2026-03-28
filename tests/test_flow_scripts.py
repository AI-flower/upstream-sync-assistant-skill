from __future__ import annotations

import sys
from pathlib import Path
import unittest

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from collect_git_facts import collect_git_facts  # noqa: E402
from merge_sync import EXIT_CONFLICT, perform_merge  # noqa: E402
from prepare_sync import prepare_sync  # noqa: E402
from render_report import render_reports  # noqa: E402
from verify_checks import run_checks  # noqa: E402
from tests.helpers import advance_upstream, create_sync_fixture, git, write_config  # noqa: E402


class FlowScriptsTest(unittest.TestCase):
    def test_prepare_collect_merge_verify_and_render(self) -> None:
        tmp, source, work = create_sync_fixture()
        self.addCleanup(tmp.cleanup)
        write_config(work)
        advance_upstream(source)

        context = prepare_sync(work, run_id="run-one")
        facts = collect_git_facts(work, context["run_dir"])
        merge_result, merge_code = perform_merge(work, context["run_dir"])
        verify_result, verify_code = run_checks(work, context["run_dir"])
        reports = render_reports(work, context["run_dir"])

        self.assertTrue(context["sync_branch"].startswith("sync/upstream-"))
        self.assertIn("upstream.txt", facts["changed_files"])
        self.assertEqual(merge_code, 0)
        self.assertTrue(merge_result["merged"])
        self.assertEqual(verify_code, 0)
        self.assertTrue(verify_result["passed"])
        self.assertTrue(Path(reports["risk_report"]).exists())
        self.assertTrue(Path(reports["pr_draft"]).exists())

    def test_merge_conflict_yields_conflict_json(self) -> None:
        tmp, source, work = create_sync_fixture()
        self.addCleanup(tmp.cleanup)
        write_config(work)

        (source / "README.md").write_text("upstream version\n", encoding="utf-8")
        git(source, "add", "README.md")
        git(source, "commit", "-m", "upstream readme")
        git(source, "push", "origin", "main")

        git(work, "checkout", "yl-main")
        (work / "README.md").write_text("internal version\n", encoding="utf-8")
        git(work, "add", "README.md")
        git(work, "commit", "-m", "internal readme")

        context = prepare_sync(work, run_id="run-conflict")
        collect_git_facts(work, context["run_dir"])
        merge_result, merge_code = perform_merge(work, context["run_dir"])

        self.assertEqual(merge_code, EXIT_CONFLICT)
        self.assertFalse(merge_result["merged"])
        self.assertIn("README.md", merge_result["conflicts"])

    def test_render_reports_uses_custom_pr_template(self) -> None:
        tmp, source, work = create_sync_fixture()
        self.addCleanup(tmp.cleanup)
        template_path = work / "docs" / "upstream-sync" / "pr-template.md"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(
            "# {title}\n\nRange: {upstream_range}\n\nChecks:\n{verification_checks}\n",
            encoding="utf-8",
        )
        write_config(
            work,
            reporting_extra="  pr_template: docs/upstream-sync/pr-template.md\n",
        )
        advance_upstream(source)

        context = prepare_sync(work, run_id="run-template")
        collect_git_facts(work, context["run_dir"])
        perform_merge(work, context["run_dir"])
        run_checks(work, context["run_dir"])
        reports = render_reports(work, context["run_dir"])

        pr_contents = Path(reports["pr_draft"]).read_text(encoding="utf-8")
        self.assertIn("Range: ", pr_contents)
        self.assertIn("Checks:", pr_contents)
        self.assertIn("python3 -c", pr_contents)


if __name__ == "__main__":
    unittest.main()
