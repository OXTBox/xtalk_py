on openField
   global gLog
   put "open;" after gLog
end openField
on closeField
   global gLog
   put "close;" after gLog
end closeField
on exitField
   global gLog
   put "exit;" after gLog
end exitField
on keyDown k
   if k is "x" then exit keyDown
   pass keyDown
end keyDown
