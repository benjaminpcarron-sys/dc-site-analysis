"""Regression harness for the DC site analysis pipeline.

Each pinned site in ``regression_sites.json`` is run through the full pipeline
and asserted against:

  1. Geocoder hits the expected state (and county, if specified).
  2. Every element listed in ``must_cover`` returned a non-null value.
  3. The overall scorecard average is within ``score_tolerance`` of the pinned
     value -- this catches silent regressions in any scoring threshold or
     weight without committing us to an exact number that legitimately drifts
     when reference data is updated.
  4. Any pinned ``deal_killer_signals`` are still present in the output.

Skip behavior
-------------
Tests are skipped (not failed) when:
  * The spatial cache is missing (running before ``--prepare-cache``).
  * Geocoding fails entirely (offline, rate limited, address removed from OSM).
This keeps the harness usable on a fresh checkout while still catching real
regressions when run locally with the data in place.

Run with::

    python3 -m pytest tests/ -v
    python3 -m pytest tests/test_regression.py::test_site[decatur_il] -v
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dc_site_report import compute_scores  # noqa: E402  (path-mutated)
from pipeline import (  # noqa: E402
    coverage_summary,
    default_registry,
    errored_elements,
    missing_elements,
    run_pipeline,
)
from scoring import compute_feasibility  # noqa: E402


SITES_FILE = Path(__file__).parent / "regression_sites.json"
WEIGHTS = {
    "Grid Access": 20,
    "Utility Rate": 15,
    "Environmental": 15,
    "Fiber/Telecom": 10,
    "Water": 5,
    "Transportation": 5,
    "Tax Incentives": 15,
    "DC Tariff Risk": 15,
}


def _load_sites():
    with open(SITES_FILE) as f:
        return json.load(f)["sites"]


def _cache_present() -> bool:
    cache = ROOT / "data" / "cache"
    required = ["transmission_lines.parquet", "service_territories.parquet"]
    return all((cache / f).exists() for f in required)


def _resolve_path(value: dict | list, dotted: str):
    """Walk ``dotted`` (e.g. 'dc_tariffs.deposit_onerous') against a value.

    For lists, looks at the first element. Returns None if any segment misses.
    """
    cur = value
    for part in dotted.split("."):
        if isinstance(cur, list):
            cur = cur[0] if cur else None
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


SITES = _load_sites()


@pytest.fixture(scope="module")
def registry():
    return default_registry()


@pytest.mark.parametrize("site", SITES, ids=[s["id"] for s in SITES])
def test_site(site, registry, capsys):
    """Run the full pipeline for a pinned site and assert against ground truth."""
    if not _cache_present():
        pytest.skip("spatial cache not built (run `python dc_site_report.py --prepare-cache`)")

    from geocoder import geocode

    try:
        geo = geocode(site["address"])
    except Exception as e:
        pytest.skip(f"geocode failed for {site['address']}: {e}")

    if not geo or "lat" not in geo:
        pytest.skip(f"geocoder returned no coords for {site['address']}")

    # 1. Geocoder hit the expected state / county
    assert geo.get("state") == site["expected_state"], (
        f"Geocoder regressed: expected state={site['expected_state']!r}, "
        f"got {geo.get('state')!r} for {site['address']!r}"
    )
    if "expected_county" in site:
        assert geo.get("county") == site["expected_county"], (
            f"Geocoder regressed: expected county={site['expected_county']!r}, "
            f"got {geo.get('county')!r}"
        )

    # 2. Run the pipeline
    ctx = {
        "address": site["address"],
        "lat": geo["lat"],
        "lon": geo["lon"],
        "state": geo.get("state"),
        "county": geo.get("county", ""),
        "target_mw": site.get("target_mw"),
        "tenant_profile": site.get("tenant_profile", "speculative"),
    }
    run_pipeline(ctx, registry)

    # Surface useful debug info on failure
    summary = coverage_summary(ctx)
    errors = errored_elements(ctx)
    if errors:
        with capsys.disabled():
            print(f"\n[{site['id']}] element errors:")
            for name, err in errors:
                print(f"  {name}: {err}")

    # 3. Required elements are covered (allow None for elements outside HIFLD NE coverage zone, etc.)
    missing = set(missing_elements(ctx))
    must = set(site.get("must_cover", []))
    not_covered = sorted(must & missing)
    assert not not_covered, (
        f"[{site['id']}] required elements have null coverage: {not_covered}\n"
        f"Coverage summary: {summary}\n"
        f"Address: {site['address']}"
    )

    # 4. Score is within tolerance
    scores = compute_scores(ctx)
    overall = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS) / sum(WEIGHTS.values())

    expected = site["expected_overall_score"]
    tol = site.get("score_tolerance", 0.5)
    assert abs(overall - expected) <= tol, (
        f"[{site['id']}] overall score regressed: expected {expected:.2f} +/- {tol}, "
        f"got {overall:.2f}\n"
        f"Per-factor scores: {scores}"
    )

    # 5. Known gaps -- if any documented gap is now actually covered, fail loudly
    # so we remember to promote it to must_cover. This catches "I fixed something
    # but forgot to update the harness."
    newly_fixed = [name for name in site.get("known_gaps", {}) if name not in missing]
    assert not newly_fixed, (
        f"[{site['id']}] elements in known_gaps now have coverage: {newly_fixed}. "
        f"Move them from 'known_gaps' to 'must_cover' in regression_sites.json."
    )

    # 6. Pinned deal-killer signals still present (raw data-level checks)
    for path, expected_val in site.get("deal_killer_signals", {}).items():
        # Path is e.g. "dc_tariffs.deposit_onerous" -> ctx["dc_tariffs"][0]["deposit_onerous"]
        head, _, tail = path.partition(".")
        actual = _resolve_path(ctx.get(head), tail) if tail else ctx.get(head)
        assert actual == expected_val, (
            f"[{site['id']}] deal-killer signal {path!r} regressed: "
            f"expected {expected_val!r}, got {actual!r}"
        )

    # 7. Risk-adjusted feasibility checks
    feas = compute_feasibility(ctx, scores)
    triggered_names = {tk["name"] for tk in feas["triggered_killers"]}

    must_trigger = set(site.get("must_trigger_killers", []))
    missing_killers = sorted(must_trigger - triggered_names)
    assert not missing_killers, (
        f"[{site['id']}] expected deal-killers did not fire: {missing_killers}\n"
        f"Triggered: {sorted(triggered_names)}"
    )

    must_not_trigger = set(site.get("must_not_trigger_killers", []))
    wrongly_fired = sorted(must_not_trigger & triggered_names)
    assert not wrongly_fired, (
        f"[{site['id']}] deal-killers fired that should not: {wrongly_fired}"
    )

    if "expected_feasibility" in site:
        expected_feas = site["expected_feasibility"]
        feas_tol = site.get("feasibility_tolerance", 0.10)
        assert abs(feas["feasibility"] - expected_feas) <= feas_tol, (
            f"[{site['id']}] feasibility regressed: expected {expected_feas:.2f} +/- {feas_tol}, "
            f"got {feas['feasibility']:.2f}\n"
            f"opportunity={feas['opportunity']:.2f} combined_risk={feas['combined_risk']:.2f}\n"
            f"killers: {[(tk['name'], tk['probability']) for tk in feas['triggered_killers']]}"
        )


def test_scoring_deal_killer_math():
    """Pin the combination math so recalibrating individual P values is intentional."""
    from scoring import combined_risk, compute_opportunity

    assert combined_risk([]) == 0.0
    assert combined_risk([1.0]) == 1.0
    assert abs(combined_risk([0.5, 0.5]) - 0.75) < 1e-9
    assert abs(combined_risk([0.3, 0.3, 0.3]) - (1 - 0.7 ** 3)) < 1e-9

    scores = {
        "Grid Access": 5, "Utility Rate": 5, "Fiber/Telecom": 5,
        "Water": 5, "Transportation": 5, "Tax Incentives": 5,
        "DC Tariff Risk": 1, "Environmental": 1,
    }
    # compute_opportunity returns (score, cluster_evidence); without ctx, no cluster.
    opp, cluster = compute_opportunity(scores)
    assert opp == 1.0
    assert cluster is None

    # Cluster boost applies when nearby_dcs present.
    ctx = {"nearby_dcs": [{"dist_km": 5.0} for _ in range(6)]}
    opp2, cluster2 = compute_opportunity(scores, ctx)
    assert cluster2 is not None
    # Opportunity already at 1.0 ceiling; boost caps.
    assert opp2 == 1.0


def test_tenant_profile_scales_deal_killers():
    """Hyperscaler onerous-deposit kill risk must be dramatically lower than speculative."""
    from scoring import DEAL_KILLERS

    onerous = next(k for k in DEAL_KILLERS if k.name == "onerous_tariff_deposit")
    p_spec = onerous.adjusted_probability("speculative")
    p_anc = onerous.adjusted_probability("anchored")
    p_hyp = onerous.adjusted_probability("hyperscaler")
    assert p_spec > p_anc > p_hyp, (
        f"Tenant scaling should monotonically decrease risk: "
        f"speculative={p_spec}, anchored={p_anc}, hyperscaler={p_hyp}"
    )
    assert p_hyp < 0.1, "Hyperscalers should clear onerous-deposit thresholds (P<0.1)"


def test_grid_outlook_verdict_from_signals():
    """grid_outlook classifier: promising if any supply anchor (brownfield,
    planned substation, or large existing substation); doubtful if no supply
    anchor AND no HV line within 30 km; neutral otherwise.
    See docs/screen_methodology/grid_severely_insufficient.md."""
    from scoring import grid_outlook

    # Remote + no anchors -> doubtful.
    ctx_remote = {
        "nearby_dcs": [],
        "transmission_lines": [],
        "substations": [],
        "planned_substations": [],
        "brownfield_interconnection": [],
        "interconnection_queue": [],
    }
    assert grid_outlook(ctx_remote)["verdict"] == "doubtful"

    # Brownfield present (Millsboro-style) -> promising.
    ctx_bf = dict(ctx_remote, brownfield_interconnection=[{
        "id": "indian_river_de", "name": "Indian River Power Plant",
        "former_mw": 785, "voltage_classes": ["230"], "dist_km": 0.8,
    }], target_mw=500)
    assert grid_outlook(ctx_bf)["verdict"] == "promising"

    # Large existing substation within 10 km -> promising.
    ctx_sub = dict(ctx_remote, substations=[{
        "name": "Big Bend", "max_infer": 500, "lines": 6, "dist_km": 4.2,
    }])
    assert grid_outlook(ctx_sub)["verdict"] == "promising"

    # HV line nearby but no supply anchor -> neutral (not doubtful, not promising).
    ctx_hv_only = dict(ctx_remote, transmission_lines=[{
        "volt_class": "345", "dist_km": 12.0,
    }])
    assert grid_outlook(ctx_hv_only)["verdict"] == "neutral"


def test_power_outlook_doubtful_killer_fires_on_remote_site():
    """power_outlook_doubtful fires on grid-remote sites with no supply
    anchors, and is suppressed by BTM gas for credit-worthy tenants.
    Replaces the retired grid_severely_insufficient killer."""
    from scoring import _trigger_power_outlook_doubtful

    ctx_remote = {
        "nearby_dcs": [],
        "transmission_lines": [],
        "substations": [],
        "planned_substations": [],
        "brownfield_interconnection": [],
        "interconnection_queue": [],
        "gas_pipelines": [],
        "tenant_profile": "speculative",
    }
    # Remote + speculative: fires.
    assert _trigger_power_outlook_doubtful(ctx_remote)

    # Same verdict, but BTM-gas available and tenant is hyperscaler: suppressed.
    ctx_btm = dict(
        ctx_remote,
        gas_pipelines=[{"operator": "Williams", "type": "Interstate", "dist_km": 8.0}],
        tenant_profile="hyperscaler",
    )
    assert not _trigger_power_outlook_doubtful(ctx_btm)

    # BTM-gas available but tenant is speculative: still fires (can't finance BTM).
    ctx_btm_spec = dict(ctx_btm, tenant_profile="speculative")
    assert _trigger_power_outlook_doubtful(ctx_btm_spec)


def test_btm_gas_blocked_in_severe_nonattainment():
    """BTM gas suppression must be blocked when site is in severe/extreme/serious
    nonattainment -- major-source air permit infeasible.
    See docs/screen_methodology/btm_gas_viable.md.
    """
    from scoring import btm_gas_viable

    base_ctx = {
        "gas_pipelines": [
            {"type": "Interstate", "operator": "Transco", "dist_km": 5.0},
        ],
        "tenant_profile": "hyperscaler",
    }
    ok_plain, _ = btm_gas_viable(base_ctx)
    assert ok_plain is True, "Interstate pipeline at 5 km should be viable in attainment areas"

    severe_ctx = dict(base_ctx, nonattainment_zones=[{"classification": "Severe"}])
    ok_severe, reason = btm_gas_viable(severe_ctx)
    assert ok_severe is False
    assert "severe-nonattainment" in reason.lower() or "permit" in reason.lower()


def test_regulatory_pause_p_scales_with_lift_date():
    """Lift-proximity tiers P: near-term pause is schedule risk; >24mo is
    near-existential. See docs/screen_methodology/moratoriums.md."""
    from datetime import date, timedelta
    from scoring import _p_regulatory_pause

    def ctx_for(months: float):
        d = (date.today() + timedelta(days=int(months * 30.44))).isoformat()
        return {"regulatory_moratoriums": [{"expected_lift_date": d}]}

    p3 = _p_regulatory_pause(ctx_for(3))
    p9 = _p_regulatory_pause(ctx_for(9))
    p18 = _p_regulatory_pause(ctx_for(18))
    p36 = _p_regulatory_pause(ctx_for(36))
    assert p3 < p9 < p18 < p36, f"Monotone lift-proximity expected: {p3}, {p9}, {p18}, {p36}"
    assert p3 == 0.30 and p36 == 0.85


def test_regulatory_pause_distinct_from_tariff_moratorium():
    """PSC/PUC docket pauses fire regulatory_interconnection_pause (P=0.55,
    tenant-scaled) not utility_moratorium (P=0.90). See Millsboro DE."""
    from scoring import (
        DEAL_KILLERS,
        _trigger_regulatory_pause,
        _trigger_tariff_moratorium,
    )

    moratorium = next(k for k in DEAL_KILLERS if k.name == "utility_moratorium")
    pause = next(k for k in DEAL_KILLERS if k.name == "regulatory_interconnection_pause")
    assert moratorium.probability > pause.probability, (
        "Tariff moratorium (indefinite) must carry higher P than docket pause (defined lift)."
    )

    ctx_reg_only = {
        "regulatory_moratoriums": [{
            "utility_name": "Delmarva Power", "docket": "DE PSC 25-0826",
            "expected_lift_date": "2026-12-31",
        }],
        "dc_tariffs": [],
    }
    assert _trigger_regulatory_pause(ctx_reg_only)
    assert not _trigger_tariff_moratorium(ctx_reg_only)

    ctx_tariff_only = {
        "regulatory_moratoriums": [],
        "dc_tariffs": [{"utility_name": "Foo Utility", "moratorium": True}],
    }
    assert _trigger_tariff_moratorium(ctx_tariff_only)
    assert not _trigger_regulatory_pause(ctx_tariff_only)

    # Tenant scaling: hyperscaler absorbs pause delay better than speculative.
    assert pause.adjusted_probability("hyperscaler") < pause.adjusted_probability("speculative")


def test_brownfield_flips_outlook_to_promising():
    """A nearby retired plant with adequate former-capacity flips
    grid_outlook to 'promising' (supply anchor), which then suppresses
    power_outlook_doubtful. See Millsboro DE / Indian River Power Plant."""
    from scoring import (
        _trigger_power_outlook_doubtful,
        grid_outlook,
        has_brownfield_interconnection,
    )

    ctx = {
        "target_mw": 500,
        "nearby_dcs": [],
        "transmission_lines": [],
        "substations": [],
        "planned_substations": [],
        "interconnection_queue": [],
        "brownfield_interconnection": [{
            "id": "indian_river_de",
            "name": "Indian River Power Plant",
            "former_mw": 785,
            "voltage_classes": ["230", "138"],
            "dist_km": 0.8,
        }],
        "tenant_profile": "speculative",
        "gas_pipelines": [],
    }
    assert has_brownfield_interconnection(ctx)[0]
    assert grid_outlook(ctx)["verdict"] == "promising"
    assert not _trigger_power_outlook_doubtful(ctx)

    # Tiny retired plant: doesn't qualify as brownfield, outlook goes back to
    # doubtful (no HV line, no other anchors), killer fires.
    ctx_tiny = dict(ctx)
    ctx_tiny["brownfield_interconnection"] = [{
        "id": "tiny_plant", "name": "Tiny Plant", "former_mw": 50,
        "voltage_classes": ["69"], "dist_km": 1.0,
    }]
    assert not has_brownfield_interconnection(ctx_tiny)[0]
    assert grid_outlook(ctx_tiny)["verdict"] == "doubtful"
    assert _trigger_power_outlook_doubtful(ctx_tiny)


def test_btm_gas_suppression_is_tenant_gated():
    """BTM gas viability only suppresses power_outlook_doubtful for anchored
    / hyperscaler tenants (speculative developers typically cannot finance
    on-site generation)."""
    from scoring import _trigger_power_outlook_doubtful, btm_gas_viable

    ctx_base = {
        "target_mw": 500,
        "nearby_dcs": [],
        "transmission_lines": [],
        "substations": [],
        "planned_substations": [],
        "interconnection_queue": [],
        "brownfield_interconnection": [],
        "gas_pipelines": [{
            "operator": "Williams", "type": "Interstate", "dist_km": 8.0,
        }],
    }
    assert btm_gas_viable(ctx_base)[0]

    # Speculative: gas pipe alone doesn't save it -- killer still fires.
    assert _trigger_power_outlook_doubtful({**ctx_base, "tenant_profile": "speculative"})

    # Hyperscaler: viability + credit = suppresses.
    assert not _trigger_power_outlook_doubtful({**ctx_base, "tenant_profile": "hyperscaler"})


def test_scoring_catalog_stable():
    """The deal-killer catalog size is pinned so additions/removals are intentional.

    Update this number (and regression_sites.json) when deliberately adding a
    new killer. Every addition needs a calibration_hook docstring.
    """
    from scoring import DEAL_KILLERS

    assert len(DEAL_KILLERS) == 8, (
        f"Deal-killer catalog size changed to {len(DEAL_KILLERS)}. "
        "This is a deliberate decision -- update this assertion and re-pin "
        "expected_feasibility values in regression_sites.json. "
        "2026-04-24: retired marginal_nonattainment AND justice40_disadvantaged "
        "(narrative-only). Grid methodology pass: retired grid_minor_deficit "
        "and replaced grid_severely_insufficient with qualitative "
        "power_outlook_doubtful. Catalog = 8."
    )
    for killer in DEAL_KILLERS:
        assert 0.0 <= killer.probability <= 1.0, (
            f"{killer.name}: probability {killer.probability} out of [0,1]"
        )
        assert killer.calibration_hook, (
            f"{killer.name}: missing calibration_hook (needed for backtesting)"
        )


def test_pipeline_metadata_shape():
    """Smoke test: run a tiny pipeline and verify _meta has the right shape.

    Uses synthetic elements only, so this runs without the spatial cache.
    """
    from pipeline import Element, run_pipeline as rp

    registry = [
        Element(name="ok", fn=lambda ctx: [1, 2, 3], output_key="ok_val", source="test"),
        Element(name="empty", fn=lambda ctx: [], output_key="empty_val", source="test"),
        Element(name="none", fn=lambda ctx: None, output_key="none_val", source="test"),
        Element(name="boom", fn=lambda ctx: 1 / 0, output_key="boom_val", source="test"),
        Element(name="off", fn=lambda ctx: 1, output_key="off_val", source="test", enabled=False),
    ]
    ctx: dict = {}
    rp(ctx, registry)

    meta = ctx["_meta"]
    assert meta["ok"]["ok"] is True
    assert meta["empty"]["ok"] is False
    assert meta["empty"]["error"] is None
    assert meta["none"]["ok"] is False
    assert meta["boom"]["ok"] is False
    assert "ZeroDivisionError" in meta["boom"]["error"]
    assert meta["off"]["skipped"] is True

    summary = coverage_summary(ctx)
    assert summary == {"covered": 1, "missing": 2, "errored": 1, "total": 5}
    assert sorted(missing_elements(ctx)) == ["empty", "none"]
    assert errored_elements(ctx)[0][0] == "boom"
