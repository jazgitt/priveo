"""Makes the app's brand images from the owner's files in docs/brand:
the Android launcher icon, the native splash mark and the in-app logo.

The owner's files are white with gold, for dark backgrounds. The versions for
light backgrounds are DERIVED here: white becomes the light text colour and
gold becomes the light gold text colour from tokens.json.

Needs Pillow. Run from apps/mobile: python tool/gen_brand_mark.py
"""
import colorsys
import json
from pathlib import Path

from PIL import Image, ImageColor

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT.parent.parent / "docs/brand"
RES = ROOT / "android/app/src/main/res"
TOKENS = json.loads((BRAND / "tokens.json").read_text())["color"]
INK = TOKENS["dark"]["ink"]
LIGHT_TEXT = ImageColor.getrgb(TOKENS["light"]["text"])
LIGHT_GOLD = ImageColor.getrgb(TOKENS["light"]["goldText"])
DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def trimmed(name: str) -> Image.Image:
    """The owner's image without its empty border and faint specks."""
    img = Image.open(BRAND / name).convert("RGBA")
    solid = img.getchannel("A").point(lambda a: 255 if a > 60 else 0)
    return img.crop(solid.getbbox())


def for_light(img: Image.Image) -> Image.Image:
    out = img.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            hue, sat, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            is_gold = sat > 0.22 and 0.07 < hue < 0.17
            px[x, y] = (*(LIGHT_GOLD if is_gold else LIGHT_TEXT), a)
    return out


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
p_mark_light = for_light(p_mark)
for density, factor in DENSITIES.items():
    # Legacy launcher icon, 48 dp, full square.
    save(square(p_mark, round(48 * factor), 0.62, INK),
         RES / f"mipmap-{density}/ic_launcher.png")
    # Adaptive icon foreground, 108 dp. Only the middle 66 dp is always shown.
    save(square(p_mark, round(108 * factor), 0.40),
         RES / f"mipmap-{density}/ic_launcher_foreground.png")
    # Native splash mark, 96 dp: dark ink by day, white at night.
    save(square(p_mark_light, round(96 * factor), 0.90),
         RES / f"drawable-{density}/splash_mark.png")
    save(square(p_mark, round(96 * factor), 0.90),
         RES / f"drawable-night-{density}/splash_mark.png")

# The logo inside the app, 600 px wide (shown at 200 logical pixels).
logo = trimmed("priveo_full_logo.png")
logo = logo.resize((600, round(600 * logo.height / logo.width)), Image.LANCZOS)
save(logo, ROOT / "assets/brand/priveo-logo.png")
save(for_light(logo), ROOT / "assets/brand/priveo-logo-light.png")
print("wrote launcher icons, splash marks and the in-app logos")
