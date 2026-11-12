-- ============================================================================
-- LIB_XTJSON -- rebuild LiveCode stacks from an LCHarvest2 export
-- Target: LiveCode 9.6.3.
--
-- WHAT IT DOES
--   Reads XTJSON/manifest.json and every stack_*.json, then builds new stacks
--   in memory: cards, controls (groups nested), properties, custom properties,
--   images, behaviors and scripts. Nothing is saved to disk except the report.
--
--   Rebuilt stacks are named with the prefix "XT_" (kPrefix) because the
--   original stack is normally still open and two loaded stacks cannot share
--   a name. Rebuilt substacks become substacks of the rebuilt mainstack.
--
--   Every problem is written to XTJSON/rebuild_report.txt: objects that could
--   not be created, properties that could not be set or read back differently,
--   ids that could not be preserved, rects that moved, scripts that failed.
--
-- HOW IT RUNS
--   xtjsonRebuild folder        -- folder = the XTJSON folder; summary in the result
--   xtjsonRebuiltMain()         -- name of the rebuilt mainstack of the last run
--   This is a library: it has no system-message handlers. The "Rebuild" button
--   of stack xtReemder loads it and calls it.
--
--   Messages are locked for the whole build and while the rebuilt mainstack
--   is opened, so none of the rebuilt scripts run on their own. The cursor is
--   set to busy while it works and back to arrow when it is done.
--
-- NEEDS
--   JsonImport (the JSON library that ships with LiveCode 8+), or failing
--   that JSONToArray (mergJSON). Both are present in the 9.6.3 IDE.
-- ============================================================================

constant kFolder = "XTJSON"
constant kPrefix = "XT_"
-- never applied from props: set elsewhere, read-only, or meaningless on a copy
constant kNeverSet = "name,id,rect,number,layer,owner,visible,mainStack,substacks"

local sRoot         -- the XTJSON folder, no trailing slash
local sLog          -- report lines
local sStats        -- counters
local sNameMap      -- sNameMap[original stack name] = rebuilt stack name
local sMainNew      -- rebuilt mainstack name
local sSourceFile   -- file path of the original mainstack (from the manifest)
local sIdMap        -- sIdMap[original control id] = id in the stack being built
local sScripts      -- pending scripts:   sScripts[n]["ref" | "label" | "file" | "text"]
local sBehaviors    -- pending behaviors: sBehaviors[n]["ref" | "label" | "value"]
local sShow         -- sShow[rebuilt stack name] = true when the original was visible
local sDeferred     -- group properties set after all cards exist: sDeferred[n]["ref" | "key" | "value" | "label"]

-- ============================================================================
-- ENTRY POINTS
-- ============================================================================

