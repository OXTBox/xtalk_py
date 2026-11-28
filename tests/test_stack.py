#!/usr/bin/env python3
"""Phase 2 (stack runtime) without a window: the message path and object rules measured in LiveCode
(docs/LIVECODE_FACTS.md, "Objects and messages"), on a hand-made copy of the measured stack
(tests/stacks/mini), then the owner's card reader stack from ~/projects/XTJSON if it is there.

    python3 -I tests/test_stack.py
"""
import os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from xtalk.stack import StackRuntime   # noqa: E402

N, BAD = [0], []
def check(name, got, want):
    N[0] += 1
    if got != want:
        BAD.append(name)
        print('FAIL  %s\n        want %r\n        got  %r' % (name, want, got))

rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
rt.open()
rt.run('set the width of graphic "G" to 50')
check('width keeps the centre', rt.get('graphic "G"', 'rect'), '35,10,85,60')
rt.run('set the left of graphic "G" to 0')
check('left moves', rt.get('graphic "G"', 'rect'), '0,10,50,60')
rt.run('set the loc of graphic "G" to 100,100')
check('loc centres', rt.get('graphic "G"', 'rect'), '75,75,125,125')
rt.run('set the height of graphic "G" to 21')
check('odd height', rt.get('graphic "G"', 'rect'), '75,89,125,110')
check('loc rounds down', rt.get('graphic "G"', 'loc'), '100,99')
rt.G['glog'] = ''
rt.run('send "mouseUp" to button "B"')
rt.run('send "hello 7" to button "B"')
rt.run('dispatch "hello" to button "B" with 8')
check('pass / send / dispatch along the path', rt.G['glog'],
      'btn:B,stackMouseUp:B,btnHello:7,stackHello:7,btnHello:8,stackHello:8,')
check('long id', rt.eval('the long id of button "B"'), 'button id 1004 of card id 1002 of stack "xtM1"')
check('names', rt.eval('the name of button "B" & "," & the short name of button "B" & "," & the name of card 1 of stack "xtM1"'),
      'button "B",B,card id 1002')
check('custom property', rt.eval('the uFoo of this stack & "," & the uFoo of stack "xtM1"'), 'bar,bar')
check('custom set', rt.eval('the cSet["k"] of this stack'), 'v')
check('button i of this stack (i is a variable, not a property)',
      rt.run('put 2 into i\nreturn the short name of button i of this stack'), 'R1')
check('a card fills its stack: rect and loc (measured)', (rt.eval('the rect of this card'), rt.eval('the loc of this card')),
      ('0,0,300,200', '150,100'))
check('number/id of card 1', rt.eval('the number of card 1 & "," & the id of card 1'), '1,1002')
check('the "abc"', rt.eval('the "abc"'), 'abc')
# not measured in LiveCode, but how the engine is used:
rt.G['glog'] = ''
rt.click('button "B"')
check('a click: mouseUp to the button, pass to the stack', rt.G['glog'], 'btn:B,stackMouseUp:B,')
rt.click('button "R1"')
check('radio button in a group', (rt.get('button "R1"', 'hilite'), rt.get('button "R2"', 'hilite')), ('true', 'false'))
rt.run('put " two" after field "F"')
check('put after a field', rt.get('field 1', 'text'), 'one two')
rt.obj('field "F"').props['listBehavior'] = 'true'
rt.run('put "aa" & return & "bb" & return & "cc" into field "F"')
f = rt.obj('field "F"')
lh = rt.field_metrics(f)[1]
rt.click('%d,%d' % (f.rect[0] + 10, int(f.rect[1] + 4 + lh * 1.5)))     # the middle of line 2
check('list field: a click hilites the line under it', (rt.get('field "F"', 'hilitedLine'), rt.get('field "F"', 'selectedText')),
      ('2', 'bb'))
check('list field: the selectedLine (word 2 = the line)', rt.eval('word 2 of the selectedLine of field "F"'), '2')
rt.run('set the hilitedLine of field "F" to 3')
check('set the hilitedLine', rt.get('field "F"', 'selectedText'), 'cc')
rt.run('put "one two" into field "F"')
rt.obj('field "F"').props['hilitedLines'] = ''
rt.obj('field "F"').props['listBehavior'] = 'false'
check('a field used as a value is its text', (rt.eval('field "F"'), rt.eval('word 2 of field "F"'), rt.eval('line 1 to -1 of field 1')),
      ('one two', 'two', 'one two'))
rt.run('hide button "B"')
check('hide', rt.get('button "B"', 'visible'), 'false')
check('hidden: a click there hits the card', rt.control_at(160, 20), None)
rt.G['glog'] = ''
rt.run('send "tickTock 1" to this stack in 100 milliseconds')
rt.tick(50)
check('send in: not yet', rt.G['glog'], '')
rt.tick(300)
check('send in: runs, and sends again', rt.G['glog'], 'tick1,tick2,tick3,')
rt.run('global gMid\nsend "tickTock 9,8" to this stack in 5 seconds\nput the result into gMid')
mid = rt.G['gmid']
pm = rt.eval('the pendingMessages').split('\n')
check('pendingMessages: id,due,name,long id of target (measured)', (pm[0].split(',')[0] == mid, pm[0].split(',', 3)[2:]),
      (True, ['tickTock', 'stack "%s"' % rt.default_stack.name]))
rt.run('cancel ' + mid)
check('cancel <id>: the message is gone', rt.eval('the pendingMessages'), '')
rt.G['glog'] = ''
rt.run('go card "Two"')
check('go card', rt.G['glog'], 'openCard:Two,')
rt.G['glog'] = ''
rt.drag((30, 30), (130, 90))      # grab me (Dictionary): follows the mouse, mouseUp when released
check('grab me: the button follows the mouse', rt.get('button "D"', 'rect'), '120,80,160,110')
check('grab me: mouseUp to the grabbed button', rt.G['glog'], 'up:D,')
rt.G['glog'] = ''
rt.drag((110, 30), (110, 200))    # grab graphic "G2" from D2: the mouse is not inside G2
check('grab: mouse outside the control, nothing moves', rt.get('graphic "G2"', 'rect'), '20,100,60,140')
check('grab: no grab; mouseMove to D2 while held; mouseLeave waits for the release (Dictionary)', rt.G['glog'],
      'in;mv:110/72;mv:110/115;mv:110/157;mv:110/200;rel;out;')
rt.G['glog'] = ''
rt.mouse_move(120, 30)
rt.mouse_move(120, 30)
rt.mouse_move(300, 300)
check('mouseMove once a move; mouseEnter / mouseLeave', rt.G['glog'], 'in;mv:120/30;out;')
rt.G['glog'] = ''
rt.click('100,170')                       # field T: the focus and the caret (after "ab": the click is right of it)
check('typing: a click focuses the field (openField)', (rt.G['glog'].split(';')[0], rt.eval('the short name of the focusedObject')), ('open', 'T'))
for c in 'cxd':
    rt.key(c)                             # x: the field's keyDown takes it (no pass), so it is not typed
