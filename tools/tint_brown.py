#!/usr/bin/env python3
"""Make a second colour variant of the FULL stonetop set by TINTING the baked stone faces.

The full faces have the parchment stone colour BAKED into the texture (opaque source-over), so a
recolour can't come from the colorset alone — we multiply every COLOUR face toward the target stone
colour (#714e30). Multiply maps the parchment midtone (#cab68c) exactly onto the target while keeping
the carved engraving's relative contrast (dark grooves stay darker, highlights become light brown), so
the numerals + frame stay legible and the 3D carving survives. Bump maps are grayscale heightmaps —
copied unchanged. d4blank (transparent placeholder) copied unchanged.

Tints BOTH textures/<face> and textures/_fit/<face> (tint is geometry-independent, so this matches the
calibrated render without re-baking). Output -> textures/brown/ (+ textures/brown/_fit/).

    python tools/tint_brown.py            # default target #714e30
    python tools/tint_brown.py 8a5a34     # custom hex
"""
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

MOD = Path(__file__).resolve().parent.parent
TEX = MOD / "textures"
OUT = TEX / "brown"

PAPER = np.array([0xCA, 0xB6, 0x8C], float)  # existing parchment stone midtone

# Colour face base-names per die (mirrors tools/bake_calibration.py DICE) + the d4 backgrounds.
FACES = (
    ["d2f1", "d2f2"]
    + [f"d4bg{n}" for n in range(1, 5)]
    + [f"face{n}" for n in range(1, 7)]
    + [f"d8face{n}" for n in range(1, 9)]
    + [f"d10f{n}" for n in range(1, 11)]
    + [f"d12f{n}" for n in range(1, 13)]
    + [f"d20f{n}" for n in range(1, 21)]
)


def tint(src: Path, dst: Path, mult):
    im = Image.open(src).convert("RGBA")
    a = np.asarray(im).astype(float)
    a[..., :3] = np.clip(a[..., :3] * mult, 0, 255)
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a.astype("uint8"), "RGBA").save(dst, "WEBP", quality=92)


def copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def run(target_hex):
    t = target_hex.lstrip("#")
    target = np.array([int(t[i:i + 2], 16) for i in (0, 2, 4)], float)
    mult = target / PAPER
    print(f"target #{t}  multiply={mult.round(3)}")
    if OUT.exists():
        shutil.rmtree(OUT)

    made = skipped = 0
    # For each source root (raw and _fit), tint faces, copy bumps/blank.
    for sub in ("", "_fit"):
        srcdir = TEX / sub if sub else TEX
        for base in FACES:
            f = srcdir / f"{base}.webp"
            b = srcdir / f"{base}-bump.webp"
            if f.exists():
                tint(f, OUT / sub / f"{base}.webp", mult); made += 1
            elif sub == "":
                print(f"  ! missing colour face: {base}.webp"); skipped += 1
            if b.exists():
                copy(b, OUT / sub / f"{base}-bump.webp"); made += 1
    # transparent d4 label placeholder (shared, untinted)
    if (TEX / "d4blank.webp").exists():
        copy(TEX / "d4blank.webp", OUT / "d4blank.webp")
    # stone body texture: tint colour, copy heightmap
    if (TEX / "stone.webp").exists():
        tint(TEX / "stone.webp", OUT / "stone.webp", mult); made += 1
    if (TEX / "stone-bump.webp").exists():
        copy(TEX / "stone-bump.webp", OUT / "stone-bump.webp")
    print(f"wrote {made} files -> {OUT}  ({skipped} missing)")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "714e30")
