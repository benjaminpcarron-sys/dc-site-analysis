#!/usr/bin/env python3
"""Download environmental datasets for DC site analysis.

Downloads:
  - EPA NAAQS NonAttainment areas (Ozone 2015, PM2.5 2012)
  - Justice40 disadvantaged community tracts (EJ screening)

Note: FEMA flood zones (4.4M records) are queried on-demand per site
rather than bulk downloaded.

Usage:
    python download_environmental_data.py [--force]
"""

import argparse
import json
import os
import sys
import time
import urllib.request

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data", "cache")
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "data", "downloads")

EPA_NONATTAINMENT_LAYERS = [
    {
        "name": "ozone_2015",
        "url": "https://gispub.epa.gov/arcgis/rest/services/OAR_OAQPS/NAA2015Ozone8hour/MapServer/0",
        "pollutant": "Ozone (8-hr, 2015)",
    },
    {
        "name": "pm25_2012",
        "url": "https://gispub.epa.gov/arcgis/rest/services/OAR_OAQPS/NAA2012PM25Annual/MapServer/0",
        "pollutant": "PM2.5 (Annual, 2012)",
    },
    {
        "name": "pm10_1987",
        "url": "https://gispub.epa.gov/arcgis/rest/services/OAR_OAQPS/NAA1987PM10/MapServer/0",
        "pollutant": "PM10 (1987)",
    },
    {
        "name": "so2_2010",
        "url": "https://gispub.epa.gov/arcgis/rest/services/OAR_OAQPS/NAA2010SO21hour/MapServer/0",
        "pollutant": "SO2 (1-hr, 2010)",
    },
    {
        "name": "lead_2008",
        "url": "https://gispub.epa.gov/arcgis/rest/services/OAR_OAQPS/NAA2008Lead/MapServer/0",
        "pollutant": "Lead (2008)",
    },
]


