import unittest
from unittest.mock import patch, MagicMock
import git_checker
def fake_result(stdout="", stderr="", returncode=0):
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result
class TestGetFilesList(unittest.TestCase):
    @patch("git_checker.subprocess.run")
    def test_parses_porcelain_status_lines(self, mock_run):
        mock_run.return_value = fake_result(stdout="M  modified.py\n?? untracked.py\n A staged_new.py\n")
        files = git_checker.GetFilesList()
        self.assertEqual(len(files), 3)
        self.assertEqual(
            files[0],
            {"filename": "modified.py", "staged": "M", "unstaged": " "},
        )
        self.assertEqual(
            files[1],
            {"filename": "untracked.py", "staged": "?", "unstaged": "?"},
        )

    @patch("git_checker.subprocess.run")
    def test_empty_status_returns_empty_list(self, mock_run):
        mock_run.return_value = fake_result(stdout="")
        self.assertEqual(git_checker.GetFilesList(), [])


class TestGetBranchesList(unittest.TestCase):
    @patch("git_checker.subprocess.run")
    def test_parses_branch_lines_and_skips_blanks(self, mock_run):
        mock_run.return_value = fake_result(stdout="* main\n  feature/x\n\n")
        branches = git_checker.GetBranchesList()
        self.assertEqual(branches, ["* main", "  feature/x"])


class TestDoCommit(unittest.TestCase):
    @patch("git_checker.subprocess.run")
    def test_returns_stdout_stderr_and_returncode(self, mock_run):
        mock_run.return_value = fake_result(stdout="ok", stderr="", returncode=0)
        stdout, stderr, code = git_checker.doCommit("feat: add thing")
        self.assertEqual((stdout, stderr, code), ("ok", "", 0))
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], ["git", "commit", "-m", "feat: add thing"])

    @patch("git_checker.subprocess.run")
    def test_failed_commit_reports_nonzero_code(self, mock_run):
        mock_run.return_value = fake_result(stderr="nothing to commit", returncode=1)
        _, stderr, code = git_checker.doCommit("empty commit")
        self.assertEqual(code, 1)
        self.assertIn("nothing to commit", stderr)


class TestGetConflicts(unittest.TestCase):
    @patch("git_checker.subprocess.run")
    def test_returns_list_of_conflicted_files(self, mock_run):
        mock_run.return_value = fake_result(stdout="a.py\nb.py\n")
        self.assertEqual(git_checker.getConflicts(), ["a.py", "b.py"])

    @patch("git_checker.subprocess.run")
    def test_no_conflicts_returns_empty_list(self, mock_run):
        mock_run.return_value = fake_result(stdout="")
        self.assertEqual(git_checker.getConflicts(), [])
class TestIsGitRepo(unittest.TestCase):
    @patch("git_checker.os.path.isdir")
    def test_false_when_git_dir_missing(self, mock_isdir):
        mock_isdir.return_value = False
        self.assertFalse(git_checker.is_git_repo("/some/path"))


class TestDoPush(unittest.TestCase):
    @patch("git_checker.subprocess.run")
    def test_normal_push_success_does_not_retry(self, mock_run):
        mock_run.return_value = fake_result(stdout="pushed", returncode=0)
        stdout, stderr, code = git_checker.doPush()
        self.assertEqual(code, 0)
        mock_run.assert_called_once()

    @patch("git_checker.getCurrentBranch")
    @patch("git_checker.subprocess.run")
    def test_missing_upstream_retries_with_set_upstream(self, mock_run, mock_current_branch):
        mock_current_branch.return_value = "feature/x"
        first_fail = fake_result(stderr="fatal: has no upstream branch", returncode=128)
        second_success = fake_result(stdout="pushed with upstream", returncode=0)
        mock_run.side_effect = [first_fail, second_success]

        stdout, stderr, code = git_checker.doPush()

        self.assertEqual(code, 0)
        self.assertEqual(stdout, "pushed with upstream")
        self.assertEqual(mock_run.call_count, 2)
        second_call_args = mock_run.call_args_list[1][0][0]
        self.assertEqual(
            second_call_args, ["git", "push", "--set-upstream", "origin", "feature/x"]
        )

    @patch("git_checker.subprocess.run")
    def test_other_failure_does_not_retry(self, mock_run):
        mock_run.return_value = fake_result(stderr="fatal: some other error", returncode=1)
        stdout, stderr, code = git_checker.doPush()
        self.assertEqual(code, 1)
        mock_run.assert_called_once()


class TestDoCommand(unittest.TestCase):
    @patch("git_checker.subprocess.run")
    def test_runs_parsed_shell_command(self, mock_run):
        mock_run.return_value = fake_result(stdout="output", returncode=0)
        stdout, stderr, code = git_checker.doCommand("git status")
        self.assertEqual(stdout, "output")
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], ["git", "status"])

    def test_unparseable_command_returns_error(self):
        stdout, stderr, code = git_checker.doCommand('git commit -m "unterminated')
        self.assertEqual(code, 1)
        self.assertIn("Could not parse command", stderr)

    @patch("git_checker.subprocess.run", side_effect=FileNotFoundError)
    def test_missing_executable_returns_127(self, mock_run):
        stdout, stderr, code = git_checker.doCommand("not-a-real-command")
        self.assertEqual(code, 127)

if __name__ == "__main__":
    unittest.main()
