from __future__ import annotations

import sys
from pathlib import Path
import unittest

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import create_run_dir, load_config, run_git  # noqa: E402
from tests.helpers import init_basic_repo, write_config  # noqa: E402


class CommonHelpersTest(unittest.TestCase):
    def test_load_config_parses_expected_fields(self) -> None:
        tmp, repo = init_basic_repo()
        self.addCleanup(tmp.cleanup)
        write_config(repo)

        config = load_config(repo)

        self.assertEqual(config["git"]["mirror_branch"], "main")
        self.assertEqual(config["git"]["integration_branch"], "yl-main")
        self.assertEqual(config["policy"]["require_clean_worktree"], True)

    def test_create_run_dir_creates_timestamped_structure(self) -> None:
        tmp, repo = init_basic_repo()
        self.addCleanup(tmp.cleanup)

        run_dir = create_run_dir(repo, "manual-run")

        self.assertTrue(run_dir.exists())
        self.assertEqual(run_dir.name, "manual-run")
        self.assertEqual(run_dir.parent.parent.name, ".upstream-sync")

    def test_run_git_returns_stdout(self) -> None:
        tmp, repo = init_basic_repo()
        self.addCleanup(tmp.cleanup)

        current_branch = run_git(repo, ["branch", "--show-current"])

        self.assertEqual(current_branch, "main")


if __name__ == "__main__":
    unittest.main()
