"""DuckDB queries for electricity rates, interconnection queues, and nearby DC projects."""

import csv
import math
import os
import re

import duckdb

ENERGY_DB = os.environ.get(
    "ENERGY_ANALYTICS_DB",
    "/Users/bencarron/Projects/dc-site-mapper/data/energy_analytics.duckdb",
)
DEMAND_DB = os.environ.get(
    "DEMAND_LEDGER_DB",
    "/Users/bencarron/Projects/dc-site-mapper/data/demand_ledger.duckdb",
)
DC_CSV = os.environ.get(
    "DC_CSV",
    "/Users/bencarron/Projects/data-center-demand-analysis/data/raw_documents/data_centers.csv",
)


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _parse_dms(dms_str):
    if not dms_str or not dms_str.strip():
        return None
    s = dms_str.strip()
    m = re.match(r"(\d+)\s*[°]\s*(\d+)\s*['\u2032]\s*(\d+(?:\.\d+)?)\s*[\"'\u2033]?\s*([NSEW])", s)
    if m:
        deg = float(m.group(1)) + float(m.group(2)) / 60 + float(m.group(3)) / 3600
        if m.group(4) in ('S', 'W'):
            deg = -deg
        return deg
    return None


def get_utility_rate(utility_name, state):
    """Look up industrial electricity rate from energy_analytics.duckdb."""
    if not os.path.exists(ENERGY_DB):
        return None
    try:
        db = duckdb.connect(ENERGY_DB, read_only=True)
        # Try matching by utility name first
        if utility_name:
            rows = db.execute("""
                SELECT utility_name, state, avg_rate_kwh, customer_class
                FROM retail_rates
                WHERE notes LIKE '%eia_861%'
                  AND customer_class = 'industrial'
                  AND LOWER(utility_name) LIKE ?
                LIMIT 1
            """, [f"%{utility_name.lower()[:20]}%"]).fetchall()
            if rows:
                r = rows[0]
                db.close()
                return {
                    "utility_name": r[0],
                    "state": r[1],
                    "industrial_rate_cents": round(r[2] * 100, 2) if r[2] else None,
                }

        # Fallback: state average
        if state:
            rows = db.execute("""
                SELECT AVG(avg_rate_kwh) as avg_rate
                FROM retail_rates
                WHERE notes LIKE '%eia_861%'
                  AND customer_class = 'industrial'
                  AND state = ?
            """, [state]).fetchall()
            if rows and rows[0][0]:
                db.close()
                return {
                    "utility_name": f"State average ({state})",
                    "state": state,
                    "industrial_rate_cents": round(rows[0][0] * 100, 2),
                }
        db.close()
    except Exception:
        pass
    return None


def get_interconnection_queue(state):
    """Get interconnection queue summary for a state."""
    if not os.path.exists(ENERGY_DB):
        return []
    try:
        db = duckdb.connect(ENERGY_DB, read_only=True)
        # Check which table exists
        tables = [r[0] for r in db.execute("SHOW TABLES").fetchall()]

        if "lcb_forecast_queue_projects_raw" in tables:
            rows = db.execute("""
                SELECT
                    COALESCE(tech_type, fuel_type, 'Unknown') as technology,
                    COALESCE(queue_phase, study_stage, 'Unknown') as stage,
                    COUNT(*) as project_count,
                    SUM(COALESCE(capacity_mw, 0)) as total_mw
                FROM lcb_forecast_queue_projects_raw
                WHERE state = ?
                GROUP BY technology, stage
                ORDER BY total_mw DESC
                LIMIT 20
            """, [state]).fetchall()
            db.close()
            return [{"technology": r[0], "stage": r[1], "count": r[2], "total_mw": round(r[3], 1)} for r in rows]

        if "interconnection_queue" in tables:
            rows = db.execute("""
                SELECT
                    COALESCE(technology_type, 'Unknown') as technology,
                    COALESCE(status_code, 'Unknown') as stage,
                    COUNT(*) as project_count,
                    SUM(COALESCE(summer_capacity_mw, 0)) as total_mw
                FROM interconnection_queue
                WHERE state = ?
                GROUP BY technology, stage
                ORDER BY total_mw DESC
                LIMIT 20
            """, [state]).fetchall()
            db.close()
            return [{"technology": r[0], "stage": r[1], "count": r[2], "total_mw": round(r[3], 1)} for r in rows]

        db.close()
    except Exception:
        pass
    return []


