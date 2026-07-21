from core.claimables import add_claimable, remove_claimable, set_claimable, resolve_name
from core.priority import (add_priority, remove_priority, update_priority_field,
                            set_priority_order, record_char_result, record_lc_result)
from core.state import save_state
from core.log import write_log
from rendering.registry import get_view
from engine.debug import trace


HANDLERS = {}

def register(key):
    def wrapper(func):
        HANDLERS[key] = func
        return func
    return wrapper


# -------------------------
# HELP
# -------------------------
@register(("help", None))
def handle_help(state, command):

    G = "\033[92m"
    D = "\033[2m"
    R = "\033[0m"

    def sec(t):   return f"\n{G}// {t}{R}"
    def cmd(t):   return f"  {t}"
    def ex(t):    return f"  {D}e.g.  {t}{R}"
    def note(t):  return f"  {D}      {t}{R}"

    lines = [
        "",
        f"{G}// COMMANDS — v0.2.0{R}",
        "=" * 60,

        sec("Navigation"),
        cmd("open <view>"),
        ex("open dashboard  |  open claimables  |  open pull_history"),

        sec("Dashboard — Pulls"),
        cmd("dashboard pulls set <sj> <sp>         overwrite"),
        cmd("dashboard pulls add <sj> <sp>          add to existing"),
        cmd("dashboard pulls subtract <sj> <sp>     subtract from existing"),
        ex("dashboard pulls set 1058 210"),

        sec("Dashboard — Future Versions"),
        cmd("dashboard future add <version> <sj|*> <sp|*> [chars] <notes>"),
        note("* = unknown / omit.  chars in [brackets, comma separated]"),
        ex("dashboard future add v4.3 * 100 [Himeko Nova, Robin SP] N/A"),
        cmd("dashboard future set <version> <sj|sp|characters|notes> <value>"),
        cmd("dashboard future remove <version>"),

        sec("Dashboard — Luck"),
        cmd("dashboard luck set <field> <value>"),
        note("fields: charpulls  lcpulls  winrate  lcrate  charstreak  lcstreak"),
        ex("dashboard luck set charpulls 63.1"),

        sec("Dashboard — Pity  (shared across all limited banners)"),
        cmd("dashboard pity set char <count> [guaranteed|fresh]"),
        cmd("dashboard pity set lc <count> [guaranteed|fresh]"),
        ex("dashboard pity set char 45 guaranteed"),

        sec("Claimables"),
        cmd("claimables claimable add <name> <sj> <sp> [abbr]"),
        cmd("claimables claimable set <name> <field> <value>"),
        note("fields:  sj <n>  |  sp <n>  |  name <newname>  |  abbr <newabbr>"),
        note("         count <completed> <total>  (achievements only)"),
        cmd("claimables claimable subtract <name> <sj> <sp>"),
        cmd("claimables claimable remove <name or abbreviation>"),
        note("Achievements, Divergent_Universe, Currency_Wars, Nameless_Honor"),
        note("are permanent and cannot be removed."),

        sec("Priority"),
        cmd("priority char add <name> <order> [char|lc|both]"),
        note("type defaults to 'both' if omitted"),
        note("inserting at an occupied order shifts existing entries down"),
        ex("priority char add Nihilux 1 both"),
        ex("priority char add Firefly 2 lc"),
        cmd("priority char set <name> type <char|lc|both>"),
        cmd("priority char set <name> order <n>"),
        note("moving to an occupied order shifts everything between old/new position"),
        cmd("priority char set <name> eidolon <0-6>"),
        note("target Eidolon level — determines copies needed (E0=1 copy ... E6=7 copies)"),
        ex("priority char set Nihilux eidolon 2"),
        cmd("priority char set <name> superimposition <1-5>"),
        note("target Superimposition level — determines LC copies needed (S1=1 ... S5=5)"),
        ex("priority char set Nihilux superimposition 1"),
        cmd("priority char set <name> result <won|lost|skip> [spent_sp] [lost_to]"),
        note("auto-updates pity, luck stats, and win/loss streak"),
        note("lost_to only applies when result is 'lost'"),
        note("skip with a spent_sp value logs partial pulls abandoned without a"),
        note("  5-star (doesn't touch global pity/guaranteed — track those via"),
        note("  'dashboard pity' — and never counts toward the avg-pulls stat)"),
        ex("priority char set Nihilux result won 65"),
        ex("priority char set Nihilux result lost 90 Firefly"),
        ex("priority char set Nihilux result skip"),
        ex("priority char set Nihilux result skip 22"),
        cmd("priority char remove <name>"),
        cmd("priority lc set <name> result <won|lost|skip> [spent_sp] [lost_to]"),
        ex("priority lc set Nihilux result won 43"),
        ex("priority lc set Nihilux result lost 60 Firefly"),

        sec("Debug"),
        cmd("debug file enable|disable      write trace to data/debug.log  (default: on)"),
        cmd("debug terminal enable|disable  show trace in terminal          (default: off)"),

        sec("Other"),
        cmd("help / commands"),
        cmd("exit / quit"),
        "",
    ]

    print("\n".join(lines))


