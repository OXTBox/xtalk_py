script "LIB_TRACE"
-- LIB_TRACE: bitmap -> shapes. Outline tracing: bitmap to polygon points.
-- (Grid to 3D map moved to LIB_MAP: Map.Pieces.)
-- Pure handlers: data in, data out; no globals, custom properties, graphics or screen.
--
--   start using stack "<path>/LIB_TRACE/livecode/lib_trace.livecodescript"
--   put Trace.MaskToGrid(the maskData of image "logo", the width of image "logo", \
--         the height of image "logo") into tGrid
--   set the points of graphic "outline" to Trace.Offset(Trace.Contours(tGrid), \
--         the left of image "logo" - 1, the top of image "logo" - 1)
--
-- Grids are LIB_BIT's format: lines of "0"/"1" (any non-"0" character counts as filled).
-- Points are LiveCode's polygon format: one "x,y" per line, 1-based pixel positions,
-- an empty line between separate outlines.
--
-- From the owner's bitmap tracer (radial sweep contour following), made pure.
-- Handlers: Trace.Contours, Trace.MaskToGrid, Trace.Offset, Trace.Scale

-------------------------------------------------------------------- outline tracing

-- Follow every outline in the grid. Rows are scanned top to bottom; where a row goes from
-- empty to filled at a pixel not yet traced, the outline from there is followed clockwise
-- until it returns to its first two points; it ends on its first point again, closing it.
-- A lone pixel is its own one-point outline.
function Trace.Contours pGrid
   local tCell, tW, tH, tSweep, tFound, tPoints, tRowNo, tCol, tRow
   local tLast, tValue, tStart, tFirst, tSecond, tAt, tNext, tAngle, tSteps, tLimit
   put Trace.SweepTable() into tSweep
   put the number of lines of pGrid into tH
   put the number of chars of line 1 of pGrid into tW
   put 4 * tW * tH + 8 into tLimit   -- no outline can be longer; a guard against looping forever
   -- tCell[y][x] = 1 for filled pixels
   repeat with tRowNo = 1 to tH
      put line tRowNo of pGrid into tRow
      repeat with tCol = 1 to tW
         if char tCol of tRow is not "0" and char tCol of tRow is not empty then put 1 into tCell[tRowNo][tCol]
      end repeat
   end repeat

   repeat with tRowNo = 1 to tH
      put false into tLast
      repeat with tCol = 1 to tW
         put tCell[tRowNo][tCol] is 1 into tValue
         if not tValue or tLast then
            put tValue into tLast
            next repeat
         end if
         put tValue into tLast
         put tCol & "," & tRowNo into tStart
         if tFound[tStart] is true then next repeat   -- already part of an outline

         put tStart & return after tPoints
         put true into tFound[tStart]
         put 180 into tAngle
         put Trace.Sweep(tCol, tRowNo, tAngle, tSweep, tCell) into tNext
         if tNext is "none" then
            put return after tPoints               -- a lone pixel
            put false into tLast
            next repeat
         end if
         put tStart into tFirst
         put tNext into tSecond
         put tNext & return after tPoints
         put true into tFound[tNext]
         put tNext into tAt
         put 0 into tSteps
         repeat
            put Trace.Sweep(item 1 of tAt, item 2 of tAt, tAngle, tSweep, tCell) into tNext
            if tNext is "none" then exit repeat
            -- standing on the first point and about to step to the second: closed
            if tAt is tFirst and tNext is tSecond then exit repeat
            put tNext & return after tPoints
            put true into tFound[tNext]
            put tNext into tAt
            add 1 to tSteps
            if tSteps > tLimit then exit repeat
         end repeat
         -- as in the original, the outline ends on its first point again (closing it), and
         -- the rest of this row counts as inside the shape (tLast stays true)
         put return after tPoints
      end repeat
   end repeat
   -- tidy: no empty line at the start or end
   repeat while char -1 of tPoints is return
      delete char -1 of tPoints
   end repeat
   return tPoints
end Trace.Contours

-- angle we arrived from -> neighbour offset to test first (the tracer's uRadialSweepAngle)
private function Trace.SweepTable
   local tT
   put "1,1" into tT[0]
   put "1,0" into tT[45]
   put "1,-1" into tT[90]
   put "0,-1" into tT[135]
   put "-1,-1" into tT[180]
   put "-1,0" into tT[225]
   put "-1,1" into tT[270]
   put "0,1" into tT[315]
   return tT
end Trace.SweepTable

-- look round the 8 neighbours, clockwise, starting from the direction we came from;
-- returns "x,y" of the first filled one (and updates pAngle), or "none"
private function Trace.Sweep pX, pY, @pAngle, @pSweep, @pCell
   local tI, tNX, tNY, tDX, tDY
   put pAngle into tI
   repeat 8 times
      put pX + item 1 of pSweep[tI] into tNX
      put pY + item 2 of pSweep[tI] into tNY
      if pCell[tNY][tNX] is 1 then
         put tNX - pX into tDX
         put tNY - pY into tDY
         -- the angle back to where we were; 360 is the same as 0
         put round(abs(atan2(tDY, tDX) * 180 / pi - 180)) mod 360 into pAngle
         return tNX & "," & tNY
      end if
      put (tI - 45 + 360) mod 360 into tI
   end repeat
   return "none"
end Trace.Sweep

-- an image's maskData (one byte per pixel) -> grid; pixels above pThreshold are filled
function Trace.MaskToGrid pMask, pWidth, pHeight, pThreshold
   local tGrid, tRowNo, tCol, tByte
   if pThreshold is empty then put 0 into pThreshold
   repeat with tRowNo = 0 to pHeight - 1
      repeat with tCol = 1 to pWidth
         put byteToNum(byte tRowNo * pWidth + tCol of pMask) into tByte
         if tByte > pThreshold then
            put "1" after tGrid
         else
            put "0" after tGrid
         end if
      end repeat
      put return after tGrid
   end repeat
   delete the last char of tGrid
   return tGrid
end Trace.MaskToGrid

-- move every point by pDX, pDY (e.g. to the image's place on the card); keeps empty lines
function Trace.Offset pPoints, pDX, pDY
   local tLine, tOut
   repeat for each line tLine in pPoints
      if tLine is empty then
         put return after tOut
      else
         put (item 1 of tLine + pDX) & "," & (item 2 of tLine + pDY) & return after tOut
      end if
   end repeat
   delete the last char of tOut
   return tOut
end Trace.Offset

-- multiply every point by pScale (a grid cell becomes pScale pixels)
function Trace.Scale pPoints, pScale
   local tLine, tOut
   repeat for each line tLine in pPoints
      if tLine is empty then
         put return after tOut
      else
         put (item 1 of tLine * pScale) & "," & (item 2 of tLine * pScale) & return after tOut
      end if
   end repeat
   delete the last char of tOut
   return tOut
end Trace.Scale
