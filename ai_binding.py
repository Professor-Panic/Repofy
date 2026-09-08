import ai
import asyncio


# class RepofyApp(App):
#     BINDINGS = [
#         ("g", "ai_commit", "AI-suggest commit"),
#         # ...your other bindings...
#     ]

async def action_ai_commit(self):

   diff_text= getStagedDiff() #fetch the staged diff
   if not diff_text.strip():
      self.notify("Nothing staged to summarize.", title="AI commit", severity="warning")
      return # nothing staged, nothing to suggest

   log_display = self.query_one(CommandLogDisplay)


   #---------------SHOW STAGED-DIFF-SUMMARY BEFORE COMMIT BOX-------------------------
   #no AI needed, it's instant
   summary_data = ai.summarize_diff(diff_text)
   summary_lines= [f"• {f}: +{d['added']} -{d['removed']}" for f, d in summary_data.items()]
   self.query_one("#diff-summary", Static).update("\n".join(summary_lines))

   log_display.log("AI: generating commit message...", "Running...", "", 0)


   # asyncio.to_thread because suggest_commit_message makes blocking network calls
   # running it directly here would freeze the whole UI while it waits.
   try:
      result = await asyncio.to_thread(ai.suggest_commit_message, diff_text)
   except Exception as e:
      self.notify(f"AI suggestion failed: {e}", title="AI commit", severity="warning")
      return  # both providers failed=> nothing left to prefill


   #--------PREFILL THE INPUT WITH THE COMMIT MESSAGE-------
   commit_input = self.query_one("#commit-message", Input)
   commit_input.value = result["summary"]
   self._last_full_message = result["full"] # stash for when they actually commit


   #---------COMMIT MESSAGE QUALITY CHECK--------------
   is_valid, corrected = ai.check_conventional_format(result["summary"])
   if not is_valid:
      commit_input.value = corrected
      self._last_full_message = corrected + "\n\n" + result["full"].split("\n\n", 1)[-1] #grab just the second piece (the body, without the old summary line) instead of list
      log_display.log("ai suggest", f"Reformatted to: {corrected}", "", 0)


   #-----------LABEL FOR THE PROVIDER <INDICATOR>------------
   provider_label = self.query_one("#ai-provider-label", Label)
   if result["provider"] == "claude":
      provider_label.update("☁ Claude")
   else:
      provider_label.update("⚙ Local (Ollama)")

   log_display.log("AI: generated", result["full"], "", 0)

  

async def _handle_commit(self,message):
   # Called when the user actually hits commit, using whatever's in the
   # input box (either the AI's prefill, or their own edit of it).
   if not message:
      return
   stdout, stderr, returncode = await asyncio.to_thread(doCommit, message)
   self.query_one(CommandLogDisplay).log(f'git commit -m "{message}"',stdout, stderr, returncode)
   await self.query_one(FileDisplay).refresh_display(force=True)