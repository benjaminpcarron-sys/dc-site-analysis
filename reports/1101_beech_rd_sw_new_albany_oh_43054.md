# Data Center Site Pre-Feasibility Report
**Address:** 1101 Beech Rd SW, New Albany, OH 43054
**Coordinates:** 40.070051 N, -82.754042 W
**State:** OH | **County:** Licking County
**Report Date:** 2026-04-21
**Target Capacity:** 500 MW
**Tenant Profile:** hyperscaler *(scales deal-killer probabilities; see scoring.py)*

![Site Map](1101_beech_rd_sw_new_albany_oh_43054_map.png)
*DC Site Mapper — infrastructure layers for 1101 Beech Rd SW, New Albany, OH 43054*

---

## Executive Summary
**Overall Site Rating: 2.4 / 5.0 (Challenging)** *(legacy weighted score)*

**Risk-Adjusted Feasibility: 0.47 / 1.00 (Moderate)**  
Opportunity 0.59 × (1 − Combined Risk 0.20) = 0.47  *(tenant: hyperscaler)*

*Cluster signal active:* 28 existing DC projects within 50 km (utility has demonstrated build-out for this market). Opportunity boosted by +12 pts and grid-severity killer suppressed when HV line is proximate.

**Deal-Killers Triggered (3 of 10):**
| Factor | Category | P(kill) | Evidence |
| --- | --- | --- | --- |
| onerous_tariff_deposit | tariff | 0.04 | AEP Ohio Schedule DCT: onerous deposit/collateral requirement |
| marginal_nonattainment | environmental | 0.12 | EPA Ozone (8-hr, 2015) nonattainment (Marginal) |
| justice40_disadvantaged | regulatory | 0.05 | Justice40 disadvantaged community (NEPA/EJ scrutiny) |


*P(kill) values are seed estimates; see `scoring.py` for calibration hooks.*

Highest voltage line: 765.0 kV (735 AND ABOVE) at 20.9 km, owned by NOT AVAILABLE. Estimated grid capacity without major upgrades: ~0 MW. Connecting substations: UNKNOWN151647 to CORRIDOR. Target of 500.0 MW exceeds estimated capacity by 500.0 MW -- significant grid upgrades will be required.
 Utility service territory: **LICKING RURAL ELECTRIC INC** (LICKING RURAL ELECTRIC INC).
 Note: AEP Ohio tariff has onerous deposit requirements.

## 1. Power Infrastructure

### Transmission Lines (within 30 km)
| Class | Voltage | Dist (km) | Owner | Substations |
| --- | --- | --- | --- | --- |
| 735 AND ABOVE | 765 kV | 20.9 |  | UNKNOWN151647 - CORRIDOR |
| 345 | 345 kV | 1.4 | AMERICAN ELECTRIC POWER CO., INC | JUG STREET - UNKNOWN177284 |
| 100-161 | 138 kV | 7.2 |  | CORRIDOR - GAHANNA SUBSTATION |
| UNDER 100 | 69 kV | 14.5 | OHIO POWER CO | KIRK - TAP171396 |
| NOT AVAILABLE | NOT AVAILABLE | 0.2 |  | UNKNOWN177284 - UNKNOWN177371 |

### Substations (within 30 km)
| Name | Type | Dist (km) | Max Voltage |
| --- | --- | --- | --- |
| Corridor | Existing | 9.8 | 345.00 kV |
| Bixby | Existing | 25.4 | 345.00 kV |

### Grid Adequacy Assessment
- **Estimated Capacity:** N/A MW
- **Upgrade Required:** Yes
- **Confidence:** low
- **Score:** [+----] (1/5)

### Planned Grid Buildout (within 150 km)
Substations with planned upgrades or new construction:

| Substation | Current | Planned Project | Target kV | Type | Dist (km) |
| --- | --- | --- | --- | --- | --- |
| Corridor | 345.00 kV | Conesville - Corridor 345 kV | 345 kV | Existing | 10 |
| Bixby | 345.00 kV | Rebuild Conesville - Bixby 345 kV | 345 kV | Existing | 25 |
| Hyatt | 345.00 kV | Rebuild Hyatt - Marysville 345 kV | 345 kV | Existing | 33 |
| Ohio Central | 345.00 kV | Rebuild Conesville - Bixby 345 kV | 345 kV | Existing | 63 |
| Marysville | 765.00 kV | Rebuild Hyatt - Marysville 345 kV | 345 kV | Existing | 64 |
| Conesville Station | 345.00 kV | Rebuild Conesville - Bixby 345 kV, Conesville - Co | 345 kV | Existing | 76 |
| Sporn | 345.00 kV | Sporn - Mercers Bottom 345 kV Line | 345 kV | Existing | 142 |


