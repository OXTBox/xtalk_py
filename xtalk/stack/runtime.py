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
import heapq, os, re, time
from ..pyrt import Runtime
from ..interp import Frame, Thrown, ExitRepeat, NextRepeat, Break
from ..values import XtError
from .model import Harvest
from .host import StackHost
from . import styled

SCRIPT_ERRORS = (XtError, Thrown, ExitRepeat, NextRepeat, Break, RecursionError, ValueError, KeyError, IndexError, TypeError, ZeroDivisionError, OverflowError, OSError, AttributeError)   # a script error never ends the window: it goes to rt.errors (the panel)
OPEN_MESSAGES = ('preOpenStack', 'preOpenCard', 'openStack', 'openCard')   # in this order, all to the card (measured 26 Nov)


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
        t = self.rt.target                 # pass goes on along the target's path (a card's: card, its
        later = self.rt.contexts(t) if t is not None else []      # background groups, stack)
        if self not in later:
            later = self.rt.contexts(self.obj)
        for c in later[later.index(self) + 1:] if self in later else []:
            if n in c.handlers:
                return c.invoke(name, args)
        self.rt.passed_off = True          # passed past the last handler: the engine does its default
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
        self.templates = {}            # (stack, type) -> the templateGraphic (Button...) object
        self.dialog_answers = []       # no window (tests): replies to answer/ask in order (None = Cancel)
        self.menu_choices = []         # no window (tests): the picks to make, in order (None = close the menu)
        self.menus = []                # every menu shown: (button name, [item labels])
        self.swallow_up = False        # a menu opened while the button was down took the release
        self.started = []              # programs shell() started (.py scripts), for tests to wait on
        self.last_down = None          # (object, clock, x, y) of the last press: a quick second one is a double click
        self.double = False            # this press is the second of a double click
        self.scroll_drag = None        # a field whose scrollbar the mouse is dragging
        self.thumb_drag = None         # a scrollbar / slider whose thumb the mouse is dragging
        self.focused = None            # the field being typed into
        self.sel_drag = None           # a field the mouse is selecting in (button held)
        self.sel = (0, 0)              # its selection: character offsets (start, end); start == end: the caret
        self.field_changed = False     # typed into since it got the focus (closeField, else exitField)
        self.passed_off = False
        self.measure = lambda o, s, st=None: len(s) * 7     # text width (a style run); the window puts in the real font's
        self.measure_key = 'plain'     # which measure the cached rows were made with
        self._rows = {}                # id(field) -> (key, rows): the layout, made again when its key changes
        self.start_programs = True     # False: shell() only notes the script (the survey: no windows pop up)
        self.not_started = []          # the scripts shell() would have started
        self.clock = 0.0               # virtual milliseconds
        self.timers, self._seq = [], 0
        self.t0 = time.time()          # real seconds at virtual time 0 (the pendingMessages shows due times)
        self.changed = True
        self.on_wait = None
        self.keys_down = set()         # 'shiftkey', 'optionkey'... while held (the window fills it)
        self.held_codes = []           # the key codes held now (the keysDown; the window fills it)
        self.closed = False            # the window sets this: draw frames while a script waits
        self.closing_sent = False      # closeCard / closeStack went out
        self.opened = set()            # id() of the stacks opened (they got their open messages)
        self.shown_before = []         # the stacks shown before this one (one window: close/hide goes back)
        self.first_stack = self.default_stack     # closing this one ends the window
        self.clipboard = ''            # the clipboard's text; the window keeps it in step with the system's
        self.on_clipboard_get = None   # the window: read the system clipboard
        self.on_clipboard_set = None
        for st in self.harvest.stacks:
            for o in [st] + st.children + [c for card in st.children for c in card.flat()]:
                if o.script.strip() and id(o) not in self.ctx:
                    c = ObjInterp(self, o)
                    c.load(o.script.split('\n', 1)[1] if o.script.startswith('script ') else o.script)
                    for e in c.load_errors:
                        self.load_errors.append((self.host.name_of(o, 'long'), e))
                    self.ctx[id(o)] = c

    def set_script(self, o, text):
        """set the script of o: a fresh script context (its script locals start empty)"""
        o.script = text
        self.ctx.pop(id(o), None)
        if text.strip():
            c = ObjInterp(self, o)
            c.load(text)
            self.ctx[id(o)] = c
            return '; '.join(c.load_errors)
        return ''

    # ------------------------------------------------------------ the message path
    @staticmethod
    def backgrounds(card):
        """the card's groups with backgroundBehavior: after the card on the message path; entering / leaving
        them sends the background messages"""
        return [g for g in card.children if g.type == 'group'
                and any(k.lower() == 'backgroundbehavior' and str(v).lower() == 'true' for k, v in g.props.items())]

    def path(self, o):
        out = []
        while o is not None:
            out.append(o)
            if o.type == 'card':
                out.extend(g for g in self.backgrounds(o) if g not in out)   # card -> background groups -> stack
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
        """send text to o in ms; returns the message id (`the result` after `send ... in`, measured)"""
        self._seq += 1
        heapq.heappush(self.timers, (self.clock + ms, self._seq, o, text))
        return self._seq

    def cancel(self, mid):
        """cancel <id>: that pending message is dropped (an unknown id: nothing happens)"""
        keep = [t for t in self.timers if str(t[1]) != str(mid).strip()]
        if len(keep) != len(self.timers):
            heapq.heapify(keep)
            self.timers = keep

    def pending_messages(self):
        """one line per pending message, soonest first: id,due time in long seconds,message name,long id of
        the target (measured 25 Nov: the name only, its parameters left out)"""
        out = []
        for due, mid, o, text in sorted(self.timers):
            when = round(self.t0 + due / 1000.0, 3)
            out.append('%d,%s,%s,%s' % (mid, ('%.3f' % when).rstrip('0').rstrip('.'),
                                        (text.split() or [''])[0], self.host.long_id(o)))
        return '\n'.join(out)

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
        """the stack opens: preOpenStack, preOpenCard, openStack, openCard, all to the current card
        (measured 26 Nov: a card's own `on openStack` runs first, then the stack's)"""
        st = self.default_stack
        self.opened.add(id(st))
        self.send_open(st.current)

    def send_open(self, card):
        """a stack opens on card: preOpenStack, [preOpenBackground,] preOpenCard, openStack, [openBackground,]
        openCard, all to the card; the background ones when it has a background group (measured 25 Nov)"""
        bg = bool(self.backgrounds(card))
        for m in OPEN_MESSAGES:
            if bg and m in ('preOpenCard', 'openCard'):
                self.message(card, m.replace('Card', 'Background'))
            self.message(card, m)

    def send_close(self, card):
        """a stack closes on card: closeCard, [closeBackground,] closeStack, all to the card (measured 25 Nov)"""
        self.message(card, 'closeCard')
        if self.backgrounds(card):
            self.message(card, 'closeBackground')
        self.message(card, 'closeStack')

    def close_stack(self):
        """the window closes (or `close stack`): closeCard, then closeStack, both to the card (measured 26 Nov)"""
        if self.closing_sent:
            return
        self.closing_sent = True
        card = self.default_stack.current
        if card is not None:
            self.send_close(card)

    def leave_stack(self, st, closing):
        """close or hide a stack that is not the first: closing sends closeCard, closeStack to its card (as a
        stack closing does, measured 26 Nov) and its next opening sends the open messages again; the window
        then shows the stack shown before it (no messages: going back to an open stack sends none)"""
        if closing and id(st) in self.opened:
            self.opened.discard(id(st))
            if st.current is not None:
                self.send_close(st.current)
        if st is not self.default_stack:
            return
        self.shown_before = [x for x in self.shown_before if x is not st]
        if self.focused is not None and self.focused.stack is st:
            self.set_focus(None)
        self.default_stack = self.shown_before.pop() if self.shown_before else self.first_stack
        self.changed = True

    def go_card(self, card):
        st = card.stack
        if st.current is card and st is self.default_stack:
            return                     # go to the card already shown: no messages (measured 26 Nov)
        if self.focused is not None and self.focused.card is not card:
            self.set_focus(None)
        if st is not self.default_stack:
            self.shown_before.append(self.default_stack)
            self.default_stack = st
            self.changed = True
            if id(st) not in self.opened:  # a stack opened the first time: the four open messages to its card
                self.opened.add(id(st))    # (measured 26 Nov); going back to an open stack sends nothing
                st.current = card
                self.send_open(card)
                return
            if st.current is card:
                return
        old = st.current if st.current is not card else None
        before = {g.id for g in self.backgrounds(old)} if old is not None else set()
        after = {g.id for g in self.backgrounds(card)}
        if old is not None:                # measured 25 Nov: closeCard, closeBackground (a background left),
            self.message(old, 'closeCard')  # preOpenBackground (one entered), preOpenCard, openBackground, openCard;
            if before - after:              # a background on both cards: no background messages
                self.message(old, 'closeBackground')
        st.current = card
        self.default_stack = st
        if after - before:
            self.message(card, 'preOpenBackground')
        self.message(card, 'preOpenCard')
        if after - before:
            self.message(card, 'openBackground')
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
            if self.editable(o):
                if self.focused is not o:
                    self.set_focus(o)
                p = self.char_at(o, x, y)
                if 'shiftkey' in self.keys_down:     # shift-click: the selection grows to here
                    self.sel = (self.sel[0], p)
                else:
                    self.sel = (p, p)
                self.sel_drag = o                    # moving with the button held selects (mouse_move)
            if self.host.obj_prop(o, 'listbehavior') == 'true' and self.host.obj_prop(o, 'disabled') != 'true':
                n = self.field_line_at(o, y)     # the line is hilited before mouseDown (the owner's scripts read it there)
                o.props['hilitedLines'] = str(n) if n else ''
                self.changed = True
        if self.focused is not None and o is not self.focused:
            self.set_focus(None)                 # a click elsewhere: the field loses the focus
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
        self.sel_drag = None
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
        return size, self.line_height(o, size), m, scroll, sbw

    FREE_LINE = {10: 15, 12: 18, 14: 18, 18: 26, 24: 36}   # Segoe UI, fixedLineHeight false (measured 25 Nov)

    def line_height(self, o, size):
        """fixedLineHeight true (a new field): every line is the textHeight, floor(size * 4/3) unless set;
        false: the font's own height (Segoe UI table; other sizes 1.5 x size). Measured 25 Nov. Not done: with
        fixedLineHeight false a line with bigger text is taller (we use one height for the whole field)"""
        if str(self.host.obj_prop(o, 'fixedlineheight')).lower() == 'false':
            return self.FREE_LINE.get(size, int(round(size * 1.5)))
        try:
            th = int(float(self.inherit(o, 'textHeight') or 0))
        except ValueError:
            th = 0
        return th if th > 0 else size * 4 // 3

    # ---- the layout: one rule for drawing, clicks, scrolling and the caret
    def text_width(self, o, a, b):
        """the width of characters a..b of field o, run by run in their own styles"""
        return sum(self.measure(o, o.text[i:j], st) for i, j, st in styled.runs(o.text, o.styles, a, b))

    def field_rows(self, o):
        """field o as drawn: rows (line number, first char, end char); a line wraps at spaces to the field's
        width unless dontWrap is true (a new field wraps: measured). A word too long for a row is cut."""
        size, lh, m, scroll, sbw = self.field_metrics(o)
        wrap = self.host.obj_prop(o, 'dontwrap') != 'true'
        avail = o.width - m - 4 - sbw
        key = (o.text, id(o.styles), avail, size, wrap, self.measure_key)
        c = self._rows.get(id(o))
        if c is not None and c[0] == key:
            return c[1]
        rows, pos = [], 0
        for n, line in enumerate(o.text.split('\n'), 1):
            a, b = pos, pos + len(line)
            if not wrap or avail <= 0 or self.text_width(o, a, b) <= avail:
                rows.append((n, a, b))
            else:
                start, i, used = a, a, 0
                while i < b:
                    j = i
                    while j < b and o.text[j] != ' ':
                        j += 1                                   # the word i..j
                    k = j
                    while k < b and o.text[k] == ' ':
                        k += 1                                   # its spaces j..k (they may hang past the edge)
                    w = self.text_width(o, i, j)
                    if i > start and used + w > avail:           # the word goes to a new row
                        rows.append((n, start, i))
                        start, used = i, 0
                    if w > avail:                                # longer than a row alone: cut it
                        q = i
                        while self.text_width(o, q, j) > avail:
                            r = q + 1
                            while r < j and self.text_width(o, q, r + 1) <= avail:
                                r += 1
                            rows.append((n, q, r))
                            q = r
                        start, used = q, self.text_width(o, q, j)
                    else:
                        used += w
                    used += self.text_width(o, j, k)
                    i = k
                rows.append((n, start, b))
            pos = b + 1
        self._rows[id(o)] = (key, rows)
        return rows

    def row_at(self, o, y):
        """the row index under window y (may be out of range)"""
        size, lh, m, scroll, _ = self.field_metrics(o)
        return int((y - (o.rect[1] + m / 2 - scroll)) // lh)

    def row_of(self, o, p):
        """the row the caret at char p is in (at a wrap, the later row)"""
        rows = self.field_rows(o)
        for i, (n, a, b) in enumerate(rows):
            if a <= p < b or (p == b and (i + 1 == len(rows) or rows[i + 1][0] != n)):
                return i
        return len(rows) - 1

    def field_line_at(self, o, y):
        """the line of field o at window y (0: below the last line); a wrapped line is one line"""
        rows = self.field_rows(o)
        r = self.row_at(o, y)
        return rows[r][0] if 0 <= r < len(rows) else 0

    def in_field_scrollbar(self, o, x, y):
        sbw = self.field_metrics(o)[4]
        return bool(sbw) and x >= o.rect[2] - sbw - 1

    def field_max_scroll(self, o):
        size, lh, m, scroll, sbw = self.field_metrics(o)
        return max(0, int(len(self.field_rows(o)) * lh + m - o.height))

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
        if self.sel_drag is not None and self.button_down and self.focused is self.sel_drag:
            self.sel = (self.sel[0], self.char_at(self.sel_drag, x, y))    # drag-select: from where it went down
            self.changed = True
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

    def handled(self, o, msg, args=()):
        """send msg; True when a handler took it (did not pass it past the last handler)"""
        self.passed_off = False
        found = self.message(o, msg, args)
        return found is not None and not self.passed_off

    def key(self, ch):
        """a typed character: keyDown to the focused field (else the card); nobody takes it: it is typed"""
        if hasattr(self, 'log_clicks'):
            self.log_clicks.append('key %r' % ch)
        f = self.focused
        if not self.handled(f or self.default_stack.current, 'keyDown', [ch]) and f is not None and self.focused is f:
            self.type_into(f, ch)

    SPECIAL = {'backspace': ('backspaceKey', []), 'delete': ('deleteKey', []), 'return': ('returnInField', []),
               'enter': ('enterInField', []), 'left': ('arrowKey', ['left']), 'right': ('arrowKey', ['right']),
               'up': ('arrowKey', ['up']), 'down': ('arrowKey', ['down']), 'tab': ('tabKey', []),
               'home': (None, []), 'end': (None, [])}

    def special_key(self, name):
        """Backspace, Delete, Return, Enter, arrows, Tab: their message, then the field's own action.
        With no field focused: returnKey / enterKey / arrowKey / tabKey to the card; an arrowKey nobody
        takes changes cards (navigationArrows)."""
        if hasattr(self, 'log_clicks'):
            self.log_clicks.append('key %s' % name)
        f = self.focused
        msg, args = self.SPECIAL[name]
        if f is None:
            if msg:
                card = self.default_stack.current
                msg = {'returnInField': 'returnKey', 'enterInField': 'enterKey'}.get(msg, msg)
                if self.handled(card, msg, args) or msg != 'arrowKey':
                    return
                if self.props.get('navigationarrows', 'true') != 'false':
                    self.arrow_card(args[0])
            return
        if msg and self.handled(f, msg, args):
            return
        if self.focused is not f:
            return
        t, (s, e) = f.text, self.sel
        if name == 'backspace':
            if s != e:
                self.type_into(f, '')
            elif s > 0:
                self.sel = (s - 1, s)
                self.type_into(f, '')
        elif name == 'delete':
            if s == e and s < len(t):
                self.sel = (s, s + 1)
            self.type_into(f, '')
        elif name == 'return':
            self.type_into(f, '\n')
        elif name == 'enter':
            self.set_focus(None)
        elif name == 'tab':
            fields = [c for c in self.default_stack.current.flat() if self.editable(c)]
            if fields:
                self.set_focus(fields[(fields.index(f) + 1) % len(fields)] if f in fields else fields[0], select_all=True)
        elif name in ('left', 'right'):
            p = (min(s, e) - (1 if s == e else 0)) if name == 'left' else (max(s, e) + (1 if s == e else 0))
            p = max(0, min(len(t), p))
            self.sel = (p, p)
        elif name in ('up', 'down', 'home', 'end'):     # by rows as drawn (a wrapped line has several)
            rows = self.field_rows(f)
            r = self.row_of(f, s)
            n, a, b = rows[r]
            if name == 'home':
                p = a
            elif name == 'end':
                p = b
            elif (name == 'up' and r == 0) or (name == 'down' and r == len(rows) - 1):
                p = 0 if name == 'up' else len(t)
            else:
                x = f.rect[0] + self.field_metrics(f)[2] / 2 + 2 + self.text_width(f, a, s)
                p = self.char_in_row(f, rows[r - 1 if name == 'up' else r + 1], x)
            self.sel = (p, p)
        self.changed = True

    # ---- the clipboard (the window keeps it in step with the system's; tests use rt.clipboard)
    def get_clipboard(self):
        """the system's clipboard text when the window can read it, else what was copied here
        (WSLg does not always hand the text over)"""
        if self.on_clipboard_get is not None:
            t = self.on_clipboard_get() or ''
            if t:
                self.clipboard = t
        return self.clipboard

    def set_clipboard(self, text):
        self.clipboard = text
        if self.on_clipboard_set is not None:
            self.on_clipboard_set(text)

    def edit_action(self, what):
        """copy / cut / paste / select all on the focused field's selection (Ctrl+C, X, V, A or the commands)"""
        f = self.focused
        if f is None:
            return
        s, e = sorted(self.sel)
        if what in ('copy', 'cut') and s != e:
            self.set_clipboard(f.text[s:e])
            if what == 'cut':
                self.type_into(f, '')
        elif what == 'paste':
            t = self.get_clipboard().replace('\r\n', '\n').replace('\r', '\n')
            if t:
                self.type_into(f, t)
        elif what == 'selectall':
            self.sel = (0, len(f.text))
        self.changed = True

    def control_key(self, ch):
        """a key pressed with Control (Command on a Mac): commandKeyDown to the focused field, else the card
        (Dictionary); nobody takes it: C, X, V, A copy, cut, paste, select all in the field"""
        if hasattr(self, 'log_clicks'):
            self.log_clicks.append('key ctrl+%s' % ch)
        f = self.focused
        if self.handled(f or self.default_stack.current, 'commandKeyDown', [ch]):
            return
        act = {'c': 'copy', 'x': 'cut', 'v': 'paste', 'a': 'selectall'}.get(ch.lower())
        if act and self.focused is f and (act in ('copy', 'selectall') or self.editable(f)):
            self.edit_action(act)

    def arrow_card(self, which):
        """an arrowKey no handler took, no field focused (Dictionary, navigationArrows): left/right go to the
        previous/next card, up/down to the first/last (not measured, Dictionary not checked yet: up/down
        may be back/forth through recent cards)"""
        st = self.default_stack
        cards = st.children
        if len(cards) < 2:
            return
        i = cards.index(st.current)
        to = {'left': cards[i - 1], 'right': cards[(i + 1) % len(cards)], 'up': cards[0], 'down': cards[-1]}[which]
        self.go_card(to)

    def type_into(self, f, text):
        """the engine's own typing: the selection becomes text, the caret after it"""
        s, e = sorted(self.sel)
        self.host.replace_text(f, s, e, text)
        self.sel = (s + len(text), s + len(text))
        self.field_changed = True
        self.changed = True

    def editable(self, o):
        h = self.host.obj_prop
        return (o.type == 'field' and h(o, 'locktext') != 'true' and h(o, 'listbehavior') != 'true'
                and h(o, 'disabled') != 'true' and self._shown(o))

    def set_focus(self, f, select_all=False):
        """focus moves: closeField (text changed) or exitField to the field left, openField to the new one"""
        old = self.focused
        if old is f:
            return
        self.focused = None
        if old is not None:
            self.message(old, 'closeField' if self.field_changed else 'exitField')
        self.field_changed = False
        if f is not None:
            self.focused = f
            self.sel = (0, len(f.text)) if select_all else (len(f.text), len(f.text))
            self.message(f, 'openField')
        self.changed = True

    def char_at(self, o, x, y):
        """the character offset in field o under window point x,y (the caret goes before it)"""
        rows = self.field_rows(o)
        r = max(0, min(self.row_at(o, y), len(rows) - 1))
        return self.char_in_row(o, rows[r], x)

    def char_in_row(self, o, row, x):
        n, a, b = row
        size, lh, m, scroll, sbw = self.field_metrics(o)
        rel = x - (o.rect[0] + m / 2 + 2)
        p = a
        while p < b and self.text_width(o, a, p + 1) - self.text_width(o, p, p + 1) / 2 < rel:
            p += 1
        return p

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
