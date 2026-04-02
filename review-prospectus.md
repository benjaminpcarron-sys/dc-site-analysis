# Review DC Investment Prospectus

Review a data center investment prospectus PDF against the dc-site-analysis tool. Extract key claims, validate against public infrastructure data, and produce an enhanced feasibility report.

## Input
The user provides a path to a PDF file (investment memo, prospectus, pitch deck, or project summary for a data center development).

## Process

### Step 1: Extract Key Information from the Prospectus
Read the PDF and extract these fields into a structured summary. For each field note the exact quote/page where found, and flag if not mentioned:

**Project Identity:**
- Project name / SPV name
- Developer / sponsor
- Location (address, city, county, state)
- Site acreage

**Technical Specs:**
- Target IT capacity (MW)
- Total facility power (MW) including cooling
- PUE target
- Number of phases / buildings
- Cooling technology (air, liquid, hybrid)
- Backup power (generators, fuel type, N+1 redundancy)

**Power & Grid:**
- Serving utility
- Interconnection voltage and substation
- Interconnection timeline / status
- Power rate ($/kWh or $/MWh) - contracted or assumed
- PPA details (if any)
- Behind-the-meter generation (if any)

**Financial:**
- Total project cost / capex
- Cost per MW (calculate if not stated)
- Target IRR / cash yield
- Debt/equity structure
- Off-taker / anchor tenant (if disclosed)
- Lease terms / contract duration

**Permitting & Timeline:**
- Zoning status (approved, pending, needed)
- Air permit status
- Building permit status
- Environmental review status
- Construction start date
- Target COD (commercial operation date)
- Phase delivery schedule

**Risk Factors:**
- Identified risks in the document
- Utility rate escalation assumptions
- Interconnection delay risks
- Community opposition mentioned
- Environmental constraints mentioned

### Step 2: Run Site Analysis
Using the extracted address (or best available location), run the dc-site-analysis tool:
```bash
cd /Users/bencarron/Projects/dc-site-analysis
python3 dc_site_report.py "EXTRACTED_ADDRESS" --target-mw EXTRACTED_MW
```

### Step 3: Cross-Reference & Validate
Compare prospectus claims against the site analysis findings. For each category, produce a validation assessment:

**Power Infrastructure Validation:**
- Does the claimed utility match our service territory data?
- Does the claimed interconnection voltage exist at the stated distance?
- Is the claimed substation in our planned substations database?
- Is the grid adequate for the stated MW target?

**Rate Validation:**
- How does the claimed rate compare to EIA-861 industrial rates for the area?
- Are rate escalation assumptions reasonable?

**Cost Validation:**
- How does the $/MW compare to the $8M/MW infrastructure benchmark and $30M/MW all-in benchmark from the database?
- Are there red flags (too cheap = missing costs, too expensive = inflated)?

**Environmental Validation:**
- Is the site in a nonattainment zone? (affects generator permitting timeline)
- Is it in a flood zone? (affects insurance and construction costs)
- Is it in a Justice40 community? (affects community engagement requirements)
- What's the seismic design category? (affects structural costs)

**Zoning Validation:**
- What does NLCD show for current land cover?
- Does OSM confirm industrial/commercial zoning?
- If prospectus says "zoned industrial" but NLCD shows cropland, flag the discrepancy timeline

**Tariff Risk:**
- What tariff provisions apply in this state/utility?
- Does the prospectus account for minimum billing, exit fees, collateral?
- Is there a moratorium risk?

**Market Context:**
- How many other DC projects are within 50km?
- Is this an established DC market or greenfield?
- What's in the interconnection queue for this state?

### Step 4: Generate Enhanced Report
Produce a markdown report with these sections:

1. **Prospectus Summary** - Structured extraction of all key claims
2. **Site Analysis** - Full dc-site-analysis output
3. **Validation Matrix** - Side-by-side comparison of claims vs. findings
   | Category | Prospectus Claims | Independent Findings | Status |
   |---|---|---|---|
   | Utility | "Ameren Illinois" | AEP Ohio (service territory) | ⚠️ MISMATCH |
   | Rate | "$0.045/kWh" | $0.067/kWh (EIA-861) | ⚠️ BELOW MARKET |
   | Grid | "345kV at site" | 345kV at 10.8km | ✅ CONFIRMED |

4. **Red Flags** - Material discrepancies, missing information, or unrealistic assumptions
5. **Due Diligence Checklist** - Items requiring further verification
6. **Research Links** - Pre-built URLs for FERC, state PUC, county permits, etc.

### Step 5: Save
Save the enhanced report to:
- `/Users/bencarron/Projects/dc-site-analysis/reports/prospectus_[project_name_slug].md`

## Notes
- Always read the full PDF before extracting - don't assume structure
- Flag financial projections you can't independently verify (IRR, lease rates) as "unverified - requires financial model review"
- If the prospectus references specific permits or filings, include those document numbers in the research links section
- Compare the $/MW to both the infrastructure-only benchmark ($8M/MW) and the all-in benchmark ($30M/MW) from the data_centers.csv analysis
- If multiple sites are mentioned, run the analysis for each
