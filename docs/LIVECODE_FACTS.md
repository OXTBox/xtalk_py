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
- `switch` compares as text, ignoring case unless `the caseSensitive` is true (re-measured 25 Nov; an older
  line here said case-sensitive, which was wrong and broke LightCycles3): `switch "right"` takes `case "Right"`;
  `switch "1.0"` does not take `case 1` (no number compare); `switch " b "` does not take `case "b"` (no trim).
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

## 25 Nov 2026 (nine-ball stack; standalone, `lcmcp run` and `lcmcp compile`)
- **Trailing delimiter:** one delimiter at the end starts no new item or line. `the number of items of "a,b,"` = 2,
  of `","` = 1, of `",,"` = 2, of `"a,,"` = 2; lines of `"a" & cr & "b" & cr` = 2, of `cr` = 1.
  `item 3 of "a,b,"` is empty, `item -1 of "a,b,"` = b. Writing past the end counts the trailing comma as there:
  put X into item 3 / item 4 / item -1 of `a,b,` gives `a,b,X` / `a,b,,X` / `a,X,`; `delete item 2` gives `a,`;
  `put X after item 2` gives `a,bX,`. `repeat for each item` in `",,"` runs 2 times.
  (Our interpreter said 3: the nine-ball pocket list `pocket1,...,pocket6,` then had a 7th, empty pocket.)
- **Booleans:** only "true" (any case, no spaces) is true. Empty, "x", " true", "true ", "1", "yes" are false, with
  NO error, in `if`, `not`, `and`, `or` (`if s then` with s empty takes the else). Our "bad boolean" error was wrong.
- **One-line else:** `else put 2 into x` ends a multi-line `if` by itself. An `end if` after it is a compile error
  ("end doesn't match handler name") unless it closes an outer `if`.
- **Names may contain an apostrophe:** `put 3 into xx'` works (Scott Rossi's `resetVel xx,yy,xx',yy'`).
- **Lines outside handlers are ignored**, even nonsense: the script compiles, the result of `set the script` is empty,
  and the handlers before and after still run.
- `the number of buttons` with no "of" counts on the current card (0 there); `the number of cards` = 1.
- The standalone has no message box: `put "k" into msg box` fails at run time there, but compiles in scripts.
- From the Dictionary (mouse events cannot be measured without a hand on the mouse):
  `grab` returns at once, the control follows the mouse until release, then gets mouseUp; nothing happens if the
  mouse is not inside it. mouseMove goes to the control under the mouse (or the card); while the button is held, to
  the object clicked. mouseEnter/mouseLeave wait while the button is held and come after the release.
  `within(graphic, point)`: the inside counts only if the graphic is filled.
- **A card's rect is 0,0,<stack width>,<stack height>**; its loc is the middle (stack 400x300: `0,0,400,300`, loc
  `200,150`). We had 0,0,0,0, so nine-ball's scratched cue ball went back to -205,0, off the window.
- **"of" may be left out** (TKInter-izer compiles with these): `item 2 "p,q,r"` = q, `word 2 "aa bb cc"` = bb,
  `item 1 the loc of this stack`; `set the width button "x" to 50` and `the width button "x"` both work.
- `the the keys of A` = the keys (a doubled "the" is one). `return 5 into q` returns 5; the `into q` does nothing.
- `mouseLoc()` = the mouseLoc; `the mouse` and `mouse(1)` = up/down (a "the" function can be called with brackets).
- From the Dictionary: `popup button [at point]` pauses the handler while the menu shows; a pick sends menuPick to
  the button. NOT measured (needs a hand on the mouse): whether an option menu also gets mouseUp after a pick
  (we send none), and menuPick's order against the rest of the handler (we send it before the handler goes on).
- **A field used as a value is its text:** `field "F"`, `word 2 of field "F"`, `line 1 to -1 of field "F"` give
  `one two` / `two` / `one two` (measured 25 Nov). We gave the field's name, so TKInter-izer's Run wrote the words
  `field "Program"` into its .py file. Commands (hide, send to, popup...) still get the object itself.
