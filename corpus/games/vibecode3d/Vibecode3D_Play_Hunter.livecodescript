## CARD SCRIPT: "Play.Hunter"   GEM HUNTER (first person)  (11 09 2026)
## Pac-Man meets Halo: walk rolling vector terrain, crack rocks to free the gems
## hidden inside, grab them before the enemies dive in and smash them.
##
## CONTROLS
##   mouse          look (the pointer is held at the centre: that's your crosshair)
##   W A S D/arrows move        Shift  sprint        Space  jump
##   LEFT click     grab a gem (or crack a rock you're standing next to)
##   RIGHT click    shoot, one shot per click, 12 per clip
##   R              reload        Escape  pause menu (again: Developer card)
##
## RULES
##   Every rock hides a gem. Shoot it (2 hits) or crack it up close with left clicks:
##   the gem pops out, flies up and lands nearby. Left-click it to bank it.
##   Enemies (the Canyon's shapes) come from above. Some hunt you, some go for the
##   gems lying around: shoot them first. Your shield recharges after a short rest
##   (Halo); when it breaks you lose a life. Bank every gem to clear the level.
##
## Paste into the script of card "Play.Hunter" (setup.games "Hunter" makes the card).
## The engine sends: Game.OnStart Game.OnUpdate Game.OnClick Game.OnKill Game.OnStop
## and Collision.Hit. World: +X right, +Y DOWN (up is -Y), +Z forward at yaw 0.
######################################################################################

global gObjectTransforms
global gSceneObjects
global gCameraYaw
global gCameraPitch
global gViewLeft,gViewTop,gViewRight,gViewBottom
global CenterX,CenterY
global bPaused,bPlaying -- engine flags (globals, so the card can set them)

constant kMaxAmmo = 12
constant kReloadTicks = 45 -- 1.5 s
constant kEyeHeight = 70
constant kMouseSens = 0.0035

-- Terrain
local sGridN = 8, sGridS = 170, sHalf, sH, sPh1, sPh2, sPh3
-- Player
local sPX = 0, sPZ = 0, sFootY = 0, sVY = 0, sOnGround = true, sMouseReady = false
local sShield = 100, sShieldDelay = 0, sInvuln = 0, sLives = 3
local sAmmo = 12, sReloadTicks = 0
-- Game
local sStepMS = 33, sTicks = 0, sLevel = 1, sGems = 0, sValue = 0, sKills = 0
local sRocks, sRockGem, sRockPos, sAirGems, sGroundGems, sEnemies
local sMsgTicks = 0, sGameOverTicks = 0, sHudAmmo, sHudShield, sHudGems


## ---------------------------------------------------------------- START / STOP

on Game.OnStart
   Engine.ResetCamera
   put Engine.Info("stepMS") into sStepMS
   Scene.ClearAll
   Particles.Clear
   HUD.Clear
   Collision.ClearRules
   delete variable gObjectTransforms["Player"]

   Hunter.MakeMeshes
   Hunter.MakeTerrain
   Scene.AddObject "Terrain","TerrainLine",0,0,0,"#3A7D44"

   put 1 into sLevel
   put 3 into sLives
   put 0 into sGems
   put 0 into sValue
   put 0 into sKills
   put 0 into sTicks
   put 0 into sGameOverTicks
   put empty into sEnemies
   put empty into sAirGems
   put empty into sGroundGems
   Hunter.Respawn
   Hunter.SpawnRocks

   Collision.AddRule "bullet","player"
   Collision.AddRule "enemy","player"
   Collision.SetGroup "Player","player",28

   -- The pointer becomes the crosshair and is held at the centre.
   set the lockCursor to true
   set the cursor to cross
   put false into sMouseReady
   Hunter.CenterMouse

   put empty into sHudAmmo
   put empty into sHudShield
   put empty into sHudGems
   HUD.Set "cross","+",round(CenterX) - 6,round(CenterY) - 6,12
   Hunter.ShowHUD
   Hunter.Message "FIND THE GEMS",60
end Game.OnStart

on Game.OnStop
   Hunter.ReleaseMouse
   HUD.Remove "msg"
end Game.OnStop

## Pause menu: give the mouse back. Resume: take it again (no jump on the first step).
on Game.OnPause
   Hunter.ReleaseMouse
end Game.OnPause

on Game.OnResume
   set the lockCursor to true
   set the cursor to cross
   put false into sMouseReady
end Game.OnResume

on Hunter.ReleaseMouse
   set the lockCursor to false
   put false into sMouseReady
end Hunter.ReleaseMouse

