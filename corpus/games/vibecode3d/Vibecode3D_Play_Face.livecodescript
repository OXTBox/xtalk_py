######################################################################################
## CARD SCRIPT: "Play.Face"   CLAUDE FACE  (11 12 2026)
## Claude's face as raised vector blocks on a dim grid panel: the "LIB_MCP connected"
## card. The picture is LIB_MCP's assets/claude_face_bits.txt (a 48 x 26 one-bit grid,
## the smiling "I" of "HI!"). LIB_MAP's Map.BlockEdges turns it into line segments,
## and they become two ordinary engine meshes (wire lines only, no faces).
## The face sways slowly from side to side. Nothing else happens: Escape leaves.
## INSTALL   This file is the card script of card "Play.Face" (see LIB_GAMES README.md).
## CONTROLS  Escape: back to Developer.
## NEEDS     ../LIB_MCP and ../LIB_MAP next to the Vibecode3D folder (found the same
##           way MCP.Attach finds LIB_MCP). Without them the card says what is missing.
######################################################################################

global bPaused, bPlaying

local sStepMS = 33, sTicks = 0, sFaceKey, sPanelKey

constant kFaceCell = 10      -- world units per grid cell: the face is 480 x 260
constant kFaceHeight = 6     -- how far the blocks stand out of the panel
constant kFaceSway = 0.35    -- radians each way
constant kFaceYaw = 0.45     -- the resting three-quarter turn
constant kFaceDist = 380    -- in front of the camera (which sits at 0,0,0 after Engine.ResetCamera)

on Game.OnStart
   local tErr
   Camera.Reset
   put Engine.Info("stepMS") into sStepMS
   Scene.ClearAll
   Particles.Clear
   HUD.Clear
   Collision.ClearRules
   put 0 into sTicks
   put Face.MakeMeshes() into tErr
   if tErr is not empty then
      HUD.Set "Face.Msg", tErr, 20, 160, 12
      exit Game.OnStart
   end if
   put Entity.Spawn("Face.Panel", 0, 0, kFaceDist, "30,95,105") into sPanelKey
   put Entity.Spawn("Face.Bits", 0, 0, kFaceDist, "130,250,250") into sFaceKey
   Face.Turn
   HUD.Set "Face.Title", "CLAUDE", 20, 120, 16
end Game.OnStart

on Game.OnUpdate
   add 1 to sTicks
   Face.Turn
end Game.OnUpdate

-- a slow side-to-side sway around the three-quarter view, a little from above
on Face.Turn
   local tYaw
   put kFaceYaw * sin(sTicks * sStepMS / 2400) into tYaw
   if sFaceKey is not empty then Entity.SetRotation sFaceKey, 0.18, tYaw, 0
   if sPanelKey is not empty then Entity.SetRotation sPanelKey, 0.18, tYaw, 0
end Face.Turn

on Game.OnClick pX,pY,pButton
end Game.OnClick

on Game.OnKill pKey,pX,pY,pZ
end Game.OnKill

on Game.OnPause
end Game.OnPause

on Game.OnResume
end Game.OnResume

on Game.OnStop
   HUD.Remove "Face.Title"
   HUD.Remove "Face.Msg"
end Game.OnStop

on Collision.Hit pA,pB
end Collision.Hit

-- Defines "Face.Bits" (the face) and "Face.Panel" (the dim grid behind it).
-- Returns empty, or a message saying what is missing.
function Face.MakeMeshes
   local tFaceFile, tMapLib, tGrid, tBlank
   put Game.FindFile("LIB_MCP/assets/claude_face_bits.txt") into tFaceFile
   put Game.FindFile("LIB_MAP/livecode/lib_map.livecodescript") into tMapLib
   if tFaceFile is empty then return "FACE: LIB_MCP NOT FOUND"
   if tMapLib is empty then return "FACE: LIB_MAP NOT FOUND"
   start using stack tMapLib
   put URL ("file:" & tFaceFile) into tGrid
   replace numToChar(13) with empty in tGrid
   put tGrid into tBlank
   replace "1" with "0" in tBlank
   Mesh.Define "Face.Bits", Face.SegmentsToMesh(Map.BlockEdges(tGrid, kFaceCell, kFaceHeight, false))
   Mesh.Define "Face.Panel", Face.SegmentsToMesh(Map.BlockEdges(tBlank, kFaceCell, kFaceHeight, true))
   return empty
end Face.MakeMeshes

-- LIB_MAP segments (x1,y1,z1,x2,y2,z2 per line; +Y up, z = height out of the panel)
-- into an engine mesh of wire lines. Engine axes: +Y is down, and the camera looks
-- along +Z, so up becomes -Y and "out of the panel" becomes -Z (toward the viewer).
-- Shared corners are stored once.
function Face.SegmentsToMesh pSegments
   local tMesh, tSeg, tIndex, tA, tB
   put Mesh.New() into tMesh
   set the itemDel to comma
   repeat for each line tSeg in pSegments
      if the number of items of tSeg < 6 then next repeat
      put Face.Vertex(tMesh, tIndex, item 1 of tSeg, item 2 of tSeg, item 3 of tSeg) into tA
      put Face.Vertex(tMesh, tIndex, item 4 of tSeg, item 5 of tSeg, item 6 of tSeg) into tB
      Mesh.AddLine tMesh, tA, tB
   end repeat
   return tMesh
end Face.SegmentsToMesh

function Face.Vertex @pMesh, @pIndex, pX, pY, pZ
   local tKey
   put pX & "," & pY & "," & pZ into tKey
   if pIndex[tKey] is empty then
      Mesh.AddVertex pMesh, pX, -pY, -pZ
      put the result into pIndex[tKey]
   end if
   return pIndex[tKey]
end Face.Vertex

