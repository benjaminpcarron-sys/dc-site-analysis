"""Generate research links for interconnection, permitting, and regulatory filings.

Produces pre-built search URLs pointing analysts to the right portals for:
- FERC eLibrary (federal interconnection filings)
- RTO/ISO interconnection queues (PJM, MISO, ERCOT, SPP, CAISO, NYISO)
- State PUC/PSC docket search (utility rate cases, large load tariffs)
- State environmental agency (air permits, NPDES)
- County/city permit portals (building permits, zoning, CUP)
"""

import urllib.parse

# RTO/ISO queue portals by state
STATE_TO_RTO = {
    "VA": ("PJM", "https://www.pjm.com/planning/service-requests/services-request-status"),
    "MD": ("PJM", "https://www.pjm.com/planning/service-requests/services-request-status"),
    "PA": ("PJM", "https://www.pjm.com/planning/service-requests/services-request-status"),
    "NJ": ("PJM", "https://www.pjm.com/planning/service-requests/services-request-status"),
    "DE": ("PJM", "https://www.pjm.com/planning/service-requests/services-request-status"),
    "OH": ("PJM", "https://www.pjm.com/planning/service-requests/services-request-status"),
    "WV": ("PJM", "https://www.pjm.com/planning/service-requests/services-request-status"),
    "NC": ("PJM/Duke", "https://www.pjm.com/planning/service-requests/services-request-status"),
    "IN": ("MISO", "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/gi-interactive-queue/"),
    "IL": ("MISO/PJM", "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/gi-interactive-queue/"),
    "MI": ("MISO", "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/gi-interactive-queue/"),
    "WI": ("MISO", "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/gi-interactive-queue/"),
    "MN": ("MISO", "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/gi-interactive-queue/"),
    "IA": ("MISO", "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/gi-interactive-queue/"),
    "MO": ("MISO/SPP", "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/gi-interactive-queue/"),
    "AR": ("MISO/SPP", "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/gi-interactive-queue/"),
    "LA": ("MISO", "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/gi-interactive-queue/"),
    "MS": ("MISO", "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/gi-interactive-queue/"),
    "TX": ("ERCOT", "https://www.ercot.com/gridinfo/generation"),
    "OK": ("SPP", "https://opsportal.spp.org/Studies/GenerationInterconnection"),
    "KS": ("SPP", "https://opsportal.spp.org/Studies/GenerationInterconnection"),
    "NE": ("SPP", "https://opsportal.spp.org/Studies/GenerationInterconnection"),
    "ND": ("SPP/MISO", "https://opsportal.spp.org/Studies/GenerationInterconnection"),
    "SD": ("SPP", "https://opsportal.spp.org/Studies/GenerationInterconnection"),
    "CA": ("CAISO", "https://rimspub.caiso.com/rimsui/logon.do"),
    "NY": ("NYISO", "https://www.nyiso.com/interconnection-projects"),
    "GA": ("Southern/SOCO", "https://www.oasis.oati.com/woa/docs/SPC/SPCdocs/SouthernCompaniesLargeLoad.html"),
    "AL": ("Southern/SOCO", "https://www.oasis.oati.com/woa/docs/SPC/SPCdocs/SouthernCompaniesLargeLoad.html"),
    "TN": ("TVA", "https://www.tva.com/energy/transmission-system/transmission-system-projects"),
    "KY": ("TVA/PJM", "https://www.tva.com/energy/transmission-system/transmission-system-projects"),
    "MT": ("NWMT", "https://www.northwesternenergy.com/transmission"),
    "OR": ("BPA", "https://www.bpa.gov/energy-and-services/transmission/interconnection-requests"),
    "WA": ("BPA", "https://www.bpa.gov/energy-and-services/transmission/interconnection-requests"),
    "ID": ("Idaho Power", "https://www.idahopower.com/energy-environment/energy/open-access-transmission-tariff/"),
    "NV": ("NV Energy", "https://www.nvenergy.com/about-nvenergy/rates-regulatory"),
    "AZ": ("AZPS", "https://www.aps.com/en/About/Our-Company/Doing-Business-with-Us/Generation-Interconnection"),
    "CO": ("PSCO/Xcel", "https://www.xcelenergy.com/working_with_us/transmission_interconnection"),
    "NM": ("PNM", "https://www.pnm.com/transmission"),
    "WY": ("WACM", "https://www.wapa.gov/transmission/Pages/interconnection.aspx"),
    "SC": ("Duke", "https://www.duke-energy.com/business/products/interconnection"),
}

