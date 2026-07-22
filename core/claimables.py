from engine.debug import trace


# Claimables that cannot be removed -- they are ongoing permanent sources
PERMANENT = {
    "Achievements",
    "Divergent_Universe",
    "Currency_Wars",
    "Nameless_Honor",
}


def resolve_name(state, name_or_abbr):
    """
    Returns the canonical claimable name for a given name or abbreviation.
    Returns None if not found.
    """
    claimables = state.get("claimables", {})

    if name_or_abbr in claimables:
        return name_or_abbr

    for name, item in claimables.items():
        if item.get("abbreviation", "").lower() == name_or_abbr.lower():
            return name

    return None


def add_claimable(state, command):

    if "claimables" not in state:
        state["claimables"] = {}

    name  = command["name"]
    sj    = command.get("sj", 0)
    sp    = command.get("sp", 0)
    abbr  = command.get("abbreviation")

    entry = {
        "abbreviation": abbr,
        "sj":           sj,
        "sp":           sp,
    }

    if name in PERMANENT:
        entry["permanent"] = True

    # Preserve count fields if re-adding an existing entry
    if name in state["claimables"]:
        existing = state["claimables"][name]
        if "count_completed" in existing:
            entry["count_completed"] = existing["count_completed"]
        if "count_total" in existing:
            entry["count_total"] = existing["count_total"]

    state["claimables"][name] = entry
    return state


def set_claimable(state, command):
    """Update individual fields on an existing claimable."""

    if "claimables" not in state:
        state["claimables"] = {}

    name  = resolve_name(state, command["name"])
    field = command["field"]
    value = command.get("value")

    if name is None:
        trace(state, "CLAIMABLES", f"set_claimable: '{command['name']}' not found")
        return state, f"Claimable '{command['name']}' not found (tried name and abbreviation)"

    entry = state["claimables"][name]

    if field == "sj":
        entry["sj"] = int(value)

    elif field == "sp":
        entry["sp"] = int(value)

    elif field == "name":
        new_name = value
        if new_name in state["claimables"]:
            return state, f"Name '{new_name}' already exists"
        state["claimables"][new_name] = entry
        del state["claimables"][name]

    elif field == "abbr":
        entry["abbreviation"] = value

    elif field == "count":
        completed = command.get("count_completed")
        total     = command.get("count_total")
        if completed is not None:
            entry["count_completed"] = int(completed)
        if total is not None:
            entry["count_total"] = int(total)

    return state, "OK"


def remove_claimable(state, command):

    raw  = command["name"]
    name = resolve_name(state, raw)

    if name is None:
        trace(state, "CLAIMABLES", f"not found: {raw}")
        return state, f"'{raw}' not found (tried name and abbreviation)"

    if state["claimables"][name].get("permanent"):
        trace(state, "CLAIMABLES", f"refused remove of permanent: {name}")
        return state, f"'{name}' is permanent -- use 'set claimable {name} sj 0' to zero it out"

    del state["claimables"][name]
    trace(state, "CLAIMABLES", f"removed {name}")
    return state, "OK"


def compute_claimables(state):

    claimables = state.get("claimables", {})
    total_sj   = 0
    total_sp   = 0

    for item in claimables.values():
        total_sj += item.get("sj", 0)
        total_sp += item.get("sp", 0)

    claim_converted_total_sj = total_sj + (total_sp * 160)
    claim_converted_total_sp = claim_converted_total_sj // 160

    return {
        "total_claim_sj":           total_sj,
        "total_claim_sp":           total_sp,
        "claim_converted_total_sj": claim_converted_total_sj,
        "claim_converted_total_sp": claim_converted_total_sp,
    }
