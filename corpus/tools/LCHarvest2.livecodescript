-- ============================================================================
-- LC HARVEST 2 -- LiveCode stack -> JSON exporter for LLMs and GUI generators
-- Target: LiveCode 9.6.3. No externals, no libraries, pure script.
-- Replaces the 2007/2021 iGame3D "Controls Harvester".
--
-- Paste into a stack script, a library stack (start using), or a behavior.
--
-- PUBLIC API
--   harvestStack [stackName] [, outFolder] [, optionsArray]
--        Whole mainstack + substacks -> files. Summary comes back in the result.
--   harvestCard [cardRef] [, outFolder] [, optionsArray]
--        One card -> one self-contained JSON file (+ script files).
--   harvestCardJSON([cardRef] [, optionsArray])        -> JSON string, no files
--   harvestControlJSON(controlRef [, optionsArray])    -> JSON string, no files
--   harvestTypeDefaultsJSON()                          -> JSON string
--   harvestErrors()                                    -> errors of the last run
--
-- OUTPUT (flat, one level deep)
--   <outFolder>/manifest.json           format notes, typeDefaults, stack list, counts
--   <outFolder>/stack_<Name>.json       stack -> cards -> controls (groups nest)
--   <outFolder>/scripts/*.livecodescript   one untouched script per scripted object
--   <outFolder>/assets/*                embedded images (png/gif/jpg/bmp)
--   <outFolder>/blobs/*                 oversize text / binary custom properties
--   Default outFolder: <folder of the stack file>/Harvest/<MainStackName>
--
-- OPTIONS (keys of optionsArray; defaults shown)
--   scripts       "files" | "inline" | "none"   ("inline" when no files are written)
--   handlerIndex  true    list each script's handlers with line numbers
--   sparse        true    props hold only values that differ from typeDefaults
--   substacks     true    false = harvest only the named stack
--   assets        true    write embedded image data to assets/
--   dedupeShared  true    a shared (background) group is written in full on the
--                         first card only; later cards get a small sharedRef stub
--   ideProps      false   true = keep the IDE's cREV* custom properties
--   clean         true    remove files of a previous harvest in outFolder first
--   maxInline     20000   longer text values go to blobs/ (0 = always inline)
--   skipCustomKeys        comma list of custom property names to ignore
--
-- The target stack is only read. Nothing in it is renamed, set or deleted.
-- (One exception, undone immediately: an object whose active customPropertySet
-- is not the default set has it switched for the moment its default set is read.)
--
-- KNOWN LIMITS
--   * Groups that are not placed on any card are not harvested.
--   * With dedupeShared, per-card text of non-sharedText fields inside a shared
--     group is only captured for the first card.
--   * Named colors ("red") are passed through as strings, not converted to RGB.
-- ============================================================================

constant kFormat = "livecode-harvest"
constant kFormatVersion = 2

-- handled explicitly, derivable from rect, deprecated duplicates, or binary
constant kSkipProps = "name,id,rect,left,top,right,bottom,width,height,loc,location,topLeft,topRight,bottomLeft,bottomRight,layer,number,script,text,htmlText,rtfText,unicodeText,styledText,unicodeLabel,unicodeTitle,unicodeToolTip,customKeys,customProperties,customPropertySet,customPropertySets,imageData,alphaData,maskData,behavior,parentScript,owner,kind,points,relativePoints"
constant kSkipStackProps = "fileName,mainStack,substacks,password,key"
-- always JSON strings, even when the content looks like a number or a list
constant kStringProps = "label,title,toolTip,textFont,fileName,menuName,acceleratorText,acceleratorKey,mnemonic,numberFormat,stackFiles,externals,dashes,markerPoints"
constant kNumRE = "\A-?(0|[1-9][0-9]*)(\.[0-9]+)?\z"
constant kIntListRE = "\A-?(0|[1-9][0-9]*)(,-?(0|[1-9][0-9]*))+\z"

local sOpt          -- options of the current run
local sOut          -- output folder, no trailing slash; empty = in-memory run
local sDefaults     -- sDefaults[type] = the properties of a freshly created object
local sErrors       -- cr list
local sCount        -- counters
local sSeenShared   -- sSeenShared[groupId] = id of the card it was first written on
local sSeenOnCard   -- sSeenOnCard[controlId] = true once written for this card
local sStackSafe    -- file-safe short name of the stack being harvested

-- ============================================================================
-- PUBLIC
-- ============================================================================

command harvestStack pStack, pOutFolder, pOptions
   local tMain, tNames, tName, tRef, tRole, tRel, tEntries, tEntry
   local tStart, tCardsBefore, tControlsBefore, tSummary
   put the milliseconds into tStart
   if pStack is empty then put the short name of this stack into pStack
   if there is not a stack pStack then return "harvest error: no such stack:" && pStack
   put the mainStack of stack pStack into tMain
   if pOutFolder is empty then put defaultOutFolder(tMain) into pOutFolder
   beginHarvest pOptions, pOutFolder

   if sOpt["substacks"] is true then
      put tMain into tNames
      if the substacks of stack tMain is not empty then
         put cr & the substacks of stack tMain after tNames
      end if
   else
      put pStack into tNames
   end if

   repeat for each line tName in tNames
      if tName is empty then next repeat
      if tName is tMain then
         put the long id of stack tMain into tRef
         put "main" into tRole
      else
         put the long id of stack tName of stack tMain into tRef
         put "substack" into tRole
      end if
      put sCount["cards"] + 0 into tCardsBefore
      put sCount["controls"] + 0 into tControlsBefore
      put "stack_" & safeName(tName) & ".json" into tRel
      try
         writeText tRel, stackNode(tRef, tRole)
      catch tErr
         logError "stack" && tName && "failed:" && line 1 of tErr
         next repeat
      end try
      put "{" & jPair("name", jStr(tName)) & ", " & jPair("role", jStr(tRole)) & ", " & \
            jPair("file", jStr(tRel)) & ", " & jPair("cards", sCount["cards"] - tCardsBefore) & ", " & \
            jPair("controls", sCount["controls"] - tControlsBefore) & "}" into tEntry
      listAdd tEntries, tEntry
   end repeat

   writeText "manifest.json", manifestJSON(tMain, tEntries, the milliseconds - tStart)

   put "harvested" && (the number of lines of tNames) && "stack(s)," && (sCount["cards"] + 0) && "card(s)," && \
         (sCount["controls"] + 0) && "control(s)," && (sCount["scripts"] + 0) && "script(s) in" && \
         (the milliseconds - tStart) && "ms ->" && sOut into tSummary
   if sErrors is not empty then put cr & (the number of lines of sErrors) && "error(s), see harvestErrors()" after tSummary
   return tSummary
end harvestStack

command harvestCard pCardRef, pOutFolder, pOptions
   local tCard, tStackRef, tMain, tBody, tRel
   if pCardRef is empty then put the long id of this card into tCard
   else put the long id of pCardRef into tCard
   put stackRefOf(tCard) into tStackRef
   put the mainStack of tStackRef into tMain
   if pOutFolder is empty then put defaultOutFolder(tMain) into pOutFolder
   if pOptions is not an array then put empty into pOptions
   put false into pOptions["clean"]
   put false into pOptions["dedupeShared"]
   beginHarvest pOptions, pOutFolder
   put safeName(the short name of tStackRef) into sStackSafe
   put empty into sSeenShared
   jAdd tBody, "format", jStr(kFormat)
   jAdd tBody, "formatVersion", kFormatVersion
   jAdd tBody, "stack", jStr(the short name of tStackRef)
   jAdd tBody, "conventions", conventionsJSON()
   jAdd tBody, "typeDefaults", typeDefaultsJSON()
   jAdd tBody, "card", cardNode(tCard, the number of tCard)
   put "card_" & sStackSafe & "_" & the id of tCard & ".json" into tRel
   writeText tRel, jNode(tBody)
   return sOut & "/" & tRel
end harvestCard

function harvestCardJSON pCardRef, pOptions
   local tCard, tStackRef
   if pCardRef is empty then put the long id of this card into tCard
   else put the long id of pCardRef into tCard
   put stackRefOf(tCard) into tStackRef
   beginHarvest pOptions, empty
   put safeName(the short name of tStackRef) into sStackSafe
   put empty into sSeenShared
   return cardNode(tCard, the number of tCard)
end harvestCardJSON

function harvestControlJSON pControlRef, pOptions
   local tLong, tId, tStackRef, tCard, tOffset
   put the long id of pControlRef into tLong
   put the id of tLong into tId
   put stackRefOf(tLong) into tStackRef
   put offset(" of card id ", tLong) into tOffset
   if tOffset > 0 then
      put char (tOffset + 4) to -1 of tLong into tCard
   else
      put the long id of this card of tStackRef into tCard
   end if
   beginHarvest pOptions, empty
   put safeName(the short name of tStackRef) into sStackSafe
   put empty into sSeenShared
   put empty into sSeenOnCard
   return controlNode("control id" && tId && "of" && tCard, tCard, tId)
end harvestControlJSON

function harvestTypeDefaultsJSON
   if sOpt is not an array then beginHarvest empty, empty
   if sDefaults is not an array then buildDefaults
   return typeDefaultsJSON()
end harvestTypeDefaultsJSON

function harvestErrors
   return sErrors
end harvestErrors

-- ============================================================================
-- RUN SETUP
-- ============================================================================

private command beginHarvest pOptions, pOutFolder
   local tKey
   put empty into sOpt
   put "files" into sOpt["scripts"]
   put true into sOpt["handlerIndex"]
   put true into sOpt["sparse"]
   put true into sOpt["substacks"]
   put true into sOpt["assets"]
   put true into sOpt["dedupeShared"]
   put false into sOpt["ideProps"]
   put true into sOpt["clean"]
   put 20000 into sOpt["maxInline"]
   -- bookkeeping properties the old harvester left on the mainstack
   put "scriptBackUpPathList,propsBackUpPathList,functionRecord,handlerRecord,scriptLineCount,defaultBackupPath" into sOpt["skipCustomKeys"]
   if pOptions is an array then
      repeat for each key tKey in pOptions
         put pOptions[tKey] into sOpt[tKey]
      end repeat
   end if

   if char -1 of pOutFolder is "/" then delete char -1 of pOutFolder
   put pOutFolder into sOut
   put empty into sErrors
   put empty into sCount
   put empty into sSeenShared
   put empty into sSeenOnCard

   if sOut is empty then
      -- in-memory run: nothing may touch the disk
      if sOpt["scripts"] is "files" then put "inline" into sOpt["scripts"]
      put false into sOpt["assets"]
      put 0 into sOpt["maxInline"]
   else
      if sOpt["clean"] is true then cleanOutput
      ensureFolder sOut
   end if

   if sOpt["sparse"] is true and sDefaults is not an array then buildDefaults
end beginHarvest

private function defaultOutFolder pMain
   local tFile
   put the effective filename of stack pMain into tFile
   if tFile is empty then
      put specialFolderPath("documents") into tFile
   else
      set the itemDelimiter to "/"
      put item 1 to -2 of tFile into tFile
   end if
   return tFile & "/Harvest/" & safeName(pMain)
end defaultOutFolder

-- Only empties a folder that carries a manifest written by this script.
private command cleanOutput
   local tOld, tSub, tFile
   if there is not a file (sOut & "/manifest.json") then exit cleanOutput
   put URL ("binfile:" & sOut & "/manifest.json") into tOld
   if offset(kFormat, tOld) is 0 then exit cleanOutput
   repeat for each item tSub in "scripts,assets,blobs"
      if there is a folder (sOut & "/" & tSub) then
         repeat for each line tFile in files(sOut & "/" & tSub)
            if tFile is not empty then delete file (sOut & "/" & tSub & "/" & tFile)
         end repeat
      end if
   end repeat
   repeat for each line tFile in files(sOut)
      if tFile begins with "stack_" and tFile ends with ".json" then delete file (sOut & "/" & tFile)
   end repeat
end cleanOutput

-- Records what a freshly created object of each type looks like, using a
-- throwaway invisible stack. These become typeDefaults in the manifest.
private command buildDefaults
   local tOldDefault, tTmp, tType
   put empty into sDefaults
   put the defaultStack into tOldDefault
   put "lcHarvestDefaults" & the milliseconds into tTmp
   lock screen
   lock messages
   try
      create invisible stack tTmp
      set the defaultStack to tTmp
      put the properties of stack tTmp into sDefaults["stack"]
      put the properties of card 1 of stack tTmp into sDefaults["card"]
      repeat for each item tType in "button,field,graphic,image,scrollbar,group,player"
         try
            switch tType
               case "button"
                  create button
                  break
               case "field"
                  create field
                  break
               case "graphic"
                  create graphic
                  break
               case "image"
                  create image
                  break
               case "scrollbar"
                  create scrollbar
                  break
               case "group"
                  create group
                  break
               case "player"
                  create player
                  break
            end switch
            put the properties of it into sDefaults[tType]
         catch tErr2
            -- type not available on this platform: its props are written in full
         end try
      end repeat
   catch tErr
      logError "could not build type defaults (props written in full):" && line 1 of tErr
   end try
   if there is a stack tTmp then delete stack tTmp
   if tOldDefault is not empty then set the defaultStack to tOldDefault
   unlock messages
   unlock screen
end buildDefaults

-- ============================================================================
-- NODES: stack -> card -> control
-- ============================================================================

private function stackNode pStackRef, pRole
   local tBody, tName, tCards, tCount, i, tCardRef
   put the short name of pStackRef into tName
   put safeName(tName) into sStackSafe
   put empty into sSeenShared

   put jPair("type", jStr("stack")) & ", " & jPair("name", jStr(tName)) & ", " & \
         jPair("role", jStr(pRole)) & ", " & jPair("id", the id of pStackRef) into tBody
   jAdd tBody, "rect", "[" & the rect of pStackRef & "]"
   jAdd tBody, "size", "[" & the width of pStackRef & "," & the height of pStackRef & "]"
   jAdd tBody, "file", jStr(the effective filename of pStackRef)
   jAdd tBody, "props", propsJSON(pStackRef, "stack")
   jAdd tBody, "effective", effectiveJSON(pStackRef)
   jAdd tBody, "behavior", behaviorJSON(pStackRef)
   jAdd tBody, "custom", customJSON(pStackRef, sStackSafe & "__stack")
   jAdd tBody, "script", scriptJSON(pStackRef, sStackSafe & "__stack")

   put the number of cards of pStackRef into tCount
   repeat with i = 1 to tCount
      try
         put the long id of card i of pStackRef into tCardRef
         listAdd tCards, cardNode(tCardRef, i)
      catch tErr
         logError "card" && i && "of stack" && tName && "failed:" && line 1 of tErr
      end try
   end repeat
   jAdd tBody, "cards", jList(tCards)
   add 1 to sCount["stacks"]
   return jNode(tBody)
end stackNode

private function cardNode pCardRef, pNumber
   local tBody, tId, tName, tBase, tItems, tCount, i, tCtlId
   put the id of pCardRef into tId
   put the short name of pCardRef into tName
   if tName is ("card id" && tId) then put empty into tName
   put sStackSafe & "__card_" & tId & nameSuffix(tName) into tBase
   put empty into sSeenOnCard

   put jPair("type", jStr("card")) & ", " & jPair("name", jStr(tName)) & ", " & \
         jPair("id", tId) & ", " & jPair("number", pNumber) into tBody
   jAdd tBody, "props", propsJSON(pCardRef, "card")
   jAdd tBody, "behavior", behaviorJSON(pCardRef)
   jAdd tBody, "custom", customJSON(pCardRef, tBase)
   jAdd tBody, "script", scriptJSON(pCardRef, tBase)

   -- Controls come in layer order, back to front. A group is met before its
   -- children; controlNode marks the children it writes, so they are skipped here.
   put the number of controls of pCardRef into tCount
   repeat with i = 1 to tCount
      try
         put the id of control i of pCardRef into tCtlId
         if sSeenOnCard[tCtlId] is true then next repeat
         listAdd tItems, controlNode("control id" && tCtlId && "of" && pCardRef, pCardRef, tCtlId)
      catch tErr
         logError "control" && i && "of" && pCardRef && "failed:" && line 1 of tErr
      end try
   end repeat
   jAdd tBody, "controls", jList(tItems)
   add 1 to sCount["cards"]
   return jNode(tBody)
end cardNode

private function controlNode pRef, pCardRef, pId
   local tBody, tType, tName, tBase, tText, tHtml, tProbe, tKids, tChildId, tStyle
   put true into sSeenOnCard[pId]
   put word 1 of the name of pRef into tType
   if tType is "bkgnd" or tType is "background" then put "group" into tType
   put the short name of pRef into tName
   if tName is (tType && "id" && pId) then put empty into tName
   put sStackSafe & "__" & tType & "_" & pId & nameSuffix(tName) into tBase

   put jPair("type", jStr(tType)) & ", " & jPair("name", jStr(tName)) & ", " & \
         jPair("id", pId) & ", " & jPair("layer", the layer of pRef) & ", " & \
         jPair("rect", "[" & the rect of pRef & "]") into tBody

   -- a group already written on an earlier card of this stack
   if tType is "group" and sOpt["dedupeShared"] is true then
      if sSeenShared[pId] is not empty then
         markDescendantsSeen pRef, pCardRef
         put ", " & jPair("sharedRef", "true") & ", " & jPair("definedOnCard", sSeenShared[pId]) after tBody
         return "{" & tBody & "}"
      end if
      put the id of pCardRef into sSeenShared[pId]
   end if

   if tType is "widget" then jAdd tBody, "kind", jStr(the kind of pRef)
   jAdd tBody, "props", propsJSON(pRef, tType)

   switch tType
      case "field"
         put the text of pRef into tText
         if tText is not empty then
            jAdd tBody, "text", textValueJSON(tText, tBase & "__text")
            -- htmlText only when it carries styling beyond plain paragraphs
            put the htmlText of pRef into tHtml
            put tHtml into tProbe
            replace "<p>" with empty in tProbe
            replace "</p>" with empty in tProbe
            if tProbe contains "<" then jAdd tBody, "htmlText", textValueJSON(tHtml, tBase & "__html")
         end if
         break
      case "button"
         -- menu contents for menu-style buttons
         put the text of pRef into tText
         if tText is not empty then jAdd tBody, "text", textValueJSON(tText, tBase & "__text")
         break
      case "graphic"
         put the style of pRef into tStyle
         if tStyle is among the items of "polygon,line,curve" then jAdd tBody, "points", pointsJSON(the points of pRef)
         break
      case "image"
         jAdd tBody, "asset", imageAssetJSON(pRef, pCardRef, pId, tBase)
         break
   end switch

   jAdd tBody, "behavior", behaviorJSON(pRef)
   jAdd tBody, "custom", customJSON(pRef, tBase)
   jAdd tBody, "script", scriptJSON(pRef, tBase)

   if tType is "group" then
      repeat for each line tChildId in the childControlIDs of pRef
         if tChildId is empty then next repeat
         try
            listAdd tKids, controlNode("control id" && tChildId && "of" && pCardRef, pCardRef, tChildId)
         catch tErr
            logError "control id" && tChildId && "of" && pCardRef && "failed:" && line 1 of tErr
         end try
      end repeat
      jAdd tBody, "controls", jList(tKids)
   end if

   add 1 to sCount["controls"]
   add 1 to sCount[tType & "s"]
   return jNode(tBody)
end controlNode

private command markDescendantsSeen pGroupRef, pCardRef
   local tChildId, tChild
   repeat for each line tChildId in the childControlIDs of pGroupRef
      if tChildId is empty then next repeat
      put true into sSeenOnCard[tChildId]
      put "control id" && tChildId && "of" && pCardRef into tChild
      if word 1 of the name of tChild is "group" then markDescendantsSeen tChild, pCardRef
   end repeat
end markDescendantsSeen

-- ============================================================================
-- PROPERTIES
-- ============================================================================

private function propsJSON pRef, pType
   local tProps, tDef
   try
      put the properties of pRef into tProps
   catch tErr
      logError "properties unreadable:" && pRef
      return empty
   end try
   if sOpt["sparse"] is true and (sDefaults[pType] is an array) then put sDefaults[pType] into tDef
   return compactProps(tProps, tDef, pType)
end propsJSON

-- pDef is an array: write only values that differ from it (an emptied value is
-- written as ""). pDef is empty: write every non-empty value.
private function compactProps pProps, pDef, pType
   local tKeys, tKey, tVal, tOut, tHasDef
   if pProps is not an array then return empty
   put (pDef is an array) into tHasDef
   put the keys of pProps into tKeys
   sort lines of tKeys
   repeat for each line tKey in tKeys
      if tKey is among the items of kSkipProps then next repeat
      if pType is "stack" and tKey is among the items of kSkipStackProps then next repeat
      put pProps[tKey] into tVal
      if tVal is an array then
         put ", " & jPair(tKey, jArray(tVal)) after tOut
         next repeat
      end if
      if isBinary(tVal) then next repeat
      if tHasDef and (pDef[tKey] is not an array) and (tVal is pDef[tKey]) then next repeat
      if (not tHasDef) and tVal is empty then next repeat
      if tKey is among the items of kStringProps then
         put ", " & jPair(tKey, jStr(tVal)) after tOut
      else
         put ", " & jPair(tKey, jAuto(tVal)) after tOut
      end if
   end repeat
   if tOut is empty then return empty
   return "{" & char 3 to -1 of tOut & "}"
end compactProps

-- What an object with no text/color settings of its own finally inherits.
private function effectiveJSON pRef
   local tOut, tVal
   try
      put the effective textFont of pRef into tVal
      if tVal is not empty then put ", " & jPair("textFont", jStr(tVal)) after tOut
      put the effective textSize of pRef into tVal
      if tVal is not empty then put ", " & jPair("textSize", jAuto(tVal)) after tOut
      put the effective textStyle of pRef into tVal
      if tVal is not empty then put ", " & jPair("textStyle", jStr(tVal)) after tOut
      put the effective foregroundColor of pRef into tVal
      if tVal is not empty then put ", " & jPair("foregroundColor", jAuto(tVal)) after tOut
      put the effective backgroundColor of pRef into tVal
      if tVal is not empty then put ", " & jPair("backgroundColor", jAuto(tVal)) after tOut
   catch tErr
   end try
   if tOut is empty then return empty
   return "{" & char 3 to -1 of tOut & "}"
end effectiveJSON

private function behaviorJSON pRef
   local tBehavior
   try
      put the behavior of pRef into tBehavior
   catch tErr
      return empty
   end try
   if tBehavior is empty then return empty
   return jStr(tBehavior)
end behaviorJSON

private function pointsJSON pPoints
   local tOut, tLine
   repeat for each line tLine in pPoints
      if tLine is empty then
         put ",null" after tOut   -- a break in the path
      else if matchText(tLine, kIntListRE) then
         put ",[" & tLine & "]" after tOut
      else
         put "," & jStr(tLine) after tOut
      end if
   end repeat
   if tOut is empty then return empty
   return "[" & char 2 to -1 of tOut & "]"
end pointsJSON

private function imageAssetJSON pRef, pCardRef, pId, pBase
   local tData, tSuffix, tRel, tPath
   if sOpt["assets"] is not true then return empty
   if the fileName of pRef is not empty then return empty
   put the text of pRef into tData
   if tData is empty then return empty
   if byte 2 to 4 of tData is "PNG" then
      put "png" into tSuffix
   else if byte 1 to 3 of tData is "GIF" then
      put "gif" into tSuffix
   else if byteToNum(byte 1 of tData) is 255 and byteToNum(byte 2 of tData) is 216 then
      put "jpg" into tSuffix
   else if byte 1 to 2 of tData is "BM" then
      put "bmp" into tSuffix
   end if
   if tSuffix is not empty then
      put "assets/" & pBase & "." & tSuffix into tRel
      writeBinary tRel, tData
      return jStr(tRel)
   end if
   -- painted image in the engine's internal format: ask the engine for a PNG
   put "assets/" & pBase & ".png" into tRel
   put sOut & "/" & tRel into tPath
   ensureFolder sOut & "/assets"
   try
      do "export image id" && pId && "of" && pCardRef && "to file tPath as PNG"
      add 1 to sCount["files"]
      return jStr(tRel)
   catch tErr
      logError "image id" && pId && "could not be exported"
   end try
   return empty
end imageAssetJSON

-- ============================================================================
-- CUSTOM PROPERTIES
-- ============================================================================

private function customJSON pRef, pBase
   local tBody, tArr, tActive, tSets, tSet, tSetsBody, tJSON
   try
      put the customPropertySet of pRef into tActive
      if tActive is empty then
         put the customProperties of pRef into tArr
      else
         lock messages
         set the customPropertySet of pRef to empty
         put the customProperties of pRef into tArr
         set the customPropertySet of pRef to tActive
         unlock messages
      end if
      put customSetBody(tArr, pBase) into tBody

      put the customPropertySets of pRef into tSets
      sort lines of tSets
      repeat for each line tSet in tSets
         if tSet is empty then next repeat
         if sOpt["ideProps"] is not true and tSet begins with "cREV" then next repeat
         put customSetBody(the customProperties[tSet] of pRef, pBase & "__" & safeName(tSet)) into tJSON
         if tJSON is not empty then jAdd tSetsBody, tSet, jNode(tJSON)
      end repeat
      if tSetsBody is not empty then jAdd tBody, "$sets", jNode(tSetsBody)
   catch tErr
      logError "custom properties unreadable:" && pRef
   end try
   if tBody is empty then return empty
   return jNode(tBody)
end customJSON

private function customSetBody pArr, pBase
   local tBody, tKeys, tKey, tVal
   if pArr is not an array then return empty
   put the keys of pArr into tKeys
   sort lines of tKeys
   repeat for each line tKey in tKeys
      if tKey is empty then next repeat
      if sOpt["ideProps"] is not true and tKey begins with "cREV" then next repeat
      if tKey is among the items of sOpt["skipCustomKeys"] then next repeat
      put pArr[tKey] into tVal
      if tVal is an array then
         jAdd tBody, tKey, jArray(tVal)
      else if tVal is not empty then
         jAdd tBody, tKey, customValueJSON(tVal, pBase & "__" & safeName(tKey))
      end if
   end repeat
   return tBody
end customSetBody

private function customValueJSON pVal, pBlobBase
   local tRel
   if isBinary(pVal) then
      if sOut is not empty and sOpt["assets"] is true then
         put "blobs/" & pBlobBase & ".bin" into tRel
         writeBinary tRel, pVal
         return "{" & jPair("$binary", "true") & ", " & jPair("bytes", length(pVal)) & ", " & jPair("$file", jStr(tRel)) & "}"
      end if
      return "{" & jPair("$binary", "true") & ", " & jPair("bytes", length(pVal)) & "}"
   end if
   if isOversize(pVal) then return blobJSON(pVal, pBlobBase)
   return jScalar(pVal)
end customValueJSON

private function textValueJSON pVal, pBlobBase
   if isOversize(pVal) then return blobJSON(pVal, pBlobBase)
   return jStr(pVal)
end textValueJSON

private function isOversize pVal
   if sOut is empty then return false
   if sOpt["maxInline"] is not a number then return false
   if sOpt["maxInline"] <= 0 then return false
   return (length(pVal) > sOpt["maxInline"])
end isOversize

private function blobJSON pVal, pBlobBase
   local tRel
   put "blobs/" & pBlobBase & ".txt" into tRel
   writeText tRel, pVal
   return "{" & jPair("$file", jStr(tRel)) & ", " & jPair("chars", length(pVal)) & "}"
end blobJSON

-- ============================================================================
-- SCRIPTS
-- ============================================================================

private function scriptJSON pRef, pBase
   local tScript, tBody, tRel
   if sOpt["scripts"] is "none" then return empty
   try
      put the script of pRef into tScript
   catch tErr
      logError "script unreadable (password protected?):" && pRef
      return empty
   end try
   if word 1 of tScript is empty then return empty

   if sOpt["scripts"] is "files" then
      put "scripts/" & pBase & ".livecodescript" into tRel
      writeText tRel, tScript   -- written untouched so it can be pasted straight back
      put jPair("file", jStr(tRel)) & ", " & jPair("lines", the number of lines of tScript) into tBody
   else
      put jPair("lines", the number of lines of tScript) into tBody
      jAdd tBody, "text", jStr(tScript)
   end if
   if sOpt["handlerIndex"] is true then jAdd tBody, "handlers", jList(handlerItems(tScript))
   add 1 to sCount["scripts"]
   return jNode(tBody)
end scriptJSON

-- One entry per handler: line number, type, name, parameters.
private function handlerItems pScript
   local tItems, tLineNo, tLine, tWord, tOff, tPrivate, tName, tParams, tMark, tPos, tInBlock, tEntry
   put 0 into tLineNo
   put false into tInBlock
   repeat for each line tLine in pScript
      add 1 to tLineNo
      if tInBlock then
         if tLine contains "*/" then put false into tInBlock
         next repeat
      end if
      put word 1 of tLine into tWord
      if tWord begins with "/*" then
         if not (tLine contains "*/") then put true into tInBlock
         next repeat
      end if
      put 0 into tOff
      put false into tPrivate
      if tWord is "private" then
         put true into tPrivate
         put 1 into tOff
         put word 2 of tLine into tWord
      end if
      if tWord is not among the items of "on,command,function,getProp,setProp" then next repeat
      put word (2 + tOff) of tLine into tName
      if tName is empty then next repeat
      put word (3 + tOff) to -1 of tLine into tParams
      repeat for each item tMark in "--,#,//"
         put offset(tMark, tParams) into tPos
         if tPos > 0 then put char 1 to (tPos - 1) of tParams into tParams
      end repeat
      put word 1 to -1 of tParams into tParams
      put "{" & jPair("line", tLineNo) & ", " & jPair("type", jStr(toLower(tWord))) & ", " & jPair("name", jStr(tName)) into tEntry
      if tParams is not empty then put ", " & jPair("params", jStr(tParams)) after tEntry
      if tPrivate then put ", " & jPair("private", "true") after tEntry
      put "}" after tEntry
      listAdd tItems, tEntry
   end repeat
   return tItems
