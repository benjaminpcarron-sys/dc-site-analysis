"""DC tariff provisions and state tax incentive reference data.

Copied from dc-site-mapper ingest scripts (March 2026 vintage).
"""

DC_TARIFFS = [
    {
        "utility_name": "Dominion Energy Virginia",
        "utility_aliases": ["Virginia Electric & Power Co", "Virginia Electric and Power"],
        "state": "VA",
        "tariff_name": "GS-5",
        "tariff_type": "dc_specific",
        "min_demand_mw": 25,
        "contract_term_years": 14,
        "min_billing_pct": 85,
        "collateral_desc": "Upfront collateral payments to cover grid upgrade costs",
        "exit_fee_desc": "Capacity reduction >20% or termination triggers exit fees",
        "deposit_onerous": False,
        "moratorium": False,
        "status": "approved",
        "notes": "SCC approved Nov 2025. 85% min billing for T&D, 60% for generation. Up to 4-year ramp. Load factor >= 75% required.",
    },
    {
        "utility_name": "AEP Ohio",
        "utility_aliases": ["Ohio Power Company", "Ohio Power Co"],
        "state": "OH",
        "tariff_name": "Schedule DCT",
        "tariff_type": "dc_specific",
        "min_demand_mw": 25,
        "contract_term_years": 12,
        "min_billing_pct": 85,
        "collateral_desc": "50% of total minimum charges for full term if credit below A-/A3. Load study fees: 25-50MW $10K, 50-100MW $50K, 100+MW $100K.",
        "exit_fee_desc": "3 years of minimum charges; available only after year 5 post-ramp",
        "deposit_onerous": True,
        "deposit_severity": "onerous",
        "deposit_severity_rationale": "50% collateral on 12-yr minimum bills is ~6-year forward revenue at risk for below-IG credit; prohibitive for merchants, negotiable for anchors.",
        "moratorium": False,
        "status": "effective",
        "notes": "PUCO approved Jul 9, 2025. Prior moratorium (Mar 2023 - Jul 2025) now lifted. Ramp: Yr1 50%, Yr2 65%, Yr3 80%, Yr4 90%.",
    },
    {
        "utility_name": "Indiana Michigan Power",
        "utility_aliases": ["Indiana Michigan Power Co", "I&M"],
        "state": "IN",
        "tariff_name": "Large Load Settlement",
        "tariff_type": "large_load",
        "min_demand_mw": 70,
        "contract_term_years": 12,
        "min_billing_pct": 80,
        "collateral_desc": "Required for customers not meeting credit rating and liquidity thresholds",
        "exit_fee_desc": "Triggered if capacity reduced >20%; mutual reductions require IURC approval",
        "deposit_onerous": False,
        "moratorium": False,
        "status": "approved",
        "notes": "IURC approved Feb 2025. 70 MW single location OR 150 MW aggregate. Up to 5-year ramp.",
    },
    {
        "utility_name": "Georgia Power",
        "utility_aliases": ["Georgia Power Co", "Georgia Power Company"],
        "state": "GA",
        "tariff_name": "Special Contract Authority",
        "tariff_type": "dc_specific",
        "min_demand_mw": 100,
        "contract_term_years": 15,
        "min_billing_pct": None,
        "collateral_desc": "Can charge for upstream generation, transmission, and distribution costs",
        "exit_fee_desc": "Per negotiated contract terms; PSC review required",
        "deposit_onerous": False,
        "moratorium": False,
        "status": "approved",
        "notes": "PSC rule approved unanimously Jan 23, 2025. Every contract >100MW must be submitted to PSC. Rate freeze for residential through 2028.",
    },
    {
        "utility_name": "Entergy Louisiana",
        "utility_aliases": ["Entergy Louisiana LLC", "Entergy Louisiana Inc"],
        "state": "LA",
        "tariff_name": "Fair Share Plus",
        "tariff_type": "dc_specific",
        "min_demand_mw": None,
        "contract_term_years": None,
        "min_billing_pct": None,
        "collateral_desc": "Cash deposits + letters of credit + parent company guarantees required",
        "exit_fee_desc": "Assets at end of term either cost-effective for all customers or paid by DC",
        "deposit_onerous": True,
        "moratorium": False,
        "status": "framework",
        "notes": "Framework announced 2025. Individual contracts filed with state commissions. Rates must cover incremental + existing grid costs.",
    },
    {
        "utility_name": "Entergy Mississippi",
        "utility_aliases": ["Entergy Mississippi LLC", "Entergy Mississippi Inc"],
        "state": "MS",
        "tariff_name": "Fair Share Plus",
        "tariff_type": "dc_specific",
        "min_demand_mw": None,
        "contract_term_years": None,
        "min_billing_pct": None,
        "collateral_desc": "Cash deposits + letters of credit + parent company guarantees",
        "exit_fee_desc": "Per contract; pre-certification statute for generation tied to data centers",
        "deposit_onerous": True,
        "moratorium": False,
        "status": "framework",
        "notes": "MS passed pre-certification statute for generation tied to data centers.",
    },
    {
        "utility_name": "DTE Energy",
        "utility_aliases": ["DTE Electric Company", "DTE Electric Co"],
        "state": "MI",
        "tariff_name": "Schedule D11 (DC Contract)",
        "tariff_type": "dc_specific",
        "min_demand_mw": 1383,
        "contract_term_years": 19,
        "min_billing_pct": 80,
        "collateral_desc": "Customer-funded 1.4 GW energy storage",
        "exit_fee_desc": "Up to 10 years of minimum billing demand for early termination",
        "deposit_onerous": True,
        "deposit_severity": "prohibitive",
        "deposit_severity_rationale": "1.4 GW customer-funded BESS + 10-yr min-bill exit fee implies $1B+ upfront capital + decade of revenue risk. Only ultra-anchored hyperscalers (Meta/Google) could plausibly underwrite.",
        "moratorium": False,
        "status": "approved",
        "notes": "MPSC approved Dec 18, 2025 (Oracle subsidiary). MPSC directed DTE to file general large load tariff within 90 days.",
    },
    {
        "utility_name": "Consumers Energy",
        "utility_aliases": ["Consumers Energy Co", "Consumers Energy Company"],
        "state": "MI",
        "tariff_name": "Rate GPD (DC Provision)",
        "tariff_type": "dc_specific",
        "min_demand_mw": 100,
        "contract_term_years": 15,
        "min_billing_pct": 80,
        "collateral_desc": "Must file ex parte case showing no subsidy from other customer classes",
        "exit_fee_desc": None,
        "deposit_onerous": False,
        "moratorium": False,
        "status": "approved",
        "notes": "MPSC approved Nov 6, 2025. 100 MW single customer or aggregated with individual sites >= 20 MW. Up to 5-year ramp.",
    },
    {
        "utility_name": "Xcel Energy",
        "utility_aliases": ["Public Service Company of Colorado", "PSCo", "Northern States Power"],
        "state": "CO",
        "tariff_name": "Large Load Tariff (proposed)",
        "tariff_type": "dc_specific",
        "min_demand_mw": None,
        "contract_term_years": 15,
        "min_billing_pct": None,
        "collateral_desc": "Upfront fees and security deposits (PUC guiding principles)",
        "exit_fee_desc": "Early exit fees for early termination (PUC guiding principles)",
        "deposit_onerous": False,
        "moratorium": False,
        "status": "proposed",
        "notes": "PUC directed filing Jan 2026. 5.8 GW pending DC applications; $22B infrastructure projected through 2040. Also pursuing in MN, WI, NM.",
    },
    {
        "utility_name": "NorthWestern Energy",
        "utility_aliases": ["NorthWestern Corp", "Northwestern Energy"],
        "state": "MT",
        "tariff_name": "Large Load Tariff (proposed)",
        "tariff_type": "dc_specific",
        "min_demand_mw": None,
        "contract_term_years": None,
        "min_billing_pct": None,
        "collateral_desc": "Full cost of transmission, generation, distribution upgrades",
        "exit_fee_desc": None,
        "deposit_onerous": True,
        "deposit_severity": "prohibitive",
        "deposit_severity_rationale": "Full upgrade cost passthrough with no cap + moratorium shows legislature treats large-load DCs as externalities to be fully internalized.",
        "moratorium": True,
        "status": "proposed",
        "notes": "De facto moratorium: will not serve new large loads until PSC approves tariff. Earthjustice complaint filed Nov 2025. 11 DC developers in active talks (Feb 2026). Up to 1,400 MW LOIs.",
    },
    {
        "utility_name": "ComEd",
        "utility_aliases": ["Commonwealth Edison", "Commonwealth Edison Co"],
        "state": "IL",
        "tariff_name": "Transmission Security Agreements",
        "tariff_type": "large_load",
        "min_demand_mw": 50,
        "contract_term_years": 10,
        "min_billing_pct": None,
        "collateral_desc": "Take-or-pay agreements with collateral covering 10 years of transmission service revenues",
        "exit_fee_desc": "If load requirements not met, large load applicant covers shortfall dollar-for-dollar",
        "deposit_onerous": True,
        "moratorium": False,
        "status": "effective",
        "notes": "8 customers signed, covering 6.5 GW, preventing >$2B in transmission charges to existing customers.",
    },
    {
        "utility_name": "Evergy",
        "utility_aliases": ["Evergy Kansas Central", "Evergy Metro", "Westar Energy"],
        "state": "KS",
        "tariff_name": "LLPS (Large Load Power Service)",
        "tariff_type": "large_load",
        "min_demand_mw": 75,
        "contract_term_years": 17,
        "min_billing_pct": 80,
        "collateral_desc": "2 years of minimum monthly bills",
        "exit_fee_desc": "Min monthly bill x remaining months OR 12 months (whichever greater); higher penalties if notice <36 months",
        "deposit_onerous": True,
        "moratorium": False,
        "status": "effective",
        "notes": "KCC unanimously approved Nov 6, 2025. Capacity reduction permitted once after 5 years (max 25%). Optional renewable add-on.",
    },
    {
        "utility_name": "Ameren Missouri",
        "utility_aliases": ["Union Electric Co", "Ameren Missouri LLC"],
        "state": "MO",
        "tariff_name": "Large Load Customer Rate Plan",
        "tariff_type": "large_load",
        "min_demand_mw": 75,
        "contract_term_years": 17,
        "min_billing_pct": 80,
        "collateral_desc": "100% of direct interconnection costs upfront + financial security equal to 2 years of minimum monthly bills",
        "exit_fee_desc": "Exit fee = min projected monthly bill x remaining months; 36 months written notice required",
        "deposit_onerous": True,
        "moratorium": False,
        "status": "effective",
        "notes": "PSC approved Nov 24, 2025. No rate discounts. Revenue sharing when profits exceed authorized levels.",
    },
    {
        "utility_name": "Portland General Electric",
        "utility_aliases": ["Portland General Electric Co", "PGE"],
        "state": "OR",
        "tariff_name": "POWER Act Rate Class",
        "tariff_type": "dc_specific",
        "min_demand_mw": 20,
        "contract_term_years": 10,
        "min_billing_pct": None,
        "collateral_desc": "Large energy users pay for new transmission additions",
        "exit_fee_desc": None,
        "deposit_onerous": False,
        "moratorium": False,
        "status": "proposed",
        "notes": "POWER Act (HB 3546) signed Aug 2025. Proposed 25% rate increase for DC class. 430 MW contracted, 1.7 GW pipeline.",
    },
    {
        "utility_name": "APS",
        "utility_aliases": ["Arizona Public Service", "Arizona Public Service Co"],
        "state": "AZ",
        "tariff_name": "Extra-Large User Rate (proposed)",
        "tariff_type": "large_load",
        "min_demand_mw": None,
        "contract_term_years": None,
        "min_billing_pct": None,
        "collateral_desc": "DCs pay directly for infrastructure; no subsidy from residential/small business",
        "exit_fee_desc": None,
        "deposit_onerous": False,
        "moratorium": False,
        "status": "proposed",
        "notes": "Proposed 45% rate increase for extra-large users. Rate case filed Jun 2025. Phoenix #2 in North America for proposed DC development.",
    },
    {
        "utility_name": "Consolidated Edison",
        "utility_aliases": ["ConEd", "Con Edison"],
        "state": "NY",
        "tariff_name": "None (moratorium proposed)",
        "tariff_type": "moratorium",
        "min_demand_mw": 20,
        "contract_term_years": None,
        "min_billing_pct": None,
        "collateral_desc": None,
        "exit_fee_desc": None,
        "deposit_onerous": False,
        "moratorium": True,
        "status": "proposed",
        "notes": "Senate Bill S.9144: 3-year + 90-day moratorium on permits for DCs >= 20 MW. Queue grew from 6.8 GW to 12 GW. Bill introduced Feb 2026.",
    },
    {
        "utility_name": "Duke Energy Carolinas",
        "utility_aliases": ["Duke Energy Carolinas LLC"],
        "state": "NC",
        "tariff_name": "Energy Supply Agreements (no formal tariff yet)",
        "tariff_type": "large_load",
        "min_demand_mw": 100,
        "contract_term_years": None,
        "min_billing_pct": None,
        "collateral_desc": "Not yet formalized in tariff",
        "exit_fee_desc": "Not yet formalized",
        "deposit_onerous": False,
        "moratorium": False,
        "status": "under_review",
        "notes": "100 MW threshold triggers enhanced intake. Large load tariff docket expected per rate case settlement. New rates effective Jan 2027.",
    },
]

