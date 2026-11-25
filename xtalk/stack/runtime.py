"""StackRuntime: a harvested stack, running. No GUI here (xtalk/stack/view.py draws it with raylib).

    from xtalk.stack import StackRuntime
    rt = StackRuntime('~/projects/XTJSON/Game_card_reader_11_13_2025')
    rt.open()                          # preOpenStack, preOpenCard, openStack, openCard
    rt.click('button id 6592')         # mouseDown + mouseUp to it, as a click there would
    rt.get('graphic "Box1"', 'label')
    rt.tick(100)                       # 100 ms of virtual time: runs `send ... in N milliseconds`

Every scripted object has its own script context (its handlers and script locals); globals are
shared. A message goes to its target, then along the message path: the control, its groups, the
card, the card's stack, the mainstack. `pass` hands it on; `send`/`dispatch` start a new one.
"""
import heapq, os, re
from ..pyrt import Runtime
from ..interp import Frame, Thrown, ExitRepeat, NextRepeat, Break
from ..values import XtError
from .model import Harvest
from .host import StackHost

SCRIPT_ERRORS = (XtError, Thrown, ExitRepeat, NextRepeat, Break, RecursionError, ValueError, KeyError, IndexError, TypeError, ZeroDivisionError, OverflowError, OSError, AttributeError)   # a script error never ends the window: it goes to rt.errors (the panel)
OPEN_MESSAGES = ('preOpenStack', 'preOpenCard', 'openStack', 'openCard')   # order NOT measured (LIVECODE_FACTS)


class ObjInterp(Runtime):
    """the script context of one object"""

    def __init__(self, rt, obj):
        super().__init__()
        self.rt, self.obj = rt, obj
        self.G = rt.G
        self.host = rt.host
        self.props = rt.props

    def lookup(self, name):
        n = name.lower()
        for c in self.rt.contexts(self.obj):
            h = c.handlers.get(n)
            if h is not None:
                return c, h
        return None, None

    def after_pass(self, name, args):
        n = name.lower()
        later = self.rt.contexts(self.obj)
        for c in later[later.index(self) + 1:] if self in later else []:
            if n in c.handlers:
                return c.invoke(name, args)
        return ''

    def invoke(self, name, args):
        self.rt.running.append(self.obj)
        try:
            return super().invoke(name, args)
        finally:
            self.rt.running.pop()

    def getvar(self, fr, name):
        if name.lower() == 'me' and 'me' not in fr.vars and 'me' not in fr.globals:
            return self.host.long_id(self.obj)
        return super().getvar(fr, name)


