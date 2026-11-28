# x1-06: MCP work in Python (plan only, nothing built)

27 Nov 2026, Claude (Opus 5.5), the lead. The bubble: "Which of our MCP tools gain from Python; plan only."
Your word picks which bubbles get built; until then nothing below exists.

## What we have today

| Tool | Where it runs | What it is good at | What hurts |
|---|---|---|---|
| **lcmcp** (LIB_MCP) | LiveCode 9.6.3 standalone, port 8767 (Windows) | the REFEREE: what real LiveCode answers | ONE copy shared by everyone (two at most); slow to start; a helper must wait its turn |
| **LIB_MCP mcp_server** | Python, stdio; tools `livecode_run/eval/compile/errors/snapshot` + packs (xt3d, xtjson) | gives LM Studio / Claude Desktop LiveCode | every tool still goes to the one LiveCode |
| **oxt-beyond bridge** | OXT-Beyond on your screen | reading and building YOUR open stacks, look_at_card | one driver (only the lead); you are asked before every run |
| **xtalk_py tools/** | Python, hidden windows | games survey, xt3d_game_check (--keys --eval --snap), open_stack --snap --click, golden.py | each is its own command line with its own options; no way to keep a stack open between questions |

The Python runtime is the one thing that can run **as many copies as we like, hidden, at once, with nothing on
your screen**. That is what Python adds: every helper gets its own LiveCode-like engine to ask questions of,
instead of queueing for the one LiveCode.

What stays as it is: lcmcp and the LiveCode server stay LiveCode (they are the referee, the thing we compare
against). The oxt-beyond bridge stays for your own open stacks.

## The gap that started this (27 Nov, g1-09 Thrmnlra)

`xt3d_game_check.py --keys` sends only rawKeyDown. A real window sends rawKeyDown, then keyDown with the
character, then types it into a focused field (or backspaceKey, returnInField...). To prove the note box could be
typed in, I had to write a throwaway script. Typing text into a hidden game must be one option.

## Bubbles (smallest first; each its own branch in xtalk_py)

| id | size | what you get |
|---|---|---|
| **x1-11** | 30 min, fix | `xt3d_game_check.py --type "hello:300"`: from frame 300 types `hello` the way a window does (rawKeyDown, keyDown, the character into the focused field; `\b` = backspace, `\n` = Return). Fixes the g1-09 gap. |
| **x1-12** | 90 min, utility | **`xtpy`**, a command line like lcmcp but for Python: `xtpy HARVEST_OR_GAME do 'click button "OK"' 'type hello' 'key 65361' 'frames 60' 'eval the text of fld 1' 'snap out.png'`. One stack opened hidden, the steps run in order, the answers printed. Replaces the scattered options of open_stack --snap/--click and xt3d_game_check --keys/--eval. Any number may run at once. |
| **x1-13** | 60 min, utility | **`xtpy diff '<xTalk>'`**: runs a snippet in the interpreter, in the fast (translated) mode and in LiveCode (lcmcp, one short call), shows the three answers side by side and says AGREE or which one differs; `--fact` drafts the LIVECODE_FACTS.md line. Today this is three tools and hand work each time a rule is measured. |
| **x1-14** | 120 min, big | **A Python MCP tool pack** (`xtalk_py/mcp/xtpy_tools.py`, plugged into LIB_MCP's mcp_server with `--tools`, the way xt3d and XTJSON packs are): `xtpy_open` (keeps a stack open in memory, hidden, between calls), `xtpy_eval`, `xtpy_run`, `xtpy_click`, `xtpy_type`, `xtpy_frames`, `xtpy_snap`, `xtpy_close`, `xtpy_diff`, `xtpy_game` (the survey on one game). Like the oxt-beyond bridge, but invisible, safe to run many at once, and on Python. Registered for Claude Code in ~/projects (so every helper has it) and usable from LM Studio. Built on x1-12's steps. |
| **x1-15** | 20 min, utility | Spark (local model) tries the x1-14 tools through LM Studio: open a game, press keys, read a value; notes what a small model gets wrong; one primer page for it like `livecode_primer.md`. |

Order: x1-11 at once (it helps every helper now), then x1-12, x1-13, x1-14, x1-15. x1-12 and x1-13 can be done by
two helpers side by side (different files); x1-14 waits for x1-12.

## Not worth doing (looked at, left out)

- Rewriting LIB_MCP's server (the LiveCode side) in Python: it must stay LiveCode, it is the referee.
- A second copy of the oxt-beyond bridge on Python: the x1-14 pack covers the hidden side; your screen stays OXT.
- Pythonizing the `xt3d_MCP` standalone stack: it is a launcher for the LiveCode server, nothing to run in Python.

## Questions for you

1. Build x1-11 now (30 min, helps the helpers already running)?
2. The rest: all four, in that order, or only some?
3. x1-14: register the Python tools for Claude Code in all of ~/projects (every session and helper sees them), or
   only inside xtalk_py?

## His answers (27 Nov night)

"for now run with MCP Python": all five, built in the order above (x1-11, x1-12, x1-13, x1-14, x1-15; the
tube now lists them that way). Shaders (x1-09) next, then the raylib Examples folder (x1-16).
Question 3 not answered: Claude's pick is to register the x1-14 tools in all of ~/projects, so every helper has
them (he can say otherwise before x1-14 is merged).

- x1-11 DONE on branch `type-keys`: `StackRuntime.type_char` + `xt3d_game_check.py --type "TEXT:FRAME"`
  (repeatable; \b \n \t). Tried on Thrmnlra: `` `hellx\bo:40 `` opened the note box and left "hello" in it.
- x1-12 DONE on branch `xtpy` (made from `type-keys`: merge type-keys first): `xtalk/session.py` (one stack kept
  open hidden, steps click/type/key/hold/release/frames/eval/run/snap/stats/errors) + `tools/xtpy` (steps on the
  command line, or `serve`: one step a line in, one JSON answer a line out, for x1-14). One session a process
  (raylib has one window a process): many at once = many processes, each its own run_files/xtpy/<pid> folder,
  where the stack's writes go (checked: a note saved in Thrmnlra's box lands there, GAME_NOTES.txt unchanged).
  tests/test_xtpy.py (14, two at once included). make_stack moved from xt3d_game_check into xtalk/session.py.
- x1-13 BUILT on branch `xtpy-diff` (made from `xtpy`): `tools/xtpy diff '<xTalk>'` (tools/xtpy_diff.py): interpreter,
  translated, fast mode, LiveCode; AGREE / DIFFER; `--fact` drafts the LIVECODE_FACTS line; `--no-lc`.
  LiveCode is asked once, never retried (exit 2 = not asked). The LiveCode column is NOT yet tried: it waits for
  his OK to ping lcmcp (a failed start opens a command prompt on his screen).
