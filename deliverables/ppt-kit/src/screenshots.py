"""
Portal screenshots for the PPT, at 2x, cropped to the part a slide needs.

    cd ui && npm run build        (first)
    python deliverables/ppt-kit/src/screenshots.py
"""

import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[3]
DIST = (ROOT / "ui" / "dist" / "index.html").as_uri()
OUT = ROOT / "deliverables" / "ppt-kit" / "images"


def sign_in(page, role, org=None):
    page.goto(DIST)
    page.evaluate("localStorage.clear()")
    page.goto(DIST + "#dashboard")
    page.reload()
    page.wait_for_timeout(1200)
    page.get_by_text(role, exact=True).click()
    if org:
        page.get_by_role("button", name=org, exact=True).click()
    page.locator("button", has_text="Sign in as").click()
    page.wait_for_timeout(1200)


def column(page, anchor, top, bottom, pad=14):
    """Clip from the left edge of the page's content column (found from a
    card that spans it) to the right edge of the main area."""
    left = anchor.bounding_box()
    right = page.locator("#main").bounding_box()
    x = left["x"] - pad
    return {"x": x, "y": top - pad, "width": min(left["width"] + 2 * pad, right["x"] + right["width"] - x - 8),
            "height": bottom - top + 2 * pad}


def shot(page, name, locator, pad=12):
    box = locator.bounding_box()
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True,
                    clip={"x": box["x"] - pad, "y": box["y"] - pad, "width": box["width"] + 2 * pad,
                          "height": box["height"] + 2 * pad})
    print("wrote", name)


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    page = b.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=2).new_page()

    sign_in(page, "Ministry Viewer")
    page.goto(DIST + "#dashboard")
    page.wait_for_timeout(2500)
    shot(page, "screen-evidence-panel", page.locator("section", has_text="How we know it is safe").first)

    page.goto(DIST + "#real")
    page.wait_for_timeout(1500)
    shot(page, "screen-real-text", page.locator("div.card", has_text="101.60").first)

    sign_in(page, "CPSE Reviewer", "CPCL")
    page.goto(DIST + "#block")
    page.wait_for_timeout(6500)
    card = page.locator("div.card", has_text="Text similarity").first
    top = page.get_by_text("Extracted specifications").first.bounding_box()
    end = page.locator("div.card", has_text="What if").first.bounding_box()
    page.screenshot(path=str(OUT / "screen-block-whatif.png"), full_page=True,
                    clip=column(page, card, top["y"], end["y"] + end["height"]))
    print("wrote screen-block-whatif")

    page.goto(DIST + "#gate")
    page.wait_for_timeout(1200)
    page.get_by_text("A line that contradicts itself").first.click()
    page.wait_for_timeout(1000)
    card = page.locator("div.card", has_text="incoming description").first
    top = card.bounding_box()
    end = page.locator("div.card", has_text="Contradicts itself").first.bounding_box()
    page.screenshot(path=str(OUT / "screen-gate-contradicts.png"), full_page=True,
                    clip=column(page, card, top["y"], end["y"] + end["height"]))
    print("wrote screen-gate-contradicts")

    sign_in(page, "National Registrar")
    page.goto(DIST + "#review")
    page.wait_for_timeout(1500)
    card = page.locator("div.card", has_text="keyboard").first
    top = page.get_by_text("Which of these is this item?").first.bounding_box()
    end = page.get_by_text("Field by field").first.bounding_box()
    page.screenshot(path=str(OUT / "screen-review-queue.png"), full_page=True,
                    clip=column(page, card, top["y"] - 26, end["y"] - 10))
    print("wrote screen-review-queue")

    page.keyboard.press("a")
    page.wait_for_timeout(500)
    page.goto(DIST + "#audit")
    page.wait_for_timeout(1200)
    page.get_by_role("button", name="Test the seal").click()
    page.wait_for_timeout(500)
    card = page.locator("div.card", has_text="Seal intact").first
    top = card.bounding_box()
    end = page.get_by_text("Export log").first.bounding_box()
    page.screenshot(path=str(OUT / "screen-audit-seal.png"), full_page=True,
                    clip=column(page, card, top["y"], end["y"] + 230))
    print("wrote screen-audit-seal")
    page.evaluate("localStorage.clear()")
    b.close()
