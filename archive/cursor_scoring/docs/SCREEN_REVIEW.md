# Screen Methodology Review

Index of methodology reviews for each screen in [scoring.py](../scoring.py). Each entry links to a per-screen brief in [screen_methodology/](screen_methodology/) documenting what the screen tests, current thresholds, observed failure modes, the Tighten / Qualitative / Hybrid choice, and the calibration hook.

## Legend

- **Tighten**: keep as a deterministic deal-killer; improve thresholds, tier P by sub-condition, and/or add a data source.
- **Qualitative**: remove from `DEAL_KILLERS` math; surface as narrative color in the report with evidence.
- **Hybrid**: keep a deterministic core but expand the qualitative envelope in the report.

## Screens reviewed

| Date | Screen | Tier | Category | Recommendation | Brief | Code change |
|---|---|---|---|---|---|---|
| 2026-04-24 | grid_severely_insufficient | 1 | grid | Tighten | [brief](screen_methodology/grid_severely_insufficient.md) | tiered P by deficit severity + suppression evidence in output |
| 2026-04-24 (rev) | **power_outlook_doubtful** (replaces `grid_severely_insufficient`) | 1 | grid | Qualitative | [brief](screen_methodology/grid_severely_insufficient.md) | Retired the MW-deficit tiering (precision without accuracy). New qualitative `grid_outlook` classifier: promising / neutral / doubtful from brownfield, planned substations, large existing substations, state IX queue, and announced-DC pressure. Flat P=0.40 on doubtful. |
| 2026-04-24 | onerous_tariff_deposit | 1 | tariff | Hybrid | [brief](screen_methodology/onerous_tariff_deposit.md) | new `deposit_severity` rubric (light/moderate/onerous/prohibitive); tiered P |
| 2026-04-24 | utility_moratorium + regulatory_interconnection_pause | 1 | tariff/regulatory | Tighten | [brief](screen_methodology/moratoriums.md) | lift-proximity scaling on regulatory pause P |
| 2026-04-24 | brownfield_interconnection | 1 | alt-power | Tighten | [brief](screen_methodology/brownfield_interconnection.md) | radius 5 -> 10 km; tiered opportunity boost by capacity ratio |
| 2026-04-24 | cluster signal | 2 | alt-power | Tighten | [brief](screen_methodology/cluster_signal.md) | MW-weighted threshold OR count threshold |
| 2026-04-24 | btm_gas_viable | 2 | alt-power | Tighten | [brief](screen_methodology/btm_gas_viable.md) | suppression blocked in severe-nonattainment counties; tenant gate retained |
| 2026-04-24 | grid_minor_deficit | 2 | grid | Retired | [brief](screen_methodology/grid_minor_deficit.md) | Subsumed by `grid_outlook` (no middle-tier killer remains; neutral verdict adds no risk). |
| 2026-04-24 | high_industrial_rate | 2 | market | Tighten | [brief](screen_methodology/high_industrial_rate.md) | rate > 1.25x national industrial avg OR > 14c (absolute floor retained) |
| 2026-04-24 | flood_zone_av | 3 | environmental | Hybrid | [brief](screen_methodology/flood_zone_av.md) | keep A/V as killer; add X-shaded (500-yr) as narrative |
| 2026-04-24 | severe + marginal nonattainment | 3 | environmental | Mixed (severe=Tighten, marginal=Qualitative) | [brief](screen_methodology/nonattainment.md) | retire marginal as killer; keep severe; narrative both |
| 2026-04-24 | high_seismic | 3 | environmental | Tighten | [brief](screen_methodology/high_seismic.md) | tiered P by SDC class (D vs E/F) |
| 2026-04-24 | justice40_disadvantaged | 3 | regulatory | Qualitative | [brief](screen_methodology/justice40_disadvantaged.md) | retire from DEAL_KILLERS; keep as narrative block |
| 2026-04-24 (rev) | **Grid Access scorecard** (1-5) | scorecard | grid | Qualitative | [brief](screen_methodology/grid_access_score.md) | Retired the `max_mw / target_mw` derivation. Now mapped from `grid_outlook` verdict + observable HV proximity. Ends the back-door reuse of the same heuristic the killer rewrite retired. |
| 2026-04-24 (rev) | **Utility Rate scorecard** (1-5) | scorecard | market | Tighten | [brief](screen_methodology/utility_rate_score.md) | Replaced absolute-cents banding with state-relative quantile + absolute floor. Mirrors the killer-side state-relative logic; ends the Cal-vs-NM blindness. |
| 2026-04-24 (rev) | **Water scorecard** (1-5) | scorecard | resources | Hybrid | [brief](screen_methodology/water_score.md) | Coarsened to 3 tiers + arid-state cap + report disclaimer. Acknowledges the underlying signal is civic-infrastructure proximity, not process-water capacity. |
| 2026-04-24 | **P-values audit** | meta | all | Documentation | [brief](screen_methodology/p_values_audit.md) | Inventory of every catalog P value with evidential basis (A/B/C/D grading). Identifies `flood_zone_av` flat 0.50 and `power_outlook_doubtful` flat 0.40 as the highest-leverage candidates for future calibration. |

