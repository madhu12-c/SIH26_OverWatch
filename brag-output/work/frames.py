"""Draw the video frame by frame: render(t) in video.html, one screenshot per frame.

    python frames.py --stills 1.2,3.6,...   check frames into stills/
    python frames.py                         all frames into frames/
"""
import argparse
import pathlib

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
FPS, DURATION = 30, 24.0

ap = argparse.ArgumentParser()
ap.add_argument("--stills")
args = ap.parse_args()

with sync_playwright() as p:
    br = p.chromium.launch(channel="chrome")
    page = br.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    page.goto((HERE / "video.html").as_uri())
    page.evaluate("document.fonts.ready")
    page.wait_for_function("document.getElementById('p_img').complete")
    ok = page.evaluate("""[document.fonts.check('800 40px "Noto Sans"'), document.fonts.check('500 40px "IBM Plex Mono"')]""")
    print("fonts loaded:", ok)
    if args.stills:
        out = HERE / "stills"
        out.mkdir(exist_ok=True)
        for s in args.stills.split(","):
            t = float(s)
            page.evaluate(f"render({t})")
            page.screenshot(path=str(out / f"t{t:05.2f}.png"))
        print("stills:", args.stills)
    else:
        out = HERE / "frames"
        out.mkdir(exist_ok=True)
        n = int(round(FPS * DURATION))
        for i in range(n):
            page.evaluate(f"render({i / FPS})")
            page.screenshot(path=str(out / f"f{i:04d}.png"))
            if i % 90 == 0:
                print("frame", i, "/", n, flush=True)
        print("frames:", n)
    br.close()
