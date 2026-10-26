"""
Stonetop dice -> "carved stone DECAL" generator (whole-die montage mode).

For each die we compose ALL of its faces into a single grid montage on a pure
chroma-green field, send that ONE image to gpt-image-2, and ask it to return only
the dark engraved lines + light highlights (no stone fill colour) on the same
green. We then slice the returned grid into per-face cells and key the green out
to alpha -> transparent "detail + depth" decals. The stone colour is supplied
later by Dice So Nice underneath the decal.

ONE API call per die (not per face) -- cost is per call, so a whole die costs the
same as a single face. Because we chroma-key, the slice does not need to be tight:
generous green margins around each triangle simply become transparent.

Usage:
    python tools/make_decals.py d20          # one or more die ids
    python tools/make_decals.py --all        # every die
    python tools/make_decals.py d20 --raw-only   # keep the green montage, skip slicing
"""
import base64
import io
import os
import re
import sys
from pathlib import Path

import requests
from PIL import Image

MODULE = Path(__file__).resolve().parents[1]
TEX = MODULE / "textures"
OUT = TEX / "decal"
RAW = OUT / "_raw"

API_URL = "https://api.openai.com/v1/images/edits"
MODEL = "gpt-image-2"
QUALITY = "high"

GREEN = (0, 255, 0)
CELL = 400          # per-face cell (incl. margin) in the montage
FACE = 340          # source face is scaled to fit this inside the cell
LINE_THRESH = 135   # luminance below this is treated as engraving line (edges + digits)

# die id -> (ordered face base-names, (cols, rows))
DICE = {
    "d2":  ([f"d2f{n}" for n in range(1, 3)],            (2, 1)),
    "d4":  ([f"d4bg{n}" for n in range(1, 5)],           (2, 2)),
    "d6":  ([f"face{n}" for n in range(1, 7)],           (3, 2)),
    "d8":  ([f"d8face{n}" for n in range(1, 9)],         (4, 2)),
    "d10": ([f"d10f{n}" for n in range(1, 11)],          (5, 2)),
    "d12": ([f"d12f{n}" for n in range(1, 13)],          (4, 3)),
    "d20": ([f"d20f{n}" for n in range(1, 21)],          (5, 4)),
}

PROMPT = (
    "This is a grid of line drawings of die faces on a green background: only the dark "
    "outline edges of each die face and the numerals are drawn  the faces are otherwise "
    "empty. Reproduce every drawing in EXACTLY the same grid position, size and shape. "
    "Render each as a carved-stone engraving: keep the dark incised lines (edges + numerals) "
    "as solid dark near-black grooves, and ADD bright raised highlights running along those "
    "lines as light near-white edges, so the lines read as chiselled into stone with real "
    "depth. Add NO stone fill, NO texture, NO shading inside the empty faces  the interior "
    "and all space between faces must stay one pure, uniform, saturated chroma-green "
    "(RGB 0,255,0): a clean green screen, no gradient, no shadow. Do NOT change, restyle, "
    "re-letter, add or move any numeral: keep the exact same digits and layout as the input. "
    "No new text, no watermark. Flat 2D line+highlight decals on solid green, same count and "
    "arrangement as the input grid. CRITICAL: every face's art must stay STRICTLY INSIDE its outline "
    " nothing (lines, highlights, numerals) may cross or extend past the drawn face edge; the outline "
    "is the visible face boundary and anything outside it is invalid."
)


def api_key() -> str:
    txt = (MODULE / "image2api.txt").read_text(encoding="utf-8")
    m = re.search(r"OPENAI_API\s*=\s*(\S+)", txt)
    if not m:
        sys.exit("No OPENAI_API key found in image2api.txt")
    return m.group(1)