check('typing: keys are typed unless a keyDown takes them', rt.get('field "T"', 'text'), 'abcd')
rt.special_key('backspace')
rt.special_key('left')
rt.special_key('return')
rt.key('z')
check('typing: Backspace, Left, Return', rt.get('field "T"', 'text'), 'ab\nzc')
rt.run('select after text of field "T"')
rt.key('!')
rt.run('select char 1 to 2 of field "T"')
check('select: after text, then a chunk (the selectedText)', (rt.get('field "T"', 'text'), rt.eval('the selection')), ('ab\nzc!', 'ab'))
rt.G['glog'] = ''
rt.click('40,30')                         # elsewhere: the field had changed: closeField
check('typing: leaving a changed field sends closeField', (rt.G['glog'].split(';')[0], rt.eval('the focusedObject')), ('close', ''))
rt.G['glog'] = ''
rt.run('focus on field "T"')
rt.run('focus on nothing')
check('focus on / nothing: unchanged gives exitField', rt.G['glog'], 'open;exit;')
rt.run('put "ab" into field "T"')
rt.G['glog'] = ''
rt.menu_choices = ['Three']
rt.click('button "P"')                # popup in mouseUp: the handler waits for the pick (Dictionary)
check('popup: the items shown', rt.menus[-1], ('PM', ['One', '-', 'Two', 'Three', 'More', 'Deep']))
check('popup: menuPick to the menu button, then the handler goes on', rt.G['glog'], 'pick:Three;after;')
check('popup: menuHistory', rt.get('button "PM"', 'menuHistory'), '4')
rt.G['glog'] = ''
rt.menu_choices = ['More|Deep']
rt.click('button "P"')
check('popup: a submenu pick is Parent|Child', rt.G['glog'], 'pick:More|Deep;after;')
rt.G['glog'] = ''
rt.click('button "P"')                # no pick: the menu closed
check('popup closed without a pick: no menuPick', rt.G['glog'], 'after;')
rt.G['glog'] = ''
rt.menu_choices = ['Green']
rt.click('button "OM"')
check('option menu: opens on the click, label = pick, no mouseUp after it',
      (rt.G['glog'], rt.get('button "OM"', 'label')), ('om:Green;', 'Green'))
check('no script errors', rt.errors, [])
rt.run('put "x" into URL "file:/tmp/escape_test.txt"')
rt.run('put "y" into URL ("file:" & specialFolderPath("Documents") & "/in.txt")')
home = rt.host.folders['home']
check('a write outside the sandbox is redirected into it',
      (os.path.exists('/tmp/escape_test.txt'), os.path.exists(os.path.join(home, 'elsewhere', 'tmp', 'escape_test.txt'))), (False, True))
os.makedirs(os.path.join(home, 'Documents'), exist_ok=True)
with open(os.path.join(home, 'Documents', 'hello.py'), 'w') as f:
    f.write('open("shell_ran.txt", "w").write("yes")\n')
if os.path.exists(os.path.join(home, 'Documents', 'shell_ran.txt')):
    os.remove(os.path.join(home, 'Documents', 'shell_ran.txt'))
os.environ['XTALK_SCRIPT_PYTHON'] = sys.executable     # this Python: the test must not depend on Windows
rt.run('get shell(specialFolderPath("Documents") & "/hello.py")')
del os.environ['XTALK_SCRIPT_PYTHON']
for p in rt.started:
    try:
        p.wait(20)
    except Exception:
        p.kill()
ran = os.path.join(home, 'Documents', 'shell_ran.txt')
check('shell: a .py file in the sandbox runs with Python', open(ran).read() if os.path.exists(ran) else None, 'yes')
try:
    rt.run('get shell("dir")')
    refused = False
except Exception as e:
    refused = 'only a .py file' in str(e)
check('shell: any other command is refused', refused, True)
rt.run('go card 1')
n_before = rt.eval('the number of graphics')
check('create graphic: it = the long id, no name, 128x32 centred, rectangle (measured)',
      rt.run('create graphic\nreturn it & "|" & the name of it & "|" & the rect of it & "|" & the style of it'),
      'graphic id 1039 of card id 1002 of stack "xtM1"|graphic id 1039|86,84,214,116|rectangle')
rt.run('set the backgroundColor of the templateGraphic to "255,0,0"\nset the width of the templateGraphic to 40')
check('the template: its colour, and its changed rect (measured)',
      rt.run('create graphic "Red"\nreturn the backgroundColor of graphic "Red" & "|" & the rect of graphic "Red"'),
      '255,0,0|43,-1,83,31')
rt.run('reset the templateGraphic')
check('reset the templateGraphic', rt.run('create invisible graphic "After"\nreturn the backgroundColor of graphic "After" & "|" & the visible of graphic "After"'), '|false')
rt.run('delete graphic "Red"')
check('delete graphic: gone', (rt.eval('there is a graphic "Red"'), rt.eval('the number of graphics')), ('false', str(int(n_before) + 2)))
rt.run('create button "Go" in group "Grp"')
check('create in a group', rt.eval('the short name of the owner of button "Go"') if False else rt.obj('button "Go"').parent.name, 'Grp')
rt.run('delete button "Go"')
rt.run('delete graphic "After"\ndelete graphic id 1039')
rt.run('create folder (specialFolderPath("Documents") & "/made_here")')
check('create folder: inside the sandbox', os.path.isdir(os.path.join(home, 'Documents', 'made_here')), True)
rt.dialog_answers = ['No', 'Bob', None]
check('answer: it = the button picked', rt.run('answer "Go?" with "Yes" or "No" titled "T"\nreturn it'), 'No')
check('ask: it = the text typed', rt.run('ask "Name?" with "x"\nreturn it & "|" & the result'), 'Bob|')
check('ask cancelled: it empty, the result = cancel (Dictionary)', rt.run('ask "Name?"\nreturn it & "|" & the result'), '|cancel')
check('no replies left: answer takes its last (default) button', rt.run('answer "Go?" with "A" or "B"\nreturn it'), 'B')
check('a sandbox write stays where it says', os.path.exists(os.path.join(home, 'Documents', 'in.txt')), True)

# ---- rounding off Phase 2 (26 Nov): measured in LiveCode, docs/LIVECODE_FACTS.md "26 Nov 2026"
from xtalk.stack.runtime import ObjInterp            # noqa: E402
from xtalk.transpile import translate_statements     # noqa: E402
import xtalk.pyrt as pyrt                            # noqa: E402
rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
LOGGER = '\n'.join('on %s\nglobal gLog\nput the short name of me && "%s" && the short name of the target & "/" after gLog\npass %s\nend %s'
                   % (m, m, m, m) for m in ('preOpenStack', 'openStack', 'preOpenCard', 'openCard', 'closeCard', 'closeStack'))
card1 = rt.default_stack.current
c = ObjInterp(rt, card1)
c.load(LOGGER)
rt.ctx[id(card1)] = c
rt.G['glog'] = ''
rt.open()
check('open: all four messages to the card, in this order; passed on to the stack script (measured)', rt.G['glog'],
      'card id 1002 preOpenStack card id 1002/preOpenStack,card id 1002 preOpenCard card id 1002/'
      'card id 1002 openStack card id 1002/card id 1002 openCard card id 1002/openCard:card id 1002,')
rt.G['glog'] = ''
rt.run('go card 1')
check('go to the card already shown: no messages (measured)', rt.G['glog'], '')
rt.run('create card "C2"')
rt.run('go card 1')
rt.G['glog'] = ''
rt.special_key('right')
check('an arrow key nobody takes: next card (navigationArrows)', (rt.eval('the number of this card'), rt.G['glog']),
      ('2', 'card id 1002 closeCard card id 1002/openCard:Two,'))
