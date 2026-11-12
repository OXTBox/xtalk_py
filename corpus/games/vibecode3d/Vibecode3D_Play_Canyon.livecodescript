## CARD SCRIPT: "Play.Canyon"   DEFENSIVE 3D: CANYON RUN  (11 08 2026)
## Paste this into the script of card "Play.Canyon". The engine (rendering, meshes,
## entities, collisions, FX, HUD, sound, view) lives in the stack script; this card
## holds only the game. The engine sends these to the current card:
##   Game.OnStart  Game.OnUpdate  Game.OnStop  Collision.Hit pA,pB
## Start: Game.Select "Canyon" then Game.Play (or the Title card PLAY button).
##
##   Defensive (2D)                      ->  Canyon run (3D)
##   scrolling mountains + parallax     ->  endless procedural canyon, depth-faded
##   green triangle ship, mouse flies   ->  3D arrow ship flies to the mouse, banks
##   mouse down = missiles              ->  mouse down = twin shots
##   20 random polygon enemies          ->  20 random 3D shapes, same 20 colours
##   enemies: 3-11 destinations, shoot  ->  same, then exit far away or fly past you
##   more enemies every minute (max 10) ->  same: level up, +1000, shapes regenerated
##   3 lives / explosions / score       ->  same, with vector derez + HUD
## WORLD: camera at the origin looking down +Z (+X right, +Y down), sized from the screen.
######################################################################################

global gObjectTransforms
global gSceneObjects
global gCameraYaw
global gCameraPitch
global gViewLeft,gViewTop,gViewRight,gViewBottom
global CenterX,CenterY

local sU, sF -- world unit sized from the screen, and sU/300 for mesh sizes
local sProjK, sProjOffX, sProjOffY, sStepMS = 33 -- from the engine (Engine.Info)
local sCamX = 0, sCamY = 0 -- camera follow offset
local sShipZ, sShipMaxX, sShipMaxY, sShipId, sShipDead = false, sInvulnTicks = 0, sRespawnTicks = 0
local sSegCount, sSegLen, sScroll, sSegFarZ, sCanyonCX, sLastProfile
local sEnemies, sScore = 0, sLives = 3, sLevel = 1, sCanyonTicks = 0, sFireCool = 0
local sGameOverTicks = 0, sMsgTicks = 0

## Defensive's colour list, as hex so glow colours work.
function Canyon.Palette
   return "#D02090,#FF0000,#FF4500,#FFA500,#FFFF00,#7CFC00,#32CD32,#00FF00,#00FFFF,#6495ED," & \
         "#1E90FF,#3399FF,#FF00FF,#00FF7F,#FFC0CB,#FF69B4,#00F5FF,#87CEEB,#E6E6FA,#FFFFFF"
end Canyon.Palette

## Start (or restart) the canyon game. The engine sends this from Game.Play.
on Game.OnStart
   -- A plain camera: no scene spin, no pivot, looking straight down +Z.
   Engine.ResetCamera
   put 0 into sCamX
   put 0 into sCamY
   Canyon.GetProjection
   put Engine.Info("stepMS") into sStepMS

   -- Size everything from the screen: sU = visible half-height at depth 400.
   put (gViewBottom - gViewTop) / 2 into tHalfH
   put (gViewRight - gViewLeft) / 2 into tHalfW
   put tHalfH * 400 / sProjK into sU
   put sU / 300 into sF
   put sU * 0.75 into sShipZ
   put 0.8 * tHalfW * sShipZ / sProjK into sShipMaxX
   put 0.7 * tHalfH * sShipZ / sProjK into sShipMaxY

   -- Clear the old scene.
   Scene.ClearAll
   Particles.Clear
   HUD.Clear
   put empty into sEnemies

   -- Meshes.
   Mesh.Define "Ship", Canyon.ShipMesh()
   Mesh.Define "Shot", Canyon.ShotMesh()
   Mesh.Define "Bullet", Canyon.BulletMesh()
   Canyon.MakeEnemyMeshes

   -- The canyon: sSegCount segments, each sSegLen deep.
   put 10 into sSegCount
   put sU * 0.6 into sSegLen
   put sSegLen / 9 into sScroll
   put 0 into sCanyonCX
   put Canyon.NewProfile() into sLastProfile
   repeat with i = 1 to sSegCount
      put "CanyonSeg" & i into tMeshName
      put Canyon.NewProfile() into tBack
      Mesh.Define tMeshName, Canyon.SegmentMesh(sLastProfile,tBack,sSegLen)
      put tBack into sLastProfile
      put "Canyon_" & i into tKey
      SetObjectPosition tKey,0,0,(i-1)*sSegLen
      SetObjectRotation tKey,0,0,0
      SetObjectRotationSpeed tKey,0,0,0
      SetObjectVelocity tKey,0,0,0
      Scene.Register tMeshName,tKey,Scene.ColorGraphic("#88FF22")
   end repeat
   put sSegCount * sSegLen into sSegFarZ

   -- Rules.
   Collision.ClearRules
   Collision.AddRule "shot","enemy"
   Collision.AddRule "bullet","ship"
   Collision.AddRule "enemy","ship"

   -- Player.
   put 0 into sScore
   put 3 into sLives
   put 1 into sLevel
   put 0 into sCanyonTicks
   put 0 into sFireCool
   put 0 into sGameOverTicks
   Canyon.SpawnShip
   Canyon.ShowHUD
   Canyon.Message "LEVEL 1",60
