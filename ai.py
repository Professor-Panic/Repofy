import os
import json
import requests #for ollama HTTP call
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()  # reads .env and loads ANTHROPIC_API_KEY into the environment

#client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
ANTHROPIC_MODEL = "claude-sonnet-5"
OLLAMA_MODEL = "qwen2.5-coder:3b"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 30

class CommitMessageProvider:
     """
    Base class for anything that can turn a git diff into a commit message.
    Both Claude and Ollama need the exact same prompt and the exact same
    JSON-parsing step —> and each subclass only overrides the one method that's actually different.

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


     
class AnthropicProvider(CommitMessageProvider):
    def __init__(self):
       # Client is created once when the provider is created, not on every call.
       self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def _call_model(self, prompt):
        response = self.client.messages.create(
              model=ANTHROPIC_MODEL,
              max_tokens=500,
              messages=[{"role": "user", "content": prompt}]
        )
        # response.content is a list of content blocks; [0] is the text block.
        return response.content[0].text
    
            

class OllamaProvider(CommitMessageProvider):
    def __init__(self, model=OLLAMA_MODEL):
        self.model = model ## lets you spin up a provider with a different model later if you want

          
    def _call_model(self, prompt):
        response = request.post(
                OLLAMA_URL,
                json={"model":self.model, "prompt":prompt, "stream": False},
                timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status() # throws an exception if Ollama returns an error status
            
        return response.json()["response"] # Ollama wraps the model's text under "response"
    


"""
Tries Claude first (best quality). Falls back to local Ollama if the
    API call fails for any reason — out of credits, no internet, bad key,
    rate limited, etc. Whoever answers, the shape returned is identical:
    {"summary": ..., "full": ...}.
"""

def suggest_commit_message(diff_text):
    try:
        return AnthropicProvider().suggest(diff_text)
    except Exception as e: #A broad catch -> so that no matter why the primary failed, use the backup.
        print(f"[ai] Anthropic call failed ({e}), falling back to Ollama...")
        return OllamaProvider().suggest(diff_text)
            
