from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class GitCommand(ABC):
    """Base class for one Git command."""

    @property
    @abstractmethod
    def command(self) -> list[str]:
        """Return the command and its arguments."""

    def run(self, repository: str | Path = ".") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            self.command,
            cwd=repository,
            check=True,
            text=True,
            capture_output=True,
        )

    def __str__(self) -> str:
        return " ".join(self.command)
