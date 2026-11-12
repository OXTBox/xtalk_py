<!-- Spark first-look catalogue of lib_bit.livecodescript (model spark-x2.6-4b, 2026-11-12 05:06). DRAFT for Claude to review. -->

# LIB_BIT: 1-bit grid utilities for sprites, fonts and maps

**Form follows function:** This library provides pure, parameter-based handlers for working with 1-bit grids, which are text representations of pixel grids where filled pixels are "1" and empty pixels are "0". It has no user interface, so it is meant to be used from stack scripts, cards, or standalone scripts by passing grid data as parameters. All handlers take input grids or strings and return transformed grids or strings, touching no globals, fields, or images, so they work identically in any LiveCode context.

**Kind:** library

**Main parts:**
- Core grid creation and measurement: Bit.Blank, Bit.Width, Bit.Height, Bit.Count
- Grid transformation and conversion: Bit.Invert, Bit.FromLongString, Bit.Shift, Bit.FlipHorizontal, Bit.FlipVertical, Bit.Rotate, Bit.Pad, Bit.ToPBM, Bit.FromPBM
- Grid row and bit-pattern conversion: Bit.ToRows, Bit.FromRows

**Reusable handlers:**
- Bit.Blank: Creates a zero-filled grid of the given width and height (uses width as height if height is omitted). Needs: none (only parameters).
- Bit.Width: Returns the number of characters in the first line of the given grid. Needs: none (only the grid parameter).
- Bit.Height: Returns the number of lines in the given grid. Needs: none (only the grid parameter).
- Bit.Count: Counts the number of filled pixels in the given grid by removing empty characters and zeros, then counting remaining characters. Needs: none (only the grid parameter).
- Bit.Invert: Inverts the filled/empty state of every character in the given grid by swapping 1s and 0s. Needs: none (only the grid parameter).
- Bit.FromLongString: Splits a string into consecutive pieces of the given width, places each piece into grid rows, then trims trailing empty rows. Needs: none (only string and width parameters).
- Bit.Shift: Moves every pixel of the grid one step in the given direction, wrapping around edges; modifies the passed-in grid in place. Needs: none (grid and direction parameters).
- Bit.FlipHorizontal: Mirrors the grid left to right by reversing each line's characters. Needs: none (only the grid parameter).
- Bit.FlipVertical: Mirrors the grid top to bottom by reversing the order of the grid's lines. Needs: none (only the grid parameter).
- Bit.Rotate: Rotates a grid 90 degrees clockwise (90) or anticlockwise (-90), returns the grid unchanged for other degree values. Needs: none (grid and degrees parameters).
- Bit.Pad: Centers a grid inside a larger grid by adding blank space on the sides, returns the original grid if it is too large for the target size. Needs: none (grid, target width, and optional target height parameters).
- Bit.ToPBM: Converts a grid into a PBM text string in P1 format, including header and grid content. Needs: none (only the grid parameter).
- Bit.FromPBM: Converts a PBM P1 text string back into a grid, returns an empty string for invalid input. Needs: none (only the PBM string parameter).
- Bit.ToRows: Converts each line of the input grid into a comma-separated number string using power-of-two column values, removes the trailing comma. Needs: none (only the grid parameter).
- Bit.FromRows: Converts each number from the input rows back into grid rows using the corresponding power-of-two column values, removes the trailing return character. Needs: none (rows and optional width parameters).

**Workarounds:**
- In LiveCode 9.6.3, a stepped loop runs one extra pass past the end unless the steps land on the string exactly (1 to 8 step 4 gives 1, 5, 9); Bit.FromLongString avoids this by using a while loop with an explicit start value and increment.

**Library candidates:**
- The script already is a `LIB_` library. It is missing no additional required elements; it is a complete, self-contained grid utility library with all pure handlers included.

**Questions for Claude:** none.

**Tags:** livecode, 1-bit grids, sprite utilities, bitmap conversion, grid manipulation, pure handlers, reusable library

---

# Handler notes

## Part 1 of 4

### Declarations
- No declarations before the first handler.

### Bit.Blank (function)
- **Does:** Creates a grid of zeros with the given width and height, or uses the given width if no height is provided.
- **Takes:** pWidth (width of the grid in characters), pHeight (height of the grid in characters; defaults to pWidth if empty).
- **Gives back:** The created zero-filled grid.
- **Touches:** nothing.
- **Reusable:** yes, it is a pure data-creation handler that only takes parameters and returns a grid.

### Bit.Width (function)
- **Does:** Returns the number of characters in the first line of the given grid.
- **Takes:** pGrid (the grid to measure).
- **Gives back:** The width of the grid in characters.
- **Touches:** nothing.
- **Reusable:** yes, it is a pure data-measurement handler that only takes a grid and returns a number.

### Bit.Height (function)
- **Does:** Returns the number of lines in the given grid.
- **Takes:** pGrid (the grid to measure).
- **Gives back:** The height of the grid in lines.
- **Touches:** nothing.
- **Reusable:** yes, it is a pure data-measurement handler that only takes a grid and returns a number.

### Bit.Count (function)
- **Does:** Counts the number of filled pixels in the given grid by removing empty characters and zeros, then counting the remaining characters.
- **Takes:** pGrid (the grid to count).
- **Gives back:** The number of filled pixels in the grid.
- **Touches:** nothing.
- **Reusable:** yes, it is a pure data-counting handler that only takes a grid and returns a number.