class StackRuntime:
    def __init__(self, folder, files_dir=None):
        self.harvest = Harvest(os.path.expanduser(folder))
        self.default_stack = self.harvest.main
        self.G = {}
        self.props = {'itemdelimiter': ',', 'linedelimiter': '\n', 'numberformat': '0.######', 'casesensitive': 'false'}
        self.host = StackHost(self)
        files = files_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                          'run_files')
        self.host.folders = {'documents': os.path.join(files, 'Documents'), 'temporary': os.path.join(files, 'tmp'),
                             'desktop': os.path.join(files, 'Desktop'), 'home': files, 'resources': self.harvest.folder}
        self.ctx = {}
        self.load_errors = []
        self.errors = []               # script errors while running: (message, object, error text)
        self.answers = []              # what `answer` would have shown
        self.target = None
        self.running = []              # objects whose handlers are running (innermost last)
        self.mouse = (0, 0)
        self.button_down = False       # the mouse button is held (mouse_down .. mouse_up)
        self.grabbed = None            # `grab`: (control, x offset, y offset) until the button comes up
        self.pressed = None            # the object the button went down on (it gets mouseMove while held)
        self.hover = None              # the control the mouse is in, as far as mouseEnter/mouseLeave go
        self.on_menu = None            # the window: show a menu, return the pick (text) or None
        self.on_dialog = None          # the window: show answer/ask, return (it, the result)
        self.dialog_answers = []       # no window (tests): replies to answer/ask in order (None = Cancel)
        self.menu_choices = []         # no window (tests): the picks to make, in order (None = close the menu)
        self.menus = []                # every menu shown: (button name, [item labels])
        self.swallow_up = False        # a menu opened while the button was down took the release
        self.started = []              # programs shell() started (.py scripts), for tests to wait on
        self.last_down = None          # (object, clock, x, y) of the last press: a quick second one is a double click
        self.double = False            # this press is the second of a double click
        self.scroll_drag = None        # a field whose scrollbar the mouse is dragging
        self.thumb_drag = None         # a scrollbar / slider whose thumb the mouse is dragging
        self.start_programs = True     # False: shell() only notes the script (the survey: no windows pop up)
        self.not_started = []          # the scripts shell() would have started
        self.clock = 0.0               # virtual milliseconds
        self.timers, self._seq = [], 0
        self.changed = True
        self.on_wait = None
        self.keys_down = set()         # 'shiftkey', 'optionkey'... while held (the window fills it)
        self.closed = False            # the window sets this: draw frames while a script waits
        for st in self.harvest.stacks:
            for o in [st] + st.children + [c for card in st.children for c in card.flat()]:
                if o.script.strip() and id(o) not in self.ctx:
                    c = ObjInterp(self, o)
                    c.load(o.script.split('\n', 1)[1] if o.script.startswith('script ') else o.script)
                    for e in c.load_errors:
                        self.load_errors.append((self.host.name_of(o, 'long'), e))
                    self.ctx[id(o)] = c

    # ------------------------------------------------------------ the message path
    def path(self, o):
        out = []
        while o is not None:
            out.append(o)
            if o.type == 'card':
                o = o.stack
            elif o.type == 'stack':
                o = o.mainstack if o.mainstack is not o else None
            else:
                o = o.parent
        return out

    def contexts(self, o):
        return [self.ctx[id(x)] for x in self.path(o) if id(x) in self.ctx]

    def running_obj(self):
        return self.running[-1] if self.running else None

    def message(self, o, msg, args=()):
        """the engine sends msg to o (mouseUp, openCard...): the first handler on the path runs"""
        self.target = o
        n = msg.lower()
        for c in self.contexts(o):
            if n in c.handlers:
                try:
                    return c.invoke(msg, list(args))
                except SCRIPT_ERRORS as e:
                    self.errors.append((msg, self.host.name_of(o, 'long'), '%s: %s' % (type(e).__name__, e)))
                    return ''
        return None

    def dispatch(self, o, msg, args):
        saved = self.target
        self.message(o, msg, args)
        self.target = saved

    def send_text(self, o, text):
        """`send "hello 7" to o`: the text runs as a statement, starting at o"""
        c = self.ctx.get(id(o)) or ObjInterp(self, o)
        saved = self.target
        self.target = o
        try:
            self.running.append(o)
            c.run(text)
        finally:
            self.running.pop()
            self.target = saved

    def after(self, ms, o, text):
        self._seq += 1
        heapq.heappush(self.timers, (self.clock + ms, self._seq, o, text))

    def wait(self, ms):
        """`wait`: time passes; a window keeps drawing (on_wait), timers wait for the next tick"""
        if self.on_wait is not None:
            self.on_wait(ms)
        self.clock += ms

    def tick(self, ms):
        """let ms of virtual time pass: due `send ... in` messages run in order"""
        end = self.clock + ms
        while self.timers and self.timers[0][0] <= end:
            t, _, o, text = heapq.heappop(self.timers)
            self.clock = max(self.clock, t)
            try:
                self.send_text(o, text)
            except SCRIPT_ERRORS as e:
                self.errors.append((text, self.host.name_of(o, 'long'), '%s: %s' % (type(e).__name__, e)))
        self.clock = end

    # ------------------------------------------------------------ cards and events
    def open(self):
        st = self.default_stack
        for m in OPEN_MESSAGES:
            self.message(st.current if 'Card' in m else st, m)

    def go_card(self, card):
        st = card.stack
        if st.current is not None and st.current is not card:
            self.message(st.current, 'closeCard')
        st.current = card
        self.default_stack = st
        self.message(card, 'preOpenCard')
        self.message(card, 'openCard')
        self.changed = True

    def visible(self, o):
        v = self.host.obj_prop(o, 'visible')
        return v != 'false'

    def control_at(self, x, y):
        """the topmost visible control under the point (layer order, a group's children above it)"""
        hit = None
        for o in self.default_stack.current.flat():
            if o.type == 'group':
                continue
            l, t, r, b = o.rect
            if l <= x < r and t <= y < b and self._shown(o):
                hit = o
        return hit

    def _shown(self, o):
        while o is not None and o.type not in ('card', 'stack'):
            if not self.visible(o):
                return False
            o = o.parent
        return True

    def mouse_down(self, x, y, button=1):
        self.mouse = (x, y)
        self._enter_leave()            # the mouse came here before it pressed
        self.button_down = True
        o = self.control_at(x, y) or self.default_stack.current
        self.pressed = o
        if hasattr(self, 'log_clicks'):
            self.log_clicks.append('%s at %d,%d' % (self.host.name_of(o, 'short'), x, y))
        last = self.last_down
        self.double = bool(last and last[0] is o and self.clock - last[1] <= 400 and abs(last[2] - x) <= 4 and abs(last[3] - y) <= 4)
        self.last_down = None if self.double else (o, self.clock, x, y)
        if o.type == 'field':
            if self.in_field_scrollbar(o, x, y):
                self.scroll_drag = o
                self.scroll_field_to(o, y)
                return o
            if self.host.obj_prop(o, 'listbehavior') == 'true' and self.host.obj_prop(o, 'disabled') != 'true':
                n = self.field_line_at(o, y)     # the line is hilited before mouseDown (the owner's scripts read it there)
                o.props['hilitedLines'] = str(n) if n else ''
                self.changed = True
        if o.type == 'scrollbar' and self.host.obj_prop(o, 'disabled') != 'true':
            self.thumb_drag = o
            self.set_thumb_at(o, x, y)
        self.message(o, 'mouseDoubleDown' if self.double else 'mouseDown', [str(button)])
        if o.type == 'button' and self.host.obj_prop(o, 'style') == 'menu' and self.visible(o) \
                and self.host.obj_prop(o, 'menumode') in ('option', 'pulldown', 'combobox') \
                and self.host.obj_prop(o, 'disabled') != 'true':
            l, t, r, b = o.rect                  # a menu button opens its list under itself
            self.show_menu(o, l, b)
        return o

    def mouse_up(self, x, y, button=1, down_on=None):
        self.mouse_move(x, y)
        self.button_down = False
        self.pressed = None
        self.thumb_drag = None
        if self.scroll_drag is not None:     # the release ends a scrollbar drag: no message
            self.scroll_drag = None
            return down_on
        if self.swallow_up:              # the menu took this release: no mouseUp / mouseRelease
            self.swallow_up = False
            self._enter_leave()
            return down_on
        o = self._release(button, down_on)
        self._enter_leave()            # held back while the button was down (Dictionary, mouseEnter/mouseLeave)
        return o

    def _release(self, button, down_on):
        x, y = self.mouse
        if self.grabbed is not None:   # a grabbed control gets the mouseUp (Dictionary, grab)
            g = self.grabbed[0]
            self.grabbed = None
            self.message(g, 'mouseUp', [str(button)])
            return g
        o = self.control_at(x, y) or self.default_stack.current
        if down_on is not None and o is not down_on:
            self.message(down_on, 'mouseRelease', [str(button)])
            return o
        if o.type == 'button':
            self._auto_hilite(o)
        self.message(o, 'mouseDoubleUp' if self.double else 'mouseUp', [str(button)])
        return o

    def _enter_leave(self):
        """mouseLeave to the control the mouse left, mouseEnter to the one it is in now
        (order against mouseMove: not measured)"""
        now = self.control_at(*self.mouse)
        if now is self.hover:
            return
        old, self.hover = self.hover, now
        if old is not None and old.card is self.default_stack.current:
            self.message(old, 'mouseLeave')
        if now is not None:
            self.message(now, 'mouseEnter')

    # ------------------------------------------------------------ fields: lines, scrolling
    def inherit(self, o, key):
        """a text or colour property: the object, its groups, card, stack, then the stack's effective value"""
        from .host import canon
        k = canon(key)
        x = o
        while x is not None:
            for pk, v in x.props.items():
                if canon(pk) == k and v != '':
                    return v
            x = x.parent if x.type != 'card' else x.stack
            if x is not None and x.type == 'stack':
                for pk, v in x.props.items():
                    if canon(pk) == k and v != '':
                        return v
                return next((v for ek, v in x.effective.items() if canon(ek) == k), None)
        return None

    def field_metrics(self, o):
        """(text size, line height, margin, vScroll, scrollbar width) as the window draws the field
        (line height = size * 4/3 + 2: our drawing, not measured against LiveCode)"""
        try:
            size = int(float(self.inherit(o, 'textSize') or 12))
        except ValueError:
            size = 12
        try:
            m = int(float(str(self.host.obj_prop(o, 'margins')).split(',')[0] or 8))
        except ValueError:
            m = 8
        try:
            scroll = int(float(self.host.obj_prop(o, 'vscroll') or 0))
        except ValueError:
            scroll = 0
        try:
            sbw = int(float(self.host.obj_prop(o, 'scrollbarwidth') or 16)) if self.host.obj_prop(o, 'vscrollbar') == 'true' else 0
        except ValueError:
            sbw = 16
        return size, size * 4 / 3 + 2, m, scroll, sbw

    def field_line_at(self, o, y):
        """the line of field o at window y (0: below the last line)"""
        size, lh, m, scroll, _ = self.field_metrics(o)
        n = int((y - (o.rect[1] + m / 2 - scroll)) // lh) + 1
        return n if 1 <= n <= len(o.text.split('\n')) else 0

    def in_field_scrollbar(self, o, x, y):
        sbw = self.field_metrics(o)[4]
        return bool(sbw) and x >= o.rect[2] - sbw - 1

    def field_max_scroll(self, o):
        size, lh, m, scroll, sbw = self.field_metrics(o)
        return max(0, int(len(o.text.split('\n')) * lh + m - o.height))

    def scroll_field(self, o, pixels):
        """the mouse wheel over a field"""
        top = self.field_max_scroll(o)
        cur = self.field_metrics(o)[3]
        new = max(0, min(top, cur + int(pixels)))
        if new != cur:
            o.props['vScroll'] = str(new)
            self.changed = True
            self.message(o, 'scrollbarDrag', [str(new)])

    def scroll_field_to(self, o, y):
        """the mouse on the scrollbar strip: the thumb goes where the mouse is"""
        top = self.field_max_scroll(o)
        f = (y - o.rect[1]) / max(1, o.height)
        self.scroll_field(o, int(max(0, min(1, f)) * top) - self.field_metrics(o)[3])

    # ------------------------------------------------------------ scrollbars and sliders
    def thumb_range(self, o):
        try:
            a = float(self.host.obj_prop(o, 'startvalue') or 0)
            b = float(self.host.obj_prop(o, 'endvalue') or 65535)
        except ValueError:
            a, b = 0.0, 65535.0
        return a, b

    def set_thumb_at(self, o, x, y):
        """the thumb goes under the mouse (the window draws a 12 px thumb); a change sends scrollbarDrag.
        Whole numbers when both ends are whole: not measured."""
        a, b = self.thumb_range(o)
        l, t, r, btm = o.rect
        if r - l >= btm - t:
            f = (x - l - 6) / max(1, r - l - 12)
        else:
            f = (y - t - 6) / max(1, btm - t - 12)
        v = a + max(0.0, min(1.0, f)) * (b - a)
        v = round(v) if a == int(a) and b == int(b) else round(v, 4)
        text = str(int(v)) if v == int(v) else str(v)
        if self.host.obj_prop(o, 'thumbposition') == text:
            return
        o.props['thumbPosition'] = text
        self.changed = True
        self.message(o, 'scrollbarDrag', [text])

    # ------------------------------------------------------------ menus
    @staticmethod
    def menu_items(text):
        """a menu button's text -> [(label, pick, enabled)], ('-', None, False) for a line;
        a tab-indented line belongs to the item above it (picked as "Parent|Child")"""
        out, parent = [], None
        for raw in str(text).split('\n'):
            if raw.strip() == '':
                continue
            sub = raw.startswith('\t')
            line = raw.strip('\t')
            if line == '-':
                out.append(('-', None, False, sub))
                continue
            enabled = not line.startswith('(')
            line = line.lstrip('(')
            while line[:2] in ('!c', '!n', '!r', '!u', '!C', '!N', '!R', '!U'):
                line = line[2:]
            line = re.sub(r'(?<!/)/[^/]$', '', line)          # Save/S: the shortcut is not shown
            label = line.replace('//', '/').replace('&&', '\0').replace('&', '').replace('\0', '&')
            if not sub:
                parent = label
            out.append((label, (parent + '|' + label) if sub and parent else label, enabled, sub))
        return out

    def show_menu(self, o, x, y):
        """show o's menu (Dictionary, popup: the handler pauses while it is shown); a pick sets the
        menuHistory (an option menu shows it as its label) and sends menuPick to the button.
        Order of menuPick against the rest of the handler: not measured."""
        items = self.menu_items(o.text)
        self.menus.append((o.name, [i[0] for i in items]))
        if self.button_down:
            self.swallow_up = True
        if self.on_menu is not None:
            pick = self.on_menu(items, x, y)
        else:
            pick = self.menu_choices.pop(0) if self.menu_choices else None
        if pick is None:
            return
        n = next((k + 1 for k, i in enumerate(i for i in items if not i[3]) if i[1] == pick.split('|')[0]), 0)
        if n:
            o.props['menuHistory'] = str(n)
        if self.host.obj_prop(o, 'menumode') in ('option', 'combobox'):
            o.props['label'] = pick
            self.changed = True
        self.message(o, 'menuPick', [pick])

    def grab(self, o):
        """`grab o` (LiveCode Dictionary): only while the button is down and the mouse is inside o;
        returns at once, o follows the mouse until the button comes up"""
        x, y = self.mouse
        l, t, r, b = o.rect
        if self.button_down and l <= x < r and t <= y < b:
            self.grabbed = (o, x - l, y - t)

    def mouse_move(self, x, y):
        """the mouse is at x,y: a grabbed control follows it (hidden on the way: the grab ends, no message)"""
        if (x, y) == self.mouse:
            return
        self.mouse = (x, y)
        if self.grabbed is not None:
            self._follow(x, y)
        if self.scroll_drag is not None:
            self.scroll_field_to(self.scroll_drag, y)
            return
        if self.thumb_drag is not None:
            self.set_thumb_at(self.thumb_drag, x, y)
        if not self.button_down:
            self._enter_leave()
        # mouseMove (Dictionary): to the control under the mouse, or the card; while the button is held,
        # to the object that was clicked, even outside it
        o = self.pressed if self.button_down and self.pressed is not None else \
            (self.control_at(x, y) or self.default_stack.current)
        self.message(o, 'mouseMove', [str(x), str(y)])

    def _follow(self, x, y):
        o, dx, dy = self.grabbed
        if not self._shown(o) or o.card is not self.default_stack.current:
            self.grabbed = None
            return
        self.move_by(o, x - dx - o.rect[0], y - dy - o.rect[1])

    def move_by(self, o, dx, dy):
        """move a control (a group with all inside it) by dx,dy pixels"""
        if not (dx or dy):
            return
        for c in [o] + (o.flat() if o.type == 'group' else []):
            c.rect = [c.rect[0] + dx, c.rect[1] + dy, c.rect[2] + dx, c.rect[3] + dy]
            if c.points:
                c.points = [None if q is None else [q[0] + dx, q[1] + dy] for q in c.points]
        self.changed = True

    def drag(self, start, end, steps=4):
        """for tests: press at start (x,y), move to end in steps, release there"""
        o = self.mouse_down(*start)
        for i in range(1, steps + 1):
            self.mouse_move(start[0] + (end[0] - start[0]) * i // steps, start[1] + (end[1] - start[1]) * i // steps)
        return self.mouse_up(*end, down_on=o)

    def _auto_hilite(self, o):
        style = self.host.obj_prop(o, 'style')
        if self.host.obj_prop(o, 'autohilite') == 'false':
            return
        if style == 'checkbox':
            o.props['hilited'] = 'false' if self.host.obj_prop(o, 'hilited') == 'true' else 'true'
        elif style == 'radiobutton':
            group = o.parent if o.parent is not None and o.parent.type == 'group' else None
            if group is not None:
                for s in group.children:
                    if s.type == 'button' and self.host.obj_prop(s, 'style') == 'radiobutton':
                        s.props['hilited'] = 'false'
            o.props['hilited'] = 'true'

    def click(self, where):
        """a click on an object (text naming it) or at 'x,y'"""
        if isinstance(where, str) and not where[:1].isdigit():
            o = self.host.resolve(where)
            x, y = o.loc
        else:
            x, y = (where if not isinstance(where, str) else [int(v) for v in where.split(',')])
        self.last_down = None              # one deliberate click: never the second half of a double click
        o = self.mouse_down(x, y)
        self.mouse_up(x, y, down_on=o)
        return o

    def double_click(self, where):
        """for tests: two clicks at once: mouseDown, mouseUp, mouseDoubleDown, mouseDoubleUp"""
        o = self.click(where)
        x, y = self.mouse
        o2 = self.mouse_down(x, y)
        self.mouse_up(x, y, down_on=o2)
        return o

    def key(self, ch):
        self.message(self.default_stack.current, 'keyDown', [ch])

    # ------------------------------------------------------------ for tests and tools
    def get(self, desc, prop):
        return self.host.get_prop(desc, prop)

    def obj(self, desc):
        return self.host.resolve(desc)

    def run(self, text, where=None):
        """statements as if a script of `where` (default: the current card) ran them"""
        o = self.host.resolve(where) if where else self.default_stack.current
        c = self.ctx.get(id(o)) or ObjInterp(self, o)
        return c.run(text)

    def eval(self, text, where=None):
        o = self.host.resolve(where) if where else self.default_stack.current
        c = self.ctx.get(id(o)) or ObjInterp(self, o)
        return c.eval(text, Frame([]))
