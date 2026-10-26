#!/usr/bin/env python3
"""Warp each generated die face onto its DSN UV polygon using DETECTED corners of the
actual art (convex hull reduced to N vertices) -> the UV polygon, with a single
whole-image transform and NO masking. This is the d8 method generalised to kites and
pentagons, so the art lands where DSN actually samples it.
"""
import math
import numpy as np
from PIL import Image
from slice_faces import chroma_key, feather_alpha

SIZE = 512

# TRUE UV target polygons (cell-local), from extract_face_polys.py
TGT = {
    "d10": [(0.496, 0.003), (0.86, 0.774), (0.496, 0.955), (0.132, 0.774)],
    "d12": [(0.499, 0.003), (0.991, 0.36), (0.803, 0.937), (0.195, 0.937), (0.008, 0.36)],
    "d20": [(0.501, 0.002), (0.999, 0.864), (0.003, 0.864)],
}
CFG = {"d10": ("tools/gen_d10.png", 5, 2, 10),
       "d12": ("tools/gen_d12.png", 4, 3, 12),
       "d20": ("tools/gen_d20.png", 5, 4, 20)}


def hull(points):
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts
    def cr(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo = []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    up = []
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def reduce_to(poly, n):
    poly = list(poly)
    while len(poly) > n:
        m = len(poly)
        # remove the vertex whose triangle (prev,cur,next) area is smallest
        def tri(i):
            a, b, c = poly[(i-1) % m], poly[i], poly[(i+1) % m]
            return abs((b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]))/2
        i = min(range(m), key=tri)
        poly.pop(i)
    return poly


def order(poly):
    cx = sum(p[0] for p in poly)/len(poly); cy = sum(p[1] for p in poly)/len(poly)
    poly = sorted(poly, key=lambda p: math.atan2(p[1]-cy, p[0]-cx))
    k0 = min(range(len(poly)), key=lambda k: (poly[k][1], poly[k][0]))  # start topmost
    return poly[k0:] + poly[:k0]


def detect(cell, n):
    """Shape-aware, symmetric corner detection (robust vs rounded corners)."""
    a = np.asarray(cell.split()[-1]) > 128
    ys, xs = np.nonzero(a)
    ymin, ymax, xmin, xmax = ys.min(), ys.max(), xs.min(), xs.max()
    if n == 3:  # apex-up triangle: apex = centre of top edge, base = bottom extremes
        apex = (xs[ys <= ymin + 3].mean(), ymin)
        base = ys >= ymax - 3
        return order([apex, (xs[base].max(), ymax), (xs[base].min(), ymax)])
    if n == 4:  # kite: top / right / bottom / left tips
        top = (xs[ys <= ymin + 3].mean(), ymin)
        bottom = (xs[ys >= ymax - 3].mean(), ymax)
        left = (xmin, ys[xs <= xmin + 3].mean())
        right = (xmax, ys[xs >= xmax - 3].mean())
        return order([top, right, bottom, left])
    # general n-gon: convex hull reduced to n
    return order(reduce_to(hull(list(zip(xs.tolist(), ys.tolist()))), n))


def overscan(dst, k=0.02):
    # Grow slightly to cover the bevel seam, but CLAMP to the texture so a wide face
    # (e.g. d20 base at ~0.999) is never pushed off the canvas — that would CLIP the face.
    cx = sum(p[0] for p in dst)/len(dst); cy = sum(p[1] for p in dst)/len(dst)
    pts = [(cx+(x-cx)*(1+k), cy+(y-cy)*(1+k)) for x, y in dst]
    return [(min(max(x, 0.0), SIZE), min(max(y, 0.0), SIZE)) for x, y in pts]


def affine_ls(src, dst):
    D = np.array([[x, y, 1] for x, y in dst], float)
    mx = np.linalg.lstsq(D, np.array([s[0] for s in src]), rcond=None)[0]
    my = np.linalg.lstsq(D, np.array([s[1] for s in src]), rcond=None)[0]
    return (mx[0], mx[1], mx[2], my[0], my[1], my[2])


def perspective(src, dst):
    A, B = [], []
    for (sx, sy), (dx, dy) in zip(src, dst):
        A.append([dx, dy, 1, 0, 0, 0, -sx*dx, -sx*dy]); B.append(sx)
        A.append([0, 0, 0, dx, dy, 1, -sy*dx, -sy*dy]); B.append(sy)
    return tuple(np.linalg.solve(np.array(A, float), np.array(B, float)))


def main():
    for die, (atlas, cols, rows, faces) in CFG.items():
        keyed = feather_alpha(chroma_key(Image.open(atlas).convert("RGB"), 90, 35), 1.0)
        W, H = keyed.size; cw, ch = W//cols, H//rows
        tgt = order([(x*SIZE, y*SIZE) for x, y in TGT[die]])
        n = len(tgt)
        ok = 0
        for r in range(rows):
            for c in range(cols):
                ok += 1
                if ok > faces:
                    break
                cell = keyed.crop((c*cw, r*ch, (c+1)*cw, (r+1)*ch))
                src = detect(cell, n)
                if len(src) != n:
                    print(f"  {die}f{ok}: detected {len(src)} != {n}, skipped"); continue
                dst = overscan(tgt)
                if n == 4:
                    coeffs, mode = perspective(src, dst), Image.PERSPECTIVE
                else:
                    coeffs, mode = affine_ls(src, dst), Image.AFFINE
                face = cell.transform((SIZE, SIZE), mode, coeffs, resample=Image.BICUBIC)
                face.save(f"textures/{die}f{ok}.webp", "WEBP", quality=92, method=6)
                bg = Image.new("RGBA", (SIZE, SIZE), (128, 128, 128, 255)); bg.alpha_composite(face)
                bg.convert("L").save(f"textures/{die}f{ok}-bump.webp", "WEBP", quality=90, method=6)
        print(f"{die}: {min(ok, faces)} faces (detected {n}-gon corners, no mask)")


if __name__ == "__main__":
    main()
