######################################################################################
## XT3D EDITION OVERRIDES  (11 12 2026)
## tools/make_vibe_xt3d.py appends this to the Vibecode3D engine script. A handler here
## replaces the engine handler of the same name (that one is renamed Vibe.Orig.<name>).
## Everything else is the owner's engine, unchanged: meshes, entities, movement,
## collisions, particles, weapons, HUD text, view presets.
##
## The host (xt3d_testBench_lib_mcp) owns the timer and the drawing:
##   Vibe.Begin rect      once, before dispatching Game.OnStart to the card
##   Vibe.Step            each tick: runs the fixed 33 ms simulation steps that are due
##   Vibe.Frame()         each tick: what to draw (objects in camera space, 2D lines)
## Camera space is the engine's own: +X right, +Y down, +Z forward, so a raylib camera at
## 0,0,0 looking along +Z with up = -Y shows exactly what the LiveCode renderer showed.
######################################################################################

local sVibeRect -- the host view's rect (card coordinates)

## Start a game run in a host view. pRect: the view's rect in card coordinates.
on Vibe.Begin pRect
   put pRect into sVibeRect
   init.globals
   init.locals
   Engine.Init
   Vibe.ApplyRect
   put true into sLoopActive
   put true into bPlaying
   put false into bPaused
   put false into bDeveloper
   View.Init
   Scene.ClearAll
   Particles.Clear
   HUD.Clear
   Collision.ClearRules
   put the milliseconds into sLastMS
   put 0 into sAccumMS
end Vibe.Begin

## After Game.OnStart, like game.loop.start: the game runs from here. (OnStart may have
## reset the engine flags, e.g. App.ResetScene clears bPlaying.)
on Vibe.Go
   put true into bPlaying
   put false into bPaused
   put false into bDeveloper
   put true into sLoopActive
   put the milliseconds into sLastMS
   put 0 into sAccumMS
end Vibe.Go

## The view rect and its centre. Engine.Init and Engine.ResetCamera take them from the
## whole stack window, which here also holds the bench's panel; put them back each tick.
on Vibe.ApplyRect
   if the number of items of sVibeRect is not 4 then exit Vibe.ApplyRect
   put item 1 of sVibeRect into gViewLeft
   put item 2 of sVibeRect into gViewTop
   put item 3 of sVibeRect into gViewRight
   put item 4 of sVibeRect into gViewBottom
   put (gViewLeft + gViewRight) / 2 into CenterX
   put (gViewTop + gViewBottom) / 2 into CenterY
end Vibe.ApplyRect

## The fixed-step part of game.loop.tick, without its drawing or its timer.
on Vibe.Step
   local tNow
   Vibe.ApplyRect
   put the milliseconds into tNow
   if sLastMS is empty then put tNow into sLastMS
   if bPaused then
      put 0 into sAccumMS
   else
      add min(250, tNow - sLastMS) to sAccumMS
      repeat while sAccumMS >= kStepMS and bPlaying
         game.update
         subtract kStepMS from sAccumMS
      end repeat
   end if
   put tNow into sLastMS
end Vibe.Step

## What to draw this frame, as an array:
##   ["objects"]    one line per scene object: mesh tab key tab r,g,b,a tab 12-item xform
##                  (Xform.Object: camera = M * local + T)
##   ["lines2d"][n] graphic points (card coordinates, blank line = pen up) for particles,
##                  weapon and HUD, and ["colors2d"][n] their r,g,b
##   ["background"] r,g,b of the view preset's background
function Vibe.Frame
   local tOut, tEntry, tGraphic, tKey, tXf, tBuf, tName
   Vibe.ApplyRect
   Render.BeginFrame
   repeat for each line tEntry in gSceneObjects
      put word 2 of tEntry into tKey
      put word 3 of tEntry into tGraphic
      if tGraphic is empty then put tKey into tGraphic
      put Xform.Object(tKey) into tXf
      put word 1 of tEntry & tab & tKey & tab & Vibe.Color(tGraphic, item 12 of tXf) & tab & tXf & cr after tOut["objects"]
   end repeat
   Particles.Render tBuf
   Weapon.Render tBuf
   HUD.Render tBuf
   repeat for each key tName in tBuf
      if tBuf[tName] is empty then next repeat
      put tBuf[tName] into tOut["lines2d"][tName]
      put Vibe.Color(tName) into tOut["colors2d"][tName]
   end repeat
   put Color.ToRGB(sView["background"]) into tOut["background"]
   if sView["background"] is empty then put "0,0,0" into tOut["background"]
   return tOut
