## CARD SCRIPT: "Play.Demo"   THE SEA DEMO  (11 08 2026)
## Paste this into the script of card "Play.Demo".
## Boat and buoy bobbing on a grid sea, a field of drifting rocks, and a laser:
## click to fire, 100 points per rock. Rocks that drift into the boat derez.
## The engine sends these to the current card:
##   Game.OnStart  Game.OnUpdate  Game.OnClick x,y  Game.OnKill key  Game.OnStop
## Collision.Hit is not handled here, so the stack's default rule runs
## (anything with "hp" is destroyed).
## Start: Game.Select "Demo" then Game.Play.
######################################################################################

global gObjectTransforms

local sScore = 0

on Game.OnStart
   -- Back to the editor's camera and the original test objects (cube, cone ...).
   App.ResetScene

   -- Meshes: recipes only, nothing is stored in the stack.
   Mesh.Define "Sea", MeshGrid(6,6,100)
   Mesh.Define "Boat", Demo.BoatMesh()
   Mesh.Define "Rock", MeshPyramid(5,30,50)
   Mesh.Define "Buoy", MeshLathe("0,-30|6,-18|14,0|10,12|0,12", 6)

   Scene.AddObject "Sea","SeaLine",0,260,0,"#2E6F8E"
   Scene.AddObject "Boat","BoatLine",0,245,150,"white"
   Scene.SetBob "BoatLine",4,0.08,0.06
   Scene.AddObject "Buoy","BuoyLine",-180,250,200,"yellow"
   Scene.SetBob "BuoyLine",3,0.12,0.09

   -- A field of rocks, all sharing one "Rock" mesh and one orange graphic.
   repeat 8 times
      get Demo.SpawnRock()
   end repeat

   -- Rocks that drift into the boat are destroyed (stack default Collision.Hit).
   Collision.SetGroup "BoatLine","boat",45
   Collision.AddRule "rock","boat"

   put 0 into sScore
   Demo.ShowScore
end Game.OnStart

## Top the rock field back up every 3 seconds or so.
on Game.OnUpdate
   if Engine.Info("simTick") mod 90 is not 0 then exit Game.OnUpdate
   if Entity.Count("Rock") < 8 then get Demo.SpawnRock()
end Game.OnUpdate

## Click while playing = laser (engine's Weapon.FireAt).
on Game.OnClick pX,pY
   Weapon.FireAt pX,pY
end Game.OnClick

## The laser destroyed something.
on Game.OnKill pKey
   if pKey begins with "Rock" then
      add 100 to sScore
      Demo.ShowScore
   end if
end Game.OnKill

on Game.OnStop
end Game.OnStop

on Demo.ShowScore
   HUD.Set "score","SCORE" && format("%06d", sScore),12,12,14
end Demo.ShowScore

## A drifting, spinning, destructible rock somewhere on the sea (not on the boat).
function Demo.SpawnRock
   put GetObjectPosition("BoatLine","x") into tBoatX
   put GetObjectPosition("BoatLine","z") into tBoatZ
   repeat 10 times
      put random(600) - 300 into x
      put random(600) - 300 into z
      if sqrt((x - tBoatX)^2 + (z - tBoatZ)^2) > 140 then exit repeat
   end repeat
   put Entity.Spawn("Rock", x, 235, z, "orange") into tId
   SetObjectRotation tId,0,random(628)/100,0
   SetObjectRotationSpeed tId,0,(random(21)-11)/1000,0
   SetObjectVelocity tId,(random(13)-7)/10,0,(random(13)-7)/10
   put 1 into gObjectTransforms[tId]["hp"]
   Collision.SetGroup tId,"rock",30
   Scene.SetBounds tId,"-300,300,-300,300"
   return tId
end Demo.SpawnRock

## The boat: lofted hull, box cabin, wire mast, triangle sail. 31 edges.
## Deck at y=0, keel (half-size copy of the deck) at y=+25, mast top at y=-70. Bow to +Z.
function Demo.BoatMesh
   put MeshLoft("0,60|20,25|20,-50|-20,-50|-20,25", 0, "0,30|10,12.5|10,-25|-10,-25|-10,12.5", 25) into tBoat
   put Mesh.Merge(tBoat, Mesh.Transform(MeshBox(24,14,30),0,0,0,0,-7,-15,1)) into tBoat
   -- Mast: wire only.
   Mesh.AddVertex tBoat,0,0,10
   put the result into tFoot
   Mesh.AddVertex tBoat,0,-70,10
   put the result into tTop
   Mesh.AddLine tBoat,tFoot,tTop
   -- Sail: one triangle.
   Mesh.AddVertex tBoat,0,-66,12
   put the result into s1
   Mesh.AddVertex tBoat,0,-8,12
   put the result into s2
   Mesh.AddVertex tBoat,0,-8,45
   put the result into s3
   Mesh.AddFace tBoat,s1 && s2 && s3
   return tBoat
end Demo.BoatMesh

