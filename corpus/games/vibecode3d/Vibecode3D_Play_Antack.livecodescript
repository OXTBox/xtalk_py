######################################################################################
## CARD SCRIPT: "Play.Antack"   ANTACK  (11 12 2026)
## The owner's uDevGame 2002 game (T3D: Tobias Opfermann code, William Griffin design,
## Russell Murphy voices), back as a vector game with placeholder models. Six of your
## ant-hill bases face six enemy hills. Launch ant armies at the enemy hills and shoot
## down the red armies the computer sends at yours. Destroy all six enemy hills to win
## the level; lose all six of yours and the game is lost.
## SCREENS   Title (Easy / Medium / Hard / Trainer / Quit), the fight levels, You Win,
##           You Lost. Easy: Fight 1, 2, 4, 3. Medium starts at Fight 2, Hard at Fight 3.
## CONTROLS  1-6       launch an ant army at enemy hill 1-6 (from a free hill of yours)
##           click     anti-ant missile at the red army nearest the pointer (3 at a time);
##                     each one takes out one ant of the five in an army
##           W A S D   move    R F  up / down    arrow keys  look around
## RULES     A hill has 5 lives and shrinks as it loses them. Every 10 seconds a hill
##           that is still standing wins a life back. An army flies for 4 seconds,
##           tilting from nose-up to nose-down (the T3D poses "starting" to "falling");
##           while one ant is left it still costs the hill it lands on a life.
## DATA      Antack/antack_data.txt beside this file: the T3D terrains and the hill
##           positions of each level (tools/t3d_to_antack.py). Hills, ants and shots
##           are procedural placeholders.
######################################################################################

global gObjectTransforms, gSceneObjects
global gCameraYaw, gCameraPitch
global gViewLeft, gViewTop, gViewRight, gViewBottom
global bPaused, bPlaying

constant kFlightSecs = 4.0     -- an army's time in the air
constant kRegenSecs = 10.0     -- a standing hill wins a life back this often
constant kShotSecs = 3.0       -- an anti-ant missile gives up after this
constant kShotSpeed = 22       -- anti-ant missile, engine units a step
constant kMoveSpeed = 4        -- the player, engine units a step
constant kTurn = 0.035         -- radians a step for the arrow keys
constant kMaxShots = 3
constant kPlayerColor = "#40E0FF"
constant kEnemyColor = "#FF5050"
constant kGroundColor = "#3A7D44"

local sStepMS = 33, sTicks = 0
local sScreen        -- "title", "play", "won", "lost"
local sData          -- [levels][name][...], [meshes][name] (text: v/e lines)
local sDataError
local sLevel, sNextAt, sMessage
local sBase          -- [key][team|n|life|x|y|z|busy|dead]
local sArmy          -- [key][from|target|team|x0|y0|z0|x1|y1|z1|t0|arc]
local sShot          -- [key][army|t0|x|y|z]
local sCX, sCY, sCZ  -- the player's camera position
local sKeyWas, sNextAI, sNextRegen, sHover, sMenu, sEndAt

-------------------------------------------------------------------- engine hooks

on Game.OnStart
   put Engine.Info("stepMS") into sStepMS
   if sStepMS is not a number then put 33 into sStepMS
   put 0 into sTicks
   Antack.LoadData
   Antack.MakeMeshes
   Antack.Title
end Game.OnStart

on Game.OnUpdate
   add 1 to sTicks
   switch sScreen
      case "play"
         Antack.PlayStep
         break
      case "title"
         Antack.MenuHover
         break
      case "won"
      case "lost"
         if Antack.Now() > sEndAt then Antack.Title
         break
   end switch
end Game.OnUpdate

on Game.OnClick pX,pY,pButton
   switch sScreen
      case "title"
         Antack.MenuClick pX, pY
         break
      case "play"
         Antack.Fire pX, pY
         break
      default
         Antack.Title
   end switch
end Game.OnClick

on Game.OnKill pKey,pX,pY,pZ
end Game.OnKill

on Game.OnPause
end Game.OnPause

on Game.OnResume
end Game.OnResume

on Game.OnStop
   HUD.Clear
end Game.OnStop

on Collision.Hit pA,pB
end Collision.Hit

-------------------------------------------------------------------- time, scene

function Antack.Now
   return sTicks * sStepMS / 1000
end Antack.Now

-- start a screen with nothing in it
on Antack.Clear
   Engine.ResetCamera
   Scene.ClearAll
   Particles.Clear
   HUD.Clear
   Collision.ClearRules
   put empty into sBase
   put empty into sArmy
   put empty into sShot
end Antack.Clear

