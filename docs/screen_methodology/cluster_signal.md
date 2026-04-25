# Screen Methodology — `has_active_cluster` (cluster signal)

Not a deal-killer: it is a suppression signal on `grid_severely_insufficient` and adds `CLUSTER_OPPORTUNITY_BOOST` to opportunity.

## 1. What it tests

Whether the site sits inside a demonstrated DC market — i.e. a utility has already built enough HV capacity and staffed up enough development engineering to serve multiple DC tenants. An active cluster is statistical proof that the utility can handle the interconnection ask, even if current headline `max_mw` looks short.

## 2. Current implementation

- **Detector**: `has_active_cluster` in [scoring.py](../../scoring.py).
- **Trigger**: `>= CLUSTER_MIN_COUNT = 5` existing DC projects within `CLUSTER_RADIUS_KM = 50` km.
- **Effects**:
  - Suppresses `grid_severely_insufficient` (when combined with HV line within `CLUSTER_GRID_RANGE_KM = 30` km).
  - `+CLUSTER_OPPORTUNITY_BOOST = 0.15` additive on opportunity.
- **Inputs**: `nearby_dcs[*].dist_km`.

## 3. Failure modes observed

- **Quincy WA** (documented gap): Only 2 DCs currently detected within 50 km, so `has_active_cluster` returns False. But Quincy is one of the oldest US DC hubs (Microsoft, Yahoo, Sabey, Vantage), and the 2 detected are hyperscaler anchors with GW+ built. Count-only misses this because the underlying `nearby_dcs` feed is sparse on smaller Quincy colo sites.
- **Ashburn, Loudoun County VA**: 50+ DCs within 50 km -- signal correctly fires, but CLUSTER_MIN_COUNT=5 is way below the "credible hub" threshold. A site on the very edge (e.g. 49 km out, only catching 6 shared DCs) gets the same boost as a site in the core (50 DCs within 20 km).
- **MW-blind**: 5 × 20 MW colo DCs within 50 km triggers; a single 1.5 GW Microsoft campus within 15 km does not (if not accompanied by 4 others). The latter is the far stronger signal.

## 4. Ground truth available

- `demand_ledger.duckdb` has per-DC MW (sometimes null). Count-based is the robust signal we already use; MW-weighted is stronger when data is present but needs null-handling.
- Historical signal: utilities with active clusters consistently approved new DC interconnections over the last 5 years. Cross-reference with `project_outcomes` table.

## 5. Option A — Tighten deterministic

Two changes:

1. **MW-weighted OR count threshold**: cluster fires when EITHER
   - `count >= 5` within 50 km (legacy), OR
   - `sum(mw_within_30km) >= 400 MW` (Quincy, Council Bluffs, Umatilla cases)
2. **Tier the opportunity boost** by strength:
   | Cluster strength | Opportunity boost |
   | --- | --- |
   | count >= 5 AND sum(mw) >= 1 GW | 0.20 (hub tier) |
   | count >= 5 OR sum(mw) >= 400 MW | 0.15 (current tier) |

## 6. Option B — Qualitative

Not viable. The cluster signal is the dominant mechanism that allows the model to correctly rate built-anchor sites. Removing it would over-kill New Albany-style cases.

## 7. Option C — Hybrid

Already hybrid (cluster evidence is in the Power Path narrative). Option A adds quantitative tiering to that narrative.

## 8. Recommendation

**Option A (Tighten)**. Add MW-weighted fallback path and tier the opportunity boost. Retain count-based as primary because many `nearby_dcs` entries have `mw=None`.

## 9. Proposed code changes

[scoring.py](../../scoring.py):

```python
CLUSTER_RADIUS_KM = 50.0              # unchanged
CLUSTER_MIN_COUNT = 5                 # unchanged
CLUSTER_MW_RADIUS_KM = 30.0           # tighter radius for MW-weighted path
CLUSTER_MW_THRESHOLD = 400            # MW
CLUSTER_HUB_MW_THRESHOLD = 1000       # MW (hub tier boost)

CLUSTER_OPPORTUNITY_BOOST = 0.15
CLUSTER_HUB_OPPORTUNITY_BOOST = 0.20

def cluster_signal(ctx) -> dict | None:
    """Return {tier, count, mw_total, evidence} or None. Tier in
    {'hub', 'active'}."""
    ...
```

## 10. Regression pin updates

- `new_albany_oh` (Ashburn-analogue): 28 DCs within 50 km with multiple hyperscaler GW campuses -> hub tier. Boost rises from 0.15 to 0.20. Opportunity goes up by ~0.05, feasibility nudges up by ~0.03. Update `expected_feasibility` to reflect (currently ~0.47, rising to ~0.50).
- `the_dalles_or`: check if hub tier triggers with Google Dalles -- likely `active` tier only (cluster is small despite Google being 1.2+ GW). No change if count <5.
- `millsboro_de`: no cluster, no change.

## 11. Calibration hook

```sql
SELECT CASE WHEN mw_within_30km >= 1000 THEN 'hub'
            WHEN count_within_50km >= 5 OR mw_within_30km >= 400 THEN 'active'
            ELSE 'none' END AS cluster_tier,
       AVG(CAST(status='operating' AS DOUBLE)) AS build_rate
FROM project_snapshots
WHERE snapshot_age_months >= 24
GROUP BY 1;
```

Fit build-rate vs tier; adjust boosts so the boost approximately equals the observed build-rate lift.
