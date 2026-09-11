from pathlib import Path
import copy
import json

# Always resolve next to this file, regardless of the cwd the app is run from.
BASE_DIR = Path(__file__).resolve().parent
THEME_FILE = BASE_DIR / "themes.json"

# Built-in preset(s) available even before the user has ever saved anything,
# so Theme Maker isn't the only way to see a custom theme in action.
ARCTIC_THEME = {
    "name": "arctic",
    "primary": "#88C0D0",
    "secondary": "#81A1C1",
    "accent": "#B48EAD",
    "foreground": "#D8DEE9",
    "background": "#2E3440",
    "success": "#A3BE8C",
    "warning": "#EBCB8B",
    "error": "#BF616A",
    "surface": "#3B4252",
    "panel": "#434C5E",
    "dark": True,
    "variables": {
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#88C0D0",
        "input-selection-background": "#81a1c1 35%",
    },
}

DEFAULT_DATA = {
    "current": "tokyo-night",
    "themes": {
        "arctic": ARCTIC_THEME,
    },
}
def _load_all() -> dict:
    if not THEME_FILE.exists():
        return DEFAULT_DATA
    with open(THEME_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return DEFAULT_DATA
    data.setdefault("current", DEFAULT_DATA["current"])
    data.setdefault("themes", {})
    return data


def _save_all(data: dict) -> None:
    with open(THEME_FILE, "w") as f:
        json.dump(data, f, indent=2)


def SaveTheme(theme_data: dict) -> None:
    """Save/replace a custom theme definition and mark it as the current theme."""
    data = _load_all()
    name = theme_data["name"]
    data["themes"][name] = theme_data
    data["current"] = name
    _save_all(data)


def LoadTheme() -> dict:
    """Return the currently selected theme's data.

    For a built-in Textual theme this is just {"name": "<theme name>"}.
    For a saved custom theme this is the full color dict.
    """
    data = _load_all()
    current = data["current"]
    return data["themes"].get(current, {"name": current})


def LoadCustomThemes() -> dict:
    """Return every saved custom theme as {name: theme_data}."""
    return _load_all()["themes"]


def SetCurrentTheme(name: str) -> None:
    data = _load_all()
    data["current"] = name
    _save_all(data)