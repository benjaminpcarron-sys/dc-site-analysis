"""Spatial queries against Parquet-cached infrastructure layers via DuckDB."""

import json
import os
import math
import urllib.parse
import urllib.request

import duckdb

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data", "cache")

_db = None

def _get_db():
    global _db
    if _db is None:
        _db = duckdb.connect()
        _db.execute("INSTALL spatial; LOAD spatial;")
    return _db


def _parquet(name):
    return os.path.join(CACHE_DIR, f"{name}.parquet")


def _deg_for_km(km, lat):
    """Approximate degrees of longitude/latitude for a given km radius."""
    lat_deg = km / 111.0
    lon_deg = km / (111.0 * math.cos(math.radians(lat)))
    return lat_deg, lon_deg


def _distance_km_sql():
    """SQL expression for approximate distance in km using the Haversine formula."""
    return """
        6371 * 2 * ASIN(SQRT(
            POWER(SIN(RADIANS({lat_col} - {lat}) / 2), 2) +
            COS(RADIANS({lat})) * COS(RADIANS({lat_col})) *
            POWER(SIN(RADIANS({lon_col} - {lon}) / 2), 2)
        ))
    """


def find_nearest_transmission_lines(lat, lon, radius_km=30):
    """Find nearest transmission lines grouped by voltage class."""
    db = _get_db()
    pq = _parquet("transmission_lines")
    if not os.path.exists(pq):
        return []

    lat_deg, lon_deg = _deg_for_km(radius_km, lat)
    sql = f"""
        WITH nearby AS (
            SELECT *,
                6371 * 2 * ASIN(SQRT(
                    POWER(SIN(RADIANS(centroid_lat - {lat}) / 2), 2) +
                    COS(RADIANS({lat})) * COS(RADIANS(centroid_lat)) *
                    POWER(SIN(RADIANS(centroid_lon - {lon}) / 2), 2)
                )) as approx_dist_km
            FROM read_parquet('{pq}')
            WHERE centroid_lat BETWEEN {lat - lat_deg} AND {lat + lat_deg}
              AND centroid_lon BETWEEN {lon - lon_deg} AND {lon + lon_deg}
        ),
        with_exact AS (
            SELECT *,
                ST_Distance(
                    ST_Transform(ST_GeomFromWKB(geom_wkb), 'EPSG:4326', 'EPSG:4326'),
                    ST_Point({lon}, {lat})
                ) * 111.0 as line_dist_km
            FROM nearby
            WHERE approx_dist_km < {radius_km * 1.5}
        ),
        ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY VOLT_CLASS ORDER BY approx_dist_km) as rn
            FROM with_exact
        )
        SELECT id, VOLTAGE, VOLT_CLASS, OWNER, SUB_1, SUB_2, approx_dist_km as dist_km
        FROM ranked
        WHERE rn = 1
        ORDER BY
            CASE VOLT_CLASS
                WHEN '735 AND ABOVE' THEN 1
                WHEN 'DC' THEN 2
                WHEN '500' THEN 3
                WHEN '345' THEN 4
                WHEN '220-287' THEN 5
                WHEN '100-161' THEN 6
                WHEN 'UNDER 100' THEN 7
                WHEN 'SUB 100' THEN 8
                ELSE 9
            END
    """
    try:
        rows = db.execute(sql).fetchall()
        cols = ["id", "voltage", "volt_class", "owner", "sub_1", "sub_2", "dist_km"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        print(f"  Warning: transmission line query failed: {e}")
        return []


def find_nearest_substations(lat, lon, radius_km=30, limit=5):
    """Find nearest substations from HIFLD + planned_transmission_substations."""
    db = _get_db()
    results = []

    # Source 1: HIFLD substations (NE US only)
    pq = _parquet("substations")
    if os.path.exists(pq):
        lat_deg, lon_deg = _deg_for_km(radius_km, lat)
        sql = f"""
            SELECT id, NAME, CITY, STATE, TYPE, STATUS, LINES, MAX_INFER, MIN_INFER,
                6371 * 2 * ASIN(SQRT(
                    POWER(SIN(RADIANS(lat - {lat}) / 2), 2) +
                    COS(RADIANS({lat})) * COS(RADIANS(lat)) *
                    POWER(SIN(RADIANS(lon - {lon}) / 2), 2)
                )) as dist_km
            FROM read_parquet('{pq}')
            WHERE lat BETWEEN {lat - lat_deg} AND {lat + lat_deg}
              AND lon BETWEEN {lon - lon_deg} AND {lon + lon_deg}
            HAVING dist_km < {radius_km}
            ORDER BY dist_km
            LIMIT {limit}
        """
        try:
            rows = db.execute(sql).fetchall()
            cols = ["id", "name", "city", "state", "type", "status", "lines",
                    "max_infer", "min_infer", "dist_km"]
            results.extend([dict(zip(cols, r)) for r in rows])
        except Exception:
            pass

    # Source 2: Planned transmission substations (nationwide, from energy_analytics.duckdb)
    energy_db = os.environ.get(
        "ENERGY_ANALYTICS_DB",
        "/Users/bencarron/Projects/dc-site-mapper/data/energy_analytics.duckdb",
    )
    if os.path.exists(energy_db):
        try:
            edb = duckdb.connect(energy_db, read_only=True)
            lat_deg, _ = _deg_for_km(radius_km, lat)
            lon_deg = radius_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
            rows = edb.execute("""
                SELECT substation_name, state_abbrev,
                       current_max_voltage_kv, planned_project, planned_project_voltage,
                       existing_or_new_substation, latitude, longitude
                FROM planned_transmission_substations
                WHERE latitude BETWEEN ? AND ?
                  AND longitude BETWEEN ? AND ?
            """, [lat - lat_deg, lat + lat_deg, lon - lon_deg, lon + lon_deg]).fetchall()
            edb.close()
            for r in rows:
                if r[6] is None or r[7] is None:
                    continue
                dist = 6371 * 2 * math.asin(math.sqrt(
                    math.sin(math.radians(float(r[6]) - lat) / 2) ** 2 +
                    math.cos(math.radians(lat)) * math.cos(math.radians(float(r[6]))) *
                    math.sin(math.radians(float(r[7]) - lon) / 2) ** 2
                ))
                if dist <= radius_km:
                    max_kv = f"{r[2]} kV" if r[2] and float(r[2]) > 0 else "N/A"
                    planned = f"Planned: {r[3]} @ {r[4]} kV" if r[3] else ""
                    results.append({
                        "name": r[0],
                        "city": "",
                        "state": r[1],
                        "type": r[5] or "",
                        "status": "PLANNED" if r[5] == "New build" else "IN SERVICE",
                        "max_infer": max_kv,
                        "min_infer": "",
                        "planned_project": planned,
                        "dist_km": round(dist, 1),
                    })
        except Exception:
            pass

    results.sort(key=lambda x: x.get("dist_km", 999))
    return results[:limit]


def find_nearest_gas_pipelines(lat, lon, radius_km=50, limit=3):
    db = _get_db()
    pq = _parquet("gas_pipelines")
    if not os.path.exists(pq):
        return []
    lat_deg, lon_deg = _deg_for_km(radius_km, lat)
    sql = f"""
        SELECT id, OPERATOR, TYPEPIPE,
            6371 * 2 * ASIN(SQRT(
                POWER(SIN(RADIANS(centroid_lat - {lat}) / 2), 2) +
                COS(RADIANS({lat})) * COS(RADIANS(centroid_lat)) *
                POWER(SIN(RADIANS(centroid_lon - {lon}) / 2), 2)
            )) as dist_km
        FROM read_parquet('{pq}')
        WHERE centroid_lat BETWEEN {lat - lat_deg} AND {lat + lat_deg}
          AND centroid_lon BETWEEN {lon - lon_deg} AND {lon + lon_deg}
        HAVING dist_km < {radius_km}
        ORDER BY dist_km
        LIMIT {limit}
    """
    try:
        rows = db.execute(sql).fetchall()
        return [dict(zip(["id", "operator", "type", "dist_km"], r)) for r in rows]
    except Exception:
        return []


def find_nearest_highways(lat, lon, radius_km=30, limit=3):
    db = _get_db()
    pq = _parquet("highways")
    if not os.path.exists(pq):
        return []
    lat_deg, lon_deg = _deg_for_km(radius_km, lat)
    sql = f"""
        SELECT id, SIGN1, SIGNT1, LNAME,
            6371 * 2 * ASIN(SQRT(
                POWER(SIN(RADIANS(centroid_lat - {lat}) / 2), 2) +
                COS(RADIANS({lat})) * COS(RADIANS(centroid_lat)) *
                POWER(SIN(RADIANS(centroid_lon - {lon}) / 2), 2)
            )) as dist_km
        FROM read_parquet('{pq}')
        WHERE centroid_lat BETWEEN {lat - lat_deg} AND {lat + lat_deg}
          AND centroid_lon BETWEEN {lon - lon_deg} AND {lon + lon_deg}
          AND SIGNT1 IN ('I', 'U')
        HAVING dist_km < {radius_km}
        ORDER BY dist_km
        LIMIT {limit}
    """
    try:
        rows = db.execute(sql).fetchall()
        return [dict(zip(["id", "sign", "type", "name", "dist_km"], r)) for r in rows]
    except Exception:
        return []


def find_nearest_railroads(lat, lon, radius_km=30, limit=3):
    db = _get_db()
    pq = _parquet("railroads")
    if not os.path.exists(pq):
        return []
    lat_deg, lon_deg = _deg_for_km(radius_km, lat)
    sql = f"""
        SELECT id, RROWNER1,
            6371 * 2 * ASIN(SQRT(
                POWER(SIN(RADIANS(centroid_lat - {lat}) / 2), 2) +
                COS(RADIANS({lat})) * COS(RADIANS(centroid_lat)) *
                POWER(SIN(RADIANS(centroid_lon - {lon}) / 2), 2)
            )) as dist_km
        FROM read_parquet('{pq}')
        WHERE centroid_lat BETWEEN {lat - lat_deg} AND {lat + lat_deg}
          AND centroid_lon BETWEEN {lon - lon_deg} AND {lon + lon_deg}
        HAVING dist_km < {radius_km}
        ORDER BY dist_km
        LIMIT {limit}
    """
    try:
        rows = db.execute(sql).fetchall()
        return [dict(zip(["id", "owner", "dist_km"], r)) for r in rows]
    except Exception:
        return []


def find_nearest_water(lat, lon, radius_km=30, limit=3):
    db = _get_db()
    pq = _parquet("water_facilities")
    if not os.path.exists(pq):
        return []
    lat_deg, lon_deg = _deg_for_km(radius_km, lat)
    sql = f"""
        SELECT id, PRIMARY_NAME, CITY_NAME, STATE_CODE,
            6371 * 2 * ASIN(SQRT(
                POWER(SIN(RADIANS(lat - {lat}) / 2), 2) +
                COS(RADIANS({lat})) * COS(RADIANS(lat)) *
                POWER(SIN(RADIANS(lon - {lon}) / 2), 2)
            )) as dist_km
        FROM read_parquet('{pq}')
        WHERE lat BETWEEN {lat - lat_deg} AND {lat + lat_deg}
          AND lon BETWEEN {lon - lon_deg} AND {lon + lon_deg}
        HAVING dist_km < {radius_km}
        ORDER BY dist_km
        LIMIT {limit}
    """
    try:
        rows = db.execute(sql).fetchall()
        return [dict(zip(["id", "name", "city", "state", "dist_km"], r)) for r in rows]
    except Exception:
        return []


def find_nearest_fiber(lat, lon, radius_km=30, limit=3):
    db = _get_db()
    pq = _parquet("fiber_routes")
    if not os.path.exists(pq):
        return []
    lat_deg, lon_deg = _deg_for_km(radius_km, lat)
    sql = f"""
        SELECT id, name, operator,
            6371 * 2 * ASIN(SQRT(
                POWER(SIN(RADIANS(centroid_lat - {lat}) / 2), 2) +
                COS(RADIANS({lat})) * COS(RADIANS(centroid_lat)) *
                POWER(SIN(RADIANS(centroid_lon - {lon}) / 2), 2)
            )) as dist_km
        FROM read_parquet('{pq}')
        WHERE centroid_lat BETWEEN {lat - lat_deg} AND {lat + lat_deg}
          AND centroid_lon BETWEEN {lon - lon_deg} AND {lon + lon_deg}
        HAVING dist_km < {radius_km}
        ORDER BY dist_km
        LIMIT {limit}
    """
    try:
        rows = db.execute(sql).fetchall()
        return [dict(zip(["id", "name", "operator", "dist_km"], r)) for r in rows]
    except Exception:
        return []


def find_nearest_cell_towers(lat, lon, radius_km=30, limit=3):
    db = _get_db()
    pq = _parquet("cellular_towers")
    if not os.path.exists(pq):
        return []
    lat_deg, lon_deg = _deg_for_km(radius_km, lat)
    sql = f"""
        SELECT id, LICENSEE, CITY,
            6371 * 2 * ASIN(SQRT(
                POWER(SIN(RADIANS(lat - {lat}) / 2), 2) +
                COS(RADIANS({lat})) * COS(RADIANS(lat)) *
                POWER(SIN(RADIANS(lon - {lon}) / 2), 2)
            )) as dist_km
        FROM read_parquet('{pq}')
        WHERE lat BETWEEN {lat - lat_deg} AND {lat + lat_deg}
          AND lon BETWEEN {lon - lon_deg} AND {lon + lon_deg}
        HAVING dist_km < {radius_km}
        ORDER BY dist_km
        LIMIT {limit}
    """
    try:
        rows = db.execute(sql).fetchall()
        return [dict(zip(["id", "licensee", "city", "dist_km"], r)) for r in rows]
    except Exception:
        return []


def find_service_territory(lat, lon):
    """Find utility service territory containing the point."""
    db = _get_db()
    pq = _parquet("service_territories")
    if not os.path.exists(pq):
        return []
    sql = f"""
        SELECT id, NAME, STATE, TYPE, CNTRL_AREA, HOLDING_CO, CUSTOMERS
        FROM read_parquet('{pq}')
        WHERE bbox_min_lon <= {lon} AND bbox_max_lon >= {lon}
          AND bbox_min_lat <= {lat} AND bbox_max_lat >= {lat}
          AND ST_Contains(
              ST_GeomFromWKB(geom_wkb),
              ST_Point({lon}, {lat})
          )
        LIMIT 3
    """
    try:
        rows = db.execute(sql).fetchall()
        cols = ["id", "name", "state", "type", "control_area", "holding_company", "customers"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


# ── Environmental Queries ──────────────────────────────────────────────

def check_nonattainment_zone(lat, lon):
    """Check if site is in any EPA NAAQS nonattainment area."""
    db = _get_db()
    pq = _parquet("naaqs_nonattainment")
    if not os.path.exists(pq):
        return []
    sql = f"""
        SELECT pollutant, area_name, state_name, classification, current_status, meets_naaqs
        FROM read_parquet('{pq}')
        WHERE bbox_min_lon <= {lon} AND bbox_max_lon >= {lon}
          AND bbox_min_lat <= {lat} AND bbox_max_lat >= {lat}
          AND ST_Contains(
              ST_GeomFromWKB(geom_wkb),
              ST_Point({lon}, {lat})
          )
    """
    try:
        rows = db.execute(sql).fetchall()
        cols = ["pollutant", "area_name", "state", "classification", "status", "meets_naaqs"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


def check_flood_zone(lat, lon):
    """Query FEMA flood hazard data via Esri's USA Flood Hazard service."""
    try:
        base = "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/USA_Flood_Hazard_Reduced_Set_gdb/FeatureServer/0"
        # Must use Web Mercator (3857) for the geometry since the service extent is in 3857
        # But we can pass WGS84 and specify inSR=4326
        geom = json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}})
        params = urllib.parse.urlencode({
            "geometry": geom,
            "geometryType": "esriGeometryPoint",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "FLD_ZONE,ZONE_SUBTY,SFHA_TF,STATIC_BFE,DFIRM_ID",
            "returnGeometry": "false",
            "f": "json",
            "resultRecordCount": 5,
        })
        url = f"{base}/query?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "dc-site-analysis/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        results = []
        for feat in data.get("features", []):
            attrs = feat.get("attributes", {})
            zone = attrs.get("FLD_ZONE", "")
            if zone:
                results.append({
                    "flood_zone": zone,
                    "zone_subtype": attrs.get("ZONE_SUBTY", ""),
                    "sfha": attrs.get("SFHA_TF", ""),
                    "static_bfe": attrs.get("STATIC_BFE", ""),
                    "dfirm_id": attrs.get("DFIRM_ID", ""),
                })
        return results
    except Exception:
        return []


