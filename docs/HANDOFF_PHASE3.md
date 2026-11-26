# Handoff: the next phase of the Pythonization (written 26 Nov 2026, evening)

**Order (the owner's word, 26 Nov): first "Phase 2, thorough" (below), then Phase 3 (xt3d on Python raylib) with
uDead CullTest as the first game.**

Read first: `CLAUDE.md`, `docs/ROADMAP.md` (Phases), `docs/LIVECODE_FACTS.md`, then this.
Where Phase 2 ended: `docs/HANDOFF_2026-11-26.md` ("Done 26 Nov" and "Later the same day").

## Where things stand
- **Phase 1 (interpreter) and Phase 2 (stack runtime) are done** for the stacks the owner uses as tests. All on
  xtalk_py main and **pushed** to OXTBox (c653286, 26 Nov).
- Seen working on the owner's own screen:
  - nine-ball (styled Instructions, Help menu, About, Preferences radio buttons)
  - LightCycles3 (keys, sliders, Redraw ALL, the turned hitbox graphics)
  - TKInter-izer (menus, list fields, typing, drag-select, Ctrl+A/C)
  - the card reader
- Tests (run all three after any change to `xtalk/`):

  | Test | Result |
  |---|---|
  | `python3 -I tests/test_interp.py` | 396/396 |
  | `python3 -I tests/test_transpile.py` | 401/401 |
  | `python3 -I tests/test_stack.py` | 115/115 |

  Survey (`python3 -I tools/survey_stacks.py`):

  | Stack | Clicks that work |
  |---|---|
  | nine-ball | 16/16 |
  | LightCycles3 | 18/18 |
  | card reader | 3/3 |
  | TKInter-izer | 14/15 (its Program field names a button the stack does not have) |

- Phase 2 leftovers (small, do when a stack needs them):
  - **Rotated images:** the `angle` of an image is not drawn.
  - **Styled fields:** `delete` or `sort` on a styled field probably loses its styles.
  - **Line height:** `fixedLineHeight false` and LiveCode's exact line height are not measured.
- **Check in the Dictionary when OXT-Beyond is open** (we wrote these from memory):
  - up/down arrows with no field focused: first/last card, or back/forth through recent cards?
  - `angle` on rectangles and ovals
  - `commandKeyDown`

## Phase 3: xt3d on Python raylib
ROADMAP: "the `xt3d_` handlers map onto pyray; the frame-into-image path is not needed when raylib draws
everything." Scripts written against xt3d should run unchanged in the Python runner.

**TWO ENGINES (put this in every brief):**
- **Vibecode3D (XT)** is pure xTalk.
- **xRay** is the xt3d raylib bridge extension (`~/projects/xt3D_Raylib_Livecode_Bridge`).
- `vibe_engine_xt3d` is a GENERATED script (Engine-1); never edit it by hand.

### What xt3d is today (in its own project, on OXTBox)
- **The API list:** `xt3d_raylib_manifest.json` lists every raylib function: 619 in all, 493 wrapped as
  `xt3d_<Name>`, 126 skipped.
  - Each entry has the raylib name, the C prototype, a `signature` (s=string i=integer f=number b=boolean
    p=pointer, a digit = repeat count), params and the return type.
  - Conventions: images, textures, models, sounds and cameras are **positive integer handles** (0 = invalid);
    colours are r,g,b,a; vectors are spread into separate numbers; struct returns are comma-separated text.
- **Hand-written extras:** `xt3d_shim.c` has 43 helpers (cameras, model animation info, the frame-to-imageData
  path...). These have no single pyray call; each needs its own Python.
- **Scripts that call xt3d:**
  - `demos/` (view, window, face, diagnostic)
  - `testbench/` (xt3d_testbench, vibe_engine_xt3d...)
  - one script each in LIB_ig3d, LIB_SFX, LIB_MAP, LIB_INPUT, LIB_HOWTO, LIB_DEV, LIB_BUILD
  - none of the harvests in `~/projects/XTJSON` calls xt3d yet.

### Phase 3 steps, after Phase 2 (small, one at a time)
1. **Generate the mapping, don't hand-write it.** A tool (`tools/gen_xt3d_py.py`) reads the manifest and writes
   `xtalk/xt3d/generated.py`:
   - one Python function per wrapped entry: xTalk text args in, converted by `signature`, then pyray, then the
     result as xTalk text;
   - a handle table (integer -> pyray object) the same as the shim's.
   - Never edit the generated file (the same rule as `generated/`).
2. **The 43 helpers by hand** in `xtalk/xt3d/helpers.py`, checked against what `xt3d_shim.c` does.
3. **Hook into the interpreter:** an `xt3d_...` call in a script finds the Python function (as BUILTINS / host
   commands do), in both the interpreter and the translator.
4. **Where it draws.** In LiveCode the scene is either an image on the card or raylib's own window. Here the
   stack window already is a raylib window, so:
   - draw the 3D scene in the image control's rect (a render texture drawn there);
   - or let `xt3d_InitWindow` mean "use the stack window".
   - The owner's answer: the image mode for editors and test stacks, the whole window for games.
5. **Targets:** `demos/xt3d_view_demo.livecodescript` (or the diagnostic) as a first check of the mapping, then the
   testbench host, then **uDead CullTest** (the owner's choice, see below).
6. **The referee:** LiveCode with the real xt3d DLL gives the expected text results (handles, struct returns,
   `xt3d_Version`); pictures are compared by eye or by snapshot.
   - `lcmcp --standalone` needs the extension loaded; read `LIB_MCP` and the xt3d `CLAUDE.md` for how the
     testbench does it.

### The owner's answers (26 Nov, evening)
- **A) Phase 2 first, and thorough.** Finish Phase 2 properly before any Phase 3 code (see "Phase 2, thorough"
  below).
- **B) Where the 3D view draws:**
  - In an **editor or test stack** that has controls, the 3D view goes **inside an image** on the card.
  - A **game fills the whole window**; a game is a final or pre-final stage of editing.
  - So both modes are needed: the image mode for editors/test stacks, the whole window for games.
