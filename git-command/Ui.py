from __future__ import annotations

from pathlib import Path

from Brancher import SwitchCommand
from File_picker import PushCommand
from Git_command import GitCommand
from Merger import PullCommand
from Sprinter import CommitCommand
from Stager import AddCommand, StatusCommand


class GitWorkflow:
    """Arrange and execute the normal local-to-GitHub publishing steps."""

    def __init__(
        self,
        commit_message: str,
        branch: str,
        paths: list[str] | None = None,
        remote: str = "origin",
        sync_before_push: bool = True,
    ) -> None:
        self.commands: list[GitCommand] = [
            StatusCommand(),
            AddCommand(paths),
            CommitCommand(commit_message),
        ]
        if sync_before_push:
            self.commands.extend([PullCommand(remote, branch)])
        self.commands.append(PushCommand(remote, branch))

    def command_list(self) -> list[str]:
        return [str(command) for command in self.commands]

    def run(self, repository: str | Path = ".") -> None:
        for command in self.commands:
            command.run(repository)


__all__ = ["GitWorkflow", "SwitchCommand"]