-- swap the mesh an object is drawn with (the hills shrink with their lives)
on Antack.SetMesh pKey, pMesh
   local tOut, tLine
   repeat for each line tLine in gSceneObjects
      if word 2 of tLine is pKey then put pMesh into word 1 of tLine
      put tLine & cr after tOut
   end repeat
   delete the last char of tOut
   put tOut into gSceneObjects
   put pMesh into gObjectTransforms[pKey]["mesh"]
end Antack.SetMesh

-- engine rotation angles (applied Z, then Y, then X) for a heading and a nose pitch:
-- turn to pYaw about the vertical, with the nose raised by pPitch (up is -Y)
function Antack.Euler pYaw, pPitch
   local sy, cy, sp, cp
   put sin(pYaw) into sy
   put cos(pYaw) into cy
   put sin(pPitch) into sp
   put cos(pPitch) into cp
   return atan2(sp, cy * cp) & comma & asin(max(-1, min(1, sy * cp))) & comma & atan2(-sy * sp, cy)
end Antack.Euler

on Antack.Turn pKey, pYaw, pPitch
   local tE
   put Antack.Euler(pYaw, pPitch) into tE
   SetObjectRotation pKey, item 1 of tE, item 2 of tE, item 3 of tE
end Antack.Turn

-- where an object is on screen: "x,y", or empty when it is behind the camera
function Antack.ScreenOf pKey
   local tXf, tP
   put Xform.Object(pKey) into tXf
   if item 12 of tXf < 5 then return empty
   put Engine.Info("projection") into tP
   return round(item 10 of tXf * item 1 of tP / item 12 of tXf + item 2 of tP) & comma & \
         round(item 11 of tXf * item 1 of tP / item 12 of tXf + item 3 of tP)
end Antack.ScreenOf

-------------------------------------------------------------------- data and meshes

-- Antack/antack_data.txt beside this script's file, found the way Face.FindFile does
on Antack.LoadData
   local tFile, tText, tLine, tSection, tName, tKind
   if sData is an array then exit Antack.LoadData
   put Antack.FindFile("LIB_GAMES/Vibecode3D_Games/Antack/antack_data.txt") into tFile
   if tFile is empty then
      put "ANTACK DATA NOT FOUND" into sDataError
      exit Antack.LoadData
   end if
   put URL ("file:" & tFile) into tText
   replace numToChar(13) with empty in tText
   repeat for each line tLine in tText
      if tLine is empty or char 1 of tLine is "#" then next repeat
      if char 1 of tLine is "[" then
         -- chunks nest small inside big: cut the brackets off first
         put char 2 to -2 of tLine into tSection
         put word 1 of tSection into tKind
         put word 2 of tSection into tName
         next repeat
      end if
      if tKind is "mesh" then
         put tLine & cr after sData["meshes"][tName]
      else if tKind is "level" then
         if word 1 of tLine is among the items of "base0,base1" then
            put word 2 of tLine & cr after sData["levels"][tName][word 1 of tLine]
         else
            put word 2 to -1 of tLine into sData["levels"][tName][word 1 of tLine]
         end if
      end if
   end repeat
end Antack.LoadData

function Antack.FindFile pRelPath
   local tPath, tTry
   put the effective filename of this stack into tPath
   set the itemDel to "/"
   repeat 8 times
      delete item -1 of tPath
      if tPath is empty then exit repeat
      put tPath & "/" & pRelPath into tTry
      if there is a file tTry then return tTry
   end repeat
   put "//wsl$/Ubuntu/home/igame3d/projects/" & pRelPath into tTry
   if there is a file tTry then return tTry
   return empty
end Antack.FindFile

on Antack.MakeMeshes
   local n, tName, tM, tLine, tR, tH
   -- hills: a mound per number of lives, and a flat ring when destroyed
   repeat with n = 1 to 5
      put 24 + 8 * n into tR
      put 10 + 7 * n into tH
      Mesh.Define "Antack.Hill" & n, MeshLathe("0," & -tH & "|" & tR * 0.3 & "," & -tH * 0.85 & "|" & \
            tR * 0.7 & "," & -tH * 0.35 & "|" & tR & ",0", 8)
   end repeat
   Mesh.Define "Antack.HillDead", MeshLathe("30,0|18,-3", 8)
   -- an army of 1 to 5 ants: each anti-ant missile takes out one ant
   repeat with n = 1 to 5
      Mesh.Define "Antack.Army" & n, Antack.ArmyMesh(1.4, n)
   end repeat
   Mesh.Define "Antack.Ant", Antack.AntMesh(0, 0, 9)
   Mesh.Define "Antack.Shot", MeshPyramid(3, 4, 14)
   Mesh.Define "Antack.Ring", Antack.RingMesh(210, 32)
   Mesh.Define "Antack.Ring2", Antack.RingMesh(190, 32)
   repeat for each key tName in sData["meshes"]
      put Mesh.New() into tM
      repeat for each line tLine in sData["meshes"][tName]
         if word 1 of tLine is "v" then
            Mesh.AddVertex tM, word 2 of tLine, word 3 of tLine, word 4 of tLine
         else if word 1 of tLine is "e" then
            Mesh.AddLine tM, word 2 of tLine, word 3 of tLine
         end if
      end repeat
      Mesh.Define "Antack.T_" & tName, tM
   end repeat
