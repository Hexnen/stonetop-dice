#!/usr/bin/env python3
"""Re-slice the d6 atlas, aligned to the DSN d6 face UV polygon.

The d6 face samples the cell from ~0.013..0.990 (not the full 0..1), so the tile art is
fit into that inset rectangle of the 512 texture instead of bleeding to the very edges.
That puts the tile's edge spikes exactly on the cube-face edges (no clip, no gap).

Usage:
    python build_d6_aligned.py <green_atlas> <out_dir>
"""
import os
import sys
from PIL import Image, ImageFilter
from slice_faces import chroma_key, feather_alpha, detect_face_boxes, autocrop_alpha

SIZE = 512
# d6 face polygon (cell-local) from references/dsn-face-uv.json
X0, Y0, X1, Y1 = 0.013, 0.012, 0.990, 0.989


def make_bump(face):
    bg = Image.new("RGBA", face.size, (128, 128, 128, 255))
    bg.alpha_composite(face)
    return bg.convert("L")


def main():
    atlas_path, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    keyed = feather_alpha(chroma_key(Image.open(atlas_path).convert("RGB"), 90, 35), 1.0)
    W, H = keyed.size
    boxes, nr, nc = detect_face_boxes(keyed)
    print(f"detected {nr}x{nc} = {len(boxes)} faces")

    tx0, ty0 = round(X0 * SIZE), round(Y0 * SIZE)
    tw, th = round((X1 - X0) * SIZE), round((Y1 - Y0) * SIZE)
    print(f"target rect: ({tx0},{ty0}) size {tw}x{th}")

    for i, (x0, y0, x1, y1) in enumerate(boxes, start=1):
        pad = 10
        crop = keyed.crop((max(0, x0 - pad), max(0, y0 - pad),
                           min(W, x1 + pad), min(H, y1 + pad)))
        art = autocrop_alpha(crop).resize((tw, th), Image.LANCZOS)
        canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        canvas.paste(art, (tx0, ty0))
        canvas.save(os.path.join(out_dir, f"face{i}.webp"), "WEBP", quality=92, method=6)
        make_bump(canvas).save(os.path.join(out_dir, f"face{i}-bump.webp"),
                               "WEBP", quality=90, method=6)
        print(f"face{i}: aligned")
    print(f"Done -> {out_dir}")


if __name__ == "__main__":
    main()
