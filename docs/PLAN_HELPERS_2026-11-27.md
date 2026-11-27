# Plan: helpers in parallel (written 26 Nov night, for a fresh terminal)

Owner's ask: "What can you work on with helpers to get done faster without stepping on each other's commits?"
then "write the plan and the handoff and we'll spin up a fresh Terminal". He agreed to the split below.

## Where things stand (all MERGED + PUSHED on main, 26 Nov night)

- xtalk_py main = bf46ff0 + handoff commits. game-speed merged: Dot Maze 62 fps, Squad Buggy 29 fps (his plays).
- Tests at that point: interp 458/458, transpile 921/921, stack 186/186 (both modes), measured 30/30, xt3d 248/248,
  native 3603/3603, frame_referee AGREE, games survey 59/61 (Simple_Test2 + demo: their own deleted-button bug).
- Priority Tube (LIB_DEV/PriorityTube): bugs g1-01..04 + g1-06 open, g1-05 done.

## The rule that keeps helpers apart

1. Each helper gets its OWN git worktree of xtalk_py on its OWN branch:
   ```
   cd ~/projects/xtalk_py
   git worktree add ../xtalk_py_wt/<branch> -b <branch> main
   ln -s ~/projects/xtalk_py/.venv ../xtalk_py_wt/<branch>/.venv
   mkdir -p ../xtalk_py_wt/<branch>/run_files
   ln -s ~/projects/xtalk_py/run_files/target_harvests ../xtalk_py_wt/<branch>/run_files/target_harvests
   ```
   (.venv and run_files are git-ignored; every tool finds its folder from its own path, nothing hard-codes
   ~/projects/xtalk_py, so a worktree is self-contained. Logs and pngs land in the worktree's own run_files.)
2. A helper commits ONLY on its branch, in its worktree. It never merges, never pushes, never checks out main,
   never edits another project (reading is fine).
3. Each helper owns the files in its row; touching a file of another row = say so in the report, keep it small.
4. The lead (main session) merges one branch at a time into main, runs ALL tests + the survey after each, and only
   on the owner's "merge". The owner plays a helper's work from its worktree, e.g.
   `! ~/projects/xtalk_py_wt/play-window/tools/play_xt3d.sh Thrmnlra`.
5. The machine draws on the processor (WSLg llvmpipe): at most 3 helpers at once while he plays.
   Hidden windows: `WAYLAND_DISPLAY=no-wayland` (X11), or a hidden window's framebuffer does not resize.

## The split

| Helper | Branch / worktree | Bubbles | Owns |
|---|---|---|---|
| A Play window | `play-window` | g1-01, g1-02, g1-03 | `xtalk/stack/view.py`, `xtalk/native/xt3d_testbench_host.py`, `tools/xt3d_game_check.py` |
| B Missing pieces | `game-libs` | g1-04, g1-06 | library loading / missing handlers in `xtalk/stack/runtime.py` + new files; NOT host.py's launch/shell parts |
| C Speed | `speed-2` | g1-07 Squad Buggy slow spells | `xtalk/native/vibe_engine_xt3d.py`, `xtalk/parser.py`, `xtalk/pyrt.py` (careful: shared rule set), `tests/test_native.py` |
| Lead | `library-play` | x1-02 step 2 | `xtalk/stack/host.py`, `tools/open_stack.py` |
| D raylib (LATER, on his word) | bridge branch `raylib-examples` | batch 2 (~20 examples, no files) | `xt3D_Raylib_Livecode_Bridge/examples_xt/` only |

Overlap to expect: B and Lead may both touch runtime.py (create stack / libraries). Lead merges B first if so.

## Briefs (paste each as a helper's task; every brief starts with the TWO ENGINES note)

Common header for every brief:

> TWO ENGINES: Engine 1 = pure xTalk Vibecode3D (XT); Engine 2 = the xt3d raylib bridge (xRay).
> `xt3D_Raylib_Livecode_Bridge/testbench/vibe_engine_xt3d.livecodescript` is GENERATED (Engine 1's script for
> the xt3d bench): NEVER edit it, and never edit game scripts in LIB_GAMES; fix the Python runtime instead.
> Read ~/projects/xtalk_py/CLAUDE.md first. Work ONLY in your worktree (path below), commit ONLY on your branch,
> never merge/push/checkout main, never edit other projects. LiveCode 9.6.3 is the reference: when unsure, ask it
> (`~/projects/LIB_MCP/tools/lcmcp --standalone eval --server '<expr>'`) and write the answer in
> docs/LIVECODE_FACTS.md. After any change to xtalk/: test_interp + test_transpile; after native/: test_native +
> frame_referee --run; before your last commit: all of tests/ plus `tools/games_survey.py` (59/61 expected).
> Report in plain words (the owner reads it): what was wrong, what you changed, numbers, how he can try it.

**A, Play window** (worktree ~/projects/xtalk_py_wt/play-window, branch play-window)
- g1-01 Thrmnlra (LIB_GAMES/Vibecode3D_Games/Vibecode3D_Play_Thrmnlra...): the asset names to type and
  destroy are not drawn in the Python play window. Find where the game writes them (a field? the info line?
  xt3d text drawing?) and why Python does not show it. Compare with LiveCode if unsure.
- g1-02 In Thrmnlra, ` opens the GameNotes box; Esc is taken but the box stays and the keyboard stays locked.
  In Squad Buggy the note box WORKED (26 Nov 22:19), so find what Thrmnlra does differently (its own key
  handling / `\\` console key / focus). GameNotes: Return saves, Esc cancels and the game goes on.
- g1-03 Game windows open at scale 1 and look ~25% too small, text and pictures cropped (Block City Hustle).
  The window scale (x1-00: view.py scale, Ctrl +/-/0, run_files/window_scale.json) was kept OFF game windows
  because of xt3d's own clipping/scissor. Give game windows the scale, with xt3d's 3D image and clip
  following it; then fix any cropping. Scale 1 must stay exactly as now.

**B, Missing pieces** (worktree ~/projects/xtalk_py_wt/game-libs, branch game-libs)
- g1-06 Every play log: `unknown property "the users.driver"` (stack LIB_LOADING, h_loading_user) and
  `unknown property "the data.root"` (GameNotes, inside value()). Caught by a try, but the loading screen and
  notes then miss the user / the Data folder. The handlers live in LIB_USERS/livecode/lib_users.livecodescript
  and LIB_DATA/livecode/lib_data.livecodescript. Find how LiveCode gets them in use (start using / library
  stacks) and why Python does not have them; note `the users.driver` is a FUNCTION call written as a property
  (a custom function `Users.Driver` called as `the Users.Driver`?) - check what LiveCode does with that form.
- g1-04 Block City Hustle "might have crashed on start" (his note 26 Nov 18:42). Run it hidden:
  `WAYLAND_DISPLAY=no-wayland .venv/bin/python -I tools/xt3d_game_check.py BlockCityHustle --frames 300`,
  read errors, compare with LiveCode, fix in the runtime.

**C, Speed** (worktree ~/projects/xtalk_py_wt/speed-2, branch speed-2)
- Squad Buggy in his window (26 Nov 22:19): average 29 fps, often 40-60, but spells at 8 fps (step 107 ms)
  and 18 fps (step 38 ms), likely when many things spawn (bombers, craters, explosions, Entity.Spawn/Kill,
  Scene.Register/Remove/Has). Profile:
  `XTALK_PROF_OUT=<file> WAYLAND_DISPLAY=no-wayland .venv/bin/python -I tools/xt3d_game_check.py SquadBuggy --frames 200 --keys "d:20, :40" --profile`
  and `--slow MS` (prints what ran in a frame slower than MS). Known left-over cost: Squad.Ground's ~94
  Entity.SetPosition a step; chunk access (`item n of`), XtArray case lookups. Tools that worked today: parse
  memory (parser._PARSED), native handlers with SIGS (tools/native_sigs.py) + a test case in test_native.py.
  Every native must match its xTalk to the bit (frame_referee AGREE). Also check Dot Maze stays at 60.

**Lead, x1-02 step 2** (worktree ~/projects/xtalk_py_wt/library-play, branch library-play)
- The Library's Play now (interim) starts tools/play_xt3d.sh on the LIB_GAMES copy (open_stack.py
  second_copy). Step 2: support `create stack`, `set the script of stack`, `go stack` in the runtime so Play
  runs the INSTALLED copy on V: through game_player, like LiveCode. See HANDOFF_2026-11-26_EVENING.md (x1-02).

**D, raylib examples batch 2** (only when the owner says; he has not yet tried the first 10)
- Plan: xt3D_Raylib_Livecode_Bridge/reference/raylib_examples/PLAN_OUR_EXAMPLES.md; first 10 in examples_xt/,
  checked by tools/check_examples_xt.py. Bridge folder is on branch raylib-examples (not pushed).

## Merge order (lead, on his word, one at a time, tests + survey after each)

C speed-2 (smallest surface) -> B game-libs -> A play-window -> library-play.
After the merges: `git worktree remove ../xtalk_py_wt/<branch>` and delete the branch; update the tube
(extra_items.txt status done, `python3 -I PriorityTube/tools/tube_items.py`), the handoff top, memory.
