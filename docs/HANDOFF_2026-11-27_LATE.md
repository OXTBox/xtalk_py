# Handoff 27 Nov late: START HERE (MCP Python run)

This file lives on branch `mcp-pack` (worktree ~/projects/xtalk_py_wt/mcp-pack) until the merge.
HANDOFF_2026-11-27_NIGHT.md is history except its Open list, carried over below.

## His word 27 Nov late (all done)
- p1-03 board comment closed (a `done` line in BOARD_COMMENTS.txt).
- LIB_SHADERS on GitHub: github.com/OXTBox/LIB_SHADERS, public, MIT LICENSE (raylib reference keeps zlib); added
  with LIB_SCREENS to LIB_BAT/get_everything.bat and LIB_ARRAY/get_everything.sh (both pushed).
- x1-16 (raylib Examples) placed right after x1-09 shaders. Tube now: x1-11, x1-12, x1-13, x1-14, x1-15
  (build order), x1-09, x1-16, s1-01, ... (the Tube reloads PRIORITY_ORDER.txt by itself every 2 s).
- "for now run with MCP Python": x1-11..x1-14 built, x1-15 ready (LM Studio was off).

## The chain (xtalk_py; each branch made from the one before; merge in this order, full tests after each)
type-keys (x1-11) -> xtpy (x1-12) -> xtpy-diff (x1-13) -> mcp-pack (x1-14, x1-15 prep, review fixes).
What each gives: docs/MCP_PYTHON_PLAN.md, "His answers" at its end. Full test list: CLAUDE.md, Working rules
(new: tests/test_xtpy.py, 25). Survey on mcp-pack (27 Nov late): 59/61, the same two as before (Simple_Test2, demo: missing btn).
After the merge: register `mcp/xtpy_server.py` (xtpy tools ONLY) for Claude Code at user scope (command in the plan).

His tries (worktree ~/projects/xtalk_py_wt/mcp-pack):
- `tools/xtpy Thrmnlra 'frames 40' 'type \`hello' 'eval the text of field "GameNote"' 'snap /tmp/x.png'`
- `tools/xtpy SquadBuggy 'frames 400' 'hold d' 'frames 120' 'release d' 'stats'`
- `tools/xtpy diff --no-lc '7 mod -3'`
- with LM Studio on: `python3 -I tools/spark_try_xtpy.py`

Safety, checked: xtpy sessions write only in run_files/xtpy/<pid> (a note saved in Thrmnlra's box landed there,
GAME_NOTES.txt unchanged; C:/xt3d/raylib_log.txt untouched); they start no programs (shell/launch noted only);
the runtime has no delete/rename/save-stack. Spark's runner and xtpy_server give no LiveCode tools.

## Waiting on him
1. OK to ping lcmcp once (a failed start opens a command prompt on his screen). Then: xtpy diff's LiveCode column,
   the Backspace/Return/arrow question in LIVECODE_FACTS (rawKeyDown taken -> special keys?), x1-09 step 2,
   s1-01 steps 1-2.
2. The LIB_MCP hidden-restart fix (start the standalone hidden, one retry): still waits for his word.
3. LM Studio on, for x1-15 (then note what Spark gets wrong, fix mcp/xtpy_primer.md).
4. "merge" for the chain.
5. LIB_VectorMap note + "Imagine this as 3D cities" stack (two copies) in LIB_LLMIN: not acted on yet.

## Carried over from the NIGHT handoff (still open)
- lcmcp 8767: the reboot should have ended the stuck copy; one ping (with his OK) tells. RULE: never export
  snapshot from the windowless standalone.
- x1-04: `read from file` not built; dev server off; harvest_xt3d_bench.sh not run end to end.
- x1-08 extras he may keep or drop: shrink-to-fit, second close click = force close.
- x1-05: Project Map's long ids left as names (one line in stack_ref if he wants).
- GPU default through the launchers: not yet played by him. His four NIGHT tries (open_library.sh,
  open_xt3d.sh, open_stack.sh NeonArcade, play_xt3d.sh SquadBuggy) are on main.