# -------------------------
# OPEN VIEW
# -------------------------
@register(("open", None))
def handle_open_view(state, command):

    view_name = command.get("view")
    renderer  = get_view(view_name)

    if not renderer:
        trace(state, "HANDLER", f"No view registered: {view_name}")
        print(f"[ERROR] Unknown view: '{view_name}'")
        return

    print(renderer(state))
    write_log("OPEN_VIEW", {"view": view_name})


# -------------------------
# DEBUG TOGGLE
# -------------------------
@register(("debug", "debug"))
def handle_debug_toggle(state, command):

    payload = command.get("payload", {})
    target  = payload.get("target")
    enabled = payload.get("enabled")

    state.setdefault("config", {})
    key = "debug_file" if target == "file" else "debug_terminal"
    state["config"][key] = enabled
    save_state(state)

    status = "enabled" if enabled else "disabled"
    dest   = "data/debug.log" if target == "file" else "terminal"
    print(f"[OK] Debug {target} {status} — {'writing to ' + dest if enabled else 'not writing to ' + dest}")


# -------------------------
# PULLS
# -------------------------
@register(("set", "pulls"))
def handle_set_pulls(state, command):
    payload = command.get("payload", {})
    sj = payload.get("sj", 0)
    sp = payload.get("sp", 0)
    state["pulls"]["sj"] = sj
    state["pulls"]["sp"] = sp
    save_state(state)
    write_log("SET_PULLS", {"sj": sj, "sp": sp})
    print(f"[OK] Pulls set — SJ: {sj}  SP: {sp}")

@register(("add", "pulls"))
def handle_add_pulls(state, command):
    payload = command.get("payload", {})
    sj = payload.get("sj", 0)
    sp = payload.get("sp", 0)
    state["pulls"]["sj"] += sj
    state["pulls"]["sp"] += sp
    save_state(state)
    write_log("ADD_PULLS", {"sj": sj, "sp": sp})
    print(f"[OK] Pulls updated — SJ: {state['pulls']['sj']}  SP: {state['pulls']['sp']}")

@register(("subtract", "pulls"))
def handle_subtract_pulls(state, command):
    payload = command.get("payload", {})
    sj = payload.get("sj", 0)
    sp = payload.get("sp", 0)
    state["pulls"]["sj"] = max(0, state["pulls"]["sj"] - sj)
    state["pulls"]["sp"] = max(0, state["pulls"]["sp"] - sp)
    save_state(state)
    write_log("SUBTRACT_PULLS", {"sj": sj, "sp": sp})
    print(f"[OK] Pulls updated — SJ: {state['pulls']['sj']}  SP: {state['pulls']['sp']}")


# -------------------------
# FUTURE VERSION
# -------------------------
@register(("add", "future"))
def handle_add_future(state, command):
    payload = command.get("payload", {})
    version = payload.get("version")
    if not version:
        print("[ERROR] Missing version")
        return
    raw_sj  = payload.get("sj", "*")
    raw_sp  = payload.get("sp", "*")
    chars   = payload.get("characters")
    notes   = payload.get("notes", "N/A")
    sj      = None if raw_sj == "*" else int(raw_sj)
    sp      = None if raw_sp == "*" else int(raw_sp)
    state.setdefault("future_versions", {})[version] = {
        "sj": sj, "sp": sp, "characters": chars, "notes": notes
    }
    save_state(state)
    write_log("ADD_FUTURE_VERSION", {"version": version})
    print(f"[OK] Added future version: {version}")

