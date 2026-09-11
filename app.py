from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header
from textual.binding import Binding
from textual.theme import Theme
from git_checker import *
from Sprinter import SprintTodo,SprintTodoError
from widgets import (
    StatusDisplay, FileDisplay, BranchDisplay, CommitDisplay,
    StashDisplay, DiffDisplay, ConflictDisplay, CommandLogDisplay,
    CommitModal, AIControlModal, SprintBoardModal, BranchSelectModal,
    CommandPaletteModal,BranchInputModal, ThemeMakerModal, ThemeSelectModal
)
from File_picker import FilePickerModal
from themes import *
import asyncio
import os
class Repofy(App):
    CSS_PATH = "git_tui.tcss"
    BINDINGS = [
        ("c", "commit", "Commit"),
        ("p", "push", "Push"),
        ("l", "pull", "Pull"),
        ("ctrl+s", "stage_all", "Stage all"),
        ("t", "open_sprint_board", "Sprint board"),
        ("g", "ai_commit", "AI-suggest commit"),
        ("e", "ai_explain", "AI-explain diff"),
        (":", "open_palette", "Commands"),
        ("ctrl+x", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.todo = SprintTodo()
        # Register every custom theme that's been created before, so they're
        # all selectable (not just the one that was active last time).
        for theme_data in LoadCustomThemes().values():
            self.register_theme(Theme(**theme_data))
        self.theme = LoadTheme()["name"]
    def compose(self):
        yield Header(show_clock=True)
        yield Footer()
        yield Container(
            StatusDisplay(id="status"),
            FileDisplay(id="files"),
            BranchDisplay(id="branches"),
            CommitDisplay(id="commits"),
            StashDisplay(id="stash"),
            id="left-column")
        yield Container(
            DiffDisplay(id="diff"),
            ConflictDisplay(id="conflicts"),
            CommandLogDisplay(id="command-log"),
            id="right-column")
    async def action_commit(self):
        async def handle_result(message: str | None) -> None:
            if not message:
                return
            log_display = self.query_one(CommandLogDisplay)
            log_display.log(f'git commit -m "{message}"', "Running...", "", 0)
            stdout, stderr, returncode = await asyncio.to_thread(doCommit, message)
            log_display.log(f'git commit -m "{message}" (done)', stdout, stderr, returncode)
            await self.query_one(FileDisplay).refresh_display(force=True)

        # We no longer prefill from AICommitPanel; user can still type manually.
        #this was previously   self.push_screen(CommitModal()) didn't work
        self.push_screen(CommitModal(), handle_result)

    async def action_ai_commit(self):
        async def handle_result(message: str | None) -> None:
            if not message:
                return
            log_display = self.query_one(CommandLogDisplay)
            log_display.log(f'git commit -m "{message}"', "Running...", "", 0)
            stdout, stderr, returncode = await asyncio.to_thread(doCommit, message)
            log_display.log(f'git commit -m "{message}" (done)', stdout, stderr, returncode)
            await self.query_one(FileDisplay).refresh_display(force=True)

        self.push_screen(AIControlModal(action="commit"), handle_result)

    async def action_ai_explain(self):
        self.push_screen(AIControlModal(action="explain"))

    async def action_push(self):
        log_display = self.query_one(CommandLogDisplay)
        log_display.log(f'git push', "Running...", "", 0)
        stdout, stderr, returncode = await asyncio.to_thread(doPush)
        log_display.log(f'git push" (done)', stdout, stderr, returncode)
        await self.query_one(FileDisplay).refresh_display(force=True)

    async def action_pull(self):
        log_display = self.query_one(CommandLogDisplay)
        log_display.log(f'git pull', "Running...", "", 0)
        stdout, stderr, returncode = await asyncio.to_thread(doPull)
        log_display.log(f'git pull" (done)', stdout, stderr, returncode)
        await self.query_one(FileDisplay).refresh_display(force=True)

    async def action_stage_all(self):
        log_display = self.query_one(CommandLogDisplay)
        log_display.log(f'git add .', "Running...", "", 0)
        stdout, stderr, returncode = await asyncio.to_thread(stageAll)
        log_display.log(f'git add ." (done)', stdout, stderr, returncode)
        await self.query_one(FileDisplay).refresh_display(force=True)

    async def action_open_sprint_board(self):
        if self.todo.main_branch is None:
            async def handle_branch(branch: str | None) -> None:
                if branch:
                    self.todo.set_main_branch(branch)
                    self.push_screen(SprintBoardModal(self.todo))
            self.push_screen(BranchSelectModal(), handle_branch)
        else:
            self.push_screen(SprintBoardModal(self.todo))

    async def action_open_palette(self):
        async def handle_choice(result) -> None:
            if result is None:
                return
            action, extra = result
            log_display = self.query_one(CommandLogDisplay)

            if action == "need_branch":
                operation = extra

                async def handle_branch(branch_name: str | None) -> None:
                    if not branch_name:
                        return
                    if operation == "switch":
                        log_display.log(f"git checkout {branch_name}", "Running...", "", 0)
                        stdout, stderr, returncode = await asyncio.to_thread(switchBranch, branch_name)
                        log_display.log(f"git checkout {branch_name} (done)", stdout, stderr, returncode)
                    elif operation == "merge":
                        log_display.log(f"git merge {branch_name}", "Running...", "", 0)
                        stdout, stderr, returncode = await asyncio.to_thread(doMerge, branch_name)
                        log_display.log(f"git merge {branch_name} (done)", stdout, stderr, returncode)
                    elif operation == "create":
                        log_display.log(f"git checkout -b {branch_name}", "Running...", "", 0)
                        stdout, stderr, returncode = await asyncio.to_thread(createBranch, branch_name)
                        log_display.log(f"git checkout -b {branch_name} (done)", stdout, stderr, returncode)
                    elif operation == "delete":
                        log_display.log(f"git branch -d {branch_name}", "Running...", "", 0)
                        stdout, stderr, returncode = await asyncio.to_thread(deleteBranch, branch_name)
                        log_display.log(f"git branch -d {branch_name} (done)", stdout, stderr, returncode)
                    await self.query_one(FileDisplay).refresh_display(force=True)
                    await self.query_one(ConflictDisplay).refresh_display()

                self.push_screen(BranchInputModal(), handle_branch)

            elif action == "stash":
                log_display.log("git stash", "Running...", "", 0)
                stdout, stderr, returncode = await asyncio.to_thread(doStash)
                log_display.log("git stash (done)", stdout, stderr, returncode)
                await self.query_one(FileDisplay).refresh_display(force=True)

            elif action == "stage":
                log_display.log("git add .", "Running...", "", 0)
                stdout, stderr, returncode = await asyncio.to_thread(stageAll)
                log_display.log("git add . (done)", stdout, stderr, returncode)
                await self.query_one(FileDisplay).refresh_display(force=True)

            elif action == "pull":
                log_display.log("git pull", "Running...", "", 0)
                stdout, stderr, returncode = await asyncio.to_thread(doPull)
                log_display.log("git pull (done)", stdout, stderr, returncode)
                await self.query_one(FileDisplay).refresh_display(force=True)

            elif action == "push":
                log_display.log("git push", "Running...", "", 0)
                stdout, stderr, returncode = await asyncio.to_thread(doPush)
                log_display.log("git push (done)", stdout, stderr, returncode)

            elif action == "taskboard":
                self.push_screen(SprintBoardModal(self.todo))

            elif action == "dir_picker":
                async def handle_dir_picker(path):
                    if path is not None:
                        if path.is_dir():
                            os.chdir(path)
                        await self.query_one(FileDisplay).refresh_display(force=True)
                        self.query_one(StatusDisplay).check_status()
                        await self.query_one(BranchDisplay).refresh_display()
                        await self.query_one(CommitDisplay).refresh_display()
                        await self.query_one(ConflictDisplay).refresh_display()
                        self.notify(f"Changed directory to {path}", title="Directory changed")
                self.push_screen(FilePickerModal(), handle_dir_picker)

            elif action == "ai_commit":
                self.push_screen(AIControlModal(action="commit"))

            elif action == "ai_explain":
                self.push_screen(AIControlModal(action="explain"))

            elif action == "theme_maker":
                async def handle_new_theme(theme_data: dict | None) -> None:
                    if theme_data is None:
                        return
                    theme = Theme(**theme_data)
                    self.register_theme(theme)
                    self.theme = theme.name
                    SaveTheme(theme_data)
                    self.notify(f"Theme '{theme.name}' created and applied.", title="Theme maker")

                self.push_screen(ThemeMakerModal(), handle_new_theme)

            elif action == "theme_select":
                async def handle_theme_choice(name: str | None) -> None:
                    if name is None:
                        return
                    self.theme = name
                    SetCurrentTheme(name)

                self.push_screen(ThemeSelectModal(), handle_theme_choice)

        self.push_screen(CommandPaletteModal(), handle_choice)


if __name__ == "__main__":
    app = Repofy()
    app.run()