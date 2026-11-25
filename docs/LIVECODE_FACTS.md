# LiveCode 9.6.3 behaviour, measured

Answers taken from the real engine (through LIB_MCP), for the interpreter to reproduce
exactly. Each line was checked in LiveCode 9.6.3; add the date and how.

## Values
- `"1.0" = 1` is true (2026-11-11, IDE).

## Chunks
- `word 1 to -1 of char 1 to 5 of x` is a compile error, "Chunk: bad chunk order (must be small to large)" (2026-11-11, compile check).

## Loops
- `repeat with x = a to b step s` (s not 1) runs one extra pass past `b` unless the steps land on `b` exactly: `1 to 8 step 4` gives 1, 5, 9; `1 to 10 step 4` gives 1, 5, 9, 13; `10 down to 1 step -4` gives 10, 6, 2, -2. In effect it continues while x < b + s. Use `repeat while` when the end matters. (2026-11-11, standalone)

## Handlers and do
- Code run with `do` inside a handler shares that handler's locals: declaring `local tErr` again in the done code is a compile error (2026-11-11).

## Measured 2026-11-21 (tests/golden.json, made by tools/golden.py; LiveCode 9.6.3 standalone)
- Numbers print with the `numberFormat` default `0.######`: `1/3` is `0.333333`, `pi` is `3.141593`, `sqrt(2)` is `1.414214`. Whole numbers print plain. All arithmetic is double precision: `2^53 + 1` is `9007199254740992`; `100000000000000 + 0.5` is `100000000000000.5`.
- `-2^2` is `4` (unary minus binds tighter than `^`); `- - 3` is an error.
- `true and "x"` is `false`, no error (and/or treat anything but "true" as false).
- `switch` matches cases exactly, case-sensitively: `switch "b"` does not take `case "B"`.
- `switch` falls through (measured 24 Nov, standalone): the first case that matches (cases are tried in order,
  also those below the default), else the default, is where it starts; from there every body runs, through the
  `case` lines and the `default` line, until a `break`. `case "a"` / `case "b"` / body is one body for both.
  Tests: the last three blocks of tests/script_cases.txt ("AB", "CDyz", "1/DE!F/E/").
- A chunk given to an `@` (by reference) parameter of a command is an error: `T.Bump2 item 2 of tC` (measured 24 Nov).
  A variable and an array element (`tK["n"]`) are fine.
- `repeat for each element tE in tArray` walks the values of an array (measured 24 Nov: 5 + 7 = 12).
- `return` inside `try` still runs `finally`; `throw` goes to `catch` with the thrown text (tests/wrap_translator.txt).
- `repeat with i = 10 down to 1 step 4` (positive step with `down to`) runs zero times. `repeat with i = 1 to 10 step 4` gives 1, 5, 9, 13 and leaves `i` at 13.
- `word`, `char` and the like, written bare, are errors (reserved words), not variables.
- `cr` is a newline (ASCII 10), the same as `return`; not a carriage return.
- QUIRK, unexplained: LCHarvest2's `jArray` (recursive, with `exit repeat` then `sort lines of tKeys` then a second `repeat for each line tKey`) printed the key `""` for a nested array's second key in 9.6.3, though the value was found under the right key. Small recursive loops with `exit repeat` did not reproduce it. The case is left out of tests/lib_cases.txt.
- After a library test run, always `stop using stack` / `delete stack` the test stack: a leftover test library in the long-lived standalone made later expression runs hang (tools/golden.py now cleans up).
- (SOLVED 22 Nov, see below) `Hunter.GemInfo("Ruby")` (LIB_GAMES Hunter card script loaded on the engine) never returned in 9.6.3's standalone and left it busy. The same shape of code in a small test (return from inside `repeat for each line ... in f()`) returned at once, so the cause is still unknown.
- OPEN: `asin(...)` differs from Python's in the 6th decimal for some inputs (Antack.Euler(0.5, 0.3): LiveCode 0.475758, ours 0.475759). Compare `atan2(x, sqrt(1-x*x))` once LiveCode answers again.

## (WRONG, see 22 Nov correction) A second game library in one standalone session hangs it (21 Nov 2026)
Loading engine+game (stack script, `start using stack`) works in a fresh standalone (~10 s). Loading a second one in the same
session never returns (measured with Antack, Face, Hunter; the cases themselves pass in a fresh session). Use a fresh
standalone per library group.

## 22 Nov 2026 (golden run, 319 cases)
- A variable keeps the full number: `put (x+680)/170 into fx` does not round to numberFormat (6 decimals) until it is
  shown as text. Rounding at every `put` gave wrong last digits (HeightAt, Antack.Euler).
- `eval` of an expression that returns an array (a mesh) gives empty, not an error.
- CORRECTION (22 Nov): a second engine+game library in one copy does NOT hang. Antack, Face, Antack again in one copy all
  answered; the first load took 10 s, later ones 32 s. The 21 Nov hangs were most likely the launcher bug (LIB_MCP `Client.standalone`
  held pipes), not LiveCode. `golden.py` still uses a fresh copy per group (faster and safe).
- `Hunter.GemInfo` was never a runaway loop: same cause. Its cases are now in lib_cases.txt (322 of 322 match).
- Script locals (`local sH`) are shared by all handlers, arrays included: `put x into sH[i]` writes the script local.

## Objects and messages (measured 24 Nov, standalone; Phase 2)
- `set the width of graphic G to 50` keeps the centre: rect 10,10,110,60 -> 35,10,85,60. Height 50 -> 21 with
  centre y 85 (after loc 100,100: rect 75,75,125,125) -> 75,89,125,110: new top = centre - trunc(h/2)... measured
  89 = trunc(100 - 10.5); bottom = top + 21.
- `the loc` = trunc((left+right)/2), trunc((top+bottom)/2): rect 75,89,125,110 -> 100,99.
- `set the left` moves, keeps the width: 35,10,85,60 -> 0,10,50,60. `set the loc` centres the rect.
- `the long id of button "B"` = `button id 1004 of card id 1002 of stack "xtM1"`; `the name` = `button "B"`;
  an unnamed card's name = `card id 1002`. `the short name of me` = B.
- `pass mouseUp` in a button goes on to the card, then the stack; `the target` stays the button.
- `send "hello 7" to button "B"`: the words after the message name are its parameters. `dispatch "hello" to
  button "B" with 8` the same. Both follow the message path (and pass).
- `the "abc"` is just abc (the card reader stack uses `put the "Entrance, Obstacle..." into tItems`).
- A custom property reads as `the uFoo of stack "x"` and `the uFoo of this stack`.
- NOT measured: preOpenStack/openCard order (an invisible stack opened from a library sent none of them).
