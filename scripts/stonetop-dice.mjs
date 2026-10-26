const MODULE_ID = "stonetop-dice";
const TEX = `modules/${MODULE_ID}/textures`;
const range = (a, b) => Array.from({ length: b - a + 1 }, (_, i) => a + i);

Hooks.once("diceSoNiceReady", async (dice3d) => {
  // Calibration (scale + offset) is BAKED into real .webp files by tools/bake_calibration.py
  // — DSN only treats a label as an image when its path matches /\.(png|jpg|jpeg|gif|webp)$/i,
  // so we must hand it a real file path, never a composed data: URL (that renders as TEXT and
  // the face fails to load). `data/baked.json` lists which die types have baked textures under
  // textures/_fit/. For a baked die we load from _fit/ (transform already applied); otherwise
  // we use the original texture (identity). `rel` is the path relative to textures/, e.g.
  // "face1", "face1-bump", "decal/d20f1".
  const baked = await fetch(`modules/${MODULE_ID}/data/baked.json`)
    .then((r) => (r.ok ? r.json() : []))
    .catch(() => []);
  const tex = (type, rel) => `${TEX}/${baked.includes(type) ? "_fit/" : ""}${rel}.webp`;

  // Register the dice theme and make it the default look while playing Stonetop.
  dice3d.addSystem({ id: "stonetop", name: "Stonetop" }, "preferred");

  // Stone surface texture — covers the die body (faces without an image label, e.g. d4,
  // plus all bevels/edges) so everything reads as carved parchment. Await before the
  // colorset that references it.
  await dice3d.addTexture("stonetop-stone", {
    name: "Stonetop Stone",
    composite: "source-over",
    source: `${TEX}/stone.webp`,
    bump: `${TEX}/stone-bump.webp`
  });

  // TINTABLE stone for the decal sets: a grayscale grain composited "multiply" over the
  // colorset `background`, so the stone colour comes from `background` (incl. the DSN
  // per-die "Dice Color" picker) and the die is truly recolourable — the colour is NOT
  // locked into a colour image like stonetop-stone. Built by tools/make_stone_tint.py.
  await dice3d.addTexture("stonetop-stone-tint", {
    name: "Stonetop Stone (tintable)",
    composite: "multiply",
    source: `${TEX}/stone-tint.webp`,
    bump: `${TEX}/stone-bump.webp`
  });

  // Carved-stone parchment colorset (fills bevels/edges and any face transparency).
  dice3d.addColorset(
    {
      name: "stonetop",
      description: "STONETOPDICE.Colorset.Description",
      category: "Stonetop",
      foreground: "#3a2d1a",
      background: "#cab68c",
      edge: "#9a8a63",
      outline: "#241c12",
      texture: "stonetop-stone",
      material: "wood",
      font: "Arial"
    },
    "preferred"
  );

  // Register a die: maps an ordered list of texture base-names to face labels + bumps,
  // pulling from the baked (calibrated) folder when this die has been baked.
  const registerDie = (type, shape, names) =>
    dice3d.addDicePreset(
      {
        type,
        system: "stonetop",
        colorset: "stonetop",
        labels: names.map((n) => tex(type, n)),
        bumpMaps: names.map((n) => tex(type, `${n}-bump`))
      },
      shape
    );

  // d4 — use the full GENERATED faces (gen_d4: each triangular face already has its 3
  // carved numerals baked in) as `backgrounds`. `labels` must be present for DSN to
  // process backgrounds, but we make them transparent so no extra numerals are drawn.
  dice3d.addDicePreset(
    {
      type: "d4",
      system: "stonetop",
      colorset: "stonetop",
      labels: range(1, 4).map(() => `${TEX}/d4blank.webp`),
      backgrounds: {
        labels: range(1, 4).map((n) => tex("d4", `d4bg${n}`)),
        bumpMaps: range(1, 4).map((n) => tex("d4", `d4bg${n}-bump`))
      }
    },
    "d4"
  );

  // Full carved-stone set (labels[i] = face value i+1).
  registerDie("d2", "d2", ["d2f1", "d2f2"]);
  registerDie("d6", "d6", range(1, 6).map((n) => `face${n}`));
  registerDie("d8", "d8", range(1, 8).map((n) => `d8face${n}`));
  // d10 atlas shows 0-9 (d10f1="0" .. d10f10="9"); order so value 1->"1" .. value 10->"0".
  registerDie("d10", "d10", [...range(2, 10), 1].map((n) => `d10f${n}`));
  registerDie("d12", "d12", range(1, 12).map((n) => `d12f${n}`));
  registerDie("d20", "d20", range(1, 20).map((n) => `d20f${n}`));

  // ── Second colour: "Stonetop (Brown)" ─────────────────────────────────────
  // Same carved full-stone faces, TINTED to a darker brown stone (#714e30) — the
  // parchment midtone is multiplied onto #714e30 (tools/tint_brown.py), so the
  // numerals + frame stay legible and the carving keeps its depth. The brown is
  // baked into the textures (textures/brown/*), so background/edge just match it
  // for the bevels/chamfers. Same per-die calibration (loaded from brown/_fit/).
  const BROWN = `${TEX}/brown`;
  const btex = (type, rel) => `${BROWN}/${baked.includes(type) ? "_fit/" : ""}${rel}.webp`;
  dice3d.addSystem({ id: "stonetop-brown", name: "Stonetop (Brown)" }, "preferred");
  await dice3d.addTexture("stonetop-brown-stone", {
    name: "Stonetop Brown Stone",
    composite: "source-over",
    source: `${BROWN}/stone.webp`,
    bump: `${BROWN}/stone-bump.webp`
  });
  dice3d.addColorset(
    {
      name: "stonetop-brown",
      description: "STONETOPDICE.BrownColorset.Description",
      category: "Stonetop",
      foreground: "#e8dcc4",
      background: "#714e30", // brown stone — fills bevels/edges to match the tinted faces
      edge: "#714e30",
      outline: "#120c06",
      texture: "stonetop-brown-stone",
      material: "wood",
      font: "Arial"
    },
    "preferred"
  );
  const registerBrown = (type, shape, names) =>
    dice3d.addDicePreset(
      {
        type,
        system: "stonetop-brown",
        colorset: "stonetop-brown",
        labels: names.map((n) => btex(type, n)),
        bumpMaps: names.map((n) => btex(type, `${n}-bump`))
      },
      shape
    );
  dice3d.addDicePreset(
    {
      type: "d4",
      system: "stonetop-brown",
      colorset: "stonetop-brown",
      labels: range(1, 4).map(() => `${BROWN}/d4blank.webp`),
      backgrounds: {
        labels: range(1, 4).map((n) => btex("d4", `d4bg${n}`)),
        bumpMaps: range(1, 4).map((n) => btex("d4", `d4bg${n}-bump`))
      }
    },
    "d4"
  );
  registerBrown("d2", "d2", ["d2f1", "d2f2"]);
  registerBrown("d6", "d6", range(1, 6).map((n) => `face${n}`));
  registerBrown("d8", "d8", range(1, 8).map((n) => `d8face${n}`));
  registerBrown("d10", "d10", [...range(2, 10), 1].map((n) => `d10f${n}`));
  registerBrown("d12", "d12", range(1, 12).map((n) => `d12f${n}`));
  registerBrown("d20", "d20", range(1, 20).map((n) => `d20f${n}`));

  // ── Third set: "Stonetop (Brown Body)" ────────────────────────────────────
  // NO texture changes — the ORIGINAL parchment faces are reused as-is. Only the
  // DIE-BODY colour changes: the stone shown BETWEEN/around the face tiles (the
  // bevels, edges, chamfers, and the transparent margins around each polygon face)
  // is painted by the colorset, not the face image. So a TINTABLE grayscale stone
  // (multiply) over background #714e30 turns the body + edges brown while every face
  // stays the original carved parchment. This is DSN's own per-die colour setting —
  // change `background` (or the DSN "Dice Color" picker) to retint with no new files.
  dice3d.addSystem({ id: "stonetop-brownbody", name: "Stonetop (Brown Body)" }, "preferred");
  dice3d.addColorset(
    {
      name: "stonetop-brownbody",
      description: "STONETOPDICE.BrownBodyColorset.Description",
      category: "Stonetop",
      foreground: "#3a2d1a",
      background: "#7a522c", // "Kolor Kości" — die-body stone shown between the original faces
      edge: "#714e30", // "Kolor ramki" — die edge/rim
      outline: "#120c06",
      texture: "stonetop-stone-tint", // tintable grayscale stone -> body tinted by background
      material: "wood",
      font: "Arial"
    },
    "preferred"
  );
  const registerBody = (type, shape, names) =>
    dice3d.addDicePreset(
      {
        type,
        system: "stonetop-brownbody",
        colorset: "stonetop-brownbody",
        labels: names.map((n) => tex(type, n)),
        bumpMaps: names.map((n) => tex(type, `${n}-bump`))
      },
      shape
    );
  dice3d.addDicePreset(
    {
      type: "d4",
      system: "stonetop-brownbody",
      colorset: "stonetop-brownbody",
      labels: range(1, 4).map(() => `${TEX}/d4blank.webp`),
      backgrounds: {
        labels: range(1, 4).map((n) => tex("d4", `d4bg${n}`)),
        bumpMaps: range(1, 4).map((n) => tex("d4", `d4bg${n}-bump`))
      }
    },
    "d4"
  );
  registerBody("d2", "d2", ["d2f1", "d2f2"]);
  registerBody("d6", "d6", range(1, 6).map((n) => `face${n}`));
  registerBody("d8", "d8", range(1, 8).map((n) => `d8face${n}`));
  registerBody("d10", "d10", [...range(2, 10), 1].map((n) => `d10f${n}`));
  registerBody("d12", "d12", range(1, 12).map((n) => `d12f${n}`));
  registerBody("d20", "d20", range(1, 20).map((n) => `d20f${n}`));

  // ── New set: "Stonetop (Decal)" ───────────────────────────────────────────
  // Same carved-stone look, but the per-face art is a transparent line+highlight
  // DECAL (textures/decal/*.webp): only the dark engraving lines and bright carved-
  // edge highlights, no stone fill colour. The stone colour + surface come from the
  // colorset/texture here, so the whole die can be recoloured without regenerating
  // faces. Decals reuse the same per-die calibration and the original engraving
  // heightmaps (bumpMaps) for true geometric depth.
  dice3d.addSystem({ id: "stonetop-decal", name: "Stonetop (Decal)" }, "preferred");

  dice3d.addColorset(
    {
      name: "stonetop-decal",
      description: "STONETOPDICE.DecalColorset.Description",
      category: "Stonetop",
      foreground: "#3a2d1a",
      background: "#cab68c", // stone colour shown through the transparent decal faces
      edge: "#9a8a63",
      outline: "#241c12",
      texture: "stonetop-stone-tint", // tintable: stone colour = `background`, recolourable
      material: "wood",
      font: "Arial"
    },
    "preferred"
  );

  const registerDecalDie = (type, shape, names) =>
    dice3d.addDicePreset(
      {
        type,
        system: "stonetop-decal",
        colorset: "stonetop-decal",
        labels: names.map((n) => tex(type, `decal/${n}`)),
        bumpMaps: names.map((n) => tex(type, `${n}-bump`))
      },
      shape
    );

  // Only d20 generated so far; add d2/d4/d6/d8/d10/d12 here as their decals are made.
  registerDecalDie("d20", "d20", range(1, 20).map((n) => `d20f${n}`));

  // ── New set: "Stonetop Norse (Decal)" ─────────────────────────────────────
  // Norse-styled DECAL faces (textures/decal-norse/*.webp): ONE identical braided
  // border frame on every face + a Norse Bold numeral, rendered as dark grooves +
  // bright highlights on transparency (no stone fill). Stone colour/surface come from
  // the colorset, so the die is recolourable. Faces are drawn to the exact DSN d8 UV
  // polygon, so they map at identity (no calibration). Generated by tools/make_d8_norse.py.
  // Only d8 so far; extend with more dice as their Norse decals are generated.
  const NORSE = `${TEX}/decal-norse`;
  dice3d.addSystem({ id: "stonetop-norse-decal", name: "Stonetop Norse (Decal)" }, "preferred");

  dice3d.addColorset(
    {
      name: "stonetop-norse-decal",
      description: "STONETOPDICE.NorseDecalColorset.Description",
      category: "Stonetop",
      foreground: "#3a2d1a",
      background: "#cab68c", // stone colour — change this (or DSN "Dice Color") to recolour
      edge: "#9a8a63",
      outline: "#241c12",
      texture: "stonetop-stone-tint", // tintable grayscale stone (multiply over background)
      material: "wood",
      font: "Arial"
    },
    "preferred"
  );

  dice3d.addDicePreset(
    {
      type: "d8",
      system: "stonetop-norse-decal",
      colorset: "stonetop-norse-decal",
      labels: range(1, 8).map((n) => `${NORSE}/d8nf${n}.webp`)
    },
    "d8"
  );
});
