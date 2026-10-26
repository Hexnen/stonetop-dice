#!/usr/bin/env python3
"""Generate a carved-stone d8 face atlas with OpenAI gpt-image-1, using a reference image.

Reads the API key from image2api.env (looks for OPENAI_API_KEY, OPENAI_API, or a bare
sk-... line). Sends the reference (d6 stone style + target numerals) to the image-edit
endpoint and asks for 8 stone faces numbered 1-8 on a transparent background.

Usage:
    python gen_d8.py --ref tools/ref_d8_rimba.png --out tools/gen_d8_rimba.png
                     [--env image2api.env] [--size 1024x1024]
"""
import argparse
import base64
import os
import re
import sys
import requests

ENDPOINT = "https://api.openai.com/v1/images/edits"

PROMPT = (
    "Using the reference image, create a texture atlas of eight (8) dice faces for a "
    "d8. Replicate EXACTLY the carved-stone parchment tile style of the dice in the "
    "reference (cracked bone-colored stone, dark engraved border with the small pointed "
    "spikes at the edge midpoints, hand-inked outline). Instead of spiral pips, each "
    "tile must show a SINGLE carved numeral, using the numeral shapes from the reference "
    "strip: one tile each for 1, 2, 3, 4, 5, 6, 7, 8. The numerals must look chiseled / "
    "engraved into the stone, same dark ink color as the border. Arrange the 8 tiles in "
    "a clean 4-columns x 2-rows grid with even spacing, every tile the same size and "
    "orientation. The background and all space around and between the tiles must be a "
    "SOLID BRIGHT CHROMA-GREEN (like a green screen, RGB ~ 0,255,0) with no gradient, "
    "no texture, no shadows on the green. The green is for keying out later, so keep it "
    "pure and uniform and away from the stone color. No extra text outside the numerals."
)


def load_key(env_path):
    if not os.path.exists(env_path):
        sys.exit(f"ERROR: {env_path} not found")
    text = open(env_path, encoding="utf-8").read().strip()
    if not text:
        sys.exit(f"ERROR: {env_path} is empty — paste your key (e.g. OPENAI_API_KEY=sk-...)")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("OPENAI_API_KEY", "OPENAI_API")) and "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    m = re.search(r"(sk-[A-Za-z0-9_\-]+)", text)
    if m:
        return m.group(1)
    sys.exit("ERROR: no API key found in env file")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, nargs="+",
                    help="one or more reference images (up to 4), sent as image[]")
    ap.add_argument("--out", required=True)
    ap.add_argument("--env", default="image2api.env")
    ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--model", default="gpt-image-2", help="OpenAI image model id")
    ap.add_argument("--background", default="opaque",
                    help="opaque|auto|transparent. Default opaque: prompt asks for a green "
                         "screen, then key it out with slice_faces.py (works on gpt-image-2). "
                         "transparent would force gpt-image-1.5.")
    ap.add_argument("--quality", default="high")
    ap.add_argument("--prompt", default=PROMPT)
    args = ap.parse_args()

    model = args.model
    # gpt-image-2 cannot produce transparent backgrounds; route transparency to 1.5.
    if args.background == "transparent" and model.startswith("gpt-image-2"):
        print("NOTE: gpt-image-2 has no transparent background -> using gpt-image-1.5")
        model = "gpt-image-1.5"

    key = load_key(args.env)
    refs = args.ref[:4]  # endpoint accepts up to 4 reference images
    handles = [open(p, "rb") for p in refs]
    try:
        files = [("image[]", (os.path.basename(p), fh, "image/png"))
                 for p, fh in zip(refs, handles)]
        data = {
            "model": model,
            "prompt": args.prompt,
            "size": args.size,
            "n": "1",
            "quality": args.quality,
            "background": args.background,
            "output_format": "png",
        }
        print(f"Requesting {model} edit from {len(refs)} ref(s): {refs} "
              f"(background={args.background}, quality={args.quality}) ...")
        r = requests.post(
            ENDPOINT,
            headers={"Authorization": f"Bearer {key}"},
            files=files,
            data=data,
            timeout=180,
        )
    finally:
        for fh in handles:
            fh.close()
    if r.status_code != 200:
        sys.exit(f"API error {r.status_code}: {r.text[:500]}")
    payload = r.json()
    b64 = payload["data"][0]["b64_json"]
    with open(args.out, "wb") as out:
        out.write(base64.b64decode(b64))
    report_cost(model, payload.get("usage"), args.out)


# $/1M tokens by model: (text_input, image_input, image_output)
RATES = {
    "gpt-image-2": (5.0, 8.0, 30.0),
    "gpt-image-1.5": (5.0, 8.0, 32.0),
    "gpt-image-1": (5.0, 8.0, 30.0),
    "gpt-image-1-mini": (2.0, 2.5, 8.0),
}
COST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_api_cost.json")


def report_cost(model, usage, out):
    if not usage:
        print(f"Saved {out} (no usage returned)")
        return
    tin = usage.get("input_tokens_details", {}).get("text_tokens", 0)
    iin = usage.get("input_tokens_details", {}).get("image_tokens", 0)
    iout = usage.get("output_tokens_details", {}).get("image_tokens",
                                                       usage.get("output_tokens", 0))
    tr, ir, outr = RATES.get(model, RATES["gpt-image-2"])
    cost = tin / 1e6 * tr + iin / 1e6 * ir + iout / 1e6 * outr
    import json
    total = cost
    if os.path.exists(COST_FILE):
        try:
            total += json.load(open(COST_FILE)).get("total", 0.0)
        except Exception:
            pass
    json.dump({"total": round(total, 4)}, open(COST_FILE, "w"))
    print(f"Saved {out}")
    print(f"COST: this call ${cost:.4f}  |  cumulative ${total:.4f}  "
          f"(model={model}, in {tin}txt/{iin}img, out {iout}img)")


if __name__ == "__main__":
    main()