end Vibe.Frame

## r,g,b,a for a graphic's colour; with a depth pZ, faded by the view's depth bands
## (the LiveCode renderer fades far edges; here the whole object fades by its centre).
function Vibe.Color pGraphic, pZ
   local tRGB, tBand, tAlpha
   if sView["mono"] is not empty then
      put Color.ToRGB(sView["mono"]) into tRGB
   else
      put Color.ToRGB(sOrigColor[pGraphic]) into tRGB
   end if
   put 255 into tAlpha
   if pZ is a number and sViewBands > 1 then
      put 1 + trunc((pZ - sViewNear) * sViewBands / (sViewFar - sViewNear)) into tBand
      put max(1, min(sViewBands, tBand)) into tBand
      put round(255 * (1 - (sView["fade"] + 0) * (tBand - 1) / (sViewBands - 1) / 100)) into tAlpha
      put max(40, min(255, tAlpha)) into tAlpha
   end if
   return tRGB & comma & tAlpha
end Vibe.Color

## A cached mesh (count, vx, vy, vz, ea, eb, edgeCount), for building its xt3d model.
function Vibe.Mesh pName
   local tErr
   try
      return Mesh.Get(pName)
   catch tErr
      return empty
   end try
end Vibe.Mesh

## Projection constants, so the host's camera matches: "focal,scale,moveX,moveY"
function Vibe.Projection
   return gFocalLength & comma & theScale & comma & MOVEX & comma & MOVEY
end Vibe.Projection

function Vibe.Playing
   return bPlaying is true and sLoopActive is true
end Vibe.Playing

## Leaving a game: no cards to go back to here, just stop.
on Game.Exit
   dispatch "Game.OnStop" to this card
   game.loop.stop
   put false into sLoopActive
   put false into bMissile
   SetMouseLook false
end Game.Exit

## Escape stops the game (there is no pause menu card in the host).
on escapekeyDown
   if sLoopActive then Game.Exit
end escapekeyDown

## The look settings only: no cards to colour, no menus, no LiveCode redraw.
on View.Apply
   put max(1, min(4, round(sView["bands"]))) into sViewBands
   put sView["depthNear"] + 0 into sViewNear
   put sView["depthFar"] + 0 into sViewFar
   if sViewFar <= sViewNear then put sViewNear + 1 into sViewFar
   put empty into sStyled
   HUD.Refresh
end View.Apply

## The host draws; the LiveCode renderer must not run.
on game.render
end game.render

on UpdateSelectionMarker
end UpdateSelectionMarker

######################################################################################
## EDITOR HOOKS (Opus 15 Nov 2026, TODO A-86 / A-87; the Vibecode3D editor = Play.Ig3dEditor)
######################################################################################

## A-87: a point on the screen (card coordinates, as the mouse gives them) dropped onto the
## horizontal plane y = pFloorY (engine units, y down). Returns "x z" in world units, or empty
## when the ray misses the plane (looking away from it). Same maths as Weapon.FireAt's hit:
## camera = Rcam * world + T, so a camera-space ray r from the eye is world dir Rcam' r from Rcam' (-T).
function Engine.ScreenToFloor pX, pY, pFloorY
   local tRay, rx, ry, rz, tx, ty, tz, ox, oy, oz, dx, dy, dz, t
   Render.FrameMatrices
   put ScreenToCameraRay(pX, pY, CenterX, CenterY, MOVEX, MOVEY, theScale, gFocalLength) into tRay
   if the number of words of tRay < 3 then return empty
   put word 1 of tRay into rx
   put word 2 of tRay into ry
   put word 3 of tRay into rz
   put -(word 1 of sFrameT) into tx
   put -(word 2 of sFrameT) into ty
   put -(word 3 of sFrameT) into tz
   set the itemDelimiter to comma
   put (item 1 of sCamM) * tx + (item 4 of sCamM) * ty + (item 7 of sCamM) * tz into ox
   put (item 2 of sCamM) * tx + (item 5 of sCamM) * ty + (item 8 of sCamM) * tz into oy
   put (item 3 of sCamM) * tx + (item 6 of sCamM) * ty + (item 9 of sCamM) * tz into oz
   put (item 1 of sCamM) * rx + (item 4 of sCamM) * ry + (item 7 of sCamM) * rz into dx
   put (item 2 of sCamM) * rx + (item 5 of sCamM) * ry + (item 8 of sCamM) * rz into dy
   put (item 3 of sCamM) * rx + (item 6 of sCamM) * ry + (item 9 of sCamM) * rz into dz
   if abs(dy) < 0.000001 then return empty
   put (pFloorY - oy) / dy into t
   if t <= 0 then return empty
   return (ox + t * dx) && (oz + t * dz)