def get_grid_energy_mix(state):
    """Get generation fuel mix for the ISO/region serving a state."""
    if not os.path.exists(ENERGY_DB):
        return None
    # Map states to ISOs
    STATE_TO_ISO = {
        "NY": "NYISO", "NJ": "PJM", "PA": "PJM", "OH": "PJM", "VA": "PJM",
        "MD": "PJM", "DE": "PJM", "WV": "PJM", "DC": "PJM", "NC": "PJM",
        "IN": "MISO", "IL": "MISO", "MI": "MISO", "WI": "MISO", "MN": "MISO",
        "IA": "MISO", "MO": "MISO", "AR": "MISO", "LA": "MISO", "MS": "MISO",
        "TX": "ERCOT", "OK": "SPP", "KS": "SPP", "NE": "SPP", "ND": "SPP",
        "MT": "NWMT", "CA": "CAISO", "OR": "BPA", "WA": "BPA",
        "GA": "SOCO", "AL": "SOCO", "TN": "TVA", "KY": "TVA",
        "AZ": "AZPS", "NV": "NV", "CO": "PSCO", "NM": "PNM",
        "ID": "IPCO", "WY": "WACM", "SD": "WAPA", "UT": "PACE",
    }
    iso = STATE_TO_ISO.get(state)
    if not iso:
        return None
    try:
        db = duckdb.connect(ENERGY_DB, read_only=True)
        rows = db.execute("""
            SELECT gf.fuel_type, SUM(gf.generation_mw) as total_gen
            FROM generation_fuel_mix gf
            JOIN geography g ON gf.geography_id = g.geography_id
            WHERE g.iso_code = ?
            GROUP BY gf.fuel_type
            ORDER BY total_gen DESC
        """, [iso]).fetchall()
        db.close()
        if not rows:
            return None
        total = sum(r[1] for r in rows)
        if total == 0:
            return None
        clean_fuels = {"Nuclear", "Hydro", "Wind", "Solar", "Other Renewables", "Geothermal"}
        clean_gen = sum(r[1] for r in rows if r[0] in clean_fuels)
        mix = [{"fuel": r[0], "pct": round(100 * r[1] / total, 1)} for r in rows]
        return {
            "iso": iso,
            "clean_energy_pct": round(100 * clean_gen / total, 1),
            "fuel_mix": mix[:8],
        }
    except Exception:
        return None


def get_nearby_dc_projects(lat, lon, radius_km=50):
    """Find nearby data center projects from both demand_ledger and data_centers.csv."""
    results = []

    # Source 1: data_centers.csv
    if os.path.exists(DC_CSV):
        try:
            with open(DC_CSV) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rlat = _parse_dms(row.get("Latitude", ""))
                    rlon = _parse_dms(row.get("Longitude", ""))
                    if rlat is None or rlon is None:
                        continue
                    dist = _haversine_km(lat, lon, rlat, rlon)
                    if dist <= radius_km:
                        mw = float(row.get("Current power (MW)", 0) or 0)
                        cost = float(row.get("Current total capital cost (2025 USD billions)", 0) or 0)
                        results.append({
                            "source": "dc_database",
                            "name": row.get("Title", row.get("Handle", "")),
                            "owner": row.get("Owner", ""),
                            "users": row.get("Users", ""),
                            "power_mw": mw,
                            "cost_b": cost,
                            "energy_company": row.get("Energy companies", ""),
                            "dist_km": round(dist, 1),
                        })
        except Exception:
            pass

    # Source 2: demand_ledger.duckdb
    if os.path.exists(DEMAND_DB):
        try:
            db = duckdb.connect(DEMAND_DB, read_only=True)
            lat_deg = radius_km / 111.0
            lon_deg = radius_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
            rows = db.execute("""
                SELECT
                    pl.city, pl.county, pl.state, pl.utility,
                    p.project_name, p.operator, p.developer, p.lifecycle_stage,
                    pl.latitude, pl.longitude
                FROM project_locations pl
                JOIN projects p ON pl.project_id = p.project_id
                WHERE pl.latitude BETWEEN ? AND ?
                  AND pl.longitude BETWEEN ? AND ?
                  AND pl.latitude IS NOT NULL
                  AND pl.longitude IS NOT NULL
            """, [lat - lat_deg, lat + lat_deg, lon - lon_deg, lon + lon_deg]).fetchall()
            db.close()

            for r in rows:
                if r[8] is None or r[9] is None:
                    continue
                dist = _haversine_km(lat, lon, float(r[8]), float(r[9]))
                if dist <= radius_km:
                    name = r[4] or f"{r[5] or ''} {r[0] or ''} {r[2] or ''}".strip()
                    results.append({
                        "source": "demand_ledger",
                        "name": name,
                        "owner": r[5] or "",
                        "users": r[6] or "",
                        "power_mw": 0,
                        "cost_b": 0,
                        "energy_company": r[3] or "",
                        "dist_km": round(dist, 1),
                        "lifecycle_stage": r[7] or "",
                    })
        except Exception:
            pass

    results.sort(key=lambda x: x["dist_km"])
    return results


