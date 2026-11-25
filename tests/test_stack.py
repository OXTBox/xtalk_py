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
check('no script errors', rt.errors, [])
rt.run('put "x" into URL "file:/tmp/escape_test.txt"')
rt.run('put "y" into URL ("file:" & specialFolderPath("Documents") & "/in.txt")')
home = rt.host.folders['home']
check('a write outside the sandbox is redirected into it',
      (os.path.exists('/tmp/escape_test.txt'), os.path.exists(os.path.join(home, 'elsewhere', 'tmp', 'escape_test.txt'))), (False, True))
check('a sandbox write stays where it says', os.path.exists(os.path.join(home, 'Documents', 'in.txt')), True)

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
print('\n%d of %d stack checks pass' % (N[0] - len(BAD), N[0]))
sys.exit(1 if BAD else 0)
