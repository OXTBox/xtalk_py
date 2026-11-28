#!/usr/bin/env python3
"""The window rules (docs/WINDOW_RULES.md) on HIDDEN windows: place, fit, the owner's resize (min/max,
resizeStack), the grip, the close box (closeStackRequest), remembered place and size. Needs the .venv.

    WAYLAND_DISPLAY=no-wayland .venv/bin/python -I tests/test_window_rules.py

A close click is faked by setting GLFW's close flag (what the window system does on a click); the owner's
drag of the window edge by giving the window a new size. Nothing is remembered in his run_files: the
memory file is a temporary one.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ['WAYLAND_DISPLAY'] = 'no-wayland'   # a hidden window's framebuffer resizes under X11 only
os.environ.pop('XTALK_NO_REMEMBER', None)
from xtalk.stack import StackRuntime           # noqa: E402
from xtalk.stack import view as V              # noqa: E402
rl = V.rl
TMP = tempfile.mkdtemp(prefix='window_rules_')
V.WINDOWS_FILE = os.path.join(TMP, 'windows.json')
V.SCALE_FILE = os.path.join(TMP, 'window_scale.json')
FILES = os.path.join(ROOT, 'run_files', 'test')
WS = V.windows_scale()

N, BAD = [0], []
def check(name, got, want):
    N[0] += 1
    if got != want:
        BAD.append(name)
        print('FAIL  %s\n        want %r\n        got  %r' % (name, want, got))


def frames(v, n=1):
    for _ in range(n):
        v.frame()
        if v.close_asked > v.close_done:            # as View.run does after each frame
            v.close_done = v.close_asked
            v.close_request()


def click_close(v):
    rl.glfw_set_window_should_close(rl.glfw_get_current_context(), 1)
    frames(v)


MINI = os.path.join(ROOT, 'tests/stacks/mini')
LOG = '''on resizeStack a,b,c,d
   global gLog
   put "resize:" & a & "," & b & "," & c & "," & d & ";" after gLog
end resizeStack
on closeStackRequest
   global gLog, gKeep
   put "request;" after gLog
   if gKeep is true then exit closeStackRequest
   set the destroyStack of this stack to true
   pass closeStackRequest
end closeStackRequest
on closeStack
   global gLog
   put "closeStack;" after gLog
end closeStack'''

def window(folder, remember=False, **kw):
    rt = StackRuntime(folder, files_dir=FILES)
    v = V.View(rt, hidden=True, rules=True, scale=kw.pop('scale', 1.0), **kw)
    rt.on_wait, rt.on_menu, rt.on_dialog = v.wait_frames, v.menu_frames, v.dialog_frames
    rt.open()
    rt.G['gscript'] = LOG
    rt.run('global gScript\nset the script of this stack to gScript')
    rt.G['glog'] = ''
    if remember:                       # a hidden window remembers nothing unless asked: placed again, remembering
        v.remember = True
        v.place_window()
    return rt, v


# 1. opening: 200,32 (screen units), the stack's rect says where the window is
rt, v = window(MINI)
st = rt.default_stack
check('opens at 200,32 (topLeft of the stack)', (st.rect[0], st.rect[1]), (200, 32))
check('the window is there (pixels = units x Windows scale)', v.place_px, (200 * WS, 32 * WS))
check('globalLoc base follows', rt.window_pos, (200, 32))
check('size kept', (st.width, st.height), (300, 200))

# 2. a script resizes the stack: resizeStack at once (measured), the window follows
rt.run('set the width of this stack to 320')
check('script resize: resizeStack new,old', rt.G['glog'], 'resize:320,200,300,200;')
frames(v)
check('window follows the script size', (rl.get_screen_width(), rl.get_screen_height()), (320, 200))
check('width keeps the centre: the window moves (measured)', v.place, (190, 32))

# 3. the owner drags the window bigger: the stack follows, resizeStack, top-left kept
rt.G['glog'] = ''
rl.set_window_size(400, 260)
frames(v)
check('owner resize: stack size', (st.width, st.height), (400, 260))
check('owner resize: resizeStack', rt.G['glog'], 'resize:400,260,320,200;')
check('owner resize: top-left kept', (st.rect[0], st.rect[1]), (190, 32))
frames(v, 2)
check('owner resize: no second resizeStack', rt.G['glog'], 'resize:400,260,320,200;')

# 4. min/max: the owner can not make it smaller than minWidth/minHeight
rt.run('set the minWidth of this stack to 250\nset the minHeight of this stack to 150')
rt.G['glog'] = ''
rl.set_window_size(100, 100)
frames(v, 2)
check('held at the min size', (st.width, st.height), (250, 150))
check('held at the min size: the window too', (rl.get_screen_width(), rl.get_screen_height()), (250, 150))
check('min size: one resizeStack', rt.G['glog'], 'resize:250,150,400,260;')
check('limits given to the window', v.limits_px[:2], (250, 150))

# 5. the grip in the lower-right corner
rt.G['glog'] = ''
real = (rl.get_mouse_position, rl.is_mouse_button_pressed, rl.is_mouse_button_down)
mouse = {'at': (245, 145), 'down': True, 'pressed': True}
rl.get_mouse_position = lambda: rl.Vector2(*mouse['at'])
rl.is_mouse_button_pressed = lambda b: b == 0 and mouse['pressed']
rl.is_mouse_button_down = lambda b: b == 0 and mouse['down']
try:
    check('grip is on', bool(v.grip_on()), True)
    check('a press in the corner takes the mouse', v.grip(), True)
    mouse['pressed'] = False
    mouse['at'] = (295, 175)
    v.grip()
    check('grip drag: bigger', (st.width, st.height), (300, 180))
    check('grip drag: resizeStack', rt.G['glog'], 'resize:300,180,250,150;')
    mouse['down'] = False
    v.grip()
    check('grip released', v.gripping, None)
finally:
    rl.get_mouse_position, rl.is_mouse_button_pressed, rl.is_mouse_button_down = real

# 6. resizable false: no grip, the owner can not resize
rt.run('set the resizable of this stack to false')
frames(v)
check('resizable false: no grip', bool(v.grip_on()), False)
check('resizable false: told to the window', v.limits_px[4], False)
rt.run('set the resizable of this stack to true')
frames(v)

# 7. the close box: closeStackRequest first; kept by the handler = the window stays
rt.G['glog'], rt.G['gkeep'] = '', 'true'
click_close(v)
check('close box: closeStackRequest sent', rt.G['glog'], 'request;')
check('kept by its handler: still open', rt.closed, False)
check('one click = one request', (v.close_asked, v.close_done), (1, 1))
frames(v, 2)
check('no second request without a click', rt.G['glog'], 'request;')
# a click while a script waits: answered after the wait, the wait is not cut short
rt.G['glog'] = ''
rl.glfw_set_window_should_close(rl.glfw_get_current_context(), 1)
v.wait_frames(50)
check('click during a wait: noted, not yet sent', (v.close_asked - v.close_done, rt.G['glog']), (1, ''))
frames(v)
check('... sent once back in the main loop', rt.G['glog'], 'request;')
# a second click while the first is still waiting = closes for sure
rl.glfw_set_window_should_close(rl.glfw_get_current_context(), 1)
v.wait_frames(20)
rl.glfw_set_window_should_close(rl.glfw_get_current_context(), 1)
v.wait_frames(20)
check('second click before the answer: closes', v.should_close(), True)
v.force_close = False
v.close_done = v.close_asked
# passed: the stack closes (closeCard, closeStack), destroyStack set by its handler
rt.G['glog'], rt.G['gkeep'] = '', 'false'
click_close(v)
check('passed: closed', rt.closed, True)
check('passed: request, then closeStack', rt.G['glog'], 'request;closeStack;')
check('LIB_ALPHA 12b: destroyStack set', rt.host.obj_prop(st, 'destroystack'), 'true')
v.close()

# 8. remembered place and size: written at close, used at the next opening (fitted to the screen)
rt, v = window(MINI, remember=True, key='rules test')
v.move_to(300, 100)
rt.run('set the width of this stack to 420\nset the height of this stack to 240')
frames(v, 2)
v.save_window()
v.close()
rec = V.remembered_windows().get('rules test')
check('remembered', rec, {'left': 300 - 60, 'top': 100 - 20, 'width': 420, 'height': 240})
rt, v = window(MINI, remember=True, key='rules test')
st = rt.default_stack
check('reopens at its remembered place', (st.rect[0], st.rect[1]), (240, 80))
check('reopens at its remembered size', (st.width, st.height), (420, 240))
v.close()
V.remember_window('rules test', left=5000, top=5000)
rt, v = window(MINI, remember=True, key='rules test')
st = rt.default_stack
sw, sh = v.screen_px()
check('a place off the screen is brought back on it', (st.rect[0] * WS + 420 <= sw + 1, st.rect[1] * WS + 240 <= sh - V.TASKBAR * WS + 1),
      (True, True))
v.close()

# 9. too big for the screen: moved, then shrunk (resizable) not under its min size; scale remembered too
rt, v = window(MINI, scale=2.0)
st = rt.default_stack
rt.run('set the minWidth of this stack to 100\nset the minHeight of this stack to 100')
rt.G['glog'] = ''
rt.run('set the rect of this stack to 0,0,1500,900')
v.follow_stack_size()
v.place_window()
sw, sh = v.screen_px()
w, h = rl.get_screen_width(), rl.get_screen_height()
check('too big: fits the screen', (v.place_px[0] + w <= sw, v.place_px[1] + h <= sh - V.TASKBAR * WS), (True, True))
check('too big: shrunk with resizeStack', rt.G['glog'].count('resize:'), 2)
v.close()
V.remember_scale('rules test', 1.4)
check('scale remembered in the same file', (V.window_scale('rules test'), V.remembered_windows()['rules test']['width']), (1.4, 420))

# 10. a hidden window without the rules is as before (checks keep their fixed window)
rt = StackRuntime(MINI, files_dir=FILES)
before = list(rt.default_stack.rect)
v = V.View(rt, hidden=True)
rt.open()
check('hidden, no rules: rect untouched', rt.default_stack.rect, before)
check('hidden, no rules: not placed', v.placed, False)
v.close()

print('%d of %d window rule checks pass' % (N[0] - len(BAD), N[0]))
sys.exit(1 if BAD else 0)
