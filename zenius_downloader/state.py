import json
from pathlib import Path

STATE_FILE = Path("state.json")


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"downloaded": {}}
    with STATE_FILE.open() as f:
        return json.load(f)


def save_state(state: dict) -> None:
    with STATE_FILE.open("w") as f:
        json.dump(state, f, indent=2)
