# Roadmap: carrying LiveCode forward

Started 2026-11-11. LiveCode Community 9.6.3 is the last of its kind. The goal: the
owner's xTalk scripts and stacks keep running, and keep being written, on a Python
runtime with raylib, after 9.6.3 can no longer be used.

## Decisions (made by the owner, 2026-11-11)

| Question | Decision |
|---|---|
| How scripts run | **Interpreter first**: reads xTalk and executes it, as LiveCode does. The translator to plain Python comes second, after thorough testing (owner, 21 Nov). Both exist since 24 Nov. |
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
5. **Translator**: xTalk to plain Python (`xtalk/transpile.py`, built 24 Nov ahead of phases 2-4, see below).

## Where Phase 1 stands (21 Nov 2026)

- Package `xtalk/` (values, chunks, parser, interpreter, host). Tests: `python3 -I tests/test_interp.py`
  compares 245 cases with LiveCode 9.6.3's own answers (`tests/golden.json`, made by `tools/golden.py`;
  cases in `tests/expr_cases.txt`, `script_cases.txt`, `lib_cases.txt`). All match.
- Whole libraries run and agree with LiveCode: LIB_BIT, LIB_MAP, LIB_TRACE and the engine's maths
  (Mat3, colours, rays, meshes) when loaded as libraries.
- `python3 -I tools/parse_corpus.py` : 99% of the corpus's handlers parse (the rest are typos in the source).
- Not yet: object commands do nothing (the default host only records them: `go`, `show`, `lock`, `send`,
  `answer`), `send ... in N milliseconds`, `dispatch`, `pass`, message path, `do` of handler-local code
  across handlers, the property catalogue (207 properties), styled text. Those need Phase 2 (stack runtime).

## Where the translator stands (24 Nov 2026)

- `xtalk/transpile.py` turns a script into a Python module; `xtalk/pyrt.py` is what it runs on (the
  interpreter's own rules, so both always agree). Handlers, if/repeat/switch/try become plain Python;
  `do` and `value()` of text made at run time are interpreted. A handler it cannot translate is kept as
  xTalk and interpreted (none so far).
- `python3 -I tests/test_transpile.py`: the same LiveCode answers, every case and library translated
  first: 352 of 352 (incl. switch fall-through and 14 cases for the translator's own paths), plus 5 self-checks.
- `python3 -I tools/translate_corpus.py`: corpus 1124 of 1129 handlers (5 do not parse). All 1652
  distinct `.livecodescript` files in ~/projects: 20,591 handlers become Python that compiles, 430 do not parse.
- `generated/lib_bit.py`, `lib_map.py`, `lib_trace.py`: the three libraries as generated Python
  (`python3 -I tools/translate.py --libs`; the test fails when they are out of date).
- Speed: about the same as the interpreter (every operation still goes through the shared rules).
  Faster output (plain Python locals where a variable is surely text) is a later step.
- Still open, and Phase 2 work: objects, the message path, `send`/`dispatch`/`pass`, properties, the GUI.

## Next concrete step (written 11 Nov; Phase 1 is done)

Phase 1 begins with the value model and chunk expressions (`put`, `char/word/item/line
of`, `&`, `&&`, comparisons, number formatting), because `put` alone is 7,500 of the
census uses. Each piece gets a test list of expressions whose answers are taken from
LiveCode 9.6.3 through the dev server.