# State PUC/PSC search portals
STATE_PUC = {
    "VA": ("Virginia State Corporation Commission", "https://scc.virginia.gov/pages/Case-Information"),
    "TX": ("Public Utility Commission of Texas", "https://interchange.puc.texas.gov/search/filings/"),
    "OH": ("Public Utilities Commission of Ohio", "https://dis.puc.state.oh.us/CaseSearch.aspx"),
    "IL": ("Illinois Commerce Commission", "https://www.icc.illinois.gov/docket/search"),
    "GA": ("Georgia Public Service Commission", "https://psc.ga.gov/search/"),
    "IN": ("Indiana Utility Regulatory Commission", "https://iurc.portal.in.gov/legal-case-search/"),
    "MI": ("Michigan Public Service Commission", "https://mi-psc.force.com/s/global-search"),
    "PA": ("Pennsylvania Public Utility Commission", "https://www.puc.pa.gov/search/document-search/"),
    "NY": ("New York Public Service Commission", "https://documents.dps.ny.gov/public/Common/SearchResults.aspx"),
    "NC": ("North Carolina Utilities Commission", "https://starw1.ncuc.gov/NCUC/page/docket-search/"),
    "NJ": ("New Jersey Board of Public Utilities", "https://publicaccess.bpu.state.nj.us/"),
    "MD": ("Maryland Public Service Commission", "https://www.psc.state.md.us/search-cases/"),
    "WI": ("Public Service Commission of Wisconsin", "https://apps.psc.wi.gov/ERF/ERFsearch/"),
    "MN": ("Minnesota Public Utilities Commission", "https://efiling.web.commerce.state.mn.us/edockets/searchDocuments.do"),
    "LA": ("Louisiana Public Service Commission", "https://lpsc.louisiana.gov/"),
    "MS": ("Mississippi Public Service Commission", "https://www.psc.state.ms.us/"),
    "KS": ("Kansas Corporation Commission", "https://estar.kcc.ks.gov/estar/portal/kscc/page/docket-search/"),
    "MO": ("Missouri Public Service Commission", "https://efis.psc.mo.gov/mpsc/filing_submission/DocketSearch/"),
    "CO": ("Colorado Public Utilities Commission", "https://www.dora.state.co.us/pls/efi/EFI_Search_UI.search"),
    "OR": ("Oregon Public Utility Commission", "https://edockets.puc.state.or.us/"),
    "AZ": ("Arizona Corporation Commission", "https://edocket.azcc.gov/edocket"),
    "MT": ("Montana Public Service Commission", "https://dataportal.mt.gov/t/DOAPSC/views/PSCDashboard/"),
    "AL": ("Alabama Public Service Commission", "https://psc.alabama.gov/"),
    "TN": ("Tennessee Public Utility Commission", "https://tn.gov/tra"),
    "KY": ("Kentucky Public Service Commission", "https://psc.ky.gov/Case/Search"),
    "NV": ("Public Utilities Commission of Nevada", "https://pucn.nv.gov/Dockets/Dockets/"),
    "ID": ("Idaho Public Utilities Commission", "https://puc.idaho.gov/case-search/"),
    "WY": ("Wyoming Public Service Commission", "https://efiling.wyomingpsc.com/"),
}

# State environmental agency permit portals
STATE_ENV = {
    "VA": ("Virginia DEQ", "https://www.deq.virginia.gov/permits"),
    "TX": ("TCEQ", "https://www2.tceq.texas.gov/oce/eer/index.cfm"),
    "OH": ("Ohio EPA", "https://epermits.epa.ohio.gov/"),
    "IL": ("Illinois EPA", "https://external.epa.illinois.gov/EPASearch/"),
    "GA": ("Georgia EPD", "https://epd.georgia.gov/air/permit-search"),
    "IN": ("Indiana DEM", "https://www.in.gov/idem/permits/"),
    "MI": ("Michigan EGLE", "https://www.michigan.gov/egle/about/organization/air-quality/permits"),
    "PA": ("Pennsylvania DEP", "https://www.dep.pa.gov/DataandTools/Reports/Pages/default.aspx"),
    "NY": ("New York DEC", "https://www.dec.ny.gov/permits/6054.html"),
    "NC": ("North Carolina DEQ", "https://deq.nc.gov/permits"),
    "NJ": ("New Jersey DEP", "https://www.nj.gov/dep/online/"),
    "MD": ("Maryland MDE", "https://mde.maryland.gov/programs/Permits/Pages/index.aspx"),
    "WI": ("Wisconsin DNR", "https://dnr.wi.gov/topic/AirPermits/Search.html"),
    "MN": ("Minnesota PCA", "https://www.pca.state.mn.us/air/air-permits"),
    "LA": ("Louisiana DEQ", "https://www.deq.louisiana.gov/page/air-permits"),
    "MS": ("Mississippi DEQ", "https://www.mdeq.ms.gov/permits/"),
    "CA": ("California SCAQMD / BAAQMD", "https://www.aqmd.gov/home/permits"),
    "CO": ("Colorado CDPHE", "https://cdphe.colorado.gov/air-quality-permits"),
    "OR": ("Oregon DEQ", "https://www.oregon.gov/deq/aq/Pages/Permits.aspx"),
    "AZ": ("Arizona DEQ", "https://www.azdeq.gov/permits"),
    "MT": ("Montana DEQ", "https://deq.mt.gov/air/airpermits"),
    "AL": ("Alabama DEM", "https://adem.alabama.gov/programs/air/airPermits.cnt"),
    "TN": ("Tennessee TDEC", "https://www.tn.gov/environment/permits.html"),
    "KY": ("Kentucky DEP", "https://eec.ky.gov/Environmental-Protection/Air/Pages/default.aspx"),
}


