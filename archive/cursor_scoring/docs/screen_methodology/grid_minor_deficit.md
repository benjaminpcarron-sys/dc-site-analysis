# Screen Methodology — `grid_minor_deficit` (RETIRED)

**Status:** Retired from `DEAL_KILLERS` on 2026-04-24.

This screen relied on the same `grid_assessment.max_mw` heuristic that drove the former `grid_severely_insufficient` killer. That value is a voltage-class proxy, not a capacity measurement; tiering a 50-75% vs 75-100% deficit on top of it was compounding false precision.

The new qualitative classifier `grid_outlook` (promising / neutral / doubtful) subsumes the function this screen tried to perform. See [`grid_severely_insufficient.md`](grid_severely_insufficient.md) for the replacement logic. There is intentionally no "minor deficit" tier in the new model — if a site's outlook is promising (has supply anchors) it scores no grid-risk contribution; if it's neutral or doubtful with no anchor, the single `power_outlook_doubtful` killer handles it with a flat P=0.40.

## Why no middle tier?

The old approach had three gradations (minor, moderate, severe/critical) because it treated deficit depth as a continuous number. With a qualitative classifier, there are only three directional answers — promising / neutral / doubtful — and the middle (neutral) is explicitly "no call" rather than a mid-severity kill. A site with ambiguous signals shouldn't be penalized at a baked-in P; it should be flagged for further diligence through the report narrative.

## Calibration note

If future labeled data suggests we're under-calling sites with modest-but-real grid gaps (e.g. operating cluster present but all large substations are at 138 kV and nearing thermal limits), the correct fix is a new supply-side signal in `grid_outlook`, not a new killer with a made-up P.
