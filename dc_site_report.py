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

    # Grid Access (from grid_assessment)
    scores["Grid Access"] = d.get("grid_assessment", {}).get("score", 1)

    # Utility Rate
    rate = d.get("utility_rate")
    if rate and rate.get("industrial_rate_cents"):
        cents = rate["industrial_rate_cents"]
        if cents < 4:
            scores["Utility Rate"] = 5
        elif cents < 6:
            scores["Utility Rate"] = 4
        elif cents < 8:
            scores["Utility Rate"] = 3
        elif cents < 10:
            scores["Utility Rate"] = 2
        else:
            scores["Utility Rate"] = 1
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

    # Water
    water = d.get("water_facilities", [])
    if water and water[0]["dist_km"] < 5:
        scores["Water"] = 5
    elif water and water[0]["dist_km"] < 15:
        scores["Water"] = 4
    elif water and water[0]["dist_km"] < 30:
        scores["Water"] = 3
    else:
        scores["Water"] = 2

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

    # Step 2: Spatial queries
    print("Running spatial queries ...", end=" ", flush=True)
    import spatial_queries as sq
    radius = args.radius_km

    transmission_lines = sq.find_nearest_transmission_lines(lat, lon, radius)
    substations = sq.find_nearest_substations(lat, lon, radius, limit=10)
    planned_substations = sq.find_planned_substations(lat, lon, radius_km=150, limit=10)
    gas_pipelines = sq.find_nearest_gas_pipelines(lat, lon, 50)
    highways = sq.find_nearest_highways(lat, lon, radius)
    railroads = sq.find_nearest_railroads(lat, lon, radius)
    water_facilities = sq.find_nearest_water(lat, lon, radius)
    fiber_routes = sq.find_nearest_fiber(lat, lon, radius)
    cell_towers = sq.find_nearest_cell_towers(lat, lon, radius)
    service_territories = sq.find_service_territory(lat, lon)
    print("done")

    # Step 2b: Environmental queries
    print("Running environmental queries ...", end=" ", flush=True)
    nonattainment_zones = sq.check_nonattainment_zone(lat, lon)
    flood_zones = sq.check_flood_zone(lat, lon)
    justice40 = sq.check_justice40(lat, lon)
    seismic = sq.check_seismic_hazard(lat, lon)
    land_cover = sq.check_land_cover(lat, lon)
    osm_landuse = sq.check_osm_landuse(lat, lon)
    print("done")

    # Step 3: Data queries
    print("Running data queries ...", end=" ", flush=True)
    from data_queries import get_utility_rate, get_interconnection_queue, get_nearby_dc_projects, get_grid_energy_mix

    utility_name = service_territories[0]["name"] if service_territories else None
    utility_rate = get_utility_rate(utility_name, state)
    interconnection_queue = get_interconnection_queue(state)
    nearby_dcs = get_nearby_dc_projects(lat, lon, 50)
    grid_energy_mix = get_grid_energy_mix(state) if state else None
    print("done")

    # Step 4: Reference data
    from reference_data import get_dc_tariffs, get_state_incentives, get_cooling_degree_days, get_land_value
    from research_links import generate_research_links
    dc_tariffs = get_dc_tariffs(state, utility_name) if state else []
    tax_incentives = get_state_incentives(state) if state else None
    cooling_dd = get_cooling_degree_days(state) if state else None
    land_value = get_land_value(state) if state else None
    research_links = generate_research_links(state, geo.get("county", ""), utility_name, args.address) if state else []

    # Step 5: Grid assessment
    from grid_assessment import assess_grid
    grid_assessment = assess_grid(transmission_lines, substations, args.target_mw)

    # Step 6: Assemble results
    d = {
        "address": args.address,
        "lat": lat,
        "lon": lon,
        "state": state,
        "county": geo.get("county", ""),
        "target_mw": args.target_mw,
        "transmission_lines": transmission_lines,
        "substations": substations,
        "planned_substations": planned_substations,
        "gas_pipelines": gas_pipelines,
        "highways": highways,
        "railroads": railroads,
        "water_facilities": water_facilities,
        "fiber_routes": fiber_routes,
        "cell_towers": cell_towers,
        "service_territories": service_territories,
        "utility_rate": utility_rate,
        "interconnection_queue": interconnection_queue,
        "nearby_dcs": nearby_dcs,
        "dc_tariffs": dc_tariffs,
        "tax_incentives": tax_incentives,
        "grid_assessment": grid_assessment,
        "grid_energy_mix": grid_energy_mix,
        "nonattainment_zones": nonattainment_zones,
        "flood_zones": flood_zones,
        "justice40": justice40,
        "seismic": seismic,
        "land_cover": land_cover,
        "osm_landuse": osm_landuse,
        "cooling_degree_days": cooling_dd,
        "land_value_per_acre": land_value,
        "research_links": research_links,
    }

    # Step 7: Score
    scores = compute_scores(d)
    d["scores"] = scores
    weights = {"Grid Access": 20, "Utility Rate": 15, "Environmental": 15,
               "Fiber/Telecom": 10, "Water": 5, "Transportation": 5, "Tax Incentives": 15,
               "DC Tariff Risk": 15}
    overall = sum(scores[k] * weights[k] for k in weights) / sum(weights.values())
    d["overall_score"] = overall

    # Step 8: Generate report
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


if __name__ == "__main__":
    main()
