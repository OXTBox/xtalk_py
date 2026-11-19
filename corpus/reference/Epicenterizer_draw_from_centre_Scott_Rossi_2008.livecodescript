## From Scott Rossi's "Epicenterizer" stack  Oct. 8, 2008.
## Click and drag produces circle, rectangle or Triangle from their center instead of from their lower right edge.

local uAllowScale,currObj

on mouseDown
  put short name of btn (the hilitedbutton of grp 1) of grp 1 into tName
  put long id of grc tName into currObj
  show currObj at mouseH(),mouseV()
  put true into uAllowScale
end mouseDown

on mouseMove X,Y
  if not uAllowScale then exit mouseMove
  put loc of currObj into tLoc
  put rect of currObj into tRect
  put max(abs(X - item 1 of clickLoc()),abs(Y - item 2 of clickLoc())) into R
  put item 1 of tLoc - R into item 1 of tRect
  put item 1 of tLoc + R into item 3 of tRect
  put item 2 of tLoc - R into item 2 of tRect
  put item 2 of tLoc + R into item 4 of tRect
  set rect of currObj to tRect
end mouseMove

on mouseUp
  put false into uAllowScale
  hide currObj
  put rect of currObj into tRect
  put item 1 of tRect + 1 into item 3 of tRect
  put item 2 of tRect + 1 into item 4 of tRect
  set rect of currObj to tRect
end mouseUp

on mouseRelease
  mouseUp
end mouseRelease





on preOpenStack
  set loc of this stack to the screenLoc
end preOpenStack

