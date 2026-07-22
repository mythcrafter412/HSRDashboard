import json
import os

from core.migrate import CURRENT_SCHEMA_VERSION, check_and_migrate
from core.utils import get_data_dir

STATE_FILE = os.path.join(get_data_dir(), "state.json")


def create_initial_state():
    return {
        "_meta": {"schema_version": CURRENT_SCHEMA_VERSION},
        "pulls": {"sj": 0, "sp": 0},
        "claimables": {},
        "future_versions": {},
        "priority": {},
        "pity": {
            "char": {"count": 0, "guaranteed": False},
            "lc":   {"count": 0, "guaranteed": False}
        },
        "pull_history": {
            "char": [],
            "lc":   []
        },
        "luck": {
            "avg_pulls_char": 62,
            "avg_pulls_lc":   50,
            "win_rate":       55.0,
            "lc_win_rate":    75.0,
            "char_streak":    0,
            "lc_streak":      0
        },
        "config": {
            "sj_per_sp":      160,
            "debug_file":     True,
            "debug_terminal": False
        }
    }


def load_state():
    if not os.path.exists(STATE_FILE):
        state = create_initial_state()
        save_state(state)
        return state

    with open(STATE_FILE, "r") as f:
        state = json.load(f)

    state, applied = check_and_migrate(state)
    if applied:
        print(f"[MIGRATE] Applied schema migration(s): {', '.join(str(v) for v in applied)}")
    save_state(state)  # persist the schema_version stamp even when no migration ran

    return state


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
