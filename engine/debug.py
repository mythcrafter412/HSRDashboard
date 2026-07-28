import ctypes
import gzip
import os
import shutil
import sys
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


def _gzip_copy(src_path, dst_path):
    # A copy, not a move -- the live log stays in place and readable right
    # after the app closes. It's only cleared the NEXT time the app starts.
    with open(src_path, "rb") as src, gzip.open(dst_path, "wb") as dst:
        shutil.copyfileobj(src, dst)


def archive_current_session_logs():
    """
    Archives THIS session's latest.log/debug.log into logs/archive/ as
    paired, dated, incrementing gzip files -- without touching the live
    files, so they're still there to read immediately after the app closes.
    Meant to be called right as the app is closing, from both the normal
    exit path (main.py's finally block) and register_close_handler below
    (for the console window being closed directly, which raises no
    catchable Python exception at all).

    Safe to call more than once, but isn't expected to be in normal use --
    only one of the two hooks above fires for any given close.
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
            _gzip_copy(LATEST_FILE, os.path.join(ARCHIVE_DIR, f"{date_str}_{n}.log.gz"))
        if os.path.exists(DEBUG_FILE):
            _gzip_copy(DEBUG_FILE, os.path.join(ARCHIVE_DIR, f"{date_str}_{n}-debug.log.gz"))
    except Exception as e:
        print(f"[LOG] Couldn't archive session logs: {e}")


def _clear_stale_session_logs():
    """
    Runs once, lazily, on this session's first trace() call. Any
    latest.log/debug.log present at this point belong to the PREVIOUS
    session -- already archived when that one closed (see
    archive_current_session_logs) -- so it's safe to just clear them here
    to start this session fresh. If the previous session never closed
    cleanly (crash, killed via Task Manager), these were never archived and
    get overwritten unarchived -- an accepted gap, not worth a heavier
    fix for a personal single-user app's debug logs.
    """
    for path in (LATEST_FILE, DEBUG_FILE):
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"[LOG] Couldn't clear {path}: {e}")


_console_handler_ref = None  # must outlive the call to SetConsoleCtrlHandler, or ctypes GCs the callback


def register_close_handler():
    """
    Catches the console window being closed directly (the X button), user
    logoff, or system shutdown, and archives this session's logs before the
    process is terminated -- none of these raise a catchable Python
    exception the way Ctrl+C (KeyboardInterrupt) does, so this is the only
    hook available for them. Windows gives a several-second grace period
    for this handler to run before force-terminating the process regardless.
    ctypes only -- stdlib, no extra dependency, same pattern as updater.py's
    single-instance mutex. No-op on non-Windows.
    """
    global _console_handler_ref
    if sys.platform != "win32":
        return

    CTRL_CLOSE_EVENT    = 2
    CTRL_LOGOFF_EVENT    = 5
    CTRL_SHUTDOWN_EVENT = 6

    def handler(ctrl_type):
        if ctrl_type in (CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT):
            archive_current_session_logs()
        return False  # don't suppress Windows' own handling, just log first

    try:
        handler_type = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)
        _console_handler_ref = handler_type(handler)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(_console_handler_ref, True)
    except Exception:
        pass


def trace(state, level, layer, message):
    """
    Leveled session logging (TRACE < DEBUG < INFO < WARN < ERROR < CRITICAL).
    Writes to debug.log (TRACE and up -- everything) and, for INFO and up,
    also to latest.log. state may be None (e.g. while state.json itself
    failed to load) -- CRITICAL always still gets logged and shown.
    """
    global _rotated_this_session
    if not _rotated_this_session:
        _clear_stale_session_logs()
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
