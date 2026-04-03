# Handover — 2026-04-03

## Session Summary
Built a complete DC site pre-feasibility analysis CLI tool from scratch, enriched the data_centers.csv with 62 EEI projects, and created a prospectus review workflow. Also began integrating Halcyon regulatory search for automated due diligence.

## What We Were Working On
End-to-end data center site analysis tooling: from EEI document parsing → database enrichment → spatial analysis tool → environmental layers → prospectus review → regulatory research automation.

## What Got Done
- **EEI Data Enrichment**: Parsed FERC filing (EEI March 2026 Large Load Projects) and added 62 new DC entries to data_centers.csv (22 → 84 entries), with MW estimates using $8M/MW infrastructure cost ratio
- **Transmission Grid Analysis**: Cross-referenced all 84 DCs against HIFLD transmission lines (94,619 segments) to identify nearby substations and voltage adequacy
- **DC Site Analysis Tool** (`dc-site-analysis/`): 10 Python files, fully functional CLI
  - GeoJSON → Parquet spatial cache (9 layers, ~267 MB, sub-second queries via DuckDB)
  - 14-section markdown report: power, utility, tariffs, incentives, land use, environmental, gas, water, transport, telecom, interconnection queue, nearby DCs, research links, scoring
  - NLCD land cover + OSM landuse tags for zoning assessment
  - EPA NAAQS nonattainment zones (5 pollutants)
  - Justice40 EJ screening (73,767 census tracts)
  - USGS seismic hazard API (ASCE 7-22 design parameters)
  - Cooling degree days + USDA land values by state
  - Planned substation grid buildout (1,012 substations from energy_analytics.duckdb)
  - Grid energy mix from generation_fuel_mix data
  - Annual energy cost projections (PUE × capacity factor × rate)
- **Research Links**: Deep-linkable Halcyon URLs (`/workspaces/preview?keyword=term1,term2`) + Google site-search for FERC, state PUC, EPA, county permits
- **Word Export** (`export_docx.py`): Markdown → formatted .docx with clickable hyperlinks, styled tables, navy headings
- **Prospectus Review Skill** (`/review-prospectus`): Reads PDFs, extracts structured claims, runs site analysis, produces validation matrix with red flags
- **First Prospectus Review**: Decatur Commerce Park (QueenAnne Realty, 274 MW) — validated Ameren Boxcar Study claims, flagged 7 red flags including no anchor tenant
- **Halcyon Research Skill** (`/halcyon-research`): Chrome-driven search automation for regulatory filings
- **GitHub Repos**: Both `dc-site-analysis` (public) and `data-center-demand-analysis` (private) pushed

## In Progress / Uncommitted Work
- `halcyon-research.md` skill is created but the Chrome automation workflow needs refinement:
  - Commission filter doesn't work via URL param (needs UI click)
  - Document detail pages require free Halcyon account sign-in
  - The AI summaries on search results are rich enough to extract info without opening docs
- The Halcyon skill command file is committed but not the latest research_links.py changes
- Scoring model redesign discussed (deal-killer probability-weighted approach) but NOT yet implemented

## Blocked / Pending
- **Halcyon sign-in**: Need user to create free Halcyon account to access full document text via Chrome automation
- **Scoring redesign**: User proposed probability-weighted deal-killer scoring (moratorium=90% block, nonattainment=25%, etc.) with `Feasibility = Opportunity × (1 - Combined Risk)`. Agreed on concept, not yet coded.
- **FEMA flood data**: The Esri-hosted reduced flood dataset has coverage gaps. Direct FEMA NFHL endpoint returned 404. Need alternate flood data source.
- **HIFLD substations**: The GeoJSON only covers NE US (8,712 substations). Workaround: using `planned_transmission_substations` from energy_analytics.duckdb (1,012 nationwide). Full HIFLD substations not available via their current ArcGIS services.

## Bugs & Fixes
- **GeoJSON geometry type mismatch**: Transmission lines were `LineString` not `MultiLineString` — grid indexing only captured 141/94,619. Fixed by handling both types.
- **DMS coordinate parsing**: CSV had escaped quotes (`\'`) that regex didn't match. Fixed parser.
- **CSV column misalignment**: Two rows (Consumers Energy MI, Dominion Richmond VA) got shifted columns when appending via heredoc. Fixed with Python CSV writer.
- **Parquet cache column names**: Gas pipelines used `FID` not `OBJECTID`, cell towers used `Licensee`/`LocCity` not `LICENSEE`/`CITY`. Fixed by checking actual GeoJSON field names.
- **Word hyperlinks**: Initially rendered as blue text only, not clickable. Fixed by creating proper `w:hyperlink` XML elements with external relationship IDs.
- **Halcyon search**: Single keyword tag with spaces treated as one phrase. Fixed by using comma-separated tags (`keyword=term1,term2`).

