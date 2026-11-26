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
- ~~Script behaviors~~: done 26 Nov (branch script-behaviors), see "Behaviors" below.
- Simple_Test2 and demo set the label of btn "Next Preset", which the engine deletes on purpose: a bug in those game
  scripts (would fail in LiveCode too); not changed without the owner.
- Every game logs two caught errors from the loading screen (both in `try` on purpose): `Users.Driver` (LIB_USERS not
  loaded in the test host) and `export snapshot` (not built in Python).
- Slowest in Python: DotMaze 16 fps, MeadowMarsh 18, DeadDays 21, SquadBuggy 26 (the rest 35-60).

## Behaviors (26 Nov, branch script-behaviors)

`set the behavior of X to <a button | a stack | a script-only stack file>` and a harvested `behavior` now work as
LiveCode 9.6.3 does (measured first: LIVECODE_FACTS "Behaviors"): the path is the object, its behavior, the
behavior's behavior, then the object's groups / card / stack; `me` is the object; each object using a behavior has
its own script locals; `dispatch function` gives the handler's value as the result; `dispatch ... with` an array
keeps the array (before, it arrived empty: the sequencer's clip settings).

| Pass | ok | errors | hang | black |
|---|---|---|---|---|
| all 61 games with behaviors | 59 | 2 | 0 | 0 |

- Thrmnlra: no longer black. The Sequencer group runs its clips (Wait, Type, Ask clip buttons, each with its own clip
  behavior) and types "GREETINGS. WOULD YOU LIKE TO PLAY A GAME? [Y] / [N]" in vector lines; no script errors, in
  both run modes (translated and XTALK_INTERP=1). The survey's keys do not answer Y/N, so it waits there.
- The 2 errors are the known Simple_Test2 / demo game-script bug (btn "Next Preset").
- Harvest survey (tools/survey_stacks.py): the same as before, click for click. No harvest in ~/projects/XTJSON has a
  script behavior: their "behavior" keys are listBehavior / backgroundBehavior / radioBehavior flags.
- Not done: `it` after dispatch (handled / unhandled / passed, measured) is not set; `the long id` of a script-only
  stack loaded from a file gives `stack "Name"` (LiveCode gives the file path).
