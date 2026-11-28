# x1-04: the xt3d test bench as a Python app (approach note, helper C, 27 Nov evening)

## What the bench is

Two files in `xt3D_Raylib_Livecode_Bridge/testbench/` (read as they are, never changed):

- `xt3d_Bench_LibMCP.livecode`: a tiny binary stack (1 card, no controls, a 56-line stack script). It is the
  standalone's starter: walks up from its own file to find the bench script and LIB_MCP, starts LIB_MCP's dev
  server on port 8770, then `go stack <the bench script>`. In the IDE (`environment` = development) it does nothing.
- `xt3d_testBench_lib_mcp.livecodescript` (stack "xt3dTestBenchLibMCP", 1628 lines, script-only): builds all its
  own controls in preOpenStack (3D view image 720x540, console log + line, side panel: Folder..., file list,
  Load file..., Run checks, Spin/Grid/Tint/Solid/Wires/Culling/Cull front, animation menu, Play + frame slider,
  Reset camera, Face, Unload, Games, Editor, Stop game, Dev server, info field). Model viewer (C:/xt3d/test_models),
  Claude's face (LIB_MCP asset via LIB_MAP), Run checks, the Games / Editor lists that play Vibecode3D game cards
  and LIB_EDITOR examples on the engine's xt3d edition, LIB_ig3d's console under the view.

## How the harvest is made

`~/projects/LIB_MCP/tools/lcmcp --standalone harvest ~/projects/xt3D_Raylib_Livecode_Bridge/testbench/xt3d_Bench_LibMCP.livecode ~/projects/xtalk_py/run_files/target_harvests/xt3d_Bench`
(24 ms; one short lcmcp call). The harvest is git-ignored and shared through the run_files symlink, so a script on
the branch (`tools/harvest_xt3d_bench.sh`) remakes it. The harvest holds only the starter; the bench itself is
read straight from the bridge file by the starter's `go stack`, the same as in LiveCode.

## What already ran before this bubble

Only the view-only mode (`gXbViewRect` set: one image filling the window): `tools/xt3d_game_check.py` and
`tools/play_xt3d.sh` build a fake one-card harvest around the bench script and call `xbPlayGame`.

## First hidden run (this note's starting point)

Starter -> `go stack` bench -> preOpenStack builds all 26 controls -> openStack starts the view: "Ready. xt3d
0.1.0 / raylib 6.5-dev", grid drawn in the view. Two fixes so far (host.py): `accept connections` answers a
result (no sockets in Python, so DevServer.Start says it could not listen and the script goes on, as in LiveCode
when the port is taken), and `the screenLoc`.

## Steps

1. Harvest + recipe script (done above).
2. A hidden checker `tools/xt3d_bench_check.py`: open the starter, click controls by name (Games, a game, Stop game,
   a model, Face, checkboxes, Run checks), report errors, snapshot. Fix runtime gaps one by one (seen so far:
   button and checkbox labels not drawn, the file list empty for `C:/xt3d/test_models`, field borders).
3. The games from the full bench: the same xbPlayFile path as the play window, but inside the 720x540 view with
   the panel around it (key routing: Escape, console Tab guard, the click on the view = focus on nothing).
4. A window: `tools/open_xt3d.sh` (sources tools/gpu.sh) -> open_stack.py on the harvest (real_app), so the
   window follows the bench's own size; xt3d timers (send xbFrame in 16 ms, xbGameTick) run from the View loop.
5. Tests listed in the brief, report.

## Risks

- Dev server: Python has no sockets; the bench shows "Dev server: false" and the Face (shown only when the server
  runs) is behind the Face button. A real server in Python belongs to x1-06 (the lead's MCP plan), not here.
- `C:/...` paths (raylib log, checks log, test models): need the C: drive mapping (/mnt/c); writes in real_app go
  to his real C:/xt3d files (raylib_log.txt, bench_checks.txt), the same files LiveCode writes.
- scaleFactor: the bench sets `scaleFactor = 1 / screenPixelScale` (1 here) and its own px(); the window scale of
  x1-00 (Ctrl +/-) must not stretch the 3D image (it is a drawn texture, the g1-03 "big" frame helps).
- Rendering parts owned by helper B (view.py: labels, menus, borders): changes kept small and named in the report.
- Two engines in one window: the bench's own model view (xbFrame) and a game (xbGameTick) share the view image;
  only one runs at a time in the script, so it should hold.