end handlerItems

-- ============================================================================
-- MANIFEST
-- ============================================================================

private function manifestJSON pMain, pStackEntries, pMs
   local tBody, tErrs, tLine
   jAdd tBody, "format", jStr(kFormat)
   jAdd tBody, "formatVersion", kFormatVersion
   jAdd tBody, "harvested", jStr(the internet date)
   jAdd tBody, "livecodeVersion", jStr(the version)
   jAdd tBody, "platform", jStr(the platform)
   jAdd tBody, "mainStack", jStr(pMain)
   jAdd tBody, "sourceFile", jStr(the effective filename of stack pMain)
   jAdd tBody, "milliseconds", pMs
   jAdd tBody, "conventions", conventionsJSON()
   jAdd tBody, "options", jArray(sOpt)
   jAdd tBody, "counts", jArray(sCount)
   jAdd tBody, "stacks", jList(pStackEntries)
   jAdd tBody, "typeDefaults", typeDefaultsJSON()
   repeat for each line tLine in sErrors
      if tLine is not empty then listAdd tErrs, jStr(tLine)
   end repeat
   jAdd tBody, "errors", jList(tErrs)
   return jNode(tBody)
end manifestJSON

private function conventionsJSON
   local tItems
   listAdd tItems, jStr("Hierarchy: stack -> cards[] -> controls[]; a group nests its children in its own controls[].")
   listAdd tItems, jStr("controls[] is in layer order, back to front. layer is the control's layer number on its card (1 = backmost); a group and each of its children have their own layer numbers.")
   listAdd tItems, jStr("rect is [left, top, right, bottom] in pixels. Origin is the top-left of the card, y grows downward. A stack's rect is in screen coordinates; its size is [width, height].")
   listAdd tItems, jStr("props holds only the properties that differ from typeDefaults[type]. A property missing from both is empty or unset. With option sparse=false props holds every non-empty property instead.")
   listAdd tItems, jStr("Colors are [r, g, b], or a LiveCode color name or #hex string. A missing color or text property is inherited: control -> group -> card -> stack -> stack.effective.")
   listAdd tItems, jStr("icon, hiliteIcon and pattern values are ids of image objects.")
   listAdd tItems, jStr("custom holds the default custom property set; custom.$sets holds named sets. Empty custom properties are omitted.")
   listAdd tItems, jStr("script.file points to the unmodified script; script.handlers[].line is a 1-based line number in it.")
   listAdd tItems, jStr("{$file, chars} means the text value is stored in that file. {$binary, bytes} marks binary data.")
   listAdd tItems, jStr("A group with sharedRef:true is a shared group written in full on the card whose id is definedOnCard.")
   listAdd tItems, jStr("An empty name means the object was never named.")
   return jList(tItems)