on Reselect.browse
   choose "browse tool"
end Reselect.browse

## Back to the start point with a full shield.
on Hunter.Respawn
   put 0 into sPX
   put -sHalf * 0.6 into sPZ
   put Hunter.HeightAt(sPX,sPZ) into sFootY
   put 0 into sVY
   put true into sOnGround
   put 0 into gCameraYaw
   put 0 into gCameraPitch
   put 100 into sShield
   put 0 into sShieldDelay
   put 60 into sInvuln
   put kMaxAmmo into sAmmo
   put 0 into sReloadTicks
end Hunter.Respawn


## ---------------------------------------------------------------- MESHES

on Hunter.MakeMeshes
   Mesh.Define "Rock", MeshPyramid(5,30,50)
   Mesh.Define "Rock4", MeshPyramid(4,36,40)
   Mesh.Define "HBullet", Hunter.BulletMesh()
   -- Gems (about 25 units across so they read at a distance).
   -- Diamond: short crown on top, tall pavilion below.
   put Mesh.Transform(MeshPyramid(8,13,7),0,0,0,0,-3.5,0,1) into tM
   Mesh.Define "Gem.Diamond", Mesh.Merge(tM, Mesh.Transform(MeshPyramid(8,13,17),pi,0,0,0,8.5,0,1))
   Mesh.Define "Gem.Sapphire", MeshSphere(12,2,6)
   put Mesh.Transform(MeshPyramid(6,9,8),0,0,0,0,-13,0,1) into tM
   put Mesh.Merge(tM, MeshPrism(6,9,18)) into tM
   Mesh.Define "Gem.Ruby", Mesh.Merge(tM, Mesh.Transform(MeshPyramid(6,9,8),pi,0,0,0,13,0,1))
   Mesh.Define "Gem.Emerald", MeshPrism(8,13,9)
   put Mesh.Transform(MeshPyramid(4,10,14),0,0,0,0,-7,0,1) into tM
   Mesh.Define "Gem.Amethyst", Mesh.Merge(tM, Mesh.Transform(MeshPyramid(4,10,14),pi,0,0,0,7,0,1))
   Mesh.Define "Gem.Topaz", MeshSphere(11,3,5)
   Hunter.MakeEnemyMeshes
end Hunter.MakeMeshes

## name,colour,value,weight (rarer = lower weight).
function Hunter.GemTypes
   return "Diamond,#E8F8FF,500,1" & cr & "Sapphire,#3A7BFF,300,2" & cr & \
         "Ruby,#FF2A4A,250,3" & cr & "Emerald,#22FF88,200,3" & cr & \
         "Amethyst,#B455FF,150,4" & cr & "Topaz,#FFC21A,100,5"
end Hunter.GemTypes

function Hunter.RandomGem
   put 0 into tTotal
   repeat for each line tL in Hunter.GemTypes()
      add item 4 of tL to tTotal
   end repeat
   put random(tTotal) into tPick
   repeat for each line tL in Hunter.GemTypes()
      subtract item 4 of tL from tPick
      if tPick <= 0 then return item 1 of tL
   end repeat
   return "Topaz"
end Hunter.RandomGem

function Hunter.GemInfo pName
   repeat for each line tL in Hunter.GemTypes()
      if item 1 of tL is pName then return tL
   end repeat
   return "Topaz,#FFC21A,100,5"
end Hunter.GemInfo

function Hunter.BulletMesh
   put Mesh.New() into tM
   Mesh.AddVertex tM,-6,0,0
   Mesh.AddVertex tM,6,0,0
   Mesh.AddVertex tM,0,-6,0
   Mesh.AddVertex tM,0,6,0
   Mesh.AddVertex tM,0,0,-6
   Mesh.AddVertex tM,0,0,6
   Mesh.AddLine tM,1,2
   Mesh.AddLine tM,3,4
   Mesh.AddLine tM,5,6
   return tM
end Hunter.BulletMesh

## The Canyon's 20 random enemy shapes ("HEnemy1".."HEnemy20"), a bit bigger.
on Hunter.MakeEnemyMeshes
   repeat with n = 1 to 20
      put (12 + random(14)) * 1.4 into r
      switch random(4)
         case 1
            put Mesh.Transform(MeshPrism(2 + random(6), r, r * 0.6),pi/2,0,0,0,0,0,1) into tM
            break
         case 2
            put MeshPyramid(2 + random(6), r, r * 1.4) into tM
            break
         case 3
            put MeshSphere(r, 2 + random(2), 3 + random(5)) into tM
            break
         default
            put 2 + random(5) into tSides
            put Mesh.Transform(MeshPyramid(tSides, r, r),0,0,0,0,-r/2,0,1) into tM
            put Mesh.Merge(tM, Mesh.Transform(MeshPyramid(tSides, r, r),pi,0,0,0,r/2,0,1)) into tM
      end switch
      Mesh.Define "HEnemy" & n, tM
   end repeat
