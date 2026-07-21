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
        "order":                  order,
        "type":                   payload.get("type", "both"),   # char | lc | both
        "target_eidolon":         payload.get("target_eidolon", 0),        # 0-6
        "target_superimposition": payload.get("target_superimposition", 1), # 1-5
        "char_result":            None,
        "lc_result":              None,
        "char_spent":             None,
        "lc_spent":               None,
    }

    reorder_priority(state, name, order)

    return state


def remove_priority(state, name):

    if name in state.get("priority", {}):
        del state["priority"][name]
        _renumber(state)

    return state


def update_priority_field(state, name, field, value):

    if name in state.get("priority", {}):
        state["priority"][name][field] = value

    return state


def set_priority_order(state, name, new_order):
    reorder_priority(state, name, new_order)
    return state


def get_sorted_priority(state):
    priority = state.get("priority", {})
    return sorted(priority.items(), key=lambda x: x[1].get("order", 99))


def _renumber(state):
    for i, (name, entry) in enumerate(get_sorted_priority(state), start=1):
        entry["order"] = i
    return state


def reorder_priority(state, name, new_order):
    """
    Move (or place a newly-added) `name` into position `new_order` (1-indexed),
    shifting every other entry to make room, then renumber everyone
    sequentially so order values never collide or leave gaps.
    """
    priority = state.get("priority", {})
    if name not in priority:
        return state

    entry  = priority[name]
    others = [(n, e) for n, e in get_sorted_priority(state) if n != name]

    new_order = max(1, min(new_order, len(others) + 1))
    others.insert(new_order - 1, (name, entry))

    for i, (n, e) in enumerate(others, start=1):
        e["order"] = i

    return state


# -----------------------------
# LUCK AUTO-UPDATE
# -----------------------------

def update_luck_from_history(state):
    """
    Recompute avg_pulls_char, avg_pulls_lc, win_rate, lc_win_rate from pull_history.

    Avg pulls = flat average of pulls-to-result (the "spent" field) across every
    event where a 5-star was actually obtained — win, loss, or guarantee-completion
    each contribute their own value independently (a loss+guarantee pair is NOT
    combined into one figure). Abandoned/skipped entries (partial pulls with no
    5-star reached) are excluded — they never got a result, so they can't
    contribute to "pulls per 5-star."

    Win rate = clean wins / (clean wins + loss-then-guarantee cycles).
    Here a loss+guarantee pair IS counted as a single cycle (denominator-only
    increase on the guarantee win) — this is a separate concern from the average.
    """
    history = state.get("pull_history", {})
    luck    = state.get("luck", {})

    for kind, avg_key, rate_key in [("char", "avg_pulls_char", "win_rate"),
                                     ("lc",   "avg_pulls_lc",   "lc_win_rate")]:

        entries = history.get(kind, [])
        if not entries:
            continue

        spents = [e["spent"] for e in entries
                  if e.get("spent") is not None and e.get("result") != "skip"]
        if spents:
            luck[avg_key] = round(sum(spents) / len(spents), 1)

        clean_wins   = 0
        total_cycles = 0

        for entry in entries:
            if entry["result"] == "won" and not entry.get("via_guarantee"):
                clean_wins   += 1
                total_cycles += 1
            elif entry.get("via_guarantee"):
                total_cycles += 1
            # "lost" entries not yet linked to a guarantee are in-progress —
            # not counted toward win rate until the guarantee resolves them

        if total_cycles:
            luck[rate_key] = round(clean_wins / total_cycles * 100, 1)

    state["luck"] = luck
    return state


