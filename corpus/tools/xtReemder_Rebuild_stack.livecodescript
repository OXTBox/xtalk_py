script "xtReemder_Rebuild_stack"
-- ============================================================================
-- xtReemder_Rebuild_stack -- launcher for the XTJSON rebuild.  LiveCode 9.6.3
--
-- A script-only stack: open this file with File > Open Stack. Only this
-- script is stored in the file; the button and the library cards are made
-- when needed and refreshed from the files beside it, so editing
-- LIB_XTJSON.livecodescript and clicking again always runs the new version.
--
-- Folder layout (everything beside this file):
--   xtReemder_Rebuild_stack.livecodescript    this file
--   LIB_XTJSON.livecodescript                 the rebuild library
--   LCHarvest2.livecodescript                 the harvester (optional)
--   XTJSON/                                   the harvest to rebuild from
--   XTJSON_REBUILT/                           written here if the harvester is present
--
-- REFRESH (every click on card 1, on the button or on the card itself)
--   1. LIB_XTJSON.livecodescript is read into the custom property
--      XTJSON_SCRIPT of card 1.
--   2. If there is no card "LIB_XTJSON", the templateCard is named
--      "LIB_XTJSON" and the card is created.
--   3. Either way the script of card "LIB_XTJSON" is set to the XTJSON_SCRIPT
--      of card 1.
--   The harvester is handled the same way: XTHARVEST_SCRIPT, card "LIB_XTHARVEST".
--
-- CLICKS
--   button "Rebuild"   refresh, rebuild from XTJSON, then harvest the rebuilt
--                      stack into XTJSON_REBUILT. Busy cursor while it runs.
--   the card           refresh, then switch between card 1 and card "LIB_XTJSON".
-- ============================================================================

on preOpenStack
   xtSetup
   pass preOpenStack
end preOpenStack

on openCard
   set the title of me to "xtRededemption" && "|" && the short name of this card
   pass openCard
end openCard

on mouseUp
   local tError
   if word 1 of the target is "button" and the short name of the target is "Rebuild" then
      xtRefresh
      put the result into tError
      if tError is empty then
         xtRebuild
      else
         put tError
      end if
      exit mouseUp
   end if
   if word 1 of the target is "card" then
      if the number of this card is 1 then
         xtRefresh
         put the result into tError
         if tError is not empty then put tError
      end if
      toggle.card
   end if
end mouseUp

on toggle.card
   local tName
   put the short name of me into tName
   if the number of this card is 1 and there is a card "LIB_XTJSON" of me then
      go card "LIB_XTJSON" of stack tName
   else
      go card 1 of stack tName
   end if
end toggle.card

-- ============================================================================
-- SETUP: the one button
-- ============================================================================

command xtSetup
   local tOldDefault
   if there is a button "Rebuild" of card 1 of me then exit xtSetup
   put the defaultStack into tOldDefault
   lock messages
   set the defaultStack to the short name of me
   set the width of me to 360
   set the height of me to 110
   reset the templateButton
   create button "Rebuild"
   set the rect of button "Rebuild" of card 1 of me to 20,20,340,60
   set the label of button "Rebuild" of card 1 of me to "Rebuild from XTJSON"
   if tOldDefault is not empty then set the defaultStack to tOldDefault
   unlock messages
end xtSetup

-- ============================================================================
-- REFRESH: files -> card 1 properties -> library card scripts
-- Returns empty in the result, or what went wrong.
-- ============================================================================

