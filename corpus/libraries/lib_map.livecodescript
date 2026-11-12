script "LIB_MAP"
-- LIB_MAP: levels from 1-bit grids. Stitch sections into a world, check the seams,
-- list floors and walls, find paths for AI, merge open space into navigation regions,
-- and build mesh data for 3D. Pure handlers: data in, data out. For xt3d and Vibecode3D.
--
--   start using stack "<path>/LIB_MAP/livecode/lib_map.livecodescript"
--
-- GRIDS are LIB_BIT's format, one line per row:  "1" = wall,  "0" = open floor.
-- (A sprite drawn the other way round: Bit.Invert.) Cells are "col,row", 1-based,
-- rows grow southward, columns eastward.
--
-- Handlers: Map.Stitch, Map.Seams, Map.Pieces, Map.IsOpen, Map.Blocks, Map.BlockEdges, Map.IsFilled,
-- Map.FindPath, Map.Regions, Map.RegionLinks, Map.MeshText

-------------------------------------------------------------------- sections and world

-- pSections: array, section name -> grid (all the same size)
-- pLayout:   lines of section names separated by spaces; "-" is a solid (all wall) section
--   e.g.  "a b a" & return & "c - c"
-- Returns the world grid, or "ERROR: ..." when a name is missing or sizes differ.
function Map.Stitch pSections, pLayout
   local tW, tH, tName, tKeys, tWorld, tLayoutRow, tRowNo, tOut, tSolidRow, tWordNo
   put the keys of pSections into tKeys
   if tKeys is empty then return "ERROR: no sections"
   put line 1 of tKeys into tName
   put the number of chars of line 1 of pSections[tName] into tW
   put the number of lines of pSections[tName] into tH
   repeat for each line tName in tKeys
      if the number of chars of line 1 of pSections[tName] is not tW or \
            the number of lines of pSections[tName] is not tH then
         return "ERROR: section" && tName && "is not" && tW & "x" & tH
      end if
   end repeat
   repeat tW times
      put "1" after tSolidRow
   end repeat
   repeat for each line tLayoutRow in pLayout
      if word 1 of tLayoutRow is empty then next repeat
      repeat with tRowNo = 1 to tH
         put empty into tOut
         repeat with tWordNo = 1 to the number of words of tLayoutRow
            put word tWordNo of tLayoutRow into tName
            if tName is "-" then
               put tSolidRow after tOut
            else if tName is among the lines of tKeys then
               put line tRowNo of pSections[tName] after tOut
            else
               return "ERROR: no section named" && tName
            end if
         end repeat
         put tOut & return after tWorld
      end repeat
   end repeat
   delete the last char of tWorld
   return tWorld
end Map.Stitch

-- Where neighbouring sections meet. One line per seam:
--   sectionCol,sectionRow,east|south,doorways,mismatches
-- doorways = cells open on both sides (0 means the two sections are not connected there);
-- mismatches = positions along the seam (1-based) where one side is open and the other
-- is wall, separated by ";" (a dead end against the neighbour). "-" sections are skipped.
function Map.Seams pSections, pLayout
   local tRows, tRowNo, tCol, tA, tB, tOut, tLayoutRow, tNext, tKeys, tName
   put the keys of pSections into tKeys
   put line 1 of tKeys into tName
   put 0 into tRowNo
   repeat for each line tLayoutRow in pLayout
      if word 1 of tLayoutRow is empty then next repeat
      add 1 to tRowNo
      put tLayoutRow into tRows[tRowNo]
   end repeat
   repeat with tRowNo = 1 to the number of lines of the keys of tRows
      repeat with tCol = 1 to the number of words of tRows[tRowNo]
         put word tCol of tRows[tRowNo] into tA
         if tA is "-" then next repeat
         -- east neighbour
         put word tCol + 1 of tRows[tRowNo] into tB
         if tB is not empty and tB is not "-" then
            put tCol & "," & tRowNo & ",east," & Map.SeamCompare(Map.Column(pSections[tA], -1), \
                  Map.Column(pSections[tB], 1)) & return after tOut
         end if
         -- south neighbour
         if tRowNo < the number of lines of the keys of tRows then
            put word tCol of tRows[tRowNo + 1] into tB
            if tB is not empty and tB is not "-" then
               put tCol & "," & tRowNo & ",south," & Map.SeamCompare(line -1 of pSections[tA], \
                     line 1 of pSections[tB]) & return after tOut
            end if
         end if
      end repeat
   end repeat
   delete the last char of tOut
   return tOut
