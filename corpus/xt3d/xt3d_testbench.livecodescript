script "xt3dTestBench"
-- xt3d Test Bench: a script-only stack. In LiveCode: File > Open Stack, pick this
-- file. It builds its own controls each time it opens (nothing is saved but this
-- script), so edits to the file show up the next time it is opened.
--
-- WHEN CLOSING THIS STACK, CHOOSE "DON'T SAVE". This file is the source; saving from the
-- IDE writes LiveCode's in-memory copy back over it, which may be older.
--
-- Needs the xt3d extension loaded first (Extension Builder > open
-- C:\xt3d\extension\xt3d.lcb > Test).
--
--   drag on the view ...... orbit the camera
--   mouse wheel on view ... zoom
--   file list ............. click a model to load it; "Folder..." picks another folder
--   Dev server ............ lets Claude Code drive this bench; starts with it. It is the LIB_MCP
--                           library, found as a sibling project (../LIB_MCP); optional
--   Run checks ............ crash guards, pure functions, the test models, a frame copy;
--                           each step is written to C:/xt3d/bench_checks.txt before it runs
--
-- Layout numbers are in "logical" pixels (as at 100% display scaling). The stack's
-- scaleFactor cancels Windows display scaling so the 3D image is never stretched;
-- px() then scales every control back up so they keep their usual size.

constant kRaylibLog = "C:/xt3d/raylib_log.txt"
constant kCheckLog = "C:/xt3d/bench_checks.txt"
constant kTestModels = "C:/xt3d/test_models"
constant kModelTypes = "(?i)\.(glb|gltf|obj|iqm|m3d|vox)$"
constant kViewW = 720      -- view size in logical pixels
constant kViewH = 540
constant kPanelX = 730     -- left edge of the side panel
constant kPanelW = 250
constant kSample = 2       -- 2 = render at double size and shrink (smooth edges); 1 = off
constant kAnimFPS = 60     -- raylib samples glTF animations at 60 key frames a second
constant kSpin = 30        -- degrees a second when Spin is on
constant kFrameMS = 16     -- milliseconds between frames while something moves

