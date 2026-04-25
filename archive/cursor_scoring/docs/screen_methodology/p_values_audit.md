# Killer P-Values Audit (2026-04-24)

A direct, no-laundering inventory of every probability used in the deal-killer catalog, what evidence supports each value, and where we are still relying on judgment dressed as math.

## Why this audit exists

After the grid pivot ("precision without accuracy"), we owe the same scrutiny to the remaining P values. Below, each killer is graded on *evidential basis*: how grounded the input signal is, and how grounded the resulting probability tier is.

| Grade | Meaning |
|---|---|
| A | Both input signal and P value rest on observable, citable data. |
| B | Input signal is observable; P value is engineering judgment, but reasoned from a published mechanism. |
| C | Input signal is observable; P value is pure judgment (round number with no derivation). |
| D | Input signal is itself partly judgment (hand-curated registry); P value is judgment. Defensible but should be flagged. |

Goal: the "honest answer" is to label C/D values as such in narratives and avoid implying they are calibrated.

---

## 1. `utility_moratorium`

| | |
|---|---|
| Probability | 0.90 flat |
| Tenant scaling | speculative 1.0 / anchored 0.95 / hyperscaler 0.90 |
| Input signal | `dc_tariffs[*].moratorium = True` |
| Source | Hand-curated `DC_TARIFFS` registry; signal is whether a utility's data-center tariff itself imposes a connection moratorium. |
| Grade | **D** |

The input is hand-curated (we maintain `DC_TARIFFS` ourselves), but moratorium status is publicly verifiable from each utility's tariff filings — the registry isn't subjective. The 0.90 P is judgment: a tariff-level moratorium with no defined lift is the closest thing in the catalog to a hard stop, but 0.90 vs 0.85 vs 0.95 isn't separately defensible.

**Honest framing:** "tariff-level moratoriums are the closest thing to a hard kill we model; absent a backtest corpus we treat them as roughly 90% project-killing."

**Calibration target:** count of pending DC interconnection requests in moratorium-utility service territories that subsequently completed — should be < 10% if 0.90 is right.

---

## 2. `regulatory_interconnection_pause`

| | |
|---|---|
| Probability | tiered by months until lift: ≤6mo 0.30 / ≤12mo 0.55 / ≤24mo 0.70 / >24mo 0.85 |
| Tenant scaling | speculative 1.0 / anchored 0.85 / hyperscaler 0.75 |
| Input signal | `regulatory_moratoriums` from hand-curated `REGULATORY_MORATORIUMS` registry; PSC/PUC docket numbers + expected_lift_date. |
| Source | Public docket filings (DE PSC 25-0826, IN IURC 45911, etc.). |
| Grade | **B** |

Input is observable (docket numbers are real, expected_lift_date is from filings). The tier mapping is reasoned: the "schedule slip eats project optionality" mechanism is real, and 6/12/24-month thresholds bracket typical hyperscaler plan horizons. But the specific P at each tier (0.30/0.55/0.70/0.85) is judgment.

**Honest framing:** the tier shape (more time-to-lift → more risk) is defensible; the absolute P values are anchored to "tariff moratoriums are 0.90; this is bounded above by that, and below by ~0.30 for short slips."

**Calibration target:** completion rates for DC projects announced during a pause vs after lift; ratio across pause-duration buckets.

---

## 3. `onerous_tariff_deposit`

| | |
|---|---|
| Probability | tiered by `deposit_severity`: light 0.05 / moderate 0.15 / onerous 0.30 / prohibitive 0.50 |
| Tenant scaling | speculative 1.0 / anchored 0.30 / hyperscaler 0.15 |
| Input signal | `dc_tariffs[*].deposit_severity` from hand-curated `DC_TARIFFS`. |
| Source | Tariff text (collateral / deposit / contract-term obligations). |
| Grade | **D** for severity rating, **B** for P tiers |

The 4-tier severity classification is judgment applied to real tariff language (5-year LOC > 10-year LOC, $10M deposit per MW vs none, etc.). The P tier shape — "light is nearly free for hyperscalers, prohibitive kills half the time even with creditworthy backing" — is reasoned. Tenant scaling is the strongest P modifier in the catalog and is clearly directionally right (hyperscaler IG credit makes deposits trivially-financed by the parent).

**Honest framing:** "we maintain a 4-tier severity classification of tariff collateral language; the absolute P at each tier is engineering judgment but the relative ordering is sound."