- **C) First game through Python raylib: uDead CullTest**, the most complicated one.
  - The script: `~/projects/LIB_GAMES/Vibecode3D_Games/Vibecode3D_Play_uDead_CullTest.livecodescript` (2,493 lines;
    card "Play.uDead_CullTest", keys 0-3 switch gCullMode hiding, an FPS line on top).
  - It is a **Vibecode3D game**: it calls the engine (Mesh.*, Entity.*, Game.On*, Camera.*, Collision.*...),
    not xt3d directly.

### How uDead reaches raylib today (found 26 Nov; read before planning)
- The engine on xt3d is `xt3D_Raylib_Livecode_Bridge/testbench/vibe_engine_xt3d.livecodescript` (10,209 lines).
  - It is GENERATED by `tools/make_vibe_xt3d.py`: the owner's Vibecode3D engine script + `vibe_xt3d_overrides`.
  - It is pure xTalk: it has hardly any xt3d calls of its own.
- The **host** draws:
  - `xt3d_testBench_lib_mcp.livecodescript` (95 xt3d calls) owns the timer and the drawing;
  - it calls `Vibe.Begin rect` once, then each tick `Vibe.Step` (the fixed 33 ms steps) and `Vibe.Frame()` (what
    to draw: objects in camera space, 2D lines);
  - camera space: +X right, +Y down, +Z forward.
- So uDead in Python needs:
  1. the 10k-line engine script running in our interpreter (a big load test: every handler must parse and run);
  2. the uDead card script on a card;
  3. a host that draws `Vibe.Frame()` with raylib. Either run the testbench host script itself, its xt3d calls
     going through the generated mapping (steps 1-3 above; it tests Phase 3 fully), or a Python host that draws
     the frame directly. **Recommend the first; ask the owner.**
- The game fills the whole window (answer B). Culling modes 0-3 are the test: compare frames-a-second and lines
  drawn with the xRay numbers in `Next_Steps_With_Claude/FABLE_NIGHT_11_18_RESULTS.md`.
- How uDead is played today: `LIB_TEST/PLAY_uDead_Vibecode3D.bat`; game tests on the real engine:
  `LIB_GAMES/tools/engine_play.sh <Game> <Prefix> "keys..."`.

### Phase 2, thorough (do this first, by the owner's word)
1. **The leftovers listed above:**
   - rotated images (`angle`)
   - `delete` / `sort` on a styled field (measure, then keep the styles as LiveCode does)
   - `fixedLineHeight` and LiveCode's real line height (measure)
   - the three Dictionary checks
