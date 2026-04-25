# Screen Methodology — `brownfield_interconnection`

Not a deal-killer: it is a **suppression signal** that breaks `grid_severely_insufficient` and adds `BROWNFIELD_OPPORTUNITY_BOOST` to the opportunity score. This review tightens its thresholds.

## 1. What it tests

Whether a retired power plant's existing switchyard, right-of-way, and generator interconnection can be repurposed for the DC, sidestepping a fresh network-upgrade queue. Indian River DE (retired 2022) is adjacent to the Millsboro site and exemplifies this — you inherit a ~670 MW connection instead of waiting for PJM to build one.

## 2. Current implementation

- **Detector**: `has_brownfield_interconnection` in [scoring.py](../../scoring.py). True when a `brownfield_interconnection` element entry exists with `former_mw >= 0.6 * target_mw` within `BROWNFIELD_INTERCONNECTION_RADIUS_KM = 5.0`.
- **Source data**: `RETIRED_GENERATION_SITES` in [reference_data.py](../../reference_data.py) -- 4 hand-curated entries (Indian River DE, Homer City PA, Conemaugh PA, Brandon Shores MD).
- **Effects**:
  - Suppresses `grid_severely_insufficient`.
  - `+BROWNFIELD_OPPORTUNITY_BOOST = 0.10` additive on opportunity.
- **Inputs**: `brownfield_interconnection[*].former_mw`, `dist_km`.

## 3. Failure modes observed

- **Radius is arbitrary**: 5 km was chosen because Indian River is 0.8 km. Homer City redevelopment is ~4 km. Brandon Shores / CPV Fairview-style co-location is typically <1 km. But hypothetical future sites may be 6-10 km away with direct feeder access via existing ROW (e.g. Four Corners NM retired coal with ~12 km feeder to Farmington sites). 5 km is too tight for future inventory growth.
- **Flat opportunity boost**: 100-MW-former / 500-MW-target is a partial fit (only 20%) but currently gets the same +0.10 boost as a 1.5-GW-former / 500-MW-target which is a full cost-saving solve. These should tier.
- **Capacity-ratio threshold feels right**: 0.6 -> 60% of target means at least you're not under-sized on transformer capacity. But the hard boolean is unfriendly to close-misses (59%).
- **Only 4 entries**: the inventory is thin. Other meaningful candidates: Yates GA (retired 2014), Cheswick PA (retired 2022), San Juan NM (retired 2022), Dave Johnston WY (retirement pending 2028).

## 4. Ground truth available

- EIA-860 retirement table: complete list of retired plants by year with capacity. Machine-readable.
- PJM / MISO / ERCOT retired-ICA studies: in some cases the existing interconnection agreement is explicitly available for transfer (e.g. PJM's "surplus interconnection service").
- Existing DC announcements at retired plants: Homer City (Strategic Bitcoin Mining / Knoxville Construction), Lordstown OH (Foxconn / Amazon), Brandon Shores (rumoured). Each is a labeled data point for the signal.

## 5. Option A — Tighten deterministic

Three changes:

1. **Expand radius** to `10 km` with a graceful distance-decay: sites <=5 km are "direct co-location" (full effect); 5-10 km are "adjacent ROW" (opportunity boost halved; grid-killer suppression still applies).
2. **Tier the opportunity boost** by capacity ratio:
   | Capacity ratio (former_mw / target_mw) | Opportunity boost |
   | --- | --- |
   | <0.60 | 0.00 (no suppression either) |
   | 0.60 - 0.90 | 0.07 |
   | >=0.90 | 0.12 |
3. **Soften the binary** to a continuous capacity-fitness score in the evidence string: "Indian River 670 MW vs 500 MW target (fit = 1.34)". Makes the log self-explanatory.

## 6. Option B — Qualitative

Not viable. The signal's entire purpose is to quantitatively break the grid-killer. Removing the deterministic path makes that suppression implicit and hard to audit.

## 7. Option C — Hybrid

Already hybrid: the Power Path section of the report narrates the brownfield evidence. This brief adds quantitative texture (fit ratio + tier), keeping the hybrid character.

## 8. Recommendation

**Option A (Tighten)**. Expand to 10 km with distance-decay; tier the opportunity boost by capacity ratio; expand the `RETIRED_GENERATION_SITES` registry with 4 additional confirmed retirements (Yates GA, Cheswick PA, San Juan NM, Dave Johnston WY) at 2028 and later. Keep the 0.6 capacity-ratio floor as the hard suppression threshold (grid-killer stays killed only if former is at least 60% of target).

## 9. Proposed code changes

[scoring.py](../../scoring.py):

```python
BROWNFIELD_INTERCONNECTION_RADIUS_KM = 10.0  # was 5.0
BROWNFIELD_DIRECT_RADIUS_KM = 5.0            # new: full-effect tier
BROWNFIELD_MIN_CAPACITY_RATIO = 0.6          # unchanged

_BROWNFIELD_OPP_BY_RATIO = [(0.90, 0.12), (0.60, 0.07)]  # (min_ratio, boost)

def brownfield_fit(ctx) -> dict | None:
    """Return {site, ratio, distance_tier, opportunity_boost} for best usable
    brownfield, or None if none qualify."""
    ...
```

Rewire `compute_opportunity` to use `brownfield_fit()['opportunity_boost']` when present (instead of the flat constant).

[reference_data.py](../../reference_data.py): add 4 more `RETIRED_GENERATION_SITES` entries.

## 10. Regression pin updates

- `millsboro_de`: Indian River is 0.8 km away with 670 MW former / 500 MW target -> ratio 1.34, direct-tier, boost = 0.12. Current pin uses implicit 0.10; new boost adds 0.02 to opportunity, feasibility nudges up by ~0.01 (within tolerance). No pin change required.
- Future sites near Yates GA or San Juan NM would test the 10 km ring and the graduated boost.

## 11. Calibration hook

```sql
-- Is brownfield proximity actually predictive of build success?
SELECT CASE WHEN nearest_retired_plant_km <= 5 THEN 'direct'
            WHEN nearest_retired_plant_km <= 10 THEN 'adjacent'
            ELSE 'none' END AS tier,
       AVG(CAST(status='operating' AS DOUBLE)) AS build_rate
FROM labeled_sites
WHERE target_mw IS NOT NULL
GROUP BY 1;
```

If `direct` and `adjacent` tiers show materially different build rates, re-tier the opportunity boost.