end Hunter.MakeEnemyMeshes

function Hunter.Palette
   return "#D02090,#FF0000,#FF4500,#FFA500,#FFFF00,#7CFC00,#32CD32,#00FF00,#00FFFF,#6495ED," & \
         "#1E90FF,#3399FF,#FF00FF,#00FF7F,#FFC0CB,#FF69B4,#00F5FF,#87CEEB,#E6E6FA,#FFFFFF"
end Hunter.Palette


## ---------------------------------------------------------------- TERRAIN
## A MeshGrid with rolling heights. The heights are kept (sH, by vertex) so
## Hunter.HeightAt matches exactly what is drawn.

on Hunter.MakeTerrain
   put sGridN * sGridS / 2 into sHalf
   put random(628) / 100 into sPh1
   put random(628) / 100 into sPh2
   put random(628) / 100 into sPh3
   put MeshGrid(sGridN,sGridN,sGridS) into tM
   put empty into sH
   repeat with i = 1 to tM["count"]
      put tM["vx"][i] into x
      put tM["vz"][i] into z
      put 38 * sin(x * 0.0045 + sPh1) * cos(z * 0.0052 + sPh2) + 18 * sin((x - z) * 0.009 + sPh3) \
            + (random(13) - 7) into h
      put h into sH[i]
      put h into tM["vy"][i]
   end repeat
   Mesh.Define "Terrain", tM
end Hunter.MakeTerrain

## Ground height (y, down is +) at x,z: bilinear between the grid points.
function Hunter.HeightAt pX,pZ
   put (pX + sHalf) / sGridS into fx
   put (pZ + sHalf) / sGridS into fz
   put max(0, min(sGridN - 0.0001, fx)) into fx
   put max(0, min(sGridN - 0.0001, fz)) into fz
   put trunc(fx) into c
   put trunc(fz) into r
   put fx - c into t
   put fz - r into u
   put sGridN + 1 into w
   put r * w + c + 1 into i00
   return (sH[i00] * (1 - t) + sH[i00 + 1] * t) * (1 - u) + (sH[i00 + w] * (1 - t) + sH[i00 + w + 1] * t) * u
end Hunter.HeightAt


## ---------------------------------------------------------------- ROCKS & GEMS

on Hunter.SpawnRocks
   put empty into sRocks
   put empty into sRockGem
   put empty into sRockPos
   put min(24, 12 + sLevel * 2) into tCount
   repeat tCount times
      repeat 20 times
         put random(round(sHalf * 2 - 160)) - round(sHalf - 80) into x
         put random(round(sHalf * 2 - 160)) - round(sHalf - 80) into z
         if sqrt((x - sPX)^2 + (z - sPZ)^2) > 180 then exit repeat
      end repeat
      if random(2) = 1 then
         put "Rock" into tMesh
         put 25 into tHalfH
      else
         put "Rock4" into tMesh
         put 20 into tHalfH
      end if
      put Entity.Spawn(tMesh, x, Hunter.HeightAt(x,z) - tHalfH + 4, z, "orange") into tId
      SetObjectRotation tId,0,random(628)/100,0
      put 2 into gObjectTransforms[tId]["hp"]
      put Hunter.RandomGem() into sRockGem[tId]
      put x & comma & z into sRockPos[tId]
      put tId & cr after sRocks
   end repeat
end Hunter.SpawnRocks

## The gem flies up out of the broken rock and lands somewhere close by.
on Hunter.PopGem pRock
   put sRockGem[pRock] into tName
   if tName is empty then put Hunter.RandomGem() into tName
   put sRockPos[pRock] into tPos
   put item 1 of tPos into x
   put item 2 of tPos into z
   put Hunter.GemInfo(tName) into tInfo
   put Entity.Spawn("Gem." & tName, x, Hunter.HeightAt(x,z) - 30, z, item 2 of tInfo) into tId
   SetObjectRotationSpeed tId,0,0.08,0
   put item 3 of tInfo into gObjectTransforms[tId]["value"]
   put tName into gObjectTransforms[tId]["gemName"]
   -- Pop: up, and out in a random direction.
   put random(628) / 100 into a
   put (20 + random(15)) / 10 into tOut
   put cos(a) * tOut into gObjectTransforms[tId]["gvx"]
   put sin(a) * tOut into gObjectTransforms[tId]["gvz"]
   put -(7 + random(3)) into gObjectTransforms[tId]["gvy"]
   put tId & cr after sAirGems
   delete variable sRockGem[pRock]
   delete variable sRockPos[pRock]
   Sound.Play "Warp"
