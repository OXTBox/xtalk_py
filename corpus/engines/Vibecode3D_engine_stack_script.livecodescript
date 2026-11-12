## VIBECOD3D GAME ENGINE IN LIVECODE 11 11 2026  5:30 AM #### 
----BEGIN DAILY DEVELOPER NOTES NOTEs TO CLAUDE AI 11/10/2026:
/*
 NEXT: bug-hunt the delete-and-rebuild of game cards (Game.Rebuild / Games.Rebuild,
 GAME_ENTITIES set: ["GameScripted"] and ["User"] per game).

 LIBRARIES: a card "LIB_<name>" holds a library script; Lib.Load / Lib.LoadAll copy
 it into an unsaved library stack "LIB_<name>_SCRIPT". Libraries have no GUI calls
 and no system-message handlers. LIB_LLM (LM Studio), LIB_DEVSERVER (Claude Code
 bridge: DevServer.Exec / DevServer.Eval below run what it is sent, in this script).

 THE "User" GROUP IS ALWAYS CARD-SIZED (Entities.UserGroup): four invisible 2x2
 anchors ATL/ATR/ABL/ABR in the card's corners, margins 0, lockLoc true. Its rect
 never changes, so nothing inside it moves and glows are never cropped by it.
 Entities.GroupUser groups loose user objects on the current card the same way.

 LIVECODE GOTCHAS FOUND THE HARD WAY
 - Setting a group's rect MOVES its contents (it does not just resize the frame).
   Never set the rect of a group that holds placed objects; put children back after.
 - A group can only be deleted with its cantDelete false, and deleting groups is
   safest from closeCard (Menu.Purge runs from the stack's closeCard).
 - Only top-level groups can be placed onto other cards. AudioPlayers now lives
   INSIDE the Viewport group (a background group), so it comes with every card
   that shows the Viewport and is never placed on its own.
 - "does not begin with" is not LiveCode: use not (x begins with y) or char ranges.
 - A one-line "if ... then x" followed by "else" takes that else as its own.
 - "engine" is reserved: engine graphics carry the custom property Entity = true.
 - Custom property names must start with a letter ("1983" -> "Preset_1983").
 - Always return to the empty customPropertySet after using a set.

 CARD SCRIPTS come from custom property sets:
   GAME_CARD_SCRIPTS: Canyon, Demo, Hunter, Simple_Test1, Simple_Test2
   EDIT_CARD_SCRIPTS: Trace, HUD
 save.card.script.to.set / load.card.script.from.set move scripts between them.

 CARDS
 Developer        code and break things
 Title            title / main menu (keeps its own PauseMenuGroup / OptionsGroup)
 Play.<game>      one per game: Viewport (background) + script from GAME_CARD_SCRIPTS
 Edit_HUD         HUD layouts per game (Game_Huds set)
 Edit_Viewport    whatever is put here goes into the Viewport (Viewport.AdoptFromEditCard)
 Edit_Title / Edit_Pause / Edit_Options   menu templates (TemplateTitle / TemplatePause
                  / TemplateOptions), copied in by Menu.Open, deleted by Menu.Purge
 Edit_Procedurals parameters for procedural objects (Procedural_Geometry set)
 Edit_Entities    entity game properties (nothing yet)
 Edit_Emitters    procedurals that spawn / derez things (nothing yet)
 Edit_Pathing     paths on the map, procedures, behaviours (nothing yet)
 Edit_Styles      colour / line / opacity schemes (ViewPresets set)
 Edit_Level       copy of a game for placing / flagging objects (nothing yet)
 Edit_Trace       2480 lines, to discuss
 (Edit_Viewports, plural, is an empty duplicate: can be deleted.)

 THREEDOTS MENU (button in the Viewport), filled by Menu.Threedots.Build:
 Developer | Reset | Play | Game > games | Edit > Level, Bitmap, HUD, Procedurals, Trace
 Style > 1983, Arcade, Fast, Vectrex, -, Save Preset, Save As... | View Bands > 1-4
 Glow > On, Off
 */
---- BEGIN 3D GAME ENGINE IN LIVECODE  STACK SCRIPT
---- ## These initial values From 3D CUBE in 2D Tutorial which is mostly irrevelevant now but the Variables persist
---- ## https://www.skytopia.com/project/cube/cube.html
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
global bDeveloper -- is the user on the Developer card?
global gCurrentGame  -- was set Global once in Game.Select and never used or accesible?

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
## Phase 5
constant kMaxParticles = 200
local sSceneM -- scene rotation matrix for this frame (see Render.FrameMatrices)
local sCollisionRules -- one "groupA groupB" per line
local sPCount = 0 -- live particles
local sPX,sPY,sPZ,sHX,sHY,sHZ,sVX,sVY,sVZ,sLife,sPGfx,sPG,sSC,sSS,sTC,sTS -- particle arrays
local sLaserX,sLaserY,sLaserFrames = 0
## Phase 4
local sView -- current view settings (see View.PresetDefaults)
local sViewBands = 1, sViewNear = 450, sViewFar = 950 -- fast copies for the renderer
local sStyled, sBandMade, sBandBase, sOrigColor -- per-graphic styling bookkeeping
local sFont, sHUD, sScore = 0 -- vector font, HUD items, demo score
## Game cards, derez, audio, menus
constant kDerezSlots = 8 -- how many derez effects can run at once
constant kDerezFrames = 14 -- how long one lasts
local sDerezNext = 0, sDerezAge, sDerezRect
local sAudioReady = false, sMusicPlayers, sCurrentSong
local sSoundList, sSoundNext, sSoundOff = false
local currentMusicVolume = 75, currentFXVolume = 75
local bFullScreen = false, bAntiAlias = true
local sHudTest = false -- true while testing a game from Edit_HUD
local sPreparedGame -- the game whose card Game.Prepare.Card has made ready
local sEscMS = 0 -- when Escape last acted (escapekeyDown)
local sHudTemplate -- LiveCode's template properties per control type (HUD storage)
global gSceneObjects -- draw list, one "MeshName GraphicName" per line (Phase 2)
global gMeshCache -- cached meshes, see Mesh.Build
global gLogSelection -- set true to log UpdateSelectionMarker diagnostics into gSelectionHistory
global bKeyDown -- have to stop repeated activations of key called scripts

----END OF STACK SCRIPT GLOBAL & LOCAL DEFINITIONS

--init 
on PreOpenStack
   APP.init
end PreOpenStack

on APP.init
   init.globals
   init.locals

   Engine.Init
   Viewport.Ensure -- rebuild the shared 3D group if it was deleted
   init.object.Transforms
   
   -- objects only needed to be defined once and stored in stack
   -- init.object.definitions --procedural 3D objects
   
   -- 3D objects are draw by Livecode graphics objects
   init.graphic.objects.for.geometry
   Mesh.Invalidate -- rebuild all cached meshes from the stack properties
   init.scene.objects -- procedural meshes + the draw list
   View.Init -- vector look: presets, vector font, HUD
   choose browse tool
   RENDER_SCENE 
   Menu.Threedots.Build -- games, edit cards and presets from the stack
   Lib.LoadAll -- every LIB_ card becomes a library stack
   -- Claude Code's bridge (tools/lc.sh): IDE only, never in a standalone.
--   if the environment is "development" and there is a card "LIB_DEVSERVER" then DevServer.Start
MCP.Attach   -- LIB_MCP 11 11 2026 738pm
end APP.init

on init.graphic.objects.for.geometry
   put "cubeLine,coneLine,cylinderLine,gridLine" into tObjs
   put "green,cyan,magenta,purple" into tcolors
   repeat with i = 1 to 4
      put item i of tObjs into tName
      Scene.NewLineGraphic tName
      if there is a graphic tName then set the foregroundcolor of graphic tName to item i of tColors
      put item i of tColors into sOrigColor[tName]
   end repeat
end init.graphic.objects.for.geometry


on init.UI
if the  short name of this card is "developer" then
   set the label of button "TheKey" to ""
   set the showName of button "TheKey" to false
   set the label of button "TheValue" to ""
   set the showName of button "TheValue" to false
  end if
end init.UI

on init.game.engine
   global bPlaying
   global bPaused
   global bEditor
   global bMissile
   put false into bPlaying -- toggle simulation loop 
   put false into bPaused -- show pause menu, simulation may or may not continue
   put false into bEditor  -- mouse can move objects, edits save for init, editor UI will show (coming soon)
   put false into bMissile  -- is the missile active? update!
end init.game.engine

on init.globals
	put false into bKeyDown
   put empty  into gCurrentGame
   put false into bDeveloper  -- game updates while in developer mode kill script editing
   put "" into gSelectionHistory
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

on Engine.Init
   -- The closest distance at which we allow drawing.
   put 1 into gNearPlane
   
   -- Controls perspective magnification.
   put 300 into gFocalLength
   
   -- Screen boundaries, relative to the stack.
   put 0 into gViewLeft
   put 0 into gViewTop
   put the width of stack (the mainStack of this stack) into gViewRight
   put the height of stack (the mainStack of this stack) into gViewBottom
end Engine.Init

--B. TransformVertex()
function TransformVertex tX,tY,tZ,tWorldX,tWorldY,tWorldZ
   
   -- =========================================================
   -- INPUT:
   --   tX,tY,tZ = vertex coordinates in the scene's input space.
   --
   -- PIVX/Y/Z = scene rotation pivot.
   -- ANGLEX/Y/Z = scene rotation angles, in radians.
   -- CAMX/Y/Z = scene translation applied after rotation.
   --
   -- ROTATION ORDER:
   --   Z, then Y, then X.
   --
   -- OUTPUT:
   --   Transformed coordinates before camera orientation.
   -- =========================================================
   
   -- 1. Move the vertex relative to the scene rotation pivot.
   put tX-PIVX into tDX
   put tY-PIVY into tDY
   put tZ-PIVZ into tDZ
   
   -- 2. Rotate around Z.
   put tDX*cos(ANGLEZ)-tDY*sin(ANGLEZ) into tX1
   put tDX*sin(ANGLEZ)+tDY*cos(ANGLEZ) into tY1
   put tDZ into tZ1
   
   -- 3. Rotate around Y.
   put tX1*cos(ANGLEY)+tZ1*sin(ANGLEY) into tX2
   put -tX1*sin(ANGLEY)+tZ1*cos(ANGLEY) into tZ2
   put tY1 into tY2
   
   -- 4. Rotate around X.
   put tY2*cos(ANGLEX)-tZ2*sin(ANGLEX) into tY3
   put tY2*sin(ANGLEX)+tZ2*cos(ANGLEX) into tZ3
   put tX2 into tX3
   
   -- 5. Restore the pivot and apply scene translation.
   put tX3+PIVX+CAMX into tX3
   put tY3+PIVY+CAMY into tY3
   put tZ3+PIVZ+CAMZ into tZ3
   
   -- 6. Return transformed coordinates.
   return tX3 && tY3 && tZ3
   --   CAMX/Y/Z are translations in the transformed coordinate system. 
   --   They are not themselves perspective calculations. 
   --   Perspective division occurs later in ProjectVertex.
   
   --   Also, tWorldX/Y/Z are currently unused parameters. 
   --   We should eventually remove them if no existing calls depend on the six-argument signature.
end TransformVertex

--This is the first major fix.
--It examines both endpoints of a line before projection.
--There are three possible outcomes:
--1. Both endpoints are in front of the near plane: keep the line.
--2. Both endpoints are behind it: discard the line.
--3. One endpoint is behind it: calculate the intersection and shorten the line.
function ClipLineToNearPlane tX1,tY1,tZ1,tX2,tY2,tZ2
   
   put gNearPlane into tNear
   
   -- Both endpoints are behind the camera's near plane.
   if tZ1 < tNear and tZ2 < tNear then
      return empty
   end if
   
   -- First endpoint is behind the near plane.
   if tZ1 < tNear then
      
      put (tNear-tZ1)/(tZ2-tZ1) into tRatio
      
      put tX1+(tX2-tX1)*tRatio into tX1
      put tY1+(tY2-tY1)*tRatio into tY1
      put tNear into tZ1
      
   end if
   
   -- Second endpoint is behind the near plane.
   if tZ2 < tNear then
      
      put (tNear-tZ1)/(tZ2-tZ1) into tRatio
      
      put tX1+(tX2-tX1)*tRatio into tX2
      put tY1+(tY2-tY1)*tRatio into tY2
      put tNear into tZ2
      
   end if
   
   return tX1 && tY1 && tZ1 && tX2 && tY2 && tZ2
   
end ClipLineToNearPlane


--D. ProjectVertex()
--This is the conversion from camera-space XYZ into screen-space XY.
function ProjectVertex tX,tY,tZ
   
   -- Never divide by zero or project behind the near plane.
   if tZ < gNearPlane then return empty
   
   if theScale = 0 then put 0.01 into theScale
   
   -- Perspective projection.
   put (tX*gFocalLength)/tZ into tScreenX
   put (tY*gFocalLength)/tZ into tScreenY
   
   -- Apply zoom.
   put tScreenX/theScale into tScreenX
   put tScreenY/theScale into tScreenY
   
   ## MOVEX/Y/Z are screen-space offsets applied after projection. 
   ## They move the rendered image without changing its perspective.
   -- Apply screen position and object movement.
   put tScreenX+CenterX+MOVEX into tScreenX
   put tScreenY+CenterY+MOVEY into tScreenY
   
   return tScreenX && tScreenY
   
end ProjectVertex

--E. RenderEdge()
--We also need viewport clipping. Near-plane clipping prevents extreme perspective values,
-- but it doesn't prevent a perfectly valid line from extending beyond the screen.
--We will use the Liang-Barsky line-clipping algorithm.
--First, add this helper:
-- Clip a projected line against the viewport using Liang-Barsky.

function ClipLineToViewport tX1,tY1,tX2,tY2
   
   put tX2-tX1 into tDX
   put tY2-tY1 into tDY
   
   -- Enter and leave positions along the line.
   put 0 into tEnter
   put 1 into tLeave
   
   -- Calculate the four boundary tests.
   put -tDX into tP[1]
   put tDX into tP[2]
   put -tDY into tP[3]
   put tDY into tP[4]
   
   put tX1-gViewLeft into tQ[1]
   put gViewRight-tX1 into tQ[2]
   put tY1-gViewTop into tQ[3]
   put gViewBottom-tY1 into tQ[4]
   
   -- Test all four viewport boundaries.
   repeat with tI = 1 to 4
      
      put tP[tI] into tCurrentP
      put tQ[tI] into tCurrentQ
      
      -- Parallel to this boundary?
      if tCurrentP = 0 then
         
         -- Parallel and outside means reject the line.
         if tCurrentQ < 0 then
            return empty
         end if
         
      else
         
         -- Calculate the intersection position.
         put tCurrentQ/tCurrentP into tR
         
         if tCurrentP < 0 then
            
            -- Potentially entering the viewport.
            if tR > tEnter then
               put tR into tEnter
            end if
            
         else
            
            -- Potentially leaving the viewport.
            if tR < tLeave then
               put tR into tLeave
            end if
            
         end if
         
         -- The line misses the viewport.
         if tEnter > tLeave then
            return empty
         end if
         
      end if
      
   end repeat
   
   -- Calculate the clipped endpoints.
   put tX1+tEnter*tDX into tNewX1
   put tY1+tEnter*tDY into tNewY1
   
   put tX1+tLeave*tDX into tNewX2
   put tY1+tLeave*tDY into tNewY2
   
   return tNewX1 && tNewY1 && tNewX2 && tNewY2
   
end ClipLineToViewport

## Now the edge renderer:
on RenderEdge tVertexA,tVertexB
   global gRenderPoints
   global gCameraVertices
   -- Retrieve the transformed endpoints.
   put gCameraVertices[tVertexA] into tA
   put gCameraVertices[tVertexB] into tB
   
   if tA is empty or tB is empty then exit RenderEdge
   
   put word 1 of tA into tX1
   put word 2 of tA into tY1
   put word 3 of tA into tZ1
   
   put word 1 of tB into tX2
   put word 2 of tB into tY2
   put word 3 of tB into tZ2
   
   -- Clip against the camera's near plane.
   put ClipLineToNearPlane(tX1,tY1,tZ1,tX2,tY2,tZ2) into tClipped
   
   if tClipped is empty then exit RenderEdge
   
   put word 1 of tClipped into tX1
   put word 2 of tClipped into tY1
   put word 3 of tClipped into tZ1
   put word 4 of tClipped into tX2
   put word 5 of tClipped into tY2
   put word 6 of tClipped into tZ2
   
   -- Project both endpoints.
   put ProjectVertex(tX1,tY1,tZ1) into tScreenA
   put ProjectVertex(tX2,tY2,tZ2) into tScreenB
   
   if tScreenA is empty or tScreenB is empty then exit RenderEdge
   
   put word 1 of tScreenA into tX1
   put word 2 of tScreenA into tY1
   put word 1 of tScreenB into tX2
   put word 2 of tScreenB into tY2
   
   put "Viewport: " & gViewLeft & comma & gViewTop & comma & gViewRight & comma & gViewBottom into tDebug
   --put tDebug
   -- Clip against the actual drawing area.
   put ClipLineToViewport(tX1,tY1,tX2,tY2) into tScreenLine
   
   if tScreenLine is empty then exit RenderEdge
   
   -- Format the two endpoints as a separate line segment.
   put cr & (word 1 of tScreenLine) & comma & (word 2 of tScreenLine) into tRenderLine
   
   put cr & (word 3 of tScreenLine) & comma & (word 4 of tScreenLine) & cr & cr after tRenderLine
   
   -- Add the segment to the drawing buffer.
   put tRenderLine after gRenderPoints
end RenderEdge

--One implementation note: the viewport helper uses dynamically constructed variable names for its four clipping boundaries. That is legal LiveCode do syntax, but I would eventually replace it with explicit boundary tests if you want to optimize this for large OBJ meshes.
--F. RenderMesh()
--This is the replacement for both CUBE_LOOP and OBJ_LOOP.

--It does two passes:
--- Pass 1: Transform every vertex and remember its camera-space position.
--- Pass 2: Draw only the edges defined by the mesh.
on RenderMesh tVertices,tEdges,tGraphicName,tObjectName
   global gRenderPoints
   global gMeshVertices
   global gMeshEdges
   global gCameraVertices
   
   -- Reset the drawing buffer.
   put empty into gRenderPoints
   put empty into gCameraVertices
   
   -- Use the common screen center.
   put (the width of this stack/2) into CenterX
   put (the height of this stack/2) into CenterY
   
   -- Retrieve this object's world position.
   put GetObjectPosition(tObjectName,"x") into tWorldX
   put GetObjectPosition(tObjectName,"y") into tWorldY
   put GetObjectPosition(tObjectName,"z") into tWorldZ
   -- Retrieve this object's local rotation.
   put GetObjectRotation(tObjectName) into tObjectRotation
   
   set itemDel to comma
   put item 1 of tObjectRotation into tRotX
   put item 2 of tObjectRotation into tRotY
   put item 3 of tObjectRotation into tRotZ
   
   -- PASS 1: Transform every vertex exactly once.
   repeat with tI = 1 to the number of lines of tVertices
      put line tI of tVertices into tVertex
      if tVertex is empty then next repeat
      
      put word 1 of tVertex into tX
      put word 2 of tVertex into tY
      put word 3 of tVertex into tZ
      -- Apply this object's local rotation.
      put RotateObjectVertex(tX,tY,tZ,tRotX,tRotY,tRotZ) into tVertex
      
      -- Apply existing scene rotation and CAM translation.
      put TransformVertex(word 1 of tVertex,word 2 of tVertex,word 3 of tVertex) into tCameraVertex
      
      -- Apply this object's world translation.
      put word 1 of tCameraVertex + tWorldX into tX
      put word 2 of tCameraVertex + tWorldY into tY
      put word 3 of tCameraVertex + tWorldZ into tZ
      
      -- Apply inverse camera orientation.
      put RotateCameraVertex(tX,tY,tZ) into tCameraVertex
      
      -- Store the final camera-space vertex.
      put tCameraVertex into gCameraVertices[tI]
   end repeat
   -- PASS 2: Draw the edges connecting those vertices.
   repeat with tI = 1 to the number of lines of tEdges
      
      put line tI of tEdges into tEdge
      if tEdge is empty then next repeat
      
      put word 1 of tEdge into tA
      put word 2 of tEdge into tB
      
      RenderEdge tA,tB
      
   end repeat
   
   -- One graphic receives the complete mesh.
   set the points of graphic tGraphicName to gRenderPoints
   
end RenderMesh

--G. BuildMeshFromXYZArray()
--This small adapter allows us to retain your existing XYZCubeArray, XYZCylinderArray, etc.
--It converts your existing coordinate arrays into the new engine's simpler vertex format.
on BuildMeshFromXYZArray tObject,tVertexCount,tEdges
   put empty into gMeshVertices
   repeat with tI = 1 to tVertexCount
      put getXYZ(tObject,"X",tI) into tX
      put getXYZ(tObject,"Y",tI) into tY
      put getXYZ(tObject,"Z",tI) into tZ
      put tX && tY && tZ & cr after gMeshVertices
   end repeat
   --put "debug: BuildMeshFromXYZArray = " & cr & gMeshVertices
   put tEdges into gMeshEdges
   set the customPropertySet of graphic (tObject &"line") to empty
   set the MeshEdges of graphic (tObject &"line") to gMeshEdges
   set the MeshVertices of graphic (tObject &"line") to gMeshVertices
end BuildMeshFromXYZArray

--H. The cube becomes an ordinary mesh
--Here is the important part.
--Your cube already has eight vertices. We simply define the twelve connections between them.
on RenderCube
   put 8 into tVertexCount
   -- Each line identifies two connected vertex numbers.
   put "1 3" & cr into tEdges
   put "1 2" & cr after tEdges
   put "1 5" & cr after tEdges
   put "2 4" & cr after tEdges
   put "2 6" & cr after tEdges
   put "3 4" & cr after tEdges
   put "4 8" & cr after tEdges
   put "5 6" & cr after tEdges
   put "5 7" & cr after tEdges
   put "6 8" & cr after tEdges
   put "7 3" & cr after tEdges
   put "7 8" after tEdges
   -- Phase 1: cached mesh + matrix renderer. (Old path kept below for reference.)
   RenderMeshFast "Cube","CubeLine"
   --BuildMeshFromXYZArray "Cube",tVertexCount,tEdges
   --RenderMesh gMeshVertices,gMeshEdges,"CubeLine","CubeLine"
end RenderCube

on RenderCone
   -- Phase 1: cached mesh + matrix renderer.
   RenderMeshFast "Cone","ConeLine"
end RenderCone

--RenderCube preserves your original cube topology.
--The same approach works for your other primitives. Each object needs its own edge list.
--For example:
on RenderCylinder
   -- Phase 1: cached mesh + matrix renderer.
   RenderMeshFast "Cylinder","CylinderLine"
end RenderCylinder

----This helper deliberately reproduces the renderer's existing transform order:
----1. Object-local rotation, Z-Y-X.
----2. Scene transform through TransformVertex.
----3. Object world-position offset.
----4. Camera yaw and pitch through RotateCameraVertex.
----It accepts the already-built vertex coordinates, so it never accesses the source XYZ arrays.

## Transform one mesh vertex into camera-space coordinates.
function TransformRayVertex pX,pY,pZ,pRotX,pRotY,pRotZ,pWorldX,pWorldY,pWorldZ
   -- Object-local rotation: Z, then Y, then X.
   -- Rotate around Z.
   put pX*cos(pRotZ)-pY*sin(pRotZ) into tX1
   put pX*sin(pRotZ)+pY*cos(pRotZ) into tY1
   put pZ into tZ1
   -- Rotate around Y.
   put tX1*cos(pRotY)+tZ1*sin(pRotY) into tX2
   put -tX1*sin(pRotY)+tZ1*cos(pRotY) into tZ2
   put tY1 into tY2
   -- Rotate around X.
   put tY2*cos(pRotX)-tZ2*sin(pRotX) into tY3
   put tY2*sin(pRotX)+tZ2*cos(pRotX) into tZ3
   put tX2 into tX3
   -- Apply the existing scene transform.
   put TransformVertex(tX3,tY3,tZ3) into tSceneVertex
   put word 1 of tSceneVertex into tX
   put word 2 of tSceneVertex into tY
   put word 3 of tSceneVertex into tZ
   -- Add the object's world position.
   add pWorldX to tX
   add pWorldY to tY
   add pWorldZ to tZ
   -- Apply the existing camera orientation.
   put RotateCameraVertex(tX,tY,tZ) into tCameraVertex
   return tCameraVertex
end TransformRayVertex

## RayTriangleIntersect  (Moller-Trumbore)
## Ray from (pOx,pOy,pOz) along (pDx,pDy,pDz) against one triangle.
## Two-sided: does not reject triangles by winding / backface orientation.
## Returns "distance U V" (U,V = barycentric coordinates), or empty for no hit.
## NOTE: since Phase 2, picking uses RayPolygonHit (whole n-gons, no triangulation).
## Kept as a utility.
function RayTriangleIntersect pOx,pOy,pOz,pDx,pDy,pDz,pV0X,pV0Y,pV0Z,pV1X,pV1Y,pV1Z,pV2X,pV2Y,pV2Z
   --put  "@RayTriangleIntersect gdebug" && pOx,pOy,pOz,pDx,pDy,pDz,pV0X,pV0Y,pV0Z,pV1X,pV1Y,pV1Z,pV2X,pV2Y,pV2Z &cr & cr after gDebug
   
   -- Triangle edges.
   put pV1X-pV0X into tE1X
   put pV1Y-pV0Y into tE1Y
   put pV1Z-pV0Z into tE1Z
   
   put pV2X-pV0X into tE2X
   put pV2Y-pV0Y into tE2Y
   put pV2Z-pV0Z into tE2Z
   
   -- Cross product: ray direction x edge 2.
   put pDy*tE2Z-pDz*tE2Y into tHX
   put pDz*tE2X-pDx*tE2Z into tHY
   put pDx*tE2Y-pDy*tE2X into tHZ
   
   -- Determinant.
   put tE1X*tHX+tE1Y*tHY+tE1Z*tHZ into tA
   
   if abs(tA) < 0.000001 then return empty
   
   put 1/tA into tF
   
   -- Vector from vertex 0 to ray origin.
   put pOx-pV0X into tSX
   put pOy-pV0Y into tSY
   put pOz-pV0Z into tSZ
   
   -- First barycentric coordinate.
   put tF*(tSX*tHX+tSY*tHY+tSZ*tHZ) into tU
   
   if tU < 0 or tU > 1 then return empty
   
   -- Cross product: S x edge 1.
   put tSY*tE1Z-tSZ*tE1Y into tQX
   put tSZ*tE1X-tSX*tE1Z into tQY
   put tSX*tE1Y-tSY*tE1X into tQZ
   
   -- Second barycentric coordinate.
   put tF*(pDx*tQX+pDy*tQY+pDz*tQZ) into tV
   
   if tV < 0 or tU+tV > 1 then return empty
   
   -- Distance along the ray.
   put tF*(tE2X*tQX+tE2Y*tQY+tE2Z*tQZ) into tDistance
   
   if tDistance <= 0.000001 then return empty
   
   return tDistance && tU && tV
   
end RayTriangleIntersect

## RayCastObject  (Phase 2: whole polygons, no triangulation)
## Casts a camera-space ray (origin = camera) against every face of one object.
## Reads the mesh from the cache (Mesh.Get) and transforms it exactly like the
## renderer (Xform.Object), so what you see is what you pick.
## Returns:
##   distance faceIndex v0 v1 v2 0 0 hitX hitY hitZ localX localY localZ
## v0 v1 v2 are the face's first three vertex indices; the two 0s are where the
## old triangle U,V used to be (kept so test.Raycast's word positions still match).
## hit = camera space; local = mesh-local (used by UpdateSelectionMarker).
function RayCastObject pGeometry,pObject,pRayDX,pRayDY,pRayDZ
   if pObject is empty or pGeometry is empty then return empty
   if gObjectTransforms[pObject] is not an array then return empty
   put Mesh.Get(pGeometry) into tMesh
   put tMesh["count"] into tCount
   if tCount < 1 or tMesh["faces"] is empty then return empty
   
   Render.FrameMatrices
   set itemDel to comma
   put Xform.Object(pObject) into tXf
   put item 1 of tXf into m1
   put item 2 of tXf into m2
   put item 3 of tXf into m3
   put item 4 of tXf into m4
   put item 5 of tXf into m5
   put item 6 of tXf into m6
   put item 7 of tXf into m7
   put item 8 of tXf into m8
   put item 9 of tXf into m9
   put item 10 of tXf into t1
   put item 11 of tXf into t2
   put item 12 of tXf into t3
   
   -- Every vertex to camera space.
   put tMesh["vx"] into tVX
   put tMesh["vy"] into tVY
   put tMesh["vz"] into tVZ
   repeat with i = 1 to tCount
      put tVX[i] into x
      put tVY[i] into y
      put tVZ[i] into z
      put m1*x + m2*y + m3*z + t1 into tCX[i]
      put m4*x + m5*y + m6*z + t2 into tCY[i]
      put m7*x + m8*y + m9*z + t3 into tCZ[i]
   end repeat
   
   -- Nearest face.
   put 1.0e+30 into tBest
   put empty into tBestFace
   put 0 into tFaceIndex
   repeat for each line tFace in tMesh["faces"]
      add 1 to tFaceIndex
      put RayPolygonHit(tFace,tCX,tCY,tCZ,pRayDX,pRayDY,pRayDZ) into tDist
      if tDist is not empty and tDist < tBest then
         put tDist into tBest
         put tFaceIndex into tBestIndex
         put tFace into tBestFace
      end if
   end repeat
   if tBestFace is empty then return empty
   
   -- Camera-space hit point.
   put tBest * pRayDX into tHX
   put tBest * pRayDY into tHY
   put tBest * pRayDZ into tHZ
   
   -- Back to mesh-local: local = transpose(M) * (hit - T).
   put tHX - t1 into tQX
   put tHY - t2 into tQY
   put tHZ - t3 into tQZ
   put m1*tQX + m4*tQY + m7*tQZ into tLX
   put m2*tQX + m5*tQY + m8*tQZ into tLY
   put m3*tQX + m6*tQY + m9*tQZ into tLZ
   
   return tBest && tBestIndex && (word 1 of tBestFace) && (word 2 of tBestFace) && (word 3 of tBestFace) \
         && 0 && 0 && tHX && tHY && tHZ && tLX && tLY && tLZ
end RayCastObject



#### Ray cast multiple objects
----For now, use explicit geometry/instance pairs.
---- This also gives us a straightforward way to introduce uniquely identified imported objects later.
---- The input is a line-delimited list of pairs,
---- with a space between each geometry label and graphic instance:
on test.Raycast
   -- Everything in the draw list is pickable.
   put gSceneObjects into tObjects
   put the mouseLoc into tMouse
   put "@test.raycast gdebug start" & cr & cr into gDebug
   put the mouseH,the mouseV,CenterX,CenterY,MOVEX,MOVEY,theScale,gFocalLength into tiTems
   put "put ScreenToCameraRay(" & tiTems& ") tRay= "  &cr after gDebug
   put ScreenToCameraRay(item 1 of tMouse,item 2 of tMouse,CenterX,CenterY,MOVEX,MOVEY,theScale,gFocalLength) into tRay
   put tRay & cr &cr after gDebug
   
   if tRay is not empty then
      
      put RayCastScene(tObjects,word 1 of tRay,word 2 of tRay,word 3 of tRay) into tHit
      put "@test.raycast gdebug tHit:" & cr &  tHit &cr & cr after gDebug
      if tHit is not empty then
         put word 1 of tHit into tGeometry
         put word 2 of tHit into tObject
         put word 3 of tHit into tDistance
         put word 4 of tHit into tFace
         put word 5 of tHit into tV0
         put word 6 of tHit into tV1
         put word 7 of tHit into tV2
         put word 8 of tHit into tU
         put word 9 of tHit into tV
         put word 10 of tHit into tHitX
         put word 11 of tHit into tHitY
         put word 12 of tHit into tHitZ
         put tHitX into gSelectedCameraX
         put tHitY into gSelectedCameraY
         put tHitZ into gSelectedCameraZ
         
         ## You can now also extract the mesh-local hit:
         put word 13 of tHit into tLocalX
         put word 14 of tHit into tLocalY
         put word 15 of tHit into tLocalZ
         
         -- Retain the current hit as the selected object.
         put tGeometry into gSelectedGeometry
         put tObject into gSelectedObject
         
         put tFace into gSelectedFace
         
         put tV0 into gSelectedV0
         put tV1 into gSelectedV1
         put tV2 into gSelectedV2
         
         put tU into gSelectedU
         put tV into gSelectedV
         put 1-tU-tV into gSelectedW
         
         put tLocalX into gSelectedLocalX
         put tLocalY into gSelectedLocalY
         put tLocalZ into gSelectedLocalZ
         
         put "CURRENT SELECTION:" & cr & \
               "Geometry: " & gSelectedGeometry & cr & \
               "Instance: " & gSelectedObject & cr & \
               "Face: " & gSelectedFace & cr & \
               "Local point: " & \
               gSelectedLocalX && gSelectedLocalY && gSelectedLocalZ & cr & cr after gDebug
         
         put 1-tU-tV into tW
         
         put "tGeometry,tObject,tDistance,tFace,tV0,tV1,tV2,tU,tV,tHitX,tHitY,tHitZ,tLocalX,tLocalY,tLocalZ" into tCols
         repeat for each item I in tCols
            do "put" && I &&  "into tVar"
            put I && tVar & cr after gDebug
         end repeat
         put "Triangle barycentric coordinates:" & cr & \
               "W: " & tW & cr & \
               "U: " & tU & cr & \
               "V: " & tV & cr &cr after gDebug
      else
         put empty into gSelectedGeometry
         put empty into gSelectedObject
         put 0 into gSelectedFace
         put 0 into gSelectedV0
         put 0 into gSelectedV1
         put 0 into gSelectedV2
         put 0 into gSelectedU
         put 0 into gSelectedV
         put 0 into gSelectedW
         put 0 into gSelectedLocalX
         put 0 into gSelectedLocalY
         put 0 into gSelectedLocalZ
      end if -- thit 
   end if -- tray
   
   Render_Scene
   UI.update.status.display
   --put gDebug &cr & cr &  "@test.rayacast gdebug end" 
end test.Raycast


## UpdateSelectionMarker IS THE CURRENT STAGE OF APPLICATION PRODUCTION 11 07 2026 2:25 PM PST
## there are bugs to debug
#### The transformation order deliberately matches your existing rendering pipeline:
----1. `RotateObjectVertex` — object-local rotation.
----2. `TransformVertex` — scene rotation and CAM translation.
----3. Add object world position.
----4. `RotateCameraVertex` — camera orientation.
----5. `ProjectVertex` — screen projection.
## UpdateSelectionMarker
## Transforms the selected mesh-local hit point into screen coordinates
## and positions the selection marker.
## UpdateSelectionMarker
## Converts the selected mesh-local point into screen coordinates.
## UpdateSelectionMarker
## Converts the selected mesh-local hit point into screen coordinates.

on UpdateSelectionMarker
   if there is not a graphic "SelectionMarker" then exit UpdateSelectionMarker
   if gSelectedObject is empty then
      set the visible of graphic "SelectionMarker" to false
      exit UpdateSelectionMarker
   end if
   
   -- Same transform the renderer used this frame (Render.BeginFrame ran first).
   set itemDel to comma
   put Xform.Object(gSelectedObject) into tXf
   put gSelectedLocalX into x
   put gSelectedLocalY into y
   put gSelectedLocalZ into z
   put (item 1 of tXf)*x + (item 2 of tXf)*y + (item 3 of tXf)*z + (item 10 of tXf) into tCheckX
   put (item 4 of tXf)*x + (item 5 of tXf)*y + (item 6 of tXf)*z + (item 11 of tXf) into tCheckY
   put (item 7 of tXf)*x + (item 8 of tXf)*y + (item 9 of tXf)*z + (item 12 of tXf) into tCheckZ
   
   -- Diagnostics: right after a click the differences should be ~0.
   -- (Off by default: put true into gLogSelection to turn on.)
   if gLogSelection is true then put "Original camera hit " && gSelectedObject &":"  && \
         gSelectedCameraX && gSelectedCameraY && gSelectedCameraZ & cr & \
         "Difference:" && \
         tCheckX-gSelectedCameraX && \
         tCheckY-gSelectedCameraY && \
         tCheckZ-gSelectedCameraZ & cr after gSelectionHistory
   
   -- Project the camera-space point onto the screen.
   put ProjectVertex(tCheckX,tCheckY,tCheckZ) into tScreenPoint
   if tScreenPoint is empty then
      set the visible of graphic "SelectionMarker" to false
      exit UpdateSelectionMarker
   end if
   set the loc of graphic "SelectionMarker" to \
         word 1 of tScreenPoint,word 2 of tScreenPoint
   set the visible of graphic "SelectionMarker" to true
end UpdateSelectionMarker

on debug.clear
   put empty into gDebug
end debug.clear

## Cast the center-screen ray against a list of objects.
## Returns the nearest object hit and its triangle information.
function RayCastScene pObjects,pRayDX,pRayDY,pRayDZ
   
   put empty into tBestHit
   put 1.0e+30 into tBestDistance
   
   repeat for each line tObjectPair in pObjects
      
      if tObjectPair is not empty then
         
         put word 1 of tObjectPair into tGeometry
         put word 2 of tObjectPair into tObject
         
         put RayCastObject(tGeometry,tObject,pRayDX,pRayDY,pRayDZ) into tHit
         
         if tHit is not empty then
            
            put word 1 of tHit into tDistance
            
            if tDistance < tBestDistance then
               
               put tDistance into tBestDistance
               
               -- Include geometry and instance names in the result.
               put tGeometry && tObject && tHit into tBestHit
               
            end if
            
         end if
         
      end if
      
   end repeat
   
   return tBestHit
   
