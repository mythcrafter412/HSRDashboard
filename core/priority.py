CHAR_HARD_PITY = 90
LC_HARD_PITY   = 80
LC_AVG_PULLS   = 50


# -----------------------------
# CRUD
# -----------------------------

def add_priority(state, payload):

    if "priority" not in state:
        state["priority"] = {}

    name  = payload["name"]
    order = int(payload.get("order", len(state["priority"]) + 1))

    state["priority"][name] = {
        "order":       order,
        "char_result": None,
        "lc_result":   None,
        "char_spent":  None,
        "lc_spent":    None,
    }

    return state


def remove_priority(state, name):

    if name in state.get("priority", {}):
        del state["priority"][name]

    return state


def update_priority_field(state, name, field, value):

    if name in state.get("priority", {}):
        state["priority"][name][field] = value

    return state


def get_sorted_priority(state):
    priority = state.get("priority", {})
    return sorted(priority.items(), key=lambda x: x[1].get("order", 99))


# -----------------------------
# LUCK AUTO-UPDATE
# -----------------------------

def update_luck_from_history(state):
    """
    Recompute avg_pulls_char, avg_pulls_lc, win_rate, lc_win_rate
    from pull_history. Called automatically when a result is recorded.
    """
    history = state.get("pull_history", {})
    luck    = state.get("luck", {})

    char_pulls = history.get("char", [])
    lc_pulls   = history.get("lc",   [])

    if char_pulls:
        spent_list = [p["spent"] for p in char_pulls if p.get("spent") is not None]
        wins       = sum(1 for p in char_pulls if p.get("result") == "won")

        if spent_list:
            luck["avg_pulls_char"] = round(sum(spent_list) / len(spent_list), 1)
        if char_pulls:
            luck["win_rate"] = round(wins / len(char_pulls) * 100, 1)

    if lc_pulls:
        spent_list = [p["spent"] for p in lc_pulls if p.get("spent") is not None]
        wins       = sum(1 for p in lc_pulls if p.get("result") == "won")

        if spent_list:
            luck["avg_pulls_lc"] = round(sum(spent_list) / len(spent_list), 1)
        if lc_pulls:
            luck["lc_win_rate"] = round(wins / len(lc_pulls) * 100, 1)

    state["luck"] = luck
    return state


def record_char_result(state, result, spent):
    """
    Record a character pull result.
    Updates: pull_history, pity, luck (auto), streak.
    """
    pity    = state.setdefault("pity", {})
    char_p  = pity.setdefault("char", {"count": 0, "guaranteed": False})
    luck    = state.setdefault("luck", {})
    history = state.setdefault("pull_history", {"char": [], "lc": []})

    was_guaranteed = char_p.get("guaranteed", False)

    # Record in history
    if spent is not None:
        history["char"].append({"spent": spent, "result": result})
        update_luck_from_history(state)

    # Update pity and streak
    if result == "won":
        char_p["count"]      = 0
        char_p["guaranteed"] = False
        # Only increment streak on a genuine fresh 50/50 win
        if not was_guaranteed:
            luck["char_streak"] = luck.get("char_streak", 0) + 1

    elif result == "lost":
        char_p["count"]      = 0
        char_p["guaranteed"] = True
        luck["char_streak"]  = 0

    # skip: no pity or streak change


def record_lc_result(state, result, spent):
    """
    Record a light cone pull result.
    Updates: pull_history, pity, luck (auto), streak.
    """
    pity    = state.setdefault("pity", {})
    lc_p    = pity.setdefault("lc", {"count": 0, "guaranteed": False})
    luck    = state.setdefault("luck", {})
    history = state.setdefault("pull_history", {"char": [], "lc": []})

    was_guaranteed = lc_p.get("guaranteed", False)

    if spent is not None:
        history["lc"].append({"spent": spent, "result": result})
        update_luck_from_history(state)

    if result == "won":
        lc_p["count"]      = 0
        lc_p["guaranteed"] = False
        if not was_guaranteed:
            luck["lc_streak"] = luck.get("lc_streak", 0) + 1

    elif result == "lost":
        lc_p["count"]      = 0
        lc_p["guaranteed"] = True
        luck["lc_streak"]  = 0


# -----------------------------
# FLOOR CALCULATIONS
# -----------------------------

def compute_floors(luck, char_pity=0, char_guaranteed=False,
                   lc_pity=0, lc_guaranteed=False):
    """
    Returns high-floor and low-floor SP cost for char and LC.

    High floor = hard-pity worst case:
      Char fresh:      (90 - pity) + 90
      Char guaranteed: (90 - pity)
      LC fresh:        (80 - pity) + 80
      LC guaranteed:   (80 - pity)

    Low floor = blended expected case using luck stats.
    """

    avg_char = luck.get("avg_pulls_char", 62)
    avg_lc   = luck.get("avg_pulls_lc",   50)
    wr       = luck.get("win_rate",       55) / 100.0
    lc_wr    = luck.get("lc_win_rate",    75) / 100.0

    char_remaining = CHAR_HARD_PITY - char_pity
    lc_remaining   = LC_HARD_PITY   - lc_pity

    # HIGH FLOOR
    char_high = char_remaining if char_guaranteed else char_remaining + CHAR_HARD_PITY
    lc_high   = lc_remaining   if lc_guaranteed   else lc_remaining   + LC_HARD_PITY

    # LOW FLOOR
    pf_char = char_remaining / CHAR_HARD_PITY
    pf_lc   = lc_remaining   / LC_HARD_PITY

    eff_char = max(1, round(avg_char * pf_char))
    eff_lc   = max(1, round(avg_lc   * pf_lc))

    if char_guaranteed:
        char_low = eff_char
    else:
        char_low = round(wr * eff_char + (1 - wr) * 2 * eff_char)

    if lc_guaranteed:
        lc_low = eff_lc
    else:
        lc_low = round(lc_wr * eff_lc + (1 - lc_wr) * 2 * eff_lc)

    return {
        "char_high": char_high,
        "char_low":  char_low,
        "lc_high":   lc_high,
        "lc_low":    lc_low,
    }
