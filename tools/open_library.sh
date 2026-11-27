#!/bin/sh
# The Vibecode3D Library in Python (x1-02), reading the install on V: (his "real user" copy), window at 200,32.
#   ~/projects/xtalk_py/tools/open_library.sh
# Play opens the game in the Python play window (interim: the game's LIB_GAMES copy; see open_stack.py second_copy).
# The Library runs from LIB_PUBLIC/launcher/vibe_launcher.livecodescript (harvest: run_files/target_harvests/Vibecode3D_Library).
cd "$(dirname "$0")/.." || exit 1
mkdir -p run_files
if ! .venv/bin/python -I tools/open_stack.py run_files/target_harvests/Vibecode3D_Library \
     --engine "V:/Program Files (x86)/Vibecode3D" > run_files/open_library.log 2>&1; then
  echo "open_library: it stopped with an error. Last lines of run_files/open_library.log:"
  grep -v -E "libEGL|MESA|GLFW" run_files/open_library.log | tail -5
fi
