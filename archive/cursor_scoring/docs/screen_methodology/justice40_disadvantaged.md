# Screen Methodology — `justice40_disadvantaged`

## 1. What it tests

Whether the site sits in a Climate & Economic Justice Screening Tool (CEJST) designated "disadvantaged community" census tract. Intent: flag sites where NEPA review may incorporate environmental-justice analysis that materially extends federal permitting timelines or adds community-engagement obligations.

## 2. Current implementation

- **Trigger**: `_trigger_justice40` in [scoring.py](../../scoring.py). Fires when `justice40.is_disadvantaged = True`.
- **Base P**: `0.05` (previously `0.10`, lowered after anchor-site calibration confirmed the signal fires on nearly every built urban/suburban DC).
- **Tenant scaling**: `1.0 / 1.0 / 1.0`.
- **Inputs**: `justice40.is_disadvantaged`.

## 3. Failure modes observed

- **Fires on essentially every built anchor**: Ashburn VA, New Albany OH, Dallas, Quincy WA, Santa Clara CA all intersect at least one disadvantaged CEJST tract. This is the signal you *want* for generic community-engagement awareness but the wrong signal for a deal-killer — it's a false positive at the class level.
- **Binary is too coarse**: a site where the nearest CEJST-designated tract is 20 km away reads the same as a site whose operations will be inside the tract. The boolean doesn't capture overlap intensity.
- **Policy volatility**: Justice40 is an executive-order framework. Its regulatory weight changes with administration. A 2024 federal project scrutinised under EO 14008 is functionally different from a 2026 project after changes in federal EJ policy.

## 4. Ground truth available

- `demand_ledger.duckdb` project outcomes, cross-referenced to CEJST overlap.
- Federal permit-duration data: NEPA EIS preparation time for DCs historically averages 12-18 months regardless of Justice40 designation (primary driver is project footprint and federal-nexus magnitude, not EJ tract overlap).

## 5. Option A — Tighten deterministic

Possible via CEJST overlap-area weighting (% of site footprint inside disadvantaged tract). But this requires spatial intersect math and still retains the policy-volatility problem. Limited upside.

## 6. Option B — Convert to qualitative (RECOMMENDED)

Retire `justice40_disadvantaged` from `DEAL_KILLERS`. Replace with a narrative block in the report:

- Whether the site intersects a disadvantaged tract.
- Which CEJST categories drive the designation (energy burden, air quality, health, etc.).
- A one-sentence implication: "Federal-nexus projects here may face expanded community-engagement obligations under EO 14008 or successor orders."

This gives readers the signal without the model over-calling feasibility-Poor on routine urban sites.

## 7. Option C — Hybrid

Possible (keep a very-low P like 0.02 + narrative) but at this level the math contribution is noise. Retire cleanly.

## 8. Recommendation

**Option B (Qualitative)**. Retire from `DEAL_KILLERS`. Surface as `justice40_narrative(ctx)` helper that the report consumes. Catalog size drops from 10 to 9.

## 9. Proposed code changes

[scoring.py](../../scoring.py):

- Remove the `DealKiller` entry for `justice40_disadvantaged`.
- Keep `_trigger_justice40` as a helper; add `justice40_narrative(ctx) -> list[str]`.

[report_template.py](../../report_template.py):

- Existing Justice40 block stays (already a narrative). Add CEJST-category detail if available in payload.

[tests/test_regression.py](../../tests/test_regression.py):

- Update `assert len(DEAL_KILLERS) == 9`.

## 10. Regression pin updates

- `millsboro_de`: currently has `justice40_disadvantaged` in `must_trigger_killers`. Move it out (killer no longer exists). Recalc `expected_feasibility`: removing P=0.05 (hyperscaler-gated anyway) raises feasibility by a few percentage points. Pin tolerance of 0.15 absorbs it, but update `notes`.
- `hurt_ranch_nm`: had j40 as `must_trigger`; remove.
- Any other pin with `justice40_disadvantaged` in `must_trigger_killers`.

## 11. Calibration hook

```sql
-- Does CEJST overlap predict actual DC outcome?
SELECT cejst_overlap_pct_bucket,
       COUNT(*) AS n,
       AVG(CAST(status='operating' AS DOUBLE)) AS build_rate,
       AVG(nepa_eis_months) AS avg_nepa_duration
FROM project_outcomes
GROUP BY 1;
```

Hypothesis: overlap-area is weakly correlated with build rate. If it is, the deterministic killer can return with area-weighted threshold; if not, narrative-only is correct.