command xtjsonRebuild pFolder
   local tManifest, tEntries, tEntry, tCount, i, tOldDefault, tStart, tSummary, tName
   put the milliseconds into tStart
   put empty into sLog
   put empty into sStats
   put empty into sNameMap
   put empty into sScripts
   put empty into sBehaviors
   put empty into sShow
   put empty into sDeferred

   put xtMyStack() into tName
   if the short name of tName begins with kPrefix then return "xtjson: this is a rebuilt stack, not rebuilding from inside it"
   if pFolder is empty then put xtMyStackFolder() & "/" & kFolder into pFolder
   if char -1 of pFolder is "/" then delete char -1 of pFolder
   put pFolder into sRoot
   if there is not a file (sRoot & "/manifest.json") then return "xtjson: no manifest.json in" && sRoot

   put xtReadJSON("manifest.json") into tManifest
   if tManifest is not an array then
      xtWriteReport tManifest, tStart
      set the cursor to arrow
      return "xtjson: manifest.json could not be parsed (see" && sRoot & "/rebuild_report.txt)"
   end if
   put tManifest["sourceFile"] into sSourceFile
   put tManifest["stacks"] into tEntries
   put xtCount(tEntries) into tCount
   put kPrefix & tManifest["mainStack"] into sMainNew
   repeat with i = 1 to tCount
      put kPrefix & tEntries[i]["name"] into sNameMap[tEntries[i]["name"]]
   end repeat

   put the defaultStack into tOldDefault
   lock cursor
   set the cursor to busy
   lock screen
   lock messages
   try
      -- remove rebuilt stacks left from an earlier run (only names with the prefix)
      repeat for each key tName in sNameMap
         if there is a stack sNameMap[tName] then delete stack sNameMap[tName]
      end repeat
      if there is a stack sMainNew then delete stack sMainNew

      -- mainstack first, so substacks have something to attach to
      repeat with i = 1 to tCount
         if tEntries[i]["role"] is "main" then xtBuildStack tEntries[i]
      end repeat
      repeat with i = 1 to tCount
         if tEntries[i]["role"] is not "main" then xtBuildStack tEntries[i]
      end repeat

      -- backgroundBehavior only now: a background group is put on every card
      -- created after it, which would land it on the wrong layer of later cards
      xtApplyDeferred

      -- behaviors and scripts last, when every object exists
      xtApplyBehaviors
      xtApplyScripts

      -- show what was visible, then open the mainstack with messages still locked
      repeat for each key tName in sShow
         if there is a stack tName then set the visible of stack tName to true
      end repeat
      if there is a stack sMainNew then
         set the visible of stack sMainNew to true
         go stack sMainNew
      end if
   catch tErr
      xtLog "fatal", line 1 of tErr
   end try
   if tOldDefault is not empty then
      try
         set the defaultStack to tOldDefault
      catch tErr2
      end try
   end if
   unlock messages
   unlock screen

   xtWriteReport tManifest, tStart
   unlock cursor
   set the cursor to arrow
   put "xtjson: rebuilt" && (sStats["stacks"] + 0) && "stack(s)," && (sStats["cards"] + 0) && "card(s)," && \
         (sStats["controls"] + 0) && "control(s)," && (sStats["scripts"] + 0) && "script(s);" && \
         (sStats["issues"] + 0) && "issue(s). Report:" && sRoot & "/rebuild_report.txt" into tSummary
   return tSummary
end xtjsonRebuild

function xtjsonRebuiltMain
   return sMainNew
end xtjsonRebuiltMain

-- ============================================================================
-- STACK / CARD / CONTROL
-- ============================================================================

private command xtBuildStack pEntry
   local tData, tNew, tStackRef, tCards, tCount, i, tLabel
   put xtReadJSON(pEntry["file"]) into tData
   if tData is not an array then
      xtLog "stack", pEntry["name"] & ": could not read" && pEntry["file"]
      exit xtBuildStack
   end if
   put sNameMap[tData["name"]] into tNew
   if tNew is empty then put kPrefix & tData["name"] into tNew
   put "stack" && quote & tData["name"] & quote into tLabel
   put empty into sIdMap

   create invisible stack tNew
   if tData["role"] is not "main" and tNew is not sMainNew then
      try
         set the mainStack of stack tNew to sMainNew
      catch tErr
         xtLog "stack", tLabel & ": could not be made a substack of" && sMainNew
      end try
   end if
   put the long id of stack tNew into tStackRef
   set the defaultStack to tNew

   if tData["rect"] is an array then
      try
         set the rect of tStackRef to xtPropValue(tData["rect"])
      catch tErr
         xtLog "rect", tLabel & ": rect could not be set"
      end try
   end if
   if tData["props"]["visible"] is true then put true into sShow[tNew]
   xtApplyProps tStackRef, tData["props"], "password,key", tLabel
   xtApplyCustom tStackRef, tData["custom"], tLabel
   xtQueueBehavior tStackRef, tData["behavior"], tLabel
   xtQueueScript tStackRef, tData["script"], tLabel

   put tData["cards"] into tCards
   put xtCount(tCards) into tCount
   repeat with i = 1 to tCount
      try
         xtBuildCard tCards[i], tStackRef, i, tData["name"]
      catch tErr
         xtLog "card", "card" && i && "of" && tLabel & ":" && line 1 of tErr
      end try
   end repeat

   -- leave the stack on its first card
   try
      go card 1 of stack tNew
   catch tErr
   end try
   add 1 to sStats["stacks"]
end xtBuildStack

