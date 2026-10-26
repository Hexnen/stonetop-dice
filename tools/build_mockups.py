#!/usr/bin/env python3
"""Build green-screen mockups for image2: carved-stone faces in the correct shape per die
(triangle / kite / pentagon) with Rimba numerals AUTO-FIT inside the outline.

Numerals are scaled to the polygon's inscribed circle (Chebyshev center) so they never
spill past the border, and two-digit numbers shrink to fit the width too.

Usage:
    python build_mockups.py <green_atlas> <rimba.otf> <out_dir> [--d4-mode three|single]
"""
import argparse
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

GREEN = (12, 251, 6, 255)
DARK = (40, 30, 18, 255)
INK = (30, 22, 12, 255)
HI = (232, 220, 190, 150)
TILE = 232


def stone_patch(atlas_path, size):
    atlas = Image.open(atlas_path).convert("RGB")
    return atlas.crop((35, 195, 190, 350)).resize((size, size), Image.LANCZOS)


def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
            inside = not inside
        j = i
    return inside


def dist_to_edges(x, y, poly):
    n = len(poly); best = 1e9
    for i in range(n):
        ax, ay = poly[i]; bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy + 1e-9)))
        px, py = ax + t * dx, ay + t * dy
        best = min(best, math.hypot(x - px, y - py))
    return best


def chebyshev_center(poly):
    """Point inside the polygon farthest from any edge (incircle center + radius)."""
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    best, bc = -1, (sum(xs) / len(xs), sum(ys) / len(ys))
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    for _ in range(2):  # coarse then refine
        step = (x1 - x0) / 40
        gx = x0
        while gx <= x1:
            gy = y0
            while gy <= y1:
                if point_in_poly(gx, gy, poly):
                    d = dist_to_edges(gx, gy, poly)
                    if d > best:
                        best, bc = d, (gx, gy)
                gy += step
            gx += step
        x0, x1 = bc[0] - step * 2, bc[0] + step * 2
        y0, y1 = bc[1] - step * 2, bc[1] + step * 2
    return bc, best


