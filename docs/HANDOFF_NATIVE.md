# Handoff: native Python output (written 25 Nov 2026, late night, system clock)

**Read first:** `CLAUDE.md`, `docs/ROADMAP.md`, then `HANDOFF_PHASE3.md` START HERE (what runs today), then this.

## The owner's word (25 Nov, late night)
After playing uDead in the Python window ("absolutely passable performance and user interaction"):
"at this point we are loading the livecode in and testing what bugs we find in the python in memory, the next best
step should certainly be **native python output**. ... you're going to get all that done in the order you see fit
and use the help you need to do it."

So the order below is mine to choose, and helper agents may be used: one per bubble, each with a clear test to
pass. The **TWO ENGINES** note goes in every brief.

## Where we stand
- **What runs:** `tools/play_xt3d.sh` starts Python with raylib (the `raylib` package: an OpenGL window via GLFW,
  shown by WSLg). `xtalk/stack/view.py` draws the card and feeds keys and mouse in LiveCode's terms; ImGui only
  draws menus, dialogs and the F2 error panel.
- **The scripts:** the unchanged bridge testbench host, the generated `vibe_engine_xt3d`, the uDead card,
  LIB_LOADING and GameNotes. Each is translated to Python at load (`xtalk/fastgen.py`) and run by `StackRuntime`.
- **The `xt3d_` calls:** they go to raylib through `xtalk/xt3d/generated.py` + `helpers.py`.
- **Speed (uDead CullTest, uDead with blood capped at 3):** 12-14 fps in a rush at hiding mode 3; game step
  22-42 ms, scene 17, draw 22.
  - Against LiveCode + xRay (19 Nov table, about 45 objects): draw is the same, scene about 2x slower, step
    about 3x slower.
  - The time goes to running xTalk in Python, not to raylib.
- **Profile, rush, 600 frames:**

  | Part | Share |
  |---|---|
  | `UpdateObjectTransforms` (with `RotateLocalVector`, `Mat3.Mul`) | 28% |
  | `uDead.FieldWork` | 17% |
  | number to text (`fmt_num` / `numstr`) | 8% |
  | `gchunk` (items and words of text) | 7% |
  | handler calls (`invoke`), `dict.get`, `isinstance` | the rest of the top |

## Not merged yet: waiting for his word (he played these and liked the result)
- xtalk_py branch `phase3-play-fixes`:
  - close box ends the game at once; Escape frees the mouse and keys
  - mouse look: soft grab under WSL, right-button look tuned in his play
  - GameNotes front scripts; the defaultStack; `value(expr, obj)`; the system date
  - `put after URL` adds to the file; `mouse(3)`
- LIB_GAMES branch `udead-blood-limit`: blood capped at 3 (`kBloodMax`; 0 = none); right-button look
  (`kLookRightMouse`) in both uDead scripts.
- Ask "merge these two?" before building on them. If there is no answer yet, branch the new work from
  `phase3-play-fixes`.

## The plan, in order

### 0. A bench that gives the same numbers twice (before any speed work)
- uDead's maps and cast are random: `the randomSeed` is set to `the milliseconds` near line 430 of the CullTest.
  Fix the seed when a test asks, through a global the game reads (e.g. `gTestSeed`). That changes the game
  script: do it on the LIB_GAMES branch.
- Make `tools/bench_xt3d.py`: a fixed key script (hiding mode 3; R at frame 60; walk), 900 frames, hidden window.
  - It prints the average and worst step / scene / draw, objects, and wall time.
  - It saves the result in `run_files/bench/<date>_<label>.txt`; the first run is the baseline.
- Every step below reports its bench result against the baseline.

### 1. A referee for native code (before any native code)
- `tools/frame_referee.py`: run N frames with the bench keys, then dump `Vibe.Frame()` (object lines with their
  transforms) and the camera.
  - Run it with the translated handlers, then with the native ones; numbers must agree to a small tolerance
    (1e-6 relative).
  - Also compare once with the interpreter (`XTALK_INTERP=1`).
- Later, against real xRay in LiveCode at one `uDead.TestPlace` pose (`tools/gamebench` in the bridge), if he
  lets it run.

### 2. Native handlers (the first "native Python output")
- **Mechanism:** a native override table, `xtalk/native/`. Each entry is a module of plain Python functions
  named by the stack and handler (`VibeEngineXt3d`, `UpdateObjectTransforms`).
  - When a stack loads, a handler that has an override uses the Python function; the xTalk handler stays as
    the reference.
  - `XTALK_NATIVE=0` turns all overrides off.
  - Each override has a test: random inputs through both versions, the same answers (all three run modes).
- **Data:** the native function still receives and returns xTalk values (text, XtArray), converting once at the
  edges. Inside it, real numbers, tuples and lists.
