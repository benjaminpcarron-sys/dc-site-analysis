"""Generate markdown pre-feasibility report from site analysis data."""

import re
from datetime import date

CLUSTER_OPPORTUNITY_BOOST = 0.12  # kept for report formatting backward compat


def _table(headers, rows):
    if not rows:
        return "_No data available._\n"
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines) + "\n"


def _yn(val):
    if val is True:
        return "Yes"
    if val is False:
        return "No"
    return "N/A"


def _fmt_mw(val):
    if val and val > 0:
        return f"{val:,.0f}"
    return "N/A"


def _score_bar(score):
    filled = "+" * score
    empty = "-" * (5 - score)
    return f"[{filled}{empty}]"


def _render_feasibility_by_tenant(feas_all: dict) -> list[str]:
    """Render the multi-tenant executive-summary block.

    Replaces the previous single-tenant 'Risk-Adjusted Feasibility: X' line
    with: (a) plain-English description of each tenant tier, (b) a 3-row
    feasibility table, (c) the grid outlook + power path anchors (tenant-
    independent), and (d) a deal-killer table with P-by-tenant columns + an
    interpretive paragraph for any killer where the spec/hyp spread is large.
    """
    out: list[str] = []
    by_tenant = feas_all.get("by_tenant", {})
    descriptions = feas_all.get("tenant_descriptions", {})
    opportunity = feas_all.get("opportunity", 0.0)
    triggered = feas_all.get("triggered_killers", [])
    catalog = feas_all.get("killer_catalog_size", 0)

    out.append("")
    out.append("### Feasibility by Tenant Profile")
    out.append("")
    out.append(
        "The same site has materially different economics depending on who "
        "is building. Each tier below reflects a real difference in counterparty "
        "credit, financial runway, and ability to negotiate around published "
        "tariffs. The opportunity number is identical across tiers (it depends "
        "on site fundamentals, not the buyer); only the deal-killer probabilities "
        "scale by tenant."
    )
    out.append("")

    rows = []
    for t in ("speculative", "anchored", "hyperscaler"):
        bt = by_tenant.get(t)
        if not bt:
            continue
        rows.append([
            t.capitalize(),
            f"{bt['feasibility']:.2f}",
            bt["rating"],
            f"Opp {opportunity:.2f} × (1 − Risk {bt['combined_risk']:.2f})",
        ])
    out.append(_table(["Tenant", "Feasibility", "Rating", "Math"], rows))

    out.append("**Who each tier is, in counterparty terms:**")
    out.append("")
    for t in ("speculative", "anchored", "hyperscaler"):
        desc = descriptions.get(t)
        if desc:
            out.append(f"- **{t.capitalize()}** -- {desc}")
    out.append("")

    pp = feas_all.get("power_path") or {}
    outlook = pp.get("outlook") or {}
    verdict = outlook.get("verdict")
    if verdict:
        out.append(f"**Grid Outlook: {verdict.title()}** *(tenant-independent)*  ")
        supply_ev = outlook.get("supply_signals") or []
        demand_ev = outlook.get("demand_signals") or []
        if supply_ev:
            out.append("Supply anchors:")
            for ev in supply_ev:
                out.append(f"  - {ev}")
        if demand_ev:
            out.append("Demand pressure / gaps:")
            for ev in demand_ev:
                out.append(f"  - {ev}")
        if not supply_ev and not demand_ev:
            out.append("  - No strong supply or demand signals observed (thin data).")
        out.append("")

    paths = pp.get("paths") or []
    supply_evidence_text = "\n".join(outlook.get("supply_signals") or [])
    if paths:
        path_labels = ", ".join(p["label"] for p in paths)
        out.append(f"**Power Path Anchors:** {path_labels}")
        for p in paths:
            ev = p["evidence"]
            if ev and ev in supply_evidence_text:
                # Already shown verbatim under Supply anchors; just label.
                out.append(f"  - *{p['label']}* (see supply anchor above)")
            else:
                out.append(f"  - *{p['label']}*: {ev}")
        out.append("")
    elif verdict == "doubtful":
        out.append("**Power Path Anchors:** *none identified* -- no brownfield, no cluster-grid, no BTM gas.")
        out.append("")

    boost_ev = feas_all.get("opportunity_boost_evidence")
    if boost_ev:
        import re as _re
        # Strip the "(+X.XX opportunity)" magnitude suffix before checking
        # whether the underlying evidence already appeared in supply anchors.
        magnitude_match = _re.search(r"\(\+([0-9.]+)\s*opportunity\)", boost_ev)
        magnitude = f"+{magnitude_match.group(1)} opportunity" if magnitude_match else "boost applied"
        core = _re.sub(r"\s*\(\+[0-9.]+\s*opportunity\)\s*", "", boost_ev).strip()
        if core and core in supply_evidence_text:
            out.append(f"*Opportunity boost:* {magnitude} (from supply anchor above).")
        else:
            out.append(f"*Opportunity boost:* {boost_ev}")
        out.append("")

    if triggered:
        out.append(f"**Deal-Killers Triggered ({len(triggered)} of {catalog}):**")
        killer_rows = [
            [
                tk["name"],
                tk["category"],
                f"{tk['p_by_tenant']['speculative']:.2f}",
                f"{tk['p_by_tenant']['anchored']:.2f}",
                f"{tk['p_by_tenant']['hyperscaler']:.2f}",
                tk["evidence"],
            ]
            for tk in triggered
        ]
        out.append(_table(
            ["Factor", "Category", "Spec P", "Anc P", "Hyp P", "Evidence"],
            killer_rows,
        ))

        # Where tenant scaling is materially divergent (>=3x spread between
        # speculative and hyperscaler), surface a one-line interpretation so
        # readers know WHY the gap exists. Coarse threshold avoids cluttering
        # the report when scaling is uniform or near-uniform.
        gap_notes: list[str] = []
        for tk in triggered:
            spec = tk["p_by_tenant"]["speculative"]
            hyp = tk["p_by_tenant"]["hyperscaler"]
            if spec >= 0.05 and hyp > 0 and spec / max(hyp, 0.01) >= 3.0:
                gap_notes.append(
                    f"- **{tk['name']}**: P drops {spec:.2f} -> {hyp:.2f} from spec to hyperscaler "
                    f"(scaling {tk['tenant_scaling']['speculative']:.2f} -> "
                    f"{tk['tenant_scaling']['hyperscaler']:.2f}). "
                    f"{_tenant_gap_rationale(tk['name'])}"
                )
        if gap_notes:
            out.append("**Why the tenant gap on these killers:**")
            out.append("")
            out.extend(gap_notes)
            out.append("")
        out.append("*P(kill) values are seed estimates; see `scoring.py` and `docs/screen_methodology/p_values_audit.md`.*")
    else:
        out.append("*No deal-killers triggered. Feasibility reflects opportunity factors alone.*")

    return out


