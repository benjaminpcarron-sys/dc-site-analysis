# Screen Methodology — `utility_moratorium` + `regulatory_interconnection_pause`

Reviewed together because they were split out of a single killer in the prior session. This brief formalises the taxonomy and adds lift-date-aware probability scaling.

## 1. What they test

Both test whether a utility will physically let a new large-load DC connect in the near term. They differ by the mechanism and durability of the block:

- **`utility_moratorium`**: an indefinite tariff-level freeze (e.g. new bills before legislatures that would ban large-load service, or tariffs that explicitly suspend new applications). Multi-year horizon or open-ended. Mechanism: tariff provision.
- **`regulatory_interconnection_pause`**: a PSC/PUC docket-level pause with a defined commission decision horizon (e.g. DE PSC 25-0826, Delmarva lifting late 2026). Primarily schedule risk. Mechanism: docket action.

Missing third category: **rolling queue-review pauses** (e.g. PJM's periodic cluster-study batching, CAISO's CAISO 23-09 interconnection process reform). These aren't permanent, aren't docket-scoped, and have no firm lift date, but they do meaningfully delay DC projects. Not ingested today.

## 2. Current implementation

### `utility_moratorium`
- **Trigger**: `_trigger_tariff_moratorium`. Fires when any matched DC tariff has `moratorium = True`.
- **Base P**: `0.90`.
- **Tenant scaling**: `1.0 / 0.9 / 0.8`.
- **Inputs**: `dc_tariffs[*].moratorium`.

### `regulatory_interconnection_pause`
- **Trigger**: `_trigger_regulatory_pause`. Fires when any entry in `REGULATORY_MORATORIUMS` matches state + utility.
- **Base P**: `0.55`.
- **Tenant scaling**: `1.0 / 0.7 / 0.5`.
- **Inputs**: `regulatory_moratoriums[*]`.

## 3. Failure modes observed

- **Millsboro DE** (initial): a single `utility_moratorium` killer caught Delmarva's Docket 25-0826 at P=0.90, which implicitly treated a docket-level pause as indefinite. Site scored 0.05 Poor vs revised report's "Viable with Conditions." Fixed by splitting the killer.
- **Lift-date blindness**: once split, a docket pause expected to lift in 3 months scores the same (P=0.55) as one expected to lift in 18 months. A 3-month delay for a project already 24 months from break-ground is noise; an 18-month delay is a showstopper.
- **Hyperscaler vs merchant time horizon**: tenant scaling partly captures this, but lift date is orthogonal (a 6-month pause is fine even for a merchant developer).

## 4. Ground truth available

- FERC / state PSC dockets (text): `expected_lift_date` from hearing schedules.
- `demand_ledger.duckdb`: project status during active pauses vs after lift for the same utility. Validates the "schedule risk" vs "existential" framing.
- Historical AEP Ohio moratorium (Mar 2023 -> Jul 2025, lifted): actual project outcomes in Ohio during that window are a dataset we already have in `demand_ledger`.

## 5. Option A — Tighten deterministic

Two changes:

1. **Lift-proximity scaling** on `regulatory_interconnection_pause`. Parse `expected_lift_date` (ISO "YYYY-MM-DD") and compute months-to-lift. Scale P by:
   ```
   months <=  6  -> 0.30
   months <= 12  -> 0.55 (current)
   months <= 24  -> 0.70
   months >  24  -> 0.85  (open-ended pause, approaches tariff moratorium)
   ```
   Parsed days-from-now, not wall-clock months, so the model ages gracefully.

2. **Add a rolling-review category** as a new moratorium `type` field. Tariff-level `moratorium=True` maps to `type="tariff"` (P=0.90). Regulatory docket pauses with a firm lift map to `type="docket"` (lift-proximity scaled). Cluster-study / queue-reform pauses map to `type="rolling"` (P=0.40, no lift scaling). Only docket-type enters `regulatory_interconnection_pause`; rolling-type is a new signal folded into the existing killer or handled as narrative.

## 6. Option B — Qualitative

Not viable for `utility_moratorium` (a declared tariff freeze is the paradigmatic deal-killer). `regulatory_interconnection_pause` could plausibly be qualitative, but Millsboro proves it materially changes siting decisions for merchants — keep deterministic.

## 7. Option C — Hybrid

Already effectively hybrid: the evidence strings quote the docket ID + expected lift. Option A deepens this by parameterising the date. The report's "Power Path" section already narrates what the pause means for the project — no additional narrative needed.

## 8. Recommendation

**Option A (Tighten)** — lift-proximity P scaling for `regulatory_interconnection_pause`; keep tariff moratorium at flat 0.90 for now. Defer the rolling-review category to a future pass (we don't have an ingestion source for PJM cluster-study timing yet).

## 9. Proposed code changes

[scoring.py](../../scoring.py):

```python
from datetime import date

_REG_PAUSE_P_BY_MONTHS = [(6, 0.30), (12, 0.55), (24, 0.70), (9999, 0.85)]

def _months_until(iso_date: str | None) -> float | None:
    if not iso_date: return None
    try:
        target = date.fromisoformat(iso_date)
    except Exception:
        return None
    today = date.today()
    return (target - today).days / 30.44

def _p_regulatory_pause(ctx):
    months_min = None
    for m in ctx.get("regulatory_moratoriums") or []:
        mo = _months_until(m.get("expected_lift_date"))
        if mo is None: continue
        mo = max(mo, 0.0)  # past-dated: treat as about-to-lift
        months_min = mo if months_min is None else min(months_min, mo)
    if months_min is None:
        return 0.55   # unknown lift -> baseline
    for cap, p in _REG_PAUSE_P_BY_MONTHS:
        if months_min <= cap: return p
    return 0.85
```

## 10. Regression pin updates

- `millsboro_de`: DE PSC 25-0826 expected lift `2026-12-31`. From today (2026-04-24) that's ~8 months. Falls in the `<=12` bucket at P=0.55 (unchanged). No pin change.
- If we add a test with an expected-lift <=6 months away, pin P at 0.30.

## 11. Calibration hook

```sql
-- For each historical docket pause:
SELECT docket,
       AVG(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) AS observed_kill_rate,
       AVG(months_paused) AS actual_paused_duration
FROM project_outcomes
JOIN docket_history USING (utility, state)
WHERE pause_status='lifted'
GROUP BY 1;
```

Correlate `actual_paused_duration` with `observed_kill_rate`; fit a monotonic curve to replace the hand-tiered buckets.