end Antack.MakeMeshes

-- one ant, nose along +Z, legs out to the sides, at pX,pZ, pScale engine units a unit
-- (The T3D ants were a texture on a plane bent along the middle; these are lines.)
function Antack.AntMesh pX, pZ, pScale
   local tM, tShape
   put Mesh.New() into tM
   -- abdomen, thorax, head as diamonds with a raised ridge
   Antack.AddDiamond tM, pX, pZ, pScale, -14, -2, 5, 4
   Antack.AddDiamond tM, pX, pZ, pScale, -2, 6, 2.5, 2
   Antack.AddDiamond tM, pX, pZ, pScale, 6, 11, 3, 2.5
   -- antennae and legs: "x1 y1 z1 x2 y2 z2 x3 y3 z3" bent lines
   repeat for each line tShape in "1 0 10.5 4 -1 15 6 0 18" & cr & "-1 0 10.5 -4 -1 15 -6 0 18" & cr & \
         "2 0 2 7 -1 5 9 1 9" & cr & "-2 0 2 -7 -1 5 -9 1 9" & cr & \
         "2.5 0 2 8 -1 1 10 1 0" & cr & "-2.5 0 2 -8 -1 1 -10 1 0" & cr & \
         "2 0 3 6 -1 -3 8 1 -7" & cr & "-2 0 3 -6 -1 -3 -8 1 -7"
      Mesh.AddVertex tM, pX + (word 1 of tShape) * pScale, (word 2 of tShape) * pScale, pZ + (word 3 of tShape) * pScale
      Mesh.AddVertex tM, pX + (word 4 of tShape) * pScale, (word 5 of tShape) * pScale, pZ + (word 6 of tShape) * pScale
      Mesh.AddVertex tM, pX + (word 7 of tShape) * pScale, (word 8 of tShape) * pScale, pZ + (word 9 of tShape) * pScale
      Mesh.AddLine tM, tM["count"] - 2, tM["count"] - 1
      Mesh.AddLine tM, tM["count"] - 1, tM["count"]
   end repeat
   return tM
end Antack.AntMesh

-- a diamond from z pZ1 to pZ2, pHalf wide, with a ridge pRise high (up is -Y)
on Antack.AddDiamond @pM, pX, pZ, pScale, pZ1, pZ2, pHalf, pRise
   local tA, tMid
   put (pZ1 + pZ2) / 2 into tMid
   Mesh.AddVertex pM, pX, 0, pZ + pZ1 * pScale
   put pM["count"] into tA
   Mesh.AddVertex pM, pX + pHalf * pScale, 0, pZ + tMid * pScale
   Mesh.AddVertex pM, pX, 0, pZ + pZ2 * pScale
   Mesh.AddVertex pM, pX - pHalf * pScale, 0, pZ + tMid * pScale
   Mesh.AddVertex pM, pX, -pRise * pScale, pZ + tMid * pScale
   Mesh.AddLine pM, tA, tA + 1
   Mesh.AddLine pM, tA + 1, tA + 2
   Mesh.AddLine pM, tA + 2, tA + 3
   Mesh.AddLine pM, tA + 3, tA
   Mesh.AddLine pM, tA, tA + 4
   Mesh.AddLine pM, tA + 4, tA + 2
end Antack.AddDiamond

-- an army: up to five ants in the loose group of the T3D texture
function Antack.ArmyMesh pScale, pCount
   local tArmy, tSpot
   repeat for each line tSpot in line 1 to pCount of ("0 2" & cr & "-11 -16" & cr & "12 -8" & cr & "-22 -4" & cr & "24 8")
      if tArmy is empty then
         put Antack.AntMesh(word 1 of tSpot * pScale, word 2 of tSpot * pScale, pScale) into tArmy
      else
         put Mesh.Merge(tArmy, Antack.AntMesh(word 1 of tSpot * pScale, word 2 of tSpot * pScale, pScale)) into tArmy
      end if
   end repeat
   return tArmy
end Antack.ArmyMesh