# Per-state DC tax incentives. Each entry SHOULD include `data_vintage` so
# stale research is never silently scored. When a state is absent, the current
# coverage gap is that `get_state_incentives` returns None, which the scorer
# treats as "no incentive" -- not "unknown". See EFFICACY_SCORECARD.md D20.
#
# Data vintage: March 2026 for all entries below unless otherwise noted. Any
# entry updated after that date should bump its own `data_vintage`.
_INCENTIVES_VINTAGE = "2026-03"

STATE_TAX_INCENTIVES = {
    "VA": {"sales_tax": True, "property_tax": True, "income_tax": False, "investment_threshold_m": 150, "job_requirement": 50, "duration_years": 10, "summary": "Sales & use tax exemption on computer equipment & cooling. Localities offer property tax abatement. Virginia is the #1 US DC market.", "data_vintage": _INCENTIVES_VINTAGE},
    "TX": {"sales_tax": True, "property_tax": True, "income_tax": False, "investment_threshold_m": 200, "job_requirement": 20, "duration_years": 10, "summary": "Ch. 313/Ch. 403 property tax abatement. Sales tax exemption on equipment. No state income tax."},
    "GA": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 100, "job_requirement": 25, "duration_years": 20, "summary": "Sales tax exemption on DC equipment (>$100M investment). Investment tax credit. County-level property tax abatements."},
    "NC": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 75, "job_requirement": 20, "duration_years": 10, "summary": "Sales tax refund on qualifying DC purchases. Property tax exemption via local incentives. Investment tax credit available."},
    "SC": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 50, "job_requirement": 25, "duration_years": 10, "summary": "Sales tax exemption on DC equipment. Property tax reduction via fee-in-lieu. Income tax credit for job creation."},
    "OH": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 100, "job_requirement": 20, "duration_years": 15, "summary": "Sales tax exemption on DC equipment (>$100M). Property tax exemption via CRA. Job creation tax credit."},
    "IN": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 50, "job_requirement": 10, "duration_years": 10, "summary": "Sales tax exemption on qualifying DC equipment. Property tax abatement. Economic development income tax credit."},
    "IA": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 10, "job_requirement": 1, "duration_years": 20, "summary": "Sales tax refund on DC equipment. Property tax exemption up to 20 years. Investment tax credit. Very low thresholds."},
    "NV": {"sales_tax": True, "property_tax": True, "income_tax": False, "investment_threshold_m": 100, "job_requirement": 50, "duration_years": 20, "summary": "Sales tax abatement (partial). Property tax abatement up to 75% for 10-20 years. No state income tax."},
    "MS": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 50, "job_requirement": 25, "duration_years": 10, "summary": "Sales tax exemption on DC construction & equipment. Ad valorem tax exemption. Income tax credit for infrastructure."},
    "NE": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 37, "job_requirement": 10, "duration_years": 10, "summary": "Sales tax exemption on DC equipment. Property tax exemption via ImagiNE Nebraska Act. Investment credit."},
    "OK": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 5, "job_requirement": 10, "duration_years": 10, "summary": "Sales tax exemption on DC equipment. Ad valorem exemption for 5 years. Quality Jobs incentive."},
    "WA": {"sales_tax": True, "property_tax": False, "income_tax": False, "investment_threshold_m": 10, "job_requirement": 35, "duration_years": None, "summary": "Sales & use tax exemption on eligible DC equipment and construction. No income tax. Low electricity costs."},
    "OR": {"sales_tax": False, "property_tax": True, "income_tax": True, "investment_threshold_m": 25, "job_requirement": 35, "duration_years": 15, "summary": "No sales tax. Enterprise zone property tax exemption (3-15 years). Strategic Investment Program for large DCs."},
    "AZ": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 100, "job_requirement": 25, "duration_years": 10, "summary": "Transaction privilege tax exemption on DC equipment. Property tax reduction via GPLET. Qualified facility tax credit."},
    "UT": {"sales_tax": True, "property_tax": False, "income_tax": True, "investment_threshold_m": 50, "job_requirement": 50, "duration_years": 10, "summary": "Sales tax exemption on DC equipment. Economic Development Tax Increment Financing."},
    "CO": {"sales_tax": False, "property_tax": False, "income_tax": True, "investment_threshold_m": None, "job_requirement": None, "duration_years": None, "summary": "Enterprise zone tax credits. Job creation tax credits. Limited DC-specific incentives."},
    "IL": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 250, "job_requirement": 20, "duration_years": 20, "summary": "EDGE tax credit. Enterprise zone sales tax exemption. Local property tax abatement for qualifying DCs."},
    "TN": {"sales_tax": True, "property_tax": True, "income_tax": False, "investment_threshold_m": 100, "job_requirement": 25, "duration_years": 10, "summary": "Sales tax exemption on DC equipment. PILOT property tax abatement. No income tax."},
    "KY": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 100, "job_requirement": 10, "duration_years": 15, "summary": "Sales tax exemption on DC equipment. Property tax moratorium via KBI. Income tax credits for job creation."},
    "MO": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 25, "job_requirement": 10, "duration_years": 10, "summary": "Sales tax exemption on DC equipment. Chapter 100 property tax abatement. Missouri Works income tax credit."},
    "WI": {"sales_tax": True, "property_tax": False, "income_tax": True, "investment_threshold_m": 50, "job_requirement": 10, "duration_years": 10, "summary": "Sales tax exemption on DC equipment. Enterprise Zone tax credits."},
    "PA": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 50, "job_requirement": 25, "duration_years": 10, "summary": "Computer DC Equipment Incentive Program (sales tax exemption). Keystone Innovation Zones. Local property tax abatement."},
    "NJ": {"sales_tax": True, "property_tax": False, "income_tax": True, "investment_threshold_m": 50, "job_requirement": 25, "duration_years": 10, "summary": "Sales tax exemption on DC equipment. NJEDA Grow NJ tax credits for job creation."},
    "NY": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 100, "job_requirement": 25, "duration_years": 15, "summary": "IDA-sponsored sales tax exemption. PILOT property tax abatement. Excelsior Jobs Program investment credit."},
    "MD": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 2, "job_requirement": None, "duration_years": 10, "summary": "Sales tax exemption on DC equipment (>$2M). Enterprise Zone property tax credits. Income tax credits."},
    "AL": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 100, "job_requirement": 20, "duration_years": 10, "summary": "Sales tax abatement on DC equipment. Property tax abatement via APDA. Growing Alabama credits."},
    "LA": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 25, "job_requirement": 5, "duration_years": 10, "summary": "Industrial Tax Exemption (property tax). Quality Jobs rebate. Enterprise Zone credits. Digital media credit."},
    "MN": {"sales_tax": True, "property_tax": False, "income_tax": True, "investment_threshold_m": 30, "job_requirement": 10, "duration_years": 10, "summary": "Sales tax exemption on DC equipment. Minnesota Job Creation Fund. DEED business incentives."},
    "MI": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 100, "job_requirement": 25, "duration_years": 15, "summary": "Sales tax exemption on DC equipment. PA 198 property tax abatement. Michigan Business Development Program."},
    "ID": {"sales_tax": True, "property_tax": True, "income_tax": True, "investment_threshold_m": 10, "job_requirement": 20, "duration_years": 15, "summary": "Sales tax exemption on DC equipment. Property tax exemption (via county). Tax reimbursement incentive."},
    # --- Added 2026-04-20 after D20 regression-harness finding (Millsboro DE) ---
    "DE": {"sales_tax": True, "property_tax": False, "income_tax": False, "investment_threshold_m": None, "job_requirement": None, "duration_years": None, "summary": "No state sales tax (de facto exemption on DC equipment). No state-level DC-specific program; property tax abatements are negotiated at county level (Sussex/Kent). New Castle County DC activity limited.", "data_vintage": "2026-04"},
}


