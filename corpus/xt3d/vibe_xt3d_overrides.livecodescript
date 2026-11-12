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