-- a circle of pSides lines, radius pR, standing up facing the camera (in the X-Y plane)
function Antack.RingMesh pR, pSides
   local tM, i, tA
   put Mesh.New() into tM
   repeat with i = 0 to pSides - 1
      Mesh.AddVertex tM, pR * cos(2 * pi * i / pSides), pR * sin(2 * pi * i / pSides), 0
   end repeat
   repeat with i = 1 to pSides
      put (i mod pSides) + 1 into tA
      Mesh.AddLine tM, i, tA
   end repeat
   return tM
end Antack.RingMesh

-------------------------------------------------------------------- title, won, lost

on Antack.Title
   local tW, tH, tSize, tItem, tY, n
   Antack.Clear
   put "title" into sScreen
   put empty into sHover
   Antack.Emblem
   put gViewRight - gViewLeft into tW
   put gViewBottom - gViewTop into tH
   put round(tW / 9) into tSize
   HUD.Set "A.Title", "ANTACK", gViewLeft + (tW - 6 * tSize) / 2, gViewTop + tH * 0.06, tSize
   put round(tH / 20) into tSize
   put gViewTop + tH * 0.30 into tY
   put empty into sMenu
   put 0 into n
   repeat for each item tItem in "EASY,MEDIUM,HARD,TRAINER,QUIT"
      add 1 to n
      put tItem & comma & round(gViewLeft + tW * 0.05) & comma & round(tY) & comma & tSize into sMenu[n]
      HUD.Set "A.Menu" & n, tItem, gViewLeft + tW * 0.05, tY, tSize
      add tSize * 1.7 to tY
   end repeat
   put round(min(tH / 50, tW / 52)) into tSize
   HUD.Set "A.Help1", "KEYS 1-6: ANT ARMIES ATTACK ENEMY HILLS 1-6", gViewLeft + tW * 0.05, gViewBottom - tSize * 7, tSize
   HUD.Set "A.Help2", "CLICK: ANTI-ANT MISSILE AT RED ARMIES", gViewLeft + tW * 0.05, gViewBottom - tSize * 5, tSize
   HUD.Set "A.Help3", "WASD MOVE   R/F UP/DOWN   ARROWS LOOK", gViewLeft + tW * 0.05, gViewBottom - tSize * 3, tSize
   if sDataError is not empty then HUD.Set "A.Err", sDataError, gViewLeft + tW * 0.05, gViewTop + tH * 0.25, tSize
end Antack.Title

-- the T3D logo as lines: two rings and a big ant turning inside them
on Antack.Emblem
   local tKey
   put Entity.Spawn("Antack.Ring", 110, 20, 480, "yellow") into tKey
   put Entity.Spawn("Antack.Ring2", 110, 20, 480, "cyan") into tKey
   put Entity.Spawn("Antack.Ant", 110, 20, 480, kEnemyColor) into tKey
   -- seen from above (lying in X-Z, turned to face the camera), turning slowly
   SetObjectRotation tKey, -pi / 2, 0, 0
   SetObjectRotationSpeed tKey, 0, 0.012, 0
end Antack.Emblem

on Antack.MenuHover
   local tM, n, tHit, tSpec
   put the mouseLoc into tM
   repeat with n = 1 to 5
      put sMenu[n] into tSpec
      if item 1 of tM >= item 2 of tSpec and item 1 of tM <= item 2 of tSpec + 8 * item 4 of tSpec and \
            item 2 of tM >= item 3 of tSpec and item 2 of tM <= item 3 of tSpec + item 4 of tSpec then
         put n into tHit
      end if
   end repeat
   if tHit is sHover then exit Antack.MenuHover
   if sHover is not empty then HUD.Set "A.Menu" & sHover, item 1 of sMenu[sHover], item 2 of sMenu[sHover], item 3 of sMenu[sHover], item 4 of sMenu[sHover]
   put tHit into sHover
   if tHit is not empty then HUD.Set "A.Menu" & tHit, item 1 of sMenu[tHit] && "+", item 2 of sMenu[tHit], item 3 of sMenu[tHit], item 4 of sMenu[tHit]
end Antack.MenuHover

on Antack.MenuClick pX, pY
   Antack.MenuHover
   switch item 1 of sMenu[sHover]
      case "EASY"
         Antack.StartLevel "Fight1"
         break
      case "MEDIUM"
         Antack.StartLevel "Fight2"
         break
      case "HARD"
         Antack.StartLevel "Fight3"
         break
      case "TRAINER"
         Antack.StartLevel "Trainer"
         break
      case "QUIT"
         Game.Exit
         break
   end switch
end Antack.MenuClick