def _vintage(entry):
    """Backfill data_vintage for entries that pre-date the field addition."""
    if entry is None:
        return None
    if "data_vintage" not in entry:
        entry["data_vintage"] = _INCENTIVES_VINTAGE
    return entry


# One-pass vintage backfill so existing entries don't each need touching.
for _st, _entry in list(STATE_TAX_INCENTIVES.items()):
    _vintage(_entry)


# Annual Cooling Degree Days by state (base 65°F, 30-year NOAA normals)
# Higher CDD = more cooling energy needed = higher OPEX
# Source: NOAA Climate Normals 1991-2020, state population-weighted averages
STATE_COOLING_DEGREE_DAYS = {
    "AL": 2102, "AK": 0, "AZ": 3916, "AR": 1826, "CA": 1013,
    "CO": 696, "CT": 711, "DE": 1117, "FL": 3556, "GA": 1981,
    "HI": 4522, "ID": 522, "IL": 1089, "IN": 1005, "IA": 868,
    "KS": 1457, "KY": 1253, "LA": 2677, "ME": 312, "MD": 1195,
    "MA": 596, "MI": 667, "MN": 581, "MS": 2270, "MO": 1432,
    "MT": 353, "NE": 1007, "NV": 2289, "NH": 414, "NJ": 962,
    "NM": 1303, "NY": 699, "NC": 1569, "ND": 508, "OH": 865,
    "OK": 1994, "OR": 315, "PA": 813, "RI": 613, "SC": 1930,
    "SD": 734, "TN": 1591, "TX": 2738, "UT": 1101, "VT": 375,
    "VA": 1276, "WA": 244, "WV": 838, "WI": 534, "WY": 322,
}

