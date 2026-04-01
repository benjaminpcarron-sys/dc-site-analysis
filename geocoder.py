"""Geocode addresses via Nominatim with local file cache."""

import json
import os
import urllib.request
import urllib.parse

CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "geocode_cache.json")

# US state abbreviation lookup
STATE_ABBREVS = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}


def _load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def _extract_state_abbrev(nominatim_address, raw_address):
    """Extract 2-letter state abbreviation from Nominatim response or raw address."""
    # Try Nominatim structured address
    state_full = nominatim_address.get("state", "")
    if state_full:
        abbrev = STATE_ABBREVS.get(state_full.lower())
        if abbrev:
            return abbrev
        if len(state_full) == 2 and state_full.upper() in STATE_ABBREVS.values():
            return state_full.upper()

    # Fallback: parse from raw address (look for 2-letter state code)
    import re
    m = re.search(r'\b([A-Z]{2})\b\s*\d{5}', raw_address)
    if m and m.group(1) in STATE_ABBREVS.values():
        return m.group(1)
    m = re.search(r',\s*([A-Z]{2})\b', raw_address)
    if m and m.group(1) in STATE_ABBREVS.values():
        return m.group(1)
    return None


def geocode(address):
    """Geocode an address. Returns dict with lat, lon, state, county, display_name."""
    cache = _load_cache()
    if address in cache:
        return cache[address]

    params = urllib.parse.urlencode({
        "q": address,
        "format": "json",
        "addressdetails": 1,
        "limit": 1,
        "countrycodes": "us",
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "dc-site-analysis/1.0"})

    with urllib.request.urlopen(req, timeout=15) as resp:
        results = json.loads(resp.read())

    if not results:
        raise ValueError(f"Could not geocode address: {address}")

    r = results[0]
    addr = r.get("address", {})
    state = _extract_state_abbrev(addr, address)
    county = addr.get("county", "")

    result = {
        "lat": float(r["lat"]),
        "lon": float(r["lon"]),
        "state": state,
        "county": county,
        "display_name": r.get("display_name", address),
    }

    cache[address] = result
    _save_cache(cache)
    return result
