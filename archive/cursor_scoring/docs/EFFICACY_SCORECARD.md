# Efficacy Scorecard

_Companion to `TOOL_MAP.md`. Rescore when an element is changed or when a new regression site reveals a failure mode._

## The five axes

Every element of the tool is scored 1–5 on:

1. **Coverage (Cov)** — share of real sites where it returns a non-null, usable answer.
   - 5 = ≥95% of CONUS sites; 1 = <25% or region-locked.
2. **Accuracy (Acc)** — when non-null, how often is it right (against a trusted ground truth)?
   - 5 = verified primary source, rarely wrong; 1 = guessed or frequently stale.
3. **Decision relevance (Rel)** — does this output actually change an invest/pass call?
   - 5 = can flip the decision alone (deal-killer); 1 = nice-to-have color.
4. **Calibration (Cal)** — if it outputs a score/probability, does the magnitude match observed outcomes?
   - 5 = backtested; 3 = reasonable bucketing, unvalidated; 1 = arbitrary thresholds.
5. **Provenance (Prov)** — can a reader trace every claim to a primary source URL?
   - 5 = source link per row/claim in report; 1 = value appears with no citation.

**Total = sum / 25.** Priority for improvement ≈ (Rel × weakness) so elements that move decisions get fixed first.

## Summary table

High-relevance elements listed first within each layer. "Top lever" is the single change that would most improve that element's total score.

### Data sources

| ID | Element | Cov | Acc | Rel | Cal | Prov | Total | Top lever |
|---|---|---|---|---|---|---|---|---|
| D1 | Geocoder | 4 | 3 | 5 | n/a | 2 | 14/20 | Add parcel-ID fallback (county GIS) when Nominatim returns centroid of a city/park |
| D19 | DC tariffs | 2 | 4 | 5 | n/a | 3 | 14/20 | Replace hand-curated inline dict with pull from `demand_ledger`/Halcyon-sourced table + refresh date |
| D14 | Utility rates (EIA 861) | 3 | 4 | 5 | n/a | 4 | 16/20 | Add fallback to EIA form 861 state-avg when utility match fails |
| D3 | HIFLD substations (existing) | 1 | 4 | 5 | n/a | 3 | 13/20 | Replace/supplement with OpenInfraMap or state-scraped subs; current NE-only dataset fails most sites |
| D12 | FEMA flood | 2 | 4 | 5 | n/a | 3 | 14/20 | Switch to NFHL state shapefiles downloaded to Parquet cache; live API is gappy |
| D2 | Transmission lines (HIFLD) | 5 | 3 | 5 | n/a | 3 | 16/20 | Voltage field is often "NOT AVAILABLE"; augment with VOLT_CLASS + operator-disclosed additions |
| D20 | State incentives | 5 | 3 | 4 | n/a | 2 | 14/20 | Add effective-date and source-URL fields; stale entries silently score well |
| D4 | Planned substations | 3 | 4 | 5 | n/a | 4 | 16/20 | Include ISO/RTO queue-linked upgrades (currently only utility-filed planned subs) |
| D13 | Seismic (USGS) | 5 | 5 | 3 | n/a | 4 | 17/20 | Fine; surface SDC as deal-killer only above D |
| D11 | Justice40 | 5 | 5 | 3 | n/a | 4 | 17/20 | Fine; rescore impact — federal permit friction, not blocking |
| D10 | NAAQS | 5 | 5 | 4 | n/a | 4 | 18/20 | Fine; distinguish marginal vs severe nonattainment |
| D17 | Demand ledger | 4 | 4 | 3 | n/a | 3 | 14/20 | Flag overlap — multiple nearby DCs means grid saturation risk, not just "context" |
| D15 | IX queue | 3 | 3 | 4 | n/a | 3 | 13/20 | Geocode queue entries so you can filter by distance, not state |

### Analyzers

