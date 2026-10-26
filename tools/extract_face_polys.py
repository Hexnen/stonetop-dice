#!/usr/bin/env python3
"""Re-extract the TRUE face polygon per DSN die: convex hull (cell-local) of all the
main face triangles in one cell, so kites/pentagons keep their real vertex count.
Prints shape -> ordered hull vertices + count."""
import json
import math
import os
import re

BASE = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "FoundryVTT",
                    "Data", "modules", "dice-so-nice")
SHAPES = ["d4", "d6", "d8", "d10", "d12", "d20", "d2"]


def grab(s, start, name, intt=False):
    m = re.search(name + r":\{[^\[]*array:\[([-0-9eE.,]+)\]", s[start:start + 600000])
    if not m:
        return None
    return [int(x) if intt else float(x) for x in m.group(1).split(",")]


def hull(points):
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo = []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    up = []
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def simplify(poly, tol=0.03):
    """Drop near-collinear / very close vertices."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b, c = poly[(i-1) % n], poly[i], poly[(i+1) % n]
        # distance of b from line a-c
        dx, dy = c[0]-a[0], c[1]-a[1]
        L = math.hypot(dx, dy) + 1e-9
        d = abs((b[0]-a[0])*dy - (b[1]-a[1])*dx)/L
        if d > tol:
            out.append(b)
    return out or poly


def main():
    s = open(os.path.join(BASE, "main.js"), encoding="utf-8").read()
    na = s.find("Na=")
    out = {}
    for sh in SHAPES:
        key = s.find(sh + ":", na)
        uv = grab(s, key, "uv"); idx = grab(s, key, None, True) if False else None
        m = re.search(r"index:\{[^\[]*array:\[([0-9,]+)\]", s[key:key + 600000])
        idx = [int(x) for x in m.group(1).split(",")]
        pts = [(uv[2*i], uv[2*i+1]) for i in range(len(uv)//2)]
        tris = [(idx[i], idx[i+1], idx[i+2]) for i in range(0, len(idx), 3)]
        def area(t):
            (ax, ay), (bx, by), (cx, cy) = pts[t[0]], pts[t[1]], pts[t[2]]
            return abs((bx-ax)*(cy-ay)-(cx-ax)*(by-ay))/2
        amax = max(area(t) for t in tris)
        main = [t for t in tris if area(t) >= 0.18*amax]   # main face triangles (kite=2)
        # pick the cell with the most main triangles -> one representative face
        # group by rounded centroid cell using detected pitch
        cents = []
        for t in main:
            cx = sum(pts[i][0] for i in t)/3; cy = sum(pts[i][1] for i in t)/3
            cents.append((cx, cy, t))
        # pitch guess
        B = {"d2": 0.5, "d4": 0.25, "d6": 0.25, "d8": 0.25, "d10": 0.25,
             "d12": 0.25, "d20": 0.125, "d24": 0.125, "d30": 0.125}[sh]
        from collections import defaultdict
        cells = defaultdict(list)
        for cx, cy, t in cents:
            cells[(math.floor(cx/B), math.floor(cy/B))].append(t)
        best = max(cells.values(), key=len)
        # collect verts, normalize to that cell
        vs = []
        for t in best:
            for i in t:
                vs.append(pts[i])
        ox = math.floor(min(v[0] for v in vs)/B + 1e-6)*B
        oy = math.floor(min(v[1] for v in vs)/B + 1e-6)*B
        loc = [((x-ox)/B, (y-oy)/B) for x, y in vs]
        h = simplify(hull(loc))
        # order from topmost CCW
        cx = sum(p[0] for p in h)/len(h); cy = sum(p[1] for p in h)/len(h)
        h.sort(key=lambda p: math.atan2(p[1]-cy, p[0]-cx))
        k0 = min(range(len(h)), key=lambda k: (h[k][1], h[k][0]))
        h = h[k0:]+h[:k0]
        out[sh] = {"verts": len(h), "tris_in_face": len(best),
                   "polygon": [[round(x, 3), round(y, 3)] for x, y in h]}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
