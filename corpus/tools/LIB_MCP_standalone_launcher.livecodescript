-- Stack script for LIB_MCP/standalone/xt3d_MCP.livecode, the standalone LIB_MCP server.
-- Paste it as the stack script, save, and build a standalone (Windows is enough).
--
-- At start it walks up from its own .exe until it finds livecode/lib_mcp.livecodescript
-- (the build lands in standalone/<StackName>/Windows x86-64/, so that is LIB_MCP's own
-- folder), loads the server from there and starts it on port 8767. Changes to the server
-- file therefore need no rebuild; only changes to this script do.
-- Port 8767, so it runs beside the IDE's server (8766). Clients start it as needed.
-- Opened in the IDE it does nothing: there, a stack starts the server itself.

on openStack
   local tServer, tResult
   -- the server library also sees openStack; only act for this stack
   if the short name of the owner of the target is not the short name of me then pass openStack
   if the environment is "development" then exit openStack
   put LibMCP.FindServer() into tServer
   if tServer is empty then
      answer "LIB_MCP: could not find livecode/lib_mcp.livecodescript above" && the effective filename of me
      exit openStack
   end if
   start using stack tServer
   DevServer.Start 8767
   put the result into tResult
   set the title of me to "LIB_MCP server"
   if there is not a field "status" then create field "status"
   set the rect of field "status" to 0, 0, the width of me, the height of me
   put tResult & return & "Server file:" && tServer & return & \
         "Errors: C:/LIB_MCP/livecode_errors.txt" & return & \
         "Close this window to stop the server." into field "status"
end openStack

-- walk up from this standalone's file to the folder that holds livecode/lib_mcp.livecodescript
function LibMCP.FindServer
   local tPath, tTry
   put the effective filename of me into tPath
   set the itemDel to "/"
   repeat 8 times
      delete item -1 of tPath
      if tPath is empty then exit repeat
      put tPath & "/livecode/lib_mcp.livecodescript" into tTry
      if there is a file tTry then return tTry
   end repeat
   return empty
end LibMCP.FindServer
