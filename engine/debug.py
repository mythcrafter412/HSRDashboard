import os
from datetime import datetime

BASE_DIR   = os.path.dirname(os.path.dirname(__file__))
DEBUG_FILE = os.path.join(BASE_DIR, "data", "debug.log")


def trace(state, layer, message):

    config        = state.get("config", {})
    write_to_file = config.get("debug_file",     True)   # ON by default
    write_to_term = config.get("debug_terminal",  False)  # OFF by default

    if not write_to_file and not write_to_term:
        return

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    line      = f"[{timestamp}] [{layer}] {message}"

    if write_to_term:
        print(line)

    if write_to_file:
        try:
            os.makedirs(os.path.dirname(DEBUG_FILE), exist_ok=True)
            with open(DEBUG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"[DEBUG] Could not write to debug.log: {e}")
