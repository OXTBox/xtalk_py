######################################################################################
## CARD SCRIPT: "Play.Simple_Test1"   SPINNING CUBE  (11 12 2026)
## The standard first test: one wireframe cube turning over a floor grid. If this
## runs, meshes, entities, rotation, colours, the HUD and the loop all work.
## (Replaces an old copy of the engine's own card variables, which had no game.)
## CONTROLS  click: reverse the spin    Escape: back to Developer
######################################################################################

global gObjectTransforms, gSceneObjects
global bPaused, bPlaying

local sStepMS = 33, sCubeKey, sFloorKey, sDir = 1, sTicks = 0

constant kCubeSize = 160   -- world units along each edge
constant kCubeDist = 600   -- in front of the camera (at 0,0,0 after Engine.ResetCamera)
constant kSpinX = 0.011    -- radians per 33 ms step
constant kSpinY = 0.023

on Game.OnStart
   Engine.ResetCamera
   put Engine.Info("stepMS") into sStepMS
   Scene.ClearAll
   Particles.Clear
   HUD.Clear
   Collision.ClearRules
   put 0 into sTicks
   put 1 into sDir
   Mesh.Define "Cube.Box", MeshBox(kCubeSize, kCubeSize, kCubeSize)
   Mesh.Define "Cube.Floor", MeshGrid(10, 10, 60)
   -- +Y is down: the floor sits below the cube
   put Entity.Spawn("Cube.Floor", 0, kCubeSize, kCubeDist, "#2E6F8E") into sFloorKey
   put Entity.Spawn("Cube.Box", 0, 0, kCubeDist, "cyan") into sCubeKey
   Cube.Spin
   HUD.Set "Cube.Title", "SPINNING CUBE", 20, 20, 14
   HUD.Set "Cube.Help", "CLICK TO REVERSE", 20, 44, 10
end Game.OnStart

on Game.OnUpdate
   add 1 to sTicks
end Game.OnUpdate

on Game.OnClick pX,pY,pButton
   put -sDir into sDir
   Cube.Spin
end Game.OnClick

on Cube.Spin
   if sCubeKey is not empty then SetObjectRotationSpeed sCubeKey, kSpinX * sDir, kSpinY * sDir, 0
end Cube.Spin

on Game.OnKill pKey,pX,pY,pZ
end Game.OnKill

on Game.OnPause
end Game.OnPause

on Game.OnResume
end Game.OnResume

on Game.OnStop
   HUD.Remove "Cube.Title"
   HUD.Remove "Cube.Help"
end Game.OnStop

on Collision.Hit pA,pB
end Collision.Hit
