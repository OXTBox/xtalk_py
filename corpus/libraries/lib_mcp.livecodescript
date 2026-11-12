script "LIB_MCP"
-- LIB_MCP: lets Claude Code, a local model (through MCP) or any local tool drive a running
-- LiveCode 9.6.3 IDE or standalone: run code, evaluate, compile-check, read errors, snapshot.
-- https: none. Plain HTTP on 127.0.0.1 only. A script-only library stack.
--
-- START IT
--   * from any stack:  start using stack "<path>/LIB_MCP/livecode/lib_mcp.livecodescript"
--                      DevServer.Start 8766, "<name of the stack /run should talk to>"
--   * or open this file (File > Open Stack): it starts itself on port 8766
--   * or run the standalone in LIB_MCP/standalone (port 8767), which loads this file
-- One engine, one server: the library keeps one listener. The IDE uses 8766 and the
-- standalone 8767, so both can run at once.
--
-- FILES (runtime folder C:/LIB_MCP, created on start)
--   devtoken_<port>.txt ....... line 1 token, line 2 port; clients read it
--   livecode_errors.txt ....... every script error, translated (see below)
--   lc_execution_errors.txt,
--   lc_parsing_errors.txt ..... LiveCode's error message lists, saved from the IDE on start,
--                               used where the engine has none (a standalone)
--   snap.png .................. default snapshot
--
-- ERRORS GO TO A FILE, so nobody copies them out of the IDE's locked error window:
--   * errorDialog: the message LiveCode sends when a script fails (logged, then passed
--     on so the IDE still shows its error window)
--   * the IDE's error window (stack "revErrorDisplay"), read once a second; this adds the
--     object and handler names the IDE shows. Based on the owner's capture script.
-- Adapted from the LIB_DEVSERVER kit (owner's vector engine project).
--
-- Every request must carry the header  X-Token: <token>.  The token is new on every start.
--
-- ROUTES (bodies are UTF-8 text)
--   GET  /ping                   "OK" + LiveCode version + environment + target stack
--   POST /run                    body = LiveCode statements. Runs inside the target stack's
--                                script (its handlers and script locals are reachable) when it
--                                is open and has a DevServer.Exec handler, else here
--                                (?in=server forces here). Answers the message box text
--                                (anything "put" with no destination) and the result.
--                                Code runs through "do" inside a handler: don't declare local
--                                names that handler uses (tErr, tResult).
--   POST /eval                   body = one expression -> its value (?in=server as above)
--   POST /compile                body = a whole script (a .livecodescript file's text is fine):
--                                "COMPILES OK" or the compile errors, translated, with line
--                                numbers of the text as sent
--   POST /reload                 close the target stack and open it again from its file
--                                (?path=<file> opens that file instead)
--   GET  /snap                   PNG of the target stack's card (?file=, default C:/LIB_MCP/snap.png)
--
-- THIS RUNS ANY CODE IT IS SENT. Development only; never ship it inside an application.

constant kRuntime = "C:/LIB_MCP"
constant kSnapFile = "C:/LIB_MCP/snap.png"
constant kErrorFile = "C:/LIB_MCP/livecode_errors.txt"
constant kExecErrorList = "C:/LIB_MCP/lc_execution_errors.txt"
constant kParseErrorList = "C:/LIB_MCP/lc_parsing_errors.txt"

local sDev   -- ["port"], ["token"], ["target"], ["reload"], ["conn"][socket][...]
local sLastErrorWindow   -- text of the IDE error window when last read
local sWatching          -- true while the error window is being watched

-------------------------------------------------------------------- opened directly

-- Opening this file as a stack starts the server. As a library this stack sits in every
-- message path, so openStack for any other stack is passed straight on.
on openStack
   local tResult
   if the short name of the owner of the target is not the short name of me then pass openStack
   start using me
   DevServer.Start
   put the result into tResult
   DevServer.ShowStatus tResult
end openStack

command DevServer.ShowStatus pText
   if there is not a field "status" of me then
      set the defaultStack to the short name of me
      set the title of me to "LIB_MCP dev server"
      set the width of me to 420
      set the height of me to 90
      create field "status" in card 1 of me
      set the lockText of it to true
      set the rect of it to 0, 0, 420, 90
   end if
   put pText & return & "Errors are logged to" && kErrorFile & return & \
         "Close this window any time; the server keeps running." into field "status" of me
end DevServer.ShowStatus

-------------------------------------------------------------------- start / stop

command DevServer.Start pPort, pTarget
   local tErr
   if pPort is empty then put 8766 into pPort
   if there is not a folder kRuntime then create folder kRuntime
   DevServer.Stop
   put pPort into sDev["port"]
   put pTarget into sDev["target"]
   put DevServer.NewToken() into sDev["token"]
   put kRuntime & "/devtoken_" & pPort & ".txt" into sDev["tokenfile"]
   -- the IDE knows LiveCode's error messages; save them for engines that don't
   if the environment is "development" and the scriptExecutionErrors is not empty then
      put the scriptExecutionErrors into URL ("file:" & kExecErrorList)
      put the scriptParsingErrors into URL ("file:" & kParseErrorList)
   end if
   accept connections on port pPort with message "DevServer.OnConnect"
   put the result into tErr
   if tErr is not empty then
      put empty into sDev
      return "DevServer: could not listen on port" && pPort & ":" && tErr
   end if
   put sDev["token"] & return & sDev["port"] & return into URL ("file:" & sDev["tokenfile"])
   DevServer.LogError empty, "dev server started on port" && pPort
   if sWatching is not true then
      put true into sWatching
      DevServer.WatchErrors
   end if
   return "DevServer listening on 127.0.0.1:" & pPort
end DevServer.Start

command DevServer.Stop
   local tErr
   if sDev["port"] is not empty then
      try
         close socket sDev["port"]
      catch tErr
      end try
   end if
   if sDev["tokenfile"] is not empty and there is a file sDev["tokenfile"] then
      delete file sDev["tokenfile"]
   end if
   put empty into sDev
end DevServer.Stop

function DevServer.Running
   return sDev["port"] is not empty
end DevServer.Running

function DevServer.NewToken
   local tChars, tToken
   put "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" into tChars
   repeat 32 times
      put char random(62) of tChars after tToken
   end repeat
   return tToken
end DevServer.NewToken

-------------------------------------------------------------------- HTTP in

on DevServer.OnConnect pSocket
   set the itemDel to ":"
   if item 1 of pSocket is not "127.0.0.1" then
      close socket pSocket
      exit DevServer.OnConnect
   end if
   read from socket pSocket until crlf & crlf with message "DevServer.OnHeader"
end DevServer.OnConnect

on DevServer.OnHeader pSocket, pData
   local tC, tReq, tPath, tQ, tQuery, tPair, tEq, tToken, tLine, tColon, tKey, tVal
   replace crlf with return in pData
   put line 1 of pData into tReq
   put word 1 of tReq into tC["method"]
   put word 2 of tReq into tPath
   put offset("?", tPath) into tQ
   if tQ > 0 then
      put char 1 to tQ - 1 of tPath into tC["route"]
      put char tQ + 1 to -1 of tPath into tQuery
   else
      put tPath into tC["route"]
   end if
   set the itemDel to "&"
   repeat for each item tPair in tQuery
      put offset("=", tPair) into tEq
      if tEq = 0 then next repeat
      put urlDecode(char tEq + 1 to -1 of tPair) into tC["query"][char 1 to tEq - 1 of tPair]
   end repeat
   put 0 into tC["len"]
   repeat for each line tLine in line 2 to -1 of pData
      put offset(":", tLine) into tColon
      if tColon = 0 then next repeat
      -- chunks nest big-to-small only ("word of char" is "bad chunk order"),
      -- so cut the characters first, then trim with word 1 to -1
      put char 1 to tColon - 1 of tLine into tKey
      put toLower(word 1 to -1 of tKey) into tKey
      put char tColon + 1 to -1 of tLine into tVal
      put word 1 to -1 of tVal into tVal
      if tKey is "content-length" then put tVal into tC["len"]
      if tKey is "x-token" then put tVal into tToken
   end repeat
   if sDev["token"] is empty or tToken is not sDev["token"] then
      DevServer.Reply pSocket, 403, "bad or missing X-Token"
      exit DevServer.OnHeader
   end if
   put tC into sDev["conn"][pSocket]
   if tC["len"] > 0 then
      read from socket pSocket for tC["len"] with message "DevServer.OnBody"
   else
      DevServer.Handle pSocket, empty
   end if
end DevServer.OnHeader

on DevServer.OnBody pSocket, pData
   DevServer.Handle pSocket, textDecode(pData, "UTF-8")
end DevServer.OnBody

-------------------------------------------------------------------- routes

on DevServer.Handle pSocket, pBody
   local tC, tCode, tOut, tErr, tTarget, bInServer, tFile, tVersion
   put sDev["conn"][pSocket] into tC
   put 200 into tCode
   put sDev["target"] into tTarget
   -- run in the target stack when it is open, unless asked to run here
   put (tC["query"]["in"] is "server" or there is not a stack tTarget) into bInServer
   try
      switch tC["route"]
         case "/ping"
            put "OK LiveCode" && the version && "(" & the environment & ") | target" && \
                  tTarget && "open:" && (tTarget is not empty and there is a stack tTarget) into tOut
            break
         case "/run"
            put DevServer.Run(pBody, bInServer, tTarget) into tOut
            break
         case "/eval"
            if bInServer then
               put DevServer.Eval(pBody) into tOut
            else
               dispatch function "DevServer.Eval" to stack tTarget with pBody
               if it is "unhandled" then
                  put DevServer.Eval(pBody) into tOut
               else
                  put the result into tOut
               end if
            end if
            break
         case "/reload"
            if tC["query"]["path"] is not empty then
               put tC["query"]["path"] into sDev["reload"]
            else if there is a stack tTarget then
               put the effective filename of stack tTarget into sDev["reload"]
            else
               put "ERROR: the target stack is not open; give ?path=" into tOut
               break
            end if
            -- after the reply has gone: the target can't be closed while it is answering
            send "DevServer.DoReload" to me in 50 milliseconds
            put "OK reloading" && sDev["reload"] into tOut
            break
         case "/compile"
            put DevServer.Compile(pBody) into tOut
            break
         case "/snap"
            put tC["query"]["file"] into tFile
            if tFile is empty then put kSnapFile into tFile
            put DevServer.Snap(tTarget, tFile) into tOut
            break
         default
            put 404 into tCode
            put "unknown route:" && tC["route"] into tOut
      end switch
   catch tErr
      put 500 into tCode
      put "ERROR:" && tErr into tOut
   end try
   if tOut begins with "ERROR:" and tCode is 200 then put 422 into tCode
   DevServer.Reply pSocket, tCode, tOut
end DevServer.Handle

-- Statements run through "do". Anything put into the message box comes back,
-- followed by the result if there is one.
function DevServer.Run pCode, pInServer, pTarget
   local tErr, tResult
   put empty into msg
   if pInServer then
      try
         do pCode
         put the result into tResult
      catch tErr
         DevServer.LogError tErr, "/run"
         return "ERROR:" & return & DevServer.ErrorText(tErr)
      end try
   else
      dispatch "DevServer.Exec" to stack pTarget with pCode
      if it is "unhandled" then
         -- the target has no DevServer.Exec handler: run here instead
         return DevServer.Run(pCode, true, pTarget)
      end if
      put the result into tResult
      if tResult begins with "ERROR:" then return tResult
   end if
   -- what was put into the message box is the answer; the result only when there is none
   -- (after a function call the result often still holds that function's return value)
   if msg is not empty then return msg
   if tResult is empty then return empty
   return "result:" && tResult
end DevServer.Run

-- Compile a script without running it: set it as the script of a hidden scratch stack.
-- A script-only file's first line (script "name") is blanked, so line numbers still match.
function DevServer.Compile pScript
   local tOld, tErr
   if line 1 of pScript begins with "script " then put empty into line 1 of pScript
   if there is not a stack "xtCompileCheck" then
      put the defaultStack into tOld
      create invisible stack "xtCompileCheck"
      set the defaultStack to tOld
   end if
   set the script of stack "xtCompileCheck" to pScript
   put the result into tErr
   -- empty the script before deleting: deleting sends closeStack, and the checked script's
   -- own closeStack handler would run (a launcher's "quit" ended the engine once)
   set the script of stack "xtCompileCheck" to empty
   lock messages
   delete stack "xtCompileCheck"   -- so the IDE never asks to save it
   unlock messages
   if tErr is empty then return "COMPILES OK"
   return "COMPILE ERROR" & return & DevServer.ErrorText(tErr, true)
end DevServer.Compile

function DevServer.Eval pExpr
   local tErr
   try
      return value(pExpr)
   catch tErr
      DevServer.LogError tErr, "/eval"
      return "ERROR:" & return & DevServer.ErrorText(tErr)
   end try
end DevServer.Eval

command DevServer.DoReload
   local tPath, tName
   put sDev["reload"] into tPath
   put sDev["target"] into tName
   if there is a stack tName then
      -- its queued messages (frame timers) would keep the old copy alive: cancel them
      DevServer.CancelPending tName
      -- closeStack stops the bench's view; delete removes the old script from memory
      close stack tName
      if there is a stack tName then delete stack tName
   end if
   go stack tPath
end DevServer.DoReload

-- cancel every pending message addressed to stack pName or one of its objects
command DevServer.CancelPending pName
   local tLine, tLong
   if there is not a stack pName then exit DevServer.CancelPending
   put the long name of stack pName into tLong
   repeat for each line tLine in the pendingMessages
      if item 4 to -1 of tLine contains tLong then cancel item 1 of tLine
   end repeat
end DevServer.CancelPending

function DevServer.Snap pTarget, pFile
   local tErr
   if there is not a stack pTarget then return "ERROR: stack" && pTarget && "is not open"
   try
      export snapshot from this card of stack pTarget to file pFile as PNG
   catch tErr
      try
         export image "view" of stack pTarget to file pFile as PNG
      catch tErr
         return "ERROR: snapshot failed:" && tErr
      end try
   end try
   return "OK" && pFile
end DevServer.Snap

-------------------------------------------------------------------- errors to a file

-- LiveCode reports an error as lines of  code,line,column,hint . The code is a line
-- number in the scriptExecutionErrors (run time) or scriptParsingErrors (compile) list.
function DevServer.ErrorText pError, pParsing
   local tLine, tOut, tCode, tList, tMsg
   if pParsing is true then
      put the scriptParsingErrors into tList
      if tList is empty and there is a file kParseErrorList then
         put URL ("file:" & kParseErrorList) into tList
      end if
   else
      put the scriptExecutionErrors into tList
      if tList is empty and there is a file kExecErrorList then
         put URL ("file:" & kExecErrorList) into tList
      end if
   end if
   repeat for each line tLine in pError
      put item 1 of tLine into tCode
      if tCode is an integer and tCode > 0 then
         put line tCode of tList into tMsg
         put "  " & tMsg & "  (line" && item 2 of tLine & ", column" && item 3 of tLine into tMsg
         if item 4 of tLine is not empty then put ", near:" && item 4 to -1 of tLine after tMsg
         put tMsg & ")" into tLine
      end if
      put tLine & return after tOut
   end repeat
   return tOut
end DevServer.ErrorText

-- append one entry: time, where it came from, the raw error and its translation
command DevServer.LogError pError, pSource
   local tEntry
   put "==== " & the internet date & " | " & pSource & return into tEntry
   if pError is not empty then
      put DevServer.ErrorText(pError) after tEntry
      put "raw:" && pError & return after tEntry
   end if
   open file kErrorFile for append
   write tEntry & return to file kErrorFile
   close file kErrorFile
end DevServer.LogError

-- LiveCode sends errorDialog when a script fails. Log it, then let the IDE show it.
on errorDialog pError
   DevServer.LogError pError, "errorDialog"
   pass errorDialog
end errorDialog

-- The IDE's error window shows the failing object and handler. Read its fields once a
-- second and log them whenever they change. (From the owner's xt_error_capture.)
command DevServer.WatchErrors
   local tText
   if sWatching is not true then exit DevServer.WatchErrors
   put DevServer.ErrorWindowText() into tText
   if tText is not empty and tText is not sLastErrorWindow then
      put tText into sLastErrorWindow
      DevServer.LogError empty, "IDE error window" & return & tText
   end if
   send "DevServer.WatchErrors" to me in 1000 milliseconds
end DevServer.WatchErrors

function DevServer.ErrorWindowText
   local tStack, tOut, tCardNo, tCtlNo, tRef, tValue, tCaught
   put "revErrorDisplay" into tStack
   if there is not a stack tStack then return empty
   try
      repeat with tCardNo = 1 to the number of cards of stack tStack
         repeat with tCtlNo = 1 to the number of controls of card tCardNo of stack tStack
            put the long id of control tCtlNo of card tCardNo of stack tStack into tRef
            if word 1 of tRef is not "field" then next repeat
            put the text of tRef into tValue
            if tValue is empty then next repeat
            put "[" & the short name of tRef & "]" & return & tValue & return after tOut
         end repeat
      end repeat
   catch tCaught
      put "reading the error window failed:" && line 1 of tCaught & return after tOut
   end try
   return tOut
end DevServer.ErrorWindowText

-------------------------------------------------------------------- HTTP out

on DevServer.Reply pSocket, pCode, pText
   local tStatus, tBytes, tHead
   switch pCode
      case 200
         put "OK" into tStatus
         break
      case 403
         put "Forbidden" into tStatus
         break
      case 404
         put "Not Found" into tStatus
         break
      case 422
         put "Unprocessable" into tStatus
         break
      default
         put "Error" into tStatus
   end switch
   put textEncode(pText, "UTF-8") into tBytes
   put "HTTP/1.1" && pCode && tStatus & crlf into tHead
   put "Content-Type: text/plain; charset=utf-8" & crlf after tHead
   put "Content-Length: " & the number of bytes of tBytes & crlf after tHead
   put "Connection: close" & crlf & crlf after tHead
   write textEncode(tHead, "UTF-8") & tBytes to socket pSocket
   close socket pSocket
   delete variable sDev["conn"][pSocket]
end DevServer.Reply