2. **Every harvest in `~/projects/XTJSON` to 100% in the survey:**

   | Stack | Now | Errors |
   |---|---|---|
   | 3DShufflepuckaroo | 0/3 | 3 load errors |
   | xTalk_Raycasting_101 | 0/0 | 2 load errors |
   | TKInter-izer | 14/15 | the stack's own missing button: ask him whether to fix the script, as with nine-ball |
   | GAD_WORKING | 3/77 | skipped by the owner on 25 Nov as "overly complicated, incomplete": ask before starting it |

   Read the survey's "most common causes" list (`run_files/survey.txt`): "expression: bad operand" (900) and
   "can't find handler" lines first.
3. **The open-message order with groups:** preOpenBackground / openBackground are not measured.
4. **Things still drawn plainly:**
   - players and widgets
   - gradients and ink effects
   - an icon and its name together on a button
5. Ask him for more stacks to harvest when these are clean (`lcmcp harvest <stack>`).

### Phase 2 thorough: done so far (branch `phase2-thorough`, commits d14aedb..ea62a50 + this note; NOT merged, NOT pushed)
Dated by the system clock (25 Nov; the notes above say 26 Nov). Every rule below was measured in LiveCode
first and is in LIVECODE_FACTS (the end of the file), unless it says "from memory".

| Done | What it fixed |
|---|---|
| Script-level `global` lines reach the handlers below them | the 900 "bad operand" errors; GAD went 3/77 -> 65/77 without being touched |
| Numbers keep their full value through arrays, parameters, returns | Raycasting_101's divide by zero (`sin(pi)` stored in an array) |
| `this wd` / `this window`, `delete local/global`, `the graphic ID x` | 3DShufflepuckaroo and Raycasting_101 load errors |
| `the pendingMessages`, `cancel`, `send ... in` gives the id, `the long seconds` | Shufflepuck 3/3 |
| `choose` tool (from memory), `the keysDown` (from memory) | Raycasting_101 opens and runs its loop |
| `set the points` to one comma list | Raycasting walls |
| Filled polygons drawn filled | Raycasting walls were invisible (snapshot checked) |
| Turned images: rect, direction, move, resize | leftover 1 |
| `delete line` / `sort lines` keep a styled field's styles | leftover 2 |
| Line heights, fixedLineHeight true/false | leftover 3 (one height a field: a bigger-text line in a free field is not taller yet) |
| Background groups: on the card's message path; open/close/go background messages | open-message order with groups |
| `set the script of`; `set the loc` with odd sizes; `pass` follows the target's path | found on the way |
| A parameter named like a script global is the parameter (measured) | a wrong-variable risk the globals fix brought |
| `rawKeyDown`, `set the cursor to none`, `set the screenMouseLoc` (real window only), `globalLoc`/`localLoc` (from memory) | Raycasting_101: Esc / backtick free the mouse; W A S D through the keysDown |
| Numbers copy as themselves | arrays copy faster than on main again (20k elements: 0.15 s, main 0.22 s) |

What he will SEE differently: nine-ball's Instructions lines are 16 apart, not 18 (the real stack's field is
fixedLineHeight true, textHeight 16: measured on a copy). LightCycles3 is pixel-identical to main.
Raycasting_101 draws its walls (filled polygons); XtRedeemer (shared backgrounds, a pendingMessages loop): 47/55.

Tests: 405 / 410 / 128. Corpus 41,132 handlers to Python, no file worse. Survey: every harvest has no errors
except TKInter-izer 14/15 (his question) and GAD 65/77 (skipped by him).

Still open:
- The Dictionary checks (OXT-Beyond was closed): arrow keys with no field focused; `commandKeyDown`.
  (`angle` on rectangles/ovals is MEASURED now: stored, corners not turned; we already did that.)
- Drawn plainly: glow/shadow effects (Shufflepuck uses 13, LightCycles3 2), maybe an icon with its name
  (TKInter-izer 1). No harvest uses players, widgets or gradients.
- Questions for him: TKInter-izer's missing button; start GAD now (65/77)?; more stacks to harvest; a look at
  Shufflepuck and Raycasting_101 on screen.

### Phase 2 thorough, round 2 (25 Nov; branch `phase2-thorough` up to d6c33d7)
- Simple_image_viewer (his OXT stack) runs: files()/folders()/defaultFolder, image fileName, the answer-folder
  browser, real folders in his window (writes stay sandboxed). Arrow keys in its lists move the hilite and his
  `send mouseDown to me in 30 milliseconds` picks the folder/file (a click on a list focuses it).
