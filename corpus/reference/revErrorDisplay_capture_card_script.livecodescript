-- ============================================================================
-- The user's card script for capturing stack "revErrorDisplay", exactly as
-- written on 2026-11-11, kept for testing. It stores what it reads in the
-- custom property "savedStack", in a custom property set named after the
-- captured stack, on card 1 of the mainstack.
--
-- Known problems in this version (see docs/harvest/XTJSON_ROUNDTRIP.md):
--   1. "exitcaptureStackText" is missing a space: exit captureStackText
--   2. tObjects[i] is given the name, then tObjects[i]["label"] turns that
--      element into an array, so the name is lost. Use tObjects[i]["name"].
--   3. "label of control i" is outside the try: a control type without a
--      label raises "Object: does not have this property", like text did.
--   4. preopenstack has no try: it fails when revErrorDisplay is not loaded.
-- xt_error_capture.livecodescript is a version without these problems that
-- returns the text instead of storing it.
-- ============================================================================

global gStack
on preopenstack
   put the long ID of stack "revErrorDisplay" into gStack
end preopenstack

on mouseUp
   preopenstack
   captureStackText
end mouseUp

on captureStackText pStack
   if gStack is empty then
      try
         put the long ID of stack "revErrorDisplay" into gStack
      end try
   end if

   if pStack is not empty then put pStack into gStack
   if word 1 of gStack is not "stack" then exitcaptureStackText

   repeat with i = 1 to number of controls of gStack
      put name of control i of gStack into tObjects[i]
      put label of control i of gStack into tObjects[i]["label"]
      try
         put the text of control i of gStack into tObjects[i]["text"]
      end try
      put the long name of control i of gStack into tObjects[i]["long"]
   end repeat
   put the short name of gStack into tsaveStack
   set the customPropertySet of card 1 of stack (The mainStack of this stack) to tsaveStack
   set the savedStack of card 1 of stack (The mainStack of this stack) to tObjects
   set the customPropertySet of card 1 of stack (The mainStack of this stack) to empty

end captureStackText
