# Screen Methodology — `power_outlook_doubtful` (formerly `grid_severely_insufficient`)

**Status:** Rewritten 2026-04-24. The prior deficit-ratio tiering (critical / severe / high, driven by `grid_assessment.max_mw`) was retired for the reason documented in §3. This screen now runs as a qualitative supply-vs-demand judgment.

## 1. What it tests

Is the site's power picture directionally **promising** (observable supply anchors present), **doubtful** (nothing nearby to build off of AND/OR heavy competing demand with no supply offset), or **neutral**?

The prior version asked "how many MW are left?" — a question we can't honestly answer without a real host-utility system-impact study. The replacement asks a question our data can actually speak to: what infrastructure is nearby, and is the supply-demand balance leaning the site's way?

## 2. Current implementation

- **Classifier**: `scoring.grid_outlook(ctx)`. Returns `{"verdict", "supply_signals", "demand_signals", "evidence"}`.
- **Killer trigger**: `_trigger_power_outlook_doubtful` fires when `verdict == "doubtful"` AND no BTM-gas suppression applies for a credit-worthy tenant.
- **Base P**: `0.40` (flat, no ratio tiering — the underlying judgment is coarse by design).
- **Tenant scaling**: `1.0 / 0.7 / 0.5` (speculative / anchored / hyperscaler) — hyperscalers can self-finance build-out even at doubtful sites; merchants can't.
- **Inputs**: `brownfield_interconnection`, `planned_substations`, `substations`, `interconnection_queue`, `nearby_dcs`, `transmission_lines`, `gas_pipelines`, `nonattainment_zones`, `tenant_profile`.

## 3. Why the old deficit-ratio approach was retired

The prior logic was:

```
deficit_ratio = grid_assessment.max_mw / target_mw
if ratio < 0.10:     P = 0.75  (critical)
elif ratio < 0.30:   P = 0.55  (severe)
elif ratio < 0.50:   P = 0.35  (high)
```

`grid_assessment.max_mw` was computed in `grid_assessment.py` by taking the nearest transmission line, bucketing its voltage class (e.g. 500 kV → "deep bucket"), applying a distance discount, and multiplying by a substation / multiple-line factor. **This is a voltage-class heuristic, not a capacity study.** The host utility's actual deliverable capacity depends on existing dispatch, load flows, congestion constraints, and queue dwell — none of which we measure.

So what looked like precise tiering (critical vs severe vs high) was layering false precision on a rough proxy. Per user feedback:

> "I have no idea how you are determining how many MWs are left. All you are describing is how you treat the results once you make that call. This is hardly valuable and is precision without accuracy."

Fixing this required either (a) ingesting real queue + system-impact data (not feasible without utility-specific studies) or (b) changing what we ask. We chose (b): a directional call from observable infrastructure facts.

## 4. Signals in the new classifier

### Supply (+)

| Signal | Source | Threshold |
|---|---|---|
| Brownfield retired-gen nearby | `brownfield_interconnection` (from `reference_data.RETIRED_GENERATION_SITES`) | Within 10 km, qualified by `brownfield_fit` |
| Planned / under-construction substation | `planned_substations` (from `energy_analytics.duckdb`) | Within 50 km |
| Existing large substation | `substations` (HIFLD + planned feed) | ≥230 kV OR ≥5 circuits, within 10 km |
| Active in-state generation pipeline | `interconnection_queue` (state-level) | ≥3 GW in advanced stages (construction / IA-executed / facility / planning) |
| Cluster track record | `cluster_signal` | Existing DC operators served by same utility → demonstrated build capacity (narrative positive, not an anchor) |

### Demand (−)

| Signal | Source | Threshold |
|---|---|---|
| Competing announced / planned DC pipeline | `nearby_dcs` filtered to non-operating stages | ≥5 projects within 50 km; elevated severity at ≥1 GW total |
| Grid-remote with zero supply | `transmission_lines`, supply signals above | No HV line (≥100 kV) within 30 km AND no supply anchor |

## 5. Verdict logic

