import ctypes
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from ctypes import wintypes

REPO       = "mythcrafter412/HSRDashboard"
API_RELEASES = f"https://api.github.com/repos/{REPO}/releases"
USER_AGENT = "HSRDashboard-Updater"

# Session-local (no "Global\" prefix) rather than machine-wide -- this is a
# personal single-user app, so the lock only needs to cover "don't let me
# double-launch this in my own session," not interfere across other Windows
# accounts/sessions on a shared machine, which "Global\" would do unnecessarily.
_SINGLE_INSTANCE_MUTEX_NAME = "HSRDashboard_SingleInstance_Mutex"
_ERROR_ALREADY_EXISTS       = 183

# Kept at module scope so the handle stays alive (and the lock held) for the
# whole process lifetime -- Windows releases it automatically on exit either way.
_instance_mutex_handle = None


def _acquire_single_instance_lock():
    """
    Windows-only single-instance guard via a named mutex (ctypes -- stdlib,
    no extra dependency). Two instances writing to the same data\\state.json
    at once risks one silently clobbering the other's save on exit, so a
    second launch is refused rather than allowed to run alongside the first.

    Returns True if this is the only running instance, False if another one
    already holds the lock. Fails open (returns True) on non-Windows or if
    the mutex API call itself fails, rather than ever blocking the user over
    a platform this hasn't been tested on.
    """
    global _instance_mutex_handle

    if sys.platform != "win32":
        return True

    import ctypes
    try:
        _instance_mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, _SINGLE_INSTANCE_MUTEX_NAME)
        if not _instance_mutex_handle:
            return True
        return ctypes.windll.kernel32.GetLastError() != _ERROR_ALREADY_EXISTS
    except Exception:
        return True


