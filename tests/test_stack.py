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
check('up arrow: first card', rt.eval('the number of this card'), '1')
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
check('no errors in these checks', rt.errors, [])

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
print('\n%d of %d stack checks pass' % (N[0] - len(BAD), N[0]))
sys.exit(1 if BAD else 0)