rt.special_key('up')
check('up arrow: back to the card before (recent cards, Dictionary)', rt.eval('the number of this card'), '1')
rt.special_key('down')
check('down arrow: forward again through the recent cards', rt.eval('the number of this card'), '2')
rt.special_key('up')
rt.run('set the navigationArrows to false')
rt.special_key('down')
check('navigationArrows false: the arrow changes nothing', rt.eval('the number of this card'), '1')
rt.run('set the navigationArrows to true')
rt.G['glog'] = ''
rt.close_stack()
check('closing: closeCard, closeStack to the card (measured)', rt.G['glog'],
      'card id 1002 closeCard card id 1002/card id 1002 closeStack card id 1002/')

rt.run('set the style of graphic "G" to "regular"\nset the polySides of graphic "G" to 3\nset the rect of graphic "G" to 100,100,140,140')
from xtalk.stack.model import regular_points          # noqa: E402
check('regular graphic corners (measured: the effective points)', regular_points([100, 100, 140, 140], 3, 0),
      [[139, 120], [111, 136], [111, 104], [139, 120]])
check('angle 30 turns them clockwise (measured)', regular_points([100, 100, 140, 140], 3, 30),
      [[136, 129], [104, 129], [120, 101], [136, 129]])
check('an ellipse, not a circle (measured 60x40)', regular_points([100, 100, 160, 140], 4, 0),
      [[159, 120], [130, 139], [101, 120], [130, 101], [159, 120]])
check('6 sides at 90 (measured)', regular_points([100, 100, 200, 200], 6, 90),
      [[150, 199], [108, 174], [108, 126], [150, 101], [192, 126], [192, 174], [150, 199]])
rt.run('create graphic "PolyT"\nset the style of graphic "PolyT" to "polygon"\nset the points of graphic "PolyT" to "10,20,30,40,50,60,10,20"')
check('points as one comma list: paired (measured)', rt.get('graphic "PolyT"', 'points'), '10,20\n30,40\n50,60\n10,20')
rt.run('set the points of graphic "PolyT" to "1,2" & cr & "3,4,5,6"')
check('points: lines with two pairs (measured)', rt.get('graphic "PolyT"', 'points'), '1,2\n3,4\n5,6')
rt.run('delete graphic "PolyT"')
rt.run('create image "ImT"\nset the rect of image "ImT" to 100,100,160,140')
rt.run('set the angle of image "ImT" to 45')
im45 = rt.get('image "ImT"', 'rect')
rt.run('set the angle of image "ImT" to 30')
im30 = rt.get('image "ImT"', 'rect')
rt.run('set the angle of image "ImT" to 90')
im90 = rt.get('image "ImT"', 'rect')
rt.run('set the angle of image "ImT" to 0')
check('image angle: the rect is the box around the turned picture; 0 gives it back (measured)',
      (im45, im30, im90, rt.get('image "ImT"', 'rect')),
      ('94,84,165,155', '94,87,166,152', '109,90,150,150', '100,100,160,140'))
rt.run('set the angle of image "ImT" to 30\nset the loc of image "ImT" to 300,300')
_m1 = rt.get('image "ImT"', 'rect')
rt.run('set the angle of image "ImT" to 45')
_m2 = rt.get('image "ImT"', 'rect')
rt.run('set the angle of image "ImT" to 30\nset the width of image "ImT" to 100')
_m3 = rt.get('image "ImT"', 'rect')
rt.run('set the angle of image "ImT" to 0')
check('a turned image moved takes its picture along; a new width is ignored (measured)',
      (_m1, _m2, _m3, rt.get('image "ImT"', 'rect')),
      ('264,268,336,333', '264,265,335,336', '264,268,336,333', '270,281,330,321'))
rt.run('delete image "ImT"')
rt.run('create graphic "LocT"\nset the rect of graphic "LocT" to 0,0,71,71\nset the loc of graphic "LocT" to 300,300')
check('set the loc, odd size: left = x - (width div 2) (measured)', rt.get('graphic "LocT"', 'rect'), '265,265,336,336')
rt.run('delete graphic "LocT"')
SF = '<p><b>zz</b> bb</p><p><i>cc</i> yy</p><p>aa <font color="#FF0000">rr</font></p>'
rt.run('create field "SfT"')
def sf_after(cmd, h=SF):
    rt.run('set the htmlText of field "SfT" to "%s"' % h.replace('"', '" & quote & "'))
    rt.run(cmd)
    return rt.get('field "SfT"', 'htmltext')
check('styled field: delete line / sort lines keep each line\'s styles (measured)',
      (sf_after('delete line 2 of field "SfT"'), sf_after('sort lines of field "SfT"'),
       sf_after('sort lines of field "SfT" descending', '<p><b>zz</b> bb</p><p><i>cc</i> yy</p><p>aa</p>')),
      ('<p><b>zz</b> bb</p>\n<p>aa <font color="#FF0000">rr</font></p>',
       '<p>aa <font color="#FF0000">rr</font></p>\n<p><i>cc</i> yy</p>\n<p><b>zz</b> bb</p>',
       '<p><b>zz</b> bb</p>\n<p><i>cc</i> yy</p>\n<p>aa</p>'))
rt.run('delete field "SfT"')
rt.run('go card 1')
rt.run('set the backgroundBehavior of group "Grp" to true')
_bgs = ''.join('on %s\nglobal glog\nput "%s," after glog\npass %s\nend %s\n' % (m, m, m, m) for m in
               ['preOpenBackground', 'openBackground', 'closeBackground', 'closeCard', 'preOpenCard', 'openCard'])
rt.run('set the script of group "Grp" to "%s"' % _bgs.replace('"', '" & quote & "').replace('\n', '" & cr & "'))
rt.G['glog'] = ''
rt.run('go card "Two"')
_leave = rt.G['glog']
rt.G['glog'] = ''
rt.run('go card 1')
check('background messages: leaving / entering a background group (measured order)',
      tuple(','.join(next(m for m in ('preOpenBackground', 'openBackground', 'closeBackground', 'closeCard', 'preOpenCard', 'openCard')
                          if m in x) for x in g.split('openCard:')[0].split(',') if x) + ',' for g in (_leave, rt.G['glog'])),
      ('closeCard,closeBackground,', 'preOpenBackground,preOpenCard,openBackground,openCard,'))   # the message names in the order logged
rt.run('set the script of group "Grp" to empty')
rt.run('set the backgroundBehavior of group "Grp" to false')
rt.run('set the angle of graphic "G" to 390')
a1 = rt.eval('the angle of graphic "G"')
rt.run('set the angle of graphic "G" to -30')
check('angle reads back mod 360 (measured)', (a1, rt.eval('the angle of graphic "G"'), rt.eval('the rect of graphic "G"')),
      ('30', '330', '100,100,140,140'))
rt.run('set the angle of graphic "G" to 90\nset the filled of graphic "G" to true')
check('within() a turned regular graphic (90: the point at the bottom)',
      (rt.eval('within(graphic "G", "120,108")'), rt.eval('within(graphic "G", "120,135")')), ('false', 'true'))

R, E = rt.run, rt.eval
R('put "hello world" & cr & "two & <three>" into field "F"')
check('htmlText of plain text (measured)', E('the htmlText of field "F"'), '<p>hello world</p>\n<p>two &amp; &lt;three&gt;</p>')
R('set the textStyle of word 2 of field "F" to "bold"')
R('set the textColor of char 1 to 2 of field "F" to "255,0,0"')
R('set the textSize of line 2 of field "F" to 18')
R('set the textFont of word 1 of line 2 of field "F" to "Courier"')
check('chunk styles -> htmlText (measured)', E('the htmlText of field "F"'),
      '<p><font color="#FF0000">he</font>llo <b>world</b></p>\n'
      '<p><font face="Courier" size="18">two</font><font size="18"> &amp; &lt;three&gt;</font></p>')
