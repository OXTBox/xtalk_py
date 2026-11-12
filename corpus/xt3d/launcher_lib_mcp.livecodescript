-- Stack script for xt3d/standalone/xt3d_Bench_LibMCP.livecode: the bench with games
-- (testbench/xt3d_testBench_lib_mcp.livecodescript) as a standalone with LIB_MCP inside,
-- so it plays the Vibecode3D game scripts in LIB_GAMES and Claude can drive it.
-- Same design as launcher.livecodescript (the plain bench, port 8768); see README.md.
--
-- At start it walks up from its own .exe to find the bench
-- (testbench/xt3d_testBench_lib_mcp.livecodescript) and the sibling LIB_MCP project, starts
-- the LIB_MCP server on port 8770 (IDE 8766, LIB_MCP standalone 8767, plain bench 8768,
-- VibeCode3D 8769),
-- then opens the bench, which sees the server running and talks through it.
-- Both are loaded from their files each time: changes to them need no rebuild.
-- Close this small window to quit. Opened in the IDE it does nothing.

on openStack
   local tBench, tLib, tResult
   -- libraries also see openStack; only act for this stack
   if the short name of the owner of the target is not the short name of me then pass openStack
   if the environment is "development" then exit openStack
   put xbFindAbove("testbench/xt3d_testBench_lib_mcp.livecodescript") into tBench
   put xbFindAbove("LIB_MCP/livecode/lib_mcp.livecodescript") into tLib
   set the title of me to "xt3d games bench server"
   if there is not a field "status" then create field "status"
   set the rect of field "status" to 0, 0, the width of me, the height of me
   if tBench is empty or tLib is empty then
      put "Not found above" && the effective filename of me & ":" & return & \
            "bench: " & tBench & return & "LIB_MCP: " & tLib into field "status"
      exit openStack
   end if
   start using stack tLib
   DevServer.Start 8770, "xt3dTestBenchLibMCP"
   put the result into tResult
   put tResult & return & "Bench:" && tBench & return & \
         "Errors: C:/LIB_MCP/livecode_errors.txt" & return & \
         "Close this window to quit." into field "status"
   go stack tBench
end openStack

on closeStack
   -- closing this window ends the application, bench included
   if the short name of the owner of the target is not the short name of me then pass closeStack
   if the environment is not "development" then quit
end closeStack

-- walk up from this standalone's file; at each folder try pRelative beneath it
function xbFindAbove pRelative
   local tPath, tTry
   put the effective filename of me into tPath
   set the itemDel to "/"
   repeat 8 times
      delete item -1 of tPath
      if tPath is empty then exit repeat
      put tPath & "/" & pRelative into tTry
      if there is a file tTry then return tTry
   end repeat
   return empty
end xbFindAbove