private command xtBuildCard pNode, pStackRef, pNumber, pStackName
   local tCardRef, tLabel, tControls, tCount, i, tId, tBad
   put "card" && quote & pNode["name"] & quote && "(id" && pNode["id"] & ") of stack" && pStackName into tLabel

   -- a new stack already has card 1; later cards are created after the current
   -- (always the last) card and become the current card
   if pNumber > 1 then create card
   put the long id of card (the number of cards of pStackRef) of pStackRef into tCardRef

   put the id of tCardRef into tId
   if pNode["id"] is not empty and pNode["id"] is not tId then
      try
         set the id of tCardRef to pNode["id"]
         put pNode["id"] into tId
      catch tErr
         xtLog "id", tLabel & ": id not preserved, now" && tId
      end try
   end if
   put "card id" && tId && "of" && pStackRef into tCardRef

   if pNode["name"] is not empty then set the name of tCardRef to pNode["name"]
   xtApplyProps tCardRef, pNode["props"], empty, tLabel
   xtApplyCustom tCardRef, pNode["custom"], tLabel
   xtQueueBehavior tCardRef, pNode["behavior"], tLabel
   xtQueueScript tCardRef, pNode["script"], tLabel

   put pNode["controls"] into tControls
   put xtCount(tControls) into tCount
   repeat with i = 1 to tCount
      try
         xtBuildControl tControls[i], tCardRef, empty, tLabel
      catch tErr
         xtLog "control", "control" && i && "of" && tLabel & ":" && line 1 of tErr
      end try
   end repeat

   xtFixTopLayers tControls, tCardRef, tLabel
   put 0 into tBad
   xtCheckLayers tControls, tCardRef, tLabel, tBad
   if tBad > 5 then xtLog "layer", tLabel & ": ..." && (tBad - 5) && "more control(s) on a different layer"
   add 1 to sStats["cards"]
end xtBuildCard

-- pGroupClause: empty for a control directly on the card, otherwise the text
-- 'group id N of card id M of stack "..."' naming the group to create it in.
private command xtBuildControl pNode, pCardRef, pGroupClause, pWhere
   local tType, tName, tKind, tOldId, tNewId, tRef, tLabel, tCmd, tRect, tCheck
   local tKids, tCount, i, tPath, tLock, tStyle
   set the cursor to busy
   put pNode["type"] into tType
   put pNode["name"] into tName
   put pNode["id"] into tOldId
   put tType && quote & tName & quote && "(id" && tOldId & ") on" && pWhere into tLabel

   -- shared group already built on an earlier card: place it here
   if pNode["sharedRef"] is true then
      try
         do "place group id" && sIdMap[tOldId] && "onto" && pCardRef
         add 1 to sStats["placed"]
      catch tErr
         xtLog "place", tLabel & ": shared group could not be placed"
      end try
      exit xtBuildControl
   end if

   -- create (through do, so one odd type cannot stop the script compiling)
   put "create" && tType into tCmd
   if tName is not empty then put " tName" after tCmd
   if tType is "widget" then
      put pNode["kind"] into tKind
      put " as tKind" after tCmd
   end if
   if pGroupClause is not empty then put " in" && pGroupClause after tCmd
   put cr & "put it into tRef" after tCmd
   try
      do tCmd
   catch tErr
      xtLog "create", tLabel & ": could not be created:" && line 1 of tErr
      exit xtBuildControl
   end try

   -- keep the original id: icons, behaviors and scripts refer to ids
   put the id of tRef into tNewId
   if tOldId is not empty and tOldId is not tNewId then
      try
         set the id of tRef to tOldId
         put "control id" && tOldId && "of" && pCardRef into tCheck
         get the id of tCheck
         put tOldId into tNewId
      catch tErr
         xtLog "id", tLabel & ": id not preserved, now" && tNewId
      end try
   end if
   put tNewId into sIdMap[tOldId]
   put "control id" && tNewId && "of" && pCardRef into tRef
   put xtPropValue(pNode["rect"]) into tRect

   if tType is "group" then
      -- fix the frame first, build the children at their card positions inside
      -- it, then release the lock if the original group was not locked
      set the lockLoc of tRef to true
      xtSetRect tRef, tRect, tLabel, false
      xtApplyProps tRef, pNode["props"], "lockLocation,lockLoc,hScroll,vScroll,backgroundBehavior,sharedBehavior", tLabel
      xtDefer tRef, "backgroundBehavior", pNode["props"]["backgroundBehavior"], tLabel
      xtDefer tRef, "sharedBehavior", pNode["props"]["sharedBehavior"], tLabel
      put pNode["controls"] into tKids
      put xtCount(tKids) into tCount
      repeat with i = 1 to tCount
         try
            xtBuildControl tKids[i], pCardRef, "group id" && tNewId && "of" && pCardRef, tLabel
         catch tErr
            xtLog "control", "child" && i && "of" && tLabel & ":" && line 1 of tErr
         end try
      end repeat
      xtSetOne tRef, "hScroll", pNode["props"]["hScroll"], tLabel
      xtSetOne tRef, "vScroll", pNode["props"]["vScroll"], tLabel
      put (pNode["props"]["lockLocation"] is true or pNode["props"]["lockLoc"] is true) into tLock
      if not tLock then set the lockLoc of tRef to false
      xtCheckRect tRef, tRect, tLabel
   else
      -- order: style, content, remaining properties, rect
      put pNode["props"]["style"] into tStyle
      if tStyle is not empty then xtSetOne tRef, "style", tStyle, tLabel
      switch tType
         case "field"
            if pNode["htmlText"] is not empty then
               xtSetOne tRef, "htmlText", xtValue(pNode["htmlText"]), tLabel
            else if pNode["text"] is not empty then
               xtSetOne tRef, "text", xtValue(pNode["text"]), tLabel
            end if
            break
         case "button"
            if pNode["text"] is not empty then xtSetOne tRef, "text", xtValue(pNode["text"]), tLabel
            break
         case "graphic"
            if pNode["points"] is an array then xtSetOne tRef, "points", xtPoints(pNode["points"]), tLabel
            break
         case "image"
            if pNode["asset"] is not empty then
               put sRoot & "/" & pNode["asset"] into tPath
               if there is a file tPath then
                  try
                     set the text of tRef to URL ("binfile:" & tPath)
                  catch tErr
                     xtLog "asset", tLabel & ": image data could not be set"
                  end try
               else
                  xtLog "asset", tLabel & ": missing file" && pNode["asset"]
               end if
            end if
            break
      end switch
      xtApplyProps tRef, pNode["props"], "style", tLabel
      xtSetRect tRef, tRect, tLabel, true
   end if

   xtApplyCustom tRef, pNode["custom"], tLabel
   xtQueueBehavior tRef, pNode["behavior"], tLabel
   xtQueueScript tRef, pNode["script"], tLabel
   add 1 to sStats["controls"]