end RayCastScene


##  TransformVertex rotates around the pivot, restores the pivot, and adds CAMX/Y/Z.
##  We must undo those operations in precisely the opposite order.
##  1. CameraToWorldPoint
##  This reverses RotateCameraVertex, then removes the camera translation.
## Convert camera-space coordinates back to scene-space coordinates.
function CameraToWorldPoint pX,pY,pZ
   global gCameraYaw
   global gCameraPitch
   -- Reverse camera pitch.
   put pX into tX1
   put pY*cos(gCameraPitch)-pZ*sin(gCameraPitch) into tY1
   put pY*sin(gCameraPitch)+pZ*cos(gCameraPitch) into tZ1
   --return cr &cr & "CAMZ seen by CameraToWorldPoint: " & CAMZ &cr&cr into tDebug
   -- Reverse camera yaw.
   put tX1*cos(gCameraYaw)+tZ1*sin(gCameraYaw) into tX2
   put -tX1*sin(gCameraYaw)+tZ1*cos(gCameraYaw) into tZ2
   put tY1 into tY2
   
   -- Remove camera translation.
   subtract CAMX from tX2
   subtract CAMY from tY2
   subtract CAMZ from tZ2
   
   return tX2 && tY2 && tZ2  
   
end CameraToWorldPoint

## 2. ReverseTransformVertex
## This reverses the scene rotation and pivot operation performed by TransformVertex
## Reverse the scene transform applied by TransformVertex.
function ReverseTransformVertex pX,pY,pZ
   
   -- Remove the restored pivot.
   put pX-PIVX into tX
   put pY-PIVY into tY
   put pZ-PIVZ into tZ
   
   -- Reverse rotation around X.
   put tX into tX1
   put tY*cos(ANGLEX)+tZ*sin(ANGLEX) into tY1
   put -tY*sin(ANGLEX)+tZ*cos(ANGLEX) into tZ1
   
   -- Reverse rotation around Y.
   put tX1*cos(ANGLEY)-tZ1*sin(ANGLEY) into tX2
   put tY1 into tY2
   put tX1*sin(ANGLEY)+tZ1*cos(ANGLEY) into tZ2
   
   -- Reverse rotation around Z.
   put tX2*cos(ANGLEZ)+tY2*sin(ANGLEZ) into tX3
   put -tX2*sin(ANGLEZ)+tY2*cos(ANGLEZ) into tY3
   put tZ2 into tZ3
   
   -- Restore the original pivot-relative coordinates.
   add PIVX to tX3
   add PIVY to tY3
   add PIVZ to tZ3
   
   return tX3 && tY3 && tZ3
   
end ReverseTransformVertex


--Our complete coordinate conversion chain -- this may have been udated, troubleshooting 3D object selection
--Stage	Coordinate space	Operation
--1	Mesh local	Original vertex
--2	Object local	RotateObjectVertex
--3	World	Add object position
--4	Scene transformed	TransformVertex
--5	Camera	RotateCameraVertex
--6	Camera hit	Ray intersection
--7	Scene transformed	CameraToWorldPoint
--8	World	ReverseTransformVertex
--9	Mesh local	WorldToObjectPoint

--We can now reconstruct a ray intersection all the way back to the original mesh's coordinate system.

-- CameraHitToWorld
--Important correction to the name: 
--this produces the point in the object's original geometry coordinate system 
--only if we also undo its local rotation. 
--The returned point from this version is therefore not yet the final world-space point.
--Rather than misleadingly call it world-space,let's keep this as an intermediate diagnostic and add the object-local inverse next.
##  3. Complete world-space reconstruction
##  We now combine the two inverses and remove the object's world position.
## Convert a camera-space hit into world-space coordinates.
function CameraHitToWorld pObject,pX,pY,pZ
   
   -- Reverse camera orientation and translation.
   put CameraToWorldPoint(pX,pY,pZ) into tPoint
   
   -- Reverse scene orientation and pivot.
   put ReverseTransformVertex( \
         word 1 of tPoint, \
         word 2 of tPoint, \
         word 3 of tPoint) into tPoint
   
   -- Reverse object translation and local rotation.
   put WorldToObjectPoint(pObject, \
         word 1 of tPoint, \
         word 2 of tPoint, \
         word 3 of tPoint) into tPoint
   
   return tPoint
   
end CameraHitToWorld
#### CameraHitToWorld  naming note: CameraHitToWorld now returns object-local coordinates, not world coordinates. 
#### Once verified, I'd rename it CameraHitToObject to make that distinction explicit.






on test.camera.hit.to.world
   #CameraHitToWorld
   put 25 into tX
   put 40 into tY
   put 60 into tZ
   put GetObjectRotation("CubeLine") into tRotation
   
   put item 1 of tRotation into tRotX
   put item 2 of tRotation into tRotY
   put item 3 of tRotation into tRotZ
   -- Forward local rotation.
   put RotateObjectVertex(25,40,60, \
         tRotX,tRotY,tRotZ) into tRotated
   ####  One important distinction: WorldToObjectPoint must apply the inverse rotation,
   ####  not call the forward rotation function.
   ####  The explicit arguments make both operations consistent, but we should retain 
   ####  the inverse X-Y-Z calculations already implemented there.
   ####  This is my preferred interface:
   ####  - RotateObjectVertex: local → rotated local.
   ####  - WorldToObjectPoint: world → unrotated mesh-local.
   ####  - Both use the same three explicit rotation angles, in radians, with Z-Y-X as the forward rotation order.
   
   
   
   -- Add object world position.
   put GetObjectPosition("CubeLine") into tPosition
   
   put word 1 of tRotated + item 1 of tPosition into tWorldX
   put word 2 of tRotated + item 2 of tPosition into tWorldY
   put word 3 of tRotated + item 3 of tPosition into tWorldZ
   
   -- Reverse the transformation.
   put WorldToObjectPoint("CubeLine", \
         tWorldX,tWorldY,tWorldZ) into tRecovered
   
   put "Original local: 25 40 60" & cr & \
         "World position: " & tWorldX && tWorldY && tWorldZ & cr & \
         "Recovered local: " & tRecovered \
         into gDebug
   --   put gDebug
end test.camera.hit.to.world

function RotateObjectVertex tX,tY,tZ,tRotX,tRotY,tRotZ
   -- Rotate around the object's local origin.
   put tX into tDX
   put tY into tDY
   put tZ into tDZ
   --answer tDX,tDY,tDZ  -- this passes
   --fails at tRotZ 
   -- Rotate around Z.
   put tDX*cos(tRotZ)-tDY*sin(tRotZ) into tX1
   put tDX*sin(tRotZ)+tDY*cos(tRotZ) into tY1
   put tDZ into tZ1
   -- Rotate around Y.
   put tX1*cos(tRotY)+tZ1*sin(tRotY) into tX2
   put -tX1*sin(tRotY)+tZ1*cos(tRotY) into tZ2
   put tY1 into tY2
   -- Rotate around X.
   --answer "!!ERROR @ RotateObjectVertex" & cr &tY2 &cr & tRotX & cr & tz2 
   --exit RotateObjectVertex
   put tY2*cos(tRotX)-tZ2*sin(tRotX) into tY3
   put tY2*sin(tRotX)+tZ2*cos(tRotX) into tZ3
   put tX2 into tX3
   return tX3 && tY3 && tZ3
end RotateObjectVertex


##  4. Test the inverse scene and camera transforms
##  Before incorporating object-local rotation, test a point through the forward and reverse scene/camera transforms.
on test.hit.point.roncstruction
   put 25 into tX
   put 40 into tY
   put 60 into tZ
   
   --passed
   put TransformVertex(tX,tY,tZ) into tForward    
   --passed
   put RotateCameraVertex(word 1 of tForward,word 2 of tForward,word 3 of tForward) into tCamera    
   --Fails
   put CameraToWorldPoint(word 1 of tCamera,word 2 of tCamera,word 3 of tCamera) into tReverseCamera
   put "PIVX: " & PIVX & cr & \
         "PIVY: " & PIVY & cr & \
         "PIVZ: " & PIVZ & cr & \
         "CAMX: " & CAMX & cr & \
         "CAMY: " & CAMY & cr & \
         "CAMZ: " & CAMZ & cr & \
         "Before reverse: " & tReverseCamera &cr into gDebug
   --put gDebug
   
   put ReverseTransformVertex(word 1 of tReverseCamera,word 2 of tReverseCamera,word 3 of tReverseCamera) into tReverse
   put cr &"Original: 25 40 60" & cr & "Recovered: " & tReverse after gDebug
   --put gDebug
end test.hit.point.roncstruction

on test.hit.point.reconstruction2
   put TransformVertex(25,40,60) into tForward
   
   put RotateCameraVertex( \
         word 1 of tForward, \
         word 2 of tForward, \
         word 3 of tForward) into tCamera
   
   put CameraToWorldPoint( \
         word 1 of tCamera, \
         word 2 of tCamera, \
         word 3 of tCamera) into tCameraReverse
   
   put ReverseTransformVertex( \
         word 1 of tCameraReverse, \
         word 2 of tCameraReverse, \
         word 3 of tCameraReverse) into tFinal
   
   put "TransformVertex: " & tForward & cr & \
         "RotateCameraVertex: " & tCamera & cr & \
         "CameraToWorldPoint: " & tCameraReverse & cr & \
         "ReverseTransformVertex: " & tFinal \
         into gDebug
   --   put gDebug
end test.hit.point.reconstruction2

##########################################################################################
##  1. WorldToObjectPoint
##  Will undo the object's world translation, then reverse its local rotation in the opposite order: X, Y, Z.
##  This uses your existing GetObjectPosition and GetObjectRotation functions.
##  It does not modify either of them or the verified scene/camera inverse functions.
function WorldToObjectPoint pObject,pX,pY,pZ
   
   -- Retrieve the object's world position.
   put GetObjectPosition(pObject) into tPosition
   
   -- Remove world translation.
   put pX-item 1 of tPosition into tX
   put pY-item 2 of tPosition into tY
   put pZ-item 3 of tPosition into tZ
   
   -- Retrieve the object's local rotation.
   put GetObjectRotation(pObject) into tRotation
   
   put item 1 of tRotation into tAngleX
   put item 2 of tRotation into tAngleY
   put item 3 of tRotation into tAngleZ
   
   -- Reverse local rotation around X.
   put tX into tX1
   put tY*cos(tAngleX)+tZ*sin(tAngleX) into tY1
   put -tY*sin(tAngleX)+tZ*cos(tAngleX) into tZ1
   
   -- Reverse local rotation around Y.
   put tX1*cos(tAngleY)-tZ1*sin(tAngleY) into tX2
   put tY1 into tY2
   put tX1*sin(tAngleY)+tZ1*cos(tAngleY) into tZ2
   
   -- Reverse local rotation around Z.
   put tX2*cos(tAngleZ)+tY2*sin(tAngleZ) into tX3
   put -tX2*sin(tAngleZ)+tY2*cos(tAngleZ) into tY3
   put tZ2 into tZ3
   
   return tX3 && tY3 && tZ3
   
end WorldToObjectPoint

## This is your existing inverse-rotation mathematics, separated from the object-translation removal.
## ReverseObjectRotation
## Converts a point from object-rotated coordinates into mesh-local coordinates.
function ReverseObjectRotation pObject,pX,pY,pZ
   
   -- Retrieve the object's local rotation.
   put GetObjectRotation(pObject) into tRotation
   
   set itemDel to comma
   put item 1 of tRotation into tAngleX
   put item 2 of tRotation into tAngleY
   put item 3 of tRotation into tAngleZ
   
   -- Reverse local rotation around X.
   put pX into tX1
   put pY*cos(tAngleX)+pZ*sin(tAngleX) into tY1
   put -pY*sin(tAngleX)+pZ*cos(tAngleX) into tZ1
   
   -- Reverse local rotation around Y.
   put tX1*cos(tAngleY)-tZ1*sin(tAngleY) into tX2
   put tY1 into tY2
   put tX1*sin(tAngleY)+tZ1*cos(tAngleY) into tZ2
   
   -- Reverse local rotation around Z.
   put tX2*cos(tAngleZ)+tY2*sin(tAngleZ) into tX3
   put -tX2*sin(tAngleZ)+tY2*cos(tAngleZ) into tY3
   put tZ2 into tZ3
   
   return tX3 && tY3 && tZ3
   
end ReverseObjectRotation
## Number of vertices stored in the stack's xyz<Name>Array custom property.
function count.stored.vertices tObj
   set the customPropertySet of stack (the mainStack of this stack) to empty
   put "xyz" &tObj & "Array" into tArrayLabel
   Do "put the" && tArrayLabel && "of stack (the mainStack of this stack) into tArray"
   return the number of lines of the keys of tArray["x"]
end count.stored.vertices



on BuildCubeMesh
   
   -- Start with an empty vertex list.
   put empty into gMeshVertices
   
   -- Rebuild all eight vertices from the original XYZ data.
   repeat with tI = 1 to 8
      
      put getXYZ("Cube","X",tI) into tX
      put getXYZ("Cube","Y",tI) into tY
      put getXYZ("Cube","Z",tI) into tZ
      
      -- Each line represents one complete XYZ vertex.
      put tX && tY && tZ & cr after gMeshVertices
      set the MeshVertices of graphic "cubeLine" to gMeshVertices
   end repeat
   
   -- Define the twelve edges of the cube.
   put "1 3" & cr into gMeshEdges
   put "1 2" & cr after gMeshEdges
   put "1 5" & cr after gMeshEdges
   put "2 4" & cr after gMeshEdges
   put "2 6" & cr after gMeshEdges
   put "3 4" & cr after gMeshEdges
   put "4 8" & cr after gMeshEdges
   put "5 6" & cr after gMeshEdges
   put "5 7" & cr after gMeshEdges
   put "6 8" & cr after gMeshEdges
   put "7 3" & cr after gMeshEdges
   put "7 8" after gMeshEdges
   set the MeshEdges of graphic "cubeLine" to gMeshEdges
end BuildCubeMesh



## You can unpack the custom property array as JSON
--LiveCode 9.6.3 supports ArrayToJSON().
-- It converts a LiveCode array into a JSON string, including nested arrays. 
--The optional third parameter produces readable, indented output
-- Convert an object's stored XYZ array into readable JSON.
function getXYZArrayJSON tObj
   set the customPropertySet of stack (the mainstack of this stack) to empty
   put "xyz" & tObj & "Array" into tArrayLabel
   do "put the" && tArrayLabel && "of stack (the mainStack of this stack) into tArray"
   put ArrayToJSON(tArray,,true) into tJSON
   return tJSON
end getXYZArrayJSON


##2. ImportOBJFile
--This is the main parser. It reads vertices, interprets polygon 
--faces, and builds a deduplicated edge list.
--A particularly useful detail: OBJ face indices can be negative.
-- For example, f -3 -2 -1 refers to the last three vertices defined.
-- We'll handle that now rather than having to retrofit it later.
-- Import a Wavefront OBJ file into the existing XYZ storage system.
-- tObject is the name used for the stored geometry, e.g. "Imported".
-- geometry is stored in an xyz<tObject>Array custom Property of the stack by way of setXYZ tobject,X Y or Z,vertice index
function ImportOBJFile tFilePath,tObject
   -- Read the entire OBJ file.
   open file tFilePath for read
   if the result is not empty then
      answer error "Could not open OBJ file:" & cr & the result
      return empty
   end if
   
   read from file tFilePath until EOF
   put it into tOBJData
   close file tFilePath
   
   if tOBJData is empty then
      answer error "The OBJ file is empty."
      return empty
   end if
   
   -- Clear any previous geometry for this object.
   put "xyz" & tObject & "Array" into tArrayLabel
   
   set the customPropertySet of stack (the mainStack of this stack) to empty
   set the tArrayLabel of stack (the mainStack of this stack) to empty
   
   -- PASS 1: Collect vertices and calculate bounding box.
   
   put empty into tRawVertices
   put 0 into tVertexCount
   
   repeat for each line tLine in tOBJData
      
      put word 1 of tLine into tCommand
      
      if tCommand is not "v" then next repeat
      
      put word 2 of tLine into tRawX
      put word 3 of tLine into tRawY
      put word 4 of tLine into tRawZ
      
      if tRawX is not a number or \
            tRawY is not a number or \
            tRawZ is not a number then next repeat
      
      add 1 to tVertexCount
      
      put tRawX && tRawY && tRawZ & cr after tRawVertices
      
      -- Initialize the bounding box with the first vertex.
      if tVertexCount is 1 then
         
         put tRawX into tMinX
         put tRawX into tMaxX
         put tRawY into tMinY
         put tRawY into tMaxY
         put tRawZ into tMinZ
         put tRawZ into tMaxZ
         
      else
         
         if tRawX < tMinX then put tRawX into tMinX
         if tRawX > tMaxX then put tRawX into tMaxX
         
         if tRawY < tMinY then put tRawY into tMinY
         if tRawY > tMaxY then put tRawY into tMaxY
         
         if tRawZ < tMinZ then put tRawZ into tMinZ
         if tRawZ > tMaxZ then put tRawZ into tMaxZ
         
      end if
      
   end repeat
   
   if tVertexCount is 0 then
      answer error "No valid vertices found in OBJ file."
      return empty
   end if
   
   -- Calculate the bounding box center.
   put (tMinX + tMaxX) / 2 into tCenterX
   put (tMinY + tMaxY) / 2 into tCenterY
   put (tMinZ + tMaxZ) / 2 into tCenterZ
   
   -- Find the largest dimension.
   put tMaxX - tMinX into tSizeX
   put tMaxY - tMinY into tSizeY
   put tMaxZ - tMinZ into tSizeZ
   
   put tSizeX into tLargest
   
   if tSizeY > tLargest then put tSizeY into tLargest
   if tSizeZ > tLargest then put tSizeZ into tLargest
   
   -- Normalize the largest dimension to 120 units.
   if tLargest > 0 then
      put 120 / tLargest into tScale
   else
      put 0 into tScale
   end if
   
   -- PASS 2: Center, normalize, and store vertices.
   
   repeat with tI = 1 to tVertexCount
      
      put line tI of tRawVertices into tVertex
      
      put word 1 of tVertex into tRawX
      put word 2 of tVertex into tRawY
      put word 3 of tVertex into tRawZ
      
      put (tRawX - tCenterX) * tScale into tX
      put (tRawY - tCenterY) * tScale into tY
      put (tRawZ - tCenterZ) * tScale into tZ
      
      setXYZ tObject,"X",tI,tX
      setXYZ tObject,"Y",tI,tY
      setXYZ tObject,"Z",tI,tZ
      
   end repeat
   
   -- PASS 3: Build the unique edge collection.
   
   put empty into tEdges
   put empty into tFaces
   put empty into tEdgeSeen
   put 0 into tVerticesSeen
   
   repeat for each line tLine in tOBJData
      
      put word 1 of tLine into tCommand
      
      if tCommand is empty or tCommand is "#" then
         next repeat
      end if
      
      if tCommand is "v" then
         
         add 1 to tVerticesSeen
         next repeat
         
      else if tCommand is "f" then
         
         put the number of words of tLine into tWordCount
         
         if tWordCount < 4 then next repeat
         
         put empty into tFace
         put true into tFaceValid
         
         -- Extract the vertex index from each face token.
         repeat with tW = 2 to tWordCount
            
            put word tW of tLine into tToken
            
            if char 1 of tToken is "#" then
               exit repeat
            end if
            
            put offset("/",tToken) into tSlash
            
            if tSlash > 0 then
               put char 1 to (tSlash - 1) of tToken into tIndexText
            else
               put tToken into tIndexText
            end if
            
            if tIndexText is not a number then
               put false into tFaceValid
               exit repeat
            end if
            
            put tIndexText into tIndex
            
            -- Negative indices count backward from
            -- the vertices defined at this point in the OBJ.
            if tIndex < 0 then
               put tVerticesSeen + tIndex + 1 into tIndex
            end if
            
            -- Reject invalid vertex references.
            if tIndex < 1 or tIndex > tVerticesSeen then
               put false into tFaceValid
               exit repeat
            end if
            
            put tIndex & cr after tFace
            
         end repeat
         
         if tFaceValid is false then next repeat
         
         filter lines of tFace without empty
         
         put the number of lines of tFace into tFaceCount
         
         if tFaceCount < 3 then next repeat
         -- Preserve the original polygon for ray casting.
         put (tFace) into tFaceLine
         replace cr with space in tFaceLine
         put tFaceLine & cr after tFaces
         
         -- Connect every vertex to the next one.
         -- The final vertex connects back to the first.
         
         repeat with tI = 1 to tFaceCount
            
            put tI + 1 into tNextI
            
            if tNextI > tFaceCount then
               put 1 into tNextI
            end if
            
            put line tI of tFace into tA
            put line tNextI of tFace into tB
            
            if tA = tB then next repeat
            
            -- Create a direction-independent edge key.
            if tA < tB then
               put tA & "_" & tB into tEdgeKey
            else
               put tB & "_" & tA into tEdgeKey
            end if
            
            -- Avoid duplicate edges shared by adjacent faces.
            if tEdgeSeen[tEdgeKey] is empty then
               put true into tEdgeSeen[tEdgeKey]
               put (tA && tB) & cr after tEdges
            end if
         end repeat
      end if
   end repeat
   -- Remove empty lines from the edge & face lists.
   filter lines of tEdges without empty
   filter lines of tFaces without empty
   -- Store the edges as a custom property.
   put tObject & "Edges" into tEdgeLabel
   put tObject & "Faces" into tFaceLabel
   set the customPropertySet of stack (the mainStack of this stack) to empty
   set the tEdgeLabel of stack (the mainStack of this stack) to tEdges
   set the tFaceLabel of stack (the mainStack of this stack) to tFaces
   return "OK"
end ImportOBJFile



-- Then every Render* type handler essentially looks like RenderImportedOBJ, RenderCube specifically details a clean empty cube to avoid triangluation.
on RenderImportedOBJ tObject,tGraphicName
   global gMeshVertices
   global gMeshEdges
   -- Phase 1: cached mesh + matrix renderer.
   RenderMeshFast tObject,tGraphicName
end RenderImportedOBJ

on ChooseOBJFile
   answer file "Select a Wavefront OBJ file:"
   if it is empty then exit ChooseOBJFile
   put it into tFilePath
   -- Import the geometry.
   put ImportOBJFile(tFilePath,"Imported") into tStatus
   if tStatus is not "OK" then
      exit ChooseOBJFile
   end if
   -- Create the drawing graphic if necessary.
   if exists (graphic "ImportedLine") is false then
      Scene.NewLineGraphic "ImportedLine"
      if there is a graphic "ImportedLine" then set the lineSize of graphic "ImportedLine" to 2
   end if
   -- Rebuild the cached mesh from the new data, then draw it.
   Mesh.Invalidate "Imported"
   RenderImportedOBJ "Imported","ImportedLine"
   answer information "OBJ import successful."
end ChooseOBJFile


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

--- INITIAL TEST OF OBJECT 3D POSITIONING
on init.object.Transforms
   ## POSITION -- static pre-positioning during development
   SetObjectPosition "cubeline",-150,0,0
   SetObjectPosition "cylinderline",0,0,0
   SetObjectPosition "coneline",150,10,-150
   SetObjectPosition "importedline",0,150,50
   SetObjectPosition "gridLine",0,350,0
   put "CubeLine,CylinderLine,coneLine,importedLine,gridLine" into tObjs
   repeat for each item tObj in tObjs
      SetObjectRotation tObj,0,0,0
      SetObjectRotationSpeed tObj,0,0,0
      SetObjectVelocity tObj,0,0,0
      SetObjectLocalVelocity tObj,0,0,0
      SetObjectLocalAcceleration tObj,0,0,0
      -- Local-space braking strength.
      put 0 into gObjectTransforms[tObj]["localBrake"]
      -- Maximum persistent world-space speed.
      -- Zero means unlimited.
      put 0 into gObjectTransforms[tObj]["maxWorldSpeed"]
   end repeat
end init.object.Transforms


----  set the initial angle modifier values at the start of the CUBE_LOOP
on SetAngles xa,ya,za
   if xa is empty then put 0.1 into xa
   put xa into fXrot
   put 0 into fYrot
   put 0 into fZrot
   if ya is not empty then put ya into fYrot
   if za is not empty then put za into fZrot
end SetAngles

----  the center of the stack window
on SetCenterXY
   put the width of stack (the mainStack of this stack)/2 into CenterX
   put the height of stack (the mainStack of this stack)/2 into CenterY
end SetCenterXY


on show.pivot.pixel
   ----  Display of the pivot point code (optional)
   if PIVZ <0 then put 0.01 into piVZ
   if CAMZ >1  then  
      put ( (PIVX+CAMX) / (PIVZ+CAMZ) ) /theSCALE +MOVEX +CenterX into PX 
      put ( (PIVY+CAMY) / (PIVZ+CAMZ) ) /theSCALE +MOVEY +CenterY into PY
      Draw_Pixel PX, PY
   end if
end show.pivot.pixel


on rawKeyUp pKey
put false into bkeyDown
pass rawKeyUp
end rawKeyUp

on UI.Display.Title.Options
lock screen
set the top of group "PauseMenuGroup" to the bottom of field "Title"
set the width of group "PauseMenuGroup" to width of this stack
set the left of group "PauseMenuGroup" to 0
set the visible of group "PauseMenuGroup" to not the visible of group "PauseMenuGroup" 
put item 1 the loc of group "PauseMenuGroup" into X
set the loc of button "OptionsOfPlay" to x,item 2 the loc of button "OptionsOfPlay"
set the loc of button "ExitBUtton" to x,item 2 the loc of button "ExitBUtton"
unlock screen
end UI.Display.Title.Options

## Escape: Title card = close menus; playing = pause menu; paused (or anywhere else)
## = stop and go back to the Developer card.
## Escape: HUD test = back to Edit_HUD; Title card = close menus; playing = pause menu
## (if the stack has its template); anything else = stop and go to the Developer card.
on escapekeyDown
   -- Don't repeat while the key is held. rawKeyUp clears bKeyDown; after a second
   -- it is ignored anyway, in case the key-up went to the IDE (pointer tool).
   if bKeyDown is true and the milliseconds - sEscMS < 1000 then exit escapekeyDown
   put true into bKeyDown
   put the milliseconds into sEscMS
   put the short name of this card into tCard
   if sHudTest is true then
      Menu.CloseAll	
      Game.Exit
      exit escapekeyDown
   end if

   if tCard is "Title" then
TitleCardOpened
UI.Display.Title.Options
-- there used to be an options group to show in this card (its there)
      exit escapekeyDown
   end if

   if tCard begins with "Play." and sLoopActive and bPaused is not true and Menu.Available("Pause") then
      Game.Pause
      exit escapekeyDown
   end if
   Menu.CloseAll
   Game.Exit -- stop the loop, back to the Developer card
   choose "pointer tool"
end escapekeyDown

on rawKeyDown theKey
   --if name of the target is not the name of stack (the mainStack of this stack) then pass rawKeyDown
   ---- escape rawkeydown on pointer tool so e can still use Livecode IDE
   if the tool is not "browse tool" then
      pass rawKeyDown
      exit rawKeyDown
   end if
   ## CAPSLOCK MOUSELOOK TOGGLE (mouse-look only; it no longer starts the game loop)
   if theKey = 65509 then
      SetMouseLook (the capslockkey is "down" )
      put true into bKeyUpdate
   end if
   ## Escape Key
   if theKey is 65307 then
      escapekeyDown
      pass rawKeyDown
   end if
   if thekey = 65505 then pass rawKeyDown -- shift key
   pass rawkeyDown
end rawKeyDown

## Play / stop. Call from a button. Escape also stops.
on Toggle.Playing
   if sLoopActive then
      Game.Exit
   else
      Game.Play
   end if
end Toggle.Playing

## Start the current game (Game.Select) on its "Play.<game>" card.
## Start the current game (Game.Select) on its "Play.<game>" card.
## The card is prepared first (once per play) so nothing old is on screen.
on Game.Play
   if Game.Current() is empty or there is not a card ("Play." & Game.Current()) then
      get Game.GoToPlayCard() -- goes to Developer and says why
      exit Game.Play
   end if
   if sPreparedGame is not Game.Current() then Game.Prepare.Card
   lock screen
   get Game.GoToPlayCard()
   -- The next Game.Play (after Exit / game over) starts a fresh game.
   put empty into sPreparedGame
   choose browse tool
   put false into bPaused
   put false into bDeveloper
   Audio.StartMusic
   game.loop.start
   unlock screen
end Game.Play

--- prepare the card before even going there !!
## Prepare the game card BEFORE it is shown: visit it with the screen and the card
## messages locked, clear the Viewport, apply the HUD, let the card build its scene
## (Game.OnStart) and draw it once, then come back. Everything happens on the game
## card itself, so its graphics and HUD controls can't land on the current card.
## pGame: game name (empty = the current game).
on Game.Prepare.Card pGame
   if pGame is not empty then Game.Select pGame
   put "Play." & Game.Current() into tCard
   if there is not a card tCard then exit Game.Prepare.Card
   if sAudioReady is not true then Audio.Init
   put the short name of this card into tBackTo
   lock screen
   lock messages
   go to card tCard
   unlock messages
   Viewport.Clean
   -- This game's HUD controls, as saved from the Edit_HUD card.
   HUD.ApplyToCard Game.Current()
   put false into bPaused
   put false into bDeveloper
   dispatch "Game.OnStart" to this card
   game.render
   if there is a group "User" then set the layer of group "User" to top
   put Game.Current() into sPreparedGame
   if tBackTo is not tCard then
      lock messages
      go to card tBackTo
      unlock messages
   end if
   unlock screen
end Game.Prepare.Card

## DELETE every engine graphic in the Viewport (old games' lines, faded copies, derez,
## HUD text) and forget the engine's lists of them. The engine makes again whatever the
## next game draws (Game.Prepare.Card draws one frame with the screen locked), so the
## group only ever holds the current game's graphics.
on Viewport.Clean
   if there is not a group "Viewport" then exit Viewport.Clean
   lock screen
   repeat with i = the number of graphics of group "Viewport" down to 1
      put the long id of graphic i of group "Viewport" into tRef
      if Viewport.IsEngineGraphic(tRef) then
         put the short id of tRef into tId
         delete graphic id tId
      end if
   end repeat
   if there is a graphic "SelectionMarker" then set the visible of graphic "SelectionMarker" to false
   put empty into gSelectedObject
   put empty into sLastBatchGraphics
   put empty into sBandMade
   put empty into sBandBase
   put empty into sStyled
   repeat with n = 1 to kDerezSlots
      put 0 into sDerezAge[n]
   end repeat
   unlock screen
end Viewport.Clean

## Made by the engine? (property Engine = true, or an engine name from before that.)
## Made by the engine? Custom property Entity = true (Games.Fix stamps the older ones),
## or a name only the engine uses: Batch_..., Derez..., a faded copy ..._d2 to _d4.
function Viewport.IsEngineGraphic pRef
   set the customPropertySet of pRef to empty
   if the Entity of pRef is true then return true
   put the short name of pRef into tName
   if tName begins with "Batch_" or tName begins with "Derez" then return true
   if char -3 to -2 of tName is "_d" and char -1 of tName is among the items of "2,3,4" then return true
   return false
end Viewport.IsEngineGraphic

## The older rule (any name ending in "Line"), used once by Games.Fix to stamp Entity.
function Viewport.IsOldEngineName pName
   if pName begins with "Batch_" or pName begins with "Derez" then return true
   if pName ends with "Line" or "Line_d" is in pName then return true
   return false
end Viewport.IsOldEngineName

## The old sea demo (boat, rocks, laser).
## The sea demo (boat, rocks, laser) on card "Play.Demo".
on Game.PlayDemo
   Game.Select "Demo"
   Game.Play
end Game.PlayDemo


## Stop the loop and go back to the "Developer" card (if there is one).
on Game.Exit
   dispatch "Game.OnStop" to this card
   Audio.StopMusic
   game.loop.stop
   put empty into sPreparedGame
   Viewport.Clean
   put false into bMissile
   SetMouseLook false
   if sHudTest is true and there is a card "Edit_HUD" then
      -- Testing a HUD: back to the layout card.
      put false into sHudTest
      go to card "Edit_HUD"
      choose browse tool
   else if there is a card "Developer" and the short name of this card is not "Developer" then
      go to card "Developer"
   end if
end Game.Exit

######################################################################################
## ENGINE ACCESS FOR CARD SCRIPTS
## The scene values (CAMX, MOVEX, theSCALE, PIVX, fXrot, ANGLEX ...) and the current
## selection are LOCAL to this stack script. A card script cannot read or set them
## directly ("put CAMY-4 into CAMY" in a card only changes a card variable).
## Use these instead, from any card script:
##   Engine.Add "CAMY",-4            Engine.Set "fXrot",0
##   put Engine.Get("theSCALE") into tScale
##   put Selection.Object() into tSel
##   Selection.Kill                  Game.TogglePause
######################################################################################

## Names a card script may read and change.
function Engine.Names
   return "CAMX,CAMY,CAMZ,MOVEX,MOVEY,theSCALE,theMODE,ANGLEX,ANGLEY,ANGLEZ,PIVX,PIVY,PIVZ,fXrot,fYrot,fZrot"
end Engine.Names

function Engine.Get pName
   if pName is not among the items of Engine.Names() then return empty
   do "put" && pName && "into tValue"
   return tValue
end Engine.Get

on Engine.Set pName,pValue
   if pName is not among the items of Engine.Names() then exit Engine.Set
   if pValue is not a number then exit Engine.Set
   do "put pValue into" && pName
end Engine.Set

on Engine.Add pName,pDelta
   if pName is not among the items of Engine.Names() then exit Engine.Add
   if pDelta is not a number then exit Engine.Add
   do "add pDelta to" && pName
end Engine.Add

## The selected object's key (e.g. "BoatLine", "Rock_3"), or empty.
function Selection.Object
   return gSelectedObject
end Selection.Object

## Remove the selected object from the scene.
on Selection.Kill
   Entity.Kill gSelectedObject
end Selection.Kill

on Game.TogglePause
   put not bPaused into bPaused
end Game.TogglePause

