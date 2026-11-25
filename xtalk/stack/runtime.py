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
import heapq, os
from ..pyrt import Runtime
from ..interp import Frame
from ..values import XtError
from .model import Harvest
from .host import StackHost

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
                except (XtError, RecursionError) as e:
                    self.errors.append((msg, self.host.name_of(o, 'long'), str(e)))
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
            except (XtError, RecursionError) as e:
                self.errors.append((text, self.host.name_of(o, 'long'), str(e)))
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
        o = self.control_at(x, y) or self.default_stack.current
        self.message(o, 'mouseDown', [str(button)])
        return o

    def mouse_up(self, x, y, button=1, down_on=None):
        self.mouse = (x, y)
        o = self.control_at(x, y) or self.default_stack.current
        if down_on is not None and o is not down_on:
            self.message(down_on, 'mouseRelease', [str(button)])
            return o
        if o.type == 'button':
            self._auto_hilite(o)
        self.message(o, 'mouseUp', [str(button)])
        return o

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
        o = self.mouse_down(x, y)
        self.mouse_up(x, y, down_on=o)
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
