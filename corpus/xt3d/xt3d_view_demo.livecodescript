script "xt3dViewDemo"
-- xt3d view demo: load a model, fit it to the view, play its first animation if it
-- has one, with switches for spin and face culling. Needs the DLL built after
-- xt3d_SetBackfaceCulling was added. Type  xt3dStart  and pick a file.
-- Pixel-exact on scaled displays: the stack's scaleFactor cancels the Windows
-- display scale, and the view is rendered at the screen's real pixel size.
--
-- 1. Build the xt3d library (see README.md) and load the xt3d extension.
-- 2. Put this script on a card (or "start using" it) and send "xt3dStart".
-- 3. Send "xt3dStop" before closing the stack.

constant kWidth = 640
constant kHeight = 480
constant kSample = 2      -- 2 = draw at double size and shrink (smooth edges); 1 = off
constant kSpin = 30        -- degrees a second; 0 holds the model still
constant kCulling = false  -- false draws both sides of every face (for models whose faces point inward)
constant kAnimFPS = 60     -- animation key frames advanced per second
constant kFrameMS = 16    -- milliseconds between frames: 16 is about 60 a second, 33 about 30

local sTarget, sBig, sBigTexture, sCamera, sModel, sRunning, sAngle, sLastTick
local sViewW, sViewH    -- view size in real screen pixels
local sAnimFirst, sAnimCount, sAnimFrames, sAnimFrame
local sFit, sLift       -- scale that makes the model 2 units across, and its half height

on xt3dStart
   if sRunning is true then exit xt3dStart
   -- one stack unit = one screen pixel, so the image is never stretched
   local tScale
   put the screenPixelScale into tScale
   set the scaleFactor of this stack to 1 / tScale
   put round(kWidth * tScale) into sViewW     -- same physical size as kWidth x kHeight at 100%
   put round(kHeight * tScale) into sViewH
   
   -- raylib's own messages (what it loaded, why something failed) go to this file
   get xt3d_SetTraceLogFile("C:/xt3d/raylib_log.txt")
   xt3d_InitHidden sViewW, sViewH, "xt3d"
   put xt3d_LoadRenderTexture(sViewW, sViewH) into sTarget
   -- the scene is drawn into a larger texture, then shrunk with smoothing into sTarget
   put xt3d_LoadRenderTexture(sViewW * kSample, sViewH * kSample) into sBig
   put xt3d_RenderTextureGetTexture(sBig) into sBigTexture
   xt3d_SetTextureFilter sBigTexture, 1     -- 1 = bilinear
   -- eye 6,5,6  looking at 0,0.5,0  up 0,1,0  fov 45  perspective (0)
   put xt3d_CameraCreate(6,5,6, 0,0.5,0, 0,1,0, 45, 0) into sCamera
   -- choose and load the model
   local tPath, tBox, tCX, tCY, tCZ, tSizeX, tSizeY, tSizeZ, tBiggest
   answer file "Choose a model file (obj, gltf, glb, iqm, m3d, vox)"
   if it is empty then
      xt3d_CloseWindow
      set the scaleFactor of this stack to 1
      exit xt3dStart
   end if
   put it into tPath
   put xt3d_LoadModel(tPath) into sModel
   
   -- bounding box: minX,minY,minZ,maxX,maxY,maxZ
   put xt3d_GetModelBoundingBox(sModel) into tBox
   put item 4 of tBox - item 1 of tBox into tSizeX
   put item 5 of tBox - item 2 of tBox into tSizeY
   put item 6 of tBox - item 3 of tBox into tSizeZ
   put (item 1 of tBox + item 4 of tBox) / 2 into tCX
   put (item 2 of tBox + item 5 of tBox) / 2 into tCY
   put (item 3 of tBox + item 6 of tBox) / 2 into tCZ
   put max(tSizeX, tSizeY, tSizeZ) into tBiggest
   if tBiggest <= 0 then put 1 into tBiggest
   put 2 / tBiggest into sFit
   put tSizeY * sFit / 2 into sLift
   
   -- move the model's centre to its own origin so it spins about its middle
   -- (a 4x4 matrix m0..m15; m12,m13,m14 are the x,y,z offset)
   xt3d_ModelSetTransform sModel, 1,0,0,0, 0,1,0,0, 0,0,1,0, -tCX,-tCY,-tCZ,1
   
   -- animations: "firstHandle,count"; handles are consecutive
   local tAnims, tReport, tIndex
   put xt3d_LoadModelAnimations(tPath) into tAnims
   put item 1 of tAnims into sAnimFirst
   put item 2 of tAnims into sAnimCount
   put 0 into sAnimFrame
   put 0 into sAnimFrames
   repeat with tIndex = 0 to sAnimCount - 1
      -- name,boneCount,keyframeCount
      put "  animation " & tIndex & ": " & xt3d_ModelAnimationInfo(sAnimFirst + tIndex) & return after tReport
   end repeat
   if sAnimCount > 0 then put the last item of xt3d_ModelAnimationInfo(sAnimFirst) into sAnimFrames
   
   put "file: " & tPath & return & \   -- lint-ok: report to the message box
         "meshes,materials,bones: " & xt3d_ModelInfo(sModel) & return & \
         "bounding box: " & tBox & return & \
         "size: " & tSizeX & "," & tSizeY & "," & tSizeZ & return & \
         "fit scale: " & sFit & return & \
         "animations: " & sAnimCount & return & tReport
   
   -- loading is logged; from here on only warnings and errors (every frame would log a line)
   xt3d_SetTraceLogLevel 4   -- 4 = LOG_WARNING

   if there is no image "xt3dView" then create image "xt3dView"
   set the lockLoc of image "xt3dView" to true
   set the width of image "xt3dView" to sViewW
   set the height of image "xt3dView" to sViewH
   set the topLeft of image "xt3dView" to 0,0
   
   put 0 into sAngle
   put the milliseconds into sLastTick
   put true into sRunning
   xt3dFrame