on opencard
try
   hide group "PauseMenuGroup"
   hide group "OptionsGroup"
end try
end opencard






--- Initial start up variables:
local theSIZE=40  -- "size" is resserved word in livecode 
local theMODE=0   -- "mode" is resserved word in livecode 

local CAMX=0 , CAMY=0 , CAMZ=-600   ----  Position of the camera.
local MOVEX=0 , MOVEY=0 , TheSCALE=1  ----  Image fixed to 'paper' so you can move around and 'scale' in/out.
local ANGLEX=0  , ANGLEY=0 , ANGLEZ=0   ----  Angle of rotation about the following pivots:
local PIVX=0 , PIVY=0 ,PIVZ=0    ----  Pivots x, y and z.

----  additional variables beyond tutorial
global gSceneTransforms  -- all the 3D attributes in one array
global gObjectTransforms -- the 3D attributes of an object
global gDebug  -- makes it easier to find my while bug hunting

global CenterX,CenterY ----  the center, or pivot point of the object(s)
local P1,P2,P3,P4,P5,P6,P7,P8 ----  the vertices that make the cube
local LoopIndex=1 ----  for tracking loop N position to identify circle vertice markers
local fXrot,fYrot,fZrot ----   values to modify angles each loop. "f" for float
local bShowVerticeIds=true

----  points of 3d objects
local CubePoints ----  store the whole cube in here
local CylinderPoints
local SpherePoints
local ConePoints

---- additions for 3D Cylinder, cone and sphere
----  for recursing the cylinder
local CylinderVertices

----  for recursing the cone
local ConeVertices

----  updated based on radio button press
local current3DPrimitive="Cube"

global gNearPlane
global gFocalLength
global gViewLeft,gViewTop
global gViewRight,gViewBottom

## 3D GEOMETRY MODEL
global gMeshVertices
global gMeshEdges
global gMeshFaces
global gCameraVertices
global gRenderPoints

## MOUSELOOK
global bMouseLook
global gCameraYaw
global gCameraPitch
global gMouseLookLastH
global gMouseLookLastV
global gMouseLookSensitivity
global gMouseDeltaX
global gMouseDeltaY

## 3D MOUSE SELECTION
local gSelectedGeometry = ""
local gSelectedObject = ""
local gSelectedFace = 0
local gSelectedV0 = 0
local gSelectedV1 = 0
local gSelectedV2 = 0
local gSelectedU = 0
local gSelectedV = 0
local gSelectedW = 0
local gSelectedLocalX = 0
local gSelectedLocalY = 0
local gSelectedLocalZ = 0
local gSelectedCameraX = 0
local gSelectedCameraY = 0
local gSelectedCameraZ = 0
global gSelectionHistory  -- Can't access locals from the Message Box, so Global it is!


## GAME AND EDITOR  -- Not entirely implemented yet
global bPlaying -- is the application running the game LOOP (as opposed to menus etc)
global bPaused -- has the game paused while playing?
global bEditor -- is the engine in editor mode, ie, can the user drag objects around the scene, should keysboard act differently?
global bMissile -- is the missile firing? (primitive caveman math missile removed, until mouse selection is fixed)

## GAME LOOP + FAST RENDERER (Phase 0/1, 11 08 2026)
constant kStepMS = 33 -- fixed simulation step, about 30 updates per second
local sLoopActive = false -- true while game.loop.tick is scheduling itself
local sLastMS, sAccumMS
local sFrameCount = 0, sFPSStamp, sFPS = 0, sEdgesDrawn = 0
local sCamM, sSceneCamM, sFrameT -- per-frame matrices, see Render.BeginFrame
local sProjK, sProjOffX, sProjOffY -- per-frame projection constants
local sMissileObj = "CubeLine"
local sSimTick = 0 -- counts game.update steps (bobbing etc.)
local sEntitySerial = 0 -- numbering for Entity.Spawn ids (Phase 3)
local sLastBatchGraphics -- graphics drawn last frame, so emptied ones get cleared
global gSceneObjects -- draw list, one "MeshName GraphicName" per line (Phase 2)
global gMeshCache -- cached meshes, see Mesh.Build
global gLogSelection -- set true to log UpdateSelectionMarker diagnostics into gSelectionHistory
----END OF GLOBAL & LOCAL DEFINITIONS

on init.globals
  put "" into gselectionHistory
  put false into bPlaying -- toggle simulation loop 
  put false into bPaused -- show pause menu, simulation may or may not continue
  put false into bEditor  -- mouse can move objects, edits save for init, editor UI will show (coming soon)
  put false into bMissile
  put empty into gSceneTransforms
  put empty into  gObjectTransforms
  put empty into gDebug
  -- Camera and projection settings
  put 1 into gNearPlane
  put 300 into gFocalLength

  -- Viewport boundaries
  put 0 into gViewLeft
  put 0 into gViewTop
  put 306 into gViewRight
  put 446 into gViewBottom

  -- Mesh data
  put empty into gMeshVertices
  put empty into gMeshEdges

  -- Transformed camera-space vertices
  put empty into gCameraVertices

  -- Projected screen coordinates
  put empty into gRenderPoints

  put false into bMouseLook
  put 3.14 into gCameraYaw -- radians
  put 0 into gCameraPitch
  put width of this stack/2 into gMouseLookLastH
  put height of this stack/2  into gMouseLookLastV
  put 0.003 into gMouseLookSensitivity
  put 0 into gMouseDeltaX
  put 0 into gMouseDeltaY
