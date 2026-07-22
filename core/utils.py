import os
import re

VERSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VERSION")


def get_version():
    try:
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


def get_data_dir():
    """
    Resolve the directory for state.json/history_log.json/debug.log.

    updater.py sets HSR_DATA_DIR before launching the app, pointing at
    %APPDATA%\\HSRDashboard\\data — a sibling of app\\, not nested inside
    it, so save data survives every update (app\\ gets wiped and replaced
    each time). Falls back to a data\\ folder next to this repo's root for
    standalone `python main.py` use, where there's no app\\/data\\ split.
    """
    override = os.environ.get("HSR_DATA_DIR")
    if override:
        return override
    repo_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(repo_root, "data")


def display(name):
    """Convert stored name format to display format: Yao_Guang → Yao Guang"""
    return str(name).replace("_", " ")


def to_key(name):
    """Convert display/input name to storage key: Yao Guang → Yao_Guang"""
    return str(name).replace(" ", "_")


def parse_brackets(raw_input):
    """
    Extract bracket list and clean parts from a raw input string.

    e.g. "dashboard future add v4.3 * 100 [Himeko Nova, Yao Guang] notes here"
    returns:
        parts   = ["dashboard", "future", "add", "v4.3", "*", "100", "notes", "here"]
        content = ["Himeko_Nova", "Yao_Guang"]

    Returns (parts, content) where content is None if no brackets found.
    Items inside brackets are normalized to underscore keys.
    """
    match = re.search(r'\[([^\]]*)\]', raw_input)

    if not match:
        return raw_input.strip().split(), None

    raw_content = match.group(1)
    content     = [to_key(c.strip()) for c in raw_content.split(",") if c.strip()]

    cleaned = (raw_input[:match.start()].rstrip()
               + " "
               + raw_input[match.end():].lstrip())

    return cleaned.strip().split(), content


def display_list(items):
    """Display a list of stored name keys as a readable string."""
    if not items:
        return ""
    return ", ".join(display(item) for item in items)