def _tenant_gap_rationale(killer_name: str) -> str:
    """Plain-English explanation for why a killer's P scales steeply by tenant.

    Only reached when the spec-vs-hyperscaler spread is >=3x. Returns a short
    sentence appropriate for a footnote-style annotation.
    """
    rationales = {
        "onerous_tariff_deposit": (
            "Multi-million-dollar collateral / multi-year LOC requirements that "
            "cripple a merchant developer are parent-financed for an IG-credit "
            "hyperscaler -- the deposit is real either way, but only one tier can "
            "absorb it without disturbing capital structure."
        ),
        "regulatory_interconnection_pause": (
            "Hyperscaler planning horizons absorb 12-24 month interconnection "
            "delays as routine; merchant developers underwrite to a 24-month "
            "build window and cancel when slippage approaches that limit."
        ),
        "high_industrial_rate": (
            "Hyperscalers negotiate bilateral utility contracts (special-load "
            "tariffs, RECs-bundled deals) that materially diverge from the "
            "published industrial rate; speculative buyers pay the published rate."
        ),
        "utility_moratorium": (
            "Tariff-level moratoriums are structural, not tenant-dependent -- "
            "if scaling is firing here it's small, but hyperscalers have slightly "
            "more political/regulatory engagement to track lift timing."
        ),
    }
    return rationales.get(killer_name, "Tenant-scaling reflects credit and runway differentials.")


