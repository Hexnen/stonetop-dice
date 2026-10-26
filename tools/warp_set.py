#!/usr/bin/env python3
"""Chroma-key each generated die atlas and fit every face into its DSN UV-polygon
bounding box, producing per-face textures (+ bump). For apex-up symmetric faces this
equals the exact affine warp; for the rest it reliably fills the face region.

Outputs textures/<die>f<cell>.webp (cell = reading order in the atlas).
"""
import os
from PIL import Image
from slice_faces import chroma_key, feather_alpha, autocrop_alpha

SIZE = 512
# UV-polygon bounding box (cell-local x0,y0,x1,y1) from dsn-face-uv.json
BBOX = {
    "d4":  (0.009, 0.000, 0.992, 0.851),
    "d10": (0.139, 0.003, 0.867, 0.774),
    "d12": (0.009, 0.004, 0.992, 0.938),
    "d20": (0.003, 0.002, 0.999, 0.864),
    "d2":  (0.050, 0.050, 0.950, 0.950),
}
CFG = {  # die: (atlas, cols, rows, faces)
    "d4":  ("tools/gen_d4.png", 2, 2, 4),
    "d10": ("tools/gen_d10.png", 5, 2, 10),
    "d12": ("tools/gen_d12.png", 4, 3, 12),
    "d20": ("tools/gen_d20.png", 5, 4, 20),
    "d2":  ("tools/gen_d2.png", 2, 1, 2),
}


def main():
    for die, (atlas, cols, rows, faces) in CFG.items():
        keyed = feather_alpha(chroma_key(Image.open(atlas).convert("RGB"), 90, 35), 1.0)
        W, H = keyed.size
        cw, ch = W // cols, H // rows
        bx0, by0, bx1, by1 = BBOX[die]
        tx0, ty0 = round(bx0 * SIZE), round(by0 * SIZE)
        tw, th = round((bx1 - bx0) * SIZE), round((by1 - by0) * SIZE)
        n = 0
        for r in range(rows):
            for c in range(cols):
                n += 1
                if n > faces:
                    break
                cell = keyed.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))
                art = autocrop_alpha(cell)
                if art.size[0] < 4:
                    continue
                art = art.resize((tw, th), Image.LANCZOS)
                canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
                canvas.paste(art, (tx0, ty0))
                canvas.save(f"textures/{die}f{n}.webp", "WEBP", quality=92, method=6)
                bg = Image.new("RGBA", (SIZE, SIZE), (128, 128, 128, 255))
                bg.alpha_composite(canvas)
                bg.convert("L").save(f"textures/{die}f{n}-bump.webp", "WEBP", quality=90, method=6)
        print(f"{die}: {min(n, faces)} faces -> textures/{die}f*.webp")


if __name__ == "__main__":
    main()