def render_numeral(font_path, text, max_w, max_h):
    """Carved numeral scaled to fit max_w x max_h."""
    f = ImageFont.truetype(font_path, 200)
    tmp = Image.new("L", (10, 10)); bb = ImageDraw.Draw(tmp).textbbox((0, 0), text, font=f)
    gw, gh = bb[2] - bb[0], bb[3] - bb[1]
    pad = 240
    img = Image.new("RGBA", (pad, pad), (0, 0, 0, 0))
    mask = Image.new("L", (pad, pad), 0)
    ImageDraw.Draw(mask).text(((pad - gw) // 2 - bb[0], (pad - gh) // 2 - bb[1]), text, font=f, fill=255)
    hi = Image.new("RGBA", (pad, pad), (0, 0, 0, 0)); hi.paste(HI, (0, 0), mask)
    hi = hi.transform(hi.size, Image.AFFINE, (1, 0, -2, 0, 1, -2))
    img.alpha_composite(hi)
    dk = Image.new("RGBA", (pad, pad), (0, 0, 0, 0)); dk.paste(INK, (0, 0), mask)
    img.alpha_composite(dk)
    img = img.crop(img.getbbox())
    scale = min(max_w / img.width, max_h / img.height)
    return img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)


def stone_tile(poly01, patch, size):
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pts = [(x * size, y * size) for x, y in poly01]
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    tile.paste(patch.resize((size, size), Image.LANCZOS), (0, 0), mask)
    ImageDraw.Draw(tile).line(pts + [pts[0]], fill=DARK, width=max(6, size // 42), joint="curve")
    return tile, pts


def alpha_centroid(img):
    """Center of mass of the ink (alpha-weighted) — for optical centering by weight."""
    a = np.asarray(img.split()[-1], dtype=np.float64)
    tot = a.sum()
    if tot < 1:
        return img.width / 2, img.height / 2
    ys, xs = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    return (xs * a).sum() / tot, (ys * a).sum() / tot


def place_weight(tile, num, cx, cy):
    """Paste so the numeral's center of mass (not its bbox) lands at (cx, cy)."""
    mx, my = alpha_centroid(num)
    tile.alpha_composite(num, (int(round(cx - mx)), int(round(cy - my))))


# face shapes in [0,1] (y-down)
TRI = [(0.50, 0.08), (0.93, 0.90), (0.07, 0.90)]
KITE = [(0.50, 0.03), (0.86, 0.74), (0.50, 0.95), (0.14, 0.74)]
def _pentagon():
    cx, cy, r = 0.5, 0.55, 0.45
    return [(cx + r * math.cos(math.radians(-90 + i * 72)),
             cy + r * math.sin(math.radians(-90 + i * 72))) for i in range(5)]
PENTA = _pentagon()
TRI20 = [(0.50, 0.06), (0.97, 0.90), (0.03, 0.90)]                    # wide-base d20 triangle
CIRCLE = [(0.5 + 0.46 * math.cos(math.radians(a)), 0.5 + 0.46 * math.sin(math.radians(a)))
          for a in range(0, 360, 15)]                                # d2 coin


NUM_H = 0.34   # numeral height as a fraction of the tile — CONSTANT across the whole set
NUM_W = 0.58   # width cap (two-digit numbers shrink to fit this)


def single_face(poly01, patch, font_path, text, size):
    tile, pts = stone_tile(poly01, patch, size)
    (cx, cy), r = chebyshev_center(pts)         # most-inside point of the face
    num = render_numeral(font_path, text, max_w=size * NUM_W, max_h=size * NUM_H)
    place_weight(tile, num, cx, cy)             # optical centering by ink weight
    return tile


def d4_three_face(poly01, patch, font_path, triple, size):
    tile, pts = stone_tile(poly01, patch, size)
    cx = sum(p[0] for p in pts) / 3; cy = sum(p[1] for p in pts) / 3
    for (vx, vy), t in zip(pts, triple):
        dx, dy = vx - cx, vy - cy
        ax, ay = cx + dx * 0.46, cy + dy * 0.46          # sit between centroid and vertex
        num = render_numeral(font_path, str(t), max_w=size * 0.20, max_h=size * 0.20)
        # rotate so the numeral's TOP points at its vertex (upright when that tip is up)
        rot = -math.degrees(math.atan2(dx, -dy))
        num = num.rotate(rot, expand=True, resample=Image.BICUBIC)
        place_weight(tile, num, ax, ay)
    return tile


def grid(faces, cols, out, atlas, font_path, draw):
    rows = (faces + cols - 1) // cols
    canvas = Image.new("RGBA", (cols * 256, rows * 256), GREEN)
    patch = stone_patch(atlas, 256)
    for i in range(faces):
        r, c = i // cols, i % cols
        canvas.alpha_composite(draw(i, patch, font_path), (c * 256 + 12, r * 256 + 12))
    canvas.convert("RGB").save(out)
    print("wrote", out, canvas.size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("atlas"); ap.add_argument("font"); ap.add_argument("out_dir")
    ap.add_argument("--d4-mode", choices=["three", "single"], default="three")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    D4 = [(1, 2, 3), (1, 3, 4), (1, 4, 2), (2, 4, 3)]
    if a.d4_mode == "three":
        grid(4, 2, os.path.join(a.out_dir, "mockup_d4.png"), a.atlas, a.font,
             lambda i, p, f: d4_three_face(TRI, p, f, D4[i], TILE))
    else:
        grid(4, 2, os.path.join(a.out_dir, "mockup_d4.png"), a.atlas, a.font,
             lambda i, p, f: single_face(TRI, p, f, str(i + 1), TILE))
    grid(10, 5, os.path.join(a.out_dir, "mockup_d10.png"), a.atlas, a.font,
         lambda i, p, f: single_face(KITE, p, f, str(i), TILE))
    grid(12, 4, os.path.join(a.out_dir, "mockup_d12.png"), a.atlas, a.font,
         lambda i, p, f: single_face(PENTA, p, f, str(i + 1), TILE))
    grid(20, 5, os.path.join(a.out_dir, "mockup_d20.png"), a.atlas, a.font,
         lambda i, p, f: single_face(TRI20, p, f, str(i + 1), TILE))
    grid(2, 2, os.path.join(a.out_dir, "mockup_d2.png"), a.atlas, a.font,
         lambda i, p, f: single_face(CIRCLE, p, f, str(i + 1), TILE))


if __name__ == "__main__":
    main()
