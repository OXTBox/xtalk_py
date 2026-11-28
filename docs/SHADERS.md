# Graphic effects in the Python window (x1-09, 27 Nov)

LiveCode's five graphic effects are drawn by the Python window with three GPU shaders kept in
`~/projects/LIB_SHADERS/shaders` (`blur.fs`, `glow.fs`, `inner.fs`; `XTALK_SHADERS=<folder>` points elsewhere).
Code: `xtalk/stack/effects.py` (class Effects), called from `View.draw_card`; the properties in `xtalk/stack/host.py`.

| Effect | Drawn | Keys used |
|---|---|---|
| dropShadow | under the object: its blurred shape, moved by distance at angle, in the colour | color, opacity, size, spread, distance, angle |
| outerGlow | under the object: its blurred shape in the colour | color, opacity, size, spread |
| colorOverlay | over the object: its shape in the colour | color, opacity |
| innerShadow | over the object, inside its shape: where the moved blurred shape thins | color, opacity, size, spread, distance, angle |
| innerGlow | over the object, inside its shape, from the edges in (source "center": from the middle out) | color, opacity, size, spread, source |

Order (LiveCode's): dropShadow, outerGlow, the object, colorOverlay, innerShadow, innerGlow.
size = blur radius in units (times the window's scale in pixels); spread 0-255 = how much of the size stays solid;
opacity 0-255. Not done: blendMode (all of his are "normal"), knockout, range, the filter kinds (box1pass ...
gaussian all draw as one gaussian; box3pass, his most used, is close to it).

## How it is made

Per object with an effect: (1) its shape, the object drawn alone into a texture padded by the size; (2) blurred
across then down (blur.fs), once per effect; (3) drawn in the card through glow.fs / inner.fs. The textures are made
again only when the object's LOOK changes (size, relative points, text, props, scale); moving it only draws them
elsewhere. Playing NeonArcade (puck and paddles change size with the perspective): 163 remakes in 300 frames.

## The properties (a runtime fix found on the way)

The five effects are real properties: `the outerGlow["size"] of X` reads the harvested glow's value (it read empty
before), `set the outerGlow["Spread"] of X to 24` changes that one key (any case; before it made a separate custom
property beside the glow, so his scripts' hover glows did nothing), `set the outerGlow of X to tArray`,
`set the outerGlow of X to empty` removes it. A key set on an object without the effect starts the effect with the
other keys missing: drawn with `effects.DEFAULTS` (LiveCode's defaults NOT measured yet: see LIVECODE_FACTS).

## A stack without effects costs nothing

The window keeps the shown card's objects with an effect, looked for again only when an effect is set, an object is
made, or the card changes (`rt.fx_version`, one compare a frame). None: no shader loaded, no texture, the card is drawn
by the same loop as before. Measured (hidden window, 1.25, best of 5 x 300 frames, other helpers running: yes):

| Stack | before (window-rules) | after (shaders) | |
|---|---|---|---|
| Priority Tube (no effects), CPU | 3.79 / 3.89 ms | 3.83 / 3.29 ms | the same (noise) |
| Priority Tube (no effects), GPU (tools/gpu.sh) | 3.67 / 3.70 ms | 3.64 / 3.90 ms | the same (noise) |
| NeonArcade, still card (9 glowing objects), GPU | 2.07 ms | 6.47 ms | the glows' drawing |
| NeonArcade playing (tick + draw, 300 frames), CPU | 2.31 ms | 7.34 ms | ~136 frames a second |

## Checks

`.venv/bin/python -I tests/test_effects.py` (24, also with XTALK_INTERP=1): the properties, nothing made without
effects, the pixels of a glow (under the object, fading out), a drop shadow (to the side of its angle only), an inner
glow (inside near the edge only), a color overlay, a field and a button glowing at scale 1.25, a glow set by a
handler (translated).
