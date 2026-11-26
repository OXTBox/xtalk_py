#!/usr/bin/env python3
"""LiveCode answers measured by hand (lcmcp, 25 Nov 2026, Phase 3), kept as a test in all three run modes:
interpreted, translated, fast-translated. Each case is a script whose function t() returns one text; the
answer is what LiveCode 9.6.3 gave for the same script (LIVECODE_FACTS has the story of each).

    python3 -I tests/test_measured.py [-v]

Cases that depend on today's date or the clock compare only what does not change.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from xtalk import XtError                                     # noqa: E402
from xtalk.interp import Interp                               # noqa: E402
from xtalk.parser import parse_script                         # noqa: E402
from xtalk.pyrt import Runtime                                # noqa: E402
from xtalk.transpile import translate_script                  # noqa: E402

CASES = [
    ('comment after a continuing backslash', '''
function t
   put 1 & \\   -- c
      2 into a
   put 3 & \\ # c
      4 into b
   put 5 & \\ // c
      6 into c
   put 7 & \\ /* c */
      8 into d
   return a && b && c && d
end t''', '12 34 56 78'),
    ('there is no / there is not a', '''
function t
   return (there is no button "zzq") && (there is not a button "zzq") && (there is a button "zzq")
end t''', 'true true false'),
    ('then on the next line', '''
function t
   put empty into tA
   if tA is empty
   then put 1 into x
   else
     put 2 into x
   end if
   if tA is not empty
   then put 3 into y
   else put 4 into y
   return x & y
end t''', '14'),
    ('two constants on one line', '''
constant kA = 24, kB = 16
function t
   return kA + kB
end t''', '40'),
    ('itemDel, lineDel, numberFormat, caseSensitive belong to the handler', '''
function t
   set the itemDel to "/"
   put tB() into tR
   put tR && the itemDel into tR
   tC
   put tR && the itemDel && tD() into tR
   put tR & "|" & tE() & "|" & tG() & "|" & tCS() into tR
   return tR
end t
function tB
   put the itemDel into tX
   set the itemDel to ":"
   return tX
end tB
command tC
   set the itemDel to ";"
end tC
function tD
   return the itemDel
end tD
function tE
   tF
   return the itemDel
end tE
command tF
   set the itemDel to "/"
end tF
function tG
  set the lineDel to "|"
  set the numberFormat to "0.00"
  return tH()
end tG
function tH
  return (the lineDel is return) && the numberFormat
end tH
function tCS
   set the caseSensitive to true
   return tCS2() & "," & the caseSensitive
end tCS
function tCS2
   return the caseSensitive
end tCS2''', ', / / ,|,|true 0.######|false,true'),
    ('array keys ignore case unless caseSensitive', '''
function t
   put 5 into a["X"]
   put 7 into a["Name"]
   put 9 into a["name"]
   put a["x"] & "|" & the number of elements of a & "|" & the keys of a & "|" & a["NAME"] into r
   set the caseSensitive to true
   put "|" & a["x"] & "|" & a["X"] after r
   put 1 into b["k"]
   put 2 into b["K"]
   put "|" & the number of elements of b after r
   return r
end t''', '5|2|X\nName|9||5|2'),
    ('delete item takes the delimiter after it', '''
function t
   put "3," into a
   delete item 1 of a
   put "a,b," into b
   delete item 1 of b
   put "," into c
   delete item 1 of c
   put "5" into d
   delete item 1 of d
   put "a,b" into e
   delete item 2 of e
   put "x" & return & "y" & return into f
   delete line 1 of f
   return "[" & a & "][" & b & "][" & c & "][" & d & "][" & e & "][" & f & "]"
end t''', '[][b,][][][a][y\n]'),
    ('convert', '''
function t
   put "11/25/26" into a
   convert a to dateItems
   put "2026,11,40,25,0,0,1" into b
   convert b to long date
   put "bogus" into e
   convert e to dateItems
   put the result into r
   put "2026,11,40,25,0,0,1" into h
   convert h to dateItems
   put "Wednesday, November 25, 2026" into d
   convert d to dateItems
   return a & "|" & b & "|" & e & "/" & r & "|" & h & "|" & d
end t''', '2026,11,25,0,0,0,4|Friday, December 11, 2026|bogus/invalid date|2026,12,11,1,0,0,6|2026,11,25,0,0,0,4'),
    ('textEncode / textDecode', '''
function t
   put textEncode("h" & numToCodepoint(233), "UTF-8") into tE
   put textDecode(tE & "llo", "UTF-8") into tT
   return length(tE) && length(tT) && charToNum(char 2 of tE) && (tT = "h" & numToCodepoint(233) & "llo")
end t''', '3 5 195 true'),
    ('the system date: Windows short date, year in full (25 Nov eve: 11/25/2026 vs the date 11/25/26)', '''
function t
   set the itemDel to "/"
   return the number of chars of item 3 of the system date && the number of chars of item 3 of the date
end t''', '4 2'),
]


def run(src, mode):
    if mode == 'interp':
        it = Interp()
        it.handlers.update({k: v for k, v in parse_script(src).items() if not k.startswith('#')})
        top = parse_script(src).get('#top', [])
        from xtalk.interp import Frame
        it.exec_block(top, Frame([]))
        return it.invoke('t', [])
    rt = Runtime()
    py, _ = translate_script(src, 'case', fast=(mode == 'fast'))
    rt.install(py)
    return rt.call('t')


bad, n = [], 0
for label, src, want in CASES:
    for mode in ('interp', 'translated', 'fast'):
        n += 1
        try:
            got = str(run(src, mode))
        except XtError as e:
            got = 'ERROR %s' % e
        if got != want:
            bad.append((mode, label, want, got))
        elif '-v' in sys.argv:
            print('ok   %-10s %s' % (mode, label))
for mode, label, want, got in bad:
    print('FAIL %-10s %s\n     want %r\n     got  %r' % (mode, label, want, got))
print('%d of %d measured cases match LiveCode 9.6.3' % (n - len(bad), n))
sys.exit(1 if bad else 0)
