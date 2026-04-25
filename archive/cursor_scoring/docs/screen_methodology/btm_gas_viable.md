# Screen Methodology — `btm_gas_viable` (signal)

Not a deal-killer: it is the third suppression path on `grid_severely_insufficient`, tenant-gated.

## 1. What it tests

Whether the site has access to gas supply sufficient to support behind-the-meter (BTM) generation — gas turbines, reciprocating engines, or a gas-to-BESS hybrid — as an alternative or supplement to grid power. The archetype is Stargate / Abilene TX, where the project doesn't wait for ERCOT upgrade and instead self-generates from intrastate gas.

## 2. Current implementation

- **Detector**: `btm_gas_viable` in [scoring.py](../../scoring.py).
- **Trigger**: `interstate pipeline within 15 km` OR `>=2 intrastate pipelines within 10 km`.
- **Effect**: when tenant is anchored or hyperscaler, suppresses `grid_severely_insufficient`.
- **Inputs**: `gas_pipelines[*].type`, `dist_km`, `operator`.
- **Probability**: N/A (signal, not killer).

## 3. Failure modes observed

- **No air-permit awareness**: the current logic assumes if there's a pipeline, BTM gas is viable. But a site in a `severe` nonattainment county (e.g. Houston 8-hour ozone, San Joaquin PM2.5) cannot get new major-source gas turbine air permits without offsets that may not be obtainable. Suppressing `grid_severely_insufficient` on the basis of BTM gas in a severe-nonattainment county is a false positive.
- **No pipeline-capacity awareness**: a 6-inch intrastate lateral is not the same delivery capacity as a 24-inch interstate trunk. HIFLD doesn't consistently publish diameter/pressure, so the signal treats them as equivalent.
- **Only relevant for anchored/hyperscaler tenants**: already gated correctly in the killer-suppression path.

## 4. Ground truth available

- EPA AirData: nonattainment polygons with classification (severe / extreme / serious / moderate / marginal).
- HIFLD gas pipelines table with `type`, `operator`, sometimes `diameter`, `pressure`.
- FERC 7(c) filings: pipeline capacity expansions.

## 5. Option A — Tighten deterministic

Add one gate:

**BTM gas suppression is blocked when the site sits in a severe-or-worse nonattainment zone.** This is a physical-permit reality, not a calibration question.

Optional (deferred): weight the pipeline distance by operator brand-name (Energy Transfer / Kinder Morgan intrastate trunks = trunk-grade; no-name transmission = lateral-grade).

## 6. Option B — Qualitative

Not viable. Removing BTM gas suppression re-breaks Stargate / Abilene and similar sites.

## 7. Option C — Hybrid

Already in the report narrative via Power Path. Option A tightens the deterministic gate.

## 8. Recommendation

**Option A (Tighten)**. Add a nonattainment block on BTM gas suppression. Do not alter the detection threshold (pipeline distances); those work.

## 9. Proposed code changes

[scoring.py](../../scoring.py):

```python
def _severe_nonattainment_present(ctx) -> bool:
    severe = {"SEVERE", "EXTREME", "SERIOUS"}
    for zone in ctx.get("nonattainment_zones") or []:
        cls = (zone.get("classification") or "").upper()
        if any(s in cls for s in severe):
            return True
    return False

def btm_gas_viable(ctx):
    if _severe_nonattainment_present(ctx):
        return False, "BTM gas suppression blocked: site in severe-nonattainment county (air-permit barrier)."
    # ... existing pipeline-distance checks ...
```

## 10. Regression pin updates

- `abilene_tx`: check that Abilene is not in severe nonattainment. Taylor County TX is in attainment -- no change.
- `millsboro_de`: already has brownfield suppression; BTM gas wouldn't have fired anyway -- no change.
- `new_albany_oh`: Licking County OH is in attainment -- no change.
- Hypothetical `los_angeles_ca`: San Bernardino County is in severe 8-hour ozone NAAQS; BTM gas would previously suppress grid-kill; now correctly doesn't. (No existing pin but this is the target failure mode.)

## 11. Calibration hook

```sql
-- Do BTM-gas-announced projects in severe-nonattainment counties actually build?
SELECT nonattainment_class,
       AVG(CAST(btm_gas_announced AND status='operating' AS DOUBLE)) AS btm_build_rate
FROM project_outcomes
WHERE btm_gas_announced
GROUP BY 1;
```

If severe-class build rate is near zero, the block is validated. If severe-class build rate is nontrivial (offsets available, tenant pre-purchased), relax the block.
