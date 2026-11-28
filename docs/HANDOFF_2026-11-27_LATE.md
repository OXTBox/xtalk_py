# Handoff 27 Nov late: START HERE (MCP Python run; older handoffs are history)

His word 27 Nov late: p1-03 comment closed; LIB_SHADERS to GitHub (DONE: github.com/OXTBox/LIB_SHADERS, MIT, in
both get_everything lists with LIB_SCREENS); x1-16 placed right after x1-09 shaders in the tube; "for now run
with MCP Python". Tube order now: x1-11, x1-12, x1-13, x1-14, x1-15, x1-09, x1-16, s1-01...

Chain of branches in xtalk_py (each made from the one before; merge in this order, all tests after each):
type-keys (x1-11) -> xtpy (x1-12) -> xtpy-diff (x1-13) -> mcp-pack (x1-14 + x1-15 prep).
Details and his try lines: docs/MCP_PYTHON_PLAN.md (the "His answers" part at its end).
Full test list: CLAUDE.md "Working rules" (test_xtpy.py new: 22).

His tries (on branch mcp-pack):
- `tools/xtpy Thrmnlra 'frames 40' 'type \`hello' 'eval the text of field "GameNote"' 'snap ~/x.png'`
- `tools/xtpy diff --no-lc '7 mod -3'`
- with LM Studio on: `tools/spark_try_xtpy.sh`

Waiting on him:
1. OK to ping lcmcp once (then: xtpy diff's LiveCode column, the Backspace/Return question in LIVECODE_FACTS,
   x1-09 step 2, s1-01).
2. LM Studio on, for x1-15.
3. "merge" for the chain; after it, register the pack for Claude Code (command in MCP_PYTHON_PLAN.md).
4. LIB_VectorMap note + "Imagine this as 3D cities" stack in LIB_LLMIN (not acted on yet).
