import os
import re
import json
import requests  # for Ollama HTTP call
from dotenv import load_dotenv
from groq import Groq
from anthropic import Anthropic

load_dotenv()  # loads GROQ_API_KEY and ANTHROPIC_API_KEY

# ----- Provider settings -----
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_TIMEOUT = 30
ANTHROPIC_MODEL = "claude-sonnet-5"
OLLAMA_MODEL = "qwen2.5-coder:3b"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 30


# ================================================================
#  Base class
# ================================================================
class CommitMessageProvider:
    """
    Base class for All three providers (Groq, Anthropic, Ollama) share the same prompt,
    the same JSON parsing step, and the same public `suggest()` method —
    each subclass only overrides `_call_model`, which is the one thing
    that actually differs.
    """

    def build_prompt(self, diff_text):
        # The doubled {{ }} are literal curly braces in the output
        # (a single { would be read as an f-string variable slot).
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
        # Public entry point. JSON is used instead of free-form text so we
        # can reliably split "summary" from "full" via json.loads() rather
        # than guessing where one ends and the other begins.
        prompt = self.build_prompt(diff_text)
        raw_text = self._call_model(prompt, json_mode=True)
        return self._parse_json(raw_text)

    def _parse_json(self, raw_text):
        # Strip markdown code fences if the model added them.
        cleaned = re.sub(r"```(?:json)?\s*", "", raw_text).strip()
        # Grab the JSON object between the first { and last }.
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON object found in response: {raw_text[:200]}")
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}\nResponse: {raw_text[:300]}")

    def _call_model(self, prompt, json_mode=False):
        # Subclasses override this.
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
            # Force the model to emit a JSON object as the final content
            # instead of reasoning text or markdown-wrapped JSON.
            kwargs["response_format"] = {"type": "json_object"}

        chat_completion = self.client.chat.completions.create(**kwargs)
        return chat_completion.choices[0].message.content

class AnthropicProvider(CommitMessageProvider):
    def __init__(self, model=ANTHROPIC_MODEL):
        self.model = model
        # Client is created once when the provider is created, not on every call.
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def _call_model(self, prompt, json_mode=False):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        # response.content is a list of content blocks; [0] is the text block.
        return response.content[0].text


# ================================================================
#  Ollama provider (local fallback)
# ================================================================
class OllamaProvider(CommitMessageProvider):
    def __init__(self, model=OLLAMA_MODEL):
        self.model = model  # lets you swap in a different local model later

    def _call_model(self, prompt, json_mode=False):
        response = requests.post(
            OLLAMA_URL,
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["response"]


def suggest_commit_message(diff_text):
    """
    Try Groq first . Fall back to Anthropic if Groq fails. Fall back
    to local Ollama if Anthropic also fails. 
    """
    try:
        result = GroqProvider().suggest(diff_text)
        result["provider"] = "groq"
        return result
    except Exception as e:
        print(f"[ai] Groq call failed ({e}), falling back to Anthropic...")

    try:
        result = AnthropicProvider().suggest(diff_text)
        result["provider"] = "claude"
        return result
    except Exception as e:
        print(f"[ai] Anthropic call failed ({e}), falling back to Ollama...")

    result = OllamaProvider().suggest(diff_text)
    result["provider"] = "ollama"
    return result


# ================================================================
#  Commit message quality check
# ================================================================
CONVENTIONAL_TYPES = ("feat", "fix", "chore", "docs", "refactor", "test", "style", "perf")

def check_conventional_format(summary):
    """
    Checks whether a commit summary follows Conventional Commits style,
    e.g. 'feat: add login screen' or 'fix(auth): handle expired tokens'.
    Returns (is_valid, corrected_summary). If invalid, corrected_summary
    guesses a reasonable prefix rather than leaving it unformatted.
    """
    pattern = r"^(" + "|".join(CONVENTIONAL_TYPES) + r")(\([\w\-]+\))?: .+"
    if re.match(pattern, summary):
        return True, summary
    # No valid prefix found — default to "chore:" as a safe, generic guess.
    corrected = f"chore: {summary[0].lower()}{summary[1:]}" if summary else summary
    return False, corrected


# ================================================================
#  Staged diff summary
# ================================================================
def summarize_diff(diff_text):
    """
    Turns a raw git diff into a simple per-file bullet list:
    filename, lines added, lines removed. Pure text parsing.
    Ref: https://git-scm.com/docs/git-diff
    """
    files = {}
    current_file = None

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            # line looks like: diff --git a/path/to/file.py b/path/to/file.py
            current_file = line.split("b/")[-1]
            files[current_file] = {"added": 0, "removed": 0}
        elif current_file and line.startswith("+") and not line.startswith("+++"):
            files[current_file]["added"] += 1
        elif current_file and line.startswith("-") and not line.startswith("---"):
            files[current_file]["removed"] += 1

    return files  # e.g. {"main.py": {"added": 12, "removed": 3}}


# ================================================================
#  Explain this diff  (same fallback chain, free-form text)
# ================================================================
def explain_diff(diff_text):
    """
    Plain-English explanation of what changed and why it might matter.
    Returns {"explanation": ..., "provider": ...} — no JSON parsing needed
    here since we just want free-form text back, not a structured object.
    """
    prompt = f"""
You are an expert software engineer reviewing a git diff for a teammate.
In 2-4 sentences, explain what changed and why it might matter.
Plain English, no code repetition, no JSON.

Diff:
{diff_text}
"""

    try:
        text = GroqProvider()._call_model(prompt, json_mode=False)
        provider = "groq"
    except Exception as e:
        print(f"[ai] Groq call failed ({e}), falling back to Anthropic...")
        try:
            text = AnthropicProvider()._call_model(prompt)
            provider = "claude"
        except Exception as e:
            print(f"[ai] Anthropic call failed ({e}), falling back to Ollama...")
            text = OllamaProvider()._call_model(prompt)
            provider = "ollama"

    return {"explanation": text.strip(), "provider": provider}