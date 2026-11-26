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
