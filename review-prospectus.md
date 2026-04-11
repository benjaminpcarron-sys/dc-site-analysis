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

### Step 3: Halcyon Regulatory Research (REQUIRED)
Run three focused Halcyon queries via Chrome DevTools to find actual regulatory filings. This is a mandatory step -- the site analysis tool provides infrastructure data, but the regulatory context (tariffs, capacity outlook, generation plans) is essential for investment decisions.

**Query 1: Large Load Tariff & Interconnection**
Navigate to Halcyon with keywords `[utility name]` + `large load`, filtered by the state PUC commission.
Query: "What are [utility]'s large load tariff provisions, data center interconnection requirements, and relevant docket numbers?"
- Extract: MW thresholds, contract terms, billing minimums, exit fees, collateral requirements
- Extract: Active docket numbers with direct ICC/PUC links

**Query 2: Supply-Demand Balance & Capacity Outlook**
Keywords `[utility]` + `capacity` + `load forecast`, filtered by state PUC.
Query: "What is the expected supply demand balance and capacity outlook for [utility] service territory for [energization year range]?"
- Extract: Peak demand forecasts, generation additions/retirements, resource adequacy concerns
- Extract: Whether the utility owns generation or depends on RTO market
- Extract: MISO/PJM capacity auction results for the relevant zone

**Query 3: Resource Adequacy & Generation Plan**
Keywords `[utility/state]` + `generation` + `resource plan`, filtered by state PUC.
Query: "What did the [most recent] resource adequacy study find about capacity shortfalls in [RTO zone]?"
- Extract: MW surplus/deficit projections for the energization timeframe
- Extract: Historical capacity auction clearing prices (indicates scarcity)
- Extract: Fossil fuel retirement schedules and replacement plans
- Extract: IRP filing status and docket numbers

**For each query:**
1. Navigate to `https://app.halcyon.io/workspaces/preview?keyword=[terms]&keyword_strategy=ALL&publisher=[commission_id]`
2. Click Query tab, type the question, apply suggested filters, click Run
3. Wait ~15 seconds for the AI response
4. Capture the answer text AND the cited document links (ICC/PUC docket URLs)
5. Record document titles, docket numbers, filing dates, and page references

### Step 4: Cross-Reference & Validate
Compare prospectus claims against BOTH the site analysis findings AND the Halcyon regulatory research:

**Power Infrastructure Validation:**
- Does the claimed utility match our service territory data?
- Does the claimed interconnection voltage exist at the stated distance?
- Is the claimed substation in our planned substations database?
- Is the grid adequate for the stated MW target?

**Generation & Capacity Validation (from Halcyon):**
- Does the utility own generation or depend on RTO market?
- What is the capacity surplus/deficit outlook for the energization year?
- Are there capacity shortfall warnings from NERC, MISO, or the state?
- What generation retirements are scheduled in the region?
- Has the zone experienced capacity auction price spikes?

**Rate Validation:**
- How does the claimed rate compare to EIA-861 industrial rates?
- What do the Halcyon filings show about rate trajectory?
- Are rate escalation assumptions reasonable given capacity outlook?

**Cost Validation:**
- How does the $/MW compare to the $8M/MW infrastructure benchmark and $30M/MW all-in benchmark?
- Are there red flags (too cheap = missing costs, too expensive = inflated)?

**Tariff & Regulatory Validation (from Halcyon):**
- Does the utility have a published large load tariff, or does it use bilateral agreements?
- What are the actual MW thresholds, contract terms, and exit fees from the tariff filing?
- Is there a moratorium risk?
- Does the prospectus account for minimum billing, exit fees, collateral?

**Environmental Validation:**
- Nonattainment zone? Flood zone? Justice40? Seismic?

**Zoning Validation:**
- NLCD land cover + OSM landuse tags

**Market Context:**
- Nearby DC projects within 50km
- Interconnection queue for the state

### Step 5: Generate Enhanced Report
Produce a markdown report with these sections:

1. **Prospectus Summary** - Structured extraction of all key claims
2. **Site Analysis** - Full dc-site-analysis output (14 sections)
3. **Validation Matrix** - Side-by-side comparison of claims vs. findings
   | Category | Prospectus Claims | Independent Findings | Status |
   |---|---|---|---|
   | Utility | "Ameren Illinois" | Confirmed (HIFLD service territory) | ✅ |
   | Grid capacity | "sufficient" | 345kV at 10.8km, Boxcar confirms 274 MW | ✅ |
   | Generation | Not addressed | MISO Zone 4 deficit projected 2028-2029 | ⚠️ NOT DISCLOSED |
   | Rate | Not stated | No published tariff; MISO market dependent | ⚠️ MISSING |
