#!/bin/sh
# Remake the harvest of the xt3d test bench's standalone starter (x1-04) with LiveCode 9.6.3 (lcmcp, one short call).
#   ~/projects/xtalk_py/tools/harvest_xt3d_bench.sh
# In:  xt3D_Raylib_Livecode_Bridge/testbench/xt3d_Bench_LibMCP.livecode (the bridge's file, only read)
# Out: run_files/target_harvests/xt3d_Bench (git-ignored; in a worktree that folder is a link to the main checkout's)
# The starter's script then opens the bench script itself (testbench/xt3d_testBench_lib_mcp.livecodescript), read
# from the bridge each time, as LiveCode does: a change to the bench needs no new harvest.
cd "$(dirname "$0")/.." || exit 1
mkdir -p run_files/target_harvests
exec ~/projects/LIB_MCP/tools/lcmcp --standalone harvest \
  "$HOME/projects/xt3D_Raylib_Livecode_Bridge/testbench/xt3d_Bench_LibMCP.livecode" \
  "$(cd run_files/target_harvests && pwd -P)/xt3d_Bench"
