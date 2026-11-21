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
- `repeat with i = 10 down to 1 step 4` (positive step with `down to`) runs zero times. `repeat with i = 1 to 10 step 4` gives 1, 5, 9, 13 and leaves `i` at 13.
- `word`, `char` and the like, written bare, are errors (reserved words), not variables.
