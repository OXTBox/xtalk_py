on mouseDown
   -- the mouse is not inside graphic G2: nothing happens (Dictionary, grab)
   grab graphic "G2"
end mouseDown
on mouseUp
   global gLog
   put "up:" & the short name of me & "," after gLog
end mouseUp
on mouseMove x,y
   global gLog
   put "mv:" & x & "/" & y & ";" after gLog
end mouseMove
on mouseEnter
   global gLog
   put "in;" after gLog
end mouseEnter
on mouseLeave
   global gLog
   put "out;" after gLog
end mouseLeave
on mouseRelease
   global gLog
   put "rel;" after gLog
end mouseRelease
