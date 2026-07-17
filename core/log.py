import json
import os
from datetime import datetime

LOG_FILE = "data/history_log.json"


def load_log():
    if not os.path.exists(LOG_FILE):
        return []

    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def save_log(log):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

def write_log(action, details):
    log = load_log()

    log.append({
        "time": datetime.now().isoformat(),
        "action": action,
        "details": details
    })

    save_log(log)
