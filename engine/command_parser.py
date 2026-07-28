from core.utils import parse_brackets


def parse(raw_input: str):

    parts, bracket_content = parse_brackets(raw_input)

    if not parts:
        return None

    first = parts[0].lower()

    # -------------------------
    # TOP-LEVEL COMMANDS
    # -------------------------
    if first in ["help", "commands"]:
        return {"action": "help", "subdomain": None}

    if first in ["exit", "quit"]:
        return {"action": "exit", "subdomain": None}

    if first == "open":
        if len(parts) != 2:
            return None
        return {"action": "open", "view": parts[1].lower()}

    if first == "debug":
        # File logging (logs/latest.log, logs/debug.log) is always on and
        # unconditional -- only whether trace lines ALSO print live to the
        # terminal is still a toggle.
        if len(parts) != 3:
            return None
        target = parts[1].lower()
        toggle = parts[2].lower()
        if target != "terminal" or toggle not in ["enable", "disable"]:
            return None
        return {
            "action":    "debug",
            "subdomain": "debug",
            "payload":   {"enabled": toggle == "enable"}
        }

    # -------------------------
    # DASHBOARD
    # -------------------------
    if first == "dashboard":
        if len(parts) < 3:
            return None
        sub    = parts[1].lower()
        action = parts[2].lower()

        if sub == "pulls":
            if action not in ["set", "add", "subtract"] or len(parts) != 5:
                return None
            try:
                sj = int(parts[3])
                sp = int(parts[4])
            except:
                return None
            return {
                "action":    action,
                "domain":    "dashboard",
                "subdomain": "pulls",
                "payload":   {"sj": sj, "sp": sp}
            }

        if sub == "future":
            if action == "add":
                version = parts[3] if len(parts) > 3 else None
                sj      = parts[4] if len(parts) > 4 else "*"
                sp      = parts[5] if len(parts) > 5 else "*"
                chars   = bracket_content if bracket_content else None
                notes   = " ".join(parts[6:]) if len(parts) > 6 else "N/A"
                return {
                    "action":    "add",
                    "domain":    "dashboard",
                    "subdomain": "future",
                    "payload": {
                        "version":    version,
                        "sj":         sj,
                        "sp":         sp,
                        "characters": chars,
                        "notes":      notes
                    }
                }

            if action == "set":
                if len(parts) < 5:
                    return None
                version = parts[3]
                field   = parts[4].lower()
                if field not in ["sj", "sp", "characters", "notes"]:
                    return None
                if field == "characters" and bracket_content:
                    value = bracket_content
                elif len(parts) >= 6:
                    value = " ".join(parts[5:])
                else:
                    return None
                return {
                    "action":    "set",
                    "domain":    "dashboard",
                    "subdomain": "future_field",
                    "payload":   {"version": version, "field": field, "value": value}
                }

            if action == "remove":
                if len(parts) != 4:
                    return None
                return {
                    "action":    "remove",
                    "domain":    "dashboard",
                    "subdomain": "future",
                    "payload":   {"version": parts[3]}
                }

        if sub == "luck":
            if action != "set" or len(parts) != 5:
                return None
            field = parts[3].lower()
            if field not in ["charpulls", "lcpulls", "winrate", "lcrate", "charstreak", "lcstreak"]:
                return None
            try:
                value = float(parts[4]) if field in ["charpulls", "lcpulls", "winrate", "lcrate"] else int(parts[4])
            except:
                return None
            return {
                "action":    "set",
                "domain":    "dashboard",
                "subdomain": "luck",
                "payload":   {"field": field, "value": value}
            }

        if sub == "pity":
            if action != "set" or len(parts) < 4:
                return None
            banner = parts[3].lower()
            if banner not in ["char", "lc"]:
                return None
            if len(parts) == 4:
                return None

            flag_only = parts[4].lower() in ["guaranteed", "fresh"]

            if flag_only:
                guaranteed = parts[4].lower() == "guaranteed"
                return {
                    "action":    "set",
                    "domain":    "dashboard",
                    "subdomain": "pity",
                    "payload":   {"banner": banner, "count": None, "guaranteed": guaranteed}
                }

            try:
                count = int(parts[4])
            except:
                return None

            guaranteed = None
            if len(parts) >= 6:
                g = parts[5].lower()
                if g not in ["guaranteed", "fresh"]:
                    return None
                guaranteed = g == "guaranteed"

            return {
                "action":    "set",
                "domain":    "dashboard",
                "subdomain": "pity",
                "payload":   {"banner": banner, "count": count, "guaranteed": guaranteed}
            }

        return None

    # -------------------------
    # CLAIMABLES
    # -------------------------
    if first == "claimables":
        if len(parts) < 3:
            return None
        sub    = parts[1].lower()
        action = parts[2].lower()

        if sub != "claimable":
            return None

        if action == "add":
            if len(parts) not in [6, 7]:
                return None
            try:
                name = parts[3]
                sj   = int(parts[4])
                sp   = int(parts[5])
            except:
                return None
            abbr = parts[6].lower() if len(parts) == 7 else None
            return {
                "action":    "add",
                "domain":    "claimables",
                "subdomain": "claimable",
                "payload":   {"name": name, "sj": sj, "sp": sp, "abbreviation": abbr}
            }

        if action == "set":
            if len(parts) < 6:
                return None
            name  = parts[3]
            field = parts[4].lower()

            if field in ["sj", "sp"]:
                try:
                    value = int(parts[5])
                except:
                    return None
                return {
                    "action":    "set",
                    "domain":    "claimables",
                    "subdomain": "claimable_field",
                    "payload":   {"name": name, "field": field, "value": value}
                }

            if field in ["name", "abbr"]:
                return {
                    "action":    "set",
                    "domain":    "claimables",
                    "subdomain": "claimable_field",
                    "payload":   {"name": name, "field": field, "value": parts[5]}
                }

            if field == "count":
                if len(parts) < 7:
                    return None
                try:
                    completed = int(parts[5])
                    total     = int(parts[6])
                except:
                    return None
                return {
                    "action":    "set",
                    "domain":    "claimables",
                    "subdomain": "claimable_field",
                    "payload": {
                        "name": name, "field": "count",
                        "count_completed": completed, "count_total": total
                    }
                }
            return None

        if action == "subtract":
            if len(parts) != 6:
                return None
            try:
                name = parts[3]
                sj   = int(parts[4])
                sp   = int(parts[5])
            except:
                return None
            return {
                "action":    "subtract",
                "domain":    "claimables",
                "subdomain": "claimable",
                "payload":   {"name": name, "sj": sj, "sp": sp}
            }

        if action == "remove":
            if len(parts) != 4:
                return None
            return {
                "action":    "remove",
                "domain":    "claimables",
                "subdomain": "claimable",
                "payload":   {"name": parts[3]}
            }

        return None

    # -------------------------
    # PRIORITY
    # -------------------------
    if first == "priority":
        if len(parts) < 3:
            return None
        sub    = parts[1].lower()
        action = parts[2].lower()

        # priority char add <name> <order> [type]
        # type: char | lc | both  (defaults to "both")
        if sub == "char" and action == "add":
            if len(parts) not in [5, 6]:
                return None
            name = parts[3]
            try:
                order = int(parts[4])
            except:
                return None
            ptype = parts[5].lower() if len(parts) == 6 else "both"
            if ptype not in ["char", "lc", "both"]:
                return None
            return {
                "action":    "add",
                "domain":    "priority",
                "subdomain": "priority",
                "payload":   {"name": name, "order": order, "type": ptype}
            }

        # priority char remove <name>
        if sub == "char" and action == "remove":
            if len(parts) != 4:
                return None
            return {
                "action":    "remove",
                "domain":    "priority",
                "subdomain": "priority",
                "payload":   {"name": parts[3]}
            }

        # priority char set <name> <field> ...
        # priority lc set <name> <field> ...
        if action == "set":
            if len(parts) < 6:
                return None
            name  = parts[3]
            field = parts[4].lower()

            # priority char set <name> result <won|lost|skip> [spent] [lost_to]
            # priority lc set <name> result <won|lost|skip> [spent] [lost_to]
            if field == "result":
                result = parts[5].lower()
                if result not in ["won", "lost", "skip"]:
                    return None

                spent = None
                if len(parts) >= 7:
                    try:
                        spent = int(parts[6])
                    except:
                        return None

                lost_to = None
                if len(parts) >= 8 and result == "lost":
                    lost_to = parts[7]

                subdomain = "priority_char_result" if sub == "char" else "priority_lc_result"
                return {
                    "action":    "set",
                    "domain":    "priority",
                    "subdomain": subdomain,
                    "payload":   {"name": name, "result": result, "spent": spent, "lost_to": lost_to}
                }

            # priority char set <name> order <n>
            if sub == "char" and field == "order":
                try:
                    order = int(parts[5])
                except:
                    return None
                return {
                    "action":    "set",
                    "domain":    "priority",
                    "subdomain": "priority_order",
                    "payload":   {"name": name, "order": order}
                }

            # priority char set <name> type <char|lc|both>
            if sub == "char" and field == "type":
                ptype = parts[5].lower()
                if ptype not in ["char", "lc", "both"]:
                    return None
                return {
                    "action":    "set",
                    "domain":    "priority",
                    "subdomain": "priority_type",
                    "payload":   {"name": name, "type": ptype}
                }

            # priority char set <name> eidolon <0-6>
            if sub == "char" and field == "eidolon":
                try:
                    eidolon = int(parts[5])
                except:
                    return None
                if eidolon < 0 or eidolon > 6:
                    return None
                return {
                    "action":    "set",
                    "domain":    "priority",
                    "subdomain": "priority_eidolon",
                    "payload":   {"name": name, "eidolon": eidolon}
                }

            # priority char set <name> superimposition <1-5>
            if sub == "char" and field == "superimposition":
                try:
                    superimposition = int(parts[5])
                except:
                    return None
                if superimposition < 1 or superimposition > 5:
                    return None
                return {
                    "action":    "set",
                    "domain":    "priority",
                    "subdomain": "priority_superimposition",
                    "payload":   {"name": name, "superimposition": superimposition}
                }

        return None

    return None
