"""Grid adequacy assessment based on nearby transmission infrastructure."""

VOLT_TIERS = [
    ("735 AND ABOVE", 1500, 10),
    ("DC", 1500, 10),
    ("500", 800, 10),
    ("345", 500, 15),
    ("220-287", 200, 15),
    ("100-161", 100, 10),
    ("UNDER 100", 50, 5),
    ("SUB 100", 50, 5),
]


def assess_grid(transmission_lines, substations, target_mw=None):
    """Assess grid adequacy based on nearby transmission and substations.

    Returns dict with: max_mw, confidence, narrative, upgrade_needed, score (1-5)
    """
    if not transmission_lines:
        return {
            "max_mw": 0,
            "confidence": "low",
            "narrative": "No transmission lines found within search radius. Major grid build-out required.",
            "upgrade_needed": True,
            "score": 1,
        }

    best = transmission_lines[0]
    best_vc = best.get("volt_class", "")
    best_dist = best.get("dist_km", 999)

    max_mw = 0
    for vc, mw_cap, max_dist in VOLT_TIERS:
        if best_vc == vc and best_dist <= max_dist:
            max_mw = mw_cap
            break

    # Substation proximity bonus
    sub_bonus = ""
    if substations:
        nearest_sub = substations[0]
        sub_dist = nearest_sub.get("dist_km", 999)
        if sub_dist < 5:
            max_mw = int(max_mw * 1.2)
            sub_bonus = f" Nearest substation ({nearest_sub.get('name', 'N/A')}) is {sub_dist:.1f} km away, which reduces interconnection cost."

    # Multiple high-voltage lines boost
    hv_count = sum(1 for t in transmission_lines
                   if t.get("volt_class", "") in ("500", "345", "735 AND ABOVE", "DC"))
    if hv_count >= 2:
        max_mw = int(max_mw * 1.3)

    # Score
    if target_mw and target_mw > 0:
        ratio = max_mw / target_mw
        if ratio >= 1.5:
            score = 5
        elif ratio >= 1.0:
            score = 4
        elif ratio >= 0.5:
            score = 3
        elif ratio >= 0.25:
            score = 2
        else:
            score = 1
    else:
        if max_mw >= 800:
            score = 5
        elif max_mw >= 500:
            score = 4
        elif max_mw >= 200:
            score = 3
        elif max_mw >= 50:
            score = 2
        else:
            score = 1

    upgrade_needed = target_mw is not None and max_mw < target_mw

    # Build narrative
    voltage_str = f"{best.get('voltage', 'N/A')} kV" if best.get("voltage") and best["voltage"] > 0 else best_vc
    narrative = f"Highest voltage line: {voltage_str} ({best_vc}) at {best_dist:.1f} km"
    if best.get("owner"):
        narrative += f", owned by {best['owner']}"
    narrative += f". Estimated grid capacity without major upgrades: ~{max_mw} MW."
    if best.get("sub_1"):
        subs = best["sub_1"]
        if best.get("sub_2"):
            subs += f" to {best['sub_2']}"
        narrative += f" Connecting substations: {subs}."
    narrative += sub_bonus

    if upgrade_needed:
        deficit = target_mw - max_mw
        narrative += f" Target of {target_mw} MW exceeds estimated capacity by {deficit} MW -- significant grid upgrades will be required."

    return {
        "max_mw": max_mw,
        "confidence": "medium" if best_dist < 15 else "low",
        "narrative": narrative,
        "upgrade_needed": upgrade_needed,
        "score": score,
    }
