"""Make a TINTABLE grayscale stone texture from the full-colour stone.webp.

The decal sets want the stone colour to come from the colorset (recolourable), not be
locked in a colour image. A grayscale texture composited "multiply" over the colorset
`background` lets that background colour tint the stone live (incl. the DSN per-die
"Dice Color" picker). We keep the stone grain but lift it into a light range [0.62..1.0]
so the multiply tint stays close to the chosen colour instead of darkening it to mud.
"""
from pathlib import Path

from PIL import Image

MOD = Path(__file__).resolve().parents[1]
SRC = MOD / "textures" / "stone.webp"
DST = MOD / "textures" / "stone-tint.webp"

LO, HI = 0.62, 1.0   # output luminance range for multiply tinting


def main():
    g = Image.open(SRC).convert("L")
    px = g.load()
    w, h = g.size
    lo_v = min(px[x, y] for y in range(h) for x in range(w))
    hi_v = max(px[x, y] for y in range(h) for x in range(w))
    span = (hi_v - lo_v) or 1
    out = Image.new("L", (w, h))
    op = out.load()
    for y in range(h):
        for x in range(w):
            n = (px[x, y] - lo_v) / span          # normalise grain to 0..1
            op[x, y] = int(round((LO + (HI - LO) * n) * 255))
    out.convert("RGB").save(DST, "WEBP", quality=92)
    print(f"wrote {DST} ({w}x{h}) range {LO}-{HI}")


if __name__ == "__main__":
    main()
