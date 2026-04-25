"""Element registry + pipeline runner.

Wraps the existing analyzer functions in a uniform Element interface so that
each step can be skipped, substituted, timed, and audited independently.

Behavior is identical to the previous inline orchestration in
``dc_site_report.main()`` -- the same ``ctx`` keys are populated, the report
template is unchanged. The only addition is ``ctx["_meta"]`` which carries
per-element provenance metadata for the scorecard and the regression harness.

See ``docs/EFFICACY_SCORECARD.md`` for the design rationale.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


# ---------------------------------------------------------------------------
# Element + runner
# ---------------------------------------------------------------------------


@dataclass
class Element:
    """A single unit of work in the pipeline.

    ``fn`` receives the current ``ctx`` dict (read-only by convention) and
    returns the raw value that will be written to ``ctx[output_key]``.
    """

    name: str
    fn: Callable[[dict], Any]
    output_key: str
    source: str
    deps: list[str] = field(default_factory=list)
    enabled: bool = True


def _coverage_ok(value: Any) -> bool:
    """A value 'covers' the site if it isn't None / empty.

    Lists, dicts, strings, tuples → empty is failure.
    Numbers / bools / nonempty containers → success.
    """
    if value is None:
        return False
    if isinstance(value, (list, dict, str, tuple, set)) and len(value) == 0:
        return False
    return True


def run_pipeline(
    ctx: dict,
    registry: Iterable[Element],
    *,
    on_step: Callable[[Element, dict], None] | None = None,
) -> dict:
    """Run every enabled element in order, writing outputs and metadata into ctx.

    ``ctx["_meta"][name]`` is populated for every element with::

        {
          "ok": bool,            # coverage_ok of the returned value
          "elapsed_ms": int,
          "source": str,         # provenance label from the Element
          "error": str | None,   # exception text if fn raised
          "skipped": bool,       # True if element.enabled was False
        }

    ``on_step`` (optional) is invoked after each element for progress reporting.
    """
    meta: dict[str, dict] = ctx.setdefault("_meta", {})

    for el in registry:
        if not el.enabled:
            meta[el.name] = {
                "ok": False,
                "elapsed_ms": 0,
                "source": el.source,
                "error": None,
                "skipped": True,
            }
            if on_step:
                on_step(el, meta[el.name])
            continue

        t0 = time.perf_counter()
        error: str | None = None
        try:
            value = el.fn(ctx)
        except Exception as e:  # noqa: BLE001 -- we intentionally surface every failure
            value = None
            error = f"{type(e).__name__}: {e}"

        ctx[el.output_key] = value
        meta[el.name] = {
            "ok": _coverage_ok(value),
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            "source": el.source,
            "error": error,
            "skipped": False,
        }
        if on_step:
            on_step(el, meta[el.name])

    return ctx


# ---------------------------------------------------------------------------
# Default registry: the current production pipeline
# ---------------------------------------------------------------------------


def default_registry(radius_km: float = 30.0) -> list[Element]:
    """Build the production element registry.

    Imports are deferred so the registry can be constructed in test contexts
    without forcing every dependency to load.
    """
    import spatial_queries as sq
    from data_queries import (
        get_capacity_prices,
        get_gas_prices,
        get_grid_energy_mix,
        get_interconnection_queue,
        get_nearby_dc_projects,
        get_nearby_generators,
        get_planned_transmission,
        get_utility_rate,
        get_wholesale_power_costs,
    )
    from grid_assessment import assess_grid
    from reference_data import (
        get_cooling_degree_days,
        get_dc_tariffs,
        get_land_value,
        get_regulatory_moratoriums,
        get_retired_generation_sites,
        get_state_incentives,
    )
    from research_links import generate_research_links

    def _find_brownfield_interconnection(ctx, radius_km: float = 5.0):
        """Return retired generation sites within ``radius_km`` of the subject
        parcel, sorted by distance.

        This is the second 'off-data-feed' signal (alongside cluster effect) that
        flips grid-adequacy analysis. A retired plant's switchyard + HV lines
        are invisible to HIFLD transmission_lines / substations but are the
        single most valuable DC siting asset when present. See scorecard note
        D-new-brownfield and the Millsboro DE regression site for the worked
        example (Indian River Power Plant 0.8 km from 499 Mitchell St).
        """
        state = ctx.get("state")
        if not state:
            return []
        lat = ctx.get("lat")
        lon = ctx.get("lon")
        if lat is None or lon is None:
            return []
        import math
        hits = []
        for s in get_retired_generation_sites(state=state):
            slat, slon = s.get("lat"), s.get("lon")
            if slat is None or slon is None:
                continue
            dlat = math.radians(slat - lat)
            dlon = math.radians(slon - lon)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat)) * math.cos(math.radians(slat)) *
                 math.sin(dlon / 2) ** 2)
            dist_km = 6371.0 * 2 * math.asin(math.sqrt(a))
            if dist_km <= radius_km:
                entry = dict(s)
                entry["dist_km"] = round(dist_km, 2)
                hits.append(entry)
        hits.sort(key=lambda x: x["dist_km"])
        return hits

    def _find_regulatory_moratoriums(ctx):
        """Return active state+utility-level regulatory interconnection pauses.

        Separate from DC_TARIFFS[*].moratorium because PSC/PUC docket-level
        pauses are not captured in utility tariffs (they precede them). See
        Millsboro DE / Delmarva Power PSC 25-0826 for the anchor case.
        """
        state = ctx.get("state")
        if not state:
            return []
        util = _utility_name(ctx)
        hits = get_regulatory_moratoriums(state, util) if util else []
        # Fall back to state-level matches when we don't know the utility yet
        # (rare but happens when service_territories is empty and state fallback
        # hasn't populated it).
        if not hits:
            hits = get_regulatory_moratoriums(state)
        return hits

    def _ll(ctx):
        return ctx["lat"], ctx["lon"]

    def _utility_name(ctx):
        """Return the best single utility name for rate/alias lookups.

        Prefers investor-owned utilities over cooperatives/municipals, since
        large-load DC tariffs are almost always IOU filings and sites in
        overlapping service territories (common for co-op + IOU) should not
        silently skip the IOU.
        """
        sts = ctx.get("service_territories") or []
        if not sts:
            return None
        iou = next((s for s in sts if (s.get("type") or "").upper() == "INVESTOR OWNED"), None)
        return (iou or sts[0]).get("name")

    def _match_dc_tariffs(ctx):
        """Match DC tariffs against ALL service territories, not just the first.

        Fixes A17 (regression harness): overlapping IOU+coop territories were
        silently dropping IOU tariffs like AEP Ohio Schedule DCT.
        """
        state = ctx.get("state")
        if not state:
            return []
        sts = ctx.get("service_territories") or []
        seen_names: set[str] = set()
        matched: list[dict] = []
        for st in sts:
            name = st.get("name")
            if not name:
                continue
            for t in get_dc_tariffs(state, name):
                key = t.get("utility_name", "") + ":" + t.get("tariff_name", "")
                if key in seen_names:
                    continue
                seen_names.add(key)
                matched.append(t)
        # If the site had zero service territories (HIFLD coverage gap, see D5),
        # still surface any state-level tariffs so the report is not blank.
        if not matched and not sts:
            matched = list(get_dc_tariffs(state))
        return matched

    return [
        # --- Layer 3a: spatial / infrastructure -------------------------------
        Element(
            name="transmission_lines",
            fn=lambda ctx: sq.find_nearest_transmission_lines(*_ll(ctx), radius_km),
            output_key="transmission_lines",
            source="HIFLD transmission lines (cached parquet)",
            deps=["lat", "lon"],
        ),
        Element(
            name="substations",
            fn=lambda ctx: sq.find_nearest_substations(*_ll(ctx), radius_km, limit=10),
            output_key="substations",
            source="HIFLD substations (NE US only) + planned_transmission_substations",
            deps=["lat", "lon"],
        ),
        Element(
            name="planned_substations",
            fn=lambda ctx: sq.find_planned_substations(*_ll(ctx), radius_km=150, limit=10),
            output_key="planned_substations",
            source="energy_analytics.duckdb:planned_transmission_substations",
            deps=["lat", "lon"],
        ),
        Element(
            # Limit bumped from 3 -> 20 so BTM-gas viability logic in
            # scoring.py can count Interstate vs Intrastate pipelines within
            # range. Downstream consumers still read the nearest entries
            # (results are dist-sorted).
            name="gas_pipelines",
            fn=lambda ctx: sq.find_nearest_gas_pipelines(*_ll(ctx), 20, limit=20),
            output_key="gas_pipelines",
            source="HIFLD gas pipelines",
            deps=["lat", "lon"],
        ),
        Element(
            name="highways",
            fn=lambda ctx: sq.find_nearest_highways(*_ll(ctx), radius_km),
            output_key="highways",
            source="HIFLD primary roads",
            deps=["lat", "lon"],
        ),
        Element(
            name="railroads",
            fn=lambda ctx: sq.find_nearest_railroads(*_ll(ctx), radius_km),
            output_key="railroads",
            source="HIFLD railroads",
            deps=["lat", "lon"],
        ),
        Element(
            name="water_facilities",
            fn=lambda ctx: sq.find_nearest_water(*_ll(ctx), radius_km),
            output_key="water_facilities",
            source="HIFLD water/wastewater treatment",
            deps=["lat", "lon"],
        ),
        Element(
            name="fiber_routes",
            fn=lambda ctx: sq.find_nearest_fiber(*_ll(ctx), radius_km),
            output_key="fiber_routes",
            source="HIFLD long-haul fiber",
            deps=["lat", "lon"],
        ),
        Element(
            name="cell_towers",
            fn=lambda ctx: sq.find_nearest_cell_towers(*_ll(ctx), radius_km),
            output_key="cell_towers",
            source="FCC ASR cellular towers",
            deps=["lat", "lon"],
        ),
        Element(
            name="service_territories",
            fn=lambda ctx: sq.find_service_territory(*_ll(ctx), state=ctx.get("state")),
            output_key="service_territories",
            source="HIFLD electric retail service territories (+ state fallback for HIFLD gaps)",
            deps=["lat", "lon", "state"],
        ),
        # --- Layer 3b: environmental ----------------------------------------
        Element(
            name="nonattainment_zones",
            fn=lambda ctx: sq.check_nonattainment_zone(*_ll(ctx)),
            output_key="nonattainment_zones",
            source="EPA Green Book NAAQS nonattainment areas",
            deps=["lat", "lon"],
        ),
        Element(
            name="flood_zones",
            fn=lambda ctx: sq.check_flood_zone(*_ll(ctx)),
            output_key="flood_zones",
            source="FEMA NFHL (live API; gappy)",
            deps=["lat", "lon"],
        ),
        Element(
            name="justice40",
            fn=lambda ctx: sq.check_justice40(*_ll(ctx)),
            output_key="justice40",
            source="CEQ Justice40 disadvantaged communities",
            deps=["lat", "lon"],
        ),
        Element(
            name="seismic",
            fn=lambda ctx: sq.check_seismic_hazard(*_ll(ctx)),
            output_key="seismic",
            source="USGS ASCE 7-22 design API",
            deps=["lat", "lon"],
        ),
        Element(
            name="land_cover",
            fn=lambda ctx: sq.check_land_cover(*_ll(ctx)),
            output_key="land_cover",
            source="NLCD land cover raster",
            deps=["lat", "lon"],
        ),
        Element(
            name="osm_landuse",
            fn=lambda ctx: sq.check_osm_landuse(*_ll(ctx)),
            output_key="osm_landuse",
            source="OpenStreetMap landuse tags",
            deps=["lat", "lon"],
        ),
        # --- Layer 3c: market / data queries --------------------------------
        Element(
            name="utility_rate",
            fn=lambda ctx: get_utility_rate(_utility_name(ctx), ctx.get("state")),
            output_key="utility_rate",
            source="EIA Form 861 retail rates (energy_analytics.duckdb)",
            deps=["service_territories", "state"],
        ),
        Element(
            name="interconnection_queue",
            fn=lambda ctx: get_interconnection_queue(ctx.get("state")),
            output_key="interconnection_queue",
            source="ISO/RTO + utility IX queues (energy_analytics.duckdb)",
            deps=["state"],
        ),
        Element(
            name="nearby_dcs",
            fn=lambda ctx: get_nearby_dc_projects(ctx["lat"], ctx["lon"], 50),
            output_key="nearby_dcs",
            source="demand_ledger.duckdb + data_centers.csv",
            deps=["lat", "lon"],
        ),
        Element(
            name="grid_energy_mix",
            fn=lambda ctx: get_grid_energy_mix(ctx["state"]) if ctx.get("state") else None,
            output_key="grid_energy_mix",
            source="EIA generation_fuel_mix",
            deps=["state"],
        ),
        Element(
            name="nearby_generators",
            fn=lambda ctx: get_nearby_generators(
                ctx["state"], ctx.get("county", "").replace(" County", "").strip()
            ) if ctx.get("state") else [],
            output_key="nearby_generators",
            source="EIA generators (energy_analytics.duckdb)",
            deps=["state", "county"],
        ),
        Element(
            name="capacity_prices",
            fn=lambda ctx: get_capacity_prices(ctx["state"]) if ctx.get("state") else [],
            output_key="capacity_prices",
            source="RTO capacity auction prices (energy_analytics.duckdb)",
            deps=["state"],
        ),
        Element(
            name="planned_transmission",
            fn=lambda ctx: get_planned_transmission(ctx["state"]) if ctx.get("state") else [],
            output_key="planned_transmission",
            source="Planned transmission projects (energy_analytics.duckdb)",
            deps=["state"],
        ),
        Element(
            name="gas_prices",
            fn=lambda ctx: get_gas_prices(),
            output_key="gas_prices",
            source="Natural gas hub prices (energy_analytics.duckdb)",
            deps=[],
        ),
        Element(
            name="wholesale_power",
            fn=lambda ctx: get_wholesale_power_costs(ctx["state"]) if ctx.get("state") else [],
            output_key="wholesale_power",
            source="ISO wholesale power costs (energy_analytics.duckdb)",
            deps=["state"],
        ),
        # --- Layer 3d: reference data ---------------------------------------
        Element(
            name="dc_tariffs",
            fn=_match_dc_tariffs,
            output_key="dc_tariffs",
            source="reference_data.DC_TARIFFS (hand-curated, March 2026)",
            deps=["state", "service_territories"],
        ),
        Element(
            name="tax_incentives",
            fn=lambda ctx: get_state_incentives(ctx["state"]) if ctx.get("state") else None,
            output_key="tax_incentives",
            source="reference_data.STATE_INCENTIVES (hand-curated, March 2026)",
            deps=["state"],
        ),
        Element(
            name="cooling_degree_days",
            fn=lambda ctx: get_cooling_degree_days(ctx["state"]) if ctx.get("state") else None,
            output_key="cooling_degree_days",
            source="NOAA 30-yr CDD normals",
            deps=["state"],
        ),
        Element(
            name="land_value_per_acre",
            fn=lambda ctx: get_land_value(ctx["state"]) if ctx.get("state") else None,
            output_key="land_value_per_acre",
            source="USDA NASS state cropland values",
            deps=["state"],
        ),
        Element(
            name="regulatory_moratoriums",
            fn=_find_regulatory_moratoriums,
            output_key="regulatory_moratoriums",
            source="reference_data.REGULATORY_MORATORIUMS (hand-curated PSC/PUC docket index)",
            deps=["state", "service_territories"],
        ),
        Element(
            name="brownfield_interconnection",
            fn=lambda ctx: _find_brownfield_interconnection(ctx, radius_km=5.0),
            output_key="brownfield_interconnection",
            source="reference_data.RETIRED_GENERATION_SITES (hand-curated retired plants + switchyards)",
            deps=["lat", "lon", "state"],
        ),
        Element(
            name="research_links",
            fn=lambda ctx: generate_research_links(
                ctx["state"], ctx.get("county", ""), _utility_name(ctx), ctx["address"]
            ) if ctx.get("state") else [],
            output_key="research_links",
            source="Halcyon + Google site-search URL templates",
            deps=["state", "county", "service_territories", "address"],
        ),
        # --- Layer 3e: derived assessments ----------------------------------
        Element(
            name="grid_assessment",
            fn=lambda ctx: assess_grid(
                ctx.get("transmission_lines", []),
                ctx.get("substations", []),
                ctx.get("target_mw"),
            ),
            output_key="grid_assessment",
            source="grid_assessment.assess_grid (voltage-tier heuristic)",
            deps=["transmission_lines", "substations", "target_mw"],
        ),
    ]


# ---------------------------------------------------------------------------
# Convenience: meta summary helpers (used by report + tests)
# ---------------------------------------------------------------------------


def coverage_summary(ctx: dict) -> dict:
    """Return {covered: int, missing: int, errored: int, total: int} for the run."""
    meta = ctx.get("_meta", {})
    covered = sum(1 for m in meta.values() if m.get("ok"))
    missing = sum(1 for m in meta.values() if not m.get("ok") and not m.get("error") and not m.get("skipped"))
    errored = sum(1 for m in meta.values() if m.get("error"))
    return {
        "covered": covered,
        "missing": missing,
        "errored": errored,
        "total": len(meta),
    }


def missing_elements(ctx: dict) -> list[str]:
    """Element names whose value was None/empty (excluding errors and skips)."""
    meta = ctx.get("_meta", {})
    return [
        name for name, m in meta.items()
        if not m.get("ok") and not m.get("error") and not m.get("skipped")
    ]


def errored_elements(ctx: dict) -> list[tuple[str, str]]:
    """(name, error) for every element whose fn raised."""
    meta = ctx.get("_meta", {})
    return [(name, m["error"]) for name, m in meta.items() if m.get("error")]
