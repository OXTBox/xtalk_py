#!/bin/sh
# The xt3d test bench in Python (x1-04), window at 200,32: the bridge's bench as his standalone starts it
# (testbench/xt3d_Bench_LibMCP.livecode, harvested), which opens testbench/xt3d_testBench_lib_mcp.livecodescript
# as it is. Models (Folder..., the list, Load file...), Spin/Grid/Tint/Solid/Wires, Face, Run checks, Games and
# Editor (play a Vibecode3D game card or a LIB_EDITOR example in the view; Escape or Stop game ends it), the console
# under the view (type Entity. then Tab; Return runs the line).
#   ~/projects/xtalk_py/tools/open_xt3d.sh
# Not in Python: the Dev server (no sockets yet: it says it could not listen; the Face button still shows the face).
# Like LiveCode's bench it writes C:/xt3d/raylib_log.txt (raylib's own lines go to the log below instead) and
# Run checks writes C:/xt3d/bench_checks.txt. Ctrl + / Ctrl - / Ctrl 0: the window's scale (remembered).
# What it prints goes to run_files/open_xt3d.log. It draws on the graphics card (tools/gpu.sh); XTALK_GPU=0: CPU.
cd "$(dirname "$0")/.." || exit 1
mkdir -p run_files
[ -f run_files/target_harvests/xt3d_Bench/manifest.json ] || tools/harvest_xt3d_bench.sh || exit 1
. tools/gpu.sh                      # graphics card when WSL has one; XTALK_GPU=0: CPU
if ! .venv/bin/python -I tools/open_stack.py run_files/target_harvests/xt3d_Bench > run_files/open_xt3d.log 2>&1; then
  echo "open_xt3d: it stopped with an error. Last lines of run_files/open_xt3d.log:"
  grep -v -E "libEGL|MESA|GLFW" run_files/open_xt3d.log | tail -5
fi
