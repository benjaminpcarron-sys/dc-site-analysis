#!/usr/bin/env python3
"""DC Site Pre-Feasibility Analysis Tool.

Usage:
    python dc_site_report.py "5502 Spinks Rd, Abilene, TX 79601" --target-mw 500
    python dc_site_report.py --prepare-cache
"""

import argparse
import os
import re
import sys
import time


def check_cache():
    cache_dir = os.path.join(os.path.dirname(__file__), "data", "cache")
    required = ["transmission_lines.parquet", "service_territories.parquet"]
    missing = [f for f in required if not os.path.exists(os.path.join(cache_dir, f))]
    return len(missing) == 0


def compute_scores(d):
    """Compute factor scores (1-5) for the site suitability matrix."""
    scores = {}

    # Grid Access: derived from the qualitative grid_outlook verdict plus
    # observable HV proximity. Intentionally NOT derived from
    # grid_assessment.max_mw (voltage-class heuristic, precision without
    # accuracy). See docs/screen_methodology/grid_severely_insufficient.md.
    from scoring import grid_outlook, _hv_line_within, _large_substation_nearby
    outlook = grid_outlook(d)
    verdict = outlook["verdict"]
    hv_10 = _hv_line_within(d, 10)
    hv_30 = _hv_line_within(d, 30)
    large_sub, _ = _large_substation_nearby(d)

    if verdict == "promising":
        grid_score = 5 if (hv_10 or large_sub) else 4
    elif verdict == "neutral":
        grid_score = 4 if hv_10 else (3 if hv_30 else 2)
    else:  # doubtful
        grid_score = 1
    scores["Grid Access"] = grid_score

    # Utility Rate: state-relative + absolute floor. The killer logic
    # already treats ">=14 c/kWh OR >=1.25x state avg" as triggering; mirror
    # that structure on the scorecard side so a 10c/kWh site in CA
    # (state avg ~20c) isn't scored the same as 10c/kWh in NM (state avg ~6c).
    # See docs/screen_methodology/utility_rate_score.md.
    rate = d.get("utility_rate")
    if rate and rate.get("industrial_rate_cents"):
        cents = rate["industrial_rate_cents"]
        from reference_data import get_state_industrial_rate_avg
        state_avg = get_state_industrial_rate_avg(d.get("state")) if d.get("state") else None

        if cents >= 20 or (state_avg and cents >= state_avg * 1.5):
            scores["Utility Rate"] = 1
        elif cents >= 14 or (state_avg and cents >= state_avg * 1.25):
            scores["Utility Rate"] = 2
        elif state_avg and cents <= state_avg * 0.8:
            scores["Utility Rate"] = 5
        elif state_avg and cents <= state_avg * 1.0:
            scores["Utility Rate"] = 4
        elif cents < 6:
            scores["Utility Rate"] = 5
        elif cents < 8:
            scores["Utility Rate"] = 4
        elif cents < 10:
            scores["Utility Rate"] = 3
        else:
            scores["Utility Rate"] = 3
    else:
        scores["Utility Rate"] = 3

    # Fiber/Telecom
    fiber = d.get("fiber_routes", [])
    towers = d.get("cell_towers", [])
    if fiber and fiber[0]["dist_km"] < 5:
        scores["Fiber/Telecom"] = 5
    elif fiber and fiber[0]["dist_km"] < 15:
        scores["Fiber/Telecom"] = 4
    elif towers and towers[0]["dist_km"] < 10:
        scores["Fiber/Telecom"] = 3
    else:
        scores["Fiber/Telecom"] = 2

    # Water: proximity to HIFLD water/wastewater facilities is a weak proxy
    # for DC process-water availability. HIFLD does not include facility
    # capacity, so a 2 MGD village plant scores identically to a 200 MGD
    # regional system. We coarsen to 3 tiers (adequate/marginal/remote) and
    # cap arid-state sites one tier lower with a narrative warning. See
    # docs/screen_methodology/water_score.md.
    water = d.get("water_facilities", [])
    if water and water[0]["dist_km"] < 10:
        water_score = 4
    elif water and water[0]["dist_km"] < 25:
        water_score = 3
    else:
        water_score = 2
    ARID_STATES = {"AZ", "NM", "NV", "UT", "CO", "CA"}
    if d.get("state") in ARID_STATES:
        water_score = max(1, water_score - 1)
    scores["Water"] = water_score

    # Transportation
    hw = d.get("highways", [])
    if hw and hw[0]["dist_km"] < 5:
        scores["Transportation"] = 5
    elif hw and hw[0]["dist_km"] < 15:
        scores["Transportation"] = 4
    elif hw and hw[0]["dist_km"] < 30:
        scores["Transportation"] = 3
    else:
        scores["Transportation"] = 2

    # Tax Incentives
    inc = d.get("tax_incentives")
    if inc:
        n_types = sum([inc.get("sales_tax", False), inc.get("property_tax", False), inc.get("income_tax", False)])
        thresh = inc.get("investment_threshold_m") or 999
        if n_types >= 3 and thresh <= 50:
            scores["Tax Incentives"] = 5
        elif n_types >= 2:
            scores["Tax Incentives"] = 4
        elif n_types >= 1:
            scores["Tax Incentives"] = 3
        else:
            scores["Tax Incentives"] = 2
    else:
        scores["Tax Incentives"] = 2

    # DC Tariff Risk (inverted: moratorium = bad)
    tariffs = d.get("dc_tariffs", [])
    if tariffs:
        t = tariffs[0]
        if t.get("moratorium"):
            scores["DC Tariff Risk"] = 1
        elif t.get("deposit_onerous"):
            scores["DC Tariff Risk"] = 2
        elif t.get("status") == "effective" or t.get("status") == "approved":
            scores["DC Tariff Risk"] = 4
        else:
            scores["DC Tariff Risk"] = 3
    else:
        scores["DC Tariff Risk"] = 3

    # Environmental Risk
    env_score = 5
    naaqs = d.get("nonattainment_zones", [])
    if naaqs:
        env_score -= min(2, len(naaqs))
    flood = d.get("flood_zones", [])
    if flood and flood[0].get("flood_zone", "").startswith(("A", "V")):
        env_score -= 2
    j40 = d.get("justice40")
    if j40 and j40.get("is_disadvantaged"):
        env_score -= 1
    seismic = d.get("seismic")
    if seismic and seismic.get("seismic_design_category") in ("D", "E", "F"):
        env_score -= 1  # High seismic zone = construction cost premium
    scores["Environmental"] = max(1, env_score)

    return scores


