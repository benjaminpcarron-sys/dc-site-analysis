"""
Capture a zoomed-in map screenshot from the DC Site Mapper for a given lat/lon.

Requires:
  - DC Site Mapper running at http://localhost:5173 (docker compose up)
  - Playwright installed: pip install playwright && playwright install chromium

Usage:
  python capture_map.py LAT LON OUTPUT_PATH [--zoom ZOOM]
  python capture_map.py 38.5778 -75.2828 reports/site_map.png --zoom 12.5
"""

import argparse
import sys

def capture_map(lat: float, lon: float, output_path: str, zoom: float = 12.5,
                mapper_url: str = "http://localhost:5173",
                layers=None):
    """Capture a map screenshot with infrastructure layers enabled."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    if layers is None:
        layers = ["Transmission Lines", "Electric Substations", "Electric Service Territories"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(mapper_url, wait_until="networkidle")

        # Wait for the map to render
        page.wait_for_selector(".maplibregl-canvas", timeout=15000)
        page.wait_for_timeout(2000)

        # Fly to coordinates by injecting into React's mapRef
        page.evaluate(f"""() => {{
            const mapDiv = document.querySelector('.maplibregl-map');
            const fiberKey = Object.keys(mapDiv).find(k => k.startsWith('__reactFiber'));
            let fiber = mapDiv[fiberKey];
            let attempts = 0;
            while (fiber && attempts < 100) {{
                if (fiber.memoizedState) {{
                    let hook = fiber.memoizedState;
                    while (hook) {{
                        const val = hook.memoizedState;
                        if (val && typeof val === 'object' && val.current &&
                            typeof val.current.flyTo === 'function' &&
                            typeof val.current.getCenter === 'function') {{
                            val.current.flyTo({{ center: [{lon}, {lat}], zoom: {zoom}, duration: 100 }});
                            return;
                        }}
                        hook = hook.next;
                    }}
                }}
                fiber = fiber.return;
                attempts++;
            }}
        }}""")
        page.wait_for_timeout(1500)

        # Click the Layers tab
        layers_tab = page.get_by_role("tab", name="Layers")
        if layers_tab:
            layers_tab.click()
            page.wait_for_timeout(500)

        # Toggle on requested layers
        for layer_name in layers:
            label = page.locator(f"text={layer_name}")
            if label.count() > 0:
                # Find the adjacent switch and click it
                switch = label.locator("xpath=preceding-sibling::button[@role='switch'] | ../preceding-sibling::*//button[@role='switch']")
                if switch.count() == 0:
                    # Try a different selector pattern
                    parent = label.locator("xpath=..")
                    switch = parent.locator("button[role='switch']")
                if switch.count() > 0:
                    switch.first.click()
                    page.wait_for_timeout(300)

        # Wait for layer data to load
        page.wait_for_timeout(3000)

        # Hide the sidebar for a clean map view
        page.evaluate("""() => {
            const panels = document.querySelectorAll('div');
            for (const p of panels) {
                const rect = p.getBoundingClientRect();
                if (rect.left === 0 && rect.width > 200 && rect.width < 400 && rect.height > 500) {
                    p.style.display = 'none';
                    break;
                }
            }
        }""")
        page.wait_for_timeout(500)

        # Take the screenshot
        page.screenshot(path=output_path, full_page=False)
        browser.close()

    print(f"Map screenshot saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Capture map screenshot from DC Site Mapper")
    parser.add_argument("lat", type=float, help="Latitude")
    parser.add_argument("lon", type=float, help="Longitude")
    parser.add_argument("output", type=str, help="Output file path (PNG)")
    parser.add_argument("--zoom", type=float, default=12.5, help="Map zoom level (default: 12.5)")
    parser.add_argument("--url", type=str, default="http://localhost:5173", help="Mapper URL")
    args = parser.parse_args()

    capture_map(args.lat, args.lon, args.output, zoom=args.zoom, mapper_url=args.url)


if __name__ == "__main__":
    main()
