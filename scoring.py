"""Site scoring and deal-killer narrative assessment.

Two outputs:
1. Weighted average score (1-5) for the report card -- simple, transparent
2. Deal-killer narrative -- identifies the specific things that could stop
   a project, with evidence and reasoning, not probabilities

The quantitative scoring from the Cursor refactor is archived in
archive/cursor_scoring/scoring.py. That approach is useful for thinking
about which factors matter and how tenant profiles affect risk, but the
numeric probabilities (P=0.25, tenant_scale=0.75) create false precision.
The deal-killer framework is preserved here as narrative flags.

See archive/cursor_scoring/docs/screen_methodology/ for the detailed
thinking on each factor -- those docs remain the best reference for
HOW to evaluate each risk, even though we don't quantify them.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Deal-killer identification (narrative, not numeric)
# ---------------------------------------------------------------------------

def identify_deal_killers(ctx: dict) -> list[dict]:
    """Identify factors that could independently kill this project.

    Returns a list of dicts with: name, category, severity, evidence, reasoning.
    Severity is "critical" (likely project-ending), "major" (significant obstacle),
    or "watch" (needs monitoring but probably manageable).
    """
    killers = []

    # 1. Active moratorium
    tariffs = ctx.get("dc_tariffs", [])
    for t in tariffs:
        if t.get("moratorium"):
            killers.append({
                "name": "Active moratorium",
                "category": "regulatory",
                "severity": "critical",
                "evidence": f"{t['utility_name']}: {t.get('notes', '')}",
                "reasoning": "Active moratoriums prevent new DC interconnections entirely. Project cannot proceed until lifted.",
            })

    moratoriums = ctx.get("regulatory_moratoriums", [])
    for m in moratoriums:
        killers.append({
            "name": f"Regulatory pause: {m.get('utility', m.get('state', ''))}",
            "category": "regulatory",
            "severity": "critical",
            "evidence": m.get("notes", ""),
            "reasoning": "PSC/PUC-level interconnection pause blocks new large load service.",
        })

    # 2. Grid severely insufficient
    grid = ctx.get("grid_assessment", {})
    target_mw = ctx.get("target_mw")
    if target_mw and grid.get("max_mw", 0) > 0:
        ratio = grid["max_mw"] / target_mw
        if ratio < 0.25:
            killers.append({
                "name": "Grid severely insufficient",
                "category": "grid",
                "severity": "critical",
                "evidence": f"Estimated grid capacity ~{grid['max_mw']} MW vs target {target_mw} MW ({ratio:.0%} coverage)",
                "reasoning": "Would require major new transmission infrastructure. Multi-year timeline and hundreds of millions in grid investment.",
            })
        elif ratio < 0.5:
            killers.append({
                "name": "Grid upgrade needed",
                "category": "grid",
                "severity": "major",
                "evidence": f"Estimated grid capacity ~{grid['max_mw']} MW vs target {target_mw} MW ({ratio:.0%} coverage)",
                "reasoning": "Significant grid upgrades required but potentially feasible if utility and RTO are cooperative.",
            })

    # 3. No transmission within range
    lines = ctx.get("transmission_lines", [])
    if not lines:
        killers.append({
            "name": "No transmission infrastructure",
            "category": "grid",
            "severity": "critical",
            "evidence": "No transmission lines found within search radius",
            "reasoning": "Site has no access to high-voltage transmission. Complete grid build-out required.",
        })

    # 4. Flood zone
    flood = ctx.get("flood_zones", [])
    if flood and flood[0].get("flood_zone", "").startswith(("A", "V")):
        killers.append({
            "name": "FEMA high-risk flood zone",
            "category": "environmental",
            "severity": "major",
            "evidence": f"Flood zone {flood[0]['flood_zone']}",
            "reasoning": "Mandatory flood insurance, elevated construction, potential deal-killer for lenders and insurers.",
        })

    # 5. Nonattainment zone (for large facilities with generators)
    naaqs = ctx.get("nonattainment_zones", [])
    if naaqs and target_mw and target_mw >= 100:
        pollutants = [n.get("pollutant", "") for n in naaqs]
        classifications = [n.get("classification", "") for n in naaqs]
        severity = "major" if any(c in ("Serious", "Severe", "Extreme") for c in classifications) else "watch"
        killers.append({
            "name": "Air quality nonattainment zone",
            "category": "environmental",
            "severity": severity,
            "evidence": f"Nonattainment for: {', '.join(pollutants)}. Classifications: {', '.join(classifications)}",
            "reasoning": "Backup generators require stricter permitting (BACT/LAER). May need emission offsets. Adds 6-18 months to timeline.",
        })

    # 6. Onerous tariff deposits
    for t in tariffs:
        if t.get("deposit_onerous"):
            killers.append({
                "name": "Onerous tariff deposits",
                "category": "financial",
                "severity": "major",
                "evidence": f"{t['utility_name']}: {t.get('collateral_desc', '')}",
                "reasoning": "Large upfront collateral requirement strains project finance. May be manageable for well-capitalized developers but can kill speculative projects.",
            })

    # 7. Justice40 community
    j40 = ctx.get("justice40")
    if j40 and j40.get("is_disadvantaged"):
        killers.append({
            "name": "Justice40 disadvantaged community",
            "category": "community",
            "severity": "watch",
            "evidence": f"Census tract {j40.get('tract_id', 'N/A')}. Diesel PM: {j40.get('diesel_pm_pct', 'N/A')} pct, Low income: {j40.get('low_income_pct', 'N/A')} pct",
            "reasoning": "Regulatory agencies increasingly require EJ analysis and community engagement. Risk of organized opposition and permitting delays.",
        })

    # 8. Extreme remoteness
    fiber = ctx.get("fiber_routes", [])
    water = ctx.get("water_facilities", [])
    highways = ctx.get("highways", [])
    remote_count = sum([
        not fiber or fiber[0].get("dist_km", 999) > 30,
        not water or water[0].get("dist_km", 999) > 30,
        not highways or highways[0].get("dist_km", 999) > 30,
    ])
    if remote_count >= 3:
        killers.append({
            "name": "Extreme remoteness",
            "category": "infrastructure",
            "severity": "major",
            "evidence": f"No fiber, water, or highway access within 30 km",
            "reasoning": "All supporting infrastructure must be built from scratch. Adds $50-100M+ in non-power costs and significant timeline risk.",
        })

    # 9. High seismic (SDC D+)
    seismic = ctx.get("seismic")
    if seismic and seismic.get("seismic_design_category") in ("D", "E", "F"):
        killers.append({
            "name": "High seismic zone",
            "category": "environmental",
            "severity": "watch",
            "evidence": f"SDC {seismic['seismic_design_category']}, PGA {seismic.get('pga', 'N/A')}g",
            "reasoning": "10-25% construction cost premium for seismic design. Not a deal-killer but materially impacts project economics.",
        })

    # 10. Brownfield opportunity (positive signal)
    brownfield = ctx.get("brownfield_interconnection", [])
    if brownfield:
        bf = brownfield[0]
        killers.append({
            "name": "Brownfield interconnection opportunity",
            "category": "grid",
            "severity": "positive",
            "evidence": f"Retired generation site within {bf.get('dist_km', '?')} km: {bf.get('name', 'N/A')}",
            "reasoning": "Retired plant switchyard and HV lines may provide ready-made interconnection point. Significant development advantage.",
        })

    return killers


# ---------------------------------------------------------------------------
# Grid outlook (qualitative, from Cursor's methodology docs)
# ---------------------------------------------------------------------------

def grid_outlook(ctx: dict) -> dict:
    """Qualitative grid outlook: promising, neutral, or doubtful.

    Uses the thinking from archive/cursor_scoring/docs/screen_methodology/
    grid_severely_insufficient.md but returns a narrative verdict rather
    than a numeric probability.
    """
    lines = ctx.get("transmission_lines", [])
    subs = ctx.get("substations", [])
    planned = ctx.get("planned_substations", [])
    nearby_dcs = ctx.get("nearby_dcs", [])
    target_mw = ctx.get("target_mw")

    if not lines:
        return {"verdict": "doubtful", "reasoning": "No transmission lines within search radius."}

    best = lines[0]
    best_vc = best.get("volt_class", "")
    best_dist = best.get("dist_km", 999)

    hv_classes = {"735 AND ABOVE", "DC", "500", "345"}
    has_hv = any(l.get("volt_class") in hv_classes for l in lines)
    hv_nearby = any(l.get("volt_class") in hv_classes and l.get("dist_km", 999) <= 15 for l in lines)

    # Cluster signal: existing DCs nearby = utility has track record
    active_dcs = [d for d in nearby_dcs if d.get("dist_km", 999) <= 50]
    has_cluster = len(active_dcs) >= 5

    # Planned buildout nearby = grid is being upgraded
    has_planned = len(planned) >= 3

    if hv_nearby and (has_cluster or has_planned):
        verdict = "promising"
        reasoning = f"High-voltage transmission ({best_vc} at {best_dist:.0f} km)"
        if has_cluster:
            reasoning += f", active DC cluster ({len(active_dcs)} facilities within 50 km)"
        if has_planned:
            reasoning += f", {len(planned)} planned substation upgrades within 150 km"
    elif has_hv:
        verdict = "neutral"
        reasoning = f"High-voltage access available ({best_vc} at {best_dist:.0f} km) but "
        if not has_cluster:
            reasoning += "no established DC market nearby"
        if not has_planned:
            reasoning += ", limited planned grid buildout"
    else:
        verdict = "doubtful"
        reasoning = f"Highest voltage: {best_vc} at {best_dist:.0f} km. No 345kV+ transmission within range."
        if target_mw and target_mw > 100:
            reasoning += f" Insufficient for {target_mw} MW target."

    return {"verdict": verdict, "reasoning": reasoning}


# ---------------------------------------------------------------------------
# Feasibility narrative (replaces numeric feasibility score)
# ---------------------------------------------------------------------------

def compute_feasibility(ctx: dict, scores: dict) -> dict:
    """Produce a feasibility assessment with narrative, not a number.

    Returns dict with: rating, headline, killers, outlook, strengths.
    """
    killers = identify_deal_killers(ctx)
    outlook = grid_outlook(ctx)

    critical = [k for k in killers if k["severity"] == "critical"]
    major = [k for k in killers if k["severity"] == "major"]
    positive = [k for k in killers if k["severity"] == "positive"]

    # Simple rating based on killer count
    if critical:
        rating = "Not Feasible"
        headline = f"{len(critical)} critical obstacle(s) identified that would likely prevent development."
    elif len(major) >= 3:
        rating = "Challenging"
        headline = f"No critical blockers but {len(major)} major obstacles require resolution."
    elif major:
        rating = "Feasible with Conditions"
        headline = f"{len(major)} major obstacle(s) to address but development path exists."
    else:
        rating = "Feasible"
        headline = "No critical or major obstacles identified. Standard development pathway."

    # Identify strengths
    strengths = []
    if outlook["verdict"] == "promising":
        strengths.append(f"Grid outlook: {outlook['reasoning']}")
    inc = ctx.get("tax_incentives")
    if inc:
        n_types = sum([inc.get("sales_tax", False), inc.get("property_tax", False), inc.get("income_tax", False)])
        if n_types >= 2:
            strengths.append(f"State tax incentives: {n_types} types available ({inc.get('duration_years', '?')} year duration)")
    if positive:
        for p in positive:
            strengths.append(f"{p['name']}: {p['evidence']}")

    return {
        "rating": rating,
        "headline": headline,
        "killers": killers,
        "critical_count": len(critical),
        "major_count": len(major),
        "outlook": outlook,
        "strengths": strengths,
    }
