import os
import re
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # loads GROQ_API_KEY

# Groq settings - use a model you confirmed works
GROQ_MODEL = "openai/gpt-oss-120b"   # or "groq/compound", "openai/gpt-oss-20b"
GROQ_TIMEOUT = 30

class CommitMessageProvider:
    def build_prompt(self, diff_text):
        return f"""
You are an expert software engineer writing a git commit message.
Given the diff below, respond with ONLY a JSON object, no other text before or after, in exactly this format:
{{
"summary": "a single-line summary under 72 characters", 
"full": "a fuller multi-line message: summary line, blank line, then bullet points on what changed and why"
}}

Diff:
{diff_text}
"""

    def suggest(self, diff_text):
        prompt = self.build_prompt(diff_text)
        # json_mode=True: forces the model to return a clean JSON object
        # instead of prose/reasoning wrapped around it.
        raw_text = self._call_model(prompt, json_mode=True)
        return self._parse_json(raw_text)

    def _parse_json(self, raw_text):
        # Remove markdown code fences if present
        cleaned = re.sub(r"```(?:json)?\s*", "", raw_text).strip()
        # Try to find a JSON object between { and }
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON object found in response: {raw_text[:200]}")
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}\nResponse: {raw_text[:300]}")

    def _call_model(self, prompt, json_mode=False):
        raise NotImplementedError("Subclasses must implement _call_model")


class GroqProvider(CommitMessageProvider):
    def __init__(self, model=GROQ_MODEL):
        self.model = model
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set in environment")
        self.client = Groq(api_key=self.api_key)

    def _call_model(self, prompt, json_mode=False):
        kwargs = {
            "messages": [{"role": "user", "content": prompt}],
            "model": self.model,
            "temperature": 0.3,
            "max_completion_tokens": 1024,
            # "low" keeps the model's internal reasoning short so it
            # doesn't eat the whole token budget before answering.
            "reasoning_effort": "low",
            "timeout": GROQ_TIMEOUT,
        }
        if json_mode:
            # Forces the model to emit a JSON object as the final content
            # instead of reasoning text or markdown-wrapped JSON.
            kwargs["response_format"] = {"type": "json_object"}

        chat_completion = self.client.chat.completions.create(**kwargs)
        return chat_completion.choices[0].message.content


# ------------------- Public API functions ------------------------

def suggest_commit_message(diff_text):
    result = GroqProvider().suggest(diff_text)
    result["provider"] = "groq"
    return result


# --------------- COMMIT MESSAGE QUALITY CHECK -------------------
CONVENTIONAL_TYPES = ("feat", "fix", "chore", "docs", "refactor", "test", "style", "perf")

def check_conventional_format(summary):
    pattern = r"^(" + "|".join(CONVENTIONAL_TYPES) + r")(\([\w\-]+\))?: .+"
    if re.match(pattern, summary):
        return True, summary
    corrected = f"chore: {summary[0].lower()}{summary[1:]}" if summary else summary
    return False, corrected


# ------------------- STAGED DIFF SUMMARY ------------------------
def summarize_diff(diff_text):
    files = {}
    current_file = None
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            current_file = line.split("b/")[-1]
            files[current_file] = {"added": 0, "removed": 0}
        elif current_file and line.startswith("+") and not line.startswith("+++"):
            files[current_file]["added"] += 1
        elif current_file and line.startswith("-") and not line.startswith("---"):
            files[current_file]["removed"] += 1
    return files

def explain_diff(diff_text):
    prompt = f"""
You are an expert software engineer reviewing a git diff for a teammate.
In 1-2 sentences, explain what changed.
Plain English, no code repetition, no JSON.Keep it short and consise.Don't explain the benefits
Diff:
{diff_text}
"""
    text = GroqProvider()._call_model(prompt, json_mode=False)
    return {"explanation": text.strip(), "provider": "groq"}