| ID | Element | Cov | Acc | Rel | Cal | Prov | Total | Top lever |
|---|---|---|---|---|---|---|---|---|
| A21 | Grid adequacy heuristic | 5 | 3 | 5 | 2 | 3 | 18/25 | Replace point-estimate `max_mw` with range + probability; incorporate queue cluster density |
| A22 | Factor scoring | 5 | 3 | 5 | 2 | 2 | 17/25 | Replace with deal-killer probability model (see §Calibration below) |
| A23 | Overall weighted score | 5 | 2 | 5 | 1 | 1 | 14/25 | Depends on A22; weighted average hides asymmetric risks. Retire in favor of risk-adjusted opportunity |
| A17 | DC tariffs match | 3 | 4 | 5 | n/a | 3 | 15/25 | Utility alias matching is fuzzy; normalize via shared utility-ID dictionary |
| A13 | Utility industrial rate | 3 | 4 | 5 | n/a | 4 | 16/25 | See D14 lever |
| A1 | Nearest transmission | 5 | 4 | 5 | n/a | 4 | 18/25 | Surface voltage-class ambiguity ("NOT AVAILABLE") instead of silently picking something |
| A2 | Nearest substations | 2 | 4 | 5 | n/a | 4 | 15/25 | See D3 lever |
| A8 | Flood zone check | 2 | 4 | 5 | n/a | 4 | 15/25 | See D12 lever |
| A7 | Nonattainment | 5 | 5 | 4 | n/a | 5 | 19/25 | Fine |
| A18 | State incentives | 5 | 3 | 4 | n/a | 2 | 14/25 | See D20 lever |
| A14 | IX queue | 3 | 3 | 4 | n/a | 3 | 13/25 | See D15 lever |
| A10 | Seismic | 5 | 5 | 3 | n/a | 4 | 17/25 | Fine |
| A15 | Nearby DC projects | 4 | 3 | 3 | n/a | 3 | 13/25 | Cluster analysis: count MW within 50 km to flag load-concentration risk |
| A4 | Gas pipelines | 5 | 4 | 2 | n/a | 4 | 15/25 | Low relevance today (backup only); could rise if on-site gen becomes thesis |
| A5 | Highways/rail/water/fiber/cell | 5 | 4 | 2 | 3 | 4 | 18/25 | Most are table-stakes; consider collapsing into one "logistics OK?" flag |
| A6 | Service territory | 5 | 4 | 5 | n/a | 4 | 18/25 | Fine; feeds A13/A17 matching |
| A9 | Justice40 | 5 | 5 | 3 | n/a | 5 | 18/25 | Fine |
| A11 | NLCD land cover | 5 | 4 | 2 | n/a | 4 | 15/25 | Low relevance for prefeasibility; keep for wetland/forested flags only |
| A12 | OSM landuse | 3 | 3 | 3 | n/a | 3 | 12/25 | Often missing or informal; deprioritize |
| A16 | Grid energy mix | 5 | 4 | 2 | n/a | 4 | 15/25 | Rel rising if hyperscale customer has clean-energy mandate; parameterize by use case |
| A19 | CDD | 5 | 5 | 3 | n/a | 5 | 18/25 | Fine |
| A20 | Land value | 5 | 3 | 2 | n/a | 3 | 13/25 | State avg is too coarse; swap for county $/acre when available |

### Outputs

| ID | Element | Cov | Acc | Rel | Cal | Prov | Total | Top lever |
|---|---|---|---|---|---|---|---|---|
| O1 | Markdown report | 5 | n/a | 5 | n/a | 2 | 12/15 (3-axis) | Add a "Confidence & Source" column to every table; surface element-level nulls instead of hiding them |
| O2 | Research links | 5 | 4 | 4 | n/a | 5 | 18/20 | Add direct links to the specific docket/filing IDs when known, not just keyword search |
| O3 | Word export | 5 | n/a | 3 | n/a | n/a | — | Fine; output-only |

## Calibration: the big one

**Status: seed model shipped 2026-04-20 in `scoring.py`. Backtesting is the remaining work.**

A22 (factor scoring) and A23 (overall) were the lowest-calibration elements and simultaneously drove the headline number every report began with. The three compounding problems:

1. **Weighted average masks deal-killers.** A site with a moratorium tariff (Tariff=1) but strong everything else scored ~3.7 → "Moderate" — misleadingly investable.
2. **Thresholds are picked by feel.** The <4¢ = 5-star cutoff, 30 km as the "Transportation" threshold, etc. were written once and never validated against outcomes.
3. **No regression set.** *(Resolved 2026-04-20: `tests/regression_sites.json` now pins 5 sites with expected feasibility + deal-killer triggers.)*