def main():
    parser = argparse.ArgumentParser(description="DC Site Pre-Feasibility Analysis")
    parser.add_argument("address", nargs="?", help="Address to analyze")
    parser.add_argument("--target-mw", type=float, default=None, help="Target capacity in MW")
    parser.add_argument("--output", "-o", type=str, default=None, help="Save report to file")
    parser.add_argument("--prepare-cache", action="store_true", help="Build spatial cache from GeoJSON")
    parser.add_argument("--force-cache", action="store_true", help="Force rebuild of spatial cache")
    parser.add_argument("--radius-km", type=float, default=30, help="Search radius in km (default: 30)")
    parser.add_argument("--no-map", action="store_true", help="Skip map screenshot capture")
    parser.add_argument(
        "--tenant",
        choices=["speculative", "anchored", "hyperscaler"],
        default="speculative",
        help=(
            "Tenant profile for risk-adjusted scoring (default: speculative). "
            "'anchored' = credit-worthy named anchor; 'hyperscaler' = IG-credit FAANG-tier. "
            "Scales deal-killer probabilities (e.g. tariff deposits trivial for hyperscalers)."
        ),
    )
    args = parser.parse_args()

    if args.prepare_cache or args.force_cache:
        from prepare_spatial_cache import prepare_cache
        prepare_cache(force=args.force_cache)
        if not args.address:
            return

    if not args.address:
        parser.print_help()
        sys.exit(1)

    if not check_cache():
        print("Spatial cache not found. Run with --prepare-cache first:")
        print(f"  python {__file__} --prepare-cache")
        sys.exit(1)

    t0 = time.time()

    # Step 1: Geocode
    print(f"Geocoding: {args.address} ...", end=" ", flush=True)
    from geocoder import geocode
    geo = geocode(args.address)
    lat, lon = geo["lat"], geo["lon"]
    state = geo.get("state")
    print(f"{lat:.6f}, {lon:.6f} ({state})")

    # Step 2-5: Run the pipeline (spatial, environmental, data, reference, grid).
    # Each element is independently timed and its provenance recorded in d["_meta"].
    from pipeline import default_registry, run_pipeline, coverage_summary

    d = {
        "address": args.address,
        "lat": lat,
        "lon": lon,
        "state": state,
        "county": geo.get("county", ""),
        "target_mw": args.target_mw,
        "tenant_profile": args.tenant,
    }

    print("Running pipeline ...", end=" ", flush=True)
    registry = default_registry(radius_km=args.radius_km)
    run_pipeline(d, registry)
    summary = coverage_summary(d)
    print(
        f"done ({summary['covered']}/{summary['total']} covered, "
        f"{summary['missing']} missing, {summary['errored']} errored)"
    )

    # Step 6: Score -- legacy weighted average is kept for backward compat;
    # feasibility is the new risk-adjusted headline metric (see scoring.py and
    # docs/EFFICACY_SCORECARD.md).
    scores = compute_scores(d)
    d["scores"] = scores
    weights = {"Grid Access": 20, "Utility Rate": 15, "Environmental": 15,
               "Fiber/Telecom": 10, "Water": 5, "Transportation": 5, "Tax Incentives": 15,
               "DC Tariff Risk": 15}
    overall = sum(scores[k] * weights[k] for k in weights) / sum(weights.values())
    d["overall_score"] = overall

    from scoring import compute_feasibility, compute_feasibility_all_tenants
    d["feasibility"] = compute_feasibility(d, scores)
    d["feasibility_all_tenants"] = compute_feasibility_all_tenants(d, scores)

    # Step 7: Generate report
    from report_template import generate_report
    report = generate_report(d)

    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.1f}s\n")
    print(report)

    # Auto-save to reports/ folder
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '_', args.address.lower()).strip('_')[:60]
    auto_path = os.path.join(reports_dir, f"{slug}.md")
    with open(auto_path, "w") as f:
        f.write(report)
    print(f"Report saved to {auto_path}")

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Also saved to {args.output}")

    # Step 9: Capture map screenshot from DC Site Mapper (if available)
    if not args.no_map:
        map_path = os.path.join(reports_dir, f"{slug}_map.png")
        try:
            from capture_map import capture_map
            print("Capturing map screenshot ...", end=" ", flush=True)
            capture_map(lat, lon, map_path, zoom=12.5)
            print(f"Map saved to {map_path}")
        except Exception as e:
            print(f"Map capture skipped: {e}")
            print("  (Ensure DC Site Mapper is running: cd ../dc-site-mapper && docker compose up -d)")


if __name__ == "__main__":
    main()
