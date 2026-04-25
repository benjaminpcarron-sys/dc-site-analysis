# Screen Methodology — `Utility Rate` scorecard factor (1-5)

**Status:** Rewritten 2026-04-24 to mirror the state-relative logic already in the `high_industrial_rate` killer.

## 1. What it tests

The 1-5 `Utility Rate` factor in the opportunity-side scorecard. Contributes to the legacy weighted `overall_score` (15% weight) and the opportunity average.

## 2. Prior approach and its problem

Absolute-cents banding, no state context:

```
< 4 c/kWh -> 5
< 6      -> 4
< 8      -> 3
< 10     -> 2
else     -> 1
```

This treats 10.5 c/kWh in California identically to 10.5 c/kWh in New Mexico, but these have opposite implications for DC economics:
- California industrial avg ~19.8 c/kWh → 10.5 c/kWh is a *great* rate, below state average.
- New Mexico industrial avg ~6.5 c/kWh → 10.5 c/kWh is 60% above state average, a genuinely bad rate.

The `high_industrial_rate` killer was updated (earlier in the April 2026 review) to use state-relative logic. Keeping the scorecard on absolute-cents created an internal inconsistency: a site could clear the killer while getting banded as a "2" on the scorecard, or vice versa.

## 3. New banding

```
absolute >= 20 c/kWh OR >= 1.5x state avg          -> 1 (extreme)
absolute >= 14 c/kWh OR >= 1.25x state avg          -> 2 (elevated; matches killer threshold)
<= 0.8x state avg                                   -> 5 (below state norm, genuine advantage)
<= 1.0x state avg                                   -> 4 (at or slightly below state norm)
absolute < 6 c/kWh                                  -> 5 (fallback when state avg missing)
absolute < 8                                        -> 4
absolute < 10                                       -> 3
else                                                -> 3 (missing data or borderline)
```

Rationale:
- **Band 1-2 thresholds mirror the killer**: the site penalties should be consistent across scorecard and feasibility math.
- **Band 4-5 are state-relative**: a site that beats the state norm has a real competitive rate advantage; a site at exactly state-avg is neutral-to-positive.
- **Absolute floors (6 / 8 c/kWh)** kick in when state avg data is missing — avoids scoring a 3 c/kWh site poorly just because we don't have a comparator.

## 4. What state avg comes from

`reference_data.STATE_INDUSTRIAL_RATE_AVG_CENTS` — EIA 2024 industrial rate averages per state. Hand-curated, refreshable from EIA Form 861 annually. `get_state_industrial_rate_avg(state)` returns None for states we haven't seeded (then fallback to absolute-cents).

## 5. Expected regression impact

- Most anchor sites (Ashburn VA, Altoona IA, Council Bluffs IA): industrial rates in the 6-9 c/kWh range vs state avg ~7-9 c/kWh → now score 4 (was 3 or 4). Opportunity rises slightly.
- CA / NY / MA sites (if we pin any): 10-15 c/kWh in a 19-23 c/kWh state → now score 4-5 (was 1-2). Material correction.
- Hurt Ranch NM (no matched utility rate): falls to the default 3. No change.
- New Albany OH (AEP Ohio industrial rate ~8 c/kWh, OH avg ~7.3 c/kWh): now score 3 (slightly above avg) rather than 3 under absolute bands. No material change.

## 6. Calibration hook

Backtest: DC operating-rate vs utility industrial-rate bucket, using both absolute cents and state-relative quantile. Hypothesis: the state-relative axis predicts DC site selection better than absolute cents, because developers benchmark within a state's regulatory/wholesale context.

## 7. Related

- `docs/screen_methodology/high_industrial_rate.md` — the killer-side state-relative logic this scorecard factor mirrors.
- `reference_data.STATE_INDUSTRIAL_RATE_AVG_CENTS` — the data source.