### Bit.Invert (function)
- **Does:** Inverts the filled/empty state of every character in the given grid by swapping 1s and 0s.
- **Takes:** pGrid (the grid to invert).
- **Gives back:** The inverted grid.
- **Touches:** nothing.
- **Reusable:** yes, it is a pure data-transformation handler that only takes a grid and returns a grid.

### Bit.FromLongString (function)
- **Does:** Splits the given string into consecutive pieces of pWidth characters, placing each piece into the grid row by row, then trims the trailing empty row.
- **Takes:** pString (the string to split), pWidth (the number of characters per grid row).
- **Gives back:** The grid containing the string pieces.
- **Touches:** nothing.
- **Reusable:** yes, it is a pure data-conversion handler that only takes parameters and returns a grid.
- **Workaround:** In LiveCode 9.6.3, a stepped loop runs one extra pass past the end unless the steps land on the string exactly (1 to 8 step 4 gives 1, 5, 9); the handler avoids this by using a while loop with an explicit start value and increment.

## Part 2 of 4

### Declarations

### Bit.Shift (function)
- **Does:** Moves every pixel of the grid one step in the given direction, wrapping around the edge. For left and right it shifts characters within each line; for up and down it moves whole lines between the grid.
- **Takes:** `pGrid` (the grid to shift) and `pDirection` (the direction: "left", "right", "up", or "down").
- **Gives back:** The shifted grid.
- **Touches:** Nothing external; only the passed-in `pGrid` is modified in place.
- **Reusable:** yes, it is a pure function that takes a grid and direction and returns the shifted grid.

### Bit.FlipHorizontal (function)
- **Does:** Mirrors the grid left to right by reversing each line's characters.
- **Takes:** `pGrid` (the grid to flip).
- **Gives back:** The horizontally flipped grid.
- **Touches:** Nothing external; only the passed-in `pGrid` is modified in place.
- **Reusable:** yes, it is a pure function that takes a grid and returns the horizontally flipped grid.

### Bit.FlipVertical (function)
- **Does:** Mirrors the grid top to bottom by reversing the order of the grid's lines.
- **Takes:** `pGrid` (the grid to flip).
- **Gives back:** The vertically flipped grid.
- **Touches:** Nothing external; only the passed-in `pGrid` is modified in place.
- **Reusable:** yes, it is a pure function that takes a grid and returns the vertically flipped grid.

## Part 3 of 4

### Declarations
- No declarations before the first handler.

### Bit.Rotate (function)
- **Does:** Rotates a grid by 90 degrees clockwise or anticlockwise, or returns the grid unchanged for any other degree value.
- **Takes:** `pGrid` (the grid to rotate) and `pDegrees` (the rotation angle in degrees; 90 is clockwise, -90 is anticlockwise).
- **Gives back:** The rotated grid, or the original grid if `pDegrees` is not 90 or -90.
- **Touches:** nothing (pure data handler).
- **Reusable:** yes, it only takes and returns data with a fixed set of parameters.

### Bit.Pad (function)
- **Does:** Centers a grid inside a larger grid by adding blank space on the sides, or returns the original grid if the grid is too large for the target size.
- **Takes:** `pGrid` (the grid to center), `pWidth` (the target width), `pHeight` (the target height; defaults to `pWidth` if left empty).
- **Gives back:** The centered grid, or the original grid if `pWidth` or `pHeight` is smaller than the grid's own dimensions.
- **Touches:** nothing (pure data handler).
- **Reusable:** yes, it only takes and returns data with a fixed set of parameters.

### Bit.ToPBM (function)
- **Does:** Converts a grid into a PBM text string in format P1, including the header and the grid content.
- **Takes:** `pGrid` (the grid to convert).
- **Gives back:** The PBM text string.
- **Touches:** nothing (pure data handler).
- **Reusable:** yes, it only takes and returns data with a fixed parameter.

### Bit.FromPBM (function)
- **Does:** Converts a PBM text string back into a grid, or returns an empty string if the string is not valid PBM format P1.
- **Takes:** `pPBM` (the PBM text string to convert).
- **Gives back:** The converted grid, or an empty string for invalid input.
- **Touches:** nothing (pure data handler).
- **Reusable:** yes, it only takes and returns data with a fixed parameter.

## Part 4 of 4

### Declarations

### Bit.ToRows (function)
- **Does:** Takes each line of the input grid, converts it into a comma-separated number string where column 1 is 1, column 2 is 2, column 3 is 4, and so on, then removes the trailing comma from the result.
- **Takes:** pGrid, the grid to convert; each line of the grid is treated as one row.
- **Gives back:** the comma-separated number string representing the converted rows.
- **Touches:** nothing.
- **Reusable:** yes, it is a pure function that only takes input and returns the converted output.

### Bit.FromRows (function)
- **Does:** Takes each number from the input rows, converts it back into a grid row of pWidth characters, where each column position uses the corresponding power-of-two value, then removes the trailing return character from the result.
- **Takes:** pRows, the rows to convert; pWidth, the width of the output grid (defaults to 16 if empty).
- **Gives back:** the comma-separated grid rows as a string.
- **Touches:** nothing.
- **Reusable:** yes, it is a pure function that only takes input and returns the converted output.
