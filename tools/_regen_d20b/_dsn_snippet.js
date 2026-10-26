// Paste inside Hooks.once('diceSoNiceReady', async (dice3d) => { ... })
// const TEX = `modules/<id>/textures`;  // adjust to your asset path

await dice3d.addTexture("set-stone", { name:"Set Stone", composite:"source-over",
  source:`${TEX}/stone.webp`, bump:`${TEX}/stone-bump.webp` });

dice3d.addSystem({ id:"my-set", name:"My Set" }, "preferred");
dice3d.addColorset({ name:"my-set", category:"My Set", foreground:"#3a2d1a",
  background:"#cab68c", edge:"#9a8a63", outline:"#241c12", texture:"set-stone",
  material:"plastic", font:"Arial" }, "preferred");

dice3d.addDicePreset({ type:"d20", system:"my-set", colorset:"my-set",
  labels:[`${TEX}/d20f1.webp`, `${TEX}/d20f2.webp`, `${TEX}/d20f3.webp`, `${TEX}/d20f4.webp`, `${TEX}/d20f5.webp`, `${TEX}/d20f6.webp`, `${TEX}/d20f7.webp`, `${TEX}/d20f8.webp`, `${TEX}/d20f9.webp`, `${TEX}/d20f10.webp`, `${TEX}/d20f11.webp`, `${TEX}/d20f12.webp`, `${TEX}/d20f13.webp`, `${TEX}/d20f14.webp`, `${TEX}/d20f15.webp`, `${TEX}/d20f16.webp`, `${TEX}/d20f17.webp`, `${TEX}/d20f18.webp`, `${TEX}/d20f19.webp`, `${TEX}/d20f20.webp`],
  bumpMaps:[`${TEX}/d20f1-bump.webp`, `${TEX}/d20f2-bump.webp`, `${TEX}/d20f3-bump.webp`, `${TEX}/d20f4-bump.webp`, `${TEX}/d20f5-bump.webp`, `${TEX}/d20f6-bump.webp`, `${TEX}/d20f7-bump.webp`, `${TEX}/d20f8-bump.webp`, `${TEX}/d20f9-bump.webp`, `${TEX}/d20f10-bump.webp`, `${TEX}/d20f11-bump.webp`, `${TEX}/d20f12-bump.webp`, `${TEX}/d20f13-bump.webp`, `${TEX}/d20f14-bump.webp`, `${TEX}/d20f15-bump.webp`, `${TEX}/d20f16-bump.webp`, `${TEX}/d20f17-bump.webp`, `${TEX}/d20f18-bump.webp`, `${TEX}/d20f19-bump.webp`, `${TEX}/d20f20-bump.webp`] }, "d20");