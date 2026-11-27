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

Behaviors (`set the behavior of X to <a button or stack>`, measured 26 Nov): each object on the path is
followed by its behavior, that behavior's behavior and so on. A behavior's script runs in a context of its
own FOR EACH OBJECT using it (own script locals; `me` = that object): ObjInterp(rt, obj, script_of=behavior).
"""
import heapq, os, re, time
from ..pyrt import Runtime
from ..transpile import translate_script
from ..interp import Frame, Thrown, ExitRepeat, NextRepeat, Break
from ..values import XtError
from .model import Harvest
from .host import StackHost
from . import styled

SCRIPT_ERRORS = (XtError, Thrown, ExitRepeat, NextRepeat, Break, RecursionError, ValueError, KeyError, IndexError, TypeError, ZeroDivisionError, OverflowError, OSError, AttributeError)   # a script error never ends the window: it goes to rt.errors (the panel)
OPEN_MESSAGES = ('preOpenStack', 'preOpenCard', 'openStack', 'openCard')   # in this order, all to the card (measured 26 Nov)


# an exported game (tools/export_py.py) fills this: sha1 of a script's text -> {'module': path of its translation,
# 'parse_errors', 'plain', 'natives_verified': [handlers whose native version was checked at export]}
PRECOMPILED = {}


def linux_path(p):
    """a Windows path a harvest recorded (//wsl$/Ubuntu/home/..., C:/...) as this machine's path; '' when unknown"""
    p = str(p or '').replace('\\', '/')
    m = re.match(r'(?i)^//(?:wsl\$|wsl\.localhost)/[^/]+(/.*)$', p)
    if m:
        return m.group(1)
    m = re.match(r'^([A-Za-z]):(/.*)$', p)
    if m:
        return '/mnt/' + m.group(1).lower() + m.group(2)
    return p if p.startswith('/') else ''


def script_body(text):
    """a script-only stack's text without its first line (`script "Name"`)"""
    m = re.match(r'\s*script\s+"[^"\n]*"[^\n]*(\n|$)', text)
    return text[m.end():] if m else text


def _sha(text):
    import hashlib
    return hashlib.sha1(text.encode('utf-8', 'surrogatepass')).hexdigest()


class ObjInterp(Runtime):
    """the script context of one object"""

    def __init__(self, rt, obj, script_of=None):
        super().__init__()
        self.rt, self.obj = rt, obj
        self.script_of = script_of         # a behavior's context: the button / stack whose script this is
        self.G = rt.G
        self.host = rt.host
        self.props = rt.props
        self.plain = []                    # handlers the fast translation left to the plain way (and why)

    def load(self, script):
        """the script, translated to Python (xtalk/fastgen.py) and run as Python; XTALK_INTERP=1 or
        StackRuntime(fast=False): interpreted line by line instead"""
        pre = PRECOMPILED.get(_sha(script)) if PRECOMPILED and self.rt.fast else None
        if self.script_of is not None and self.rt.fast and pre is None:
            return self._load_behavior(script)
        if not self.rt.fast:
            r = super().load(script)
        elif pre is not None:                  # an exported game: this script's translation was made beforehand
            self.load_errors = pre['parse_errors']
            self.plain = pre['plain']
            with open(pre['module'], encoding='utf-8') as f:
                self.install(f.read(), '<%s>' % self.host.name_of(self.obj, 'long'))
            r = None
        else:
            py, rep = translate_script(script, self.host.name_of(self.obj, 'long'), fast=True, byref_fns=self.rt.byref_fns)
            self.load_errors = rep['parse_errors']
            self.plain = rep['plain'] + rep['interpreted']
            self.install(py, '<%s>' % self.host.name_of(self.obj, 'long'))
            r = None
        if self.obj.type == 'stack' and self.script_of is None:   # handlers written in Python for this stack (xtalk/native)
            from .. import native
            self.natives = native.apply(self, self.obj.name, script,
                                        verified=pre.get('natives_verified') if pre is not None else None)
        return r

    def _load_behavior(self, script):
        """a behavior's script, translated once and run once more for each object using it"""
        label = self.host.name_of(self.script_of, 'long')
        key = (script, label)
        t = self.rt.trans_cache.get(key)
        if t is None:
            py, rep = translate_script(script, label, fast=True, byref_fns=self.rt.byref_fns)
            t = self.rt.trans_cache[key] = (py, rep, self.compile_module(py, '<%s>' % label))
        py, rep, code = t
        self.load_errors = rep['parse_errors']
        self.plain = rep['plain'] + rep['interpreted']
        if code is not None:
            import linecache
            linecache.cache['<%s>' % label] = (len(py), None, py.splitlines(True), '<%s>' % label)
        self.install(py, '<%s>' % label, code=code)

    def value_in(self, text, desc):
        """value(expr, object) (Dictionary, not measured): the expression evaluated in that object's script"""
        from ..parser import parse_expr
        o = self.host.resolve(desc)
        c = self.rt.ctx.get(id(o)) or ObjInterp(self.rt, o)
        return c.ev(parse_expr(text), Frame([]))

    @property
    def HN(self):
        return self.rt.handler_names

    def lookup(self, name):
        n = name.lower()
        if self._here is not None and self._here == n:   # deliver(): this context's own handler, not the first on
            self._here = None                            # me's path (a behavior's, while me has one too)
            h = self.handlers.get(n)
            if h is not None:
                return self, h
        for c in self.rt.contexts(self.obj):
            h = c.handlers.get(n)
            if h is not None:
                return c, h
        return None, None

    def after_pass(self, name, args):
        n = name.lower()
        t = self.rt.target                 # pass goes on along the target's path (a card's: card, its
        later = self.rt.engine_contexts(t) if t is not None else []   # background groups, stack)
        if self not in later:
            later = self.rt.contexts(self.obj)
        for c in later[later.index(self) + 1:] if self in later else []:
            if n in c.handlers:
                return c.deliver(name, args)
        self.rt.passed_off = True          # passed past the last handler: the engine does its default
        return ''

    _here = None

    def deliver(self, name, args):
        """a message arriving at this context (from the engine, dispatch, or pass): its own handler runs. A
        handler call by name (invoke) starts at me's own script instead (measured 26 Nov), and so would find
        the object's handler before its behavior's"""
        self._here = name.lower()
        try:
            return self.invoke(name, args)
        finally:
            self._here = None

    def invoke(self, name, args):
        self.rt.running.append(self.obj)
        try:
            return super().invoke(name, args)
        finally:
            self.rt.running.pop()

    def getvar(self, fr, name):
        if len(name) == 2 and name.lower() == 'me' and 'me' not in fr.vars and 'me' not in fr.globals:
            return self.host.long_id(self.obj)
        return super().getvar(fr, name)

    def _me_container(self, e, fr):
        return (e[0] == 'var' and len(e[1]) == 2 and e[1].lower() == 'me' and 'me' not in fr.vars and 'me' not in fr.globals
                and self.obj.type in ('field', 'button'))

    def undefined(self, fr, name):
        if len(name) == 2 and name.lower() == 'me' and self._me_container(('var', name), fr):
            return False
        return super().undefined(fr, name)

    def e_var(self, e, fr):
        """me as a value in a field or button script is its text (measured 25 Nov: line 2 of me)"""
        n = e[1]
        if len(n) == 2 and self._me_container(e, fr):
            return self.host.get_prop(self.host.long_id(self.obj), 'text')
        return self.getvar(fr, n)

    def assign(self, target, value, mode, fr):
        if target[0] == 'var' and self._me_container(target, fr):     # put "XX" into line 1 of me: the field's text changes
            return self.put_obj(self.host.long_id(self.obj), value, 'keep' if mode == 'into' else mode)
        return super().assign(target, value, mode, fr)


class StackRuntime:
    def __init__(self, folder, files_dir=None, real_folders=False, fast=None, real_app=False):
        try:                           # xt3d_... calls, when the raylib package is there (the .venv)
            from .. import xt3d
            xt3d.install()
        except ImportError:
            pass
        self.fast = (os.environ.get('XTALK_INTERP', '') != '1') if fast is None else fast
        self.harvest = Harvest(os.path.expanduser(folder))
        self.default_stack = self.harvest.main
        self.G = {}
        self.props = {'itemdelimiter': ',', 'linedelimiter': '\n', 'numberformat': '0.######', 'casesensitive': 'false'}
        self.host = StackHost(self)
        files = files_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                          'run_files')
        self.host.folders = {'documents': os.path.join(files, 'Documents'), 'temporary': os.path.join(files, 'tmp'),
                             'desktop': os.path.join(files, 'Desktop'), 'home': files, 'resources': self.harvest.folder,
                             'support': os.path.join(files, 'AppData', 'Roaming')}
        self.host.sandbox_root = files     # every write goes in here, whatever the folders are
        self.real_folders = real_folders or real_app
        self.real_app = real_app           # the owner's own window (open_stack, play): writes his real files, shell()
                                           # runs through cmd.exe, the platform is Win32 (owner 26 Nov: real apps)
        if self.real_folders:              # a real window: specialFolderPath and reading use the user's own folders;
            home = self.host.user_home()   # writes too when real_app (checking tools: writes stay sandboxed)
            self.host.folders.update({'home': home, 'documents': os.path.join(home, 'Documents'),
                                      'desktop': os.path.join(home, 'Desktop'), 'pictures': os.path.join(home, 'Pictures'),
                                      'support': os.path.join(home, 'AppData', 'Roaming')})   # C:/Users/<name>/AppData/Roaming
                                   # (measured 27 Nov): GameNotes' and LIB_DATA's data_root.txt, iGame3D XT's settings
        if real_app:
            self.host.platform = 'Win32'   # his stacks then take their Windows paths (shell(): cmd.exe, owner 26 Nov)
            src = linux_path(self.harvest.manifest.get('sourceFile', ''))
            if src and os.path.isfile(src) and self.harvest.main is not None and not getattr(self.harvest.main, 'filename', ''):
                # the stack's own file (its data files sit next to it: Project Map), named as his Windows
                # LiveCode names it (//wsl$/Ubuntu/...): paths built from it work in Explorer and cmd.exe too
                self.harvest.main.filename = str(self.harvest.manifest['sourceFile']).replace('\\', '/')
        self.host.default_folder = self.harvest.folder
        self.ctx = {}
        self.trans_cache = {}          # (behavior script, its label) -> (python, report, compiled): see ObjInterp._load_behavior
        self.load_errors = []
        self.using = []                # library stacks (start using): on every message path, after the stacks
        self.fronts, self.backs = [], []   # insert script of X into front / back: first / last on every path
        self.ctx_cache = {}            # id(object) -> (object, its path's script contexts): see contexts()
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
        self.on_self_launch = None     # the window: start a second copy of this program (args) (Library's Play)
        self.clock = 0.0               # virtual milliseconds
        self.timers, self._seq = [], 0
        self.t0 = time.time()          # real seconds at virtual time 0 (the pendingMessages shows due times)
        self.changed = True
        self.on_wait = None
        self.keys_down = set()         # 'shiftkey', 'optionkey'... while held (the window fills it)
        self.held_codes = []           # the key codes held now (the keysDown; the window fills it)
        self.test_keys = []            # key codes a test holds down (the window adds them to the keysDown)
        self.recent, self.recent_i, self._nav = [], -1, False   # recent cards (up/down arrows go through them)
        self.window_pos = (0, 0)       # the window's place on the screen (globalLoc); the window sets it
        self.on_warp = None            # the window: move the real mouse to a screen point
        self.closed = False            # the window sets this: draw frames while a script waits
        self.closing_sent = False      # closeCard / closeStack went out
        self.opened = set()            # id() of the stacks opened (they got their open messages)
        self.shown_before = []         # the stacks shown before this one (one window: close/hide goes back)
        self.first_stack = self.default_stack     # closing this one ends the window
        self.clipboard = ''            # the clipboard's text; the window keeps it in step with the system's
        self.on_clipboard_get = None   # the window: read the system clipboard
        self.on_clipboard_set = None
        self.handler_names = set()     # every handler name in every script (a call to `trunc` checks it)
        everything = [o for st in self.harvest.stacks for o in [st] + st.children + [c for card in st.children for c in card.flat()]]
        self.byref_fns = set()         # functions with @ parameters anywhere: a call to one is translated the plain way
        for o in everything:
            self.note_byref(o.script)
        for st in self.harvest.stacks:
            for o in [st] + st.children + [c for card in st.children for c in card.flat()]:
                if o.script.strip() and id(o) not in self.ctx:
                    c = ObjInterp(self, o)
                    c.load(script_body(o.script) if o.script.startswith('script ') else o.script)
                    for e in c.load_errors:
                        self.load_errors.append((self.host.name_of(o, 'long'), e))
                    self.ctx[id(o)] = c
        for o in everything:           # a harvested `behavior` (LIB_XTJSON writes `the behavior of X`)
            ref = o.node.get('behavior') if isinstance(o.node, dict) else None
            if ref:
                try:
                    self.set_behavior(o, str(ref))
                except XtError as e:
                    self.load_errors.append((self.host.name_of(o, 'long'), 'behavior %s: %s' % (ref, e)))
        self.names_changed()

    def note_byref(self, script):
        for m in re.finditer(r'^[ \t]*(?:private[ \t]+)?function[ \t]+([^\s(]+)([^\n]*)', script, re.M | re.I):
            if '@' in m.group(2).split('--')[0].split('#')[0]:
                self.byref_fns.add(m.group(1).lower())

    def names_changed(self):
        self.ctx_cache.clear()
        self.handler_names = set()
        for c in self.ctx.values():
            self.handler_names.update(c.handlers)

    def set_script(self, o, text):
        """set the script of o: a fresh script context (its script locals start empty); o as a behavior:
        every object using it starts with empty script locals too (measured 26 Nov)"""
        o.script = text
        o.script_gen = getattr(o, 'script_gen', 0) + 1
        self.note_byref(text)
        self.ctx.pop(id(o), None)
        if text.strip():
            c = ObjInterp(self, o)
            c.load(text)
            self.ctx[id(o)] = c
            self.names_changed()
            return '; '.join(c.load_errors)
        self.names_changed()
        return ''

    # ------------------------------------------------------------ the message path
    @staticmethod
    def backgrounds(card):
        """the card's groups with backgroundBehavior: after the card on the message path; entering / leaving
        them sends the background messages"""
        return [g for g in card.children if g.type == 'group'
                and any(k.lower() == 'backgroundbehavior' and str(v).lower() == 'true' for k, v in g.props.items())]

    # ------------------------------------------------------------ behaviors
    def set_behavior(self, o, ref):
        """set the behavior of o to ref (text: a button's or a stack's long id, any form that names one; empty
        removes it). Measured 26 Nov: a field, a missing object or a loop is an error; the same behavior again
        keeps the script locals, any other change starts them empty"""
        ref = ref.strip() if isinstance(ref, str) else ''
        b = self.host.resolve(ref, must=False) if ref else None
        if ref and b is None:
            m = re.match(r'\s*stack\s+"(.*)"\s*$', ref, re.S)
            if m:
                b = self.host.library(ref)       # a script-only stack file not loaded yet
            else:
                raise XtError('set: no such object %s' % ref)
        if b is not None and b.type not in ('button', 'stack'):
            raise XtError("set: can't set property (a behavior is a button or a stack)")
        x = b
        while x is not None:
            if x is o:
                raise XtError('parentScript: loop in hierarchy')
            x = getattr(x, 'behavior', None)
        if b is getattr(o, 'behavior', None):
            return
        o.behavior = b
        o.bctx = {}
        self.paths_changed()
        self.changed = True

    @staticmethod
    def behavior_text(o):
        """the behavior of o, as LiveCode gives it: `button id N of stack "S"` (no card or group), `stack "S"`"""
        b = getattr(o, 'behavior', None)
        if b is None:
            return ''
        if b.type == 'stack':
            return 'stack "%s"' % b.name
        return '%s id %d of stack "%s"' % (b.type, b.id, b.stack.name)

    def behavior_contexts(self, o):
        """the script contexts of o's behavior, its behavior's behavior...: one of each per object using it"""
        out, b, seen = [], getattr(o, 'behavior', None), set()
        while b is not None and id(b) not in seen:
            seen.add(id(b))
            c = self.behavior_ctx(o, b)
            if c is not None:
                out.append(c)
            b = getattr(b, 'behavior', None)
        return out

    def behavior_ctx(self, o, b):
        text = script_body(b.script) if b.type == 'stack' else b.script
        if not text.strip():
            return None
        d = o.__dict__.setdefault('bctx', {})
        gen = getattr(b, 'script_gen', 0)
        e = d.get(id(b))
        if e is not None and e[0] is b and e[1] == gen:
            return e[2]
        c = ObjInterp(self, o, script_of=b)
        c.load(text)
        d[id(b)] = (b, gen, c)
        return c

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
        out.extend(x for x in self.using if x not in out)                    # then the libraries (start using)
        out.extend(x for x in self.backs if x not in out)                    # then the back scripts
        return out

    def engine_contexts(self, o):
        """where a message from the engine (rawKeyDown, mouseUp...) goes: the front scripts, then o's path
        (Dictionary, not measured: front scripts, object path, libraries, back scripts). Handler calls from
        scripts use contexts() alone."""
        c = self.contexts(o)
        if not self.fronts:
            return c
        f = [self.ctx[id(x)] for x in self.fronts if id(x) in self.ctx]
        return f + [x for x in c if x not in f]

    def insert_script(self, o, where):
        lst = self.fronts if where == 'front' else self.backs
        if o not in lst:
            lst.insert(0, o)          # the newest first (as the frontScripts lists them)
            self.paths_changed()

    def remove_script(self, o, where):
        lst = self.fronts if where == 'front' else self.backs
        if o in lst:
            lst.remove(o)
            self.paths_changed()

    # ------------------------------------------------------------ script-only stacks and libraries
    def script_stack(self, path):
        """a script-only stack file (`script "Name"`, then its script) as a stack in memory; the one already
        loaded when a stack of that name is there"""
        from .model import Stack
        text = open(path, encoding='utf-8', errors='replace').read().lstrip('\ufeff').replace('\r\n', '\n')
        m = re.match(r'\s*script\s+"([^"]*)"', text)
        name = m.group(1) if m else os.path.splitext(os.path.basename(path))[0]
        old = self.harvest.stack(name)
        if old is not None:
            return old
        node = {'type': 'stack', 'name': name, 'id': 1001, 'role': 'sub', 'rect': [0, 0, 400, 400],
                'cards': [{'type': 'card', 'name': '', 'id': 1002, 'number': 1, 'controls': []}]}
        st = Stack(node, os.path.dirname(path), {})
        st.mainstack = st                  # a script-only stack is a main stack of its own
        st.filename = path
        st.script = text
        self.harvest.stacks.append(st)
        self.note_byref(text)
        c = ObjInterp(self, st)
        c.load(script_body(text) if m else text)
        for e in c.load_errors:
            self.load_errors.append((self.host.name_of(st, 'long'), e))
        self.ctx[id(st)] = c
        self.names_changed()
        return st

    def start_using(self, st):
        if st not in self.using:
            self.using.insert(0, st)
            self.paths_changed()           # the newest library first (stacksInUse order)
            self.message(st, 'libraryStack')

    def stop_using(self, st):
        if st in self.using:
            self.message(st, 'releaseStack')
            self.using.remove(st)
            self.paths_changed()

    def forget_stack(self, st):
        """delete stack "X" (a script-only stack loaded here): gone from memory"""
        self.stop_using(st)
        if st in self.harvest.stacks and st is not self.harvest.main:
            self.harvest.stacks.remove(st)
        for x in [st] + st.children + [c for card in st.children for c in card.flat()]:
            self.ctx.pop(id(x), None)
        self.names_changed()

    def contexts(self, o):
        """the script contexts on o's message path (kept until a script, a library or an object changes)"""
        c = self.ctx_cache.get(id(o))
        if c is None or c[0] is not o:
            lst = []
            for x in self.path(o):
                if id(x) in self.ctx:
                    lst.append(self.ctx[id(x)])
                if getattr(x, 'behavior', None) is not None:
                    lst.extend(self.behavior_contexts(x))
            c = self.ctx_cache[id(o)] = (o, lst)
        return c[1]

    def paths_changed(self):
        self.ctx_cache.clear()

    def running_obj(self):
        return self.running[-1] if self.running else None

    def message(self, o, msg, args=()):
        """the engine sends msg to o (mouseUp, openCard...): the first handler on the path runs"""
        self.target = o
        n = msg.lower()
        for c in self.engine_contexts(o):
            if n in c.handlers:
                try:
                    return c.deliver(msg, list(args))
                except SCRIPT_ERRORS as e:
                    self.errors.append((msg, self.host.name_of(o, 'long'), '%s: %s' % (type(e).__name__, e)))
                    return ''
        return None

    def dispatch(self, o, msg, args):
        saved = self.target
        try:
            return self.message(o, msg, args)
        finally:
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

    def tick(self, ms, budget=None):
        """let ms of virtual time pass: due `send ... in` messages run in order.
        budget (real seconds, the window gives one): stop running messages once that much real time went by;
        the rest run next frame, so a game loop that re-sends itself can never starve the window's drawing and keys"""
        end = self.clock + ms
        stop = time.perf_counter() + budget if budget is not None else None
        while self.timers and self.timers[0][0] <= end:
            if stop is not None and time.perf_counter() > stop:
                return                         # the clock stays: what is due runs on the next frame
            t, _, o, text = heapq.heappop(self.timers)
            self.clock = max(self.clock, t)
            self.changed = True                # a script ran: the window draws again (not its idle picture)
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
        if not self._nav:              # a new visit: the recent cards after this point are dropped
            if not self.recent and st.current is not None:
                self.recent = [st.current]
            self.recent = self.recent[:self.recent_i + 1] if self.recent_i >= 0 else self.recent
            self.recent.append(card)
            self.recent_i = len(self.recent) - 1
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
        o = self.control_at(x, y) or self.default_stack.current
        if hasattr(self, 'log_clicks'):
            self.log_clicks.append('%s at %d,%d%s' % (self.host.name_of(o, 'short'), x, y, '' if button == 1 else ' (button %s)' % button))
        if button != 1:                # right / middle: only the message (no selecting, dragging or menu opening)
            self.message(o, 'mouseDown', [str(button)])
            return o
        self.button_down = True
        self.pressed = o
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
                if self.host.obj_prop(o, 'traversalon') != 'false' and self.focused is not o:
                    self.set_focus(None)         # a list field takes the focus (its arrow keys move the hilite)
                    self.focused = o
                    self.message(o, 'focusIn')
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
        if button != 1:                # right / middle: mouseUp (or mouseRelease off the object), nothing else
            self.mouse_move(x, y)
            if self.swallow_up:
                self.swallow_up = False
                return down_on
            o = self.control_at(x, y) or self.default_stack.current
            if down_on is not None and o is not down_on:
                self.message(down_on, 'mouseRelease', [str(button)])
            else:
                self.message(o, 'mouseUp', [str(button)])
            return o
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
        if o.type == 'field' and button == 1 and not self.double:
            link = self.link_at(o, x, y)
            if link is not None:       # a link in a locked field: linkClicked in place of mouseUp (measured 26 Nov)
                self.message(o, 'linkClicked', [link])
                return o
        self.message(o, 'mouseDoubleUp' if self.double else 'mouseUp', [str(button)])
        return o

    def link_at(self, o, x, y):
        """a click on linked text of a locked field: its linkText, else the link's own words; None: no link"""
        if self.host.obj_prop(o, 'locktext') != 'true' or not o.styles:
            return None
        rows = self.field_rows(o)
        r = self.row_at(o, y)
        if not 0 <= r < len(rows):
            return None
        _, a, b = rows[r]
        rel = x - (o.rect[0] + self.field_metrics(o)[2] / 2 + 2)
        if rel < 0 or rel >= self.text_width(o, a, b):
            return None                # beside the text: no link
        p = a                          # the character under the point (not the caret's gap)
        while p + 1 < b and self.text_width(o, a, p + 1) <= rel:
            p += 1
        n = len(o.text)
        if p >= n or o.text[p] == '\n' or p >= len(o.styles):
            return None
        st = o.styles[p] or styled.PLAIN
        if 'link' not in st[0]:
            return None
        a, b = p, p + 1                # the link: the characters around it with the same style
        while a > 0 and o.styles[a - 1] == st:
            a -= 1
        while b < n and b < len(o.styles) and o.styles[b] == st:
            b += 1
        return st[6] or o.text[a:b]

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
            for pk in x.props.keys_for(k):
                v = x.props[pk]
                if v != '':
                    return v
            x = x.parent if x.type != 'card' else x.stack
            if x is not None and x.type == 'stack':
                for pk in x.props.keys_for(k):
                    v = x.props[pk]
                    if v != '':
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

    def field_margins(self, o):
        """left, top, right, bottom: margins is one number for all four, or four items (default 8)"""
        v = [x.strip() for x in str(self.host.obj_prop(o, 'margins') or '8').split(',')]
        try:
            n = [int(float(x)) for x in v]
        except ValueError:
            return 8, 8, 8, 8
        return tuple(n) if len(n) == 4 else (n[0],) * 4

    FREE_LINE = {10: 15, 11: 15, 12: 18, 13: 18, 14: 18, 18: 26, 24: 36}   # Segoe UI, fixedLineHeight false (measured 25 + 26 Nov)

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
        """a menu button's text -> [(label, pick, enabled, depth)], ('-', None, False, depth) for a line;
        a line indented by n tabs is a submenu item n levels down, under the last item one level up
        (picked as "Parent|Child|Grandchild")"""
        out, path = [], []
        for raw in str(text).split('\n'):
            if raw.strip() == '':
                continue
            depth = len(raw) - len(raw.lstrip('\t'))
            depth = min(depth, len(path))          # no deeper than one below the item above
            line = raw.strip('\t')
            if line == '-':
                out.append(('-', None, False, depth))
                continue
            enabled = not line.startswith('(')
            line = line.lstrip('(')
            while line[:2] in ('!c', '!n', '!r', '!u', '!C', '!N', '!R', '!U'):
                line = line[2:]
            line = re.sub(r'(?<!/)/[^/]$', '', line)          # Save/S: the shortcut is not shown
            label = line.replace('//', '/').replace('&&', '\0').replace('&', '').replace('\0', '&')
            path = path[:depth] + [label]
            out.append((label, '|'.join(path), enabled, depth))
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

    def raw_key(self, code):
        """a key went down: rawKeyDown with its code to the focused field (else the card), before keyDown.
        True when a handler took it (did not pass it): LiveCode then sends no keyDown (the View drops the
        character it would type, View.frame)"""
        f = self.focused
        return self.handled(f or self.default_stack.current, 'rawKeyDown', [str(code)])

    def wheel(self, o, amount):
        """the mouse wheel: LiveCode sends rawKeyDown 65309 (up) / 65308 (down) a notch, to the control under
        the mouse (else the card); True when a script took it (Project Map zooms), else a field scrolls"""
        code = '65309' if amount > 0 else '65308'
        took = False
        for _ in range(max(1, min(int(abs(amount) + 0.5), 5))):
            if self.handled(o or self.default_stack.current, 'rawKeyDown', [code]):
                took = True
        return took

    def key(self, ch):
        """a typed character: keyDown to the focused field (else the card); nobody takes it: it is typed"""
        if hasattr(self, 'log_clicks'):
            self.log_clicks.append('key %r' % ch)
        f = self.focused
        if not self.handled(f or self.default_stack.current, 'keyDown', [ch]) and f is not None and self.focused is f \
                and self.editable(f):
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
        if not self.editable(f):                 # a list field: Up/Down move the hilite (after a passed arrowKey)
            if name in ('up', 'down') and self.host.obj_prop(f, 'listbehavior') == 'true':
                n = len(f.text.split('\n'))
                cur = self.host.hilited_lines(f)
                i = (cur[0] if cur else 0) + (1 if name == 'down' else -1)
                if cur or name == 'down':
                    i = max(1, min(n, i))
                    f.props['hilitedLines'] = str(i)
                    self.scroll_to_line(f, i) if hasattr(self, 'scroll_to_line') else None
                    self.changed = True
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
        previous/next card; up/down go back/forward through the recent cards"""
        st = self.default_stack
        if which in ('up', 'down'):
            j = self.recent_i + (-1 if which == 'up' else 1)
            if 0 <= j < len(self.recent):
                self.recent_i = j
                self._nav = True
                try:
                    self.go_card(self.recent[j])
                finally:
                    self._nav = False
            return
        cards = st.children
        if len(cards) < 2:
            return
        i = cards.index(st.current)
        self.go_card(cards[i - 1] if which == 'left' else cards[(i + 1) % len(cards)])

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
