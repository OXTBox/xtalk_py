script "LIB_BIT"
-- LIB_BIT: 1-bit grids for sprites, fonts and maps.
-- A grid is text: one line per row, one character per pixel, "1" filled, "0" empty.
-- Any width and height. Every handler here is pure: it takes grids and returns grids,
-- touching no globals, fields or images, so it works the same in a stack, a
-- standalone or a server.
--
--   start using stack "<path>/LIB_BIT/livecode/lib_bit.livecodescript"
--   put Bit.Blank(16, 16) into tGrid
--   set the text of image "sprite" to Bit.ToPBM(tGrid)     -- LiveCode shows PBM text
--
-- Taken from the owner's GridDraw animator and bitmap tracer (2023-2026), made pure.
-- Handlers: Bit.Blank, Bit.Width, Bit.Height, Bit.Count, Bit.Invert, Bit.Shift,
-- Bit.FlipHorizontal, Bit.FlipVertical, Bit.Rotate, Bit.Pad, Bit.FromLongString,
-- Bit.ToPBM, Bit.FromPBM, Bit.ToRows, Bit.FromRows, Bit.Maze

-------------------------------------------------------------------- making and measuring

-- a grid of pWidth x pHeight zeros
function Bit.Blank pWidth, pHeight
   local tRow, tGrid
   if pHeight is empty then put pWidth into pHeight
   repeat pWidth times
      put "0" after tRow
   end repeat
   repeat pHeight times
      put tRow & return after tGrid
   end repeat
   delete the last char of tGrid
   return tGrid
end Bit.Blank

function Bit.Width pGrid
   return the number of chars of line 1 of pGrid
end Bit.Width

function Bit.Height pGrid
   return the number of lines of pGrid
end Bit.Height

-- number of filled pixels
function Bit.Count pGrid
   local tAll
   put pGrid into tAll
   replace return with empty in tAll
   replace "0" with empty in tAll
   return the number of chars of tAll
end Bit.Count

function Bit.Invert pGrid
   replace "1" with "x" in pGrid
   replace "0" with "1" in pGrid
   replace "x" with "0" in pGrid
   return pGrid
end Bit.Invert