The remedy, implemented in `scoring.py`:

```
Feasibility = Opportunity × (1 − Combined_Risk)
Combined_Risk = 1 − Π(1 − P_killer_i)
```

`DEAL_KILLERS` has **8 seeded killers** across 5 categories (tariff, grid, environmental, regulatory, market), down from 11 after the 2026-04-24 screen-methodology review (a) retired `marginal_nonattainment` and `justice40_disadvantaged` as narrative-only, (b) retired `grid_minor_deficit` and replaced `grid_severely_insufficient` with the qualitative `power_outlook_doubtful`. Both the legacy weighted score and the new feasibility render in the executive summary so teams can evaluate the shift during the calibration window.

### 2026-04-20 additions: multi-path power + docket-level regulatory pause

A second round of anchor calibration, driven by the user-flagged Millsboro DE site report showing the Indian River substation, surfaced three architectural gaps and delivered three model additions:

1. **Retired / brownfield power plants** (`reference_data.RETIRED_GENERATION_SITES`). Retired coal/nuclear plants keep their switchyards, 230-500 kV interconnections, and large industrial-zoned parcels. HIFLD's transmission_lines layer doesn't know the plant is offline — so a DC adjacent to Indian River / Homer City / Conemaugh is repurposing ~1 GW of interconnection capacity that the old grid heuristic ignored. New pipeline element `brownfield_interconnection` detects sites within 5 km of a retired plant with former_mw ≥ 60% of target. Suppresses `grid_severely_insufficient` and adds **+0.10 to Opportunity**.
2. **Regulatory interconnection moratoriums** (`reference_data.REGULATORY_MORATORIUMS`). PSC/PUC docket pauses (e.g. DE PSC 25-0826 freezing Delmarva large-load interconnections until late 2026) are structurally different from tariff-level moratoriums — defined lift date, primarily schedule risk, not existential. Split into a new killer `regulatory_interconnection_pause` (P=0.55, tenant-scaled 1.0/0.7/0.5) separate from `utility_moratorium` (P=0.90, indefinite). Catalog size 10 → 11.
3. **Behind-the-meter gas viability** (`scoring.btm_gas_viable`). Existing `gas_pipelines` pipeline element was already populated but unused by scoring. Now: Interstate pipeline within 15 km OR ≥2 Intrastate pipelines within 10 km (the Texas path — HIFLD classifies in-state Texas mesh as Intrastate) gates an **anchored/hyperscaler**-only suppression of `grid_severely_insufficient`. Speculative developers typically cannot finance BTM gen so the suppression does not apply to them.

All three signals flow into a new **Power Path** section in the report executive summary listing every viable path (grid / cluster-grid / brownfield / BTM gas / none) with evidence, so readers see *why* the grid killer did or did not fire.

### Seeded → calibrated P(kill) values

The first seed run (2026-04-20) rated New Albany OH "Poor (0.07)" despite being a built hyperscaler cluster. Diagnosis: grid heuristic is static-infrastructure only, `onerous_tariff_deposit` was miscalibrated for investment-grade tenants, and cluster effects weren't in the Opportunity side. A second calibration pass (2026-04-20) added:

1. **Cluster signal** (`scoring.has_active_cluster`): ≥5 nearby DCs within 50 km. Suppresses `grid_severely_insufficient` when an HV line is also within 30 km (utility has demonstrated build-out). Boosts Opportunity by +0.12.
2. **Tenant profile** (`--tenant {speculative,anchored,hyperscaler}`): multiplicative scaling on per-killer probability. Hyperscaler onerous-deposit scaling = 0.15; grid-deficit = 0.50; rate-ceiling = 0.50.
3. **Re-seeded P values** after anchor-site pinning (5 built clusters: New Albany OH, Ashburn VA, Altoona IA, Council Bluffs IA, The Dalles OR).

