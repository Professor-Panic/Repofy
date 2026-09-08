from Git_command import GitCommand


class CommitCommand(GitCommand):
    def __init__(self, message: str) -> None:
        if not message.strip():
            raise ValueError("A commit message is required")
        self.message = message

    @property
    def command(self) -> list[str]:
        return ["git", "commit", "-m", self.message]