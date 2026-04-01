#!/usr/bin/env python3
"""One-time conversion of GeoJSON files to Parquet for fast spatial queries.

Reads large GeoJSON files via DuckDB's ST_Read, extracts key columns + centroid
coordinates, and writes compact Parquet files with columnar statistics for fast
bounding box prefiltering.

Usage:
    python prepare_spatial_cache.py [--force]
"""

import argparse
import os
import sys
import time

import duckdb

GEOJSON_DIR = os.environ.get(
    "GEOJSON_DIR",
    "/Users/bencarron/Projects/dc-site-mapper/data/downloads",
)
CACHE_DIR = os.path.join(os.path.dirname(__file__), "data", "cache")

LAYERS = [
    {
        "name": "transmission_lines",
        "source": "hifld_transmission_lines.geojson",
        "sql": """
            SELECT
                OBJECTID_1 as id,
                VOLTAGE, VOLT_CLASS, OWNER, STATUS, SUB_1, SUB_2,
                ST_AsWKB(geom) as geom_wkb,
                ST_X(ST_Centroid(geom)) as centroid_lon,
                ST_Y(ST_Centroid(geom)) as centroid_lat
            FROM st_read('{src}')
            WHERE geom IS NOT NULL
        """,
    },
    {
        "name": "substations",
        "source": "hifld_substations.geojson",
        "sql": """
            SELECT
                OBJECTID as id,
                NAME, CITY, STATE, TYPE, STATUS, LINES,
                MAX_INFER, MIN_INFER,
                ST_AsWKB(geom) as geom_wkb,
                ST_X(geom) as lon,
                ST_Y(geom) as lat
            FROM st_read('{src}')
            WHERE geom IS NOT NULL
        """,
    },
    {
        "name": "gas_pipelines",
        "source": "hifld_gas_pipelines.geojson",
        "sql": """
            SELECT
                FID as id,
                TYPEPIPE, Operator as OPERATOR, Status as STATUS,
                ST_AsWKB(geom) as geom_wkb,
                ST_X(ST_Centroid(geom)) as centroid_lon,
                ST_Y(ST_Centroid(geom)) as centroid_lat
            FROM st_read('{src}')
            WHERE geom IS NOT NULL
        """,
    },
    {
        "name": "highways",
        "source": "ntad_highways.geojson",
        "sql": """
            SELECT
                OBJECTID as id,
                SIGN1, SIGNT1, SIGNN1, LNAME,
                ST_AsWKB(geom) as geom_wkb,
                ST_X(ST_Centroid(geom)) as centroid_lon,
                ST_Y(ST_Centroid(geom)) as centroid_lat
            FROM st_read('{src}')
            WHERE geom IS NOT NULL
        """,
    },
    {
        "name": "railroads",
        "source": "ntad_railroads.geojson",
        "sql": """
            SELECT
                OBJECTID as id,
                RROWNER1, RROWNER2, STATEAB,
                ST_AsWKB(geom) as geom_wkb,
                ST_X(ST_Centroid(geom)) as centroid_lon,
                ST_Y(ST_Centroid(geom)) as centroid_lat
            FROM st_read('{src}')
            WHERE geom IS NOT NULL
        """,
    },
    {
        "name": "water_facilities",
        "source": "epa_water_facilities.geojson",
        "sql": """
            SELECT
                OBJECTID as id,
                PRIMARY_NAME, CITY_NAME, STATE_CODE, COUNTY_NAME,
                ST_AsWKB(geom) as geom_wkb,
                ST_X(geom) as lon,
                ST_Y(geom) as lat
            FROM st_read('{src}')
            WHERE geom IS NOT NULL
        """,
    },
    {
        "name": "fiber_routes",
        "source": "osm_fiber_routes.geojson",
        "sql": """
            SELECT
                row_number() OVER () as id,
                name, operator,
                ST_AsWKB(geom) as geom_wkb,
                ST_X(ST_Centroid(geom)) as centroid_lon,
                ST_Y(ST_Centroid(geom)) as centroid_lat
            FROM st_read('{src}')
            WHERE geom IS NOT NULL
        """,
    },
    {
        "name": "cellular_towers",
        "source": "hifld_cellular_towers.geojson",
        "sql": """
            SELECT
                OBJECTID as id,
                Licensee as LICENSEE, LocCity as CITY, LocState as STATE_CODE,
                ST_AsWKB(geom) as geom_wkb,
                ST_X(geom) as lon,
                ST_Y(geom) as lat
            FROM st_read('{src}')
            WHERE geom IS NOT NULL
        """,
    },
    {
        "name": "service_territories",
        "source": "hifld_service_territories.geojson",
        "sql": """
            SELECT
                OBJECTID as id,
                NAME, STATE, TYPE, CNTRL_AREA, HOLDING_CO, CUSTOMERS,
                ST_AsWKB(geom) as geom_wkb,
                ST_XMin(geom) as bbox_min_lon,
                ST_XMax(geom) as bbox_max_lon,
                ST_YMin(geom) as bbox_min_lat,
                ST_YMax(geom) as bbox_max_lat
            FROM st_read('{src}')
            WHERE geom IS NOT NULL
        """,
    },
]


def prepare_cache(force=False):
    os.makedirs(CACHE_DIR, exist_ok=True)
    db = duckdb.connect()
    db.execute("INSTALL spatial; LOAD spatial;")

    for layer in LAYERS:
        parquet_path = os.path.join(CACHE_DIR, f"{layer['name']}.parquet")
        if os.path.exists(parquet_path) and not force:
            print(f"  [skip] {layer['name']}.parquet already exists")
            continue

        src = os.path.join(GEOJSON_DIR, layer["source"])
        if not os.path.exists(src):
            print(f"  [skip] Source not found: {layer['source']}")
            continue

        print(f"  Processing {layer['source']} -> {layer['name']}.parquet ...", end=" ", flush=True)
        t0 = time.time()
        sql = layer["sql"].format(src=src)
        try:
            db.execute(f"COPY ({sql}) TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
            elapsed = time.time() - t0
            size_mb = os.path.getsize(parquet_path) / 1024 / 1024
            print(f"done ({elapsed:.1f}s, {size_mb:.1f} MB)")
        except Exception as e:
            print(f"FAILED: {e}")
            if os.path.exists(parquet_path):
                os.remove(parquet_path)

    db.close()
    print("\nCache preparation complete.")


def main():
    parser = argparse.ArgumentParser(description="Prepare spatial cache from GeoJSON")
    parser.add_argument("--force", action="store_true", help="Overwrite existing parquet files")
    args = parser.parse_args()
    prepare_cache(force=args.force)


if __name__ == "__main__":
    main()
