#!/bin/bash
# x1-15: Spark (the local model in LM Studio) tries the xtpy MCP tools. LM Studio must be running with its
# server on (port 1234) and a model loaded. Writes run_files/spark_try_xtpy.log (the tool calls and answers).
# Usage: tools/spark_try_xtpy.sh [MODEL]     (default: lib_mcp.ask_local's default, spark)
cd "$(dirname "$0")/.." || exit 1
LOG=run_files/spark_try_xtpy.log
MODEL=${1:+--model $1}
PACK="$PWD/mcp/xtpy_tools.py"
: > "$LOG"
ask() {
  echo "=== $1" | tee -a "$LOG"
  (cd ~/projects/LIB_MCP/python && python3 -m lib_mcp.ask_local $MODEL --max-steps 12 --tools "$PACK" "$1") >> "$LOG" 2>&1
  tail -3 "$LOG"; echo
}
ask "Read xtpy_primer. Then list the games and tell me how many there are."
ask "Read xtpy_primer. Open the game SquadBuggy, let it load, hold the d key for 120 frames, let it go, and tell me the game's stats line. Close it after."
ask "Read xtpy_primer. Open Thrmnlra, let it load, open its note box with the backtick key, type hello, and tell me the text of field \"GameNote\". Close it after."
ask "Use xtpy_diff to find what the xTalk expression 7 mod -3 gives."
echo "log: $LOG"
