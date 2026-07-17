from core.priority import get_sorted_priority, compute_floors


GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"
RESET  = "\033[0m"

_STATUS_MAP = {
    "SAFE":        (GREEN,  "[+]"),
    "CONTROLLED":  (GREEN,  "[+]"),
    "CONDITIONAL": (YELLOW, "[/]"),
    "ELEVATED":    (YELLOW, "[/]"),
    "BLOCKED":     (RED,    "[-]"),
    "HIGH":        (RED,    "[-]"),
    "RESOLVED":    (GREEN,  "[+]"),
    "SKIPPED":     (DIM,    "[ ]"),
    "PENDING":     (DIM,    "[ ]"),
    "WARNING":     (RED,    "[!]"),
}

def fmt(status_key, label=None):
    color, symbol = _STATUS_MAP.get(status_key, ("", f"[{status_key}]"))
    text = label if label else status_key
    return f"{color}{symbol} {text}{RESET}"


def compute_affordability(state):

    from core.dashboard import compute_dashboard

    data     = compute_dashboard(state)
    total_sp = data["total_passes"]
    luck     = state.get("luck", {})
    pity     = state.get("pity", {})

    global_char_pity      = pity.get("char", {}).get("count",      0)
    global_char_guaranteed = pity.get("char", {}).get("guaranteed", False)
    global_lc_pity        = pity.get("lc",   {}).get("count",      0)
    global_lc_guaranteed  = pity.get("lc",   {}).get("guaranteed", False)

    sorted_priority = get_sorted_priority(state)

    pool_high = total_sp
    pool_low  = total_sp

    char_results = []
    lc_results   = []
    first_pending_char = True
    first_pending_lc   = True

    for name, entry in sorted_priority:

        char_result = entry.get("char_result")
        lc_result   = entry.get("lc_result")

        # Use global pity only for the first unresolved character
        if char_result not in ("won", "lost", "skip") and first_pending_char:
            cp = global_char_pity
            cg = global_char_guaranteed
            first_pending_char = False
        else:
            cp, cg = 0, False

        if lc_result not in ("won", "lost", "skip") and first_pending_lc:
            lp = global_lc_pity
            lg = global_lc_guaranteed
            first_pending_lc = False
        else:
            lp, lg = 0, False

        floors = compute_floors(luck, cp, cg, lp, lg)

        # -------------------------
        # CHAR
        # -------------------------
        if char_result == "skip":
            char_results.append(_make_result(name, "SKIPPED", 0, 0, 0, 0))

        elif char_result in ("won", "lost"):
            spent = entry.get("char_spent") or 0
            pool_high -= spent
            pool_low  -= spent
            char_results.append(_make_result(
                name, "RESOLVED",
                floors["char_high"], floors["char_low"],
                pool_high, pool_low,
                spent=spent, result=char_result
            ))

        else:
            sh, sl = _afford_status(pool_high, pool_low, floors["char_high"], floors["char_low"])
            char_results.append(_make_result(
                name, _combined(sh, sl),
                floors["char_high"], floors["char_low"],
                pool_high, pool_low,
                status_high=sh, status_low=sl
            ))
            pool_high -= floors["char_high"]
            pool_low  -= floors["char_low"]

        # -------------------------
        # LC
        # -------------------------
        if lc_result == "skip":
            lc_results.append(_make_result(name, "SKIPPED", 0, 0, 0, 0))
            continue

        if lc_result in ("won", "lost"):
            spent_lc = entry.get("lc_spent") or 0
            pool_high -= spent_lc
            pool_low  -= spent_lc
            lc_results.append(_make_result(
                name, "RESOLVED",
                floors["lc_high"], floors["lc_low"],
                pool_high, pool_low,
                spent=spent_lc, result=lc_result
            ))

        else:
            if char_result == "lost":
                lc_results.append(_make_result(
                    name, "BLOCKED",
                    floors["lc_high"], floors["lc_low"],
                    pool_high, pool_low,
                    note="Lost char 50/50 — skip LC"
                ))
                continue

            sh, sl = _afford_status(pool_high, pool_low, floors["lc_high"], floors["lc_low"])
            lc_results.append(_make_result(
                name, _combined(sh, sl),
                floors["lc_high"], floors["lc_low"],
                pool_high, pool_low,
                status_high=sh, status_low=sl
            ))
            pool_high -= floors["lc_high"]
            pool_low  -= floors["lc_low"]

    all_items = char_results + lc_results
    statuses  = [r["status"] for r in all_items if r["status"] not in ("SKIPPED", "RESOLVED")]

    if not statuses or all(s == "SAFE" for s in statuses):
        risk = "CONTROLLED"
    elif any(s == "BLOCKED" for s in statuses):
        risk = "HIGH"
    else:
        risk = "ELEVATED"

    return {
        "total_sp":     total_sp,
        "char_results": char_results,
        "lc_results":   lc_results,
        "pool_high":    pool_high,
        "pool_low":     pool_low,
        "risk":         risk,
    }


def _afford_status(ph, pl, ch, cl):
    return ("SAFE" if ph >= ch else "BLOCKED"), ("SAFE" if pl >= cl else "BLOCKED")

def _combined(sh, sl):
    if sh == "SAFE":    return "SAFE"
    if sl == "SAFE":    return "CONDITIONAL"
    return "BLOCKED"

def _make_result(name, status, cost_high, cost_low, pool_high, pool_low,
                 status_high=None, status_low=None,
                 spent=None, result=None, note=None):
    return {
        "name":        name,
        "status":      status,
        "status_high": status_high or status,
        "status_low":  status_low  or status,
        "cost_high":   cost_high,
        "cost_low":    cost_low,
        "pool_high":   pool_high,
        "pool_low":    pool_low,
        "spent":       spent,
        "result":      result,
        "note":        note,
    }
