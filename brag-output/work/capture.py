"""Capture real portal screens (ui/dist) at 1920x1080, 2x, plus the boxes of the parts the video zooms into."""
import json, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = (ROOT / "ui" / "dist" / "index.html").as_uri()
OUT = pathlib.Path(__file__).parent / "shots"
boxes = {}

def sign_in(page, role, org=None):
    page.goto(DIST); page.evaluate("localStorage.clear()")
    page.goto(DIST + "#dashboard"); page.reload(); page.wait_for_timeout(1200)
    page.get_by_text(role, exact=True).click()
    if org: page.get_by_role("button", name=org, exact=True).click()
    page.locator("button", has_text="Sign in as").click(); page.wait_for_timeout(1200)

def grab(page, name, parts):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
    b = {}
    for key, loc in parts.items():
        try:
            bb = loc.first.bounding_box()
            if bb: b[key] = bb
        except Exception as e:
            print("miss", name, key, e)
    size = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.scrollHeight]")
    boxes[name] = {"size": size, "parts": b}
    print("shot", name, size, list(b))

with sync_playwright() as p:
    br = p.chromium.launch(channel="chrome")
    page = br.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2).new_page()
    sign_in(page, "CPSE Reviewer", "CPCL")
    page.goto(DIST + "#match"); page.wait_for_timeout(6500)
    grab(page, "match", {"sim": page.locator("div.card", has_text="Text similarity"),
                          "specs": page.get_by_text("Extracted specifications"),
                          "main": page.locator("#main")})
    page.goto(DIST + "#block"); page.wait_for_timeout(6500)
    grab(page, "block", {"sim": page.locator("div.card", has_text="Text similarity"),
                          "specs": page.get_by_text("Extracted specifications"),
                          "whatif": page.locator("div.card", has_text="What if"),
                          "main": page.locator("#main")})
    page.goto(DIST + "#gate"); page.wait_for_timeout(1200)
    page.get_by_text("A line that contradicts itself").first.click(); page.wait_for_timeout(1000)
    grab(page, "gate", {"incoming": page.locator("div.card", has_text="incoming description"),
                         "verdict": page.locator("div.card", has_text="Contradicts itself"),
                         "main": page.locator("#main")})
    sign_in(page, "Ministry Viewer")
    page.goto(DIST + "#dashboard"); page.wait_for_timeout(2500)
    grab(page, "dashboard", {"evidence": page.locator("section", has_text="How we know it is safe"),
                              "main": page.locator("#main")})
    page.evaluate("localStorage.clear()")
    br.close()
(OUT / "boxes.json").write_text(json.dumps(boxes, indent=1))
