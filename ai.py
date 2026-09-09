import re
import json
import requests #for ollama HTTP call

OLLAMA_MODEL = "qwen2.5-coder:3b"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 30

class CommitMessageProvider:
     """
    Base class for anything that can turn a git diff into a commit message.
    Kept even with a single provider so the prompt-building and JSON-parsing
    steps stay in one place -- if another provider gets added later, it only
    has to override _call_model, same as before.

    """
     def build_prompt(self, diff_text):
        # The doubled {{ }} are literal curly braces in the output (since a
        # single { would be read as an f-string variable slot).
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
        #public method callers
        prompt = self.build_prompt(diff_text)
        #Instead of asking the model for a "summary and a full message" in free-form text 
        # and then trying to guess where one ends and the other begins, JSON gives you a format Python can parse reliably with json.loads()
        raw_text = self._call_model(prompt) #subclass-specific network call
        return json.loads(raw_text) ##turns the JSON string into an actual Python dict, so you can access result["summary"] and result["full"] afterward.


     def _call_model(self, prompt):
         #subclasses override this
         raise NotImplementedError("Subclasses must implement _call_model")


class OllamaProvider(CommitMessageProvider):
    def __init__(self, model=OLLAMA_MODEL):
        self.model = model ## lets you spin up a provider with a different model later if you want

          
    def _call_model(self, prompt):
        response = requests.post(
                OLLAMA_URL,
                json={"model":self.model, "prompt":prompt, "stream": False},
                timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status() # throws an exception if Ollama returns an error status
            
        return response.json()["response"] # Ollama wraps the model's text under "response"
    


"""
Ollama-only: no Claude fallback right now. Whatever calls this gets the
    same shape back either way: {"summary": ..., "full": ..., "provider": "ollama"}.
"""

def suggest_commit_message(diff_text):
    result = OllamaProvider().suggest(diff_text)
    result["provider"] = "ollama" # tag the source before returning -> labelling
    return result


#---------------COMMIT MESSAGE QUALITY CHECK--------------
#Shows judgment, not just generation.
#source => https://www.conventionalcommits.org/en/v1.0.0/#specification
CONVENTIONAL_TYPES = ("feat", "fix", "chore", "docs", "refactor", "test", "style", "perf")

def check_conventional_format(summary):
    """
    Checks whether a commit summary follows Conventional Commits style, e.g. 'feat: add login screen' or 'fix(auth): handle expired tokens'.
    Returns (is_valid, corrected_summary). If invalid, corrected_summary guesses a reasonable prefix rather than leaving it unformatted.
    """
    #Reference => Python re module docs -> https://docs.python.org/3/library/re.html
    pattern = r"^(" + "|".join(CONVENTIONAL_TYPES) + r")(\([\w\-]+\))?: .+"
    if re.match(pattern, summary):
        return True, summary
    # No valid prefix found — default to "chore:" as a safe, generic guess
    # rather than silently failing or guessing wrong every time.
    corrected = f"chore: {summary[0].lower()}{summary[1:]}" if summary else summary
    return False, corrected



#------------------STAGED-DIFF-SUMMARY--------------------------
#A bullet-point breakdown of files changed and what changed in each, shown above the commit box useful context, 
# and reuses the same diff data you already have.
def summarize_diff(diff_text):
    """
    Turns a raw git diff into a simple per-file bullet list:
    filename, lines added, lines removed. Pure text parsing — no AI call.
    """

    files={}
    current_file = None

    #Resource : https://git-scm.com/docs/git-diff
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            # line looks like: diff --git a/path/to/file.py b/path/to/file.py
            current_file = line.split("b/")[-1]
            files[current_file]= {"added":0, "removed":0}
        elif current_file and line.startswith("+") and not line.startswith("+++"):
            files[current_file]["added"] += 1
        elif current_file and line.startswith("-") and not line.startswith("---"):
            files[current_file]["removed"] +=1

    return files  # e.g. {"main.py": {"added": 12, "removed": 3}}


# ------------------EXPLAIN THIS DIFF--------------------------
#This is exactly why _call_model was kept separate from suggest().
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
     text = OllamaProvider()._call_model(prompt)
     return {"explanation": text.strip(), "provider": "ollama"}