on Antack.EndScreen pWon
   local tW, tH, tSize, tText, tLine2
   Antack.Clear
   if pWon then
      put "won" into sScreen
      put "YOU WIN!" into tText
      put "CLICK TO PLAY AGAIN" into tLine2
   else
      put "lost" into sScreen
      put "YOU LOST!" into tText
      put "CLICK TO TRY AGAIN" into tLine2
   end if
   put Antack.Now() + 30 into sEndAt
   get Entity.Spawn("Antack.Ring", 0, 0, 480, "cyan")
   get Entity.Spawn("Antack.Ring2", 0, 0, 480, "#8080FF")
   get Entity.Spawn("Antack.Ant", 0, 0, 480, "#FF8040")
   SetObjectRotation it, -pi / 2, 0, 0
   SetObjectRotationSpeed it, 0, 0.015, 0
   put gViewRight - gViewLeft into tW
   put gViewBottom - gViewTop into tH
   put round(tW / 10) into tSize
   HUD.Set "A.End", tText, gViewLeft + (tW - the number of chars of tText * tSize) / 2, gViewTop + tH * 0.08, tSize
   put round(tH / 24) into tSize
   HUD.Set "A.End2", tLine2, gViewLeft + (tW - the number of chars of tLine2 * tSize) / 2, gViewBottom - tSize * 4, tSize
end Antack.EndScreen

-------------------------------------------------------------------- a fight level

on Antack.StartLevel pName
   local tLevel, tTeam, n, tPos, tKey, tColor, tEX, tEY, tEZ
   if sData["levels"][pName] is not an array then
      HUD.Set "A.Err", "NO LEVEL" && pName, gViewLeft + 20, gViewTop + 60, 14
      exit Antack.StartLevel
   end if
   Antack.Clear
   put "play" into sScreen
   put pName into sLevel
   put sData["levels"][pName] into tLevel
   get Entity.Spawn("Antack.T_" & tLevel["terrain"], 0, 0, 0, kGroundColor)
   repeat for each item tTeam in "0,1"
      if tTeam is 0 then
         put kPlayerColor into tColor
      else
         put kEnemyColor into tColor
      end if
      repeat with n = 1 to 6
         put line n of tLevel["base" & tTeam] into tPos
         put Entity.Spawn("Antack.Hill5", item 1 of tPos, item 2 of tPos, item 3 of tPos, tColor) into tKey
         put tTeam into sBase[tKey]["team"]
         put n into sBase[tKey]["n"]
         put 5 into sBase[tKey]["life"]
         put item 1 of tPos into sBase[tKey]["x"]
         put item 2 of tPos into sBase[tKey]["y"]
         put item 3 of tPos into sBase[tKey]["z"]
         put false into sBase[tKey]["dead"]
         put empty into sBase[tKey]["busy"]
         if tTeam is 1 then
            add item 1 of tPos to tEX
            add item 2 of tPos to tEY
            add item 3 of tPos to tEZ
         end if
      end repeat
   end repeat
   -- the camera starts where T3D started it, facing the enemy hills
   put sData["levels"][pName]["camera"] into tPos
   put item 1 of tPos into sCX
   put item 2 of tPos into sCY
   put item 3 of tPos into sCZ
   put atan2(tEX / 6 - sCX, tEZ / 6 - sCZ) into gCameraYaw
   put -atan2(tEY / 6 - sCY, sqrt((tEX / 6 - sCX) ^ 2 + (tEZ / 6 - sCZ) ^ 2)) into gCameraPitch
   Engine.SetCam -sCX, -sCY, -sCZ
   put Antack.Now() + item 1 of tLevel["ai"] + 2 into sNextAI
   put Antack.Now() + kRegenSecs into sNextRegen
   put empty into sNextAt
   put empty into sKeyWas
   Antack.Message Antack.LevelTitle(pName), 3
   Antack.Counters
end Antack.StartLevel

function Antack.LevelTitle pName
   if pName is "Trainer" then return "TRAINER"
   return "FIGHT" && char -1 of pName
end Antack.LevelTitle

on Antack.Message pText, pSecs
   local tW, tSize
   put gViewRight - gViewLeft into tW
   put round((gViewBottom - gViewTop) / 16) into tSize
   HUD.Set "A.Msg", pText, gViewLeft + (tW - the number of chars of pText * tSize) / 2, gViewTop + (gViewBottom - gViewTop) * 0.3, tSize
   put Antack.Now() + pSecs into sMessage
end Antack.Message

