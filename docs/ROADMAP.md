# Roadmap: carrying LiveCode forward

Started 2026-11-11. LiveCode Community 9.6.3 is the last of its kind. The goal: the
owner's xTalk scripts and stacks keep running, and keep being written, on a Python
runtime with raylib, after 9.6.3 can no longer be used.

## Decisions (made by the owner, 2026-11-11)

| Question | Decision |
|---|---|
| How scripts run | **Interpreter first**: reads xTalk and executes it, as LiveCode does. A one-time translator to plain Python may come later. |
| GUI foundation | **raylib + Dear ImGui**. One engine for the editors, the stack runtime and the 3D view. |
| Where | **This project** (`~/projects/xtalk_py`, working name). xt3d, Vibecode3D and LIB_LLM stay separate projects and tools. |
| Goal for the editors | "Final Cut Pro quality" doodle, animate, meshify and game-play editors, usable from both Vibecode3D and xt3d. Eventually. |

## The tools and how they meet

```
                 shared formats
  Vibecode3D  ─┐   harvest JSON (stacks, cards, controls)     ┌─ xt3d (raylib bridge)
  LIB_LLM     ─┼── sprite frames as 0/1 text (GridDraw)  ──┼─ editors: doodle, animate,
  GridDraw    ─┤   models (glb/obj), xt3d_ calls = raylib     │  meshify, game play
  XTJSON      ─┘   names                                       └─ xtalk_py runtime
```

Each tool keeps its own project and can move to the Python runtime on its own schedule.
They agree on data, not on code.

## What makes this doable

1. **The glossary is small.** `docs/GLOSSARY.md` (from `tools/glossary_census.py`): about
   22,000 lines of the owner's scripts use about 100 commands (the top 25 cover 98% of uses),
   about 80 functions and about 200 properties.
2. **XTJSON reads the stacks.** `.livecode` files are binary and only LiveCode reads them
   reliably. LCHarvest2 turns them into JSON plus script files while 9.6.3 still runs. The
   Python runtime loads harvests, never `.livecode` files. *Harvest every stack worth
   keeping while LiveCode still runs.*
3. **LiveCode 9.6.3 is the referee.** xt3d's dev server can run any expression in the
   real IDE. The interpreter is tested by running the same code in both and comparing:
   differential testing, automated, while the original still exists.
4. **xt3d is already named after raylib.** `xt3d_DrawCube` maps to `pyray.draw_cube`.
   Scripts written against xt3d run unchanged on the Python side.

## The hard parts (not the word list)

- Chunk expressions as targets: `put x after word 3 of line 2 of tVar`, `delete item 2 of ...`
- Everything is text: numbers convert silently, and `"1.0" = 1` is true
- The message path: control, then card, then background, then stack, then library stacks,
  then the back scripts; plus `pass`, `send ... in N milliseconds` and `dispatch`
- `do` and `value()`: code built at run time
- Custom property sets, the `templateXXX` objects, `lock screen` / `lock messages`
- Fields with styled text (the biggest single control to reproduce)

## Phases

0. **Now, in LiveCode** (other projects): keep the tools working and harvest every
   stack. Settle the shared formats; first piece: GridDraw sprite frames into xt3d
   textures (`xt3d_ImageFromBits`).
1. **xTalk core, no GUI**: tokenizer, parser, and an interpreter for the census
   vocabulary: values, chunks, arrays, handlers, globals and locals, the message path
   between script objects, `send`/`dispatch`/`do`/`value`. Tested against LiveCode
   through the dev server. Done when the owner's library-style scripts (XTJSON
   libraries, LIB_LLM logic, GridDraw's bit functions) give the same results.
2. **Stack runtime**: load a harvest, with stacks, cards, controls and their properties,
   custom property sets, and events (`openCard`, `mouseUp`...). Drawn with raylib +
   ImGui. Done when a harvested stack opens and its buttons work.
3. **xt3d on Python raylib**: the `xt3d_` handlers map onto pyray; the frame-into-image
   path is not needed when raylib draws everything.
4. **Editors**: doodle, animate, meshify, game play, built on the runtime and shared by
   Vibecode3D and xt3d.
5. **Optional translator**: xTalk to plain Python, for people who want Python output.

## Next concrete step

Phase 1 begins with the value model and chunk expressions (`put`, `char/word/item/line
of`, `&`, `&&`, comparisons, number formatting), because `put` alone is 7,500 of the
census uses. Each piece gets a test list of expressions whose answers are taken from
LiveCode 9.6.3 through the dev server.
