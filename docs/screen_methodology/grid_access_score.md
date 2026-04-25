# Screen Methodology — `Grid Access` scorecard factor (1-5)

**Status:** Rewritten 2026-04-24 as a follow-on to the `grid_outlook` rewrite. The prior derivation from `grid_assessment.max_mw` was retired for the same reason.

## 1. What it tests

The 1-5 `Grid Access` factor in the opportunity-side scorecard, which:
- Contributes to the legacy weighted `overall_score` (20% weight — the largest single factor)
- Contributes to the new opportunity average (`compute_opportunity` in `scoring.py`)

## 2. Why the prior approach was wrong

`compute_scores["Grid Access"] = d.get("grid_assessment", {}).get("score", 1)` — and `grid_assessment.score` was a 5-band mapping of `max_mw / target_mw`:

```
ratio >= 1.5 -> 5
ratio >= 1.0 -> 4
ratio >= 0.5 -> 3
ratio >= 0.25 -> 2
else -> 1
```

`max_mw` is computed in `grid_assessment.py` from the nearest transmission-line voltage class with a substation/multi-line multiplier. Same voltage-class heuristic that drove the retired `grid_severely_insufficient` killer.

We retired the killer on 2026-04-24 because the underlying number isn't a capacity study — it's a proxy. Leaving the same number as the backbone of the highest-weighted scorecard factor would preserve the same dishonesty via the back door: a site like Hurt Ranch NM (115 kV rural coop line 14 km away) would still score 1/5, dragging opportunity down with false precision — just through the scorecard instead of through a killer probability.

## 3. New derivation

`Grid Access` is now computed in `dc_site_report.compute_scores` from two honest inputs:

1. **`grid_outlook` verdict** (promising / neutral / doubtful) — the qualitative supply-vs-demand classifier. See [`grid_severely_insufficient.md`](grid_severely_insufficient.md).
2. **Observable HV proximity** — is an HV (≥100 kV) transmission line within 10 km? within 30 km? Is a large substation (≥230 kV or ≥5 circuits) within 10 km?

### Mapping

| Outlook | HV ≤10 km OR large sub ≤10 km | Score |
|---|---|---|
| Promising | yes | 5 |
| Promising | no | 4 |
| Neutral | HV ≤10 km | 4 |
| Neutral | HV 10-30 km | 3 |
| Neutral | no HV ≤30 km | 2 |
| Doubtful | — | 1 |

Rationale:
- **Promising (anchor present)**: The site has a brownfield / planned substation / large existing substation nearby. 5 when there's also direct HV reach; 4 when the anchor is credible but the immediate HV route is indirect (still materially easier than greenfield).
- **Neutral**: No anchor, but HV access determines whether this is "serviceable with effort" (4) or "needs a meaningful build" (2-3).
- **Doubtful**: 1 — the power picture is poor enough that the killer may fire; scorecard reflects the same direction honestly.

## 4. What is NOT used

- `grid_assessment.max_mw` — retained in the report as a "rough HV-line MW proxy" with an explicit disclaimer. Does not drive any scoring decision.
- `grid_assessment.score` — same. Still emitted for backwards compat with the narrative section, but no scoring factor reads it.
- `grid_assessment.upgrade_needed` — same.

This is a key architectural constraint: **the `max_mw` heuristic lives only in narrative, never in math.** Any future feature that wants a quantitative grid answer must produce it from real data (system impact studies, publish PJM/MISO/ERCOT queue dwell, etc.) rather than re-deriving it from the heuristic.

## 5. Regression behavior

- `hurt_ranch_nm`: Neutral outlook + 115 kV at 14 km + no large sub → HV within 30 km but not within 10 km → **Grid Access = 3** (was 1 under the old mapping). Opportunity rises correspondingly; feasibility goes from 0.10 → ~0.45 as pinned.
- `millsboro_de`: Promising (Indian River brownfield) + HV available + no large sub within 10 km → **5** (was likely 1 under the old mapping because target 500 MW vs estimated 180 MW max = 0.36 ratio = 2; brownfield wasn't visible to the scorecard). Opportunity credit for the brownfield is now coherent between killers and scorecard.
- `new_albany_oh`, `ashburn_va`, cluster sites: Promising + large subs within 10 km → **5**. No change from typical behavior but now for the honest reason.
- `the_dalles_or`: Needs check — BPA territory, transmission lines present. Likely 4-5 depending on substation coverage.

## 6. Calibration hook

Once a labeled corpus of built/cancelled DC sites exists, regress observed outcomes on this 5-band mapping. If promising-verdict sites without HV proximity (score 4) cancel at the same rate as promising+HV (score 5), collapse them. If neutral sites at score 3 cancel at the same rate as doubtful (score 1), reconsider whether "neutral" is a meaningful middle ground for opportunity purposes.

## 7. Related

- [grid_severely_insufficient.md](grid_severely_insufficient.md) — the parent rewrite
- [grid_minor_deficit.md](grid_minor_deficit.md) — retired companion
- `scoring.grid_outlook`, `scoring._hv_line_within`, `scoring._large_substation_nearby` — the shared helpers