end conventionsJSON

private function typeDefaultsJSON
   local tBody, tTypes, tType, tJSON
   if sDefaults is not an array then return empty
   put the keys of sDefaults into tTypes
   sort lines of tTypes
   repeat for each line tType in tTypes
      put compactProps(sDefaults[tType], empty, tType) into tJSON
      if tJSON is not empty then jAdd tBody, tType, tJSON
   end repeat
   if tBody is empty then return empty
   return jNode(tBody)
end typeDefaultsJSON

-- ============================================================================
-- JSON WRITER
-- Built as text so key order is fixed and types are predictable. Multi-line
-- nodes are joined with cr; encoded strings never contain a raw cr, so nested
-- blocks can be indented with a plain replace.
-- ============================================================================

private function jStr pText
   local i
   replace "\" with "\\" in pText
   replace quote with ("\" & quote) in pText
   replace numToCodepoint(10) with "\n" in pText
   replace numToCodepoint(13) with "\r" in pText
   replace numToCodepoint(9) with "\t" in pText
   if matchText(pText, "[\x00-\x08\x0B\x0C\x0E-\x1F]") then
      repeat with i = 0 to 31
         replace numToCodepoint(i) with ("\u" & format("%04x", i)) in pText
      end repeat
   end if
   return quote & pText & quote
end jStr

private function jPair pKey, pJSON
   return jStr(pKey) & ": " & pJSON
end jPair

-- adds "key": value as a new line of a node body; empty values are left out
private command jAdd @xBody, pKey, pJSON
   if pJSON is empty then exit jAdd
   if xBody is not empty then put "," & cr after xBody
   put jStr(pKey) & ": " & pJSON after xBody
end jAdd

private command listAdd @xList, pJSON
   if pJSON is empty then exit listAdd
   if xList is not empty then put "," & cr after xList
   put pJSON after xList
end listAdd

private function jNode pBody
   if pBody is empty then return "{}"
   replace cr with (cr & "  ") in pBody
   return "{" & cr & "  " & pBody & cr & "}"
end jNode

private function jList pItems
   if pItems is empty then return "[]"
   replace cr with (cr & "  ") in pItems
   return "[" & cr & "  " & pItems & cr & "]"
end jList

-- booleans and plain numbers typed, everything else a string
private function jScalar pVal
   if pVal is "true" then return "true"
   if pVal is "false" then return "false"
   if matchText(pVal, kNumRE) then return pVal
   return jStr(pVal)
end jScalar

-- as jScalar, plus "1,2,3" integer lists (rects, points, rgb colors) -> [1,2,3]
private function jAuto pVal
   if pVal is an array then return jArray(pVal)
   if pVal is "true" then return "true"
   if pVal is "false" then return "false"
   if matchText(pVal, kNumRE) then return pVal
   if matchText(pVal, kIntListRE) then return "[" & pVal & "]"
   return jStr(pVal)
end jAuto

-- LiveCode array -> JSON. Keys 1..n become a JSON array, anything else an
-- object with sorted keys. Nested arrays recurse.
private function jArray pArr
   local tKeys, tCount, tKey, tIsList, tOut, i
   if pArr is not an array then return "{}"
   put the keys of pArr into tKeys
   put the number of lines of tKeys into tCount
   put true into tIsList
   repeat for each line tKey in tKeys
      if tKey is not an integer then
         put false into tIsList
         exit repeat
      end if
      if tKey < 1 or tKey > tCount then
         put false into tIsList
         exit repeat
      end if
   end repeat
   if tIsList then
      repeat with i = 1 to tCount
         put "," & jAny(pArr[i]) after tOut
      end repeat
      return "[" & char 2 to -1 of tOut & "]"
   end if
   sort lines of tKeys
   repeat for each line tKey in tKeys
      put ", " & jPair(tKey, jAny(pArr[tKey])) after tOut
   end repeat
   return "{" & char 3 to -1 of tOut & "}"
end jArray

private function jAny pVal
   if pVal is an array then return jArray(pVal)
   if isBinary(pVal) then return "{" & jPair("$binary", "true") & ", " & jPair("bytes", length(pVal)) & "}"
   return jScalar(pVal)
end jAny

private function isBinary pVal
   return (pVal contains numToCodepoint(0))
end isBinary

-- ============================================================================
-- FILES AND NAMES
-- ============================================================================

private command writeText pRel, pText
   writeBinary pRel, textEncode(pText, "UTF-8")
end writeText

private command writeBinary pRel, pData
   local tPath
   put sOut & "/" & pRel into tPath
   set the itemDelimiter to "/"
   ensureFolder item 1 to -2 of tPath
   put pData into URL ("binfile:" & tPath)
   if the result is not empty then
      logError "write failed:" && pRel && "(" & the result & ")"
   else
      add 1 to sCount["files"]
   end if
end writeBinary

private command ensureFolder pPath
   if pPath is empty then exit ensureFolder
   if there is a folder pPath then exit ensureFolder
   set the itemDelimiter to "/"
   ensureFolder item 1 to -2 of pPath
   create folder pPath
end ensureFolder

private function safeName pName
   return replaceText(pName, "[^A-Za-z0-9_\-]+", "_")
end safeName

private function nameSuffix pName
   if pName is empty then return empty
   return "_" & char 1 to 40 of safeName(pName)
end nameSuffix

-- 'card id 1002 of stack "sub" of stack "/path/main.livecode"' -> the stack part
private function stackRefOf pLongId
   local tOffset
   put offset(" of stack ", pLongId) into tOffset
   if tOffset is 0 then return the long id of this stack
   return char (tOffset + 4) to -1 of pLongId
end stackRefOf

private command logError pMessage
   put pMessage & cr after sErrors
end logError