# Average farmland value $/acre by state (USDA NASS 2024)
# Proxy for greenfield DC site land costs. Actual DC-zoned land will be higher
# but relative state-to-state comparison is valid.
STATE_LAND_VALUE_PER_ACRE = {
    "AL": 4500, "AK": 1200, "AZ": 2200, "AR": 4200, "CA": 12300,
    "CO": 2600, "CT": 15100, "DE": 10500, "FL": 8900, "GA": 5400,
    "HI": 12600, "ID": 4500, "IL": 9200, "IN": 8800, "IA": 9900,
    "KS": 2600, "KY": 5200, "LA": 4100, "ME": 3700, "MD": 11100,
    "MA": 14900, "MI": 6400, "MN": 6200, "MS": 3700, "MO": 4800,
    "MT": 1100, "NE": 4400, "NV": 1300, "NH": 5400, "NJ": 16500,
    "NM": 580, "NY": 5200, "NC": 6300, "ND": 3100, "OH": 8400,
    "OK": 2600, "OR": 3600, "PA": 8200, "RI": 16400, "SC": 5100,
    "SD": 2900, "TN": 5400, "TX": 3000, "UT": 3000, "VT": 4100,
    "VA": 6400, "WA": 4600, "WV": 2500, "WI": 6100, "WY": 830,
}