def _install_root():
    """
    Portable install: app\\ and data\\ live next to this exe (or, when run
    as a plain script, next to updater.py) wherever the user put it -- not
    tucked away in %APPDATA%. Lets the whole install be moved as one folder.

    getattr(sys, "frozen", False) and sys.executable are how PyInstaller
    reports "I'm a compiled exe" and its real path -- this needs no extra
    dependency, both are stdlib/interpreter-provided.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _app_dir():
    return os.path.join(_install_root(), "app")


def _data_dir():
    return os.path.join(_install_root(), "data")


def get_local_version():
    version_file = os.path.join(_app_dir(), "VERSION")
    if not os.path.exists(version_file):
        return None
    with open(version_file, "r") as f:
        return f.read().strip()


def _parse_version(v):
    """
    "0.2.1" -> (0, 2, 1), for numeric comparison rather than string equality
    -- a plain string check can't tell "ahead of the latest release" apart
    from "behind it", which matters for picking the right message/menu.
    Non-numeric parts fall back to 0 rather than raising, since a malformed
    VERSION file shouldn't crash the updater.
    """
    parts = []
    for part in v.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _compare_versions(a, b):
    """
    -1/0/1 for a<b, a==b, a>b. Pads the shorter tuple with zeros first --
    without this, plain tuple comparison treats (0, 2) as LESS than
    (0, 2, 0) (a shorter prefix loses), which would wrongly call "0.2" and
    "0.2.0" different versions instead of equal.
    """
    length   = max(len(a), len(b))
    a_padded = a + (0,) * (length - len(a))
    b_padded = b + (0,) * (length - len(b))
    if a_padded < b_padded:
        return -1
    if a_padded > b_padded:
        return 1
    return 0


def fetch_latest_release():
    """
    Returns a dict describing the latest published GitHub Release, None if
    the repo has none, or "offline" if the request failed (network down,
    DNS, etc.) so the caller can degrade gracefully.

    Deliberately hits /releases (the list endpoint) instead of the seemingly
    more convenient /releases/latest -- that endpoint's own docs say it
    returns "the most recent non-prerelease, non-draft release", i.e. it
    silently EXCLUDES pre-releases entirely, returning 404 if that's all
    that exists. Since this app is meant to support a pre-release/beta
    channel, that shortcut can't be used -- list everything published and
    take the newest instead.
    """
    req = urllib.request.Request(
        API_RELEASES,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            releases = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return "offline"
    except urllib.error.URLError:
        return "offline"

    published = [r for r in releases if not r.get("draft")]
    if not published:
        return None

    published.sort(key=lambda r: r.get("published_at") or r.get("created_at") or "", reverse=True)
    data = published[0]

    tag     = data.get("tag_name", "")
    version = tag[1:] if tag.startswith("v") else tag

    return {
        "tag":        tag,
        "version":    version,
        "zip_url":    data.get("zipball_url"),
        "prerelease": bool(data.get("prerelease")),
        "name":       data.get("name") or tag,
    }


def download_and_install(zip_url):
    """
    Downloads a GitHub source zipball and replaces app\\ with its contents.
    data\\ is a sibling directory and is never touched.
    """
    install_root = _install_root()
    app_dir      = _app_dir()
    os.makedirs(install_root, exist_ok=True)
    os.makedirs(_data_dir(), exist_ok=True)

    req = urllib.request.Request(zip_url, headers={"User-Agent": USER_AGENT})

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "release.zip")
        with urllib.request.urlopen(req, timeout=60) as resp, open(zip_path, "wb") as out:
            shutil.copyfileobj(resp, out)

        extract_dir = os.path.join(tmp, "extracted")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        # GitHub zipballs wrap everything in a single top-level
        # "{repo}-{commit}" folder -- unwrap it before copying into app\.
        entries = os.listdir(extract_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
            source_root = os.path.join(extract_dir, entries[0])
        else:
            source_root = extract_dir

        if os.path.exists(app_dir):
            shutil.rmtree(app_dir)
        shutil.copytree(source_root, app_dir)


def run_app():
    """
    Loads app\\main.py with this process's own (bundled, when frozen)
    Python interpreter and runs it -- no separately compiled main exe needed.
    """
    app_dir  = _app_dir()
    main_py  = os.path.join(app_dir, "main.py")

    # Must be set before importing anything from app\ -- core/state.py,
    # core/log.py, and engine/debug.py all read this at import time to keep
    # save data in data\ (a sibling of app\) instead of nested inside app\,
    # which gets wiped and replaced on every update.
    os.environ["HSR_DATA_DIR"] = _data_dir()

    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    spec   = importlib.util.spec_from_file_location("hsr_dashboard_main", main_py)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


def _wait_for_enter(message):
    try:
        input(message)
    except EOFError:
        pass


def _prompt(options):
    """
    Fallback typed-choice prompt (type a number, press Enter) -- used when
    raw keystroke reading isn't available: non-Windows, or stdin isn't a
    real attached console (piped/redirected input, as in every automated
    test of this file -- ReadConsoleInputW needs an actual console input
    handle and can't read from a pipe).
    """
    print()
    for key, label in options.items():
        print(f"  [{key}] {label}")
    try:
        return input("> ").strip()
    except EOFError:
        return ""


class _KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("bKeyDown",         wintypes.BOOL),
        ("wRepeatCount",     wintypes.WORD),
        ("wVirtualKeyCode",  wintypes.WORD),
        ("wVirtualScanCode", wintypes.WORD),
        ("uChar",            wintypes.WCHAR),
        ("dwControlKeyState", wintypes.DWORD),
    ]


class _INPUT_RECORD_EVENT(ctypes.Union):
    _fields_ = [("KeyEvent", _KEY_EVENT_RECORD), ("_padding", ctypes.c_byte * 16)]


class _INPUT_RECORD(ctypes.Structure):
    _fields_ = [("EventType", wintypes.WORD), ("Event", _INPUT_RECORD_EVENT)]


_STD_INPUT_HANDLE = -10
_KEY_EVENT        = 0x0001
_VK_RETURN        = 0x0D
_VK_BACK          = 0x08
_CTRL_PRESSED     = 0x0002 | 0x0004  # LEFT_CTRL_PRESSED | RIGHT_CTRL_PRESSED


def _read_single_keypress():
    """
    Reads raw console key-down events via ReadConsoleInputW (ctypes --
    stdlib, no dependency) until Enter, Ctrl+Enter, or Backspace is seen;
    returns "enter", "ctrl_enter", or "backspace". Plain msvcrt.getch()
    can't distinguish Ctrl+Enter from plain Enter -- holding Ctrl doesn't
    change the character code CR already has -- so this reads the actual
    KEY_EVENT_RECORD and checks dwControlKeyState directly instead.

    Returns None if this can't be done at all (non-Windows, no real
    console attached, or the API call fails) so the caller can fall back
    to the typed-choice _prompt() instead.
    """
    if sys.platform != "win32":
        return None

    try:
        h_input = ctypes.windll.kernel32.GetStdHandle(_STD_INPUT_HANDLE)
        if not h_input or h_input == -1:
            return None

        record      = _INPUT_RECORD()
        events_read = wintypes.DWORD()

        while True:
            ok = ctypes.windll.kernel32.ReadConsoleInputW(
                h_input, ctypes.byref(record), 1, ctypes.byref(events_read)
            )
            if not ok or events_read.value == 0:
                return None

            if record.EventType != _KEY_EVENT:
                continue

            key = record.Event.KeyEvent
            if not key.bKeyDown:
                continue  # ignore key-release events

            if key.wVirtualKeyCode == _VK_RETURN:
                return "ctrl_enter" if (key.dwControlKeyState & _CTRL_PRESSED) else "enter"
            if key.wVirtualKeyCode == _VK_BACK:
                return "backspace"
            # anything else: ignore, keep waiting
    except Exception:
        return None


def _prompt_continue_or_exit():
    print("  [ENTER] Continue   [BACKSPACE] Exit")
    key = _read_single_keypress()
    if key == "backspace":
        return "exit"
    if key is not None:
        return "continue"  # enter or ctrl_enter both just mean "go"
    choice = _prompt({"1": "Continue", "2": "Exit"})
    return "exit" if choice == "2" else "continue"


def _prompt_update_menu():
    print("  [CTRL+ENTER] Update   [ENTER] Continue anyway   [BACKSPACE] Exit")
    key = _read_single_keypress()
    if key == "ctrl_enter":
        return "update"
    if key == "backspace":
        return "exit"
    if key == "enter":
        return "continue"
    if key is None:
        choice = _prompt({"1": "Update", "2": "Continue anyway", "3": "Exit"})
        return {"1": "update", "2": "continue"}.get(choice, "exit")
    return "exit"


def main():
    # Safety net: some Windows console codepages can't encode every
    # character the app might print. Never let that crash the app --
    # worst case a character shows oddly instead of raising.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except Exception:
                pass

    print("// HSR Dashboard Updater")

    if not _acquire_single_instance_lock():
        print("[ERROR] HSRDashboard is already running -- close the other window first.")
        _wait_for_enter("Press Enter to exit...")
        return

    release = fetch_latest_release()
    offline = release == "offline"
    if offline:
        print("[WARN] Couldn't reach GitHub -- skipping update check.")
        release = None

    local_version = get_local_version()

    if local_version is None:
        if release is None:
            print("[ERROR] Nothing installed yet, and no release is available to install from.")
            if offline:
                print("        (Check your internet connection and try again.)")
            _wait_for_enter("Press Enter to exit...")
            return

        print(f"Installing HSRDashboard {release['tag']}...")
        download_and_install(release["zip_url"])
        run_app()
        return

    local_tuple  = _parse_version(local_version)
    remote_tuple = _parse_version(release["version"]) if release else None
    comparison   = _compare_versions(remote_tuple, local_tuple) if release else 0

    if release is None or comparison == 0:
        print(f"Up to date (v{local_version})")
        if _prompt_continue_or_exit() == "continue":
            run_app()
        return

    if comparison < 0:
        # Local is AHEAD of the latest published release -- not an update
        # to offer, just a heads-up that this isn't a normal released build.
        print("You are using a beta (unreleased) or modified version of this app,")
        print("this may include bugs and unfinished mechanics.")
        if _prompt_continue_or_exit() == "continue":
            run_app()
        return

    channel = "PRE-RELEASE" if release["prerelease"] else "RELEASE"
    print(f"Update available [{channel}]: v{local_version} -> v{release['version']}")
    choice = _prompt_update_menu()

    if choice == "update":
        print(f"Downloading v{release['version']}...")
        download_and_install(release["zip_url"])
        run_app()
    elif choice == "continue":
        run_app()
    # else: exit


if __name__ == "__main__":
    main()