- `shell()` (not LiveCode's general version, by the owner's word 25 Nov): only starts a .py file from the stack's
  files folder, with a Python that has Tkinter (Windows Python 3.14 + Tk 8.6 today; WSL's has no Tkinter).
  Windows Python started from WSL waits forever on its input unless the input is closed (stdin = nothing).
- List fields (listBehavior): the owner's TKInter-izer reads `the selectedLine of me` in mouseDown, so the click
  hilites the line BEFORE mouseDown runs. `the selectedLine` = `line N of field K`. A double click: the second press
  and release send mouseDoubleDown / mouseDoubleUp instead of mouseDown / mouseUp (common LiveCode knowledge, NOT
  measured: needs a hand on the mouse). Line height for clicks = the window's drawing rule (size*4/3+2), not
  measured against LiveCode either.
- `answer` / `ask` (Dictionary; dialogs cannot be measured in the windowless standalone): answer puts the clicked
  button into `it` (no buttons: OK; the last one named is the default, Return picks it); ask puts the typed text into
  `it`, Cancel gives `it` empty and the result "cancel". `answer file "p"` is a file dialog (was read as URL file).
- **create** (measured 25 Nov, a 400x300 stack): `create graphic` -> it = `graphic id 1003 of card id 1002 of stack
  "zzCreate"` (the long id), no name (`the name` = `graphic id 1003`), rect `136,134,264,166` (128x32 centred on the
  card), style rectangle, on top, visible. Buttons and fields the same rect. Ids go on from the stack's highest.
  The templateGraphic: its colour is copied; its rect starts at -1,-1,127,31 (width 40 gave `43,-1,83,31`), and a
  changed template rect is used as it is. `reset the templateGraphic` clears it. `create card "C2"`: it = the long
  id, and C2 becomes this card. `delete graphic "Red"`: gone, the result empty.
- **customPropertySet** (measured): with a set active, `the customKeys` lists that set's keys and plain reads/writes
  use it (`the plain of stack` reads empty under set "Vec"); `the Vec["a1"]` reads the set directly.
  **`the tProp of x` with tProp a variable reads the property named by its value** (tProp = "a1" gave a1's value).
  We do this only when the name is not one of LiveCode's own properties (width, loc...).
- `set the style of it to "Line"` is stored as `line`; "RadioButton" as `radiobutton` (measured).
- Typing (Dictionary; keys cannot be measured in the windowless standalone): an unlocked field (lockText false,
  not a list) gets the focus on a click: openField; leaving it: closeField if its text changed, else exitField.
  Keys go to the focused field (keyDown, backspaceKey, deleteKey, returnInField, enterInField, arrowKey, tabKey) and
  along the path; when no handler takes one (or it is passed past the last handler) the field types / deletes /
  moves the caret. NOT done: arrow keys with no field focused would change cards in LiveCode (we only send arrowKey).

## 26 Nov 2026 (rounding off Phase 2; standalone, `lcmcp run --server`)
- **Open messages** (a saved stack opened with `go stack`, handlers in the stack and both card scripts): order
  preOpenStack, preOpenCard, openStack, openCard, and **all four go to the current card** (`the target` = the card;
  the card's handler runs first, then the stack's). We used to send the stack messages to the stack, so a card's
  `on openStack` never ran. No preOpenBackground/openBackground/resumeStack were sent (no groups on that card).
  `go next card`: closeCard (old card), preOpenCard, openCard (new card). **`go` to the card already shown sends
  nothing.** `close stack`: closeCard, then closeStack, both to the card. `the lockMessages` was false.
  **`go stack "Sub"` (a substack) the first time: the same four open messages to its card**; going back to the
  mainstack, or to the substack again, sends nothing (both stay open).
- **`angle` of a regular graphic** (`the effective points`): vertex k sits at angle + k*360/polySides degrees,
  turning clockwise on screen (y down), angle 0 = the first vertex straight right of the centre. Centre =
  (left+right) div 2, (top+bottom) div 2; x radius = width div 2 - 1, y radius = height div 2 - 1 (60x40 gave
  29 and 19: an ellipse, not a circle); each offset from the centre rounded half toward the centre
  (110.5 -> 111, 129.5 -> 129); the first point is repeated at the end. Rect 100,100,
  140,140, 3 sides: `139,120 111,136 111,104 139,120`; angle 30: `136,129 104,129 120,101 136,129`.
  Setting the angle does not change the rect. 390 reads back 30, -30 reads 330. A rectangle or oval keeps its
  angle (reads back 45), its rect and style unchanged (that it is not drawn turned: from memory, not checked).
- **htmlText** (field "F"): a plain field gives `<p>line</p>` per line, joined by return. `&` `<` `>` as `&amp;`
  `&lt;` `&gt;`, tab as `&#9;`, a quote stays `"`, é `&eacute;`, € `&euro;`, ” `&rdquo;`, あ `&#12354;`.
  Styles of a run nest as `<i><b><strike><u><font face=".." size=".." color="#RRGGBB" bgcolor="#RRGGBB">`
  (outer to inner, attributes in that order); the style tags stay open across runs whose font tags differ; runs
  of the same style merge (`<b>a</b><b>b</b>` -> `<b>ab</b>`). Setting it: text outside `<p>` is one paragraph,
  returns between `</p>` and `<p>` are ignored, `<p></p>` = an empty line, `<br>` = a new line, `<span>` is
  ignored, `<font color="red">` reads back `#FF0000`, `&#65;` = A, `<sub>`/`<sup>` come back with
  `shift="4"`/`shift="-4"`, `<img src>` is a space char. The field's own textStyle (`set the textStyle of field`)
  is NOT in its htmlText.
- **Chunk styles:** `set the textStyle of word 2 of field "F" to "bold"`; `the textStyle of line 1` = `mixed` when
  its characters differ; a chunk with no style of its own reads empty (`the textSize of line 1`, `the textFont of
  word 2`; `the effective textFont` gives the field's). `set the textColor of word 1 to "blue"` reads back `0,0,255`.
- **Putting text into a styled field:** `put x into field` clears all styles. A chunk put (`into char 1`, `after
  word 1`, `before word 2`) and `put after/before field` keep the other styles; the new text takes the style of the
  character just before it, or of the first character when it goes at the very start (`put "y" before` a field
  starting bold: y is bold; `put "X" into word 2` after a plain space: X is plain, though word 2 was bold).
- **set the layer** (graphics A, B, C on a card, layers read back as A B C): `to top` 312, then `to 1` 123,
  C `to bottom` 231, C `to 2` 132, A `to 99` 321 (past the top = top; the others close up). Nine-ball's Help menu
  uses `set the layer of field "instructions" to top`; we ignored it, so the balls drew over the text.
- **A stack is found by its name, not its title**: title "Zz T" on stack "zzT": `exists(stack "Zz T")` false,
  `exists(stack "zzT")` true. So nine-ball's Preferences scripts (`card 1 of stack "nine ball"`; the stack is named
  nineball, titled "Nine Ball") stop with an error in LiveCode too.
- A new field: `dontWrap` false (it wraps). `the navigationArrows` = true.
- **clipboardData:** `set the clipboardData["text"] to "hi there"` reads back; `the clipboard` = `text`; keys
  text, unicode, styles, rtf, html. `set the clipboardData to empty`: `the clipboard` = `empty`.
- NOT measured and NOT yet checked in the Dictionary (OXT-Beyond was closed 26 Nov): with navigationArrows true
  and no field focused, an arrowKey nobody takes goes to the previous / next card (left/right) and, as we do it,
  first / last card (up/down; this may instead be back/forth through recent cards). Also from memory only:
  angle turns only regular polygons and images (not rectangles/ovals), and commandKeyDown goes first for
  Control + a key (Ctrl+C/X/V/A copy, cut, paste, select all when no handler takes it).

## Phase 2 thorough, harvests to 100% (standalone, `lcmcp run --server`)
- **A script-level `global` line reaches only the handlers BELOW it.** A handler above it reads the name as an
  unset variable (its own name: `gSgT`). Our interpreter had ignored script-level globals altogether; that was the
  900 "bad operand" errors in the survey (tests/lib_sglobals.txt).
- **A number keeps its full value** through array elements, parameters, return values, `the result` and copies
  of arrays, not only plain variables: `put sin(pi) into a[1]`, then `1/a[1]` = 8165619676597685; `a[1] = 0` is
  true; only text made from it shows 0 (tests/lib_fullnum.txt).
- `this wd` = `this window` = this stack (same height). `delete local sA` / `delete global gZ` empty the variable
  (not an array, 0 elements). `the graphic ID x`: a `the` before an object reference is allowed.
- **the pendingMessages**: one line each, soonest first: `id,due time in long seconds,message name,long id of
  target` (`107,1795638528.773,zzTick,stack "xtPM"`; parameters left out; a button shows
  `button id 1003 of card id 1002 of stack "xtPM"`). `the result` after `send ... in` = that id; `cancel id`
  removes it; `cancel` of an unknown id does nothing (the result unchanged).
- **set the points** to `"10,20,30,40,50,60"` (one line): pairs, read back one point a line. `"1,2,3"`: `1,2` and an
  empty line (the odd number left over makes a break). `"1,2" & cr & "3,4,5,6"`: three points.
- **angle of a rectangle / oval graphic**: stored and read back (30), but the rect and the effective points do
  not change (the corners are not turned). Our runtime already did this.
- **angle of an image** turns it COUNTERclockwise about its centre (a pixel at top-right of a 4x2 image is at
  top-left after 90). The rect becomes the box around the turned picture: width ceil(w|cos a| + h|sin a|),
  height ceil(w|sin a| + h|cos a|), left/top = floor(centre - size/2): 60x40 at 100,100: 45 -> 94,84,165,155;
  30 -> 94,87,166,152; 90 -> 109,90,150,150 (41 wide: cos 90 is not exactly 0). Angle 0 gives the first rect
  back. formattedWidth/Height stay 60x40. An image with no pixels behaves differently (not used).
- **Styled field, delete and sort** (htmlText `<p><b>zz</b> bb</p><p><i>cc</i> yy</p><p>aa <font color=red>rr</font></p>`):
  `delete word 1 of line 1` -> `<p>bb</p>` (the rest keeps its styles); `delete line 2` -> lines 1 and 3 with their
  styles; `sort lines of field` and `... descending` -> each line moves with its own styles.
- **Background messages** (group with backgroundBehavior, card 1 and card 2 share it, card 3 has none):
  1->2 `closeCard,preOpenCard,openCard` (no background messages); 2->3 `closeCard,closeBackground,preOpenCard,openCard`;
  3->1 `closeCard,preOpenBackground,preOpenCard,openBackground,openCard`. The group's handler ran with `me` = the
  group (a card's path: card, its background groups, stack). Not measured: several background groups at once,
  and whether a card's own handler sees them first (we send them to the card).
- **A turned image moved** (`set the loc` at angle 30): the picture goes along (angle 0 then gives a 60x40 rect around
  the new place: 270,281,330,321). `set the width` while turned is ignored (rect and formattedWidth unchanged).
- **set the loc with an odd size**: left = x - (width div 2): 71 wide at 300 -> 265,265,336,336; 72x65 at 300,300 ->
  264,268,336,333 (graphics and images alike). `the loc` = trunc of the middle.
- `choose browse tool` / `choose "pointer tool"`: written from memory (not measured): we note the tool and
  `the tool` reads it back; nothing else changes.
- **A stack with a background on its card** (all to the card; `the target` = the card): close/delete
  `closeCard,closeBackground,closeStack`; open (`go stack`) `preOpenStack,preOpenBackground,preOpenCard,openStack,
  openBackground,openCard`.
- `the keysDown`: the codes of the keys held now, comma separated (letters lower-case ASCII, arrows 65361-65364,
  shift 65505...). From memory, not measured (needs a real keyboard).
- A filled (opaque) polygon graphic is drawn filled; graphics a script creates with no colour take the stack's
  colours (Raycasting_101: black floor/roof, grey walls). The fill rule we use is even-odd (not measured).
- **Line height** (Segoe UI, margins 8, 4 lines): fixedLineHeight true: the effective textHeight = floor(textSize * 4/3)
  (10->13, 12->16, 14->18, 18->24, 24->32) and formattedHeight = lines x textHeight + 8; a line with bigger text
  (size 24 in a size-12 field) stays 16. fixedLineHeight false: each line its font's own height: 10->15, 12->18,
  14->18, 18->26, 24->36; a size-24 line in a size-12 field makes that line 36 (we do not do this yet: one height a
  field).
- **formattedHeight of a field** (measured 26 Nov, Segoe UI, sizes 11-14, 1-4 lines, margins 0 / 4 / 12 / "4,6,8,10"):
  rows x line height - 8 + top margin + bottom margin (margins: one number for all four, or left,top,right,bottom).
  Free line heights also measured: 11->15, 13->18. A size-11 line in a size-13 fixed field stays 17 high.
  formattedWidth: the widest row + left + right margins (approximate; can exceed the field's width).
- **roundRadius** (measured 26 Nov, pixels of an exported snapshot, antialiased false): it is the corner's DIAMETER;
  each corner is an ellipse of min(r/2, width/2) x min(r/2, height/2). Default 15. Priority Tube sets it to the
  bubble's height for a pill.
- **Links** (measured 26 Nov): htmlText `<a href="x">` = textStyle link + linkText x; `<a>` = link, no linkText;
  linkText alone (no link style) reads back as `<a name="x">`; the a tag is written outside font:
  `<a href="remove"><font color="#FF8C8C">Remove it</font></a>`. A link draws in its own text colour if it has one,
  else the effective linkColor (0,0,239 in a new stack), underlined (underlineLinks true). A click on a link in a
  LOCKED field: mouseDown, then linkClicked (the linkText, else the link's own words) IN PLACE of mouseUp; plain
  text: mouseDown, mouseUp; an unlocked field: neither (it takes the focus).
- **Text widths** (measured 26 Nov, Segoe UI, dontWrap, "The quick brown fox jumps over the lazy dog", sizes
  10-24): formattedWidth = the font's exact (unrounded) advances at textSize x 4/3 pixels: bold within 1 px
  (213 at 10, 276 at 13, 509 at 24); plain a steady 1.033 x wider (205, 266, 491). Python's window is narrower
  (raylib truncates each advance to whole pixels at the loaded size: plain 13 = 246 instead of 266), so its text
  wraps later than LiveCode's (a Priority Tube bubble: 3 rows where LiveCode makes 4). Not fixed yet.
  LiveCode's own rows for that bubble: "Matrix Lock: camera control, / shifting and turning blocks, jump, /
  climb (bottom of the list, your / word)" at width 220, margins 4, size 13 bold; border on or off the same.
- A handler parameter named like a script-level global is the parameter (the global is not read or changed:
  `ARG-`, global still `G`). `local g` in a handler below `global g` does not compile.
- From memory (not measured): `rawKeyDown` gets the key code before keyDown (Esc 65307, backtick 96); `set the cursor
  to none` hides the pointer; `set the screenMouseLoc` moves the real mouse; `globalLoc` / `localLoc` add / take
  the window's place. Our window: rawKeyDown is sent but does not yet stop keyDown when not passed; a hidden
  (test) window never moves the mouse.
  27 Nov night (x1-11): a taken (not passed) rawKeyDown now stops keyDown for letters/digits/space/` in the View
  and in `type_char`. OPEN, to measure in LiveCode: does a taken rawKeyDown 65288/65293/65289 also stop
  backspaceKey / returnInField / tabKey? The View still sends them (it only drops characters); `type_char` (hidden
  tests) does not. Whichever LiveCode does, make both agree.
- nine-ball's Instructions field (the real stack, a scratch copy): fixedLineHeight true, effective textSize 12,
  textHeight 16, so its lines are 16 apart (we drew 18 before; the text runs are size 11).
- **Dictionary (OXT-Beyond, 25 Nov)** settles the old "NOT checked" note: with navigationArrows true and no text
  selection, Left/Right = previous/next card, Up/Down = back/forward through the recent cards (not first/last; fixed).
  commandKeyDown: sent with the key's character to the focused control, else the card; on Windows/Unix whenever
  Control is held; not sent with Return/Tab/Backspace/Delete/Enter/arrows/function keys (as we did).
- **me as a value in a field / button script is its text**: `return line 2 of me` -> the field's line 2;
  `put "XX" into line 1 of me` changes the field; in a button script `me` is the button's text (empty).
  `the short name of me`, `send ... to me`, `hide me`, `within(me, ...)` still mean the object.
- files() / folders(): the names in the defaultFolder; folders() starts with `..` (Simple_image_viewer filters it).

## Comparing numbers (measured 25 Nov 2026, standalone 9.6.3)
- `=` `<` `>` compare numbers at their FULL value, not the numberFormat text: `(1/3) = 0.333333` is false,
  `(1/3) > 0.333333` true; a variable holding 1/3 compares the same way.
- With a tolerance of about 10 steps of a double, relative to the bigger number: `0.1+0.2 = 0.3` true,
  `1+2e-15 = 1` true, `1+5e-15 = 1` false, `1e6+1e-9 = 1e6` true, `1e6+1e-8 = 1e6` false, `1e20+1e5 = 1e20` true;
  near zero about 2.2e-16: `1e-16 = 0` true, `1e-14 = 0` false. Equal within it is not greater: `1+1e-15 > 1` false.
  Ours: values.num_cmp (2.22e-15 relative, 2.22e-16 absolute) fits every point measured.
- An unset variable is its own name, and a copy of it is plain text: `put foo into y; put "bar" after y` -> foobar;
  `add 1 to y` then fails. A `local y` line AFTER y was used is a compile error in LiveCode (we accept it: open).
- A `constant kN = 5` line inside a handler works there: `put kN + 1` -> 6.
- (25 Nov, Phase 3) A comment may follow the `\` that continues a line: `put 1 & \   -- c`, `\ # c`, `\ // c` and
  `\ /* c */` all compile and give 12 / 34 / 56 / 78 (the xt3d view demo has `& \   -- lint-ok: ...`).
- (25 Nov, Phase 3, the real xt3d bridge: tests/xt3d_golden.json) An LCB handler's number parameter cuts a fraction
  toward zero (2.7 -> 2, -2.7 -> -2); an empty argument is an error (899); a negative number for an unsigned one is
  an error (863); a CInt result is signed (`xt3d_ColorToInt(255,0,0,255)` = -16776961). As a command, its value
  goes into the result.
- (25 Nov) The itemDelimiter, lineDelimiter and numberFormat belong to the handler: each handler starts with
  comma / return / 0.######, and a change never reaches its caller or the handlers it calls (tA sets "/", calls
  tB: tB sees ","; tB sets ":", tA still has "/"; a command tF setting "/" leaves its caller at ","). Found
  because the xt3d testbench's xbFindAbove leaves the itemDel at "/".
- (25 Nov) Array keys ignore case while the caseSensitive is false: `a["x"]` finds what was put into `a["X"]`;
  `put 9 into a["name"]` after `a["Name"]` changes that element and the keys still say `Name`; with the
  caseSensitive true, `a["x"]` is empty and `b["k"]`, `b["K"]` are two elements. `split` arrays too.
  The caseSensitive belongs to the handler like the itemDel (a called function sees false).
  Ours: values.XtArray. (The engine's SetObjectPosition stores ["X"], GetObjectPosition reads ["x"].)
- (25 Nov) `the topStack` is `stack "Name"`; in the standalone `the defaultStack` also gave `stack "LIB_MCP"`.
  (25 Nov eve, measured again) `the short name of the defaultStack` = LIB_MCP; `the short name of "LIB_MCP"` (a bare
  name) is an ERROR; `there is a stack t` with t = `stack "LIB_MCP"` is true. Ours now gives `stack "Name"` and
  `stack t` accepts `stack "X"` (GameNotes' `this card of stack (the short name of the defaultStack)` needed it).
- (25 Nov eve) `the system date` = 11/25/2026 (Windows' short date, the year in full) while `the date` = 11/25/26;
  long / abbr system date and system time / long system time = the plain forms. (GameNotes stamps notes with it.)
  Ours: the system date done; `the long system date` / `the abbr system date` do not PARSE yet (open, rare).
- (25 Nov eve, the Dictionary, not measured) front scripts get engine messages before the object's path; back scripts
  after the libraries. Ours: `insert script of X into front/back`, `remove script`, the frontScripts/backScripts.
- (25 Nov) the date forms (US English Windows): 11/25/26 | Wednesday, November 25, 2026 | Wed, Nov 25, 2026 |
  5:35 PM | 5:35:01 PM | internet date Wed, 25 Nov 2026 17:35:01 -0800. `convert`: dateItems =
  y,m,d,h,min,s,weekday (1 = Sunday), overflow normalised (2026,11,40,25,0,0 -> 2026,12,11,1,0,0,6); a date alone
  is midnight, a time alone today; bad input leaves the variable and the result is "invalid date";
  `to short date and long time` joins with a space. `binfile:` is one char a byte; textDecode(...,"UTF-8").
- (25 Nov) `delete item 1 of "3,"` -> empty (the delimiter after the item goes with it, a trailing one too);
  `delete item 1 of ","` -> empty; `delete item 2 of "a,b"` -> a. Ours left "," (the testbench's xbGameFill
  queue then never emptied: uDead hung in hiding mode 1).
- (25 Nov night) `set the randomSeed to 12345.7` -> `the randomSeed` = 12346 (rounded), and it reads back the
  same after random() calls; the same seed gives the same random() numbers (12345: 226, 920). Ours did NOTHING
  with the randomSeed until 25 Nov night; now it rounds, reads back and seeds Python's random (same seed = same
  numbers every run, but not LiveCode's numbers: a run in Python and one in LiveCode never match draw for draw).

## split / combine and `is among the keys` (measured 26 Nov 2026, LiveCode 9.6.3 standalone)
- `split t by comma`: keys 1..n; ONE delimiter at the very end makes no empty last element ("a,b,," -> 3 elements,
  the 3rd empty); "a,,b" -> 3. Empty text stays empty and is not an array. One piece ("x") -> an array of 1.
- `split t by comma and "="`: key = the text before the first "=", value = the rest ("m=a=b" -> m: "a=b"); no "="
  -> the key with an empty value; a key seen again takes the later value. ("A=1,a=2" gives 2 elements in LiveCode,
  keys A and a, t["a"] = 1: not copied, our arrays fold case.)
- `with` and `using` = `by`. `by row` = by return; `by column` = columns of tab-separated rows (t[2] = "y" & cr & "w").
  `by comma as set`: each piece a key, the value true.
- `combine a with comma`: elements in the KEYS' TEXT ORDER, any case: keys 1,2,10 -> 1,10,2; Alpha, beta, zeta.
  `combine a by cr and "="`: key=value lines. Not an array -> empty. An element that is an array -> empty.
- `x is among the keys of a` is true for a key (the keys are lines). `is among` with no chunk type (`is among "a,b"`,
  `is among (the keys of a)`) does not compile in LiveCode.
- An array used as text is EMPTY, never an error: `a & "x"` = "x", `the length of a` = 0. But in a comparison an array
  with elements equals no text: `a is empty` false, `a = empty` false, `a is "x"` false, `a <> empty` true; an array
  whose elements were all deleted is empty (measured 26 Nov; before, the runtime stopped with "can't treat an array
  as text": 5 games hit it, NineBall at `if sDot is empty`).
- bitAnd / bitXor / bitOr / bitNot (measured 26 Nov): bitAnd binds tighter than bitXor, bitXor than bitOr; all looser
  than = (`6 bitAnd 2 = 2` is an error: 2 = 2 first) and tighter than `and`. Operands: rounded half away from zero
  (2.5 -> 3, 5.7 -> 6), below 0 -> 0, then the low 32 bits (4294967297 -> 1); empty -> 0. bitNot: 32 bits
  (bitNot 0 = 4294967295). Before: not in the parser (lib_cellmap's 5 handlers, Amazing_Couple's maze).
- `send X to card 1` when nothing handles X is an ERROR in LiveCode too (573 can't find handler; measured 26 Nov):
  the Vibecode3D Launcher's `send setStackScript to card 1` in preOpenStack fails the same way there.
- `the stacksInUse` is empty (not an error) with no libraries in use. `$#` = how many command-line arguments, `$1`... each
  one (empty when missing), `$NAME` an environment variable.


## Behaviors (measured 2026-11-26, LiveCode 9.6.3 standalone, `lcmcp --standalone run --server`)
Test stack "BhvTest" made and deleted in the run; scripts set with `set the script`, calls by `dispatch` / `send`.

| What | LiveCode 9.6.3 |
|---|---|
| `dispatch "foo" to btn T` (T, its behavior B, card all have foo, each passes) | T, then B (me = T, the target = T), then card, then stack |
| T has no foo, B has it | B runs (me = T2 for button T2 using the same B) |
| behavior of a behavior (T -> B -> BB) | T, B, BB, card, stack; me = T in all three |
| group G with behavior GB, button Inner in G | Inner (none), G, GB (me = G, target = Inner), card, stack |
| a handler call from B's script (`helper`; T and B both have helper) | T's helper runs: a call starts at me's own script, then me's behavior, then the path |
| B calls `onlyT` (T and card have it) | T's; B calls `cardH` (only the card) -> card's |
| script locals in B | one copy per object: T 1,2,3; T2 1; B itself (dispatched to B) its own 1 |
| `set the behavior` of T to the same B again | locals kept (2 -> 3) |
| `set the script of B` again | every user's locals start empty (-> 1) |
| T switched to B2, back to B, or to empty and back | locals start empty each time (1) |
| `value("bump()", btn T)` | runs B's bump with T's locals |
| `the behavior of btn T` (B on card 1002) | `button id 1003 of stack "BhvTest"` (no card, no group even for a grouped button) |
| behavior a script-only stack loaded by path | `set the behavior of U to the long id of stack tPath`; the behavior of U = `stack "BhvSO"` (its name); `the long id of stack tPath` = `stack "<the path>"` |
| two buttons on one script-only stack | own locals each (U 1,2; U2 1); path U, SO, card, stack |
| no behavior | `the behavior` = empty; set to empty removes it (path goes straight to the card) |
| set to `btn "B"` (the button's contents, empty) | behavior empty, no error |
| set to the text `button "B"` | resolved: `button id 1003 of stack "BhvTest"` |
| set to a missing object / a field / itself (loop) | error (`parentScript: loop in hierarchy` for the loop) |
| card behavior | settable, reads back the same `button id N of stack "S"` form |
| `dispatch` result in `it` | handled / unhandled (no handler anywhere, behaviors included) / passed (the last one passed) |
| send a function name as a command | error (can't find handler) |

Harvests: LIB_XTJSON's harvester writes `node["behavior"]` = `the behavior of X` (the form above). None of the
harvests in ~/projects/XTJSON has one (26 Nov): their "behavior" keys are listBehavior / backgroundBehavior /
radioBehavior / sharedBehavior / tabGroupBehavior flags, not script behaviors.

## `it` after dispatch; the long id of a stack with a file (27 Nov, x1-05)

Measured with `lcmcp --standalone run --server` (LiveCode 9.6.3 on Windows); test stacks made and deleted in the run.
Button T: `foo` (handles), `bar` (passes), `baz` (passes; the card has baz), `ret` (return 42), function `fn` (return 7),
`setit` (put 99 into it).

| What | `it` / the result |
|---|---|
| `dispatch "foo"` | handled / empty |
| `dispatch "bar"` (T passes, no one after) | passed |
| `dispatch "baz"` (T passes, the card handles) | handled |
| `dispatch "nope"` (no handler anywhere) | unhandled |
| `dispatch "ret"` | handled / 42 |
| `dispatch function "fn"` | handled / 7 |
| `dispatch "fn"` (a function dispatched as a command) | unhandled (not built here: we run it, handled) |
| `dispatch "setit"` (the handler puts 99 into its own it) | handled (the caller's it) |
| `send "foo"` | it unchanged |
| `dispatch "sendp"` (sendp does `send "bar" to me`; bar passes off the end) | handled |
| a handler calling `bar` by name, bar passing off the end | error: can't find handler |
| `dispatch "mouseUp"` to a button with no mouseUp anywhere | unhandled |

| What | LiveCode |
|---|---|
| `the long id of stack tPath` (a script-only stack file) | `stack "C:/Users/.../Temp/lidSO.livecodescript"` (the filename) |
| `the long id of stack "LidSO"` (by name), `the long name` | the same path form |
| `the name` / `the short name` / `the abbreviated id` | `stack "LidSO"` / `LidSO` / `stack id 1001` |
| `the long id of card 1` of that stack | `card id 0 of stack "<path>"` (card id 0: here it stays 1002) |
| a new stack, not saved | `stack "LidNorm"` |
| the same stack after `set the filename` + `save` | `stack "C:/.../lidN.livecode"`; a button on it: `button id 1003 of card id 1002 of stack "<path>"` |

Built: script-only stacks loaded from a file (host.stack_ref). Not built: the same for the harvest's own stack when it has
a file (real_app gives it one: every long id in Project Map would change); substacks of a stack with a file not measured.

## A library that is not in use; specialFolderPath("support"); caseSensitive and text operators (27 Nov, g1-06)

Measured with `lcmcp --standalone` (LiveCode 9.6.3 on Windows):

| What | LiveCode |
|---|---|
| `put Nope.Driver() into x` (no such handler anywhere, no library in use) | runtime error 219 (`219,311,7,Nope.Driver`): can't find handler; a `try` catches it and the error names the function |
| `value("Nope.Driver()")` | the same error 219 |
| the same function once its stack is `start using`-ed | runs (42) |
| `the Zq.Fn` for a custom function Zq.Fn (in a script) | compile error: `the X` is only for properties and built-in functions, never a custom function |
| `value("the Zq.Fn")` | error 618 |
| `specialFolderPath("support")` | `C:/Users/<name>/AppData/Roaming` (documents, home, desktop: `C:/Users/<name>/...`) |
| caseSensitive true: `"x" is in "X"`, `"AbC" begins with "a"`, `ends with "c"`, `"a" = "A"`, `"a" is among the items of "A,B"`, `offset("b","ABC")` | false, false, false, false, false, 0 (all case-sensitive) |

Ours since 27 Nov (g1-08): `values.fold` / `compare` and pyrt `among_items` follow the caseSensitive in all three
modes (tests/test_measured.py); a new runtime or stack starts it at false, an object's context made mid-handler keeps it.

So `unknown property "the users.driver"` in the Python play logs was only Python's wording for
`Users.Driver()` with LIB_USERS not in use: no `the` form is involved. In LiveCode the same call fails the same
way, because neither the xt3d test bench (xt3d_testBench_lib_mcp) nor LIB_DEV's game_player starts using
LIB_USERS; game_player starts LIB_DATA only for a game with an `.input.txt`, PhotonBall/VectorToss start it
themselves. lib_loading's Loading.User and GameNotes' Notes.DataRoot catch the error on purpose and fall back
($XT_USER / "OWNER"; the install's data_root.txt, `<support>/Vibecode3D/data_root.txt`, Documents/Data).
Python now says `can't find function Users.Driver` (same as LiveCode's meaning), and has the support folder.

Not fixed yet (Python, found while measuring): `is in`, `begins with`, `ends with`, `=`, `among`,
`offset` ignore caseSensitive true in the Python runtime (they always ignore case).

## Keys and focus in the play window (27 Nov, g1-02; NOT measured: the standalone server has no window or focus)

Asked of the standalone (`focus on field`, `click at`, `the focusedObject`): every answer came back empty, so
these follow the Dictionary and the owner's scripts, not a measurement. Measure them in the IDE when it is free.

| Question | What the runtime does now | Source |
|---|---|---|
| a rawKeyDown handler that does not pass | no keyDown follows (the key is not typed) | Dictionary (rawKeyDown); GameNotes relies on it ("the engine never sees this Escape") |
| order of rawKeyDown | front scripts, then the focused field or the card, its path | Dictionary |
| a click on the card or an image while a field has the focus | the field loses the focus (runtime, unchanged) | not checked |
| a card keyDown handler that never passes (Thrmnlra while playing) | a focused field gets no typing | message path: field, card, stack |

## create stack (measured 27 Nov, 9.6.3 standalone; for the Library's Play, x1-02 step 2)

`lock messages` / `create invisible stack "ProbeXY"` / `unlock messages`, then:

| asked | answer |
|---|---|
| `it` | `stack "ProbeXY"` |
| the defaultStack | unchanged (the stack that ran the create) |
| in the openStacks / the mainStacks | true / true (open at once, a main stack of its own) |
| the mainStack of it | ProbeXY |
| visible, cards, rect | false, 1, `32,32,288,288` |
| card 1's short name, the filename | `card id 1002` (no name), empty |
| set its script to text that does not compile | the result = `114,2,5` (error line), the script text is kept |
| set its script to good text | the result = empty |
| `show stack` then `go stack` | no open messages (it was already open); the defaultStack becomes it after go |
| `close stack` | closeCard, closeStack (to the card); the stack is still there (destroyStack false) |

## Stack window limits and resizeStack (measured 27 Nov, 9.6.3 standalone, `create invisible stack`; x1-08)

| asked | answer |
|---|---|
| a new stack's minWidth, minHeight, maxWidth, maxHeight, resizable | 32, 32, 65535, 65535, true |
| `set the width of stack` (rect 100,100,500,500 -> width 200) | 200,100,400,500: the centre is kept, as for controls; height the same |
| set the minWidth to 300, then the width to 200 | width 200: minWidth does not hold a script's size (the window system holds the owner's drag) |
| set the width to 200, then the minWidth to 300 | width stays 200 |
| set the maxHeight to 250, then the height to 400 | 250: maxHeight does clip a script's size (maxHeight 1000, height 1200 -> 1000) |
| resizable false, then set the width | the width changes (resizable is only about the owner's drag) |
| resizeStack after `set the rect/width/height of stack` | sent at once, every time the size changes, params newW,newH,oldW,oldH (default 256x256 -> rect 100,100,500,500: `400,400,256,256`; width 200: `200,400,400,400`; height 300: `200,300,200,400`) |
| resizeStack after `set the loc of stack` | none (only the size counts) |

Not measured (no window on the server): closeStackRequest on a close-box click. Used as LiveCode documents it: to the
stack's current card; passed (or no handler) = the stack closes; not passed = it stays open (LIB_ALPHA rule 12b
handlers set destroyStack and close the mainStack themselves).

## x1-04, the xt3d bench (measured 27 Nov evening, 9.6.3 standalone, helper C)

- `filter X with regex pattern P`: P is found ANYWHERE in the line (a search, not a whole-line match) and follows
  the caseSensitive: false (the default) = `"b"` keeps `abc`, `ABD`, `xbz`, `b`; true = only `abc`. `without regex
  pattern "B"` with caseSensitive false drops all four. `filter items of X with regex pattern` works on items.
  `with wildcard pattern "?B?"` and `with pattern "*b*"` match the whole line and follow the caseSensitive too
  (true: `"*b*"` keeps `abc`, not `ABD`). Before x1-04 Python read `regex` and `pattern` as variables (empty), so
  the bench's model list (`filter tFiles with regex pattern kModelTypes`) came out empty.
- `set` (any property: `set the itemDel`, `set the defaultFolder`, `set the cXx of me`) empties the result
  (built for global and object properties; `set the script of X` gives its compile errors as the result);
  `put`, `get`, `add` keep it (a failed `open file` = "can't open that file" stays through them).
  `set the defaultFolder to "Q:/nope"` (no such folder): the result is "can't open directory".
- `the screenLoc` = 768,432 and `the screenRect` = 0,0,1536,864 on his laptop (the middle of the screenRect).
- File commands (for the bench's check log, C:/xt3d/bench_checks.txt): `write "zz" to file p` with p not open = the
  result "file is not open for write"; `close file p` not open = "file is not open"; `open file p for append` adds
  at the end; `for write` empties the file first; `open file p` (no mode = update) writes over the start ("w" then
  "U" = "U"); a folder that is not there = "can't open that file". (`read from file` is not built in Python yet.)
- An option menu button (style menu, menuMode option): a new one's label is empty; `set the text` makes the label
  line 1 and the menuHistory 1; `set the menuHistory to 2` makes the label line 2.

## Graphic effects (x1-09, 27 Nov): NOT MEASURED YET

The one probe (`create invisible stack`, a graphic with an outerGlow, `export snapshot from graphic ... with effects
to tVar as PNG`) never answered, and the standalone server (port 8767) stayed silent afterwards (lead told).
Wanted when it answers, no snapshot first: each effect's array after setting one key on a bare graphic (its
defaults: effects.DEFAULTS is LiveCode's DOCUMENTED meaning, from memory, until then); then, with the 26 Nov
roundRadius recipe (export snapshot to a file), the pixel profile of an outerGlow (size 10, spread 0 / 128) and
the direction of a dropShadow's angle. Harvested from his stacks (read, not measured): effects are arrays with keys
color, blendMode, opacity (0-255), filter (box3pass / gaussian), size, spread (0-255), range; shadows add distance,
angle, knockout; innerGlow adds source (edge); colorOverlay has color, blendMode, opacity.