@register(("set", "future_field"))
def handle_set_future_field(state, command):
    payload  = command.get("payload", {})
    version  = payload.get("version")
    field    = payload.get("field")
    value    = payload.get("value")
    fv = state.get("future_versions", {})
    if version not in fv:
        print(f"[ERROR] Future version '{version}' not found")
        return
    if field == "sj":
        fv[version]["sj"] = None if value == "*" else int(value)
    elif field == "sp":
        fv[version]["sp"] = None if value == "*" else int(value)
    elif field == "characters":
        fv[version]["characters"] = value if isinstance(value, list) else None
    elif field == "notes":
        fv[version]["notes"] = value
    save_state(state)
    write_log("SET_FUTURE_FIELD", {"version": version, "field": field})
    print(f"[OK] {version} {field} updated")

@register(("remove", "future"))
def handle_remove_future(state, command):
    payload = command.get("payload", {})
    version = payload.get("version")
    if version not in state.get("future_versions", {}):
        print(f"[ERROR] Future version '{version}' not found")
        return
    del state["future_versions"][version]
    save_state(state)
    write_log("REMOVE_FUTURE_VERSION", {"version": version})
    print(f"[OK] Removed future version: {version}")


# -------------------------
# LUCK
# -------------------------
@register(("set", "luck"))
def handle_set_luck(state, command):
    payload   = command.get("payload", {})
    field     = payload.get("field")
    value     = payload.get("value")
    field_map = {
        "charpulls":  "avg_pulls_char",
        "lcpulls":    "avg_pulls_lc",
        "winrate":    "win_rate",
        "lcrate":     "lc_win_rate",
        "charstreak": "char_streak",
        "lcstreak":   "lc_streak",
    }
    key = field_map.get(field)
    if not key:
        print(f"[ERROR] Unknown luck field: {field}")
        return
    state.setdefault("luck", {})[key] = value
    save_state(state)
    write_log("SET_LUCK", {"field": field, "value": value})
    print(f"[OK] Luck {field} = {value}")


# -------------------------
# PITY
# -------------------------
@register(("set", "pity"))
def handle_set_pity(state, command):
    payload    = command.get("payload", {})
    banner     = payload.get("banner")
    count      = payload.get("count")
    guaranteed = payload.get("guaranteed")

    pity = state.setdefault("pity", {})
    entry = pity.setdefault(banner, {"count": 0, "guaranteed": False})

    if count is not None:
        entry["count"] = count
    if guaranteed is not None:
        entry["guaranteed"] = guaranteed

    save_state(state)
    write_log("SET_PITY", {"banner": banner, "count": count, "guaranteed": guaranteed})

    parts = []
    if count is not None:
        limit = 90 if banner == "char" else 80
        parts.append(f"{count}/{limit}")
    if guaranteed is not None:
        parts.append("GUARANTEED" if guaranteed else "fresh")
    print(f"[OK] {banner} pity: {' '.join(parts)}")


# -------------------------
# CLAIMABLES
# -------------------------
@register(("add", "claimable"))
def handle_add_claimable(state, command):
    payload = command.get("payload", {})
    add_claimable(state, payload)
    save_state(state)
    write_log("ADD_CLAIMABLE", payload)
    print(f"[OK] Added claimable: {payload.get('name')}")

@register(("set", "claimable_field"))
def handle_set_claimable(state, command):
    payload = command.get("payload", {})
    _, msg  = set_claimable(state, payload)
    if msg != "OK":
        print(f"[ERROR] {msg}")
        return
    save_state(state)
    write_log("SET_CLAIMABLE", payload)
    field = payload.get("field")
    name  = payload.get("name")
    if field == "count":
        print(f"[OK] {name} count: {payload.get('count_completed')} / {payload.get('count_total')}")
    elif field == "name":
        print(f"[OK] Renamed '{name}' → '{payload.get('value')}'")
    else:
        print(f"[OK] {name} {field} = {payload.get('value')}")

@register(("subtract", "claimable"))
def handle_subtract_claimable(state, command):
    payload = command.get("payload", {})
    name    = resolve_name(state, payload.get("name", ""))
    if name is None:
        print(f"[ERROR] Claimable '{payload.get('name')}' not found")
        return
    sj = payload.get("sj", 0)
    sp = payload.get("sp", 0)
    entry = state["claimables"][name]
    entry["sj"] = max(0, entry.get("sj", 0) - sj)
    entry["sp"] = max(0, entry.get("sp", 0) - sp)
    save_state(state)
    write_log("SUBTRACT_CLAIMABLE", {"name": name, "sj": sj, "sp": sp})
    print(f"[OK] {name} — SJ: {entry['sj']}  SP: {entry['sp']}")

