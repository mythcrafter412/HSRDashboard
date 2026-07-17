from core.claimables import compute_claimables

def compute_dashboard(state):

    pulls = state.get("pulls", {})

    # -------------------------
    # Pulls
    # -------------------------
    pulls_sj = pulls.get("sj", 0)
    pulls_sp = pulls.get("sp", 0)

    pulls_conv_sj = pulls_sj + (pulls_sp * 160)
    pulls_conv_sp = pulls_conv_sj // 160

    # -------------------------
    # Claimables (already aggregated)
    # -------------------------
    claim = compute_claimables(state)

    claim_converted_total_sj = claim["claim_converted_total_sj"]
    claim_converted_total_sp = claim["claim_converted_total_sp"]

    # -------------------------
    # Future Versions
    # -------------------------
    future_sj = 0
    future_sp = 0

    for fv in state.get("future_versions", {}).values():
        if fv.get("sj") is not None:
            future_sj += fv["sj"]
        if fv.get("sp") is not None:
            future_sp += fv["sp"]

    future_conv_sj = future_sj + (future_sp * 160)

    # -------------------------
    # TOTALS
    # -------------------------
    total_jade   = pulls_conv_sj + claim_converted_total_sj + future_conv_sj
    total_passes = total_jade // 160

    return {
        "pulls_sj": pulls_sj,
        "pulls_sp": pulls_sp,
        "pulls_conv_sj": pulls_conv_sj,
        "pulls_conv_sp": pulls_conv_sp,

        "claim_converted_total_sj": claim_converted_total_sj,
        "claim_converted_total_sp": claim_converted_total_sp,

        "future_conv_sj": future_conv_sj,
        "future_sp": future_sp,

        "total_jade":   total_jade,
        "total_passes": total_passes
    }