end xtBuildControl

-- ============================================================================
-- PROPERTIES
-- ============================================================================

private command xtApplyProps pRef, pProps, pSkip, pLabel
   local tKeys, tKey
   if pProps is not an array then exit xtApplyProps
   put the keys of pProps into tKeys
   sort lines of tKeys
   repeat for each line tKey in tKeys
      if tKey is among the items of kNeverSet then next repeat
      if pSkip is not empty and tKey is among the items of pSkip then next repeat
      xtSetOne pRef, tKey, pProps[tKey], pLabel
   end repeat
end xtApplyProps

-- Sets one built-in property by name, then reads it back and reports a difference.
private command xtSetOne pRef, pKey, pValue, pLabel
   local tVal, tBack
   if pValue is empty and pValue is not an array then
      if pKey is among the items of "hScroll,vScroll,style" then exit xtSetOne
   end if
   if not matchText(pKey, "^[A-Za-z][A-Za-z0-9]*$") then
      xtLog "prop", pLabel & ":" && pKey && "skipped, not a property name"
      exit xtSetOne
   end if
   put xtPropValue(pValue) into tVal
   try
      do "set the" && pKey && "of pRef to tVal"
   catch tErr
      xtLog "prop", pLabel & ":" && pKey && "could not be set to" && xtShort(tVal)
      exit xtSetOne
   end try
   add 1 to sStats["props"]
   if tVal is an array then exit xtSetOne
   if pKey is among the items of "htmlText,text" then exit xtSetOne
   try
      do "put the" && pKey && "of pRef into tBack"
      if tBack is not tVal then xtLog "differs", pLabel & ":" && pKey && "set to" && xtShort(tVal) && "reads back" && xtShort(tBack)
   catch tErr
   end try
end xtSetOne