def round16(n: int) -> int:
    return max(16, (n // 16) * 16)


def extract_lines(src: Path, thresh: int = LINE_THRESH) -> Image.Image:
    """Keep ONLY the dark engraving (edges + digits); everything else -> transparent.

    No stone fill, no parchment 'wzr', no background. Alpha scales with how dark a
    pixel is, so line edges stay smooth; the line itself is kept near-black."""
    img = Image.open(src).convert("RGBA")
    px = img.load()
    w, h = img.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if lum < thresh:
                # darker -> more opaque; clamp to a strong line
                alpha = int(min(255, (thresh - lum) / thresh * 255 * 1.6))
                op[x, y] = (20, 16, 10, alpha)   # near-black engraving line
    return out


def build_montage(names, cols, rows) -> tuple[Image.Image, tuple[int, int]]:
    """Empty faces: only extracted edges+digits, composited onto the green key field."""
    w, h = cols * CELL, rows * CELL
    canvas = Image.new("RGBA", (w, h), GREEN + (255,))
    for i, name in enumerate(names):
        src = TEX / f"{name}.webp"
        if not src.exists():
            sys.exit(f"Missing source texture: {src}")
        face = extract_lines(src)
        face.thumbnail((FACE, FACE), Image.LANCZOS)
        cx = (i % cols) * CELL + (CELL - face.width) // 2
        cy = (i // cols) * CELL + (CELL - face.height) // 2
        canvas.alpha_composite(face, (cx, cy))
    return canvas, (w, h)


def generate(montage: Image.Image, out_size: tuple[int, int], key: str) -> bytes:
    buf = io.BytesIO()
    montage.convert("RGB").save(buf, "PNG")
    buf.seek(0)
    size = f"{round16(out_size[0])}x{round16(out_size[1])}"
    r = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {key}"},
        files=[("image[]", ("montage.png", buf, "image/png"))],
        data={"model": MODEL, "prompt": PROMPT, "size": size,
              "quality": QUALITY, "background": "opaque"},
        timeout=300,
    )
    if not r.ok:
        sys.exit(f"API error {r.status_code}: {r.text[:600]}")
    return base64.b64decode(r.json()["data"][0]["b64_json"])


def chroma_key(img: Image.Image, thresh: int = 90) -> Image.Image:
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if g > 100 and g - r > thresh and g - b > thresh:
                px[x, y] = (r, g, b, 0)          # key out green
            elif g > r and g > b:
                px[x, y] = (r, max(r, b), b, a)  # despill
    return img


def slice_and_key(raw: bytes, names, cols, rows):
    grid = Image.open(io.BytesIO(raw)).convert("RGBA")
    gw, gh = grid.size
    cw, ch = gw / cols, gh / rows
    OUT.mkdir(parents=True, exist_ok=True)
    for i, name in enumerate(names):
        cx, cy = (i % cols) * cw, (i // cols) * ch
        cell = grid.crop((round(cx), round(cy), round(cx + cw), round(cy + ch)))
        keyed = chroma_key(cell)
        dest = OUT / f"{name}.webp"
        keyed.save(dest, "WEBP", lossless=True)
        print(f"  {name} -> {dest.name}")


def process(die: str, key, raw_only: bool = False, prep: bool = False):
    if die not in DICE:
        sys.exit(f"Unknown die '{die}'. Known: {', '.join(DICE)}")
    names, (cols, rows) = DICE[die]
    montage, size = build_montage(names, cols, rows)
    RAW.mkdir(parents=True, exist_ok=True)
    montage.save(RAW / f"{die}_montage_in.png")
    # also a white-bg preview so faint lines are easy to judge by eye
    Image.alpha_composite(Image.new("RGBA", montage.size, (255, 255, 255, 255)),
                          chroma_key(montage.copy())).convert("RGB").save(
        RAW / f"{die}_montage_in_preview.png")
    if prep:
        print(f"[{die}] PREP only -> {RAW / (die + '_montage_in.png')} "
              f"(+ _preview.png). No API call.")
        return
    print(f"[{die}] montage {cols}x{rows} ({len(names)} faces) -> generating...")
    raw = generate(montage, size, key)
    (RAW / f"{die}_out.png").write_bytes(raw)
    print(f"[{die}] raw -> {RAW / (die + '_out.png')}")
    if not raw_only:
        slice_and_key(raw, names, cols, rows)


def main():
    args = sys.argv[1:]
    raw_only = "--raw-only" in args
    prep = "--prep" in args
    dice = list(DICE) if "--all" in args else [a for a in args if not a.startswith("--")]
    if not dice:
        sys.exit(__doc__)
    key = None if prep else api_key()
    for d in dice:
        process(d, key, raw_only=raw_only, prep=prep)


if __name__ == "__main__":
    main()