## 2. Utility & Rates
- **Utility:** LICKING RURAL ELECTRIC INC
- **Control Area / ISO:** PJM
- **Holding Company:** LICKING RURAL ELECTRIC INC
- **Customers Served:** 27,116
- **Industrial Rate:** Not available

## 3. DC Tariff Provisions
### AEP Ohio -- Schedule DCT
- **Type:** dc_specific
- **Status:** effective
- **Min Demand:** 25 MW
- **Contract Term:** 12 years
- **Min Billing:** 85%
- **Collateral:** 50% of total minimum charges for full term if credit below A-/A3. Load study fees: 25-50MW $10K, 50-100MW $50K, 100+MW $100K.
- **Exit Fees:** 3 years of minimum charges; available only after year 5 post-ramp
- **Deposit Onerous:** Yes
- **Notes:** PUCO approved Jul 9, 2025. Prior moratorium (Mar 2023 - Jul 2025) now lifted. Ramp: Yr1 50%, Yr2 65%, Yr3 80%, Yr4 90%.


## 4. State Tax Incentives (OH)
- **Sales Tax Exemption:** Yes
- **Property Tax Abatement:** Yes
- **Income Tax Credit:** Yes
- **Investment Threshold:** $100M
- **Job Requirement:** 20
- **Duration:** 15 years
- **Summary:** Sales tax exemption on DC equipment (>$100M). Property tax exemption via CRA. Job creation tax credit.

## 5. Land Use & Zoning

### Land Cover: **Cultivated Crops** (NLCD 82)
- Greenfield -- undeveloped land. Will require rezoning to industrial/commercial. Check county zoning map.

### OSM Zoning: **Industrial**
- Nearby: Meta New Albany Data Center
- OpenStreetMap confirms industrial/commercial land use at or near this location.

## 6. Environmental & Regulatory Risk

### Air Quality NonAttainment Zones
**WARNING: Site is in one or more EPA nonattainment areas.**
Backup generators and cooling systems may require stricter permitting (BACT/LAER, emission offsets).

| Pollutant | Area | Classification | Status |
| --- | --- | --- | --- |
| Ozone (8-hr, 2015) | Columbus | Marginal | Maintenance |

### Flood Zone: Data not available
FEMA NFHL query returned no results for this location.

### Environmental Justice: **Disadvantaged Community (Justice40)**
Site is in a federally designated disadvantaged community. Regulatory agencies may require additional EJ analysis and community engagement.
- **Census Tract:** 39089755600
- **Diesel PM Percentile:** 0.58
- **PM2.5 Percentile:** 0.66
- **Low Income Percentile:** 0.12
- **Housing Burden Percentile:** 0.22

### Seismic Hazard: **SDC B** (Low)
- **Peak Ground Acceleration:** 0.080g
- **Ss (short-period):** 0.15g | **S1 (1-sec):** 0.065g
- Standard construction practices adequate.

### Climate & Land Cost
- **Cooling Degree Days:** 865 (Good)
- **Avg Farmland Value:** $8,400/acre (USDA state average; DC-zoned land typically 3-10x)
- **Est. Land Cost (150 acres at ~5x farmland):** $6M

## 7. Gas Infrastructure
_No gas pipelines found within 50 km._

## 8. Water Resources
_No water facilities found within 30 km._

## 9. Transportation Access
_No interstate/US highways found within 30 km._

## 10. Telecommunications
_No fiber routes found within 30 km._

## 11. Interconnection Queue (OH)
| Technology | Stage | Projects | Total MW |
| --- | --- | --- | --- |
| nuclear | under_construction | 4 | 2,768 |
| nuclear | contracted | 3 | 2,677 |
| gas_cc | progressing | 5 | 2,252 |
| gas_ct | progressing | 2 | 841 |
| solar | early_development | 2 | 713 |
| gas_cc | speculative | 1 | 692 |
| gas_ct | contracted | 1 | 649 |
| gas_ct | speculative | 1 | 521 |
| gas_cc | early_development | 1 | 442 |
| wind | under_construction | 2 | 433 |


