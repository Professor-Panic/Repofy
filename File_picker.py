from Git_command import GitCommand


class PushCommand(GitCommand):
    def __init__(self, remote: str = "origin", branch: str | None = None) -> None:
        self.remote = remote
        self.branch = branch

    @property
    def command(self) -> list[str]:
        return ["git", "push", self.remote, *([self.branch] if self.branch else [])]