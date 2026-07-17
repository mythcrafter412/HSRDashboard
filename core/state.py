import json
import os

BASE_DIR   = os.path.dirname(os.path.dirname(__file__))
STATE_FILE = os.path.join(BASE_DIR, "data", "state.json")


def create_initial_state():
    return {
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
        return json.load(f)


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
