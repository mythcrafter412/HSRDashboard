import gzip
import os
import shutil
from datetime import datetime

from core.utils import get_data_dir

LEVELS = {"TRACE": 10, "DEBUG": 20, "INFO": 30, "WARN": 40, "ERROR": 50, "CRITICAL": 60}

LOGS_DIR    = os.path.join(get_data_dir(), "logs")
ARCHIVE_DIR = os.path.join(LOGS_DIR, "archive")
LATEST_FILE = os.path.join(LOGS_DIR, "latest.log")
DEBUG_FILE  = os.path.join(LOGS_DIR, "debug.log")

# latest.log: INFO and above (what a user actually needs to see)
# debug.log:  everything, TRACE and above (the full firehose)
LATEST_THRESHOLD = LEVELS["INFO"]
DEBUG_THRESHOLD  = LEVELS["TRACE"]

_rotated_this_session = False


def _gzip_and_remove(src_path, dst_path):
    with open(src_path, "rb") as src, gzip.open(dst_path, "wb") as dst:
        shutil.copyfileobj(src, dst)
    os.remove(src_path)


def _archive_previous_session():
    """
    Minecraft-style rotation: latest.log/debug.log are always overwritten
    fresh each session, never appended to forever. If either exists from a
    prior session, gzip it into logs/archive/ under a shared dated,
    incrementing name (paired so a session's latest+debug archives line up),
    then remove the originals so this session starts clean.
    """
    if not (os.path.exists(LATEST_FILE) or os.path.exists(DEBUG_FILE)):
        return

    try:
        os.makedirs(ARCHIVE_DIR, exist_ok=True)

        mtimes = [os.path.getmtime(p) for p in (LATEST_FILE, DEBUG_FILE) if os.path.exists(p)]
        date_str = datetime.fromtimestamp(max(mtimes)).strftime("%Y-%m-%d")

        n = 1
        while os.path.exists(os.path.join(ARCHIVE_DIR, f"{date_str}_{n}.log.gz")):
            n += 1

        if os.path.exists(LATEST_FILE):
            _gzip_and_remove(LATEST_FILE, os.path.join(ARCHIVE_DIR, f"{date_str}_{n}.log.gz"))
        if os.path.exists(DEBUG_FILE):
            _gzip_and_remove(DEBUG_FILE, os.path.join(ARCHIVE_DIR, f"{date_str}_{n}-debug.log.gz"))
    except Exception as e:
        print(f"[LOG] Couldn't archive previous session's logs: {e}")


def trace(state, level, layer, message):
    """
    Leveled session logging (TRACE < DEBUG < INFO < WARN < ERROR < CRITICAL).
    Writes to debug.log (TRACE and up -- everything) and, for INFO and up,
    also to latest.log. state may be None (e.g. while state.json itself
    failed to load) -- CRITICAL always still gets logged and shown.
    """
    global _rotated_this_session
    if not _rotated_this_session:
        _archive_previous_session()
        _rotated_this_session = True

    level_num = LEVELS.get(level.upper(), LEVELS["INFO"])
    config    = (state or {}).get("config", {})

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    line      = f"[{timestamp}] [{level.upper()}] [{layer}] {message}"

    # CRITICAL always reaches the terminal immediately -- can't rely on
    # someone digging through log files after something this serious happens.
    if level_num >= LEVELS["CRITICAL"] or config.get("debug_terminal", False):
        print(line)

    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        if level_num >= DEBUG_THRESHOLD:
            with open(DEBUG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        if level_num >= LATEST_THRESHOLD:
            with open(LATEST_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as e:
        print(f"[LOG] Could not write to log file: {e}")
