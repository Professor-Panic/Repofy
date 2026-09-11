import os
import shutil
import subprocess
import tempfile
import unittest

import git_checker


def sh(*args, cwd=None, check=True):
    #Run a actual commands  for test setup used as a base to test git_checker
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result


class GitRepoTestCase(unittest.TestCase):
    """Base class: creates a real git repo in a temp dir and chdirs into it
    so git_checker's subprocess calls (which rely on process cwd) operate
    on it. Cleans up afterwards regardless of test outcome."""
    def setUp(self):
        self.repo_dir = tempfile.mkdtemp(prefix="git_checker_test_")
        self._old_cwd = os.getcwd()
        os.chdir(self.repo_dir)
        sh("init", "-q", "-b", "main")
        sh("config", "user.email", "simulation_world4@gmail.com")
        sh("config", "user.name", "Professor_Panic")

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.repo_dir, ignore_errors=True)

    def write(self, filename, content="content\n"):
        with open(os.path.join(self.repo_dir, filename), "w") as f:
            f.write(content)

    def commit_all(self, message="initial commit"):
        sh("add", "-A")
        sh("commit", "-q", "-m", message)


class TestGetFilesList(GitRepoTestCase):
    def test_parses_real_status_for_staged_modified_and_untracked(self):
        # Baseline file, committed, so we can dirty it later.
        self.write("tracked.py", "line1\n")
        self.commit_all()

        # Unstaged modification -> " M tracked.py"
        self.write("tracked.py", "line1\nline2\n")

        # New file, staged -> "A  staged.py"
        self.write("staged.py")
        sh("add", "staged.py")

        # New file, not staged -> "?? untracked.py"
        self.write("untracked.py")

        files = git_checker.GetFilesList()
        by_name = {f["filename"]: f for f in files}

        self.assertEqual(len(files), 3)
        self.assertEqual(by_name["tracked.py"], {"filename": "tracked.py", "staged": " ", "unstaged": "M"})
        self.assertEqual(by_name["staged.py"], {"filename": "staged.py", "staged": "A", "unstaged": " "})
        self.assertEqual(by_name["untracked.py"], {"filename": "untracked.py", "staged": "?", "unstaged": "?"})

    def test_clean_repo_returns_empty_list(self):
        self.write("committed.py")
        self.commit_all()
        self.assertEqual(git_checker.GetFilesList(), [])


class TestGetBranchesList(GitRepoTestCase):
    def test_lists_current_and_other_branches(self):
        self.write("f.py")
        self.commit_all()
        sh("branch", "feature/x")

        branches = git_checker.GetBranchesList()

        self.assertIn("* main", branches)
        self.assertIn("  feature/x", branches)
        self.assertEqual(len(branches), 2)

    def test_current_branch_matches_getCurrentBranch(self):
        self.write("f.py")
        self.commit_all()
        current = git_checker.getCurrentBranch()
        branches = git_checker.GetBranchesList()
        self.assertIn(f"* {current}", branches)


class TestDoCommit(GitRepoTestCase):
    def test_commit_with_staged_changes_succeeds(self):
        self.write("new.py")
        sh("add", "new.py")

        stdout, stderr, code = git_checker.doCommit("feat: add new.py")

        self.assertEqual(code, 0)
        self.assertIn("feat: add new.py", stdout)
        # Nothing left staged after a successful commit.
        self.assertEqual(git_checker.GetFilesList(), [])

    def test_commit_with_nothing_staged_fails(self):
        self.write("committed.py")
        self.commit_all()  # working tree is now clean

        stdout, stderr, code = git_checker.doCommit("empty commit")

        self.assertNotEqual(code, 0)
        # Real git puts this message on stdout (with a nonzero exit code),
        # not stderr -- confirmed by running it for real, not assumed.
        self.assertIn("nothing to commit", stdout.lower())


class TestGetConflicts(GitRepoTestCase):
    def test_detects_real_merge_conflict(self):
        self.write("f.txt", "base\n")
        self.commit_all()

        sh("checkout", "-q", "-b", "feature")
        self.write("f.txt", "feature change\n")
        self.commit_all("feature change")

        sh("checkout", "-q", "main")
        self.write("f.txt", "main change\n")
        self.commit_all("main change")

        sh("merge", "feature", check=False)  # expected to conflict

        self.assertTrue(git_checker.isMergeInProgress())
        self.assertEqual(git_checker.getConflicts(), ["f.txt"])

    def test_no_conflicts_on_clean_repo(self):
        self.write("f.txt")
        self.commit_all()
        self.assertEqual(git_checker.getConflicts(), [])
        self.assertFalse(git_checker.isMergeInProgress())


