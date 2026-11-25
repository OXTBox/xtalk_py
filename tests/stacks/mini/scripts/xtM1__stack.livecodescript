on preOpenStack
   global gLog
   put "preOpenStack," after gLog
end preOpenStack
on openCard
   global gLog
   put "openCard:" & the short name of this card & "," after gLog
end openCard
on mouseUp
   global gLog
   put "stackMouseUp:" & the short name of the target & "," after gLog
end mouseUp
on hello p
   global gLog
   put "stackHello:" & p & "," after gLog
end hello
on tickTock pN
   global gLog
   put "tick" & pN & "," after gLog
   if pN < 3 then send "tickTock" && pN + 1 to me in 100 milliseconds
end tickTock
