from Git_command import GitCommand


class StatusCommand(GitCommand):
    @property
    def command(self) -> list[str]:
        return ["git", "status"]


class AddCommand(GitCommand):
    def __init__(self, paths: list[str] | None = None) -> None:
        self.paths = paths or ["."]

    @property
    def command(self) -> list[str]:
        return ["git", "add", *self.paths]