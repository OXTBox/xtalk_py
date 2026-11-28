# Handoff 27 Nov evening: START HERE (helpers + advisor run)

The owner (27 Nov eve): "we're going to use helpers and advisor to power through what there is to do, when
applicable ... prepare for the next steps with some reasonable extra hands on board." He just reordered the
Priority Tube; this plan follows it. Older handoffs (HANDOFF_2026-11-27.md and before) are history.

## Where things stand (all MERGED + PUSHED, 27 Nov eve)

- xtalk_py main a9a981d+: x1-03 GPU drawing is the DEFAULT (tools/gpu.sh, sourced by open_stack.sh,
  open_library.sh, play_xt3d.sh: only on WSL with /dev/dxg + Mesa's d3d12 driver; XTALK_GPU=0 = the CPU).
  g1-08 caseSensitive (values.fold / compare, pyrt.among_items; a new runtime starts it at false).
- LIB_GAMES main: g1-09 Thrmnlra note box types again (his note 27 Nov 17:38: "testing this looks like works");
  the fixed script is also on V: (copied, `vibeinstall.py verify` ok).
- No open branches, no worktrees, in any repo.
- Tests on main: interp 458, transpile 921, stack 191 (and with XTALK_INTERP=1), measured 36, xt3d 248,
  native ok, frame_referee AGREE, games survey 59/61 (Simple_Test2, demo: their own deleted-button bug).

### Not yet seen by him (carry forward)

- GPU default: measured hidden only (Squad Buggy 46 -> 58 fps, draw time 2-4x shorter); nobody has played
  through the launchers since the flip, and Library Play passing it on to the game's second copy was read from
  the code (no env= in open_stack.py's Popen), not run. His first try of the session:
  `~/projects/xtalk_py/tools/play_xt3d.sh SquadBuggy`, then `~/projects/xtalk_py/tools/open_library.sh` + Play.
  `grep -i renderer` is not printed by default; to see which card drew, raylib's INFO log shows
  "Renderer: D3D12 (NVIDIA GeForce RTX 3060 Laptop GPU)".
- Helpers run `tools/xt3d_game_check.py` DIRECTLY (not through the .sh launchers), so their numbers are on the
  CPU unless they source tools/gpu.sh: say which in every report, so numbers stay comparable.

## The tube, his order (LIB_LLMIN/LIB_DEV/PRIORITY_ORDER.txt, 27 Nov eve)

1 x1-06 MCP work in Python (plan) . 2 x1-05 behaviours leftovers . 3 x1-08 window rules . 4 x1-04 xt3d bench in
Python . 5 x1-09 shaders . 6 s1-01 pause + options screens . 7 x1-07 iGame3D XT editor in Python (deep test) .
then Comfy installer, Matrix Lock, ... (bottom: DOOM). Open board comment c1795473221928 (p1-03 "fixed by
Bill") is an old open comment on a done bubble: ask him whether to close it.

## The split (file ownership decides it: three helpers at most, plus the lead)

| Who | Branch / worktree | Bubbles, in order | Owns |
|---|---|---|---|
| Lead (main session) | `mcp-python` in ~/projects/xtalk_py | x1-06 plan FIRST (his OK before building), then the tools he approves; then s1-01 steps 1-2 (LiveCode measuring + keepsake harvest) | new `tools/mcp_*` / LIB_MCP side; LIB_SCREENS; merging |
| A Behaviours | `behaviours-2` | x1-05 | `xtalk/stack/runtime.py` (dispatch, long id), `xtalk/interp.py`, `xtalk/pyrt.py` (shared rule set: careful), tests |
| B Windows | `window-rules`, then `shaders` (made from window-rules) | x1-08, then x1-09 | `xtalk/stack/view.py`, LIB_SHADERS (`shaders/*.fs`, PLAN.md) |
| C xt3d bench | `xt3d-bench` | x1-04 | `xtalk/native/xt3d_testbench_host.py`, `xtalk/stack/host.py` (bench parts), new files, a new `tools/open_xt3d.sh` |

- Expected overlap: C may need small view.py changes (B owns it): keep them small, name them in the report;
  the lead merges B's window-rules first if both touch it. A and C may both touch runtime.py: merge A first.
- Merge order (one at a time, ALL tests + survey after each, only on his "merge"): A, B window-rules, C,
  B shaders, lead.
- Why the lead takes x1-06 and s1-01 steps 1-2: x1-06 is a plan whose answer is new sized bubbles (and may
  give the helpers better tools mid-run); s1-01 needs LiveCode (lcmcp) and the OXT-Beyond bridge, which only
  one agent may drive at a time. s1-01 never edits game scripts (LIB_SCREENS/PLAN.md: the game player shows
  the screens).
- lcmcp (`~/projects/LIB_MCP/tools/lcmcp --standalone`) is SHARED: short calls only; if busy, wait and retry;
  never kill it. x1-04's first step (harvest xt3d_Bench_LibMCP.livecode) and x1-09 step 2 (measure effects)
  use it.
- Use the advisor: before each helper's approach is fixed, when stuck, and before declaring done.

## x1-06 inputs already known (lead)

- Today's gap: to prove g1-09 the lead had to wrap StackRuntime.raw_key in a throwaway script, because
  `xt3d_game_check.py --keys` sends only rawKeyDown, never the typed key (keyDown / backspaceKey / the
  character into a focused field). A tool that plays a game hidden and TYPES text (rawKeyDown, then keyDown and
  the character, as a real window does) is the first candidate; fixing --keys itself is the smallest version.
- Other candidates to weigh: run an xTalk snippet in Python and in LiveCode side by side (differential test in
  one call); open any harvest hidden and answer `the X of Y`; snapshot a card; the games survey on one game.
- Look at what exists first: LIB_MCP (its MCP server and lcmcp), the oxt-beyond bridge tools, xtalk_py tools/.
  Plan only, sized bubbles into extra_items.txt + claude_sizes.txt, then his word.

## Worktree recipe (worked 27 Nov)

```
cd ~/projects/xtalk_py
git worktree add ../xtalk_py_wt/<branch> -b <branch> main
ln -s ~/projects/xtalk_py/.venv ../xtalk_py_wt/<branch>/.venv
mkdir -p ../xtalk_py_wt/<branch>/run_files
ln -s ~/projects/xtalk_py/run_files/target_harvests ../xtalk_py_wt/<branch>/run_files/target_harvests
```
Removing: `git worktree remove --force` (the .venv link is untracked). Hidden windows:
`WAYLAND_DISPLAY=no-wayland` (X11), or a hidden window's framebuffer does not resize. Two helpers appending to
docs/LIVECODE_FACTS.md = a conflict at each merge: keep both sides.

## Brief header (paste at the top of every helper's brief)

> TWO ENGINES: Engine 1 = pure xTalk Vibecode3D (XT); Engine 2 = the xt3d raylib bridge (xRay).
> `xt3D_Raylib_Livecode_Bridge/testbench/vibe_engine_xt3d.livecodescript` is GENERATED (Engine 1's script for
> the xt3d bench): NEVER edit it, and never edit game scripts in LIB_GAMES; fix the Python runtime instead.
> Read ~/projects/xtalk_py/CLAUDE.md first. Work ONLY in your worktree (path below), commit ONLY on your branch,
> never merge/push/checkout main, never edit other projects (reading is fine). LiveCode 9.6.3 is the reference:
> when unsure, ask it (`~/projects/LIB_MCP/tools/lcmcp --standalone eval --server '<expr>'`, shared: short
> calls) and write the answer in docs/LIVECODE_FACTS.md. After any change to xtalk/: test_interp +
> test_transpile; after native/: test_native + frame_referee --run; before your last commit: ALL of
> `python3 -I tests/test_interp.py` (458), `test_transpile.py` (921), `test_stack.py` (191, and again with
> XTALK_INTERP=1), `test_measured.py` (36), `.venv/bin/python -I tests/test_xt3d.py` (248), test_native,
> frame_referee --run (AGREE), `.venv/bin/python -I tools/games_survey.py` (59/61). Say whether your fps were
> on the CPU or the GPU (source tools/gpu.sh for the GPU). Never grab the screen (look_at_card or a hidden
> --snap only). Report in plain words (the owner reads it): what was wrong, what you changed, numbers, and ONE
> command he can run to try it from your worktree.

## Briefs

**A, Behaviours** (worktree ~/projects/xtalk_py_wt/behaviours-2, branch behaviours-2), x1-05:
- `it` after `dispatch` (handled / unhandled / passed) is measured in LiveCode but not built (GAMES_SURVEY.md
  line ~55, HANDOFF_2026-11-26_EVENING.md ~158): find the measured values (LIVECODE_FACTS; measure again if
  missing) and set `it` the same way in both modes.
- `the long id` of a script-only stack loaded from a file should be its path: measure, build, test.
- Add both to tests/test_measured.py (all three modes). His try: nothing to play; the report says what a script
  now sees.

**B, Windows** (worktree ~/projects/xtalk_py_wt/window-rules, branch window-rules; then shaders), x1-08 then x1-09:
- x1-08: one set of rules every Python window follows, written down once (docs/WINDOW_RULES.md) and built once
  in View: resize from the lower-right corner, min sizes, opens at 200,32, close = closeStackRequest (the stack's
  own handler first, LIB_ALPHA 12b), the scale (x1-00, Ctrl + / - / 0), size and place remembered per stack.
  Check each app: Project Map, Priority Tube, the Library, a game window. Keep the show-once opening (27 Nov,
  `show_after_open`) working. His try: `~/projects/xtalk_py_wt/window-rules/tools/open_library.sh`.
- x1-09 (branch shaders, made from window-rules, only after x1-08's report): LIB_SHADERS/PLAN.md steps 1-4:
  which harvests use outerGlow / innerGlow / dropShadow / innerShadow / colorOverlay (read the harvests' props),
  measure one effect in LiveCode, then one shader at a time (blur, glow, shadow) drawn per object that has an
  effect; a stack with no effects costs nothing. Shader files go in LIB_SHADERS/shaders (that repo, its own
  branch `shaders`). His try: a stack with a glow, opened through tools/open_stack.sh.

**C, xt3d bench** (worktree ~/projects/xtalk_py_wt/xt3d-bench, branch xt3d-bench), x1-04:
- The xt3d test bench (xt3D_Raylib_Livecode_Bridge/testbench/xt3d_Bench_LibMCP.livecode, script
  xt3d_testBench_lib_mcp.livecodescript) as a real Python app, as the Library was in x1-02: harvest it
  (LIB_XTJSON / LIB_LLMIN/xtalk_py/fromXJSON recipe, into run_files/target_harvests/xt3d_Bench), run it hidden,
  fix what fails, then a window. Today only its view-only mode runs (tools/xt3d_game_check.py, play_xt3d.sh).
- Never edit the bridge's files; the bench's script is read as it is.
- His try: a new `~/projects/xtalk_py_wt/xt3d-bench/tools/open_xt3d.sh` (sources tools/gpu.sh like the others).

## After the run

- Lead: one report to him in plain words, each branch with its try command; mark bubbles done in
  LIB_DEV/PriorityTube/extra_items.txt + `python3 -I tools/tube_items.py`; every new file on the review list
  (LIB_DEV/tools/for_review.py add); merge only on his "merge"; push after merging, as on 27 Nov.
- Before he leaves: night shutdown rule (nothing armed: no waiters, wakeups, loops, background jobs).