def get_cooling_degree_days(state):
    """Return annual cooling degree days for a state."""
    return STATE_COOLING_DEGREE_DAYS.get(state)


def get_land_value(state):
    """Return average farmland value $/acre for a state (USDA NASS proxy)."""
    return STATE_LAND_VALUE_PER_ACRE.get(state)


def get_dc_tariffs(state, utility_name=None):
    """Return tariff provisions matching a state, optionally filtered by utility name."""
    results = []
    for t in DC_TARIFFS:
        if t["state"] != state:
            continue
        if utility_name:
            names = [t["utility_name"].lower()] + [a.lower() for a in t.get("utility_aliases", [])]
            ul = utility_name.lower()
            if not any(ul in n or n in ul for n in names):
                continue
        results.append(t)
    return results


def get_state_incentives(state):
    """Return tax incentive info for a state, or None."""
    return STATE_TAX_INCENTIVES.get(state)


# ---------------------------------------------------------------------------
# Regulatory interconnection moratoriums
# ---------------------------------------------------------------------------
#
# Captures utility-or-state-level interconnection pauses that exist as PSC/PUC
# docket actions rather than as tariff provisions. Critical distinction from
# DC_TARIFFS[*].moratorium: those are long-term tariff features; these are
# temporary regulatory holds with clearer lift timelines.
#
# Each entry uniquely identifies a utility and describes the docket-level
# action; add a 'county' filter only if the moratorium is geographically scoped
# (rare). Expire entries by setting status="lifted" when the hold is released
# -- keep the history so the regression harness can backtest decisions.
#
# Data vintage: 2026-04 unless otherwise noted.

