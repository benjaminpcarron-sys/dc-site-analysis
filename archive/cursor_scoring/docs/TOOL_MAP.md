# Tool Map — DC Site Pre-Feasibility Analysis

_Snapshot: 2026-04-20. Regenerate when the pipeline structure changes, not when data vintage changes._

This document inventories every element of the tool so each can be evaluated and improved independently. See `EFFICACY_SCORECARD.md` for the 1–5 scoring of each element on five efficacy axes.

## Pipeline shape

```
address ─► Geocoder ─► (lat, lon, state, county)
                           │
                           ▼
              ┌────────────────────────────┐
              │ Parallel analyzer calls    │
              │  - spatial_queries         │
              │  - environmental queries   │
              │  - data_queries            │
              │  - reference_data          │
              └──────────────┬─────────────┘
                             ▼
                    grid_assessment
                             ▼
                    compute_scores  ──► overall (weighted avg)
                             ▼
                    report_template
                             ▼
                    reports/<slug>.md (+ optional .docx)
```

All intermediate state lives in the dict `d` assembled in `dc_site_report.main()` (lines 218–251). Every element reads from or writes to `d`.

## Element inventory

### Layer 1 — Inputs (I*)

| ID | Element | Code | Produces |
|---|---|---|---|
| I1 | CLI args | `dc_site_report.main()` argparse | `address`, `target_mw`, `radius_km`, `output` |

### Layer 2 — Data sources (D*)

External facts the tool pulls in. Each has a "freshness" property distinct from the tool version.

| ID | Element | Source of truth | Access path | Freshness |
|---|---|---|---|---|
| D1 | Geocoder | Nominatim (OSM) | `geocoder.py` + file cache | live API |
| D2 | Transmission lines | HIFLD (94,619 segs) | `data/cache/transmission_lines.parquet` | one-time snapshot |
| D3 | Substations (existing) | HIFLD — NE US only | `data/cache/substations.parquet` | one-time snapshot |
| D4 | Substations (planned) | `energy_analytics.duckdb:planned_transmission_substations` | DuckDB | March 2026 |
| D5 | Service territories | HIFLD electric retail service | `data/cache/service_territories.parquet` | one-time |
| D6 | Gas pipelines | HIFLD | `data/cache/gas_pipelines.parquet` | one-time |
| D7 | Highways / rail / water / fiber / cell | HIFLD | respective `.parquet` | one-time |
| D8 | NLCD land cover | USGS raster | `data/cache/` | one-time |
| D9 | OSM landuse | OSM | `data/cache/` | one-time |
| D10 | NAAQS nonattainment | EPA | `data/cache/` | one-time |
| D11 | Justice40 tracts | CEQ | `data/cache/` (73,767 tracts) | one-time |
| D12 | Flood zones | FEMA NFHL | **live API** (often 404) | live, gappy |
| D13 | Seismic hazard | USGS design API | **live API** | live |
| D14 | Utility industrial rates | `energy_analytics.duckdb:retail_rates` (EIA 861) | DuckDB | March 2026 |
| D15 | Interconnection queues | `energy_analytics.duckdb` | DuckDB | March 2026 |
| D16 | Grid energy mix | `energy_analytics.duckdb:generation_fuel_mix` | DuckDB | March 2026 |
| D17 | DC project tracker | `demand_ledger.duckdb` (1,338 projects) | DuckDB | March 2026 |
| D18 | DC CSV | `data_centers.csv` (84 rows) | CSV | March 2026 |
| D19 | DC tariffs | `reference_data.DC_TARIFFS` (17 utilities) | inline Python | March 2026, hand-curated |
| D20 | State incentives | `reference_data.STATE_INCENTIVES` (31 states) | inline Python | March 2026, hand-curated |
| D21 | Cooling degree days | `reference_data.COOLING_DEGREE_DAYS` | inline Python | 30-yr NOAA normals |
| D22 | State land values | `reference_data.LAND_VALUE` | inline Python | USDA, one vintage |

### Layer 3 — Analyzers (A*)

Compute derived values from the data sources above.