on Antack.Counters
   local tKey, tMine, tTheirs, tSize
   put 0 into tMine
   put 0 into tTheirs
   repeat for each key tKey in sBase
      if sBase[tKey]["dead"] then next repeat
      if sBase[tKey]["team"] is 0 then
         add 1 to tMine
      else
         add 1 to tTheirs
      end if
   end repeat
   put round((gViewBottom - gViewTop) / 30) into tSize
   HUD.Set "A.Mine", "YOUR HILLS" && tMine, gViewLeft + 16, gViewTop + 16, tSize
   HUD.Set "A.Theirs", "ENEMY HILLS" && tTheirs, gViewRight - 16 - 13 * tSize, gViewTop + 16, tSize
   if tTheirs is 0 and sNextAt is empty then
      Antack.Message "HILLS DESTROYED!", 3
      put Antack.Now() + 3 into sNextAt
   else if tMine is 0 and sNextAt is empty then
      Antack.Message "YOUR HILLS ARE GONE", 3
      put Antack.Now() + 3 into sNextAt
   end if
end Antack.Counters

on Antack.PlayStep
   local tNow, tKeys, n, tKey, tPos, tSize
   put Antack.Now() into tNow
   -- level over: on to the next level or an end screen
   if sNextAt is not empty and tNow >= sNextAt then
      if Antack.Alive(1) is 0 then
         if sData["levels"][sLevel]["win"] is "WON" then
            Antack.EndScreen true
         else
            Antack.StartLevel sData["levels"][sLevel]["win"]
         end if
      else
         Antack.EndScreen false
      end if
      exit Antack.PlayStep
   end if
   Antack.MovePlayer
   -- keys 1-6, once per press
   put the keysDown into tKeys
   repeat with n = 1 to 6
      if (48 + n) is among the items of tKeys then
         if sKeyWas[n] is not true then Antack.Launch 0, n
         put true into sKeyWas[n]
      else
         put false into sKeyWas[n]
      end if
   end repeat
   Antack.ComputerTurn tNow
   Antack.MoveArmies tNow
   Antack.MoveShots tNow
   if tNow >= sNextRegen then
      put tNow + kRegenSecs into sNextRegen
      repeat for each key tKey in sBase
         if not sBase[tKey]["dead"] and sBase[tKey]["life"] < 5 then
            add 1 to sBase[tKey]["life"]
            Antack.SetMesh tKey, "Antack.Hill" & sBase[tKey]["life"]
         end if
      end repeat
   end if
   if sMessage is not empty and tNow >= sMessage then
      HUD.Remove "A.Msg"
      put empty into sMessage
   end if
   -- crosshair at the pointer, numbers over the enemy hills
   put the mouseLoc into tPos
   put round((gViewBottom - gViewTop) / 28) into tSize
   HUD.Set "A.Cross", "+", item 1 of tPos - tSize / 2, item 2 of tPos - tSize / 2, tSize
   repeat for each key tKey in sBase
      if sBase[tKey]["team"] is not 1 then next repeat
      put empty into tPos
      if not sBase[tKey]["dead"] then put Antack.ScreenOf(tKey) into tPos
      if tPos is empty then
         HUD.Remove "A.L" & sBase[tKey]["n"]
      else
         HUD.Set "A.L" & sBase[tKey]["n"], sBase[tKey]["n"], item 1 of tPos - tSize / 2, item 2 of tPos - tSize * 3, tSize
      end if
   end repeat
end Antack.PlayStep

function Antack.Alive pTeam
   local tKey, tCount
   put 0 into tCount
   repeat for each key tKey in sBase
      if sBase[tKey]["team"] is pTeam and not sBase[tKey]["dead"] then add 1 to tCount
   end repeat
   return tCount
end Antack.Alive

on Antack.MovePlayer
   local tKeys, tF, tS, tU, fx, fz
   put the keysDown into tKeys
   put 0 into tF
   put 0 into tS
   put 0 into tU
   if 119 is among the items of tKeys or 87 is among the items of tKeys then add 1 to tF
   if 115 is among the items of tKeys or 83 is among the items of tKeys then subtract 1 from tF
   if 100 is among the items of tKeys or 68 is among the items of tKeys then add 1 to tS
   if 97 is among the items of tKeys or 65 is among the items of tKeys then subtract 1 from tS
   if 114 is among the items of tKeys or 82 is among the items of tKeys then subtract 1 from tU
   if 102 is among the items of tKeys or 70 is among the items of tKeys then add 1 to tU
   if 65361 is among the items of tKeys then subtract kTurn from gCameraYaw
   if 65363 is among the items of tKeys then add kTurn to gCameraYaw
   if 65362 is among the items of tKeys then put min(1.3, gCameraPitch + kTurn) into gCameraPitch
   if 65364 is among the items of tKeys then put max(-1.3, gCameraPitch - kTurn) into gCameraPitch
   put sin(gCameraYaw) into fx
   put cos(gCameraYaw) into fz
   add (fx * tF + fz * tS) * kMoveSpeed to sCX
   add (fz * tF - fx * tS) * kMoveSpeed to sCZ
   add tU * kMoveSpeed to sCY
   Engine.SetCam -sCX, -sCY, -sCZ
