"""Draws the PLACEHOLDER Priveo mark (a gold serif P) for the Android launcher
icon and the native splash. Replace it when the owner supplies the real mark.

Needs Pillow. Run from apps/mobile: python tool/gen_brand_mark.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "android/app/src/main/res"
TOKENS = json.loads((ROOT.parent.parent / "docs/brand/tokens.json").read_text())
GOLD = TOKENS["color"]["dark"]["gold"]
INK = TOKENS["color"]["dark"]["ink"]
FONT = ROOT / "assets/fonts/CormorantGaramond.ttf"
DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def mark(size: int, glyph_share: float, background: str | None) -> Image.Image:
    """A square image with the P centred. glyph_share is the P height / size."""
    scale = 4  # draw large, then shrink for smooth edges
    big = size * scale
    img = Image.new("RGBA", (big, big), background or (0, 0, 0, 0))
    font = ImageFont.truetype(str(FONT), 100)
    font.set_variation_by_axes([600])
    left, top, right, bottom = font.getbbox("P")
    font = ImageFont.truetype(str(FONT), int(100 * big * glyph_share / (bottom - top)))
    font.set_variation_by_axes([600])
    left, top, right, bottom = font.getbbox("P")
    xy = ((big - (right - left)) / 2 - left, (big - (bottom - top)) / 2 - top)
    ImageDraw.Draw(img).text(xy, "P", font=font, fill=GOLD)
    return img.resize((size, size), Image.LANCZOS)


def save(img: Image.Image, folder: str, name: str) -> None:
    out = RES / folder
    out.mkdir(parents=True, exist_ok=True)
    img.save(out / name, optimize=True)


for density, factor in DENSITIES.items():
    # Legacy launcher icon, 48 dp, full square.
    save(mark(round(48 * factor), 0.56, INK), f"mipmap-{density}", "ic_launcher.png")
    # Adaptive icon foreground, 108 dp. Only the middle 66 dp is always shown.
    save(mark(round(108 * factor), 0.34, None), f"mipmap-{density}",
         "ic_launcher_foreground.png")
    # Native splash mark, 96 dp.
    save(mark(round(96 * factor), 0.80, None), f"drawable-{density}", "splash_mark.png")
print("wrote launcher icons and splash marks")
