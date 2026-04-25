# Screen Methodology — `Water` scorecard factor (1-5)

**Status:** Rewritten 2026-04-24. Prior version claimed more precision than the data supports.

## 1. What it tests

The 1-5 `Water` factor in the opportunity-side scorecard. 5% weight in `overall_score`.

Nominally: does the site have reliable access to process and make-up water?

## 2. Prior approach

```
dist_km < 5   -> 5
dist_km < 15  -> 4
dist_km < 30  -> 3
else          -> 2
```

`dist_km` is distance to the nearest HIFLD water/wastewater treatment facility.

## 3. Why this was thin

HIFLD's water-facility dataset flags the location of any water or wastewater facility — a 2 MGD village treatment plant looks the same as a 200 MGD regional system. There is no capacity attribute. So "nearest water facility < 5 km" could mean:

- Adjacent to a 200+ MGD regional system with surplus capacity (genuinely a 5)
- 4 km from a small municipal plant in a drought-stressed county with negligible allocation headroom (not a 5 at all — possibly a 1 if process water is genuinely unavailable)

The 1-5 banding pretends we have a capacity judgment. We have a proximity proxy.

Additionally, for hyperscale DC specifically:
- Many modern designs use air-side economizers, closed-loop cooling, or immersion cooling that minimize consumptive water use
- When water IS required, the binding constraint is typically water-rights allocation under state law, not physical proximity to a treatment plant
- Discharge permits (source water / receiving water body) often dominate the siting question more than intake availability

The old banding captured none of this — it answered "is there civic infrastructure here?" which is actually closer to a redundancy check on the `Transportation` factor.

## 4. New derivation

Three-tier banding instead of five, acknowledging the thinness:

| Nearest HIFLD water facility | Base score |
|---|---|
| < 10 km | 4 (adequate: civic infrastructure present) |
| 10-25 km | 3 (marginal: reachable, may need a lateral) |
| none within 25 km | 2 (remote: likely private well + hauling for construction) |

Plus an **arid-state cap**: sites in AZ, NM, NV, UT, CO, CA are floored one band lower (4 → 3, 3 → 2, 2 → 1). Rationale: these states have documented water-stress indices and/or active allocation moratoriums in DC-relevant counties (Maricopa, Clark, parts of Utah), so proximity to a facility is insufficient evidence of actual allocation availability.

Note: we deliberately do NOT award a top score (5) in this new banding. We do not have the data to claim any site is "water-abundant" in a DC-operations sense; the best we can honestly say is "civic infrastructure is present."

## 5. What would move this to a real screen

- **Water-rights data** by county/allocation-basin (USGS + state engineer offices).
- **DC water-use disclosures** (AWS, Google, Microsoft report by region; can be cross-referenced to known sites).
- **Drought monitor classifications** (US Drought Monitor per-county severity).

Until any of those are integrated, the factor intentionally carries lower variance and the report narrative flags it as a proxy.

## 6. Expected regression impact

- `hurt_ranch_nm`: arid-state cap applies. Was 2 (no water facility within 30 km). Now 1 (arid cap from base 2). Opportunity drops slightly; acceptable because NM water is genuinely constrained.
- `abilene_tx`: West TX is arid but TX isn't in the cap list (too much state heterogeneity; East TX is wet). Covered by narrative. No score change.
- `the_dalles_or`: near Columbia River — scorecard says 4, reality is 5. We under-score this site; acceptable trade-off for not over-scoring arid sites.
- Midwest/Southeast anchors: score 4 (was typically 4 or 5). Minor decrease; opportunity slightly lower but more honest.

## 7. Calibration hook

When we have per-site water-consumption disclosures (AWS/Google/MSFT region reports), check whether scorecard scores 4-5 sites actually have 10x the consumption of scores 1-2 sites. Hypothesis: they don't — the signal is noise beyond the arid/non-arid binary.

## 8. Related

- HIFLD water facilities (source)
- Potential upgrade: USGS Water Resources NLDI / state-engineer allocation data
