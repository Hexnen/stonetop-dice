#!/usr/bin/env python3
"""Precise piecewise-affine warp of generated die faces onto their TRUE DSN UV polygon.

Source = the known mockup shape (the generated art follows it); target = the real face
polygon extracted from Na[shape]. Both share vertex order, so we fan-triangulate from the
centroid and affine-map each wedge. Fills kites/pentagons/triangles exactly.
d2 (coin) is simply scaled to fill the round face. d4 is skipped (DSN draws no image
labels for d4 — it has special text-only face handling).
"""
import math
import os
import numpy as np
from PIL import Image, ImageDraw
from slice_faces import chroma_key, feather_alpha, autocrop_alpha

SIZE = 512
CELL = 256
PLACE_O, PLACE_S = 12 / 256, 232 / 256   # mockup tile placement inside the 256 cell


def cellpoly(poly01):
    return [((PLACE_O + x * PLACE_S) * CELL, (PLACE_O + y * PLACE_S) * CELL) for x, y in poly01]


def tgtpoly(poly01):
    return [(x * SIZE, y * SIZE) for x, y in poly01]


# mockup shapes (tile [0,1]) — must match build_mockups
KITE_SRC = [(0.50, 0.03), (0.86, 0.74), (0.50, 0.95), (0.14, 0.74)]
PENTA_SRC = [(0.5 + 0.45 * math.cos(math.radians(-90 + i * 72)),
              0.55 + 0.45 * math.sin(math.radians(-90 + i * 72))) for i in range(5)]
TRI20_SRC = [(0.50, 0.06), (0.97, 0.90), (0.03, 0.90)]

# TRUE UV target polygons (cell-local, normalized), from extract_face_polys.py
KITE_TGT = [(0.496, 0.003), (0.86, 0.774), (0.496, 0.955), (0.132, 0.774)]
PENTA_TGT = [(0.499, 0.003), (0.991, 0.36), (0.803, 0.937), (0.195, 0.937), (0.008, 0.36)]
TRI20_TGT = [(0.501, 0.002), (0.999, 0.864), (0.003, 0.864)]

CFG = {
    "d10": ("tools/gen_d10.png", 5, 2, 10, KITE_SRC, KITE_TGT),
    "d12": ("tools/gen_d12.png", 4, 3, 12, PENTA_SRC, PENTA_TGT),
    "d20": ("tools/gen_d20.png", 5, 4, 20, TRI20_SRC, TRI20_TGT),
}


def affine_out_to_in(src, dst):
    D = np.array([[dst[i][0], dst[i][1], 1] for i in range(3)], float)
    sx = np.array([src[i][0] for i in range(3)], float)
    sy = np.array([src[i][1] for i in range(3)], float)
    cx = np.linalg.solve(D, sx); cy = np.linalg.solve(D, sy)
    return (cx[0], cx[1], cx[2], cy[0], cy[1], cy[2])


def warp_poly(cell, src, dst, overscan=0.02):
    n = len(src)
    Cs = (sum(p[0] for p in src) / n, sum(p[1] for p in src) / n)
    Ct = (sum(p[0] for p in dst) / n, sum(p[1] for p in dst) / n)
    dst = [(Ct[0] + (x - Ct[0]) * (1 + overscan), Ct[1] + (y - Ct[1]) * (1 + overscan)) for x, y in dst]
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    for i in range(n):
        s_tri = [Cs, src[i], src[(i + 1) % n]]
        d_tri = [Ct, dst[i], dst[(i + 1) % n]]
        coeffs = affine_out_to_in(s_tri, d_tri)
        warped = cell.transform((SIZE, SIZE), Image.AFFINE, coeffs, resample=Image.BICUBIC)
        mask = Image.new("L", (SIZE, SIZE), 0)
        ImageDraw.Draw(mask).polygon(d_tri, fill=255)
        out.paste(warped, (0, 0), mask)
    return out


def save(face, die, n):
    face.save(f"textures/{die}f{n}.webp", "WEBP", quality=92, method=6)
    bg = Image.new("RGBA", (SIZE, SIZE), (128, 128, 128, 255)); bg.alpha_composite(face)
    bg.convert("L").save(f"textures/{die}f{n}-bump.webp", "WEBP", quality=90, method=6)


def main():
    for die, (atlas, cols, rows, faces, src01, tgt01) in CFG.items():
        keyed = feather_alpha(chroma_key(Image.open(atlas).convert("RGB"), 90, 35), 1.0)
        W, H = keyed.size; cw, ch = W // cols, H // rows
        src = cellpoly(src01); tgt = tgtpoly(tgt01)
        n = 0
        for r in range(rows):
            for c in range(cols):
                n += 1
                if n > faces:
                    break
                cell = keyed.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)).resize((CELL, CELL))
                save(warp_poly(cell, src, tgt), die, n)
        print(f"{die}: warped {min(n, faces)} faces")

    # d2 coin: fill the round face
    keyed = feather_alpha(chroma_key(Image.open("tools/gen_d2.png").convert("RGB"), 90, 35), 1.0)
    W, H = keyed.size; cw = W // 2
    for i in range(2):
        art = autocrop_alpha(keyed.crop((i * cw, 0, (i + 1) * cw, H)))
        d = int(SIZE * 0.96)
        art = art.resize((d, d), Image.LANCZOS)
        canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        canvas.paste(art, ((SIZE - d) // 2, (SIZE - d) // 2))
        save(canvas, "d2", i + 1)
    print("d2: filled 2 faces")


if __name__ == "__main__":
    main()
