"""Draw demo.html frame by frame.  --stills 5,10  -> demo_stills/ ;  no args -> demo_frames/ (all)."""
import argparse, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).parent
FPS, DURATION = 30, 104.0
ap = argparse.ArgumentParser(); ap.add_argument("--stills"); args = ap.parse_args()
with sync_playwright() as p:
    br = p.chromium.launch(channel="chrome", args=["--js-flags=--max-old-space-size=4096"])
    page = br.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    page.goto((HERE / "demo.html").as_uri())
    page.evaluate("document.fonts.ready")
    page.wait_for_function("window.ready()", timeout=120000)
    if args.stills:
        out = HERE / "demo_stills"; out.mkdir(exist_ok=True)
        for s in args.stills.split(","):
            t = float(s); page.evaluate(f"render({t})"); page.wait_for_timeout(60)
            page.screenshot(path=str(out / f"t{t:06.2f}.png"))
        print("stills:", args.stills)
    else:
        out = HERE / "demo_frames"; out.mkdir(exist_ok=True)
        n = int(round(FPS * DURATION))
        for i in range(n):
            page.evaluate(f"render({i / FPS})")
            page.screenshot(path=str(out / f"f{i:05d}.png"))
            if i % 300 == 0: print("frame", i, "/", n, flush=True)
        print("frames:", n)
    br.close()
