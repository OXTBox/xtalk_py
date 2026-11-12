script "xt3dFace"
-- xt3d face demo: a procedurally generated wireframe face in the style of 1980s computer
-- graphics, rendered by raylib and saved as a PNG. Mouth controls make it "say" things.
--
--   start using stack "<path>/demos/xt3d_face.livecodescript"
--   Face.Render "C:/LIB_MCP/face.png", 0.2, 0.0, "HI!"     -- file, mouth open, smile, caption
--
-- Needs a raylib window (the test bench or xt3d_InitHidden). Face.Mesh is pure: it only
-- builds number lists, so another engine (Vibecode3D) could draw the same face.

constant kCols = 36       -- grid cells across
constant kRows = 22       -- grid cells down
constant kW = 1200        -- picture size
constant kH = 700

-- one smooth bump: height pAmount at (pCX, pCY), widths pSX, pSY
private function Face.Bump pX, pY, pCX, pCY, pSX, pSY, pAmount
   return pAmount * exp(-(((pX - pCX) / pSX) ^ 2) - (((pY - pCY) / pSY) ^ 2))
end Face.Bump

-- depth of the face at (pX, pY): x from -1.6 to 1.6, y from -1 (chin) to 1 (forehead)
function Face.Depth pX, pY, pOpen, pSmile
   local tZ, tSide, tMouthY
   -- the head: a wide rounded front, falling away at the sides
   put 0.55 * cos(pX * 0.85) + 0.15 * cos(pY * 1.2) into tZ
   repeat for each item tSide in "-1,1"
      add Face.Bump(pX, pY, 0.55 * tSide, 0.28, 0.30, 0.15, -0.20) to tZ   -- eye socket
      add Face.Bump(pX, pY, 0.55 * tSide, 0.27, 0.15, 0.07, 0.10) to tZ    -- eyeball
      add Face.Bump(pX, pY, 0.55 * tSide, 0.48, 0.36, 0.06, 0.12) to tZ    -- brow
      add Face.Bump(pX, pY, 0.82 * tSide, -0.22, 0.30, 0.30, 0.13) to tZ   -- cheek
      add Face.Bump(pX, pY, 0.11 * tSide, -0.36, 0.06, 0.05, -0.06) to tZ  -- nostril
   end repeat
   add Face.Bump(pX, pY, 0, 0.0, 0.11, 0.42, 0.42) to tZ        -- nose bridge
   add Face.Bump(pX, pY, 0, -0.30, 0.17, 0.12, 0.16) to tZ      -- nose tip
   -- the mouth line rises at the corners when smiling
   put -0.62 + pSmile * 0.25 * (pX ^ 2) into tMouthY
   add Face.Bump(pX, pY, 0, tMouthY + 0.07, 0.42, 0.05, 0.10) to tZ           -- upper lip
   add Face.Bump(pX, pY, 0, tMouthY - 0.08 - pOpen * 0.10, 0.38, 0.06, 0.10) to tZ   -- lower lip
   add Face.Bump(pX, pY, 0, tMouthY - pOpen * 0.05, 0.34 + pSmile * 0.10, 0.02 + pOpen * 0.07, \
         -0.10 - pOpen * 0.30) to tZ                                          -- the opening
   add Face.Bump(pX, pY, 0, -0.95, 0.40, 0.14, 0.10) to tZ      -- chin
   return tZ
end Face.Depth

-- the face as a mesh: ["vertices"] x,y,z per line, ["indices"] three 0-based vertex
-- numbers per triangle. Diagonals alternate cell by cell for the faceted look.
function Face.Mesh pOpen, pSmile
   local tOut, tRow, tCol, tX, tY, tV, tI, tA, tB, tC, tD, tStride
   put kCols + 1 into tStride
   repeat with tRow = 0 to kRows
      repeat with tCol = 0 to kCols
         put -1.6 + 3.2 * tCol / kCols into tX
         put 1 - 2 * tRow / kRows into tY
         put tX & "," & tY & "," & Face.Depth(tX, tY, pOpen, pSmile) & return after tV
      end repeat
   end repeat
   repeat with tRow = 0 to kRows - 1
      repeat with tCol = 0 to kCols - 1
         put tRow * tStride + tCol into tA      -- top left
         put tA + 1 into tB                     -- top right
         put tA + tStride into tC               -- bottom left
         put tC + 1 into tD                     -- bottom right
         if (tRow + tCol) mod 2 = 0 then
            put tA & "," & tC & "," & tB & "," & tB & "," & tC & "," & tD & "," after tI
         else
            put tA & "," & tC & "," & tD & "," & tA & "," & tD & "," & tB & "," after tI
         end if
      end repeat
   end repeat
   delete the last char of tV
   delete the last char of tI
   put tV into tOut["vertices"]
   put tI into tOut["indices"]
   return tOut
