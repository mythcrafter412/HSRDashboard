from core.utils import display
from rendering.registry import register_view

GREEN  = "\033[92m"
RED    = "\033[91m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def _entry_line(index, entry, running_total=None):
    result = entry.get("result")
    pity   = entry.get("pity", 0)
    spent  = entry.get("spent")
    name   = entry.get("name")
    spent_str = f"{spent} SP" if spent is not None else "? SP"
    name_str  = f"{display(name):<18}  " if name else ""
    total_str = f"  ({running_total} pulls total)" if running_total is not None else ""

    if result == "won" and entry.get("via_guarantee"):
        total = entry.get("total_spent")
        cycle_total_str = f"{total} SP" if total is not None else "? SP"
        return (f"  {index:>2}. {name_str}{GREEN}WON (guarantee){RESET}   "
                f"pity: {pity:>2}  spent: {spent_str}  cycle total: {cycle_total_str}{total_str}")

    if result == "won":
        return (f"  {index:>2}. {name_str}{GREEN}WON{RESET}               "
                f"pity: {pity:>2}  spent: {spent_str}{total_str}")

    if result == "lost":
        lost_to  = entry.get("lost_to")
        lost_str = f"  lost to: {display(lost_to)}" if lost_to else ""
        status   = (f"{DIM}[resolved]{RESET}" if entry.get("linked")
                    else f"{DIM}[pending guarantee]{RESET}")
        return (f"  {index:>2}. {name_str}{RED}LOST{RESET}              "
                f"pity: {pity:>2}  spent: {spent_str}{lost_str}  {status}{total_str}")

    if result == "skip":
        return (f"  {index:>2}. {name_str}{DIM}ABANDONED{RESET}        "
                f"pity: {pity:>2}  spent: {spent_str}  {DIM}[not counted toward avg]{RESET}{total_str}")

    return f"  {index:>2}. {name_str}{result}{total_str}"


def _render_section(title, entries, luck, streak_key, loss_streak_key, avg_key, rate_key):
    lines = [f"// {title}", "-" * 50]

    if not entries:
        lines.append("No history recorded yet.")
        lines.append("")
        return lines

    # Running total — every pull actually spent counts here (including
    # abandoned/skipped attempts), unlike avg_pulls which only counts pulls
    # that ended in an actual 5-star. Only accumulates across BACK-TO-BACK
    # entries for the same character (e.g. a loss immediately followed by
    # its guarantee, or repeated eidolon copies pulled in a row) — it resets
    # the moment a different character's entry appears in between, since a
    # later attempt (a different banner, versions later) isn't a continuation
    # of the earlier one even if it's the same character again.
    run_name  = None
    run_total = 0
    run_count = 0

    for i, entry in enumerate(entries, start=1):
        name  = entry.get("name")
        spent = entry.get("spent") or 0

        if name and name == run_name:
            run_total += spent
            run_count += 1
        else:
            run_name  = name
            run_total = spent
            run_count = 1

        running_total = run_total if (name and run_count > 1) else None
        lines.append(_entry_line(i, entry, running_total))

    lines.append("-" * 50)
    lines.append(f"  Win streak : {luck.get(streak_key, 0)}")
    lines.append(f"  Loss streak: {luck.get(loss_streak_key, 0)}")
    lines.append(f"  Win rate   : {luck.get(rate_key, 0)}%")
    lines.append(f"  Avg spent  : {luck.get(avg_key, 0)} SP")
    lines.append("")
    return lines


def render_pull_history(state):
    history = state.get("pull_history", {})
    luck    = state.get("luck", {})

    lines = ["// PULL HISTORY", "=" * 50, ""]

    lines += _render_section(
        "Characters", history.get("char", []), luck,
        "char_streak", "loss_char_streak", "avg_pulls_char", "win_rate"
    )
    lines += _render_section(
        "Light Cones", history.get("lc", []), luck,
        "lc_streak", "loss_lc_streak", "avg_pulls_lc", "lc_win_rate"
    )

    return "\n".join(lines)


register_view("pull_history", render_pull_history)