REGULATORY_MORATORIUMS = [
    {
        "state": "DE",
        "utility_name": "Delmarva Power",
        "utility_aliases": ["Delmarva Power & Light", "Delmarva Power and Light", "DPL"],
        "docket": "DE PSC 25-0826",
        "scope": "All new large-load interconnections >=25 MW in Delmarva Power DE territory.",
        "status": "active",
        "filed_date": "2025-09-03",
        "expected_lift_date": "2026-12-31",  # commission decision late 2026
        "evidence_url": "https://depsc.delaware.gov/2025/10/14/delaware-psc-opens-docket-for-large-load-tariff-pauses-interconnections/",
        "notes": "Docket opened Sep 2025. Delmarva final tariff filing due Apr 27, 2026; hearing examiner ruling summer 2026; commission decision late 2026. No 500 MW facility can enter the interconnection queue until this lifts. Surfaced via Millsboro DE regression site.",
        "data_vintage": "2026-04",
    },
]


def get_regulatory_moratoriums(state, utility_name=None):
    """Return active regulatory moratoriums matching a state/utility, or []. Lifted entries are excluded."""
    results = []
    for m in REGULATORY_MORATORIUMS:
        if m.get("status") != "active":
            continue
        if m["state"] != state:
            continue
        if utility_name:
            names = [m["utility_name"].lower()] + [a.lower() for a in m.get("utility_aliases", [])]
            ul = utility_name.lower()
            if not any(ul in n or n in ul for n in names):
                continue
        results.append(m)
    return results


