## ============================================================================
## LIB_DEVSERVER  -  lets Claude Code (or any local tool) talk to the running IDE.
## Loaded like every LIB_ card: Lib.Load "DEVSERVER", then DevServer.Start.
## APP.init starts it automatically in the IDE (never in a standalone).
##
## Plain HTTP on 127.0.0.1 only, every request must carry the header
##   X-Token: <token>
## The token is new on every start and is written, with the port, to the file
## ".lc_devtoken" next to the stack file (line 1 token, line 2 port). tools/lc.sh
## reads it from there. The custom header also stops web pages from calling in.
##
## ROUTES (body = UTF-8 text)
##   GET  /ping                      "OK" + LiveCode version + stack name
##   GET  /list                      "stack" and "card:<name>" for each card with a script
##   GET  /script?target=T           the script of T ("stack" or "card:<name>")
##   POST /script?target=T           set it; answers OK or the compile error.
##                                   Play./Edit_ cards are saved to their set too;
##                                   LIB_ cards are reloaded as libraries.
##   POST /run                       body = LiveCode statements, run in the stack script
##   POST /eval                      body = one expression -> its value
##   GET  /report?filter=Play.*      Report.Compact
##   POST /lib?name=LLM              Lib.Load that library
##
## This runs ANY code it is sent. Development only.
## ============================================================================

local sDev   -- ["port"], ["token"], ["conn"][socket][method/route/query/len]

on DevServer.Start pPort
   if pPort is empty then put 8765 into pPort
   try
      close socket pPort   -- a listener left from before a reload
   catch tErr
   end try
   put pPort into sDev["port"]
   put DevServer.NewToken() into sDev["token"]
   accept connections on port pPort with message "DevServer.OnConnect"
   put the result into tErr
   if tErr is not empty then return "DevServer: could not listen on" && pPort & ":" && tErr
   DevServer.WriteToken
   return "DevServer listening on 127.0.0.1:" & pPort
end DevServer.Start

on DevServer.Stop
   if sDev["port"] is not empty then
      try
         close socket sDev["port"]
      catch tErr
      end try
   end if
   put empty into sDev
end DevServer.Stop

function DevServer.Running
   return sDev["port"] is not empty
end DevServer.Running

function DevServer.NewToken
   put "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" into tChars
   put empty into tToken
   repeat 32 times
      put char random(62) of tChars after tToken
   end repeat
   return tToken
end DevServer.NewToken

function DevServer.MainStack
   return the long id of stack (the mainStack of this stack)
end DevServer.MainStack

on DevServer.WriteToken
   put the effective filename of stack (the mainStack of this stack) into tPath
   set the itemDel to "/"
   delete item -1 of tPath
   put sDev["token"] & cr & sDev["port"] & cr into url ("file:" & tPath & "/.lc_devtoken")
end DevServer.WriteToken

## ---------------------------------------------------------------- HTTP IN

on DevServer.OnConnect pSocket
   set the itemDel to ":"
   if item 1 of pSocket is not "127.0.0.1" then
      close socket pSocket
      exit DevServer.OnConnect
   end if
   read from socket pSocket until crlf & crlf with message "DevServer.OnHeader"
end DevServer.OnConnect

on DevServer.OnHeader pSocket, pData
   replace crlf with cr in pData
   put line 1 of pData into tReq
   put empty into tC
   put word 1 of tReq into tC["method"]
   put word 2 of tReq into tPath
   put offset("?", tPath) into tQ
   if tQ > 0 then
      put char 1 to tQ - 1 of tPath into tC["route"]
      put char tQ + 1 to -1 of tPath into tQuery
   else
      put tPath into tC["route"]
      put empty into tQuery
   end if
   set the itemDel to "&"
   repeat for each item tPair in tQuery
      put offset("=", tPair) into tEq
      if tEq = 0 then next repeat
      put urlDecode(char tEq + 1 to -1 of tPair) into tC["query"][char 1 to tEq - 1 of tPair]
   end repeat
   put 0 into tC["len"]
   put empty into tToken
   repeat for each line tLine in line 2 to -1 of pData
      put offset(":", tLine) into tColon
      if tColon = 0 then next repeat
      put toLower(word 1 to -1 of char 1 to tColon - 1 of tLine) into tKey
      put word 1 to -1 of char tColon + 1 to -1 of tLine into tVal
      if tKey is "content-length" then put tVal into tC["len"]
      if tKey is "x-token" then put tVal into tToken
   end repeat
   if tToken is not sDev["token"] or sDev["token"] is empty then
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