end Hunter.PopGem

## Flying gems fall and land; landed gems bob (Scene.SetBob).
on Hunter.UpdateGems
   put empty into tStill
   repeat for each line tId in sAirGems
      if gObjectTransforms[tId] is not an array then next repeat
      add 0.45 to gObjectTransforms[tId]["gvy"]
      put gObjectTransforms[tId]["x"] + gObjectTransforms[tId]["gvx"] into x
      put gObjectTransforms[tId]["z"] + gObjectTransforms[tId]["gvz"] into z
      put max(-sHalf + 20, min(sHalf - 20, x)) into x
      put max(-sHalf + 20, min(sHalf - 20, z)) into z
      put gObjectTransforms[tId]["y"] + gObjectTransforms[tId]["gvy"] into y
      put Hunter.HeightAt(x,z) - 16 into tGround
      put x into gObjectTransforms[tId]["x"]
      put z into gObjectTransforms[tId]["z"]
      if y >= tGround and gObjectTransforms[tId]["gvy"] > 0 then
         put tGround into gObjectTransforms[tId]["y"]
         Scene.SetBob tId,3,0.12,0.08
         put tId & cr after sGroundGems
      else
         put y into gObjectTransforms[tId]["y"]
         put tId & cr after tStill
      end if
   end repeat
   put tStill into sAirGems
end Hunter.UpdateGems

on Hunter.CollectGem pId
   if gObjectTransforms[pId] is not an array then exit Hunter.CollectGem
   add 1 to sGems
   add gObjectTransforms[pId]["value"] to sValue
   put Hunter.GemInfo(gObjectTransforms[pId]["gemName"]) into tInfo
   FX.Sparks gObjectTransforms[pId]["x"],gObjectTransforms[pId]["y"],gObjectTransforms[pId]["z"],8,item 2 of tInfo
   Entity.Kill pId
   Hunter.Message toUpper(item 1 of tInfo) && "+" & item 3 of tInfo,20
   Sound.Play "Warp"
   Hunter.ShowHUD
end Hunter.CollectGem


## ---------------------------------------------------------------- EVERY STEP

on Game.OnUpdate
   add 1 to sTicks
   Hunter.Look
   Hunter.Move
   Hunter.UpdateGems
   Hunter.UpdateEnemies
   Hunter.UpdatePlayerState

   -- Level clear: no rocks left and no gems anywhere.
   if sTicks mod 15 = 0 then Hunter.CheckLevel

   if sMsgTicks > 0 then
      subtract 1 from sMsgTicks
      if sMsgTicks = 0 then HUD.Remove "msg"
   end if
   if sGameOverTicks > 0 then
      subtract 1 from sGameOverTicks
      if sGameOverTicks = 0 then Hunter.EndGame
   end if
end Game.OnUpdate

## Mouse look: how far the pointer moved from the centre, then put it back.
## Only while this stack is the front window: an error dialog or the IDE taking
## focus must never have its pointer dragged back to the game.
on Hunter.Look
   if the short name of the topStack is not the short name of this stack then
      put false into sMouseReady
      exit Hunter.Look
   end if
   put the mouseLoc into tM
   if sMouseReady then
      put (item 1 of tM) - round(CenterX) into dx
      put (item 2 of tM) - round(CenterY) into dy
      -- A huge jump means the pointer was elsewhere (pause menu, another window).
      if abs(dx) > 250 or abs(dy) > 250 then
         put 0 into dx
         put 0 into dy
      end if
      add dx * kMouseSens to gCameraYaw
      put max(-1.35, min(1.35, gCameraPitch - dy * kMouseSens)) into gCameraPitch
   end if
   Hunter.CenterMouse
   put true into sMouseReady
end Hunter.Look

on Hunter.CenterMouse
   set the screenMouseLoc to globalLoc(round(CenterX) & comma & round(CenterY))
end Hunter.CenterMouse

