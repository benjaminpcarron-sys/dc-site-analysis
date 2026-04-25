# Screen Methodology — `onerous_tariff_deposit`

## 1. What it tests

Whether the utility's large-load tariff imposes collateral, minimum-billing, or exit-fee commitments that are burdensome enough to deter merchant / speculative developers. The classic example is AEP Ohio Schedule DCT: 50% of minimum charges as upfront collateral (full-term) for customers below A-/A3 credit, plus 3-year exit fee. This is fatal for a merchant dev with no IG backstop and nearly invisible to a hyperscaler.

## 2. Current implementation

- **Trigger**: `_trigger_onerous_deposit` in [scoring.py](../../scoring.py). Fires when any matched DC tariff has `deposit_onerous = True` (binary hand-flag in [reference_data.py](../../reference_data.py) `DC_TARIFFS`).
- **Base P**: `0.30` (flat).
- **Tenant scaling**: `1.0 / 0.4 / 0.15`.
- **Inputs**: `dc_tariffs[*].deposit_onerous`, `dc_tariffs[*].collateral_desc`, `dc_tariffs[*].exit_fee_desc`.

## 3. Failure modes observed

- **New Albany OH**: fires on AEP Ohio Schedule DCT as expected. Speculative P=0.30, hyperscaler P=0.045. Correctly differentiates merchant vs anchor.
- **Ambiguity in `deposit_onerous` flag**: the binary is hand-set by whoever authored the tariff entry. No rubric in the code comments or the `DC_TARIFFS` file. Reviewing the entries, the flag is set based on qualitative judgment of `collateral_desc` -- e.g. Dominion VA (`85% min billing for T&D`) is flagged as `deposit_onerous=False` while AEP (`50% of minimum charges as collateral`) is `True`. This is defensible but non-reproducible.
- **No severity ladder**: a tariff with $100K load-study fees only and a tariff with $50M upfront collateral both look the same in the binary.

## 4. Ground truth available

- `demand_ledger.duckdb` has project status + utility. For each utility with a known onerous tariff, compute merchant-tenant cancellation rate over 24 months; compare to peer utility.
- Public filings: SCC/PUCO order PDFs enumerate collateral terms. We could parse the MW-weighted collateral-as-percent-of-annual-revenue for each tariff.
- Credit rating agency coverage of utility tariff risk.

## 5. Option A — Tighten deterministic

Replace the binary flag with a four-tier `deposit_severity` field:

| Tier | Criterion (illustrative) | Base P |
|---|---|---|
| light | Load-study fee only, no collateral | 0.05 |
| moderate | Collateral <= 10% of full-term revenue OR credit-gated without full-term | 0.15 |
| onerous | Collateral 10-30% of full-term revenue (most existing "True" flags) | 0.30 |
| prohibitive | Collateral > 30% of full-term revenue OR >12 months upfront deposit | 0.50 |

Hand-review each of the ~11 current tariff entries and assign a tier. Each entry carries a one-line rationale for reproducibility.

## 6. Option B — Convert to qualitative

Not viable. Tariff collateral is the most concrete merchant-vs-hyperscaler differentiator and drove the New Albany calibration. Removing it would lose the only mechanism that correctly predicts merchant sites fail where hyperscalers succeed under identical physical conditions.

## 7. Option C — Hybrid (RECOMMENDED)

Tiered deterministic P (Option A) plus a narrative block in the report listing the specific collateral / minimum-billing / exit-fee terms so readers can re-price for their own tenant profile without trusting the classification.

## 8. Recommendation

**Option C (Hybrid)**. Add `deposit_severity` field to `DC_TARIFFS` entries; add a `probability_fn` helper that maps severity -> P; surface the tariff's `collateral_desc` + `exit_fee_desc` in the report evidence string so the numbers are readable, not just "onerous." Keep the existing `deposit_onerous` binary as a fallback (defaults `deposit_severity = "onerous" if deposit_onerous else "light"`) so existing entries work without hand-edits.

## 9. Proposed code changes

[reference_data.py](../../reference_data.py):

```python
# In each DC_TARIFFS entry:
"deposit_severity": "onerous",   # light | moderate | onerous | prohibitive
"deposit_severity_rationale": "50% of minimum charges as collateral for full 12-year term if credit below A-/A3; load-study fees up to $100K.",
```

[scoring.py](../../scoring.py):

```python
_DEPOSIT_SEVERITY_P = {
    "light": 0.05, "moderate": 0.15, "onerous": 0.30, "prohibitive": 0.50,
}

def _p_onerous_deposit(ctx):
    ts = [t for t in (ctx.get("dc_tariffs") or []) if _tariff_deposit_severity(t) != "light"]
    if not ts: return 0.30
    worst = max((_tariff_deposit_severity(t) for t in ts), key=lambda s: _DEPOSIT_SEVERITY_P[s])
    return _DEPOSIT_SEVERITY_P[worst]

def _tariff_deposit_severity(t):
    return t.get("deposit_severity") or ("onerous" if t.get("deposit_onerous") else "light")
```

Trigger fires when any tariff's severity is >= `"moderate"`. Evidence string names severity + quotes `collateral_desc`.

## 10. Regression pin updates

- `new_albany_oh`: AEP Ohio Schedule DCT gets `deposit_severity = "onerous"` (matches existing flag), so P is unchanged at 0.30. `expected_feasibility ~ 0.47` stays.
- `decatur_il`: IL tariff currently has no DC-specific entry, so tariff-match returns []; no change.
- New: pin `deal_killer_signals.dc_tariffs.deposit_severity = "onerous"` for New Albany so the tier surfaces in regression.

## 11. Calibration hook

For each utility with a tariff entry:

```sql
SELECT utility, deposit_severity,
       COUNT(*) FILTER (WHERE tenant_class='merchant' AND status='cancelled') / NULLIF(COUNT(*) FILTER (WHERE tenant_class='merchant'), 0) AS merchant_cancel_rate,
       COUNT(*) FILTER (WHERE tenant_class='hyperscaler' AND status='operating') / NULLIF(COUNT(*) FILTER (WHERE tenant_class='hyperscaler'), 0) AS hyperscaler_success_rate
FROM project_outcomes
GROUP BY 1, 2;
```

Rank-correlation between severity-tier ordering and observed merchant-cancellation rate is the refit target.