end Game.OnStart

## The engine's projection numbers (they change with the window size).
on Canyon.GetProjection
   put Engine.Info("projection") into tP
   put item 1 of tP into sProjK
   put item 2 of tP into sProjOffX
   put item 3 of tP into sProjOffY
end Canyon.GetProjection

on Game.OnStop
   HUD.Remove "msg"
end Game.OnStop



## ---------------------------------------------------------------- MESHES

## Arrow-head fighter, nose to +Z (Defensive's green triangle, in 3D).
function Canyon.ShipMesh
   put Mesh.New() into tM
   Mesh.AddVertex tM,0,0,30*sF -- 1 nose
   Mesh.AddVertex tM,-24*sF,5*sF,-12*sF -- 2 left wing
   Mesh.AddVertex tM,24*sF,5*sF,-12*sF -- 3 right wing
   Mesh.AddVertex tM,0,-9*sF,-10*sF -- 4 fin
   Mesh.AddVertex tM,0,4*sF,-8*sF -- 5 belly
   Mesh.AddFace tM,"1 2 4"
   Mesh.AddFace tM,"1 4 3"
   Mesh.AddFace tM,"1 3 5"
   Mesh.AddFace tM,"1 5 2"
   Mesh.AddFace tM,"2 4 3 5"
   return tM
end Canyon.ShipMesh

## A laser bolt: one line along Z.
function Canyon.ShotMesh
   put Mesh.New() into tM
   Mesh.AddVertex tM,0,0,-14*sF
   Mesh.AddVertex tM,0,0,14*sF
   Mesh.AddLine tM,1,2
   return tM
end Canyon.ShotMesh

## Enemy bullet: a 3-line star.
function Canyon.BulletMesh
   put 5 * sF into r
   put Mesh.New() into tM
   Mesh.AddVertex tM,-r,0,0
   Mesh.AddVertex tM,r,0,0
   Mesh.AddVertex tM,0,-r,0
   Mesh.AddVertex tM,0,r,0
   Mesh.AddVertex tM,0,0,-r
   Mesh.AddVertex tM,0,0,r
   Mesh.AddLine tM,1,2
   Mesh.AddLine tM,3,4
   Mesh.AddLine tM,5,6
   return tM
end Canyon.BulletMesh

## 20 random enemy shapes, "Enemy1".."Enemy20" (Defensive's MakeEnemies).
## Called again on every level up (Defensive's RandomizeEnemies).
on Canyon.MakeEnemyMeshes
   repeat with n = 1 to 20
      put (12 + random(14)) * sF into r
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
            -- Diamond: two pyramids base to base.
            put 2 + random(5) into tSides
            put Mesh.Transform(MeshPyramid(tSides, r, r),0,0,0,0,-r/2,0,1) into tM
            put Mesh.Merge(tM, Mesh.Transform(MeshPyramid(tSides, r, r),pi,0,0,0,r/2,0,1)) into tM
      end switch
      Mesh.Define "Enemy" & n, tM
   end repeat
