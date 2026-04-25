# Screen Methodology — _TEMPLATE_

_Copy this file to `<screen_name>.md` when reviewing a new screen. Keep every section: comparability across screens is the point._

## 1. What it tests

One paragraph stating the real-world risk this screen is meant to detect.

## 2. Current implementation

- **Trigger**: source file + function, with trigger predicate quoted.
- **Base P**:
- **Tenant scaling**:
- **Inputs**: which pipeline elements feed it.

## 3. Failure modes observed

- Site: what went wrong, and how we noticed.
- Site: ...

## 4. Ground truth available

Where could we backtest this? Name specific datasets / tables / filing types.

## 5. Option A — Tighten deterministic

What threshold / tiering / data-source change would make this more predictive?

## 6. Option B — Convert to qualitative

What does this screen look like as narrative color in the report, with zero contribution to feasibility math?

## 7. Option C — Hybrid

Deterministic core + qualitative expansion.

## 8. Recommendation

Which option and why (one paragraph).

## 9. Proposed code changes

File refs + minimal snippet showing the change.

## 10. Regression pin updates

Which `tests/regression_sites.json` entries need new `must_trigger`, `expected_feasibility`, or added `deal_killer_signals`.

## 11. Calibration hook

The exact query / dataset / method that would let us refit this screen's P after more ground truth arrives.
