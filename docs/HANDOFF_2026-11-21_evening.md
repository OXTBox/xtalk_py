# Handoff, 21 Nov 2026 evening (Sonnet 5.5), continues HANDOFF_2026-11-21.md

## Done today (since the morning handoff)
- Ran `tools/golden.py` once as it was: hung for 10 min (no answer, no output), and the standalone (8767)
  stayed stuck afterwards. `tests/golden.json` is STILL NOT regenerated; nothing in xtalk_py committed
  (uncommitted: `tests/lib_cases.txt`, `tests/lib_cases_games.pending.txt`, `tools/golden.py`).
- LIB_MCP (own repo, committed on main, b4dc612 + a follow-up): standalone copies with ABSOLUTE rules.
  - At most two copies. `xt3d_MCP.exe` = port 8767, `xt3d_MCP_1.exe` = port 8768 (launcher takes the port
    from its own exe name; any other name is refused and quits). Owner rebuilt with the new launcher.
  - Both exes sit in `LIB_MCP/standalone/` (owner's copies were named xt3d_MCP1/2.exe; I renamed them,
    no rebuild needed). Both verified: `3*3` answers 9 on each.
  - Client: `Client.standalone(slot=0|1)` or env `LIBMCP_SLOT`; slot >= 2 refused; counts running
    `xt3d_MCP*` processes (tasklist.exe) and refuses a third; `Client.kill_slot(n)` ends one copy and
    drops its token (`/mnt/c/LIB_MCP/devtoken_876X.txt`). `lcmcp --standalone` uses LIBMCP_SLOT.

## Next steps (in order)
1. `tools/golden.py`: replace `restart_standalone()` by the slots. One engine+game group per fresh copy:
   `Client.kill_slot(n)`, start slot n, run the group, alternate slots 0/1 (never more than two).
   Add a hang log next to golden.py (`tools/golden_hangs.log`): case, library, seconds, slot, timeout.
   Per-group timeout (about 120 s, the first load takes ~10 s), then kill that copy and go on with the next group.
2. Run `python3 -I tools/golden.py` (run it in the background, groups are slow), then `python3 -I tests/test_interp.py`
   (was 302 of 302 before the new rows).
3. Then the open cases: GemInfo/RandomGem (runaway loop in 9.6.3, not understood), the valid-segments Face case
   (parked in `tests/lib_cases_games.pending.txt`), the asin rounding difference, Face.SegmentsToMesh bad-line case.
4. Record measured behaviour in `docs/LIVECODE_FACTS.md`; commit xtalk_py when golden is regenerated.

## Traps
- Second engine+game library in the SAME session hangs LiveCode: one game group per fresh copy.
- `pkill -f <name>` kills your own shell if the name is in the command line. `taskkill.exe`/`tasklist.exe`
  take 20 s+ when WSL is slow (ISSUES 0001-0003).
- Owner's rule: a stuck window is his to close; do not kill his other LiveCode windows (kill by exact exe name only).
