#!/usr/bin/env python
"""docs/<scenario>/ viewer -> docs/img/flood-<scenario>.gif + .mp4 (link-preview teaser for websites).

Drives the WebGL viewer frame by frame in headless Chrome (playwright, `pip install playwright`; uses the
installed Google Chrome) and encodes with ffmpeg. The caption keeps the "not a certified assessment" wording.
"""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CSS = ('#help,.topright,#side,.mini,#speed,.tright,.rl:not(.key):not(.pond){display:none!important}'
       '.rl.key{font-size:16px!important}.rl.pond{font-size:18px!important}'
       '.title{max-width:none!important}.title h1{font-size:26px!important}'
       '.stat .v{font-size:32px!important}.stat .k{font-size:13px!important}')


def capture(scenario, frames_dir, caption, zoom):
    W, H = 1280, 720
    url = (ROOT / "docs" / scenario / "index.html").as_uri()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", args=["--use-angle=metal", "--enable-webgl", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1, reduced_motion="reduce")
        pg.goto(url); pg.wait_for_function("document.getElementById('loading').hidden"); pg.wait_for_timeout(1500)
        pg.keyboard.press("i")  # collapse the title panel to its heading
        pg.add_style_tag(content=CSS)
        pg.evaluate("t => { document.querySelector('.title h1').textContent = t }", caption)
        pg.mouse.move(W / 2, H / 2); pg.mouse.wheel(0, -zoom)
        n = int(pg.evaluate("document.getElementById('scrub').max")) + 1
        for k in range(n):
            pg.evaluate("k => { const s = document.getElementById('scrub'); s.value = k; s.dispatchEvent(new Event('input')) }", k)
            pg.wait_for_timeout(120)
            pg.screenshot(path=str(frames_dir / f"{k:03d}.png"))
        b.close()
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", default="east-extended", help="folder under docs/ (east, east-extended, north, ...)")
    ap.add_argument("--caption", default=None)
    ap.add_argument("--fps", type=int, default=8)
    ap.add_argument("--width", type=int, default=800, help="GIF width in px")
    ap.add_argument("--hold", type=float, default=2.0, help="seconds to hold the last frame before looping")
    ap.add_argument("--zoom", type=int, default=330, help="wheel delta to zoom in from the default view")
    a = ap.parse_args()
    caption = a.caption or (f"Wrights Road ponds – {a.scenario.split('-')[0]} breach · screening flood model, "
                            "not a certified assessment")
    out = ROOT / "docs" / "img"; out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        n = capture(a.scenario, tmp, caption, a.zoom)
        for i in range(n, n + int(a.hold * a.fps)):
            shutil.copy(tmp / f"{n - 1:03d}.png", tmp / f"{i:03d}.png")
        src = ["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-i", str(tmp / "%03d.png")]
        gif = out / f"flood-{a.scenario}.gif"
        subprocess.run(src + ["-vf", f"scale={a.width}:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];"
                              "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle", str(gif)], check=True)
        subprocess.run(src + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart",
                              str(gif.with_suffix(".mp4"))], check=True)
    print(f"wrote {gif} ({gif.stat().st_size / 1e6:.1f} MB) and {gif.with_suffix('.mp4').name}")


if __name__ == "__main__":
    main()