def generate_report(d):
    """Generate markdown report. d is a dict with all site analysis results."""
    target_mw = d.get("target_mw")
    target_str = f"{target_mw:,.0f} MW" if target_mw else "Not specified"

    lines = []
    lines.append(f"# Data Center Site Pre-Feasibility Report")
    lines.append(f"**Address:** {d['address']}")
    lines.append(f"**Coordinates:** {d['lat']:.6f} N, {d['lon']:.6f} W")
    lines.append(f"**State:** {d.get('state', 'N/A')} | **County:** {d.get('county', 'N/A')}")
    lines.append(f"**Report Date:** {date.today().isoformat()}")
    lines.append(f"**Target Capacity:** {target_str}")
    lines.append("")

    # Site Map (auto-generated by capture_map.py if DC Site Mapper is running)
    slug = re.sub(r'[^a-z0-9]+', '_', d['address'].lower()).strip('_')[:60]
    lines.append(f"![Site Map]({slug}_map.png)")
    lines.append(f"*DC Site Mapper — infrastructure layers for {d['address']}*")
    lines.append("")

    # Executive Summary
    grid = d.get("grid_assessment", {})
    score = d.get("overall_score", 0)
    rating = "Strong" if score >= 4 else "Moderate" if score >= 3 else "Challenging" if score >= 2 else "Poor"
    lines.append("---")
    lines.append("")
    lines.append(f"## Executive Summary")
    lines.append(f"**Overall Site Rating: {score:.1f} / 5.0 ({rating})** *(legacy weighted score)*")

    feas_all = d.get("feasibility_all_tenants")
    if feas_all:
        lines.extend(_render_feasibility_by_tenant(feas_all))
    lines.append("")

    # Utility info
    territories = d.get("service_territories", [])
    if territories:
        t = territories[0]
        lines.append(f" Utility service territory: **{t.get('name', 'N/A')}** ({t.get('holding_company', '')}).")

    rate = d.get("utility_rate")
    if rate and rate.get("industrial_rate_cents"):
        lines.append(f" Industrial electricity rate: **{rate['industrial_rate_cents']:.2f} cents/kWh**.")
        if target_mw:
            annual_mwh = target_mw * 8760 * 0.95
            annual_cost_m = annual_mwh * rate["industrial_rate_cents"] / 100 / 1e6
            lines.append(f" Estimated annual electricity cost at {target_mw} MW (95% CF): **${annual_cost_m:,.0f}M**.")

    tariffs = d.get("dc_tariffs", [])
    if tariffs:
        t = tariffs[0]
        if t.get("moratorium"):
            lines.append(f" **WARNING: Active moratorium** on new DC connections ({t['utility_name']}).")
        elif t.get("deposit_onerous"):
            lines.append(f" Note: {t['utility_name']} tariff has onerous deposit requirements.")

    lines.append("")

    # 1. Power Infrastructure
    lines.append("## 1. Power Infrastructure")
    lines.append("")
    lines.append("### Transmission Lines (within 30 km)")
    tx = d.get("transmission_lines", [])
    tx_rows = []
    for t in tx:
        v = f"{t['voltage']:.0f} kV" if t.get("voltage") and t["voltage"] > 0 else t.get("volt_class", "N/A")
        subs = ""
        if t.get("sub_1") and t["sub_1"] != "NOT AVAILABLE":
            subs = t["sub_1"]
            if t.get("sub_2") and t["sub_2"] != "NOT AVAILABLE":
                subs += f" - {t['sub_2']}"
        owner = t.get("owner", "")
        if owner == "NOT AVAILABLE":
            owner = ""
        tx_rows.append([t.get("volt_class", ""), v, f"{t['dist_km']:.1f}", owner[:35], subs[:40]])
    lines.append(_table(["Class", "Voltage", "Dist (km)", "Owner", "Substations"], tx_rows))

    lines.append("### Substations (within 30 km)")
    subs = d.get("substations", [])
    sub_rows = []
    for s in subs:
        sub_rows.append([
            s.get("name", "N/A"),
            s.get("type", ""),
            f"{s['dist_km']:.1f}",
            s.get("max_infer", "N/A"),
        ])
    lines.append(_table(["Name", "Type", "Dist (km)", "Max Voltage"], sub_rows))

    lines.append("### Grid Adequacy Assessment")
    feas_for_grid = d.get("feasibility") or {}
    pp_for_grid = feas_for_grid.get("power_path") or {}
    outlook_for_grid = pp_for_grid.get("outlook") or {}
    verdict_for_grid = outlook_for_grid.get("verdict")
    if verdict_for_grid:
        lines.append(f"- **Grid Outlook (qualitative):** {verdict_for_grid.title()}")
        lines.append(f"  *{outlook_for_grid.get('evidence','')}*")
    lines.append(f"- **Rough HV-line capacity proxy:** {_fmt_mw(grid.get('max_mw'))} MW")
    lines.append(
        "  *Voltage-class heuristic only (nearest line kV × typical feeder multiplier); "
        "not a host-utility capacity study. Scoring uses the qualitative outlook above, "
        "not this number.*"
    )
    lines.append(f"- **Upgrade Required (heuristic):** {'Yes' if grid.get('upgrade_needed') else 'No'}")
    lines.append(f"- **Confidence (HV proximity):** {grid.get('confidence', 'N/A')}")
    grid_access_score = (d.get("scores") or {}).get("Grid Access")
    if grid_access_score is not None:
        lines.append(
            f"- **Scorecard Grid Access:** {_score_bar(grid_access_score)} "
            f"({grid_access_score}/5) -- derived from grid_outlook + HV proximity "
            f"(not from the HV-line MW proxy above)."
        )
    lines.append("")

    # Planned substation projects (grid pipeline)
    planned = d.get("planned_substations", [])
    if planned:
        lines.append("### Planned Grid Buildout (within 150 km)")
        lines.append("Substations with planned upgrades or new construction:")
        lines.append("")
        pp_rows = []
        for s in planned:
            pp_rows.append([
                s.get("name", "N/A"),
                s.get("current_kv", "N/A"),
                s.get("planned_project", "")[:50],
                s.get("planned_voltage", ""),
                s.get("status", ""),
                f"{s['dist_km']:.0f}",
            ])
        lines.append(_table(["Substation", "Current", "Planned Project", "Target kV", "Type", "Dist (km)"], pp_rows))
    lines.append("")

    # 2. Utility & Rates
    lines.append("## 2. Utility & Rates")
    if territories:
        t = territories[0]
        lines.append(f"- **Utility:** {t.get('name', 'N/A')}")
        lines.append(f"- **Control Area / ISO:** {t.get('control_area', 'N/A')}")
        lines.append(f"- **Holding Company:** {t.get('holding_company', 'N/A')}")
        lines.append(f"- **Customers Served:** {t.get('customers', 'N/A'):,}" if isinstance(t.get('customers'), (int, float)) else f"- **Customers Served:** {t.get('customers', 'N/A')}")
    else:
        lines.append("_No service territory match found._")

    if rate:
        lines.append(f"- **Industrial Rate:** {rate.get('industrial_rate_cents', 'N/A')} cents/kWh (EIA-861)")
    else:
        lines.append("- **Industrial Rate:** Not available")

    # Energy cost projection
    target_mw = d.get("target_mw")
    if target_mw and rate and rate.get("industrial_rate_cents"):
        pue = 1.3  # Industry average for modern DCs
        cf = 0.95  # Capacity factor
        it_mw = target_mw / pue
        annual_mwh = target_mw * 8760 * cf
        annual_cost_m = annual_mwh * rate["industrial_rate_cents"] / 100 / 1e6
        lines.append(f"\n### Annual Energy Cost Projection ({target_mw:,.0f} MW site)")
        lines.append(f"- **PUE assumption:** {pue} (IT load: {it_mw:,.0f} MW)")
        lines.append(f"- **Capacity factor:** {cf*100:.0f}%")
        lines.append(f"- **Annual consumption:** {annual_mwh/1e6:,.1f} TWh")
        lines.append(f"- **Estimated annual cost:** ${annual_cost_m:,.0f}M")

    # Grid energy mix
    mix = d.get("grid_energy_mix")
    if mix:
        lines.append(f"\n### Grid Energy Mix ({mix['iso']})")
        lines.append(f"- **Clean Energy:** {mix['clean_energy_pct']:.1f}%")
        mix_parts = [f"{m['fuel']} {m['pct']:.0f}%" for m in mix.get("fuel_mix", [])[:5]]
        if mix_parts:
            lines.append(f"- **Mix:** {', '.join(mix_parts)}")

    lines.append("")

    # 3. DC Tariff
    lines.append("## 3. DC Tariff Provisions")
    if tariffs:
        for t in tariffs:
            lines.append(f"### {t['utility_name']} -- {t['tariff_name']}")
            lines.append(f"- **Type:** {t.get('tariff_type', 'N/A')}")
            lines.append(f"- **Status:** {t.get('status', 'N/A')}")
            if t.get("moratorium"):
                lines.append(f"- **MORATORIUM: Active**")
            lines.append(f"- **Min Demand:** {_fmt_mw(t.get('min_demand_mw'))} MW")
            lines.append(f"- **Contract Term:** {t.get('contract_term_years', 'N/A')} years")
            lines.append(f"- **Min Billing:** {t.get('min_billing_pct', 'N/A')}%")
            if t.get("collateral_desc"):
                lines.append(f"- **Collateral:** {t['collateral_desc']}")
            if t.get("exit_fee_desc"):
                lines.append(f"- **Exit Fees:** {t['exit_fee_desc']}")
            if t.get("deposit_onerous"):
                lines.append(f"- **Deposit Onerous:** Yes")
            if t.get("notes"):
                lines.append(f"- **Notes:** {t['notes']}")
            lines.append("")
    else:
        lines.append(f"_No DC-specific tariff identified for this state ({d.get('state', 'N/A')})._")
    lines.append("")

    # 4. Tax Incentives
    lines.append(f"## 4. State Tax Incentives ({d.get('state', 'N/A')})")
    inc = d.get("tax_incentives")
    if inc:
        lines.append(f"- **Sales Tax Exemption:** {_yn(inc.get('sales_tax'))}")
        lines.append(f"- **Property Tax Abatement:** {_yn(inc.get('property_tax'))}")
        lines.append(f"- **Income Tax Credit:** {_yn(inc.get('income_tax'))}")
        lines.append(f"- **Investment Threshold:** ${inc.get('investment_threshold_m', 'N/A')}M")
        lines.append(f"- **Job Requirement:** {inc.get('job_requirement', 'N/A')}")
        lines.append(f"- **Duration:** {inc.get('duration_years', 'N/A')} years")
        lines.append(f"- **Summary:** {inc.get('summary', '')}")
    else:
        lines.append("_No DC-specific state tax incentive data available._")
    lines.append("")

    # 5. Land Use & Zoning
    lines.append("## 5. Land Use & Zoning")
    lines.append("")

    lc = d.get("land_cover")
    osm = d.get("osm_landuse", [])

    if lc:
        cat = lc.get("category", "")
        code = lc.get("nlcd_code", 0)
        label = lc.get("nlcd_label", "Unknown")

        if cat == "developed_high":
            suitability = "Excellent -- already developed, high-intensity land use. Likely zoned industrial/commercial."
        elif cat == "developed_med":
            suitability = "Good -- developed area, medium intensity. May be zoned commercial or mixed-use."
        elif cat == "developed_low":
            suitability = "Moderate -- developed but low-intensity (parking, parks, large-lot residential). Rezoning may be needed."
        elif cat in ("agriculture", "grassland", "scrub", "barren"):
            suitability = "Greenfield -- undeveloped land. Will require rezoning to industrial/commercial. Check county zoning map."
        elif cat == "forest":
            suitability = "Greenfield (forested) -- clearing + rezoning required. Environmental review likely."
        elif cat == "wetland":
            suitability = "Constrained -- wetland area. Section 404 permit required. Significant permitting risk."
        elif cat == "water":
            suitability = "Not suitable -- open water."
        else:
            suitability = "Review required."

        lines.append(f"### Land Cover: **{label}** (NLCD {code})")
        lines.append(f"- {suitability}")
    else:
        lines.append("### Land Cover: Data not available")

    # OSM landuse tags
    if osm:
        industrial = [o for o in osm if o["landuse"] in ("industrial", "commercial", "retail")]
        if industrial:
            names = [o.get("name", "") for o in industrial if o.get("name")]
            lines.append(f"\n### OSM Zoning: **{industrial[0]['landuse'].title()}**")
            if names:
                lines.append(f"- Nearby: {', '.join(names[:3])}")
            lines.append("- OpenStreetMap confirms industrial/commercial land use at or near this location.")
        else:
            types = list(set(o["landuse"] for o in osm))
            lines.append(f"\n### OSM Landuse: {', '.join(types[:3])}")
    else:
        lines.append("\n_No OpenStreetMap landuse data mapped for this immediate area._")
    lines.append("")

    # 6. Environmental & Regulatory Risk
    lines.append("## 6. Environmental & Regulatory Risk")
    lines.append("")

    # NAAQS NonAttainment
    naaqs = d.get("nonattainment_zones", [])
    if naaqs:
        lines.append("### Air Quality NonAttainment Zones")
        lines.append("**WARNING: Site is in one or more EPA nonattainment areas.**")
        lines.append("Backup generators and cooling systems may require stricter permitting (BACT/LAER, emission offsets).")
        lines.append("")
        na_rows = [[n["pollutant"], n.get("area_name", ""), n.get("classification", ""), n.get("status", "")] for n in naaqs]
        lines.append(_table(["Pollutant", "Area", "Classification", "Status"], na_rows))
        # Narrative-only marginal/moderate notes (not deal-killers; see
        # docs/screen_methodology/nonattainment.md).
        try:
            from scoring import marginal_nonattainment_narrative
            for ev in marginal_nonattainment_narrative(d):
                lines.append(f"- {ev}")
        except Exception:  # noqa: BLE001
            pass
        lines.append("")
    else:
        lines.append("### Air Quality: **Attainment Zone**")
        lines.append("Site is not in any EPA nonattainment area. Standard air permitting applies for backup generators.")
        lines.append("")

    # FEMA Flood Zone
    flood = d.get("flood_zones", [])
    if flood:
        fz = flood[0]
        zone = fz.get("flood_zone", "")
        if zone.startswith("A") or zone.startswith("V"):
            lines.append(f"### Flood Zone: **{zone}** (High Risk)")
            lines.append("Site is in a FEMA Special Flood Hazard Area. Flood insurance required. Elevated construction may be mandated.")
        elif zone.startswith("X") or zone == "AREA OF MINIMAL FLOOD HAZARD":
            lines.append(f"### Flood Zone: **{zone}** (Low/Moderate Risk)")
            lines.append("Site is outside the 100-year floodplain.")
        else:
            lines.append(f"### Flood Zone: **{zone}**")
    else:
        lines.append("### Flood Zone: Data not available")
        lines.append("FEMA NFHL query returned no results for this location.")
    # 500-year exposure narrative (not a deal-killer; see
    # docs/screen_methodology/flood_zone_av.md).
    try:
        from scoring import flood_500yr_exposure
        for ev in flood_500yr_exposure(d):
            lines.append(f"- {ev}")
    except Exception:  # noqa: BLE001
        pass
    lines.append("")

    # Justice40 / EJ
    j40 = d.get("justice40")
    if j40:
        if j40.get("is_disadvantaged"):
            lines.append("### Environmental Justice: **Disadvantaged Community (Justice40)**")
            lines.append("Site is in a federally designated disadvantaged community. Regulatory agencies may require additional EJ analysis and community engagement.")
            # Narrative-only detail (Justice40 retired from DEAL_KILLERS 2026-04-24;
            # see docs/screen_methodology/justice40_disadvantaged.md).
            try:
                from scoring import justice40_narrative
                for ev in justice40_narrative(d):
                    lines.append(f"- {ev}")
            except Exception:  # noqa: BLE001
                pass
        else:
            lines.append("### Environmental Justice: Not a designated disadvantaged community")
        lines.append(f"- **Census Tract:** {j40.get('tract_id', 'N/A')}")
        if j40.get("diesel_pm_pct"):
            lines.append(f"- **Diesel PM Percentile:** {j40['diesel_pm_pct']}")
        if j40.get("pm25_pct"):
            lines.append(f"- **PM2.5 Percentile:** {j40['pm25_pct']}")
        if j40.get("low_income_pct"):
            lines.append(f"- **Low Income Percentile:** {j40['low_income_pct']}")
        if j40.get("housing_burden_pct"):
            lines.append(f"- **Housing Burden Percentile:** {j40['housing_burden_pct']}")
    else:
        lines.append("### Environmental Justice: Data not available")
    lines.append("")

    # Seismic Hazard
    seismic = d.get("seismic")
    if seismic:
        sdc = seismic.get("seismic_design_category", "N/A")
        pga = seismic.get("pga")
        if sdc in ("A", "B"):
            risk = "Low"
            note = "Standard construction practices adequate."
        elif sdc == "C":
            risk = "Moderate"
            note = "Some seismic detailing required. Minor cost impact."
        elif sdc == "D":
            risk = "High"
            note = "Significant seismic design requirements. 10-15% construction cost premium."
        elif sdc in ("E", "F"):
            risk = "Very High"
            note = "Stringent seismic design required. 15-25% construction cost premium."
        else:
            risk = "Unknown"
            note = ""
        lines.append(f"### Seismic Hazard: **SDC {sdc}** ({risk})")
        if pga:
            lines.append(f"- **Peak Ground Acceleration:** {pga:.3f}g")
        lines.append(f"- **Ss (short-period):** {seismic.get('ss', 'N/A')}g | **S1 (1-sec):** {seismic.get('s1', 'N/A')}g")
        if note:
            lines.append(f"- {note}")
    else:
        lines.append("### Seismic Hazard: Data not available")
    lines.append("")

    # Climate & Land
    cdd = d.get("cooling_degree_days")
    land = d.get("land_value_per_acre")
    if cdd or land:
        lines.append("### Climate & Land Cost")
        if cdd is not None:
            if cdd < 500:
                climate = "Excellent (low cooling load)"
            elif cdd < 1000:
                climate = "Good"
            elif cdd < 1500:
                climate = "Moderate"
            elif cdd < 2500:
                climate = "Warm (higher cooling costs)"
            else:
                climate = "Hot (significant cooling costs)"
            lines.append(f"- **Cooling Degree Days:** {cdd:,} ({climate})")
        if land is not None:
            lines.append(f"- **Avg Farmland Value:** ${land:,}/acre (USDA state average; DC-zoned land typically 3-10x)")
            if d.get("target_mw"):
                # Rough: 20-40 acres per 100 MW
                acres = d["target_mw"] / 100 * 30
                land_cost_m = acres * land * 5 / 1e6  # 5x multiplier for developed land
                lines.append(f"- **Est. Land Cost ({acres:.0f} acres at ~5x farmland):** ${land_cost_m:,.0f}M")
        lines.append("")

    # 6. Gas
    lines.append("## 7. Gas Infrastructure")
    gas = d.get("gas_pipelines", [])
    if gas:
        for g in gas[:2]:
            lines.append(f"- **{g.get('operator', 'N/A')}** ({g.get('type', '')}) at {g['dist_km']:.1f} km")
    else:
        lines.append("_No gas pipelines found within 50 km._")
    lines.append("")

    # 6. Water
    lines.append("## 8. Water Resources")
    water = d.get("water_facilities", [])
    if water:
        for w in water[:2]:
            lines.append(f"- **{w.get('name', 'N/A')}** ({w.get('city', '')}, {w.get('state', '')}) at {w['dist_km']:.1f} km")
    else:
        lines.append("_No water facilities found within 30 km._")
    arid_states = {"AZ", "NM", "NV", "UT", "CO", "CA"}
    if d.get("state") in arid_states:
        lines.append(
            "\n*Arid-state note: proximity to a water facility is NOT evidence "
            "of allocation availability. State engineer / water-rights records "
            "should be consulted before any consumptive-use commitment.*"
        )
    lines.append(
        "\n*Water facility proximity is a civic-infrastructure proxy -- "
        "HIFLD does not expose facility capacity. Process-water availability at "
        "DC scale (tens of MGD) requires a separate allocation/discharge study.*"
    )
    lines.append("")

    # 7. Transportation
    lines.append("## 9. Transportation Access")
    hw = d.get("highways", [])
    if hw:
        for h in hw[:2]:
            lines.append(f"- **{h.get('sign', 'N/A')} {h.get('name', '')}** at {h['dist_km']:.1f} km")
    else:
        lines.append("_No interstate/US highways found within 30 km._")
    rr = d.get("railroads", [])
    if rr:
        for r in rr[:2]:
            lines.append(f"- **Railroad:** {r.get('owner', 'N/A')} at {r['dist_km']:.1f} km")
    lines.append("")

    # 8. Telecom
    lines.append("## 10. Telecommunications")
    fiber = d.get("fiber_routes", [])
    if fiber:
        for f_ in fiber[:2]:
            lines.append(f"- **Fiber:** {f_.get('name', 'N/A')} ({f_.get('operator', '')}) at {f_['dist_km']:.1f} km")
    else:
        lines.append("_No fiber routes found within 30 km._")
    towers = d.get("cell_towers", [])
    if towers:
        lines.append(f"- **Nearest Cell Tower:** {towers[0].get('licensee', 'N/A')} at {towers[0]['dist_km']:.1f} km")
    lines.append("")

    # 9. Interconnection Queue
    lines.append(f"## 11. Interconnection Queue ({d.get('state', 'N/A')})")
    queue = d.get("interconnection_queue", [])
    if queue:
        q_rows = [[q["technology"], q["stage"], str(q["count"]), f"{q['total_mw']:,.0f}"] for q in queue[:10]]
        lines.append(_table(["Technology", "Stage", "Projects", "Total MW"], q_rows))
    else:
        lines.append("_No interconnection queue data available._")
    lines.append("")

    # 10. Nearby DCs
    lines.append(f"## 12. Nearby Data Center Activity (within 50 km)")
    dcs = d.get("nearby_dcs", [])
    if dcs:
        dc_rows = []
        for dc in dcs[:15]:
            mw = f"{dc['power_mw']:,.0f}" if dc.get("power_mw") else "TBD"
            dc_rows.append([
                dc.get("name", "")[:40],
                dc.get("owner", "")[:20],
                mw,
                dc.get("energy_company", "")[:25],
                f"{dc['dist_km']:.1f}",
            ])
        lines.append(_table(["Project", "Owner", "MW", "Utility", "Dist (km)"], dc_rows))
        total_mw = sum(dc.get("power_mw", 0) for dc in dcs)
        lines.append(f"\n**{len(dcs)} facilities** totaling **{total_mw:,.0f} MW** within 50 km.")
    else:
        lines.append("_No data center projects found within 50 km._")
    lines.append("")

    # 13. Research Links
    links = d.get("research_links", [])
    if links:
        lines.append("## 13. Research Links")
        lines.append("Pre-built search links for deeper due diligence:")
        lines.append("")
        current_cat = None
        for link in links:
            cat = link.get("category", "")
            if cat != current_cat:
                current_cat = cat
                lines.append(f"\n**{cat}:**")
            lines.append(f"- [{link['name']}]({link['url']}) -- {link['description']}")
            if link.get("note"):
                lines.append(f"  - {link['note']}")
        lines.append("")

    # 14. Scoring Summary
    lines.append("## 14. Site Suitability Score")
    scores = d.get("scores", {})
    score_rows = []
    weights = {
        "Grid Access": 20, "Utility Rate": 15, "Environmental": 15,
        "Fiber/Telecom": 10, "Water": 5, "Transportation": 5,
        "Tax Incentives": 15, "DC Tariff Risk": 15,
    }
    for factor, weight in weights.items():
        s = scores.get(factor, 3)
        score_rows.append([factor, _score_bar(s), f"{s}/5", f"{weight}%"])
    lines.append(_table(["Factor", "Score", "Value", "Weight"], score_rows))
    lines.append(f"\n**Weighted Total: {score:.1f} / 5.0**")
    lines.append("")

    lines.append("---")
    lines.append("*Generated by dc-site-analysis. Data sources: HIFLD, NTAD, EPA, OSM, EIA-861, demand_ledger.*")

    return "\n".join(lines)