## Key Decisions
- **$8M/MW ratio** for estimating MW from EEI dollar amounts (infrastructure-only, not all-in with chips which is ~$30M/MW)
- **Parquet + DuckDB spatial** over PostGIS/Docker — enables standalone operation, sub-second queries, ~267 MB cache vs 4.8 GB raw GeoJSON
- **NLCD + OSM dual approach** for land use: NLCD gives satellite baseline (always available), OSM gives community-mapped zoning (when mapped)
- **On-demand FEMA/USGS queries** vs bulk download for flood zones and seismic — these APIs are small per-point queries
- **Halcyon over Google** for regulatory research links — 6M+ indexed filings vs Google's web crawl
- **Report auto-saves** to `reports/` with slugified filename on every run

## Gotchas & Lessons Learned
- HIFLD substation GeoJSON only covers NE US (NY/PA/VA/MD/NJ/New England) — the `direct_url` download returned a partial dataset. The full dataset is no longer available via HIFLD ArcGIS services.
- Halcyon URL params: `keyword=` accepts comma-separated tags, default strategy is "All of". Commission filter does NOT work via URL param.
- Halcyon requires free account to view individual documents, but the AI summaries on search results pages contain substantial extracted content.
- The EEI dollar figures are inconsistent — some include chips, some don't. Three tiers: $4-7M/MW (shell), $10-15M/MW (fit-out), $20-37M/MW (all-in).
- Nominatim geocoding sometimes returns incorrect points for commercial park addresses — verify with parcel ID.
- DuckDB spatial extension handles `ST_Read` of GeoJSON well but is slow on raw files (18s for highways). Parquet pre-processing is essential.

## Important Files
| File | Purpose |
|------|---------|
| `/Users/bencarron/Projects/dc-site-analysis/dc_site_report.py` | Main CLI entry point |
| `/Users/bencarron/Projects/dc-site-analysis/prepare_spatial_cache.py` | GeoJSON → Parquet converter |
| `/Users/bencarron/Projects/dc-site-analysis/spatial_queries.py` | DuckDB spatial queries (infrastructure + environmental) |
| `/Users/bencarron/Projects/dc-site-analysis/data_queries.py` | Rates, queue, nearby DCs, grid energy mix |
| `/Users/bencarron/Projects/dc-site-analysis/reference_data.py` | 17 DC tariffs + 31 state incentives + CDD + land values |
| `/Users/bencarron/Projects/dc-site-analysis/research_links.py` | Halcyon + Google research link generator |
| `/Users/bencarron/Projects/dc-site-analysis/report_template.py` | 14-section markdown report builder |
| `/Users/bencarron/Projects/dc-site-analysis/grid_assessment.py` | Voltage-tier MW capacity heuristic |
| `/Users/bencarron/Projects/dc-site-analysis/export_docx.py` | Markdown → Word with hyperlinks |
| `/Users/bencarron/Projects/dc-site-analysis/download_environmental_data.py` | EPA NAAQS + Justice40 downloader |
| `/Users/bencarron/Projects/dc-site-analysis/geocoder.py` | Nominatim with file cache |
| `/Users/bencarron/Projects/dc-site-analysis/reports/prospectus_decatur_commerce_park.md` | First prospectus review |
| `/Users/bencarron/.claude/commands/review-prospectus.md` | Prospectus review skill |
| `/Users/bencarron/.claude/commands/halcyon-research.md` | Halcyon research skill |
| `/Users/bencarron/Projects/data-center-demand-analysis/data/raw_documents/data_centers.csv` | 84-entry DC database |
| `/Users/bencarron/Projects/dc-site-mapper/data/energy_analytics.duckdb` | Energy market data (rates, queue, planned substations) |
| `/Users/bencarron/Projects/dc-site-mapper/data/demand_ledger.duckdb` | DC project tracking (1,338 projects) |
| `/Users/bencarron/Documents/Professional/Weiss Realty/Decatur, IL/` | Decatur prospectus review Word doc |

## Next Steps
1. **Implement deal-killer scoring model**: Replace current weighted-average scoring with `Feasibility = Opportunity × (1 - Combined Risk)` where deal-killers (moratorium, grid insufficiency, flood zone, nonattainment) have probability weights
2. **Complete Halcyon research automation**: Sign into Halcyon, then the `/halcyon-research` skill can open documents, extract content, and compile findings into the prospectus review
3. **Fix commission filter in Halcyon URLs**: The `commission=` URL param doesn't work; need to click the commission dropdown via Chrome automation
4. **Find better flood data source**: Current FEMA endpoint has gaps; consider downloading state-level NFHL shapefiles for key markets
5. **Add more prospectus reviews**: Test the `/review-prospectus` workflow on additional sites to refine the skill

## Context for Next Session
- Working directory: `/Users/bencarron/Projects/dc-site-analysis/`
- GitHub: `benjaminpcarron-sys/dc-site-analysis` (public), `benjaminpcarron-sys/data-center-demand-analysis` (private)
- All spatial cache is built and ready (9 parquet files in `data/cache/`)
- Environmental data downloaded (NAAQS + Justice40 in `data/downloads/` and `data/cache/`)
- Chrome may still be open on `app.halcyon.io` from the research session
- The user is evaluating a Decatur, IL data center investment (QueenAnne Realty / Weiss Realty deal, 274 MW at 2500 N 22nd St)
- User receives investment prospectuses regularly and wants to run them through this tool
- User subscribes to Halcyon's newsletter (Nat Bullard) but not the paid data trackers