end Engine.ScreenToFloor

## A-86: SKINS. A game defines its placeholder meshes with Mesh.Define as always. When the
## global gV3DSkin names a model for that mesh name (gV3DSkin[name] = a model file), the model's
## wire mesh is used instead, scaled to the placeholder's size. The Game Player fills gV3DSkin
## from LIB_GAMES/Vibecode3D_Games/Skins/<Game>/ACTIVE.txt before Game.OnStart; the editor's
## Edit > Replace With Model... writes those skins. Models: iGame3D .wtf files for now.
on Mesh.Define pName, pMesh
   global gV3DSkin
   local tModel, tR
   if gV3DSkin[pName] is not empty and there is a file gV3DSkin[pName] then
      put Mesh.Finalize(pMesh) into tR
      put Skin.WTFMesh(gV3DSkin[pName], max(1, tR["radius"])) into tModel
      if tModel["count"] > 0 then put tModel into pMesh
   end if
   Vibe.Orig.Mesh.Define pName, pMesh
end Mesh.Define

## An iGame3D .wtf model as a wire mesh: its #Vertices (x,y,z,bone) and #Edges (a,b from 0),
## centred, scaled so its bounding radius is pRadius; iGame3D's y is up, the engine's is down.
function Skin.WTFMesh pPath, pRadius
   local tText, n, tCount, i, tLine, tM, cx, cy, cz, tR2, tD2, k, tVX, tVY, tVZ
   put Mesh.New() into tM
   put textDecode(url ("binfile:" & pPath), "UTF-8") into tText
   replace numToCodepoint(13) with empty in tText
   put lineOffset("#Vertices:", tText) into n
   if n is 0 then return tM
   put line n + 1 of tText into tCount
   if tCount is not an integer then return tM
   set the itemDelimiter to comma
   put 0 into cx
   put 0 into cy
   put 0 into cz
   repeat with i = 1 to tCount
      put line n + 1 + i of tText into tLine
      put item 1 of tLine + 0 into tVX[i]
      put -(item 2 of tLine + 0) into tVY[i]
      put item 3 of tLine + 0 into tVZ[i]
      add tVX[i] to cx
      add tVY[i] to cy
      add tVZ[i] to cz
   end repeat
   put cx / tCount into cx
   put cy / tCount into cy
   put cz / tCount into cz
   put 0 into tR2
   repeat with i = 1 to tCount
      put (tVX[i] - cx) ^ 2 + (tVY[i] - cy) ^ 2 + (tVZ[i] - cz) ^ 2 into tD2
      if tD2 > tR2 then put tD2 into tR2
   end repeat
   put pRadius / max(0.000001, sqrt(tR2)) into k
   repeat with i = 1 to tCount
      Mesh.AddVertex tM, (tVX[i] - cx) * k, (tVY[i] - cy) * k, (tVZ[i] - cz) * k
   end repeat
   put lineOffset("#Edges:", tText) into n
   if n > 0 then
      put line n + 1 of tText into tCount
      if tCount is an integer then
         repeat with i = 1 to tCount
            put line n + 1 + i of tText into tLine
            put (item 1 of tLine + 1) && (item 2 of tLine + 1) & return after tM["lines"]
         end repeat
      end if
   end if
   return tM
end Skin.WTFMesh

## Vector Toss banter needs three more HUD glyphs: ? , and ' (Opus 15 Nov 2026).
on VectorText.Init
   Vibe.Orig.VectorText.Init
   put "01 10 30 41 42 23 24|25 26" into sFont["?"]
   put "25 26 16" into sFont[","]
   put "20 21" into sFont["'"]
end VectorText.Init
