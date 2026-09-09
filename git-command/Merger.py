from Git_command import GitCommand


class PullCommand(GitCommand):
    def __init__(self, remote: str = "origin", branch: str | None = None) -> None:
        self.remote = remote
        self.branch = branch

    @property
    def command(self) -> list[str]:
        return ["git", "pull", self.remote, *([self.branch] if self.branch else [])]


class MergeCommand(GitCommand):
    def __init__(self, branch: str) -> None:
        self.branch = branch

    @property
    def command(self) -> list[str]:
        return ["git", "merge", self.branch]
