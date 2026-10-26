#!/usr/bin/env python3
"""Warp a generated triangular d8 atlas so each triangle's tips land EXACTLY on the
d8 face UV triangle that Dice So Nice samples. The target triangle (cell-local, y-down)
was read from DSN's baked geometry Na["d8"]:

    apex      = (0.501, 0.002)
    base-left = (0.034, 0.810)
    base-right= (0.968, 0.810)

DSN draws the label image across the whole p x p face cell, then the flat face samples
only this triangle. Aligning the art's 3 corners to it makes the stone fill the face
with no gap and no cut.

Usage:
    python warp_d8.py <green_tri_atlas> <out_dir> [--size 512 --cols 4 --rows 2]
"""
import argparse
import os
import numpy as np
from PIL import Image, ImageDraw

# DSN d8 face triangle in cell-local [0,1] coords (y down), from Na["d8"].
APEX = (0.501, 0.002)
BL = (0.034, 0.810)
BR = (0.968, 0.810)


def key_green(rgb, key_g=90, key_d=35):
    a = np.asarray(rgb.convert("RGB")).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    is_green = (g >= key_g) & ((g - r) >= key_d) & ((g - b) >= key_d)
    spill = np.maximum(r, b)
    g2 = np.where(g > spill, spill, g)
    out = np.dstack([r, g2, b, np.where(is_green, 0, 255)]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def find_corners(cell):
    """Apex (topmost) + two base corners (bottom-most extremes) of the keyed triangle."""
    a = np.asarray(cell.split()[-1]) > 128
    ys, xs = np.nonzero(a)
    ymin, ymax = ys.min(), ys.max()
    apex_x = xs[ys <= ymin + 3].mean()
    base = ys >= ymax - 4
    bl_x = xs[base].min()
    br_x = xs[base].max()
    return [(apex_x, ymin), (bl_x, ymax), (br_x, ymax)]


def affine_out_to_in(src, dst):
    """PIL AFFINE wants output->input. Solve src = M * [dst,1]; return 6 coeffs."""
    D = np.array([[dst[i][0], dst[i][1], 1] for i in range(3)], float)
    sx = np.array([src[i][0] for i in range(3)], float)
    sy = np.array([src[i][1] for i in range(3)], float)
    cx = np.linalg.solve(D, sx)
    cy = np.linalg.solve(D, sy)
    return (cx[0], cx[1], cx[2], cy[0], cy[1], cy[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("atlas")
    ap.add_argument("out_dir")
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--rows", type=int, default=2)
    ap.add_argument("--overscan", type=float, default=0.015,
                    help="grow target triangle slightly so edges/bevel show no seam")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    S = args.size
    # target corners in pixels, grown slightly about the centroid
    tri = np.array([APEX, BL, BR]) * S
    c = tri.mean(axis=0)
    tri = c + (tri - c) * (1 + args.overscan)
    dst = [tuple(p) for p in tri]
    print("target px:", [(round(x, 1), round(y, 1)) for x, y in dst])

    atlas = Image.open(args.atlas).convert("RGB")
    W, H = atlas.size
    cw, ch = W // args.cols, H // args.rows
    n = 0
    for r in range(args.rows):
        for col in range(args.cols):
            n += 1
            cell = key_green(atlas.crop((col * cw, r * ch, (col + 1) * cw, (r + 1) * ch)))
            src = find_corners(cell)
            coeffs = affine_out_to_in(src, dst)
            warped = cell.transform((S, S), Image.AFFINE, coeffs, resample=Image.BICUBIC)
            warped.save(os.path.join(args.out_dir, f"d8face{n}.webp"), "WEBP",
                        quality=92, method=6)
            # bump: grayscale of the warped art on neutral gray
            bg = Image.new("RGBA", (S, S), (128, 128, 128, 255))
            bg.alpha_composite(warped)
            bg.convert("L").save(os.path.join(args.out_dir, f"d8face{n}-bump.webp"),
                                 "WEBP", quality=90, method=6)
            print(f"d8face{n}: src {[(round(x),round(y)) for x,y in src]}")
    print(f"Done -> {args.out_dir}")


if __name__ == "__main__":
    main()
