# x1-09 shaders: approach note (helper B, 27 Nov, for the lead; not the final doc)

## Step 1 found (harvests' props read by script, 51 JSON files in run_files/target_harvests + ~/projects/XTJSON)

| Harvest | outerGlow | innerGlow | dropShadow | innerShadow | colorOverlay | on |
|---|---|---|---|---|---|---|
| 3DShufflepuckaroo_v5_NeonArcade | 9 | 4 | - | - | - | graphics (walls, paddles, puck, lines) |
| XtRedeemer_FIRST_SUCCESS | 76 | - | - | 2 | 40 | buttons, fields, graphics |
| OLD_VIBECODE3D_GUI_v1 | 44 | - | - | 1 | 20 | buttons, fields, graphics |
| LightCycles3 | - | - | 2 | - | - | graphics (the bikes) |
| Project Map, Priority Tube, Library, xt3d bench | - | - | - | - | - | |

Scripts (his + corpus) only set `outerGlow["size"]` / `["spread"]` (~140 lines). Filters used: box3pass (most), gaussian.
His try: NeonArcade, a real stack of his with glows (green walls, red/blue paddles, puck): no test harvest needed.

## Found on the way (runtime bug)
`the outerGlow["size"] of X` reads '' for a harvested glow, and `set the outerGlow["size"]` makes a separate custom
property beside the harvested glow (host.get_prop/set_prop with a key look only in custom props). Fix in host:
the five effects are real properties (an array in props), keys read/written case-insensitively,
`set the outerGlow of X to empty` removes it; `rt.effects` counts objects with one (zero-cost flag).

## Step 2: LiveCode measurement
The first probe (`export snapshot ... with effects` on an invisible stack) left the shared server not answering
(lead told). Retry with NO snapshot: defaults of each effect array, what `set the outerGlow["size"]` on an object with
no glow fills in. Pixel profile (what size/spread draw) needs a window: left unmeasured unless the server answers a
safe way; the meaning used until then is LiveCode's documented one (Photoshop-like): size = blur radius in pixels,
spread = how much of the size is solid before it fades (0-255 -> 0..100%), opacity 0-255, distance/angle for shadows.

## Step 3 build (view.py, LIB_SHADERS/shaders/*.fs)
Per object with an effect, at the window's scale, in render textures cached per object (redone only when its rect,
points, text or props change):
1. mask: the object drawn alone into a texture padded by size+distance;
2. blur.fs: separable gaussian (horizontal, then vertical; box3pass ~ gaussian), radius = size;
3. glow.fs: blurred alpha -> colour x opacity, spread = alpha lifted (a / (1 - spread));
   outer glow drawn UNDER the object, drop shadow the same offset by distance at angle;
4. inner.fs: inner glow / inner shadow = mask x (1 - blurred mask (shifted for the shadow)), drawn OVER the object;
   colorOverlay = the mask in the colour at opacity, over the object.
Order (LiveCode's): dropShadow, outerGlow, object, colorOverlay, innerShadow, innerGlow.

## Step 4: zero cost
`rt.effects == 0` -> draw_card never looks (one integer test a frame). Proof: hidden frame time of a no-effect stack
on main vs this branch, CPU and GPU stated.

## Risks
- CPU (llvmpipe) blur of big glows (size 47 at scale 1.25 ~ 60 px radius) may be slow: taps capped (stride), cache.
- Fields draw with scissors in window pixels: inside the mask texture an offset is needed (handled in View.scissor).
- blendMode (screen, multiply...) not done: normal only (all of his are "normal").