end init.globals

----  if things break, reset!
on init.locals
  --- Initial start up variables:
  put 40 into theSize 
  put 0 into theMODE
  put 0 into CAMX
  put 0 into CAMY
  put -600 into CAMZ  --300
  put 0 into MOVEX
  put 0 into MOVEY
  put 1   into TheSCALE
  put 0  into ANGLEX
  put 0 into ANGLEY
  put 0   into ANGLEZ
  put 0 into PIVX
  put 0 into PIVY
  put 0   into PIVZ
  SetAngles 0.01,0.01,0.01
  --SetCenterXY
  put true into bShowVerticeIds
end init.locals



on rawKeyDown theKey
  if the tool is not "browse tool" then
     pass rawKeyDown
  end if
  if thekey is 32 then 
     put View.NextPreset() into tName
     set the  label of btn "Next Preset"  to tName
     exit rawKeyDown
  end if
  Keyboard.handler theKey
  pass rawKeyDown
end rawKeyDown


on Keyboard.handler theKey
  if the tool is not "browse tool" then
     pass Keyboard.handler
  end if
  ----   Keys
  if theKey is  a number then put numtoChar(theKey) into tChar

  IF there is a button "TheValue" then  set the showName of button "TheValue" to true
  IF there is a button "theKey" then 
     set the label of button "theKey" to  theKey && tChar
     set the showName of button "TheKey" to true
  end if

  if tChar is a number then 
     Object.Angle.Keys tChar
     exit Keyboard.handler
  end if
  switch tChar
     case  "Cursor_Left" 
     case "j" 
        put  MOVEX-2  into  MOVEX

        put true into bKeyUpdate
        break
     case  "Cursor_Right"  
     case "l"
        put  MOVEX+2  into MOVEX 

        put true into bKeyUpdate
        break
     case  "Cursor_Up"  
     case "i"
        put  MOVEY-2  into  MOVEY 

        put true into bKeyUpdate
        break
     case  "Cursor_Down"  
     case "k"
        put  MOVEY+2  into  MOVEY 

        put true into bKeyUpdate
        break
     case  "["  
        put  theSCALE/1.02 into  theSCALE

        put true into bKeyUpdate 
        break 
     case  "]"  
        put  theSCALE*1.02 into  theSCALE 

        put true into bKeyUpdate
        break
     case  "f"  
        put  PIVX-2  into  PIVX 

        break
     case  "h"  
        put  PIVX+2  into  PIVX 

        break
     case  "t"  
        put  PIVY-2  into  PIVY 

        break
     case  "g"  
        put  PIVY+2  into  PIVY 

        break
     case  "c"  
        put  PIVZ-2  into  PIVZ 

        break
     case  "v"  
        put  PIVZ+2  into  PIVZ 

        break

     case  "Keypad_8"  
     case  "q" 

        put  CAMY-4  into  CAMY 

        put true into bKeyUpdate
        break
     case  "Keypad_2"  
     case  "e"  

        put  CAMY+4  into  CAMY 

        put true into bKeyUpdate
        break
     case "n"
        get Entity.SpawnRock()
        RENDER_VIEW
        break
     case "b"
        Selection.Kill
        RENDER_VIEW
        break
     case "p"
        Game.TogglePause
        break
     case "w"
        MoveCameraLocal "forward",4

        put true into bKeyUpdate
        break

     case "s"
        MoveCameraLocal "backward",4

        put true into bKeyUpdate
        break

     case "a"
        MoveCameraLocal "left",4

        put true into bKeyUpdate
        break

     case "d"
        MoveCameraLocal "right",4

        put true into bKeyUpdate
        break
        ----  additions to tutorial keys
  end switch
  if the shiftkey is down then
     switch tChar
        case  "X"  
           put  0  into  fxRot 

           put true into bKeyUpdate
           break
        case  "Y"  
           put  0  into  fyRot 

           put true into bKeyUpdate
           break
        case  "Z"  
           put  0  into  fzRot 

           put true into bKeyUpdate
     end switch
  else
     switch tChar
        case  "X"  
           put  fxRot+.1  into  fxRot 

           put true into bKeyUpdate
           break
        case  "Y"  
           put  fyRot+.1  into  fyRot 

           put true into bKeyUpdate
           break
        case  "Z"  
           put  fzRot+.1  into  fzRot 

           put true into bKeyUpdate
           break
     end switch
  end if

  if bKeyUpdate then RENDER_SCENE
end Keyboard.handler
