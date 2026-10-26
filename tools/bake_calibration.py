#!/usr/bin/env python3
"""Bake per-die calibration (scale + offset) into real .webp face textures.

Dice So Nice only treats a face label as an image when its PATH ends in
.png/.jpg/.jpeg/.gif/.webp — it cannot consume a composed data: URL (that gets
drawn as text and the face fails to load). So instead of transforming images in
the browser at load time, we transform them here into real files under
textures/_fit/ and let the module load those by path.

The transform is IDENTICAL to the 2D preview in tools/dice-fit/index.html:

    s  = W * scale                       # scaled size, about the centre
    dx = (W - s) / 2 + offsetX * W       # offset as a fraction of the cell
    dy = (W - s) / 2 + offsetY * W       # +offsetY moves the art DOWN

Reads:  data/calibration.json   (written by tools/dice-fit/index.html)
Writes: textures/_fit/<same relative paths>.webp   (only for non-identity dice)
        data/baked.json         (list of die types that now have baked textures)

Run after changing calibration, then RELOAD THE WORLD in Foundry to see it.

    python tools/bake_calibration.py
"""
import json
import shutil
from pathlib import Path

from PIL import Image

MODULE = Path(__file__).resolve().parent.parent
TEX = MODULE / "textures"
FIT = TEX / "_fit"
CALIB = MODULE / "data" / "calibration.json"
MANIFEST = MODULE / "data" / "baked.json"

# Relative texture base-names per die — mirrors scripts/stonetop-dice.mjs.
# Each entry's color + "-bump" partner is baked with that die's calibration.
def _r(a, b):
    return range(a, b + 1)

DICE = {
    "d2":  [f"d2f{n}" for n in _r(1, 2)],
    "d4":  [f"d4bg{n}" for n in _r(1, 4)],          # d4 full-face backgrounds
    "d6":  [f"face{n}" for n in _r(1, 6)],
    "d8":  [f"d8face{n}" for n in _r(1, 8)],
    "d10": [f"d10f{n}" for n in _r(1, 10)],
    "d12": [f"d12f{n}" for n in _r(1, 12)],
    "d20": [f"d20f{n}" for n in _r(1, 20)],
}
# Extra color faces that reuse another die's calibration + bump maps.
# (calibKey, [color relative paths], bump base-names)
DECAL = ("d20", [f"decal/d20f{n}" for n in _r(1, 20)], [f"d20f{n}" for n in _r(1, 20)])

EPS = 1e-4


def is_identity(t):
    return abs(t.get("scale", 1) - 1) < EPS and abs(t.get("offsetX", 0)) < EPS and abs(t.get("offsetY", 0)) < EPS


def transform(src: Path, dst: Path, t: dict, is_bump: bool):
    img = Image.open(src).convert("RGBA")
    w, h = img.size
    s = max(1, round(w * t.get("scale", 1)))
    resized = img.resize((s, s), Image.LANCZOS)
    # Color faces: transparent margin so the stone colorset shows through.
    # Bump maps: neutral grey (128) margin = flat, so scaling down adds no false depth.
    bg = (128, 128, 128, 255) if is_bump else (0, 0, 0, 0)
    canvas = Image.new("RGBA", (w, h), bg)
    dx = round((w - s) / 2 + t.get("offsetX", 0) * w)
    dy = round((h - s) / 2 + t.get("offsetY", 0) * h)
    canvas.alpha_composite(resized, (dx, dy))
    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst, "WEBP", quality=92)


def jobs_for(die_type, color_rels, bump_bases):
    """Yield (relative_path, is_bump) pairs for one die."""
    for rel in color_rels:
        yield rel, False
    for base in bump_bases:
        yield f"{base}-bump", True


def bake():
    """Bake all non-identity dice. Returns {baked, total, log} — also used by tools/serve.py."""
    if not CALIB.exists():
        raise FileNotFoundError(f"Brak {CALIB} — najpierw zapisz kalibrację z tools/dice-fit/index.html.")
    calib = json.loads(CALIB.read_text(encoding="utf-8"))

    # Fresh _fit/ every run, so it always matches the current calibration.
    if FIT.exists():
        shutil.rmtree(FIT)

    baked = []
    total = 0
    log = []
    for die_type, names in DICE.items():
        t = calib.get(die_type)
        if not t or is_identity(t):
            continue
        seen = set()
        for rel, is_bump in jobs_for(die_type, names, names):
            if rel in seen:
                continue
            seen.add(rel)
            src = TEX / f"{rel}.webp"
            if not src.exists():
                log.append(f"! pomijam (brak pliku): {rel}.webp")
                continue
            transform(src, FIT / f"{rel}.webp", t, is_bump)
            total += 1
        baked.append(die_type)
        log.append(f"{die_type}: scale={t.get('scale', 1)} offset=({t.get('offsetX', 0)},{t.get('offsetY', 0)}) — {len(seen)} plik(ów)")

    # Decal color faces reuse the d20 calibration (their bumps are the shared d20 bumps,
    # already baked above when d20 is non-identity).
    dkey, dcolor, _dbump = DECAL
    dt = calib.get(dkey)
    if dt and not is_identity(dt):
        for rel in dcolor:
            src = TEX / f"{rel}.webp"
            if not src.exists():
                log.append(f"! pomijam decal (brak pliku): {rel}.webp")
                continue
            transform(src, FIT / f"{rel}.webp", dt, False)
            total += 1
        log.append(f"decal({dkey}): {len(dcolor)} plik(ów)")

    MANIFEST.write_text(json.dumps(sorted(baked)) + "\n", encoding="utf-8")
    return {"baked": sorted(baked), "total": total, "log": log}


def main():
    r = bake()
    for line in r["log"]:
        print("  " + line)
    print(f"\nWypalono {r['total']} tekstur do {FIT}")
    print(f"Manifest: {MANIFEST} -> {r['baked']}")
    print("Przeładuj świat w Foundry, aby zastosować (DSN rejestruje presety przy diceSoNiceReady).")


if __name__ == "__main__":
    main()
