"""Print content.html to the kit's PDF with Chrome (named pages: the diagram page is landscape)."""
import pathlib
from playwright.sync_api import sync_playwright

KIT = pathlib.Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    page = b.new_page()
    page.goto((KIT / "src" / "content.html").as_uri())
    page.wait_for_timeout(1500)
    out = KIT / "SIH26099-PPT-Content-Kit.pdf"
    page.pdf(path=str(out), prefer_css_page_size=True, print_background=True)
    b.close()
    print("wrote", out.name, out.stat().st_size // 1024, "KB")