- `.oxtstack` harvests get OXT-Beyond's dark theme (white on 32,32,32, hilite 0,120,215: asked of OXT-Beyond).
- Mouse-look games: `cursor none` + `lockCursor true` grabs the mouse (a virtual mouseLoc; `screenMouseLoc` moves
  it). Untested on his screen whether WSL passes grabbed movement through (a pointer fallback is in).
- Never load his photos in checks: the harvested image fileName points at his own picture; checks use test
  pictures in the scratchpad.

### Speed: the fast translator (branch `fast-translate`, on `phase2-thorough`; NOT merged, NOT pushed)
His word (25 Nov): "definitely translate to pure Python before running, not a slow walk over the code".
Raycasting_101 was unusable: 85-125 ms a game step in the interpreter, and the window ran every due message
before drawing, so a GameLoop that re-sends itself 1 ms later starved the window (one key, then frozen).

| Change | Where |
|---|---|
| Every stack script is translated to Python when the stack opens (`XTALK_INTERP=1` = interpreted as before) | `xtalk/stack/runtime.py` ObjInterp.load |
| Fast mode: handler variables are Python variables, numbers stay floats inside a handler, comparisons are Python truths, plain constants inlined | `xtalk/fastgen.py` (translate_script(fast=True)) |
| `do`, value(), select, styled chunks, `sort by each`, @ parameters, matchText captures: the variables go into the frame (and come back) around them | fastgen sync_out / rt.W |
| The window runs at most 20 ms of messages a frame (the rest next frame) | view.py `rt.tick(..., budget=0.02)` |
| Line/item splits of long texts are kept (`char x of line y of sWorldMap`) | chunks.py, pyrt.gchunk |
| Numbers compare at their full value with LiveCode's tolerance (MEASURED, was wrong: we compared the 6-decimal text) | values.compare / num_cmp |

Results: Raycasting step 12 ms (was 85-125); hidden window 54 fps with ~23-26 game steps a second; 100 scripted
steps give identical script locals and identical properties of all 52 objects, interpreted vs fast.
Tests 416 / 837 (every golden case also in fast mode) / 132 (also with XTALK_INTERP=1). Survey identical to the
interpreter, click for click. Corpus: 41,143 handlers to Python, 41,091 of them fast; the rest plain (a `global`
line below other lines, @ argument that is an array element of a handler variable).

Next for speed (when uDead needs it): host object lookups by description text (set the points of graphic id
N) will show up next in the profile; `put ... after` of a long text copies it each time.

## How we work (unchanged; see HANDOFF_2026-11-26.md for details)
- **Looking at a stack:**
  - He runs `~/projects/xtalk_py/tools/open_stack.sh <harvest folder>` (window at 200,32).
  - Afterwards, read the report at the end of `run_files/open_stack.log` before asking him.
  - That report does not show menu picks or what he saw: ask him.
- **Snapshots:** check our own drawing with a hidden-window snapshot (`tools/open_stack.py --snap`, or
  `View(rt, hidden=True)` + `snapshot`) before asking him to look. Never grab his whole screen.
- **Measure, then build:** measure in LiveCode first (`~/projects/LIB_MCP/tools/lcmcp --standalone run --server
  '...'`), record the answer in LIVECODE_FACTS, and end both copies afterwards (`Client.kill_slot(0)`, `(1)`).
  Long scripts go in a file piped with `run --server -`.
- **After any parser change:** run the corpus check before and after:
  `python3 -I tools/translate_corpus.py -v ~/projects` (today: 41,094 handlers to Python; none may get worse).
- **Git:**
  - a branch per piece of work;
  - merge only on his "merge";
  - push only on his "push" (each push needs its own word).
- **Folders:**
  - `~/projects/XTJSON` is harvest OUTPUT only (not git; holds his test stacks and our edit of nine-ball's
    Preferences scripts, the old ones in `OLD_scripts_keepsake_26Nov`).
  - The harvester and rebuilder code live in **LIB_XTJSON**; `lcmcp harvest` lives in **LIB_MCP**. Both on OXTBox.
- **WSLg:**
  - the hidden snapshot window cannot reach the Windows clipboard, but his real window can (he copied fine);
  - Windows programs started from WSL need stdin closed.