## WASD / arrows, sprint, jump, reload, and staying out of the rocks.
on Hunter.Move
   put the keysDown into tKeys
   put 0 into tF
   put 0 into tS
   
   # Must escape the cursor lock, errors lock our focus in revEditorStack
   if 65307 is among the items of tKeys then
      Hunter.ReleaseMouse
      put true into bPaused
      put false into bPlaying
      choose "pointer tool"
      --  maybe clearing pending messages instead? (game.loop.tick stops itself
      --  when bPlaying is false, so no tick is left pending)
      send "Reselect.browse" to me in 600 milliseconds
      exit Hunter.Move
   end if
   if 119 is among the items of tKeys or 87 is among the items of tKeys or 65362 is among the items of tKeys then add 1 to tF
   if 115 is among the items of tKeys or 83 is among the items of tKeys or 65364 is among the items of tKeys then subtract 1 from tF
   if 100 is among the items of tKeys or 68 is among the items of tKeys or 65363 is among the items of tKeys then add 1 to tS
   if 97 is among the items of tKeys or 65 is among the items of tKeys or 65361 is among the items of tKeys then subtract 1 from tS
   put 5.5 into tSpeed
   if 65505 is among the items of tKeys or 65506 is among the items of tKeys then put 9 into tSpeed
   if tF is not 0 and tS is not 0 then multiply tSpeed by 0.7071

   -- Forward and right on the ground, from the yaw.
   put sin(gCameraYaw) into fx
   put cos(gCameraYaw) into fz
   add (fx * tF + fz * tS) * tSpeed to sPX
   add (fz * tF - fx * tS) * tSpeed to sPZ
   put max(-sHalf + 30, min(sHalf - 30, sPX)) into sPX
   put max(-sHalf + 30, min(sHalf - 30, sPZ)) into sPZ

   -- Rocks are solid: push out.
   repeat for each line tId in sRocks
      put sRockPos[tId] into tPos
      if tPos is empty then next repeat
      put sPX - item 1 of tPos into dx
      put sPZ - item 2 of tPos into dz
      put sqrt(dx*dx + dz*dz) into d
      if d < 48 and d > 0.01 then
         put item 1 of tPos + dx / d * 48 into sPX
         put item 2 of tPos + dz / d * 48 into sPZ
      end if
   end repeat

   -- Jump and gravity (+Y is down).
   put Hunter.HeightAt(sPX,sPZ) into tGround
   if sOnGround then
      put tGround into sFootY
      if 32 is among the items of tKeys then
         put -9 into sVY
         put false into sOnGround
      end if
   else
      add 0.6 to sVY
      add sVY to sFootY
      if sFootY >= tGround then
         put tGround into sFootY
         put 0 into sVY
         put true into sOnGround
      end if
   end if

   -- Reload.
   if (114 is among the items of tKeys or 82 is among the items of tKeys) and sReloadTicks = 0 and sAmmo < kMaxAmmo then
      put kReloadTicks into sReloadTicks
      Sound.Play "Bullet"
      Hunter.ShowHUD
   end if

   -- The camera is the player's eyes; the "Player" collision sphere follows.
   put sFootY - kEyeHeight into tEyeY
   Engine.SetCam -sPX, -tEyeY, -sPZ
   put sPX into gObjectTransforms["Player"]["x"]
   put tEyeY + 25 into gObjectTransforms["Player"]["y"]
   put sPZ into gObjectTransforms["Player"]["z"]
end Hunter.Move

on Hunter.UpdatePlayerState
   if sInvuln > 0 then subtract 1 from sInvuln
   -- Halo: the shield recharges after 3 seconds without damage.
   if sShieldDelay > 0 then
      subtract 1 from sShieldDelay
   else if sShield < 100 then
      put min(100, sShield + 1) into sShield
   end if
   if sReloadTicks > 0 then
      subtract 1 from sReloadTicks
      if sReloadTicks = 0 then put kMaxAmmo into sAmmo
   end if
   Hunter.ShowHUD
end Hunter.UpdatePlayerState


## ---------------------------------------------------------------- CLICKS

## Left = grab a gem / crack a nearby rock. Right = shoot.
on Game.OnClick pX,pY,pButton
   if sGameOverTicks > 0 then exit Game.OnClick
   if pButton is 3 then
      Hunter.Shoot
   else
      Hunter.Grab
   end if
end Game.OnClick

on Hunter.Shoot
   if sReloadTicks > 0 then exit Hunter.Shoot
   if sAmmo <= 0 then
      Hunter.Message "RELOAD - R",30
      exit Hunter.Shoot
   end if
   subtract 1 from sAmmo
   Sound.Play "PlayerLaser"
   -- The engine's hitscan laser through the crosshair (Game.OnKill on a kill).
   Weapon.FireAt round(CenterX), round(CenterY)
   Hunter.ShowHUD
