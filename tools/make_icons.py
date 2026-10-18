#!/usr/bin/env python3
"""Draw every app icon and the link-preview card from a simple football mark.

    python3 tools/make_icons.py

The mark is a plain football drawn in code: a chalk-white ball (two circle arcs) with
slate laces and seam stripes, on a slate square (#24303F, the page's theme colour).
No team logo is scraped, copied or hotlinked; the mark belongs to no school.

Writes, all into icons/:
  icon-192.png, icon-512.png ... slate rounded square, football (purpose any)
  icon-maskable-512.png ........ slate to the edge, the ball sized so its farthest
                                 pixel from the centre sits at 38% of the side
                                 (inside the 40% maskable safe circle), measured
                                 on the generated file
  apple-touch-icon.png (180), favicon-32.png
  og.png (1200x630) ............ link-preview card (og:image), text in Barlow Condensed /
                                 Public Sans (OFL, bundled in assets/fonts/ for this script)

One-time tool, run by hand when the mark changes; the scheduled build never
calls it.  Needs Pillow (pip install pillow), which requirements.txt does not.
"""
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SLATE = (0x24, 0x30, 0x3F)        # --brand, theme_color
CHALK = (0xEC, 0xEE, 0xF2)        # the ball (dark --ink)
BG_DARK = (0x11, 0x12, 0x16)      # the dark theme's --bg (manifest background_color)
INK_DARK = (0xEC, 0xEE, 0xF2)
MUTED_DARK = (0x9A, 0xA0, 0xAE)
S1_DARK = (0x39, 0x87, 0xE5)      # dark --s1 (first selection)
S2_DARK = (0xD9, 0x59, 0x26)      # dark --s2 (second selection)
DISPLAY = ROOT / "assets" / "fonts" / "barlow-condensed-latin-700-normal.woff"
BODY = ROOT / "assets" / "fonts" / "public-sans-latin-400-normal.woff"
SS = 4  # supersampling factor for smooth edges


def font(path, px):
    from PIL import ImageFont
    return ImageFont.truetype(str(path), px)


def ball(n, frac):
    """A transparent n x n RGBA layer with the football, its long axis frac of n, tilted 35 degrees."""
    from PIL import Image, ImageDraw
    L, Wd = frac * n, frac * n * 0.58          # length and width of the ball
    # the ball is the intersection of two circles whose chord is the long axis
    R = (L * L / 4 + Wd * Wd / 4) / Wd        # circle radius giving that length and width
    m = Image.new("L", (n, n), 0)
    a = Image.new("L", (n, n), 0); b = Image.new("L", (n, n), 0)
    c = n / 2
    ImageDraw.Draw(a).ellipse([c - R, c - (R - Wd / 2) - R, c + R, c - (R - Wd / 2) + R], fill=255)
    ImageDraw.Draw(b).ellipse([c - R, c + (R - Wd / 2) - R, c + R, c + (R - Wd / 2) + R], fill=255)
    from PIL import ImageChops
    m = ImageChops.multiply(a, b)
    layer = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    layer.paste(CHALK, (0, 0), m)
    g = ImageDraw.Draw(layer)
    lw = max(1, round(n * 0.022))
    # seam stripes near each tip, then the laces along the long axis
    for side in (-1, 1):
        x = c + side * L * 0.30
        h = Wd * 0.5 * math.sqrt(max(0, 1 - (2 * (x - c) / L) ** 2)) * 0.98
        g.line([x, c - h, x, c + h], fill=SLATE, width=lw)
    g.line([c - L * 0.17, c, c + L * 0.17, c], fill=SLATE, width=lw)
    for i in range(-2, 3):
        x = c + i * L * 0.075
        g.line([x, c - Wd * 0.14, x, c + Wd * 0.14], fill=SLATE, width=lw)
    return layer.rotate(35, resample=Image.BICUBIC, center=(c, c))


def icon(size, frac=0.74, radius_frac=0.2):
    from PIL import Image, ImageDraw
    n = size * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    if radius_frac: g.rounded_rectangle([0, 0, n - 1, n - 1], radius=radius_frac * n, fill=SLATE)
    else: g.rectangle([0, 0, n - 1, n - 1], fill=SLATE)
    b = ball(n, frac)
    img.alpha_composite(b)
    return img.resize((size, size), Image.LANCZOS)


def farthest(img):
    """Distance from the centre to the farthest pixel nearer chalk than slate, as a fraction of the side."""
    n = img.size[0]; c = (n - 1) / 2; px = img.convert("RGB").load(); best = 0
    for y in range(n):
        for x in range(n):
            p = px[x, y]
            if sum((a - b) ** 2 for a, b in zip(p, CHALK)) < sum((a - b) ** 2 for a, b in zip(p, SLATE)):
                best = max(best, math.hypot(x - c, y - c))
    return best / n


def maskable(size=512, target=0.38):
    """Shrink the mark until its farthest pixel (measured on the output) is within target of the side."""
    frac = 0.8
    for _ in range(20):
        out = icon(size, frac, radius_frac=0).convert("RGB")
        reach = farthest(out)
        if reach <= target: return out, reach
        frac *= target / reach * 0.995
    sys.exit("make_icons: maskable mark did not fit the safe circle")


def og():
    from PIL import Image, ImageDraw
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BG_DARK)
    g = ImageDraw.Draw(img)
    g.rectangle([0, 0, W, 18], fill=SLATE)
    mark = icon(220)
    img.paste(mark, (70, 120), mark)
    g.text((335, 108), "COLLEGE", font=font(DISPLAY, 132), fill=INK_DARK)
    g.text((335, 238), "FOOTBALL", font=font(DISPLAY, 132), fill=INK_DARK)
    g.rectangle([338, 392, 520, 400], fill=S1_DARK)
    g.rectangle([540, 392, 722, 400], fill=S2_DARK)
    g.text((72, 440), "COMPARE ANY FBS TEAMS AND PLAYERS  ·  2024–2026", font=font(DISPLAY, 54), fill=INK_DARK)
    g.text((72, 515), "Game by game: records, points, yards, turnovers, quarterbacks, backs, receivers.", font=font(BODY, 29), fill=MUTED_DARK)
    return img


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("make_icons needs Pillow: pip install pillow")
    out = ROOT / "icons"; out.mkdir(exist_ok=True)
    icon(512).save(out / "icon-512.png", optimize=True)
    icon(192).save(out / "icon-192.png", optimize=True)
    icon(180, radius_frac=0).convert("RGB").save(out / "apple-touch-icon.png", optimize=True)  # iOS rounds the corners itself
    icon(32, 0.84, radius_frac=0.18).save(out / "favicon-32.png", optimize=True)
    m, reach = maskable()
    m.save(out / "icon-maskable-512.png", optimize=True)
    og().save(out / "og.png", optimize=True)
    print(f"wrote icons/: icon-192, icon-512, icon-maskable-512 (farthest pixel {reach:.3f} of the side), apple-touch-icon, favicon-32, og")


if __name__ == "__main__":
    main()