# ---------------------------------------------------------------------------
# Retired / brownfield generation sites (candidate DC interconnection anchors)
# ---------------------------------------------------------------------------
#
# Retired fossil/nuclear plants frequently have intact switchyards, high-voltage
# transmission ties, and large industrial-zoned parcels -- the three hardest
# things to reproduce for a greenfield DC site. A site within a few km of such
# a retired plant can reuse that interconnection capacity, which fundamentally
# changes the grid-adequacy analysis (HIFLD's transmission cache doesn't know
# the plant is offline, and has no concept of "repurposable capacity").
#
# Selection criteria for inclusion:
#   * former_mw >= 100 (material to DC-scale loads)
#   * retired_date <= current year + 5 (i.e. already offline or near-term)
#   * switchyard still physically in place (not demolished)
#
# Seed list is deliberately short. Expand as new sites surface in
# demand_ledger or site-specific research. Each entry should document the
# evidence URL.

RETIRED_GENERATION_SITES = [
    {
        "id": "indian_river_de",
        "name": "Indian River Power Plant",
        "operator": "NRG Energy (Indian River Power LLC)",
        "state": "DE",
        "county": "Sussex County",
        "lat": 38.5852,
        "lon": -75.2834,
        "former_mw": 785,
        "voltage_classes": ["230", "138"],
        "fuel": "coal",
        "retired_date": "2025-02",
        "acreage": 1200,
        "evidence_url": "https://www.gem.wiki/Indian_River_power_station",
        "notes": "4 coal units retired Feb 2025; 16 MW oil peaker decommissioning Jun 2025. 230 kV + 138 kV switchyard remains. Also proposed interconnection point for US Wind (~1,710 MW offshore) -- co-development opportunity. Partial flood exposure.",
        "data_vintage": "2026-04",
    },
    {
        "id": "homer_city_pa",
        "name": "Homer City Generating Station",
        "operator": "Homer City Redevelopment",
        "state": "PA",
        "county": "Indiana County",
        "lat": 40.5167,
        "lon": -79.1950,
        "former_mw": 1884,
        "voltage_classes": ["500", "345", "230"],
        "fuel": "coal",
        "retired_date": "2023-07",
        "acreage": 1900,
        "evidence_url": "https://www.gem.wiki/Homer_City_Generating_Station",
        "notes": "Announced 2025 redevelopment as natural gas + data center campus (Kiewit + Knighthead). 4.5 GW gas planned. Exemplar of retired-coal -> DC conversion.",
        "data_vintage": "2026-04",
    },
    {
        "id": "conemaugh_pa",
        "name": "Conemaugh Generating Station",
        "operator": "NRG Energy",
        "state": "PA",
        "county": "Indiana County",
        "lat": 40.3850,
        "lon": -79.0650,
        "former_mw": 1711,
        "voltage_classes": ["500", "345"],
        "fuel": "coal",
        "retired_date": "2028-12",  # announced retirement
        "acreage": 1500,
        "evidence_url": "https://www.gem.wiki/Conemaugh_Generating_Station",
        "notes": "Announced 2028 retirement. Large 500 kV switchyard. Early-stage candidate for DC redevelopment.",
        "data_vintage": "2026-04",
    },
    {
        "id": "brandon_shores_md",
        "name": "Brandon Shores Generating Station",
        "operator": "Talen Energy",
        "state": "MD",
        "county": "Anne Arundel County",
        "lat": 39.1775,
        "lon": -76.5333,
        "former_mw": 1295,
        "voltage_classes": ["230"],
        "fuel": "coal",
        "retired_date": "2028-06",  # announced retirement
        "acreage": 600,
        "evidence_url": "https://www.gem.wiki/Brandon_Shores_Generating_Station",
        "notes": "Retirement deferred to mid-2028 under RMR agreement. MD PSC concerns about reliability. Switchyard + BGE territory.",
        "data_vintage": "2026-04",
    },
    # 2026-04-24 expansion: per docs/screen_methodology/brownfield_interconnection.md,
    # 10 km radius + tiered opportunity boost. Added 4 confirmed retirements
    # with documented SIS or ROW reuse potential.
    {
        "id": "yates_ga",
        "name": "Plant Yates",
        "operator": "Georgia Power (Southern Company)",
        "state": "GA",
        "county": "Coweta County",
        "lat": 33.4514,
        "lon": -84.8911,
        "former_mw": 1250,
        "voltage_classes": ["500", "230"],
        "fuel": "coal",
        "retired_date": "2015-04",
        "acreage": 1700,
        "evidence_url": "https://www.gem.wiki/Plant_Yates",
        "notes": "Fully retired 2015. Switchyard retained; Southern has announced several gas reuse studies. Close to Atlanta metro DC demand.",
        "data_vintage": "2026-04",
    },
    {
        "id": "cheswick_pa",
        "name": "Cheswick Generating Station",
        "operator": "GenOn Energy (retired)",
        "state": "PA",
        "county": "Allegheny County",
        "lat": 40.5500,
        "lon": -79.7933,
        "former_mw": 637,
        "voltage_classes": ["230"],
        "fuel": "coal",
        "retired_date": "2022-04",
        "acreage": 100,
        "evidence_url": "https://www.gem.wiki/Cheswick_power_station",
        "notes": "Small-footprint retired coal within PJM. 230 kV interconnection retained. Candidate for adjacent-ROW DC (<=10 km).",
        "data_vintage": "2026-04",
    },
    {
        "id": "san_juan_nm",
        "name": "San Juan Generating Station",
        "operator": "PNM (retired)",
        "state": "NM",
        "county": "San Juan County",
        "lat": 36.8047,
        "lon": -108.4497,
        "former_mw": 1683,
        "voltage_classes": ["345", "230", "115"],
        "fuel": "coal",
        "retired_date": "2022-09",
        "acreage": 1750,
        "evidence_url": "https://www.gem.wiki/San_Juan_Generating_Station",
        "notes": "Four Corners-region. Retired Sept 2022. 345/230 kV switchyard, adjacent to Four Corners plant. Regional hyperscaler candidate.",
        "data_vintage": "2026-04",
    },
    {
        "id": "dave_johnston_wy",
        "name": "Dave Johnston Power Plant",
        "operator": "PacifiCorp",
        "state": "WY",
        "county": "Converse County",
        "lat": 42.8328,
        "lon": -105.7839,
        "former_mw": 762,
        "voltage_classes": ["230"],
        "fuel": "coal",
        "retired_date": "2028-12",  # announced retirement
        "acreage": 540,
        "evidence_url": "https://www.pacificorp.com/about/newsroom/news-releases.html",
        "notes": "PacifiCorp IRP retirement 2028. 230 kV switchyard. Remote but sits on PacifiCorp backbone.",
        "data_vintage": "2026-04",
    },
]


