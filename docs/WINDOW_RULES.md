# Window rules (x1-08, 27 Nov)

One set of rules every Python stack window follows, built once in `xtalk/stack/view.py` (class View, the
"window rules" section). Every app gets them: Project Map, Priority Tube, the Vibecode3D Library, a game
window (the Library's Play, and the xt3d play window), any stack opened with `tools/open_stack.sh`.

A real window has the rules (`View(rt)`); a hidden window (the checks: test_stack, games_survey,
frame_referee, the xt3d checks) does not, so their numbers stay as they were, unless it asks (`rules=True`,
as `tests/test_window_rules.py` does).

| Rule | What happens | Where |
|---|---|---|
| **Opens at 200,32** | Owner rule (19 Nov): its topLeft at 200,32 in screen units (his screenRect 0,0,1536,864, i.e. pixels / Windows' 125%). A remembered place wins over it. The opening scripts may set a rect (the Library's game window centres itself, VL.WindowRect): the rule still places it, and after that a script that moves the stack (`set the loc / rect / left of this stack`) moves the window. | `place_window`, `move_to` |
| **Shown once** | `show_after_open` (27 Nov) is kept: the window stays hidden while preOpenStack / openStack run and appears once, at its final size and place. A dialog or menu during opening shows it at once. | `reveal` |
| **Fits the screen** | The whole window on the monitor, its title bar on screen, clear of the taskbar (48 units): first moved left / up; a stack still too big that may be resized is made smaller (not under its minWidth / minHeight) and gets resizeStack. Project Map (1500x900) opens as 1500x790 at 1.25. | `fit` |
| **The stack's rect is true** | `the rect / topLeft of this stack` say where the window is; dragging the window moves them; `globalLoc` and the screenMouseLoc use the same place. | `set_place`, `follow_window` |
| **Resize from the lower-right corner** | When the stack's `resizable` is true (LiveCode's default): the window frame resizes it, and a grip drawn in the lower-right corner (three short lines, 14 pixels) resizes it too. The top-left stays put; the card grows to the right and down. The card's scripts get `resizeStack newWidth, newHeight, oldWidth, oldHeight` (Project Map lays out its HUD and redraws, Priority Tube runs ptLayout). The grip is off for a play window, while the mouse is grabbed (mouse look), and while a menu or dialog is up. | `follow_window`, `grip`, `resize_units` |
| **Min / max size** | The stack's minWidth / minHeight / maxWidth / maxHeight (LiveCode's defaults 32 and 65535), times the scale, go to the window system, and our own code holds the owner's drag to them too. A script's own size is taken as given (LiveCode does that, measured). | `apply_limits`, `clamp_units` |
| **resizable false** | No grip, the frame does not resize it (the Library, every game window). Scripts can still set its size (measured). | `resizable` |
| **A script resizes the stack** | The window follows, and resizeStack goes to the card at once, as in LiveCode (measured 27 Nov). | `host.stack_resized`, `follow_stack_size` |
| **Close box = closeStackRequest** | A click sends `closeStackRequest` to the shown stack's card (LIB_ALPHA rule 12b: the handler sets destroyStack true and closes the mainStack). Passed, or no handler: the stack closes (closeCard, closeStack), as `close this stack` does. Not passed and not closed by the handler: the window stays, as in LiveCode. A click during a `wait`, menu or dialog is kept and answered once the scripts are back (the dialog is not cut short). A **second click** before the first was answered closes for sure (a script that never gets back). | `after_frame`, `close_request`, `run` |
| **Play window close** | The xt3d play window (tools/play_xt3d.sh) keeps "the close box is absolute" (owner 25 Nov): it ends the program at once, report written. | `should_close` (on_close) |
| **Scale** | Ctrl + / Ctrl - (steps of 0.05, 0.5 to 3), Ctrl 0 = Windows' own scale. The window and everything in it bigger or smaller; scripts see units only. The min/max sizes follow the scale. | `set_scale` (x1-00) |
| **Remembered per stack** | `run_files/windows.json`, one line per stack name (lower case): `scale`, `left`, `top` (screen units), and for a stack that may be resized `width`, `height` (card units). Written when the window closes (and the scale on Ctrl + / -). Read at the next opening, fitted to the screen again (another monitor, a bad value: brought back on screen). The older `run_files/window_scale.json` is still read for scales. `XTALK_NO_REMEMBER=1`: nothing is written. A hidden window never reads or writes it. | `remember_window`, `save_window`, `place_window` |

## The names a window is remembered under

The stack shown when the window first appears: `vibecode3d_launcher` (the Library), `play <game>` (a game window
from the Library's Play: place only, it may not be resized), `projectmap`, `prioritytube`, `xt3dtestbenchlibmcp` (the
xt3d play window; its scale stays under `xt3d game window`).

## Checks

`WAYLAND_DISPLAY=no-wayland .venv/bin/python -I tests/test_window_rules.py`: 41 checks on hidden windows (the place, a
script resize, the owner's resize faked by giving the window a new size, min size, the grip, resizable false, the close
box faked by setting GLFW's close flag (raylib reads it for one frame), kept / passed / during a wait / second click,
remembered place and size, too big for the screen, a hidden window without rules untouched).

What only a real window shows (the owner's try): the WSLg frame's own edge resize, the real close click, the place the
window system really gives (raylib asks it again for ~0.2 s after showing, `XTALK_DEBUG_PLACE=1` prints it).
