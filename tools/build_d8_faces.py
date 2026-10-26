#!/usr/bin/env python3
"""Build d8 face textures the way Forbidden Lands / DSN expect: a FULL-BLEED opaque
stone square with a centered numeral. Dice So Nice draws the label image across the
whole face cell and then clips it to the triangular octahedron face, so a full square
of textured stone fills the triangle completely and a centered numeral never gets cut.

Outputs textures/d8faceN.webp (+ -bump) for N=1..8.

Usage:
    python build_d8_faces.py <stone_atlas_green> <rimba.otf> <out_dir>
"""
import math
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SIZE = 512
DARK = (38, 28, 16, 255)
HILITE = (232, 220, 190, 150)


def stone_square(atlas_path, size):
    """Full opaque parchment-stone square (same stone as the d6 faces) at `size`."""
    atlas = Image.open(atlas_path).convert("RGB")
    patch = atlas.crop((35, 195, 190, 350))          # clean parchment, no spiral
    tile = patch.resize((size + 40, size + 40), Image.LANCZOS)  # slight overscan
    return tile.crop((20, 20, 20 + size, 20 + size)).convert("RGBA")


def carved_numeral(font, ch, size):
    """Dark numeral with a soft upper highlight (engraved look), transparent bg."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    box = d.textbbox((0, 0), ch, font=font)
    gw, gh = box[2] - box[0], box[3] - box[1]
    x = (size - gw) // 2 - box[0]
    y = (size - gh) // 2 - box[1]
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).text((x, y), ch, font=font, fill=255)
    hi = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hi.paste(HILITE, (0, 0), mask)
    hi = hi.transform(hi.size, Image.AFFINE, (1, 0, -3, 0, 1, -3), resample=Image.BILINEAR)
    img.alpha_composite(hi)
    dk = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dk.paste(DARK, (0, 0), mask)
    img.alpha_composite(dk)
    return img, mask


def main():
    atlas_path, font_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)
    stone = stone_square(atlas_path, SIZE)
    font = ImageFont.truetype(font_path, int(SIZE * 0.42))   # numeral ~42% of the cell

    for i in range(1, 9):
        face = stone.copy()
        num, mask = carved_numeral(font, str(i), SIZE)
        face.alpha_composite(num)
        # bump: neutral gray field, numeral engraved (darker), faces stay flat-ish
        bump = Image.new("L", (SIZE, SIZE), 128)
        bump.paste(Image.new("L", (SIZE, SIZE), 70), (0, 0), mask)
        bump = bump.filter(ImageFilter.GaussianBlur(1.2))
        face.convert("RGBA").save(os.path.join(out_dir, f"d8face{i}.webp"), "WEBP",
                                  quality=92, method=6)
        bump.save(os.path.join(out_dir, f"d8face{i}-bump.webp"), "WEBP", quality=90, method=6)
        print(f"d8face{i}: done")
    print(f"Done -> {out_dir}")


if __name__ == "__main__":
    main()
