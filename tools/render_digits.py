#!/usr/bin/env python3
"""Render digit glyphs from a font into carved-stone face labels + bump maps.

Each digit becomes a transparent-background label sized for Dice So Nice. The glyph
is drawn dark with a subtle lower-edge highlight so it reads as carved into stone, and
a matching bump map (dark glyph on neutral gray) makes it engrave physically on the die.

Usage:
    python render_digits.py <font.otf> <out_dir> [--digits 12345678] [--size 512]
                            [--dark 36,28,18] [--highlight 232,220,190]
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def parse_rgb(s):
    return tuple(int(x) for x in s.split(","))


def render_glyph(draw_size, font, ch, color):
    """Render a single char centered on a transparent draw_size square."""
    img = Image.new("RGBA", (draw_size, draw_size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    box = d.textbbox((0, 0), ch, font=font)
    gw, gh = box[2] - box[0], box[3] - box[1]
    x = (draw_size - gw) // 2 - box[0]
    y = (draw_size - gh) // 2 - box[1]
    d.text((x, y), ch, font=font, fill=color)
    return img


def carved(glyph_mask, size, dark, highlight):
    """Compose a carved look: light highlight offset down-right, dark glyph on top."""
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hi = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hi.paste(highlight + (170,), (0, 0), glyph_mask)
    hi = hi.transform(
        hi.size, Image.AFFINE, (1, 0, -4, 0, 1, -4), resample=Image.BILINEAR
    )  # shift highlight up-left so light sits on the upper lip of the groove
    out.alpha_composite(hi)
    dk = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dk.paste(dark + (255,), (0, 0), glyph_mask)
    out.alpha_composite(dk)
    return out


def make_bump(glyph_mask, size):
    """Mid-gray field, glyph darker => recessed/engraved on the die surface."""
    bump = Image.new("L", (size, size), 128)
    dark = Image.new("L", (size, size), 60)
    bump.paste(dark, (0, 0), glyph_mask)
    return bump.filter(ImageFilter.GaussianBlur(1.2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("font")
    ap.add_argument("out_dir")
    ap.add_argument("--digits", default="12345678")
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--glyph-frac", type=float, default=0.62, dest="glyph_frac")
    ap.add_argument("--dark", default="36,28,18")
    ap.add_argument("--highlight", default="232,220,190")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    dark = parse_rgb(args.dark)
    highlight = parse_rgb(args.highlight)
    font = ImageFont.truetype(args.font, int(args.size * args.glyph_frac))

    for ch in args.digits:
        # Render the glyph once to get a clean alpha mask, then style it.
        flat = render_glyph(args.size, font, ch, (0, 0, 0))
        mask = flat.split()[-1]
        face = carved(mask, args.size, dark, highlight)
        bump = make_bump(mask, args.size)
        face.save(os.path.join(args.out_dir, f"num{ch}.webp"), "WEBP", quality=92, method=6)
        bump.save(os.path.join(args.out_dir, f"num{ch}-bump.webp"), "WEBP", quality=90, method=6)
        print(f"num{ch}: done")
    print(f"Done -> {args.out_dir}")


if __name__ == "__main__":
    main()
