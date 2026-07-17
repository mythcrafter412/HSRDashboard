from core.dashboard import compute_dashboard
from core.priority import get_sorted_priority, compute_floors
from core.rules import compute_affordability, fmt
from core.utils import display, display_list
from rendering.registry import register_view


def render_dashboard(state):

    data   = compute_dashboard(state)
    afford = compute_affordability(state)
    luck   = state.get("luck", {})
    pity   = state.get("pity", {})
    fv     = state.get("future_versions", {})

    lines = []
    lines.append("// DASHBOARD")
    lines.append("=" * 44)
    lines.append("")

    # -------------------------
    # BASE STATE
    # -------------------------
    lines.append("// Base State")
    lines.append(f"Stellar Jade  : {data['pulls_sj']}")
    lines.append(f"Special Passes: {data['pulls_sp']}")
    lines.append(f"Converted     : {data['pulls_conv_sj']} SJ  ({data['pulls_conv_sp']} SP)")
    lines.append("")

    # -------------------------
    # PITY  (global, shared across all limited banners)
    # -------------------------
    char_p    = pity.get("char", {})
    lc_p      = pity.get("lc",   {})
    char_guar = "GUARANTEED" if char_p.get("guaranteed") else "fresh"
    lc_guar   = "GUARANTEED" if lc_p.get("guaranteed")   else "fresh"

    lines.append("// Pity  (shared across all limited banners)")
    lines.append(f"Char banner    : {char_p.get('count', 0)}/90  ({char_guar})")
    lines.append(f"LC banner      : {lc_p.get('count', 0)}/80  ({lc_guar})")
    lines.append("")

    # -------------------------
    # LUCK
    # -------------------------
    lines.append("// Luck")
    lines.append(f"Char avg pulls : {luck.get('avg_pulls_char', 62)}")
    lines.append(f"Char win rate  : {luck.get('win_rate', 55)}%")
    lines.append(f"Char streak    : {luck.get('char_streak', 0)}")
    lines.append(f"LC avg pulls   : {luck.get('avg_pulls_lc', 50)}")
    lines.append(f"LC win rate    : {luck.get('lc_win_rate', 75)}%")
    lines.append(f"LC streak      : {luck.get('lc_streak', 0)}")
    lines.append("")

    # -------------------------
    # CLAIMABLE POOL
    # -------------------------
    lines.append("// Claimable Pool")
    lines.append(f"Total          : {data['claim_converted_total_sj']} SJ  ({data['claim_converted_total_sp']} SP)")
    lines.append("")

    # -------------------------
    # FUTURE VERSIONS
    # -------------------------
    lines.append("// Future Versions")
    if not fv:
        lines.append("None added.")
    else:
        for version, info in fv.items():
            lines.append(f"{version}:")
            if info.get("sj") is not None:
                lines.append(f"  - Stellar Jade  : {info['sj']}")
            if info.get("sp") is not None:
                lines.append(f"  - Special Passes: {info['sp']}")
            if info.get("characters"):
                lines.append(f"  - Characters    : {display_list(info['characters'])}")
            lines.append(f"  - Notes         : {info.get('notes', 'N/A')}")
    lines.append("")

    # -------------------------
    # TOTALS
    # -------------------------
    lines.append("// Total Available")
    lines.append(f"Stellar Jade  : {data['total_jade']}")
    lines.append(f"Special Passes: {data['total_passes']}")
    lines.append("")

    # -------------------------
    # CHARACTER PULL PRIORITY
    # -------------------------
    sorted_priority = get_sorted_priority(state)
    global_cp = pity.get("char", {}).get("count", 0)
    global_cg = pity.get("char", {}).get("guaranteed", False)
    global_lp = pity.get("lc",   {}).get("count", 0)
    global_lg = pity.get("lc",   {}).get("guaranteed", False)

    lines.append("// Character Pull Priority")
    lines.append("-" * 44)

    if not sorted_priority:
        lines.append("No characters in priority list.")
    else:
        total_char_high = 0
        total_char_low  = 0
        first_pending   = True

        for name, entry in sorted_priority:
            order  = entry.get("order", "?")
            result = entry.get("char_result")
            spent  = entry.get("char_spent")

            if result not in ("won", "lost", "skip") and first_pending:
                floors = compute_floors(luck, global_cp, global_cg, global_lp, global_lg)
                pity_str = f"pity: {global_cp}/90  {global_cg and 'GUARANTEED' or 'fresh'}"
                first_pending = False
            else:
                floors = compute_floors(luck)
                pity_str = "pity: 0/90  fresh"

            if result in ("won", "lost"):
                s = f"spent: {spent} SP" if spent else "spent: ?"
                lines.append(f"{order}. {display(name):<18}  RESOLVED  ({s} — 50/50: {result})")
                total_char_high += spent or 0
                total_char_low  += spent or 0
            elif result == "skip":
                lines.append(f"{order}. {display(name):<18}  [ ] SKIPPED")
            else:
                lines.append(f"{order}. {display(name):<18}  high: {floors['char_high']:>3} SP  low: {floors['char_low']:>3} SP    [{pity_str}]")
                total_char_high += floors["char_high"]
                total_char_low  += floors["char_low"]

        lines.append("-" * 44)
        lines.append(f"   {'Total Required':<18}  high: {total_char_high:>3} SP  low: {total_char_low:>3} SP")

    lines.append("")

    # -------------------------
    # LC PULL PRIORITY
    # -------------------------
    lines.append("// LC Pull Priority")
    lines.append("-" * 44)

    if not sorted_priority:
        lines.append("No characters in priority list.")
    else:
        total_lc_high = 0
        total_lc_low  = 0
        first_pending = True

        for name, entry in sorted_priority:
            order  = entry.get("order", "?")
            result = entry.get("lc_result")
            spent  = entry.get("lc_spent")
            char_r = entry.get("char_result")

            if result not in ("won", "lost", "skip") and first_pending:
                floors = compute_floors(luck, global_cp, global_cg, global_lp, global_lg)
                pity_str = f"pity: {global_lp}/80  {global_lg and 'GUARANTEED' or 'fresh'}"
                first_pending = False
            else:
                floors = compute_floors(luck)
                pity_str = "pity: 0/80  fresh"

            lc_label = display(name) + " LC"

            if result in ("won", "lost"):
                s = f"spent: {spent} SP" if spent else "spent: ?"
                lines.append(f"{order}. {lc_label:<18}  RESOLVED  ({s} — 75/25: {result})")
                total_lc_high += spent or 0
                total_lc_low  += spent or 0
            elif result == "skip":
                lines.append(f"{order}. {lc_label:<18}  [ ] SKIPPED")
            elif char_r == "lost":
                lines.append(f"{order}. {lc_label:<18}  [-] BLOCKED  (lost char 50/50)")
            else:
                lines.append(f"{order}. {lc_label:<18}  high: {floors['lc_high']:>3} SP  low: {floors['lc_low']:>3} SP    [{pity_str}]")
                total_lc_high += floors["lc_high"]
                total_lc_low  += floors["lc_low"]

        lines.append("-" * 44)
        lines.append(f"   {'Total Required':<18}  high: {total_lc_high:>3} SP  low: {total_lc_low:>3} SP")

    lines.append("")

    # -------------------------
    # AFFORDABILITY
    # -------------------------
    lines.append("// Affordability")
    lines.append(f"\\\\  {afford['total_sp']} SP available")
    lines.append("-" * 44)
    lines.append(f"  {'Item':<22}  {'High Floor':>10}  {'Low Floor':>10}")
    lines.append("-" * 44)

    char_rows = {r["name"]: r for r in afford["char_results"]}
    lc_rows   = {r["name"]: r for r in afford["lc_results"]}

    for name, entry in sorted_priority:

        char_r = char_rows.get(name)
        lc_r   = lc_rows.get(name)

        def row_str(r):
            if not r:
                return "  —", "  —"
            s = r["status"]
            if s == "RESOLVED":
                v = f"{r['spent'] or '?'} SP (done)"
                return v, v
            if s == "SKIPPED":
                return "skipped", "skipped"
            return fmt(r["status_high"], r["status_high"]), fmt(r["status_low"], r["status_low"])

        if char_r:
            h, l = row_str(char_r)
            lines.append(f"  {display(name) + ' (char)':<22}  {h:>10}  {l:>10}")
        if lc_r:
            s = lc_r["status"]
            if s in ("SKIPPED", "BLOCKED") and lc_r.get("note"):
                lines.append(f"  {display(name) + ' LC':<22}  {fmt('BLOCKED', 'BLOCKED'):>10}  {lc_r['note']}")
            else:
                h, l = row_str(lc_r)
                lines.append(f"  {display(name) + ' LC':<22}  {h:>10}  {l:>10}")

    lines.append("-" * 44)
    lines.append(f"  {'Remaining pool':<22}  {afford['pool_high']:>10} SP  {afford['pool_low']:>10} SP")
    lines.append("")

    # -------------------------
    # RISK STATE
    # -------------------------
    lines.append("// Risk State")
    lines.append(fmt(afford["risk"], afford["risk"]))
    lines.append("")

    return "\n".join(lines)


register_view("dashboard", render_dashboard)