def check_justice40(lat, lon):
    """Check if site is in a Justice40 disadvantaged community tract."""
    db = _get_db()
    pq = _parquet("justice40_tracts")
    if not os.path.exists(pq):
        return None
    sql = f"""
        SELECT tract_id, is_disadvantaged, climate_factor,
               diesel_pm, pm25, flood_100yr_pct, flood_200yr_pct,
               low_income_pct, low_median_income, high_school_pct, housing_burden_pct
        FROM read_parquet('{pq}')
        WHERE bbox_min_lon <= {lon} AND bbox_max_lon >= {lon}
          AND bbox_min_lat <= {lat} AND bbox_max_lat >= {lat}
          AND ST_Contains(
              ST_GeomFromWKB(geom_wkb),
              ST_Point({lon}, {lat})
          )
        LIMIT 1
    """
    try:
        rows = db.execute(sql).fetchall()
        if not rows:
            return None
        r = rows[0]
        return {
            "tract_id": r[0],
            "is_disadvantaged": bool(r[1]),
            "climate_factor": bool(r[2]),
            "diesel_pm_pct": r[3],
            "pm25_pct": r[4],
            "flood_100yr_pct": r[5],
            "flood_200yr_pct": r[6],
            "low_income_pct": r[7],
            "low_median_income": bool(r[8]),
            "high_school_pct": r[9],
            "housing_burden_pct": r[10],
        }
    except Exception:
        return None