end Canyon.MakeEnemyMeshes

## One cross-section of the canyon: 7 "x,y" points, left rim -> floor -> right rim.
## Jittered for the crunchy look; the centre line wanders left and right.
function Canyon.NewProfile
   add (random(31) - 16) / 100 * sU - sCanyonCX * 0.1 to sCanyonCX
   put max(-0.35 * sU, min(0.35 * sU, sCanyonCX)) into sCanyonCX
   put sCanyonCX into c
   put 0.55 * sU into tFloorW
   put 1.15 * sU into tRimW
   put 0.62 * sU into tFloorY
   put -0.75 * sU into tRimY
   put (tRimY + tFloorY) / 2 into tMidY
   put (tRimW + tFloorW) / 2 + 0.1 * sU into tMidW
   put (c - tRimW + Canyon.J(0.15)) & comma & (tRimY + Canyon.J(0.2)) & cr into tP
   put (c - tMidW + Canyon.J(0.12)) & comma & (tMidY + Canyon.J(0.2)) & cr after tP
   put (c - tFloorW + Canyon.J(0.08)) & comma & (tFloorY + Canyon.J(0.05)) & cr after tP
   put (c + Canyon.J(0.15)) & comma & (tFloorY + 0.06 * sU + Canyon.J(0.05)) & cr after tP
   put (c + tFloorW + Canyon.J(0.08)) & comma & (tFloorY + Canyon.J(0.05)) & cr after tP
   put (c + tMidW + Canyon.J(0.12)) & comma & (tMidY + Canyon.J(0.2)) & cr after tP
   put (c + tRimW + Canyon.J(0.15)) & comma & (tRimY + Canyon.J(0.2)) after tP
   return tP
end Canyon.NewProfile

## Random jitter of +/- pAmount * sU.
function Canyon.J pAmount
   return (random(2001) - 1001) / 1000 * pAmount * sU
end Canyon.J

## One canyon segment between two profiles. Draws the front profile and the long edges
## only (the back profile is drawn by the next segment). Wall faces are pickable.
function Canyon.SegmentMesh pFront,pBack,pLen
   put Mesh.New() into tM
   put the number of lines of pFront into tN
   repeat for each line tPt in pFront
      Mesh.AddVertex tM,item 1 of tPt,item 2 of tPt,0
   end repeat
   repeat for each line tPt in pBack
      Mesh.AddVertex tM,item 1 of tPt,item 2 of tPt,pLen
   end repeat
   repeat with k = 1 to tN - 1
      Mesh.AddFace tM,k && (k+1) && (tN+k+1) && (tN+k)
      Mesh.AddLine tM,k,k+1
   end repeat
   repeat with k = 1 to tN
      Mesh.AddLine tM,k,tN+k
   end repeat
   put false into tM["edgesFromFaces"]
   return tM
end Canyon.SegmentMesh


## ---------------------------------------------------------------- UPDATE (every step)

## Every simulation step (the engine sends this from game.update).
on Game.OnUpdate
   add 1 to sCanyonTicks
   put 0 into gCameraYaw
   put 0 into gCameraPitch
   if sCanyonTicks mod 30 = 0 then Canyon.GetProjection

   Canyon.ScrollCanyon
   Canyon.UpdateShip
   Canyon.UpdateEnemies

   -- Level up every minute (Defensive: timeLevel), up to 10.
   put min(10, 1 + sCanyonTicks div (60 * 1000 div sStepMS)) into tLevel
   if tLevel > sLevel then
      put tLevel into sLevel
      Canyon.MakeEnemyMeshes
      Canyon.AddScore 1000
      Canyon.Message "LEVEL" && sLevel,60
      Sound.Play "Warp"
   end if

   -- Message timer.
   if sMsgTicks > 0 then
      subtract 1 from sMsgTicks
      if sMsgTicks = 0 then HUD.Remove "msg"
   end if

   -- Game over: wait, then leave.
   if sGameOverTicks > 0 then
      subtract 1 from sGameOverTicks
      if sGameOverTicks = 0 then Canyon.EndGame
   end if
end Game.OnUpdate