private command xtSetRect pRef, pRect, pLabel, pCheck
   if pRect is empty then exit xtSetRect
   try
      set the rect of pRef to pRect
   catch tErr
      xtLog "rect", pLabel & ": rect could not be set to" && pRect
      exit xtSetRect
   end try
   if pCheck then xtCheckRect pRef, pRect, pLabel
end xtSetRect

private command xtCheckRect pRef, pRect, pLabel
   if pRect is empty then exit xtCheckRect
   if the rect of pRef is not pRect then xtLog "rect", pLabel & ": wanted" && pRect & ", got" && the rect of pRef
end xtCheckRect

private command xtDefer pRef, pKey, pValue, pLabel
   local n
   if pValue is empty then exit xtDefer
   put xtCount(sDeferred) + 1 into n
   put pRef into sDeferred[n]["ref"]
   put pKey into sDeferred[n]["key"]
   put pValue into sDeferred[n]["value"]
   put pLabel into sDeferred[n]["label"]
end xtDefer

private command xtApplyDeferred
   local tCount, i
   put xtCount(sDeferred) into tCount
   repeat with i = 1 to tCount
      xtSetOne sDeferred[i]["ref"], sDeferred[i]["key"], sDeferred[i]["value"], sDeferred[i]["label"]
   end repeat
end xtApplyDeferred