def _record_result(state, kind, result, spent, lost_to=None, name=None):
    """
    Shared logic for recording a char or LC pull result.
    kind: "char" or "lc"
    """
    streak_key = "char_streak" if kind == "char" else "lc_streak"

    pity    = state.setdefault("pity", {})
    p       = pity.setdefault(kind, {"count": 0, "guaranteed": False})
    luck    = state.setdefault("luck", {})
    history = state.setdefault("pull_history", {"char": [], "lc": []})

    was_guaranteed = p.get("guaranteed", False)
    pity_at_event  = p.get("count", 0)

    if result == "skip":
        # Global pity.count/guaranteed are tracked separately (via `dashboard
        # pity`) and already carry over untouched — this never resets them.
        # If partial pulls were made toward this character before giving up,
        # log them as a bookkeeping entry so the character's historical total
        # reflects it. It's not a resolved 5-star, so it never counts toward
        # win rate or the avg-pulls-per-5-star stat (see update_luck_from_history).
        if spent is not None:
            history[kind].append({
                "result": "skip",
                "pity":   pity_at_event,
                "spent":  spent,
                "name":   name,
            })
            update_luck_from_history(state)
        return

    if result == "won":
        p["count"]      = 0
        p["guaranteed"] = False

        if was_guaranteed:
            # This win COMPLETES a loss->guarantee cycle.
            # Find the most recent unlinked "lost" entry for THIS character to
            # link to — pity/guarantee is banner-wide, but a resolved cycle
            # only makes sense tied to the character that was actually lost.
            entries = history[kind]
            linked  = False
            for entry in reversed(entries):
                if (entry["result"] == "lost" and not entry.get("linked")
                        and entry.get("name") == name):
                    entry["linked"]  = True
                    prior_spent      = entry.get("spent")
                    total_spent      = (None if (prior_spent is None or spent is None)
                                        else prior_spent + spent)
                    history[kind].append({
                        "result":        "won",
                        "pity":          pity_at_event,
                        "spent":         spent,
                        "name":          name,
                        "via_guarantee": True,
                        "total_spent":   total_spent,
                    })
                    linked = True
                    break
            if not linked:
                # Fallback: no matching loss found, log as guarantee anyway
                history[kind].append({
                    "result": "won", "pity": pity_at_event,
                    "spent": spent, "name": name, "via_guarantee": True,
                    "total_spent": spent
                })

            # Loss streak +1 (stacks), win streak resets
            luck[f"loss_{streak_key}"] = luck.get(f"loss_{streak_key}", 0) + 1
            luck[streak_key] = 0

        else:
            # Clean win
            history[kind].append({
                "result": "won", "pity": pity_at_event, "spent": spent, "name": name
            })
            luck[streak_key] = luck.get(streak_key, 0) + 1
            luck[f"loss_{streak_key}"] = 0

        update_luck_from_history(state)

    elif result == "lost":
        p["count"]      = 0
        p["guaranteed"] = True

        history[kind].append({
            "result":  "lost",
            "pity":    pity_at_event,
            "spent":   spent,
            "name":    name,
            "lost_to": lost_to,
            "linked":  False,
        })
        update_luck_from_history(state)
        # Streak isn't touched here — it only resolves once the guarantee
        # pull comes in and closes the cycle (see "won" branch above).


def record_char_result(state, result, spent, lost_to=None, name=None):
    _record_result(state, "char", result, spent, lost_to, name)


def record_lc_result(state, result, spent, lost_to=None, name=None):
    _record_result(state, "lc", result, spent, lost_to, name)


# -----------------------------
# FLOOR CALCULATIONS
# -----------------------------

def compute_floors(luck, char_pity=0, char_guaranteed=False,
                   lc_pity=0, lc_guaranteed=False,
                   target_eidolon=0, target_superimposition=1):
    """
    Returns high-floor and low-floor SP cost for char and LC,
    scaled by target Eidolon (copies = E+1) and Superimposition (copies = S).
    """

    avg_char = luck.get("avg_pulls_char", 62)
    avg_lc   = luck.get("avg_pulls_lc",   50)
    wr       = luck.get("win_rate",       55) / 100.0
    lc_wr    = luck.get("lc_win_rate",    75) / 100.0

    char_copies = target_eidolon + 1        # E0=1 copy ... E6=7 copies
    lc_copies   = max(1, target_superimposition)  # S1=1 copy ... S5=5 copies

    char_remaining = CHAR_HARD_PITY - char_pity
    lc_remaining   = LC_HARD_PITY   - lc_pity

    # HIGH FLOOR (first copy only — pity resets after)
    char_high_first = char_remaining if char_guaranteed else char_remaining + CHAR_HARD_PITY
    lc_high_first   = lc_remaining   if lc_guaranteed   else lc_remaining   + LC_HARD_PITY

    # Subsequent copies always start fresh (no pity carryover assumed)
    char_high = char_high_first + (char_copies - 1) * (CHAR_HARD_PITY * 2)
    lc_high   = lc_high_first   + (lc_copies   - 1) * (LC_HARD_PITY * 2)

    # LOW FLOOR
    pf_char = char_remaining / CHAR_HARD_PITY
    pf_lc   = lc_remaining   / LC_HARD_PITY

    eff_char = max(1, round(avg_char * pf_char))
    eff_lc   = max(1, round(avg_lc   * pf_lc))

    if char_guaranteed:
        char_low_first = eff_char
    else:
        char_low_first = round(wr * eff_char + (1 - wr) * 2 * eff_char)

    if lc_guaranteed:
        lc_low_first = eff_lc
    else:
        lc_low_first = round(lc_wr * eff_lc + (1 - lc_wr) * 2 * eff_lc)

    char_low = char_low_first + (char_copies - 1) * round(wr * avg_char + (1 - wr) * 2 * avg_char)
    lc_low   = lc_low_first   + (lc_copies   - 1) * round(lc_wr * avg_lc + (1 - lc_wr) * 2 * avg_lc)

    return {
        "char_high": char_high,
        "char_low":  char_low,
        "lc_high":   lc_high,
        "lc_low":    lc_low,
    }