check('chunk styles read back: mixed, bold, empty (measured)',
      E('the textStyle of line 1 of field "F" & "|" & the textStyle of word 2 of field "F" & "|" & the textStyle of field "F" '
        '& "|" & the textSize of line 2 of field "F" & "|" & the textSize of line 1 of field "F"'), 'mixed|bold||18|')
R('put "X" into word 2 of field "F"')
check('put into a bold word after a plain space: plain (measured)', E('the htmlText of field "F"').split('\n')[0],
      '<p><font color="#FF0000">he</font>llo X</p>')
PUTS = [('put "x" after field "F"', '<p><b>ab</b> cdx</p>'), ('put "y" before field "F"', '<p><b>yab</b> cdx</p>'),
        ('put "new" into field "F"', '<p>new</p>'), ('set the htmlText of field "F" to "<p><b>ab</b> cd</p>"', '<p><b>ab</b> cd</p>'),
        ('put "Q" into char 1 of field "F"', '<p><b>Qb</b> cd</p>'), ('put "ZZ" after word 1 of field "F"', '<p><b>QbZZ</b> cd</p>'),
        ('put "W" before word 2 of field "F"', '<p><b>QbZZ</b> Wcd</p>')]
R('set the htmlText of field "F" to "<p><b>ab</b> cd</p>"')
got = []
for st, _ in PUTS:
    R(st)
    got.append(E('the htmlText of field "F"'))
check('puts keep or clear styles as LiveCode does (7 measured)', got, [w for _, w in PUTS])
HT = ('<p>a <b>bold <i>bi</i></b> &amp; &lt;x&gt; &rdquo;q&ldquo; &#65;</p><p></p><p><font face="Arial" size="14" '
      'color="#00FF00">g</font> <u>u</u> <strike>s</strike></p>')
R('set the htmlText of field "F" to "%s"' % HT.replace('"', '" & quote & "'))
check('set the htmlText: text and htmlText back (measured)', (E('the text of field "F"'), E('the htmlText of field "F"')),
      ('a bold bi & <x> ”q“ A\n\ng u s', '<p>a <b>bold <i>bi</i></b> &amp; &lt;x&gt; &rdquo;q&ldquo; A</p>\n<p></p>\n'
       '<p><font face="Arial" size="14" color="#00FF00">g</font> <u>u</u> <strike>s</strike></p>'))
R('put "abc def" into field "F"')
R('set the textStyle of word 1 of field "F" to "bold,italic,underline,strikeout"\nset the textFont of word 1 of field "F" to "Arial"'
  '\nset the textColor of word 1 of field "F" to "blue"\nset the backgroundColor of char 1 of field "F" to "yellow"')
check('tag order i b strike u font (measured)', E('the htmlText of field "F"'),
      '<p><i><b><strike><u><font face="Arial" color="#0000FF" bgcolor="#FFFF00">a</font><font face="Arial" color="#0000FF">bc'
      '</font></u></strike></b></i> def</p>')
check('textColor of a chunk reads r,g,b (measured)', E('the textColor of word 1 of field "F"'), '0,0,255')
# the same through the translator (its own code path for chunk properties)
env = dict({k: getattr(pyrt, k) for k in dir(pyrt) if not k.startswith('__')})
exec(translate_statements('put "one two" into field "F"\nset the textStyle of word 2 of field "F" to "italic"\n'
                          'put the textStyle of word 2 of field "F" & "|" & the htmlText of field "F" into tout'), env)
fr = pyrt.Frame([])
env['_body'](rt.ctx.get(id(rt.default_stack.current)) or ObjInterp(rt, rt.default_stack.current), fr)
check('translator: chunk style set and read', fr.vars.get('tout'), 'italic|<p>one <i>two</i></p>')
# typing keeps styles: the new character takes the one before it
f = rt.obj('field "F"')
R('set the htmlText of field "F" to "<p><b>ab</b>c</p>"')
rt.set_focus(f)
rt.sel = (2, 2)
rt.key('Z')
check('typing after bold text is bold', E('the htmlText of field "F"'), '<p><b>abZ</b>c</p>')

R('put "aaa bbb ccc ddd eee" & cr & "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" & cr & "short" into field "F"')
rows = rt.field_rows(f)
check('word wrap: a line wraps at spaces, a long word is cut (7 px a char headless)',
      [f.text[a:b] for _, a, b in rows],
      ['aaa bbb ', 'ccc ddd ', 'eee', 'xxxxxxxx', 'xxxxxxxx', 'xxxxxxxx', 'xxxxxxxx', 'xxxxxx', 'short'])
lh = rt.field_metrics(f)[1]
check('a wrapped line is one line for clicks', rt.field_line_at(f, int(f.rect[1] + 4 + lh * 2.5)), 1)
R('set the dontWrap of field "F" to true')
check('dontWrap: one row a line', len(rt.field_rows(f)), 3)
R('set the dontWrap of field "F" to false')
rt.sel = (2, 2)
rt.special_key('down')
check('down arrow moves by rows as drawn', rt.sel, (10, 10))

R('put "one two three" into field "F"\nset the dontWrap of field "F" to true')
y = int(f.rect[1] + 4 + rt.field_metrics(f)[1] / 2)
x0 = int(f.rect[0] + rt.field_metrics(f)[2] / 2 + 2)
rt.drag((x0 + 1, y), (x0 + 7 * 3 + 1, y))
check('drag across a field selects the text', E('the selection'), 'one')
rt.keys_down = {'shiftkey'}
rt.click('%d,%d' % (x0 + 7 * 7 + 1, y))
rt.keys_down = set()
check('shift-click grows the selection', E('the selection'), 'one two')
R('set the clipboardData["text"] to "hi there"')
check('clipboardData["text"] and the clipboard (measured)', (E('the clipboardData["text"]'), E('the clipboard')), ('hi there', 'text'))
R('put "one two" into field "F"')
rt.set_focus(f)
rt.sel = (0, 3)
rt.control_key('c')
rt.sel = (7, 7)
rt.control_key('v')
check('Ctrl+C, Ctrl+V in a field', (f.text, rt.clipboard), ('one twoone', 'one'))
rt.sel = (0, 4)
rt.control_key('x')
check('Ctrl+X cuts', (f.text, rt.clipboard), ('twoone', 'one '))
R('set the clipboardData["text"] to "Z"\npaste')
check('the paste command types the clipboard in', f.text, 'Ztwoone')
R('put "one two three" into field "F"')
check('functions of a chunk of a field stay functions (length, value)',
      (E('the length of word 2 of field "F"'), E('the value of "1+2"'), E('the number of chars of line 1 of field "F"')),
      ('3', '3', '13'))
env = dict({k: getattr(pyrt, k) for k in dir(pyrt) if not k.startswith('__')})
exec(translate_statements('put the length of word 2 of field "F" & "|" & the length of word 3 of "a b cde" into tout'), env)
fr = pyrt.Frame([])
env['_body'](ObjInterp(rt, rt.default_stack.current), fr)
check('translator: the length of a chunk', fr.vars.get('tout'), '3|3')
rt.run('create card "L"')
for n in 'ABC':
    rt.run('create graphic "%s"' % n)
lay = []
for st in ['set the layer of graphic "A" to top', 'set the layer of graphic "A" to 1', 'set the layer of graphic "C" to bottom',
           'set the layer of graphic "C" to 2', 'set the layer of graphic "A" to 99']:
    rt.run(st)
    lay.append(''.join(rt.eval('the layer of graphic "%s"' % n) for n in 'ABC'))
