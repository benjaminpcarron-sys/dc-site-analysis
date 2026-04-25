# Screen Methodology — `high_industrial_rate`

## 1. What it tests

Whether retail industrial electric rates at the site are high enough to materially hurt the project's LCOE, discouraging development.

## 2. Current implementation

- **Trigger**: `_trigger_high_rate` in [scoring.py](../../scoring.py). Fires when `utility_rate.industrial_rate_cents > 14`.
- **Base P**: `0.15`.
- **Tenant scaling**: `1.0 / 0.8 / 0.5`.
- **Inputs**: `utility_rate.industrial_rate_cents`.

## 3. Failure modes observed

- **Arbitrary threshold**: 14 c/kWh is close to the US national industrial average (~8-9 c/kWh as of 2025 EIA), but there is no published rubric for why 14 was chosen. A 15 c/kWh rate in CA (where state average is 18+) is normal for that market; in AR (where state average is 6-7) it's extreme.
- **Absolute-only**: doesn't compare to state or regional average, so high-cost markets (CA, NY, MA) fire broadly even when the rate is competitive within that state.
- **No tenant-specific rate awareness**: hyperscalers typically negotiate bespoke DC tariffs that materially differ from the filed industrial rate. The 0.5 hyperscaler scaling partially captures this but doesn't address the root cause.

## 4. Ground truth available

- EIA Form 861: state-level industrial retail rate monthly / annual. Already machine-readable.
- Utility-specific filed rates: in `reference_data.py` `UTILITY_RATES` structure already.
- DC-specific tariffs: `DC_TARIFFS` -- when present, often shows rates well below filed industrial rate.

## 5. Option A — Tighten deterministic

Replace absolute threshold with a **blended rule**:

```
fires iff rate > max(14 c/kWh, 1.25 * state_industrial_avg)
```

State-industrial-avg comes from `STATE_INDUSTRIAL_RATE_AVG_CENTS` (new constant table). 14 c/kWh stays as a hard floor because rates that high are economically relevant regardless of state norm. The 1.25x multiplier catches sites that are notably above their state norm even when below the 14c floor.

Add a P tier:
| Rate condition | Base P |
|---|---|
| rate > 20 | 0.25 |
| rate > 1.25 * state_avg OR rate > 14 | 0.15 |
| otherwise | 0.00 (doesn't fire) |

## 6. Option B — Qualitative

Semi-viable. Rate risk is real but often overlapped with tenant-specific tariff arrangements (hyperscalers pay what they negotiate, not what the state filing says). Keeping rate as a killer risks double-counting with tariff risk. But fully removing it loses the signal for merchant sites where the dev cannot negotiate.

## 7. Option C — Hybrid

Keep deterministic with state-relative threshold (Option A); add a narrative note in the report when DC_TARIFFS offers a materially lower rate than the filed industrial rate, flagging the "paper vs negotiated" gap.

## 8. Recommendation

**Option A (Tighten)**. Blended state-relative + absolute threshold; tiered P with a "very high" tier at 20 c/kWh. Seed `STATE_INDUSTRIAL_RATE_AVG_CENTS` with EIA 2024 data for the states we currently cover.

## 9. Proposed code changes

[reference_data.py](../../reference_data.py): add `STATE_INDUSTRIAL_RATE_AVG_CENTS` (dict of state -> cents/kWh, EIA 2024 annual average).

[scoring.py](../../scoring.py):

```python
HIGH_RATE_ABSOLUTE_FLOOR_CENTS = 14.0
HIGH_RATE_STATE_RELATIVE_MULT = 1.25
VERY_HIGH_RATE_CENTS = 20.0

def _p_high_rate(ctx) -> float:
    cents = (ctx.get("utility_rate") or {}).get("industrial_rate_cents")
    if cents is None: return 0.15
    if cents > VERY_HIGH_RATE_CENTS: return 0.25
    return 0.15

def _trigger_high_rate(ctx):
    cents = (ctx.get("utility_rate") or {}).get("industrial_rate_cents")
    if cents is None: return False
    state = (ctx.get("site_state") or "").upper()
    state_avg = STATE_INDUSTRIAL_RATE_AVG_CENTS.get(state)
    relative_trip = state_avg is not None and cents > HIGH_RATE_STATE_RELATIVE_MULT * state_avg
    absolute_trip = cents > HIGH_RATE_ABSOLUTE_FLOOR_CENTS
    if absolute_trip or relative_trip:
        components = []
        if absolute_trip: components.append(f">{HIGH_RATE_ABSOLUTE_FLOOR_CENTS} c/kWh absolute")
        if relative_trip: components.append(f">{HIGH_RATE_STATE_RELATIVE_MULT}x state avg ({state_avg:.1f})")
        return f"Industrial rate {cents:.1f} c/kWh triggers: {', '.join(components)}"
    return False
```

## 10. Regression pin updates

- `new_albany_oh`: AEP Ohio industrial rate ~8 c/kWh; below threshold; no trigger. No change.
- Add a new test case for a CA-style 15 c/kWh site to verify the absolute-floor trigger still works at rates above 14 but below 1.25x state avg.

## 11. Calibration hook

```sql
-- Does high rate actually correlate with merchant cancellation?
SELECT CASE WHEN industrial_rate_cents > 20 THEN 'very_high'
            WHEN industrial_rate_cents > 14 THEN 'high'
            WHEN industrial_rate_cents > state_avg * 1.25 THEN 'above_state'
            ELSE 'normal' END AS rate_bucket,
       AVG(CAST(status='cancelled' AS DOUBLE)) AS cancel_rate
FROM project_outcomes GROUP BY 1;
```