######################################################################################
## CARDS (run setup.cards ONCE from the Message Box, on your current card)
##   "Developer" card : your current card with all the tool/debug buttons.
##   "Play" card      : clean playback card (Defensive's name; "Game" is kept for an editor).
## All 3D line graphics live in one background group, "Viewport", that is placed on
## BOTH cards, so the same graphics draw on whichever card is showing.
## New graphics (Scene.NewLineGraphic) are created inside "Viewport" automatically.
######################################################################################
on setup.cards
   global gSceneObjects
   lock screen
   if there is not a card "Developer" then set the name of this card to "Developer"
   
   if there is not a group "Viewport" then
      -- Every 3D graphic: the scene list, colour batches, the selection marker.
      put "SelectionMarker" & cr into tWanted
      repeat for each line tEntry in gSceneObjects
         put word 2 of tEntry & cr & word 3 of tEntry & cr after tWanted
      end repeat
      put empty into tList
      repeat with i = 1 to the number of graphics of this card
         put the short name of graphic i of this card into tName
         if tName is among the lines of tWanted or tName begins with "Batch_" then
            if tList is not empty then put " and " after tList
            put "graphic" && quote & tName & quote after tList
         end if
      end repeat
      if tList is empty then
         unlock screen
         answer "setup.cards: no 3D graphics found on this card. Run APP.init first."
         exit setup.cards
      end if
      do "group" && tList
      set the name of the last group to "Viewport"
   end if
   
   -- Fixed full-card rect: no clipping, and no re-measuring the group every frame.
   set the backgroundBehavior of group "Viewport" to true
   set the lockLoc of group "Viewport" to true
   set the rect of group "Viewport" to the rect of this card
   set the margins of group "Viewport" to 0
   set the showBorder of group "Viewport" to false
   
   -- The Play card (Defensive's name for it). New cards get background groups automatically.
   -- An existing "Game" card is left alone (it can become the level editor).
   if there is not a card "Play" then
      create card "Play"
      go to card "Developer"
   end if
   if there is not a group "Viewport" of card "Play" then place group "Viewport" onto card "Play"
   go to card "Developer"
   unlock screen
   answer "Cards ready: Developer + Play, sharing group" && quote & "Viewport" & quote & "."
end setup.cards

## Create a line graphic for the 3D view, inside "Viewport" when it exists.
## Create a line graphic for the 3D view, always inside "Viewport". On a card without
## the Viewport (Title, ...) nothing is created, so engine graphics can't litter it.
## Engine graphics get the custom property "Entity" = true (see Viewport.Clean).
## ("Engine" is a reserved word / property in LiveCode.)
on Scene.NewLineGraphic pName
   if there is a graphic pName then exit Scene.NewLineGraphic
   if there is not a group "Viewport" then exit Scene.NewLineGraphic
   reset the templateGraphic
   create graphic pName in group "Viewport"
   set the style of graphic pName to "line"
   set the lineSize of graphic pName to 1
   set the opaque of graphic pName to false
   set the customPropertySet of graphic pName to empty
   set the Entity of graphic pName to true
end Scene.NewLineGraphic

on  Object.Angle.Keys pNumber
   if pNumber is empty or pNumber <0 then exit Object.Angle.Keys
   switch pNumber
      case  "1"  
         put  ANGLEZ-.1  into  ANGLEZ 
         break 
      case  "2"  
         put  ANGLEZ+.1  into  ANGLEZ 
         break
      case  "3"  
         put  ANGLEY-.1  into  ANGLEY 
         break 
      case  "4"  
         put  ANGLEY+.1  into  ANGLEY 
         break
      case  "5"  
         put  ANGLEX-.1  into  ANGLEX 
         break 
      case  "6"  
         put ANGLEX+.1  into  ANGLEX
         break
   end switch
   Render_Scene
end Object.Angle.Keys

--The old OBJ routine should follow the same pattern. 
--Its graphic must supply a mesh edge list and vertex count:
on OBJ_LOOP
   put the objectType of me into tObject
   -- Obtain this object's edge definitions.
   put the MeshEdges of me into tEdges
   -- Retrieve its existing vertex array.
   put "XYZ"&tObject&"Array" into tArrayName
   do "put the" && tArrayName && "of stack (the mainStack of this stack) into tArray"
   put the number of lines of the keys of tArray["X"] into tCount
   BuildMeshFromXYZArray tObject,tCount,tEdges
   RenderMesh gMeshVertices,gMeshEdges,the short name of me
end OBJ_LOOP

function Scene.Variables.Array ANGLEX,ANGLEY,ANGLEZ,fXrot,fYrot,fZrot,pivX,pivY,pivZ,XROTOFFSET,YROTOFFSET,ZROTOFFSET,CAMX,CAMY,CAMZ,moveX,moveY,moveZ,theSCALE,theMode
   put  "ANGLEX,ANGLEY,ANGLEZ,fXrot,fYrot,fZrot,pivX,pivY,pivZ,XROTOFFSET,YROTOFFSET,ZROTOFFSET,CAMX,CAMY,CAMZ,moveX,moveY,moveZ,theSCALE,theMode" into theVars
   repeat for each item tVar in theVars
      do "put" && tVar&& "into tVal"
      if tVal is empty or tVal is not a number then put 0 into tVal
      put tVal into gSceneTransforms[tVar]
   end repeat
   set the customPropertySet of stack (the mainStack of this stack) to Transforms
   put the customKeys of stack (the mainStack of this stack) into tKeys
   put the number of lines of tKeys+1 into tIndex
   put "t"& the seconds into tKey
   do "set the" && tKey && "of stack (the mainStack of this stack) to  gSceneTransforms"
   set the customPropertySet of stack (the mainStack of this stack) to empty
   return gSceneTransforms
end Scene.Variables.Array

function Scene.Variables.State tIndex
   set the customPropertySet of stack (the mainStack of this stack) to Transforms
   put the customKeys of stack (the mainStack of this stack) into tKeys
   sort lines of tKeys numeric ascending
   filter lines of tKeys without empty
   if number of lines of tKeys < 1 then exit scene.variables.state
   put line -1 of tKeys into tCurrentFrame
   do "put the" && tCurrentFrame &&"of stack (the mainStack of this stack) into gSceneTransforms"
   set the customPropertySet of stack (the mainStack of this stack) to empty
   put the keys of gSceneTransforms into tKeys
   repeat for each line L in tKeys
      do "Put gSceneTransforms["  &quote & L &quote &"]"&& "into tVal" 
      if tVal is empty then do "put 0 into" && tVal
      do  "put L &&" &  tVal & "& cr after tState" 
   end repeat
   sort lines of tState
   return tState
end scene.variables.state

-- prevent the auto rotation increments
on zero.rotation.per.frame
   put  0  into  fxRot
   put  0  into  fyRot
   put  0  into  fzRot
end zero.rotation.per.frame


----  300 is CAMZ default
on ResetCamZ
   put -600 into CAMZ
   Render_Scene  
end ResetCamZ

## Retrieve the stored polygon faces for an object.
function GetObjectFaces pObject
   put pObject & "Faces" into tFaceLabel
   set the customPropertySet of stack (the mainStack of this stack) to empty
   return the tFaceLabel of stack (the mainStack of this stack)
end GetObjectFaces

-- object name, X,Y, or Z, vertice/index Number, distance from center of object
on setXYZ tObject,XYZ,n,tval
   set the customPropertySet of stack (the mainStack of this stack) to empty
   put "xyz"&tObject&"Array" into tArrayName
   put the tArrayName  of stack (the mainstack of this stack) into tArray
   put tArray[xyz] into subArray
   put tVal into subArray[n]
   put subArray into tArray[xyz]
   set the tArrayName of  stack (the mainstack of this stack) to tArray
end setXYZ

function getXYZ tObject,xyz,n
   set the customPropertySet of stack (the mainStack of this stack) to empty
   put "xyz"&tObject&"Array" into tArrayName
   put the tArrayName of stack (the mainstack of this stack) into tArray
   put tArray[xyz] into subArray
   return subArray[n]
end getXYZ

----  this draws the pivot point at the center of the object
on Draw_Pixel x,y
   if exists (graphic "Pixel") is false then
      create graphic
      set the style of the last graphic to "line"
      set the name of the last graphic to "Pixel"
      set the lineSize of the last graphic to 2
   end if
   ----  if it's already created, we hide it in mode 0/show in mode 1
   show graphic "pixel"
   put cr & x & comma & y & cr & cr after tPoints
   set the points of  graphic "Pixel" to tPoints
end Draw_Pixel

on show.all.graphics
   repeat with i = 1 to number of graphics of stack (the mainStack of this stack)
      show graphic i
   end repeat
end show.all.graphics

on RENDER_SCENE
   -- One-shot step + draw, for key presses and editor actions while the loop is stopped.
   -- While the game loop is running it owns all updating and drawing, so do nothing here.
   if sLoopActive then exit RENDER_SCENE
   lock screen
   game.update
   game.render
   unlock screen
   UI.update.status.display
end RENDER_SCENE

## Redraw only: no simulation step. For mouse-look and camera moves while editing.
on RENDER_VIEW
   if sLoopActive then exit RENDER_VIEW
   lock screen
   game.render
   unlock screen
end RENDER_VIEW


######################################################################################
## PHASE 0: GAME LOOP  (11 08 2026)
## One chain of messages only. Simulation runs at a fixed step (kStepMS),
## drawing happens once per tick. Replaces game.loop.init/update.scene/validate/continue.
######################################################################################

on game.loop.start
   if sLoopActive then exit game.loop.start   -- never start a second chain
   choose browse tool
   put true into bPlaying
   put false into bPaused
   put true into sLoopActive
   put the milliseconds into sLastMS
   put 0 into sAccumMS
   put empty into sFPSStamp
   game.loop.tick
end game.loop.start

-- Old name, still called by Toggle.Playing.
on game.loop.init
   game.loop.start
end game.loop.init

on game.loop.stop
   put false into bPlaying
   put false into sLoopActive
   repeat for each line tMsg in the pendingMessages
      if item 3 of tMsg is "game.loop.tick" then cancel item 1 of tMsg
   end repeat
end game.loop.stop

on game.loop.tick
   if the tool is not "browse tool" then put false into bPlaying
   if the short name of this card is "Title" then put false into bPlaying
   if bDeveloper is true then put false into bPlaying
   -- The script editor is in front: don't update or draw, just check again later,
   -- so editing scripts isn't fighting the game loop.
   if bPlaying and the short name of the topStack begins with "revNewScriptEditor" then
      put the milliseconds into sLastMS
      put 0 into sAccumMS
      send "game.loop.tick" to this stack in 500 milliseconds
      exit game.loop.tick
   end if
   if not bPlaying then
      put false into sLoopActive
      exit game.loop.tick
   end if
   
   put the milliseconds into tNow
   if bPaused then
      put 0 into sAccumMS
   else
      -- Cap the catch-up so a long stall (IDE, dialog) cannot freeze the loop.
      add min(250, tNow - sLastMS) to sAccumMS
      repeat while sAccumMS >= kStepMS
         game.update
         subtract kStepMS from sAccumMS
      end repeat
   end if
   put tNow into sLastMS
   
   lock screen
   game.render
   unlock screen
   
   -- Exactly one pending tick, ever.
   repeat for each line tMsg in the pendingMessages
      if item 3 of tMsg is "game.loop.tick" then cancel item 1 of tMsg
   end repeat
   put max(1, kStepMS - (the milliseconds - tNow)) into tDelay
   send "game.loop.tick" to this stack in tDelay milliseconds
end game.loop.tick

## Simulation only: no drawing here.
on game.update
   add fXrot to ANGLEX
   add fYrot to ANGLEY
   add fZrot to ANGLEZ
   UpdateObjectTransforms
   Scene.UpdateBehaviors -- bobbing, bounds, time-to-live
   -- The current game card's rules (Play.Canyon, Play.Demo ...).
   dispatch "Game.OnUpdate" to this card
   Collision.Update
   Particles.Update
   Weapon.Update
   Audio.UpdateMusic
   if bMissile then missile.check
end game.update

## Drawing only: no state changes here.
on game.render
   put the width of this stack / 2 into CenterX
   put the height of this stack / 2 into CenterY
   -- Window resized (Options / full screen): follow it.
   if gViewRight is not the width of this stack or gViewBottom is not the height of this stack then
      put 0 into gViewLeft
      put 0 into gViewTop
      put the width of this stack into gViewRight
      put the height of this stack into gViewBottom
      if there is a group "Viewport" then set the rect of group "Viewport" to the rect of this card
   end if
   Render.BeginFrame
   -- Phase 3: every object in the scene list adds its lines to its graphic's buffer.
   -- Line format: "Mesh Key [Graphic]"; no Graphic means the graphic is named Key.
   put empty into tBuf
   repeat for each line tEntry in gSceneObjects
      put word 3 of tEntry into tGraphic
      if tGraphic is empty then put word 2 of tEntry into tGraphic
      RenderMeshInto word 1 of tEntry, word 2 of tEntry, tGraphic, tBuf
   end repeat
   -- Particles, laser beams and HUD text join the same colour batches.
   Particles.Render tBuf
   Weapon.Render tBuf
   HUD.Render tBuf
   -- One "set the points" per graphic (one per colour batch).
   put empty into tDrawnList
   repeat for each key tGraphic in tBuf
      -- Deleted by Viewport.Clean (or never made): make it again, in its colour.
      if there is not a graphic tGraphic and tBuf[tGraphic] is not empty then
         Scene.NewLineGraphic tGraphic
         if there is a graphic tGraphic and sOrigColor[tGraphic] is not empty then
            set the foregroundColor of graphic tGraphic to sOrigColor[tGraphic]
         end if
      end if
      if there is a graphic tGraphic then
         -- Phase 4: colour / fade / glow, once per graphic until the view changes.
         if sStyled[tGraphic] is not true then View.StyleGraphic tGraphic
         set the points of graphic tGraphic to tBuf[tGraphic]
      end if
      put tGraphic & cr after tDrawnList
   end repeat
   -- Clear graphics that had lines last frame but none now (killed objects).
   repeat for each line tGraphic in sLastBatchGraphics
      if tGraphic is not among the lines of tDrawnList and there is a graphic tGraphic then
         set the points of graphic tGraphic to empty
      end if
   end repeat
   put tDrawnList into sLastBatchGraphics
   FX.DerezRender
   -- Marker last, so it uses this frame's object transforms.
   UpdateSelectionMarker
   Render.UpdateFPS
end game.render

on Render.UpdateFPS
   add 1 to sFrameCount
   put the milliseconds into tNow
   if sFPSStamp is empty then put tNow into sFPSStamp
   if tNow - sFPSStamp >= 1000 then
      put round(sFrameCount * 1000 / (tNow - sFPSStamp)) into sFPS
      put 0 into sFrameCount
      put tNow into sFPSStamp
      -- Once a second only: updating controls is slow in LiveCode.
      if sLoopActive then UI.update.status.display
   end if
end Render.UpdateFPS

## One-line scene readout in the LABEL of button "Status" (much cheaper than a field).
on UI.update.status.display
   global gSceneObjects
   global gCameraYaw
   global gCameraPitch
   -- "Status" is a rectangle graphic (a button also still works).
   if there is a graphic "Status" then
      put "graphic" into tKind
   else if there is a button "Status" then
      put "button" into tKind
   else
      exit UI.update.status.display
   end if
   if sLoopActive then
      put "FPS" && sFPS into tText
   else
      put "STOPPED" into tText
   end if
   put " | Edges" && sEdgesDrawn after tText
   put " | Objs" && the number of lines of gSceneObjects after tText
   put " | Parts" && sPCount after tText
   put " | View" && sView["name"] after tText
   put " | Cam" && round(CAMX) & comma & round(CAMY) & comma & round(CAMZ) after tText
   put " | Yaw" && round(gCameraYaw,2) && "Pitch" && round(gCameraPitch,2) after tText
   if gSelectedObject is not empty then put " | Sel" && gSelectedObject after tText
   if bPaused then put " | PAUSED" after tText
   if tKind is "graphic" then
      set the showName of graphic "Status" to true
      set the label of graphic "Status" to tText
   else
      set the label of button "Status" to tText
   end if
end UI.update.status.display


######################################################################################
## PHASE 1: FAST RENDERER  (11 08 2026)
## Same math as RotateObjectVertex -> TransformVertex -> + world -> RotateCameraVertex,
## folded into ONE 3x3 matrix + translation per object per frame.
## Per vertex: 9 multiplies, no trig, no word chunking.
## Matrices are 9-item comma lists, row-major: r1c1,r1c2,r1c3,r2c1,...,r3c3
######################################################################################

## Rx * Ry * Rz : rotates Z first, then Y, then X (same order as RotateObjectVertex).
function Mat3.RotZYX pRX,pRY,pRZ
   put cos(pRX) into tCX
   put sin(pRX) into tSX
   put cos(pRY) into tCY
   put sin(pRY) into tSY
   put cos(pRZ) into tCZ
   put sin(pRZ) into tSZ
   put tCZ,-tSZ,0,tSZ,tCZ,0,0,0,1 into tRZ
   put tCY,0,tSY,0,1,0,-tSY,0,tCY into tRY
   put 1,0,0,0,tCX,-tSX,0,tSX,tCX into tRX
   return Mat3.Mul(tRX, Mat3.Mul(tRY,tRZ))
end Mat3.RotZYX

## Pitch * Yaw : same as RotateCameraVertex.
function Mat3.Camera
   global gCameraYaw
   global gCameraPitch
   put cos(gCameraYaw) into tCY
   put sin(gCameraYaw) into tSY
   put cos(gCameraPitch) into tCP
   put sin(gCameraPitch) into tSP
   put tCY,0,-tSY,0,1,0,tSY,0,tCY into tYaw
   put 1,0,0,0,tCP,tSP,0,-tSP,tCP into tPitch
   return Mat3.Mul(tPitch,tYaw)
end Mat3.Camera

function Mat3.Mul pA,pB
   set itemDel to comma
   put empty into tC
   repeat with tR = 0 to 2
      repeat with tCol = 1 to 3
         put (item (tR*3+1) of pA) * (item tCol of pB) \
               + (item (tR*3+2) of pA) * (item (3+tCol) of pB) \
               + (item (tR*3+3) of pA) * (item (6+tCol) of pB) into tVal
         if tC is empty then
            put tVal into tC
         else
            put comma & tVal after tC
         end if
      end repeat
   end repeat
   return tC
end Mat3.Mul

## Returns "x y z" (space separated, like the other engine functions).
function Mat3.Apply pM,pX,pY,pZ
   set itemDel to comma
   put (item 1 of pM)*pX + (item 2 of pM)*pY + (item 3 of pM)*pZ into tX
   put (item 4 of pM)*pX + (item 5 of pM)*pY + (item 6 of pM)*pZ into tY
   put (item 7 of pM)*pX + (item 8 of pM)*pY + (item 9 of pM)*pZ into tZ
   return tX && tY && tZ
end Mat3.Apply

## Once per frame: camera + scene matrices and projection constants.
## Camera + scene matrices from the current state. Used by drawing AND picking.
on Render.FrameMatrices
   put Mat3.Camera() into sCamM
   put Mat3.RotZYX(ANGLEX,ANGLEY,ANGLEZ) into tSceneM
   put tSceneM into sSceneM
   put Mat3.Mul(sCamM,tSceneM) into sSceneCamM
   
   -- Frame translation = Rcam * (PIV - Rscene*PIV + CAM)
   put Mat3.Apply(tSceneM,PIVX,PIVY,PIVZ) into tRP
   put Mat3.Apply(sCamM, \
         PIVX - (word 1 of tRP) + CAMX, \
         PIVY - (word 2 of tRP) + CAMY, \
         PIVZ - (word 3 of tRP) + CAMZ) into sFrameT
end Render.FrameMatrices

## Once per frame: matrices and projection constants.
on Render.BeginFrame
   Render.FrameMatrices
   -- Projection: screen = x * f / z / scale + center + MOVE  (same as ProjectVertex)
   if theScale = 0 then put 0.01 into theScale
   put gFocalLength / theScale into sProjK
   put CenterX + MOVEX into sProjOffX
   put CenterY + MOVEY into sProjOffY
   put 0 into sEdgesDrawn
end Render.BeginFrame

## Mesh-local -> camera space for one object, as 12 comma items:
##   m1..m9 (rotation, row-major), t1,t2,t3 (translation)
##   camera = M * local + T
## M is a pure rotation, so its inverse is its transpose (used by picking).
## Needs Render.FrameMatrices (or Render.BeginFrame) first.
function Xform.Object pObj
   set itemDel to comma
   put GetObjectRotation(pObj) into tRot
   put Mat3.Mul(sSceneCamM, Mat3.RotZYX(item 1 of tRot,item 2 of tRot,item 3 of tRot)) into tM
   put Mat3.Apply(sCamM,GetObjectPosition(pObj,"x"),GetObjectPosition(pObj,"y"),GetObjectPosition(pObj,"z")) into tTW
   return tM & comma & ((word 1 of sFrameT) + (word 1 of tTW)) \
         & comma & ((word 2 of sFrameT) + (word 2 of tTW)) \
         & comma & ((word 3 of sFrameT) + (word 3 of tTW))
end Xform.Object

## Draw one cached mesh into its own line graphic (graphic name = transform key).
on RenderMeshFast pGeo,pGraphic
   if there is not a graphic pGraphic then exit RenderMeshFast
   set the points of graphic pGraphic to RenderMeshPoints(pGeo,pGraphic)
end RenderMeshFast

## One object's screen lines, as graphic points, without depth bands.
function RenderMeshPoints pGeo,pKey
   put empty into tBuf
   RenderMeshInto pGeo,pKey,"_",tBuf,true
   return tBuf["_"]
end RenderMeshPoints

## Phase 3/4: adds one object's screen line segments to pBuf[graphic name].
## Several objects share one graphic (colour batching). With depth bands on (Phase 4),
## farther edges go to faded copies of the graphic: pGraphic_d2, _d3, _d4.
## pGeo = mesh name ("Rock"), pKey = transform key ("Rock_3"), pGraphic = target graphic.
command RenderMeshInto pGeo,pKey,pGraphic,@pBuf,pNoBands
   put Mesh.Get(pGeo) into tMesh
   put tMesh["count"] into tCount
   if tCount < 1 then exit RenderMeshInto
   
   -- Object transform -> one matrix and one translation.
   set itemDel to comma
   put Xform.Object(pKey) into tXf
   put item 1 of tXf into m1
   put item 2 of tXf into m2
   put item 3 of tXf into m3
   put item 4 of tXf into m4
   put item 5 of tXf into m5
   put item 6 of tXf into m6
   put item 7 of tXf into m7
   put item 8 of tXf into m8
   put item 9 of tXf into m9
   put item 10 of tXf into t1
   put item 11 of tXf into t2
   put item 12 of tXf into t3
   
   put tMesh["vx"] into tVX
   put tMesh["vy"] into tVY
   put tMesh["vz"] into tVZ
   put sProjK into tK
   put sProjOffX into tOffX
   put sProjOffY into tOffY
   put gNearPlane into tNear
   
   -- PASS 1: every vertex to camera space, and to screen if in front of the near plane.
   repeat with i = 1 to tCount
      put tVX[i] into x
      put tVY[i] into y
      put tVZ[i] into z
      put m1*x + m2*y + m3*z + t1 into tCX[i]
      put m4*x + m5*y + m6*z + t2 into tCY[i]
      put m7*x + m8*y + m9*z + t3 into tZ
      put tZ into tCZ[i]
      if tZ >= tNear then
         put true into tIn[i]
         put tCX[i] * tK / tZ + tOffX into tSX[i]
         put tCY[i] * tK / tZ + tOffY into tSY[i]
      else
         put false into tIn[i]
      end if
   end repeat
   
   -- Depth brightness bands (Phase 4).
   put 1 into tBands
   if pNoBands is not true then put sViewBands into tBands
   if tBands > 1 then
      repeat with tB = 2 to tBands
         put View.BandGraphic(pGraphic,tB) into tBandG[tB]
      end repeat
      put sViewNear into tDNear
      put tBands / (sViewFar - sViewNear) into tDK
   end if
   
   -- PASS 2: edges.
   put tMesh["ea"] into tEA
   put tMesh["eb"] into tEB
   put 0 into tDrawn
   repeat with e = 1 to tMesh["edgeCount"]
      put tEA[e] into a
      put tEB[e] into b
      
      if tIn[a] and tIn[b] then
         put tSX[a] into x1
         put tSY[a] into y1
         put tSX[b] into x2
         put tSY[b] into y2
      else if not tIn[a] and not tIn[b] then
         next repeat
      else
         -- One end behind the camera: shorten the line, then project.
         put ClipLineToNearPlane(tCX[a],tCY[a],tCZ[a],tCX[b],tCY[b],tCZ[b]) into tClip
         if tClip is empty then next repeat
         put (word 1 of tClip) * tK / (word 3 of tClip) + tOffX into x1
         put (word 2 of tClip) * tK / (word 3 of tClip) + tOffY into y1
         put (word 4 of tClip) * tK / (word 6 of tClip) + tOffX into x2
         put (word 5 of tClip) * tK / (word 6 of tClip) + tOffY into y2
      end if
      
      -- Only run the viewport clipper when an end is off screen.
      if x1 < gViewLeft or x1 > gViewRight or y1 < gViewTop or y1 > gViewBottom \
            or x2 < gViewLeft or x2 > gViewRight or y2 < gViewTop or y2 > gViewBottom then
         put ClipLineToViewport(x1,y1,x2,y2) into tClip
         if tClip is empty then next repeat
         put word 1 of tClip into x1
         put word 2 of tClip into y1
         put word 3 of tClip into x2
         put word 4 of tClip into y2
      end if
      
      put cr & round(x1) & comma & round(y1) & cr & round(x2) & comma & round(y2) & cr & cr into tSeg
      if tBands > 1 then
         put trunc(((tCZ[a] + tCZ[b]) / 2 - tDNear) * tDK) + 1 into tBand
         if tBand <= 1 then
            put tSeg after pBuf[pGraphic]
         else
            if tBand > tBands then put tBands into tBand
            put tSeg after pBuf[tBandG[tBand]]
         end if
      else
         put tSeg after pBuf[pGraphic]
      end if
      add 1 to tDrawn
   end repeat
   
   add tDrawn to sEdgesDrawn
end RenderMeshInto


######################################################################################
## MESH CACHE
## Built ONCE per geometry from the stack's xyz<Name>Array and <Name>Edges properties,
## instead of re-reading custom properties for every vertex on every frame.
## Call Mesh.Invalidate "Name" after changing a mesh (e.g. OBJ import).
######################################################################################

function Mesh.Get pGeo
   global gMeshCache
   if gMeshCache[pGeo]["count"] is empty then Mesh.Build pGeo
   return gMeshCache[pGeo]
end Mesh.Get

on Mesh.Invalidate pGeo
   global gMeshCache
   if pGeo is empty then
      put empty into gMeshCache
   else
      delete variable gMeshCache[pGeo]
   end if
end Mesh.Invalidate

## Load one of the original stack-stored meshes (Cube, Cylinder, Cone, Imported)
## into the Phase 2 mesh format. Procedural meshes use Mesh.Define instead.
on Mesh.Build pGeo
   global gMeshCache
   put Mesh.New() into tMesh
   
   -- Vertices.
   set the customPropertySet of stack (the mainStack of this stack) to empty
   put "xyz" & pGeo & "Array" into tLabel
   put the tLabel of stack (the mainStack of this stack) into tXYZ
   put the number of lines of the keys of tXYZ["x"] into tCount
   put empty into tVertText
   repeat with i = 1 to tCount
      put tXYZ["x"][i] + 0 into tMesh["vx"][i]
      put tXYZ["y"][i] + 0 into tMesh["vy"][i]
      put tXYZ["z"][i] + 0 into tMesh["vz"][i]
      put tMesh["vx"][i] && tMesh["vy"][i] && tMesh["vz"][i] & cr after tVertText
   end repeat
   put tCount into tMesh["count"]
   
   -- Faces (for picking).
   put pGeo & "Faces" into tFaceLabel
   put the tFaceLabel of stack (the mainStack of this stack) into tFaces
   filter lines of tFaces without empty
   put tFaces into tMesh["faces"]
   
   -- Edges: keep the hand-made edge lists so these meshes draw exactly as before.
   if pGeo is "Cube" then
      put "1 3,1 2,1 5,2 4,2 6,3 4,4 8,5 6,5 7,6 8,7 3,7 8" into tEdges
      replace comma with cr in tEdges
   else
      put pGeo & "Edges" into tEdgeLabel
      put the tEdgeLabel of stack (the mainStack of this stack) into tEdges
   end if
   if tEdges is not empty then
      put tEdges into tMesh["lines"]
      put false into tMesh["edgesFromFaces"]
   end if
   
   -- Keep the graphic's copies in sync for any old code that reads them.
   put pGeo & "Line" into tGraphic
   if there is a graphic tGraphic then
      set the customPropertySet of graphic tGraphic to empty
      set the MeshVertices of graphic tGraphic to tVertText
      set the MeshEdges of graphic tGraphic to tEdges
   end if
   
   put Mesh.Finalize(tMesh) into gMeshCache[pGeo]
end Mesh.Build


######################################################################################
## PHASE 2: MESH FORMAT + PROCEDURAL PRIMITIVES  (11 08 2026)
##
## A mesh is a LiveCode array:
##   ["count"]           number of vertices
##   ["vx"][i] ["vy"][i] ["vz"][i]   vertex i, mesh-local coordinates
##   ["faces"]           one polygon per line, vertex indices separated by spaces.
##                       Any n-gon, convex or concave. NO triangulation anywhere.
##   ["lines"]           optional wire-only edges, "a b" per line (masts, antennas)
## Mesh.Finalize adds:
##   ["ea"][k] ["eb"][k] ["edgeCount"]   unique edges (from faces + lines)
##   ["radius"]          bounding radius from the mesh origin (for collisions later)
##
## AXES: +X right, +Y DOWN (screen style), +Z away. So "up" is -Y.
## Outlines and profiles use one point per line, OR "|" between points:
##   MeshLoft("0,60|20,25|20,-50|-20,-50|-20,25", 0, ...)
##
## Generators return a RAW mesh. Mesh.Transform / Mesh.Merge work on raw meshes.
## Mesh.Define "Name", tMesh finalizes it and puts it in gMeshCache, ready to draw:
##   Mesh.Define "Rock", MeshPyramid(5,30,50)
##   put Entity.Spawn("Rock",180,235,90,"orange") into tId   -- Phase 3 instances
##   Scene.AddObject "Sea","SeaLine",0,260,0,"#2E6F8E"       -- object with its own graphic
######################################################################################

function Mesh.New
   put 0 into tMesh["count"]
   put empty into tMesh["faces"]
   put empty into tMesh["lines"]
   return tMesh
end Mesh.New

## Adds a vertex; the new index is in the result.
command Mesh.AddVertex @pMesh,pX,pY,pZ
   add 1 to pMesh["count"]
   put pMesh["count"] into tI
   put pX + 0 into pMesh["vx"][tI]
   put pY + 0 into pMesh["vy"][tI]
   put pZ + 0 into pMesh["vz"][tI]
   return tI
end Mesh.AddVertex

## pIndices: vertex indices separated by spaces, in order around the polygon.
command Mesh.AddFace @pMesh,pIndices
   if pMesh["faces"] is empty then
      put pIndices into pMesh["faces"]
   else
      put cr & pIndices after pMesh["faces"]
   end if
end Mesh.AddFace

## A wire-only edge with no face (not pickable).
command Mesh.AddLine @pMesh,pA,pB
   if pMesh["lines"] is empty then
      put pA && pB into pMesh["lines"]
   else
      put cr & pA && pB after pMesh["lines"]
   end if
end Mesh.AddLine

## Store a finished mesh under a name so Scene objects can use it.
on Mesh.Define pName,pMesh
   global gMeshCache
   put Mesh.Finalize(pMesh) into gMeshCache[pName]
end Mesh.Define

## Builds the unique edge list and bounding radius.
## Edges come from the faces unless ["edgesFromFaces"] is false (legacy stack meshes
## with hand-made edge lists), plus every wire line.
function Mesh.Finalize pMesh
   put pMesh["count"] + 0 into tCount
   put tCount into pMesh["count"]
   put empty into tSeen
   put 0 into tE
   delete variable pMesh["ea"]
   delete variable pMesh["eb"]
   
   if pMesh["edgesFromFaces"] is not false then
      repeat for each line tFace in pMesh["faces"]
         put the number of words of tFace into tN
         if tN < 2 then next repeat
         repeat with k = 1 to tN
            Mesh.PushEdge pMesh,tSeen,tE,word k of tFace,word ((k mod tN) + 1) of tFace
         end repeat
      end repeat
   end if
   repeat for each line tLine in pMesh["lines"]
      Mesh.PushEdge pMesh,tSeen,tE,word 1 of tLine,word 2 of tLine
   end repeat
   put tE into pMesh["edgeCount"]
   
   put 0 into tR2
   repeat with i = 1 to tCount
      put pMesh["vx"][i]^2 + pMesh["vy"][i]^2 + pMesh["vz"][i]^2 into tD2
      if tD2 > tR2 then put tD2 into tR2
   end repeat
   put sqrt(tR2) into pMesh["radius"]
   return pMesh
end Mesh.Finalize

command Mesh.PushEdge @pMesh,@pSeen,@pE,pA,pB
   if pA is not an integer or pB is not an integer then exit Mesh.PushEdge
   if pA = pB or pA < 1 or pB < 1 then exit Mesh.PushEdge
   if pA > pMesh["count"] or pB > pMesh["count"] then exit Mesh.PushEdge
   if pA < pB then
      put pA & "_" & pB into tKey
   else
      put pB & "_" & pA into tKey
   end if
   if pSeen[tKey] is not empty then exit Mesh.PushEdge
   put true into pSeen[tKey]
   add 1 to pE
   put pA into pMesh["ea"][pE]
   put pB into pMesh["eb"][pE]
end Mesh.PushEdge

## Accept "a,b|c,d" or one point per line.
function Mesh.Points pText
   replace "|" with cr in pText
   filter lines of pText without empty
   return pText
end Mesh.Points

## Polygon "1 2 3 ... n" offset by pStart, optionally reversed.
function Mesh.Ring pStart,pN,pReverse
   put empty into tFace
   repeat with k = 1 to pN
      if pReverse then
         put pStart + pN - k into tIdx
      else
         put pStart + k - 1 into tIdx
      end if
      if tFace is empty then
         put tIdx into tFace
      else
         put space & tIdx after tFace
      end if
   end repeat
   return tFace
end Mesh.Ring


## ---------------------------------------------------------------- GENERATORS

## Box centered on the origin. 8 vertices, 6 faces, 12 edges.
function MeshBox pW,pH,pD
   put Mesh.New() into tM
   put pW/2 into hw
   put pH/2 into hh
   put pD/2 into hd
   Mesh.AddVertex tM,-hw,-hh,-hd
   Mesh.AddVertex tM,hw,-hh,-hd
   Mesh.AddVertex tM,hw,hh,-hd
   Mesh.AddVertex tM,-hw,hh,-hd
   Mesh.AddVertex tM,-hw,-hh,hd
   Mesh.AddVertex tM,hw,-hh,hd
   Mesh.AddVertex tM,hw,hh,hd
   Mesh.AddVertex tM,-hw,hh,hd
   Mesh.AddFace tM,"1 2 3 4"
   Mesh.AddFace tM,"5 8 7 6"
   Mesh.AddFace tM,"1 5 6 2"
   Mesh.AddFace tM,"4 3 7 8"
   Mesh.AddFace tM,"1 4 8 5"
   Mesh.AddFace tM,"2 6 7 3"
   return tM
end MeshBox

## N-sided prism standing on the Y axis, centered. 6-8 sides makes a fine cylinder.
## Edges: 3 * sides.
function MeshPrism pSides,pRadius,pHeight
   if pSides < 3 then put 3 into pSides
   put Mesh.New() into tM
   repeat with k = 1 to pSides
      put 2 * pi * (k-1) / pSides into tA
      Mesh.AddVertex tM,pRadius*cos(tA),-pHeight/2,pRadius*sin(tA)
   end repeat
   repeat with k = 1 to pSides
      put 2 * pi * (k-1) / pSides into tA
      Mesh.AddVertex tM,pRadius*cos(tA),pHeight/2,pRadius*sin(tA)
   end repeat
   repeat with k = 1 to pSides
      put (k mod pSides) + 1 into k2
      Mesh.AddFace tM,k && k2 && (pSides+k2) && (pSides+k)
   end repeat
   Mesh.AddFace tM,Mesh.Ring(1,pSides,false)
   Mesh.AddFace tM,Mesh.Ring(pSides+1,pSides,true)
   return tM
end MeshPrism

## N-sided pyramid / cone: base at +h/2 (bottom), apex at -h/2 (top). Edges: 2 * sides.
function MeshPyramid pSides,pRadius,pHeight
   if pSides < 3 then put 3 into pSides
   put Mesh.New() into tM
   repeat with k = 1 to pSides
      put 2 * pi * (k-1) / pSides into tA
      Mesh.AddVertex tM,pRadius*cos(tA),pHeight/2,pRadius*sin(tA)
   end repeat
   Mesh.AddVertex tM,0,-pHeight/2,0
   put the result into tApex
   repeat with k = 1 to pSides
      put (k mod pSides) + 1 into k2
      Mesh.AddFace tM,k && k2 && tApex
   end repeat
   Mesh.AddFace tM,Mesh.Ring(1,pSides,true)
   return tM
end MeshPyramid

## Spin a 2D profile around the Y axis.
## pProfile: "radius,y" points from top to bottom. Radius 0 = a single pole vertex.
##   e.g. buoy: MeshLathe("0,-30|6,-18|14,0|10,12|0,12", 6)
function MeshLathe pProfile,pSides
   if pSides < 3 then put 3 into pSides
   put Mesh.Points(pProfile) into pProfile
   put Mesh.New() into tM
   put 0 into tP
   repeat for each line tPt in pProfile
      add 1 to tP
      put item 1 of tPt into tR
      put item 2 of tPt into tY
      put tM["count"] + 1 into tStart[tP]
      if abs(tR) < 0.0001 then
         Mesh.AddVertex tM,0,tY,0
         put 1 into tSize[tP]
      else
         repeat with k = 1 to pSides
            put 2 * pi * (k-1) / pSides into tA
            Mesh.AddVertex tM,tR*cos(tA),tY,tR*sin(tA)
         end repeat
         put pSides into tSize[tP]
      end if
   end repeat
   put tP into tProfileCount
   
   -- Bands between neighbouring profile points.
   repeat with p = 1 to tProfileCount - 1
      put tStart[p] into a0
      put tStart[p+1] into b0
      if tSize[p] = 1 and tSize[p+1] = 1 then
         Mesh.AddLine tM,a0,b0
      else if tSize[p] = 1 then
         repeat with k = 1 to pSides
            put (k mod pSides) + 1 into k2
            Mesh.AddFace tM,a0 && (b0+k-1) && (b0+k2-1)
         end repeat
      else if tSize[p+1] = 1 then
         repeat with k = 1 to pSides
            put (k mod pSides) + 1 into k2
            Mesh.AddFace tM,(a0+k-1) && (a0+k2-1) && b0
         end repeat
      else
         repeat with k = 1 to pSides
            put (k mod pSides) + 1 into k2
            Mesh.AddFace tM,(a0+k-1) && (a0+k2-1) && (b0+k2-1) && (b0+k-1)
         end repeat
      end if
   end repeat
   
   -- Flat caps where the profile starts or ends on a ring.
   if tProfileCount > 0 then
      if tSize[1] > 1 then Mesh.AddFace tM,Mesh.Ring(tStart[1],pSides,false)
      if tSize[tProfileCount] > 1 then Mesh.AddFace tM,Mesh.Ring(tStart[tProfileCount],pSides,true)
   end if
   return tM
end MeshLathe

## Low-poly sphere (a lathe with poles). 3 rings x 6 sides is very "vector".
function MeshSphere pRadius,pRings,pSides
   if pRings < 2 then put 2 into pRings
   put empty into tProfile
   repeat with r = 0 to pRings
      put pi * r / pRings into tA
      put pRadius * sin(tA) into tR
      if abs(tR) < 0.0001 then put 0 into tR
      put tR & comma & (-pRadius * cos(tA)) & cr after tProfile
   end repeat
   return MeshLathe(tProfile,pSides)
end MeshSphere

## Connect two outlines (seen from above, "x,z" points, same count) at two heights.
## The workhorse for hulls, wings and ships. Caps may be concave.
## TIP: make outline B a uniformly SCALED copy of outline A (same center) so every
## side face is flat. Twisted (non-flat) sides still draw fine, but can be missed
## by picking when viewed nearly edge-on.
function MeshLoft pOutlineA,pYA,pOutlineB,pYB
   put Mesh.Points(pOutlineA) into pOutlineA
   put Mesh.Points(pOutlineB) into pOutlineB
   put min(the number of lines of pOutlineA, the number of lines of pOutlineB) into tN
   put Mesh.New() into tM
   if tN < 2 then return tM
   repeat with k = 1 to tN
      put line k of pOutlineA into tPt
      Mesh.AddVertex tM,item 1 of tPt,pYA,item 2 of tPt
   end repeat
   repeat with k = 1 to tN
      put line k of pOutlineB into tPt
      Mesh.AddVertex tM,item 1 of tPt,pYB,item 2 of tPt
   end repeat
   repeat with k = 1 to tN
      put (k mod tN) + 1 into k2
      Mesh.AddFace tM,k && k2 && (tN+k2) && (tN+k)
   end repeat
   if tN > 2 then
      Mesh.AddFace tM,Mesh.Ring(1,tN,false)
      Mesh.AddFace tM,Mesh.Ring(tN+1,tN,true)
   end if
   return tM
end MeshLoft

## Extrude a flat outline ("x,y" points, front view) along Z, centered.
## Letters, logos, wing panels, TIE-fighter hex panels.
function MeshExtrude pOutline,pDepth
   put Mesh.Points(pOutline) into pOutline
   put the number of lines of pOutline into tN
   put Mesh.New() into tM
   if tN < 2 then return tM
   repeat with k = 1 to tN
      put line k of pOutline into tPt
      Mesh.AddVertex tM,item 1 of tPt,item 2 of tPt,-pDepth/2
   end repeat
   repeat with k = 1 to tN
      put line k of pOutline into tPt
      Mesh.AddVertex tM,item 1 of tPt,item 2 of tPt,pDepth/2
   end repeat
   repeat with k = 1 to tN
      put (k mod tN) + 1 into k2
      Mesh.AddFace tM,k && k2 && (tN+k2) && (tN+k)
   end repeat
   if tN > 2 then
      Mesh.AddFace tM,Mesh.Ring(1,tN,false)
      Mesh.AddFace tM,Mesh.Ring(tN+1,tN,true)
   end if
   return tM
end MeshExtrude

## Flat grid in the XZ plane, centered. Edges: 2*c*r + c + r.
function MeshGrid pCols,pRows,pSpacing
   put Mesh.New() into tM
   put pCols * pSpacing / 2 into tHalfW
   put pRows * pSpacing / 2 into tHalfD
   repeat with r = 0 to pRows
      repeat with c = 0 to pCols
         Mesh.AddVertex tM,c*pSpacing - tHalfW,0,r*pSpacing - tHalfD
      end repeat
   end repeat
   put pCols + 1 into tW
   repeat with r = 0 to pRows - 1
      repeat with c = 1 to pCols
         put r*tW + c into tA
         Mesh.AddFace tM,tA && (tA+1) && (tA+tW+1) && (tA+tW)
      end repeat
   end repeat
   return tM
end MeshGrid


## ---------------------------------------------------------------- COMBINING

## Rotate (radians, Z then Y then X), scale, then move a raw mesh.
function Mesh.Transform pMesh,pRX,pRY,pRZ,pTX,pTY,pTZ,pScale
   if pScale is empty then put 1 into pScale
   set itemDel to comma
   put Mat3.RotZYX(pRX+0,pRY+0,pRZ+0) into tR
   repeat with i = 1 to pMesh["count"]
      put pMesh["vx"][i] * pScale into x
      put pMesh["vy"][i] * pScale into y
      put pMesh["vz"][i] * pScale into z
      put (item 1 of tR)*x + (item 2 of tR)*y + (item 3 of tR)*z + pTX into pMesh["vx"][i]
      put (item 4 of tR)*x + (item 5 of tR)*y + (item 6 of tR)*z + pTY into pMesh["vy"][i]
      put (item 7 of tR)*x + (item 8 of tR)*y + (item 9 of tR)*z + pTZ into pMesh["vz"][i]
   end repeat
   return pMesh
end Mesh.Transform

## Append mesh B to mesh A (indices of B are shifted).
function Mesh.Merge pA,pB
   put pA["count"] + 0 into tOff
   repeat with i = 1 to pB["count"]
      Mesh.AddVertex pA,pB["vx"][i],pB["vy"][i],pB["vz"][i]
   end repeat
   repeat for each line tFace in pB["faces"]
      put empty into tNew
      repeat for each word tW in tFace
         if tNew is empty then
            put tW + tOff into tNew
         else
            put space & (tW + tOff) after tNew
         end if
      end repeat
      if tNew is not empty then Mesh.AddFace pA,tNew
   end repeat
   repeat for each line tLine in pB["lines"]
      if the number of words of tLine >= 2 then Mesh.AddLine pA,(word 1 of tLine) + tOff,(word 2 of tLine) + tOff
   end repeat
   return pA
end Mesh.Merge


## ---------------------------------------------------------------- DEMO MODELS




######################################################################################
## SCENE OBJECT LIST
## gSceneObjects: one line per drawn object, "MeshName GraphicName".
## The graphic name is also the object's key in gObjectTransforms.
## game.render draws this list; test.Raycast picks from it.
######################################################################################

## Add an existing graphic/transform to the draw list (does not move it).
## Add an object to the draw list (does not move it).
## pKey = its transform key. pGraphic = graphic to draw into (empty = graphic named pKey).
on Scene.Register pMesh,pKey,pGraphic
   global gSceneObjects
   global gObjectTransforms
   if pMesh is empty or pKey is empty then exit Scene.Register
   if Scene.Has(pKey) then exit Scene.Register
   -- Phase 5: remember the mesh and its bounding radius for collisions and FX.
   put Mesh.Get(pMesh) into tMeshData
   put pMesh into gObjectTransforms[pKey]["mesh"]
   if gObjectTransforms[pKey]["radius"] is empty then put tMeshData["radius"] into gObjectTransforms[pKey]["radius"]
   put pMesh && pKey into tLine
   if pGraphic is not empty and pGraphic is not pKey then put space & pGraphic after tLine
   if gSceneObjects is empty then
      put tLine into gSceneObjects
   else
      put cr & tLine after gSceneObjects
   end if
end Scene.Register

function Scene.Has pKey
   global gSceneObjects
   repeat for each line tEntry in gSceneObjects
      if word 2 of tEntry is pKey then return true
   end repeat
   return false
end Scene.Has

## Create (if needed) a line graphic for a mesh, place it, and add it to the draw list.
on Scene.AddObject pMesh,pGraphic,pX,pY,pZ,pColor
   Scene.NewLineGraphic pGraphic
   if pColor is not empty then
      if there is a graphic pGraphic then set the foregroundColor of graphic pGraphic to pColor
      put pColor into sOrigColor[pGraphic]
   end if
   SetObjectPosition pGraphic,pX,pY,pZ
   SetObjectRotation pGraphic,0,0,0
   SetObjectRotationSpeed pGraphic,0,0,0
   Scene.Register pMesh,pGraphic
end Scene.AddObject

## Take an object out of the draw list (its transform stays; see Entity.Kill).
on Scene.Remove pKey
   global gSceneObjects
   put empty into tKeep
   repeat for each line tEntry in gSceneObjects
      if word 2 of tEntry is not pKey then put tEntry & cr after tKeep
   end repeat
   delete the last char of tKeep
   put tKeep into gSceneObjects
   -- An object with its own graphic: clear it now. Batches are cleared by game.render.
   if there is a graphic pKey then set the points of graphic pKey to empty
end Scene.Remove


######################################################################################
## PHASE 3: ENTITIES  (11 08 2026)
## Many objects can share ONE mesh. Each entity is just a transform key
## (e.g. "Rock_3") in gObjectTransforms plus a line in the scene list.
## Entities of the same colour draw into one shared graphic, "Batch_<colour>",
## so 20 rocks cost one "set the points" per frame instead of 20.
##   put Entity.Spawn("Rock",100,235,50,"orange") into tId
##   SetObjectRotationSpeed tId,0,0.01,0
##   Entity.Kill tId
## From a card key handler: get Entity.SpawnRock()  /  Selection.Kill
######################################################################################

## Create an entity using a defined mesh. Returns its id.
function Entity.Spawn pMesh,pX,pY,pZ,pColor
   global gObjectTransforms
   add 1 to sEntitySerial
   put pMesh & "_" & sEntitySerial into tId
   SetObjectPosition tId,pX,pY,pZ
   SetObjectRotation tId,0,0,0
   SetObjectRotationSpeed tId,0,0,0
   SetObjectVelocity tId,0,0,0
   put pMesh into gObjectTransforms[tId]["mesh"]
   Scene.Register pMesh,tId,Scene.ColorGraphic(pColor)
   return tId
end Entity.Spawn

## Remove an entity (or any scene object) completely.
on Entity.Kill pId
   global gObjectTransforms
   if pId is empty then exit Entity.Kill
   Scene.Remove pId
   delete variable gObjectTransforms[pId]
   if gSelectedObject is pId then put empty into gSelectedObject
end Entity.Kill

## How many objects use a mesh (e.g. Entity.Count("Rock")).
function Entity.Count pMesh
   global gSceneObjects
   put 0 into tN
   repeat for each line tEntry in gSceneObjects
      if word 1 of tEntry is pMesh then add 1 to tN
   end repeat
   return tN
end Entity.Count

## The shared graphic for a colour, created on first use.
function Scene.ColorGraphic pColor
   if pColor is empty then put "white" into pColor
   put pColor into tName
   replace "#" with empty in tName
   replace space with "_" in tName
   replace comma with "_" in tName
   put "Batch_" & tName into tGraphic
   if there is not a graphic tGraphic then
      Scene.NewLineGraphic tGraphic
      if there is a graphic tGraphic then set the foregroundColor of graphic tGraphic to pColor
   end if
   -- Remember the real colour (a mono view preset recolours the graphic).
   put pColor into sOrigColor[tGraphic]
   return tGraphic
end Scene.ColorGraphic



######################################################################################
## PHASE 5: GAMEPLAY SYSTEMS  (11 08 2026)
##
## "WORLD" SPACE used by collisions and particles = the space object positions live in
## (SetObjectPosition). A point P there draws at   camera = Rcam * P + sFrameT.
##
## COLLISIONS   bounding spheres, checked every game.update step
##   Collision.SetGroup "BoatLine","boat"          (optional 3rd param: radius)
##   Collision.AddRule "rock","boat"               (rock vs boat pairs are tested)
##   On contact:  dispatch "Collision.Hit" to this card with keyA,keyB
##   Handle Collision.Hit in a card script for game rules (don't pass it), or let the
##   stack default run: anything with an "hp" value explodes.
##
## PARTICLES    one pool (max kMaxParticles) of short 3D line segments.
##   Each draws into a colour batch graphic, so particles cost no extra controls.
##
## FX           FX.Explode tKey   -- the object bursts into its own edges + sparks
##              FX.Sparks x,y,z,count,colour
##
## WEAPON       Game card: click = laser from both bottom corners to the mouse.
##   Objects with "hp" lose 1 per hit and explode at 0. Others just spark.
######################################################################################

## ---------------------------------------------------------------- COLLISIONS

on Collision.SetGroup pKey,pGroup,pRadius
   global gObjectTransforms
   put pGroup into gObjectTransforms[pKey]["group"]
   if pRadius is a number then put pRadius into gObjectTransforms[pKey]["radius"]
end Collision.SetGroup

on Collision.AddRule pGroupA,pGroupB
   put pGroupA && pGroupB into tRule
   if tRule is among the lines of sCollisionRules then exit Collision.AddRule
   if sCollisionRules is empty then
      put tRule into sCollisionRules
   else
      put cr & tRule after sCollisionRules
   end if
end Collision.AddRule

on Collision.ClearRules
   put empty into sCollisionRules
end Collision.ClearRules

## Every pair of touching objects that a rule allows. Once per game.update.
on Collision.Update
   global gObjectTransforms
   if sCollisionRules is empty then exit Collision.Update
   
   -- Members of each group.
   repeat for each key tKey in gObjectTransforms
      put gObjectTransforms[tKey]["group"] into tGroup
      if tGroup is not empty then put tKey & cr after tMembers[tGroup]
   end repeat
   
   put empty into tHits
   repeat for each line tRule in sCollisionRules
      put word 1 of tRule into tGA
      put word 2 of tRule into tGB
      repeat for each line tA in tMembers[tGA]
         put gObjectTransforms[tA]["x"] into ax
         put gObjectTransforms[tA]["y"] into ay
         put gObjectTransforms[tA]["z"] into az
         put gObjectTransforms[tA]["radius"] into ar
         repeat for each line tB in tMembers[tGB]
            -- Same group: test each pair once.
            if tGA is tGB and tB <= tA then next repeat
            put gObjectTransforms[tB]["radius"] + ar into tR
            put gObjectTransforms[tB]["x"] - ax into dx
            if abs(dx) > tR then next repeat
            put gObjectTransforms[tB]["z"] - az into dz
            if abs(dz) > tR then next repeat
            put gObjectTransforms[tB]["y"] - ay into dy
            if dx*dx + dy*dy + dz*dz < tR*tR then put tA & comma & tB & cr after tHits
         end repeat
      end repeat
   end repeat
   
   repeat for each line tHit in tHits
      put item 1 of tHit into tA
      put item 2 of tHit into tB
      -- Skip pairs whose objects were removed by an earlier hit this step.
      if gObjectTransforms[tA] is not an array or gObjectTransforms[tB] is not an array then next repeat
      dispatch "Collision.Hit" to this card with tA,tB
   end repeat
end Collision.Update

## Default rule (runs when no card script handles Collision.Hit):
## anything with hit points explodes on contact.
on Collision.Hit pA,pB
   global gObjectTransforms
   if gObjectTransforms[pA]["hp"] is a number then FX.Destroy pA
   if gObjectTransforms[pB]["hp"] is a number then FX.Destroy pB
end Collision.Hit


## ---------------------------------------------------------------- PARTICLES
## Parallel arrays, index 1..sPCount. Each particle is a segment: center P, half-vector H.

on Particles.Clear
   put 0 into sPCount
   FX.ClearDerez
end Particles.Clear

## pSpin: true = tumbles. pGravity: added to Y speed each step (+Y is down).
on Particles.Add pX,pY,pZ,pHX,pHY,pHZ,pVX,pVY,pVZ,pLife,pGraphic,pSpin,pGravity
   if sPCount >= kMaxParticles then exit Particles.Add
   add 1 to sPCount
   put sPCount into i
   put pX into sPX[i]
   put pY into sPY[i]
   put pZ into sPZ[i]
   put pHX into sHX[i]
   put pHY into sHY[i]
   put pHZ into sHZ[i]
   put pVX into sVX[i]
   put pVY into sVY[i]
   put pVZ into sVZ[i]
   put pLife into sLife[i]
   put pGraphic into sPGfx[i]
   put pGravity + 0 into sPG[i]
   if pSpin then
      put (random(21) - 11) / 80 into tA
      put (random(21) - 11) / 80 into tB
      put cos(tA) into sSC[i]
      put sin(tA) into sSS[i]
      put cos(tB) into sTC[i]
      put sin(tB) into sTS[i]
   else
      put 1 into sSC[i]
      put 0 into sSS[i]
      put 1 into sTC[i]
      put 0 into sTS[i]
   end if
end Particles.Add

## Move the last particle into slot pIter (order does not matter).
## (Not "pI": LiveCode is case-insensitive and pi is a reserved constant.)
on Particles.RemoveAt pIter
   put sPCount into j
   if pIter < j then
      put sPX[j] into sPX[pIter]
      put sPY[j] into sPY[pIter]
      put sPZ[j] into sPZ[pIter]
      put sHX[j] into sHX[pIter]
      put sHY[j] into sHY[pIter]
      put sHZ[j] into sHZ[pIter]
      put sVX[j] into sVX[pIter]
      put sVY[j] into sVY[pIter]
      put sVZ[j] into sVZ[pIter]
      put sLife[j] into sLife[pIter]
      put sPGfx[j] into sPGfx[pIter]
      put sPG[j] into sPG[pIter]
      put sSC[j] into sSC[pIter]
      put sSS[j] into sSS[pIter]
      put sTC[j] into sTC[pIter]
      put sTS[j] into sTS[pIter]
   end if
   subtract 1 from sPCount
end Particles.RemoveAt

## Once per game.update.
on Particles.Update
   repeat with i = sPCount down to 1
      subtract 1 from sLife[i]
      if sLife[i] <= 0 then
         Particles.RemoveAt i
         next repeat
      end if
      add sVX[i] to sPX[i]
      add sVY[i] to sPY[i]
      add sVZ[i] to sPZ[i]
      add sPG[i] to sVY[i]
      -- Light drag.
      multiply sVX[i] by 0.97
      multiply sVY[i] by 0.97
      multiply sVZ[i] by 0.97
      -- Tumble: spin around Y, then around X.
      if sSS[i] is not 0 then
         put sHX[i] into hx
         put sHY[i] into hy
         put sHZ[i] into hz
         put hx*sSC[i] + hz*sSS[i] into tX
         put -hx*sSS[i] + hz*sSC[i] into tZ
         put hy*sTC[i] - tZ*sTS[i] into sHY[i]
         put hy*sTS[i] + tZ*sTC[i] into sHZ[i]
         put tX into sHX[i]
      end if
   end repeat
end Particles.Update

## Adds every particle's segment to the graphic buffers used by game.render.
on Particles.Render @pBuf
   if sPCount < 1 then exit Particles.Render
   set itemDel to comma
   put item 1 of sCamM into r1
   put item 2 of sCamM into r2
   put item 3 of sCamM into r3
   put item 4 of sCamM into r4
   put item 5 of sCamM into r5
   put item 6 of sCamM into r6
   put item 7 of sCamM into r7
   put item 8 of sCamM into r8
   put item 9 of sCamM into r9
   put word 1 of sFrameT into t1
   put word 2 of sFrameT into t2
   put word 3 of sFrameT into t3
   put gNearPlane into tNear
   put 0 into tDrawn
   repeat with i = 1 to sPCount
      -- Shrink away over the last 10 steps.
      if sLife[i] < 10 then
         put sLife[i] / 10 into s
      else
         put 1 into s
      end if
      put sHX[i]*s into hx
      put sHY[i]*s into hy
      put sHZ[i]*s into hz
      put sPX[i] - hx into ax
      put sPY[i] - hy into ay
      put sPZ[i] - hz into az
      put sPX[i] + hx into ex
      put sPY[i] + hy into ey
      put sPZ[i] + hz into ez
      put r7*ax + r8*ay + r9*az + t3 into za
      put r7*ex + r8*ey + r9*ez + t3 into zb
      if za < tNear or zb < tNear then next repeat
      put (r1*ax + r2*ay + r3*az + t1) * sProjK / za + sProjOffX into x1
      put (r4*ax + r5*ay + r6*az + t2) * sProjK / za + sProjOffY into y1
      put (r1*ex + r2*ey + r3*ez + t1) * sProjK / zb + sProjOffX into x2
      put (r4*ex + r5*ey + r6*ez + t2) * sProjK / zb + sProjOffY into y2
      -- Particles are small: drop any that leave the screen instead of clipping.
      if x1 < gViewLeft or x1 > gViewRight or y1 < gViewTop or y1 > gViewBottom \
            or x2 < gViewLeft or x2 > gViewRight or y2 < gViewTop or y2 > gViewBottom then next repeat
      put cr & round(x1) & comma & round(y1) & cr & round(x2) & comma & round(y2) & cr & cr after pBuf[sPGfx[i]]
      add 1 to tDrawn
   end repeat
   add tDrawn to sEdgesDrawn
end Particles.Render

function Particles.Count
   return sPCount
end Particles.Count


## ---------------------------------------------------------------- FX

## A random direction (length 1).
function FX.RandomDir
   repeat 10 times
      put (random(2001) - 1001) / 1000 into x
      put (random(2001) - 1001) / 1000 into y
      put (random(2001) - 1001) / 1000 into z
      put sqrt(x*x + y*y + z*z) into tLen
      if tLen > 0.1 and tLen <= 1 then return (x/tLen) && (y/tLen) && (z/tLen)
   end repeat
   return "0 -1 0"
end FX.RandomDir

## Classic vector explosion: the object breaks into its own edges, which fly apart
## and tumble, plus a burst of sparks. Then the object is removed.
on FX.Explode pKey
   global gObjectTransforms
   global gSceneObjects
   if pKey is empty or gObjectTransforms[pKey] is not an array then exit FX.Explode
   
   -- Which mesh and which graphic (so the debris keeps the object's colour).
   put empty into tMeshName
   repeat for each line tEntry in gSceneObjects
      if word 2 of tEntry is pKey then
         put word 1 of tEntry into tMeshName
         put word 3 of tEntry into tGraphic
         if tGraphic is empty then put pKey into tGraphic
         exit repeat
      end if
   end repeat
   
   if tMeshName is not empty then
      put Mesh.Get(tMeshName) into tMesh
      -- Vertex -> world: Rscene * Robj * v + position (matches what is on screen).
      Render.FrameMatrices
      set itemDel to comma
      put GetObjectRotation(pKey) into tRot
      put Mat3.Mul(sSceneM, Mat3.RotZYX(item 1 of tRot,item 2 of tRot,item 3 of tRot)) into tR
      put gObjectTransforms[pKey]["x"] into wx
      put gObjectTransforms[pKey]["y"] into wy
      put gObjectTransforms[pKey]["z"] into wz
      put tMesh["vx"] into tVX
      put tMesh["vy"] into tVY
      put tMesh["vz"] into tVZ
      put item 1 of tR into r1
      put item 2 of tR into r2
      put item 3 of tR into r3
      put item 4 of tR into r4
      put item 5 of tR into r5
      put item 6 of tR into r6
      put item 7 of tR into r7
      put item 8 of tR into r8
      put item 9 of tR into r9
      repeat with e = 1 to tMesh["edgeCount"]
         put tMesh["ea"][e] into a
         put tMesh["eb"][e] into b
         put r1*tVX[a] + r2*tVY[a] + r3*tVZ[a] into ax
         put r4*tVX[a] + r5*tVY[a] + r6*tVZ[a] into ay
         put r7*tVX[a] + r8*tVY[a] + r9*tVZ[a] into az
         put r1*tVX[b] + r2*tVY[b] + r3*tVZ[b] into bx2
         put r4*tVX[b] + r5*tVY[b] + r6*tVZ[b] into by2
         put r7*tVX[b] + r8*tVY[b] + r9*tVZ[b] into bz2
         -- Segment center (relative to the object) and half-vector.
         put (ax + bx2) / 2 into cx
         put (ay + by2) / 2 into cy
         put (az + bz2) / 2 into cz
         -- Fly outward from the object's center, a little upward, with some randomness.
         put sqrt(cx*cx + cy*cy + cz*cz) into tLen
         if tLen < 0.001 then
            put FX.RandomDir() into tDir
         else
            put (cx/tLen) && (cy/tLen) && (cz/tLen) into tDir
         end if
         put FX.RandomDir() into tJit
         put (random(30) + 15) / 10 into tSpeed
         Particles.Add wx+cx, wy+cy, wz+cz, \
               (bx2 - ax) / 2, (by2 - ay) / 2, (bz2 - az) / 2, \
               ((word 1 of tDir) + (word 1 of tJit)*0.4) * tSpeed, \
               ((word 2 of tDir) + (word 2 of tJit)*0.4) * tSpeed - 1.5, \
               ((word 3 of tDir) + (word 3 of tJit)*0.4) * tSpeed, \
               30 + random(20), tGraphic, true, 0.08
      end repeat
   else
      put gObjectTransforms[pKey]["x"] into wx
      put gObjectTransforms[pKey]["y"] into wy
      put gObjectTransforms[pKey]["z"] into wz
   end if
   
   FX.Sparks wx,wy,wz,12,"white"
   Entity.Kill pKey
end FX.Explode

## A burst of short bright streaks.
on FX.Sparks pX,pY,pZ,pCount,pColor
   put Scene.ColorGraphic(pColor) into tGraphic
   repeat pCount times
      put FX.RandomDir() into tDir
      put (random(40) + 30) / 10 into tSpeed
      put (word 1 of tDir) * tSpeed into vx
      put (word 2 of tDir) * tSpeed into vy
      put (word 3 of tDir) * tSpeed into vz
      Particles.Add pX,pY,pZ, vx*1.2,vy*1.2,vz*1.2, vx,vy,vz, 12 + random(10), tGraphic, false, 0
   end repeat
end FX.Sparks


## ---------------------------------------------------------------- WEAPON

## Hitscan laser at a screen point (mouse click on the Game card).
on Weapon.FireAt pScreenX,pScreenY
   global gObjectTransforms
   global gSceneObjects
   put pScreenX into sLaserX
   put pScreenY into sLaserY
   put 4 into sLaserFrames
   
   put ScreenToCameraRay(pScreenX,pScreenY,CenterX,CenterY,MOVEX,MOVEY,theScale,gFocalLength) into tRay
   if the number of words of tRay < 3 then exit Weapon.FireAt
   put RayCastScene(gSceneObjects,word 1 of tRay,word 2 of tRay,word 3 of tRay) into tHit
   if tHit is empty then exit Weapon.FireAt
   
   put word 2 of tHit into tKey
   -- Camera-space hit -> world: P = transpose(Rcam) * (hit - sFrameT).
   set itemDel to comma
   put (word 10 of tHit) - (word 1 of sFrameT) into qx
   put (word 11 of tHit) - (word 2 of sFrameT) into qy
   put (word 12 of tHit) - (word 3 of sFrameT) into qz
   put (item 1 of sCamM)*qx + (item 4 of sCamM)*qy + (item 7 of sCamM)*qz into px
   put (item 2 of sCamM)*qx + (item 5 of sCamM)*qy + (item 8 of sCamM)*qz into py
   put (item 3 of sCamM)*qx + (item 6 of sCamM)*qy + (item 9 of sCamM)*qz into pz
   
   if gObjectTransforms[tKey]["hp"] is a number then
      subtract 1 from gObjectTransforms[tKey]["hp"]
      if gObjectTransforms[tKey]["hp"] <= 0 then
         FX.Destroy tKey
         -- The key, and where it was hit (its transform is gone now).
         dispatch "Game.OnKill" to this card with tKey,px,py,pz
         return tKey
      end if
   end if
   FX.Sparks px,py,pz,6,"white"
   return tKey
end Weapon.FireAt

on Weapon.Update
   if sLaserFrames > 0 then subtract 1 from sLaserFrames
end Weapon.Update

## Two beams from the bottom corners to the target, Star Wars arcade style.
on Weapon.Render @pBuf
   if sLaserFrames < 1 then exit Weapon.Render
   put Scene.ColorGraphic("red") into tGraphic
   put round(sLaserX) & comma & round(sLaserY) into tTarget
   put cr & (gViewLeft + 20) & comma & (gViewBottom - 2) & cr & tTarget & cr & cr after pBuf[tGraphic]
   put cr & (gViewRight - 20) & comma & (gViewBottom - 2) & cr & tTarget & cr & cr after pBuf[tGraphic]
end Weapon.Render


## ---------------------------------------------------------------- DEMO RULES

## Rocks drift around the sea; keep them inside pBounds "xmin,xmax,zmin,zmax".
on Scene.SetBounds pKey,pBounds
   global gObjectTransforms
   put pBounds into gObjectTransforms[pKey]["bounds"]
end Scene.SetBounds



######################################################################################
## PHASE 4: THE VECTOR LOOK  (11 08 2026)
##
## VIEW SETTINGS (sView array). Change them, then View.Apply:
##   ["bands"]        1-4  depth brightness steps (1 = off, fastest)
##   ["fade"]         0-90 how faint the farthest band is (blendLevel)
##   ["depthNear"]    camera distance where fading starts
##   ["depthFar"]     camera distance of the faintest band
##   ["glow"]         true/false  LiveCode outerGlow on every 3D graphic (costs speed!)
##   ["glowSize"] ["glowSpread"] ["glowOpacity"]
##   ["lineSize"]     1 or 2
##   ["mono"]         one phosphor colour for everything, or empty for full colour
##   ["background"]   colour of the "Game" card
##   ["hud"]          true/false  vector-font score etc. while playing
##   ["hudColor"]
##   ["explode"]      "derez" (fast, dashes) or "debris" (every edge becomes a particle)
##
## PRESETS live in the stack's custom property set "ViewPresets", one array each.
## Built-ins (Arcade, Vectrex, 1983, Fast) are added if missing; edit or add more:
##   View.UsePreset "Vectrex"           View.Set "glow",false
##   View.SavePreset "MyLook"           put View.NextPreset() into tName  (cycle, for a button)
##   put View.Get("bands") into tBands  put View.PresetList() into tList
## The current preset name is remembered in the stack property "ViewCurrentPreset".
######################################################################################

## Built-in preset values.
function View.PresetDefaults pName
   put pName into tV["name"]
   put 3 into tV["bands"]
   put 60 into tV["fade"]
   put 450 into tV["depthNear"]
   put 950 into tV["depthFar"]
   put false into tV["glow"]
   put 3 into tV["glowSize"]
   put 0 into tV["glowSpread"]
   put 160 into tV["glowOpacity"]
   put 1 into tV["lineSize"]
   put empty into tV["mono"]
   put "black" into tV["background"]
   put true into tV["hud"]
   put "#00FF66" into tV["hudColor"]
   put "derez" into tV["explode"] -- "derez" (fast) or "debris" (every edge flies)
   switch pName
      case "Vectrex"
         -- One white-blue phosphor, deep fade, soft glow.
         put 4 into tV["bands"]
         put 75 into tV["fade"]
         put true into tV["glow"]
         put "#DDE8FF" into tV["mono"]
         put "#DDE8FF" into tV["hudColor"]
         break
      case "1983"
         -- Full colour, glow, gold HUD.
         put true into tV["glow"]
         put 4 into tV["glowSize"]
         put 200 into tV["glowOpacity"]
         put "#FFD200" into tV["hudColor"]
         break
      case "Fast"
         -- Everything off that costs time.
         put 1 into tV["bands"]
         put 0 into tV["fade"]
         break
      default
         -- "Arcade": full colour, 3 bands, no glow.
         put "Arcade" into tV["name"]
   end switch
   return tV
end View.PresetDefaults

## Called by APP.init.
on View.Init
   View.InstallPresets
   set the customPropertySet of stack (the mainStack of this stack) to empty
   put the ViewCurrentPreset of stack (the mainStack of this stack) into tName
   if tName is empty then put "Arcade" into tName
   VectorText.Init
   put 0 into sScore
   View.UsePreset tName
end View.Init

## Write the built-in presets into the stack, only where missing.
on View.InstallPresets
   put the customPropertySet of stack (the mainStack of this stack) into tOldSet
   set the customPropertySet of stack (the mainStack of this stack) to "ViewPresets"
   put the customKeys of stack (the mainStack of this stack) into tKeys
   repeat for each item tName in "Arcade,Vectrex,1983,Fast"
      if View.PresetKey(tName) is not among the lines of tKeys then
         put View.PresetDefaults(tName) into tV
         do "set the" && View.PresetKey(tName) && "of stack (the mainStack of this stack) to tV"
      end if
   end repeat
   set the customPropertySet of stack (the mainStack of this stack) to tOldSet
end View.InstallPresets

function View.PresetList
   put the customPropertySet of stack (the mainStack of this stack) into tOldSet
   set the customPropertySet of stack (the mainStack of this stack) to "ViewPresets"
   put the customKeys of stack (the mainStack of this stack) into tKeys
   set the customPropertySet of stack (the mainStack of this stack) to tOldSet
   set the customPropertySet of stack (the mainStack of this stack) to empty
   -- Property names back to preset names ("Preset_1983" -> "1983").
   put empty into tNames
   repeat for each line tKey in tKeys
      if tKey begins with "Preset_" then delete char 1 to 7 of tKey
      put tKey & cr after tNames
   end repeat
   delete the last char of tNames
   sort lines of tNames
   return tNames
end View.PresetList

## A preset name as a custom property name. Property names must start with a
## letter, so "1983" is stored as "Preset_1983".
function View.PresetKey pName
   replace space with empty in pName
   if char 1 of pName is not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" then return "Preset_" & pName
   return pName
end View.PresetKey

on View.UsePreset pName
   put the customPropertySet of stack (the mainStack of this stack) into tOldSet
   set the customPropertySet of stack (the mainStack of this stack) to "ViewPresets"
   put empty into tV
   if View.PresetKey(pName) is among the lines of the customKeys of stack (the mainStack of this stack) then
      do "put the" && View.PresetKey(pName) && "of stack (the mainStack of this stack) into tV"
   end if
   set the customPropertySet of stack (the mainStack of this stack) to tOldSet
   if tV is not an array then put View.PresetDefaults(pName) into tV
   put pName into tV["name"]
   put tV into sView
   set the customPropertySet of stack (the mainStack of this stack) to empty
   set the ViewCurrentPreset of stack (the mainStack of this stack) to pName
   ### !NOTE: SUPER IMPORTANT YOU MUST RETURN TO THE EMPTY CUSTOMPROPERTYSET AFTER USING SETS !
     set the customPropertySet of stack (the mainStack of this stack) to empty
   View.Apply
end View.UsePreset

## Save the current settings under a name (new or existing).
on View.SavePreset pName
   if pName is empty then put sView["name"] into pName
   put pName into sView["name"]
   put the customPropertySet of stack (the mainStack of this stack) into tOldSet
   -- Preset names become property names: letters and digits only.
   replace space with empty in pName
   put pName into sView["name"]
   put sView into tV
   set the customPropertySet of stack (the mainStack of this stack) to "ViewPresets"
   do "set the" && View.PresetKey(pName) && "of stack (the mainStack of this stack) to tV"
   set the customPropertySet of stack (the mainStack of this stack) to tOldSet
   set the customPropertySet of stack (the mainStack of this stack) to empty
   set the ViewCurrentPreset of stack (the mainStack of this stack) to pName
### !NOTE: SUPER IMPORTANT YOU MUST RETURN TO THE EMPTY CUSTOMPROPERTYSET AFTER USING SETS !
set the customPropertySet of stack (the mainStack of this stack) to empty
### ! so much havoc happens in those property sets 
   Menu.Threedots.Build
end View.SavePreset

## Next preset in the list (wraps). Returns its name, for a button label.
function View.NextPreset
   put View.PresetList() into tList
   put 0 into tLine
   repeat with i = 1 to the number of lines of tList
      if line i of tList is sView["name"] then put i into tLine
   end repeat
   if tLine = 0 or tLine >= the number of lines of tList then
      put 1 into tLine
   else
      add 1 to tLine
   end if
   View.UsePreset line tLine of tList
   return sView["name"]
end View.NextPreset

function View.Get pKey
   if pKey is empty then return sView
   return sView[pKey]
end View.Get

on View.Set pKey,pValue
   put pValue into sView[pKey]
   View.Apply
end View.Set

## View.Toggle "glow"         flips it
## View.Toggle "glow",false   sets it
on View.Toggle pKey,pState
   if pState is empty then
      put not (sView[pKey] is true) into sView[pKey]
   else
      put pState into sView[pKey]
   end if
   View.Apply
end View.Toggle

## Push the settings out. Graphics are restyled as they are next drawn.
on View.Apply
   put max(1, min(4, round(sView["bands"]))) into sViewBands
   put sView["depthNear"] + 0 into sViewNear
   put sView["depthFar"] + 0 into sViewFar
   if sViewFar <= sViewNear then put sViewNear + 1 into sViewFar
   put empty into sStyled
   if sView["background"] is not empty then
      if there is a card "Play" then set the backgroundColor of card "Play" to sView["background"]
      if there is a card "Game" then set the backgroundColor of card "Game" to sView["background"]
   end if
   HUD.Refresh
   if not sLoopActive then RENDER_VIEW
   UI.update.status.display
   Menu.Threedots.Build
end View.Apply

## The faded copy of a graphic for depth band pBand (2..4), created on first use.
function View.BandGraphic pBase,pBand
   put pBase & "_d" & pBand into tName
   if sBandMade[tName] is true then return tName
   if there is not a graphic tName then
      Scene.NewLineGraphic tName
      if there is not a graphic tName then return tName -- no Viewport here: try again later
      if there is a graphic pBase then set the foregroundColor of graphic tName to the effective foregroundColor of graphic pBase
   end if
   put pBase into sBandBase[tName]
   put true into sBandMade[tName]
   return tName
end View.BandGraphic

## Colour, fade, line size and glow for one 3D graphic, from the view settings.
on View.StyleGraphic pGraphic
   if there is not a graphic pGraphic then exit View.StyleGraphic
   -- Which band is this graphic? (name ends in _d2, _d3, _d4)
   put sBandBase[pGraphic] into tBase
   if tBase is empty then
      put 1 into tBand
      if sOrigColor[pGraphic] is empty then put the effective foregroundColor of graphic pGraphic into sOrigColor[pGraphic]
      put sOrigColor[pGraphic] into tColor
   else
      put char -1 of pGraphic into tBand
      if sOrigColor[tBase] is empty and there is a graphic tBase then put the effective foregroundColor of graphic tBase into sOrigColor[tBase]
      put sOrigColor[tBase] into tColor
   end if
   if sView["mono"] is not empty then put sView["mono"] into tColor
   if tColor is not empty then set the foregroundColor of graphic pGraphic to tColor
   set the lineSize of graphic pGraphic to max(1, sView["lineSize"])
   
   if sViewBands > 1 and tBand > 1 then
      set the blendLevel of graphic pGraphic to round(sView["fade"] * (tBand - 1) / (sViewBands - 1))
   else
      set the blendLevel of graphic pGraphic to 0
   end if
   
   -- Graphic effects are set one key at a time (see IndexEffectsValues).
   -- Read the current glow first: "the keys of the outerGlow of ..." can't be used inline.
   put the outerGlow of graphic pGraphic into fxArray
   if sView["glow"] is true then
      set the outerGlow["color"] of graphic pGraphic to Color.ToRGB(tColor)
      -- "normal": colorDodge (and screen) add nothing over a black background.
      -- (9.6.3 docs are wrong about the names: normal, multiply, colorDodge work.)
      set the outerGlow["blendMode"] of graphic pGraphic to "normal"
      set the outerGlow["opacity"] of graphic pGraphic to sView["glowOpacity"]
      set the outerGlow["filter"] of graphic pGraphic to "gaussian"
      set the outerGlow["size"] of graphic pGraphic to sView["glowSize"]
      set the outerGlow["spread"] of graphic pGraphic to sView["glowSpread"]
   else if the keys of fxArray is not empty then
      -- Remove the effect; if this engine version refuses, make it invisible instead.
      try
         set the outerGlow of graphic pGraphic to empty
      catch tErr
         set the outerGlow["opacity"] of graphic pGraphic to 0
      end try
   end if
   put true into sStyled[pGraphic]
end View.StyleGraphic

## Any colour reference -> "r,g,b" (graphic effects want a triplet).
## Handles "r,g,b", "#RRGGBB" and the colour names this engine uses.
function Color.ToRGB pColor
   if pColor is empty then return "255,255,255"
   set itemDel to comma
   if the number of items of pColor is 3 then return pColor
   if char 1 of pColor is "#" and the length of pColor is 7 then
      return baseConvert(char 2 to 3 of pColor,16,10) & comma & \
            baseConvert(char 4 to 5 of pColor,16,10) & comma & \
            baseConvert(char 6 to 7 of pColor,16,10)
   end if
   switch pColor
      case "white"
         return "255,255,255"
      case "black"
         return "0,0,0"
      case "red"
         return "255,0,0"
      case "green"
         return "0,255,0"
      case "blue"
         return "0,0,255"
      case "yellow"
         return "255,255,0"
      case "orange"
         return "255,165,0"
      case "cyan"
         return "0,255,255"
      case "magenta"
         return "255,0,255"
      case "purple"
         return "160,32,240"
      case "gray"
      case "grey"
         return "190,190,190"
   end switch
   return "255,255,255"
end Color.ToRGB

## DEBUG: every graphic-effect value of a graphic, one "effect[key]=value" per line.
## (From the 2D side-scroller.)  put IndexEffectsValues("Batch_orange")
function IndexEffectsValues aName
   put "outerGlow,innerShadow,colorOverlay,innerGlow,dropShadow" into theE
   put "graphic" && quote & aName & quote into tObject
   --//Puts
   repeat for each item E in theE
      do "put the" && E && "of" &&  tObject &&"into tProp"
      put the keys of tProp into tKeys
      if tKeys is not empty then
         repeat for each line K in tKeys
            put "put the" && E &"[" & quote & K & quote &"] of" && tObject && "into AVal" && cr after allKeys
         end repeat
      end if
   end repeat
   --//Sets
   repeat for each line A in allKeys
      do A
      put A into B
      replace "put" with "Set" in B
      replace "into AVal" with "to" && AVal in B
      put B & cr after Cs
   end repeat
   --//short hand
   repeat for each line D in Cs
      put word 3 of D & "=" & Word -1 of D  & cr After EF
   end repeat
   return EF
end IndexEffectsValues


## ---------------------------------------------------------------- VECTOR FONT
## Each glyph sits on a 4 x 6 grid (y down). Points are "xy" digit pairs, a stroke is
## points joined in order, strokes are separated by "|". Advance is 6 grid units.

on VectorText.Init
   put empty into sFont
   put "00 40 46 06 00|06 40" into sFont["0"]
   put "10 20 26|16 36" into sFont["1"]
   put "00 40 43 03 06 46" into sFont["2"]
   put "00 40 46 06|03 43" into sFont["3"]
   put "00 03 43|40 46" into sFont["4"]
   put "40 00 03 33 44 45 36 06" into sFont["5"]
   put "40 00 06 46 43 03" into sFont["6"]
   put "00 40 46" into sFont["7"]
   put "00 40 46 06 00|03 43" into sFont["8"]
   put "43 03 00 40 46 06" into sFont["9"]
   put "06 02 20 42 46|03 43" into sFont["A"]
   put "00 30 41 42 33 03|33 44 45 36 06 00" into sFont["B"]
   put "40 00 06 46" into sFont["C"]
   put "00 30 41 45 36 06 00" into sFont["D"]
   put "40 00 06 46|03 33" into sFont["E"]
   put "40 00 06|03 33" into sFont["F"]
   put "40 00 06 46 43 23" into sFont["G"]
   put "00 06|40 46|03 43" into sFont["H"]
   put "00 40|20 26|06 46" into sFont["I"]
   put "40 45 36 16 05" into sFont["J"]
   put "00 06|40 03 46" into sFont["K"]
   put "00 06 46" into sFont["L"]
   put "06 00 23 40 46" into sFont["M"]
   put "06 00 46 40" into sFont["N"]
   put "00 40 46 06 00" into sFont["O"]
   put "06 00 40 43 03" into sFont["P"]
   put "00 40 46 06 00|24 46" into sFont["Q"]
   put "06 00 40 43 03 46" into sFont["R"]
   put "40 00 03 43 46 06" into sFont["S"]
   put "00 40|20 26" into sFont["T"]
   put "00 06 46 40" into sFont["U"]
   put "00 26 40" into sFont["V"]
   put "00 06 23 46 40" into sFont["W"]
   put "00 46|40 06" into sFont["X"]
   put "00 23 40|23 26" into sFont["Y"]
   put "00 40 06 46" into sFont["Z"]
   put "21 22|24 25" into sFont[":"]
   put "03 43" into sFont["-"]
   put "03 43|21 25" into sFont["+"]
   put "25 26" into sFont["."]
   put "20 24|25 26" into sFont["!"]
   put "06 40" into sFont["/"]
   put "06 20 46 06" into sFont["^"] -- triangle, for lives
end VectorText.Init

## Graphic points for a line of text. pX,pY = top-left, pSize = letter height in pixels.
function VectorText.Points pText,pX,pY,pSize
   put pSize / 6 into k
   put pX into tCX
   put empty into tPts
   repeat for each char tCh in toUpper(pText)
      put sFont[tCh] into tGlyph
      if tGlyph is not empty then
         replace "|" with cr in tGlyph
         repeat for each line tStroke in tGlyph
            put cr after tPts
            repeat for each word w in tStroke
               put round(tCX + (char 1 of w) * k) & comma & round(pY + (char 2 of w) * k) & cr after tPts
            end repeat
         end repeat
      end if
      add 6 * k to tCX
   end repeat
   return tPts
end VectorText.Points


## ---------------------------------------------------------------- HUD
## Screen-space vector text, drawn only while the game loop runs.
##   HUD.Set "score","SCORE 000100",12,12,14     (id, text, x, y, size)
## Points are built once on Set, so drawing costs almost nothing.

on HUD.Set pId,pText,pX,pY,pSize
   put pText into sHUD[pId]["text"]
   put pX into sHUD[pId]["x"]
   put pY into sHUD[pId]["y"]
   put pSize into sHUD[pId]["size"]
   put VectorText.Points(pText,pX,pY,pSize) into sHUD[pId]["points"]
end HUD.Set

on HUD.Remove pId
   delete variable sHUD[pId]
end HUD.Remove

## Rebuild every HUD item (after a font or setting change).
on HUD.Refresh
   repeat for each key tId in sHUD
      HUD.Set tId,sHUD[tId]["text"],sHUD[tId]["x"],sHUD[tId]["y"],sHUD[tId]["size"]
   end repeat
end HUD.Refresh

on HUD.Render @pBuf
   if not sLoopActive or sView["hud"] is not true then exit HUD.Render
   if sHUD is not an array then exit HUD.Render
   put Scene.ColorGraphic(sView["hudColor"]) into tGraphic
   repeat for each key tId in sHUD
      put sHUD[tId]["points"] after pBuf[tGraphic]
   end repeat
end HUD.Render




######################################################################################
## GAME CARDS  (11 08 2026)
## The stack script is the ENGINE. Each game lives in the script of its own card,
## "Play." & the game's name ("Play.Canyon", "Play.Demo" ...). Cards copy easily
## to other stacks for focused work, sharing or a release build.
##
## The engine sends these to the current card (dispatch: a card that doesn't handle
## one just doesn't get it):
##   Game.OnStart          Game.Play started this game: build the scene
##   Game.OnUpdate         every simulation step (about 30 a second)
##   Game.OnClick x,y,btn  mouse click while playing (btn 1 left, 3 right)
##   Game.OnKill key,x,y,z Weapon.FireAt destroyed something (and where it was hit)
##   Game.OnPause          pause menu opened (Escape)
##   Game.OnResume         RESUME / Apply
##   Game.OnStop           leaving the game
##   Collision.Hit a,b     two objects touched (unhandled: the stack's default rule)
##
## Choosing a game: Game.Select "Canyon" (kept in gCurrentGame and the stack's
## CurrentGame property). Game.Play goes to card "Play." & that name.
## setup.games makes the Play.* cards by cloning your "Play" card (so they get the
## Options and Pause groups) and places the shared groups on them.
######################################################################################

function Game.Current
   global gCurrentGame
   if gCurrentGame is empty then
      set the customPropertySet of stack (the mainStack of this stack) to empty
      put the CurrentGame of stack (the mainStack of this stack) into gCurrentGame
   end if
   -- No default game: nothing selected means nothing plays.
   return gCurrentGame
end Game.Current

on Game.Select pName
   global gCurrentGame
   put pName into gCurrentGame 
put "@Game.Select gCurrentGame"  && gCurrentGame into gDebug
   set the customPropertySet of stack (the mainStack of this stack) to empty
   set the CurrentGame of stack (the mainStack of this stack) to pName
   Menu.Threedots.Build
end Game.Select

## "Play.<game>" if it exists, else "Play", else the older "Game" card.
## Go to "Play.<current game>". No fallback to any other card: if there is no game
## (or no such card) go to the Developer card. Returns true when the game card is open.
function Game.GoToPlayCard
   put Game.Current() into tGame
   if tGame is not empty and there is a card ("Play." & tGame) then
      go to card ("Play." & tGame)
      return true
   end if
   if there is a card "Developer" then go to card "Developer"
   if tGame is empty then
      UI.Message "No game selected"
   else
      UI.Message "No card Play." & tGame
   end if
   return false
end Game.GoToPlayCard

## Make the Play.* cards (run once from the Message Box). Cloning "Play" keeps its
## Options/Pause groups; then paste the card scripts into each new card.
on setup.games pGames
   if pGames is empty then put "Canyon,Demo,Hunter" into pGames
   lock screen
   repeat for each item tGame in pGames
      put "Play." & tGame into tCard
      if there is not a card tCard then
         if there is a card "Play" then
            clone card "Play"
            set the name of it to tCard
         else
            create card tCard
         end if
      end if
      repeat for each item tGroup in "Viewport,AudioPlayers"
         if there is a group tGroup of card "Developer" and there is not a group tGroup of card tCard then
            place group tGroup of card "Developer" onto card tCard
         end if
      end repeat
   end repeat
   if there is a card "Developer" then go to card "Developer"
   unlock screen
   answer "Game cards ready:" && pGames & "." & cr & "Paste each card's script, then Game.Select and Game.Play."
end setup.games

######################################################################################
## VIEWPORT SELF-REPAIR
## All 3D graphics live in the background group "Viewport". If it gets deleted
## (it is shared, so deleting it on one card removes it everywhere), this rebuilds an
## empty one on the Developer card, places it on every game card, and forgets the
## old graphics so the engine re-creates them on the next frame. APP.init runs it.
######################################################################################

on Viewport.Ensure
   if there is not a card "Developer" then exit Viewport.Ensure
   lock screen
   if there is not a group "Viewport" of card "Developer" then
      put the short name of this card into tBackTo
      go to card "Developer"
      reset the templateGroup
      create group "Viewport"
      set the backgroundBehavior of group "Viewport" to true
      set the lockLoc of group "Viewport" to true
      set the rect of group "Viewport" to the rect of this card
      set the margins of group "Viewport" to 0
      set the showBorder of group "Viewport" to false
      set the layer of group "Viewport" to 1
      -- Forget every graphic the engine made: they went with the old group.
      put empty into sBandMade
      put empty into sBandBase
      put empty into sStyled
      put empty into sLastBatchGraphics
      FX.ClearDerez
      if tBackTo is not "Developer" and there is a card tBackTo then go to card tBackTo
   end if
   repeat with i = 1 to the number of cards of this stack
      put the short name of card i of this stack into tCard
      if tCard begins with "Play" or tCard begins with "Edit_" then
         if there is not a group "Viewport" of card tCard then place group "Viewport" of card "Developer" onto card tCard
      end if
   end repeat
   unlock screen
end Viewport.Ensure


######################################################################################
## HUD LAYOUT  (11 09 2026)
## Design each game's HUD controls (buttons, fields, graphics, images ...) on the
## card "Edit_HUD" with the normal LiveCode tools. Right-click the card (browse
## tool) for the menu; every entry except New and Done lists the Play.* games:
##   Owners  > game   tick the games the current layout is saved to (several allowed)
##   Edit    > game   work on that game: its controls shown, other saved HUD hidden
##   Show    > game   bring that game's controls in too, hide nothing
##   Hide    > game   hide that game's controls
##   New...           new game: name, current layout or the default HUD, new Play card
##   Test    > game   save, then play it; Escape comes back here
##   Done             save to the owners and go to the Developer card
## Leaving the card (closeCard) also saves.
##
## WHAT IS SAVED: every VISIBLE top-level control on Edit_HUD whose custom property
## "HUD" is not false (empty counts as yes; saving sets it to true). Groups are skipped
## for now. Each control is stored as its type, its script, field htmlText / image
## data, its custom properties, and ONLY the properties that differ from LiveCode's
## template object of that type (so the data stays small).
## Stored in the stack's custom property set "Game_Huds", one array per game.
##
## IN PLAY: Game.Play deletes the game card's HUD controls (custom property HUD = true)
## and re-creates them from that game's saved array, so the layout always matches.
## One-time setup: setup.hud
######################################################################################

## The game names, from the Play.* cards.
function Game.List
   put empty into tList
   repeat with i = 1 to the number of cards of this stack
      put the short name of card i of this stack into tCard
      if tCard begins with "Play." then put char 6 to -1 of tCard & cr after tList
   end repeat
   delete the last char of tList
   return tList
end Game.List

## Make the Edit_HUD card (run once from the Message Box).
on setup.hud
   Viewport.Ensure
   lock screen
   if there is not a card "Edit_HUD" then
      if there is a card "Developer" then go to card "Developer"
      create card "Edit_HUD"
   end if
   go to card "Edit_HUD"
   if there is a group "Viewport" of card "Developer" and there is not a group "Viewport" of card "Edit_HUD" then
      place group "Viewport" of card "Developer" onto card "Edit_HUD"
   end if
   
   -- The hidden popup menu and the card script (right-click, save on close).
   if there is not a button "HUD_Menu" then
      reset the templateButton
      create button "HUD_Menu"
      set the style of button "HUD_Menu" to "menu"
      set the menuMode of button "HUD_Menu" to "popup"
      set the visible of button "HUD_Menu" to false
   end if
   set the HUD of button "HUD_Menu" to false
   set the script of button "HUD_Menu" to "on menuPick pItem" & cr & \
         "   HUD.Layout.MenuPick pItem" & cr & "end menuPick"
   set the script of card "Edit_HUD" to "on mouseDown pButton" & cr & \
         "   if pButton is 3 then HUD.Layout.Menu" & cr & "   pass mouseDown" & cr & \
         "end mouseDown" & cr & cr & "on closeCard" & cr & "   HUD.Layout.Save" & cr & \
         "   pass closeCard" & cr & "end closeCard"
   set the backgroundColor of card "Edit_HUD" to "black"
   
   -- First time: the default HUD (copies of the Developer card's Status and Next buttons).
   if HUD.LayoutControls() is empty then
      put HUD.MakeDefault() into tHud
      repeat for each key tName in tHud
         HUD.CreateControl tName,tHud[tName]
      end repeat
   end if
   if HUD.Layout.Owners() is empty then HUD.Layout.SetOwners Game.List()
   HUD.Layout.Save
   unlock screen
   answer "Edit_HUD is ready." & cr & "Right-click the card (browse tool) for the HUD menu."
end setup.hud

## The default HUD: copies of the Developer card's "Status" and "Next ..." buttons.
## The default HUD for new games. Status and Next Preview now live in the Viewport
## group (see Viewport.Adopt), so the default is empty unless you saved one as
## "DefaultHUD" (HUD.Store "DefaultHUD", ...).
function HUD.MakeDefault
   put HUD.Load("DefaultHUD") into tHud
   if tHud is an array then return tHud
   return empty
end HUD.MakeDefault


## ---------------------------------------------------------------- MENU

on HUD.Layout.Menu
   if there is not a button "HUD_Menu" then exit HUD.Layout.Menu
   put Game.List() into tGames
   put HUD.Layout.Owners() into tOwners
   put empty into tMenu
   put "Owners" & cr after tMenu
   repeat for each line tGame in tGames
      if tGame is among the items of tOwners then
         put tab & "!c" & tGame & cr after tMenu
      else
         put tab & "!n" & tGame & cr after tMenu
      end if
   end repeat
   repeat for each item tCmd in "Edit,Show,Hide"
      put tCmd & cr after tMenu
      repeat for each line tGame in tGames
         put tab & tGame & cr after tMenu
      end repeat
   end repeat
   put "-" & cr & "New..." & cr & "Test" & cr after tMenu
   repeat for each line tGame in tGames
      put tab & tGame & cr after tMenu
   end repeat
   put "-" & cr & "Done" after tMenu
   set the text of button "HUD_Menu" to tMenu
   popup button "HUD_Menu"
end HUD.Layout.Menu

on HUD.Layout.MenuPick pItem
   set itemDel to "|"
   put item 1 of pItem into tCmd
   put item 2 of pItem into tGame
   set itemDel to comma
   switch tCmd
      case "Owners"
         HUD.Layout.ToggleOwner tGame
         break
      case "Edit"
         HUD.Layout.Edit tGame
         break
      case "Show"
         HUD.Layout.ShowGame tGame
         break
      case "Hide"
         HUD.Layout.HideGame tGame
         break
      case "New..."
         HUD.Layout.NewGame
         break
      case "Test"
         HUD.Layout.Test tGame
         break
      case "Done"
         HUD.Layout.Save
         if there is a card "Developer" then go to card "Developer"
         break
   end switch
end HUD.Layout.MenuPick


## ---------------------------------------------------------------- OWNERS

function HUD.Layout.Owners
   if there is not a card "Edit_HUD" then return empty
   set the customPropertySet of card "Edit_HUD" to empty
   return the HUDOwners of card "Edit_HUD"
end HUD.Layout.Owners

on HUD.Layout.SetOwners pList
   replace cr with comma in pList
   set the customPropertySet of card "Edit_HUD" to empty
   set the HUDOwners of card "Edit_HUD" to pList
end HUD.Layout.SetOwners

on HUD.Layout.ToggleOwner pGame
   put HUD.Layout.Owners() into tOwners
   if pGame is among the items of tOwners then
      delete item itemOffset(pGame,tOwners) of tOwners
   else if tOwners is empty then
      put pGame into tOwners
   else
      put comma & pGame after tOwners
   end if
   HUD.Layout.SetOwners tOwners
end HUD.Layout.ToggleOwner


## ---------------------------------------------------------------- EDIT / SHOW / HIDE

## Work on one game: it becomes the only owner, its controls are brought in and shown,
## and saved HUD controls (HUD = true) that it doesn't use are hidden.
## Controls whose HUD is still empty stay visible: they are new, for this game.
on HUD.Layout.Edit pGame
   HUD.Layout.Save
   HUD.Layout.SetOwners pGame
   put HUD.Load(pGame) into tHud
   HUD.Layout.BringIn tHud
   repeat for each line tRef in HUD.LayoutControls()
      set the customPropertySet of tRef to empty
      if the HUD of tRef is true then
         set the visible of tRef to (tHud[the short name of tRef] is an array)
      end if
   end repeat
end HUD.Layout.Edit

on HUD.Layout.ShowGame pGame
   HUD.Layout.BringIn HUD.Load(pGame)
end HUD.Layout.ShowGame

on HUD.Layout.HideGame pGame
   put HUD.Load(pGame) into tHud
   if tHud is not an array then exit HUD.Layout.HideGame
   repeat for each key tName in tHud
      if there is a control tName of card "Edit_HUD" then hide control tName of card "Edit_HUD"
   end repeat
end HUD.Layout.HideGame

## Create (or just show) every control of a saved HUD on the layout card.
on HUD.Layout.BringIn pHud
   if pHud is not an array then exit HUD.Layout.BringIn
   if the short name of this card is not "Edit_HUD" then go to card "Edit_HUD"
   repeat for each key tName in pHud
      if there is a control tName of card "Edit_HUD" then
         show control tName of card "Edit_HUD"
      else
         HUD.CreateControl tName,pHud[tName]
      end if
   end repeat
end HUD.Layout.BringIn


## ---------------------------------------------------------------- SAVE / NEW / TEST

## Save the visible HUD controls to every owner game.
on HUD.Layout.Save
   if there is not a card "Edit_HUD" then exit HUD.Layout.Save
   put HUD.Layout.Owners() into tOwners
   if tOwners is empty then exit HUD.Layout.Save
   put empty into tHud
   repeat for each line tRef in HUD.LayoutControls()
      if not the visible of tRef then next repeat
      set the customPropertySet of tRef to empty
      if the HUD of tRef is false then next repeat
      set the HUD of tRef to true
      put HUD.CaptureControl(tRef) into tHud[the short name of tRef]
   end repeat
   repeat for each item tGame in tOwners
      HUD.Store tGame,tHud
   end repeat
end HUD.Layout.Save

on HUD.Layout.NewGame
   ask "Name of the new game (letters and digits):"
   if it is empty then exit HUD.Layout.NewGame
   put it into tName
   -- Card and property names: letters and digits only.
   put empty into tClean
   repeat for each char tCh in tName
      if tCh is in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" then put tCh after tClean
   end repeat
   if tClean is empty then exit HUD.Layout.NewGame
   if there is a card ("Play." & tClean) then
      answer "There is already a card Play." & tClean & "."
      exit HUD.Layout.NewGame
   end if
   
   answer "Use the current layout for" && tClean & "?" with "No" or "Yes"
   put it into tUseCurrent
   if tUseCurrent is "Yes" then
      HUD.Layout.SetOwners tClean
      HUD.Layout.Save
   else
      HUD.Store tClean,HUD.MakeDefault()
   end if
   
   -- The game card: just the Viewport (and sound), plus a starter script.
   lock screen
   create card ("Play." & tClean)
   repeat for each item tGroup in "Viewport,AudioPlayers"
      if there is a group tGroup of card "Developer" and there is not a group tGroup of card ("Play." & tClean) then
         place group tGroup of card "Developer" onto card ("Play." & tClean)
      end if
   end repeat
   set the script of card ("Play." & tClean) to HUD.StarterCardScript(tClean)
   go to card "Edit_HUD"
   unlock screen
   if tUseCurrent is not "Yes" then HUD.Layout.Edit tClean
   Menu.Threedots.Build
end HUD.Layout.NewGame

## Save, then play the game; Escape comes back here (see Game.Exit).
on HUD.Layout.Test pGame
   if pGame is empty then exit HUD.Layout.Test
   HUD.Layout.Save
   put true into sHudTest
   Game.Select pGame
   Game.Play
end HUD.Layout.Test

## A minimal game card script for a new game.
function HUD.StarterCardScript pName
   put "## CARD SCRIPT: Play." & pName & cr into s
   put "global gObjectTransforms" & cr & cr after s
   put "on Game.OnStart" & cr & "   Engine.ResetCamera" & cr & "   Scene.ClearAll" & cr after s
   put "   Particles.Clear" & cr & "   HUD.Clear" & cr & "   Collision.ClearRules" & cr after s
   put "   Mesh.Define " & quote & "Thing" & quote & ", MeshBox(60,60,60)" & cr after s
   put "   get Entity.Spawn(" & quote & "Thing" & quote & ",0,0,400," & quote & "#00FF66" & quote & ")" & cr after s
   put "   SetObjectRotationSpeed it,0.01,0.02,0" & cr after s
   put "end Game.OnStart" & cr & cr after s
   put "on Game.OnUpdate" & cr & "end Game.OnUpdate" & cr & cr after s
   put "on Game.OnStop" & cr & "end Game.OnStop" & cr & cr after s
   put "on opencard" & cr after s
   put "   Menu.CloseAll" & cr after s
   put "end opencard" & cr after s
   return s
end HUD.StarterCardScript


## ---------------------------------------------------------------- PLAY CARDS

## Called by Game.Play on the game card: replace its HUD controls with the saved ones.
on HUD.ApplyToCard pGame
   -- Only ever on a game card: never touch Developer, Title or Edit_* controls.
   if char 1 to 5 of the short name of this card is not "Play." then exit HUD.ApplyToCard
   put HUD.Load(pGame) into tHud
   if tHud is not an array then exit HUD.ApplyToCard
   lock screen
   repeat with i = the number of controls of this card down to 1
      put the long id of control i of this card into tRef
      if word 1 of the owner of tRef is not "card" then next repeat
      set the customPropertySet of tRef to empty
      if the HUD of tRef is true then
         put the short id of tRef into tId
         delete control id tId of this card
      end if
   end repeat
   repeat for each key tName in tHud
      HUD.CreateControl tName,tHud[tName]
   end repeat
   unlock screen
end HUD.ApplyToCard


## ---------------------------------------------------------------- STORAGE

## Long ids of the top-level, non-group controls on Edit_HUD (not the menu button).
function HUD.LayoutControls
   if there is not a card "Edit_HUD" then return empty
   put empty into tList
   repeat with i = 1 to the number of controls of card "Edit_HUD"
      put the long id of control i of card "Edit_HUD" into tRef
      if word 1 of the owner of tRef is not "card" then next repeat
      if word 1 of tRef is "group" then next repeat
      if the short name of tRef is "HUD_Menu" then next repeat
      put tRef & cr after tList
   end repeat
   delete the last char of tList
   return tList
end HUD.LayoutControls

## One control -> array: type, script, properties that differ from the template,
## field htmlText / image data, custom properties.
function HUD.CaptureControl pRef
   put word 1 of pRef into tType
   put the properties of pRef into tP
   put HUD.TemplateProps(tType) into tT
   put empty into tD
   repeat for each key k in tP
      if k is among the items of "id,altId,number,layer" then next repeat
      if tP[k] is not tT[k] then put tP[k] into tD[k]
   end repeat
   put the short name of pRef into tD["name"]
   put the rect of pRef into tD["rect"]
   put tType into tA["type"]
   put tD into tA["props"]
   put the script of pRef into tA["script"]
   if tType is "field" then put the htmlText of pRef into tA["html"]
   if tType is "image" then put the text of pRef into tA["imageData"]
   set the customPropertySet of pRef to empty
   put the customProperties of pRef into tA["custom"]
   return tA
end HUD.CaptureControl

## LiveCode's default properties for a control type (fetched once).
function HUD.TemplateProps pType
   if sHudTemplate[pType] is not an array then
      try
         do "reset the template" & pType
         do "put the properties of the template" & pType && "into tT"
         put tT into sHudTemplate[pType]
      catch tErr
         put empty into sHudTemplate[pType]
      end try
   end if
   return sHudTemplate[pType]
end HUD.TemplateProps

## Re-create a stored control on the CURRENT card.
on HUD.CreateControl pName,pA
   put pA["type"] into tType
   if tType is empty then exit HUD.CreateControl
   if there is a control pName of this card then delete control pName of this card
   do "reset the template" & tType
   do "create" && tType && quote & pName & quote
   put it into tRef
   if tRef is empty then exit HUD.CreateControl
   -- Properties one by one, so a read-only one can't stop the rest.
   put pA["props"] into tP
   repeat for each key k in tP
      if k is "rect" or k is "name" then next repeat
      try
         put tP[k] into tVal
         do "set the" && k && "of tRef to tVal"
      catch tErr
      end try
   end repeat
   if tP["rect"] is not empty then set the rect of tRef to tP["rect"]
   try
      set the script of tRef to pA["script"]
   catch tErr
   end try
   if tType is "field" and pA["html"] is not empty then set the htmlText of tRef to pA["html"]
   if tType is "image" and pA["imageData"] is not empty then set the text of tRef to pA["imageData"]
   set the customPropertySet of tRef to empty
   if pA["custom"] is an array then set the customProperties of tRef to pA["custom"]
   set the HUD of tRef to true
   set the layer of tRef to top
end HUD.CreateControl

on HUD.Store pGame,pArray
   put the customPropertySet of stack (the mainStack of this stack) into tOldSet
   set the customPropertySet of stack (the mainStack of this stack) to "Game_Huds"
   put pArray into tV
   do "set the" && pGame && "of stack (the mainStack of this stack) to tV"
   set the customPropertySet of stack (the mainStack of this stack) to tOldSet
end HUD.Store

function HUD.Load pGame
   if pGame is empty then return empty
   put the customPropertySet of stack (the mainStack of this stack) into tOldSet
   set the customPropertySet of stack (the mainStack of this stack) to "Game_Huds"
   put empty into tV
   if pGame is among the lines of the customKeys of stack (the mainStack of this stack) then
      do "put the" && pGame && "of stack (the mainStack of this stack) into tV"
   end if
   set the customPropertySet of stack (the mainStack of this stack) to tOldSet
   return tV
end HUD.Load

## Engine values a card script may need (they are local to this stack script).
function Engine.Info pKey
   switch pKey
      case "projection"
         return sProjK & comma & sProjOffX & comma & sProjOffY
      case "stepMS"
         return kStepMS
      case "simTick"
         return sSimTick
      case "fps"
         return sFPS
      case "edges"
         return sEdgesDrawn
      case "playing"
         return sLoopActive
      case "paused"
         return bPaused
   end switch
   return empty
end Engine.Info

## A plain camera: no scene rotation or spin, no pivot, at the origin looking down +Z.
on Engine.ResetCamera
   global gCameraYaw
   global gCameraPitch
   put 0 into ANGLEX
   put 0 into ANGLEY
   put 0 into ANGLEZ
   put 0 into fXrot
   put 0 into fYrot
   put 0 into fZrot
   put 0 into PIVX
   put 0 into PIVY
   put 0 into PIVZ
   put 0 into CAMX
   put 0 into CAMY
   put 0 into CAMZ
   put 0 into MOVEX
   put 0 into MOVEY
   put 1 into theScale
   put 0 into gCameraYaw
   put 0 into gCameraPitch
   put the width of this stack / 2 into CenterX
   put the height of this stack / 2 into CenterY
   Render.BeginFrame
end Engine.ResetCamera

## Scene translation (CAMX/Y/Z). Empty = leave as is.
on Engine.SetCam pX,pY,pZ
   if pX is a number then put pX into CAMX
   if pY is a number then put pY into CAMY
   if pZ is a number then put pZ into CAMZ
end Engine.SetCam

## The editor's starting scene: default camera, the original test objects.
on App.ResetScene
   init.globals
   init.locals
   Engine.Init
   init.object.Transforms
   Scene.ClearAll
   init.scene.objects
   Particles.Clear
   Collision.ClearRules
   HUD.Clear
end App.ResetScene

## Remove every object from the scene (graphics are cleared on the next frame).
on Scene.ClearAll
   global gSceneObjects
   global gObjectTransforms
   repeat for each line tEntry in gSceneObjects
      delete variable gObjectTransforms[word 2 of tEntry]
   end repeat
   put empty into gSceneObjects
   put empty into gSelectedObject
end Scene.ClearAll

on HUD.Clear
   put empty into sHUD
end HUD.Clear


######################################################################################
## DEREZ  (fast destruction, TRON style)
## The object's current screen lines are copied once into a pooled graphic. Then,
## each frame, only properties change: the rect grows (LiveCode rescales the points),
## the dashes go from long dashes to short dashes with growing gaps, and it fades.
## Far cheaper than turning every edge into a particle (FX.Explode, "debris").
## FX.Destroy picks the style from the view setting "explode": derez (default) or debris.
######################################################################################

on FX.Destroy pKey
   if sView["explode"] is "debris" then
      FX.Explode pKey
   else
      FX.Derez pKey
   end if
end FX.Destroy

on FX.Derez pKey
   global gObjectTransforms
   global gSceneObjects
   if pKey is empty or gObjectTransforms[pKey] is not an array then exit FX.Derez
   put gObjectTransforms[pKey]["x"] into wx
   put gObjectTransforms[pKey]["y"] into wy
   put gObjectTransforms[pKey]["z"] into wz
   
   put empty into tMeshName
   repeat for each line tEntry in gSceneObjects
      if word 2 of tEntry is pKey then
         put word 1 of tEntry into tMeshName
         put word 3 of tEntry into tGraphic
         if tGraphic is empty then put pKey into tGraphic
         exit repeat
      end if
   end repeat
   
   if tMeshName is not empty then
      -- The object exactly as it was drawn last frame.
      put RenderMeshPoints(tMeshName,pKey) into tPts
      if tPts is not empty then
         add 1 to sDerezNext
         if sDerezNext > kDerezSlots then put 1 into sDerezNext
         put sDerezNext into n
         put "Derez" & n into tG
         Scene.NewLineGraphic tG
         if there is not a graphic tG then
            put 0 into sDerezAge[n]
            put empty into tPts
         end if
      end if
      if tPts is not empty then
         put sOrigColor[tGraphic] into tColor
         if tColor is empty and there is a graphic tGraphic then put the effective foregroundColor of graphic tGraphic into tColor
         if sView["mono"] is not empty then put sView["mono"] into tColor
         if tColor is not empty then set the foregroundColor of graphic tG to tColor
         set the lineSize of graphic tG to max(1, sView["lineSize"])
         set the blendLevel of graphic tG to 0
         set the dashes of graphic tG to "8,2"
         set the points of graphic tG to tPts
         set the visible of graphic tG to true
         put the rect of graphic tG into sDerezRect[n]
         put 1 into sDerezAge[n]
      end if
   end if
   
   FX.Sparks wx,wy,wz,6,"white"
   Entity.Kill pKey
end FX.Derez

## Each frame (from game.render): grow, break up, fade, then clear.
on FX.DerezRender
   repeat with n = 1 to kDerezSlots
      if sDerezAge[n] is not a number or sDerezAge[n] < 1 then next repeat
      add 1 to sDerezAge[n]
      put sDerezAge[n] into tAge
      put "Derez" & n into tG
      if there is not a graphic tG then
         put 0 into sDerezAge[n]
         next repeat
      end if
      if tAge > kDerezFrames then
         set the points of graphic tG to empty
         set the dashes of graphic tG to empty
         put 0 into sDerezAge[n]
         next repeat
      end if
      -- Grow around the centre.
      put sDerezRect[n] into r
      put ((item 1 of r) + (item 3 of r)) / 2 into cx
      put ((item 2 of r) + (item 4 of r)) / 2 into cy
      put 1 + tAge * 0.07 into k
      put max(1, ((item 3 of r) - (item 1 of r)) / 2 * k) into hw
      put max(1, ((item 4 of r) - (item 2 of r)) / 2 * k) into hh
      set the rect of graphic tG to round(cx - hw),round(cy - hh),round(cx + hw),round(cy + hh)
      -- Dashes shrink while the gaps grow: it spreads out and vanishes.
      put max(1, 8 - tAge div 2) into d
      put 2 + tAge * 2 into g
      set the dashes of graphic tG to d & comma & g & comma & max(1, d - 2) & comma & (g * 2)
      set the blendLevel of graphic tG to min(95, tAge * 7)
   end repeat
end FX.DerezRender

on FX.ClearDerez
   repeat with n = 1 to kDerezSlots
      put 0 into sDerezAge[n]
      if there is a graphic ("Derez" & n) then set the points of graphic ("Derez" & n) to empty
   end repeat
end FX.ClearDerez


######################################################################################
## AUDIO  (from Defensive: InitMusic / InitSoundEffects / PlaySoundEffects)
## Sound files are loaded ONCE into player objects (LiveCode is slow reading files
## on demand). Players live in one background group, "AudioPlayers", placed on the
## Title, Developer and Play* cards.
##   <stack folder>/Data/Music/*           -> players Song1, Song2 ...
##   <stack folder>/Data/Sounds/<Type>/*   -> players <Type>1, <Type>2 ...
##     (PlayerLaser gets 10 players, Explode 3, everything else one per file)
## Sound.Play "Explode" plays the next player of that type.
## Volumes: currentMusicVolume / currentFXVolume (Options menu).
######################################################################################

## The folder the stack file is in (so files are found without dialogs).
function StackDirectory
   global gStackDirectory
   put word 2 the long name of stack (the mainStack of this stack) into myStack
   replace quote with empty in myStack
   set itemDel to "/"
   put item 1 to -2 of myStack into gStackDirectory
   set the folder to gStackDirectory
   return gStackDirectory
end StackDirectory

function SoundDirectory
   global gSoundDirectory
   put StackDirectory() & "/Data/Sounds" into gSoundDirectory
   return gSoundDirectory
end SoundDirectory

## Only the playable media files of a folder.
function FilteredMusicFiles tFolder
   set the folder to tFolder
   put files() into tFiles
   put "mp3,mp4,avi,aifc,cdda,aif,aiff,caf,m4a,wav,wave,bwf,amr,ac3,au,snd" into tFormats
   put empty into tFinal
   repeat for each item T in tFormats
      put tFiles into tFiltered
      filter tFiltered with "*." & T
      if tFiltered is not empty then put cr & tFiltered after tFinal
   end repeat
   filter tFinal without empty
   sort tFinal
   return tFinal
end FilteredMusicFiles

## Load everything once (Game.Play calls this the first time).
on Audio.Init
   if sAudioReady is true then exit Audio.Init
   LoadingScreen "LOADING SOUNDS"
   lock screen
   Audio.EnsureGroup
   put the folder into tOldFolder
   put empty into sMusicPlayers
   Sound.Reset
   
   -- Music.
   put StackDirectory() & "/Data/Music" into tMusicFolder
   if there is a folder tMusicFolder then
      put FilteredMusicFiles(tMusicFolder) into tSongs
      put 0 into n
      repeat for each line tSong in tSongs
         add 1 to n
         Audio.MakePlayer "Song" & n, tMusicFolder & "/" & tSong, currentMusicVolume
         put "Song" & n & cr after sMusicPlayers
      end repeat
   end if
   
   -- Sound effects: one sub folder per type.
   put SoundDirectory() into tSoundsFolder
   if there is a folder tSoundsFolder then
      set the folder to tSoundsFolder
      put folders() into tTypes
      filter tTypes without ".."
      filter tTypes without "."
      repeat for each line tType in tTypes
         put tSoundsFolder & "/" & tType into tDir
         put FilteredMusicFiles(tDir) into tFiles
         put the number of lines of tFiles into tCount
         if tCount = 0 then next repeat
         switch tType
            case "PlayerLaser"
               put 10 into tPlayers
               break
            case "Explode"
               put 3 into tPlayers
               break
            default
               put tCount into tPlayers
         end switch
         put empty into tList
         repeat with k = 1 to max(tPlayers, tCount)
            put line ((k - 1) mod tCount) + 1 of tFiles into tFile
            Audio.MakePlayer tType & k, tDir & "/" & tFile, currentFXVolume
            put tType & k & cr after tList
         end repeat
         put tList into sSoundList[tType]
      end repeat
   end if
   
   set the folder to tOldFolder
   put true into sAudioReady
   unlock screen
   LoadingScreen
end Audio.Init

## The shared, off-screen group that holds the players.
## The players' group, "AudioPlayers", lives INSIDE the Viewport group, so it comes
## with every card that shows the Viewport. (A nested group can't be placed.)
on Audio.EnsureGroup
   if there is a group "AudioPlayers" then exit Audio.EnsureGroup
   if there is not a group "Viewport" then exit Audio.EnsureGroup
   reset the templateGroup
   create group "AudioPlayers" in group "Viewport"
end Audio.EnsureGroup

on Audio.MakePlayer pName,pFile,pVolume
   if there is not a player pName then
      reset the templatePlayer
      create player pName in group "AudioPlayers"
   end if
   set the fileName of player pName to pFile
   set the currentTime of player pName to 0
   set the playLoudness of player pName to pVolume
   set the looping of player pName to false
   -- Keep players off the visible card.
   set the loc of player pName to (the width of this stack) div 2, -200
end Audio.MakePlayer

## Plays the next player of a type (round robin). Silent when there are none.
on Sound.Play pType
   if sSoundOff is true then exit Sound.Play
   if sSoundList[pType] is empty then
      -- Not loaded by Audio.Init: look for players with that name on the card.
      put empty into tList
      repeat with i = 1 to the number of players of this card
         put the short name of player i of this card into tName
         if tName begins with pType and char (the length of pType + 1) to -1 of tName is an integer then
            put tName & cr after tList
         end if
      end repeat
      if tList is empty then put "none" into tList
      put tList into sSoundList[pType]
   end if
   if sSoundList[pType] is "none" then exit Sound.Play
   add 1 to sSoundNext[pType]
   if sSoundNext[pType] > the number of lines of sSoundList[pType] then put 1 into sSoundNext[pType]
   put line sSoundNext[pType] of sSoundList[pType] into tPlayer
   if there is a player tPlayer then
      set the currentTime of player tPlayer to 0
      start player tPlayer
   end if
end Sound.Play

on Sound.Reset
   put empty into sSoundList
   put empty into sSoundNext
end Sound.Reset

## Music: a random song, then the next when it ends (checked from game.update).
on Audio.StartMusic
   if sMusicPlayers is empty then exit Audio.StartMusic
   Audio.StopMusic
   put line random(the number of lines of sMusicPlayers) of sMusicPlayers into sCurrentSong
   if there is a player sCurrentSong then
      set the currentTime of player sCurrentSong to 0
      set the playLoudness of player sCurrentSong to currentMusicVolume
      start player sCurrentSong
   end if
end Audio.StartMusic

on Audio.StopMusic
   if sCurrentSong is not empty and there is a player sCurrentSong then stop player sCurrentSong
   put empty into sCurrentSong
end Audio.StopMusic

on Audio.UpdateMusic
   if sCurrentSong is empty or sSimTick mod 90 is not 0 then exit Audio.UpdateMusic
   if there is not a player sCurrentSong then exit Audio.UpdateMusic
   if the paused of player sCurrentSong then Audio.StartMusic
end Audio.UpdateMusic

## Defensive's arrow keys: next / previous / random song.
on Audio.NextSong
   Audio.StartMusic
end Audio.NextSong

on Audio.SetVolumes pMusic,pFX
   if pMusic is a number then put pMusic into currentMusicVolume
   if pFX is a number then put pFX into currentFXVolume
   repeat for each line tP in sMusicPlayers
      if there is a player tP then set the playLoudness of player tP to currentMusicVolume
   end repeat
   repeat for each key tType in sSoundList
      repeat for each line tP in sSoundList[tType]
         if there is a player tP then set the playLoudness of player tP to currentFXVolume
      end repeat
   end repeat
   if there is a player "themeSong" of card "Title" then set the playLoudness of player "themeSong" of card "Title" to currentMusicVolume
end Audio.SetVolumes

## Title music: a file in Data/Music with "theme" in its name, on player "themeSong".
on ThemeSong
   if there is not a card "Title" then exit ThemeSong
   if there is not a player "themeSong" of card "Title" then exit ThemeSong
   put the folder into tOldFolder
   put StackDirectory() & "/Data/Music" into tFolder
   if there is not a folder tFolder then exit ThemeSong
   put FilteredMusicFiles(tFolder) into tFiles
   filter tFiles with "*theme*"
   if tFiles is not empty then
      put line random(the number of lines of tFiles) of tFiles into tSong
      set the filename of player "themeSong" of card "Title" to tFolder & "/" & tSong
      set the currentTime of player "themeSong" of card "Title" to 0
      set the looping of player "themeSong" of card "Title" to true
      set the playLoudness of player "themeSong" of card "Title" to currentMusicVolume
      start player "themeSong" of card "Title"
   end if
   set the folder to tOldFolder
end ThemeSong


######################################################################################
## TITLE CARD, PAUSE MENU, OPTIONS  (Defensive's handlers, for the copied groups)
## Title card: group "Title" (field "Title" throbs), player "themeSong".
## Play cards: groups "PauseMenuGroup" and "OptionsGroup".
## Escape while playing = pause menu; Escape again = back to the Developer card.
######################################################################################

-- Title card's openCard calls this (and ResetDefaults).
on TitleCardOpened
   if the short name of this card is not "Title" then exit TitleCardOpened
   game.loop.stop
   Audio.StopMusic
   choose browse tool
   --Menu.CloseAll
   if there is a group "Title" then show group "Title"
   put false into bPaused
   LoadingScreen
   TitleCardIdle
   ThemeSong
   unlock screen
end TitleCardOpened

on ResetDefaults
   put false into bPaused
end ResetDefaults

## Keeps the title centred and glowing.
on TitleCardIdle
   if the tool is not "browse tool" then exit TitleCardIdle
   if the short name of this card is not "Title" then exit TitleCardIdle
   if there is a group "Title" then set the loc of group "Title" to CenterScreen()
   if there is a group "OptionsGroup" and the visible of group "OptionsGroup" then exit TitleCardIdle
   if there is a group "PauseMenuGroup" and the visible of group "PauseMenuGroup" then exit TitleCardIdle
   TitleGlow
   send "TitleCardIdle" to me in 100 milliseconds
end TitleCardIdle

on TitleGlow
   if there is not a field "Title" then exit TitleGlow
   put the glowInc of field "Title" into gInc
   if gInc is not a number then put 2 into gInc
   put the outerGlow["size"] of field "Title" into ogs
   add gInc to ogs
   if ogs > 35 then put -2 into gInc
   if ogs < 22 then put 2 into gInc
   set the outerGlow["size"] of field "Title" to ogs
   set the glowInc of field "Title" to gInc
   put the outerGlow["color"] of field "Title" into rgb
   if the number of items of rgb is 3 then
      add random(4) * gInc to item 1 of rgb
      add random(4) * gInc to item 2 of rgb
      add random(4) * gInc to item 3 of rgb
      repeat with i = 1 to 3
         put max(0, min(255, item i of rgb)) into item i of rgb
      end repeat
      set the outerGlow["color"] of field "Title" to rgb
   end if
end TitleGlow

## Defensive's PLAY button handler.
on PlayButtonPressed
   if there is a player "themeSong" then stop player "themeSong"
   Game.Play
end PlayButtonPressed

## A simple loading/paused screen: graphic "Loading" if the stack has one.
on LoadingScreen pText
   if there is not a graphic "Loading" then exit LoadingScreen
   if pText is empty then
      hide graphic "Loading"
   else
      set the label of graphic "Loading" to pText
      set the rect of graphic "Loading" to the rect of this card
      set the layer of graphic "Loading" to top
      show graphic "Loading"
   end if
end LoadingScreen

function StackDepth
   return the width of this stack & comma & the height of this stack
end StackDepth

function CenterScreen XY
   put (the width of this stack) div 2 into tX
   put (the height of this stack) div 2 into tY
   if XY is "x" then return tX
   if XY is "y" then return tY
   return tX & comma & tY
end CenterScreen

## Defensive's debug readout into button "Viewer" (if the card has one).
on view a,b,c
   if there is not a button "Viewer" then exit view
   put a into tText
   if b is not empty then put "  ||  " & b after tText
   if c is not empty then put "  ||  " & c after tText
   set the label of button "Viewer" to tText
end view

## Escape while playing.
on Game.Pause
   put true into bPaused
   dispatch "Game.OnPause" to this card
   PauseMenu
end Game.Pause

on PauseMenu
   Menu.Open "Pause"
end PauseMenu

on PauseGame
   Game.Pause
end PauseGame

## RESUME (also after Apply in Options).
on ResumeGame
   Menu.CloseAll
   LoadingScreen
   choose browse tool
   put false into bPaused
   dispatch "Game.OnResume" to this card
   if the short name of this card begins with "Play" and not sLoopActive then game.loop.start
end ResumeGame

on QuitCommand
   quit
end QuitCommand

## OPTIONS: show the group with the current settings (Defensive's OptionsGroupSetUp).
on OptionsGroupSetUp
   Menu.Open "Options"
   if there is not a group "OptionsGroup" then exit OptionsGroupSetUp
   unlock screen
   -- Screen size choices.
   put screenRect() into tFull
   put empty into tSizes
   repeat with i = 1 to 3 step .2
      put floor(item 3 of tFull / i) & " x " & floor(item 4 of tFull / i) & cr after tSizes
   end repeat
   if there is a button "ScreenSizesMenu" then
      set the text of button "ScreenSizesMenu" to tSizes
      set the label of button "ScreenSizesMenu" to "Screen Size"
   end if
   put StackDepth() into tCur
   replace comma with " x " in tCur
   if there is a field "ScreenSizeValueLabel" then put tCur into field "ScreenSizeValueLabel"
   if there is a button "fullScreenToggle" then set the hilite of button "fullScreenToggle" to bFullScreen
   -- Volumes.
   if there is a graphic "VolumeSlider" and there is a graphic "VolumeSliderRectangle" then
      set the loc of graphic "VolumeSliderRectangle" to (the left of graphic "VolumeSlider" + currentMusicVolume), item 2 of the loc of graphic "VolumeSlider"
   end if
   if there is a field "MusicVolumeValue" then put currentMusicVolume into field "MusicVolumeValue"
   if there is a graphic "FXVolumeSlider" and there is a graphic "FXVolumeSliderRectangle" then
      set the loc of graphic "FXVolumeSliderRectangle" to (the left of graphic "FXVolumeSlider" + currentFXVolume), item 2 of the loc of graphic "FXVolumeSlider"
   end if
   if there is a field "FXVolumeValue" then put currentFXVolume into field "FXVolumeValue"
   -- Look: Use Effects = glow, Back Mountains = depth fading, Effects = strong fade.
   if there is a button "AntiAliasToggle" then set the hilite of button "AntiAliasToggle" to bAntiAlias
   if there is a button "UseEffectsToggle" then set the hilite of button "UseEffectsToggle" to (sView["glow"] is true)
   if there is a button "BackMountainsToggle" then set the hilite of button "BackMountainsToggle" to (sViewBands > 1)
   if there is a button "BackMountainsFXToggle" then set the hilite of button "BackMountainsFXToggle" to (sView["fade"] >= 70)
   set the layer of group "OptionsGroup" to top
   set the loc of group "OptionsGroup" to CenterScreen()
   LoadingScreen
   show group "OptionsGroup"
end OptionsGroupSetUp

## APPLY: read the stack properties the Options controls set, then use them.
on OptionsApplied
   set the customPropertySet of stack (the mainStack of this stack) to empty
   -- Volumes.
   put the OptionsNewVolume of stack (the mainStack of this stack) into tMusic
   put the OptionsNewFXVolume of stack (the mainStack of this stack) into tFX
   Audio.SetVolumes tMusic,tFX
   -- Window.
   put the OptionsNewFullScreen of stack (the mainStack of this stack) into tFull
   if tFull is true or tFull is false then put tFull into bFullScreen
   put the newResolution of stack (the mainStack of this stack) into tRez
   if bFullScreen is false and the number of items of tRez = 2 then
      set the width of this stack to item 1 of tRez
      set the height of this stack to item 2 of tRez
      set the loc of this stack to item 3 of screenRect() div 2, item 4 of screenRect() div 2
   end if
   set the fullScreen of this stack to bFullScreen
   -- Look.
   put the UseAntialiasBool of stack (the mainStack of this stack) into tAA
   if tAA is true or tAA is false then
      put tAA into bAntiAlias
      if there is a group "Viewport" then
         repeat with i = 1 to the number of graphics of group "Viewport"
            set the antialiased of graphic i of group "Viewport" to bAntiAlias
         end repeat
      end if
   end if
   put the UseEffectsBool of stack (the mainStack of this stack) into tFX
   if tFX is true or tFX is false then put tFX into sView["glow"]
   put the UseBackMountains of stack (the mainStack of this stack) into tBack
   if tBack is false then
      put 1 into sView["bands"]
   else if tBack is true and sView["bands"] < 2 then
      put 3 into sView["bands"]
   end if
   put the UseBackMountainsFX of stack (the mainStack of this stack) into tBackFX
   if tBackFX is true then
      put 75 into sView["fade"]
   else if tBackFX is false then
      put 50 into sView["fade"]
   end if
   View.Apply
   -- Back to where we were.
   if the short name of this card is "Title" then
      TitleCardOpened
   else if the short name of this card begins with "Play" then
      ResumeGame
   end if
end OptionsApplied


## Floating: the object bobs around its current Y and rocks gently.
## pAmp = bob height, pRoll = rock angle in radians, pSpeed = radians per update.
on Scene.SetBob pObj,pAmp,pRoll,pSpeed
   global gObjectTransforms
   put pAmp into gObjectTransforms[pObj]["bobAmp"]
   put pRoll into gObjectTransforms[pObj]["bobRoll"]
   put pSpeed into gObjectTransforms[pObj]["bobSpeed"]
   put GetObjectPosition(pObj,"y") into gObjectTransforms[pObj]["bobBaseY"]
   put random(628) / 100 into gObjectTransforms[pObj]["bobPhase"]
end Scene.SetBob

## Per-object behaviours, once per game.update:
##   bobbing (Scene.SetBob) and staying inside bounds (Scene.SetBounds).
on Scene.UpdateBehaviors
   global gObjectTransforms
   add 1 to sSimTick
   put empty into tKill
   repeat for each key tObj in gObjectTransforms
      -- Time to live: shots, bullets ... removed when it runs out.
      if gObjectTransforms[tObj]["ttl"] is not empty then
         subtract 1 from gObjectTransforms[tObj]["ttl"]
         if gObjectTransforms[tObj]["ttl"] <= 0 then put tObj & cr after tKill
      end if
      if gObjectTransforms[tObj]["bobAmp"] is not empty then
         put sSimTick * gObjectTransforms[tObj]["bobSpeed"] + gObjectTransforms[tObj]["bobPhase"] into tA
         put gObjectTransforms[tObj]["bobBaseY"] + gObjectTransforms[tObj]["bobAmp"] * sin(tA) into gObjectTransforms[tObj]["y"]
         put gObjectTransforms[tObj]["bobRoll"] * sin(tA * 0.7) into gObjectTransforms[tObj]["rotZ"]
         put gObjectTransforms[tObj]["bobRoll"] * 0.5 * cos(tA * 0.9) into gObjectTransforms[tObj]["rotX"]
      end if
      put gObjectTransforms[tObj]["bounds"] into tB
      if tB is not empty then
         if gObjectTransforms[tObj]["x"] < item 1 of tB then
            put item 1 of tB into gObjectTransforms[tObj]["x"]
            put abs(gObjectTransforms[tObj]["vx"]) into gObjectTransforms[tObj]["vx"]
         else if gObjectTransforms[tObj]["x"] > item 2 of tB then
            put item 2 of tB into gObjectTransforms[tObj]["x"]
            put -abs(gObjectTransforms[tObj]["vx"]) into gObjectTransforms[tObj]["vx"]
         end if
         if gObjectTransforms[tObj]["z"] < item 3 of tB then
            put item 3 of tB into gObjectTransforms[tObj]["z"]
            put abs(gObjectTransforms[tObj]["vz"]) into gObjectTransforms[tObj]["vz"]
         else if gObjectTransforms[tObj]["z"] > item 4 of tB then
            put item 4 of tB into gObjectTransforms[tObj]["z"]
            put -abs(gObjectTransforms[tObj]["vz"]) into gObjectTransforms[tObj]["vz"]
         end if
      end if
   end repeat
   repeat for each line tObj in tKill
      Entity.Kill tObj
   end repeat
end Scene.UpdateBehaviors

## Old name.
on Scene.UpdateBobbing
   Scene.UpdateBehaviors
end Scene.UpdateBobbing

## Called by APP.init after the meshes are cleared.
## The editor's test scene: the original stack-stored meshes, at the positions set by
## init.object.Transforms. Games build their own scenes (Game.OnStart on their card).
on init.scene.objects
   global gSceneObjects
   put empty into gSceneObjects
   Scene.Register "Cube","CubeLine"
   Scene.Register "Cylinder","CylinderLine"
   Scene.Register "Cone","ConeLine"
   Scene.Register "Imported","ImportedLine"
   Particles.Clear
   Collision.ClearRules
end init.scene.objects


######################################################################################
## PICKING WITHOUT TRIANGLES (Phase 2)
## Every face is tested as a whole polygon: ray vs. the face's plane, then a
## 2D point-in-polygon test. Works for concave faces too.
######################################################################################

## Ray from the camera origin along (pDX,pDY,pDZ) against one polygon.
## pFace = vertex indices; pCX/pCY/pCZ = camera-space vertex arrays.
## Returns the distance along the ray, or empty.
function RayPolygonHit pFace,pCX,pCY,pCZ,pDX,pDY,pDZ
   put the number of words of pFace into tN
   if tN < 3 then return empty
   repeat with k = 1 to tN
      put word k of pFace into tIdx
      if pCZ[tIdx] is empty then return empty
      put pCX[tIdx] into tPX[k]
      put pCY[tIdx] into tPY[k]
      put pCZ[tIdx] into tPZ[k]
   end repeat
   
   -- Face normal by Newell's method (fine for any planar n-gon).
   put 0 into tNX
   put 0 into tNY
   put 0 into tNZ
   repeat with k = 1 to tN
      put (k mod tN) + 1 into j
      add (tPY[k] - tPY[j]) * (tPZ[k] + tPZ[j]) to tNX
      add (tPZ[k] - tPZ[j]) * (tPX[k] + tPX[j]) to tNY
      add (tPX[k] - tPX[j]) * (tPY[k] + tPY[j]) to tNZ
   end repeat
   
   -- Where the ray meets the plane.
   put tNX*pDX + tNY*pDY + tNZ*pDZ into tDen
   if abs(tDen) < 0.0000001 then return empty
   put (tNX*tPX[1] + tNY*tPY[1] + tNZ*tPZ[1]) / tDen into tT
   if tT <= 0.000001 then return empty
   put tT*pDX into tHX
   put tT*pDY into tHY
   put tT*pDZ into tHZ
   
   -- Flatten to 2D by dropping the normal's largest axis.
   if abs(tNX) >= abs(tNY) and abs(tNX) >= abs(tNZ) then
      put tHY into tHU
      put tHZ into tHV
      repeat with k = 1 to tN
         put tPY[k] into tU[k]
         put tPZ[k] into tV[k]
      end repeat
   else if abs(tNY) >= abs(tNZ) then
      put tHX into tHU
      put tHZ into tHV
      repeat with k = 1 to tN
         put tPX[k] into tU[k]
         put tPZ[k] into tV[k]
      end repeat
   else
      put tHX into tHU
      put tHY into tHV
      repeat with k = 1 to tN
         put tPX[k] into tU[k]
         put tPY[k] into tV[k]
      end repeat
   end if
   
   -- Crossing-number test.
   put false into tInside
   repeat with k = 1 to tN
      put ((k + tN - 2) mod tN) + 1 into j
      if (tV[k] > tHV) is not (tV[j] > tHV) then
         put (tU[j] - tU[k]) * (tHV - tV[k]) / (tV[j] - tV[k]) + tU[k] into tCross
         if tHU < tCross then put not tInside into tInside
      end if
   end repeat
   if tInside then return tT
   return empty
end RayPolygonHit

##  This uses radians and the same rotation conventions as your existing functions.
##  It applies inverse yaw around Y, followed by inverse pitch around X.
function RotateCameraVertex tX,tY,tZ
   global gCameraYaw
   global gCameraPitch
   --put "RotateCameraVertex TX = " && tX
   -- Apply inverse camera yaw around Y.
   put tX*cos(gCameraYaw)-tZ*sin(gCameraYaw) into tX1
   put tX*sin(gCameraYaw)+tZ*cos(gCameraYaw) into tZ1
   put tY into tY1
   
   -- Apply inverse camera pitch around X.
   put tY1*cos(gCameraPitch)+tZ1*sin(gCameraPitch) into tY2
   put -tY1*sin(gCameraPitch)+tZ1*cos(gCameraPitch) into tZ2
   put tX1 into tX2
   
   return tX2 && tY2 && tZ2
end RotateCameraVertex

## Return the camera's forward direction in world coordinates.
function GetCameraForwardVector
   global gCameraYaw
   global gCameraPitch
   
   put sin(gCameraYaw)*cos(gCameraPitch) into tX
   put -sin(gCameraPitch) into tY
   put cos(gCameraYaw)*cos(gCameraPitch) into tZ
   
   return tX && tY && tZ
   #this is the inverse of the camera rotation you currently use in RotateCameraVertex.
   #It gives us a normalized direction vector (length 1), suitable for multiplying by a missile speed.
end GetCameraForwardVector


## Move the camera relative to its current yaw orientation.
on MoveCameraLocal pDirection,pDistance
   global gCameraYaw
   
   put 0 into tMoveX
   put 0 into tMoveZ
   
   switch pDirection
      
      case "forward"
         put -sin(gCameraYaw)*pDistance into tMoveX
         put -cos(gCameraYaw)*pDistance into tMoveZ
         break
         
      case "backward"
         put sin(gCameraYaw)*pDistance into tMoveX
         put cos(gCameraYaw)*pDistance into tMoveZ
         break
         
      case "right"
         put -cos(gCameraYaw)*pDistance into tMoveX
         put sin(gCameraYaw)*pDistance into tMoveZ
         break
         
      case "left"
         put cos(gCameraYaw)*pDistance into tMoveX
         put -sin(gCameraYaw)*pDistance into tMoveZ
         break
         
   end switch
   
   add tMoveX to CAMX
   add tMoveZ to CAMZ
end MoveCameraLocal


function GetObjectTransforms pObj, pAttribute
   global gObjectTransforms
   put gObjectTransforms into tObjA 
   switch pAttribute
      case "position"
         put "x,y,z" into tItems
         put GetObjectPositions(tObjA) into tValues
         break
      case "rotation"
         put "rotX,rotY,rotZ" into tItems
         put GetObjectRotations(tObjA) into tValues
         break
      case "rotationspeed"
         put "rotSpeedX,rotSpeedY,rotSpeedZ" into tItems
         put GetObjectRotationSpeed(tObjA) into tValues 
         break
      case "velocity"
         put "vx,vy,vz" into tItems
         put GetObjectVelocity(tObjA) into tValues
         break
   end switch
   repeat with i = 1 to number of items of tItems
      put item i of tValues into tArray[item i of tItems]
   end repeat
   Return tArray
end GetObjectTransforms

## UpdateObjectTransforms
## Advances object rotation and position using angular speed,
## world-space velocity, and orientation-relative local velocity.
## UpdateObjectTransforms
## Advances object rotation, acceleration and position.
## Supports world velocity, local velocity and local acceleration.

##v3
## UpdateObjectTransforms
## Advances object rotation, acceleration, braking and position.
## Supports world velocity, local velocity and local acceleration.
## Rotation order: Z-Y-X. Angles are radians.

on UpdateObjectTransforms
   
   global gObjectTransforms
   
   -- Work on a temporary copy of the object array.
   put gObjectTransforms into tObjA
   
   -- Get the list of objects.
   put the keys of tObjA into tKeys
   
   repeat for each line tObj in tKeys
      
      ## ROTATION AND ROTATION SPEED
      
      -- Advance the object's orientation.
      add tObjA[tObj]["rotSpeedX"] to tObjA[tObj]["rotX"]
      add tObjA[tObj]["rotSpeedY"] to tObjA[tObj]["rotY"]
      add tObjA[tObj]["rotSpeedZ"] to tObjA[tObj]["rotZ"]
      
      
      ## LOCAL ACCELERATION / THRUST
      
      -- Rotate local acceleration into world coordinates.
      put RotateLocalVector(tObjA[tObj]["localAx"],tObjA[tObj]["localAy"],tObjA[tObj]["localAz"],tObjA[tObj]["rotX"],tObjA[tObj]["rotY"],tObjA[tObj]["rotZ"]) into tAcceleration
      
      -- Extract world-space acceleration.
      put word 1 of tAcceleration into tAX
      put word 2 of tAcceleration into tAY
      put word 3 of tAcceleration into tAZ
      
      -- Apply acceleration to persistent world velocity.
      add tAX to tObjA[tObj]["vx"]
      add tAY to tObjA[tObj]["vy"]
      add tAZ to tObjA[tObj]["vz"]
      
      
      ## LOCAL BRAKING
      
      -- Read the current world-space velocity.
      put tObjA[tObj]["vx"] into tVX
      put tObjA[tObj]["vy"] into tVY
      put tObjA[tObj]["vz"] into tVZ
      
      -- Calculate its magnitude.
      put sqrt(tVX*tVX + tVY*tVY + tVZ*tVZ) into tSpeed
      
      -- Get the braking strength.
      put tObjA[tObj]["localBrake"] into tBrake
      
      if tBrake > 0 and tSpeed > 0 then
         
         -- Braking must not reverse the direction of travel.
         if tSpeed <= tBrake then
            
            put 0 into tObjA[tObj]["vx"]
            put 0 into tObjA[tObj]["vy"]
            put 0 into tObjA[tObj]["vz"]
            
         else
            
            -- Reduce speed without changing direction.
            put (tSpeed-tBrake)/tSpeed into tBrakeFactor
            
            put tVX*tBrakeFactor into tObjA[tObj]["vx"]
            put tVY*tBrakeFactor into tObjA[tObj]["vy"]
            put tVZ*tBrakeFactor into tObjA[tObj]["vz"]
            
         end if
         
      end if
      
      ## MAXIMUM WORLD-SPACE SPEED
      
      -- Read the maximum allowed speed.
      put tObjA[tObj]["maxWorldSpeed"] into tMaxSpeed
      
      if tMaxSpeed > 0 then
         
         -- Recalculate speed after braking.
         put tObjA[tObj]["vx"] into tVX
         put tObjA[tObj]["vy"] into tVY
         put tObjA[tObj]["vz"] into tVZ
         
         put sqrt(tVX*tVX + tVY*tVY + tVZ*tVZ) into tSpeed
         
         if tSpeed > tMaxSpeed then
            
            -- Scale all components proportionally.
            -- This preserves the direction of travel.
            put tMaxSpeed/tSpeed into tSpeedFactor
            
            put tVX*tSpeedFactor into tObjA[tObj]["vx"]
            put tVY*tSpeedFactor into tObjA[tObj]["vy"]
            put tVZ*tSpeedFactor into tObjA[tObj]["vz"]
            
         end if
         
      end if
      
      ## LOCAL-SPACE VELOCITY
      
      -- Rotate local velocity into world coordinates.
      put RotateLocalVector(tObjA[tObj]["localVx"],tObjA[tObj]["localVy"],tObjA[tObj]["localVz"],tObjA[tObj]["rotX"],tObjA[tObj]["rotY"],tObjA[tObj]["rotZ"]) into tLocalVelocity
      
      -- Extract world-space velocity contribution.
      put word 1 of tLocalVelocity into tLocalVX
      put word 2 of tLocalVelocity into tLocalVY
      put word 3 of tLocalVelocity into tLocalVZ
      
      
      ## POSITION AND VELOCITY
      
      -- Combine persistent world velocity and rotated local velocity.
      put tObjA[tObj]["vx"] + tLocalVX into tDeltaX
      put tObjA[tObj]["vy"] + tLocalVY into tDeltaY
      put tObjA[tObj]["vz"] + tLocalVZ into tDeltaZ
      
      -- Apply the combined displacement.
      add tDeltaX to tObjA[tObj]["x"]
      add tDeltaY to tObjA[tObj]["y"]
      add tDeltaZ to tObjA[tObj]["z"]
   end repeat
   -- Commit updated transforms.
   put tObjA into gObjectTransforms
   
end UpdateObjectTransforms


on velocity.from.camera pObject
   if pObject is empty then put sMissileObj into pObject
   put GetCameraForwardVector() into tVs
   put word 1 of tvS*2 into xV
   put word 2 of tvs*2 into yV
   put word 3 of tVs*2 into zV
   SetObjectLocalVelocity pObject,xv,yv,zv
   SetObjectVelocity pObject,xv,yv,zv
end velocity.from.camera

## or rock thrower or dice roller, tons of fun!
## Phase 0: the missile no longer runs its own message chain; game.update calls missile.check.
on missile.launch pObject
   if pObject is empty then put "CubeLine" into pObject
   put pObject into sMissileObj
   put random(3)-2 into tRND
   if tRND is 0 then put 1 into tRND
   -- Same spawn point as before. (The old Scene.Variables.Array() call had no arguments,
   -- so its camx/camy/camz were always 0.) Caveman math, to be replaced.
   SetObjectPosition pObject,(centerX*tRND)*2,230,centerY
   velocity.from.camera pObject
   SetObjectRotationSpeed pObject,0,.0314,0
   SetObjectRotation pObject,0,0,0
   -- Apply forward thrust.
   SetObjectLocalAcceleration pObject,(tRND*0.01),0,10
   SetObjectMaxWorldSpeed pObject,400
   -- Disable braking initially.
   SetObjectLocalBrake pObject,0
   put true into bMissile
   RENDER_SCENE -- does nothing if the game loop is running; the loop draws it
end missile.launch

on missile.check
   if distance.from.camera(sMissileObj) >= 2000 then put false into bMissile
end missile.check



function object.distance.from.center.screen pObj
   put item 1 the loc of graphic pObj into x1
   put item 2 the loc of graphic pObj into y1
   put the width of this stack/2 into x2
   put  the height of this stack/2 into y2
   put distance(x1,y1,x2,y2) into tDist
   return tDist
end object.distance.from.center.screen

function distance.from.camera pObj
   put getObjectPosition(pObj,"x") into x1
   put getObjectPosition(pObj,"z") into y1
   put distance(x1,y1,CAMX*-1,CAMZ*-1) into tdist
   return tDist
end distance.from.camera

function distance x1,y1,x2,y2
   return sqrt((x2-x1)^2 + (y2-y1)^2)
end distance


on test.local.velocity
   SetObjectLocalVelocity "CubeLine",20,0,0
   put (random(4)-4)*3.1459 into tRndY
   SetObjectRotationSpeed "CubeLine",0,tRndY,0
   SetObjectRotation "CubeLine",tRndY,tRndY,0
   SetObjectVelocity "CubeLine",0,0,200
   SetObjectLocalVelocity "ConeLine",-2,1,-2
   SetObjectRotationSpeed "ConeLine",0,0.02,0
   UpdateObjectTransforms
   Render_Scene
end test.local.velocity

on SetObjectVelocity pObj,px,py,pz,pLocal
   global gObjectTransforms
   if pObj is empty then exit SetObjectVelocity
   repeat for each item I in "px,py,pz"
      do "put" &&I &&"is empty into tBool"
      if tBool then  do "put 0 into" &&  I
   end repeat
   if pLocal is empty then
      put px into gObjectTransforms[pObj]["vX"] 
      put py into gObjectTransforms[pObj]["vY"] 
      put pz into gObjectTransforms[pObj]["vZ"]
   else
      put px into gObjectTransforms[tObj]["localVx"]
      put py into gObjectTransforms[tObj]["localVy"]
      put pz into gObjectTransforms[tObj]["localVz"]
   end if
end SetObjectVelocity

function GetObjectVelocity pObj,pPos
   global gObjectTransforms
   put gObjectTransforms[pObj] into tObjA
   if pPos is empty then
      return tObjA["vX"],tObjA["vY"],tObjA["vZ"]
   else
      return tObjA[pPos]
   end if
end GetObjectVelocity

on SetObjectLocalVelocity pObj,pX,pY,pZ
   global gObjectTransforms
   put pX into gObjectTransforms[pObj]["localVx"]
   put pY into gObjectTransforms[pObj]["localVy"]
   put pZ into gObjectTransforms[pObj]["localVz"]
end SetObjectLocalVelocity

## GetObjectLocalVelocity
## Returns local-space velocity as comma-delimited XYZ values.
function GetObjectLocalVelocity pObj
   global gObjectTransforms
   put gObjectTransforms[pObj]["localVx"] into tVX
   put gObjectTransforms[pObj]["localVy"] into tVY
   put gObjectTransforms[pObj]["localVz"] into tVZ
   return tVX & comma & tVY & comma & tVZ
end GetObjectLocalVelocity

## SetObjectLocalAcceleration
## Sets acceleration relative to the object's orientation.
on SetObjectLocalAcceleration pObj,pAX,pAY,pAZ
   global gObjectTransforms
   put pAX into gObjectTransforms[pObj]["localAx"]
   put pAY into gObjectTransforms[pObj]["localAy"]
   put pAZ into gObjectTransforms[pObj]["localAz"]
end SetObjectLocalAcceleration

## test.object.thrust
## Tests local thrust while an object rotates.
on test.object.thrust
   -- !! object initialization occurs outside this test
   --   init.object.Transforms
   -- Start with zero world velocity.
   --SetObjectVelocity "CubeLine",0,0,0
   -- Apply thrust along local positive Z.
   SetObjectLocalAcceleration "CubeLine",0,0,1
   -- Rotate around Y.
   SetObjectRotationSpeed "CubeLine",0,0.01,.01
   -- Advance movement.
   UpdateObjectTransforms
   -- Render.
   Render_Scene
end test.object.thrust


## GetObjectLocalAcceleration
## Returns local acceleration as comma-delimited XYZ values.
function GetObjectLocalAcceleration pObj
   global gObjectTransforms
   put gObjectTransforms[pObj]["localAx"] into tAX
   put gObjectTransforms[pObj]["localAy"] into tAY
   put gObjectTransforms[pObj]["localAz"] into tAZ
   return tAX & comma & tAY & comma & tAZ
end GetObjectLocalAcceleration

## SetObjectLocalBrake
## Sets the braking strength for an object.
## A value of zero disables braking.
on SetObjectLocalBrake pObj,pBrake
   global gObjectTransforms
   if pBrake < 0 then put 0 into pBrake
   put pBrake into gObjectTransforms[pObj]["localBrake"]
end SetObjectLocalBrake

## GetObjectLocalBrake
## Returns the object's local braking strength.
function GetObjectLocalBrake pObj
   global gObjectTransforms
   return gObjectTransforms[pObj]["localBrake"]
end GetObjectLocalBrake

## test.object.braking
## Tests thrust, braking and maximum world-space speed.
on test.object.braking
   ## !! object init occurs outside this test
   --init.object.Transforms
   -- Start without existing momentum.
   --SetObjectVelocity "CubeLine",0,0,0
   -- Allow a maximum world speed of 3 units per update.
   SetObjectMaxWorldSpeed "CubeLine",3
   -- Apply forward thrust. Also occurs outside this test
   --SetObjectLocalAcceleration "CubeLine",0,0,0.1
   -- Rotate around Y.
   SetObjectRotationSpeed "CubeLine",0,0.01,0
   -- Disable braking initially.
   SetObjectLocalBrake "CubeLine",0
   -- update occurs outside this test
   --UpdateObjectTransforms
   --Render_Scene
end test.object.braking

## SetObjectMaxWorldSpeed
## Sets the maximum magnitude of persistent world velocity.
## Zero or a negative value means unlimited.
on SetObjectMaxWorldSpeed pObj,pMaxSpeed
   global gObjectTransforms
   if pMaxSpeed < 0 then put 0 into pMaxSpeed
   put pMaxSpeed into gObjectTransforms[pObj]["maxWorldSpeed"]
end SetObjectMaxWorldSpeed

## GetObjectMaxWorldSpeed
## Returns the object's maximum world-space speed.

function GetObjectMaxWorldSpeed pObj
   global gObjectTransforms
   return gObjectTransforms[pObj]["maxWorldSpeed"]
end GetObjectMaxWorldSpeed

## RotateLocalVector
## Rotates a local-space direction vector (velocity, thrust) into world-space orientation.
## Same rotation math as RotateObjectVertex: Z, then Y, then X, radians.
## The difference is what happens afterwards: a vertex is then translated
## as part of rendering; a direction vector is not.
function RotateLocalVector tVX,tVY,tVZ,tRotX,tRotY,tRotZ
   
   -- Preserve the incoming vector.
   put tVX into tDX
   put tVY into tDY
   put tVZ into tDZ
   
   -- Rotate around Z.
   put tDX*cos(tRotZ)-tDY*sin(tRotZ) into tX1
   put tDX*sin(tRotZ)+tDY*cos(tRotZ) into tY1
   put tDZ into tZ1
   
   -- Rotate around Y.
   put tX1*cos(tRotY)+tZ1*sin(tRotY) into tX2
   put -tX1*sin(tRotY)+tZ1*cos(tRotY) into tZ2
   put tY1 into tY2
   
   -- Rotate around X.
   put tY2*cos(tRotX)-tZ2*sin(tRotX) into tY3
   put tY2*sin(tRotX)+tZ2*cos(tRotX) into tZ3
   put tX2 into tX3
   
   -- Return the rotated vector.
   return tX3 && tY3 && tZ3
   
end RotateLocalVector

on SetObjectPosition pObj,px,py,pz
   global gObjectTransforms
   if pObj is empty then exit SetObjectPosition
   repeat for each item I in "px,py,pz"
      do "put" &&I &&"is empty into tBool"
      if tBool then  do "put 0 into" &&  I
   end repeat
   put px into gObjectTransforms[pObj]["X"] 
   put py into gObjectTransforms[pObj]["Y"] 
   put pz into gObjectTransforms[pObj]["Z"]
end SetObjectPosition

function GetObjectPosition pObj,pPos
   global gObjectTransforms
   put gObjectTransforms[pObj] into tObjA
   if pPos is empty then
      return tObjA["X"],tObjA["Y"],tObjA["Z"]
   else
      return tObjA[pPos]
   end if
end GetObjectPosition

### ROTATION
command SetObjectRotation pObj,pX,pY,pZ
   global gObjectTransforms
   put pX into gObjectTransforms[pObj]["rotX"]
   put pY into gObjectTransforms[pObj]["rotY"]
   put pZ into gObjectTransforms[pObj]["rotZ"]
end SetObjectRotation


command SetObjectRotationSpeed pObj,pX,pY,pZ
   global gObjectTransforms
   put pX into gObjectTransforms[pObj]["rotSpeedX"]
   put pY into gObjectTransforms[pObj]["rotSpeedY"]
   put pZ into gObjectTransforms[pObj]["rotSpeedZ"]
end SetObjectRotationSpeed

function GetObjectRotation pObj
   global gObjectTransforms
   put gObjectTransforms[pObj]["rotX"] into tX
   put gObjectTransforms[pObj]["rotY"] into tY
   put gObjectTransforms[pObj]["rotZ"] into tZ
   if tX is empty or tX is not a number then put 0 into tX
   if tY is empty or tY is not a number then put 0 into tY
   if tZ is empty or tZ is not a number then put 0 into tZ
   return tX,tY,tZ
end GetObjectRotation

function GetObjectRotationSpeed pObj
   global gObjectTransforms
   put gObjectTransforms[pObj]["rotSpeedX"] into tX
   put gObjectTransforms[pObj]["rotSpeedY"] into tY
   put gObjectTransforms[pObj]["rotSpeedZ"] into tZ
   if tX is empty or tX is not a number then put 0 into tX
   if tY is empty or tY is not a number then put 0 into tY
   if tZ is empty or tZ is not a number then put 0 into tZ
   return tX,tY,tZ
end GetObjectRotationSpeed


-- quick text overview of the positions
function list.object.positions
   global gObjectTransforms
   repeat for each line tObj in the keys of gObjectTransforms   
      put the keys of gObjectTransforms[tObj] into tkeys
      put tobj & space after tList
      repeat for each item K in "x,y,z"
         put gObjectTransforms[tObj][k] & comma after tList
      end repeat
      put cr after tlist
   end repeat
   return tList
end list.object.positions

on record.scene.object.transform.states
   global gObjectTransforms
   set the customPropertySet of stack (the mainStack of this stack) to Object_Transforms
   repeat for each line tObj in the keys of gObjectTransforms
      record.object.transform.state tObj,gObjectTransforms[tObj]
   end repeat
end record.scene.object.transform.states

on record.object.transform.state pObj,tArray,tIndex
   global gObjectTransforms
   if pObj is  empty then exit record.object.transform.state
   if tArray is empty or number of lines of the keys of tArray < 1 then put gObjectTransforms into tarray
   set the customPropertySet of stack (the mainStack of this stack) to Object_Transforms
   do "put the" && pObj &&"of stack (the mainStack of this stack) into tObjA"
   if tIndex is empty then put the number of lines of the keys of tObjA+1 into tIndex 
   put tArray into tObjA[tIndex]
   do "set the" && pObj &&"of stack (the mainStack of this stack) to tObjA"
   set the customPropertySet of of stack (the mainStack of this stack) to empty
end record.object.transform.state

function recall.object.transform.state pObj,tIndex
   global gObjectTransforms
   if pObj is empty then exit recall.object.transform.state
   set the customPropertySet of stack (the mainStack of this stack) to Object_Transforms
   do "put the" && pObj &&"of stack (the mainStack of this stack) into tObjA"
   if tIndex is empty then 
      put the keys of tObjA into tKeys
      sort lines of tKeys numeric ascending
      put  (the number of lines of tKeys) into tIndex 
   end if
   put tObjA[tIndex] into gObjectTransforms[pObj]
   set the customPropertySet of stack (the mainStack of this stack) to empty
   return gObjectTransforms
end recall.object.transform.state

## InitMouseLook
## Initializes independent camera-look input state.

on Init.MouseLook
   global bMouseLook
   global gCameraYaw
   global gCameraPitch
   global gMouseLookLastH
   global gMouseLookLastV
   global gMouseLookSensitivity
   global gMouseDeltaX
   global gMouseDeltaY
   
   put false into bMouseLook
   
   -- Camera orientation, in radians.
   put 0 into gCameraYaw
   put 0 into gCameraPitch
   
   -- Mouse position history.
   put empty into gMouseLookLastH
   put empty into gMouseLookLastV
   
   -- Radians per mouse pixel.
   put 0.003 into gMouseLookSensitivity
   
   -- Most recently measured mouse delta.
   put 0 into gMouseDeltaX
   put 0 into gMouseDeltaY
end Init.MouseLook


## SetMouseLook
## Enables or disables mouse-look input.
on SetMouseLook pEnabled
   global bMouseLook
   global gMouseLookLastH
   global gMouseLookLastV
   
   put pEnabled into bMouseLook
   
   -- Reset the baseline to prevent a jump on reactivation.
   put empty into gMouseLookLastH
   put empty into gMouseLookLastV
end SetMouseLook


## ToggleMouseLook
## Toggles the mouse-look master switch.
on ToggleMouseLook
   global bMouseLook
   if bMouseLook then
      SetMouseLook false
   else
      SetMouseLook true
   end if
end ToggleMouseLook


on mouseUp pButton
   if the short name of this card is "Edit_HUD" and not sLoopActive then exit mouseUp
   -- Playing: the game card decides (pButton: 1 left, 3 right). Editing: click selects.
   if sLoopActive then
      dispatch "Game.OnClick" to this card with the mouseH, the mouseV, pButton
      exit mouseUp
   end if
   debug.clear
   put the mouseH into tMouseX
   put the mouseV into tMouseY
   
   put "Mouse: " & tMouseX && tMouseY & cr & \
         "Center: " & CenterX && CenterY & cr & \
         "Offset: " & (tMouseX-CenterX) && (tMouseY-CenterY) into tReport
   put ScreenToCameraRay(tMouseX,tMouseY,CenterX,CenterY,MOVEX,MOVEY,theScale,gFocalLength) into tRay
   put tReport & cr & "Ray: " & tRay into tReport
   test.Raycast
   --put tReport 
end mouseUp


## mouseMove
## Tracks mouse displacement while mouse look is enabled
## and Caps Lock is active.

on mouseMove pNewMouseH,pNewMouseV
   -- Mouse-look: Caps Lock on, browse tool. Works while editing AND while playing.
   if (the tool is not "browse tool" or pNewMouseH is empty) then
      if bMouseLook then mouselook.stop
      exit mouseMove
   end if
   if bMouseLook and not bPaused then mouseLOOK pNewMouseH,pNewMouseV
end mouseMove

on mouselook.stop
   global bMouseLook
   global gMouseLookLastH
   global gMouseLookLastV
   global gMouseLookSensitivity
   global gMouseDeltaX
   global gMouseDeltaY
   put false into bMouselook
   put empty into gMouseLookLastH
   put empty into gMouseLookLastV
   put 0 into gMouseDeltaX
   put 0 into gMouseDeltaY
end mouselook.stop

on mouseLOOK pNewMouseH,pNewMouseV
   --   PUT pNewMouseH,pNewMouseV
   global bMouseLook
   global gCameraYaw
   global gCameraPitch
   global gMouseLookLastH
   global gMouseLookLastV
   global gMouseLookSensitivity
   global gMouseDeltaX
   global gMouseDeltaY
   
   -- Mouse look must be enabled.
   if not bMouseLook then
      --put "mousemove bmouseLook =" && bMouseLook INTO FIELD "STATUS"
      put empty into gMouseLookLastH
      put empty into gMouseLookLastV
      exit mouseLOOK
   end if
   
   -- Caps Lock must be active.
   if the capsLockKey is up then
      put false into bMouseLook
      put empty into gMouseLookLastH
      put empty into gMouseLookLastV
      put 0 into gMouseDeltaX
      put 0 into gMouseDeltaY
      exit mouseLOOK
   end if
   
   -- First event establishes the baseline.
   if gMouseLookLastH is empty or gMouseLookLastV is empty then
      put pNewMouseH into gMouseLookLastH
      put pNewMouseV into gMouseLookLastV
      exit mouseLOOK
   end if
   
   -- Calculate mouse displacement.
   put pNewMouseH - gMouseLookLastH into gMouseDeltaX
   put pNewMouseV - gMouseLookLastV into gMouseDeltaY
   
   -- Store the new mouse position.
   put pNewMouseH into gMouseLookLastH
   put pNewMouseV into gMouseLookLastV
   
   -- Horizontal movement changes camera yaw.
   add gMouseDeltaX*gMouseLookSensitivity to gCameraYaw
   
   -- Vertical movement changes camera pitch.
   -- Moving the mouse upward looks upward.
   subtract gMouseDeltaY*gMouseLookSensitivity from gCameraPitch
   
   -- Limit pitch to approximately +/- 89 degrees.
   if gCameraPitch > 1.553343 then
      put 1.553343 into gCameraPitch
   end if
   
   if gCameraPitch < -1.553343 then
      put -1.553343 into gCameraPitch
   end if
   -- (yaw is shown by UI.update.status.display)
   -- The game loop redraws by itself; when editing, redraw without advancing the simulation.
   if not sLoopActive then RENDER_VIEW
end mouseLOOK

## ObjectMotionDiagnostic
## Builds a read-only diagnostic report for one object.
## Reports position, rotation, velocity, acceleration, braking,
## maximum speed, and calculated total movement.

function ObjectMotionDiagnostic pObj
   
   global gObjectTransforms
   
   -- Check that the requested object exists.
   put the keys of gObjectTransforms into tObjectKeys
   
   if pObj is not among the lines of tObjectKeys then
      return "Object not found: " & pObj
   end if
   
   ## POSITION
   
   put gObjectTransforms[pObj]["x"] into tX
   put gObjectTransforms[pObj]["y"] into tY
   put gObjectTransforms[pObj]["z"] into tZ
   
   ## ROTATION
   
   put gObjectTransforms[pObj]["rotX"] into tRotX
   put gObjectTransforms[pObj]["rotY"] into tRotY
   put gObjectTransforms[pObj]["rotZ"] into tRotZ
   
   ## WORLD VELOCITY
   
   put gObjectTransforms[pObj]["vx"] into tVX
   put gObjectTransforms[pObj]["vy"] into tVY
   put gObjectTransforms[pObj]["vz"] into tVZ
   
   put sqrt(tVX*tVX + tVY*tVY + tVZ*tVZ) into tWorldSpeed
   
   ## LOCAL VELOCITY
   
   put gObjectTransforms[pObj]["localVx"] into tLocalVX
   put gObjectTransforms[pObj]["localVy"] into tLocalVY
   put gObjectTransforms[pObj]["localVz"] into tLocalVZ
   
   -- Convert local velocity into world coordinates.
   put RotateLocalVector(tLocalVX,tLocalVY,tLocalVZ,tRotX,tRotY,tRotZ) into tRotatedVelocity
   
   put word 1 of tRotatedVelocity into tWorldLocalVX
   put word 2 of tRotatedVelocity into tWorldLocalVY
   put word 3 of tRotatedVelocity into tWorldLocalVZ
   
   ## LOCAL ACCELERATION
   
   put gObjectTransforms[pObj]["localAx"] into tLocalAX
   put gObjectTransforms[pObj]["localAy"] into tLocalAY
   put gObjectTransforms[pObj]["localAz"] into tLocalAZ
   
   -- Convert local acceleration into world coordinates.
   put RotateLocalVector(tLocalAX,tLocalAY,tLocalAZ,tRotX,tRotY,tRotZ) into tRotatedAcceleration
   
   put word 1 of tRotatedAcceleration into tWorldAX
   put word 2 of tRotatedAcceleration into tWorldAY
   put word 3 of tRotatedAcceleration into tWorldAZ
   
   ## BRAKING AND SPEED LIMIT
   
   put gObjectTransforms[pObj]["localBrake"] into tBrake
   put gObjectTransforms[pObj]["maxWorldSpeed"] into tMaxSpeed
   
   ## TOTAL MOVEMENT
   
   -- Combine persistent world velocity and rotated local velocity.
   put tVX + tWorldLocalVX into tMoveX
   put tVY + tWorldLocalVY into tMoveY
   put tVZ + tWorldLocalVZ into tMoveZ
   
   put sqrt(tMoveX*tMoveX + tMoveY*tMoveY + tMoveZ*tMoveZ) into tMoveSpeed
   
   ## BUILD REPORT
   
   put "OBJECT MOTION DIAGNOSTIC" & cr into tReport
   put "Object: " & pObj & cr & cr after tReport
   
   put "[POSITION]" & cr after tReport
   put "X: " & tX & cr after tReport
   put "Y: " & tY & cr after tReport
   put "Z: " & tZ & cr & cr after tReport
   
   put "[ROTATION - RADIANS]" & cr after tReport
   put "X: " & tRotX & cr after tReport
   put "Y: " & tRotY & cr after tReport
   put "Z: " & tRotZ & cr & cr after tReport
   
   put "[WORLD VELOCITY]" & cr after tReport
   put "X: " & tVX & cr after tReport
   put "Y: " & tVY & cr after tReport
   put "Z: " & tVZ & cr after tReport
   put "Magnitude: " & tWorldSpeed & cr & cr after tReport
   
   put "[LOCAL VELOCITY]" & cr after tReport
   put "Local X: " & tLocalVX & cr after tReport
   put "Local Y: " & tLocalVY & cr after tReport
   put "Local Z: " & tLocalVZ & cr after tReport
   put "World X: " & tWorldLocalVX & cr after tReport
   put "World Y: " & tWorldLocalVY & cr after tReport
   put "World Z: " & tWorldLocalVZ & cr & cr after tReport
   
   put "[LOCAL ACCELERATION / THRUST]" & cr after tReport
   put "Local X: " & tLocalAX & cr after tReport
   put "Local Y: " & tLocalAY & cr after tReport
   put "Local Z: " & tLocalAZ & cr after tReport
   put "World X: " & tWorldAX & cr after tReport
   put "World Y: " & tWorldAY & cr after tReport
   put "World Z: " & tWorldAZ & cr & cr after tReport
   
   put "[BRAKING AND SPEED LIMIT]" & cr after tReport
   put "Brake: " & tBrake & cr after tReport
   
   if tMaxSpeed <= 0 then
      put "Maximum world speed: Unlimited" & cr & cr after tReport
   else
      put "Maximum world speed: " & tMaxSpeed & cr & cr after tReport
   end if
   
   put "[TOTAL MOVEMENT PER UPDATE]" & cr after tReport
   put "X: " & tMoveX & cr after tReport
   put "Y: " & tMoveY & cr after tReport
   put "Z: " & tMoveZ & cr after tReport
   put "Magnitude: " & tMoveSpeed & cr AFTER treport
   
   return tReport
   
end ObjectMotionDiagnostic


## The resulting vector is normalized, 
## so the intersection distance will represent actual camera-space distance.
## Convert a screen coordinate into a normalized camera-space ray.
function ScreenToCameraRay pScreenX,pScreenY,pCenterX,pCenterY,pMoveX,pMoveY,pScale,pFocalLength
   --   put pScreenX,pScreenY,pCenterX,pCenterY,pMoveX,pMoveY,pScale,pFocalLength
   -- Validate projection parameters.
   if pFocalLength = 0 then return empty
   if pScale = 0 then return empty
   
   -- Reverse the screen-space offsets.
   put pScreenX-pCenterX-pMoveX into tOffsetX
   put pScreenY-pCenterY-pMoveY into tOffsetY
   
   -- Reverse perspective projection.
   put tOffsetX*pScale/pFocalLength into tRayX
   put tOffsetY*pScale/pFocalLength into tRayY
   put 1 into tRayZ
   
   -- Normalize the direction vector.
   -- (Explicit "/" on purpose: "divide tLength into tRayX" divided the wrong way round,
   --  so a centre click, where tRayX = 0, threw a division error and other clicks
   --  produced a skewed ray. That is why the laser missed the enemies.)
   put sqrt(tRayX*tRayX + tRayY*tRayY + tRayZ*tRayZ) into tLength
   if tLength is not a number or tLength = 0 then return empty
   return (tRayX / tLength) && (tRayY / tLength) && (tRayZ / tLength)
end ScreenToCameraRay




## ShowObjectMotionDiagnostic
## Displays the motion diagnostic for the requested object.
on ShowObjectMotionDiagnostic pObj
   put ObjectMotionDiagnostic(pObj) into tReport
   answer tReport
end ShowObjectMotionDiagnostic

on testSet
   SetObjectPosition "cubeline",-250,0,600
   SetObjectPosition "cylinderline",90,10,600
   SetObjectPosition "coneline",950,10,600
   SetObjectPosition "importedline",90,150,600
end testSet

on test.recall pobj
   put "@test.recall gdebug" && cr into gDebug
   put "Start" &cr &list.object.positions() & cr into tOut
   testSet -- set positions
   record.scene.object.transform.states -- record allobject states
   put empty into gObjectTransforms
   SetObjectPosition "cubeline",50,0,600
   SetObjectPosition "cylinderline",0,0,0
   SetObjectPosition "coneline",-50,0,600
   SetObjectPosition "importedline",50,150,600
   --testSet2 -- different positions
   record.scene.object.transform.states
   put recall.object.transform.state("cubeline",1)  into gObjectTransforms --recall  state 1
   put "test1:" & cr  &list.object.positions() & cr after tOut
   put recall.object.transform.state("cubeline",2) into gObjectTransforms --recall  state 1
   put "test2:" & cr & list.object.positions() after gDebug
   put gDebug
end test.recall


-- align the graphics with the sidebar (for when they are lost in x,y,z space beyond the screen and human editor has need of visual confirmation)
on sidebar.graphics
   put the right of button "Sidebar" into R
   put 20 into T
   repeat with i = 1 to number of graphics of this card
      set the left of graphic i to R
      set the top of graphic i to T
      put the bottom of graphic i into T
   end repeat
end sidebar.graphics


-- isolate loose debugging commands
function emptyPuts ## VERSION 11 08 2026 B
   put the script of stack (the mainStack of this stack) into tScript
   put tScript into tSubScript
   filter lines of tSubScript with "*put*"
   Filter lines of tScript with "Put*"
   put tSubScript & cr & tScript into tScript
   filter lines of tScript without "*into*"
   filter lines of tScript without "*after*"
   filter lines of tScript without "*before*"
   filter lines of tScript without "--put*"
   filter lines of tScript without "*--put*"
   filter lines of tScript without "*--  put*"
   filter lines of tScript without "*-- put*"
   filter lines of tScript without "*--   put*"
   filter lines of tScript without "* \"
   filter lines of tScript without "*& \" 
   return  tScript
end emptyPuts


#### 3D PRIMITIVES OBJECTS ONLY NEED TO BE DEFINED ONCE AND ARE STORED IN THE STACK PROPERTIES : xyzCUBEarray etc.
####  REFACTOR 11 07 2026
on DefineCone
   
   -- Read the circle coordinates.
   put the cone_base of this stack into tPoints
   filter lines of tPoints without empty
   
   put the number of lines of tPoints into tCount
   
   if tCount < 3 then exit DefineCone
   
   -- Clear the mesh data.
   put empty into tEdges
   put empty into tFaces
   put empty into tBaseFace
   
   put 0 into n
   
   -- Build the cone vertices.
   -- Each circle point produces a bottom vertex
   -- and a coincident apex vertex.
   
   repeat with tI = 1 to tCount
      
      put line tI of tPoints into XY
      
      put (item 1 of XY) + 60 into X
      put (item 2 of XY) + 60 into Y
      
      -- Base vertex.
      add 1 to n
      put -60 into Z
      
      setXYZ "Cone","X",n,X
      setXYZ "Cone","Y",n,Y
      setXYZ "Cone","Z",n,Z
      
      -- Apex vertex.
      add 1 to n
      put 60 into Z
      
      setXYZ "Cone","X",n,1
      setXYZ "Cone","Y",n,1
      setXYZ "Cone","Z",n,Z
      
      -- Collect the base vertex index.
      put (tI * 2) - 1 into tBottom
      
      if tI = 1 then
         put tBottom into tBaseFace
      else
         put tBaseFace & space & tBottom into tBaseFace
      end if
      
   end repeat
   
   -- Build the cone edges and triangular side faces.
   
   repeat with tI = 1 to tCount
      
      put (tI * 2) - 1 into tBottom
      put tI * 2 into tTop
      
      put tI + 1 into tNext
      
      if tNext > tCount then
         put 1 into tNext
      end if
      
      put (tNext * 2) - 1 into tNextBottom
      put tNext * 2 into tNextTop
      
      -- Bottom ring edge.
      put tBottom & space & tNextBottom & cr after tEdges
      
      -- Existing apex connection.
      put tBottom & space & tTop & cr after tEdges
      
      -- Triangular side face.
      put tBottom & space & tNextBottom & space & tTop & cr after tFaces
      
   end repeat
   
   -- Add the polygonal base.
   put tBaseFace & cr after tFaces
   
   -- Store the edge and face lists.
   set the customPropertySet of stack (the mainStack of this stack) to empty
   set the ConeEdges of stack (the mainStack of this stack)  to tEdges
   set the ConeFaces of stack (the mainStack of this stack)  to tFaces
   
end DefineCone

---- ## Object coordinates (these 8 points form a cube):
---- ## Stored in custom property of stack, but could be made variable array?
---- ## Once these values are stored in the stack then
---- ## This handler is no longer referenced by the program
---- ## If you copied code to a fresh stack, call this once
on DefineCube
   ----  "I" = the distance of the vertice from center, ie, pivot
   put 60 into I
   ---- X
   --- right wall
   setXYZ "Cube","X",1,I
   setXYZ "Cube","X",2,I
   setXYZ "Cube","X",3,I
   setXYZ "Cube","X",4,I
   --- left wall
   setXYZ "Cube","X",5,-I
   setXYZ "Cube","X",6,-I
   setXYZ "Cube","X",7,-I
   setXYZ "Cube","X",8,-I
   
   ---- Y
   --- floor
   setXYZ "Cube","Y",1,I
   setXYZ "Cube","Y",2,I
   setXYZ "Cube","Y",5,I
   setXYZ "Cube","Y",6,I
   ---- roof
   setXYZ "Cube","Y",3,-I
   setXYZ "Cube","Y",4,-I
   setXYZ "Cube","Y",7,-I
   setXYZ "Cube","Y",8,-I
   
   ---- Z
   --- right wall
   setXYZ "Cube","Z",1,-I
   setXYZ "Cube","Z",2,I
   setXYZ "Cube","Z",3,-I
   setXYZ "Cube","Z",4,I
   --- left wall
   setXYZ "Cube","Z",5,-I
   setXYZ "Cube","Z",6,I
   setXYZ "Cube","Z",7,-I
   setXYZ "Cube","Z",8,I
   
   -- Define the six cube faces.
   put empty into tFaces
   
   -- Negative Z face.
   put "1 3 7 5" & cr after tFaces
   
   -- Positive Z face.
   put "2 6 8 4" & cr after tFaces
   
   -- Positive X face.
   put "1 2 4 3" & cr after tFaces
   
   -- Negative X face.
   put "5 7 8 6" & cr after tFaces
   
   -- Positive Y face.
   put "1 5 6 2" & cr after tFaces
   
   -- Negative Y face.
   put "3 4 8 7" & cr after tFaces
   
   -- Store the face list.
   set the customPropertySet of this stack to empty
   set the CubeFaces of stack (the mainStack of this stack) to tFaces
end DefineCube



####  REFACTOR 11-07-2026
on DefineCylinder
   
   -- Read the circle coordinates.
   put the cone_base of this stack into tPoints
   filter lines of tPoints without empty
   
   put the number of lines of tPoints into tCount
   
   if tCount < 3 then exit DefineCylinder
   
   -- Clear the mesh data.
   put empty into tEdges
   put empty into tFaces
   put empty into tBottomFace
   put empty into tTopFace
   
   put 0 into n
   
   -- Build the cylinder vertices.
   -- Each circle point produces a bottom and top vertex.
   
   repeat with tI = 1 to tCount
      
      put line tI of tPoints into XY
      
      put (item 1 of XY) + 60 into X
      put (item 2 of XY) + 60 into Y
      
      -- Bottom vertex.
      add 1 to n
      put -60 into Z
      
      setXYZ "Cylinder","X",n,X
      setXYZ "Cylinder","Y",n,Y
      setXYZ "Cylinder","Z",n,Z
      
      -- Top vertex.
      add 1 to n
      put 60 into Z
      
      setXYZ "Cylinder","X",n,X
      setXYZ "Cylinder","Y",n,Y
      setXYZ "Cylinder","Z",n,Z
      
      -- Collect the cap vertex indices.
      put (tI * 2) - 1 into tBottom
      put tI * 2 into tTop
      
      if tI = 1 then
         put tBottom into tBottomFace
         put tTop into tTopFace
      else
         put tBottomFace & space & tBottom into tBottomFace
         put tTopFace & space & tTop into tTopFace
      end if
      
   end repeat
   
   -- Build the cylinder edges and side faces.
   
   repeat with tI = 1 to tCount
      
      put (tI * 2) - 1 into tBottom
      put tI * 2 into tTop
      
      put tI + 1 into tNext
      
      if tNext > tCount then
         put 1 into tNext
      end if
      
      put (tNext * 2) - 1 into tNextBottom
      put tNext * 2 into tNextTop
      
      -- Bottom ring edge.
      put tBottom & space & tNextBottom & cr after tEdges
      
      -- Top ring edge.
      put tTop & space & tNextTop & cr after tEdges
      
      -- Vertical edge.
      put tBottom & space & tTop & cr after tEdges
      
      -- Side face.
      put tBottom & space & tNextBottom & space & tNextTop & space & tTop & cr after tFaces
      
   end repeat
   
   -- Add the two polygonal caps.
   put tBottomFace & cr after tFaces
   put tTopFace & cr after tFaces
   
   -- Store the edge and face lists.
   set the customPropertySet of stack (the mainStack of this stack) to empty
   set the CylinderEdges of stack (the mainStack of this stack) to tEdges
   set the CylinderFaces of stack (the mainStack of this stack) to tFaces
   
end DefineCylinder


on TestPrimitiveFaces
   put "CUBE:" & cr & the number of lines of the CubeFaces of stack (the mainStack of this stack)  & cr & \
         "CYLINDER:" & cr & the number of lines of the CylinderFaces of stack (the mainStack of this stack)  & cr & \
         "CONE:" & cr & the number of lines of the ConeFaces of stack (the mainStack of this stack) 
end TestPrimitiveFaces



# new
-- 11 09 2026 STACK SCRIPT ADDITIONS

on openCard
   send stack.retitle to stack (The mainStack of this stack)   in 7 seconds -- it needs time for sounds to load, this may not be going to title card first might actually have sped this up
   pass openCard
end openCard

on menuPick.threedots myPick
set itemDel to "|"
replace " |" with "|" in myPick
put item 1 of myPick into outerMenu
if number of items of myPick >1 then put item 2 of myPick into tRealPick

switch (outerMenu)
case "Edit"
replace "|" with "_" in myPick
if there is not a card myPick then
   answer "There is no card" && myPick && "yet."
   exit menuPick.threedots
end if
go card myPick
replace "_" with space in tRealPick
stack.retitle tRealPick
break

case "Style"
   -- Save Preset / Save As... are in the Style submenu too.
   if tRealPick is "Save Preset" then
      View.SavePreset -- saves under the current preset's name
   else if tRealPick is "Save As..." then
      ask "Save as" with "MyStyle"
      -- Block form on purpose: a one-line "if ... then x" followed by "else" takes
      -- that else as its own, which broke this whole if/else.
      if it is not empty then
         View.SavePreset it
      end if
   else
      View.UsePreset tRealPick -- View.PresetDefaults is a function: calling it alone did nothing
   end if
break

case "Glow"
   View.Toggle "glow", (tRealPick is "On")
break

case "Game"
## DEBUG!  SOME OLD GAME GRAPHICS REMAIN in ViewPort WHEN SWITCHING GAMES!!
## GAME SCRIPTS ARE DISABLED FOR THE MOMENT! We want to run a fast test fake games, switch cards, see what graphics persist between cards.
if there is a card ("Play." & trealPick)  then 
-- A fresh copy of the game's script from GAME_CARD_SCRIPTS (if it has one there).
load.card.script.from.set ("Play." & tRealPick)
Game.Prepare.Card tRealPick  
put gCurrentGame into field "TITLE" of card "TITLE"
go card "Title"
stack.retitle gCurrentGame
# DEBUG! we need to confirm that all graphics in the game card Game_Graphics have been created, all music players have  been loaded and have their file names preset with something before switching to the card 	
end if
break

case"View Bands"
 View.Set "bands",tRealPick
 Render_View
break


case "Developer"
choose pointer tool
go card "Developer"
stack.retitle tRealPick
put true into bDeveloper
choose pointer tool
break

case "Reset"
if the short name of the current card is  "Developer" then
APP.init
Render_Scene
else
put gCurrentGame into tCurrentGame
  APP.init  -- this resets all globals - need game reset on the card I think
game.select tCurrentGame
Game.Prepare.Card tRealPick 
stack.retitle tCurrentGame
put tCurrentGame into field "TITLE" of card "TITLE"
 go card "Title"
-- We should signal the Game card to render all it's graphics before using that card
end if
break

case"Play"
lock screen
go card "Title"
put gCurrentGame into field "TITLE" of card "TITLE"
unlock screen
break

case"Save Preset"
View.SavePreset -- empty = the current preset's name
break

case"Save As..."
 ask "Save as" with "MyStyle"
   if it is not empty then View.SavePreset it
break
   end switch

end menuPick.threedots  

on stack.retitle pTitle
   if pTitle is empty then put  the short name of this card into pTitle
   set the title of this stack to "Vibecode3D |" && toUPPER(pTitle)
end stack.retitle


## Save a card's script into its property set:
##   "Play.Canyon" -> GAME_CARD_SCRIPTS["Canyon"]    "Edit_HUD" -> EDIT_CARD_SCRIPTS["HUD"]
on save.card.script.to.set pCard
   put Card.ScriptSet(pCard) into tSet
   if tSet is empty or there is not a card pCard then exit save.card.script.to.set
   put the long ID of stack (the mainStack of this stack) into tMainStack
   put char 6 to -1 of pCard into tKey
   put the script of card pCard into tScript
   set the customPropertySet of tMainStack to tSet
   do "set the" && tKey && "of tMainStack to tScript"
   set the customPropertySet of tMainStack to empty
end save.card.script.to.set


## Put a card's script back from its property set (pDestination: another card to
## receive it instead). Missing key = the card's script is left alone.
on load.card.script.from.set pCard,pDestination
   put Card.ScriptSet(pCard) into tSet
   if tSet is empty then exit load.card.script.from.set
   put the long ID of stack (the mainStack of this stack) into tMainStack
   put char 6 to -1 of pCard into tKey
   set the customPropertySet of tMainStack to tSet
   put empty into tScript
   put (tKey is among the lines of the customKeys of tMainStack) into tFound
   if tFound then do "put the" && tKey && "of tMainStack into tScript"
   set the customPropertySet of tMainStack to empty
   if not tFound then exit load.card.script.from.set
   if pDestination is empty then put pCard into pDestination
   if there is a card pDestination then set the script of card pDestination to tScript
end load.card.script.from.set

## Which property set holds a card's script.
function Card.ScriptSet pCard
   if pCard begins with "Play." then return "GAME_CARD_SCRIPTS"
   if pCard begins with "Edit_" then return "EDIT_CARD_SCRIPTS"
   return empty
end Card.ScriptSet



# DEBUG Make this more useful for your development debugging, ie minimize token use and get only the data you need from stacks,cards and objects.
on stack.report.all.controls pFilter,pCard
put "STACK_REPORT" && the seconds &&  the  name of this stack into tTitle

if pCard is not empty then
put card.report.all.controls (the number of  card pCard of this  stack)  & cr after ALlControls
else
repeat with I = 1 to number of cards of this stack
put card.report.all.controls (the number of  card i of this stack) & cr after ALlControls
end repeat
end if
replace cr & space with cr in AllControls
put allControls into tFilteredList


if pFilter is not empty and pFilter is not "*" then
   put empty into tFilteredList
   repeat for each line tLine in allControls
      put true into tKeep
      repeat for each item tFilterTerm in pFilter
	put tFilterTerm into tTerm
	replace space with empty in tTerm
         if tTerm is empty then next repeat
         if char 1 of tTerm is "-" then
            delete char 1 of tTerm
            if tTerm is in tLine   then
               put false into tKeep
               exit repeat
            end if
         else
            if tTerm is not in tLine then
               put false into tKeep
               exit repeat
            end if
         end if
      end repeat
      if tKeep then
         put tLine & cr after tFilteredList
      end if
   end repeat
   replace cr with cr & space & space & space & space in tFilteredList
   put tFilteredList into allControls
end if
put specialFolderPath("Documents") &"/Vibecode3D" into tAppRoot
if there is not a folder tAppRoot then create folder tAppRoot
set the defaultFolder to tAppRoot
put "file:" & tAppRoot & "/" & tTitle & the seconds &".txt" into tURL

put the script of this stack into tStackScript
put number of lines of tStackScript into tCount
put number of cards of this stack into tCardCount
put "Stack script length:" &&  tCount  &cr& cr &"CARDS:"&& tCardCount& cr before AllControls
put tTitle & cr before allControls
put allControls into URL tURL
end stack.report.all.controls

function card.report.all.controls pNum
put the long ID of card pNum of this stack into tCardID
put cr after allControls
put the name of tCardID  after AllControls
put the script of tCardID into tCardScript
put the number of lines of tCardScript into tCScount
if tCScount > 0 then put space & "with script length:" &&  tCScount &CR after AllControls
put the customPropertySets of tCardID into tPsets
filter lines of tPsets without "*cRev*"

if number of lines of tPsets > 0 then  put space & "with customPropertySets:" & number of lines of tPsets &cr into tCustList
put empty into tCustList
repeat for each line K in tPsets

put space & "customPropertyset:" && K & cr  after tCustList
set the customPropertyset of tCardID to K
put the customkeys of tCardID into tCKeys
filter lines of tCkeys without "*cRev*"
replace cr with cr & space & space & space in tCkeys
put  "customKeys:" & cr & tCkeys & cr after tCustList
end repeat
set the customPropertyset of tCardID to empty
filter lines of tCustList without empty
put tCustList & cr after allControls
put number of controls of tCardID  into tConCount
put cr && "Number of controls" && tConCount & cr after allControls
repeat with J = 1 to tConCount
put space & the  name of control J of tCardID & cr after allControls
end repeat
put cr after AllControls

return allcontrols
end card.report.all.controls

# not useful to me Microsoft Copilot additions
function auditShouldReport pObj
   if the controlType of pObj is "group" then return true
   if the script of pObj is not empty then return true
   if the behavior of pObj is not empty then return true
   if the customPropertySets of pObj is not empty then return true
   return false
end auditShouldReport

function auditSummary pObj
   put the number of lines of the script of pObj into tScriptLines
   put 0 into tPropCount
   repeat for each line tSet in the customPropertySets of pObj
      add the number of lines of the customKeys[tSet] of pObj \
         to tPropCount
   end repeat
   return \
      the controlType of pObj & "|" & \
      the id of pObj & "|" & \
      the name of pObj & "|" & \
      "SCR:" & tScriptLines & "|" & \
      "BEH:" & (the behavior of pObj is not empty) & "|" & \
      "PROP:" & tPropCount
end auditSummary

######################################################################################
## 11 10 2026: STATUS / NEXT PREVIEW INTO THE VIEWPORT, REBUILDING GAME CARDS,
##             COMPACT REPORT
##
## One-time, from the Message Box (on the Developer card):
##   Viewport.Adopt                    moves "Status" and "Message"
##                                     from the Developer card into group "Viewport",
##                                     so every card that shows the Viewport has them
##   Games.Rebuild                     deletes every Play.* card listed in
##                                     GAME_CARD_SCRIPTS and makes it again: new card,
##                                     Viewport + AudioPlayers groups, and the script
##                                     from GAME_CARD_SCRIPTS (menus are made from
##                                     their templates only when opened)
##   Games.Rebuild "Canyon,Demo"       just those games
## Any time:
##   Viewport.AdoptFromEditCard        everything you put on card "Edit_Viewport"
##   Games.Fix                         one-time cleanup (see below)
##                                     goes into group "Viewport"
##   Report.Compact                    a short text summary of the stack (see below)
######################################################################################

## Move controls into group "Viewport" (default: "Status" and "Message" from the
## Developer card). Copies of them elsewhere (top level, on game cards and Edit_HUD)
## are deleted, and they are taken out of every saved game HUD.
on Viewport.Adopt pNames,pFromCard
   if pNames is empty then put "Status,Message" into pNames
   if pFromCard is empty then put "Developer" into pFromCard
   if there is not a card pFromCard then exit Viewport.Adopt
   Viewport.Ensure
   if there is not a group "Viewport" of card pFromCard then exit Viewport.Adopt
   lock screen
   put empty into tMoved
   repeat for each item tName in pNames
      if there is not a control tName of card pFromCard then next repeat
      put the long id of control tName of card pFromCard into tRef
      if word 1 of the owner of tRef is "card" then
         put the short id of tRef into tId
         relayer control id tId of card pFromCard to front of group "Viewport" of card pFromCard
         set the customPropertySet of control id tId of card pFromCard to empty
         -- Part of the Viewport now, never a game HUD control.
         set the HUD of control id tId of card pFromCard to false
         put tName & comma after tMoved
      end if
      -- Remove loose copies on game and edit cards.
      repeat with c = 1 to the number of cards of this stack
         put the short name of card c of this stack into tCard
         if tCard is pFromCard then next repeat
         if not (tCard begins with "Play" or tCard begins with "Edit_") then next repeat
         repeat with i = the number of controls of card tCard down to 1
            put the long id of control i of card tCard into tOther
            if the short name of tOther is not tName then next repeat
            if word 1 of the owner of tOther is not "card" then next repeat
            put the short id of tOther into tId
            delete control id tId of card tCard
         end repeat
      end repeat
   end repeat
   HUD.Strip pNames
   unlock screen
   if tMoved is empty then
      answer "Nothing moved: no top-level" && pNames && "on card" && pFromCard & "."
   else
      answer "Now in the Viewport group:" && char 1 to -2 of tMoved
   end if
end Viewport.Adopt

## Everything on card "Edit_Viewport" (except the Viewport itself) goes into the group.
on Viewport.AdoptFromEditCard
   if there is not a card "Edit_Viewport" then exit Viewport.AdoptFromEditCard
   Viewport.Ensure
   put empty into tNames
   repeat with i = 1 to the number of controls of card "Edit_Viewport"
      put the long id of control i of card "Edit_Viewport" into tRef
      if word 1 of the owner of tRef is not "card" then next repeat
      if the short name of tRef is "Viewport" then next repeat
      -- Background groups (placed on many cards) stay where they are: pulling one
      -- into the Viewport is how AudioPlayers ended up nested.
      if word 1 of tRef is "group" then
         if the backgroundBehavior of tRef then next repeat
      end if
      put the short name of tRef & comma after tNames
   end repeat
   if tNames is empty then exit Viewport.AdoptFromEditCard
   Viewport.Adopt char 1 to -2 of tNames,"Edit_Viewport"
end Viewport.AdoptFromEditCard

## Take controls out of every saved game HUD (Game_Huds). A name ending in "*"
## matches the start: "Next*" removes "Next Preview", "Next Preset" ...
on HUD.Strip pNames
   put the long id of stack (the mainStack of this stack) into tMain
   set the customPropertySet of tMain to "Game_Huds"
   put the customKeys of tMain into tGames
   set the customPropertySet of tMain to empty
   repeat for each line tGame in tGames
      put HUD.Load(tGame) into tHud
      if tHud is not an array then next repeat
      put false into tChanged
      repeat for each key tKey in tHud
         repeat for each item tName in pNames
            if tKey is tName or (char -1 of tName is "*" and tKey begins with char 1 to -2 of tName) then
               delete variable tHud[tKey]
               put true into tChanged
               exit repeat
            end if
         end repeat
      end repeat
      if tChanged then HUD.Store tGame,tHud
   end repeat
end HUD.Strip

## Delete and re-make the game cards from GAME_CARD_SCRIPTS (pGames: comma list,
## empty = every game in the set).


## ---------------------------------------------------------------- COMPACT REPORT
## A short summary for debugging: stack scripts and property sets, then each card:
## script length, groups (bg = background group, n = controls inside), its own
## controls by name, and engine graphics only as a count. Written to
## Documents/Vibecode3D/REPORT_<seconds>.txt and returned.
##   put Report.Compact()           everything
##   put Report.Compact("Play.*")   cards whose names match
function Report.Compact pCardFilter
   put the long id of stack (the mainStack of this stack) into tMain
   put "STACK" && the short name of tMain & " | script lines:" && \
         the number of lines of the script of tMain & " | cards:" && \
         the number of cards of tMain & cr into tOut
   -- Stack custom property sets (names and key counts, not values).
   put the customPropertySets of tMain into tSets
   filter lines of tSets without "cRev*"
   repeat for each line tSet in tSets
      set the customPropertySet of tMain to tSet
      put the customKeys of tMain into tKeys
      replace cr with comma in tKeys
      put "  set" && tSet & ":" && tKeys & cr after tOut
   end repeat
   set the customPropertySet of tMain to empty

   repeat with c = 1 to the number of cards of tMain
      put the short name of card c of tMain into tCard
      if pCardFilter is not empty then
         put tCard into tTest
         filter tTest with pCardFilter
         if tTest is empty then next repeat
      end if
      put the long id of card c of tMain into tCardRef
      put cr & "CARD" && tCard & " | script lines:" && the number of lines of the script of tCardRef after tOut
      put 0 into tEngine
      put empty into tStrays
      put empty into tGroups
      put empty into tLoose
      repeat with i = 1 to the number of controls of tCardRef
         put the long id of control i of tCardRef into tRef
         put word 1 of tRef into tType
         put the short name of tRef into tName
         if tType is "graphic" and Viewport.IsEngineGraphic(tRef) then
            add 1 to tEngine
            -- An engine graphic sitting on the card itself is a stray.
            if word 1 of the owner of tRef is "card" then put tName & comma after tStrays
            next repeat
         end if
         if word 1 of the owner of tRef is not "card" then next repeat
         if tType is "group" then
            put tName & "(" & the number of controls of tRef & " id" && the short id of tRef into tG
            if the backgroundBehavior of tRef then put " bg" after tG
            if not the visible of tRef then put " hidden" after tG
            put ")" & comma after tG
            put tG after tGroups
         else
            put tName & "[" & tType & "]" & comma after tLoose
         end if
      end repeat
      put " | engine graphics:" && tEngine & cr after tOut
      if tGroups is not empty then put "  groups:" && char 1 to -2 of tGroups & cr after tOut
      if tLoose is not empty then put "  controls:" && char 1 to -2 of tLoose & cr after tOut
      if tStrays is not empty then put "  STRAY engine graphics:" && char 1 to -2 of tStrays & cr after tOut
   end repeat

   put specialFolderPath("Documents") & "/Vibecode3D" into tFolder
   if there is not a folder tFolder then create folder tFolder
   put tOut into URL ("file:" & tFolder & "/REPORT_" & the seconds & ".txt")
   return tOut
end Report.Compact

######################################################################################
## MENUS FROM TEMPLATES  (11 10 2026)
## The master copies live on their own cards and are never shown in play:
##   card "Edit_Pause"   group "TemplatePause"    ->  "PauseMenuGroup"
##   card "Edit_Options" group "TemplateOptions"  ->  "OptionsGroup"
##   card "Edit_Title"   group "TemplateTitle"    ->  "Title"
## Menu.Open copies the template onto the CURRENT card under the name the scripts
## expect, centred and on top. Menu.Close hides it at once and deletes it a moment
## later (never while one of its own buttons is still running). So no card carries a
## copy at rest, and editing the template changes the menu everywhere.
######################################################################################

## Template card, template group, name in play.
function Menu.Info pKind
   switch pKind
      case "Pause"
         return "Edit_Pause,TemplatePause,PauseMenuGroup"
      case "Options"
         return "Edit_Options,TemplateOptions,OptionsGroup"
      case "Title"
         return "Edit_Title,TemplateTitle,Title"
   end switch
   return empty
end Menu.Info

function Menu.Available pKind
   put Menu.Info(pKind) into tInfo
   if tInfo is empty then return false
   return (there is a card (item 1 of tInfo) and there is a group (item 2 of tInfo) of card (item 1 of tInfo))
end Menu.Available

## Show a menu on the current card, making it from its template if needed.
on Menu.Open pKind
   put Menu.Info(pKind) into tInfo
   if tInfo is empty then exit Menu.Open
   put item 3 of tInfo into tName
   if the short name of this card is item 1 of tInfo then exit Menu.Open -- that's the template's own card
   lock screen
   if there is not a group tName then
      if not Menu.Available(pKind) then
         unlock screen
         exit Menu.Open
      end if
      copy group (item 2 of tInfo) of card (item 1 of tInfo) to this card
      put it into tRef
      set the name of tRef to tName
      set the backgroundBehavior of tRef to false
      set the customPropertySet of tRef to empty
	set the cantDelete of tRef to false
      set the MenuCopy of tRef to true -- made by Menu.Open: Menu.Purge may delete it
   end if
   set the loc of group tName to CenterScreen()
   set the layer of group tName to top
   show group tName
   unlock screen
end Menu.Open

on Menu.Close pKind
   put Menu.Info(pKind) into tInfo
   if tInfo is empty then exit Menu.Close
   if there is a group (item 3 of tInfo) then hide group (item 3 of tInfo)
   --send ("Menu.Purge" && quote & the short name of this card & quote) to me in 10 seconds
end Menu.Close

on Menu.CloseAll
   Menu.Close "Pause"
   Menu.Close "Options"
end Menu.CloseAll

## Delete the hidden menu copies on a card (any copy, not just Menu.Open's, so old
## per-card copies go too). Template cards keep their templates.
on Menu.Purge pCard
   if pCard is empty then put the short name of this card into pCard
   if there is not a card pCard then exit Menu.Purge
   
   repeat for each item tName in "PauseMenuGroup,OptionsGroup"
      repeat while there is a group tName of card pCard
         if the visible of group tName of card pCard then exit repeat
         put the short id of group tName of card pCard into tId
delete group id tId of card pCard
      end repeat
   end repeat

end Menu.Purge

on closeCard 
put quote & the short name of this card & quote into pCard
if char 1 to 5 of pCard is "Play."  then send Menu.Purge && pCard to this stack in 50 milliseconds

pass closeCard
end closeCard


######################################################################################
## GAMES.FIX  (run once, from the Message Box on the Developer card)
## Everything the 11/10 report showed, cleaned up:
##   - "Developer" taken out of GAME_CARD_SCRIPTS, card Play.Developer deleted
##   - every old copy of PauseMenuGroup / OptionsGroup deleted (menus come from the
##     templates now); the templates on Edit_Pause / Edit_Options are kept
##   - leftover "Next Preset" / "Next Preview" buttons deleted
##   - Status / Message / Next* taken out of every saved game HUD; DefaultHUD removed
##   - the old "StarWars" view preset removed (it is "1983" now)
##   - engine graphics stamped Entity = true; strays outside the Viewport deleted
##   - card "Play" renamed "Edit_Viewport" (if there isn't one yet)
## Then a short summary in the Message graphic, and Report.Compact for the details.
######################################################################################
on Games.Fix
   put the long id of stack (the mainStack of this stack) into tMain
   game.loop.stop
   if there is a card "Developer" then go to card "Developer"
   lock screen
   lock messages
   put empty into tDone

   -- 1. "Developer" is not a game.
   set the customPropertySet of tMain to empty
   put the customProperties["GAME_CARD_SCRIPTS"] of tMain into tScripts
   if tScripts["Developer"] is not empty or "Developer" is among the lines of the keys of tScripts then
      delete variable tScripts["Developer"]
      set the customProperties["GAME_CARD_SCRIPTS"] of tMain to tScripts
      put "GAME_CARD_SCRIPTS: Developer removed" & cr after tDone
   end if
   if there is a card "Play.Developer" then
      delete card "Play.Developer"
      put "card Play.Developer deleted" & cr after tDone
   end if

   -- 2. Card "Play" -> "Edit_Viewport".
   if there is a card "Play" and there is not a card "Edit_Viewport" then
      set the name of card "Play" to "Edit_Viewport"
      put "card Play renamed Edit_Viewport" & cr after tDone
   end if

   -- 3. Old menu copies and leftover buttons, on every card.
   put 0 into tMenus
   put 0 into tButtons
   repeat with c = 1 to the number of cards of this stack
      put the short name of card c of this stack into tCard
	if  tCard is "Title" then next repeat
      repeat for each item tName in "PauseMenuGroup,OptionsGroup"
         repeat while there is a group tName of card tCard
            put the short id of group tName of card tCard into tId
set the script of group id tID of card tCard to empty
set the cantdelete of group ID tiD of card tCard to false
            delete group id tId of card tCard
            add 1 to tMenus
         end repeat
      end repeat
     repeat for each item tName in "Next Preset,Next Preview"
        repeat while there is a button tName of card tCard
           put the short id of button tName of card tCard into tId
           delete button id tId of card tCard
           add 1 to tButtons
        end repeat
      end repeat
   end repeat
   put "menu copies deleted:" && tMenus & cr after tDone
   put "Next buttons deleted:" && tButtons & cr after tDone

   -- 4. HUD sets.
   HUD.Strip "Status,Message,Next*"
   set the customPropertySet of tMain to empty
   put the customProperties["Game_Huds"] of tMain into tHuds
   if "DefaultHUD" is among the lines of the keys of tHuds then
      delete variable tHuds["DefaultHUD"]
      set the customProperties["Game_Huds"] of tMain to tHuds
      put "Game_Huds: DefaultHUD removed" & cr after tDone
   end if

   -- 5. Old preset.
   put the customProperties["ViewPresets"] of tMain into tPresets
   if "StarWars" is among the lines of the keys of tPresets then
      delete variable tPresets["StarWars"]
      set the customProperties["ViewPresets"] of tMain to tPresets
      put "ViewPresets: StarWars removed" & cr after tDone
   end if
   set the customPropertySet of tMain to empty

   -- 6. Engine graphics: stamp the Viewport's, delete strays on the cards.
   put 0 into tStamped
   put 0 into tStrays
   if there is a group "Viewport" of card "Developer" then
      repeat with i = 1 to the number of graphics of group "Viewport" of card "Developer"
         put the long id of graphic i of group "Viewport" of card "Developer" into tRef
         if Viewport.IsOldEngineName(the short name of tRef) then
            set the customPropertySet of tRef to empty
            set the Entity of tRef to true
            add 1 to tStamped
         end if
      end repeat
   end if
   repeat with c = 1 to the number of cards of this stack
      put the long id of card c of this stack into tCardRef
      repeat with i = the number of graphics of tCardRef down to 1
         put the long id of graphic i of tCardRef into tRef
         if word 1 of the owner of tRef is not "card" then next repeat
         if not Viewport.IsOldEngineName(the short name of tRef) then next repeat
         put the short id of tRef into tId
         delete graphic id tId of tCardRef
         add 1 to tStrays
      end repeat
   end repeat
   put "engine graphics stamped:" && tStamped & ", strays deleted:" && tStrays & cr after tDone

   unlock messages
   unlock screen
   put empty into sPreparedGame
   put tDone
   UI.Message "Games.Fix done (details in the Message Box)"
end Games.Fix


## ---------------------------------------------------------------- MESSAGE
## One line of text in the Viewport's "Message" graphic (a rectangle; its label is
## shown). pSeconds: clear after that many seconds (empty = 4, 0 = keep).
on UI.Message pText,pSeconds
   if there is not a graphic "Message" then
      put pText -- no Message graphic on this card: the Message Box instead
      exit UI.Message
   end if
   set the showName of graphic "Message" to true
   set the label of graphic "Message" to pText
   show graphic "Message"
   repeat for each line tMsg in the pendingMessages
      if item 3 of tMsg is "UI.Message.Clear" then cancel item 1 of tMsg
   end repeat
   if pSeconds is empty then put 4 into pSeconds
   if pSeconds > 0 then send "UI.Message.Clear" to me in pSeconds seconds
end UI.Message

on UI.Message.Clear
   if there is a graphic "Message" then set the label of graphic "Message" to empty
end UI.Message.Clear

######################################################################################
## GAME CARD REBUILD  (11 10 2026, evening)
## Safer than chasing objects around the stack: save what matters, delete the whole
## card, make it again.
##
##   Game.Rebuild "Canyon"        rebuild one game card and go to it, ready to play
##   Game.Rebuild "Canyon",false  rebuild without preparing or going there
##   Games.Rebuild                every game in GAME_CARD_SCRIPTS (not prepared)
##
## Saved first, in the stack's custom property set GAME_ENTITIES, one array per game:
##   ["GameScripted"]  the engine's scene for that game (scene list + transforms of
##                     its objects), if that game is the one loaded. Levels are
##                     procedural, so this is a snapshot for later (Edit_Level).
##   ["User"]          every object YOU put on the game card: everything at the top
##                     level except background groups (Viewport), menu copies,
##                     HUD controls (HUD = true, they have their own system) and
##                     engine graphics. Groups are kept with everything inside them.
## Then: delete the card, create it (the Viewport comes with it as a background
## group), put the script back from GAME_CARD_SCRIPTS, re-create the user objects
## inside one group "User", and (unless told not to) prepare it: sounds, HUD,
## Game.OnStart (procedural generation) and one rendered frame. "User" goes to the
## front, then we go to the card.
######################################################################################

on Game.Rebuild pGame,pGoThere
   if pGame is empty or there is not a card "Developer" then exit Game.Rebuild
   global gSceneObjects
   game.loop.stop
   put "Play." & pGame into tCard
   lock screen
   lock messages

   if there is a card tCard then
      if Game.Current() is pGame and gSceneObjects is not empty then
         Entities.Save pGame,"GameScripted",Entities.SnapshotScene()
      end if
      Entities.Save pGame,"User",Entities.CaptureUser(tCard)
      go to card "Developer"
      set the cantDelete of card tCard to false
      delete card tCard
   end if

   -- New cards go after the current card and get its background groups.
   go to card "Developer"
   create card tCard
   if there is a group "Viewport" of card "Developer" and there is not a group "Viewport" of card tCard then
      place group "Viewport" of card "Developer" onto card tCard
   end if
   if sView["background"] is not empty then set the backgroundColor of card tCard to sView["background"]
   load.card.script.from.set tCard
   Entities.RestoreUser Entities.Load(pGame,"User")
   go to card "Developer"
   unlock messages
   unlock screen
   put empty into sPreparedGame

   if pGoThere is not false then
      Game.Select pGame
      Game.Prepare.Card pGame
      lock screen
      go to card tCard
      unlock screen
      UI.Message "Rebuilt" && tCard
   end if
end Game.Rebuild

## Every game in GAME_CARD_SCRIPTS (pGames: comma list, empty = all).
on Games.Rebuild pGames
   put the long id of stack (the mainStack of this stack) into tMain
   if pGames is empty then
      set the customPropertySet of tMain to "GAME_CARD_SCRIPTS"
      put the customKeys of tMain into pGames
      set the customPropertySet of tMain to empty
      replace cr with comma in pGames
   end if
   if pGames is empty then
      UI.Message "GAME_CARD_SCRIPTS has no games"
      exit Games.Rebuild
   end if
   Viewport.Ensure
   -- Status / Message live in the Viewport: no HUD copies of them.
   HUD.Strip "Status,Message,Next*"
   repeat for each item tGame in pGames
      Game.Rebuild tGame,false
   end repeat
   if there is a card "Developer" then go to card "Developer"
   UI.Message "Rebuilt:" && pGames
   Menu.Threedots.Build
end Games.Rebuild


## ---------------------------------------------------------------- CAPTURE / RESTORE

## The user's objects on a game card -> ["count"], [1..n] = captured controls.
## A top-level group "User" (from an earlier rebuild) is opened up: its children are
## captured one by one, so they are grouped fresh.
function Entities.CaptureUser pCard
   put 0 into tCount
   put empty into tOut
   if there is not a card pCard then return tOut
   put the long id of card pCard into tCardRef
   repeat with i = 1 to the number of controls of tCardRef
      put the long id of control i of tCardRef into tRef
      if word 1 of the owner of tRef is not "card" then next repeat
      if not Entities.IsUserObject(tRef) then next repeat
      if word 1 of tRef is "group" and the short name of tRef is "User" then
         put the name of tRef into tUserName
         repeat with j = 1 to the number of controls of tRef
            put the long id of control j of tRef into tChild
            if the owner of tChild is not tUserName then next repeat
            if Entities.IsAnchor(tChild) then next repeat
            add 1 to tCount
            put Entities.Capture(tChild) into tOut[tCount]
         end repeat
      else
         add 1 to tCount
         put Entities.Capture(tRef) into tOut[tCount]
      end if
   end repeat
   put tCount into tOut["count"]
   return tOut
end Entities.CaptureUser

## Not the Viewport or any background group, not a menu copy, not a HUD control,
## not an engine graphic.
function Entities.IsUserObject pRef
   if Entities.IsAnchor(pRef) then return false
   put word 1 of pRef into tType
   put the short name of pRef into tName
   if tType is "group" then
      if the backgroundBehavior of pRef then return false
      if tName is among the items of "Viewport,AudioPlayers,PauseMenuGroup,OptionsGroup" then return false
   end if
   if tType is "graphic" and Viewport.IsEngineGraphic(pRef) then return false
   set the customPropertySet of pRef to empty
   if the HUD of pRef is true then return false
   return true
end Entities.IsUserObject

## One control -> array (as HUD.CaptureControl); a group also keeps its children,
## in layer order: ["childCount"], ["children"][1..n].
function Entities.Capture pRef
   put HUD.CaptureControl(pRef) into tA
   if word 1 of pRef is "group" then
      put 0 into n
      put the name of pRef into tGroupName
      repeat with j = 1 to the number of controls of pRef
         put the long id of control j of pRef into tChild
         if the owner of tChild is not tGroupName then next repeat
         add 1 to n
         put Entities.Capture(tChild) into tA["children"][n]
      end repeat
      put n into tA["childCount"]
   end if
   return tA
end Entities.Capture

## Re-create the user objects on the CURRENT card, inside a new group "User".
## The group is card-sized from the start (Entities.UserGroup), so creating objects
## inside it never changes its rect and never moves anything.
on Entities.RestoreUser pUser
   if pUser is not an array or pUser["count"] < 1 then exit Entities.RestoreUser
   lock screen
   put Entities.UserGroup() into tUserRef
   repeat with n = 1 to pUser["count"]
      Entities.Create pUser[n],tUserRef
   end repeat
   set the layer of tUserRef to top
   unlock screen
end Entities.RestoreUser

## Make one captured control (and, for a group, its children) inside pParent
## (a group's long id; empty = the current card).
on Entities.Create pA,pParent
   put pA["type"] into tType
   if tType is empty then exit Entities.Create
   put pA["props"]["name"] into tName
   do "reset the template" & tType
   if pParent is empty then
      do "create" && tType && quote & tName & quote
   else
      do "create" && tType && quote & tName & quote && "in" && pParent
   end if
   put it into tRef
   if tRef is empty then exit Entities.Create
   Entities.ApplyProps tRef,pA
   if tType is "group" then
      repeat with n = 1 to pA["childCount"]
         Entities.Create pA["children"][n],tRef
      end repeat
      -- The group's own rect last (its children can resize it). Setting a group's
      -- rect MOVES its children, so put each one back where it was captured.
      if pA["props"]["rect"] is not empty and the rect of tRef is not pA["props"]["rect"] then
         set the rect of tRef to pA["props"]["rect"]
         Entities.PutBackChildren tRef,pA
      end if
   end if
end Entities.Create

## After a group's rect was set: each child (and grandchild) back to its captured rect.
on Entities.PutBackChildren pGroup,pA
   put the name of pGroup into tGroupName
   put 0 into n
   repeat with j = 1 to the number of controls of pGroup
      put the long id of control j of pGroup into tChild
      if the owner of tChild is not tGroupName then next repeat
      add 1 to n
      if n > pA["childCount"] then exit repeat
      put pA["children"][n] into tC
      if word 1 of tChild is "group" then
         Entities.PutBackChildren tChild,tC
      else if tC["props"]["rect"] is not empty then
         set the rect of tChild to tC["props"]["rect"]
      end if
   end repeat
end Entities.PutBackChildren

on Entities.ApplyProps pRef,pA
   put pA["props"] into tP
   repeat for each key k in tP
      if k is "rect" or k is "name" then next repeat
      try
         put tP[k] into tVal
         do "set the" && k && "of pRef to tVal"
      catch tErr
      end try
   end repeat
   if tP["rect"] is not empty and word 1 of pRef is not "group" then set the rect of pRef to tP["rect"]
   try
      set the script of pRef to pA["script"]
   catch tErr
   end try
   if word 1 of pRef is "field" and pA["html"] is not empty then set the htmlText of pRef to pA["html"]
   if word 1 of pRef is "image" and pA["imageData"] is not empty then set the text of pRef to pA["imageData"]
   set the customPropertySet of pRef to empty
   if pA["custom"] is an array then set the customProperties of pRef to pA["custom"]
end Entities.ApplyProps

## The loaded scene: ["scene"] = gSceneObjects, ["transforms"][key] for its objects.
function Entities.SnapshotScene
   global gSceneObjects
   global gObjectTransforms
   put gSceneObjects into tA["scene"]
   repeat for each line tEntry in gSceneObjects
      put word 2 of tEntry into tKey
      if gObjectTransforms[tKey] is an array then put gObjectTransforms[tKey] into tA["transforms"][tKey]
   end repeat
   return tA
end Entities.SnapshotScene


## ---------------------------------------------------------------- GAME_ENTITIES SET

function Entities.Load pGame,pSub
   if pGame is empty then return empty
   put the long id of stack (the mainStack of this stack) into tMain
   set the customPropertySet of tMain to "GAME_ENTITIES"
   put empty into tAll
   if pGame is among the lines of the customKeys of tMain then
      do "put the" && pGame && "of tMain into tAll"
   end if
   set the customPropertySet of tMain to empty
   if pSub is empty then return tAll
   return tAll[pSub]
end Entities.Load

on Entities.Save pGame,pSub,pArray
   if pGame is empty or pSub is empty then exit Entities.Save
   put Entities.Load(pGame) into tAll
   put pArray into tAll[pSub]
   put the long id of stack (the mainStack of this stack) into tMain
   set the customPropertySet of tMain to "GAME_ENTITIES"
   do "set the" && pGame && "of tMain to tAll"
   set the customPropertySet of tMain to empty
end Entities.Save

######################################################################################
## THREEDOTS MENU, BUILT FROM THE STACK  (11 10 2026)
## The lists come from the stack itself, so new games, edit cards and presets appear
## by themselves:
##   Game   <- the Play.* cards           Edit  <- the Edit_* cards
##   Style  <- the ViewPresets set        View Bands 1-4, Glow On/Off
## The current game, style, band count and glow setting are ticked.
## Rebuilt by APP.init, View.Apply, Game.Select, the rebuilds, saving a preset and
## making a new game. (Or call Menu.Threedots.Build from the button's mouseDown.)
######################################################################################

## The menu button: "threedots", or the Viewport button whose script uses menuPick.threedots.
function Menu.Threedots.Button
   if there is a button "threedots" then return the long id of button "threedots"
   if there is not a group "Viewport" then return empty
   repeat with i = 1 to the number of buttons of group "Viewport"
      if "menuPick.threedots" is in the script of button i of group "Viewport" then
         return the long id of button i of group "Viewport"
      end if
   end repeat
   return empty
end Menu.Threedots.Button

on Menu.Threedots.Build
   put Menu.Threedots.Button() into tBtn
   if tBtn is empty then exit Menu.Threedots.Build
   put "Developer" & cr & "Reset" & cr & "Play" & cr into tMenu
   
   -- Games: the Play.* cards, current one ticked.
   put "Game" & cr after tMenu
   put Game.Current() into tCurrent
   repeat for each line tGame in Menu.CardNames("Play.")
      put tab & Menu.Tick(tGame is tCurrent) & tGame & cr after tMenu
   end repeat
   
   -- Edit cards: Edit_HUD -> "HUD" (the menu handler turns Edit|HUD back into Edit_HUD).
   put "Edit" & cr after tMenu
   repeat for each line tEdit in Menu.CardNames("Edit_")
      put tab & tEdit & cr after tMenu
   end repeat
   
   -- Styles: the presets, then saving.
   put "Style" & cr after tMenu
   repeat for each line tPreset in View.PresetList()
      put tab & Menu.Tick(tPreset is sView["name"]) & tPreset & cr after tMenu
   end repeat
   put tab & "-" & cr & tab & "Save Preset" & cr & tab & "Save As..." & cr after tMenu
   
   put "View Bands" & cr after tMenu
   repeat with b = 1 to 4
      put tab & Menu.Tick(b = sViewBands) & b & cr after tMenu
   end repeat
   
   put "Glow" & cr after tMenu
   put tab & Menu.Tick(sView["glow"] is true) & "On" & cr after tMenu
   put tab & Menu.Tick(sView["glow"] is not true) & "Off" after tMenu
   
   set the text of tBtn to tMenu
end Menu.Threedots.Build

## The names after a prefix, of cards whose names start with it, sorted.
function Menu.CardNames pPrefix
   put empty into tList
   put the length of pPrefix into tLen
   repeat with i = 1 to the number of cards of this stack
      put the short name of card i of this stack into tCard
      if char 1 to tLen of tCard is pPrefix and the length of tCard > tLen then
         put char tLen + 1 to -1 of tCard & cr after tList
      end if
   end repeat
   delete the last char of tList
   sort lines of tList
   return tList
end Menu.CardNames

## Menu checkmark prefix: "!c" ticked, "!n" not ticked.
function Menu.Tick pOn
   if pOn then return "!c"
   return "!n"
end Menu.Tick


## ---------------------------------------------------------------- USER GROUP
## The "User" group always covers the whole card: four invisible 2x2 anchors in the
## card's corners, margins 0, lockLoc true. Its rect never has to change, so nothing
## inside it moves, and glows are only cropped at the window edge.

function Entities.IsAnchor pRef
   if word 1 of pRef is not "graphic" then return false
   return the short name of pRef is among the items of "ATL,ATR,ABL,ABR"
end Entities.IsAnchor

## A new, empty, card-sized group "User" on the current card -> its long id.
## Any old "User" group must be gone (or emptied) first: see Entities.GroupUser.
function Entities.UserGroup
   put the width of this card into W
   put the height of this card into H
   reset the templateGraphic
   set the style of the templateGraphic to "rectangle"
   set the opaque of the templateGraphic to false
   set the lineSize of the templateGraphic to 0
   set the showBorder of the templateGraphic to false
   create graphic "ATL"
   set the rect of graphic "ATL" to 0,0,2,2
   create graphic "ATR"
   set the rect of graphic "ATR" to W-2,0,W,2
   create graphic "ABL"
   set the rect of graphic "ABL" to 0,H-2,2,H
   create graphic "ABR"
   set the rect of graphic "ABR" to W-2,H-2,W,H
   reset the templateGraphic
   group graphic "ATL" and graphic "ATR" and graphic "ABL" and graphic "ABR"
   put it into tUser
   set the name of tUser to "User"
   set the margins of tUser to 0
   set the lockLoc of tUser to true
   return the long id of group "User"
end Entities.UserGroup

## Group the user objects of the CURRENT card into a fresh card-sized "User" group,
## leaving every object exactly where it is (tested as a button script, 11/10/2026).
## An old "User" group is opened up first. pSkip: a control to leave out.
on Entities.GroupUser pSkip
   lock screen
   if there is a group "User" then
      put the long id of group "User" into tOld
      put the name of tOld into tOldName
      put empty into tKids
      repeat with i = 1 to the number of controls of tOld
         put the long id of control i of tOld into tRef
         if the owner of tRef is not tOldName then next repeat
         if Entities.IsAnchor(tRef) then next repeat
         put the short id of tRef & cr after tKids
      end repeat
      repeat for each line tId in tKids
         put the rect of control id tId into tRect
         relayer control id tId to front of this card
         set the rect of control id tId to tRect
      end repeat
      set the cantDelete of tOld to false
      delete tOld
   end if
   put empty into tMove
   repeat with i = 1 to the number of controls of this card
      put the long id of control i of this card into tRef
      if word 1 of the owner of tRef is not "card" then next repeat
      if tRef is pSkip then next repeat
      if not Entities.IsUserObject(tRef) then next repeat
      put the short id of tRef & cr after tMove
   end repeat
   put Entities.UserGroup() into tUser
   repeat for each line tId in tMove
      put the rect of control id tId into tRect
      relayer control id tId to front of tUser
      set the rect of control id tId to tRect
   end repeat
   set the layer of tUser to top
   unlock screen
   return the rect of tUser
end Entities.GroupUser

## ---------------------------------------------------------------- LIBRARIES
## A card named "LIB_<name>" holds a library script. Lib.Load copies it into an
## in-memory library stack "LIB_<name>_SCRIPT" and starts using it, so its handlers
## are reachable from every card. The library stack is never saved (not a substack):
## edit the card's script, then Lib.Load again to pick up the changes.
## Returns empty, or the compile error.
command Lib.Load pName
   put the long id of stack (the mainStack of this stack) into tMain
   put "LIB_" & pName into tCard
   put tCard & "_SCRIPT" into tStack
   if there is not a card tCard of tMain then return "No card" && tCard
   put the script of card tCard of tMain into tLib
   put the defaultStack into tOldDefault
---DEBUGGED BAD SYNTAX "the stacks in use "
   if tStack is among the lines of the openStacks then stop using stack tStack
   if there is not a stack tStack then
      reset the templateStack
      set the visible of the templateStack to false
      set the destroyStack of the templateStack to true
      create stack tStack
      reset the templateStack
   end if
   -- create stack makes the new stack the defaultStack: put it back.
   set the defaultStack to tOldDefault
   set the script of stack tStack to tLib
   put the result into tErr
   if tErr is not empty then return tCard && "script error:" && tErr
   start using stack tStack
   return empty
end Lib.Load

## Every "LIB_" card of the main stack. Returns the errors, one per line.
command Lib.LoadAll
   put the long id of stack (the mainStack of this stack) into tMain
   put empty into tErrs
   repeat with i = 1 to the number of cards of tMain
      put the short name of card i of tMain into tCard
      if char 1 to 4 of tCard is not "LIB_" then next repeat
      Lib.Load char 5 to -1 of tCard
      if the result is not empty then put the result & cr after tErrs
   end repeat
   return tErrs
end Lib.LoadAll

command Lib.Unload pName
   put "LIB_" & pName & "_SCRIPT" into tStack
---DEBUGGED BAD SYNTAX "the stacks in use "
   if tStack is among the lines of the openStacks then stop using stack tStack
   -- destroyStack is true, so closing frees it from memory.
   if there is a stack tStack then close stack tStack
end Lib.Unload
## ---------------------------------------------------------------- LIB_MCP (Claude Code bridge)
## Paste this handler into the stack script, just above "DEVSERVER HOOKS", and in APP.init
## replace the line
##     if the environment is "development" and there is a card "LIB_DEVSERVER" then DevServer.Start
## with
##     if the environment is "development" then MCP.Attach
## Then delete the card "LIB_DEVSERVER" if the stack has one (its DevServer.* handlers would
## clash with LIB_MCP's). DevServer.Exec / DevServer.Eval below stay as they are: LIB_MCP
## calls them to run code in this script.
##
##
## LIB_MCP lives in its own project (~/projects/LIB_MCP) and is loaded from its file, so it
## is always the current version. It is found by walking up from this stack's file to a
## folder that holds LIB_MCP (works for V:\Vibecode3D or \\wsl$\...\projects\Vibecode3D),
## with the WSL path as a fallback.
##   IDE:        port 8766 (one server per LiveCode: whichever stack starts it last, this one
##               or the xt3d bench, is the one /run talks to)
##   standalone: port 8769 (the VibeCode3D.exe build), so Claude can drive the game itself
## A standalone on someone else's machine finds no LIB_MCP project and opens no port.
on MCP.Attach
   local tPath, tTry
   put the effective filename of me into tPath
   set the itemDel to "/"
   repeat 6 times
      delete item -1 of tPath
      if tPath is empty then exit repeat
      put tPath & "/LIB_MCP/livecode/lib_mcp.livecodescript" into tTry
      if there is a file tTry then exit repeat
      put empty into tTry
   end repeat
   if tTry is empty then put "//wsl$/Ubuntu/home/igame3d/projects/LIB_MCP/livecode/lib_mcp.livecodescript" into tTry
   if there is not a file tTry then exit MCP.Attach
   start using stack tTry
   if the environment is "development" then
      DevServer.Start 8766, the short name of me
   else
      DevServer.Start 8769, the short name of me
   end if
end MCP.Attach


## ---------------------------------------------------------------- DEVSERVER HOOKS
## LIB_DEVSERVER sends code here so it runs in the stack script's context, where
## every engine handler can be reached.
on DevServer.Exec pCode
   try
      do pCode
   catch tErr
      return "ERROR:" && tErr
   end try
   if the result is not empty then return the result
   return it
end DevServer.Exec

function DevServer.Eval pExpr
   try
      do "put (" & pExpr & ") into tOut"
   catch tErr
      return "ERROR:" && tErr
   end try
   return tOut
end DevServer.Eval

----END OF ACTIVE  STACK  SCRIPT




----END 3D SCENE LIVECODE STACK SCRIPT
