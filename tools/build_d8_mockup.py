#!/usr/bin/env python3
"""Build a d8 mockup reference for gpt-image-2: 8 EQUILATERAL triangular carved-stone
faces (all pointing up), each bearing an exact font numeral 1-8, on a green-screen
background. Pins triangle shape (60deg), layout, and exact glyphs so the model only
polishes the stone, never invents the font or the geometry.

Usage:
    python build_d8_mockup.py <stone_atlas_green> <numeral_dir> <out.png>
"""
import math
import sys
from PIL import Image, ImageDraw

GREEN = (12, 251, 6, 255)
DARK = (40, 30, 18, 255)


def stone_patch(atlas_path, size):
    atlas = Image.open(atlas_path).convert("RGB")
    patch = atlas.crop((35, 195, 190, 350))  # face1 upper-left corner: clean parchment
    return patch.resize((size, size), Image.LANCZOS)


def equilateral_tile(size, patch):
    """Upward equilateral triangle (60deg) inscribed in a `size` square, stone-filled."""
    b = size - 12                      # base length
    h = b * math.sqrt(3) / 2           # equilateral height
    cx = size / 2
    y_base = (size + h) / 2
    y_apex = (size - h) / 2
    pts = [(cx, y_apex), (cx - b / 2, y_base), (cx + b / 2, y_base)]
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    tile.paste(patch.resize((size, size), Image.LANCZOS), (0, 0), mask)
    ImageDraw.Draw(tile).line(pts + [pts[0]], fill=DARK, width=10, joint="curve")
    return tile, (y_apex, y_base)


def main():
    atlas_path, numdir, out = sys.argv[1], sys.argv[2], sys.argv[3]
    W = H = 1024
    cols, rows = 4, 2
    canvas = Image.new("RGBA", (W, H), GREEN)
    patch = stone_patch(atlas_path, 256)
    cw, ch = W // cols, H // rows
    tsize = min(cw, ch) - 16
    for i in range(8):
        r, c = i // cols, i % cols
        tile, (y_apex, y_base) = equilateral_tile(tsize, patch)
        num = Image.open(f"{numdir}/num{i + 1}.webp").convert("RGBA")
        gs = int(tsize * 0.40)
        num = num.resize((gs, gs), Image.LANCZOS)
        # centroid of an upward triangle sits ~1/3 up from the base
        cy = int(y_base - (y_base - y_apex) / 3)
        tile.alpha_composite(num, ((tsize - gs) // 2, cy - gs // 2))
        x = c * cw + (cw - tsize) // 2
        y = r * ch + (ch - tsize) // 2
        canvas.alpha_composite(tile, (x, y))
    canvas.convert("RGB").save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