end xt3dStart

on xt3dStop
   put false into sRunning
   if sAnimCount > 0 then xt3d_UnloadModelAnimations sAnimFirst
   xt3d_UnloadModel sModel
   xt3d_UnloadRenderTexture sTarget
   xt3d_UnloadRenderTexture sBig
   xt3d_CameraFree sCamera
   xt3d_CloseWindow
   set the scaleFactor of this stack to 1
end xt3dStop

on xt3dFrame
   if sRunning is not true then exit xt3dFrame
   local tNow, tSeconds
   put the milliseconds into tNow
   put (tNow - sLastTick) / 1000 into tSeconds
   put tNow into sLastTick
   add kSpin * tSeconds to sAngle
   if sAnimFrames > 0 then
      add kAnimFPS * tSeconds to sAnimFrame
      if sAnimFrame >= sAnimFrames then put 0 into sAnimFrame
      xt3d_UpdateModelAnimation sModel, sAnimFirst, sAnimFrame
   end if
   
   -- game logic goes here, in LiveCode Script
   
   xt3d_BeginTextureMode sBig
   xt3d_ClearBackground 30, 30, 40, 255
   xt3d_BeginMode3D sCamera
   xt3d_DrawGrid 10, 1
   -- model, position xyz, rotation axis xyz, angle, scale xyz, tint rgba
   xt3d_SetBackfaceCulling kCulling
   xt3d_DrawModelEx sModel, 0,sLift,0, 0,1,0, sAngle, sFit,sFit,sFit, 255,160,0,255
   xt3d_DrawModelWiresEx sModel, 0,sLift,0, 0,1,0, sAngle, sFit,sFit,sFit, 0,0,0,255
   xt3d_SetBackfaceCulling true
   xt3d_EndMode3D
   xt3d_DrawText "xt3d " & xt3d_Version(), 10 * kSample, 10 * kSample, 20 * kSample, 255,255,255,255
   xt3d_EndTextureMode
   
   -- shrink the big picture into the 640x480 target
   -- texture, source x,y,w,h (negative h keeps it the right way up), dest x,y,w,h, origin x,y, rotation, tint
   xt3d_BeginTextureMode sTarget
   xt3d_DrawTexturePro sBigTexture, 0,0,sViewW * kSample,-(sViewH * kSample), 0,0,sViewW,sViewH, 0,0, 0, 255,255,255,255
   xt3d_EndTextureMode
   
   set the imageData of image "xt3dView" to xt3d_RenderTextureImageData(sTarget)
   send "xt3dFrame" to me in kFrameMS milliseconds
end xt3dFrame