command xtRefresh
   local tScript, tError

   put xtReadScript("LIB_XTJSON") into tScript
   if tScript is empty then return "xtReemder: no LIB_XTJSON.livecodescript in" && xtFolder() & xtLookalikes("LIB_XTJSON")
   set the XTJSON_SCRIPT of card 1 of me to tScript
   xtEnsureCard "LIB_XTJSON"
   try
      set the script of card "LIB_XTJSON" of me to the XTJSON_SCRIPT of card 1 of me
      put the result into tError
   catch tCaught
      put line 1 of tCaught into tError
   end try
   if tError is not empty then return "xtReemder: LIB_XTJSON did not compile:" && tError

   -- the harvester is optional
   put xtReadScript("LCHarvest2,LIB_XTHARVEST") into tScript
   if tScript is not empty then
      set the XTHARVEST_SCRIPT of card 1 of me to tScript
      xtEnsureCard "LIB_XTHARVEST"
      try
         set the script of card "LIB_XTHARVEST" of me to the XTHARVEST_SCRIPT of card 1 of me
         put the result into tError
      catch tCaught2
         put line 1 of tCaught2 into tError
      end try
      if tError is not empty then return "xtReemder: the harvester did not compile:" && tError
   end if
   return empty
end xtRefresh

-- Makes card pName from the templateCard if it is not there yet.
private command xtEnsureCard pName
   local tStackName, tOldDefault
   if there is a card pName of me then exit xtEnsureCard
   put the short name of me into tStackName
   put the defaultStack into tOldDefault
   lock screen
   lock messages
   set the defaultStack to tStackName
   go card (the number of cards of me) of stack tStackName
   set the name of the templateCard to pName
   create card
   reset the templateCard
   go card 1 of stack tStackName
   if tOldDefault is not empty then set the defaultStack to tOldDefault
   unlock messages
   unlock screen
end xtEnsureCard

-- First of <name>.livecodescript, .livecode, .txt found beside this stack.
private function xtReadScript pNames
   local tName, tSuffix, tPath, tScript
   repeat for each item tName in pNames
      repeat for each item tSuffix in "livecodescript,livecode,txt"
         put xtFolder() & "/" & tName & "." & tSuffix into tPath
         if there is a file tPath then
            put textDecode(URL ("binfile:" & tPath), "UTF-8") into tScript
            replace (numToCodepoint(13) & numToCodepoint(10)) with cr in tScript
            replace numToCodepoint(13) with cr in tScript
            -- a script-only stack file starts with: script "name"
            if word 1 of line 1 of tScript is "script" then delete line 1 of tScript
            if word 1 of tScript is not empty then return tScript
         end if
      end repeat
   end repeat
   return empty
end xtReadScript

-- For the "not found" message: files here whose names start with pName.
private function xtLookalikes pName
   local tFiles
   put files(xtFolder()) into tFiles
   filter lines of tFiles with (pName & "*")
   if tFiles is empty then return cr & "(no file here has a name starting with" && pName & ")"
   return cr & "Found instead (rename the right one):" & cr & tFiles
end xtLookalikes

private function xtFolder
   local tFile
   put the effective filename of me into tFile
   set the itemDelimiter to "/"
   return item 1 to -2 of tFile
end xtFolder

-- ============================================================================
-- REBUILD (one shot, no options yet)
-- ============================================================================

command xtRebuild
   local tFolder, tSummary, tMain
   put xtFolder() into tFolder
   lock cursor
   set the cursor to busy

   dispatch command "xtjsonRebuild" to card "LIB_XTJSON" of me with (tFolder & "/XTJSON")
   put the result into tSummary
   dispatch function "xtjsonRebuiltMain" to card "LIB_XTJSON" of me
   put the result into tMain

   -- harvest the rebuilt stack straight away, before anything in it has run
   lock cursor
   set the cursor to busy
   if there is not a card "LIB_XTHARVEST" of me then
      put cr & "xtReemder: no LCHarvest2.livecodescript here, XTJSON_REBUILT not written" after tSummary
   else if tMain is empty or there is not a stack tMain then
      put cr & "xtReemder: nothing was rebuilt, XTJSON_REBUILT not written" after tSummary
   else
      dispatch command "harvestStack" to card "LIB_XTHARVEST" of me with tMain, (tFolder & "/XTJSON_REBUILT")
      put cr & the result after tSummary
   end if

   unlock cursor
   set the cursor to arrow
   put tSummary
end xtRebuild
