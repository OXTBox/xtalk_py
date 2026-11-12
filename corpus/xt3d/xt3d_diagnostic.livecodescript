script "xt3dDiagnostic"
-- xt3d diagnostic 2. Logs every step to C:/xt3d/diag_log.txt before running it.
-- Order: number passing, a full frame saved to PNG, then the two risky things
-- (text coming back from the DLL, and the frame copy into LiveCode).
--
-- A script-only stack: File > Open Stack, pick this file, then type  xt3dDiag2
-- in the Message Box. (Or paste it, without line 1, into the card script of a new stack.)

constant kLog = "C:/xt3d/diag_log.txt"

command xt3dLog pText
   open file kLog for append
   write pText & return to file kLog
   close file kLog
end xt3dLog

on xt3dDiag2
   local tTarget, tCamera, tMesh, tModel, tOK, tData, tText
   put empty into URL ("file:" & kLog)

   -- A. numbers in, numbers out (no text returned by the DLL anywhere in A or B)
   xt3dLog "A1 integers: ColorToInt(1,2,3,4)"
   xt3dLog "   got " & xt3d_ColorToInt(1,2,3,4) & " (expected 16909060)"
   xt3dLog "A2 8 decimals: spheres 1.5 apart, radius 1 each"
   xt3dLog "   got " & xt3d_CheckCollisionSpheres(0,0,0,1, 1.5,0,0,1) & " (expected true)"
   xt3dLog "A3 8 decimals: spheres 2.5 apart, radius 1 each"
   xt3dLog "   got " & xt3d_CheckCollisionSpheres(0,0,0,1, 2.5,0,0,1) & " (expected false)"

   -- B. one full frame, saved to a PNG by the DLL
   xt3dLog "B1 InitHidden"
   xt3d_InitHidden 640, 480, "xt3d"
   xt3dLog "B2 LoadRenderTexture"
   put xt3d_LoadRenderTexture(640, 480) into tTarget
   xt3dLog "   handle " & tTarget
   xt3dLog "B3 CameraCreate (11 numbers)"
   put xt3d_CameraCreate(6,5,6, 0,0.5,0, 0,1,0, 45, 0) into tCamera
   xt3dLog "   handle " & tCamera
   xt3dLog "B4 GenMeshCube"
   put xt3d_GenMeshCube(1, 1, 1) into tMesh
   xt3dLog "   handle " & tMesh
   xt3dLog "B5 LoadModelFromMesh"
   put xt3d_LoadModelFromMesh(tMesh) into tModel
   xt3dLog "   handle " & tModel
   xt3dLog "B6 BeginTextureMode"
   xt3d_BeginTextureMode tTarget
   xt3dLog "B7 ClearBackground"
   xt3d_ClearBackground 30, 30, 40, 255
   xt3dLog "B8 BeginMode3D"
   xt3d_BeginMode3D tCamera
   xt3dLog "B9 DrawGrid"
   xt3d_DrawGrid 10, 1
   xt3dLog "B10 DrawCube (10 numbers)"
   xt3d_DrawCube 2,0.5,0, 1,1,1, 0,200,0,255
   xt3dLog "B11 DrawModelEx (15 numbers)"
   xt3d_DrawModelEx tModel, 0,0.5,0, 0,1,0, 30, 1,1,1, 255,160,0,255
   xt3dLog "B12 EndMode3D"
   xt3d_EndMode3D
   xt3dLog "B13 DrawText"
   xt3d_DrawText "xt3d", 10, 10, 20, 255,255,255,255
   xt3dLog "B14 EndTextureMode"
   xt3d_EndTextureMode
   xt3dLog "B15 RenderTextureExport to C:/xt3d/frame.png"
   put xt3d_RenderTextureExport(tTarget, "C:/xt3d/frame.png") into tOK
   xt3dLog "   export result: " & tOK

   -- C. text coming back from the DLL
   xt3dLog "C1 Version, once"
   put xt3d_Version() into tText
   xt3dLog "   got " & tText
   xt3dLog "C2 CameraGet, once"
   put xt3d_CameraGet(tCamera) into tText
   xt3dLog "   got " & tText
   xt3dLog "C3 Version, 50 times"
   repeat 50 times
      put xt3d_Version() into tText
   end repeat
   xt3dLog "   survived 50 text returns"

   -- D. frame copy into LiveCode
   xt3dLog "D1 RenderTextureImageData"
   put xt3d_RenderTextureImageData(tTarget) into tData
   xt3dLog "   bytes received: " & the number of bytes in tData & " (expected " & 640 * 480 * 4 & ")"
   xt3dLog "D2 set the imageData"
   if there is no image "xt3dView" then create image "xt3dView"
   set the lockLoc of image "xt3dView" to true
   set the width of image "xt3dView" to 640
   set the height of image "xt3dView" to 480
   set the imageData of image "xt3dView" to tData

   xt3dLog "E finished without crashing"
   answer "Diagnostic finished. See C:/xt3d/diag_log.txt and C:/xt3d/frame.png"
end xt3dDiag2