def get_retired_generation_sites(state=None):
    """Return retired generation sites, optionally filtered by state."""
    if state is None:
        return list(RETIRED_GENERATION_SITES)
    return [s for s in RETIRED_GENERATION_SITES if s.get("state") == state]


# ---------------------------------------------------------------------------
# State industrial retail rate averages (EIA Form 861, 2024 annual, cents/kWh)
# ---------------------------------------------------------------------------
#
# Used by _trigger_high_rate / _p_high_rate to compute state-relative rate
# thresholds. Source: EIA electric-power monthly state-level industrial rate
# averages, 2024 annual. Only states where we currently have coverage are
# seeded; unknown states fall back to the absolute 14 c/kWh floor.
#
# Values are rounded to 0.1 c/kWh. Refresh annually.

STATE_INDUSTRIAL_RATE_AVG_CENTS = {
    "AL": 6.9, "AR": 7.5, "AZ": 7.4, "CA": 19.8, "CO": 8.8,
    "CT": 14.5, "DE": 9.6, "FL": 9.2, "GA": 7.7, "IA": 7.1,
    "ID": 6.9, "IL": 8.9, "IN": 8.9, "KS": 9.2, "KY": 7.4,
    "LA": 7.3, "MA": 16.2, "MD": 9.8, "ME": 12.5, "MI": 9.3,
    "MN": 9.4, "MO": 8.5, "MS": 7.9, "MT": 7.2, "NC": 7.8,
    "ND": 8.3, "NE": 7.9, "NH": 15.1, "NJ": 13.8, "NM": 8.1,
    "NV": 8.2, "NY": 9.2, "OH": 8.2, "OK": 6.7, "OR": 8.7,
    "PA": 8.9, "RI": 15.3, "SC": 7.1, "SD": 8.1, "TN": 7.3,
    "TX": 8.3, "UT": 7.1, "VA": 8.9, "VT": 12.5, "WA": 6.7,
    "WI": 9.2, "WV": 8.8, "WY": 7.1,
}


def get_state_industrial_rate_avg(state):
    """Return the EIA 2024 industrial rate average (cents/kWh) for a state,
    or None if not seeded."""
    if state is None:
        return None
    return STATE_INDUSTRIAL_RATE_AVG_CENTS.get(state.upper())