check('set the layer: top, 1, bottom, 2, past the top (measured)', lay, ['312', '123', '231', '132', '321'])
check('no errors in these checks', rt.errors, [])

NINE = os.path.expanduser('~/projects/XTJSON/Scott_Rossi_nine_ball')
if os.path.isdir(NINE):
    rt = StackRuntime(NINE, files_dir=os.path.join(ROOT, 'run_files', 'test'))
    rt.open()
    about = rt.harvest.stack('About')
    c = ObjInterp(rt, about.current)
    c.load(LOGGER)
    rt.ctx[id(about.current)] = c
    rt.G['glog'] = ''
    rt.run('go stack "About"')
    first = rt.G['glog'].count('/'), rt.default_stack.name
    rt.G['glog'] = ''
    rt.run('go stack "nineball"\ngo stack "About"')
    check('go stack: the first time its four open messages, then none (measured)', (first, rt.G['glog'], rt.default_stack.name),
          ((4, 'About'), '', 'About'))
    rt = StackRuntime(NINE, files_dir=os.path.join(ROOT, 'run_files', 'test'))     # the stack's own scripts again
    rt.open()
    rt.message(rt.obj('button "Help"'), 'menuPick', ['About'])
    shown = rt.default_stack.name
    rt.click('100,20')                         # About's card: close this stack
    check('Help > About: open stack shows it; a click closes it, back to the game', (shown, rt.default_stack.name, rt.closed),
          ('About', 'nineball', False))
    rt.message(rt.obj('button "Help"'), 'menuPick', ['Preferences'])
    shown = rt.default_stack.name
    rt.click('button "Close"')                 # hide this stack
    check('Help > Preferences, then its Close (hide this stack): back to the game', (shown, rt.default_stack.name), ('Preferences', 'nineball'))
    rt.run('go stack "About"')
    f = rt.obj('field "Field"')
    check('nine-ball About: its styled field read from the harvest', rt.get('field "Field"', 'htmltext').count('<font face="Lucida Grande" size="14">'), 2)
    rt.close_stack()
    check('nine-ball: no errors opening, going, closing', rt.errors, [])

READER = os.path.expanduser('~/projects/XTJSON/Game_card_reader_11_13_2025')
if os.path.isdir(READER):
    random.seed(1)
    rt = StackRuntime(READER, files_dir=os.path.join(ROOT, 'run_files', 'test'))
    rt.open()
    check('card reader: all scripts load', rt.load_errors, [])
    rt.click('button id 6593')
    check('reader "3" (wide): box 3 hidden', rt.get('graphic "Box3"', 'visible'), 'false')
    check('reader "3" (wide): boxes 230 wide', rt.get('graphic "Box2"', 'rect'), '240,35,470,195')
    check('reader "3": three lines on top of the list', len(rt.get('field 1', 'text').split('\n\n')[0].split('\n')), 3)
    rt.click('button "5 Room Dungeon"')
    labels = [rt.get('graphic "Label%d"' % i, 'label') for i in range(1, 7)]
    check('reader 5 rooms: the labels', labels, ['Entrance', ' Obstacle', ' Setback', ' Climax', ' Resolution', 'Next'])
    check('reader 5 rooms: 100 dungeons in the list', rt.get('field 1', 'text').count('Entrance:'), 100)
    check('reader: no script errors', rt.errors, [])
LC = os.path.expanduser('~/projects/XTJSON/LightCycles3')
if os.path.isdir(LC):
    random.seed(3)
    rt = StackRuntime(LC, files_dir=os.path.join(ROOT, 'run_files', 'test'))
    rt.open()
    rt.click('button "reset"')
    check('cycles: countdown waits 2 s (virtual)', rt.clock, 2000.0)
    start = rt.get('graphic "playerMarker"', 'loc')
    for k in 'DDSS':                   # the script: the first press of a key sets the way, the next ones the speed
        rt.key(k)
    for i in range(10):
        rt.tick(70)
    x0, y0 = map(int, start.split(','))
    x1, y1 = map(int, rt.get('graphic "playerMarker"', 'loc').split(','))
    check('cycles: S drives the bike down, 2 px a step', (x1 - x0, (y1 - y0) % 2, y1 > y0), (0, 0, True))
    check('cycles: the trail grows', len(rt.get('graphic "PlayerLaserWall"', 'points').split('\n')) > 5, True)
    check('cycles: no script errors', rt.errors, [])
    sb = rt.obj('scrollbar "Changesscroll"')
    rt.drag((sb.rect[0] + 10, sb.rect[1] + 20), (sb.rect[2] - 20, sb.rect[1] + 20), steps=5)
    check('cycles: dragging a slider moves its thumb (scrollbarDrag runs, no errors)',
          (int(rt.get('scrollbar "Changesscroll"', 'thumbPosition')) > 38, rt.errors), (True, []))
    n = len(rt.errors)
    rt.click('button "Redraw ALL"')
    made = [o.name for o in rt.default_stack.current.flat() if o.type == 'graphic' and o.name.lower()[:4] == 'test' and o.name[4:].isdigit()]
    check('cycles: Redraw ALL creates its line graphics', (len(made) > 0, rt.errors[n:]), (True, []))
    check('cycles: the stored trails (a customPropertySet, the tProp of stack) give them points',
          (len(made), max(len(rt.obj('graphic "%s"' % m).points or []) for m in made) > 1000), (19, True))   # test5 is deleted again by each later call
    check('style "Line" is stored as line (measured)', rt.get('graphic "test1"', 'style'), 'line')
    rt.dialog_answers = ['speed', '9']
    rt.click('button "PropertyArrays"')
    check('cycles: PropertyArrays asks twice, stores key and value', rt.eval('the MyArray["speed"] of button "PropertyArrays"'), '9')
# line heights (measured 25 Nov): fixedLineHeight true = floor(size * 4/3); false = the font's own (Segoe UI)
rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
rt.open()
rt.run('create field "LH"')
_lh = []
for _fixed in ('true', 'false'):
    for _size in (10, 12, 14, 18, 24):
        rt.run('set the fixedLineHeight of field "LH" to %s\nset the textSize of field "LH" to %d' % (_fixed, _size))
        _lh.append(rt.field_metrics(rt.obj('field "LH"'))[1])
check('line heights, fixed then free, sizes 10 12 14 18 24 (measured)', _lh, [13, 16, 18, 24, 32, 15, 18, 18, 26, 36])
# formattedHeight (measured 26 Nov, Segoe UI): rows x line height - 8 + top margin + bottom margin
_fh = []
rt.run('set the width of field "LH" to 300\nset the fixedLineHeight of field "LH" to true')
for _size, _m, _text in ((11, '0', 'one'), (11, '0', 'one\ntwo'), (13, '4', 'one\ntwo'), (12, '12', 'a\nb\nc\nd'),
                         (12, '4,6,8,10', 'one\ntwo')):
    _f = rt.obj('field "LH"')
    rt.run('set the textSize of field "LH" to %d\nset the margins of field "LH" to "%s"' % (_size, _m))
    _f.text = _text
    _fh.append(rt.eval('the formattedHeight of field "LH"'))
check('formattedHeight of a field: sizes, lines, margins (measured)', _fh, ['6', '20', '34', '80', '40'])

