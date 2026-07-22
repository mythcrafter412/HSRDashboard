import importlib.util
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

REPO      = "mythcrafter412/HSRDashboard"
API_LATEST_RELEASE = f"https://api.github.com/repos/{REPO}/releases/latest"
USER_AGENT = "HSRDashboard-Updater"


def _install_root():
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(appdata, "HSRDashboard")


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


def fetch_latest_release():
    """
    Returns a dict describing the latest GitHub Release, None if the repo
    has no releases published yet, or "offline" if the request failed
    (network down, DNS, etc.) so the caller can degrade gracefully.
    """
    req = urllib.request.Request(
        API_LATEST_RELEASE,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return "offline"
    except urllib.error.URLError:
        return "offline"

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
        # "{repo}-{commit}" folder — unwrap it before copying into app\.
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
    Python interpreter and runs it — no separately compiled main exe needed.
    """
    app_dir  = _app_dir()
    main_py  = os.path.join(app_dir, "main.py")

    # Must be set before importing anything from app\ — core/state.py,
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
    print()
    for key, label in options.items():
        print(f"  [{key}] {label}")
    try:
        return input("> ").strip()
    except EOFError:
        return ""


def main():
    print("// HSR Dashboard Updater")

    release = fetch_latest_release()
    offline = release == "offline"
    if offline:
        print("[WARN] Couldn't reach GitHub — skipping update check.")
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

    if release is None or release["version"] == local_version:
        print(f"Up to date (v{local_version})")
        choice = _prompt({"1": "Continue", "2": "Exit"})
        if choice == "1":
            run_app()
        return

    channel = "PRE-RELEASE" if release["prerelease"] else "RELEASE"
    print(f"Update available [{channel}]: v{local_version} -> v{release['version']}")
    choice = _prompt({"1": "Update", "2": "Continue anyway", "3": "Exit"})

    if choice == "1":
        print(f"Downloading v{release['version']}...")
        download_and_install(release["zip_url"])
        run_app()
    elif choice == "2":
        run_app()
    # else: exit


if __name__ == "__main__":
    main()
