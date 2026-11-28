#!/bin/sh
# Play a Vibecode3D game in Python through the xt3d testbench host (Phase 3), window at 200,32.
# The view is 900x600 like the launcher's game window; the window is scaled like Windows (125% -> 1.25),
# Ctrl + / Ctrl - / Ctrl 0 change it (remembered for every game window).
#   ~/projects/xtalk_py/tools/play_xt3d.sh                 uDead CullTest
#   ~/projects/xtalk_py/tools/play_xt3d.sh GAME [WxH]      another game in LIB_GAMES/Vibecode3D_Games
# Keys 0-3 switch uDead's hiding modes. Esc frees the mouse and keys (Esc again: back to the game).
# Hold the right mouse button to look; XTALK_LOOK_SPEED=3 (default 2) turns faster.
# The close box ends it at once (the report is written first). ` (left of 1) = a note to the AI (Return saves).
# What it prints goes to xtalk_py/run_files/play_xt3d.log, with a report at the end.
# It draws on the graphics card (tools/gpu.sh); XTALK_GPU=0 in front draws on the CPU.
cd "$(dirname "$0")/.." || exit 1
mkdir -p run_files
. tools/gpu.sh                      # graphics card when WSL has one; XTALK_GPU=0: CPU
if ! .venv/bin/python -I tools/xt3d_game_check.py "${1:-uDead_CullTest}" --window --size "${2:-900x600}" > run_files/play_xt3d.log 2>&1; then
  echo "play_xt3d: it stopped with an error. Last lines of run_files/play_xt3d.log:"
  grep -v -E "libEGL|MESA|GLFW" run_files/play_xt3d.log | tail -5
fi
