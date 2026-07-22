import importlib
import os

# Bump this whenever data/state.json's shape changes, and add a matching
# migrations/00N_description.py exposing TARGET_VERSION and upgrade(state).
# There's no migration needed to reach version 1 -- it's the baseline shape
# as of when this system was introduced, and existing save files are already
# compliant with it, so a missing _meta.schema_version is treated as current
# rather than as "version 0".
CURRENT_SCHEMA_VERSION = 1

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")


def _discover_migrations():
    """
    Find migration modules in migrations/, named like 001_description.py.
    Each must expose TARGET_VERSION (int) and upgrade(state) -> state.
    Returns them sorted by TARGET_VERSION ascending.
    """
    if not os.path.isdir(MIGRATIONS_DIR):
        return []

    found = []
    for filename in sorted(os.listdir(MIGRATIONS_DIR)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        module = importlib.import_module(f"migrations.{filename[:-3]}")
        if hasattr(module, "TARGET_VERSION") and hasattr(module, "upgrade"):
            found.append(module)

    found.sort(key=lambda m: m.TARGET_VERSION)
    return found


def check_and_migrate(state):
    """
    Compare state's _meta.schema_version against CURRENT_SCHEMA_VERSION and
    apply any pending migrations in order.

    Returns (state, applied) where applied is the list of version numbers
    that were run (empty if the state was already current).
    """
    meta    = state.setdefault("_meta", {})
    current = meta.get("schema_version", CURRENT_SCHEMA_VERSION)

    if current >= CURRENT_SCHEMA_VERSION:
        meta["schema_version"] = CURRENT_SCHEMA_VERSION
        return state, []

    applied = []
    for module in _discover_migrations():
        if module.TARGET_VERSION <= current:
            continue
        if module.TARGET_VERSION > CURRENT_SCHEMA_VERSION:
            break
        state   = module.upgrade(state)
        current = module.TARGET_VERSION
        applied.append(current)

    meta["schema_version"] = current
    return state, applied
