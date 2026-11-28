# xtpy primer: playing and testing xTalk stacks with the xtpy tools

Read this before using the other xtpy tools. xTalk is LiveCode Script (HyperCard's family). It is NOT
JavaScript or Python.

## The usual order

1. `xtpy_games` lists the games. Pick a name exactly as listed (example: `SquadBuggy`).
2. `xtpy_open` with `target` = that name. It answers `session 1: ... is open`. Remember the number.
3. Let the game load: `xtpy_frames` with `count` 400. The first 200-400 frames are a loading screen,
   and a picture taken then is black. That is normal.
4. Play or test: `xtpy_key`, `xtpy_type`, `xtpy_click`, then `xtpy_frames` again so the game can react.
5. Look: `xtpy_eval` for a value, `xtpy_snap` for a picture.
6. `xtpy_close` when done. Up to 4 stacks may be open at once.

For a quick health check of one game, `xtpy_game` with `game` does all of it: it opens the game, plays it
for a while, and gives you the speed, the script errors and a picture.

## Keys

- `xtpy_key` with `key` = `d`: one tap. Games that steer with held keys need `hold` true, then
  `xtpy_frames`, then the same key with `hold` false.
- Key names: `space` `return` `backspace` `tab` `escape` `left` `right` `up` `down`, or one character,
  or a number (65361 = left arrow).
- `xtpy_type` with `text` types into the focused field, one key a frame. `\n` is Return, `\b` is Backspace.
- The backtick key opens a game's note box. Return in it saves a note. Here the note stays in a test
  folder, so trying it is safe.

## Expressions for xtpy_eval (xTalk, not JavaScript)

```
the text of field "Score"
the number of controls of this card
the short name of the focusedObject
the loc of graphic "Player"
gScore                                  -- any global is visible to xtpy_eval
the keysDown
```

Use `xtpy_run` for statements, one per line, as in a handler:

```
global gLives
put 9 into gLives
```

## Common mistakes

- Strings use double quotes, never single: `field "Score"`, not `field 'Score'`.
- Statements go in xtpy_run, not xtpy_eval: `put 1 into x` is a statement.
- `put x into y`, never `y = x`. A test is `if x = 1 then`; `==` does not exist.
- The line delimiter is `return` (or `cr`). Strings are joined with `&`, or `&&` for a space between.
- A FAILED answer says why. Read it before trying again, and do not repeat the same call unchanged.
- `xtpy_diff` runs a small piece of xTalk in Python three ways. With `ask_livecode` true it also asks
  real LiveCode. Use it to check what an expression gives.
