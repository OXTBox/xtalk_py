#!/bin/sh
# Play a Vibecode3D game in Python through the xt3d testbench host (Phase 3), window at 200,32.
#   ~/projects/xtalk_py/tools/play_xt3d.sh                 uDead CullTest
#   ~/projects/xtalk_py/tools/play_xt3d.sh GAME [WxH]      another game in LIB_GAMES/Vibecode3D_Games
# Keys 0-3 switch uDead's hiding modes. Close the window (or Esc) to stop.
# What it prints goes to xtalk_py/run_files/play_xt3d.log, with a report at the end.
cd "$(dirname "$0")/.." || exit 1
mkdir -p run_files
if ! .venv/bin/python -I tools/xt3d_game_check.py "${1:-uDead_CullTest}" --window --size "${2:-720x540}" > run_files/play_xt3d.log 2>&1; then
  echo "play_xt3d: it stopped with an error. Last lines of run_files/play_xt3d.log:"
  grep -v -E "libEGL|MESA|GLFW" run_files/play_xt3d.log | tail -5
fi