**Calibration target:** financial closing rates by deposit severity tier × tenant credit rating.

---

## 4. `power_outlook_doubtful`

| | |
|---|---|
| Probability | 0.40 flat |
| Tenant scaling | none |
| Input signal | `grid_outlook(ctx).verdict == "doubtful"` AND `not btm_gas_viable` (for credit-worthy tenants). |
| Source | Composite of HV proximity, brownfield, planned/large substations, state queue, cluster, announced-DC pressure (all observable). |
| Grade | **C** for P value, **B** for input |

Input signal is composite but each component is observable. The P value is a round number — picked to be material but not catastrophic, and intentionally below the moratorium tier. There is no derivation from outcome data.

**Honest framing:** "0.40 is a single round number meant to convey 'doubtful means project economics get harder, but not fatal.' This is not calibrated to outcome data."

**Calibration target:** completion rates of announced DC projects classified as 'doubtful' at announcement time vs 'promising' / 'neutral'.

---

## 5. `flood_zone_av`

| | |
|---|---|
| Probability | 0.50 flat |
| Tenant scaling | speculative 1.0 / anchored 0.9 / hyperscaler 0.8 |
| Input signal | FEMA flood zone classification starting with "A" or "V". |
| Source | FEMA NFHL — observable, official. |
| Grade | **C** |

Input is rock-solid. P=0.50 is a round number suggesting "half of A/V-zone DC projects die" — which is plausibly too high. Many DC projects in coastal markets *do* build in flood-prone areas with elevated platforms / mitigation (e.g., portions of Northern Virginia's western Loudoun growth, eastern Pennsylvania's flood-mitigated sites). Some FEMA Zone A delineations also turn out to be revisable via LOMR.

**Risk of being wrong:** The flat 0.50 likely *over-fires* on:
- Sites where the zone boundary clips a corner of the parcel (not the building footprint)
- Sites with active or completed LOMR / engineered fill
- Hyperscaler tenants who routinely engineer around flood risk on premium sites

**Suggested next step (not implemented now):** distinguish Zone A (1% annual, riverine) from Zone V (1% annual + wave action, coastal) — Zone V is meaningfully harder to mitigate. Could split into 0.65 (V) / 0.45 (A). Or add a "% of parcel in zone" tier when parcel data is available.

**Honest framing:** "FEMA A/V is a real flag but flat 0.50 is conservative and undifferentiated. Zone V should probably be higher; clipped Zone A on a large parcel should probably be lower."

---

## 6. `severe_nonattainment`

| | |
|---|---|
| Probability | tiered by NAAQS classification: Serious 0.30 / Severe 0.40 / Extreme 0.55 |
| Tenant scaling | none |
| Input signal | `nonattainment_zones[*].classification` |
| Source | EPA Green Book — observable, official. |
| Grade | **B** |

Input is solid. The tier shape mirrors the underlying regulatory burden (PSD applicability, offset ratios, BACT vs LAER) — that's a defensible mechanism. The specific P values are picked to land below tariff-moratorium severity (Extreme 0.55) and above an "elevated but not killing" floor (Serious 0.30). Reasoned, not measured.

**Honest framing:** "P scales with the regulatory burden imposed by EPA classification; the relative ordering is sound, the absolute P values are calibrated by reasoning about offset costs and permit duration, not by outcome data."

---

## 7. `high_seismic`

| | |
|---|---|
| Probability | tiered by SDC class: D 0.05 / E 0.15 / F 0.30 |
| Tenant scaling | none |
| Input signal | `seismic.seismic_design_category` (ASCE 7-22). |
| Source | USGS ground-motion + ASCE 7-22 maps — observable, official. |
| Grade | **B** |

Input is solid. SDC D (the most common high-seismic class) gets P=0.05, intentionally low because The Dalles, Quincy WA, and other major DC clusters all sit in SDC D and routinely get built. SDC F (rare; major fault adjacency) gets P=0.30, reflecting the cost-of-construction premium and peer-review overhead that does in fact deter some siting.

**Honest framing:** the tier shape "SDC D is a routine cost premium, F is a financing headwind" is defensible from cost-per-MW evidence (SDC F adds ~10-15% to structural; SDC D adds 3-5%). Specific P values are judgment about whether that cost premium is enough to kill the project. Anchored to observed willingness of hyperscalers to build in SDC D regions.

---

## 8. `high_industrial_rate`