## Move every segment toward the camera; recycle passed ones to the far end with a
## brand new profile (Defensive scrolled one long mountain; this one never ends).
on Canyon.ScrollCanyon
   subtract sScroll from sSegFarZ
   repeat with i = 1 to sSegCount
      put "Canyon_" & i into tKey
      subtract sScroll from gObjectTransforms[tKey]["z"]
      if gObjectTransforms[tKey]["z"] + sSegLen < 0 then
         put Canyon.NewProfile() into tBack
         Mesh.Define "CanyonSeg" & i, Canyon.SegmentMesh(sLastProfile,tBack,sSegLen)
         put tBack into sLastProfile
         put sSegFarZ into gObjectTransforms[tKey]["z"]
         add sSegLen to sSegFarZ
      end if
   end repeat
end Canyon.ScrollCanyon

on Canyon.SpawnShip
   put Entity.Spawn("Ship",0,0,sShipZ,"#00FF66") into sShipId
   put sU * 0.05 into gObjectTransforms[sShipId]["radius"]
   put false into sShipDead
   -- A moment of safety after (re)spawning: no collision group yet.
   put 45 into sInvulnTicks
end Canyon.SpawnShip

on Canyon.UpdateShip
   if sShipDead then
      subtract 1 from sRespawnTicks
      if sRespawnTicks <= 0 and sGameOverTicks = 0 then
         if sLives > 0 then
            Canyon.SpawnShip
         else
            Canyon.Message "GAME OVER",0
            put 4000 div sStepMS into sGameOverTicks
         end if
      end if
      exit Canyon.UpdateShip
   end if
   if sInvulnTicks > 0 then
      subtract 1 from sInvulnTicks
      if sInvulnTicks = 0 then Collision.SetGroup sShipId,"ship"
   end if

   -- Fly toward the mouse (screen point -> world point at the ship's depth).
   put the mouseH into tMX
   put the mouseV into tMY
   put (tMX - sProjOffX) * sShipZ / sProjK - sCamX into tTX
   put (tMY - sProjOffY) * sShipZ / sProjK - sCamY into tTY
   put max(-sShipMaxX, min(sShipMaxX, tTX)) into tTX
   put max(-sShipMaxY, min(sShipMaxY, tTY)) into tTY
   put gObjectTransforms[sShipId]["x"] into x
   put gObjectTransforms[sShipId]["y"] into y
   put (tTX - x) * 0.25 into dx
   put (tTY - y) * 0.25 into dy
   put x + dx into gObjectTransforms[sShipId]["x"]
   put y + dy into gObjectTransforms[sShipId]["y"]
   -- Bank into turns, pitch with climbs.
   put max(-0.7, min(0.7, -dx / sU * 6)) into gObjectTransforms[sShipId]["rotZ"]
   put max(-0.4, min(0.4, dy / sU * 4)) into gObjectTransforms[sShipId]["rotX"]
   -- The camera follows a little, for parallax.
   put -(x + dx) * 0.35 into sCamX
   put -(y + dy) * 0.25 into sCamY
   Engine.SetCam sCamX,sCamY,0

   -- Fire (Defensive: mouse down = FireMissile).
   if sFireCool > 0 then subtract 1 from sFireCool
   if the mouse is down and sFireCool = 0 then
      put 3 into sFireCool
      Canyon.FireShot x + dx - 22 * sF, y + dy + 5 * sF
      Canyon.FireShot x + dx + 22 * sF, y + dy + 5 * sF
      Sound.Play "PlayerLaser"
   end if
end Canyon.UpdateShip

on Canyon.FireShot pX,pY
   put Entity.Spawn("Shot",pX,pY,sShipZ + 20 * sF,"#FF3030") into tId
   SetObjectVelocity tId,0,0,sU * 0.12
   put 40 into gObjectTransforms[tId]["ttl"]
   Collision.SetGroup tId,"shot",sU * 0.04
end Canyon.FireShot


## ---------------------------------------------------------------- ENEMIES

## Defensive's ActivateEnemies: random spawns while fewer than the level allows.
on Canyon.UpdateEnemies
   -- Forget enemies that no longer exist (shot down or flown away).
   put empty into tAlive
   repeat for each line tId in sEnemies
      if gObjectTransforms[tId] is an array then put tId & cr after tAlive
   end repeat
   put tAlive into sEnemies

   if not sShipDead and the number of lines of sEnemies < sLevel + 1 and random(100) <= 4 then
      Canyon.SpawnEnemy
   end if

   repeat for each line tId in sEnemies
      Canyon.MoveEnemy tId
   end repeat
end Canyon.UpdateEnemies

on Canyon.SpawnEnemy
   put random(20) into n
   set itemDel to comma
   put item n of Canyon.Palette() into tColor
   put Entity.Spawn("Enemy" & n, Canyon.J(0.6), Canyon.J(0.4), sSegFarZ * 0.9, tColor) into tId
   SetObjectRotationSpeed tId,(random(21)-11)/200,(random(21)-11)/200,(random(21)-11)/200
   if sLevel > 4 then
      put 2 into gObjectTransforms[tId]["hp"]
   else
      put 1 into gObjectTransforms[tId]["hp"]
   end if
   put (2 + random(4)) * sU / 300 + sLevel * 0.2 * sF into gObjectTransforms[tId]["spd"]
   put 2 + random(8) into gObjectTransforms[tId]["dests"]
   put 20 + random(40) into gObjectTransforms[tId]["fireCool"]
   put false into gObjectTransforms[tId]["exiting"]
   Collision.SetGroup tId,"enemy"
   Canyon.EnemyNewDest tId
   put tId & cr after sEnemies
   Sound.Play "Enemy"
end Canyon.SpawnEnemy

## A new point to fly to inside the play space, or (when out of destinations)
## an exit: far away, or right past the player.
on Canyon.EnemyNewDest pId
   if gObjectTransforms[pId]["dests"] > 0 then
      subtract 1 from gObjectTransforms[pId]["dests"]
      put Canyon.J(0.7) into gObjectTransforms[pId]["tx"]
      put Canyon.J(0.45) into gObjectTransforms[pId]["ty"]
      put sShipZ + sU * 0.5 + random(round(sSegFarZ * 0.5)) into gObjectTransforms[pId]["tz"]
   else
      put true into gObjectTransforms[pId]["exiting"]
      put Canyon.J(1) into gObjectTransforms[pId]["tx"]
      put Canyon.J(0.6) into gObjectTransforms[pId]["ty"]
      if random(2) = 1 then
         put -sU into gObjectTransforms[pId]["tz"]
      else
         put sSegFarZ + sU into gObjectTransforms[pId]["tz"]
      end if
   end if
end Canyon.EnemyNewDest

## Defensive's EnemyTravel: fly to the target, pick the next, shoot now and then.
on Canyon.MoveEnemy pId
   put gObjectTransforms[pId]["x"] into x
   put gObjectTransforms[pId]["y"] into y
   put gObjectTransforms[pId]["z"] into z
   put gObjectTransforms[pId]["tx"] - x into dx
   put gObjectTransforms[pId]["ty"] - y into dy
   put gObjectTransforms[pId]["tz"] - z into dz
   put sqrt(dx*dx + dy*dy + dz*dz) into tDist
   put gObjectTransforms[pId]["spd"] into tSpd
   if tDist <= tSpd then
      if gObjectTransforms[pId]["exiting"] then
         Entity.Kill pId
         exit Canyon.MoveEnemy
      end if
      Canyon.EnemyNewDest pId
   else
      put x + dx / tDist * tSpd into gObjectTransforms[pId]["x"]
      put y + dy / tDist * tSpd into gObjectTransforms[pId]["y"]
      put z + dz / tDist * tSpd into gObjectTransforms[pId]["z"]
   end if

   -- Shoot at the player while in range (Defensive: ActivateBullets).
   if sShipDead or gObjectTransforms[pId]["exiting"] then exit Canyon.MoveEnemy
   if z < sShipZ + sU * 0.4 or z > sSegFarZ * 0.8 then exit Canyon.MoveEnemy
   subtract 1 from gObjectTransforms[pId]["fireCool"]
   if gObjectTransforms[pId]["fireCool"] <= 0 then
      put max(12, 60 - sLevel * 4) + random(40) into gObjectTransforms[pId]["fireCool"]
      Canyon.FireBullet x,y,z
   end if
end Canyon.MoveEnemy

on Canyon.FireBullet pX,pY,pZ
   put gObjectTransforms[sShipId]["x"] - pX into dx
   put gObjectTransforms[sShipId]["y"] - pY into dy
   put sShipZ - pZ into dz
   put sqrt(dx*dx + dy*dy + dz*dz) into tLen
   if tLen < 1 then exit Canyon.FireBullet
   put sU * (0.025 + sLevel * 0.002) into tSpd
   put Entity.Spawn("Bullet",pX,pY,pZ,"#FFDD55") into tId
   SetObjectVelocity tId,dx / tLen * tSpd,dy / tLen * tSpd,dz / tLen * tSpd
   SetObjectRotationSpeed tId,0.2,0.3,0
   put 200 into gObjectTransforms[tId]["ttl"]
   Collision.SetGroup tId,"bullet",sU * 0.03
   Sound.Play "Bullet"
end Canyon.FireBullet


## ---------------------------------------------------------------- HITS, SCORE, HUD

## The engine sends Collision.Hit to this card first; handling it here (no pass)
## replaces the stack's default rule.
on Collision.Hit pA,pB
   put gObjectTransforms[pA]["group"] into gA
   put gObjectTransforms[pB]["group"] into gB
   -- Put the pair in rule order.
   if gA is "enemy" and gB is "shot" or gA is "ship" then
      put pA into tTemp
      put pB into pA
      put tTemp into pB
      put gObjectTransforms[pA]["group"] into gA
      put gObjectTransforms[pB]["group"] into gB
   end if

   if gA is "shot" and gB is "enemy" then
      Entity.Kill pA
      subtract 1 from gObjectTransforms[pB]["hp"]
      if gObjectTransforms[pB]["hp"] <= 0 then
         Canyon.AddScore 100 + sLevel * 10
         FX.Destroy pB
         Sound.Play "Explode"
      else
         FX.Sparks gObjectTransforms[pB]["x"],gObjectTransforms[pB]["y"],gObjectTransforms[pB]["z"],6,"white"
      end if
   else if gB is "ship" then
      -- A bullet or an enemy reached the player.
      if gA is "enemy" then
         FX.Destroy pA
      else
         Entity.Kill pA
      end if
      Canyon.Crash
   end if
end Collision.Hit

## Defensive's CrashPlayer / PlayerCrash.
on Canyon.Crash
   if sShipDead then exit Canyon.Crash
   put true into sShipDead
   FX.Destroy sShipId
   Sound.Play "PlayerCrash"
   subtract 1 from sLives
   put 75 into sRespawnTicks
   -- Clear the enemy bullets (Defensive: StageGraphics "Bullet").
   put empty into tKill
   repeat for each line tEntry in gSceneObjects
      if word 1 of tEntry is "Bullet" then put word 2 of tEntry & cr after tKill
   end repeat
   repeat for each line tId in tKill
      Entity.Kill tId
   end repeat
   Canyon.ShowHUD
end Canyon.Crash

on Canyon.AddScore pPoints
   add pPoints to sScore
   Canyon.ShowHUD
end Canyon.AddScore

## Score top-left, lives as triangles beside it (like Defensive).
on Canyon.ShowHUD
   HUD.Set "score",format("%06d", sScore),16,12,22
   put empty into tLives
   repeat max(0, sLives) times
      put "^ " after tLives
   end repeat
   HUD.Set "lives",tLives,16 + 7 * 22,12,22
end Canyon.ShowHUD

## Big centred message; pTicks = 0 keeps it up.
on Canyon.Message pText,pTicks
   put 34 into tSize
   HUD.Set "msg",pText,CenterX - the length of pText * tSize / 2,CenterY - tSize * 2,tSize
   put pTicks into sMsgTicks
end Canyon.Message

## Game over: back to the Title card if there is one (Defensive), else to Developer.
on Canyon.EndGame
   HUD.Remove "msg"
   if there is a card "Title" then
      game.loop.stop
      go to card "Title"
   else
      Game.Exit
   end if
end Canyon.EndGame


on opencard
try
   hide group "PauseMenuGroup"
   hide group "OptionsGroup"
end try
end opencard