end Hunter.Shoot

## The engine's laser destroyed something.
on Game.OnKill pKey
   if pKey begins with "Rock" then
      Hunter.PopGem pKey
      Hunter.ForgetRock pKey
   else if pKey begins with "HEnemy" then
      add 1 to sKills
      Sound.Play "Explode"
      Hunter.ShowHUD
   end if
end Game.OnKill

on Hunter.Grab
   -- What is under the crosshair? (ray straight out of the camera: 0,0,1)
   put RayCastScene(gSceneObjects,0,0,1) into tHit
   put word 2 of tHit into tKey
   put word 3 of tHit into tDist
   if tKey begins with "Gem." and tDist < 320 then
      Hunter.CollectGem tKey
      exit Hunter.Grab
   end if
   if tKey begins with "Rock" and tDist < 170 then
      -- Crack it by hand.
      subtract 1 from gObjectTransforms[tKey]["hp"]
      put Hunter.ForwardPoint(tDist) into tP
      FX.Sparks item 1 of tP,item 2 of tP,item 3 of tP,5,"orange"
      if gObjectTransforms[tKey]["hp"] <= 0 then
         FX.Destroy tKey
         Hunter.PopGem tKey
         Hunter.ForgetRock tKey
      end if
      exit Hunter.Grab
   end if
   -- Missed: grab the closest landed gem within arm's reach anyway.
   put empty into tBest
   put 95 into tBestD
   repeat for each line tId in sGroundGems
      if gObjectTransforms[tId] is not an array then next repeat
      put sqrt((gObjectTransforms[tId]["x"] - sPX)^2 + (gObjectTransforms[tId]["z"] - sPZ)^2) into d
      if d < tBestD then
         put d into tBestD
         put tId into tBest
      end if
   end repeat
   if tBest is not empty then Hunter.CollectGem tBest
end Hunter.Grab

on Hunter.ForgetRock pKey
   put empty into tKeep
   repeat for each line tId in sRocks
      if tId is not pKey then put tId & cr after tKeep
   end repeat
   put tKeep into sRocks
end Hunter.ForgetRock

## The world point pDist along the crosshair.
function Hunter.ForwardPoint pDist
   put cos(gCameraPitch) into cp
   put (sFootY - kEyeHeight) - sin(gCameraPitch) * pDist into y
   return (sPX + sin(gCameraYaw) * cp * pDist) & comma & y & comma & (sPZ + cos(gCameraYaw) * cp * pDist)
end Hunter.ForwardPoint


## ---------------------------------------------------------------- ENEMIES
## Same shapes as the Canyon, more aggressive, and from above. Some hunt you;
## raiders dive at gems lying on the ground and smash them.

on Hunter.UpdateEnemies
   put empty into tAlive
   repeat for each line tId in sEnemies
      if gObjectTransforms[tId] is an array then put tId & cr after tAlive
   end repeat
   put tAlive into sEnemies
   put empty into tGems
   repeat for each line tId in sGroundGems
      if gObjectTransforms[tId] is an array then put tId & cr after tGems
   end repeat
   put tGems into sGroundGems

   if sGameOverTicks = 0 and the number of lines of sEnemies < 2 + sLevel and random(100) <= 2 + sLevel then
      Hunter.SpawnEnemy
   end if
   repeat for each line tId in sEnemies
      Hunter.MoveEnemy tId
   end repeat
end Hunter.UpdateEnemies

on Hunter.SpawnEnemy
   put random(20) into n
   put random(628) / 100 into a
   put 900 + random(300) into r
   put sPX + cos(a) * r into x
   put sPZ + sin(a) * r into z
   put Hunter.HeightAt(x,z) - (350 + random(250)) into y
   put item n of Hunter.Palette() into tColor
   put Entity.Spawn("HEnemy" & n, x, y, z, tColor) into tId
   SetObjectRotationSpeed tId,(random(21)-11)/200,(random(21)-11)/200,(random(21)-11)/200
   put 2 into gObjectTransforms[tId]["hp"]
   put 3 + random(3) + sLevel * 0.5 into gObjectTransforms[tId]["spd"]
   put 4 + random(6) into gObjectTransforms[tId]["dests"]
   put 20 + random(40) into gObjectTransforms[tId]["fireCool"]
   put "hunt" into gObjectTransforms[tId]["mode"]
   Collision.SetGroup tId,"enemy"
   Hunter.EnemyNewDest tId
   put tId & cr after sEnemies
   Sound.Play "Enemy"
