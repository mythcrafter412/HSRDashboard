from core.claimables import compute_claimables
from core.utils import display
from rendering.registry import register_view


def render_claimables(state):

    data       = compute_claimables(state)
    claimables = state.get("claimables", {})

    lines = []
    lines.append("// CLAIMABLES VIEW")
    lines.append("=" * 40)
    lines.append("")
    lines.append("// Breakdown")

    if not claimables:
        lines.append("No claimables available.")
        return "\n".join(lines)

    for name, item in claimables.items():

        sj        = item.get("sj", 0)
        sp        = item.get("sp", 0)
        abbr      = item.get("abbreviation", "")
        permanent = item.get("permanent", False)
        perm_tag  = "  [permanent]" if permanent else ""

        lines.append(f"{display(name)} ({abbr}){perm_tag}")

        if "count_completed" in item and "count_total" in item:
            completed = item["count_completed"]
            total     = item["count_total"]
            remaining = total - completed
            lines.append(f"  Progress : {completed} / {total}  ({remaining} remaining)")

        lines.append(f"  SJ: {sj}  |  SP: {sp}")
        lines.append("")

    lines.append("// Totals")
    lines.append("-" * 40)
    lines.append(f"Stellar Jade       : {data.get('total_claim_sj', 0)}")
    lines.append(f"Special Passes     : {data.get('total_claim_sp', 0)}")
    lines.append(f"Converted SJ total : {data.get('claim_converted_total_sj', 0)}")
    lines.append(f"Converted SP total : {data.get('claim_converted_total_sp', 0)}")
    lines.append("")

    return "\n".join(lines)


register_view("claimables", render_claimables)