def generate_research_links(state, county, utility_name=None, address=None):
    """Generate research links for a site's state/county/utility."""
    links = []

    utility_short = (utility_name or "").split(",")[0].strip()
    county_short = county.replace(" County", "") if county else ""

    # Halcyon deep-linkable search (free, 6M+ regulatory filings)
    # URL pattern: /workspaces/preview?keyword=term1,term2 (comma-separated, "All of" by default)

    def _halcyon_url(*keywords):
        kw = ",".join(k for k in keywords if k)
        return f"https://app.halcyon.io/workspaces/preview?keyword={urllib.parse.quote(kw, safe=',')}"

    # 1. Halcyon: Utility + data center filings
    if utility_short:
        links.append({
            "category": "Regulatory Filings (Halcyon)",
            "name": f"{utility_short} — data center filings",
            "description": "FERC + state PUC dockets, tariff filings, interconnection agreements",
            "url": _halcyon_url(utility_short, "data center"),
        })

    # 2. Halcyon: Utility + large load tariff
    if utility_short:
        links.append({
            "category": "Regulatory Filings (Halcyon)",
            "name": f"{utility_short} — large load tariff",
            "description": "Large load tariff filings, rate schedules, service agreements",
            "url": _halcyon_url(utility_short, "large load"),
        })

    # 3. Halcyon: State + data center + interconnection
    links.append({
        "category": "Regulatory Filings (Halcyon)",
        "name": f"{state} — data center interconnection",
        "description": "Interconnection studies, transmission planning, system impact studies",
        "url": _halcyon_url(state, "data center", "interconnection"),
    })

    # 4. RTO/ISO Queue
    rto_info = STATE_TO_RTO.get(state)
    if rto_info:
        rto_name, _ = rto_info
        rto_q = f'"{rto_name}" interconnection queue "{county_short or state}" data center'
        links.append({
            "category": "Interconnection",
            "name": f"{rto_name} queue / studies",
            "description": f"Interconnection requests and studies in {rto_name}",
            "url": f"https://www.google.com/search?q={urllib.parse.quote(rto_q)}",
        })

    # 5. Halcyon: Air permits / environmental
    links.append({
        "category": "Environmental (Halcyon)",
        "name": f"Air permits + data center ({state})",
        "description": "State EPA air permits, TCEQ filings, environmental reviews for data centers",
        "url": _halcyon_url("air permit", "data center", state),
    })

    # 6. Google backup: State EPA permits (for agencies not in Halcyon)
    env_info = STATE_ENV.get(state)
    if env_info:
        env_name, _ = env_info
        env_q = f'"{env_name}" "{county_short}" "data center" OR "backup generator" permit'
        links.append({
            "category": "Environmental (Google)",
            "name": f"{env_name} permits",
            "description": "Backup: state environmental agency permit search",
            "url": f"https://www.google.com/search?q={urllib.parse.quote(env_q)}",
        })

    # 5. County building permits
    county_name = county.replace(" County", "") if county else ""
    if county_name and state:
        links.append({
            "category": "Local",
            "name": f"{county_name} County Building Permits",
            "description": "Local building permits, conditional use permits, site plans",
            "url": f"https://www.google.com/search?q={urllib.parse.quote(f'{county_name} County {state} building permit data center')}",
        })

    # 6. County zoning / GIS parcel viewer
    if county_name and state:
        links.append({
            "category": "Local",
            "name": f"{county_name} County Zoning / GIS",
            "description": "County zoning maps, land use plans, parcel viewer",
            "url": f"https://www.google.com/search?q={urllib.parse.quote(f'{county_name} County {state} zoning map GIS parcel viewer')}",
        })

    # 7. County planning commission agendas
    if county_name and state:
        links.append({
            "category": "Local",
            "name": f"{county_name} County Planning Commission",
            "description": "Planning commission agendas, CUP applications, public hearings",
            "url": f"https://www.google.com/search?q={urllib.parse.quote(f'{county_name} County {state} planning commission agenda data center')}",
        })

    # 8. State economic development
    if address:
        links.append({
            "category": "Incentives",
            "name": f"{state} Economic Development",
            "description": "State incentive programs, enterprise zones, tax abatement applications",
            "url": f"https://www.google.com/search?q={urllib.parse.quote(f'{state} economic development data center incentive')}",
        })

    return links
