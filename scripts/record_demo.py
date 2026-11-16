"""Record the docs demo with Playwright: seed 7 fails, the fix goes on, the
same seed passes. Writes a GIF for the README and, with a full ffmpeg build,
an MP4.

    python scripts/record_demo.py --webm ~/Videos/humaninput-demo.webm --mp4 ~/Videos/humaninput-demo.mp4

Needs Playwright with Chromium, and Pillow for the GIF. Frames are pulled out
with ffmpeg: the one on PATH, or else the build Playwright ships for its own
video recording. That build can't write MP4; the script prints the command
to run instead.
"""

from __future__ import annotations

import argparse
import glob
import os
import pathlib
import shutil
import subprocess
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMO = ROOT / "docs" / "demo" / "index.html"
VIEWPORT = {"width": 1200, "height": 1260}
CROP_TOP = 130  # drop the page title; the README already has one
GIF_WIDTH = 760
GIF_FPS = 8


def record(webm: pathlib.Path) -> None:
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport=VIEWPORT, record_video_dir=tmp, record_video_size=VIEWPORT, color_scheme="light"
        )
        page = context.new_page()
        page.goto(DEMO.as_uri())
        page.select_option("#seed", "7")

        def play(button: str) -> None:
            page.click(button)
            page.wait_for_timeout(300)
            page.wait_for_function("!('running' in document.body.dataset)", timeout=20_000)

        page.wait_for_timeout(800)
        play("#play")
        page.wait_for_timeout(2000)
        page.check("#fixed")
        page.wait_for_timeout(700)
        play("#replay")
        page.wait_for_timeout(2500)

        video = page.video
        context.close()
        browser.close()
        webm.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(video.path(), webm)


def find_ffmpeg() -> str | None:
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~/.cache")), "ms-playwright"
    )
    for name in ("ffmpeg-win64.exe", "ffmpeg-linux", "ffmpeg-mac"):
        hits = sorted(glob.glob(os.path.join(base, "ffmpeg-*", name)))
        if hits:
            return hits[-1]
    return None


# Light-theme colours from docs/demo/demo.css. A fixed palette keeps the small red and
# green marks that an adaptive one drops in favour of the large grey areas.
TOKENS = [
    "#ffffff", "#f5f5f4", "#c9c9c6", "#1a1a1a", "#555555", "#1d4ed8", "#1e6b34", "#e3f3e7",
    "#b3261e", "#fbe7e5", "#8a5300", "#fdf0dc", "#6b7280", "#d7d9dc",
]


def _palette():
    from PIL import Image

    def rgb(h: str) -> tuple[int, int, int]:
        return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)

    colours = [rgb(h) for h in TOKENS]
    for c in list(colours):
        for bg in (rgb("#ffffff"), rgb("#f5f5f4")):
            colours.append(tuple((a + b) // 2 for a, b in zip(c, bg)))
    colours += [(v, v, v) for v in range(0, 256, 8)]
    flat = [x for c in dict.fromkeys(colours) for x in c]
    img = Image.new("P", (1, 1))
    img.putpalette(flat + flat[:3] * (256 - len(flat) // 3))
    return img


def to_gif(ffmpeg: str, webm: pathlib.Path, gif: pathlib.Path) -> None:
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        # Output -r instead of the fps filter, which Playwright's ffmpeg leaves out.
        vf = f"crop=in_w:in_h-{CROP_TOP}:0:{CROP_TOP},scale={GIF_WIDTH}:-1:flags=lanczos"
        subprocess.run(
            [ffmpeg, "-loglevel", "error", "-i", str(webm), "-vf", vf, "-r", str(GIF_FPS), os.path.join(tmp, "%04d.png")],
            check=True,
        )
        frames = [Image.open(f).convert("RGB") for f in sorted(glob.glob(os.path.join(tmp, "*.png")))]
        palette = _palette()
        quantized = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
        quantized[0].save(
            gif,
            save_all=True,
            append_images=quantized[1:],
            duration=round(1000 / GIF_FPS),
            loop=0,
            optimize=True,
        )


def has_x264(ffmpeg: str) -> bool:
    out = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    return "libx264" in out


def mp4_command(ffmpeg: str, webm: pathlib.Path, mp4: pathlib.Path) -> list[str]:
    return [
        ffmpeg, "-y", "-i", str(webm),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-movflags", "+faststart",
        str(mp4),
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--webm", type=pathlib.Path, required=True, help="where to keep the raw recording")
    ap.add_argument("--gif", type=pathlib.Path, default=ROOT / "docs" / "demo.gif")
    ap.add_argument("--mp4", type=pathlib.Path, default=None)
    args = ap.parse_args()

    record(args.webm)
    print(f"recorded {args.webm}")

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        print("no ffmpeg found; GIF and MP4 skipped")
        return
    to_gif(ffmpeg, args.webm, args.gif)
    print(f"wrote {args.gif} ({args.gif.stat().st_size / 1e6:.1f} MB)")

    if args.mp4:
        if has_x264(ffmpeg):
            subprocess.run(mp4_command(ffmpeg, args.webm, args.mp4), check=True)
            print(f"wrote {args.mp4}")
        else:
            print("this ffmpeg can't write H.264. With a full ffmpeg build, run:")
            print("  " + subprocess.list2cmdline(mp4_command("ffmpeg", args.webm, args.mp4)))


if __name__ == "__main__":
    main()