@register(("remove", "claimable"))
def handle_remove_claimable(state, command):
    payload    = command.get("payload", {})
    _, msg = remove_claimable(state, payload)
    if msg != "OK":
        print(f"[ERROR] {msg}")
        return
    save_state(state)
    write_log("REMOVE_CLAIMABLE", payload)
    print(f"[OK] Removed claimable: {payload.get('name')}")


# -------------------------
# PRIORITY
# -------------------------
@register(("add", "priority"))
def handle_add_priority(state, command):
    payload = command.get("payload", {})
    name    = payload.get("name")
    add_priority(state, payload)
    save_state(state)
    write_log("ADD_PRIORITY", payload)
    actual_order = state["priority"][name]["order"]
    print(f"[OK] Added to priority: {name}  order={actual_order}  type={payload.get('type', 'both')}")

@register(("remove", "priority"))
def handle_remove_priority(state, command):
    payload = command.get("payload", {})
    name    = payload.get("name")
    remove_priority(state, name)
    save_state(state)
    write_log("REMOVE_PRIORITY", {"name": name})
    print(f"[OK] Removed from priority: {name}")

@register(("set", "priority_order"))
def handle_set_priority_order(state, command):
    payload = command.get("payload", {})
    name    = payload.get("name")
    order   = payload.get("order")
    set_priority_order(state, name, order)
    save_state(state)
    write_log("SET_PRIORITY_ORDER", {"name": name, "order": order})
    actual_order = state["priority"][name]["order"]
    print(f"[OK] {name} order → {actual_order}")

@register(("set", "priority_type"))
def handle_set_priority_type(state, command):
    payload = command.get("payload", {})
    name    = payload.get("name")
    ptype   = payload.get("type")
    update_priority_field(state, name, "type", ptype)
    save_state(state)
    write_log("SET_PRIORITY_TYPE", {"name": name, "type": ptype})
    print(f"[OK] {name} type → {ptype}")

@register(("set", "priority_eidolon"))
def handle_set_priority_eidolon(state, command):
    payload = command.get("payload", {})
    name    = payload.get("name")
    eidolon = payload.get("eidolon")
    update_priority_field(state, name, "target_eidolon", eidolon)
    save_state(state)
    write_log("SET_PRIORITY_EIDOLON", {"name": name, "eidolon": eidolon})
    print(f"[OK] {name} target Eidolon → E{eidolon}  ({eidolon + 1} copies)")

@register(("set", "priority_superimposition"))
def handle_set_priority_superimposition(state, command):
    payload         = command.get("payload", {})
    name            = payload.get("name")
    superimposition = payload.get("superimposition")
    update_priority_field(state, name, "target_superimposition", superimposition)
    save_state(state)
    write_log("SET_PRIORITY_SUPERIMPOSITION", {"name": name, "superimposition": superimposition})
    print(f"[OK] {name} target Superimposition → S{superimposition}  ({superimposition} copies)")

@register(("set", "priority_char_result"))
def handle_set_char_result(state, command):
    payload = command.get("payload", {})
    name    = payload.get("name")
    result  = payload.get("result")
    spent   = payload.get("spent")
    lost_to = payload.get("lost_to")

    update_priority_field(state, name, "char_result", result)
    if spent is not None:
        update_priority_field(state, name, "char_spent", spent)

    record_char_result(state, result, spent, lost_to, name)
    save_state(state)
    write_log("SET_PRIORITY_CHAR_RESULT", payload)
    spent_str = f"  spent: {spent} SP" if spent else ""
    lost_str  = f"  lost to: {lost_to}" if lost_to else ""
    print(f"[OK] {name} char: {result}{spent_str}{lost_str}")

@register(("set", "priority_lc_result"))
def handle_set_lc_result(state, command):
    payload = command.get("payload", {})
    name    = payload.get("name")
    result  = payload.get("result")
    spent   = payload.get("spent")
    lost_to = payload.get("lost_to")

    update_priority_field(state, name, "lc_result", result)
    if spent is not None:
        update_priority_field(state, name, "lc_spent", spent)

    record_lc_result(state, result, spent, lost_to, name)
    save_state(state)
    write_log("SET_PRIORITY_LC_RESULT", payload)
    spent_str = f"  spent: {spent} SP" if spent else ""
    lost_str  = f"  lost to: {lost_to}" if lost_to else ""
    print(f"[OK] {name} LC: {result}{spent_str}{lost_str}")
