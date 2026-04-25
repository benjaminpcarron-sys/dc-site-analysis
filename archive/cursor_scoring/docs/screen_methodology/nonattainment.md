# Screen Methodology — `severe_nonattainment` + `marginal_nonattainment`

Joint brief: these were reviewed together because the classification is a single EPA attribute and the two killers are companion screens on that attribute.

## 1. What they test

Whether the site's EPA designated AQCR (air quality control region) is in nonattainment for any National Ambient Air Quality Standard (NAAQS). Nonattainment imposes New Source Review / nonattainment NSR permitting, offset requirements for major emissions, and — in the worst cases — local moratoria on new major sources. For DCs, the concern is BTM gas / backup-generator fleets that become "major source" cumulatively.

- `severe_nonattainment` fires on classifications containing SEVERE / EXTREME / SERIOUS.
- `marginal_nonattainment` fires on all other (non-severe) nonattainment classifications.

## 2. Current implementation

### `severe_nonattainment`
- Base P: `0.15`, tenant scaling `1.0 / 1.0 / 1.0`.
- Inputs: `nonattainment_zones[*].classification`.

### `marginal_nonattainment`
- Base P: `0.08`, tenant scaling `1.0 / 1.0 / 1.0`.
- Same input source.

## 3. Failure modes observed

- **Marginal is too common**: any urban/suburban site in Ohio, Texas, Colorado Front Range, Virginia etc. is in some flavor of marginal 8-hour ozone nonattainment. The killer fires on ~every built anchor, reducing its signal value.
- **Severe is correctly rare**: SCAQMD (CA), San Joaquin Valley, Houston-Galveston-Brazoria, etc. The P=0.15 is defensible for these.
- **Joint-triggering ambiguity**: a site in Houston-Galveston-Brazoria for 8-hr ozone would historically trigger `severe_nonattainment` AND `marginal_nonattainment` simultaneously if another NAAQS (e.g. PM2.5) was also listed at marginal. Current code correctly iterates the zones but the semantics of "same site hit twice" is unclear.

## 4. Ground truth available

- EPA Green Book (nonattainment status): already ingested.
- `demand_ledger.duckdb` per-project status; cross-reference with zone classification.
- EPA offset-ratio requirements by classification: published in 40 CFR 51.165.

## 5. Option A — Tighten deterministic

- Keep `severe_nonattainment` as is. The permitting consequences (offsets, BACT, full NSR cycle) are severe and well-characterised.
- Add tiering within severe: Extreme > Severe > Serious with base P 0.30 / 0.20 / 0.15.

## 6. Option B — Convert `marginal_nonattainment` to qualitative

Remove `marginal_nonattainment` from `DEAL_KILLERS`. Report it as a narrative paragraph listing the classification and the approximate offset ratio required (moderate 1.15:1, marginal 1.10:1) so readers can judge the overhead without the model over-counting. Severe stays deterministic.

## 7. Option C — Hybrid

Combine: severe stays as killer (tiered); marginal becomes narrative.

## 8. Recommendation

**Option B for `marginal_nonattainment` + Option A for `severe_nonattainment`.** Retire marginal as a killer (too broad); keep severe as killer with tiered P (extreme / severe / serious). Marginal re-emerges as a narrative block listing classification + offset ratio.

## 9. Proposed code changes

[scoring.py](../../scoring.py):

```python
_SEVERE_TIER_P = {"EXTREME": 0.30, "SEVERE": 0.20, "SERIOUS": 0.15}

def _p_severe_nonattainment(ctx) -> float:
    worst = "SERIOUS"
    for z in ctx.get("nonattainment_zones") or []:
        cls = (z.get("classification") or "").upper()
        for tier in ("EXTREME", "SEVERE", "SERIOUS"):
            if tier in cls and _SEVERE_TIER_P[tier] > _SEVERE_TIER_P[worst]:
                worst = tier
    return _SEVERE_TIER_P[worst]
```

Remove `marginal_nonattainment` from `DEAL_KILLERS`. Replace with a helper `marginal_nonattainment_narrative(ctx) -> list[str]` surfaced in [report_template.py](../../report_template.py).

## 10. Regression pin updates

- `millsboro_de`: currently pinned with `marginal_nonattainment` in `must_trigger_killers`. Remove that pin. Recalculate `expected_feasibility` (removing P=0.08 raises feasibility slightly).
- Any other pin that references `marginal_nonattainment` -- audit and remove.

## 11. Calibration hook

```sql
SELECT nonattainment_class,
       COUNT(*) AS n,
       AVG(CAST(status='cancelled' AS DOUBLE)) AS cancel_rate,
       AVG(offsets_required_ratio) AS avg_offset_ratio
FROM project_outcomes LEFT JOIN air_district_ref USING (aqcr)
GROUP BY 1;
```

Expect `cancel_rate` to be materially higher for severe/extreme than marginal; validates keeping severe and dropping marginal as killer.
