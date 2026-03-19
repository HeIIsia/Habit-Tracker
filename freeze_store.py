import json
import os
from typing import Dict, Any

FREEZES_FILE = "freezes.json"

DEFAULT_DATA: Dict[str, Any] = {
    "global_freezes": 0,
    "habit_freezes": {}
}

def _safe_int(x, default=0) -> int:
    try:
        n = int(x)
        return n if n >= 0 else default
    except Exception:
        return default

def load_freezes() -> Dict[str, Any]:
    """Load freeze data from JSON. Returns a normalized dict."""
    if not os.path.exists(FREEZES_FILE):
        return dict(DEFAULT_DATA)

    try:
        with open(FREEZES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return dict(DEFAULT_DATA)

    if not isinstance(data, dict):
        return dict(DEFAULT_DATA)

    global_freezes = _safe_int(data.get("global_freezes", 0), 0)

    habit_freezes_raw = data.get("habit_freezes", {})
    if not isinstance(habit_freezes_raw, dict):
        habit_freezes_raw = {}

    habit_freezes: Dict[str, int] = {}
    for k, v in habit_freezes_raw.items():
        if isinstance(k, str) and k.strip():
            habit_freezes[k] = _safe_int(v, 0)

    return {
        "global_freezes": global_freezes,
        "habit_freezes": habit_freezes
    }

def save_freezes(data: Dict[str, Any]) -> None:
    """Save freeze data to JSON."""
    if not isinstance(data, dict):
        data = dict(DEFAULT_DATA)

    normalized = {
        "global_freezes": _safe_int(data.get("global_freezes", 0), 0),
        "habit_freezes": {}
    }

    hf = data.get("habit_freezes", {})
    if isinstance(hf, dict):
        for k, v in hf.items():
            if isinstance(k, str) and k.strip():
                normalized["habit_freezes"][k] = _safe_int(v, 0)

    with open(FREEZES_FILE, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2)

# -----------------------
# Public API (what your app calls)
# -----------------------

def get_global() -> int:
    """Return number of global (star) freezes."""
    return load_freezes()["global_freezes"]

def set_global(n: int) -> None:
    """Set global freeze count."""
    data = load_freezes()
    data["global_freezes"] = _safe_int(n, 0)
    save_freezes(data)

def add_global(delta: int) -> int:
    """Add/subtract global freezes; clamps at 0. Returns new value."""
    data = load_freezes()
    data["global_freezes"] = _safe_int(data.get("global_freezes", 0), 0)
    data["global_freezes"] = max(0, data["global_freezes"] + int(delta))
    save_freezes(data)
    return data["global_freezes"]

def get_habit(habit_name: str) -> int:
    """Return freeze count for a specific habit."""
    if not isinstance(habit_name, str) or not habit_name.strip():
        return 0
    data = load_freezes()
    return _safe_int(data["habit_freezes"].get(habit_name, 0), 0)

def set_habit(habit_name: str, n: int) -> None:
    """Set freeze count for a habit."""
    if not isinstance(habit_name, str) or not habit_name.strip():
        return
    data = load_freezes()
    data["habit_freezes"][habit_name] = _safe_int(n, 0)
    save_freezes(data)

def add_habit(habit_name: str, delta: int) -> int:
    """Add/subtract habit freezes; clamps at 0. Returns new value."""
    if not isinstance(habit_name, str) or not habit_name.strip():
        return 0
    data = load_freezes()
    cur = _safe_int(data["habit_freezes"].get(habit_name, 0), 0)
    cur = max(0, cur + int(delta))
    data["habit_freezes"][habit_name] = cur
    save_freezes(data)
    return cur