end Hunter.SpawnEnemy

## Next target: a gem to raid (if one lies near you and nobody has it), a point above
## you to attack from, or (out of destinations) away into the sky.
on Hunter.EnemyNewDest pId
   if gObjectTransforms[pId]["dests"] <= 0 then
      put "leave" into gObjectTransforms[pId]["mode"]
      put gObjectTransforms[pId]["x"] + random(1200) - 600 into gObjectTransforms[pId]["tx"]
      put -1200 into gObjectTransforms[pId]["ty"]
      put gObjectTransforms[pId]["z"] + random(1200) - 600 into gObjectTransforms[pId]["tz"]
      exit Hunter.EnemyNewDest
   end if
   subtract 1 from gObjectTransforms[pId]["dests"]

   if random(100) <= 35 + sLevel * 5 then
      repeat for each line tGem in sGroundGems
         if gObjectTransforms[tGem] is not an array then next repeat
         if sqrt((gObjectTransforms[tGem]["x"] - sPX)^2 + (gObjectTransforms[tGem]["z"] - sPZ)^2) > 800 then next repeat
         if Hunter.GemTargeted(tGem) then next repeat
         put "raid" into gObjectTransforms[pId]["mode"]
         put tGem into gObjectTransforms[pId]["target"]
         exit Hunter.EnemyNewDest
      end repeat
   end if

   put "hunt" into gObjectTransforms[pId]["mode"]
   put random(628) / 100 into a
   put 150 + random(300) into r
   put sPX + cos(a) * r into tx
   put sPZ + sin(a) * r into tz
   put tx into gObjectTransforms[pId]["tx"]
   put tz into gObjectTransforms[pId]["tz"]
   put Hunter.HeightAt(tx,tz) - (120 + random(250)) into gObjectTransforms[pId]["ty"]
end Hunter.EnemyNewDest

function Hunter.GemTargeted pGem
   repeat for each line tId in sEnemies
      if gObjectTransforms[tId]["target"] is pGem and gObjectTransforms[tId]["mode"] is "raid" then return true
   end repeat
   return false
end Hunter.GemTargeted

on Hunter.MoveEnemy pId
   put gObjectTransforms[pId]["mode"] into tMode
   put gObjectTransforms[pId]["spd"] into tSpd
   if tMode is "raid" then
      put gObjectTransforms[pId]["target"] into tGem
      if gObjectTransforms[tGem] is not an array then
         -- Somebody got it first.
         Hunter.EnemyNewDest pId
         exit Hunter.MoveEnemy
      end if
      put gObjectTransforms[tGem]["x"] into gObjectTransforms[pId]["tx"]
      put gObjectTransforms[tGem]["y"] into gObjectTransforms[pId]["ty"]
      put gObjectTransforms[tGem]["z"] into gObjectTransforms[pId]["tz"]
      multiply tSpd by 1.5
   end if

   put gObjectTransforms[pId]["x"] into x
   put gObjectTransforms[pId]["y"] into y
   put gObjectTransforms[pId]["z"] into z
   put gObjectTransforms[pId]["tx"] - x into dx
   put gObjectTransforms[pId]["ty"] - y into dy
   put gObjectTransforms[pId]["tz"] - z into dz
   put sqrt(dx*dx + dy*dy + dz*dz) into tDist

   if tDist <= max(tSpd, 22) then
      if tMode is "raid" then
         -- Smash the gem.
         FX.Destroy tGem
         Hunter.Message "GEM LOST",30
         Hunter.EnemyNewDest pId
      else if tMode is "leave" then
         Entity.Kill pId
         exit Hunter.MoveEnemy
      else
         Hunter.EnemyNewDest pId
      end if
   else
      put x + dx / tDist * tSpd into gObjectTransforms[pId]["x"]
      put y + dy / tDist * tSpd into gObjectTransforms[pId]["y"]
      put z + dz / tDist * tSpd into gObjectTransforms[pId]["z"]
   end if

   -- Hunters shoot at you when close enough.
   if tMode is not "hunt" or sGameOverTicks > 0 then exit Hunter.MoveEnemy
   if sqrt((x - sPX)^2 + (z - sPZ)^2) > 1000 then exit Hunter.MoveEnemy
   subtract 1 from gObjectTransforms[pId]["fireCool"]
   if gObjectTransforms[pId]["fireCool"] <= 0 then
      put max(15, 55 - sLevel * 5) + random(30) into gObjectTransforms[pId]["fireCool"]
      Hunter.FireBullet x,y,z
   end if