## 12. Nearby Data Center Activity (within 50 km)
| Project | Owner | MW | Utility | Dist (km) |
| --- | --- | --- | --- | --- |
| Meta Prometheus | Meta #confident | 614 | Williams,American Electri | 0.4 |
| SIDECAT LLC (0145000554) | SIDECAT LLC (0145000 | TBD |  | 0.4 |
| MONTAUK INNOVATIONS LLC | MONTAUK INNOVATIONS  | TBD |  | 0.5 |
| AWS New Albany OH | Amazon #confident | 975 | AEP Ohio | 1.1 |
| Google New Albany | Google Cloud #confid | 543 |  | 1.3 |
| CMH050 (0145000544) | CMH050 (0145000544) | TBD |  | 1.7 |
| MONTAUK INNOVATIONS LLC (0145000570) | MONTAUK INNOVATIONS  | TBD |  | 2.2 |
| CMH082 CAMPUS (0145000606) | CMH082 CAMPUS (01450 | TBD |  | 3.1 |
| QTS NEW ALBANY I, LLC (0145000602) | QTS NEW ALBANY I, LL | TBD |  | 4.1 |
| QTS NEW ALBANY I, LLC (0145000603) | QTS NEW ALBANY I, LL | TBD |  | 4.1 |
| SIDECAT LLC | SIDECAT LLC | TBD |  | 4.1 |
| CMH070 CAMPUS (0145000591) | CMH070 CAMPUS (01450 | TBD |  | 12.9 |
| COLOGIX (0125044494) | COLOGIX (0125044494) | TBD |  | 21.6 |
| COLOGIX (0125043211) | COLOGIX (0125043211) | TBD |  | 21.8 |
| MAGELLAN ENTERPRISES LLC (0125044418) | MAGELLAN ENTERPRISES | TBD |  | 31.1 |


**28 facilities** totaling **2,132 MW** within 50 km.

## 13. Research Links
Pre-built search links for deeper due diligence:


**Regulatory Filings (Halcyon):**
- [OHIO POWER CO — data center filings](https://app.halcyon.io/workspaces/preview?keyword=OHIO%20POWER%20CO,data%20center) -- FERC + state PUC dockets, tariff filings, interconnection agreements
- [OHIO POWER CO — large load tariff](https://app.halcyon.io/workspaces/preview?keyword=OHIO%20POWER%20CO,large%20load) -- Large load tariff filings, rate schedules, service agreements
- [OH — data center interconnection](https://app.halcyon.io/workspaces/preview?keyword=OH,data%20center,interconnection) -- Interconnection studies, transmission planning, system impact studies

**Interconnection:**
- [PJM queue / studies](https://www.google.com/search?q=%22PJM%22%20interconnection%20queue%20%22Licking%22%20data%20center) -- Interconnection requests and studies in PJM

**Environmental (Halcyon):**
- [Air permits + data center (OH)](https://app.halcyon.io/workspaces/preview?keyword=air%20permit,data%20center,OH) -- State EPA air permits, TCEQ filings, environmental reviews for data centers

**Environmental (Google):**
- [Ohio EPA permits](https://www.google.com/search?q=%22Ohio%20EPA%22%20%22Licking%22%20%22data%20center%22%20OR%20%22backup%20generator%22%20permit) -- Backup: state environmental agency permit search

**Local:**
- [Licking County Building Permits](https://www.google.com/search?q=Licking%20County%20OH%20building%20permit%20data%20center) -- Local building permits, conditional use permits, site plans
- [Licking County Zoning / GIS](https://www.google.com/search?q=Licking%20County%20OH%20zoning%20map%20GIS%20parcel%20viewer) -- County zoning maps, land use plans, parcel viewer
- [Licking County Planning Commission](https://www.google.com/search?q=Licking%20County%20OH%20planning%20commission%20agenda%20data%20center) -- Planning commission agendas, CUP applications, public hearings

**Incentives:**
- [OH Economic Development](https://www.google.com/search?q=OH%20economic%20development%20data%20center%20incentive) -- State incentive programs, enterprise zones, tax abatement applications

## 14. Site Suitability Score
| Factor | Score | Value | Weight |
| --- | --- | --- | --- |
| Grid Access | [+----] | 1/5 | 20% |
| Utility Rate | [+++--] | 3/5 | 15% |
| Environmental | [+++--] | 3/5 | 15% |
| Fiber/Telecom | [++---] | 2/5 | 10% |
| Water | [++---] | 2/5 | 5% |
| Transportation | [++---] | 2/5 | 5% |
| Tax Incentives | [++++-] | 4/5 | 15% |
| DC Tariff Risk | [++---] | 2/5 | 15% |


**Weighted Total: 2.4 / 5.0**

---
*Generated by dc-site-analysis. Data sources: HIFLD, NTAD, EPA, OSM, EIA-861, demand_ledger.*