def check_land_cover(lat, lon):
    """Query NLCD 2021 land cover classification via MRLC WMS."""
    NLCD_CODES = {
        11: ("Open Water", "water"), 12: ("Perennial Ice/Snow", "other"),
        21: ("Developed, Open Space", "developed_low"),
        22: ("Developed, Low Intensity", "developed_low"),
        23: ("Developed, Medium Intensity", "developed_med"),
        24: ("Developed, High Intensity", "developed_high"),
        31: ("Barren Land", "barren"),
        41: ("Deciduous Forest", "forest"), 42: ("Evergreen Forest", "forest"),
        43: ("Mixed Forest", "forest"),
        51: ("Dwarf Scrub", "scrub"), 52: ("Shrub/Scrub", "scrub"),
        71: ("Grassland/Herbaceous", "grassland"),
        81: ("Pasture/Hay", "agriculture"), 82: ("Cultivated Crops", "agriculture"),
        90: ("Woody Wetlands", "wetland"), 95: ("Emergent Herbaceous Wetlands", "wetland"),
    }
    try:
        url = (
            f"https://www.mrlc.gov/geoserver/mrlc_display/wms?"
            f"SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo"
            f"&QUERY_LAYERS=NLCD_2021_Land_Cover_L48"
            f"&LAYERS=NLCD_2021_Land_Cover_L48"
            f"&INFO_FORMAT=application/json&FEATURE_COUNT=1"
            f"&X=50&Y=50&WIDTH=101&HEIGHT=101&SRS=EPSG:4326"
            f"&BBOX={lon-0.001},{lat-0.001},{lon+0.001},{lat+0.001}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "dc-site-analysis/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        code = data["features"][0]["properties"]["PALETTE_INDEX"]
        label, category = NLCD_CODES.get(code, (f"Unknown ({code})", "other"))
        return {"nlcd_code": code, "nlcd_label": label, "category": category}
    except Exception:
        return None


def check_osm_landuse(lat, lon, radius_m=200):
    """Query OpenStreetMap for landuse tags near a point via Overpass API."""
    query = f"""
[out:json][timeout:10];
(
  way["landuse"](around:{radius_m},{lat},{lon});
  relation["landuse"](around:{radius_m},{lat},{lon});
);
out tags;
"""
    try:
        url = "https://overpass-api.de/api/interpreter"
        data = urllib.parse.urlencode({"data": query}).encode()
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "dc-site-analysis/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        elements = result.get("elements", [])
        landuses = []
        for el in elements:
            tags = el.get("tags", {})
            landuses.append({
                "landuse": tags.get("landuse", ""),
                "name": tags.get("name", ""),
                "industrial": tags.get("industrial", ""),
            })
        return landuses
    except Exception:
        return []


def check_seismic_hazard(lat, lon):
    """Query USGS Design Maps API for seismic hazard at a point."""
    try:
        params = urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "riskCategory": "III",  # Essential facilities
            "siteClass": "D",  # Default stiff soil
            "title": "dc-site-analysis",
        })
        url = f"https://earthquake.usgs.gov/ws/designmaps/asce7-22.json?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "dc-site-analysis/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        resp_data = data.get("response", {}).get("data", {})
        sdc = resp_data.get("sdc", "")
        ss = resp_data.get("ss")  # Short-period spectral acceleration
        s1 = resp_data.get("s1")  # 1-second spectral acceleration
        pgam = resp_data.get("pgam")  # PGA with site amplification

        return {
            "seismic_design_category": sdc,
            "ss": round(ss, 3) if ss else None,
            "s1": round(s1, 3) if s1 else None,
            "pga": round(pgam, 3) if pgam else None,
        }
    except Exception:
        return None