-- view and GPU resources
-- sDirty: something changed and the view needs one new frame (see xbRedraw). The loop
-- runs only while Spin is on or an animation plays; otherwise the bench sleeps.
local sScale, sViewW, sViewH, sRunning, sFrameMsg, sDirty
local sTarget, sBig, sBigTexture, sCamera
-- the loaded model
local sModel, sModelPath, sFit, sLift
local sWireColor   -- set while a line-only model (the face card) is shown: draw only its lines, in this colour
local sModel2, sWireColor2   -- a second line-only model drawn with it (the face card's panel)
local sAnimFirst, sAnimCount, sAnim, sAnimFrames, sAnimFrame
-- camera orbit, spin, timing
local sYaw, sPitch, sDist, sAngle, sLastTick, sDragging, sDragX, sDragY
local sFrames, sFPSTick, sFPS
-- browsing and checks
local sFolder, sSettingSlider, sReport

-------------------------------------------------------------------- open / close

on preOpenStack
   set the defaultStack to the short name of me
   put the screenPixelScale into sScale
   if sScale is empty or sScale <= 0 then put 1 into sScale
   -- one stack unit = one screen pixel, so the 3D image is never stretched
   set the scaleFactor of me to 1 / sScale
   set the title of me to "xt3d Test Bench"
   set the resizable of me to false
   set the destroyStack of me to true   -- closing removes it from memory, so reopening reads the file
   set the width of me to px(kPanelX + kPanelW + 10)
   set the height of me to px(kViewH + 130)
   set the textSize of me to px(12)
   put px(kViewW) into sViewW
   put px(kViewH) into sViewH
   if sFolder is empty then put kTestModels into sFolder
   put 0 into sModel
   put 0 into sAnimCount
   put 0 into sAnimFrames
   put 0 into sLift
   put 1 into sFit
   xbBuildControls
   xbListFolder
   xbPlaceWindow
end preOpenStack

-- centre the window on the main screen; a script-only stack has no saved position,
-- and changing scaleFactor and size can leave it hanging off the screen
command xbPlaceWindow
   set the loc of me to the screenLoc
   if the top of me < 30 then set the top of me to 30
   if the left of me < 0 then set the left of me to 0
end xbPlaceWindow

on openStack
   local tError
   xbLoadXt3d
   try
      get xt3d_Version()
   catch tError
      put "The xt3d extension is not loaded." & return & return & \
            "Extension Builder > open C:\xt3d\extension\xt3d.lcb > Test," & return & \
            "then close and reopen this stack." into field "info"
      exit openStack
   end try
   xbPlaceWindow
   -- always on screen: a standalone build once opened it hidden
   if not the visible of me then show me
   -- the dev server (and its error log) starts with the bench; untick to stop it
   if not xbDevRunning() then xbDevServer true
   put 45 into sYaw
   put 25 into sPitch
   put 5 into sDist
   xbStartView
   put "Ready. " & xt3d_Version() & return & "Click a model in the list, or Run checks." & return & \
         "Dev server:" && xbDevRunning() & ". Errors go to C:/LIB_MCP/livecode_errors.txt" into field "info"
   -- the default card while Claude is connected: the face (the Face button brings it back)
   if xbDevRunning() then xbShowFace
end openStack

on closeStack
   xbStopView
   xbCancelPending
   set the scaleFactor of me to 1
end closeStack

-- cancel every message this stack still has queued (frame timers, redraws), so closing
-- leaves nothing behind that could keep the old copy in memory
command xbCancelPending
   local tLine, tLong
   put the long name of me into tLong
   repeat for each line tLine in the pendingMessages
      if item 4 to -1 of tLine contains tLong then cancel item 1 of tLine
   end repeat
end xbCancelPending

-- In a standalone (the xt3d_Bench build) load the xt3d extension from where build.bat
-- installs it, so the standalone always uses the latest build and needs no inclusion.
-- The library mapping comes first: the DLL is bound on the first xt3d call.
-- In the IDE the Extension Builder loads it, so nothing happens here.
command xbLoadXt3d
   local tErr
   if the environment is "development" then exit xbLoadXt3d
   if the loadedExtensions contains "org.xtalk.xtbridge" then exit xbLoadXt3d
   try
      set the revLibraryMapping["xt3d"] to "C:/xt3d/extension/code/x86_64-win32/xt3d.dll"
      load extension from file "C:/xt3d/extension/module.2.lcm" with resource path "C:/xt3d/extension"
   catch tErr
   end try
end xbLoadXt3d

function px pLogical
   return round(pLogical * sScale)
end px

-------------------------------------------------------------------- controls

command xbBuildControls
   local i, tX, tY
   lock screen
   repeat with i = the number of controls of this card down to 1
      delete control i of this card
   end repeat

   xbMake "image", "view", 0, 0, kViewW, kViewH
   set the lockLoc of image "view" to true
   xbMake "field", "log", 0, kViewH + 6, kViewW, 118
   set the vScrollbar of field "log" to true
   set the textSize of field "log" to px(11)

   put kPanelX into tX
   put 8 into tY
   xbMake "button", "folderBtn", tX, tY, 70, 24, "Folder..."
   xbMake "field", "folder", tX + 76, tY + 2, kPanelW - 76, 22
   set the textSize of field "folder" to px(10)
   add 30 to tY
   xbMake "list", "fileList", tX, tY, kPanelW, 150
   add 156 to tY
   xbMake "button", "loadBtn", tX, tY, 120, 24, "Load file..."
   xbMake "button", "checksBtn", tX + 130, tY, 120, 24, "Run checks"
   add 32 to tY
   xbMake "checkbox", "spinChk", tX, tY, 80, 20, "Spin"
   xbMake "checkbox", "gridChk", tX + 85, tY, 80, 20, "Grid"
   xbMake "checkbox", "tintChk", tX + 170, tY, 80, 20, "Tint"
   add 22 to tY
   xbMake "checkbox", "solidChk", tX, tY, 80, 20, "Solid"
   xbMake "checkbox", "wiresChk", tX + 85, tY, 80, 20, "Wires"
   add 22 to tY
   xbMake "checkbox", "cullChk", tX, tY, 80, 20, "Culling"
   xbMake "checkbox", "frontChk", tX + 85, tY, 160, 20, "Cull front faces"
   set the hilite of button "gridChk" to true
   set the hilite of button "tintChk" to true
   set the hilite of button "solidChk" to true
   set the hilite of button "wiresChk" to true
   add 28 to tY
   xbMake "option", "animMenu", tX, tY, kPanelW, 24
   add 30 to tY
   xbMake "checkbox", "playChk", tX, tY + 2, 60, 20, "Play"
   set the hilite of button "playChk" to true
   xbMake "scrollbar", "frameBar", tX + 62, tY, kPanelW - 62, 22
   add 30 to tY
   xbMake "button", "camBtn", tX, tY, 104, 24, "Reset camera"
   xbMake "button", "faceBtn", tX + 110, tY, 64, 24, "Face"
   xbMake "button", "unloadBtn", tX + 180, tY, 70, 24, "Unload"
   add 30 to tY
   xbMake "checkbox", "devChk", tX, tY, kPanelW, 20, "Dev server (lets Claude drive this bench)"
   set the hilite of button "devChk" to xbDevRunning()
   add 26 to tY
   xbMake "field", "info", tX, tY, kPanelW, kViewH + 124 - tY
   set the vScrollbar of field "info" to true
   set the textSize of field "info" to px(11)
   xbAnimMenu
   unlock screen
end xbBuildControls

-- xbMake type, name, left, top, width, height [, label]   (logical pixels)
command xbMake pType, pName, pLeft, pTop, pWidth, pHeight, pLabel
   switch pType
      case "image"
         create image pName
         break
      case "field"
      case "list"
         create field pName
         set the lockText of it to true
         set the dontWrap of it to (pType is "list")
         if pType is "list" then
            set the listBehavior of it to true
            set the vScrollbar of it to true
         end if
         break
      case "scrollbar"
         create scrollbar pName
         set the style of it to "scale"
         set the startValue of it to 0
         set the endValue of it to 1
         set the showValue of it to false
         break
      default
         create button pName
         if pType is "checkbox" then
            set the style of it to "checkbox"
         else if pType is "option" then
            set the style of it to "menu"
            set the menuMode of it to "option"
         end if
         if pLabel is not empty then set the label of it to pLabel
   end switch
   set the rect of it to px(pLeft), px(pTop), px(pLeft + pWidth), px(pTop + pHeight)
end xbMake

command xbListFolder
   local tFiles, tOld
   put the defaultFolder into tOld
   set the defaultFolder to sFolder
   if the result is not empty then
      put empty into tFiles
   else
      put the files into tFiles
   end if
   set the defaultFolder to tOld
   filter tFiles with regex pattern kModelTypes
   sort lines of tFiles
   put sFolder into field "folder"
   put tFiles into field "fileList"
end xbListFolder

command xbAnimMenu
   local i, tMenu, tInfo
   if sAnimCount > 0 then
      repeat with i = 0 to sAnimCount - 1
         put xt3d_ModelAnimationInfo(sAnimFirst + i) into tInfo
         -- name,boneCount,keyframeCount (the name may itself hold commas)
         put i & ": " & item 1 to -3 of tInfo & " (" & item -1 of tInfo & " frames)" & return after tMenu
      end repeat
      delete the last char of tMenu
   else
      put "(no animations)" into tMenu
   end if
   set the text of button "animMenu" to tMenu
   set the menuHistory of button "animMenu" to 1
end xbAnimMenu

-------------------------------------------------------------------- events

on mouseUp
   put false into sDragging
   switch the short name of the target
      case "folderBtn"
         answer folder "Choose a folder of models" with sFolder
         if it is not empty then
            put it into sFolder
            xbListFolder
         end if
         break
      case "fileList"
         if the selectedText of field "fileList" is not empty then
            xbLoadModel sFolder & "/" & the selectedText of field "fileList"
         end if
         break
      case "loadBtn"
         answer file "Choose a model file (glb, gltf, obj, iqm, m3d, vox)"
         if it is not empty then xbLoadModel it
         break
      case "checksBtn"
         xbRunChecks
         break
      case "camBtn"
         put 45 into sYaw
         put 25 into sPitch
         put 5 into sDist
         put 0 into sAngle
         break
      case "devChk"
         xbDevServer the hilite of button "devChk"
         break
      case "faceBtn"
         xbShowFace
         break
      case "unloadBtn"
         xbUnloadModel
         put "No model loaded." into field "info"
         break
   end switch
   -- any click may have changed the picture (a checkbox, the camera, a model)
   xbRedraw
end mouseUp

on mouseRelease
   put false into sDragging
end mouseRelease

on mouseDown
   if the short name of the target is "view" then
      put true into sDragging
      put the mouseH into sDragX
      put the mouseV into sDragY
   end if
end mouseDown

on mouseMove pX, pY
   if sDragging is not true then pass mouseMove
   if the mouse is up then
      put false into sDragging
      exit mouseMove
   end if
   subtract (pX - sDragX) * 0.4 from sYaw
   add (pY - sDragY) * 0.4 to sPitch
   put max(-85, min(85, sPitch)) into sPitch
   put pX into sDragX
   put pY into sDragY
   xbRedraw
end mouseMove

-- the mouse wheel arrives as raw keys 65308 (down) and 65309 (up)
on rawKeyDown pKey
   if (pKey is 65308 or pKey is 65309) and the mouseLoc is within the rect of image "view" then
      if pKey is 65308 then
         multiply sDist by 1.1
      else
         divide sDist by 1.1
      end if
      put max(0.5, min(200, sDist)) into sDist
      xbRedraw
   else
      pass rawKeyDown
   end if
end rawKeyDown

on menuPick pItem
   if the short name of the target is "animMenu" and sAnimCount > 0 then
      xbSelectAnim the menuHistory of button "animMenu" - 1
   end if
end menuPick

on scrollbarDrag pValue
   if the short name of the target is "frameBar" and sSettingSlider is not true then
      put pValue into sAnimFrame
      set the hilite of button "playChk" to false
      xbRedraw
   end if
end scrollbarDrag

-------------------------------------------------------------------- dev server

-- the server is the LIB_MCP library (a separate project), so it survives this bench being reloaded
command xbDevServer pOn
   local tPath
   if pOn then
      put xbFindLibMCP() into tPath
      if tPath is empty then
         put "Dev server: LIB_MCP not found next to this project" & return & \
               "(looked for LIB_MCP/livecode/lib_mcp.livecodescript above" && the effective filename of me & ")" into field "info"
         set the hilite of button "devChk" to false
         exit xbDevServer
      end if
      start using stack tPath
      DevServer.Start 8766, the short name of me
      put the result into field "info"
      set the hilite of button "devChk" to xbDevRunning()
   else
      if xbDevRunning() then DevServer.Stop
      put "Dev server stopped." into field "info"
   end if
end xbDevServer

-- walk up from this file; at each folder look for a LIB_MCP project beside it
function xbFindLibMCP
   local tPath, tTry
   put the effective filename of me into tPath
   set the itemDel to "/"
   repeat 6 times
      delete item -1 of tPath
      if tPath is empty then exit repeat
      put tPath & "/LIB_MCP/livecode/lib_mcp.livecodescript" into tTry
      if there is a file tTry then return tTry
   end repeat
   return empty
end xbFindLibMCP

function xbDevRunning
   local tErr
   try
      return DevServer.Running()
   catch tErr
      return false
   end try
end xbDevRunning

-- called by the dev server: run statements / evaluate an expression in this script,
-- so its handlers and script locals are reachable
command DevServer.Exec pCode
   local tErr
   local tResult
   try
      do pCode
      put the result into tResult
   catch tErr
      DevServer.LogError tErr, "/run in the bench"
      xbRedraw
      return "ERROR:" & return & DevServer.ErrorText(tErr)
   end try
   -- code run from Claude Code may have changed what the view shows
   xbRedraw
   return tResult
end DevServer.Exec

function DevServer.Eval pExpr
   local tErr
   try
      return value(pExpr)
   catch tErr
      DevServer.LogError tErr, "/eval in the bench"
      return "ERROR:" & return & DevServer.ErrorText(tErr)
   end try
end DevServer.Eval

-------------------------------------------------------------------- view

command xbStartView
   if sRunning is true then exit xbStartView
   -- raylib's own messages go to a file; INFO while loading, WARNING while running
   get xt3d_SetTraceLogFile(kRaylibLog)
   xt3d_SetTraceLogLevel 3
   xt3d_InitHidden sViewW, sViewH, "xt3d test bench"
   put xt3d_LoadRenderTexture(sViewW, sViewH) into sTarget
   put xt3d_LoadRenderTexture(sViewW * kSample, sViewH * kSample) into sBig
   put xt3d_RenderTextureGetTexture(sBig) into sBigTexture
   xt3d_SetTextureFilter sBigTexture, 1     -- 1 = bilinear, for the shrink
   put xt3d_CameraCreate(6,5,6, 0,0.5,0, 0,1,0, 45, 0) into sCamera
   xt3d_SetTraceLogLevel 4
   put 0 into sModel
   put 0 into sAnimCount
   put 0 into sAngle
   put 0 into sFrames
   put 0 into sFPS
   put the milliseconds into sLastTick
   put sLastTick into sFPSTick
   put true into sRunning
   xbShowLog
   put true into sDirty
   xbFrame
end xbStartView

-- Ask for one new frame: call after anything that changes what the view shows. Cheap to
-- call often; the frame is drawn once, after the current handler finishes. If the loop
-- is already running (Spin, an animation playing) the next frame picks the change up.
command xbRedraw
   put true into sDirty
   if sRunning is not true or sFrameMsg is not empty then exit xbRedraw
   -- waking from rest: restart the clocks so Spin and animation don't jump ahead
   put the milliseconds into sLastTick
   put sLastTick into sFPSTick
   put 0 into sFrames
   send "xbFrame" to me in 0 milliseconds
   put the result into sFrameMsg
end xbRedraw

-- true while the picture changes by itself, so the loop must keep running
function xbMoving
   if there is not a button "spinChk" then return false
   if the hilite of button "spinChk" then return true
   if sModel > 0 and sAnimFrames > 0 and the hilite of button "playChk" then return true
   return false
end xbMoving

command xbStopView
   if sRunning is not true then exit xbStopView
   put false into sRunning
   if sFrameMsg is not empty then cancel sFrameMsg
   put empty into sFrameMsg
   xbUnloadModel
   xt3d_UnloadRenderTexture sTarget
   xt3d_UnloadRenderTexture sBig
   xt3d_CameraFree sCamera
   xt3d_CloseWindow
end xbStopView

command xbFrame
   local tNow, tSeconds, tYaw, tPitch, tEX, tEY, tEZ, tTint, tWire, tText, tMoving
   put empty into sFrameMsg
   if sRunning is not true then exit xbFrame
   -- at rest with nothing changed: draw nothing and sleep until xbRedraw
   put xbMoving() into tMoving
   if not tMoving and sDirty is not true then exit xbFrame
   put false into sDirty
   put the milliseconds into tNow
   put (tNow - sLastTick) / 1000 into tSeconds
   put tNow into sLastTick
   add 1 to sFrames
   if tNow - sFPSTick >= 1000 then
      put round(sFrames * 1000 / (tNow - sFPSTick)) into sFPS
      put 0 into sFrames
      put tNow into sFPSTick
   end if
   if the hilite of button "spinChk" then add kSpin * tSeconds to sAngle

   -- animation
   if sModel > 0 and sAnimFrames > 0 then
      if the hilite of button "playChk" then
         add kAnimFPS * tSeconds to sAnimFrame
         repeat while sAnimFrame >= sAnimFrames
            subtract sAnimFrames from sAnimFrame
         end repeat
         put true into sSettingSlider
         set the thumbPosition of scrollbar "frameBar" to trunc(sAnimFrame)
         put false into sSettingSlider
      end if
      xt3d_UpdateModelAnimation sModel, sAnimFirst + sAnim, sAnimFrame
   end if

   -- orbit camera around the model's middle
   put sYaw * pi / 180 into tYaw
   put sPitch * pi / 180 into tPitch
   put sDist * cos(tPitch) * sin(tYaw) into tEX
   put sLift + sDist * sin(tPitch) into tEY
   put sDist * cos(tPitch) * cos(tYaw) into tEZ
   xt3d_CameraSet sCamera, tEX, tEY, tEZ, 0, sLift, 0, 0, 1, 0, 45, 0

   xt3d_BeginTextureMode sBig
   xt3d_ClearBackground 30, 30, 40, 255
   xt3d_BeginMode3D sCamera
   if the hilite of button "gridChk" then xt3d_DrawGrid 10, 1
   if sModel > 0 then
      xt3d_SetBackfaceCulling the hilite of button "cullChk"
      if the hilite of button "frontChk" then
         xt3d_SetCullFace 0
      else
         xt3d_SetCullFace 1
      end if
      if sWireColor is not empty then
         -- a line-only model (the face card): its lines, nothing else
         xt3d_DrawModelWiresEx sModel, 0,sLift,0, 0,1,0, sAngle, sFit,sFit,sFit, item 1 of sWireColor, item 2 of sWireColor, item 3 of sWireColor, 255
         if sModel2 > 0 then
            xt3d_DrawModelWiresEx sModel2, 0,sLift,0, 0,1,0, sAngle, sFit,sFit,sFit, item 1 of sWireColor2, item 2 of sWireColor2, item 3 of sWireColor2, 255
         end if
      else if the hilite of button "tintChk" then
         put "255,160,0" into tTint
      else
         put "255,255,255" into tTint
      end if
      if sWireColor is not empty then
         -- drawn above
      else if the hilite of button "solidChk" then
         xt3d_DrawModelEx sModel, 0,sLift,0, 0,1,0, sAngle, sFit,sFit,sFit, item 1 of tTint, item 2 of tTint, item 3 of tTint, 255
         put "0,0,0" into tWire
      else
         put tTint into tWire
      end if
      if the hilite of button "wiresChk" and sWireColor is empty then
         xt3d_DrawModelWiresEx sModel, 0,sLift,0, 0,1,0, sAngle, sFit,sFit,sFit, item 1 of tWire, item 2 of tWire, item 3 of tWire, 255
      end if
      xt3d_SetCullFace 1
      xt3d_SetBackfaceCulling true
   end if
   xt3d_EndMode3D
   if tMoving then
      put sFPS & " fps" into tText
   else
      put "at rest" into tText
   end if
   if sModel > 0 and sAnimFrames > 0 then put "   frame " & trunc(sAnimFrame) & " / " & sAnimFrames after tText
   if sModel = 0 then put "   no model loaded" after tText
   xt3d_DrawText tText, 10 * kSample, 10 * kSample, 20 * kSample, 255,255,255,255
   xt3d_EndTextureMode

   -- shrink into the view-sized target (negative source height keeps it upright)
   xt3d_BeginTextureMode sTarget
   xt3d_DrawTexturePro sBigTexture, 0,0,sViewW * kSample,-(sViewH * kSample), 0,0,sViewW,sViewH, 0,0, 0, 255,255,255,255
   xt3d_EndTextureMode
   set the imageData of image "view" to xt3d_RenderTextureImageData(sTarget)

   -- keep going only while something moves (Spin or animation may have just stopped)
   if xbMoving() then
      send "xbFrame" to me in kFrameMS milliseconds
      put the result into sFrameMsg
   end if
end xbFrame

-------------------------------------------------------------------- models

command xbLoadModel pPath
   local i, tBox, tSizeX, tSizeY, tSizeZ, tCX, tCY, tCZ, tBiggest, tAnims, tInfo
   if sRunning is not true then xbStartView
   xbUnloadModel
   xt3d_SetTraceLogLevel 3
   put xt3d_LoadModel(pPath) into sModel
   if sModel is not a number or sModel <= 0 then
      put 0 into sModel
      xt3d_SetTraceLogLevel 4
      put "Could not load:" & return & pPath & return & return & "See the raylib lines below the view." into field "info"
      xbShowLog
      return false
   end if
   put pPath into sModelPath
   xbFitModel
   put the result into tBox
   put item 4 of tBox - item 1 of tBox into tSizeX
   put item 5 of tBox - item 2 of tBox into tSizeY
   put item 6 of tBox - item 3 of tBox into tSizeZ

   -- animations: "firstHandle,count"; handles are consecutive
   put xt3d_LoadModelAnimations(pPath) into tAnims
   put item 1 of tAnims into sAnimFirst
   put item 2 of tAnims into sAnimCount
   if sAnimCount is not a number then put 0 into sAnimCount
   xt3d_SetTraceLogLevel 4
   xbAnimMenu
   xbSelectAnim 0

   put "file: " & pPath & return into tInfo
   put "meshes,materials,bones: " & xt3d_ModelInfo(sModel) & return after tInfo
   put "bounding box: " & tBox & return after tInfo
   put "size: " & tSizeX & ", " & tSizeY & ", " & tSizeZ & return after tInfo
   put "animations: " & sAnimCount & return after tInfo
   repeat with i = 0 to sAnimCount - 1
      put "  " & i & ": " & xt3d_ModelAnimationInfo(sAnimFirst + i) & "  (name,bones,frames)" & return after tInfo
   end repeat
   put tInfo into field "info"
   xbShowLog
   return true
end xbLoadModel

-- scale sModel to 2 units across, centre it on its own origin and stand it on the grid;
-- returns its bounding box (minX,minY,minZ,maxX,maxY,maxZ)
command xbFitModel
   local tBox, tSizeY, tCX, tCY, tCZ, tBiggest
   put xt3d_GetModelBoundingBox(sModel) into tBox
   put item 5 of tBox - item 2 of tBox into tSizeY
   put (item 1 of tBox + item 4 of tBox) / 2 into tCX
   put (item 2 of tBox + item 5 of tBox) / 2 into tCY
   put (item 3 of tBox + item 6 of tBox) / 2 into tCZ
   put max(item 4 of tBox - item 1 of tBox, tSizeY, item 6 of tBox - item 3 of tBox) into tBiggest
   if tBiggest <= 0 then put 1 into tBiggest
   put 2 / tBiggest into sFit
   put tSizeY * sFit / 2 into sLift
   -- move the model's middle to its origin, so it sits on the grid and spins about its middle
   xt3d_ModelSetTransform sModel, 1,0,0,0, 0,1,0,0, 0,0,1,0, -tCX,-tCY,-tCZ,1
   return tBox
end xbFitModel

-- The face card: Claude's face from LIB_MCP's assets (a 1-bit grid) as raised wireframe
-- blocks on a grid panel, made with LIB_MAP. All its lines are one mesh, so the whole
-- face is one draw call a frame. Each line is stored as a sliver triangle, which raylib's
-- wire mode draws as that line. Shown by itself when the dev server starts.
command xbShowFace
   local tLib, tMapLib, tFaceFile, tGrid, tBlank, tEdges, tCount, tMatrix
   put xbFindLibMCP() into tLib
   if tLib is empty then
      put "Face: LIB_MCP not found next to this project." into field "info"
      exit xbShowFace
   end if
   set the itemDel to "/"
   put item 1 to -3 of tLib & "/assets/claude_face_bits.txt" into tFaceFile
   put item 1 to -4 of tLib & "/LIB_MAP/livecode/lib_map.livecodescript" into tMapLib
   set the itemDel to comma
   if there is not a file tFaceFile or there is not a file tMapLib then
      put "Face: needs" && tFaceFile & return & "and" && tMapLib into field "info"
      exit xbShowFace
   end if
   -- always the current file: an older LIB_MAP may still be in memory
   if there is a stack "LIB_MAP" then
      stop using stack "LIB_MAP"
      delete stack "LIB_MAP"
   end if
   start using stack tMapLib
   if sRunning is not true then xbStartView
   put URL ("file:" & tFaceFile) into tGrid
   xbUnloadModel
   -- the panel's grid (dim) is the main model, so the fit is taken from the whole picture;
   -- the face's blocks (bright) are a second model placed the same way
   put tGrid into tBlank
   replace "1" with "0" in tBlank
   put Map.BlockEdges(tBlank, 0.1, 0.6, true) into tEdges
   put xbLinesModel(tEdges) into sModel
   put Map.BlockEdges(tGrid, 0.1, 0.6, false) into tEdges
   put the number of lines of tEdges into tCount
   put xbLinesModel(tEdges) into sModel2
   if sModel is 0 or sModel2 is 0 then
      put "Face: could not build the meshes." into field "info"
      exit xbShowFace
   end if
   xbFitModel
   put xt3d_ModelGetTransform(sModel) into tMatrix
   xt3d_ModelSetTransform sModel2, item 1 of tMatrix, item 2 of tMatrix, item 3 of tMatrix, item 4 of tMatrix, \
         item 5 of tMatrix, item 6 of tMatrix, item 7 of tMatrix, item 8 of tMatrix, \
         item 9 of tMatrix, item 10 of tMatrix, item 11 of tMatrix, item 12 of tMatrix, \
         item 13 of tMatrix, item 14 of tMatrix, item 15 of tMatrix, item 16 of tMatrix
   put "30,95,105" into sWireColor
   put "130,250,250" into sWireColor2
   put "claude face" into sModelPath
   -- a three-quarter view, a little from above, no floor grid
   put 28 into sYaw
   put 16 into sPitch
   put 3.0 into sDist
   put 0 into sAngle
   set the hilite of button "spinChk" to false
   set the hilite of button "gridChk" to false
   put "Claude (LIB_MCP connected)" & return & tCount && "face lines + panel grid, two draw calls a frame" & return & \
         "from" && tFaceFile into field "info"
   xbRedraw
end xbShowFace

-- line segments (x1,y1,z1,x2,y2,z2 per line) as one model for wire drawing: each segment
-- becomes a sliver triangle, which raylib's wire mode draws as that line. 0 on failure.
function xbLinesModel pSegments
   local tSeg, tVerts, tMesh
   repeat for each line tSeg in pSegments
      put item 1 to 3 of tSeg & return & item 4 to 6 of tSeg & return & \
            item 4 of tSeg + 0.0004 & "," & item 5 of tSeg + 0.0004 & "," & item 6 of tSeg & return after tVerts
   end repeat
   if tVerts is empty then return 0
   delete the last char of tVerts
   put xt3d_MeshFromText(tVerts, "", "") into tMesh
   if tMesh is not a number or tMesh <= 0 then return 0
   return xt3d_LoadModelFromMesh(tMesh)
end xbLinesModel

command xbSelectAnim pIndex
   put 0 into sAnimFrame
   put 0 into sAnimFrames
   put 0 into sAnim
   if sAnimCount > 0 and pIndex >= 0 and pIndex < sAnimCount then
      put pIndex into sAnim
      put item -1 of xt3d_ModelAnimationInfo(sAnimFirst + sAnim) into sAnimFrames
   end if
   put true into sSettingSlider
   set the endValue of scrollbar "frameBar" to max(1, sAnimFrames - 1)
   set the thumbPosition of scrollbar "frameBar" to 0
   put false into sSettingSlider
   xbRedraw
end xbSelectAnim

command xbUnloadModel
   if sAnimCount > 0 then xt3d_UnloadModelAnimations sAnimFirst
   if sModel > 0 then xt3d_UnloadModel sModel
   if sModel2 > 0 then xt3d_UnloadModel sModel2
   put 0 into sModel
   put 0 into sModel2
   put 0 into sAnimCount
   put 0 into sAnimFrames
   put 0 into sLift
   put 1 into sFit
   put empty into sModelPath
   put empty into sWireColor
   put empty into sWireColor2
   if there is a button "animMenu" then xbAnimMenu
   xbRedraw
end xbUnloadModel

-- warnings, errors and load reports from raylib's log, newest last
command xbShowLog
   local tLog, tCount
   if there is not a file kRaylibLog then exit xbShowLog
   put URL ("file:" & kRaylibLog) into tLog
   filter tLog with regex pattern "(WARNING|ERROR|FATAL|MODEL:|ANIM)"
   put the number of lines of tLog into tCount
   if tCount > 40 then put line tCount - 39 to tCount of tLog into tLog
   put tLog into field "log"
   set the vScroll of field "log" to 100000
end xbShowLog

-------------------------------------------------------------------- checks

command xbStep pText
   open file kCheckLog for append
   write pText & return to file kCheckLog
   close file kCheckLog
end xbStep

command xbCheck pName, pGot, pExpected
   local tLine
   if pGot is pExpected then
      put "PASS  " & pName into tLine
   else
      put "FAIL  " & pName & "   got [" & pGot & "] expected [" & pExpected & "]" into tLine
   end if
   put tLine & return after sReport
   xbStep "   " & tLine
   put sReport into field "info"
end xbCheck

command xbNote pText
   put "      " & pText & return after sReport
   xbStep "   " & pText
   put sReport into field "info"
end xbNote

on xbRunChecks
   local tKeep, tFiles, tFile, tInfo, tExpect, tData
   put empty into sReport
   put empty into URL ("file:" & kCheckLog)
   put sModelPath into tKeep
   put "Running checks... (each step is logged to " & kCheckLog & ")" into field "info"

   -- 1. crash guards: with no window, these must do nothing instead of crashing
   xbStep "G0 close the view"
   xbStopView
   xbStep "G1 IsWindowReady with no window"
   xbCheck "no window is open", xt3d_IsWindowReady(), "false"
   xbStep "G2 DrawCube with no window"
   xt3d_DrawCube 0,0,0, 1,1,1, 255,0,0,255
   xbCheck "DrawCube with no window did not crash", "ok", "ok"
   xbStep "G3 LoadModel with no window"
   xbCheck "LoadModel with no window answers 0", xt3d_LoadModel(kTestModels & "/skinned_bend.glb"), 0
   xbStep "G4 GetMousePosition with no window"
   xbCheck "GetMousePosition with no window answers empty", xt3d_GetMousePosition(), empty
   xbStep "G5 CloseWindow with no window"
   xt3d_CloseWindow
   xbCheck "CloseWindow with no window did not crash", "ok", "ok"
   xbStep "G6 UnloadModel 7 with no window"
   xt3d_UnloadModel 7
   xbCheck "UnloadModel with no window did not crash", "ok", "ok"

   -- 2. work that needs no window
   xbStep "P1 ColorToInt"
   xbCheck "ColorToInt(1,2,3,4)", xt3d_ColorToInt(1,2,3,4), 16909060
   xbStep "P2 CheckCollisionSpheres"
   xbCheck "spheres 1.5 apart touch", xt3d_CheckCollisionSpheres(0,0,0,1, 1.5,0,0,1), "true"
   xbStep "P3 Version"
   xbCheck "Version starts with xt3d", (xt3d_Version() begins with "xt3d "), "true"

   -- 3. reopen and load every test model
   xbStep "W1 open the view again"
   xbStartView
   xbCheck "window open again", xt3d_IsWindowReady(), "true"
   put "skinned_bend.glb,3,1" & return & "body_block_baked.glb,65,1" into tExpect
   put the defaultFolder into tData
   set the defaultFolder to kTestModels
   put the files into tFiles
   set the defaultFolder to tData
   filter tFiles with regex pattern kModelTypes
   repeat for each line tFile in tFiles
      xbStep "M load " & tFile
      xbLoadModel kTestModels & "/" & tFile
      if the result is not "true" then
         xbCheck tFile & " loads", "failed", "loaded"
         next repeat
      end if
      put xt3d_ModelInfo(sModel) into tInfo
      repeat for each line tData in tExpect
         if item 1 of tData is tFile then
            xbCheck tFile & " bones", item 3 of tInfo, item 2 of tData
            xbCheck tFile & " animations", sAnimCount, item 3 of tData
            put empty into tFile
            exit repeat
         end if
      end repeat
      if tFile is not empty then xbNote tFile & ": meshes,materials,bones " & tInfo & ", animations " & sAnimCount
   end repeat
   xbUnloadModel

   -- 4. one frame copied into LiveCode
   xbStep "F1 frame copy"
   put xt3d_RenderTextureImageData(sTarget) into tData
   xbCheck "frame bytes", the number of bytes in tData, sViewW * sViewH * 4

   xbStep "done"
   put return & "Done. Log: " & kCheckLog after sReport
   if tKeep is not empty then
      xbLoadModel tKeep
      put sReport & return & return & field "info" into field "info"
   else
      put sReport into field "info"
   end if
end xbRunChecks
