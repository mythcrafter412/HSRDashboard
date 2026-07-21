from engine.debug import trace


def validate(command, state):

    trace(state, "VALIDATOR", f"input: {command}")

    if not command:
        return False, "Empty command"

    action    = command.get("action", "").lower()
    subdomain = (command.get("subdomain") or "").lower()
    payload   = command.get("payload", {})

    if action in ("help", "exit"):
        return True, "OK"

    if action == "debug":
        if payload.get("target") not in ["file", "terminal"]:
            return False, "Use 'debug file enable/disable' or 'debug terminal enable/disable'"
        if payload.get("enabled") not in [True, False]:
            return False, "Use enable or disable"
        return True, "OK"

    if action == "open":
        if not command.get("view", "").strip():
            return False, "Open requires a view name"
        return True, "OK"

    # -------------------------
    # PULLS
    # -------------------------
    if action in ("set", "add", "subtract") and subdomain == "pulls":
        if "sj" not in payload or "sp" not in payload:
            return False, "Missing SJ or SP"
        try:
            int(payload["sj"]); int(payload["sp"])
        except (ValueError, TypeError):
            return False, "SJ and SP must be numbers"
        return True, "OK"

    # -------------------------
    # FUTURE VERSION
    # -------------------------
    if action == "add" and subdomain == "future":
        if not payload.get("version"):
            return False, "Missing version"
        for key in ["sj", "sp"]:
            val = payload.get(key, "*")
            if val != "*":
                try:
                    int(val)
                except (ValueError, TypeError):
                    return False, f"{key.upper()} must be a number or *"
        return True, "OK"

    if action == "remove" and subdomain == "future":
        if not payload.get("version"):
            return False, "Missing version"
        return True, "OK"

    if action == "set" and subdomain == "future_field":
        if not payload.get("version"):
            return False, "Missing version"
        if payload.get("field") not in ["sj", "sp", "characters", "notes"]:
            return False, "Field must be: sj, sp, characters, or notes"
        if not payload.get("value") and payload.get("field") != "characters":
            return False, "Missing value"
        if payload["field"] in ["sj", "sp"]:
            val = payload.get("value", "*")
            if val != "*":
                try:
                    int(val)
                except (ValueError, TypeError):
                    return False, f"{payload['field'].upper()} must be a number or *"
        return True, "OK"

    # -------------------------
    # LUCK
    # -------------------------
    if action == "set" and subdomain == "luck":
        if payload.get("field") not in ["charpulls", "lcpulls", "winrate",
                                         "lcrate", "charstreak", "lcstreak"]:
            return False, "Unknown luck field — use: charpulls lcpulls winrate lcrate charstreak lcstreak"
        try:
            float(payload["value"])
        except (ValueError, TypeError, KeyError):
            return False, "Value must be numeric"
        return True, "OK"

    # -------------------------
    # PITY
    # -------------------------
    if action == "set" and subdomain == "pity":
        if payload.get("banner") not in ["char", "lc"]:
            return False, "Banner must be 'char' or 'lc'"
        count = payload.get("count")
        if count is not None:
            try:
                c = int(count)
            except (ValueError, TypeError):
                return False, "Count must be a number"
            limit = 90 if payload["banner"] == "char" else 80
            if c < 0 or c >= limit:
                return False, f"Pity count must be 0–{limit - 1}"
        if payload.get("guaranteed") is not None:
            if payload["guaranteed"] not in [True, False]:
                return False, "guaranteed must be true or false"
        return True, "OK"

    # -------------------------
    # CLAIMABLES
    # -------------------------
    if action == "add" and subdomain == "claimable":
        if not payload.get("name"):
            return False, "Missing name"
        if "sj" not in payload or "sp" not in payload:
            return False, "Missing SJ or SP"
        try:
            int(payload["sj"]); int(payload["sp"])
        except (ValueError, TypeError):
            return False, "SJ/SP must be numbers"
        return True, "OK"

    if action == "set" and subdomain == "claimable_field":
        if not payload.get("name"):
            return False, "Missing name"
        field = payload.get("field")
        if field not in ["sj", "sp", "name", "abbr", "count"]:
            return False, f"Unknown field '{field}' — use: sj sp name abbr count"
        if field in ["sj", "sp"]:
            try:
                int(payload["value"])
            except (ValueError, TypeError, KeyError):
                return False, f"{field.upper()} must be a number"
        if field in ["name", "abbr"] and not payload.get("value"):
            return False, f"Missing new {field}"
        if field == "count":
            try:
                int(payload["count_completed"]); int(payload["count_total"])
            except (ValueError, TypeError, KeyError):
                return False, "count requires two numbers: <completed> <total>"
        return True, "OK"

    if action == "subtract" and subdomain == "claimable":
        if not payload.get("name"):
            return False, "Missing name"
        try:
            int(payload["sj"]); int(payload["sp"])
        except (ValueError, TypeError, KeyError):
            return False, "SJ/SP must be numbers"
        return True, "OK"

    if action == "remove" and subdomain == "claimable":
        if not payload.get("name"):
            return False, "Missing name"
        return True, "OK"

    # -------------------------
    # PRIORITY
    # -------------------------
    if action == "add" and subdomain == "priority":
        if not payload.get("name"):
            return False, "Missing name"
        try:
            new_order = int(payload["order"])
        except (ValueError, TypeError, KeyError):
            return False, "Order must be a number"
        if new_order < 1:
            return False, "Order must be 1 or greater"
        if payload.get("type") not in ["char", "lc", "both"]:
            return False, "Type must be 'char', 'lc', or 'both'"
        return True, "OK"

    if action == "remove" and subdomain == "priority":
        if not payload.get("name"):
            return False, "Missing name"
        return True, "OK"

    if action == "set" and subdomain == "priority_order":
        if not payload.get("name"):
            return False, "Missing name"
        if payload["name"] not in state.get("priority", {}):
            return False, f"'{payload['name']}' is not in the priority list"
        try:
            new_order = int(payload["order"])
        except (ValueError, TypeError, KeyError):
            return False, "Order must be a number"
        if new_order < 1:
            return False, "Order must be 1 or greater"
        return True, "OK"

    if action == "set" and subdomain == "priority_type":
        if not payload.get("name"):
            return False, "Missing name"
        if payload.get("type") not in ["char", "lc", "both"]:
            return False, "Type must be 'char', 'lc', or 'both'"
        return True, "OK"

    if action == "set" and subdomain == "priority_eidolon":
        if not payload.get("name"):
            return False, "Missing name"
        try:
            e = int(payload["eidolon"])
        except (ValueError, TypeError, KeyError):
            return False, "Eidolon must be a number"
        if e < 0 or e > 6:
            return False, "Eidolon must be 0-6"
        return True, "OK"

    if action == "set" and subdomain == "priority_superimposition":
        if not payload.get("name"):
            return False, "Missing name"
        try:
            s = int(payload["superimposition"])
        except (ValueError, TypeError, KeyError):
            return False, "Superimposition must be a number"
        if s < 1 or s > 5:
            return False, "Superimposition must be 1-5"
        return True, "OK"

    if action == "set" and subdomain in ("priority_char_result", "priority_lc_result"):
        if not payload.get("name"):
            return False, "Missing name"
        if payload.get("result") not in ["won", "lost", "skip"]:
            return False, "Result must be 'won', 'lost', or 'skip'"
        if payload.get("spent") is not None:
            try:
                int(payload["spent"])
            except (ValueError, TypeError):
                return False, "Spent must be a number"
        return True, "OK"

    # -------------------------
    # UNKNOWN
    # -------------------------
    return False, f"Unknown command: {action} / {subdomain}"