- **Promising**: at least one "anchor" supply signal (brownfield, planned substation, OR large existing substation). State-queue and cluster signals are positive but don't by themselves qualify as an anchor (they're regional / utility-level, not site-specific).
- **Doubtful**: no supply signals of any kind AND (no HV line within 30 km OR a dense competing-demand pressure exists).
- **Neutral**: everything else — e.g. HV line nearby but no anchor, or one softer signal without a strong case either way.

Only **doubtful** triggers the killer. **Promising** and **neutral** do not add risk; promising sites already earn their opportunity boost through `cluster_signal` / `brownfield_fit`, so we do not double-count on the opportunity side.

## 6. Alternative-path suppression (retained)

Legacy grid killer had three alt-paths that could suppress a fire: cluster + HV, brownfield, BTM gas. Under the new classifier, the first two are folded in directly (they are now supply signals that push verdict to `promising`). BTM gas is retained as an explicit suppressor at the trigger level: a doubtful outlook still doesn't fire the killer if the tenant is anchored/hyperscaler AND BTM gas is viable (the Stargate/Abilene pattern). We keep BTM gas as a suppressor rather than a supply anchor because a gas-delivery pathway isn't a grid anchor — it's a decision to bypass the grid.

## 7. Failure modes observed and expected behavior

- **Hurt Ranch NM** (remote, no nearby DCs, no retired gen, no HV line): all supply signals empty, HV absent → **doubtful**. Fires at P=0.40 × 1.0 (speculative) = 0.40. Lower than the old critical-tier 0.75, which is intentional: we don't pretend to know that Hurt Ranch is "96% deficit" — we know it has no anchors and isn't near HV.
- **Millsboro DE**: brownfield (Indian River 0.8 km) present → **promising**. No kill.
- **New Albany OH**: large AEP substations + active cluster + state-queue gen → **promising**. No kill.
- **Ashburn VA**: dense existing cluster + HV everywhere + large substations → **promising**. No kill. (Separately, announced-pipeline pressure is high — this is a real capacity concern but not a deal-killer: the cluster's demonstrated build-out overrides.)
- **Abilene TX**: ERCOT rural site, but BTM-gas pathway available and tenant is hyperscaler → even if classifier comes back doubtful, BTM-gas suppression kicks in.

## 8. Option A — Tighten deterministic

Not pursued. The whole point of the rewrite is that the underlying data can't support deterministic tiering.

## 9. Option B — Qualitative (chosen)

Three-way verdict, flat P on the killer, explicit honesty about coarseness. Evidence string names which supply / demand signals were observed so readers can audit the judgment.

## 10. Option C — Hybrid

Effectively what this is: the classifier is qualitative, but it composes deterministic sub-signals (distance / voltage / MW thresholds for each supply or demand indicator). Thresholds are documented above and in `scoring.py` constants. They can be tuned as we label more sites; the classifier is the right shape of output regardless.

## 11. Regression pin updates

- `hurt_ranch_nm`: `must_trigger_killers` → `power_outlook_doubtful` (was `grid_severely_insufficient`). Feasibility expected ≈ 0.15 (0.40 × 1.0 [spec] vs old 0.75 × 1.0 gave ~0.10; the softer P raises feas slightly — this is the honest delta from giving up false precision).
- `millsboro_de`: unchanged triggers. `grid_severely_insufficient` was already suppressed by brownfield; the new `power_outlook_doubtful` is also suppressed (verdict = promising via Indian River). No change.
- `new_albany_oh`, `ashburn_va`, `altoona_ia`, `council_bluffs_ia`, `the_dalles_or`, `decatur_il`, `abilene_tx`: all rename `grid_severely_insufficient` in `must_not_trigger_killers` → `power_outlook_doubtful`.

## 12. Calibration hook

Hand-labeled corpus: 20+ built sites and 20+ cancelled/shelved sites. Run the classifier on each at pre-announcement context, bucket by verdict, measure observed kill rate. If doubtful-verdict built-out rate >> 40%, the P is too high; if promising-verdict cancel rate >> 10%, the supply-signal thresholds are too generous.

Signal-by-signal ablation: drop each supply signal, re-run, see how many "promising" sites flip to "doubtful" — informs which signals are pulling the verdict, and which are vestigial.
