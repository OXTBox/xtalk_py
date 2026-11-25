#!/bin/sh
# Open a harvested stack in the Python runtime (Phase 2), window at 200,32.
#   ~/projects/xtalk_py/tools/open_stack.sh ~/projects/XTJSON/Game_card_reader_11_13_2025
# F2 hides the runtime panel (script errors, answers). Close the window to stop.
cd "$(dirname "$0")/.." && exec .venv/bin/python -I tools/open_stack.py "${1:-$HOME/projects/XTJSON/Game_card_reader_11_13_2025}" 2>/dev/null
