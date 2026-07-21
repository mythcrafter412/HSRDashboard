from core.utils import display
from rendering.registry import register_view

GREEN  = "\033[92m"
RED    = "\033[91m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def _entry_line(index, entry):
    result = entry.get("result")
    pity   = entry.get("pity", 0)
    spent  = entry.get("spent")
    name   = entry.get("name")
    spent_str = f"{spent} SP" if spent is not None else "? SP"
    name_str  = f"{display(name):<18}  " if name else ""

    if result == "won" and entry.get("via_guarantee"):
        total = entry.get("total_spent")
        total_str = f"{total} SP" if total is not None else "? SP"
        return (f"  {index:>2}. {name_str}{GREEN}WON (guarantee){RESET}   "
                f"pity: {pity:>2}  spent: {spent_str}  cycle total: {total_str}")

    if result == "won":
        return f"  {index:>2}. {name_str}{GREEN}WON{RESET}               pity: {pity:>2}  spent: {spent_str}"

    if result == "lost":
        lost_to  = entry.get("lost_to")
        lost_str = f"  lost to: {display(lost_to)}" if lost_to else ""
        status   = (f"{DIM}[resolved]{RESET}" if entry.get("linked")
                    else f"{DIM}[pending guarantee]{RESET}")
        return (f"  {index:>2}. {name_str}{RED}LOST{RESET}              "
                f"pity: {pity:>2}  spent: {spent_str}{lost_str}  {status}")

    return f"  {index:>2}. {name_str}{result}"


def _render_section(title, entries, luck, streak_key, loss_streak_key, avg_key, rate_key):
    lines = [f"// {title}", "-" * 50]

    if not entries:
        lines.append("No history recorded yet.")
        lines.append("")
        return lines

    for i, entry in enumerate(entries, start=1):
        lines.append(_entry_line(i, entry))

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
