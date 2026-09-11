from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Input, Label, Static
from log_display import CommandLogDisplay  # imported here, not at module scope, to avoid Ui <-> ai_binding circularity
import ai
import asyncio

class AICommitPanel(Container):

    def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)
       self._last_full_message="" # holds the fuller multi-line message


       
    def compose(self) -> ComposeResult:
       yield Static("", id="ai-diff-summary")
       yield Input(placeholder="Commit message...", id="ai-commit-input")
       yield Label("", id="ai-provider-label")
       yield Static("", id="ai-diff-explanation")


    #---------SHARED HELPER: fetch the log widget without a top-level circular import-------
    def _log_display(self):
       return self.app.query_one(CommandLogDisplay)



    #---------SHARED HELPER: runs any AI call the same safe way------
    async def _run_ai_task(self, ai_function, diff_text, task_label, notify_title):
       log_display = self._log_display()
       log_display.log(f"AI: {task_label}...", "Running...", "",0) 



       # asyncio.to_thread because suggest_commit_message and explain_diff makes blocking network calls
#      # running it directly here would freeze the whole UI while it waits.
       try:
         result = await asyncio.to_thread(ai_function, diff_text)
       except Exception as e:
         self.app.notify(f"AI {task_label} failed: {e}", title=notify_title, severity="warning")
         return None # both providers failed=> nothing left to prefill

       self._update_provider_label(result["provider"])
       return result
    

    #---------SHARED HELPER: provider indicator-------
    def _update_provider_label(self, provider: str) -> None:
      if provider == "claude":
         text = "☁ Claude"
      elif provider == "groq":
         text = "☁ Groq"
      else:
         text = "⚙ Local (Ollama)"
      self.query_one("#ai-provider-label", Label).update(text)
    def show_diff_summary(self, diff_text):
       summary_data = ai.summarize_diff(diff_text)
       summary_lines = [f"• {f}: +{d['added']} -{d['removed']}" for f, d in summary_data.items()]
       self.query_one("#ai-diff-summary", Static).update("\n".join(summary_lines))

    async def generate_suggestion(self, diff_text: str) -> None:
       if not diff_text.strip():
          self.app.notify("Nothing staged to summarize.", title="AI commit", severity="warning")
          return

       self.show_diff_summary(diff_text)

       log_display = self._log_display()  # fetch once, reuse below

       result = await self._run_ai_task(ai.suggest_commit_message, diff_text, "generating commit message", "AI commit")
       if result is None:
          return # both providers failed => nothing left to prefill
       

       #---------COMMIT MESSAGE QUALITY CHECK--------------
       is_valid, corrected = ai.check_conventional_format(result["summary"])
       final_summary = corrected if not is_valid else result["summary"]

       # store the full message, correcting the summary line inside it too
       if not is_valid:
          self._last_full_message = corrected + "\n\n" + result["full"].split("\n\n", 1)[-1] #grab just the second piece (the body, without the old summary line) instead of list
          log_display.log("ai suggest", f"Reformatted to: {corrected}", "",0)
       else:
          self._last_full_message = result["full"]


       self.query_one("#ai-commit-input", Input).value = final_summary
       log_display.log("AI: generated", result["full"], "",0)



    #------------------EXPLAIN THIS DIFF--------------------------
    async def generate_explanation(self, diff_text: str) -> None:
       if not diff_text.strip():
          self.app.notify("Nothing staged to explain.", title="AI explain", severity="warning")
          return

       result = await self._run_ai_task(ai.explain_diff, diff_text, "explaining diff", "AI explain")
       if result is None:
          return # both providers failed => nothing to show

       self.query_one("#ai-diff-explanation", Static).update(result["explanation"])
       self._log_display().log("AI: explained", result["explanation"], "", 0)


    #--------GETTER: for the commit button-------
    def get_commit_message(self) -> str:
       return self.query_one("#ai-commit-input", Input).value
   
    def get_full_message(self) -> str:
       return self._last_full_message