# links (measured 26 Nov): htmlText <a href> / <a> / <a name>; textStyle link; linkClicked in place of mouseUp
rt.run('set the htmlText of field "LH" to "<p><font color=" & quote & "#FF8C8C" & quote & "><a href=" & quote & "remove" & quote & ">Remove it</a></font><font color=" & quote & "#8888A0" & quote & ">  (Delete)</font></p>"')
check('link: htmlText reads back with <a> outside <font>', rt.eval('the htmlText of field "LH"'),
      '<p><a href="remove"><font color="#FF8C8C">Remove it</font></a><font color="#8888A0">  (Delete)</font></p>')
check('link: textStyle / linkText / colour of char 1, style of char 12', '|'.join(rt.eval(_e) for _e in (
      'the textStyle of char 1 of field "LH"', 'the linkText of char 1 of field "LH"', 'the textColor of char 1 of field "LH"',
      'the textStyle of char 12 of field "LH"')),
      'link|remove|255,140,140|')
rt.run('set the text of field "LH" to "abc def"\nset the textStyle of char 1 to 3 of field "LH" to "link"\nset the linkText of char 5 to 7 of field "LH" to "zz"')
check('link: textStyle link -> <a>, linkText alone -> <a name>', rt.eval('the htmlText of field "LH"'), '<p><a>abc</a> <a name="zz">def</a></p>')
rt.run('set the htmlText of field "LH" to "<p><a href=" & quote & "x" & quote & ">WWWW</a> <a>MMMM</a> plain</p>"\n'
       'set the margins of field "LH" to 8\nset the textSize of field "LH" to 12\nset the rect of field "LH" to 0,0,300,40\nset the lockText of field "LH" to true')
rt.run('set the script of field "LH" to "on mouseDown" & cr & "global glog" & cr & "put ""d "" after glog" & cr & "end mouseDown" & cr & '
       '"on mouseUp" & cr & "global glog" & cr & "put ""u "" after glog" & cr & "end mouseUp" & cr & '
       '"on linkClicked p" & cr & "global glog" & cr & "put ""L:"" & p & "" "" after glog" & cr & "end linkClicked"'.replace('""', '" & quote & "'))
_f = rt.obj('field "LH"')
_y = _f.rect[1] + 12
def _x_of(ch):                          # the middle of character ch (0-based)
    return int(_f.rect[0] + 4 + 2 + rt.text_width(_f, 0, ch) + rt.text_width(_f, ch, ch + 1) / 2)
rt.G['glog'] = ''
for _c in (1, 7, 13, 30):
    rt.last_down = None
    rt.click('%d,%d' % (_x_of(_c) if _c < 30 else 290, _y))
check('linkClicked: linkText, else the link words; plain text and past the end: mouseUp (measured)', rt.G['glog'],
      'd L:x d L:MMMM d u d u ')

# keysDown, rawKeyDown, globalLoc (a hidden window: window_pos 0,0, no mouse warp)
rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
rt.open()
rt.held_codes = [119, 65362]
rt.window_pos = (200, 32)
rt.run('set the script of card 1 to "on rawKeyDown k" & cr & "global glog" & cr & "put k & comma after glog" & cr & "pass rawKeyDown" & cr & "end rawKeyDown"')
rt.G['glog'] = ''
rt.raw_key(65307)
check('the keysDown; rawKeyDown with the code; globalLoc / localLoc add / take the window place',
      (rt.eval('the keysDown'), rt.G['glog'], rt.eval('globalLoc("10,20")'), rt.eval('localLoc("210,52")')),
      ('119,65362', '65307,', '210,52', '10,20'))
rt.run('set the screenMouseLoc to 5,5')          # no window: nothing moves, no error
check('set the screenMouseLoc with no window: no error', rt.errors, [])

rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
rt.open()
rt.run('close stack "Message box"')
check('close stack of a stack that is not here (the IDE Message box): the window stays open', rt.closed, False)

rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
rt.open()
rt.run('put "aa" & cr & "bb" into field "F"')
rt.run('set the script of field "F" to "function fLine" & cr & "return line 2 of me" & cr & "end fLine" & cr & '
       '"command cPut" & cr & "put " & quote & "XX" & quote & " into line 1 of me" & cr & "end cPut" & cr & '
       '"function fName" & cr & "return the short name of me" & cr & "end fName"')
rt.run('global gR\nput fLine() into gR') if False else None
_c = rt.ctx[id(rt.obj('field "F"'))]
_r1, _r2 = _c.call('fLine'), _c.call('fName')
_c.call('cPut')
check('me in a field script: its text as a value, the object for "of me" (measured)',
      (_r1, _r2, rt.get('field "F"', 'text')), ('bb', 'F', 'XX\nbb'))

rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
rt.open()
rt.run('go card 1\nput "one" & cr & "two" & cr & "three" into field "F"\nset the lockText of field "F" to true\n'
       'set the listBehavior of field "F" to true')
_f = rt.obj('field "F"')
_lh = rt.field_metrics(_f)[1]
rt.click('%d,%d' % (_f.rect[0] + 10, int(_f.rect[1] + 4 + _lh * 0.5)))
_a = (rt.focused is _f, rt.host.hilited_lines(_f))
rt.special_key('down')
rt.special_key('down')
rt.special_key('down')
check('a clicked list field takes the focus; Down moves its hilite, stops at the last line', (_a, rt.host.hilited_lines(_f)),
      ((True, [1]), [3]))

# a stack opening / closing on a card with a background group (measured 25 Nov)
rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
rt.run('set the backgroundBehavior of group "Grp" to true')
_bgs = ''.join('on %s\nglobal glog\nput "%s," after glog\npass %s\nend %s\n' % (m, m, m, m)
               for m in ['preOpenBackground', 'openBackground', 'closeBackground'])
rt.run('set the script of group "Grp" to "%s"' % _bgs.replace('"', '" & quote & "').replace('\n', '" & cr & "'))
rt.G['glog'] = ''
rt.open()
_o = rt.G['glog']
rt.G['glog'] = ''
rt.close_stack()
check('open with a background: preOpenStack, preOpenBackground, ..., openBackground, openCard; close: closeBackground',
      (_o, rt.G['glog']), ('preOpenStack,preOpenBackground,openBackground,openCard:card id 1002,', 'closeBackground,'))

# insert script of X into front (the xt3d bench's GameNotes): first on every path; pass goes on to the target
rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
rt.open()
_f = os.path.join(ROOT, 'run_files', 'test', 'FrontT.livecodescript')
os.makedirs(os.path.dirname(_f), exist_ok=True)
open(_f, 'w').write('script "FrontT"\nglobal gLog\non mouseUp\n   put "front," after gLog\n   pass mouseUp\nend mouseUp\n'
                    'on frontOnly\n   put "fo," after gLog\nend frontOnly\n')
rt.G['glog'] = ''
rt.run('start using stack "%s"' % _f)
rt.run('insert script of stack "FrontT" into front')
rt.message(rt.host.resolve('button "B"'), 'mouseUp')                 # an engine message (rawKeyDown for GameNotes)
check('front script first, pass goes to the target', rt.G['glog'], 'front,btn:B,stackMouseUp:B,')
check('the frontScripts', '"FrontT' in rt.eval('the frontScripts') or 'FrontT' in rt.eval('the frontScripts'), True)
rt.G['glog'] = ''
rt.run('remove script of stack "FrontT" from front')
rt.message(rt.host.resolve('button "B"'), 'mouseUp')
check('remove script from front', (rt.G['glog'], rt.eval('the frontScripts')), ('btn:B,stackMouseUp:B,', ''))