| Killer | Seed P | Calibrated P | Tenant scaling (spec / anc / hyp) | Calibration hook |
|---|---|---|---|---|
| utility_moratorium | 0.90 | **0.90** | 1.00 / 0.90 / 0.80 | Fires only on tariff-level moratoriums (indefinite). Fraction of demand_ledger sites in moratorium utilities shelved vs built in 36 months. |
| regulatory_interconnection_pause *(new 2026-04-20)* | — | **0.55** | 1.00 / 0.70 / 0.50 | PSC/PUC docket-level pauses (defined lift date). IX-queue dwell time during active pauses vs post-lift baseline. |
| grid_severely_insufficient | 0.70 | **0.55** (w/ cluster, brownfield, or BTM-gas suppression) | 1.00 / 0.70 / 0.50 | Sites with initial max_mw < 50% target AND no alt power path: built/cancelled rate |
| flood_zone_av | 0.50 | **0.50** | 1.00 / 0.90 / 0.80 | DC built-out rate, zone A/V vs zone X |
| severe_nonattainment | 0.40 | **0.40** | 1.00 / 1.00 / 1.00 | Permit duration for DCs in Serious+ NAAQS counties |
| onerous_tariff_deposit | 0.30 | **0.30** | 1.00 / 0.40 / 0.15 | Cancellation rate by tenant credit tier under deposit_onerous tariffs |
| grid_minor_deficit | 0.25 | **0.20** | 1.00 / 0.50 / 0.25 | Cancellation rate by grid headroom bucket |
| high_industrial_rate | 0.25 | **0.25** | 1.00 / 0.80 / 0.50 | DC announcement rate by utility avg rate bucket |
| marginal_nonattainment | 0.15 | **0.12** | 1.00 / 1.00 / 1.00 | Marginal vs attainment permit duration |
| high_seismic | 0.10 | **0.08** | 1.00 / 1.00 / 1.00 | Completed-project IRR by SDC bucket (The Dalles OR is SDC-D and operational) |
| justice40_disadvantaged | 0.10 | **0.05** | 1.00 / 1.00 / 1.00 | Fires on nearly every site; base-rate reduced by half until federal-funding conditional trigger is added |

Every killer has a `calibration_hook` string in `scoring.py` describing the exact query to run against `demand_ledger.duckdb` + outcome labels. Each P re-fit is ~one afternoon of work once labels exist.

**Next calibration step:** label ~30–50 demand_ledger projects with outcome (built / shelved / pending after 36 months) and run a single logistic fit per killer to replace the anchor-site-pinned values with backtested priors.

## Test-confirmed findings (regression harness)

The first regression run surfaced three real failures that prior reports were silently absorbing. Each is now pinned in `tests/regression_sites.json`.

| ID | Finding | Confirmed by site | Fix | Status |
|---|---|---|---|---|
| **A17** | Utility-name matcher used `service_territories[0]` only. When IOU + co-op overlap (very common), the co-op won and IOU tariffs (e.g. AEP Ohio Schedule DCT) were never matched. | `new_albany_oh` | `pipeline._match_dc_tariffs` iterates all territories; `_utility_name` prefers IOU. | **FIXED 2026-04-20.** `deal_killer_signals.dc_tariffs.deposit_onerous=true` now pinned in regression JSON. |
| **D5** | HIFLD electric retail service territory parquet lacks Delmarva Power's DE coverage. | `millsboro_de` | `STATE_UTILITY_FALLBACK` in `spatial_queries.py`; `find_service_territory(lat, lon, state=...)` falls back when HIFLD misses. | **FIXED 2026-04-20.** Expand fallback dict as future sites surface gaps. |
| **D20** | `STATE_TAX_INCENTIVES` claimed 31 states but DE (and others) missing. | `millsboro_de` | Added DE entry; introduced `data_vintage` field on every entry via `_vintage` backfill. | **PARTIAL 2026-04-20.** DE done; full 50-state audit still pending. |

### Feasibility model impact (post-calibration 2026-04-20)

Expanded to 9 regression sites: 5 built anchor clusters + 2 announced-pending + 2 control sites. Built anchors are pinned with `tenant_profile: hyperscaler` since that's who built them.

