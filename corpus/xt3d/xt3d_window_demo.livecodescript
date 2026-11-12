script "xt3dWindowDemo"
-- xt3d window demo: the same scene in raylib's own visible window, with raylib's
-- built-in 4x edge smoothing, for comparison with the in-stack image.
--
-- Stop any other xt3d demo first (xt3dStop). A script-only stack: File > Open Stack,
-- pick this file, then type  xt3dWinStart  in the Message Box.  Stop with  xt3dWinStop ,
-- the window's close box, or Escape while the raylib window has focus.

constant kWidth = 640
constant kHeight = 480
constant kFrameMS = 16

local sCamera, sModel, sRunning, sAngle, sLastTick

on xt3dWinStart
   if sRunning is true then exit xt3dWinStart
   xt3d_SetConfigFlags 32                  -- 32 = FLAG_MSAA_4X_HINT, must come before InitWindow
   xt3d_InitWindow kWidth, kHeight, "xt3d - raylib window"
   xt3d_ClearWindowState 128               -- 128 = FLAG_WINDOW_HIDDEN: make sure it is showing
   put xt3d_CameraCreate(6,5,6, 0,0.5,0, 0,1,0, 45, 0) into sCamera
   put xt3d_LoadModelFromMesh(xt3d_GenMeshCube(1, 1, 1)) into sModel
   put 0 into sAngle
   put the milliseconds into sLastTick
   put true into sRunning
   xt3dWinFrame
end xt3dWinStart

on xt3dWinStop
   if sRunning is not true then exit xt3dWinStop
   put false into sRunning
   xt3d_UnloadModel sModel
   xt3d_CameraFree sCamera
   xt3d_CloseWindow
end xt3dWinStop

on xt3dWinFrame
   if sRunning is not true then exit xt3dWinFrame
   if xt3d_WindowShouldClose() then
      xt3dWinStop
      exit xt3dWinFrame
   end if

   local tNow
   put the milliseconds into tNow
   add 60 * (tNow - sLastTick) / 1000 to sAngle
   put tNow into sLastTick

   xt3d_BeginDrawing
   xt3d_ClearBackground 30, 30, 40, 255
   xt3d_BeginMode3D sCamera
   xt3d_DrawGrid 10, 1
   xt3d_DrawModelEx sModel, 0,0.5,0, 0,1,0, sAngle, 1,1,1, 255,160,0,255
   xt3d_DrawModelWiresEx sModel, 0,0.5,0, 0,1,0, sAngle, 1,1,1, 0,0,0,255
   xt3d_EndMode3D
   xt3d_DrawText "xt3d " & xt3d_Version(), 10, 10, 20, 255,255,255,255
   xt3d_DrawFPS 10, 40
   xt3d_EndDrawing

   send "xt3dWinFrame" to me in kFrameMS milliseconds
end xt3dWinFrame