-- "abcdefgh", 4  ->  "abcd" & return & "efgh"   (from GridDraw's widestringToGrid)
function Bit.FromLongString pString, pWidth
   local tGrid, tStart
   -- not "repeat with ... step": in LiveCode 9.6.3 a stepped loop runs one extra pass
   -- past the end unless the steps land on it exactly (1 to 8 step 4 gives 1, 5, 9)
   put 1 into tStart
   repeat while tStart <= the number of chars of pString
      put char tStart to tStart + pWidth - 1 of pString & return after tGrid
      add pWidth to tStart
   end repeat
   delete the last char of tGrid
   return tGrid
end Bit.FromLongString

-------------------------------------------------------------------- moving

-- move every pixel one step, wrapping around the edge: left, right, up or down
function Bit.Shift pGrid, pDirection
   local tOut, tRow
   switch pDirection
      case "left"
         repeat for each line tRow in pGrid
            put char 2 to -1 of tRow & char 1 of tRow & return after tOut
         end repeat
         break
      case "right"
         repeat for each line tRow in pGrid
            put char -1 of tRow & char 1 to -2 of tRow & return after tOut
         end repeat
         break
      case "up"
         put line 2 to -1 of pGrid & return & line 1 of pGrid & return into tOut
         break
      case "down"
         put line -1 of pGrid & return & line 1 to -2 of pGrid & return into tOut
         break
      default
         return pGrid
   end switch
   delete the last char of tOut
   return tOut
end Bit.Shift

-- mirror left <-> right
function Bit.FlipHorizontal pGrid
   local tOut, tRow, tNew, tCol
   repeat for each line tRow in pGrid
      put empty into tNew
      repeat with tCol = the number of chars of tRow down to 1
         put char tCol of tRow after tNew
      end repeat
      put tNew & return after tOut
   end repeat
   delete the last char of tOut
   return tOut
end Bit.FlipHorizontal

-- mirror top <-> bottom
function Bit.FlipVertical pGrid
   local tOut, tLineNo
   repeat with tLineNo = the number of lines of pGrid down to 1
      put line tLineNo of pGrid & return after tOut
   end repeat
   delete the last char of tOut
   return tOut
end Bit.FlipVertical

-- rotate a quarter turn: 90 = clockwise, -90 = anticlockwise. Width and height swap.
function Bit.Rotate pGrid, pDegrees
   local tOut, tNew, tW, tH, tCol, tRowNo
   put Bit.Width(pGrid) into tW
   put Bit.Height(pGrid) into tH
   if pDegrees is 90 then
      repeat with tCol = 1 to tW
         put empty into tNew
         repeat with tRowNo = tH down to 1
            put char tCol of line tRowNo of pGrid after tNew
         end repeat
         put tNew & return after tOut
      end repeat
   else if pDegrees is -90 then
      repeat with tCol = tW down to 1
         put empty into tNew
         repeat with tRowNo = 1 to tH
            put char tCol of line tRowNo of pGrid after tNew
         end repeat
         put tNew & return after tOut
      end repeat
   else
      return pGrid
   end if
   delete the last char of tOut
   return tOut
end Bit.Rotate

-- centre a grid inside a bigger one (an 8x8 Aquarius character in a 16x16 cell)
function Bit.Pad pGrid, pWidth, pHeight
   local tW, tH, tLeft, tTop, tOut, tSide, tRight, tRow, tLineNo
   put Bit.Width(pGrid) into tW
   put Bit.Height(pGrid) into tH
   if pHeight is empty then put pWidth into pHeight
   if pWidth < tW or pHeight < tH then return pGrid
   put (pWidth - tW) div 2 into tLeft
   put (pHeight - tH) div 2 into tTop
   put line 1 of Bit.Blank(tLeft, 1) into tSide
   put line 1 of Bit.Blank(pWidth - tW - tLeft, 1) into tRight
   put line 1 of Bit.Blank(pWidth, 1) into tRow
   repeat tTop times
      put tRow & return after tOut
   end repeat
   repeat with tLineNo = 1 to tH
      put tSide & line tLineNo of pGrid & tRight & return after tOut
   end repeat
   repeat pHeight - tH - tTop times
      put tRow & return after tOut
   end repeat
   delete the last char of tOut
   return tOut
end Bit.Pad

-------------------------------------------------------------------- formats

-- PBM text (format P1). LiveCode shows it:  set the text of image "x" to Bit.ToPBM(tGrid)
function Bit.ToPBM pGrid
   local tBits
   -- a space after every bit: LiveCode reads P1 only with spaces between the bits (without them
   -- `set the text of image` silently makes a blank 128 x 32 image), found 11 14 2026
   put pGrid into tBits
   replace "1" with "1 " in tBits
   replace "0" with "0 " in tBits
   return "P1" & return & Bit.Width(pGrid) && Bit.Height(pGrid) & return & tBits & return
end Bit.ToPBM

-- PBM text (P1) back to a grid; comments (#) and spaces between bits are allowed
function Bit.FromPBM pPBM
   local tLine, tBody, tW, tH, tBits, tWordNo
   put empty into tBody
   repeat for each line tLine in pPBM
      if char 1 of word 1 of tLine is "#" then next repeat
      put tLine & " " after tBody
   end repeat
   if word 1 of tBody is not "P1" then return empty
   put word 2 of tBody into tW
   put word 3 of tBody into tH
   repeat with tWordNo = 4 to the number of words of tBody
      put word tWordNo of tBody after tBits
   end repeat
   return Bit.FromLongString(char 1 to tW * tH of tBits, tW)
end Bit.FromPBM

-- BitFontMaker2 rows: one number per row, column 1 = 1, column 2 = 2, column 3 = 4 ...
-- (as GridDraw's BuildBitWise). Comma separated, top row first.
function Bit.ToRows pGrid
   local tRow, tOut, tTotal, tCol
   repeat for each line tRow in pGrid
      put 0 into tTotal
      repeat with tCol = 1 to the number of chars of tRow
         if char tCol of tRow is "1" then add 2 ^ (tCol - 1) to tTotal
      end repeat
      put tTotal & comma after tOut
   end repeat
   delete the last char of tOut
   return tOut
end Bit.ToRows

-- BitFontMaker2 rows back to a grid pWidth wide (default 16)
function Bit.FromRows pRows, pWidth
   local tValue, tOut, tNew, tCol
   if pWidth is empty then put 16 into pWidth
   repeat for each item tValue in pRows
      put empty into tNew
      repeat with tCol = 1 to pWidth
         put (trunc(tValue) div (2 ^ (tCol - 1))) mod 2 after tNew
      end repeat
      put tNew & return after tOut
   end repeat
   delete the last char of tOut
   return tOut
end Bit.FromRows

-------------------------------------------------------------------- generating

-- A perfect maze (one path between any two places) of pCols x pRows rooms, as a grid of
-- (2 * pCols + 1) x (2 * pRows + 1): "1" wall, "0" open. Room c,r (1-based) is at grid
-- column 2c, row 2r; the outer edge is all wall. Depth-first carving, so corridors are
-- long and winding. The same pSeed (any whole number; empty = 1) always gives the same
-- maze, here and in any other engine: it uses its own Park-Miller random numbers
-- (x = x * 16807 mod 2147483647), not LiveCode's random().
function Bit.Maze pCols, pRows, pSeed
   local tW, tH, tGrid, tRow, tR, tC, tSeen, tStack, tTop, tX, tY, tDirs, tN, tPick, tNX, tNY, tSteps, tD, tLine
   if pRows is empty then put pCols into pRows
   if pCols < 1 or pRows < 1 then return empty
   if pSeed is not an integer then put 1 into pSeed
   put abs(pSeed) mod 2147483647 into tX
   if tX = 0 then put 1 into tX
   put 2 * pCols + 1 into tW
   put 2 * pRows + 1 into tH
   put 1 into tR
   repeat while tR <= tH
      put 1 into tC
      repeat while tC <= tW
         put "1" into tGrid[tR][tC]
         add 1 to tC
      end repeat
      add 1 to tR
   end repeat
   -- carve from room 1,1 with an explicit stack of rooms ("c,r" lines)
   put 1 into tSeen["1,1"]
   put "0" into tGrid[2][2]
   put "1,1" into tStack
   put 0 into tSteps
   repeat while tStack is not empty and tSteps < 4 * pCols * pRows + 10
      add 1 to tSteps
      put line -1 of tStack into tTop
      put item 1 of tTop into tC
      put item 2 of tTop into tR
      put empty into tDirs
      repeat for each line tD in "0,-1" & return & "1,0" & return & "0,1" & return & "-1,0"
         put tC + item 1 of tD into tNX
         put tR + item 2 of tD into tNY
         if tNX >= 1 and tNX <= pCols and tNY >= 1 and tNY <= pRows and tSeen[tNX & "," & tNY] is empty then
            put tNX & "," & tNY & return after tDirs
         end if
      end repeat
      if tDirs is empty then
         delete line -1 of tStack
         next repeat
      end if
      delete the last char of tDirs
      put (tX * 16807) mod 2147483647 into tX
      put the number of lines of tDirs into tN
      put line (tX mod tN) + 1 of tDirs into tPick
      put item 1 of tPick into tNX
      put item 2 of tPick into tNY
      put 1 into tSeen[tPick]
      put "0" into tGrid[tR + tNY][tC + tNX]     -- the wall between: rows 2r and 2ny meet at r+ny
      put "0" into tGrid[2 * tNY][2 * tNX]
      put return & tPick after tStack
   end repeat
   put empty into tRow
   put 1 into tR
   repeat while tR <= tH
      put empty into tLine
      put 1 into tC
      repeat while tC <= tW
         put tGrid[tR][tC] after tLine
         add 1 to tC
      end repeat
      put tLine & return after tRow
      add 1 to tR
   end repeat
   delete the last char of tRow
   return tRow
end Bit.Maze