end Antack.MovePlayer

-------------------------------------------------------------------- armies

-- team pTeam sends an army at the other team's hill pN, from its first free hill
on Antack.Launch pTeam, pN
   local tKey, tFrom, tTarget, tArmy, tColor, dx, dz, tDist, n
   repeat for each key tKey in sBase
      if sBase[tKey]["team"] is not pTeam and sBase[tKey]["n"] is pN and not sBase[tKey]["dead"] then put tKey into tTarget
   end repeat
   if tTarget is empty then exit Antack.Launch
   repeat with n = 1 to 6
      repeat for each key tKey in sBase
         if sBase[tKey]["team"] is pTeam and sBase[tKey]["n"] is n and not sBase[tKey]["dead"] \
               and sBase[tKey]["busy"] is empty and tFrom is empty then put tKey into tFrom
      end repeat
   end repeat
   if tFrom is empty then exit Antack.Launch
   if pTeam is 0 then
      put "white" into tColor
   else
      put kEnemyColor into tColor
   end if
   put Entity.Spawn("Antack.Army5", sBase[tFrom]["x"], sBase[tFrom]["y"] - 30, sBase[tFrom]["z"], tColor) into tArmy
   put 5 into sArmy[tArmy]["ants"]
   put tArmy into sBase[tFrom]["busy"]
   put tFrom into sArmy[tArmy]["from"]
   put tTarget into sArmy[tArmy]["target"]
   put pTeam into sArmy[tArmy]["team"]
   put sBase[tFrom]["x"] into sArmy[tArmy]["x0"]
   put sBase[tFrom]["y"] - 30 into sArmy[tArmy]["y0"]
   put sBase[tFrom]["z"] into sArmy[tArmy]["z0"]
   put sBase[tTarget]["x"] into sArmy[tArmy]["x1"]
   put sBase[tTarget]["y"] - 10 into sArmy[tArmy]["y1"]
   put sBase[tTarget]["z"] into sArmy[tArmy]["z1"]
   put Antack.Now() into sArmy[tArmy]["t0"]
   put sArmy[tArmy]["x1"] - sArmy[tArmy]["x0"] into dx
   put sArmy[tArmy]["z1"] - sArmy[tArmy]["z0"] into dz
   put sqrt(dx * dx + dz * dz) into tDist
   put 60 + tDist * 0.35 into sArmy[tArmy]["arc"]
   put atan2(dx, dz) into sArmy[tArmy]["yaw"]
end Antack.Launch

-- the computer: every few seconds some armies at your hills (hard levels go hill by hill)
on Antack.ComputerTurn pNow
   local tAI, tCount, tKey, tTargets, tPick, n
   if pNow < sNextAI or sNextAt is not empty then exit Antack.ComputerTurn
   put sData["levels"][sLevel]["ai"] into tAI
   put pNow + item 1 of tAI into sNextAI
   put item 2 of tAI + random(item 3 of tAI - item 2 of tAI + 1) - 1 into tCount
   repeat with n = 1 to 6
      repeat for each key tKey in sBase
         if sBase[tKey]["team"] is 0 and sBase[tKey]["n"] is n and not sBase[tKey]["dead"] then put n & cr after tTargets
      end repeat
   end repeat
   if tTargets is empty then exit Antack.ComputerTurn
   repeat tCount times
      if item 2 of tAI >= 2 then
         put line 1 of tTargets into tPick
      else
         put line random(the number of lines of tTargets) of tTargets into tPick
      end if
      Antack.Launch 1, tPick
   end repeat
end Antack.ComputerTurn

on Antack.MoveArmies pNow
   local tArmy, u, tUp, x, y, z, tSlope
   repeat for each key tArmy in sArmy
      put (pNow - sArmy[tArmy]["t0"]) / kFlightSecs into u
      if u >= 1 then
         Antack.Land tArmy
         next repeat
      end if
      put sArmy[tArmy]["arc"] * 4 * u * (1 - u) into tUp
      put sArmy[tArmy]["x0"] + (sArmy[tArmy]["x1"] - sArmy[tArmy]["x0"]) * u into x
      put sArmy[tArmy]["y0"] + (sArmy[tArmy]["y1"] - sArmy[tArmy]["y0"]) * u - tUp into y
      put sArmy[tArmy]["z0"] + (sArmy[tArmy]["z1"] - sArmy[tArmy]["z0"]) * u into z
      SetObjectPosition tArmy, x, y, z
      -- nose up on the way up, down on the way down (the T3D poses: 36 to 140 degrees)
      put sArmy[tArmy]["arc"] * 4 * (1 - 2 * u) / 300 into tSlope
      Antack.Turn tArmy, sArmy[tArmy]["yaw"], atan(tSlope)
   end repeat