## ---------------------------------------------------------------- ROUTES

on DevServer.Handle pSocket, pBody
   put sDev["conn"][pSocket] into tC
   put DevServer.MainStack() into tMain
   put 200 into tCode
   put empty into tOut
   try
      switch tC["route"]
         case "/ping"
            put "OK LiveCode" && the version && "stack" && the short name of tMain into tOut
            break
         case "/list"
            put "stack" into tOut
            repeat with i = 1 to the number of cards of tMain
               if the script of card i of tMain is not empty then
                  put cr & "card:" & the short name of card i of tMain after tOut
               end if
            end repeat
            break
         case "/script"
            put DevServer.TargetRef(tC["query"]["target"]) into tRef
            if tRef is empty then
               put 404 into tCode
               put "no such target:" && tC["query"]["target"] into tOut
            else if tC["method"] is "GET" then
               put the script of tRef into tOut
            else
               put DevServer.SetScript(tC["query"]["target"], tRef, pBody) into tOut
               if tOut is not "OK" then put 422 into tCode
            end if
            break
         case "/run"
            dispatch "DevServer.Exec" to tMain with pBody
            if it is "unhandled" then
               put "ERROR: DevServer.Exec is missing from the stack script" into tOut
            else
               put the result into tOut
            end if
            break
         case "/eval"
            dispatch function "DevServer.Eval" to tMain with pBody
            put the result into tOut
            break
         case "/report"
            dispatch function "Report.Compact" to tMain with tC["query"]["filter"]
            put the result into tOut
            break
         case "/lib"
            put DevServer.ReloadLib(tC["query"]["name"]) into tOut
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

## "stack" / "card:<name>" -> long id, or empty.
function DevServer.TargetRef pTarget
   put DevServer.MainStack() into tMain
   if pTarget is "stack" then return tMain
   if pTarget begins with "card:" then
      put char 6 to -1 of pTarget into tName
      if there is a card tName of tMain then return the long id of card tName of tMain
   end if
   return empty
end DevServer.TargetRef

function DevServer.SetScript pTarget, pRef, pScript
   put DevServer.MainStack() into tMain
   set the script of pRef to pScript
   put the result into tErr
   if tErr is not empty then return "COMPILE ERROR:" && tErr
   if pTarget is "stack" then return "OK"
   put char 6 to -1 of pTarget into tName
   -- Keep the custom property sets in step with the card.
   if tName begins with "Play." or tName begins with "Edit_" then
      dispatch "save.card.script.to.set" to tMain with tName
   end if
   if tName begins with "LIB_" then
      put DevServer.ReloadLib(char 5 to -1 of tName) into tLib
      if tLib is not "OK" and tLib is not empty then return tLib
   end if
   return "OK"
end DevServer.SetScript

## A library can't replace its own script while one of its handlers is running,
## so DEVSERVER reloads itself a moment after the reply has gone.
function DevServer.ReloadLib pName
   put DevServer.MainStack() into tMain
   if pName is "DEVSERVER" then
      send "Lib.Load DEVSERVER" to tMain in 50 milliseconds
      send "DevServer.Start" && sDev["port"] to tMain in 100 milliseconds
      return "OK (DEVSERVER restarts with a new token)"
   end if
   dispatch "Lib.Load" to tMain with pName
   if it is "unhandled" then return "ERROR: Lib.Load is missing from the stack script"
   if the result is not empty then return "ERROR:" && the result
   return "OK"
end DevServer.ReloadLib

## ---------------------------------------------------------------- HTTP OUT

on DevServer.Reply pSocket, pCode, pText
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
