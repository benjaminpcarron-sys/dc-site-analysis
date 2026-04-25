# Screen Methodology — `flood_zone_av`

## 1. What it tests

Whether the site sits in a FEMA 100-year floodplain (zones starting with "A" or "V") where federal floodplain management requirements apply and flood insurance is mandatory for any federally-backed mortgage. In practice: a fatal constraint for mission-critical infrastructure because (a) FEMA compliance forces elevation or floodproofing capex, and (b) insurance/financing adds cost.

## 2. Current implementation

- **Trigger**: `_trigger_flood_av` in [scoring.py](../../scoring.py). Fires when any flood zone starts with "A" or "V".
- **Base P**: `0.25`.
- **Tenant scaling**: `1.0 / 1.0 / 1.0` (environmental -- same P regardless of tenant).
- **Inputs**: `flood_zones[*].flood_zone`.

## 3. Failure modes observed

- **AE / AH / AO are not uniform in risk**: AE (base flood elevation determined) is the workable case; AH (ponding) and A99 (within levee protection) are notably different. Currently all fire the same P.
- **X-shaded (500-year floodplain)** is not screened at all. A site in 500-yr floodplain isn't in the 100-yr SFHA but still faces meaningful flood risk and occasional lender scrutiny for DC-scale capital. Currently invisible.
- **CBRA (Coastal Barrier Resources Act) zones** are not screened. CBRA imposes a federal-flood-insurance prohibition that is effectively a kill. Currently invisible.

## 4. Ground truth available

- FEMA NFHL already ingested for `flood_zones`. The `flood_zone` field includes A/V/X-shaded/X/X_protected/D.
- CBRA GIS: FWS-published polygons, not currently ingested.

## 5. Option A — Tighten deterministic

Split into two killers / signals:

| Zone | Tier | Base P |
|---|---|---|
| V, VE, AE*, AO, AH | primary SFHA | 0.30 |
| A, A99, D | unclassified SFHA | 0.20 |
| X-shaded (500-yr) | narrative | 0.05 |
| CBRA | CBRA kill | 0.85 |

Pre-CBRA data we don't have yet, so leave CBRA unaddressed but flagged in the brief.

## 6. Option B — Qualitative

Not viable: FEMA A/V is one of the cleanest deterministic screens available (boolean GIS polygon). Removing it loses more than it gains.

## 7. Option C — Hybrid (RECOMMENDED)

Keep deterministic A/V killer. Add X-shaded as a **narrative signal** in the report (no P contribution) so the reader sees 500-yr exposure without it becoming a false-positive deal-killer. Defer CBRA until the data source is added.

## 8. Recommendation

**Option C (Hybrid)**. Retain A/V killer at current P=0.25 (well-calibrated per brief author's judgment; no evidence to tier). Add 500-yr X-shaded as a new report narrative block. CBRA flagged for future data ingestion.

## 9. Proposed code changes

[scoring.py](../../scoring.py): no trigger change. Add a new `flood_500yr_exposure` helper used by [report_template.py](../../report_template.py) for narrative:

```python
def flood_500yr_exposure(ctx) -> list[str]:
    out = []
    for fz in ctx.get("flood_zones") or []:
        z = (fz.get("flood_zone") or "").upper()
        if z.startswith("X") and ("SHADED" in z or z == "X-SHADED"):
            out.append(f"FEMA 500-yr floodplain ({z}): elevated flood insurance premium but not SFHA.")
    return out
```

[report_template.py](../../report_template.py): new "Flood exposure" subsection under Environmental when `flood_500yr_exposure(ctx)` returns nonempty.

## 10. Regression pin updates

- No current pinned site has flood triggers; regression is unchanged.

## 11. Calibration hook

```sql
-- What proportion of DC cancellations cite flood as reason?
SELECT flood_zone_class,
       AVG(CAST(status='cancelled' AND cancel_reason ILIKE '%flood%' AS DOUBLE)) AS flood_cancel_rate
FROM project_outcomes
GROUP BY 1;
```
