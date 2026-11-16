"""Screenshot the docs demo after seed 7 finishes, for the README.

Needs Playwright and Chromium:

    python scripts/gen_demo_screenshot.py
"""

from __future__ import annotations

import json
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMO = ROOT / "docs" / "demo"
OUT = ROOT / "docs" / "demo.png"
SEED = 7

src = (DEMO / "streams.js").read_text(encoding="utf-8")
streams = json.loads(src[src.index("=") + 1 :].strip().rstrip(";"))["streams"]
duration = next(s["duration_ms"] for s in streams if s["seed"] == SEED)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=1, color_scheme="light")
    page.clock.install(time=0)
    page.clock.pause_at(1)
    page.goto((DEMO / "index.html").as_uri())
    page.select_option("#seed", str(SEED))
    page.click("#play")
    page.clock.run_for(round(duration) + 1600)
    page.locator("main").screenshot(path=str(OUT))
    browser.close()

print(f"wrote {OUT.relative_to(ROOT)}")
