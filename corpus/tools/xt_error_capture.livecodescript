-- ============================================================================
-- xt_error_capture -- copy the text out of the IDE's error window.
-- LiveCode 9.6.3 IDE. Untested; written from the object path reported at runtime:
--   field id 1004 of group id 1003 of card id 1002 of stack
--   ".../Toolset/palettes/reverrordisplay.livecodescript"
--
-- The IDE shows execution errors in stack "revErrorDisplay". Its fields are
-- locked, so the text cannot be selected by hand; a script can still read it.
--
-- USE (message box, or from any script that has these handlers in its path)
--   put xtErrorCapture()                 -- text of every field of the window
--   xtErrorCaptureToFile "C:/path/errors.txt"   -- appends, with a time stamp
--
-- Returns empty when the error window is not loaded (for example in a
-- standalone), so callers do not need to test for it first.
-- Only fields are read: other controls have no text property, and asking a
-- group or graphic for its text is the "Object: does not have this property"
-- error.
-- ============================================================================

function xtErrorCapture
   local tStack, tOut, tCardNo, tCtlNo, tRef, tValue
   put "revErrorDisplay" into tStack
   if there is not a stack tStack then return empty
   try
      repeat with tCardNo = 1 to the number of cards of stack tStack
         repeat with tCtlNo = 1 to the number of controls of card tCardNo of stack tStack
            put the long id of control tCtlNo of card tCardNo of stack tStack into tRef
            if word 1 of tRef is not "field" then next repeat
            put the text of tRef into tValue
            if tValue is empty then next repeat
            put "[" & the short name of tRef & "]" & cr & tValue & cr & cr after tOut
         end repeat
      end repeat
   catch tCaught
      put "xtErrorCapture failed:" && line 1 of tCaught & cr after tOut
   end try
   return tOut
end xtErrorCapture

command xtErrorCaptureToFile pPath
   local tNew, tOld
   put xtErrorCapture() into tNew
   if tNew is empty then return "nothing captured"
   if there is a file pPath then put textDecode(URL ("binfile:" & pPath), "UTF-8") into tOld
   put tOld & "==== " & the internet date & cr & tNew into tNew
   put textEncode(tNew, "UTF-8") into URL ("binfile:" & pPath)
   return the result
end xtErrorCaptureToFile