- **First targets,** by share:
  1. `UpdateObjectTransforms`, `RotateLocalVector`, `Mat3.Mul` / `Mat3.*`: plain maths. Start with pure Python
     tuples (often fastest for 3x3), or raylib's own matrix functions (`MatrixMultiply`, `Vector3Transform`) if
     per-call cost allows. numpy is a NEW package: ask him first (CLAUDE.md).
  2. The engine's per-frame scene build (`Vibe.Frame` parts): profile after step 1.
  3. `uDead.FieldWork`: game logic. Do it after the owner's grid (below), since the grid changes it.
- **Watch:** globals and script locals the handler reads or writes (gCamera*, s* arrays), and the
  numberFormat / itemDel rules (LIVECODE_FACTS). A native handler must leave the same state behind.

### 3. A faster translator (helps every game)
- Handler variables are already Python variables and numbers stay floats in fast mode (CLAUDE.md). The profile
  still spends 8% in number-to-text, so find where floats become text:
  - array elements and globals (stored as text?);
  - parameters passed between handlers;
  - `put x into item n of y`.
  Keep them as numbers there too, becoming text only when used as text.
  - Golden cases in all modes must stay green; measured rules (fractions, numberFormat at text time) are in
    LIVECODE_FACTS.
- Cache `fmt_num` for common values; cheaper `gchunk` for item/line access in loops (`repeat for each` already
  splits once?).
- Handler call overhead: direct Python calls between handlers of the same script when nothing can intercept
  them. Mind front scripts, `pass`, and the target.
- Check after each change:
  - tests: interp 421, transpile 847, stack 139 (both modes), measured 30, xt3d 248
  - the survey, identical
  - the corpus count (`tools/translate_corpus.py -v ~/projects`; none worse, library count not lower)

### 4. Export a game as a Python program (native output he can read and run)
- `tools/export_py.py GAME`: writes a folder with the translated modules, native overrides and assets, plus a
  `main.py` that opens the window. No XTJSON or harvest is needed at run time.
- First target: uDead CullTest, then Raycasting_101. It runs from a desktop shortcut (LIB_BAT/desk_shortcut.sh).
- This is where "Pythonized" games come from (`pythonization-goal`: a reasonable Python app, not a pixel copy).

### 5. The owner's map grid (its own feature, LIB_GAMES + LIB_BIT)
His design from the 2008 uDeadGame:
- a fixed grid of cells per map, with the red target dots LEADING the zombies;
- dots only ever on grid cells, however many targets;
- A* pre-solved on that grid.

Presolve it per map (a file next to the map, or made at level load), then `uDead.FieldWork` reads it. That is
the large game-logic win after step 2. Ask him for details before building: grid size, dot rules.

## Open items carried along (from the play rounds)
- **Mouse look toggle** (he wants one; right-button look is fine for testing now).
- **Escape as in 2008:** physics/motion stop, animations go on, and a pause column of buttons (Title/"menu",
  controls...).
  - uDead's `Game.OnPause` already unlocks the cursor, so the window's Escape toggle may become unnecessary.
  - Today the View eats Escape in play mode: decide with him.
- `Users.Driver` (LIB_USERS not loaded by the bench; caught).
- `the long system date` / `the abbr system date` do not parse.
- `there is a file` reads the real disk while writes are sandboxed.
- xt3d file calls skip the sandbox and the C:/ mapping (HANDOFF_PHASE3 "Fix before merge").
- Raycasting_101 mouse look: probably fixed by the soft grab. Check it there too.

## How to work
- **His play:** he runs `tools/play_xt3d.sh` and I read the end of `run_files/play_xt3d.log`: the report, mouse
  look line, `his note:` lines (notes go to `run_files/elsewhere/.../GAME_NOTES.txt`).
- **Hidden checks:**
  - `XTALK_PLAY_TEST="note:60;120,close:200"` (or `end:N`) with `tools/xt3d_game_check.py --window`;
  - `tools/xt3d_game_check.py --frames N --keys ... --profile --eval`.
  - Never move his real mouse in tests: stub the raylib cursor calls (see the scratch look tests described in
    git log 5262693).
- **LiveCode is the referee:** `~/projects/LIB_MCP/tools/lcmcp --standalone run --server '...'` and
  `lcmcp compile FILE`. Afterwards end both copies (`Client.kill_slot(0)` and `(1)` from LIB_MCP/python).
- **Branches:** one branch per concept; commit as I go; no merge or push without his word. Add new files to
  `LIB_LLMOUT/FOR_REVIEW.txt` via `LIB_DEV/tools/for_review.py`; log bugs in LIB_SYSTEM/ISSUES.
