"""New d8 DECAL set with Norse Bold numerals.

Per the standing rules: build from the d8 face-template (exact DSN polygon outline),
generate the whole die in ONE image2 call, and keep all art STRICTLY INSIDE the outline.
image2 only carves the decorative border frame + surface details (dark grooves + bright
highlights) on a green screen — NO stone fill. The numeral is rendered DETERMINISTICALLY
in Norse Bold (image2 corrupts glyphs) and embossed as a carved decal afterwards. Green
is then keyed out -> transparent "frame + details + digit" decal.

    python tools/make_d8_norse.py            # full pipeline (1 image2 call)
    python tools/make_d8_norse.py --prep     # build the green input montage only, no API
"""
import base64
import io
import math
import re
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

MODULE = Path(__file__).resolve().parents[1]
TEX = MODULE / "textures"
OUT = TEX / "decal-norse"
RAW = OUT / "_raw"
FONT = str(MODULE / "tools" / "norse_font" / "Norse-Bold.otf")

API_URL = "https://api.openai.com/v1/images/edits"
MODEL = "gpt-image-2"
QUALITY = "high"

GREEN = (0, 255, 0)
CELL = 400
COLS, ROWS = 4, 2
FACES = 8
# DSN d8 face polygon (cell-local [0,1], y-down) — from the skill's dsn-face-uv.json.
POLY = [(0.503, 0.003), (0.968, 0.808), (0.038, 0.808)]

INK = (22, 17, 11)
HI = (236, 228, 206)

PROMPT = (
    "This is a grid of empty triangular die-face outlines on a pure green background. Carve a "
    "decorative STONE-ENGRAVING DECAL inside each triangle: (1) a decorative carved border frame "
    "running just inside the triangle edge, and (2) subtle carved surface details/cracks. "
    "CRITICAL  IDENTICAL FRAME: use ONE single border-frame design and repeat it EXACTLY the same on "
    "ALL 8 triangles  same motifs, same thickness, same spacing, same placement. Every face must be "
    "indistinguishable from the others (the numeral, added later, is the ONLY thing that will differ). "
    "Do NOT invent a different frame per face. Render everything as dark near-black incised grooves "
    "PLUS bright near-white raised highlights along them, so it reads as chiselled stone with depth. "
    "Add NO stone fill and NO shading of the open area  keep the inner field and all space between "
    "faces one pure, uniform, saturated chroma-green (RGB 0,255,0): clean green screen, no gradient, "
    "no shadow. Keep the CENTRE of each triangle clear (a numeral is added later). Nothing may cross "
    "or touch the triangle outline  all carving stays strictly inside it. Same 4x2 grid, same "
    "positions. No text, no numerals, no watermark."
)


def api_key() -> str:
    m = re.search(r"OPENAI_API\s*=\s*(\S+)", (MODULE / "image2api.txt").read_text(encoding="utf-8"))
    if not m:
        sys.exit("No OPENAI_API key in image2api.txt")
    return m.group(1)


def poly_px(x0, y0):
    return [(x0 + x * CELL, y0 + y * CELL) for x, y in POLY]