-- Top-level controls only (a grouped control's layer cannot be set): walking
-- back to front, puts each one on its harvested layer if it is not already
-- there. Setting the layer of a group moves the group with its children.
-- The card must be the current card of its stack, which it is while it is built.
private command xtFixTopLayers pNodes, pCardRef, pLabel
   local tCount, i, tNode, tRef, tGot, tWho
   put xtCount(pNodes) into tCount
   repeat with i = 1 to tCount
      put pNodes[i] into tNode
      if tNode["layer"] is empty or sIdMap[tNode["id"]] is empty then next repeat
      put "control id" && sIdMap[tNode["id"]] && "of" && pCardRef into tRef
      put tNode["type"] && quote & tNode["name"] & quote && "(id" && tNode["id"] & ") on" && pLabel into tWho
      try
         put the layer of tRef into tGot
         if tGot is not tNode["layer"] then
            set the layer of tRef to tNode["layer"]
            xtLog "layer-fixed", tWho & ": was on layer" && tGot & ", set to" && tNode["layer"]
         end if
      catch tErr
         xtLog "layer", tWho & ": layer could not be set to" && tNode["layer"] & ":" && line 1 of tErr
      end try
   end repeat
end xtFixTopLayers

-- Compares the layer each control ended up on with the harvested layer.
-- The first five differences per card are reported in full.
private command xtCheckLayers pNodes, pCardRef, pLabel, @xBad
   local tCount, i, tNode, tRef, tGot, tWho
   put xtCount(pNodes) into tCount
   repeat with i = 1 to tCount
      put pNodes[i] into tNode
      if tNode["layer"] is not empty and sIdMap[tNode["id"]] is not empty then
         put "control id" && sIdMap[tNode["id"]] && "of" && pCardRef into tRef
         put tNode["type"] && quote & tNode["name"] & quote && "(id" && tNode["id"] & ") on" && pLabel into tWho
         try
            put the layer of tRef into tGot
            if tGot is not tNode["layer"] then
               add 1 to xBad
               if xBad <= 5 then xtLog "layer", tWho & ": harvested layer" && tNode["layer"] & ", rebuilt layer" && tGot
            end if
         catch tErr
            add 1 to xBad
            if xBad <= 5 then xtLog "layer", tWho & ": not found on the rebuilt card"
         end try
      end if
      if tNode["controls"] is an array then xtCheckLayers tNode["controls"], pCardRef, pLabel, xBad
   end repeat
end xtCheckLayers

-- JSON list [1,2,3] -> "1,2,3"; anything else is passed through
private function xtPropValue pVal
   local tKeys, tKey, tCount, tOut, i
   if pVal is not an array then return pVal
   put the keys of pVal into tKeys
   put the number of lines of tKeys into tCount
   repeat for each line tKey in tKeys
      if tKey is not an integer then return pVal
   end repeat
   repeat with i = 1 to tCount
      if pVal[i] is an array then return pVal
      put comma & pVal[i] after tOut
   end repeat
   return char 2 to -1 of tOut
end xtPropValue

-- [[x,y],null,[x,y]] -> lines of "x,y" with an empty line for each null
private function xtPoints pArr
   local tMax, tKey, tOut, i
   put 0 into tMax
   repeat for each key tKey in pArr
      if tKey is an integer and tKey > tMax then put tKey into tMax
   end repeat
   repeat with i = 1 to tMax
      if pArr[i] is an array then put pArr[i][1] & comma & pArr[i][2] after tOut
      put cr after tOut
   end repeat
   delete char -1 of tOut
   return tOut
end xtPoints

-- ============================================================================
-- CUSTOM PROPERTIES
-- ============================================================================

private command xtApplyCustom pRef, pCustom, pLabel
   local tSets, tSet
   if pCustom is not an array then exit xtApplyCustom
   put pCustom["$sets"] into tSets
   delete variable pCustom["$sets"]
   if pCustom is an array then
      try
         set the customProperties of pRef to xtValue(pCustom)
      catch tErr
         xtLog "custom", pLabel & ": default custom property set could not be set"
      end try
   end if
   if tSets is an array then
      repeat for each key tSet in tSets
         try
            set the customProperties[tSet] of pRef to xtValue(tSets[tSet])
         catch tErr
            xtLog "custom", pLabel & ": custom property set" && tSet && "could not be set"
         end try
      end repeat
   end if
end xtApplyCustom

-- Resolves {$file} and {$binary} markers, recursing through nested arrays.
private function xtValue pVal
   local tKey, tPath
   if pVal is not an array then return pVal
   if pVal["$file"] is not empty then
      put sRoot & "/" & pVal["$file"] into tPath
      if there is not a file tPath then
         xtLog "blob", "missing file" && pVal["$file"]
         return empty
      end if
      if pVal["$binary"] is true then return URL ("binfile:" & tPath)
      return textDecode(URL ("binfile:" & tPath), "UTF-8")
   end if
   if pVal["$binary"] is true then
      xtLog "blob", "a binary value was not exported and is now empty"
      return empty
   end if
   repeat for each key tKey in pVal
      put xtValue(pVal[tKey]) into pVal[tKey]
   end repeat
   return pVal
end xtValue

-- ============================================================================
-- BEHAVIORS AND SCRIPTS (applied after everything exists)
-- ============================================================================

private command xtQueueBehavior pRef, pValue, pLabel
   local n
   if pValue is empty then exit xtQueueBehavior
   put xtCount(sBehaviors) + 1 into n
   put pRef into sBehaviors[n]["ref"]
   put pLabel into sBehaviors[n]["label"]
   put pValue into sBehaviors[n]["value"]
end xtQueueBehavior

private command xtQueueScript pRef, pScript, pLabel
   local n
   if pScript is not an array then exit xtQueueScript
   put xtCount(sScripts) + 1 into n
   put pRef into sScripts[n]["ref"]
   put pLabel into sScripts[n]["label"]
   put pScript["file"] into sScripts[n]["file"]
   put pScript["text"] into sScripts[n]["text"]
   put pScript["lines"] into sScripts[n]["lines"]
end xtQueueScript

private command xtApplyBehaviors
   local tCount, i, tTarget, tRef
   put xtCount(sBehaviors) into tCount
   repeat with i = 1 to tCount
      put xtRemapRef(sBehaviors[i]["value"]) into tTarget
      put sBehaviors[i]["ref"] into tRef
      try
         set the behavior of tRef to tTarget
      catch tErr
         xtLog "behavior", sBehaviors[i]["label"] & ": could not be set to" && tTarget
      end try
   end repeat
end xtApplyBehaviors

private command xtApplyScripts
   local tCount, i, tScript, tPath, tRef
   put xtCount(sScripts) into tCount
   repeat with i = 1 to tCount
      set the cursor to busy
      put sScripts[i]["ref"] into tRef
      if sScripts[i]["file"] is not empty then
         put sRoot & "/" & sScripts[i]["file"] into tPath
         if there is not a file tPath then
            xtLog "script", sScripts[i]["label"] & ": missing file" && sScripts[i]["file"]
            next repeat
         end if
         put textDecode(URL ("binfile:" & tPath), "UTF-8") into tScript
      else
         put sScripts[i]["text"] into tScript
      end if
      try
         set the script of tRef to tScript
      catch tErr
         xtLog "script", sScripts[i]["label"] & ": error while setting script:" && line 1 of tErr
      end try
      try
         if the script of tRef is not tScript then
            xtLog "script", sScripts[i]["label"] & ": script reads back different (" & the number of lines of the script of tRef && "lines, expected" && sScripts[i]["lines"] & ")"
         else
            add 1 to sStats["scripts"]
         end if
      catch tErr
      end try
   end repeat
end xtApplyScripts

-- Points a long id at the rebuilt stacks instead of the originals.
private function xtRemapRef pRef
   local tOld
   repeat for each key tOld in sNameMap
      replace ("stack " & quote & tOld & quote) with ("stack " & quote & sNameMap[tOld] & quote) in pRef
   end repeat
   if sSourceFile is not empty then
      replace ("stack " & quote & sSourceFile & quote) with ("stack " & quote & sMainNew & quote) in pRef
   end if
   return pRef
end xtRemapRef

-- ============================================================================
-- FILES, JSON, REPORT
-- ============================================================================

private function xtReadJSON pRel
   local tPath, tRaw, tArr
   put sRoot & "/" & pRel into tPath
   if there is not a file tPath then
      xtLog "file", "missing" && pRel
      return empty
   end if
   put URL ("binfile:" & tPath) into tRaw
   try
      put JsonImport(textDecode(tRaw, "UTF-8")) into tArr
      return tArr
   catch tErr
   end try
   try
      put JSONToArray(tRaw) into tArr
      xtLog "json", pRel & ": JsonImport unavailable or failed, used JSONToArray (non-ASCII text may be wrong)"
      return tArr
   catch tErr2
      xtLog "json", pRel & ": could not be parsed by JsonImport or JSONToArray"
   end try
   return empty
end xtReadJSON

private command xtWriteReport pManifest, pStart
   local tOut, tKey, tWant
   put "XTJSON rebuild report" & cr into tOut
   put "date:" && the internet date & cr after tOut
   put "folder:" && sRoot & cr after tOut
   put "livecode:" && the version && "on" && the platform & cr after tOut
   put "milliseconds:" && (the milliseconds - pStart) & cr & cr after tOut
   put "what" & tab & "harvested" & tab & "rebuilt" & cr after tOut
   repeat for each item tKey in "stacks,cards,controls,scripts"
      put empty into tWant
      if pManifest is an array then put pManifest["counts"][tKey] into tWant
      put tKey & tab & (tWant + 0) & tab & (sStats[tKey] + 0) & cr after tOut
   end repeat
   put "shared groups placed" & tab & tab & (sStats["placed"] + 0) & cr after tOut
   put "properties set" & tab & tab & (sStats["props"] + 0) & cr after tOut
   put cr & "issues:" && (sStats["issues"] + 0) & cr after tOut
   put "(kind, then detail; 'differs' means the property was set without error but reads back differently)" & cr & cr after tOut
   put sLog after tOut
   put textEncode(tOut, "UTF-8") into URL ("binfile:" & sRoot & "/rebuild_report.txt")
end xtWriteReport

private command xtLog pKind, pMessage
   put pKind & tab & pMessage & cr after sLog
   add 1 to sStats["issues"]
end xtLog

private function xtShort pVal
   if pVal is an array then return "(array)"
   replace cr with "\n" in pVal
   if length(pVal) > 60 then return quote & char 1 to 60 of pVal & "..." & quote
   return quote & pVal & quote
end xtShort

-- number of entries in a 1..n list; 0 for empty
private function xtCount pArr
   if pArr is not an array then return 0
   return the number of lines of the keys of pArr
end xtCount

-- the stack that owns this script, as a long id
private function xtMyStack
   local tLong, tOffset
   put the long id of me into tLong
   if word 1 of tLong is "stack" then return tLong
   put offset(" of stack ", tLong) into tOffset
   if tOffset is 0 then return the long id of this stack
   return char (tOffset + 4) to -1 of tLong
end xtMyStack

private function xtMyStackFolder
   local tFile, tStack
   put xtMyStack() into tStack
   put the effective filename of tStack into tFile
   if tFile is empty then put the effective filename of this stack into tFile
   set the itemDelimiter to "/"
   return item 1 to -2 of tFile
end xtMyStackFolder
