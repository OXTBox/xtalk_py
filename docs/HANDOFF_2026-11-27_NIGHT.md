# Handoff 27 Nov night: START HERE (helpers run finished, nothing merged)

All four helper bubbles reported; everything sits on branches in worktrees, waiting for his look and "merge".
Older handoffs (27_EVENING and before) are history.

| Bubble | Branch / worktree | State | His try |
|---|---|---|---|
| x1-05 behaviours | behaviours-2 (~/projects/xtalk_py_wt/behaviours-2), 2 commits | done | `cd ~/projects/xtalk_py_wt/behaviours-2 && python3 -I tests/test_measured.py -v` |
| x1-08 window rules | window-rules (wt/window-rules), 3 commits | done | `~/projects/xtalk_py_wt/window-rules/tools/open_library.sh` |
| x1-04 xt3d bench | xt3d-bench (wt/xt3d-bench), 5 commits | done | `~/projects/xtalk_py_wt/xt3d-bench/tools/open_xt3d.sh` |
| x1-09 shaders | shaders (wt/shaders, made from window-rules) + LIB_SHADERS branch `shaders` (checked out) | steps 1,3,4 done; step 2 (measure in LiveCode) open | `~/projects/xtalk_py_wt/shaders/tools/open_stack.sh ~/projects/XTJSON/3DShufflepuckaroo_v5_NeonArcade` |
| x1-06 MCP plan | mcp-python (main checkout ~/projects/xtalk_py), docs/MCP_PYTHON_PLAN.md | done; bubbles x1-11..x1-15 wait for his answers (3 questions in the doc) | read the doc |

## Merge (only on his "merge"; ALL tests + survey after each; push after)
Order: behaviours-2, window-rules, xt3d-bench, shaders (+ LIB_SHADERS shaders), mcp-python.
Trial merges (git merge-tree): A+B clean, A+C clean, B+C conflict in docs/LIVECODE_FACTS.md (keep both) and
xtalk/stack/host.py (resolve by hand). C also edited interp/pyrt/fastgen/transpile/parser (A's files): clean
against A, but re-run every test. Test counts after all: stack 191 + A 4 + C 4, measured 36 + A 4 + C 6, new
test_window_rules (48) and test_effects (24): add both to the full list (CLAUDE.md/brief header).

## Open
- **lcmcp standalone (port 8767) stuck since ~19:55** after B's `export snapshot ... with effects` on an invisible
  stack. Lead killed it once (kill_slot 0); the new copy logs "started" and holds the port but never answers, and
  each client ping deletes its token after 15 s. Stopped retrying. Ask him to close any "xt3d dev server"
  window/dialog; then one ping. RULE: never export snapshot from the windowless standalone.
- x1-09 step 2 (measure effects in LiveCode, no snapshots first): list in LIB_SHADERS/PLAN.md + LIVECODE_FACTS.
- x1-04: `read from file` not built; dev server off (no sockets); harvest is in the shared git-ignored
  run_files/target_harvests/xt3d_Bench (tools/harvest_xt3d_bench.sh remakes it, not run end to end); opening the
  bench empties C:/xt3d/raylib_log.txt (as LiveCode does; C's test already emptied his 25 Nov lines).
- x1-08 extras he may keep or drop: shrink-to-fit (Project Map 1500x790 at 1.25), second close click = force close.
- x1-05: Project Map's long ids left as names (LiveCode would give the path): one line in stack_ref if he wants.
- Board comment c1795473221928 (p1-03 "fixed by Bill"): ask whether to close.
- s1-01 steps 1-2 (lead, LiveCode + OXT bridge) not started: needs lcmcp back.
- GPU default through the launchers: still not played by him.
