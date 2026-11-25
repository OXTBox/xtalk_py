on mouseDown
   grab me
end mouseDown
on mouseUp
   global gLog
   put "up:" & the short name of me & "," after gLog
end mouseUp
