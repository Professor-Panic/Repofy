import ai
("g", "ai_commit", "AI-suggest commit"),

async def action_ai_commit(self):
   diff_text= getStagedDiff() #fetch the staged diff
   if not diff_text.strip():
      self.notify("Nothing staged to summarize.", title="AI commit", severity="warning")
      return # nothing staged, nothing to suggest

   log_display = self.query_one(CommandLogDisplay)
   log_display.log("AI: generating commit message...", "Running...", "", 0)

   # asyncio.to_thread because suggest_commit_message makes blocking network
   # calls — running it directly here would freeze the whole UI while it waits.
   result = await asyncio.to_thread(suggest_commit_message, diff_text)

   #--------PREFILL THE INPUT WITH THE COMMIT MESSAGE-------
   commit_input = self.query_one("#commit-message", Input)
   commit_input.value = result["summary"]
   self._last_full_message = result["full"] # stash for when they actually commit

   #---------COMMIT MESSAGE QUALITY CHECK--------------
   is_valid, corrected = check_conventional_format(result["summary"])
   if not is_valid:
      commit_input.value = corrected
      log_display.log("ai suggest", f"Reformatted to: {corrected}", "", 0)

   #-----------LABEL FOR THE PROVIDER <INDICATOR>------------
   provider_label = self.query_one("#ai-provider-label", Label)
   if result["provider"] == "claude":
      provider_label.update("☁ Claude")
   else:
      provider_label.update("⚙ Local (Ollama)")

   try:
      result = await asyncio.to_thread(ai.suggest_commit_message, diff_text)
      log_display.log("AI: generated", result["full"], "", 0)
      self.push_screen(CommitModal(), self._handle_ai_commit_result)
      self._pending_ai_message = result["full"]
   except Exception as e:
      self.notify(f"AI suggestion failed: {e}", title="AI commit", severity="warning")


async def _handle_ai_commit_result(self,message):
   if not message:
      return
   stdout, stderr, returncode = await asyncio.tothread(doCommit, message)
   self.query_one(CommandLogDisplay).log(f'git commit -m "{message}',stdout, stderr, returncode)
   await self.query_one(FileDisplay).refresh_display(force=True)