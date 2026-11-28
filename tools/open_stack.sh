#!/bin/sh
# Open a harvested stack in the Python runtime (Phase 2), window at 200,32.
#   ~/projects/xtalk_py/tools/open_stack.sh ~/projects/XTJSON/Game_card_reader_11_13_2025
# F2 hides the runtime panel (script errors, answers). Close the window to stop.
# What it prints goes to xtalk_py/run_files/open_stack.log.
cd "$(dirname "$0")/.." || exit 1
mkdir -p run_files
. tools/gpu.sh                      # graphics card when WSL has one; XTALK_GPU=0: CPU
if ! .venv/bin/python -I tools/open_stack.py "${1:-$HOME/projects/XTJSON/Game_card_reader_11_13_2025}" > run_files/open_stack.log 2>&1; then
  echo "open_stack: it stopped with an error. Last lines of run_files/open_stack.log:"
  grep -v -E "libEGL|MESA|GLFW" run_files/open_stack.log | tail -5
fi