class TestMergeResolution(GitRepoTestCase):
    def test_abort_merge_clears_conflict_state(self):
        self.write("f.txt", "base\n")
        self.commit_all()
        sh("checkout", "-q", "-b", "feature")
        self.write("f.txt", "feature\n")
        self.commit_all("feature change")
        sh("checkout", "-q", "main")
        self.write("f.txt", "main\n")
        self.commit_all("main change")
        sh("merge", "feature", check=False)
        self.assertTrue(git_checker.isMergeInProgress())

        stdout, stderr, code = git_checker.abortMerge()

        self.assertEqual(code, 0)
        self.assertFalse(git_checker.isMergeInProgress())
        self.assertEqual(git_checker.getConflicts(), [])

    def test_continue_merge_after_resolving(self):
        self.write("f.txt", "base\n")
        self.commit_all()
        sh("checkout", "-q", "-b", "feature")
        self.write("f.txt", "feature\n")
        self.commit_all("feature change")
        sh("checkout", "-q", "main")
        self.write("f.txt", "main\n")
        self.commit_all("main change")
        sh("merge", "feature", check=False)

        # Resolve by hand, the way a user would in the TUI.
        self.write("f.txt", "resolved\n")
        sh("add", "f.txt")

        stdout, stderr, code = git_checker.continueMerge()

        self.assertEqual(code, 0)
        self.assertFalse(git_checker.isMergeInProgress())


class TestIsGitRepo(GitRepoTestCase):
    def test_true_inside_real_repo(self):
        self.assertTrue(git_checker.is_git_repo(self.repo_dir))

    def test_false_outside_any_repo(self):
        plain_dir = tempfile.mkdtemp(prefix="not_a_repo_")
        try:
            self.assertFalse(git_checker.is_git_repo(plain_dir))
        finally:
            shutil.rmtree(plain_dir, ignore_errors=True)


class TestDoPush(GitRepoTestCase):
    def setUp(self):
        super().setUp()
        self.remote_dir = tempfile.mkdtemp(prefix="git_checker_remote_")
        sh("init", "-q", "--bare", self.remote_dir)
        sh("remote", "add", "origin", self.remote_dir)
        self.write("f.py")
        self.commit_all()

    def tearDown(self):
        shutil.rmtree(self.remote_dir, ignore_errors=True)
        super().tearDown()

    def test_push_without_upstream_retries_and_succeeds(self):
        # No `git push -u` has happened yet, so the first attempt should
        # fail with "no upstream branch" and doPush() should retry with
        # --set-upstream on its own.
        stdout, stderr, code = git_checker.doPush()

        self.assertEqual(code, 0)
        # Confirm it actually landed on the remote, and upstream tracking
        # is now configured (proves the --set-upstream retry really ran).
        current = git_checker.getCurrentBranch()
        remote_branches = sh("ls-remote", "--heads", self.remote_dir).stdout
        self.assertIn(current, remote_branches)
        tracking = sh("rev-parse", "--abbrev-ref", f"{current}@{{upstream}}")
        self.assertEqual(tracking.stdout.strip(), f"origin/{current}")

    def test_push_with_existing_upstream_succeeds_on_first_try(self):
        current = git_checker.getCurrentBranch()
        sh("push", "-u", "origin", current)  # establish upstream out-of-band
        self.write("more.py")
        self.commit_all("more changes")

        stdout, stderr, code = git_checker.doPush()

        self.assertEqual(code, 0)
        remote_log = sh("log", "--oneline", "-1", "main", cwd=self.remote_dir).stdout
        self.assertIn("more changes", sh("log", "-1", "--format=%s").stdout)

    def test_push_to_broken_remote_fails_without_set_upstream_retry(self):
        sh("remote", "set-url", "origin", "/nonexistent/path/does-not-exist")

        stdout, stderr, code = git_checker.doPush()

        self.assertNotEqual(code, 0)
        # A genuinely broken remote isn't a missing-upstream situation, so
        # doPush() shouldn't claim success or fabricate an upstream retry.
        self.assertNotIn("has no upstream branch", stderr)


class TestDoCommand(GitRepoTestCase):
    def test_runs_real_git_command(self):
        stdout, stderr, code = git_checker.doCommand("git rev-parse --is-inside-work-tree")
        self.assertEqual(code, 0)
        self.assertEqual(stdout.strip(), "true")

    def test_runs_non_git_shell_command(self):
        stdout, stderr, code = git_checker.doCommand("echo hello")
        self.assertEqual(code, 0)
        self.assertEqual(stdout.strip(), "hello")

    def test_unparseable_command_returns_error(self):
        stdout, stderr, code = git_checker.doCommand('git commit -m "unterminated')
        self.assertEqual(code, 1)
        self.assertIn("Could not parse command", stderr)

    def test_missing_executable_returns_127(self):
        stdout, stderr, code = git_checker.doCommand("not-a-real-command-xyz123")
        self.assertEqual(code, 127)


if __name__ == "__main__":
    unittest.main()