#!/usr/bin/env python3
"""Extract, for every Dice So Nice die shape, the face polygon in CELL-LOCAL [0,1]
coordinates (y-down) from the baked geometry object `Na` in dice-so-nice/main.js.

DSN draws each face's label image to fill its square cell, then the flat face samples a
polygon of that cell. These local polygon vertices are the calibration target for warping
custom face art so it fills the face exactly. Output is JSON: shape -> ordered [x,y] verts.
"""
import json
import math
import os
import re

import numpy as np

BASE = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "FoundryVTT",
                    "Data", "modules", "dice-so-nice")
SHAPES = ["d2", "d4", "d6", "d8", "d10", "d12", "d14", "d16", "d20", "d24", "d30"]


def load():
    return open(os.path.join(BASE, "main.js"), encoding="utf-8").read()


def grab_array(s, start, name):
    m = re.search(name + r":\{[^\[]*array:\[([-0-9eE.,]+)\]", s[start:start + 600000])
    return [float(x) for x in m.group(1).split(",")] if m else None


def grab_index(s, start):
    m = re.search(r"index:\{[^\[]*array:\[([0-9,]+)\]", s[start:start + 600000])
    return [int(x) for x in m.group(1).split(",")] if m else None


def detect_pitch(centroids_axis):
    """Find cell pitch B=1/n minimizing the variance of (centroid mod B)."""
    best, best_std = None, 1e9
    for n in range(1, 9):
        B = 1.0 / n
        offs = [(c % B) / B for c in centroids_axis]
        # circular std
        ang = np.array(offs) * 2 * math.pi
        r = math.hypot(np.cos(ang).mean(), np.sin(ang).mean())
        std = 1 - r
        if std < best_std - 1e-6:
            best_std, best = std, B
    return best


def main():
    s = load()
    na = s.find("Na=")
    out = {}
    for sh in SHAPES:
        key = s.find(sh + ":", na)
        uv = grab_array(s, key, "uv")
        idx = grab_index(s, key)
        if not uv or not idx:
            out[sh] = {"error": "no uv/index"}
            continue
        pts = [(uv[2 * i], uv[2 * i + 1]) for i in range(len(uv) // 2)]
        tris = [(idx[i], idx[i + 1], idx[i + 2]) for i in range(0, len(idx), 3)]

        def area(t):
            (ax, ay), (bx, by), (cx, cy) = pts[t[0]], pts[t[1]], pts[t[2]]
            return abs((bx - ax) * (cy - ay) - (cx - ax) * (by - ay)) / 2

        areas = [area(t) for t in tris]
        amax = max(areas)
        main = [t for t, a in zip(tris, areas) if a >= 0.4 * amax]

        # group main triangles into faces by shared vertices (connected components)
        parent = {}
        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a, b):
            parent[find(a)] = find(b)
        for t in main:
            union(t[0], t[1]); union(t[1], t[2])
        groups = {}
        for t in main:
            groups.setdefault(find(t[0]), set()).update(t)
        faces = [sorted(g) for g in groups.values()]

        # per-face centroid (of its vertices)
        fcent = []
        for f in faces:
            xs = [pts[i][0] for i in f]; ys = [pts[i][1] for i in f]
            fcent.append((sum(xs) / len(xs), sum(ys) / len(ys)))
        Bu = detect_pitch([c[0] for c in fcent])
        Bv = detect_pitch([c[1] for c in fcent])
        B = round((Bu + Bv) / 2, 6)

        # local polygon per face, anchored to the cell containing the face's min corner
        def local_poly(f):
            us = [pts[i][0] for i in f]; vs = [pts[i][1] for i in f]
            ox = math.floor((min(us) / B) + 1e-6) * B
            oy = math.floor((min(vs) / B) + 1e-6) * B
            poly = [((pts[i][0] - ox) / B, (pts[i][1] - oy) / B) for i in f]
            cx = sum(p[0] for p in poly) / len(poly); cy = sum(p[1] for p in poly) / len(poly)
            poly.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
            # rotate so the first vertex is the topmost (lowest y) for a stable order
            k0 = min(range(len(poly)), key=lambda k: (poly[k][1], poly[k][0]))
            return poly[k0:] + poly[:k0]

        polys = [local_poly(f) for f in faces]
        # group faces by rounded signature (distinct orientations)
        from collections import defaultdict
        groups2 = defaultdict(list)
        for p in polys:
            sig = tuple((round(x, 1), round(y, 1)) for x, y in p)
            groups2[sig].append(p)
        variants = []
        for sig, plist in sorted(groups2.items(), key=lambda kv: -len(kv[1])):
            nv = len(plist[0])
            avg = [[round(sum(p[k][0] for p in plist) / len(plist), 4),
                    round(sum(p[k][1] for p in plist) / len(plist), 4)] for k in range(nv)]
            dev = max(math.hypot(p[k][0] - avg[k][0], p[k][1] - avg[k][1])
                      for p in plist for k in range(nv))
            variants.append({"count": len(plist), "polygon": avg, "max_dev": round(dev, 4)})
        out[sh] = {"faces": len(faces), "cell_pitch_B": round(B, 4),
                   "orientations": len(variants), "variants": variants}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
