# Data Center Site Pre-Feasibility Report
**Address:** 499 Mitchell St, Millsboro, DE 19966
**Coordinates:** 38.577769 N, -75.282803 W
**State:** DE | **County:** Sussex County
**Report Date:** 2026-04-25
**Target Capacity:** 500 MW

![Site Map](499_mitchell_st_millsboro_de_19966_map.png)
*DC Site Mapper — infrastructure layers for 499 Mitchell St, Millsboro, DE 19966*

---

## Executive Summary
**Overall Site Rating: 3.4 / 5.0 (Moderate)** *(legacy weighted score)*

### Feasibility by Tenant Profile

The same site has materially different economics depending on who is building. Each tier below reflects a real difference in counterparty credit, financial runway, and ability to negotiate around published tariffs. The opportunity number is identical across tiers (it depends on site fundamentals, not the buyer); only the deal-killer probabilities scale by tenant.

| Tenant | Feasibility | Rating | Math |
| --- | --- | --- | --- |
| Speculative | 0.31 | Challenging | Opp 0.69 × (1 − Risk 0.55) |
| Anchored | 0.42 | Moderate | Opp 0.69 × (1 − Risk 0.39) |
| Hyperscaler | 0.50 | Moderate | Opp 0.69 × (1 − Risk 0.28) |

**Who each tier is, in counterparty terms:**

- **Speculative** -- Merchant developer building on spec, no named anchor tenant or investment-grade lease commitment. Constrained by tariff collateral, cannot wait through indefinite interconnection pauses, must close at published industrial rates, cannot finance behind-the-meter generation.
- **Anchored** -- Pre-leased to a named DC operator with investment-grade credit (CoreSite, Equinix, Digital Realty, QTS, etc.). Can absorb deposit requirements, has runway for moderate schedule slips, negotiates rates but at the second tier (not bespoke utility contracts).
- **Hyperscaler** -- Tier-1 hyperscaler (FAANG-tier IG credit) developing for own use. Negotiates around published tariffs via bilateral utility contracts, absorbs deposits via parent guarantees, can finance behind-the-meter generation, plans on horizons that absorb 12-24 month interconnection delays.

**Grid Outlook: Promising** *(tenant-independent)*  
Supply anchors:
  - brownfield: Indian River Power Plant (785 MW former, 230/138 kV) 0.8 km away [direct, fit=1.57] -- switchyard + HV ties repurposable

**Power Path Anchors:** brownfield
  - *brownfield* (see supply anchor above)

*Opportunity boost:* +0.12 opportunity (from supply anchor above).

**Deal-Killers Triggered (1 of 8):**
| Factor | Category | Spec P | Anc P | Hyp P | Evidence |
| --- | --- | --- | --- | --- | --- |
| regulatory_interconnection_pause | regulatory | 0.55 | 0.39 | 0.28 | Delmarva Power: DE PSC 25-0826 active interconnection pause (expected lift 2026-12-31, ~8.2 months out) |

*P(kill) values are seed estimates; see `scoring.py` and `docs/screen_methodology/p_values_audit.md`.*

 Utility service territory: **DELMARVA POWER** (EXELON).

## 1. Power Infrastructure

### Transmission Lines (within 30 km)
| Class | Voltage | Dist (km) | Owner | Substations |
| --- | --- | --- | --- | --- |
| 220-287 | 230 kV | 3.6 | DELMARVA POWER | UNKNOWN128221 - UNKNOWN128222 |
| 100-161 | 138 kV | 2.5 | DELMARVA POWER | UNKNOWN128223 - WHARTON |
| UNDER 100 | 69 kV | 15.0 | DELMARVA POWER | PEPPER - TAP170955 |
| NOT AVAILABLE | NOT AVAILABLE | 1.2 | DELMARVA POWER | UNKNOWN157408 - RISER170959 |

### Substations (within 30 km)
_No data available._

