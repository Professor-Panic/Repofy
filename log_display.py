# log_display.py
from textual.containers import Container
from textual.widgets import TextArea, Input
from textual.reactive import reactive
from git_checker import doCommand

class CommandLogDisplay(Container):
    log_text = reactive("")

    def compose(self):
        yield TextArea("", read_only=True, id="log-output")
        yield Input(placeholder="Run a command (e.g. git status)", id="command-input")

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