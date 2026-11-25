on mouseUp
   global gLog
   put "btn:" & the short name of me & "," after gLog
   pass mouseUp
end mouseUp
on hello p
   global gLog
   put "btnHello:" & p & "," after gLog
   pass hello
end hello
