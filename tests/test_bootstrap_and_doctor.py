from __future__ import annotations

import sys
from pathlib import Path
import unittest

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from bootstrap_repo import inspect_repository, write_bootstrap_config  # noqa: E402
from doctor import EXIT_HARD_STOP, evaluate_repo  # noqa: E402
from tests.helpers import create_sync_fixture, git, write_config  # noqa: E402


class BootstrapAndDoctorTest(unittest.TestCase):
    def test_bootstrap_infers_expected_candidates(self) -> None:
        tmp, _source, work = create_sync_fixture()
        self.addCleanup(tmp.cleanup)

        result = inspect_repository(work)

        self.assertEqual(result["candidates"]["upstream_remote"]["value"], "upstream")
        self.assertEqual(result["candidates"]["write_remote"]["value"], "origin")
        self.assertEqual(result["candidates"]["mirror_branch"]["value"], "main")
        self.assertEqual(result["candidates"]["integration_branch"]["value"], "yl-main")

    def test_bootstrap_prefers_tracked_internal_branch_over_temporary_branch(self) -> None:
        tmp, _source, work = create_sync_fixture()
        self.addCleanup(tmp.cleanup)
        git(work, "checkout", "-b", "design/scratch")

        result = inspect_repository(work)

        self.assertEqual(result["current_branch"], "design/scratch")
        self.assertEqual(result["candidates"]["integration_branch"]["value"], "yl-main")

    def test_doctor_passes_clean_fixture(self) -> None:
        tmp, _source, work = create_sync_fixture()
        self.addCleanup(tmp.cleanup)
        write_config(work)

        result, exit_code = evaluate_repo(work)

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mirror"]["ahead"], 0)
        self.assertEqual(result["mirror"]["behind"], 0)

    def test_doctor_detects_polluted_mirror_branch(self) -> None:
        tmp, _source, work = create_sync_fixture()
        self.addCleanup(tmp.cleanup)
        write_config(work)
        git(work, "checkout", "main")
        (work / "polluted.txt").write_text("bad\n", encoding="utf-8")
        git(work, "add", "polluted.txt")
        git(work, "commit", "-m", "pollute mirror")

        result, exit_code = evaluate_repo(work)

        self.assertEqual(exit_code, EXIT_HARD_STOP)
        self.assertTrue(any(item["code"] == "mirror_polluted" for item in result["hard_stops"]))

    def test_doctor_detects_dirty_worktree(self) -> None:
        tmp, _source, work = create_sync_fixture()
        self.addCleanup(tmp.cleanup)
        write_config(work)
        (work / "README.md").write_text("dirty\n", encoding="utf-8")

        result, exit_code = evaluate_repo(work)

        self.assertEqual(exit_code, EXIT_HARD_STOP)
        self.assertTrue(any(item["code"] == "dirty_worktree" for item in result["hard_stops"]))

    def test_bootstrap_can_write_repo_config(self) -> None:
        tmp, _source, work = create_sync_fixture()
        self.addCleanup(tmp.cleanup)

        config_path = write_bootstrap_config(
            work,
            {
                "integration_branch": "yl-main",
                "sync_branch_prefix": "sync/upstream-",
                "post_merge_checks": ['python3 -c "print(\'ok\')"'],
            },
        )

        contents = config_path.read_text(encoding="utf-8")
        self.assertIn("integration_branch: yl-main", contents)
        self.assertIn("sync_branch_prefix: sync/upstream-", contents)

    def test_doctor_warns_when_cadence_exceeded(self) -> None:
        tmp, source, work = create_sync_fixture()
        self.addCleanup(tmp.cleanup)
        write_config(work, extra_sync="  cadence_days: 0\n")
        git(work, "checkout", "yl-main")
        advance_commit = source / "late.txt"
        advance_commit.write_text("late\n", encoding="utf-8")
        git(source, "add", "late.txt")
        git(source, "commit", "-m", "late sync")
        git(source, "push", "origin", "main")
        git(work, "checkout", "main")
        git(work, "fetch", "upstream")

        result, exit_code = evaluate_repo(work)

        self.assertEqual(exit_code, 0)
        self.assertTrue(any(item["code"] == "cadence_exceeded" for item in result["warnings"]))

    def test_doctor_warns_when_freeze_window_matches_branch(self) -> None:
        tmp, _source, work = create_sync_fixture()
        self.addCleanup(tmp.cleanup)
        write_config(
            work,
            extra_sync="  cadence_days: 7\n  freeze_windows:\n    - name: release-freeze\n      branches:\n        - yl-main\n",
        )

        result, exit_code = evaluate_repo(work)

        self.assertEqual(exit_code, 0)
        self.assertTrue(any(item["code"] == "freeze_window_active" for item in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