end Hunter.MoveEnemy

on Hunter.FireBullet pX,pY,pZ
   put sPX + random(31) - 16 - pX into dx
   put (sFootY - kEyeHeight + 20) - pY into dy
   put sPZ + random(31) - 16 - pZ into dz
   put sqrt(dx*dx + dy*dy + dz*dz) into tLen
   if tLen < 1 then exit Hunter.FireBullet
   put 9 + sLevel into tSpd
   put Entity.Spawn("HBullet",pX,pY,pZ,"#FF5050") into tId
   SetObjectVelocity tId,dx / tLen * tSpd,dy / tLen * tSpd,dz / tLen * tSpd
   SetObjectRotationSpeed tId,0.2,0.3,0
   put 160 into gObjectTransforms[tId]["ttl"]
   Collision.SetGroup tId,"bullet",9
   Sound.Play "Bullet"
end Hunter.FireBullet


## ---------------------------------------------------------------- DAMAGE

## Bullets and enemies that reach the player (rules: bullet/player, enemy/player).
on Collision.Hit pA,pB
   if pA is "Player" then
      put pB into tOther
   else
      put pA into tOther
   end if
   if tOther is "Player" then exit Collision.Hit
   if gObjectTransforms[tOther]["group"] is "enemy" then
      FX.Destroy tOther
      Hunter.Damage 35
   else
      Entity.Kill tOther
      Hunter.Damage 12
   end if
end Collision.Hit

on Hunter.Damage pAmount
   if sInvuln > 0 or sGameOverTicks > 0 then exit Hunter.Damage
   subtract pAmount from sShield
   put 90 into sShieldDelay
   Sound.Play "PlayerCrash"
   if sShield < 0 then
      subtract 1 from sLives
      FX.Sparks sPX,sFootY - kEyeHeight,sPZ,16,"red"
      if sLives <= 0 then
         put 0 into sShield
         Hunter.Message "GAME OVER",0
         put 4000 div sStepMS into sGameOverTicks
      else
         Hunter.Respawn
         Hunter.Message "SHIELD DOWN",45
      end if
   end if
   Hunter.ShowHUD
end Hunter.Damage


## ---------------------------------------------------------------- LEVELS / HUD

on Hunter.CheckLevel
   if sGameOverTicks > 0 then exit Hunter.CheckLevel
   if sRocks is not empty or sAirGems is not empty or sGroundGems is not empty then exit Hunter.CheckLevel
   add 1 to sLevel
   Hunter.Message "LEVEL" && sLevel,60
   Hunter.MakeEnemyMeshes
   Hunter.SpawnRocks
end Hunter.CheckLevel

## Only rebuilds the text that changed (called every step).
on Hunter.ShowHUD
   put "GEMS" && sGems && " $" & sValue into tGems
   if tGems is not sHudGems then
      HUD.Set "gems",tGems,16,12,16
      put tGems into sHudGems
   end if
   put empty into tLives
   repeat max(0, sLives) times
      put "^ " after tLives
   end repeat
   put "SHIELD" && sShield && " " & tLives into tShield
   if tShield is not sHudShield then
      HUD.Set "shield",tShield,16,36,14
      put tShield into sHudShield
   end if
   if sReloadTicks > 0 then
      put "RELOADING" into tAmmo
   else
      put "AMMO" && sAmmo & "/" & kMaxAmmo into tAmmo
   end if
   if tAmmo is not sHudAmmo then
      HUD.Set "ammo",tAmmo,gViewRight - the length of tAmmo * 16 - 16,gViewBottom - 32,16
      put tAmmo into sHudAmmo
   end if
end Hunter.ShowHUD

on Hunter.Message pText,pTicks
   put 30 into tSize
   HUD.Set "msg",pText,CenterX - the length of pText * tSize / 2,CenterY - tSize * 3,tSize
   put pTicks into sMsgTicks
end Hunter.Message

on Hunter.EndGame
   HUD.Remove "msg"
   set the lockCursor to false
   if there is a card "Title" then
      game.loop.stop
      go to card "Title"
   else
      Game.Exit
   end if
end Hunter.EndGame

on opencard
   if there is a group "PauseMenuGroup" then hide group "PauseMenuGroup"
   if there is a group "OptionsGroup" then hide group "OptionsGroup"
end opencard

on rawKeyUp pKey
 
   if pKey = 96  then 
      put View.NextPreset() into tName
      try
         set the  label of button "Next Preset"  to tName
      end try
   end if
   pass rawKeyUp
end rawKeyUp
