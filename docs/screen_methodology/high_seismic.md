# Screen Methodology — `high_seismic`

## 1. What it tests

Whether the site sits in an ASCE 7-22 Seismic Design Category (SDC) D, E, or F — increasingly stringent structural design standards that add cost (specialised foundations, isolation, bracing, geotech) and can add schedule risk (peer review requirements).

## 2. Current implementation

- **Trigger**: `_trigger_high_seismic` in [scoring.py](../../scoring.py). Fires when SDC is in `{D, E, F}`.
- **Base P**: `0.08`.
- **Tenant scaling**: `1.0 / 1.0 / 1.0`.
- **Inputs**: `seismic.seismic_design_category`.

## 3. Failure modes observed

- **SDC D vs E/F blurred**: SDC D sites include much of coastal California, Cascades, Utah Wasatch Front -- where DCs are routinely built (The Dalles OR Google campus is SDC D and has been operating for 20 years). SDC E and F are near-fault regions (e.g. parts of San Francisco Bay, LA basin) where structural design is materially more demanding. Treating D the same as F under-calibrates for the tail.
- **Flat 0.08**: the_dalles_or pin works fine under current calibration (fires at P=0.08, feasibility ~0.45 Moderate). But if a hypothetical site were in SDC F near a Cascadia rupture zone, the same P=0.08 likely under-rates the risk.

## 4. Ground truth available

- USGS design maps: already ingested.
- Historical DC construction: there are many SDC D data centers (Umatilla, The Dalles, Quincy WA). Very few SDC E operational DCs; almost no SDC F.
- ASCE 7-22 commentary: relative cost multipliers published in peer literature (+5-10% for D, +15-25% for E, +25-40% for F).

## 5. Option A — Tighten deterministic

Tier P by SDC class:

| SDC | Base P |
|---|---|
| D | 0.05 |
| E | 0.15 |
| F | 0.30 |

## 6. Option B — Qualitative

Not viable. Seismic design category is clean GIS/lookup data and a real capex driver.

## 7. Option C — Hybrid

Already hybrid (evidence string names the SDC class).

## 8. Recommendation

**Option A (Tighten)**. Three-tier P. The_dalles_or stays in SDC D -> P=0.05 (tighter, reflecting that D is routine for DCs). E/F fires a higher P reflecting the capex and peer-review overhead.

## 9. Proposed code changes

```python
_SEISMIC_TIER_P = {"D": 0.05, "E": 0.15, "F": 0.30}

def _p_high_seismic(ctx) -> float:
    s = ctx.get("seismic") or {}
    sdc = (s.get("seismic_design_category") or "").upper()
    return _SEISMIC_TIER_P.get(sdc, 0.08)
```

## 10. Regression pin updates

- `the_dalles_or`: SDC D -> P drops from 0.08 to 0.05. Feasibility rises by ~0.01. Within tolerance, no pin change.
- No existing SDC E/F site in the pin set.

## 11. Calibration hook

```sql
-- Does SDC tier correlate with DC build rate?
SELECT seismic_class,
       COUNT(*) AS n,
       AVG(CAST(status='operating' AS DOUBLE)) AS build_rate,
       AVG(construction_cost_per_mw) AS cost_density
FROM project_outcomes GROUP BY 1;
```