# the defaultStack (measured 25 Nov eve in the standalone): stack "Name"; stack (that) names the stack
rt.run('global gR\nput the defaultStack into t\nput t & "|" & (there is a stack t) & "|" & the short name of stack t & "|" & '
       'the short name of t into gR')
check('the defaultStack is stack "Name"', rt.G['gr'], 'stack "xtM1"|true|xtM1|xtM1')
rt.run('global gR\nset the defaultStack to "xtM1"\nput the defaultStack into gR')
check('set the defaultStack to a name: read back as stack "Name"', rt.G['gr'], 'stack "xtM1"')

_g = os.path.join(ROOT, 'run_files', 'test', 'ValT.livecodescript')
open(_g, 'w').write('script "ValT"\nfunction valOnly\n   return "vo:" & the short name of me\nend valOnly\n')
rt.run('start using stack "%s"' % _g)
rt.run('global gR\nput value("valOnly()", stack "ValT") into gR')
check('value(expr, object): in that object\'s script', rt.G['gr'], 'vo:ValT')

# put after / before URL adds to the file (GameNotes' notes); a read sees the sandbox copy once written
_u = os.path.join(ROOT, 'run_files', 'test', 'url_after.txt')
if os.path.exists(_u):
    os.remove(_u)
rt.run('put "one" & cr after URL ("file:%s")\nput "two" & cr after URL ("file:%s")\nput "zero" & cr before URL ("file:%s")'
       % (_u, _u, _u))
check('put after / before URL', rt.eval('URL ("file:%s")' % _u), 'zero\none\ntwo\n')

# ---- script behaviors (measured 26 Nov, docs/LIVECODE_FACTS.md "Behaviors"), both run modes
def _bhv_checks(fast):
    tag = '[%s] ' % ('fast' if fast else 'interp')
    r = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'), fast=fast)
    r.open()

    def script(desc, text):
        r.G['gs'] = text
        r.run('global gS\nset the script of %s to gS' % desc)
    r.run('create button "Bh"\ncreate button "BB"\ncreate button "T"\ncreate button "T2"\ncreate group "G"\n'
          'create button "Inner" in group "G"')
    script('button "Bh"', 'local sCount\non foo\nglobal gLog\nput "B:" & the short name of me & "/" & the short name of the '
           'target & "," after gLog\npass foo\nend foo\nfunction bump\nadd 1 to sCount\nreturn sCount\nend bump\n'
           'on go1\nhelper\nend go1\non helper\nglobal gLog\nput "B-helper," after gLog\nend helper\n'
           'function meId\nreturn the long id of me\nend meId')
    script('button "BB"', 'on foo\nglobal gLog\nput "BB:" & the short name of me & "," after gLog\npass foo\nend foo')
    script('button "T"', 'on foo\nglobal gLog\nput "T," after gLog\npass foo\nend foo\n'
           'on helper\nglobal gLog\nput "T-helper," after gLog\nend helper')
    script('this card', 'on foo\nglobal gLog\nput "C," after gLog\nend foo')
    r.run('set the behavior of button "T" to the long id of button "Bh"\n'
          'set the behavior of button "T2" to the long id of button "Bh"')
    check(tag + 'the behavior of: button id N of stack "S" (no card)', r.eval('the behavior of button "T"'),
          'button id %d of stack "xtM1"' % r.obj('button "Bh"').id)
    check(tag + 'no behavior: empty', r.eval('the behavior of button "Bh"'), '')
    r.G['glog'] = ''
    r.run('dispatch "foo" to button "T"')
    check(tag + 'path: object, its behavior (me = the object), card; pass goes on', r.G['glog'], 'T,B:T/T,C,')
    r.G['glog'] = ''
    r.run('dispatch "foo" to button "T2"')
    check(tag + 'object without the handler: the behavior answers', r.G['glog'], 'B:T2/T2,C,')
    check(tag + 'me in a behavior is the object', r.eval('value("meId()", the long id of button "T")'), r.eval('the long id of button "T"'))
    r.G['glog'] = ''
    r.run('send "go1" to button "T"')
    check(tag + 'a call from the behavior starts at me (the object\'s own helper)', r.G['glog'], 'T-helper,')
    r.run('global gR\nput empty into gR\nrepeat 2\ndispatch function "bump" to button "T"\nend repeat\n'
          'put the result after gR\ndispatch function "bump" to button "T2"\nput "," & the result after gR\n'
          'dispatch function "bump" to button "Bh"\nput "," & the result after gR')
    check(tag + 'script locals: one copy per object (T 2, T2 1, the behavior button itself 1)', r.G['gr'], '2,1,1')
    r.run('global gR\nset the behavior of button "T" to the long id of button "Bh"\n'
          'dispatch function "bump" to button "T"\nput the result into gR')
    check(tag + 'the same behavior again keeps the locals', r.G['gr'], '3')
    r.run('global gR, gS\nput the script of button "Bh" into gS\nset the script of button "Bh" to gS\n'
          'dispatch function "bump" to button "T"\nput the result into gR')
    check(tag + 'the behavior\'s script set again: locals start empty', r.G['gr'], '1')
    r.run('set the behavior of button "Bh" to the long id of button "BB"')
    r.G['glog'] = ''
    r.run('dispatch "foo" to button "T"')
    check(tag + 'behavior of a behavior: T, B, BB, card', r.G['glog'], 'T,B:T/T,BB:T,C,')
    r.run('set the behavior of group "G" to the long id of button "BB"')
    r.G['glog'] = ''
    r.run('dispatch "foo" to button "Inner"')
    check(tag + 'a group\'s behavior is on its controls\' path', r.G['glog'], 'BB:G,C,')
    r.run('set the behavior of button "T" to empty')
    r.G['glog'] = ''
    r.run('dispatch "foo" to button "T"')
    check(tag + 'set to empty: the behavior goes', (r.eval('the behavior of button "T"'), r.G['glog']), ('', 'T,C,'))
    errs = []
    for bad in ('the long id of field "F"', '"button id 99999 of stack " & quote & "xtM1" & quote',
                'the long id of button "T"'):
        try:
            r.run('set the behavior of button "BB" to %s' % bad)
            r.run('set the behavior of button "T" to the long id of button "BB"') if 'button "T"' in bad else None
            errs.append('no error')
        except Exception as e:
            errs.append('error')
    check(tag + 'a field, a missing object, a loop: errors', errs, ['error', 'error', 'error'])
    # a script-only stack as the behavior (Thrmnlra's sequencer), its locals per object
    so = os.path.join(ROOT, 'run_files', 'test', 'BhvSO.livecodescript')
    open(so, 'w').write('script "BhvSO"\nlocal sK\non foo\nglobal gLog\nput "SO:" & the short name of me & "," after gLog\n'
                        'pass foo\nend foo\nfunction k\nadd 1 to sK\nreturn sK\nend k\non Setup pA\nglobal gLog\n'
                        'put "setup:" & pA & ":" & the short name of me & "," after gLog\nend Setup\n')
    r.run('create button "U"\ncreate button "U2"\n'
          'set the behavior of button "U" to the long id of stack "%s"\n'
          'set the behavior of button "U2" to the long id of stack "BhvSO"' % so)
    check(tag + 'a script-only stack: the behavior is stack "Name"', r.eval('the behavior of button "U"'), 'stack "BhvSO"')
    check(tag + 'a script-only stack from a file: its long id is its path (measured 27 Nov)',
          (r.eval('the long id of stack "BhvSO"'), r.eval('the short name of stack (the long id of stack "BhvSO")')),
          ('stack "%s"' % r.eval('the filename of stack "BhvSO"'), 'BhvSO'))
    script('this card', 'on itAfter\nglobal gR\ndispatch "Setup" to button "U2" with 1\nput it into gR\n'
           'dispatch "zzNone" to button "U"\nput "," & it after gR\ndispatch "foo" to button "U"\nput "," & it after gR\n'
           'end itAfter')
    r.run('itAfter')
    script('this card', 'on foo\nglobal gLog\nput "C," after gLog\nend foo')
    check(tag + 'it after dispatch: handled / unhandled / passed (behavior passes, measured 27 Nov)',
          r.G['gr'], 'handled,unhandled,passed')
    r.G['glog'] = ''
    r.run('dispatch "foo" to button "U"\ndispatch "Setup" to button "U2" with 7')
    check(tag + 'dispatch reaches a script-only stack behavior', r.G['glog'], 'SO:U,C,setup:7:U2,')
    r.run('global gR\ndispatch function "k" to button "U"\ndispatch function "k" to button "U"\nput the result into gR\n'
          'dispatch function "k" to button "U2"\nput "," & the result after gR')
    check(tag + 'script-only stack behavior: locals per object', r.G['gr'], '2,1')
    r.run('global gLog\nput empty into gLog\nput "x" into tA["k"]\ndispatch "Setup" to button "U" with tA')
    check(tag + 'dispatch ... with an array: the array arrives (as text: empty, measured 26 Nov)', r.G['glog'], 'setup::U,')
    script('button "Bh"', 'on Setup pA\nglobal gLog\nput pA["k"] & "," after gLog\nend Setup')
    r.run('global gLog\nput empty into gLog\nput "x" into tA["k"]\ndispatch "Setup" to button "T2" with tA')
    check(tag + 'dispatch ... with an array: an array element reads', r.G['glog'], 'x,')
    # harvested `behavior` properties (tests/stacks/bhv)
    h = StackRuntime(os.path.join(ROOT, 'tests/stacks/bhv'), files_dir=os.path.join(ROOT, 'run_files', 'test'), fast=fast)
    h.open()
    h.G['glog'] = ''
    h.run('dispatch "foo" to button "User1"\ndispatch "foo" to button "Inner"')
    check(tag + 'harvested behavior: button and group', h.G['glog'], 'H:User1,C,H:Grp,C,')
    check(tag + 'harvested behavior reads back', h.eval('the behavior of group "Grp"'), 'button id 1003 of stack "xtB1"')
    check(tag + 'harvested behavior to a missing object: a load error, no behavior',
          (h.eval('the behavior of button "Broken"'), any('behavior' in e for _, e in h.load_errors)), ('', True))


