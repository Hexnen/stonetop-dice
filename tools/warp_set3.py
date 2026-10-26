#!/usr/bin/env python3
"""Warp generated die faces onto their DSN UV polygon with a SINGLE whole-image
transform and NO masking (masking clips the art = "cuts the textures"). A small
overscan makes the art reach just past the face edges; DSN's face UV does the clipping
on the die so nothing is lost.

  triangle (d20)  -> least-squares affine (exact for 3 pts)
  pentagon (d12)  -> least-squares affine over 5 pts (near-exact, regular->regular)
  kite     (d10)  -> exact 4-point perspective
"""
import math
import numpy as np
from PIL import Image
from slice_faces import chroma_key, feather_alpha

SIZE = 512
CELL = 256
PLACE_O, PLACE_S = 12 / 256, 232 / 256


def cellpoly(p):
    return [((PLACE_O + x * PLACE_S) * CELL, (PLACE_O + y * PLACE_S) * CELL) for x, y in p]


def overscan(dst, k=0.03):
    cx = sum(p[0] for p in dst) / len(dst); cy = sum(p[1] for p in dst) / len(dst)
    return [(cx + (x - cx) * (1 + k), cy + (y - cy) * (1 + k)) for x, y in dst]


def affine_ls(src, dst):
    """output->input affine (PIL): fit src ≈ M·[dst,1] (least squares)."""
    D = np.array([[x, y, 1] for x, y in dst], float)
    mx = np.linalg.lstsq(D, np.array([s[0] for s in src]), rcond=None)[0]
    my = np.linalg.lstsq(D, np.array([s[1] for s in src]), rcond=None)[0]
    return (mx[0], mx[1], mx[2], my[0], my[1], my[2])


def perspective(src, dst):
    """output->input perspective (PIL): 8 coeffs from 4 correspondences."""
    A, B = [], []
    for (sx, sy), (dx, dy) in zip(src, dst):
        A.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy]); B.append(sx)
        A.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy]); B.append(sy)
    return tuple(np.linalg.solve(np.array(A, float), np.array(B, float)))


# mockup source shapes (match build_mockups) and TRUE UV targets (extract_face_polys)
SRC = {
    "d10": [(0.50, 0.03), (0.86, 0.74), (0.50, 0.95), (0.14, 0.74)],
    "d12": [(0.5 + 0.45 * math.cos(math.radians(-90 + i * 72)),
             0.55 + 0.45 * math.sin(math.radians(-90 + i * 72))) for i in range(5)],
    "d20": [(0.50, 0.06), (0.97, 0.90), (0.03, 0.90)],
}
TGT = {
    "d10": [(0.496, 0.003), (0.86, 0.774), (0.496, 0.955), (0.132, 0.774)],
    "d12": [(0.499, 0.003), (0.991, 0.36), (0.803, 0.937), (0.195, 0.937), (0.008, 0.36)],
    "d20": [(0.501, 0.002), (0.999, 0.864), (0.003, 0.864)],
}
CFG = {"d10": ("tools/gen_d10.png", 5, 2, 10),
       "d12": ("tools/gen_d12.png", 4, 3, 12),
       "d20": ("tools/gen_d20.png", 5, 4, 20)}


def main():
    for die, (atlas, cols, rows, faces) in CFG.items():
        keyed = feather_alpha(chroma_key(Image.open(atlas).convert("RGB"), 90, 35), 1.0)
        W, H = keyed.size; cw, ch = W // cols, H // rows
        src = cellpoly(SRC[die])
        dst = overscan([(x * SIZE, y * SIZE) for x, y in TGT[die]])
        kind = "persp" if len(src) == 4 else "affine"
        coeffs = perspective(src, dst) if kind == "persp" else affine_ls(src, dst)
        tmode = Image.PERSPECTIVE if kind == "persp" else Image.AFFINE
        n = 0
        for r in range(rows):
            for c in range(cols):
                n += 1
                if n > faces:
                    break
                cell = keyed.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)).resize((CELL, CELL))
                face = cell.transform((SIZE, SIZE), tmode, coeffs, resample=Image.BICUBIC)
                face.save(f"textures/{die}f{n}.webp", "WEBP", quality=92, method=6)
                bg = Image.new("RGBA", (SIZE, SIZE), (128, 128, 128, 255)); bg.alpha_composite(face)
                bg.convert("L").save(f"textures/{die}f{n}-bump.webp", "WEBP", quality=90, method=6)
        print(f"{die}: {min(n, faces)} faces ({kind}, no mask)")


if __name__ == "__main__":
    main()