end Map.Seams

-- one column of a grid as a string, top to bottom (-1 = last column)
private function Map.Column pGrid, pCol
   local tRow, tOut
   repeat for each line tRow in pGrid
      put char pCol of tRow after tOut
   end repeat
   return tOut
end Map.Column

-- "doorways,mismatchPositions" for two edges of equal length
private function Map.SeamCompare pEdgeA, pEdgeB
   local tI, tDoors, tBad
   put 0 into tDoors
   repeat with tI = 1 to the number of chars of pEdgeA
      if char tI of pEdgeA is "0" and char tI of pEdgeB is "0" then
         add 1 to tDoors
      else if char tI of pEdgeA is not char tI of pEdgeB then
         put tI & ";" after tBad
      end if
   end repeat
   if tBad is not empty then delete the last char of tBad
   return tDoors & "," & tBad
end Map.SeamCompare

-------------------------------------------------------------------- level pieces

function Map.IsOpen pWorld, pCol, pRow
   if pCol < 1 or pRow < 1 or pRow > the number of lines of pWorld then return false
   return char pCol of line pRow of pWorld is "0"
end Map.IsOpen

-- One line per piece:  col,row,floor  and  col,row,roof  for every open cell, and
-- col,row,north/south/east/west  for every side of an open cell that faces a wall or
-- the edge of the world (the wall's face looks into the open cell).
function Map.Pieces pWorld
   local tH, tW, tRowNo, tCol, tOut, tRow
   put the number of lines of pWorld into tH
   repeat with tRowNo = 1 to tH
      put line tRowNo of pWorld into tRow
      put the number of chars of tRow into tW
      repeat with tCol = 1 to tW
         if char tCol of tRow is not "0" then next repeat
         put tCol & "," & tRowNo & ",floor" & return after tOut
         put tCol & "," & tRowNo & ",roof" & return after tOut
         if not Map.IsOpen(pWorld, tCol, tRowNo - 1) then put tCol & "," & tRowNo & ",north" & return after tOut
         if not Map.IsOpen(pWorld, tCol, tRowNo + 1) then put tCol & "," & tRowNo & ",south" & return after tOut
         if not Map.IsOpen(pWorld, tCol + 1, tRowNo) then put tCol & "," & tRowNo & ",east" & return after tOut
         if not Map.IsOpen(pWorld, tCol - 1, tRowNo) then put tCol & "," & tRowNo & ",west" & return after tOut
      end repeat
   end repeat
   delete the last char of tOut
   return tOut
end Map.Pieces

-- Raised blocks from the filled ("1") cells: the other way round from Map.Pieces, for
-- relief pictures, sprites made solid, and bit faces. One line per face:
--   col,row,top  for every filled cell, and  col,row,north/south/east/west  for every
--   side of a filled cell next to an empty cell or the edge (facing outward).
function Map.Blocks pGrid
   local tH, tRowNo, tCol, tOut, tRow
   put the number of lines of pGrid into tH
   repeat with tRowNo = 1 to tH
      put line tRowNo of pGrid into tRow
      repeat with tCol = 1 to the number of chars of tRow
         if char tCol of tRow is "0" then next repeat
         put tCol & "," & tRowNo & ",top" & return after tOut
         if not Map.IsFilled(pGrid, tCol, tRowNo - 1) then put tCol & "," & tRowNo & ",north" & return after tOut
         if not Map.IsFilled(pGrid, tCol, tRowNo + 1) then put tCol & "," & tRowNo & ",south" & return after tOut
         if not Map.IsFilled(pGrid, tCol + 1, tRowNo) then put tCol & "," & tRowNo & ",east" & return after tOut
         if not Map.IsFilled(pGrid, tCol - 1, tRowNo) then put tCol & "," & tRowNo & ",west" & return after tOut
      end repeat
   end repeat
   if tOut is not empty then delete the last char of tOut
   return tOut
end Map.Blocks

-- The outline of Map.Blocks as line segments, for vector displays: every block edge once
-- (edges shared by neighbouring faces are not repeated). Picture layout, centred on 0,0:
-- x right, y up (rows go down the picture), z out of the picture toward the viewer;
-- a cell is pCell wide, blocks stand pHeight out. pPanel true adds the grid lines of
-- the whole picture at z = 0. One segment per line:  x1,y1,z1,x2,y2,z2
function Map.BlockEdges pGrid, pCell, pHeight, pPanel
   local tCols, tRows, tFace, tC, tR, tX0, tX1, tY0, tY1, tH, tSeen, tOut, tI, tLeft, tTop
   if pCell is empty then put 1 into pCell
   if pHeight is empty then put pCell into pHeight
   put pHeight into tH
   put the number of chars of line 1 of pGrid into tCols
   put the number of lines of pGrid into tRows
   put -tCols * pCell / 2 into tLeft
   put tRows * pCell / 2 into tTop
   repeat for each line tFace in Map.Blocks(pGrid)
      put item 1 of tFace into tC
      put item 2 of tFace into tR
      put tLeft + (tC - 1) * pCell into tX0
      put tX0 + pCell into tX1
      put tTop - tR * pCell into tY0
      put tY0 + pCell into tY1
      switch item 3 of tFace
         case "top"
            Map.AddQuad tSeen, tX0,tY0,tH, tX1,tY0,tH, tX1,tY1,tH, tX0,tY1,tH
            break
         case "north"
            Map.AddQuad tSeen, tX0,tY1,0, tX1,tY1,0, tX1,tY1,tH, tX0,tY1,tH
            break
         case "south"
            Map.AddQuad tSeen, tX0,tY0,0, tX1,tY0,0, tX1,tY0,tH, tX0,tY0,tH
            break
         case "west"
            Map.AddQuad tSeen, tX0,tY0,0, tX0,tY1,0, tX0,tY1,tH, tX0,tY0,tH
            break
         case "east"
            Map.AddQuad tSeen, tX1,tY0,0, tX1,tY1,0, tX1,tY1,tH, tX1,tY0,tH
            break
      end switch
   end repeat
   if pPanel is true then
      repeat with tI = 0 to tCols
         Map.AddEdge tSeen, (tLeft + tI * pCell) & "," & tTop & ",0", (tLeft + tI * pCell) & "," & -tTop & ",0"
      end repeat
      repeat with tI = 0 to tRows
         Map.AddEdge tSeen, tLeft & "," & (tTop - tI * pCell) & ",0", -tLeft & "," & (tTop - tI * pCell) & ",0"
      end repeat
   end if
   put the keys of tSeen into tOut
   sort lines of tOut
   return tOut
end Map.BlockEdges

private command Map.AddQuad @pSeen, pAX,pAY,pAZ, pBX,pBY,pBZ, pCX,pCY,pCZ, pDX,pDY,pDZ
   Map.AddEdge pSeen, pAX & "," & pAY & "," & pAZ, pBX & "," & pBY & "," & pBZ
   Map.AddEdge pSeen, pBX & "," & pBY & "," & pBZ, pCX & "," & pCY & "," & pCZ
   Map.AddEdge pSeen, pCX & "," & pCY & "," & pCZ, pDX & "," & pDY & "," & pDZ
   Map.AddEdge pSeen, pDX & "," & pDY & "," & pDZ, pAX & "," & pAY & "," & pAZ
end Map.AddQuad

-- one segment, stored once whichever way round it comes
private command Map.AddEdge @pSeen, pA, pB
   if pA < pB then
      put true into pSeen[pA & "," & pB]
   else
      put true into pSeen[pB & "," & pA]
   end if
end Map.AddEdge

function Map.IsFilled pGrid, pCol, pRow
   local tC
   if pCol < 1 or pRow < 1 or pRow > the number of lines of pGrid then return false
   put char pCol of line pRow of pGrid into tC
   return tC is not empty and tC is not "0"
end Map.IsFilled

-------------------------------------------------------------------- pathfinding

-- A* from pFrom to pTo ("col,row"). pDiagonal true allows 8 directions (never cutting a
-- wall corner). Returns the cells of the path, one "col,row" per line, start and goal
-- included; empty when there is no way through. Costs: 10 straight, 14 diagonal.
function Map.FindPath pWorld, pFrom, pTo, pDiagonal
   local tDirs, tG, tCame, tClosed, tBucket, tMinF, tMaxF, tAt, tX, tY, tGX, tGY
   local tD, tNX, tNY, tKey, tCost, tNewG, tF, tPath, tLimit, tSteps
   if not Map.IsOpen(pWorld, item 1 of pFrom, item 2 of pFrom) then return empty
   if not Map.IsOpen(pWorld, item 1 of pTo, item 2 of pTo) then return empty
   put "1,0,10" & return & "-1,0,10" & return & "0,1,10" & return & "0,-1,10" into tDirs
   if pDiagonal is true then
      put return & "1,1,14" & return & "1,-1,14" & return & "-1,1,14" & return & "-1,-1,14" after tDirs
   end if
   put item 1 of pTo into tGX
   put item 2 of pTo into tGY
   put 0 into tG[pFrom]
   put Map.Guess(item 1 of pFrom, item 2 of pFrom, tGX, tGY, pDiagonal) into tMinF
   put pFrom into tBucket[tMinF]
   put tMinF into tMaxF
   put 20 * the number of lines of pWorld * the number of chars of line 1 of pWorld into tLimit
   put 0 into tSteps
   repeat
      -- take the cheapest waiting cell (bucket queue: costs are whole numbers)
      repeat while tBucket[tMinF] is empty and tMinF <= tMaxF
         add 1 to tMinF
      end repeat
      if tMinF > tMaxF then return empty            -- nothing left: no path
      put line 1 of tBucket[tMinF] into tAt
      delete line 1 of tBucket[tMinF]
      if tClosed[tAt] is true then next repeat
      put true into tClosed[tAt]
      if tAt is pTo then exit repeat
      add 1 to tSteps
      if tSteps > tLimit then return empty
      put item 1 of tAt into tX
      put item 2 of tAt into tY
      repeat for each line tD in tDirs
         put tX + item 1 of tD into tNX
         put tY + item 2 of tD into tNY
         if not Map.IsOpen(pWorld, tNX, tNY) then next repeat
         if item 1 of tD is not 0 and item 2 of tD is not 0 then
            -- no squeezing diagonally past a wall corner
            if not Map.IsOpen(pWorld, tNX, tY) or not Map.IsOpen(pWorld, tX, tNY) then next repeat
         end if
         put tNX & "," & tNY into tKey
         if tClosed[tKey] is true then next repeat
         put tG[tAt] + item 3 of tD into tNewG
         if tG[tKey] is empty or tNewG < tG[tKey] then
            put tNewG into tG[tKey]
            put tAt into tCame[tKey]
            put tNewG + Map.Guess(tNX, tNY, tGX, tGY, pDiagonal) into tF
            if tBucket[tF] is empty then
               put tKey into tBucket[tF]
            else
               put return & tKey after tBucket[tF]
            end if
            if tF > tMaxF then put tF into tMaxF
            if tF < tMinF then put tF into tMinF
         end if
      end repeat
   end repeat
   -- walk back from the goal
   put pTo into tAt
   put tAt into tPath
   repeat while tAt is not pFrom
      put tCame[tAt] into tAt
      put tAt & return before tPath
   end repeat
   return tPath
end Map.FindPath

-- estimated cost to the goal: Manhattan (4 directions) or octile (8 directions)
private function Map.Guess pX, pY, pGX, pGY, pDiagonal
   local tDX, tDY
   put abs(pX - pGX) into tDX
   put abs(pY - pGY) into tDY
   if pDiagonal is true then return 10 * max(tDX, tDY) + 4 * min(tDX, tDY)
   return 10 * (tDX + tDY)
end Map.Guess

-------------------------------------------------------------------- navigation regions

-- Open space merged into rectangles, scanning top-left to bottom-right: each grows as
-- wide as it can, then as tall as it can. One line per region:  id,left,top,right,bottom
-- (cells, inclusive). AI can plan region to region (Map.RegionLinks), then cell to cell.
function Map.Regions pWorld
   local tH, tW, tUsed, tRowNo, tCol, tRight, tBottom, tOK, tC, tId, tOut, tR
   put the number of lines of pWorld into tH
   put the number of chars of line 1 of pWorld into tW
   put 0 into tId
   repeat with tRowNo = 1 to tH
      repeat with tCol = 1 to tW
         if char tCol of line tRowNo of pWorld is not "0" or tUsed[tCol, tRowNo] is true then next repeat
         put tCol into tRight
         repeat while tRight < tW
            if char tRight + 1 of line tRowNo of pWorld is not "0" or tUsed[tRight + 1, tRowNo] is true then exit repeat
            add 1 to tRight
         end repeat
         put tRowNo into tBottom
         repeat while tBottom < tH
            put true into tOK
            repeat with tC = tCol to tRight
               if char tC of line tBottom + 1 of pWorld is not "0" or tUsed[tC, tBottom + 1] is true then
                  put false into tOK
                  exit repeat
               end if
            end repeat
            if not tOK then exit repeat
            add 1 to tBottom
         end repeat
         add 1 to tId
         repeat with tR = tRowNo to tBottom
            repeat with tC = tCol to tRight
               put true into tUsed[tC, tR]
            end repeat
         end repeat
         put tId & "," & tCol & "," & tRowNo & "," & tRight & "," & tBottom & return after tOut
      end repeat
   end repeat
   delete the last char of tOut
   return tOut
end Map.Regions

-- Which regions touch (share an open edge). One line per pair, "a,b" with a < b, sorted.
function Map.RegionLinks pWorld, pRegions
   local tOwner, tLine, tC, tR, tSeen, tOut, tA, tB, tPair
   repeat for each line tLine in pRegions
      repeat with tR = item 3 of tLine to item 5 of tLine
         repeat with tC = item 2 of tLine to item 4 of tLine
            put item 1 of tLine into tOwner[tC, tR]
         end repeat
      end repeat
   end repeat
   repeat for each line tLine in pRegions
      put item 1 of tLine into tA
      repeat with tR = item 3 of tLine to item 5 of tLine
         repeat with tC = item 2 of tLine to item 4 of tLine
            -- look east and south only; every touching pair is found once that way
            put tOwner[tC + 1, tR] into tB
            if tB is not empty and tB is not tA then put min(tA, tB) & "," & max(tA, tB) into tSeen[min(tA, tB) & "," & max(tA, tB)]
            put tOwner[tC, tR + 1] into tB
            if tB is not empty and tB is not tA then put min(tA, tB) & "," & max(tA, tB) into tSeen[min(tA, tB) & "," & max(tA, tB)]
         end repeat
      end repeat
   end repeat
   put the keys of tSeen into tOut
   sort lines of tOut numeric by item 2 of each
   sort lines of tOut numeric by item 1 of each
   return tOut
end Map.RegionLinks

-------------------------------------------------------------------- 3D mesh data

-- Triangles for xt3d_MeshFromText (or any engine): a floor quad under every open cell and
-- a wall quad on every side listed by Map.Pieces, facing into the open space, so the
-- level looks right with back-face culling on. x = east, z = south, y = up; one cell is
-- pCell units, walls are pHeight high; pRoof true adds ceilings (facing down).
-- Returns an array: ["vertices"] "x,y,z" one per line, every 3 lines one triangle;
-- ["triangles"] the count.     put Map.MeshText(tWorld, 1, 1) into tM
--                              put xt3d_MeshFromText(tM["vertices"], "", "") into tMesh
function Map.MeshText pWorld, pCell, pHeight, pRoof
   local tPiece, tX0, tX1, tZ0, tZ1, tH, tOut, tCount, tResult
   if pCell is empty then put 1 into pCell
   if pHeight is empty then put pCell into pHeight
   put pHeight into tH
   put 0 into tCount
   repeat for each line tPiece in Map.Pieces(pWorld)
      put (item 1 of tPiece - 1) * pCell into tX0
      put tX0 + pCell into tX1
      put (item 2 of tPiece - 1) * pCell into tZ0
      put tZ0 + pCell into tZ1
      switch item 3 of tPiece
         case "floor"     -- facing up
            put Map.Tri(tX0,0,tZ0, tX1,0,tZ1, tX1,0,tZ0) & Map.Tri(tX0,0,tZ0, tX0,0,tZ1, tX1,0,tZ1) after tOut
            break
         case "roof"      -- facing down, only when asked
            if pRoof is not true then next repeat
            put Map.Tri(tX0,tH,tZ0, tX1,tH,tZ0, tX1,tH,tZ1) & Map.Tri(tX0,tH,tZ0, tX1,tH,tZ1, tX0,tH,tZ1) after tOut
            break
         case "north"     -- at the cell's north edge, facing south
            put Map.Tri(tX0,0,tZ0, tX1,0,tZ0, tX1,tH,tZ0) & Map.Tri(tX0,0,tZ0, tX1,tH,tZ0, tX0,tH,tZ0) after tOut
            break
         case "south"     -- facing north
            put Map.Tri(tX0,0,tZ1, tX1,tH,tZ1, tX1,0,tZ1) & Map.Tri(tX0,0,tZ1, tX0,tH,tZ1, tX1,tH,tZ1) after tOut
            break
         case "west"      -- facing east
            put Map.Tri(tX0,0,tZ0, tX0,tH,tZ1, tX0,0,tZ1) & Map.Tri(tX0,0,tZ0, tX0,tH,tZ0, tX0,tH,tZ1) after tOut
            break
         case "east"      -- facing west
            put Map.Tri(tX1,0,tZ0, tX1,0,tZ1, tX1,tH,tZ1) & Map.Tri(tX1,0,tZ0, tX1,tH,tZ1, tX1,tH,tZ0) after tOut
            break
      end switch
      add 2 to tCount
   end repeat
   if pRoof is not true then
      -- roofs were skipped but counted above; count again from the text
      put the number of lines of tOut div 3 into tCount
   end if
   if tOut is not empty then delete the last char of tOut
   put tOut into tResult["vertices"]
   put tCount into tResult["triangles"]
   return tResult
end Map.MeshText

private function Map.Tri pAX, pAY, pAZ, pBX, pBY, pBZ, pCX, pCY, pCZ
   return pAX & "," & pAY & "," & pAZ & return & pBX & "," & pBY & "," & pBZ & return & \
         pCX & "," & pCY & "," & pCZ & return
end Map.Tri
