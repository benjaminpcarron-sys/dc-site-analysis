"""Risk-adjusted site feasibility scoring.

Replaces (alongside the legacy weighted average) the headline site score with
a deal-killer-probability-weighted model:

    Feasibility   = Opportunity * (1 - Combined_Risk)
    Combined_Risk = 1 - prod(1 - P_i * tenant_scale_i) over triggered killers
    Opportunity   = mean(1-5 scorecard factors) / 5.0 + cluster_boost   (0..1)

Two inputs condition the model beyond raw site data:

  * ``ctx["tenant_profile"]`` in {"speculative", "anchored", "hyperscaler"}.
    Defaults to "speculative" (conservative). Each killer has a
    ``tenant_scaling`` dict that multiplies its base probability -- e.g. an
    onerous tariff deposit is near-lethal for a merchant developer but
    trivially clearable by a hyperscaler with investment-grade credit.

  * ``ctx["nearby_dcs"]`` (from the pipeline). When an active cluster exists
    (>= CLUSTER_MIN_COUNT existing DCs within CLUSTER_RADIUS_KM), the model
    boosts Opportunity by CLUSTER_OPPORTUNITY_BOOST (ecosystem benefit). The
    cluster also enters ``grid_outlook`` as a positive "track record" signal
    -- utilities that have historically served large DC load get credit for
    demonstrated capacity. See docs/screen_methodology/grid_severely_insufficient.md
    for the full power-outlook classifier.

Calibration history is tracked in ``docs/EFFICACY_SCORECARD.md``. P values are
tuned so the anchor regression sites (New Albany OH, Ashburn VA, Council
Bluffs IA, Altoona IA, The Dalles OR) score feasibility >= 0.35 while
genuinely constrained sites (Millsboro DE, Hurt Ranch NM) stay <= 0.25.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Tenant-profile and cluster constants
# ---------------------------------------------------------------------------


TENANT_PROFILES = ("speculative", "anchored", "hyperscaler")
DEFAULT_TENANT_PROFILE = "speculative"

# Plain-English descriptions used by the report so readers understand what each
# tier means in finance / counterparty terms, not just as a label. The
# scaling factors live on each DealKiller; these are the "what kind of buyer
# is this" prose surfaced in the executive summary.
TENANT_DESCRIPTIONS = {
    "speculative": (
        "Merchant developer building on spec, no named anchor tenant or "
        "investment-grade lease commitment. Constrained by tariff collateral, "
        "cannot wait through indefinite interconnection pauses, must close at "
        "published industrial rates, cannot finance behind-the-meter generation."
    ),
    "anchored": (
        "Pre-leased to a named DC operator with investment-grade credit "
        "(CoreSite, Equinix, Digital Realty, QTS, etc.). Can absorb deposit "
        "requirements, has runway for moderate schedule slips, negotiates rates "
        "but at the second tier (not bespoke utility contracts)."
    ),
    "hyperscaler": (
        "Tier-1 hyperscaler (FAANG-tier IG credit) developing for own use. "
        "Negotiates around published tariffs via bilateral utility contracts, "
        "absorbs deposits via parent guarantees, can finance behind-the-meter "
        "generation, plans on horizons that absorb 12-24 month interconnection "
        "delays."
    ),
}

# Cluster signal thresholds. These are deliberately conservative -- false
# positives would let sites with 3-4 small DCs escape real grid constraints.
CLUSTER_RADIUS_KM = 50
CLUSTER_MIN_COUNT = 5
CLUSTER_GRID_RANGE_KM = 30  # HV line within this range + cluster => grid deficit suppressed
CLUSTER_MW_RADIUS_KM = 30.0       # tighter ring for the MW-weighted fallback path
CLUSTER_MW_THRESHOLD = 400        # sum(mw within 30 km) >= 400 MW -> cluster even without 5 sites
CLUSTER_HUB_MW_THRESHOLD = 1000   # hub tier: >=1 GW within 30 km earns the larger boost
CLUSTER_OPPORTUNITY_BOOST = 0.12  # added to opportunity when cluster present, capped at 1.0
CLUSTER_HUB_OPPORTUNITY_BOOST = 0.20  # "hub" tier: >=1 GW built within 30 km


# ---------------------------------------------------------------------------
# Deal-killer definitions
# ---------------------------------------------------------------------------


@dataclass
class DealKiller:
    """A single factor that can independently kill a project.

    ``tenant_scaling`` maps each tenant profile to a multiplier applied to the
    base probability when the killer fires. Defaults to 1.0 for every profile.

    ``probability_fn`` optionally overrides the static ``probability`` with a
    context-dependent value (e.g. grid severity tiered by deficit ratio,
    regulatory pause discounted by expected lift date). When present it is
    consulted instead of ``probability`` to produce the base P before tenant
    scaling. See ``docs/screen_methodology/grid_severely_insufficient.md``.
    """

    name: str
    category: str  # tariff | grid | environmental | regulatory | market
    probability: float  # 0..1 marginal kill probability (seed, used when probability_fn is None)
    rationale: str
    trigger: Callable[[dict], bool | str]
    calibration_hook: str | None = None
    tenant_scaling: dict[str, float] = field(default_factory=lambda: {
        "speculative": 1.0, "anchored": 1.0, "hyperscaler": 1.0,
    })
    probability_fn: Callable[[dict], float] | None = None

    def fires(self, ctx: dict) -> tuple[bool, str]:
        try:
            result = self.trigger(ctx)
        except Exception as e:  # noqa: BLE001
            return (False, f"trigger error: {type(e).__name__}: {e}")
        if isinstance(result, str):
            return (True, result)
        return (bool(result), "triggered" if result else "not triggered")

    def base_probability(self, ctx: dict | None = None) -> float:
        """Return the seed P for this killer, calling ``probability_fn`` when set."""
        if self.probability_fn is not None and ctx is not None:
            try:
                return max(0.0, min(1.0, float(self.probability_fn(ctx))))
            except Exception:  # noqa: BLE001
                # Defensive: never let a dynamic-P helper crash the whole scorer.
                return self.probability
        return self.probability

    def effective_probability(self, ctx: dict, tenant_profile: str) -> float:
        """Base P (possibly dynamic) * tenant scaling, clamped to [0, 1]."""
        scale = self.tenant_scaling.get(tenant_profile, 1.0)
        return max(0.0, min(1.0, self.base_probability(ctx) * scale))

    def adjusted_probability(self, tenant_profile: str) -> float:
        """Back-compat alias -- uses static P only (no ctx available)."""
        return self.effective_probability({}, tenant_profile)


# --- Cluster-signal helper --------------------------------------------------


def cluster_signal(ctx: dict) -> dict | None:
    """Return the cluster-signal record or None if no active cluster.

    Fires via EITHER path:
      (a) count-based: >= CLUSTER_MIN_COUNT DCs within CLUSTER_RADIUS_KM, OR
      (b) MW-weighted: sum(mw within CLUSTER_MW_RADIUS_KM) >= CLUSTER_MW_THRESHOLD.

    Path (b) handles hyperscaler anchors like Quincy WA where only 2 known
    sites are detected but those sites are GW-scale campuses. Path (a) handles
    colo-heavy markets where individual site MW is often null.

    Tier:
      - "hub" when sum(mw within 30 km) >= CLUSTER_HUB_MW_THRESHOLD.
      - "active" otherwise.
    Hub tier earns the larger opportunity boost.

    See docs/screen_methodology/cluster_signal.md.
    """
    dcs = ctx.get("nearby_dcs") or []
    within_50 = [d for d in dcs if (d.get("dist_km") or 999) <= CLUSTER_RADIUS_KM]
    within_30 = [d for d in dcs if (d.get("dist_km") or 999) <= CLUSTER_MW_RADIUS_KM]
    mw_30 = sum((d.get("mw") or 0) for d in within_30)
    count_ok = len(within_50) >= CLUSTER_MIN_COUNT
    mw_ok = mw_30 >= CLUSTER_MW_THRESHOLD
    if not (count_ok or mw_ok):
        return None
    tier = "hub" if mw_30 >= CLUSTER_HUB_MW_THRESHOLD else "active"
    boost = CLUSTER_HUB_OPPORTUNITY_BOOST if tier == "hub" else CLUSTER_OPPORTUNITY_BOOST
    if mw_30 > 0:
        ev = (
            f"{len(within_50)} DC projects within {CLUSTER_RADIUS_KM} km "
            f"({mw_30:.0f} MW built within {CLUSTER_MW_RADIUS_KM:.0f} km, tier={tier})"
        )
    else:
        ev = (
            f"{len(within_50)} DC projects within {CLUSTER_RADIUS_KM} km "
            f"(MW data sparse; tier={tier})"
        )
    return {"tier": tier, "count": len(within_50), "mw_total": mw_30,
            "opportunity_boost": boost, "evidence": ev}


def has_active_cluster(ctx: dict) -> tuple[bool, str]:
    """Legacy wrapper: (True, evidence) when cluster_signal returns any tier."""
    cs = cluster_signal(ctx)
    if cs is None:
        return False, ""
    return True, cs["evidence"]


def _hv_line_within(ctx: dict, km: float) -> bool:
    """True if any transmission line of 100+ kV tier is within ``km``."""
    lines = ctx.get("transmission_lines") or []
    hv_classes = {"735 AND ABOVE", "DC", "500", "345", "220-287", "100-161"}
    for line in lines:
        if (line.get("volt_class") or "") in hv_classes and (line.get("dist_km") or 999) <= km:
            return True
    return False


# --- Alternative power paths ------------------------------------------------
#
# Brownfield + BTM gas are two concrete "anchor" options that feed both the
# power-outlook classifier (as supply-side positives) and the BTM gas override
# that can suppress a doubtful outlook for a credit-worthy tenant.


BROWNFIELD_INTERCONNECTION_RADIUS_KM = 10.0  # outer search radius
BROWNFIELD_DIRECT_RADIUS_KM = 5.0            # "direct co-location" tier -- full effect
BROWNFIELD_MIN_CAPACITY_RATIO = 0.6          # retired plant must have been >=60% of target MW
BROWNFIELD_OPP_BOOST_BY_RATIO: list[tuple[float, float]] = [
    # (min_capacity_ratio, direct_tier_boost). Each entry's boost is halved
    # when the plant is in the 5-10 km "adjacent ROW" ring.
    (0.90, 0.12),
    (0.60, 0.07),
]

BTM_GAS_INTERSTATE_MAX_KM = 15.0
BTM_GAS_INTRASTATE_MAX_KM = 10.0
BTM_GAS_MIN_INTRASTATE_COUNT = 2  # Texas-friendly: multiple intrastate lines compensate
BTM_GAS_ANCHORING_TENANTS = {"anchored", "hyperscaler"}  # speculative devs can't usually finance BTM gas


def brownfield_fit(ctx: dict) -> dict | None:
    """Return the best-fit brownfield site, or None if none qualify.

    A brownfield qualifies when: (a) dist_km <= BROWNFIELD_INTERCONNECTION_RADIUS_KM
    and (b) former_mw >= BROWNFIELD_MIN_CAPACITY_RATIO * target_mw (or target_mw
    is unknown -- flag the optionality). Returns:
      { site, ratio, distance_tier ("direct" | "adjacent"), opportunity_boost,
        evidence }

    "direct" tier (<=5 km) gets the full boost from BROWNFIELD_OPP_BOOST_BY_RATIO;
    "adjacent" tier (5-10 km) gets half. See
    docs/screen_methodology/brownfield_interconnection.md.
    """
    bf = ctx.get("brownfield_interconnection") or []
    if not bf:
        return None
    target = ctx.get("target_mw") or 0
    best: dict | None = None
    for site in bf:
        mw = site.get("former_mw") or 0
        dist = site.get("dist_km", 0)
        if dist is None or dist > BROWNFIELD_INTERCONNECTION_RADIUS_KM:
            continue
        if target and mw < target * BROWNFIELD_MIN_CAPACITY_RATIO:
            continue
        ratio = (mw / target) if target else None
        tier = "direct" if dist <= BROWNFIELD_DIRECT_RADIUS_KM else "adjacent"
        boost = 0.0
        if ratio is not None:
            for min_ratio, b in BROWNFIELD_OPP_BOOST_BY_RATIO:
                if ratio >= min_ratio:
                    boost = b
                    break
        else:
            boost = BROWNFIELD_OPP_BOOST_BY_RATIO[-1][1]  # unknown target -> conservative
        if tier == "adjacent":
            boost = boost * 0.5
        vclasses = "/".join(site.get("voltage_classes") or [])
        fit_str = f"fit={ratio:.2f}" if ratio is not None else "fit=?"
        evidence = (
            f"{site.get('name', 'retired plant')} ({mw} MW former, {vclasses} kV) "
            f"{dist:.1f} km away [{tier}, {fit_str}] -- switchyard + HV ties repurposable"
        )
        candidate = {
            "site": site,
            "ratio": ratio,
            "distance_tier": tier,
            "opportunity_boost": boost,
            "evidence": evidence,
        }
        if best is None or boost > best["opportunity_boost"]:
            best = candidate
    return best


def has_brownfield_interconnection(ctx: dict) -> tuple[bool, str]:
    """Legacy helper: True iff brownfield_fit finds a qualifying site."""
    fit = brownfield_fit(ctx)
    if fit is None:
        return False, ""
    return True, fit["evidence"]


def _severe_nonattainment_present(ctx: dict) -> bool:
    """True iff site sits in a severe / extreme / serious nonattainment zone.
    Used to block BTM gas suppression (major-source air permit is infeasible
    without offsets) per docs/screen_methodology/btm_gas_viable.md.
    """
    severe_classes = {"SEVERE", "EXTREME", "SERIOUS"}
    for zone in ctx.get("nonattainment_zones") or []:
        cls = (zone.get("classification") or "").upper()
        if any(s in cls for s in severe_classes):
            return True
    return False


def btm_gas_viable(ctx: dict) -> tuple[bool, str]:
    """Return (viable, evidence) for an on-site / behind-the-meter gas path.

    Interstate pipeline within 15 km OR >=2 intrastate pipelines within 10 km
    (the Intrastate path is required for Texas, where HIFLD classifies most of
    the in-state mesh as Intrastate since it doesn't cross state lines).
    Does NOT imply BTM gas is deployed -- only that a credible gas-delivery
    pathway exists.

    Returns (False, reason) when site is in a severe-nonattainment county:
    major-source gas generation can't be permitted without emissions offsets
    that are rarely available at scale.
    """
    if _severe_nonattainment_present(ctx):
        return False, "BTM gas suppression blocked: site in severe-nonattainment county (air-permit barrier)"

    pipes = ctx.get("gas_pipelines") or []
    inter = [p for p in pipes if (p.get("type") or "").lower() == "interstate"]
    intra = [p for p in pipes if (p.get("type") or "").lower() == "intrastate"]

    if inter and (inter[0].get("dist_km") or 999) <= BTM_GAS_INTERSTATE_MAX_KM:
        op = inter[0].get("operator") or "unknown operator"
        d = inter[0]["dist_km"]
        return True, f"Interstate pipeline ({op}) within {d:.1f} km"

    within_range_intra = [p for p in intra if (p.get("dist_km") or 999) <= BTM_GAS_INTRASTATE_MAX_KM]
    if len(within_range_intra) >= BTM_GAS_MIN_INTRASTATE_COUNT:
        op = within_range_intra[0].get("operator") or "unknown operator"
        d = within_range_intra[0]["dist_km"]
        return True, (
            f"{len(within_range_intra)} intrastate pipelines within {BTM_GAS_INTRASTATE_MAX_KM} km "
            f"(nearest: {op} @ {d:.1f} km)"
        )
    return False, ""


def power_path(ctx: dict) -> dict:
    """Summarize the site's power picture for the report.

    Headline is the qualitative ``grid_outlook`` verdict (promising / neutral
    / doubtful). ``paths`` then lists concrete supply anchors observed
    (brownfield, BTM gas) plus any cluster track record.

    We intentionally no longer emit a "grid" or "grid (partial)" path based
    on ``grid_assessment.max_mw`` -- that value is a voltage-class heuristic,
    not a capacity measurement, and gating power paths on it invited
    precision-without-accuracy readings. Consumers (report, feasibility)
    read ``outlook`` + ``paths``; raw ``max_mw`` still appears in the grid
    infrastructure section as a rough proxy.
    """
    outlook = grid_outlook(ctx)
    paths: list[dict] = []

    cluster_ok, cluster_ev = has_active_cluster(ctx)
    if cluster_ok and _hv_line_within(ctx, CLUSTER_GRID_RANGE_KM):
        paths.append({
            "label": "cluster-grid",
            "evidence": f"{cluster_ev}; HV line within {CLUSTER_GRID_RANGE_KM} km -- utility has demonstrated build capacity to serve cluster.",
        })

    bf_ok, bf_ev = has_brownfield_interconnection(ctx)
    if bf_ok:
        paths.append({"label": "brownfield", "evidence": bf_ev})

    gas_ok, gas_ev = btm_gas_viable(ctx)
    if gas_ok:
        paths.append({"label": "btm_gas", "evidence": gas_ev})

    primary = paths[0]["label"] if paths else outlook["verdict"]
    return {
        "primary": primary,
        "paths": paths,
        "outlook": outlook,
    }


# --- Trigger helpers --------------------------------------------------------


def _first(lst):
    if isinstance(lst, list) and lst:
        return lst[0]
    return None


def _trigger_tariff_moratorium(ctx):
    """Fires only on tariff-level DC moratoriums (indefinite, multi-year).
    See _trigger_regulatory_pause for docket-level pauses with defined lifts."""
    for t in ctx.get("dc_tariffs") or []:
        if t.get("moratorium"):
            util = t.get("utility_name", "utility")
            return f"{util} has an active DC tariff moratorium"
    return False


def _trigger_regulatory_pause(ctx):
    """Fires on PSC/PUC docket-level interconnection pauses. Structurally
    different risk from tariff moratoriums: defined lift timelines, primarily
    schedule risk rather than existential risk. Base P tiered by lift-date
    proximity via ``_p_regulatory_pause``."""
    for m in ctx.get("regulatory_moratoriums") or []:
        util = m.get("utility_name", "utility")
        docket = m.get("docket", "")
        lift = m.get("expected_lift_date", "TBD")
        months = _months_until(lift)
        when = f"~{months:.1f} months out" if months is not None else "no firm lift"
        return f"{util}: {docket} active interconnection pause (expected lift {lift}, {when})"
    return False


# Lift-date proximity -> base P for regulatory_interconnection_pause. Months
# are measured from today; past-dated lifts are clamped to 0 months (imminent).
_REG_PAUSE_P_BY_MONTHS: list[tuple[float, float]] = [
    (6.0, 0.30),    # lifting within 6 months: schedule risk only
    (12.0, 0.55),   # 6-12 months: current baseline
    (24.0, 0.70),   # 12-24 months: eats most hyperscaler plan horizons
    (9999.0, 0.85),  # >24 months: approaches tariff-moratorium severity
]


def _months_until(iso_date: str | None) -> float | None:
    """Return months from today to an ISO-formatted (YYYY-MM-DD) date, or None
    if unparseable. Past dates return a value <= 0."""
    if not iso_date:
        return None
    try:
        target = date.fromisoformat(iso_date)
    except Exception:
        return None
    return (target - date.today()).days / 30.44


def _p_regulatory_pause(ctx: dict) -> float:
    """Pick the earliest-lifting active pause and use its lift-proximity tier.

    When expected_lift_date is missing or unparseable, fall back to the
    12-month tier (0.55) -- treats "no firm lift" as moderate severity but
    not open-ended.
    """
    months_min: float | None = None
    any_pause = False
    for m in ctx.get("regulatory_moratoriums") or []:
        any_pause = True
        mo = _months_until(m.get("expected_lift_date"))
        if mo is None:
            continue
        mo = max(mo, 0.0)
        months_min = mo if months_min is None else min(months_min, mo)
    if not any_pause:
        return 0.55
    if months_min is None:
        return 0.55
    for cap, p in _REG_PAUSE_P_BY_MONTHS:
        if months_min <= cap:
            return p
    return 0.85


_DEPOSIT_SEVERITY_P = {
    "light": 0.05,
    "moderate": 0.15,
    "onerous": 0.30,
    "prohibitive": 0.50,
}


def _tariff_deposit_severity(t: dict) -> str:
    """Return the deposit-severity tier for a tariff entry.

    Prefers an explicit ``deposit_severity`` field. Falls back to the legacy
    binary ``deposit_onerous`` -> "onerous" / "light" mapping so existing
    entries work without hand-edits. See
    ``docs/screen_methodology/onerous_tariff_deposit.md``.
    """
    sev = t.get("deposit_severity")
    if sev in _DEPOSIT_SEVERITY_P:
        return sev
    return "onerous" if t.get("deposit_onerous") else "light"


def _worst_deposit_severity(tariffs: list[dict]) -> str | None:
    """Return the worst severity among matched tariffs, or None if none are
    at-or-above the firing threshold ('moderate')."""
    if not tariffs:
        return None
    firing = [
        _tariff_deposit_severity(t) for t in tariffs
        if _tariff_deposit_severity(t) != "light"
    ]
    if not firing:
        return None
    return max(firing, key=lambda s: _DEPOSIT_SEVERITY_P[s])


def _p_onerous_deposit(ctx: dict) -> float:
    worst = _worst_deposit_severity(ctx.get("dc_tariffs") or [])
    if worst is None:
        return _DEPOSIT_SEVERITY_P["onerous"]  # fallback; trigger won't fire anyway
    return _DEPOSIT_SEVERITY_P[worst]


def _trigger_onerous_deposit(ctx):
    worst = _worst_deposit_severity(ctx.get("dc_tariffs") or [])
    if worst is None:
        return False
    # Pick the tariff that matches the worst tier to build the evidence string.
    for t in ctx.get("dc_tariffs") or []:
        if _tariff_deposit_severity(t) == worst:
            util = t.get("utility_name", "utility")
            tname = t.get("tariff_name", "")
            collat = t.get("collateral_desc") or "collateral requirement"
            return f"{util} {tname} [{worst}]: {collat}"
    return False


# ---------------------------------------------------------------------------
# Power outlook -- qualitative supply-vs-demand judgment
# ---------------------------------------------------------------------------
#
# Replaces the former grid_severely_insufficient / grid_minor_deficit pair of
# MW-deficit killers (retired 2026-04-24). Rationale in
# docs/screen_methodology/grid_severely_insufficient.md:
#
#   The old approach quantified "how many MW are left" via a heuristic in
#   grid_assessment.py (nearest HV-line voltage class * multipliers). That
#   produces precision without accuracy -- actual host-utility capacity is
#   unknown without a real system-impact study. Tiering a made-up number by
#   deficit ratio compounded the error.
#
#   The replacement asks a different question: is this site's power picture
#   directionally "promising" (supply anchors present) or "doubtful" (nothing
#   nearby to build off of)? It's a scan over observable infrastructure
#   facts, not a MW calculation.
#
# Signals driving the outlook:
#   SUPPLY (+)
#     * brownfield retired-gen within 10 km -- usable switchyard/HV ties
#     * planned or under-construction substation within 50 km
#     * existing large substation within 10 km (>=230 kV or >=5 circuits)
#     * active generation pipeline in state IX queue (>=3 GW in study/
#       construction, tells us the utility+ISO are adding gen supply)
#   DEMAND (-)
#     * heavy announced/planned DC pipeline nearby competing for capacity
#     * site is grid-remote (no HV line within 30 km) with zero supply anchors
#
# Three-way verdict: promising | neutral | doubtful.
# Only "doubtful" triggers the killer (flat base P=0.40, tenant-scaled).
# "promising" earns narrative credit only -- opportunity side is already
# boosted by cluster_signal and brownfield_fit, so no double-count.


LARGE_SUBSTATION_KV = 230.0  # min voltage to count a substation as "large"
LARGE_SUBSTATION_LINES = 5   # min circuit count if voltage is unknown
LARGE_SUBSTATION_RADIUS_KM = 10.0
# Planned / under-construction substation within this range counts as a local
# supply anchor. 25 km keeps us honest -- a 345 kV project 40+ km away is a
# regional signal, not a site-specific anchor.
PLANNED_SUBSTATION_RADIUS_KM = 25.0
STATE_QUEUE_ACTIVE_GW = 3.0  # sum of advanced-stage gen in state queue


def _large_substation_nearby(ctx: dict) -> tuple[bool, str]:
    """True if a large (>=230 kV or >=5 circuits) substation is within 10 km."""
    for s in ctx.get("substations") or []:
        if (s.get("dist_km") or 999) > LARGE_SUBSTATION_RADIUS_KM:
            continue
        max_kv = s.get("max_infer") or 0
        try:
            max_kv = float(max_kv)
        except (TypeError, ValueError):
            max_kv = 0
        lines = s.get("lines") or 0
        try:
            lines = int(lines)
        except (TypeError, ValueError):
            lines = 0
        if max_kv >= LARGE_SUBSTATION_KV or lines >= LARGE_SUBSTATION_LINES:
            name = s.get("name") or "unnamed"
            kv_str = f"{max_kv:.0f} kV" if max_kv else f"{lines} circuits"
            d = s.get("dist_km") or 0
            return True, f"{name} substation ({kv_str}) {d:.1f} km"
    return False, ""


def _planned_substation_nearby(ctx: dict) -> tuple[bool, str]:
    """True if a planned/under-construction substation is within 50 km."""
    for ps in ctx.get("planned_substations") or []:
        if (ps.get("dist_km") or 999) > PLANNED_SUBSTATION_RADIUS_KM:
            continue
        name = ps.get("name") or "planned substation"
        proj = ps.get("planned_project") or "upgrade"
        d = ps.get("dist_km") or 0
        status = ps.get("existing_or_new_substation") or ""
        tag = "new" if "new" in str(status).lower() else "upgrade"
        return True, f"{name} ({proj}, {tag}) {d:.1f} km"
    return False, ""


def _state_queue_active_gw(ctx: dict) -> float:
    """Sum MW (converted to GW) of in-flight generation queue entries in the
    site's state whose stage looks advanced (beyond initial-study).
    Returns 0 when queue data missing or all entries are early-stage.
    """
    queue = ctx.get("interconnection_queue") or []
    if not queue:
        return 0.0
    advanced_keywords = (
        "construction", "built", "operational", "facility", "ia-executed",
        "ia executed", "planning", "site control", "cluster", "phase 2",
        "phase 3", "active", "committed",
    )
    mw = 0.0
    for row in queue:
        stage = (row.get("stage") or "").lower()
        tech = (row.get("technology") or "").lower()
        if "storage" in tech and "hybrid" not in tech:
            # Stand-alone storage doesn't add firm gen headroom.
            continue
        if any(k in stage for k in advanced_keywords):
            mw += float(row.get("total_mw") or 0)
    return mw / 1000.0


def _announced_dc_pressure(ctx: dict) -> tuple[float, int]:
    """Return (total announced/planned MW, count) of nearby DC projects that
    are NOT yet operating (so they represent competing demand for capacity).
    """
    dcs = ctx.get("nearby_dcs") or []
    total_mw = 0.0
    count = 0
    for d in dcs:
        stage = (d.get("lifecycle_stage") or "").lower()
        if not stage or "operat" in stage:
            continue
        if "cancel" in stage or "shelved" in stage:
            continue
        total_mw += float(d.get("power_mw") or 0)
        count += 1
    return total_mw, count


# Pressure threshold: lots of competing load AND no supply side = doubtful.
ANNOUNCED_DC_PRESSURE_COUNT = 5
ANNOUNCED_DC_PRESSURE_MW = 1000.0


def grid_outlook(ctx: dict) -> dict:
    """Return a qualitative supply-vs-demand judgment for the site's power
    picture. See docs/screen_methodology/grid_severely_insufficient.md.

    Output dict:
      {
        "verdict": "promising" | "neutral" | "doubtful",
        "supply_signals": [str, ...],   # observable positive facts
        "demand_signals": [str, ...],   # observable negative facts
        "evidence": str,                # single-line summary
      }

    This is a directional call, not a MW calculation. We do not claim to
    know how many MW the host utility can deliver -- we read what is and
    isn't nearby.
    """
    supply: list[str] = []
    demand: list[str] = []

    bf = brownfield_fit(ctx)
    if bf is not None:
        supply.append(f"brownfield: {bf['evidence']}")

    ok, ev = _planned_substation_nearby(ctx)
    if ok:
        supply.append(f"planned substation: {ev}")

    ok, ev = _large_substation_nearby(ctx)
    if ok:
        supply.append(f"large substation: {ev}")

    state_gw = _state_queue_active_gw(ctx)
    if state_gw >= STATE_QUEUE_ACTIVE_GW:
        supply.append(f"{state_gw:.1f} GW active gen in state IX queue")

    cs = cluster_signal(ctx)
    if cs is not None:
        # Operating DC cluster = grid has historically served this load class.
        # Signal is neutral-to-positive; don't count as demand pressure.
        supply.append(f"cluster track record: {cs['evidence']}")

    announced_mw, announced_ct = _announced_dc_pressure(ctx)
    if announced_ct >= ANNOUNCED_DC_PRESSURE_COUNT and announced_mw >= ANNOUNCED_DC_PRESSURE_MW:
        demand.append(
            f"{announced_ct} competing projects ({announced_mw:.0f} MW) "
            "in announced/planned pipeline within 50 km"
        )
    elif announced_ct >= ANNOUNCED_DC_PRESSURE_COUNT:
        demand.append(f"{announced_ct} competing announced/planned projects within 50 km")

    hv_nearby = _hv_line_within(ctx, 30)
    if not hv_nearby and not supply:
        demand.append("no HV transmission (>=100 kV) within 30 km")

    # Verdict logic:
    #   * promising -- any "anchor" supply signal present (brownfield, planned
    #     substation, or large existing substation). Anchors are local
    #     infrastructure facts; regional/utility signals (state queue, cluster
    #     track record) are softer and don't by themselves flip the verdict.
    #   * doubtful -- no local anchor AND (no HV nearby OR dense competing
    #     demand). The site has neither a local anchor to build off of nor
    #     baseline grid access.
    #   * neutral -- HV present but no anchor, or mixed signals.
    local_anchor = any(
        s.startswith(("brownfield", "planned substation", "large substation"))
        for s in supply
    )

    if local_anchor:
        verdict = "promising"
    elif not local_anchor and (not hv_nearby or demand):
        verdict = "doubtful"
    else:
        verdict = "neutral"

    if supply and demand:
        evidence = f"{verdict} outlook: supply -> {'; '.join(supply)}; demand pressure -> {'; '.join(demand)}"
    elif supply:
        evidence = f"{verdict} outlook: {'; '.join(supply)}"
    elif demand:
        evidence = f"{verdict} outlook: {'; '.join(demand)}"
    else:
        evidence = f"{verdict} outlook: no strong supply or demand signals"

    return {
        "verdict": verdict,
        "supply_signals": supply,
        "demand_signals": demand,
        "evidence": evidence,
    }


def _trigger_power_outlook_doubtful(ctx):
    """Power outlook == doubtful, unless a BTM-gas path can finance on-site
    generation for a credit-worthy tenant (retains the alt-path override
    from the legacy grid killer, which empirically mattered for Abilene TX).
    """
    outlook = grid_outlook(ctx)
    if outlook["verdict"] != "doubtful":
        return False

    tenant = ctx.get("tenant_profile") or DEFAULT_TENANT_PROFILE
    if tenant in BTM_GAS_ANCHORING_TENANTS and btm_gas_viable(ctx)[0]:
        return False

    return outlook["evidence"]


def _trigger_flood_av(ctx):
    fz = _first(ctx.get("flood_zones") or [])
    if fz:
        zone = (fz.get("flood_zone") or "").upper()
        if zone.startswith(("A", "V")):
            return f"FEMA flood zone {zone} (special flood hazard area)"
    return False


def flood_500yr_exposure(ctx: dict) -> list[str]:
    """Return evidence strings for any 500-year (X-shaded) exposures.

    Narrative-only per docs/screen_methodology/flood_zone_av.md. The A/V
    killer covers the 100-yr SFHA; this helper surfaces the next-severity
    tier without adding to risk math.
    """
    out: list[str] = []
    for fz in ctx.get("flood_zones") or []:
        z = (fz.get("flood_zone") or "").upper()
        if z.startswith("X") and ("SHADED" in z or "500" in z):
            out.append(
                f"FEMA 500-year floodplain ({fz.get('flood_zone')}): outside SFHA "
                "but elevated flood premium; narrative risk only."
            )
    return out


_SEVERE_NAAQS_TIER_P = {"EXTREME": 0.55, "SEVERE": 0.40, "SERIOUS": 0.30}


def _severe_naaqs_worst_tier(ctx: dict) -> str | None:
    """Return the worst severe-tier classification present in the zones, or
    None if no severe/extreme/serious zone is present."""
    worst: str | None = None
    for z in ctx.get("nonattainment_zones") or []:
        cls = (z.get("classification") or "").upper()
        for tier in ("EXTREME", "SEVERE", "SERIOUS"):
            if tier in cls:
                if worst is None or _SEVERE_NAAQS_TIER_P[tier] > _SEVERE_NAAQS_TIER_P[worst]:
                    worst = tier
    return worst


def _p_severe_nonattainment(ctx: dict) -> float:
    """Tier by EPA classification. See docs/screen_methodology/nonattainment.md."""
    worst = _severe_naaqs_worst_tier(ctx)
    return _SEVERE_NAAQS_TIER_P.get(worst, 0.40) if worst else 0.40


def _trigger_severe_nonattainment(ctx):
    worst = _severe_naaqs_worst_tier(ctx)
    if worst is None:
        return False
    # Build evidence with the specific zone that earned the worst tier.
    for z in ctx.get("nonattainment_zones") or []:
        cls = (z.get("classification") or "").upper()
        if worst in cls:
            return (
                f"EPA {z.get('pollutant','NAAQS')} nonattainment "
                f"(classification: {z.get('classification')}, tier: {worst.lower()})"
            )
    return False


def marginal_nonattainment_narrative(ctx: dict) -> list[str]:
    """Narrative-only signal for non-severe nonattainment zones (per
    docs/screen_methodology/nonattainment.md, marginal/moderate are no longer
    deal-killers but still carry permit-overhead information for readers).
    """
    severe_classes = {"SEVERE", "EXTREME", "SERIOUS"}
    out: list[str] = []
    for z in ctx.get("nonattainment_zones") or []:
        cls = (z.get("classification") or "").upper()
        if any(s in cls for s in severe_classes):
            continue
        pollutant = z.get("pollutant", "NAAQS")
        tier = z.get("classification") or "marginal"
        out.append(
            f"EPA {pollutant} nonattainment ({tier}): NSR offsets required "
            "(~1.10-1.15:1 for marginal/moderate tiers)."
        )
    return out


_SEISMIC_TIER_P = {"D": 0.05, "E": 0.15, "F": 0.30}


def _p_high_seismic(ctx: dict) -> float:
    """Tier base P by ASCE 7-22 SDC class.
    See docs/screen_methodology/high_seismic.md."""
    s = ctx.get("seismic") or {}
    sdc = (s.get("seismic_design_category") or "").upper()
    return _SEISMIC_TIER_P.get(sdc, 0.08)


def _trigger_high_seismic(ctx):
    s = ctx.get("seismic") or {}
    sdc = (s.get("seismic_design_category") or "").upper()
    if sdc in _SEISMIC_TIER_P:
        return f"ASCE 7-22 seismic design category {sdc}"
    return False


def _trigger_justice40(ctx):
    """Legacy trigger helper, retained for narrative use only.

    As of 2026-04-24 this is no longer a deal-killer; see
    docs/screen_methodology/justice40_disadvantaged.md. The signal fires on
    nearly every urban/suburban DC site including every built anchor, so its
    class-level false-positive rate is too high to justify inclusion in the
    feasibility math. The report surfaces it via justice40_narrative().
    """
    j = ctx.get("justice40") or {}
    if j.get("is_disadvantaged"):
        return "Justice40 disadvantaged community (NEPA/EJ scrutiny)"
    return False


def justice40_narrative(ctx: dict) -> list[str]:
    """Narrative-only Justice40 signal: whether the site intersects a CEJST
    disadvantaged tract and what that implies for federal-nexus projects.
    Does not contribute to feasibility math.
    """
    j = ctx.get("justice40") or {}
    if not j.get("is_disadvantaged"):
        return []
    categories = j.get("disadvantaged_categories") or j.get("categories") or []
    cat_str = ", ".join(categories) if categories else "categories not specified"
    return [
        f"CEJST disadvantaged tract overlap ({cat_str}). Federal-nexus projects "
        "here may face expanded community-engagement obligations under the "
        "prevailing environmental-justice executive order framework; timelines "
        "are weakly correlated with NEPA EIS duration based on 2022-2025 cohort."
    ]


HIGH_RATE_ABSOLUTE_FLOOR_CENTS = 14.0
HIGH_RATE_STATE_RELATIVE_MULT = 1.25
VERY_HIGH_RATE_CENTS = 20.0


def _p_high_rate(ctx: dict) -> float:
    """Tier P by rate severity.
    See docs/screen_methodology/high_industrial_rate.md."""
    r = ctx.get("utility_rate") or {}
    cents = r.get("industrial_rate_cents")
    if cents is not None and cents > VERY_HIGH_RATE_CENTS:
        return 0.25
    return 0.15


def _trigger_high_rate(ctx):
    """Fires when industrial rate is above the absolute floor (14 c/kWh) OR
    above 1.25x the state industrial average. Two-path design catches both
    absolute outliers and sites that are expensive relative to local norms.
    See docs/screen_methodology/high_industrial_rate.md.
    """
    r = ctx.get("utility_rate") or {}
    cents = r.get("industrial_rate_cents")
    if cents is None:
        return False
    # Lazy import to avoid a circular-import at module load if reference_data
    # changes later.
    from reference_data import get_state_industrial_rate_avg

    state = ctx.get("state")
    state_avg = get_state_industrial_rate_avg(state)

    abs_trip = cents > HIGH_RATE_ABSOLUTE_FLOOR_CENTS
    rel_trip = state_avg is not None and cents > HIGH_RATE_STATE_RELATIVE_MULT * state_avg

    if not (abs_trip or rel_trip):
        return False

    reasons = []
    if abs_trip:
        reasons.append(f">{HIGH_RATE_ABSOLUTE_FLOOR_CENTS:.0f} c/kWh absolute floor")
    if rel_trip:
        reasons.append(f">{HIGH_RATE_STATE_RELATIVE_MULT}x {state} avg ({state_avg:.1f} c/kWh)")
    return f"Industrial rate {cents:.1f} c/kWh triggers: {', '.join(reasons)}"


# --- The registry -----------------------------------------------------------

# Tenant scaling philosophy (recalibrated against anchor regression sites):
#   - Tariff deposits: hyperscalers clear credit thresholds trivially; anchored
#     projects negotiate; merchants bear full cost. Scale 1.0 / 0.4 / 0.15.
#   - Grid deficits: hyperscalers/anchors fund upgrades, but timing/capital
#     still hurt. Scale 1.0 / 0.7 / 0.5.
#   - Rate ceilings: even hyperscalers care about LCOE. Scale 1.0 / 0.8 / 0.5.
#   - Environmental/regulatory: same P regardless of tenant (permit timelines
#     don't compress for balance-sheet reasons).


DEAL_KILLERS: list[DealKiller] = [
    DealKiller(
        name="utility_moratorium",
        category="tariff",
        probability=0.90,
        rationale="Active tariff-level moratoriums halt new large-load interconnections indefinitely; 1-3+ year delays typical with no defined lift. Usually kill hyperscaler-deadline deals.",
        trigger=_trigger_tariff_moratorium,
        calibration_hook="backtest: fraction of demand_ledger sites in moratorium utilities shelved vs built within 36 months.",
        tenant_scaling={"speculative": 1.0, "anchored": 0.9, "hyperscaler": 0.8},
    ),
    DealKiller(
        name="regulatory_interconnection_pause",
        category="regulatory",
        # Distinct from utility_moratorium: PSC/PUC docket pauses have defined
        # lift timelines and the risk is primarily schedule slip, not project
        # death. Base P is lift-proximity-tiered per
        # docs/screen_methodology/moratoriums.md.
        probability=0.55,  # seed; effective P comes from _p_regulatory_pause
        rationale="PSC/PUC docket-level interconnection pause. Base P tiered by months to expected lift (<=6 -> 0.30, <=12 -> 0.55, <=24 -> 0.70, >24 -> 0.85). Hyperscalers with long plan horizons absorb short pauses more readily than merchants.",
        trigger=_trigger_regulatory_pause,
        calibration_hook="backtest: interconnection-queue dwell time during active regulatory pauses vs post-lift baseline; correlate actual-paused-duration with observed-kill-rate.",
        tenant_scaling={"speculative": 1.0, "anchored": 0.7, "hyperscaler": 0.5},
        probability_fn=_p_regulatory_pause,
    ),
    DealKiller(
        name="onerous_tariff_deposit",
        category="tariff",
        probability=0.30,  # seed; effective P comes from tariff deposit_severity via probability_fn
        rationale="Large collateral / minimum-bill / exit-fee commitments scare away merchant developers; IG-credit hyperscalers clear thresholds. Severity tiered light/moderate/onerous/prohibitive per docs/screen_methodology/onerous_tariff_deposit.md.",
        trigger=_trigger_onerous_deposit,
        calibration_hook="backtest: merchant cancellation rate vs hyperscaler operating rate by deposit_severity tier.",
        tenant_scaling={"speculative": 1.0, "anchored": 0.4, "hyperscaler": 0.15},
        probability_fn=_p_onerous_deposit,
    ),
    DealKiller(
        name="power_outlook_doubtful",
        category="grid",
        probability=0.40,
        rationale="Qualitative supply-vs-demand judgment: no nearby brownfield, no planned substation, no large existing substation, and no active in-state gen pipeline -- while either HV transmission is absent (>=30 km) or announced DC load is saturating. Flat P=0.40 (coarse by design -- we read observable anchors, not fake MW deltas). Suppressed when BTM gas is viable for a credit-worthy tenant. See docs/screen_methodology/grid_severely_insufficient.md.",
        trigger=_trigger_power_outlook_doubtful,
        calibration_hook="backtest: sites with doubtful outlook at announcement vs built/shelved at 36 months; sweep verdict thresholds on a hand-labeled corpus of anchor + failed sites.",
        tenant_scaling={"speculative": 1.0, "anchored": 0.7, "hyperscaler": 0.5},
    ),
    # grid_severely_insufficient + grid_minor_deficit retired 2026-04-24.
    # The former relied on grid_assessment.max_mw, which is a voltage-class
    # heuristic (precision without accuracy); replaced by the qualitative
    # power_outlook_doubtful classifier above. See
    # docs/screen_methodology/grid_severely_insufficient.md and
    # docs/screen_methodology/grid_minor_deficit.md.
    DealKiller(
        name="flood_zone_av",
        category="environmental",
        probability=0.50,
        rationale="FEMA zone A/V sites face insurability, raised-slab costs ($20-50M), investor aversion; most hyperscale customers decline.",
        trigger=_trigger_flood_av,
        calibration_hook="backtest: DC sites in zone A/V vs zone X actual build-out rates.",
        tenant_scaling={"speculative": 1.0, "anchored": 0.9, "hyperscaler": 0.8},
    ),
    DealKiller(
        name="severe_nonattainment",
        category="environmental",
        probability=0.40,  # seed; effective P tiered by classification
        rationale="Serious+ NAAQS nonattainment adds PSD/offsets for gensets. Base P tiered Extreme 0.55 / Severe 0.40 / Serious 0.30 per docs/screen_methodology/nonattainment.md.",
        trigger=_trigger_severe_nonattainment,
        calibration_hook="backtest: permit duration + cancellation rate by classification tier for DCs in severe-nonattainment counties.",
        probability_fn=_p_severe_nonattainment,
    ),
    # marginal_nonattainment retired from DEAL_KILLERS as of 2026-04-24: fired
    # on nearly every urban/suburban site including every built anchor, giving
    # it low signal value. See docs/screen_methodology/nonattainment.md.
    # Narrative surfaces via marginal_nonattainment_narrative().
    DealKiller(
        name="high_seismic",
        category="environmental",
        probability=0.05,  # seed; effective P tiered by SDC class
        rationale="SDC D/E/F drives construction cost and peer-review overhead. Base P tiered D 0.05 / E 0.15 / F 0.30 per docs/screen_methodology/high_seismic.md. D remains routine (The Dalles, Quincy); F materially harder to finance.",
        trigger=_trigger_high_seismic,
        calibration_hook="backtest: completed-project IRR distribution by SDC bucket; cost_per_mw vs SDC class.",
        probability_fn=_p_high_seismic,
    ),
    # justice40_disadvantaged retired from DEAL_KILLERS as of 2026-04-24.
    # Fired on nearly every urban/suburban DC site including every built
    # anchor, so class-level false-positive rate was too high to justify
    # inclusion in feasibility math. Narrative surfaces via
    # justice40_narrative(); see docs/screen_methodology/justice40_disadvantaged.md.
    DealKiller(
        name="high_industrial_rate",
        category="market",
        probability=0.15,  # seed; effective P tiered via _p_high_rate
        rationale="Industrial rates above 14 c/kWh absolute OR 1.25x state avg erode DC opex; LCOE-focused tenants self-deselect. P elevated to 0.25 when rate > 20 c/kWh. See docs/screen_methodology/high_industrial_rate.md.",
        trigger=_trigger_high_rate,
        calibration_hook="backtest: DC announcement rate by utility avg industrial rate bucket; correlate cancel_rate with state-relative quantile.",
        tenant_scaling={"speculative": 1.0, "anchored": 0.8, "hyperscaler": 0.5},
        probability_fn=_p_high_rate,
    ),
]


# ---------------------------------------------------------------------------
# Combination math
# ---------------------------------------------------------------------------


def combined_risk(probabilities: list[float]) -> float:
    """1 - product(1 - p_i). Independent-events assumption.

    >>> combined_risk([])
    0.0
    >>> round(combined_risk([0.5, 0.5]), 3)
    0.75
    >>> round(combined_risk([0.3, 0.3, 0.3]), 3)
    0.657
    """
    r = 1.0
    for p in probabilities:
        r *= (1.0 - max(0.0, min(1.0, p)))
    return 1.0 - r


BROWNFIELD_OPPORTUNITY_BOOST = 0.10  # legacy seed; tiered value comes from brownfield_fit()


def compute_opportunity(scores: dict, ctx: dict | None = None) -> tuple[float, str | None]:
    """Return (opportunity 0..1, boost_evidence or None).

    Uses the same 1-5 factors as the legacy weighted score, excluding the
    risk-related factors (DC Tariff Risk, Environmental) which are already
    represented on the risk side.

    Opportunity boosts stack (capped at 1.0):
      * +CLUSTER_OPPORTUNITY_BOOST when an active DC cluster is nearby.
      * +BROWNFIELD_OPPORTUNITY_BOOST when a retired-plant interconnection is
        usable. Indian River / Homer City style sites materially reduce
        interconnection cost and schedule -- that's value that belongs on the
        opportunity side, not just as risk suppression.
    """
    opportunity_factors = ["Grid Access", "Utility Rate", "Fiber/Telecom",
                           "Water", "Transportation", "Tax Incentives"]
    values = [scores[k] for k in opportunity_factors if k in scores]
    if not values:
        base = 0.0
    else:
        base = (sum(values) / len(values)) / 5.0

    ev_parts: list[str] = []
    if ctx is not None:
        cs = cluster_signal(ctx)
        if cs is not None:
            base = min(1.0, base + cs["opportunity_boost"])
            ev_parts.append(f"{cs['evidence']} (+{cs['opportunity_boost']:.2f} opportunity)")
        bf = brownfield_fit(ctx)
        if bf is not None:
            base = min(1.0, base + bf["opportunity_boost"])
            ev_parts.append(f"{bf['evidence']} (+{bf['opportunity_boost']:.2f} opportunity)")

    return base, ("; ".join(ev_parts) if ev_parts else None)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


@dataclass
class TriggeredKiller:
    name: str
    category: str
    probability: float  # adjusted for tenant profile
    base_probability: float  # seed P before tenant scaling
    evidence: str
    rationale: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "probability": self.probability,
            "base_probability": self.base_probability,
            "evidence": self.evidence,
            "rationale": self.rationale,
        }


def compute_feasibility(ctx: dict, legacy_scores: dict) -> dict:
    """Compute the risk-adjusted feasibility of a site.

    Reads ``ctx["tenant_profile"]`` (defaulting to "speculative"). See module
    docstring for the full model.
    """
    tenant = ctx.get("tenant_profile") or DEFAULT_TENANT_PROFILE
    if tenant not in TENANT_PROFILES:
        tenant = DEFAULT_TENANT_PROFILE

    triggered: list[TriggeredKiller] = []
    for killer in DEAL_KILLERS:
        fires, evidence = killer.fires(ctx)
        if fires:
            triggered.append(TriggeredKiller(
                name=killer.name,
                category=killer.category,
                probability=killer.effective_probability(ctx, tenant),
                base_probability=killer.base_probability(ctx),
                evidence=evidence,
                rationale=killer.rationale,
            ))

    risk = combined_risk([tk.probability for tk in triggered])
    opp, boost_ev = compute_opportunity(legacy_scores, ctx)
    feas = opp * (1.0 - risk)

    if feas >= 0.55:
        rating = "Strong"
    elif feas >= 0.35:
        rating = "Moderate"
    elif feas >= 0.20:
        rating = "Challenging"
    else:
        rating = "Poor"

    return {
        "feasibility": feas,
        "opportunity": opp,
        "combined_risk": risk,
        "rating": rating,
        "tenant_profile": tenant,
        "cluster_evidence": boost_ev,  # retained key name for backward compat
        "opportunity_boost_evidence": boost_ev,
        "power_path": power_path(ctx),
        "triggered_killers": [tk.to_dict() for tk in triggered],
        "killer_catalog_size": len(DEAL_KILLERS),
    }


def _rating(feas: float) -> str:
    if feas >= 0.55:
        return "Strong"
    if feas >= 0.35:
        return "Moderate"
    if feas >= 0.20:
        return "Challenging"
    return "Poor"


def compute_feasibility_all_tenants(ctx: dict, legacy_scores: dict) -> dict:
    """Compute feasibility for every tenant profile in a single pass.

    Triggered killers are determined once (whether they fire is structural,
    not tenant-dependent). For each tenant profile we compute that tenant's
    effective P per killer, the combined risk, and the resulting feasibility.

    Opportunity is identical across tenants -- it depends on site fundamentals
    plus brownfield/cluster boosts, not on who is building.

    Returns:
        {
            "primary_tenant": str,        # the requested ctx tenant (for back-compat detail sections)
            "opportunity": float,
            "opportunity_boost_evidence": str | None,
            "power_path": dict,
            "killer_catalog_size": int,
            "triggered_killers": [        # one row per fired killer
                {
                    "name": str, "category": str, "evidence": str,
                    "rationale": str, "base_probability": float,
                    "p_by_tenant": {"speculative": .., "anchored": .., "hyperscaler": ..},
                    "tenant_scaling": {"speculative": .., "anchored": .., "hyperscaler": ..},
                }
            ],
            "by_tenant": {                # one entry per tenant profile
                "speculative": {"feasibility": .., "combined_risk": .., "rating": ..},
                ...
            },
            "tenant_descriptions": {tenant: prose, ...},
        }
    """
    primary_tenant = ctx.get("tenant_profile") or DEFAULT_TENANT_PROFILE
    if primary_tenant not in TENANT_PROFILES:
        primary_tenant = DEFAULT_TENANT_PROFILE

    fired: list[tuple[DealKiller, str]] = []
    for killer in DEAL_KILLERS:
        fires, evidence = killer.fires(ctx)
        if fires:
            fired.append((killer, evidence))

    triggered: list[dict] = []
    for killer, evidence in fired:
        base = killer.base_probability(ctx)
        p_by_tenant = {
            t: max(0.0, min(1.0, base * killer.tenant_scaling.get(t, 1.0)))
            for t in TENANT_PROFILES
        }
        triggered.append({
            "name": killer.name,
            "category": killer.category,
            "evidence": evidence,
            "rationale": killer.rationale,
            "base_probability": base,
            "p_by_tenant": p_by_tenant,
            "tenant_scaling": {t: killer.tenant_scaling.get(t, 1.0) for t in TENANT_PROFILES},
        })

    opp, boost_ev = compute_opportunity(legacy_scores, ctx)

    by_tenant: dict[str, dict] = {}
    for t in TENANT_PROFILES:
        risk = combined_risk([tk["p_by_tenant"][t] for tk in triggered])
        feas = opp * (1.0 - risk)
        by_tenant[t] = {
            "feasibility": feas,
            "combined_risk": risk,
            "rating": _rating(feas),
        }

    return {
        "primary_tenant": primary_tenant,
        "opportunity": opp,
        "opportunity_boost_evidence": boost_ev,
        "power_path": power_path(ctx),
        "killer_catalog_size": len(DEAL_KILLERS),
        "triggered_killers": triggered,
        "by_tenant": by_tenant,
        "tenant_descriptions": dict(TENANT_DESCRIPTIONS),
    }