def get_nearby_generators(state, county=None):
    """Get power plants in the same state (and county if provided)."""
    if not os.path.exists(ENERGY_DB):
        return []
    try:
        db = duckdb.connect(ENERGY_DB, read_only=True)
        if county:
            county_clean = county.replace(" County", "").strip()
            rows = db.execute("""
                SELECT plant_name, nameplate_capacity_mw, summer_capacity_mw,
                       fuel_type_primary, technology, prime_mover, status,
                       utility_name, operating_year, retirement_year, county
                FROM generators
                WHERE state = ? AND (county = ? OR county LIKE ?)
                  AND nameplate_capacity_mw > 10
                ORDER BY nameplate_capacity_mw DESC
                LIMIT 20
            """, [state, county_clean, f"%{county_clean}%"]).fetchall()
        else:
            rows = db.execute("""
                SELECT plant_name, nameplate_capacity_mw, summer_capacity_mw,
                       fuel_type_primary, technology, prime_mover, status,
                       utility_name, operating_year, retirement_year, county
                FROM generators
                WHERE state = ? AND nameplate_capacity_mw > 50
                ORDER BY nameplate_capacity_mw DESC
                LIMIT 20
            """, [state]).fetchall()
        db.close()
        cols = ["plant_name", "nameplate_mw", "summer_mw", "fuel_type", "technology",
                "prime_mover", "status", "utility", "operating_year", "retirement_year", "county"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


def get_capacity_prices(state):
    """Get capacity auction clearing prices for the relevant RTO zone."""
    if not os.path.exists(ENERGY_DB):
        return []
    # Map state to likely capacity zone geography_id
    STATE_TO_CAP_ZONE = {
        "VA": 100, "MD": 100, "PA": 100, "NJ": 100, "DE": 100,  # PJM RTO
        "OH": 100, "WV": 100, "IN": 100, "IL": 100, "MI": 100,  # PJM/MISO overlap
        "NY": 12,  # NYISO
    }
    geo_id = STATE_TO_CAP_ZONE.get(state)
    if not geo_id:
        return []
    try:
        db = duckdb.connect(ENERGY_DB, read_only=True)
        rows = db.execute("""
            SELECT cp.delivery_year, cp.auction_type, cp.clearing_price, cp.cleared_mw,
                   g.name as zone_name
            FROM capacity_prices cp
            JOIN geography g ON cp.geography_id = g.geography_id
            WHERE cp.geography_id = ?
            ORDER BY cp.delivery_year DESC
            LIMIT 10
        """, [geo_id]).fetchall()
        db.close()
        return [{"year": r[0], "auction": r[1], "price_mw_day": float(r[2]),
                 "cleared_mw": float(r[3]), "zone": r[4]} for r in rows]
    except Exception:
        return []


def get_planned_transmission(state):
    """Get planned transmission projects intersecting a state."""
    if not os.path.exists(ENERGY_DB):
        return []
    try:
        db = duckdb.connect(ENERGY_DB, read_only=True)
        rows = db.execute("""
            SELECT project_name, owner, status, max_voltage_kv, capacity_mw,
                   estimated_in_service_year, origin_substation, destination_substation,
                   length_mi, states_intersected_abbrev,
                   federal_permitting_simple_status, state_permitting_simple_status
            FROM planned_transmission_projects
            WHERE states_intersected_abbrev LIKE ?
              AND status NOT IN ('Complete', 'Cancelled')
            ORDER BY max_voltage_kv DESC NULLS LAST
            LIMIT 15
        """, [f"%{state}%"]).fetchall()
        db.close()
        cols = ["project", "owner", "status", "voltage_kv", "capacity_mw",
                "in_service_year", "origin_sub", "dest_sub", "length_mi",
                "states", "federal_permit", "state_permit"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


def get_gas_prices():
    """Get recent natural gas prices from Henry Hub and regional hubs."""
    if not os.path.exists(ENERGY_DB):
        return []
    try:
        db = duckdb.connect(ENERGY_DB, read_only=True)
        rows = db.execute("""
            SELECT h.hub_name, gp.date, gp.price, gp.price_type
            FROM gas_prices gp
            JOIN gas_hubs h ON gp.hub_id = h.hub_id
            ORDER BY gp.date DESC
            LIMIT 20
        """).fetchall()
        db.close()
        return [{"hub": r[0], "date": str(r[1]), "price": float(r[2]),
                 "type": r[3]} for r in rows]
    except Exception:
        return []


def get_wholesale_power_costs(state):
    """Get wholesale power costs for the relevant ISO."""
    if not os.path.exists(ENERGY_DB):
        return []
    STATE_TO_ISO = {
        "VA": "PJM", "MD": "PJM", "PA": "PJM", "NJ": "PJM", "DE": "PJM",
        "OH": "PJM", "WV": "PJM", "NC": "PJM", "IN": "PJM", "IL": "PJM",
        "MI": "PJM",
    }
    iso = STATE_TO_ISO.get(state)
    if not iso:
        return []
    try:
        db = duckdb.connect(ENERGY_DB, read_only=True)
        rows = db.execute("""
            SELECT year, category, AVG(value) as avg_value, unit
            FROM wholesale_power_costs
            WHERE iso_code = ?
            GROUP BY year, category, unit
            ORDER BY year DESC, category
            LIMIT 20
        """, [iso]).fetchall()
        db.close()
        return [{"year": r[0], "category": r[1], "avg_value": round(float(r[2]), 2),
                 "unit": r[3]} for r in rows]
    except Exception:
        return []
