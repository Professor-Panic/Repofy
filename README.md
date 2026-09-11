# Repofy

Repofy is a terminal user interface (built with [Textual](https://textual.textualize.io/)) for everyday git workflows — staging, committing, branching, merging, and stashing — with an AI assistant built in to suggest commit messages and explain diffs.

## Current Status

**Implemented:**

- Full terminal UI (`app.py`) with live-updating panels for status, files, branches, commits, and stash
- Stage/unstage files, commit, push, pull, merge, and branch management, all from the keyboard
- Merge conflict detection and resolution flow (abort / continue)
- A command palette (`:`) for discoverable access to every action
- A directory picker (`File_picker.py`) for changing the working repo without leaving the app
- A sprint/task board (`Sprinter.py`) backed by a `TODO.md` file, synced to a remote branch with retry-on-conflict logic
- **AI commit assistant** (`ai.py` / `ai_binding.py`):
  - Suggests a commit message from your staged diff, with a one-line summary and a fuller multi-line message
  - Automatically checks and reformats messages to follow [Conventional Commits](https://www.conventionalcommits.org/) style
  - Explains a staged diff in plain English
  - Three-tier fallback chain: tries [Groq](https://groq.com/) first, then Anthropic's Claude, then a local [Ollama](https://ollama.com/) model — so the feature keeps working even without an internet connection or API credits
  - Shows which provider actually answered (☁ Groq / ☁ Claude / ⚙ Local Ollama)

## Requirements

- Python 3.10 or newer
- A local git repository to run Repofy inside of
- [Ollama](https://ollama.com/) installed locally, with a model pulled (the project defaults to `qwen2.5-coder:3b`) — this is what powers the AI assistant when no cloud provider is available
- (Optional) API keys for Groq and/or Anthropic, if you want cloud-based AI suggestions instead of relying solely on the local model

Install the Python dependencies:

```bash
pip install textual python-dotenv groq anthropic requests
```

Pull the local Ollama model:

```bash
ollama pull qwen2.5-coder:3b
```

## Configuration

Create a `.env` file in the project root (this file is git-ignored and should never be committed):

```
GROQ_API_KEY=your-groq-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
```

Both are optional. If neither is set, or if a cloud call fails for any reason, the AI assistant automatically falls back to the local Ollama model — no configuration needed for that path.

## Usage

Run Repofy from inside any git repository:

```bash
python app.py
```

### Key bindings

| Key | Action |
|---|---|
| `c` | Commit |
| `p` | Push |
| `l` | Pull |
| `ctrl+s` | Stage all changes |
| `space` | Stage/unstage the highlighted file |
| `t` | Open sprint board |
| `g` | AI-suggest commit message |
| `e` | AI-explain staged diff |
| `:` | Open command palette |
| `ctrl+x` | Quit |

The command palette (`:`) exposes every action above plus branch switching, merging, creating, and deleting, stashing, and the directory picker — useful if you forget a shortcut.

### AI commit assistant

1. Stage one or more changes (`space` on a file, or `ctrl+s` for everything).
2. Press `g`. Repofy reads the staged diff, sends it to the first available provider (Groq → Claude → local Ollama), and prefills the commit message input with the suggestion.
3. The suggested summary is checked against Conventional Commits style and corrected automatically if needed.
4. Press `c` to commit with the AI's message, or edit it first.
5. Press `e` at any point to get a plain-English explanation of what the staged diff actually does — useful before writing a commit message yourself, or for reviewing a teammate's changes.

## Project Layout

| File | Purpose |
|---|---|
| `app.py` | Application entry point and main screen layout |
| `ai.py` | AI provider classes (Groq, Anthropic, Ollama) and the fallback chain, commit-message quality check, and diff summarization |
| `ai_binding.py` | `AICommitPanel` — the self-contained widget wiring the AI assistant into the UI |
| `widgets.py` | All modal screens and display widgets (commit, branch, file, diff, sprint board, AI control modal, etc.) |
| `git_checker.py` | Thin wrappers around git CLI commands used throughout the app |
| `log_display.py` | Shared command-output log widget |
| `File_picker.py` | Directory picker modal for changing the working repo |
| `Sprinter.py` | Sprint/task board backed by `TODO.md`, synced to a remote branch |
| `git_tui.tcss` | Textual CSS styling for the whole app |
| `Brancher.py`, `Merger.py`, `Stager.py` | Currently unused placeholders |

## Development

Compile-check the Python files with:

```bash
python -m compileall .
```

The project does not currently include automated tests or a packaging configuration.

## Known limitations
- Cloud AI providers (Groq, Anthropic) require valid API keys and available credits; without them, or if they're rate-limited, the assistant transparently falls back to the local Ollama model.
