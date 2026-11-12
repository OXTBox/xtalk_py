## ---------------------------------------------------------------- LIB_MCP (Claude Code bridge)
## Paste this handler into the stack script (anywhere; e.g. above "DEVSERVER HOOKS"), and in
## APP.init the last line is simply
##     MCP.Attach
## (it decides for itself: IDE or standalone, and only when LIB_MCP is found next to it).
## Then delete the card "LIB_DEVSERVER" if the stack has one (its DevServer.* handlers would
## clash with LIB_MCP's). DevServer.Exec / DevServer.Eval below stay as they are: LIB_MCP
## calls them to run code in this script.
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