for _fast in (True, False):
    _bhv_checks(_fast)


# create stack (measured 27 Nov, LIVECODE_FACTS "create stack"): the Library's Play makes the game's window this way
rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
rt.open()
_msgs = ''.join('on %s\nglobal glog\nput "%s," after glog\nend %s\n' % (m, m, m) for m in
                ('preOpenStack', 'openStack', 'openCard', 'closeCard', 'closeStack'))
rt.G['gs'] = _msgs
rt.G['glog'] = ''
rt.run('global gS, gR\nlock messages\ncreate invisible stack "PlayX"\nunlock messages\nput it into gR\n'
       'set the script of stack "PlayX" to gS\nput "|" & the result after gR')
check('create stack: it, the defaultStack kept, open, invisible, 1 card, 32,32,288,288, script set (result empty)',
      (rt.G['gr'], rt.eval('the short name of the defaultStack'), 'PlayX' in rt.eval('the openStacks').split('\n'),
       rt.eval('the visible of stack "PlayX"'), rt.eval('the number of cards of stack "PlayX"'),
       rt.eval('the rect of stack "PlayX"'), rt.eval('the mainStack of stack "PlayX"')),
      ('stack "PlayX"|', 'xtM1', True, 'false', '1', '32,32,288,288', 'PlayX'))
rt.run('show stack "PlayX"\ngo stack "PlayX"')
check('create stack, then show + go: no open messages (it was open), it is shown',
      (rt.G['glog'], rt.default_stack.name, rt.eval('the visible of stack "PlayX"')), ('', 'PlayX', 'true'))
rt.run('close stack "xtM1"')
check('the first stack closes while the made one is shown: the window goes on with it',
      (rt.closed, rt.default_stack.name, rt.first_stack.name), (False, 'PlayX', 'PlayX'))
rt.run('set the destroyStack of stack "PlayX" to true\nclose stack "PlayX"')
check('then the shown one closes: closeCard, closeStack; the window ends', (rt.G['glog'], rt.closed), ('closeCard,closeStack,', True))
rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
rt.open()
rt.run('quit')
check('quit: the window ends', rt.closed, True)

# x1-04 (the xt3d bench, measured 27 Nov): file commands, an option menu's label, accept, the screenLoc
rt = StackRuntime(os.path.join(ROOT, 'tests/stacks/mini'), files_dir=os.path.join(ROOT, 'run_files', 'test'))
rt.open()
_p = os.path.join(ROOT, 'run_files', 'test', 'x104_file.txt')
check('write / close a file not open; append, write (empties), update (over the start); missing folder',
      rt.run('put "%s" into p\nput "abc" into URL ("file:" & p)\nwrite "zz" to file p\nput "[" & the result & "]" into r\n'
             'close file p\nput "[" & the result & "]" after r\nopen file p for append\nwrite "1" & return to file p\n'
             'write "2" to file p\nclose file p\nput "[" & URL ("file:" & p) & "]" after r\nopen file p for write\n'
             'write "w" to file p\nclose file p\nput "[" & URL ("file:" & p) & "]" after r\nopen file p\n'
             'write "U" to file p\nclose file p\nput "[" & URL ("file:" & p) & "]" after r\n'
             'open file (p & ".nope/q") for append\nput "[" & the result & "]" after r\nreplace return with "/" in r\n'
             'return r' % _p),
      "[file is not open for write][file is not open][abc1/2][w][U][can't open that file]")
check('an option menu: set the text = line 1 is the label, set the menuHistory = that line',
      rt.run('create button "OptX"\nset the style of it to "menu"\nset the menuMode of it to "option"\n'
             'put "[" & the label of button "OptX" & "]" into r\nset the text of button "OptX" to "a" & cr & "b"\n'
             'put "[" & the label of button "OptX" & "]" after r\nset the menuHistory of button "OptX" to 2\n'
             'put "[" & the label of button "OptX" & "]" after r\nset the text of button "OptX" to "x" & cr & "y"\n'
             'return r & "[" & the label of button "OptX" & "]" & the menuHistory of button "OptX"'),
      '[][a][b][x]1')
check('set the X of an object empties the result too; set the script: empty when it compiles (measured 27 Nov)',
      rt.run('accept connections on port 8799 with message "x"\nput the result is empty into r\n'
             'set the cXx of this card to 1\nput "," & (the result is empty) after r\n'
             'accept connections on port 8799 with message "x"\nset the script of button "OptX" to "on mouseUp" & cr & "end mouseUp"\n'
             'return r & "," & (the result is empty)'), 'false,true,true')
check('accept connections: no sockets, the result says so; the screenLoc',
      rt.run('accept connections on port 8799 with message "x"\nreturn (the result is not empty) & "," & the screenLoc'),
      'true,768,432')

print('\n%d of %d stack checks pass' % (N[0] - len(BAD), N[0]))
sys.exit(1 if BAD else 0)