| ID | Element | Code | Inputs | Output shape |
|---|---|---|---|---|
| A1 | Nearest transmission lines by voltage | `spatial_queries.find_nearest_transmission_lines` | D2 | list of `{voltage, volt_class, owner, sub_1, sub_2, dist_km}` (1 per voltage class) |
| A2 | Nearest substations (existing + planned, merged) | `spatial_queries.find_nearest_substations` | D3, D4 | list of `{name, state, type, status, max_infer, dist_km, planned_project?}` |
| A3 | Planned substations (wider radius) | `spatial_queries.find_planned_substations` | D4 | list |
| A4 | Nearest gas pipelines | `find_nearest_gas_pipelines` | D6 | list |
| A5 | Nearest highways / rail / water / fiber / cell | 5 functions in `spatial_queries` | D7 | list |
| A6 | Service territory | `find_service_territory` | D5 | `{name, ...}` |
| A7 | Nonattainment zones | `check_nonattainment_zone` | D10 | list of pollutants |
| A8 | Flood zone | `check_flood_zone` | D12 | `{flood_zone, ...}` or None |
| A9 | Justice40 flag | `check_justice40` | D11 | `{is_disadvantaged, ...}` |
| A10 | Seismic | `check_seismic_hazard` | D13 | `{seismic_design_category, ss, s1, ...}` |
| A11 | NLCD land cover | `check_land_cover` | D8 | class label |
| A12 | OSM landuse | `check_osm_landuse` | D9 | tag |
| A13 | Utility industrial rate | `data_queries.get_utility_rate` | D14, A6 output | `{industrial_rate_cents, ...}` or None |
| A14 | IX queue | `data_queries.get_interconnection_queue` | D15 | list |
| A15 | Nearby DC projects | `data_queries.get_nearby_dc_projects` | D17, D18 | list |
| A16 | Grid energy mix | `data_queries.get_grid_energy_mix` | D16 | `{coal_pct, gas_pct, ...}` |
| A17 | DC tariffs (utility-specific) | `reference_data.get_dc_tariffs` | D19, A6 | list |
| A18 | State incentives | `reference_data.get_state_incentives` | D20 | `{sales_tax, property_tax, income_tax, investment_threshold_m, ...}` |
| A19 | CDD | `reference_data.get_cooling_degree_days` | D21 | number |
| A20 | Land value | `reference_data.get_land_value` | D22 | $/acre |
| A21 | Grid adequacy heuristic | `grid_assessment.assess_grid` | A1, A2, I1.target_mw | `{max_mw, confidence, narrative, upgrade_needed, score}` |
| A22 | Factor scoring | `dc_site_report.compute_scores` | A21 + all environmental + rates + incentives + tariffs | `{Grid Access, Utility Rate, Fiber/Telecom, Water, Transportation, Tax Incentives, DC Tariff Risk, Environmental}` each 1–5 |
| A23 | Overall weighted score | `dc_site_report.main` lines 256–260 | A22 | 0–5 float |

### Layer 4 — Outputs (O*)

| ID | Element | Code | Artifact |
|---|---|---|---|
| O1 | Markdown report | `report_template.generate_report` | 14-section `.md` |
| O2 | Research links | `research_links.generate_research_links` | Halcyon + Google URLs embedded in O1 |
| O3 | Word export | `export_docx.py` | `.docx` with styled tables + clickable hyperlinks |
| O4 | Auto-save | `dc_site_report.main` lines 271–277 | `reports/<slug>.md` |

## Dependency graph (who reads what)

```
A21 (grid) ◄── A1, A2, I1
A22 (scores) ◄── A21, A8, A7, A9, A10, A13, A14 via d, A17, A18, plus A5 (fiber, water, highways)
A23 (overall) ◄── A22
O1 ◄── everything in d
O2 ◄── A6, I1, state
```

Note: every analyzer is called unconditionally. There is no circuit-breaker when an upstream element returns None — downstream elements defensively default to score 2–3.

## Constants & weights worth flagging

These are hard-coded values that materially drive outputs but are not parameterized:

- **Scoring weights** (`dc_site_report.py:256-258`): Grid 20, Rate 15, Env 15, Tariff 15, Incentives 15, Fiber 10, Water 5, Transport 5
- **Rate score thresholds** (¢/kWh): <4 → 5, <6 → 4, <8 → 3, <10 → 2, ≥10 → 1
- **Proximity thresholds** (km): differ by element (fiber <5/<15, water <5/<15/<30, highway <5/<15/<30)
- **Voltage → MW tiers** (`grid_assessment.VOLT_TIERS`): 735+ → 1500, 500 → 800, 345 → 500, 220-287 → 200, 100-161 → 100, <100 → 50
- **MW multipliers**: substation <5 km → ×1.2; ≥2 HV lines → ×1.3
- **Default radius**: 30 km for most queries, 50 km for gas/nearby DCs, 150 km for planned substations
- **$8M/MW** (EEI parsing, not in this repo): infrastructure-only ratio

Every one of these is a candidate for calibration (see scorecard).
