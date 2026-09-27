"""Walk the real portal (ui/dist) through the demo and capture every state, before and after each
click, as full-page 2x screenshots, plus the page-pixel boxes the camera and cursor aim at.
->  demo_shots/<state>.png  and  demo_shots/boxes.json"""
import json
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = (ROOT / "ui" / "dist" / "index.html").as_uri()
OUT = pathlib.Path(__file__).parent / "demo_shots"
OUT.mkdir(exist_ok=True)
boxes = {}


def box(loc):
    try:
        b = loc.first.bounding_box()
        if b:
            sy = page.evaluate("window.scrollY")
            return {k: round(v + (sy if k == "y" else 0), 1) for k, v in b.items()}
    except Exception as e:
        print("   miss", e)
    return None


def grab(name, parts, full=True):
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(250)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
    b = {k: box(v) for k, v in parts.items()}
    size = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.scrollHeight]")
    boxes[name] = {"size": size, "parts": b}
    print("state", name, size, {k: (v is not None) for k, v in b.items()})


with sync_playwright() as p:
    br = p.chromium.launch(channel="chrome")
    page = br.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2).new_page()
    page.goto(DIST)
    page.evaluate("localStorage.clear()")
    page.goto(DIST + "#dashboard")
    page.reload()
    page.wait_for_timeout(1500)

    # 1 sign in
    grab("login_a", {"reviewer": page.get_by_text("CPSE Reviewer", exact=True)})
    page.get_by_text("CPSE Reviewer", exact=True).click()
    page.wait_for_timeout(500)
    grab("login_b", {"cpcl": page.get_by_role("button", name="CPCL", exact=True)})
    page.get_by_role("button", name="CPCL", exact=True).click()
    page.wait_for_timeout(400)
    grab("login_c", {"signin": page.locator("button", has_text="Sign in as")})
    page.locator("button", has_text="Sign in as").click()
    page.wait_for_timeout(1500)

    # 2 the match
    page.goto(DIST + "#match")
    page.wait_for_timeout(7000)
    grab("match", {"pair": page.locator("div.card", has_text="SKF 6205"),
                   "sim": page.locator("div.card", has_text="Text similarity"),
                   "brand": page.get_by_text("brand never counts", exact=False),
                   "score": page.locator("div.card", has_text="Match score")})

    # 3 the block
    page.goto(DIST + "#block")
    page.wait_for_timeout(7000)
    grab("block", {"sim": page.locator("div.card", has_text="Text similarity"),
                   "veto": page.get_by_text("Veto field", exact=False),
                   "whatif": page.locator("div.card", has_text="What if"),
                   "trap": page.locator("div.card", has_text="threshold trap")})

    # 4 creation gate
    page.goto(DIST + "#gate")
    page.wait_for_timeout(1500)
    grab("gate_a", {"scenario": page.get_by_text("A line that contradicts itself")})
    page.get_by_text("A line that contradicts itself").first.click()
    page.wait_for_timeout(1200)
    grab("gate_b", {"incoming": page.locator("div.card", has_text="incoming description"),
                    "verdict": page.locator("div.card", has_text="Contradicts itself")})

    # 5 review queue
    page.goto(DIST + "#review")
    page.wait_for_timeout(1500)
    grab("review_a", {"record": page.get_by_text("Which of these is this item?"),
                      "keys": page.get_by_text("A — All the same"),
                      "legend": page.get_by_text("this one, not the others").first,
                      "note": page.get_by_text("could not tell", exact=False).first})
    page.keyboard.press("s")          # skip: logs an event, decides nothing
    page.wait_for_timeout(700)

    # 6 real tender text
    page.goto(DIST + "#real")
    page.wait_for_timeout(1500)
    grab("real", {"same": page.locator("div.card", has_text="101.60").first,
                  "same_head": page.get_by_text("One item, written differently"),
                  "diff_head": page.get_by_text("Alike on paper, different items")})

    # 7 dashboard evidence
    page.goto(DIST + "#dashboard")
    page.wait_for_timeout(2500)
    grab("dashboard", {"evidence": page.locator("section", has_text="How we know it is safe")})

    # 8 audit trail
    page.goto(DIST + "#audit")
    page.wait_for_timeout(1500)
    grab("audit_a", {"test": page.get_by_role("button", name="Test the seal")})
    page.get_by_role("button", name="Test the seal").click()
    page.wait_for_timeout(800)
    grab("audit_b", {"test": page.get_by_role("button", name="Test the seal"),
                     "seal": page.locator("div.card", has_text="Seal").first})

    page.evaluate("localStorage.clear()")
    br.close()

(OUT / "boxes.json").write_text(json.dumps(boxes, indent=1))