end Antack.MoveArmies

-- an army reaches its target hill: one life less, and the hill shrinks or falls
on Antack.Land pArmy
   local tTarget, tColor
   put sArmy[pArmy]["target"] into tTarget
   if sArmy[pArmy]["team"] is 0 then
      put kEnemyColor into tColor
   else
      put kPlayerColor into tColor
   end if
   if tTarget is not empty and not sBase[tTarget]["dead"] then
      subtract 1 from sBase[tTarget]["life"]
      if sBase[tTarget]["life"] <= 0 then
         put true into sBase[tTarget]["dead"]
         Antack.SetMesh tTarget, "Antack.HillDead"
         FX.Sparks sBase[tTarget]["x"], sBase[tTarget]["y"] - 20, sBase[tTarget]["z"], 40, tColor
      else
         Antack.SetMesh tTarget, "Antack.Hill" & sBase[tTarget]["life"]
         FX.Sparks sBase[tTarget]["x"], sBase[tTarget]["y"] - 20, sBase[tTarget]["z"], 16, tColor
      end if
   end if
   Antack.EndArmy pArmy
   Antack.Counters
end Antack.Land

on Antack.EndArmy pArmy
   local tFrom
   put sArmy[pArmy]["from"] into tFrom
   if tFrom is not empty and sBase[tFrom]["busy"] is pArmy then put empty into sBase[tFrom]["busy"]
   delete variable sArmy[pArmy]
   Entity.Kill pArmy
end Antack.EndArmy

-------------------------------------------------------------------- anti-ant missiles

-- a click: an anti-ant missile at the red army nearest the pointer (within reach)
on Antack.Fire pX, pY
   local tArmy, tPos, tBest, tBestD, d, tShot
   if the number of lines of the keys of sShot >= kMaxShots then exit Antack.Fire
   put 1000000 into tBestD
   repeat for each key tArmy in sArmy
      if sArmy[tArmy]["team"] is not 1 then next repeat
      put Antack.ScreenOf(tArmy) into tPos
      if tPos is empty then next repeat
      put (item 1 of tPos - pX) ^ 2 + (item 2 of tPos - pY) ^ 2 into d
      if d < tBestD then
         put d into tBestD
         put tArmy into tBest
      end if
   end repeat
   if tBest is empty or tBestD > 90 * 90 then exit Antack.Fire
   put Entity.Spawn("Antack.Shot", sCX, sCY + 15, sCZ, "yellow") into tShot
   put tBest into sShot[tShot]["army"]
   put Antack.Now() into sShot[tShot]["t0"]
   put sCX into sShot[tShot]["x"]
   put sCY + 15 into sShot[tShot]["y"]
   put sCZ into sShot[tShot]["z"]
end Antack.Fire

on Antack.MoveShots pNow
   local tShot, tArmy, tXf, dx, dy, dz, d, x, y, z
   repeat for each key tShot in sShot
      put sShot[tShot]["army"] into tArmy
      if pNow - sShot[tShot]["t0"] > kShotSecs or sArmy[tArmy] is not an array then
         delete variable sShot[tShot]
         Entity.Kill tShot
         next repeat
      end if
      put GetObjectPosition(tArmy, "x") - sShot[tShot]["x"] into dx
      put GetObjectPosition(tArmy, "y") - sShot[tShot]["y"] into dy
      put GetObjectPosition(tArmy, "z") - sShot[tShot]["z"] into dz
      put sqrt(dx * dx + dy * dy + dz * dz) into d
      if d <= kShotSpeed + 20 then
         -- one ant down; the army flies on with the rest
         subtract 1 from sArmy[tArmy]["ants"]
         FX.Sparks GetObjectPosition(tArmy, "x"), GetObjectPosition(tArmy, "y"), GetObjectPosition(tArmy, "z"), 10, "yellow"
         if sArmy[tArmy]["ants"] <= 0 then
            Antack.EndArmy tArmy
         else
            Antack.SetMesh tArmy, "Antack.Army" & sArmy[tArmy]["ants"]
         end if
         delete variable sShot[tShot]
         Entity.Kill tShot
         next repeat
      end if
      add dx / d * kShotSpeed to sShot[tShot]["x"]
      add dy / d * kShotSpeed to sShot[tShot]["y"]
      add dz / d * kShotSpeed to sShot[tShot]["z"]
      SetObjectPosition tShot, sShot[tShot]["x"], sShot[tShot]["y"], sShot[tShot]["z"]
      Antack.Turn tShot, atan2(dx, dz), atan2(-dy, sqrt(dx * dx + dz * dz)) - pi / 2
   end repeat
end Antack.MoveShots
