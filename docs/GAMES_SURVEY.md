# Games survey (26 Nov 2026)

`.venv/bin/python -I tools/games_survey.py` plays every `LIB_GAMES/Vibecode3D_Games/Vibecode3D_Play_*.livecodescript`
in Python (hidden window, test clock, the same keys and clicks for all, 600 frames, own process each; a hang reports
where it was). Full list: `run_files/games_survey.txt` (not in git). Takes about 15 minutes, 4 at a time.

| Pass | ok | errors | hang | black |
|---|---|---|---|---|
| first (main after the merges) | 50 | 8 | 3 | 0 |
| after the fixes below | 58 | 2 | 0 | 1 |

Fixed, each measured in LiveCode first (LIVECODE_FACTS 26 Nov, golden cases):
- `split` / `combine` did not exist (PhotonBall's clip loader; then its frame loop spun).
- an array used as text stopped with an error; LiveCode: empty text, and a non-empty array equals no text (5 games).
- `bitAnd` / `bitOr` / `bitXor` / `bitNot` did not exist (lib_cellmap lost 5 handlers: Amazing_Couple). Corpus +22 handlers.
- `is among the keys of` = lines.
- `stack "<path of a script file>"` loads that script-only stack (Thrmnlra's sequencer).

Open:
- **Script behaviors** (`set the behavior of X to ...`): not in the runtime. Thrmnlra (its Sequencer) shows nothing;
  the harvested stacks nine-ball, LightCycles3, card reader also carry behavior properties. Next big runtime piece.
- Simple_Test2 and demo set the label of btn "Next Preset", which the engine deletes on purpose: a bug in those game
  scripts (would fail in LiveCode too); not changed without the owner.
- Every game logs two caught errors from the loading screen (both in `try` on purpose): `Users.Driver` (LIB_USERS not
  loaded in the test host) and `export snapshot` (not built in Python).
- Slowest in Python: DotMaze 16 fps, MeadowMarsh 18, DeadDays 21, SquadBuggy 26 (the rest 35-60).

## The owner's own apps (26 Nov): harvested to run_files/target_harvests (lcmcp harvest), stack survey
Owner 26 Nov: Pythonize OUR apps (Vibecode3D Library, xt3d, Project Map, Priority Tube, MCP work; iGame3D XT editor =
deep test); the XTJSON harvests are test material only.
- ProjectMap, PriorityTube: stopped at open on `the stacksInUse` (empty = "unknown property"): fixed, both open with
  no errors. They draw their boards themselves (no buttons), so the survey clicks nothing: the real test is a window.
- Vibecode3D_Launcher: `$#` / `$1` did not parse (fixed). Its `send setStackScript to card 1` fails in LiveCode too
  (no handler anywhere): a launcher bug, left for the owner.
- Example harvests: all clean (TKInter-izer 14/15, the missing button is not in the stack; XtRedeemer does not load:
  not a stack harvest).