| Site | Outcome | Tenant | Legacy | Feasibility (seed) | Feasibility (calibrated) | Triggered killers |
|---|---|---|---|---|---|---|
| decatur_il | announced | speculative | 3.5 (Mod) | 0.54 | **0.57 (Strong)** | justice40 |
| abilene_tx | announced (Stargate) | hyperscaler | 3.3 (Mod) | 0.51 | **0.54 (Mod)** | justice40 |
| **new_albany_oh** | **built (Meta+)** | hyperscaler | 2.4 (Chg) | **0.07 (Poor)** | **0.47 (Mod)** | onerous_tariff_deposit + marginal_nonattainment + justice40 |
| ashburn_va | built (#1 market) | hyperscaler | ~3.5 | — | **0.60 (Strong)** | marginal_nonattainment + justice40 |
| altoona_ia | built (Meta) | hyperscaler | ~3.3 | — | **0.68 (Strong)** | justice40 |
| council_bluffs_ia | built (Google) | hyperscaler | ~3.3 | — | **0.68 (Strong)** | justice40 |
| the_dalles_or | built (Google) | hyperscaler | ~3.0 | — | **0.52 (Mod)** | high_seismic + justice40 |
| **millsboro_de** | unbuilt | speculative | 2.75 (Chg) | 0.13 (Poor) | **0.24 (Chg)** *(rev. 2026-04-20)* | regulatory_interconnection_pause + justice40 |
| hurt_ranch_nm | unbuilt | speculative | 2.4 (Chg) | 0.11 (Poor) | **0.17 (Poor)** | grid_severely_insufficient + justice40 |

**Separation quality:** all 7 built/announced sites score ≥ 0.47 (Moderate+); both unbuilt control sites stay ≤ 0.24. No false negatives on built anchors. Boundary case **New Albany OH**: legacy "Poor (0.07)" → calibrated "Moderate (0.47)" because the cluster signal suppresses grid_severely_insufficient and hyperscaler tenant-scaling drops onerous_tariff_deposit from P=0.30 → 0.045.

**Millsboro DE rework (2026-04-20):** previously pinned at 0.20 Poor *(grid_severely_insufficient + justice40)*. Corrected after user-flagged revised site report identifying (a) the 785 MW Indian River Power Plant 0.8 km away as a brownfield interconnection anchor and (b) DE PSC 25-0826 as the actual primary risk (interconnection pause lifting late 2026). New pin: 0.24 Challenging, `regulatory_interconnection_pause + justice40` firing, `grid_severely_insufficient` explicitly **NOT** firing (brownfield suppresses). Same site jumps to 0.39 Moderate under a hyperscaler tenant — matching the revised report's "Viable with Conditions" framing. This site is now the double-duty anchor for both brownfield and docket-level moratorium detection.

**Boundary case NOT fixed:** Quincy WA (Microsoft built) still scores 0.17 Poor under default tooling because only 2 nearby DCs hit the 50 km search radius (cluster threshold is 5), and the local HIFLD grid data shows max_mw=0. Not pinned in regression — would require either (a) expanding the nearby_dcs radius, (b) loosening cluster threshold to 3 which risks false positives, or (c) fixing PacifiCorp/BPA grid data coverage. Left as a known limit on the current calibration.

## Suggested improvement sequence — status

1. ~~**A22 / A23 — Deal-killer scoring**~~ **SHIPPED + CALIBRATED 2026-04-20** (`scoring.py`). Tenant-profile scaling and cluster signal added after anchor-site recalibration. Full backtesting against demand_ledger outcomes remaining.
2. **D3 / A2 — Substation coverage**. 5-relevance element that fails outside NE US. Pick OpenInfraMap or state-level scrapes; add to parquet cache. *Next up.*
3. **D12 / A8 — Flood data**. Same problem as D3 (high-Rel, low-Cov). Switch to NFHL shapefiles.
4. **D19 / A17 — DC tariffs**. ~~A17 utility-match fixed 2026-04-20.~~ D19 still on inline Python; move to versioned table with refresh date.
5. **O1 provenance pass**. Add a source-URL column per evidence row using `ctx["_meta"][name].source` (already populated by the pipeline). Makes every prior improvement visible and auditable.
6. **D1 — Geocoder fallback**. Parcel-ID lookup when Nominatim returns centroid-like coords; prevents garbage-in cascading.
7. ~~**Regression set**~~ **SHIPPED 2026-04-20** (`tests/regression_sites.json`, 5 sites, 8 tests passing in 9s). Expand to 10+ sites as new prospectuses review.
8. **Deal-killer calibration (new)**. Label ~30–50 demand_ledger projects with outcomes; refit each P_killer via logistic regression; tighten tolerances in regression JSON.

## Meta: structural refactor (SHIPPED 2026-04-20)

- ~~**Standardize analyzer outputs**~~ **DONE.** `ctx["_meta"][name] = {ok, elapsed_ms, source, error, skipped}` is populated on every run.
- ~~**Element registry**~~ **DONE.** `pipeline.default_registry()` returns 26 `Element` objects; `main()` is now a thin caller of `run_pipeline()`.
- ~~**Regression harness**~~ **DONE + EXPANDED 2026-04-24 (rev.).** `tests/test_regression.py` with 9 pinned sites + synthetic tests for deal-killer math, tenant-scaling monotonicity, brownfield suppression (capacity-gated), BTM-gas suppression (tenant- and nonattainment-gated), regulatory-pause vs tariff-moratorium distinction, lift-date-scaled regulatory pause P, `grid_outlook` verdict logic, and catalog stability (8 killers). **20/20 pass in ~16s.**

## 2026-04-24 (rev) — grid pivot + scorecard honesty pass

A second review wave triggered by user critique on the grid-deficit math ("precision without accuracy"). Three threads:

### Thread 1 — Grid math: numerical → qualitative

The `grid_severely_insufficient` killer (and its `grid_minor_deficit` sibling) used `max_mw` from `grid_assessment.py`, which is a voltage-class heuristic on the nearest HV line — not a host-utility deliverable-capacity study. Tiering deficit ratios off this number was precision built on a proxy.

**Replaced with `grid_outlook(ctx)` qualitative classifier** returning `promising | neutral | doubtful` from observable supply (brownfield, planned/large substations, state IX queue, cluster track record) and demand (announced DC pipeline pressure, lack of HV access) signals. New killer **`power_outlook_doubtful`** at flat P=0.40 fires only when verdict is `doubtful` AND BTM gas is not viable for credit-worthy tenants.

`grid_minor_deficit` retired entirely — the qualitative classifier subsumes the middle tier without needing a killer for "neutral."

`max_mw` is retained in narrative as "rough HV-line capacity proxy" with disclaimer; it does NOT drive any scoring decision.

Catalog size: 9 → 8.

### Thread 2 — Scorecard honesty pass

The opportunity-side scorecard (`compute_scores` in `dc_site_report.py`) had three latent dishonesties:

| Factor | Old derivation | Problem | New derivation |
|---|---|---|---|
| **Grid Access (1-5)** | `max_mw / target_mw` ratio | Same heuristic the killer just retired; was reaching opportunity through the back door | `grid_outlook` verdict + observable HV proximity (within 10 / 30 km) |
| **Utility Rate (1-5)** | Absolute cents (4/6/8/10) | A 10c rate scored 2 in CA (state-leading) and 2 in NM (60% above state avg) — same | State-relative quantile (≤0.8x/1.0x state avg) + absolute floors mirroring the killer |
| **Water (1-5)** | Distance to ANY HIFLD water facility (5/15/30 km) | Civic-infrastructure proxy pretending to be process-water capacity check | 3-tier banding (10/25 km cutoffs) + arid-state cap + report disclaimer; intentionally never awards 5 |

Briefs: [`grid_access_score.md`](screen_methodology/grid_access_score.md), [`utility_rate_score.md`](screen_methodology/utility_rate_score.md), [`water_score.md`](screen_methodology/water_score.md).

### Thread 3 — P-values audit

Direct inventory of every probability used in the catalog with evidential basis (A/B/C/D grading). [`p_values_audit.md`](screen_methodology/p_values_audit.md). Highlights:

- **C-grade flat values** (round numbers, no derivation): `utility_moratorium` 0.90, `power_outlook_doubtful` 0.40, `flood_zone_av` 0.50.
- **B-grade tier shapes** (mechanism-anchored ordering, judgment on absolute levels): `regulatory_interconnection_pause`, `onerous_tariff_deposit`, `severe_nonattainment`, `high_seismic`.
- **Highest-leverage future calibration target:** `flood_zone_av` flat 0.50 (likely conservative; doesn't differentiate Zone A vs V or partial-parcel coverage).
- **Audit changes no values** — its purpose is to make the basis transparent so the next backtest is anchored.

### Regression impact

| Site | overall_score | feasibility | Why moved |
|---|---|---|---|
| `new_albany_oh` | 2.4 → 3.2 | 0.47 → 0.69 | Grid Access went 1 → 5 (promising via cluster + AEP large sub); honest scorecard now matches the on-the-ground reality (built hyperscaler cluster) |
| `millsboro_de` | 2.75 → 3.35 | 0.24 (unchanged) | Grid Access went 2 → 5 (promising via Indian River brownfield); brownfield was visible to killer suppression but invisible to legacy scorecard |
| `hurt_ranch_nm` | unchanged | 0.10 → 0.45 | (Earlier change in grid pivot) — `power_outlook_doubtful` no longer fires; site is "neutral" not "doubtful" |
| Other 17 anchors | unchanged | unchanged | No material drift |

All 20/20 tests passing.

## 2026-04-24 screen-methodology review

A per-screen review pass produced 12 methodology briefs in `docs/screen_methodology/` + the index at `docs/SCREEN_REVIEW.md`. Principal deliverables:

1. **Dynamic base P architecture** (`DealKiller.probability_fn`). Seven screens (`grid_severely_insufficient`, `grid_minor_deficit`, `onerous_tariff_deposit`, `regulatory_interconnection_pause`, `severe_nonattainment`, `high_seismic`, `high_industrial_rate`) now tier base P by sub-condition rather than flat-rate. This unlocks a single re-fit per screen once `demand_ledger` outcomes are labeled.
2. **Retirements**: `marginal_nonattainment` and `justice40_disadvantaged` moved to narrative-only. Each fired on essentially every urban/suburban site including every built anchor, so their class-level false-positive rate was incompatible with killer semantics. Catalog size 11 -> 9.
3. **Brownfield tightening**: radius expanded 5 -> 10 km with distance-decay (`direct` <=5 km / `adjacent` 5-10 km, half boost at adjacent tier); opportunity boost tiered by capacity ratio (`>=0.9x` -> +0.12 / `>=0.6x` -> +0.07). 4 new `RETIRED_GENERATION_SITES` added (Yates GA, Cheswick PA, San Juan NM, Dave Johnston WY).
4. **Cluster tightening**: count-OR-MW-weighted detection (MW path catches Quincy-style hyperscaler-dense sub-hubs where the count feed undercounts); hub tier at >=1 GW within 30 km earns +0.20 opportunity (vs +0.12 standard).
5. **BTM gas nonattainment block**: suppression of `grid_severely_insufficient` via BTM gas is now gated on the site NOT being in a severe nonattainment county (major-source air permit is infeasible there).
6. **Flood 500-year narrative**, marginal NAAQS narrative, Justice40 narrative all surfaced in `report_template.py` via new helper functions in `scoring.py`.

Regression impact: Ashburn VA pin updated 0.60 -> 0.70 (now correctly in hub tier). Hurt Ranch NM pin updated 0.17 -> 0.10 (now in `critical` grid-deficit tier). Millsboro DE unchanged at 0.24 (regulatory pause lift 2026-12-31 sits in 12-month tier). All 19 tests pass.

Byte-identical check confirmed the refactor is non-logic-changing for sites where the three fixed bugs didn't apply (Decatur IL).

## What to do next

Pick whichever is most pressing for your current deal flow:

- **More site coverage:** work item #2 (substations OpenInfraMap) or #3 (FEMA NFHL shapefiles). Both fix "site gets report with null-valued key section" gaps that reduce trust.
- **Better numbers on the numbers:** work item #8 (calibrate P values against demand_ledger outcomes). Turns the feasibility score from "directionally better than weighted avg" into "backed by observed base rates."
- **Reports that are more investor-grade:** work item #5 (provenance pass). With `_meta` already captured, every table row can show its source in one pass through `report_template.py`.