| | |
|---|---|
| Probability | base 0.15, raised to 0.25 if rate > 20 c/kWh |
| Tenant scaling | speculative 1.0 / anchored 0.8 / hyperscaler 0.5 |
| Input signal | EIA `industrial_rate_cents` (utility-level), compared to absolute floor (14 c/kWh) and `STATE_INDUSTRIAL_RATE_AVG_CENTS * 1.25`. |
| Source | EIA + hand-curated state averages. |
| Grade | **B** |

Input is observable. Two-path trigger (absolute OR state-relative) means a site can fire as "expensive in California even at state-avg rate" or "expensive everywhere absolute." The two-tier P (0.15 base, 0.25 above 20c) captures that very high rates kill more projects. Tenant scaling is steep because hyperscalers can negotiate special-load tariffs that materially diverge from the published industrial rate.

**Honest framing:** the P shape (relatively low base + tenant scaling) is right; hyperscalers don't pay published rates. Speculative tenants do, and 0.15 / 0.25 reflects that the rate is one factor in a multi-factor decision, not a sole killer.

---

## Catalog-wide observations

### Fully judgmental (C/D) values

| Killer | P | Concern |
|---|---|---|
| `utility_moratorium` | 0.90 flat | Round number, no derivation. Defensible but not calibrated. |
| `power_outlook_doubtful` | 0.40 flat | Round number, no derivation. By design — we just retired the false-precision approach. |
| `flood_zone_av` | 0.50 flat | Likely conservative; doesn't differentiate Zone A vs V or partial-parcel coverage. |

### Tiered values where shape is defensible but absolute levels are judgment

`regulatory_interconnection_pause`, `onerous_tariff_deposit`, `severe_nonattainment`, `high_seismic`. All have published, mechanistic justifications for tier ordering; the specific P at each tier is engineering reasoning anchored against a relative scale (worst killer = 0.90, mildest = 0.05).

### Where calibration would help most

1. **`flood_zone_av`** — the 0.50 flat is the highest-leverage opportunity to either tighten or differentiate. A "% of buildable area in zone" + Zone-A-vs-V split could be implemented from parcel data we may already have.
2. **`power_outlook_doubtful`** — by design uncalibrated, but tracking promised/announced DC project completion rates by outlook verdict would tell us whether 0.40 is roughly right.
3. **`utility_moratorium`** — easiest backtest: count post-moratorium DC interconnections in known moratorium territories.

### Tenant scaling — directional review

| Killer | Speculative | Anchored | Hyperscaler | Comment |
|---|---|---|---|---|
| `utility_moratorium` | 1.00 | 0.95 | 0.90 | Minimal scaling; correct — moratorium is structural, not tenant-dependent. |
| `regulatory_interconnection_pause` | 1.00 | 0.85 | 0.75 | Modest scaling; hyperscalers can wait through pauses. Reasonable. |
| `onerous_tariff_deposit` | 1.00 | 0.30 | 0.15 | Steep — correctly reflects that IG credit makes deposits trivial. Most aggressive scaling in catalog. |
| `power_outlook_doubtful` | none | none | none | Intentional — outlook is structural to the geography, not tenant-driven. |
| `flood_zone_av` | 1.00 | 0.90 | 0.80 | Modest; arguable — hyperscalers may actually be MORE willing to engineer around flood, suggesting steeper scaling (0.7 or 0.6). |
| `severe_nonattainment` | none | none | none | Could plausibly add scaling (hyperscalers absorb offset costs better). Currently flat. |
| `high_seismic` | none | none | none | Cost premium is structural. Flat is right. |
| `high_industrial_rate` | 1.00 | 0.80 | 0.50 | Steep, correct — hyperscalers negotiate special tariffs. |

**Suggested follow-ups (not implemented):**
- Add tenant_scaling to `flood_zone_av` (0.7 hyperscaler) to reflect mitigation willingness.
- Consider adding modest tenant_scaling to `severe_nonattainment` (0.85 hyperscaler) to reflect offset-cost absorption.

---

## What this audit does NOT do

- It does not change any P value. The point is to make the basis transparent.
- It does not derive new values from outcome data — we don't have the corpus.
- It is not a substitute for backtesting. When a labeled corpus of (announced → built / cancelled) DC projects is available, every P here should be re-anchored.

## Related

- `docs/screen_methodology/grid_severely_insufficient.md` — the "precision without accuracy" rewrite that motivated this audit.
- `docs/SCREEN_REVIEW.md` — index of all per-screen reviews.