def download_arcgis_geojson(base_url, output_file, max_records=2000):
    """Download all features from an ArcGIS MapServer/FeatureServer as GeoJSON."""
    all_features = []
    offset = 0

    while True:
        query_url = (
            f"{base_url}/query?"
            f"where=1%3D1&outFields=*&f=geojson"
            f"&resultRecordCount={max_records}&resultOffset={offset}"
        )
        req = urllib.request.Request(query_url, headers={"User-Agent": "dc-site-analysis/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        features = data.get("features", [])
        if not features:
            break

        all_features.extend(features)
        print(f"    Downloaded {len(all_features)} features...", end="\r")

        if len(features) < max_records:
            break
        offset += max_records
        time.sleep(0.5)

    geojson = {"type": "FeatureCollection", "features": all_features}
    with open(output_file, "w") as f:
        json.dump(geojson, f)
    print(f"    Saved {len(all_features)} features to {os.path.basename(output_file)}")
    return len(all_features)


def download_nonattainment(force=False):
    """Download EPA NAAQS nonattainment area polygons."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    total = 0
    for layer in EPA_NONATTAINMENT_LAYERS:
        dest = os.path.join(DOWNLOAD_DIR, f"naaqs_{layer['name']}.geojson")
        if os.path.exists(dest) and not force:
            print(f"  [skip] naaqs_{layer['name']}.geojson exists")
            continue
        print(f"  Downloading {layer['pollutant']} nonattainment areas...")
        try:
            n = download_arcgis_geojson(layer["url"], dest)
            total += n
        except Exception as e:
            print(f"    FAILED: {e}")
    return total


def download_justice40(force=False):
    """Download Justice40 disadvantaged community tracts."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    dest = os.path.join(DOWNLOAD_DIR, "justice40_tracts.geojson")
    if os.path.exists(dest) and not force:
        print(f"  [skip] justice40_tracts.geojson exists")
        return 0

    print("  Downloading Justice40 tracts (73,767 records, this will take a few minutes)...")
    base = "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/usa_november_2022/FeatureServer/0"
    try:
        n = download_arcgis_geojson(base, dest)
        return n
    except Exception as e:
        print(f"    FAILED: {e}")
        return 0


def prepare_environmental_parquet(force=False):
    """Convert downloaded environmental GeoJSON to Parquet."""
    import duckdb

    os.makedirs(CACHE_DIR, exist_ok=True)
    db = duckdb.connect()
    db.execute("INSTALL spatial; LOAD spatial;")

    # Merge all NAAQS nonattainment files into one parquet
    naaqs_parquet = os.path.join(CACHE_DIR, "naaqs_nonattainment.parquet")
    if not os.path.exists(naaqs_parquet) or force:
        naaqs_files = [
            os.path.join(DOWNLOAD_DIR, f"naaqs_{layer['name']}.geojson")
            for layer in EPA_NONATTAINMENT_LAYERS
        ]
        existing = [f for f in naaqs_files if os.path.exists(f)]
        if existing:
            print(f"  Building naaqs_nonattainment.parquet from {len(existing)} files...")
            unions = []
            for i, f in enumerate(existing):
                pollutant = EPA_NONATTAINMENT_LAYERS[i]["pollutant"]
                unions.append(f"""
                    SELECT
                        '{pollutant}' as pollutant,
                        area_name, state_name, state_abbreviation, classification,
                        current_status, meets_naaqs,
                        ST_AsWKB(geom) as geom_wkb,
                        ST_XMin(geom) as bbox_min_lon, ST_XMax(geom) as bbox_max_lon,
                        ST_YMin(geom) as bbox_min_lat, ST_YMax(geom) as bbox_max_lat
                    FROM st_read('{f}')
                    WHERE geom IS NOT NULL
                """)
            sql = " UNION ALL ".join(unions)
            try:
                db.execute(f"COPY ({sql}) TO '{naaqs_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD)")
                size_mb = os.path.getsize(naaqs_parquet) / 1024 / 1024
                print(f"    Done ({size_mb:.1f} MB)")
            except Exception as e:
                print(f"    FAILED: {e}")

    # Justice40 tracts
    j40_parquet = os.path.join(CACHE_DIR, "justice40_tracts.parquet")
    j40_src = os.path.join(DOWNLOAD_DIR, "justice40_tracts.geojson")
    if os.path.exists(j40_src) and (not os.path.exists(j40_parquet) or force):
        print(f"  Building justice40_tracts.parquet...", end=" ", flush=True)
        sql = f"""
            SELECT
                GEOID10 as tract_id,
                SF as is_disadvantaged,
                CF as climate_factor,
                DF_PFS as diesel_pm,
                PM25F_PFS as pm25,
                P100_PFS as flood_100yr_pct,
                P200_I_PFS as flood_200yr_pct,
                LIF_PFS as low_income_pct,
                LMI_PFS as low_median_income,
                HSEF as high_school_pct,
                HBF_PFS as housing_burden_pct,
                ST_AsWKB(geom) as geom_wkb,
                ST_XMin(geom) as bbox_min_lon, ST_XMax(geom) as bbox_max_lon,
                ST_YMin(geom) as bbox_min_lat, ST_YMax(geom) as bbox_max_lat
            FROM st_read('{j40_src}')
            WHERE geom IS NOT NULL
        """
        try:
            db.execute(f"COPY ({sql}) TO '{j40_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD)")
            size_mb = os.path.getsize(j40_parquet) / 1024 / 1024
            print(f"done ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"FAILED: {e}")

    db.close()


def main():
    parser = argparse.ArgumentParser(description="Download environmental data for DC site analysis")
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    args = parser.parse_args()

    print("=== Downloading EPA NAAQS NonAttainment Areas ===")
    download_nonattainment(force=args.force)

    print("\n=== Downloading Justice40 Tracts ===")
    download_justice40(force=args.force)

    print("\n=== Building Parquet Cache ===")
    prepare_environmental_parquet(force=args.force)

    print("\nDone. FEMA flood zones are queried on-demand (too large for bulk download).")


if __name__ == "__main__":
    main()