### Grid Adequacy Assessment
- **Grid Outlook (qualitative):** Promising
  *promising outlook: brownfield: Indian River Power Plant (785 MW former, 230/138 kV) 0.8 km away [direct, fit=1.57] -- switchyard + HV ties repurposable*
- **Rough HV-line capacity proxy:** 200 MW
  *Voltage-class heuristic only (nearest line kV × typical feeder multiplier); not a host-utility capacity study. Scoring uses the qualitative outlook above, not this number.*
- **Upgrade Required (heuristic):** Yes
- **Confidence (HV proximity):** medium
- **Scorecard Grid Access:** [+++++] (5/5) -- derived from grid_outlook + HV proximity (not from the HV-line MW proxy above).

### Planned Grid Buildout (within 150 km)
Substations with planned upgrades or new construction:

| Substation | Current | Planned Project | Target kV | Type | Dist (km) |
| --- | --- | --- | --- | --- | --- |
| Milford | 230.00 kV | Rebuild Cartanza- Milford 230 kV Line, Rebuild Mil | 230 kV | Existing | 35 |
| Steele | 230.00 kV | Reconductor Keeney to Steele 230 kV, Rebuild Milfo | 230 kV | Existing | 58 |
| Cartanza | 230.00 kV | Rebuild Cartanza- Mil 230 kV Line | 230 kV | Existing | 71 |
| BL England | New | Ocean Wind BL England to Oyster Creek | 275 kV | Existing | 97 |
| Hope Creek | 500.00 kV | Upgrade Silver Run - Hope Creek 230 kV Line | 230 kV | Existing | 101 |
| Silver Run | New | Upgrade Silver Run - Hope Creek 230 kV Line | 230 kV | Existing | 102 |
| Cardiff | 230.00 kV | Rebuild Cardiff - New Freedom 230 kV | 230 kV | Existing | 110 |
| Keeney | 500.00 kV | Reconductor Keeney to Steele 230 kV | 230 kV | Existing | 124 |
| Riverside (230kV) | 230.00 kV | Reconductor Batavia - Riverside 230 kV Line | 230 kV | Existing | 129 |
| Edgemoor | 230.00 kV | Rebuild Edge Moor - Linwood 230 kV | 230 kV | Existing | 131 |


## 2. Utility & Rates
- **Utility:** DELMARVA POWER
- **Control Area / ISO:** PJM
- **Holding Company:** EXELON
- **Customers Served:** 320,000
- **Industrial Rate:** Not available

## 3. DC Tariff Provisions
_No DC-specific tariff identified for this state (DE)._

## 4. State Tax Incentives (DE)
- **Sales Tax Exemption:** Yes
- **Property Tax Abatement:** No
- **Income Tax Credit:** No
- **Investment Threshold:** $NoneM
- **Job Requirement:** None
- **Duration:** None years
- **Summary:** No state sales tax (de facto exemption on DC equipment). No state-level DC-specific program; property tax abatements are negotiated at county level (Sussex/Kent). New Castle County DC activity limited.

## 5. Land Use & Zoning

### Land Cover: **Developed, Medium Intensity** (NLCD 23)
- Good -- developed area, medium intensity. May be zoned commercial or mixed-use.

### OSM Zoning: **Industrial**
- OpenStreetMap confirms industrial/commercial land use at or near this location.

## 6. Environmental & Regulatory Risk

### Air Quality: **Attainment Zone**
Site is not in any EPA nonattainment area. Standard air permitting applies for backup generators.

### Flood Zone: Data not available
FEMA NFHL query returned no results for this location.

### Environmental Justice: **Disadvantaged Community (Justice40)**
Site is in a federally designated disadvantaged community. Regulatory agencies may require additional EJ analysis and community engagement.
- CEJST disadvantaged tract overlap (categories not specified). Federal-nexus projects here may face expanded community-engagement obligations under the prevailing environmental-justice executive order framework; timelines are weakly correlated with NEPA EIS duration based on 2022-2025 cohort.
- **Census Tract:** 10005050602
- **Diesel PM Percentile:** 0.76
- **PM2.5 Percentile:** 0.13
- **Low Income Percentile:** 0.46
- **Housing Burden Percentile:** 0.74

