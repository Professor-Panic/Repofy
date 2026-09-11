from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, VerticalScroll, Container, ScrollableContainer, Horizontal, Vertical
from textual.reactive import reactive
from rich.text import Text
from textual.widgets import Footer, Header, Button, Digits, Label, TextArea
from textual.widgets import ListView, ListItem, Label, Input
from textual.theme import Theme
from textual.screen import ModalScreen
from textual.message import Message
from textual.binding import Binding
from ai_binding import AICommitPanel
from log_display import CommandLogDisplay
from Sprinter import SprintTodo,SprintTodoError
from git_checker import *
import asyncio
import subprocess
def build_diff_display(diff_text: str) -> Text:
    result = Text()
    for line in diff_text.splitlines(keepends=True):
        if line.startswith("+") and not line.startswith("+++"):
            result.append(line, style="green")
        elif line.startswith("-") and not line.startswith("---"):
            result.append(line, style="red")
        elif line.startswith("@@"):
            result.append(line, style="cyan")
        else:
            result.append(line)
    return result


class CommitModal(ModalScreen):
    BINDINGS = [("escape", "dismiss_modal", "Cancel")]

    def __init__(self, initial: str = ""):
        super().__init__()
        self.initial_value = initial

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Commit message:"),
            Input(placeholder="Type your commit message...", value=self.initial_value, id="modal-commit-input"),
            id="commit-modal-box"
        )

    def on_mount(self):
        field = self.query_one("#modal-commit-input", Input)
        field.focus()
        field.cursor_position = len(field.value)

    def action_dismiss_modal(self):
        self.dismiss(None)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class TodoModal(ModalScreen):
    """Small single-input modal, styled like CommitModal. Reused for adding
    tasks, renaming tasks, and setting deadlines by swapping the label/
    placeholder/initial value."""
    BINDINGS = [("escape", "dismiss_modal", "Cancel")]

    def __init__(self, label: str = "TODO message:", placeholder: str = "Type your New task message...", initial: str = ""):
        super().__init__()
        self.label_text = label
        self.placeholder_text = placeholder
        self.initial_value = initial

    def compose(self) -> ComposeResult:
        yield Container(
            Label(self.label_text),
            Input(placeholder=self.placeholder_text, value=self.initial_value, id="modal-commit-input"),
            id="todo-modal-box"
        )

    def on_mount(self):
        field = self.query_one("#modal-commit-input", Input)
        field.focus()
        field.cursor_position = len(field.value)

    def action_dismiss_modal(self):
        self.dismiss(None)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class CommandPaletteModal(ModalScreen):
    BINDINGS = [
        ("space", "select_stage", "Stage all changes"),
        ("s", "select_stash", "Stash"),
        ("b", "select_switch", "Switch branch"),
        ("m", "select_merge", "Merge branch"),
        ("c", "create_branch", "Create branch"),
        ("d", "delete_branch", "Delete branch"),
        ("l", "select_pull", "Pull"),
        ("p", "select_push", "Push"),
        ("t", "select_task_board", "Sprint board"),
        ("f", "select_file_picker", "Directory Picker"),
        ("g", "select_ai_commit", "AI commit"),
        ("e", "select_ai_explain", "AI explain"),
        ("n", "select_theme_maker", "New theme"),
        ("w", "select_theme_switch", "Switch theme"),
        ("escape", "dismiss_modal", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Choose a command:"),
            ListView(
                ListItem(Label("space  Stage all changes"), name="stage"),
                ListItem(Label("s  Stash all changes"), name="stash"),
                ListItem(Label("b  Switch branch"), name="switch"),
                ListItem(Label("m  Merge branch"), name="merge"),
                ListItem(Label("c  Create branch"), name="create"),
                ListItem(Label("d  Delete branch"), name="delete"),
                ListItem(Label("l  Pull"), name="pull"),
                ListItem(Label("p  Push"), name="push"),
                ListItem(Label("t  Sprint board"), name="taskboard"),
                ListItem(Label("f  Change Directory"), name="dir_picker"),
                ListItem(Label("g  AI commit suggestion"), name="ai_commit"),
                ListItem(Label("e  AI explain diff"), name="ai_explain"),
                ListItem(Label("n  Create new theme"), name="theme_maker"),
                ListItem(Label("w  Switch theme"), name="theme_select"),
            ),
            id="palette-box"
        )
        yield Footer()

    def action_dismiss_modal(self):
        self.dismiss(None)

    def action_select_stage(self):
        self.dismiss(("stage", None))

    def action_select_stash(self):
        self.dismiss(("stash", None))

    def action_select_task_board(self):
        self.dismiss(("taskboard", None))

    def action_select_switch(self):
        self.dismiss(("need_branch", "switch"))

    def action_select_file_picker(self):
        self.dismiss(("dir_picker", None))

    def action_select_merge(self):
        self.dismiss(("need_branch", "merge"))

    def action_create_branch(self):
        self.dismiss(("need_branch", "create"))

    def action_delete_branch(self):
        self.dismiss(("need_branch", "delete"))

    def action_select_pull(self):
        self.dismiss(("pull", None))

    def action_select_push(self):
        self.dismiss(("push", None))

    def action_select_ai_commit(self):
        self.dismiss(("ai_commit", None))

    def action_select_ai_explain(self):
        self.dismiss(("ai_explain", None))

    def action_select_theme_maker(self):
        self.dismiss(("theme_maker", None))

    def action_select_theme_switch(self):
        self.dismiss(("theme_select", None))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        action = event.item.name
        if action in ("switch", "merge", "create", "delete"):
            self.dismiss(("need_branch", action))
        else:
            self.dismiss((action, None))


class BranchInputModal(ModalScreen):
    BINDINGS = [("escape", "dismiss_modal", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Branch name:"),
            Input(placeholder="branch name...", id="branch-name-input"),
            id="branch-input-box"
        )

    def on_mount(self):
        self.query_one("#branch-name-input", Input).focus()

    def action_dismiss_modal(self):
        self.dismiss(None)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class BranchSelectModal(ModalScreen):
    BINDINGS = [("escape", "dismiss_modal", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Select the main branch for the sprint TODO:"),
            ListView(id="branch-select-list"),
            id="branch-select-box",
        )

    async def on_mount(self) -> None:
        list_view = self.query_one("#branch-select-list", ListView)
        await list_view.clear()
        try:
            result = subprocess.run(
                ["git", "branch", "-r", "--format=%(refname:short)"],
                capture_output=True, text=True, check=True
            )
            branches = [b.strip() for b in result.stdout.splitlines() if b.strip()]
        except subprocess.CalledProcessError:
            branches = []
        for branch in branches:
            if branch.startswith("origin/"):
                name = branch[len("origin/"):]
            else:
                name = branch
            await list_view.append(ListItem(Label(name, markup=False), name=name))
        list_view.focus()

    def action_dismiss_modal(self):
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.name)


class TaskItem(ListItem):
    class DeleteRequested(Message):
        def __init__(self, task_num: int) -> None:
            self.task_num = task_num
            super().__init__()

    def __init__(self, task: dict):
        self.task_num = task["num"]
        text = f"#{task['num']} {task['description']}"
        if task.get("deadline"):
            text += f" {task['deadline']}"
        super().__init__(Label(text, markup=False), name=str(task["num"]))

    def on_click(self, event) -> None:
        if getattr(event, "button", 1) == 3:
            event.stop()
            self.post_message(self.DeleteRequested(self.task_num))

class SprintBoardModal(ModalScreen):
    BINDINGS = [
        ("escape", "dismiss_modal", "Close"),
        ("a", "add_task", "Add task"),
        ("d", "delete_task", "Delete task"),
        ("r", "rename_task", "Rename task"),
        ("e", "set_deadline", "Set deadline"),
        ("h", "move_left", "Move ←"),
        ("l", "move_right", "Move →"),
        ("ctrl+r", "refresh_board", "Refresh"),
        ("i", "add_index", "Add index"),
        ("n", "rename_index", "Rename index"),
        ("x", "delete_index", "Delete index"),
        ("s", "toggle_help", "Show/hide help"),
        ("ctrl+s", "save_changes", "Push changes now"),
    ]

    def __init__(self, todo: "SprintTodo"):
        super().__init__()
        self.todo = todo

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Sprint board", id="sprint-title"),
            Horizontal(id="board-columns"),
            VerticalScroll(
                Label(
                    "Key Bindings:\n"
                    "  a         Add task\n"
                    "  d         Delete task\n"
                    "  r         Rename task\n"
                    "  e         Set deadline\n"
                    "  h / l     Move task left/right\n"
                    "  i         Add index\n"
                    "  n         Rename index\n"
                    "  x         Delete index\n"
                    "  ctrl+r    Refresh from remote\n"
                    "  ctrl+s    Push changes now\n"
                    "  s         Toggle this help\n"
                    "  escape    Close (and push)\n",
                    id="help-text",
                ),
                id="help-popup",
                classes="hidden",
            ),
            Horizontal(
                Button("+ Add Task", id="add-task-btn", variant="primary"),
                Button("Close", id="close-btn"),
                id="sprint-actions",
            ),
            id="sprint-board-box",
        )

    async def on_mount(self) -> None:
        try:
            await asyncio.to_thread(self.todo.pull)
        except SprintTodoError as e:
            self.notify(str(e), title="Sprint board", severity="error")
        await self.refresh_board(focus_first=True)
        self.query_one("#help-popup").display = False

    async def refresh_board(self, focus_first: bool = False) -> None:
        columns = self.query_one("#board-columns", Horizontal)

        focused_flag = self._current_flag()
        focused_task = self._current_task_num()

        await columns.remove_children()

        if not self.todo.indices:
            await columns.mount(Label("No indices found in this sprint TODO yet."))
            return

        for num in sorted(self.todo.indices):
            name = self.todo.indices[num]
            tasks = sorted(
                (t for t in self.todo.tasks if t["flag"] == num),
                key=lambda t: t["num"],
            )
            col = Vertical(id=f"col-{num}", classes="sprint-column")
            await columns.mount(col)
            await col.mount(Label(f"{name} ({len(tasks)})", classes="column-header"))
            list_view = ListView(id=f"list-{num}")
            await col.mount(list_view)
            for t in tasks:
                await list_view.append(TaskItem(t))
        target_flag = focused_flag if focused_flag in self.todo.indices else (
            min(self.todo.indices) if focus_first else None
        )

        if target_flag is not None:
            list_view = self.query_one(f"#list-{target_flag}", ListView)
            list_view.focus()
            if focused_task is not None:
                for i, item in enumerate(list_view.children):
                    if item.name == str(focused_task):
                        list_view.index = i
                        break

    def _current_list_view(self):
        focused = self.app.focused
        return focused if isinstance(focused, ListView) else None

    def _current_flag(self):
        lv = self._current_list_view()
        if lv is None or not lv.id:
            return None
        try:
            return int(lv.id.split("-", 1)[1])
        except (IndexError, ValueError):
            return None

    def _current_task_num(self):
        lv = self._current_list_view()
        if lv is None or lv.highlighted_child is None:
            return None
        return int(lv.highlighted_child.name)

    async def action_toggle_help(self) -> None:
        help_popup = self.query_one("#help-popup")
        help_popup.display = not help_popup.display

    async def action_save_changes(self) -> None:
        await self._push_changes()

    async def _push_changes(self) -> None:
        if self.todo.has_pending_changes:
            try:
                await asyncio.to_thread(self.todo.push, "Update sprint Tasks")
                self.notify("Changes pushed", title="Sprint board", severity="information")
            except SprintTodoError as e:
                self.notify(str(e), title="Push failed", severity="error")

    async def action_dismiss_modal(self) -> None:
        if self.app.screen is self:
            self.dismiss(None)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-task-btn":
            await self.action_add_task()
        elif event.button.id == "close-btn":
            await self._push_changes()
            if self.app.screen is self:
                self.dismiss(None)

    async def action_add_task(self):
        if not self.todo.indices:
            self.notify(
                "No indices defined. Add an index first (e.g. via CLI).",
                title="Sprint board",
                severity="warning",
            )
            return
        flag = self._current_flag() or min(self.todo.indices)

        async def handle(description):
            if not description:
                return
            try:
                await asyncio.to_thread(self.todo.add_task, description, flag)
            except SprintTodoError as e:
                self.notify(str(e), title="Add task", severity="error")
            await self.refresh_board()

        self.app.push_screen(
            TodoModal(label="New task:", placeholder="Task description..."), handle
        )

    async def action_delete_task(self):
        num = self._current_task_num()
        if num is None:
            return
        await self._delete_task(num)

    async def _delete_task(self, num: int):
        try:
            await asyncio.to_thread(self.todo.delete_task, num)
        except SprintTodoError as e:
            self.notify(str(e), title="Delete task", severity="error")
        await self.refresh_board()

    def on_task_item_delete_requested(self, message: "TaskItem.DeleteRequested") -> None:
        self.run_worker(self._delete_task(message.task_num))

    async def action_rename_task(self):
        num = self._current_task_num()
        if num is None:
            return
        task = next((t for t in self.todo.tasks if t["num"] == num), None)

        async def handle(description):
            if not description:
                return
            try:
                await asyncio.to_thread(self.todo.rename_task, num, description)
            except SprintTodoError as e:
                self.notify(str(e), title="Rename task", severity="error")
            await self.refresh_board()

        self.app.push_screen(
            TodoModal(
                label="New description:",
                placeholder="Edit task description...",
                initial=task["description"] if task else "",
            ),
            handle,
        )

    async def action_set_deadline(self):
        num = self._current_task_num()
        if num is None:
            return
        task = next((t for t in self.todo.tasks if t["num"] == num), None)

        async def handle(value):
            if value is None:
                return
            try:
                await asyncio.to_thread(self.todo.set_deadline, num, value or None)
            except SprintTodoError as e:
                self.notify(str(e), title="Set deadline", severity="error")
            await self.refresh_board()

        self.app.push_screen(
            TodoModal(
                label="Deadline (YYYY-MM-DD, blank to clear):",
                placeholder="2026-09-15",
                initial=(task["deadline"] or "") if task else "",
            ),
            handle,
        )

    async def action_move_left(self):
        await self._move_task(-1)

    async def action_move_right(self):
        await self._move_task(1)

    async def _move_task(self, direction: int):
        num = self._current_task_num()
        flag = self._current_flag()
        if num is None or flag is None:
            return
        indices = sorted(self.todo.indices)
        pos = indices.index(flag)
        new_pos = pos + direction
        if not (0 <= new_pos < len(indices)):
            return
        new_flag = indices[new_pos]
        try:
            await asyncio.to_thread(self.todo.set_flag, num, new_flag)
        except SprintTodoError as e:
            self.notify(str(e), title="Move task", severity="error")
            await self.refresh_board()
            return
        await self.refresh_board()
        try:
            new_list = self.query_one(f"#list-{new_flag}", ListView)
        except Exception:
            return
        new_list.focus()
        for i, item in enumerate(new_list.children):
            if item.name == str(num):
                new_list.index = i
                break

    async def action_add_index(self):
        async def handle(name):
            if not name:
                return
            try:
                await asyncio.to_thread(self.todo.add_index, name)
            except SprintTodoError as e:
                self.notify(str(e), title="Add index", severity="error")
            await self.refresh_board()

        self.app.push_screen(
            TodoModal(label="New index name:", placeholder="e.g. Backlog"), handle
        )

    async def action_rename_index(self):
        flag = self._current_flag()
        if flag is None:
            self.notify("Focus a column first.", title="Rename index", severity="warning")
            return
        current_name = self.todo.indices.get(flag, "")

        async def handle(new_name):
            if not new_name:
                return
            try:
                await asyncio.to_thread(self.todo.rename_index, flag, new_name)
            except SprintTodoError as e:
                self.notify(str(e), title="Rename index", severity="error")
            await self.refresh_board()

        self.app.push_screen(
            TodoModal(
                label=f"Rename index '{current_name}' to:",
                placeholder="New index name...",
                initial=current_name,
            ),
            handle,
        )

    async def action_delete_index(self):
        flag = self._current_flag()
        if flag is None:
            self.notify("Focus a column first.", title="Delete index", severity="warning")
            return
        tasks_using = [t for t in self.todo.tasks if t["flag"] == flag]
        if tasks_using:
            self.notify(
                f"Index {flag} has {len(tasks_using)} task(s). Reassign them first via CLI.",
                title="Delete index",
                severity="error",
            )
            return

        try:
            await asyncio.to_thread(self.todo.delete_index, flag)
        except SprintTodoError as e:
            self.notify(str(e), title="Delete index", severity="error")
        await self.refresh_board()


class StatusDisplay(Container):
    is_git = reactive(False)
    current_branch = reactive("")
    latest_commit = reactive("")

    def on_mount(self) -> None:
        self.check_status()
        self.set_interval(5, self.check_status)

    def check_status(self) -> None:
        self.is_git = is_git_repo()
        if self.is_git:
            self.current_branch = getCurrentBranch()
            commits = getCommitsList()
            if commits:
                self.latest_commit = commits[0]["line"]
            else:
                self.latest_commit = ""
        else:
            self.current_branch = ""
            self.latest_commit = ""

    def watch_is_git(self, is_git: bool) -> None:
        self.refresh_display()
    def refresh_display(self):
        self.remove_children()
        text=""
        if self.is_git:
            text = "Git repo detected"
            self.mount(Label(f"[green]{text}[/green]"))
        else:
            text="Not a git repo"
            self.mount(Label(f"[red]{text}[/red]"))
class CommitDisplay(Container):
    def compose(self):
        yield ListView(id="Commit-list")

    def on_mount(self) -> None:
        self._last_commits = None
        self.call_later(self.refresh_display)
        self.set_interval(5, self.refresh_display)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is None:
            return
        diff_text = getCommitDiff(event.item.name)
        self.app.query_one(DiffDisplay).diff_text = diff_text

    async def refresh_display(self):
        commits = getCommitsList()
        if commits == self._last_commits:
            return
        self._last_commits = commits
        list_view = self.query_one("#Commit-list", ListView)
        await list_view.clear()
        for c in commits:
            await list_view.append(
                ListItem(Label(c["line"], markup=False), name=c["hash"])
            )


class BranchDisplay(Container):
    BINDINGS = [("b", "branch", "Checkout to branch")]
    selected_branch = None

    def compose(self):
        yield ListView(id="Branch-list")

    def on_mount(self) -> None:
        self._last_branches = None
        self.call_later(self.refresh_display)
        self.set_interval(5, self.refresh_display)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.selected_branch = event.item.name.strip("*")[2:]

    async def action_branch(self):
        if self.selected_branch is None:
            return
        log_display = self.app.query_one(CommandLogDisplay)
        log_display.log(f"git checkout {self.selected_branch}", "Running...", "", 0)
        stdout, stderr, returncode = await asyncio.to_thread(switchBranch, self.selected_branch)
        log_display.log(f"git checkout {self.selected_branch} (done)", stdout, stderr, returncode)
        await self.app.query_one(FileDisplay).refresh_display(force=True)
        await self.refresh_display()

    async def refresh_display(self):
        branches = GetBranchesList()
        list_view = self.query_one("#Branch-list")
        if branches == self._last_branches:
            return
        self._last_branches = branches
        await list_view.clear()
        for f in branches:
            await list_view.append(
                ListItem(Label(f, markup=False), name=f)
            )


class StashDisplay(Container):
    def compose(self):
        return []

    def on_mount(self) -> None:
        self._last_stashes = None
        self.call_later(self.refresh_display)
        self.set_interval(5, self.refresh_display)

    async def refresh_display(self):
        stashes = getStashes()
        if stashes == self._last_stashes:
            return
        self._last_stashes = stashes
        await self.remove_children()
        self.mount(Label(stashes or "No stashes", markup=False))


class DiffDisplay(ScrollableContainer):
    diff_text = reactive("")

    def watch_diff_text(self, diff_text: str) -> None:
        self.remove_children()
        if diff_text:
            self.mount(Label(build_diff_display(diff_text)))
        else:
            self.mount(Label("No change detected"))
        self.scroll_home(animate=False)


class ConflictDisplay(Container):
    BINDINGS = [
        ("ctrl+a", "abort", "Abort merge"),
        ("ctrl+g", "continue_merge", "Continue merge"),
    ]

    def compose(self):
        return []

    def on_mount(self) -> None:
        self.call_later(self.refresh_display)
        self.set_interval(3, self.refresh_display)

    async def refresh_display(self):
        await self.remove_children()
        if not isMergeInProgress():
            self.mount(Label("No merge in progress"))
            self.display = False
            return

        self.display = True
        conflicts = getConflicts()
        if conflicts:
            text = "MERGE CONFLICT in:\n" + "\n".join(f"  {f}" for f in conflicts)
            text += "\n\nResolve files, then ctrl+g to continue, ctrl+a to abort."
        else:
            text = "All conflicts resolved.\nPress ctrl+g to complete the merge."
        self.mount(Label(text))

    async def action_abort(self):
        stdout, stderr, returncode = abortMerge()
        self.app.query_one(CommandLogDisplay).log("git merge --abort", stdout, stderr, returncode)
        await self.refresh_display()
        await self.app.query_one(FileDisplay).refresh_display(force=True)

    async def action_continue_merge(self):
        stdout, stderr, returncode = continueMerge()
        self.app.query_one(CommandLogDisplay).log("git commit --no-edit", stdout, stderr, returncode)
        await self.refresh_display()
        await self.app.query_one(FileDisplay).refresh_display(force=True)


class FileDisplay(Container):
    BINDINGS = [("space", "toggle_stage", "Stage/Unstage"), ("s", "toggle_stash", "Stash file")]

    def compose(self):
        yield ListView(id="Files-list")

    def on_mount(self) -> None:
        self._last_files = None
        self.call_later(self.refresh_display, force=True, focus=True)
        self.set_interval(5, self.refresh_display)

    async def refresh_display(self, force: bool = False, focus: bool = False):
        list_view = self.query_one("#Files-list")
        has_focus = list_view.has_focus
        if not force and not has_focus:
            return

        files = GetFilesList()
        if not force and files == self._last_files:
            return
        self._last_files = files
        selected_name = None
        if list_view.highlighted_child is not None:
            selected_name = list_view.highlighted_child.name

        await list_view.clear()
        for f in files:
            await list_view.append(
                ListItem(Label(f"{f['staged']}{f['unstaged']} {f['filename']}", markup=False), name=f["filename"])
            )

        if focus or has_focus:
            list_view.focus()

        if selected_name is not None:
            for index, item in enumerate(list_view.children):
                if item.name == selected_name:
                    list_view.index = index
                    break

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        filename = event.item.name
        diff_text = getDiff(filename)
        self.app.query_one(DiffDisplay).diff_text = diff_text

    async def action_toggle_stage(self):
        list_view = self.query_one(ListView)
        highlighted = list_view.highlighted_child
        if highlighted is None:
            return
        filename = highlighted.name

        files = GetFilesList()
        current = next((f for f in files if f["filename"] == filename), None)
        if current is None:
            return

        if current["staged"] != " " and current["staged"] != "?":
            unstageFile(filename)
        else:
            stageFile(filename)

        await self.refresh_display(force=True)

    async def action_toggle_stash(self):
        list_view = self.query_one(ListView)
        highlighted = list_view.highlighted_child
        if highlighted is None:
            return
        filename = highlighted.name
        log_display = self.app.query_one(CommandLogDisplay)
        log_display.log(f"git stash  --{filename}", "Running...", "", 0)
        stdout, stderr, returncode = await asyncio.to_thread(doStashFile, filename=filename)
        log_display.log(f"git stash  --{filename} (done)", stdout, stderr, returncode)
        await self.app.query_one(FileDisplay).refresh_display(force=True)


class StashDisplay(Container):
    def compose(self):
        return []

    def on_mount(self) -> None:
        self.call_later(self.refresh_display)
        self.set_interval(5, self.refresh_display)

    async def refresh_display(self):
        await self.remove_children()
        stashes = getStashes()
        self.mount(Label(stashes or "No stashes"))


class CommandLogDisplay(Container):
    log_text = reactive("")

    def compose(self):
        yield TextArea("", read_only=True, id="log-output")
        yield Input(placeholder="Run a command (e.g. git status)", id="command-input")

    def on_mount(self):
        pass

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "command-input":
            return
        command = event.input.value
        if not command:
            return
        stdout, stderr, returncode = doCommand(command)
        event.input.value = ""
        self.log(command, stdout, stderr, returncode)

    def log(self, command_label: str, stdout: str, stderr: str, returncode: int) -> None:
        output = stdout if returncode == 0 else f"[FAILED] {stderr}"
        if returncode != 0:
            self.notify(stderr, title=command_label, severity="error")
        self.log_text += f"$ {command_label}\n{output}\n"
        self._update_log()

    def _update_log(self):
        log_area = self.query_one("#log-output", TextArea)
        log_area.load_text(self.log_text)
        log_area.scroll_end(animate=False)


class AIControlModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close", priority=True),
        Binding("c", "commit_suggestion", "Commit with AI message", priority=True),
    ]

    def __init__(self, action: str | None = None):
        super().__init__()
        self.action = action  # 'commit', 'explain', or None

    def compose(self) -> ComposeResult:
        yield Container(
            AICommitPanel(id="ai-panel-modal"),
            Horizontal(
                Button("Close", id="close-ai-modal"),
                Button("Commit", id="commit-ai-message", variant="primary"),
                id="ai-modal-buttons",
            ),
            id="ai-modal-container"
        )

    def on_mount(self) -> None:
        if self.action == "commit":
            self.run_worker(self._run_commit())
        elif self.action == "explain":
            self.run_worker(self._run_explain())

    async def _run_commit(self):
        diff_text = getStagedDiff()
        panel = self.query_one(AICommitPanel)
        await panel.generate_suggestion(diff_text)

    async def _run_explain(self):
        diff_text = getStagedDiff()
        panel = self.query_one(AICommitPanel)
        await panel.generate_explanation(diff_text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-ai-modal":
            self.dismiss(None)
        elif event.button.id == "commit-ai-message":
            self.action_commit_suggestion()

    def action_commit_suggestion(self):
        """Dismiss the modal and return the AI-generated commit message (if any)."""
        panel = self.query_one(AICommitPanel)
        message = panel.get_full_message() or panel.get_commit_message()
        if not message.strip():
            self.app.notify("No AI commit message generated yet.", title="AI commit", severity="warning")
            return
        self.dismiss(message)

    def action_dismiss_modal(self):
        self.dismiss(None)


class ThemeMakerModal(ModalScreen):
    """Lets the user define a custom Theme as plain text, one `key=value`
    per line (name, primary, background, ...), instead of a form full of
    inputs. Because it's just text in a TextArea, the whole definition can
    be selected and copied out to save/share elsewhere, or a definition
    written elsewhere can be pasted straight in. Dismisses with a dict
    suitable for Theme(**data), or None if cancelled."""

    BINDINGS = [("escape", "dismiss_modal", "Cancel")]

    DEFAULT_TEXT = """\
name=arctic
primary=#88C0D0
secondary=#81A1C1
accent=#B48EAD
foreground=#D8DEE9
background=#2E3440
success=#A3BE8C
warning=#EBCB8B
error=#BF616A
surface=#3B4252
panel=#434C5E
dark=true

# Optional extra styling variables, one per line:
# variable.footer-key-foreground=#88C0D0
"""

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Create a new theme", id="theme-maker-title"),
            Label(
                "key=value, one per line. Select all + copy to reuse this "
                "elsewhere, or paste a definition in.",
                id="theme-maker-hint",
            ),
            TextArea(self.DEFAULT_TEXT, id="theme-text"),
            Horizontal(
                Button("Cancel", id="cancel-theme"),
                Button("Create", id="create-theme", variant="primary"),
                id="theme-maker-buttons",
            ),
            id="theme-maker-box",
        )

    def on_mount(self) -> None:
        self.query_one("#theme-text", TextArea).focus()

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-theme":
            self.dismiss(None)
        elif event.button.id == "create-theme":
            self._submit()

    def _submit(self) -> None:
        text = self.query_one("#theme-text", TextArea).text
        try:
            theme_data = self._parse(text)
        except ValueError as err:
            self.app.notify(str(err), title="Theme maker", severity="warning")
            return

        if not theme_data.get("name"):
            self.app.notify("Give the theme a name first (name=...).", title="Theme maker", severity="warning")
            return

        self.dismiss(theme_data)

    @staticmethod
    def _parse(text: str) -> dict:
        """Parse `key=value` lines into a dict suitable for Theme(**data).

        - Blank lines and lines starting with '#' are ignored.
        - `dark=true`/`false` (case-insensitive; also 1/0, yes/no, on/off)
          becomes a real bool.
        - `variable.<name>=<value>` lines are collected into a nested
          "variables" dict, matching Theme's own `variables` field.
        - Anything else is kept as a plain string field (name, primary,
          background, foreground, etc.), so unknown/extra keys just get
          passed through to Theme(**data).
        """
        theme_data: dict = {}
        variables: dict = {}

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"Couldn't parse line (expected key=value): {raw_line!r}")

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if not key:
                continue

            if key.lower() == "dark":
                theme_data["dark"] = value.lower() in ("1", "true", "yes", "on")
            elif key.startswith("variable."):
                var_name = key[len("variable."):].strip()
                if var_name:
                    variables[var_name] = value
            else:
                theme_data[key] = value

        if variables:
            theme_data["variables"] = variables

        return theme_data


class ThemeSelectModal(ModalScreen):
    """Lists every registered theme (built-in + custom) so the user can pick
    one to switch to. Dismisses with the chosen theme name, or None."""

    BINDINGS = [("escape", "dismiss_modal", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Select a theme:"),
            ListView(id="theme-select-list"),
            id="theme-select-box",
        )

    async def on_mount(self) -> None:
        list_view = self.query_one("#theme-select-list", ListView)
        await list_view.clear()
        current = self.app.theme
        for name in sorted(self.app.available_themes.keys()):
            marker = "*" if name == current else " "
            await list_view.append(
                ListItem(Label(f"{marker} {name}", markup=False), name=name)
            )
        list_view.focus()

    def action_dismiss_modal(self):
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.name)