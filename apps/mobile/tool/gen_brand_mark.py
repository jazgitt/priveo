"""Makes the app's brand images from the owner's files in docs/brand:
the Android launcher icon, the native splash mark, and the logo and P mark
shown inside the app.

The owner's files are white with gold, for dark backgrounds. The app only
shows them on the dark look (splash, login, customer screens).

Needs Pillow. Run from apps/mobile: python tool/gen_brand_mark.py
"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT.parent.parent / "docs/brand"
RES = ROOT / "android/app/src/main/res"
TOKENS = json.loads((BRAND / "tokens.json").read_text())["color"]
INK = TOKENS["dark"]["ink"]
DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def trimmed(name: str) -> Image.Image:
    """The owner's image without its empty border and faint specks."""
    img = Image.open(BRAND / name).convert("RGBA")
    solid = img.getchannel("A").point(lambda a: 255 if a > 60 else 0)
    return img.crop(solid.getbbox())


def square(mark: Image.Image, size: int, share: float, background=None) -> Image.Image:
    """A square image with the mark centred. share is mark width / size."""
    width = round(size * share)
    scaled = mark.resize((width, round(width * mark.height / mark.width)), Image.LANCZOS)
    img = Image.new("RGBA", (size, size), background or (0, 0, 0, 0))
    img.alpha_composite(scaled, ((size - scaled.width) // 2, (size - scaled.height) // 2))
    return img


def save(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)


p_mark = trimmed("priveo_p_icon.png")
for density, factor in DENSITIES.items():
    # Legacy launcher icon, 48 dp, full square.
    save(square(p_mark, round(48 * factor), 0.62, INK),
         RES / f"mipmap-{density}/ic_launcher.png")
    # Adaptive icon foreground, 108 dp. Only the middle 66 dp is always shown.
    save(square(p_mark, round(108 * factor), 0.40),
         RES / f"mipmap-{density}/ic_launcher_foreground.png")
    # Native splash mark, 96 dp. The splash is dark in both phone modes.
    save(square(p_mark, round(96 * factor), 0.90),
         RES / f"drawable-{density}/splash_mark.png")

# The logo inside the app, 600 px wide (shown at 200 logical pixels).
logo = trimmed("priveo_full_logo.png")
logo = logo.resize((600, round(600 * logo.height / logo.width)), Image.LANCZOS)
save(logo, ROOT / "assets/brand/priveo-logo.png")
# The P mark in the customer top bar, 120 px high (shown at 30).
save(p_mark.resize((round(120 * p_mark.width / p_mark.height), 120), Image.LANCZOS),
     ROOT / "assets/brand/priveo-mark.png")
print("wrote launcher icons, splash marks, the in-app logo and the P mark")