### Seismic Hazard: **SDC A** (Low)
- **Peak Ground Acceleration:** 0.063g
- **Ss (short-period):** 0.12g | **S1 (1-sec):** 0.036g
- Standard construction practices adequate.

### Climate & Land Cost
- **Cooling Degree Days:** 1,117 (Moderate)
- **Avg Farmland Value:** $10,500/acre (USDA state average; DC-zoned land typically 3-10x)
- **Est. Land Cost (150 acres at ~5x farmland):** $8M

## 7. Gas Infrastructure
_No gas pipelines found within 50 km._

## 8. Water Resources
_No water facilities found within 30 km._

*Water facility proximity is a civic-infrastructure proxy -- HIFLD does not expose facility capacity. Process-water availability at DC scale (tens of MGD) requires a separate allocation/discharge study.*

## 9. Transportation Access
_No interstate/US highways found within 30 km._

## 10. Telecommunications
_No fiber routes found within 30 km._

## 11. Interconnection Queue (DE)
_No interconnection queue data available._

## 12. Nearby Data Center Activity (within 50 km)
_No data center projects found within 50 km._

## 13. Research Links
Pre-built search links for deeper due diligence:


**Regulatory Filings (Halcyon):**
- [DELMARVA POWER — data center filings](https://app.halcyon.io/workspaces/preview?keyword=DELMARVA%20POWER,data%20center) -- FERC + state PUC dockets, tariff filings, interconnection agreements
- [DELMARVA POWER — large load tariff](https://app.halcyon.io/workspaces/preview?keyword=DELMARVA%20POWER,large%20load) -- Large load tariff filings, rate schedules, service agreements
- [DE — data center interconnection](https://app.halcyon.io/workspaces/preview?keyword=DE,data%20center,interconnection) -- Interconnection studies, transmission planning, system impact studies

**Interconnection:**
- [PJM queue / studies](https://www.google.com/search?q=%22PJM%22%20interconnection%20queue%20%22Sussex%22%20data%20center) -- Interconnection requests and studies in PJM

**Environmental (Halcyon):**
- [Air permits + data center (DE)](https://app.halcyon.io/workspaces/preview?keyword=air%20permit,data%20center,DE) -- State EPA air permits, TCEQ filings, environmental reviews for data centers

**Local:**
- [Sussex County Building Permits](https://www.google.com/search?q=Sussex%20County%20DE%20building%20permit%20data%20center) -- Local building permits, conditional use permits, site plans
- [Sussex County Zoning / GIS](https://www.google.com/search?q=Sussex%20County%20DE%20zoning%20map%20GIS%20parcel%20viewer) -- County zoning maps, land use plans, parcel viewer
- [Sussex County Planning Commission](https://www.google.com/search?q=Sussex%20County%20DE%20planning%20commission%20agenda%20data%20center) -- Planning commission agendas, CUP applications, public hearings

**Incentives:**
- [DE Economic Development](https://www.google.com/search?q=DE%20economic%20development%20data%20center%20incentive) -- State incentive programs, enterprise zones, tax abatement applications

## 14. Site Suitability Score
| Factor | Score | Value | Weight |
| --- | --- | --- | --- |
| Grid Access | [+++++] | 5/5 | 20% |
| Utility Rate | [+++--] | 3/5 | 15% |
| Environmental | [++++-] | 4/5 | 15% |
| Fiber/Telecom | [++---] | 2/5 | 10% |
| Water | [++---] | 2/5 | 5% |
| Transportation | [++---] | 2/5 | 5% |
| Tax Incentives | [+++--] | 3/5 | 15% |
| DC Tariff Risk | [+++--] | 3/5 | 15% |


**Weighted Total: 3.4 / 5.0**

---
*Generated by dc-site-analysis. Data sources: HIFLD, NTAD, EPA, OSM, EIA-861, demand_ledger.*