def incenter_px():
    """Incircle centre + radius of the face polygon (cell-local), for numeral placement."""
    pts = [(x * CELL, y * CELL) for x, y in POLY]

    def inside(px, py):
        ins, n, j = False, len(pts), len(pts) - 1
        for i in range(n):
            xi, yi = pts[i]; xj, yj = pts[j]
            if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi:
                ins = not ins
            j = i
        return ins

    def edist(px, py):
        best = 1e9
        for i in range(len(pts)):
            ax, ay = pts[i]; bx, by = pts[(i + 1) % len(pts)]
            dx, dy = bx - ax, by - ay
            t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-9)))
            best = min(best, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
        return best

    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    best, bc, br = -1, (sum(xs) / 3, sum(ys) / 3), 1
    for _ in range(3):
        step = (x1 - x0) / 28 or 1
        gx = x0
        while gx <= x1:
            gy = y0
            while gy <= y1:
                if inside(gx, gy):
                    d = edist(gx, gy)
                    if d > best:
                        best, bc, br = d, (gx, gy), d
                gy += step
            gx += step
        x0, x1, y0, y1 = bc[0] - step * 2, bc[0] + step * 2, bc[1] - step * 2, bc[1] + step * 2
    return bc, br


def build_input():
    """Green montage of empty d8 outlines (the frame guide image2 carves within)."""
    w, h = COLS * CELL, ROWS * CELL
    img = Image.new("RGBA", (w, h), GREEN + (255,))
    d = ImageDraw.Draw(img)
    for i in range(FACES):
        x0, y0 = (i % COLS) * CELL, (i // COLS) * CELL
        d.polygon(poly_px(x0, y0), outline=(20, 20, 24, 255), width=5)
    return img


def carved_numeral(text, target_h):
    """Norse Bold numeral as a carved decal: dark glyph + offset light highlight."""
    f = ImageFont.truetype(FONT, 260)
    pad = 360
    mask = Image.new("L", (pad, pad), 0)
    md = ImageDraw.Draw(mask)
    bb = md.textbbox((0, 0), text, font=f)
    md.text(((pad - (bb[2] - bb[0])) // 2 - bb[0], (pad - (bb[3] - bb[1])) // 2 - bb[1]),
            text, font=f, fill=255)
    layer = Image.new("RGBA", (pad, pad), (0, 0, 0, 0))
    hi = Image.new("RGBA", (pad, pad), (0, 0, 0, 0)); hi.paste(HI + (255,), (0, 0), mask)
    layer.alpha_composite(hi.transform(hi.size, Image.AFFINE, (1, 0, -3, 0, 1, -3)))  # highlight up-left
    dk = Image.new("RGBA", (pad, pad), (0, 0, 0, 0)); dk.paste(INK + (255,), (0, 0), mask)
    layer.alpha_composite(dk)
    layer = layer.crop(layer.getbbox())
    s = target_h / layer.height
    return layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))), Image.LANCZOS)


def chroma_key(img, thresh=90):
    img = img.convert("RGBA"); px = img.load(); w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if g > 100 and g - r > thresh and g - b > thresh:
                px[x, y] = (r, g, b, 0)
            elif g > r and g > b:
                px[x, y] = (r, max(r, b), b, a)
    return img


def generate(montage, key):
    buf = io.BytesIO(); montage.convert("RGB").save(buf, "PNG"); buf.seek(0)
    r = requests.post(API_URL, headers={"Authorization": f"Bearer {key}"},
                      files=[("image[]", ("d8.png", buf, "image/png"))],
                      data={"model": MODEL, "prompt": PROMPT, "size": f"{COLS*CELL}x{ROWS*CELL}",
                            "quality": QUALITY, "background": "opaque"}, timeout=300)
    if not r.ok:
        sys.exit(f"API error {r.status_code}: {r.text[:600]}")
    return base64.b64decode(r.json()["data"][0]["b64_json"])


def main():
    prep = "--prep" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True); RAW.mkdir(parents=True, exist_ok=True)
    montage = build_input()
    montage.save(RAW / "d8_input.png")
    if prep:
        print(f"PREP only -> {RAW / 'd8_input.png'} (no API)"); return

    raw = generate(montage, api_key())
    (RAW / "d8_out.png").write_bytes(raw)
    grid = Image.open(io.BytesIO(raw)).convert("RGBA")
    (cx, cy), r = incenter_px()
    for i in range(FACES):
        col, row = i % COLS, i // COLS
        cell = grid.crop((col * CELL, row * CELL, col * CELL + CELL, row * CELL + CELL))
        cell = chroma_key(cell)
        num = carved_numeral(str(i + 1), target_h=r * 1.15)   # fit within the incircle
        cell.alpha_composite(num, (int(cx - num.width / 2), int(cy - num.height / 2)))
        cell.save(OUT / f"d8nf{i + 1}.webp", "WEBP", lossless=True)
        print(f"  d8nf{i + 1}")
    print(f"done -> {OUT}")


if __name__ == "__main__":
    main()