4. **Regulatory Research Findings** (Halcyon appendix with docket links)
   - Large load tariff analysis
   - Supply-demand balance & capacity outlook
   - Resource adequacy study findings
5. **Stakeholder Engagement Map** (see Step 4b below)
6. **Red Flags** - Material discrepancies, missing information, unrealistic assumptions
7. **Due Diligence Checklist** - Items requiring further verification
8. **Research Links** - Halcyon deep links + Google for local/environmental

### Step 4b: Stakeholder Engagement Map (REQUIRED)
Build a table of the specific people and organizations relevant to developing this site. Use multiple sources: prospectus documents (often name utility contacts), Halcyon filings (name commissioners, utility witnesses, intervenors), utility/government websites, and Google search.

**For each stakeholder, find: Name, Title, Organization, Contact (email/phone/URL), and Why they matter.**

Research in this order:

**Tier 1: Deal-Critical**
- **Utility Economic Development Rep** — The person who can initiate interconnection studies and rate negotiations. Check: utility website economic development page, prospectus attachments, Google `"[utility]" economic development contact [city]`
- **Utility Transmission Planning** — The engineer who runs system impact studies. Check: named in any Boxcar/interconnection study provided, request from BD rep
- **State PUC Commissioners** — Who votes on tariffs and rate cases. Check: state PUC website commissioners page, names in Halcyon docket orders
- **City/County Economic Development Director** — Enterprise zones, tax incentives, political support. Check: county EDC website, Google `"[county]" economic development director`
- **RTO Interconnection Contact** — MISO/PJM large load intake. Check: RTO website stakeholder contacts page

**Tier 2: Permitting & Approvals**
- **County Planning Director** — Zoning, CUP, site plan. Check: county government website planning department
- **State EPA Air Permit Reviewer** — Backup generator permits. Check: state EPA website, names in Halcyon permit filings
- **City Building Official** — Building permits. Check: city government website

**Tier 3: Infrastructure Partners**
- **Fiber/dark fiber providers** — DC connectivity. Check: Google `"dark fiber" OR "fiber provider" [city] [state]`
- **Water utility** — Cooling water. Check: municipal water department
- **Gas utility** — Generator fuel. Check: gas utility website (may be same as electric utility)

**Tier 4: Political & Community**
- **State legislator (district)** — Legislative support. Check: state legislature website, find by address
- **Mayor / City Manager** — Local political support. Check: city government website
- **County Board Chair** — County approvals. Check: county government website

Format as a table in the report:
```
| Tier | Role | Name | Organization | Contact | Notes |
|------|------|------|-------------|---------|-------|
| 1 | Utility BD | Holly Klausing | Ameren Economic Dev | hklausing@ameren.com / 217-371-4496 | Named in Ameren infrastructure doc |
| 1 | PUC Commissioner | [name] | Illinois Commerce Commission | [URL] | Chair of relevant docket |
```

Sources to mine for names:
1. **The prospectus documents themselves** — developers often include utility contact info
2. **Halcyon query results** — testimony authors, docket participants, order signatories are the decision-makers
3. **Utility website** — economic development / large customer pages
4. **State PUC website** — commissioner bios, staff directory
5. **County/city government websites** — staff directories, department pages
6. **Google** — `"[title]" "[organization]" [city]` for specific roles

### Step 6: Export & Save
- Save markdown to: `/Users/bencarron/Projects/dc-site-analysis/reports/prospectus_[project_name_slug].md`
- Export Word doc: `python3 export_docx.py reports/[file].md -o [output_path]`
- Save Word doc to the relevant client folder (e.g., Weiss Realty)
- Commit and push to GitHub

## Notes
- Always read the full PDF before extracting - don't assume structure
- The Halcyon research step is REQUIRED -- the site analysis tool covers infrastructure and environmental data, but regulatory filings (tariffs, capacity outlook, generation plans) are only available through Halcyon
- Flag financial projections you can't independently verify (IRR, lease rates) as "unverified - requires financial model review"
- If the prospectus references specific permits or filings, search for those docket numbers in Halcyon
- Compare the $/MW to both the infrastructure-only benchmark ($8M/MW) and the all-in benchmark ($30M/MW)
- For Halcyon queries: keep questions focused (one topic per query), use commission filters, and apply date filters when Halcyon suggests them
- If Halcyon flags a "totality query," break it into smaller questions
- Always capture the ICC/PUC docket URLs from Halcyon citations -- these are the primary source documents