end Face.Mesh

-- The face as a 1-bit grid (LIB_BIT format, "1" = drawn), like a pen drawing of it:
-- a cell is 1 where the face dips in (eye sockets, mouth, nostrils) by more than pDip or
-- stands out (brows, nose) by more than pRise, measured from the plain head shape.
function Face.Bits pCols, pRows, pOpen, pSmile, pDip, pRise
   local tGrid, tRow, tCol, tX, tY, tF
   if pDip is empty then put 0.05 into pDip
   if pRise is empty then put 0.10 into pRise
   repeat with tRow = 1 to pRows
      repeat with tCol = 1 to pCols
         put -1.6 + 3.2 * (tCol - 0.5) / pCols into tX
         put 1 - 2 * (tRow - 0.5) / pRows into tY
         put Face.Depth(tX, tY, pOpen, pSmile) - (0.55 * cos(tX * 0.85) + 0.15 * cos(tY * 1.2)) into tF
         if tF < -pDip or tF > pRise then
            put "1" after tGrid
         else
            put "0" after tGrid
         end if
      end repeat
      put return after tGrid
   end repeat
   delete the last char of tGrid
   return tGrid
end Face.Bits

-- vertex positions shared by the drawing handlers below
local sVX, sVY, sVZ, sZMin, sZMax

-- draw the face into a picture and save it as a PNG: pure wireframe, vector-display
-- style, lines brighter where the face comes forward.
command Face.Render pFile, pOpen, pSmile, pCaption
   local tTarget, tCam, tSize, tTextW, tRow, tCol, tX, tY, tZ
   if not xt3d_IsWindowReady() then return "no raylib window: open the bench first"
   put empty into sVX
   put empty into sVY
   put empty into sVZ
   put 99 into sZMin
   put -99 into sZMax
   repeat with tRow = 0 to kRows
      repeat with tCol = 0 to kCols
         put -1.6 + 3.2 * tCol / kCols into tX
         put 1 - 2 * tRow / kRows into tY
         put Face.Depth(tX, tY, pOpen, pSmile) into tZ
         put tX into sVX[tRow, tCol]
         put tY into sVY[tRow, tCol]
         put tZ into sVZ[tRow, tCol]
         put min(sZMin, tZ) into sZMin
         put max(sZMax, tZ) into sZMax
      end repeat
   end repeat
   put xt3d_LoadRenderTexture(kW, kH) into tTarget
   -- a little below and to the right of centre, so the relief shows; 38 degree lens
   put xt3d_CameraCreate(0.35,-0.30,4.3, 0,-0.02,0, 0,1,0, 38, 0) into tCam
   xt3d_BeginTextureMode tTarget
   xt3d_ClearBackground 6, 10, 22, 255
   xt3d_BeginMode3D tCam
   xt3d_SetBackfaceCulling false
   repeat with tRow = 0 to kRows - 1
      repeat with tCol = 0 to kCols - 1
         if (tRow + tCol) mod 2 = 0 then
            Face.Line tRow,tCol+1, tRow+1,tCol
         else
            Face.Line tRow,tCol, tRow+1,tCol+1
         end if
         Face.Line tRow,tCol, tRow,tCol+1
         Face.Line tRow,tCol, tRow+1,tCol
      end repeat
      Face.Line tRow,kCols, tRow+1,kCols
   end repeat
   repeat with tCol = 0 to kCols - 1
      Face.Line kRows,tCol, kRows,tCol+1
   end repeat
   xt3d_SetBackfaceCulling true
   xt3d_EndMode3D
   if pCaption is not empty then
      put 56 into tSize
      put xt3d_MeasureText(pCaption, tSize) into tTextW
      xt3d_DrawText pCaption, (kW - tTextW) div 2, kH - 80, tSize, 150, 250, 250, 255
   end if
   xt3d_EndTextureMode
   get xt3d_RenderTextureExport(tTarget, pFile)
   xt3d_UnloadRenderTexture tTarget
   xt3d_CameraFree tCam
   return "saved" && pFile
end Face.Render