## Brief template

See [screen_methodology/_TEMPLATE.md](screen_methodology/_TEMPLATE.md). The template has 11 sections so reviews stay directly comparable.

## Post-review state of `DEAL_KILLERS`

After this review pass (including the 2026-04-24 grid-methodology rewrite), the catalog is **8 killers** (down from 11):

- Retired: `marginal_nonattainment` (fired on essentially every urban/suburban site -- no signal value).
- Retired: `justice40_disadvantaged` (same failure mode; also policy-volatile).
- Retired: `grid_minor_deficit` (subsumed by qualitative `grid_outlook`; no middle-tier killer).
- Replaced: `grid_severely_insufficient` -> `power_outlook_doubtful` (qualitative supply-vs-demand classifier; see below).
- All three retired killers retain narrative surfaces where relevant (`marginal_nonattainment_narrative`, `justice40_narrative`); `grid_outlook`'s supply/demand signals are surfaced in the Power Path section of every report.

Surviving 8 killers: `utility_moratorium`, `regulatory_interconnection_pause`, `onerous_tariff_deposit`, `power_outlook_doubtful`, `flood_zone_av`, `severe_nonattainment`, `high_seismic`, `high_industrial_rate`.

Alt-power signals (cluster, brownfield, BTM gas) are NOT deal-killers. Brownfield and cluster feed `grid_outlook` as supply signals; BTM gas acts as an explicit suppressor on `power_outlook_doubtful` for credit-worthy tenants; cluster and brownfield also drive the Opportunity boosts.

## Architecture change: dynamic probability

A `DealKiller.probability_fn: Callable[[dict], float] | None` lets base P be computed from site context (SDC class, rate severity, lift-date proximity, deposit severity). Five of the eight surviving killers use dynamic P:

| Killer | Dynamic P logic |
|---|---|
| `power_outlook_doubtful` | **No tiering.** Flat 0.40 by design -- the underlying judgment is coarse; we don't pretend to subdivide it. |
| `onerous_tariff_deposit` | light / moderate / onerous / prohibitive -> 0.05 / 0.15 / 0.30 / 0.50 |
| `regulatory_interconnection_pause` | <=6 / <=12 / <=24 / >24 months to lift -> 0.30 / 0.55 / 0.70 / 0.85 |
| `severe_nonattainment` | Serious / Severe / Extreme -> 0.30 / 0.40 / 0.55 |
| `high_seismic` | SDC D / E / F -> 0.05 / 0.15 / 0.30 |
| `high_industrial_rate` | rate > 20 c/kWh -> 0.25, else 0.15 |

The old `DealKiller.adjusted_probability(tenant)` method is retained as a back-compat alias.
