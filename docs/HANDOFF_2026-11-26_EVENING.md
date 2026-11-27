# Handoff, 26 Nov evening: START HERE

Everything below is MERGED to main and PUSHED (xtalk_py, LIB_MENU, LIB_GAMES), on the owner's word.
Nothing is waiting on a branch.

## GAME SPEED (26 Nov night): branch `game-speed`, 3 commits, waits for his look + "merge"

- 4d0ac02 an @parameter's array is not copied: Dot Maze dots rebuild 325 -> 45 ms (the 3-4 dot jumps).
- 4b8c8b3 direct drawing: an xt3d frame goes graphics card -> window (Obj.pixels_from makes imageData only when
  read; XTALK_DIRECT=0 = old way). Dot Maze 15 -> 62 fps in his window (log of his play).
- 005e1cc `do`/value() texts parsed once (parser._PARSED); native SetObjectPosition (engine's six `do` lines);
  UpdateObjectTransforms via a lower-case key table. Squad Buggy hidden test 3.6 -> 26 fps (step 290 -> 25 ms);
  in his window it was 12 fps before this commit. Next if wanted: Squad.Ground's ~94 Entity.SetPosition calls a step.
- Profiling: `XTALK_PROF_OUT=file tools/xt3d_game_check.py GAME --frames N --profile` (pstats dump).
- Bug for the tube: LIB_LOADING asks `Users.Driver` (unknown property, caught by try) in every game.

## (26 Nov ~19:00): x1-02 Vibecode3D Library in Python, step 1, branch `library-python` (waits for his look)

- Open: `tools/open_library.sh` (reads the install on V:, `--engine "V:/Program Files (x86)/Vibecode3D"`).
- Runs from `LIB_PUBLIC/launcher/vibe_launcher.livecodescript` (harvest run_files/target_harvests/Vibecode3D_Library,
  git-ignored: `lcmcp --standalone harvest <that file> <that folder>` to remake). NOT from his saved
  Vibecode3D_Launcher.livecode: there the script sits on card 1, the stack script is empty, and preOpenStack's
  `send setStackScript to card 1` throws 573 in LiveCode too (measured, both engines); openStack then passes. Ask him.
- New in the runtime: the window follows the stack's size set by script; `launch document/url X`, `launch X with Y`
  (real window: cmd start; checks: noted); a stack starting ITSELF again (shell `start "" "<own file>" args` or
  launch ... with <own file>) -> rt.on_self_launch(args) (open_stack: second_copy). open_stack takes --engine and `-- ARGS` ($1..).
- Play is INTERIM: second_copy opens tools/play_xt3d.sh on the game's LIB_GAMES copy (test bench host), not the
  installed copy through game_player. 53 of 54 installed games have a LIB_GAMES copy (not Genetic Anomaly).
  Step 2 = create stack / set the script of stack / go stack in the runtime so VL.Play runs as written.
- Hidden snapshots must use X11 (WAYLAND_DISPLAY=no-wayland): on Wayland a hidden window's picture does not resize.

## LATEST (26 Nov ~17:45): priority-tube + window-scale MERGED and PUSHED. x1-01 (Tube reloads itself) MERGED + pushed too (owner saw it live). NOW: x1-02 Library in Python, branch `library-python`

- ptWatch in the Tube's stack script: every 2 s compares items.txt + PRIORITY_ORDER.txt + TUBE_REMOVED.txt with what it
  last read/wrote; changed -> ptBuild true (scroll kept), bar "Reloaded: Claude changed the tube". Not while dragging.
- The script now lives in `LIB_DEV/PriorityTube/priority_tube.livecodescript`; applied to the .oxtstack headless
  (OXT-BEYOND/tests/oxt_headless.py: lock messages, set the script of stack <file>, save) and re-harvested with
  `lcmcp --standalone harvest`. Checked hidden: 21 -> 20 bubbles within 2 s after marking x1-00 done.
- A raylib-examples helper runs in xt3D_Raylib_Livecode_Bridge (branch raylib-examples; plan in
  reference/raylib_examples/PLAN_OUR_EXAMPLES.md).

## LATEST (26 Nov ~17:30): x1-00 window scale on branch `window-scale` (off `priority-tube`). OWNER CHECKED: Ctrl +/- works, menus open where he clicks, size kept on reopen (Tube remembered at 1.2). Not merged yet.

- Why the windows were small: Windows is at 125% (AppliedDPI 120); WSLg draws our window one pixel a unit
  (measured: monitor 1920x1080, window DPI 1.0). LiveCode draws at 125%. Default scale = Windows' own (1.25).
- `View(rt, scale=...)`: one matrix scales the card; scissors (rounded outward), mouse in, warp out, menu place,
  ImGui sizes + font (rebuilt from scale 1 each time) follow. Scripts see units only. Scale 1 = pixel-identical.
- Text sharp: letters made at 2x (sharp to 1.5); over 1.5 a bigger set is drawn, placed by the measuring set's
  advances (layout never changes with scale).
- Keys: Ctrl + / Ctrl - (0.05 steps, 0.5..3), Ctrl 0 = Windows' scaling. Remembered per stack in
  `run_files/window_scale.json` (a '*' entry = default for every stack). `XTALK_SCALE=1.5` overrides.
- Only `tools/open_stack.py` windows scale (Tube, Project Map, ...). Checking tools, snapshots and the xt3d play
  window stay at 1 (xt3d's own scissors/screen sizes are in generated/).
- Not built: a menu entry for the scale; the window following a script's stack resize (x1-08).
- At 1.25 the Tube is 950x1075 pixels on a 1080 screen: bottom off screen; Ctrl - to ~1.1 fits (fitting = x1-08).

## LATER SAME EVENING: Priority Tube, steps 1-2 on branch `priority-tube` (not merged, waits for his look)

- Checked hidden (real_folders): opens with no errors; select, arrows, Shift-arrows, drag, wheel, right-click
  menu with LIB_MENU's ending, Move to top, Leave comment, Delete, U, T, the panel's Remove link, resize all work.
  Opening rewrites PRIORITY_ORDER.txt byte-for-byte as LiveCode would (ranks, tabs, final newline); Delete then U
  leaves TUBE_REMOVED.txt byte-identical. R sends `wsl.exe python3 -I ".../tube_items.py"` (a twin of it ran
  through cmd.exe fine; the real one was not run: it rewrites items.txt).
- Fixed (all measured in LiveCode, LIVECODE_FACTS): formattedHeight/Width of fields (bubble words were invisible),
  roundRadius (= the corner's diameter; bubbles are pills), links in fields (<a href>, linkText, linkClicked in
  place of mouseUp in a locked field).
- Opening drops "Pythonizing day" (n-f59d34e9) from the order: it is no longer in items.txt. LiveCode does the same.
- Found, NOT fixed (offer to him): text widths. LiveCode = exact font advances at size x 4/3 (plain Segoe x1.033);
  raylib truncates advances, so Python text is ~4-8% narrower and wraps later. Fixing it moves text in every app.
- His two Project Map test comments of 26 Nov 10:21/10:26 are only in the sandbox copy of BOARD_COMMENTS.txt
  (run_files/elsewhere/...), written before real_app; ask before copying them to his real file.

## Next job (the owner's words): Priority Tube in Python

"lets get that CPU use down and then we'll work on the tube". CPU is done, so the Tube is next.
Do it the way Project Map was done today:

1. Harvest is already in `run_files/target_harvests/PriorityTube` (git-ignored). If it is stale,
   harvest again with `lcmcp harvest` from `LIB_DEV/PriorityTube/PriorityTube.oxtstack`.
2. Check it hidden first, without touching his files: `StackRuntime(folder, real_folders=True)` plus
   `rt.harvest.main.filename = <its real Linux path>`. In that mode, writes go to the sandbox and
   shell() is refused. Then click its controls with `rt.mouse_down/up` and set `rt.on_menu` to pick menu items.
3. Then give him the command to open it:
   `! ~/projects/xtalk_py/tools/open_stack.sh ~/projects/xtalk_py/run_files/target_harvests/PriorityTube`
   Read `run_files/open_stack.log` after he closes it. It records clicks, keys typed, menus shown,
   script errors, and every `shell (cmd.exe): ...` command sent to Windows.
4. Fix what he reports, one thing at a time; tests after each change (list at the end).

## What a window he opens now is ("real app", owner 26 Nov)

`tools/open_stack.py` and the play window (`tools/xt3d_game_check.py --window`) use
`StackRuntime(..., real_app=True)`:
- **His real files.** It writes his real files ("as if they are real apps").
- **shell().** shell() runs any command through Windows `cmd.exe` (`StackHost.windows_shell`):
  - the command goes in an environment variable (`XT_CMD`, via WSLENV); as an argument, WSL escapes every quote;
  - `%NAME%` is filled in from Windows' own settings first.
- **Platform and filename.**
  - `the platform` is "Win32".
  - The stack's filename is the harvest's `sourceFile` (`//wsl$/Ubuntu/...`), the name his LiveCode uses.
  - `real_path` reads `//wsl$` paths.

The checking tools (games survey, bench, dots check, xt3d_game_check without --window) use
`real_folders=True` only. They read his folders, write to `run_files`, refuse shell(), and the platform is "Linux".
Never give a checking tool `real_app`.

## Done today (26 Nov), in order

- **Games survey and behaviors.**
  - 59 of 61 games run clean in Python (`docs/GAMES_SURVEY.md`).
  - Script behaviors, split/combine, the bit operators, and arrays used as text are measured in LiveCode and built.
  - The 2 games left fail because of their own script bug: they set the label of "Next Preset", which is deleted. Leave them unless he asks.
- **Project Map in Python** (he tried every item):
  - the board data loads;
  - the wheel sends rawKeyDown 65309/65308;
  - menus nest to any depth, with picks given as a full path "a|b|c";
  - submenus stay open: the menu window takes focus only once;
  - set textColor/foreColor/backColor now stores the real colour, which fixed the comment box;
  - Explorer, Open in, Terminal and WSL bash work.
- **LIB_MENU.** "Terminal here" (now `pushd`, because cmd cannot start in a `\\wsl$` folder) and "WSL bash here" are default folder entries.
  His private copies in `LIB_USERS/BILL/Data/Menus` are the same files.
- **Idle CPU**, branch idle-cpu, merged. Project Map went from 205% to 0%. His verdict: "MUCH better".
  - **Faster lookups.** `model.Props` indexes each object's properties (`keys_for`), and `host.canon` remembers names.
    Drawing went from 32 to 46 frames a second.
  - **Idle mode.** After 0.5 s with no input, no change and no timer about to fire, the window shows a stored picture of the card at 10 frames a second.
    It matches a normal draw pixel for pixel. To check, call `rl.rl_draw_render_batch_active()` BEFORE `load_image_from_screen`,
    or the last batch is missing from the screenshot.
  - **Sleeping.** It also sleeps (raylib event waiting) when no timer is waiting and no field has focus.
    `wait`, menus and dialogs call `View.wake()`. A timer that ran counts as a change.

## Open, not started

- **GPU drawing.** The window is drawn by the processor (Mesa llvmpipe). With `GALLIUM_DRIVER=d3d12`
  and `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA`, it is drawn on his RTX 3060.
  - Project Map changed little, because its cost is Python.
  - For the 3D games it may be big. Offered to him, not tested.
- **Behaviors leftovers.**
  - `it` after dispatch (handled / unhandled / passed) is measured but not built.
  - The long id of a script-only stack loaded from a file should be its path.
- **Python file commands.** delete file, rename and `open file ... for write` are not in Python yet; nothing we run uses them.
- **The other apps.** The owner's target list: Vibecode3D Library, xt3d, Priority Tube, MCP work; the iGame3D XT editor is the deep test
  (memory `pythonization-targets.md`).

## Tests after any change to xtalk/

```
python3 -I tests/test_interp.py        # 458
python3 -I tests/test_transpile.py     # 921
python3 -I tests/test_stack.py         # 181, and again with XTALK_INTERP=1
python3 -I tests/test_measured.py      # 30
.venv/bin/python -I tests/test_native.py ; .venv/bin/python -I tools/frame_referee.py --run
```