-- one cyan line between two grid points, brighter where the face is nearer
private command Face.Line pR1, pC1, pR2, pC2
   local tNear
   put ((sVZ[pR1, pC1] + sVZ[pR2, pC2]) / 2 - sZMin) / max(0.001, sZMax - sZMin) into tNear
   put 0.30 + 0.70 * tNear into tNear
   xt3d_DrawLine3D sVX[pR1, pC1], sVY[pR1, pC1], sVZ[pR1, pC1] + 0.005, \
         sVX[pR2, pC2], sVY[pR2, pC2], sVZ[pR2, pC2] + 0.005, \
         round(120 * tNear), round(240 * tNear), round(240 * tNear), 255
end Face.Line

-------------------------------------------------------------------- the bit face, in blocks

-- Draw a 1-bit grid as raised wireframe blocks standing upright on a grid panel (LIB_MAP's
-- Map.Blocks gives the faces; LIB_MAP must be in use). pCell = block size, pDepth = height.
command Face.RenderBits pGrid, pFile, pCaption, pCell, pDepth
   local tCols, tRows, tTarget, tCam, tFace, tC, tR, tX0, tX1, tY0, tY1, tH, tSize, tTextW, tI
   if not xt3d_IsWindowReady() then return "no raylib window: open the bench first"
   if pCell is empty then put 0.12 into pCell
   if pDepth is empty then put 0.24 into pDepth
   put pDepth into tH
   put the number of chars of line 1 of pGrid into tCols
   put the number of lines of pGrid into tRows
   put xt3d_LoadRenderTexture(kW, kH) into tTarget
   put xt3d_CameraCreate(1.7,-1.3,5.6, 0,-0.05,0, 0,1,0, 45, 0) into tCam
   xt3d_BeginTextureMode tTarget
   xt3d_ClearBackground 6, 10, 22, 255
   xt3d_BeginMode3D tCam
   xt3d_SetBackfaceCulling false
   -- the panel and its grid
   put -tCols * pCell / 2 into tX0
   put tRows * pCell / 2 into tY1
   repeat with tI = 0 to tCols
      xt3d_DrawLine3D tX0 + tI * pCell, tY1, 0, tX0 + tI * pCell, -tY1, 0, 30,90,100,255
   end repeat
   repeat with tI = 0 to tRows
      xt3d_DrawLine3D tX0, tY1 - tI * pCell, 0, -tX0, tY1 - tI * pCell, 0, 30,90,100,255
   end repeat
   -- the blocks
   repeat for each line tFace in Map.Blocks(pGrid)
      put item 1 of tFace into tC
      put item 2 of tFace into tR
      put (tC - 1 - tCols / 2) * pCell into tX0
      put tX0 + pCell into tX1
      put (tRows / 2 - tR) * pCell into tY0
      put tY0 + pCell into tY1
      switch item 3 of tFace
         case "top"     -- the face toward the viewer
            Face.Quad tX0,tY0,tH, tX1,tY0,tH, tX1,tY1,tH, tX0,tY1,tH
            break
         case "north"
            Face.Quad tX0,tY1,0, tX1,tY1,0, tX1,tY1,tH, tX0,tY1,tH
            break
         case "south"
            Face.Quad tX0,tY0,0, tX1,tY0,0, tX1,tY0,tH, tX0,tY0,tH
            break
         case "west"
            Face.Quad tX0,tY0,0, tX0,tY1,0, tX0,tY1,tH, tX0,tY0,tH
            break
         case "east"
            Face.Quad tX1,tY0,0, tX1,tY1,0, tX1,tY1,tH, tX1,tY0,tH
            break
      end switch
   end repeat
   xt3d_SetBackfaceCulling true
   xt3d_EndMode3D
   if pCaption is not empty then
      put 48 into tSize
      put xt3d_MeasureText(pCaption, tSize) into tTextW
      xt3d_DrawText pCaption, (kW - tTextW) div 2, kH - 70, tSize, 150, 250, 250, 255
   end if
   xt3d_EndTextureMode
   get xt3d_RenderTextureExport(tTarget, pFile)
   xt3d_UnloadRenderTexture tTarget
   xt3d_CameraFree tCam
   return "saved" && pFile
end Face.RenderBits

-- the four cyan edges of a quad
private command Face.Quad pAX,pAY,pAZ, pBX,pBY,pBZ, pCX,pCY,pCZ, pDX,pDY,pDZ
   xt3d_DrawLine3D pAX,pAY,pAZ, pBX,pBY,pBZ, 120,245,245,255
   xt3d_DrawLine3D pBX,pBY,pBZ, pCX,pCY,pCZ, 120,245,245,255
   xt3d_DrawLine3D pCX,pCY,pCZ, pDX,pDY,pDZ, 120,245,245,255
   xt3d_DrawLine3D pDX,pDY,pDZ, pAX,pAY,pAZ, 120,245,245,255
end Face.Quad
