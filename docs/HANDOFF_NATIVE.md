# Handoff: native Python output (written 25 Nov 2026, late night, system clock)

**Read first:** `CLAUDE.md`, `docs/ROADMAP.md`, then `HANDOFF_PHASE3.md` START HERE (what runs today), then this.

## The owner's word (25 Nov, late night)
After playing uDead in the Python window ("absolutely passable performance and user interaction"):
"at this point we are loading the livecode in and testing what bugs we find in the python in memory, the next best
step should certainly be **native python output**. ... you're going to get all that done in the order you see fit
and use the help you need to do it."

So the order below is mine to choose, and helper agents may be used: one per bubble, each with a clear test to
pass. The **TWO ENGINES** note goes in every brief.

## PROGRESS (25 Nov 2026, night): steps 0-2 done on branch `native-bench` (xtalk_py; NOT merged, NOT pushed)
uDead CullTest, 900 frames of the bench (hiding mode 3, rush, walk, turn), back to back on a quiet machine:

| Run | Wall | Frames a second | Step | Scene | Draw | Rest |
|---|---|---|---|---|---|---|
| native off (`XTALK_NATIVE=0`) = the old speed | 40-42 s | 22 | 7.6 ms | 17.6 ms | 19.8 ms | 2 ms |
| native on (all below) | 20.2 s | 44.5 | 6.1 ms | 3.9 ms | 8.9 ms | 3.6 ms |

Real play path (`tools/xt3d_game_check.py`, real clock, mode 3 + rush, hidden window): 11-13 fps -> 34-37 fps.
**Nothing here has been seen on his screen yet.** His next `tools/play_xt3d.sh` on this branch uses the natives
(they are on by default); `XTALK_NATIVE=0` turns them off.

What was built:
- **Step 0, the bench:** `tools/bench_xt3d.py`. The scripts' clock is a test clock (`xtalk.interp.CLOCK`: moves
  with the frames and 0.05 ms a read), so uDead's "work for 7 ms" loop and `set the randomSeed to the milliseconds`
  are the same every run; no real mouse; keys after the loading screen (it ignores keys before about frame 230).
  `--check` = two processes, the same state byte for byte (globals, every script's locals, the picture every 30
  frames). No game script was changed (the planned `gTestSeed` was not needed).
- **Found on the way:** `set the randomSeed` did nothing in Python (ISSUES 0027): now measured and done.
- **Step 1, the referee:** `tools/frame_referee.py --run [GAME]`: native off / on / interpreter / interpreter +
  natives. uDead 450 frames: all four AGREE; Antack and BigBallOfVectors: native on = off.
- **Step 2, native handlers:** `xtalk/native/` (one module a script, plain Python functions in place of xTalk
  handlers, at load, both run modes):
  - engine (`vibe_engine_xt3d.py`): Mat3.Mul (cached), RotateLocalVector, UpdateObjectTransforms, Xform.Object
    (rotation + RotZYX + Mul + Apply + position in one go), Vibe.Color (Color.ToRGB cached);
  - host (`xt3d_testbench_host.py`): xbDrawGame (the same xt3d calls straight to raylib), xbGameModel /
    xbGameFill (a made model found without copying the mesh).
  - **Safety:** each native is tied to the exact statements of the xTalk it copies (signature; also every helper
    it copies inside, and the engine handlers the host reads around). When the engine is generated again and a
    handler changed, that native switches itself off with a warning and the xTalk runs:
    `tools/native_sigs.py` shows which. A value a native was not written for (text where a number belongs)
    goes to the xTalk handler (Fallback), before anything is changed or drawn.
  - `tests/test_native.py`: 3000 random cases, native = xTalk in both modes; an edited helper is noticed.
- **Not covered:** xbDrawGame's DrawText line (only when not view-only) has never run. uDead.FieldWork (a card
  script) waits for his grid (step 5 below).
- **What is left in a frame:** step = uDead.FieldWork mostly (his grid changes it); draw = mostly the picture
  coming back from the GPU into the image (RenderTextureImageData, ~2.5 ms) and the GPU wait: that is the "3D in
  an image" design, not xTalk speed. A game drawing to the whole window (HANDOFF_PHASE3) would skip it.

**Questions for him (step 5, his grid), waiting:**
1. Grid size: one cell per map tile (uDead's 1.5 m cells), or coarser (2x2, 4x4 tiles)?
2. The red target dots LEAD the zombies: how far ahead (cells or seconds), and do they move each step or only
   when the target crosses a cell?
3. Many targets: one dot per target, or one dot per cell however many targets stand in it?
4. A* "pre-solved": a table of next steps from every cell to every cell (big for large maps), or only to the
   cells where dots can be (doors, rooms)? Is a slightly longer path fine if it is much faster?
5. Made once per map at level load (a pause), or saved in a file next to the map?

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

## His answers (25 Nov, after midnight): MERGED, and numpy is approved
- Both branches below are **merged into main** (xtalk_py e86ea67, LIB_GAMES 8997640). **Not pushed:** a push needs
  his word for that push. Start new branches from main.
- **numpy is approved** and installed in `.venv` (2.5.5, pinned in `requirements.txt`). Use it in native handlers
  where it pays (measure per-call cost: tiny 3x3 matrices can be faster as plain tuples; whole arrays of objects
  are where numpy wins). The core `xtalk/` and its tests stay standard-library only (`python3 -I`).

## What was merged (he played these and liked the result)
- xtalk_py branch `phase3-play-fixes`:
  - close box ends the game at once; Escape frees the mouse and keys
  - mouse look: soft grab under WSL, right-button look tuned in his play
  - GameNotes front scripts; the defaultStack; `value(expr, obj)`; the system date
  - `put after URL` adds to the file; `mouse(3)`
- LIB_GAMES branch `udead-blood-limit`: blood capped at 3 (`kBloodMax`; 0 = none); right-button look
  (`kLookRightMouse`) in both uDead scripts.

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
     per-call cost allows. numpy is approved (above): batch all objects' transforms in one array op if per-call cost is the limit.
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
