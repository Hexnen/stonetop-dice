#!/usr/bin/env python3
"""Slice a 3x2 d6 atlas into 6 square face textures + bump maps for Dice So Nice.

The atlas is expected on a GREEN-SCREEN background. Green is keyed out to transparency
(chroma key) — far cleaner than keying black, which collides with the dice's dark border
and crack lines. Faces are auto-detected from the keyed alpha, then padded (never cropped)
onto a shared square so every face keeps all its art at a uniform scale.

Output per face (faces numbered left->right, top->bottom = 1..6):
    faceN.webp        (RGBA, art with transparent surround; green despilled)
    faceN-bump.webp   (grayscale; dark engraved spirals read as recessed)

Usage:
    python slice_faces.py <green-source> [out_dir] [--size 512 --pad 10
                                                    --key-g 90 --key-d 35 --feather 1]
"""
import argparse
import os
import numpy as np
from PIL import Image, ImageFilter


def chroma_key(rgb, key_g, key_d):
    """Return an RGBA image with green background keyed to alpha 0 and green despilled.
    A pixel is background when green is bright AND clearly exceeds red and blue."""
    a = np.asarray(rgb.convert("RGB")).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    is_green = (g >= key_g) & ((g - r) >= key_d) & ((g - b) >= key_d)
    # Despill: clamp green to the max of red/blue on kept pixels (kills edge fringe tint).
    spill_cap = np.maximum(r, b)
    g2 = np.where(g > spill_cap, spill_cap, g)
    out = np.dstack([r, g2, b, np.where(is_green, 0, 255)]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def feather_alpha(img, radius):
    if radius <= 0:
        return img
    r, g, b, alpha = img.split()
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius))
    return Image.merge("RGBA", (r, g, b, alpha))


def detect_bands(values, on_threshold):
    bands, start = [], None
    for i, v in enumerate(values):
        if v > on_threshold and start is None:
            start = i
        elif v <= on_threshold and start is not None:
            bands.append((start, i - 1))
            start = None
    if start is not None:
        bands.append((start, len(values) - 1))
    return bands


def detect_face_boxes(keyed):
    """Row/column bands of opaque (non-keyed) content -> face box intersections."""
    alpha = np.asarray(keyed.split()[-1]) > 128
    h, w = alpha.shape
    rows = detect_bands(alpha.sum(axis=1), w * 0.04)
    cols = detect_bands(alpha.sum(axis=0), h * 0.04)
    boxes = [(x0, y0, x1 + 1, y1 + 1) for (y0, y1) in rows for (x0, x1) in cols]
    return boxes, len(rows), len(cols)


def autocrop_alpha(img):
    bbox = img.split()[-1].getbbox()
    return img.crop(bbox) if bbox else img


def pad_to_square(img, side):
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    w, h = img.size
    canvas.paste(img, ((side - w) // 2, (side - h) // 2))
    return canvas


def make_bump(face):
    """Composite over mid-gray so transparent surround is neutral, then grayscale."""
    bg = Image.new("RGBA", face.size, (128, 128, 128, 255))
    bg.alpha_composite(face)
    return bg.convert("L")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("out_dir", nargs="?", default=None)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--pad", type=int, default=10)
    ap.add_argument("--key-g", type=int, default=90, dest="key_g")
    ap.add_argument("--key-d", type=int, default=35, dest="key_d")
    ap.add_argument("--feather", type=float, default=1.0)
    ap.add_argument("--fill", action="store_true",
                    help="stretch each face's art to fill the whole square (no transparent "
                         "margin) so it covers the entire die face in Dice So Nice")
    args = ap.parse_args()

    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.source))
    os.makedirs(out_dir, exist_ok=True)

    src = Image.open(args.source).convert("RGB")
    keyed = feather_alpha(chroma_key(src, args.key_g, args.key_d), args.feather)
    W, H = keyed.size

    boxes, nrows, ncols = detect_face_boxes(keyed)
    print(f"detected {nrows} rows x {ncols} cols = {len(boxes)} faces")
    if len(boxes) != 6:
        print("WARNING: expected 6 faces; adjust --key-g/--key-d")

    arts = []
    for (x0, y0, x1, y1) in boxes:
        bx = (max(0, x0 - args.pad), max(0, y0 - args.pad),
              min(W, x1 + args.pad), min(H, y1 + args.pad))
        arts.append(autocrop_alpha(keyed.crop(bx)))

    side = max(max(a.size) for a in arts)  # pad-only -> never clips any face

    for i, art in enumerate(arts, start=1):
        if args.fill:
            square = art.resize((args.size, args.size), Image.LANCZOS)  # bleed to all edges
        else:
            square = pad_to_square(art, side).resize((args.size, args.size), Image.LANCZOS)
        fpath = os.path.join(out_dir, f"face{i}.webp")
        bpath = os.path.join(out_dir, f"face{i}-bump.webp")
        square.save(fpath, "WEBP", quality=92, method=6)
        make_bump(square).save(bpath, "WEBP", quality=90, method=6)
        print(f"face{i}: art {art.size} -> square {side} ({fpath})")

    print(f"Done: {len(arts)} faces -> {out_dir}")


if __name__ == "__main__":
    main()
