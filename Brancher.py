from Git_command import GitCommand


class BranchCommand(GitCommand):
    def __init__(self, branch: str) -> None:
        self.branch = branch

    @property
    def command(self) -> list[str]:
        return ["git", "branch", self.branch]


class SwitchCommand(GitCommand):
    def __init__(self, branch: str, create: bool = False) -> None:
        self.branch = branch
        self.create = create

    @property
    def command(self) -> list[str]:
        action = "-c" if self.create else ""
        return ["git", "switch", *([action] if action else []), self.branch]