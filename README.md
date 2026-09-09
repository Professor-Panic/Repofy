# Repofy

Repofy is a small Python project that wraps common Git operations into reusable command objects and a higher-level workflow helper. It is designed to help automate the usual local Git publishing flow in a simple, readable way.

## Project structure

- `Brancher.py` contains branch-related command classes such as `BranchCommand` and `SwitchCommand`.
- `Stager.py` contains staging commands, including `StatusCommand` and `AddCommand`.
- `Sprinter.py` contains commit-related logic through `CommitCommand`.
- `Merger.py` contains pull and merge operations such as `PullCommand` and `MergeCommand`.
- `File_picker.py` provides a Textual file-selection modal used for browsing folders and files.
- `Ui.py` composes the full Git workflow into a single `GitWorkflow` object.
- `git-command/` holds the lower-level Git command abstraction layer used by the project.

## How the git-command folder works

The code in `git-command/` is built around a shared abstract base class, `GitCommand`, in `git-command/Git_command.py`.

That base class does three important things:

- defines a required `command` property that every Git action must provide
- runs the command using `subprocess.run(...)` with a chosen repository path as the working directory
- converts the command list into a readable string via `__str__()`

Each command class is just a thin wrapper around a Git CLI command. For example:

- `StatusCommand.command` returns `["git", "status"]`
- `AddCommand.command` returns `["git", "add", *paths]`
- `CommitCommand.command` returns `["git", "commit", "-m", message]`
- `PullCommand.command` returns `["git", "pull", remote, branch]`
- `PushCommand.command` returns `["git", "push", remote, branch]`
- `SwitchCommand.command` returns `["git", "switch", "-c", branch]` when creation is requested

This pattern keeps the project consistent and avoids repeating shell logic in many places.

## Higher-level workflow

The `GitWorkflow` class in `git-command/Ui.py` assembles the command objects into a standard developer workflow:

1. check the status
2. stage files
3. create a commit
4. pull from the remote if configured
5. push to the remote branch

Example:

```python
from Ui import GitWorkflow

workflow = GitWorkflow(
    commit_message="update project",
    branch="main",
    paths=["."],
    remote="origin",
    sync_before_push=True,
)

print(workflow.command_list())
workflow.run(".")
```

This makes it easy to both inspect the exact Git commands that will run and execute them in sequence when the workflow is ready.

## Notes

This repository is intended as a lightweight Git helper project and can be expanded with more automation, validation steps, or richer UI interactions as needed.
