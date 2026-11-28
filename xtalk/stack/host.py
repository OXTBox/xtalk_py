"""StackHost: the interpreter's host for real stack objects (the in-memory one is xtalk/host.py).

The interpreter names objects with text (`graphic "Box1" of stack "X"`, `button id 1004 of card id 1002
of stack "X"`, `field 1`); this host finds the object, reads and sets its properties, and runs the
engine's commands (show, hide, send, dispatch, go, answer...). Rules measured in LiveCode are in
docs/LIVECODE_FACTS.md ("Objects and messages").
"""
import math, os, re, subprocess, sys
from ..host import Host
from ..values import XtError, to_num, to_text
from ..parser import tokenize, ORDINALS
from .model import CONTROL_TYPES, to_xtalk, Obj, Props, regular_points
from . import styled

TYPE = {'button': 'button', 'btn': 'button', 'field': 'field', 'fld': 'field', 'graphic': 'graphic',
        'grc': 'graphic', 'image': 'image', 'img': 'image', 'group': 'group', 'grp': 'group',
        'scrollbar': 'scrollbar', 'scrollbars': 'scrollbar', 'player': 'player', 'widget': 'widget',
        'control': 'control', 'card': 'card', 'cd': 'card', 'stack': 'stack', 'background': 'group',
        'bkgnd': 'group', 'bg': 'group', 'buttons': 'button', 'fields': 'field', 'graphics': 'graphic',
        'images': 'image', 'groups': 'group', 'controls': 'control', 'cards': 'card', 'players': 'player'}
EFFECTS = {'outerglow': 'outerGlow', 'innerglow': 'innerGlow', 'dropshadow': 'dropShadow',   # graphic effects:
           'innershadow': 'innerShadow', 'coloroverlay': 'colorOverlay'}       # an array each (docs/SHADERS.md)


def effect_of(o, p):
    """o's effect p (canonical, lower case) as its array (a dict), or None"""
    for k in o.props.keys_for(p):
        v = o.props[k]
        if isinstance(v, dict) and v:
            return v
    return None


GEOMETRY = {'rect', 'rectangle', 'left', 'top', 'right', 'bottom', 'width', 'height', 'loc', 'location',
            'topleft', 'topright', 'bottomleft', 'bottomright'}
SYNONYM = {'backcolor': 'backgroundcolor', 'forecolor': 'foregroundcolor', 'hilitecolor': 'hilitecolor',
           'bordercolor': 'bordercolor', 'hilited': 'hilite', 'vis': 'visible', 'textcolor': 'foregroundcolor'}


_CANON = {}


def canon(p):
    """one name for LiveCode's synonyms (backColor = backgroundColor...); remembered (a frame asks millions of times)"""
    c = _CANON.get(p)
    if c is None:
        q = p.lower()
        c = _CANON[p] = SYNONYM.get(q, q)
    return c


COMMANDS_QUIET = {'lock', 'unlock', 'beep', 'flushevents', 'set'}


def _in_polygon(x, y, pts):
    """even-odd rule"""
    inside = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _near_polyline(x, y, pts, d):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] or pts):
        dx, dy = x2 - x1, y2 - y1
        k = 0 if dx == dy == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        if (x - x1 - k * dx) ** 2 + (y - y1 - k * dy) ** 2 <= d * d:
            return True
    return False


_SCRIPT_PYTHON = []


def windows_env():
    """Windows' own settings (SystemRoot, USERPROFILE...), names in lower case: cmd.exe's `set`, asked once"""
    if not hasattr(windows_env, 'v'):
        windows_env.v = {}
        try:
            r = subprocess.run(['cmd.exe', '/d', '/c', 'set'], cwd='/mnt/c', capture_output=True, timeout=20)
            for line in r.stdout.decode('utf-8', 'replace').splitlines():
                k, eq, v = line.rstrip('\r').partition('=')
                if eq and k:
                    windows_env.v[k.lower()] = v
        except (OSError, subprocess.TimeoutExpired):
            pass
    return windows_env.v


def script_python():
    """the Python that shell() starts scripts with: XTALK_SCRIPT_PYTHON, else this one if it has Tkinter
    (TKInter-izer's programs are Tk windows), else a Windows Python (WSL has none with Tkinter today)"""
    if os.environ.get('XTALK_SCRIPT_PYTHON'):
        return os.environ['XTALK_SCRIPT_PYTHON']
    if not _SCRIPT_PYTHON:
        import glob, importlib.util
        found = sys.executable
        if importlib.util.find_spec('tkinter') is None:
            for pat in ('/mnt/c/Users/*/AppData/Local/python/pythoncore-*/python.exe',
                        '/mnt/c/Users/*/AppData/Local/Programs/Python/Python3*/python.exe',
                        '/mnt/c/Program Files/Python3*/python.exe'):
                hits = sorted(glob.glob(pat))
                if hits:
                    found = hits[-1]
                    break
        _SCRIPT_PYTHON.append(found)
    return _SCRIPT_PYTHON[0]


def ints(text, n):
    parts = [p for p in str(text).split(',')]
    if len(parts) != n:
        raise XtError('set: bad value %r' % text)
    return [int(math.floor(to_num(p) + 0.5)) for p in parts]


class StackHost(Host):
    def __init__(self, rt):
        super().__init__()
        self.rt = rt
        self.real_files = True
        self.folders = {}            # specialFolderPath name (lower) -> folder, set by the runtime
        try:                         # xt3d calls that open files take the script's paths (C:/xt3d/...) as LiveCode
            from .. import xt3d      # does: read where they are, written where this runtime writes (x1-04)
            xt3d.PATHS['read'] = self.real_path
            xt3d.PATHS['write'] = lambda p: self.write_path(self.real_path(p))
            xt3d.CLOSED[0] = False   # a new stack: no script has closed its xt3d window
        except ImportError:          # no raylib in this Python: no xt3d calls either
            pass

    # ------------------------------------------------------------ names
    def stack_ref(self, st):
        """how a long id / long name names a stack: `stack "Name"`; a script-only stack loaded from a file by
        its path, as `the filename` gives it (measured 27 Nov: `stack "C:/.../lidSO.livecodescript"`, its cards
        and controls too). LiveCode does the same for any main stack with a file (a saved stack); here only the
        script-only ones, so the harvest's own stack keeps its name."""
        fn = getattr(st, 'filename', '')
        if fn and st is not self.rt.harvest.main and getattr(st, 'mainstack', None) is st:
            return 'stack "%s"' % fn
        return 'stack "%s"' % st.name

    def long_id(self, o):
        if o.type == 'stack':
            return self.stack_ref(o)
        if o.type == 'card':
            return 'card id %d of %s' % (o.id, self.stack_ref(o.stack))
        out = '%s id %d' % (o.type, o.id)
        p = o.parent
        while p is not None and p.type == 'group':
            out += ' of group id %d' % p.id
            p = p.parent
        return out + ' of card id %d of %s' % (o.card.id if o.card else 0, self.stack_ref(o.stack))

    def name_of(self, o, form=''):
        if form == 'short':
            return o.name if o.name else ('%s id %d' % (o.type, o.id))
        if o.type == 'stack':
            return self.stack_ref(o) if form == 'long' else 'stack "%s"' % o.name
        base = '%s "%s"' % (o.type, o.name) if o.name else '%s id %d' % (o.type, o.id)
        if form == 'long':
            if o.type == 'card':
                return base + ' of %s' % self.stack_ref(o.stack)
            return base + ' of card id %d of %s' % (o.card.id if o.card else 0, self.stack_ref(o.stack))
        return base

    @property
    def current(self):
        """what `this card` / `this stack` name (the interpreter asks for it)"""
        st = self.rt.default_stack
        return {'card': self.long_id(st.current), 'stack': self.long_id(st), 'background': self.long_id(st.current)}

    @current.setter
    def current(self, v):
        pass

    # ------------------------------------------------------------ finding objects
    TEMPLATES = {'templategraphic': 'graphic', 'templatebutton': 'button', 'templatefield': 'field',
                 'templateimage': 'image', 'templatescrollbar': 'scrollbar', 'templategroup': 'group',
                 'templateplayer': 'player', 'templatecard': 'card', 'templatestack': 'stack'}
    TEMPLATE_RECT = [-1, -1, 127, 31]          # measured 25 Nov: width 40 on the template gave 43,-1,83,31

    def template(self, typ):
        """the templateGraphic (Button...): an object whose settings the next create copies"""
        st = self.rt.default_stack
        key = (id(st), typ)
        t = self.rt.templates.get(key)
        if t is None:
            t = Obj(typ, {'type': typ, 'rect': list(self.TEMPLATE_RECT)}, st, None)
            self.rt.templates[key] = t
        return t

    def resolve(self, desc, must=True):
        d = desc.strip()
        if d.lower().replace('the ', '') in self.TEMPLATES:
            return self.template(self.TEMPLATES[d.lower().replace('the ', '')])
        if not d:
            if must:
                raise XtError('no such object')
            return None
        try:
            toks = [t for t in tokenize(d) if t[0] not in ('nl', 'eof')]
        except XtError:
            toks = []
        segs, cur = [], []
        for t in toks:
            if t[0] == 'id' and t[1].lower() == 'of':
                segs.append(cur)
                cur = []
            else:
                cur.append(t)
        segs.append(cur)
        try:
            o = self._walk(list(reversed(segs)))
        except (XtError, IndexError, ValueError):
            o = None
        if o is None and must:
            raise XtError('no such object: %s' % desc)
        return o

    def _walk(self, segs):
        rt = self.rt
        stack, card, group = None, None, None
        target = None
        for seg in segs:
            if not seg:
                return None
            ordinal = None
            if seg[0][0] == 'id' and seg[0][1].lower() in ORDINALS and len(seg) > 1:
                ordinal = seg[0][1].lower()
                seg = seg[1:]
            if seg[0][0] == 'id' and seg[0][1].lower() == 'this':
                seg = seg[1:]
                kind = TYPE.get(seg[0][1].lower())
                st = stack or rt.default_stack
                target = st if kind == 'stack' else st.current
                if kind == 'stack':
                    stack = target
                else:
                    card = target
                continue
            kind = TYPE.get(seg[0][1].lower()) if seg[0][0] == 'id' else None
            if kind is None:
                return None
            rest = seg[1:]
            how, val = None, None
            if ordinal:
                how, val = 'ord', ordinal
            elif rest and rest[0][0] == 'id' and rest[0][1].lower() == 'id':
                how, val = 'id', int(float(rest[1][1]))
            elif rest and rest[0][0] == 'str':
                how, val = 'name', rest[0][1]
            elif rest and rest[0][0] == 'num':
                how, val = 'num', int(float(rest[0][1]))
            elif rest:
                how, val = 'name', ' '.join(t[1] for t in rest)
            else:
                return None
            if kind == 'stack':
                stack = self._find_stack(how, val)
                target = stack
                if stack is None:
                    return None
                continue
            st = stack or (card.stack if card else rt.default_stack)
            if kind == 'card':
                card = self._pick(st.children, how, val)
                target = card
                if card is None:
                    return None
                continue
            pool = (group.flat() if group is not None else (card or st.current).flat())
            if how == 'id':
                o = st.ids.get(val)
                target = o if o is not None and o.type in CONTROL_TYPES and (kind == 'control' or o.type == kind) else None
            else:
                target = self._pick([o for o in pool if kind == 'control' or o.type == kind], how, val)
            if target is None:
                return None
            if target.type == 'group':
                group = target
        return target

    def library(self, desc):
        """the stack of `start using stack X`: one in memory by name, else a script-only stack file"""
        o = self.resolve(desc, must=False)
        if o is not None and o.type == 'stack':
            return o
        m = re.match(r'\s*stack\s+"(.*)"\s*$', desc, re.S)
        path = self.real_path(m.group(1)) if m else ''
        if path and os.path.isfile(path):
            return self.rt.script_stack(path)
        raise XtError("start using: can't find stack %s" % desc)

    def _find_stack(self, how, val):
        if how == 'name':
            if '/' in val.replace('\\', '/'):      # a stack's long id by its file (a script-only stack): no new read
                f = val.replace('\\', '/').lower()
                for s in self.rt.harvest.stacks:
                    if (getattr(s, 'filename', '') or '').replace('\\', '/').lower() == f:
                        return s
            v = val.replace('\\', '/').split('/')[-1]
            for s in self.rt.harvest.stacks:
                if s.name.lower() in (val.lower(), v.lower()) or os.path.basename(s.node.get('file', '')).lower() == v.lower():
                    return s
            if '/' in val.replace('\\', '/'):        # stack "<path of a file>": LiveCode opens the file into memory
                path = self.real_path(val)
                if path and os.path.isfile(path) and path.lower().endswith(('.livecodescript', '.livecode')):
                    return self.rt.script_stack(path)
            return None
        return self._pick(self.rt.harvest.stacks, how, val)

    @staticmethod
    def _pick(objs, how, val):
        if how == 'id':
            return next((o for o in objs if o.id == val), None)
        if how == 'num':
            return objs[val - 1] if 1 <= val <= len(objs) else None
        if how == 'ord':
            if not objs:
                return None
            n = ORDINALS[val]
            if val == 'last':
                return objs[-1]
            if val == 'middle':
                return objs[(len(objs) + 1) // 2 - 1]
            if val == 'any':
                return objs[0]
            return objs[n - 1] if 1 <= n <= len(objs) else None
        v = val.lower()
        return next((o for o in objs if o.name.lower() == v), None)

    def select(self, desc, mode, s, e):
        """select ... of field F: the focus goes there with the caret / selection; select empty: no focus"""
        rt = self.rt
        if desc is None:
            rt.set_focus(None)
            return
        o = self.resolve(desc)
        if o.type != 'field':
            return
        if rt.focused is not o:
            rt.set_focus(o)
        if (s, e) == (0, 0):                   # "text of field": the whole text
            s, e = 0, len(o.text)
        rt.sel = (e, e) if mode == 'after' else (s, s) if mode == 'before' else (s, e)
        rt.changed = True

    def create(self, typ, name, invisible, group):
        """create (measured 25 Nov): a new object with the next id of the stack, on top of the current card
        (or in the group); 128x32 centred on the card unless the template's rect was changed; the template's
        settings copied; no name unless given. A new card is gone to. Returns the long id (into it)."""
        rt = self.rt
        rt.paths_changed()
        rt.fx_version = getattr(rt, 'fx_version', 0) + 1     # the template may carry an effect
        if typ == 'stack':
            return self.create_stack(name, invisible)
        st = rt.default_stack
        new_id = max([st.id] + list(st.ids.keys())) + 1
        t = rt.templates.get((id(st), typ))
        if typ == 'card':
            o = Obj('card', {'type': 'card', 'name': name, 'id': new_id}, st, st)
            o.number = len(st.children) + 1
            st.ids[new_id] = o
            st.children.append(o)
            rt.go_card(o)
            return self.name_of(o, 'long')
        parent = self.resolve(group) if group else st.current
        if parent.type not in ('card', 'group'):
            raise XtError("create: can't create in %s" % self.name_of(parent))
        node = {'type': typ, 'name': name, 'id': new_id, 'layer': len(st.current.flat()) + 1}
        o = Obj(typ, node, st, parent)
        if t is not None:
            o.props = Props(t.props)
            o.custom = dict(t.custom)
            o.text, o.points = t.text, (list(t.points) if t.points else None)
        if t is not None and t.rect != self.TEMPLATE_RECT:
            o.rect = list(t.rect)
        else:
            w, h = st.current.width, st.current.height
            cx, cy = w // 2, h // 2
            o.rect = [cx - 64, cy - 16, cx + 64, cy + 16]
        if invisible:
            o.props['visible'] = 'false'
        st.ids[new_id] = o
        parent.children.append(o)
        rt.changed = True
        return self.name_of(o, 'long')

    def create_stack(self, name, invisible):
        """create [invisible] stack "X" (measured 27 Nov, LIVECODE_FACTS): a main stack of its own with one card
        (no name, id 1002), rect 32,32,288,288, no filename; it is open at once (in the openStacks; a later
        `go stack` sends no open messages) but not shown; the defaultStack does not change. it = stack "X" """
        from .model import Stack
        rt = self.rt
        name = name or 'Untitled 1'
        node = {'type': 'stack', 'name': name, 'id': 1001, 'role': 'main', 'rect': [32, 32, 288, 288],
                'cards': [{'type': 'card', 'name': '', 'id': 1002, 'number': 1, 'controls': []}]}
        st = Stack(node, rt.harvest.folder, rt.harvest.manifest.get('typeDefaults', {}) if isinstance(rt.harvest.manifest, dict) else {})
        st.mainstack = st
        st.filename = ''
        st.props['visible'] = 'false' if invisible else 'true'
        rt.harvest.stacks.append(st)
        rt.opened.add(id(st))
        rt.names_changed()
        return 'stack "%s"' % name

    def delete_obj(self, desc):
        """delete graphic "x": it goes; anything pointing at it lets go"""
        rt = self.rt
        rt.paths_changed()
        o = self.resolve(desc)
        if o.type == 'stack' and getattr(o, 'filename', None) and o is not rt.harvest.main:
            rt.forget_stack(o)                 # a script-only stack loaded from its file
            return
        if o.type == 'stack':
            raise XtError("delete: can't delete a stack here")
        holder = o.stack if o.type == 'card' else o.parent
        if holder is None or o not in holder.children:
            raise XtError("delete: can't delete that")
        if o.type == 'card' and len(holder.children) == 1:
            raise XtError("delete: can't delete the last card")
        holder.children.remove(o)
        gone = {id(x) for x in [o] + o.flat()}
        for x in [o] + o.flat():
            o.stack.ids.pop(x.id, None)
            rt.ctx.pop(id(x), None)
        if rt.focused is not None and id(rt.focused) in gone:
            rt.focused = None
        for attr in ('hover', 'pressed', 'thumb_drag', 'scroll_drag', 'sel_drag'):
            if getattr(rt, attr, None) is not None and id(getattr(rt, attr)) in gone:
                setattr(rt, attr, None)
        if rt.grabbed is not None and id(rt.grabbed[0]) in gone:
            rt.grabbed = None                   # a grab ends, no message (Dictionary, grab)
        if o.type == 'card' and o.stack.current is o:
            rt.go_card(o.stack.children[0])
        rt.changed = True

    def dialog(self, kind, sub, icon, prompt, extra, title):
        """answer / ask: the window shows it (rt.on_dialog); with no window, rt.dialog_answers gives the
        replies in order (None = Cancel); with none left, answer takes its default button, ask its default text"""
        rt = self.rt
        rt.answers.append(('%s %s' % (kind, sub)).strip() + ': ' + prompt)
        if rt.on_dialog is not None:
            return rt.on_dialog(kind, sub, icon, prompt, extra, title)
        if rt.dialog_answers:
            v = rt.dialog_answers.pop(0)
            if v is None:
                return '', ('' if kind == 'answer' and not sub else 'cancel')
            if sub in ('file', 'files', 'folder', 'folders') and not rt.real_folders:
                v = self.sandboxed(v if v.startswith('/') else os.path.join(self.folders['documents'], v))
            return v, ''
        return super().dialog(kind, sub, icon, prompt, extra, title)

    def shell(self, command):
        """shell(): a .py file inside the stack's files folder starts with Python, as its own program, and the
        stack goes on (LiveCode's shell waits; TKInter-izer's scripts, 25 Nov). Any other command: in a real
        window it runs through Windows cmd.exe (owner 26 Nov, windows_shell); in tests and surveys it is refused.
        Which Python: XTALK_SCRIPT_PYTHON if set (one with Tkinter, say), else the one running this."""
        path = command.strip().strip('"').replace('\\', '/')
        full = self.sandboxed(path)
        m = self.SELF_START.match(str(command))
        if m and self.own_file(m.group(1)):        # start "" "<this program>" -game "<folder>": a second copy
            return self.self_launch([x or y for x, y in re.findall(r'"([^"]*)"|(\S+)', m.group(2))])
        if not path.lower().endswith('.py') or full != os.path.abspath(path) or not os.path.isfile(full):
            if getattr(self.rt, 'real_app', False) and self.rt.start_programs:
                return self.windows_shell(command)
            raise XtError('shell: only a .py file in the stack\'s files folder is started (owner, 25 Nov): %s' % command)
        if not self.rt.start_programs:
            self.rt.not_started.append(full)
            return ''
        python = script_python()
        target = full
        if python.lower().endswith('.exe'):          # Windows Python: it wants a Windows path
            target = subprocess.run(['wslpath', '-w', full], capture_output=True, text=True).stdout.strip() or full
        log = open(os.path.splitext(full)[0] + '.log', 'w', encoding='utf-8')
        p = subprocess.Popen([python, target], cwd=os.path.dirname(full), stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        self.rt.started.append(p)
        return ''

    def windows_shell(self, command):
        """shell() in a real window (owner, 26 Nov: "fully functional file system interaction"): the command
        runs the way LiveCode runs it on Windows, through cmd.exe /c, and its output comes back (it waits;
        `start ...` returns at once). From WSL: cmd.exe starts in C:\\ (a Linux folder would make it complain)."""
        # %NAME% filled in here, as cmd.exe /c would (the command reaches cmd.exe inside a variable, and cmd
        # fills in a variable once: %SystemRoot% in LIB_MENU's Explorer recipe stayed as it was, owner 26 Nov)
        env = windows_env()
        command = re.sub(r'%([^%\s]+)%', lambda m: env.get(m.group(1).lower(), m.group(0)), str(command))
        print('shell (cmd.exe):', command, flush=True)    # the window's log says what went to Windows
        try:
            # handed over in a variable: as an argument, WSL turns each " into \" and eats a backslash of \\wsl$
            env = dict(os.environ, XT_CMD=str(command),
                       WSLENV=(os.environ.get('WSLENV', '') + ':XT_CMD').strip(':'))
            r = subprocess.run(['cmd.exe', '/d', '/c', '%XT_CMD%'], cwd='/mnt/c', stdin=subprocess.DEVNULL,
                               capture_output=True, timeout=120, env=env)
        except (OSError, subprocess.TimeoutExpired) as e:
            return str(e)
        out = (r.stdout + r.stderr).decode('utf-8', 'replace').replace('\r\n', '\n')
        return out

    def within(self, desc, point):
        """within(object, point) (Dictionary): a graphic's inside counts only when it is filled;
        unfilled, only its outline (2 px either side: not measured). Images, tabbed buttons: the rect."""
        o = self.resolve(desc)
        x, y = ints(point, 2)
        l, t, r, b = o.rect
        if o.type != 'graphic':
            return 'true' if l <= x < r and t <= y < b else 'false'
        style = self.obj_prop(o, 'style')
        filled = self.obj_prop(o, 'filled') == 'true'
        pts = [q for q in (o.points or []) if q is not None]
        if style == 'regular':
            pts = self.regular(o)
        if style in ('polygon', 'curve', 'line', 'freehand', 'regular') and pts:
            if filled and len(pts) > 2 and _in_polygon(x, y, pts):
                return 'true'
            return 'true' if _near_polyline(x, y, pts, 2) else 'false'
        if style == 'oval':
            rx, ry = (r - l) / 2, (b - t) / 2
            if rx <= 0 or ry <= 0:
                return 'false'
            d = ((x + 0.5 - (l + rx)) / rx) ** 2 + ((y + 0.5 - (t + ry)) / ry) ** 2
            if filled:
                return 'true' if d <= 1 else 'false'
            inner = ((x + 0.5 - (l + rx)) / max(rx - 2, 0.5)) ** 2 + ((y + 0.5 - (t + ry)) / max(ry - 2, 0.5)) ** 2
            return 'true' if d <= 1 and inner >= 1 else 'false'
        inside = l <= x < r and t <= y < b
        if filled or not inside:
            return 'true' if inside else 'false'
        return 'true' if min(x - l, r - 1 - x, y - t, b - 1 - y) < 2 else 'false'

    def regular(self, o):
        """the corners of a regular graphic, turned by its angle"""
        try:
            n, a = to_num(self.obj_prop(o, 'polysides') or 4), to_num(self.obj_prop(o, 'angle') or 0)
        except XtError:
            n, a = 4, 0
        return regular_points(o.rect, n, a)

    def exists(self, desc):
        m = re.match(r'\s*(file|folder|directory)\s+"(.*)"\s*$', desc, re.S | re.I)
        if m:                                  # there is a file "x" / a folder "x": looked at, never changed
            path = self.real_path(m.group(2))
            if not os.path.isabs(path):
                path = os.path.join(self.default_folder, path)
            return os.path.isfile(path) if m.group(1).lower() == 'file' else os.path.isdir(path)
        return self.resolve(desc, must=False) is not None

    def count(self, kind, parent):
        k = TYPE.get(kind.lower(), kind.rstrip('s'))
        if k == 'card':
            st = self.resolve(parent) if parent else self.rt.default_stack
            return len(st.children)
        where = self.resolve(parent) if parent else self.rt.default_stack.current
        if where.type == 'stack':
            where = where.current
        return sum(1 for o in where.flat() if k == 'control' or o.type == k)

    # ------------------------------------------------------------ properties
    def get_prop(self, desc, prop, key=None):
        p = prop.lower()
        if not desc:
            return self.global_prop(p)
        o = self.resolve(desc)
        if key is not None and p in EFFECTS:   # the outerGlow["size"] of X: the harvested glow's own value
            d = effect_of(o, p) or {}
            return to_text(next((v for k, v in d.items() if k.lower() == key.lower()), ''))
        if key is not None:
            s = next((v for k, v in o.sets.items() if k.lower() == p), None)
            if isinstance(s, dict):
                return next((v for k, v in s.items() if k.lower() == key.lower()), '')
            arr = next((v for k, v in o.custom.items() if k.lower() == p), None)
            return arr.get(key, '') if isinstance(arr, dict) else ''
        if p in ('imagedata', 'alphadata') and o.type == 'image' and getattr(o, p, None) is not None:
            return getattr(o, p)
        if p in ('filename', 'effective filename') and o.type == 'stack':
            st = o if p == 'filename' else o.mainstack or o
            return getattr(st, 'filename', '')
        r = self.obj_prop(o, p)
        return r

    def mouse_button(self, n):
        """mouse(n): 1 left, 2 middle, 3 right -> down / up (the window sets rt.buttons_down)"""
        n = str(n).strip()
        if n in ('', '1'):
            return 'down' if self.rt.button_down else 'up'
        return 'down' if n in getattr(self.rt, 'buttons_down', ()) else 'up'

    def global_prop(self, p):
        rt = self.rt
        if p in self.TEMPLATES:            # the templateGraphic: names itself, resolve() finds it
            return p
        if p == 'focusedobject':
            return self.name_of(rt.focused, 'long') if rt.focused is not None else ''
        if p in ('selection', 'selectedtext'):
            if rt.focused is None:
                return ''
            s, e = sorted(rt.sel)
            return rt.focused.text[s:e]
        if p == 'target':
            return self.name_of(rt.target) if rt.target is not None else ''
        if p == 'topstack':                    # stack "Name" (measured 25 Nov)
            return 'stack "%s"' % rt.default_stack.name
        if p == 'defaultstack':                # stack "Name" (measured 25 Nov, twice: the short name of it is the
            return 'stack "%s"' % rt.default_stack.name    # name; the short name of a bare name is an error)
        if p == 'mouseloc':
            return '%d,%d' % rt.mouse
        if p in ('mouseh', 'mousev'):
            return str(rt.mouse[0 if p == 'mouseh' else 1])
        if p == 'mouse':                   # the mouse / mouse(1): up or down
            return 'down' if rt.button_down else 'up'
        if p in ('screenpixelscale', 'screenpixelscales'):   # WSLg draws our window unscaled: one unit, one pixel
            return '1'
        if p == 'screenrect':
            return '0,0,1536,864'
        if p == 'screenloc':                   # the middle of the screenRect (the xt3d bench centres itself, x1-04)
            return '768,432'
        if p == 'environment':                 # we run stacks the way a standalone does
            return 'standalone application'
        if p == 'loadedextensions':            # xt3d (the raylib bridge) when its Python twin is installed
            from ..interp import EXTERNALS
            return 'org.xtalk.xtbridge' if 'xt3d_version' in EXTERNALS else ''
        if p in ('frontscripts', 'backscripts'):
            return '\n'.join(self.long_id(o) for o in (rt.fronts if p == 'frontscripts' else rt.backs))
        if p == 'stacksinuse':
            return '\n'.join(st.name for st in rt.using)
        if p == 'mainstacks':
            return '\n'.join([rt.harvest.main.name] + [x.name for x in rt.harvest.stacks if x is not rt.harvest.main
                                                         and getattr(x, 'mainstack', None) is x and id(x) in rt.opened])
        if p == 'openstacks':                  # the shown stack first, then the other open ones
            shown = [rt.default_stack] + [x for x in reversed(rt.shown_before) if x is not rt.default_stack]
            rest = [x for x in rt.harvest.stacks if id(x) in rt.opened and x not in shown]
            return '\n'.join(x.name for x in shown + rest if id(x) in rt.opened or x is rt.default_stack)
        if p == 'clipboard':                   # what is on it: text, or empty (measured 26 Nov)
            return 'text' if rt.get_clipboard() != '' else 'empty'
        if p == 'navigationarrows':
            return rt.props.get('navigationarrows', 'true')
        if p == 'tool':
            return getattr(rt, 'tool', 'browse tool')
        if p == 'defaultfolder':
            return rt.host.default_folder
        if p in ('files', 'folders'):
            return self.list_dir(p)
        if p == 'keysdown':
            return ','.join(str(c) for c in rt.held_codes)
        if p == 'pendingmessages':
            return rt.pending_messages()
        if p in ('optionkey', 'shiftkey', 'commandkey', 'controlkey', 'altkey', 'capslockkey'):
            return 'down' if p in rt.keys_down else 'up'
        return ''

    def on_global_prop(self, name, v):
        """set the screenMouseLoc: the window moves the real mouse there (a game keeps it inside)"""
        rt = self.rt
        if name == 'defaultstack':            # read back as stack "Name" whatever form it was set with (measured:
            v = str(v)                        # the getter gives stack "X"); a name we don't know stays as given
            nm = v[7:-1] if v.startswith('stack "') and v.endswith('"') else v
            st = rt.harvest.stack(nm)
            if st is not None:
                rt.props['defaultstack'] = 'stack "%s"' % st.name
            return
        if name == 'defaultfolder':           # set the defaultFolder: where files() / folders() look
            p = self.real_path(v)
            if os.path.isdir(p):
                self.default_folder = p
                return
            return "can't open directory"     # measured 27 Nov (the folder stays as it was)
        if name == 'screenmouseloc' and rt.on_warp is not None:
            try:
                x, y = (int(round(to_num(p))) for p in str(v).split(',')[:2])
            except (XtError, ValueError):
                return
            rt.on_warp(x, y)

    def get_global_key(self, p, key):
        """the clipboardData["text"] (text only here; unicode the same; styles/rtf/html: empty)"""
        if p.lower() == 'clipboarddata' and key.lower() in ('text', 'unicode'):
            return self.rt.get_clipboard()
        return ''

    def set_global_key(self, p, key, v):
        if p.lower() == 'clipboarddata' and key.lower() in ('text', 'unicode'):
            self.rt.set_clipboard(v)

    def hilited_lines(self, o):
        v = o.props.get('hilitedLines', '')
        if isinstance(v, (list, tuple)):
            return [int(x) for x in v]
        return [int(x) for x in str(v).split(',') if x.strip().isdigit()]

    def field_formatted(self, o, p):
        """the formattedHeight / formattedWidth of a field. Measured 26 Nov (Segoe UI): height = rows x line
        height - 8 + top margin + bottom margin (sizes 11-14, 1-4 lines, margins 0/4/12/"4,6,8,10"); width = the
        widest row + left + right margins"""
        rt = self.rt
        ml, mt, mr, mb = rt.field_margins(o)
        rows = rt.field_rows(o)
        if p == 'formattedheight':
            size = rt.field_metrics(o)[0]
            return str(max(0, len(rows) * rt.line_height(o, size) - 8 + mt + mb))
        return str(int(round(max((rt.text_width(o, a, b) for _, a, b in rows), default=0))) + ml + mr)

    def obj_prop(self, o, p):
        if p in ('behavior', 'parentscript'):
            return self.rt.behavior_text(o)
        r = o.rect
        if p in ('hilitedline', 'hilitedlines'):
            return ','.join(str(n) for n in self.hilited_lines(o))
        if p == 'selectedline':        # line 3 of field 2 (word 2 = the line)
            hl = self.hilited_lines(o)
            if not hl:
                return ''
            n = next((i for i, c in enumerate([c for c in o.card.flat() if c.type == 'field'], 1) if c is o), 0)
            return 'line %d of field %d' % (hl[0], n) if len(hl) == 1 else 'line %d to %d of field %d' % (hl[0], hl[-1], n)
        if p == 'selectedtext' and self.rt.focused is o and self.obj_prop(o, 'listbehavior') != 'true':
            s, e = sorted(self.rt.sel)
            return o.text[s:e]
        if p == 'selectedtext':
            lines = o.text.split('\n')
            return '\n'.join(lines[n - 1] for n in self.hilited_lines(o) if 0 < n <= len(lines))
        if p in ('rect', 'rectangle'):
            return '%d,%d,%d,%d' % tuple(r)
        if p == 'left':
            return str(r[0])
        if p == 'top':
            return str(r[1])
        if p == 'right':
            return str(r[2])
        if p == 'bottom':
            return str(r[3])
        if p == 'width':
            return str(o.width)
        if p == 'height':
            return str(o.height)
        if p in ('loc', 'location'):
            return '%d,%d' % o.loc
        if p == 'topleft':
            return '%d,%d' % (r[0], r[1])
        if p == 'bottomright':
            return '%d,%d' % (r[2], r[3])
        if p == 'topright':
            return '%d,%d' % (r[2], r[1])
        if p == 'bottomleft':
            return '%d,%d' % (r[0], r[3])
        if p == 'name':
            return self.name_of(o)
        if p in ('short name', 'abbreviated name', 'abbrev name'):
            return self.name_of(o, 'short')
        if p == 'long name':
            return self.name_of(o, 'long')
        if p in ('id', 'short id', 'abbreviated id', 'abbrev id'):
            return str(o.id)
        if p == 'long id':
            return self.long_id(o)
        if p == 'number':
            if o.type == 'card':
                return str(o.stack.children.index(o) + 1)
            return str(o.layer)
        if p == 'layer':
            return str(o.layer)
        if p in ('text', 'menuitems'):
            return o.text
        if p == 'htmltext':
            return styled.to_html(o.text, o.styles)
        if p in ('formattedheight', 'formattedwidth') and o.type == 'field':
            return self.field_formatted(o, p)
        if p == 'owner':
            return self.name_of(o.parent) if o.parent is not None else ''
        if p == 'script':
            return o.script
        if p == 'mainstack':
            return o.stack.mainstack.name
        if p in ('points', 'relativepoints'):
            if o.points is None:
                return ''
            dx, dy = (o.rect[0], o.rect[1]) if p == 'relativepoints' else (0, 0)
            return '\n'.join('' if q is None else '%d,%d' % (q[0] - dx, q[1] - dy) for q in o.points)
        if p == 'customkeys':                  # the keys of the active property set (measured 25 Nov)
            return '\n'.join(self.custom_of(o))
        if p == 'custompropertyset':
            return getattr(o, 'cps', '')
        if p == 'custompropertysets':
            return '\n'.join(o.sets)
        cp = canon(p)
        for k in o.props.keys_for(cp):
            v = o.props[k]
            return to_xtalk(v) if not isinstance(v, str) else v
        k, v = o.stack.default(o.type, p if p != 'hilite' else 'hilited')
        if k is not None:
            return to_xtalk(v) if not isinstance(v, str) else v
        for k, v in self.custom_of(o).items():
            if k.lower() == p:
                return v
        return ''

    def custom_of(self, o, create=False):
        """the custom properties a plain read or write uses: the active customPropertySet, else the object's own"""
        cps = getattr(o, 'cps', '')
        if not cps:
            return o.custom
        k = next((k for k in o.sets if k.lower() == cps.lower()), None)
        if k is None or not isinstance(o.sets[k], dict):
            if not create:
                return {}
            k = cps
            o.sets[k] = {}
        return o.sets[k]

    def set_prop(self, desc, prop, value, key=None):
        r = self._set_prop(desc, prop, value, key)
        p = prop.lower()
        if desc and key is None and p in ('text', 'menuhistory'):
            o = self.resolve(desc)             # an option menu shows its chosen line as its label (measured 27 Nov:
            if o.type == 'button' and str(self.obj_prop(o, 'menumode')).lower() == 'option':   # set the text =
                lines = (o.text or '').split('\n')    # line 1 and menuHistory 1; set the menuHistory to 2 = line 2)
                if p == 'text':
                    o.props['menuHistory'] = '1'
                try:
                    n = int(float(o.props.get('menuHistory', '1') or 1))
                except ValueError:
                    n = 1
                if 1 <= n <= len(lines):
                    o.props['label'] = lines[n - 1]
        return r

    def _set_prop(self, desc, prop, value, key=None):
        p = prop.lower()
        if not desc:
            return
        o = self.resolve(desc)
        self.rt.changed = True
        if p in EFFECTS:
            self.set_effect(o, p, value, key)
            return
        if key is not None:
            s = next((k for k in o.sets if k.lower() == p), None)
            if s is not None and isinstance(o.sets[s], dict):
                o.sets[s][key] = value
                return
            s = next((k for k in o.custom if k.lower() == p), prop)
            arr = o.custom.get(s)
            if not isinstance(arr, dict):
                arr = {}
                o.custom[s] = arr
            arr[key] = value
            return
        if p == 'custompropertyset':
            o.cps = str(value)
            return
        if p in ('imagedata', 'alphadata') and o.type == 'image':
            # the picture's pixels as text (4 bytes a pixel: unused, r, g, b; rows from the top); the window
            # makes a texture of it when it draws (an xt3d frame each tick: xt3d_RenderTextureImageData)
            setattr(o, p, value if isinstance(value, str) else str(value))
            return
        if p == 'script':
            return self.rt.set_script(o, str(value))   # its compile errors: the result (empty when it compiles)
        if p in ('behavior', 'parentscript'):
            self.rt.set_behavior(o, value if isinstance(value, str) else to_text(value))
            return
        if p in ('backgroundbehavior', 'sharedbehavior'):
            self.rt.paths_changed()
            o.props['backgroundBehavior' if p == 'backgroundbehavior' else 'sharedBehavior'] = str(value).lower()
            return
        if p == 'style':                       # set the style to "Line": stored as line (measured 25 Nov)
            value = str(value).lower()
        if p == 'angle':                       # 390 reads back 30, -30 reads 330 (measured 26 Nov)
            a = to_num(value) % 360
            value = str(int(a)) if a == int(a) else str(a)
            if o.type == 'image':
                self.turn_image(o, a)          # before the angle is stored: it reads the old one
            o.custom.pop(next((k for k in o.custom if k.lower() == 'angle'), None), None)
            o.props[next((k for k in o.props if k.lower() == 'angle'), 'angle')] = value
            return
        if p in ('hilitedline', 'hilitedlines'):
            o.props['hilitedLines'] = ','.join(x.strip() for x in str(value).split(',') if x.strip().isdigit())
            return
        if p in GEOMETRY:
            old = list(o.rect)
            self.set_geometry(o, p, value)
            self.move_points(o, old)
            if o.type == 'image' and not to_num(o.props.get('angle', 0) or 0) % 360:
                o.unturned = None              # moved/resized while not turned: the next turn starts from here
            elif o.type == 'image' and getattr(o, 'unturned', None):
                self.move_turned(o, old)
            elif o.type == 'stack':            # a new size: resizeStack new w,h,old w,h to its card, at once
                self.stack_resized(o, old)     # (measured 27 Nov: width/height/rect, not loc; docs/WINDOW_RULES.md)
            return
        if p in ('points', 'relativepoints'):
            self.set_points(o, value, p == 'relativepoints')
            return
        if p == 'layer' and o.type not in ('card', 'stack') and o.parent is not None:
            self.set_layer(o, value)
            return
        if p == 'name':
            o.name = value
            return
        if p in ('text', 'menuitems'):
            o.text = value
            o.styles = None                    # put into a field: its styles go (measured 26 Nov)
            return
        if p == 'htmltext':
            o.text, o.styles = styled.from_html(value)
            return
        cp = canon(p)
        for k in o.props.keys_for(cp):
            o.props[k] = value
            return
        p = cp                                 # textColor / foreColor / backColor: stored as the real property
        if p in ('hilite', 'hilited'):
            p = 'hilited'
        if p == 'vis':
            p = 'visible'
        k, _ = o.stack.default(o.type, p)
        if k is not None or p in ('label', 'visible', 'hilited', 'backgroundcolor', 'foregroundcolor', 'textsize',
                                  'textfont', 'textstyle', 'bordercolor', 'blendlevel', 'icon', 'style'):
            o.props[k or {'backgroundcolor': 'backgroundColor', 'foregroundcolor': 'foregroundColor',
                          'hilited': 'hilited', 'textsize': 'textSize', 'textfont': 'textFont',
                          'textstyle': 'textStyle', 'bordercolor': 'borderColor',
                          'blendlevel': 'blendLevel'}.get(p, prop)] = value
            return
        d = self.custom_of(o, create=True)
        ck = next((k for k in d if k.lower() == p), prop)
        d[ck] = value

    # ------------------------------------------------------------ styled text (styled.py)
    def put_text(self, desc, v, mode):
        """put after / before a field, or a chunk put ('keep': v is the new whole text): the styles of the
        text that did not change stay; new text takes the style before it (measured 26 Nov)"""
        o = self.resolve(desc)
        old = o.text
        if mode == 'sort':
            last = getattr(self, 'last_sort', None)
            if last and last[0] == old and o.styles is not None:
                _, spans, order, d = last
                st = []
                for n, i in enumerate(order):
                    if n:
                        st += [o.styles[spans[i][0] - 1] if spans[i][0] else styled.PLAIN] * len(d)
                    st += o.styles[spans[i][0]:spans[i][1]]
                o.text, o.styles = v, st
                self.rt.changed = True
                return
            mode = 'keep'
        if mode == 'after':
            s, e, new = len(old), len(old), v
        elif mode == 'before':
            s, e, new = 0, 0, v
        else:                                  # the changed middle: what is left after the common ends
            s = 0
            while s < len(old) and s < len(v) and old[s] == v[s]:
                s += 1
            k = 0
            while k < len(old) - s and k < len(v) - s and old[-1 - k] == v[-1 - k]:
                k += 1
            e, new = len(old) - k, v[s:len(v) - k]
        self.replace_text(o, s, e, new)

    def replace_text(self, o, s, e, new):
        o.styles = styled.replace(o.styles, s, e, len(new))
        o.text = o.text[:s] + new + o.text[e:]
        self.rt.changed = True

    def set_chunk_prop(self, desc, s, e, prop, value):
        o = self.resolve(desc)
        p = prop.lower()
        if p in ('text', 'htmltext'):
            if p == 'htmltext':
                t, st = styled.from_html(value)
                self.replace_text(o, s, e, t)
                if st is not None or o.styles is not None:
                    o.styles = (o.styles or [styled.PLAIN] * len(o.text))
                    o.styles[s:s + len(t)] = st or [styled.PLAIN] * len(t)
            else:
                self.replace_text(o, s, e, value)
            return
        if p in styled.SLOT:
            o.styles = styled.set_range(o.styles, len(o.text), s, e, p, value)
            self.rt.changed = True
            return
        raise XtError("set: can't set %s of a chunk" % prop)     # only style names come here (interp.CHUNK_PROPS)

    def get_chunk_prop(self, desc, s, e, prop):
        o = self.resolve(desc)
        p = prop.lower()
        if p == 'text':
            return o.text[s:e]
        if p == 'htmltext':
            return styled.to_html(o.text[s:e], o.styles[s:e] if o.styles else None)
        eff = p.startswith('effective ')
        q = p[len('effective '):] if eff else p
        if q in styled.SLOT:
            v = styled.get_range(o.styles, o.text, s, e, q)
            if v == '' and eff:                # the effective textFont of word 2: the field's
                v = self.rt.inherit(o, q) or ''
                v = to_xtalk(v) if not isinstance(v, str) else v
            return v
        return self.obj_prop(o, p)

    def set_layer(self, o, value):
        """set the layer to top / bottom / N (measured 26 Nov: N past the top = top; the others close up).
        A control in a group moves among the group's controls only."""
        self.rt.paths_changed()                # a group moved among the card's groups: background order
        sib = o.parent.children
        flat = o.card.flat() if o.card is not None else sib
        v = str(value).strip().lower()
        sib.remove(o)
        if v == 'top':
            i = len(sib)
        elif v == 'bottom':
            i = 0
        else:
            n = ints(v, 1)[0]
            first = next((k for k, c in enumerate(flat, 1) if c.parent is o.parent), 1)
            i = max(0, min(len(sib), n - first))
        sib.insert(i, o)
        for k, c in enumerate(o.card.flat() if o.card is not None else sib, 1):
            c.layer = k
        self.rt.changed = True

    def move_turned(self, o, old):
        """a turned image moved (loc, left, rect...): its picture goes along; a new size is ignored (measured 25 Nov:
        set the width while turned leaves rect and formattedWidth as they were)"""
        if [o.rect[2] - o.rect[0], o.rect[3] - o.rect[1]] != [old[2] - old[0], old[3] - old[1]]:
            o.rect = list(old)
            return
        un = o.unturned
        w, h = un[2] - un[0], un[3] - un[1]
        cx, cy = (o.rect[0] + o.rect[2]) / 2.0, (o.rect[1] + o.rect[3]) / 2.0
        L, T = int(math.floor(cx - w / 2.0 + 0.5)), int(math.floor(cy - h / 2.0 + 0.5))
        o.unturned = [L, T, L + w, T + h]

    def turn_image(self, o, a):
        """an image's angle turns it counterclockwise about its centre; its rect becomes the box around the
        turned picture, ceil(w|cos| + h|sin|) wide; angle 0 gives the first rect back (measured 25 Nov)"""
        un = getattr(o, 'unturned', None)
        if un is None:
            if to_num(o.props.get('angle', 0) or 0) % 360 != 0:
                return                         # harvested already turned: the picture is drawn as exported
            un = o.unturned = list(o.rect)
        w, h = un[2] - un[0], un[3] - un[1]
        if a == 0:
            o.rect = list(un)
            return
        r = math.radians(a)
        W = math.ceil(w * abs(math.cos(r)) + h * abs(math.sin(r)))
        H = math.ceil(w * abs(math.sin(r)) + h * abs(math.cos(r)))
        cx, cy = (un[0] + un[2]) / 2.0, (un[1] + un[3]) / 2.0
        L, T = math.floor(cx - W / 2.0), math.floor(cy - H / 2.0)
        o.rect = [L, T, L + W, T + H]

    def set_points(self, o, value, relative):
        dx, dy = (o.rect[0], o.rect[1]) if relative else (0, 0)
        pts = []
        for line in str(value).split('\n'):
            if line.strip() == '':
                pts.append(None)
                continue
            nums = [int(math.floor(to_num(p) + 0.5)) for p in line.split(',')]
            for k in range(0, len(nums) - 1, 2):      # "x,y,x,y..." on one line: pairs (measured 25 Nov)
                pts.append([nums[k] + dx, nums[k + 1] + dy])
            if len(nums) % 2:                         # an odd number left over: a break (an empty line)
                pts.append(None)
        while pts and pts[-1] is None:
            pts.pop()
        o.points = pts
        real = [q for q in pts if q is not None]
        if real:           # the rect follows the points (exact LiveCode margins for lineSize: not measured)
            xs, ys = [q[0] for q in real], [q[1] for q in real]
            o.rect = [min(xs), min(ys), max(xs) + 1, max(ys) + 1]

    def move_points(self, o, old):
        """a moved or resized line/polygon graphic takes its points along (scaled to the new size)"""
        if not o.points or old == o.rect:
            return
        ow, oh = old[2] - old[0], old[3] - old[1]
        nw, nh = o.rect[2] - o.rect[0], o.rect[3] - o.rect[1]
        sx = nw / ow if ow else 1
        sy = nh / oh if oh else 1
        o.points = [None if q is None else [int(round(o.rect[0] + (q[0] - old[0]) * sx)),
                                            int(round(o.rect[1] + (q[1] - old[1]) * sy))] for q in o.points]

    def set_geometry(self, o, p, value):
        """LiveCode's rules (LIVECODE_FACTS): width/height keep the centre; left/top... move"""
        l, t, r, b = o.rect
        w, h = r - l, b - t
        cx, cy = o.loc
        if p in ('rect', 'rectangle'):
            o.rect = ints(value, 4)
        elif p == 'width':
            w = ints(value, 1)[0]
            l = math.floor(cx - w / 2)
            o.rect = [l, t, l + w, b]
        elif p == 'height':
            h = ints(value, 1)[0]
            t = math.floor(cy - h / 2)
            o.rect = [l, t, r, t + h]
        elif p == 'left':
            v = ints(value, 1)[0]
            o.rect = [v, t, v + w, b]
        elif p == 'top':
            v = ints(value, 1)[0]
            o.rect = [l, v, r, v + h]
        elif p == 'right':
            v = ints(value, 1)[0]
            o.rect = [v - w, t, v, b]
        elif p == 'bottom':
            v = ints(value, 1)[0]
            o.rect = [l, v - h, r, v]
        elif p in ('loc', 'location'):
            x, y = ints(value, 2)
            l, t = x - w // 2, y - h // 2      # odd sizes: 71 wide at 300 -> left 265 (measured 25 Nov)
            o.rect = [l, t, l + w, t + h]
        elif p == 'topleft':
            x, y = ints(value, 2)
            o.rect = [x, y, x + w, y + h]
        elif p == 'bottomright':
            x, y = ints(value, 2)
            o.rect = [x - w, y - h, x, y]
        elif p == 'topright':
            x, y = ints(value, 2)
            o.rect = [x - w, y, x, y + h]
        elif p == 'bottomleft':
            x, y = ints(value, 2)
            o.rect = [x, y - h, x + w, y]

    # ------------------------------------------------------------ commands
    def object_with_script(self, text):
        """the object whose script is text (`insert script of X into front` hands us X's script, not X)"""
        rt = self.rt
        cands = list(rt.fronts) + list(rt.backs) + list(rt.using) + list(rt.harvest.stacks)
        for st in list(rt.harvest.stacks):
            cands += st.children + [c for card in st.children for c in card.flat()]
        for o in cands:
            try:
                if self.get_prop(self.long_id(o), 'script') == text:
                    return o
            except Exception:                  # noqa: BLE001 - an object with no script
                continue
        return None

    def command(self, name, parts):
        rt = self.rt
        self.log.append((name, parts))
        es = [v for k, v in parts if k == 'e']
        words = [v for k, v in parts if k == 'w']
        if name in ('show', 'hide'):
            if es:
                o = self.resolve(es[0])
                if o.type == 'stack':          # one window: hide this stack = show the one before it
                    o.props['visible'] = 'true' if name == 'show' else 'false'
                    if name == 'hide':
                        rt.leave_stack(o, closing=False)
                    return ''
                o.props['visible'] = 'true' if name == 'show' else 'false'
                rt.changed = True
            return ''
        if name in COMMANDS_QUIET:
            return ''
        if name in ('insert', 'remove') and len(es) == 2 and es[1].strip().lower() in ('front', 'back'):
            o = self.object_with_script(es[0])     # insert script of stack "X" into front: the script came as text
            if o is None:
                raise XtError('%s script: no object has that script' % name)
            (rt.insert_script if name == 'insert' else rt.remove_script)(o, es[1].strip().lower())
            return ''
        if name in ('start', 'stop') and words[:1] == ['using'] and es:   # start using stack "x" (a name or a file)
            st = self.library(es[0])
            if name == 'start':
                rt.start_using(st)
            else:
                rt.stop_using(st)
            return ''
        if name == 'create' and words[:1] == ['folder'] and es:
            os.makedirs(self.write_path(self._path(es[0])), exist_ok=True)    # create folder (sandbox in tests)
            return ''
        if name == 'focus':                    # focus on field "F" / focus on nothing
            if not es or es[0].strip().lower() in ('nothing', ''):
                rt.set_focus(None)
            else:
                o = self.resolve(es[0])
                rt.set_focus(o if rt.editable(o) else None)
            return ''
        if name == 'select':
            return ''
        if name in ('copy', 'cut', 'paste') and not es:   # the selected text of the focused field
            rt.edit_action(name)
            return ''
        if name == 'reset':                  # reset the templateGraphic: back to the plain one
            if es and es[0].lower().replace('the ', '') in self.TEMPLATES:
                rt.templates.pop((id(rt.default_stack), self.TEMPLATES[es[0].lower().replace('the ', '')]), None)
            return ''
        if name in ('enable', 'disable'):
            if es:
                self.resolve(es[0]).props['disabled'] = 'true' if name == 'disable' else 'false'
                rt.changed = True
            return ''
        if name in ('open', 'close', 'write', 'read') and any(e.startswith('\x00') for e in es):
            return self.file_command(name, es, words)
        if name == 'open' and es:              # open stack "about": shown in the one window (first time: its open messages)
            o = self.resolve(es[0])
            if o.type == 'stack':
                rt.go_card(o.current)
                return ''
        if name == 'close':
            o = self.resolve(es[0], must=False) if es else rt.default_stack
            if o is None:                      # a stack that is not here (close stack "Message box", an IDE
                return ''                      # window): nothing to close, the game goes on
            return self.close_stack_obj(o)
        if name == 'wait':
            rt.wait(self.wait_ms(parts))
            return ''
        if name == 'put':
            return ''
        if name in ('send', 'dispatch'):
            return self.send(name, parts)
        if name == 'choose':                   # choose browse tool / choose "pointer tool": noted only (the
            t = ' '.join([v for k, v in parts]).strip().lower()   # runtime has no editing tools)
            if t and not t.endswith('tool'):
                t = t.replace('tool ', '').strip() + ' tool'   # choose tool "browse"
            rt.tool = t or 'browse tool'
            return ''
        if name == 'cancel':
            if es:
                rt.cancel(es[0])
            return ''
        if name == 'go':
            return self.go(' '.join(v for k, v in parts))
        if name == 'click':
            return ''
        if name == 'popup':
            if es:
                o = self.resolve(es[0])
                if len(es) > 2:                # popup btn at tX, tY: the point as two expressions (lib_console's Tab)
                    x, y = ints(es[1] + ',' + es[2], 2)
                else:
                    x, y = ints(es[1], 2) if len(es) > 1 else rt.mouse
                rt.show_menu(o, x, y)
            return ''
        if name == 'grab':
            if es:
                rt.grab(self.resolve(es[0]))
            return ''
        if name == 'launch':
            return self.launch(es, words)
        if name == 'accept':                   # accept connections on port N with message M (LIB_MCP's dev server,
            return 'no sockets in the Python runtime'   # the xt3d bench): not built; the result says so, the
                                               # script goes on as when LiveCode cannot listen there (x1-04)
        if name == 'quit':                     # the program ends: the shown stack closes, the window goes
            rt.close_stack()
            rt.closed = True
            rt.quitting = True
            return ''
        raise XtError("can't find handler %s" % name)

    def set_effect(self, o, p, value, key=None):
        """set the outerGlow["size"] of X to 5 (one key; the others stay), set the outerGlow of X to tArray,
        set the outerGlow of X to empty (gone). The window redraws it (rt.fx_version)"""
        name = next(iter(o.props.keys_for(p)), EFFECTS[p])
        d = dict(effect_of(o, p) or {})
        if key is not None:
            k = next((x for x in d if x.lower() == str(key).lower()), str(key).lower())
            d[k] = value if isinstance(value, (int, float)) else to_text(value)
        elif isinstance(value, dict):
            d = {str(k).lower(): v for k, v in value.items()}
        else:
            d = {}                             # set ... to empty: no effect
        if d:
            o.props[name] = d
        elif name in o.props:
            del o.props[name]
        self.rt.fx_version = getattr(self.rt, 'fx_version', 0) + 1

    def stack_resized(self, st, old):
        """the stack's size changed (a script, or the owner dragging the window: View.user_resize):
        resizeStack newWidth, newHeight, oldWidth, oldHeight to its current card"""
        ow, oh = old[2] - old[0], old[3] - old[1]
        nw, nh = st.width, st.height
        if (nw, nh) == (ow, oh) or st.current is None:
            return
        self.rt.changed = True
        self.rt.dispatch(st.current, 'resizeStack', [str(nw), str(nh), str(ow), str(oh)])

    def close_stack_obj(self, o):
        """close stack X; also the close box once closeStackRequest was passed (View.close_request)"""
        rt = self.rt
        if o.type == 'stack' and o is not rt.first_stack:
            rt.leave_stack(o, closing=True)    # a substack closes: back to the stack shown before it
            self.destroyed(o)
            return ''
        if o.type == 'stack' and o is not rt.default_stack and any(
                id(x) in rt.opened for x in [rt.default_stack] if x is not o):
            # the first stack closes while another one is shown (the Library's second copy closes itself
            # once the game's window is up): it closes, the window goes on with the shown stack
            rt.leave_stack(o, closing=True)
            rt.shown_before = [x for x in rt.shown_before if x is not o]
            rt.first_stack = rt.default_stack
            self.destroyed(o)
            return ''
        rt.close_stack()
        rt.closed = True               # close stack / close this stack: the window ends
        return ''

    def file_command(self, name, es, words):
        """open file / write to file / close file (x1-04: the xt3d bench's check log). Measured 27 Nov: open with no
        mode = update (writes over the start), for write empties the file, for append adds at the end; a missing
        folder = "can't open that file"; write to a file not open = "file is not open for write", close =
        "file is not open". The file is written at every write (a check log survives a crash), where every write of
        this runtime goes (write_path: his real file in his window, the sandbox in checks)."""
        ref = next(e for e in es if e.startswith('\x00'))[1:]
        real = self._path(ref)
        files = self.__dict__.setdefault('open_files', {})
        key = os.path.abspath(real)
        if name == 'open':
            mode = next((w for w in words if w in ('read', 'write', 'append', 'update')), 'update')
            wp = self.write_path(real)
            src = wp if os.path.exists(wp) else real
            if mode == 'read':
                if not os.path.isfile(src):
                    return "can't open that file"
                text = open(src, 'rb').read().decode('latin-1' if ref.startswith('binfile:') else 'utf-8', 'replace')
            else:
                if not os.path.isdir(os.path.dirname(real) or '.'):
                    return "can't open that file"
                text = '' if mode == 'write' or not os.path.isfile(src) else \
                    open(src, encoding='utf-8', errors='replace').read()
                os.makedirs(os.path.dirname(wp) or '.', exist_ok=True)
                open(wp, 'w', encoding='utf-8').write(text)
            files[key] = {'mode': mode, 'pos': len(text) if mode == 'append' else 0, 'text': text, 'wp': wp}
            return ''
        f = files.get(key)
        if name == 'close':
            if f is None:
                return 'file is not open'
            del files[key]
            return ''
        if name == 'write':
            if f is None or f['mode'] == 'read':
                return 'file is not open for write'
            data = es[0]
            t, pos = f['text'], f['pos']
            f['text'] = t[:pos] + data + t[pos + len(data):]
            f['pos'] = pos + len(data)
            open(f['wp'], 'w', encoding='utf-8').write(f['text'])
            return ''
        raise XtError('read from file: not built in Python yet (it would set `it`)')

    def destroyed(self, st):
        """a closed stack with destroyStack true (and not the harvest's own): gone from memory"""
        rt = self.rt
        if st is rt.harvest.main or str(st.props.get('destroystack', '')).lower() != 'true':
            return
        if st in rt.harvest.stacks and getattr(st, 'mainstack', None) is st and not st.filename:
            rt.forget_stack(st)

    @staticmethod
    def win_path(p):
        """a path as Windows' start wants it: back slashes (//wsl$/... -> \\\\wsl$\\...)"""
        return str(p).replace('/', '\\')

    def own_file(self, path):
        """is path this program itself (the stack's own file, as a standalone's exe)?"""
        me = getattr(self.rt.harvest.main, 'filename', '') or ''
        norm = lambda x: str(x).replace('\\', '/').strip().strip('"').lower()
        return bool(me) and norm(path) == norm(me)

    def launch(self, es, words):
        """launch document X / launch url X (Windows opens it: Explorer for a folder), launch X with Y (program Y
        opens X). A real window only (owner 26 Nov: real apps); in checks it is recorded, not started.
        Launching this program itself ("a second copy", the Library's Play) goes to rt.on_self_launch."""
        rt = self.rt
        if es and str(es[0]).lower() in ('document', 'url') and len(es) > 1:
            what, prog = str(es[1]), None
        elif es and 'with' in words and len(es) > 1:
            what, prog = str(es[0]), str(es[1])
        elif es:
            what, prog = None, str(es[0])          # launch "program.exe"
        else:
            return ''
        if prog is not None and self.own_file(prog):
            return self.self_launch([what] if what is not None else [])
        cmd = 'start "" ' + ('"%s" ' % self.win_path(prog) if prog else '') + ('"%s"' % self.win_path(what) if what else '')
        if not (getattr(rt, 'real_app', False) and rt.start_programs):
            rt.not_started.append('launch: ' + cmd)
            return ''
        self.windows_shell(cmd)
        return ''

    def self_launch(self, args):
        """a second copy of this program with these arguments (a standalone starting itself again)"""
        rt = self.rt
        if getattr(rt, 'on_self_launch', None) is None or not rt.start_programs:
            rt.not_started.append('this program again: %s' % ' '.join(args))
            return ''
        print('second copy:', args, flush=True)
        rt.on_self_launch(list(args))
        return ''

    SELF_START = re.compile(r'^\s*start\s+""\s+"([^"]+)"\s*(.*)$', re.I)

    def send(self, name, parts):
        rt = self.rt
        i = 0
        if (name == 'dispatch' and len(parts) > 1 and parts[0][0] == 'e' and parts[1][0] == 'e'
                and to_text(parts[0][1]).lower() == 'function'):
            i = 1                              # dispatch function "f" to X with ...: its value is the result
        msg = to_text(parts[i][1]) if len(parts) > i and parts[i][0] == 'e' else ''
        i, target, delay, args = i + 1, None, None, []
        while i < len(parts):
            k, v = parts[i]
            if (k, v) == ('w', 'to') and i + 1 < len(parts):
                target = self.resolve(to_text(parts[i + 1][1]))
                i += 2
            elif (k, v) == ('w', 'in') and i + 1 < len(parts):
                n = to_num(parts[i + 1][1])
                unit = parts[i + 2][1] if i + 2 < len(parts) and parts[i + 2][0] == 'w' else 'ticks'
                delay = n * {'milliseconds': 1, 'millisecond': 1, 'seconds': 1000, 'second': 1000,
                             'ticks': 1000 / 60, 'tick': 1000 / 60}.get(unit, 1)
                i += 3
            elif (k, v) == ('w', 'with'):
                args = [vv for kk, vv in parts[i + 1:] if kk == 'e']
                break
            else:
                i += 1
        if target is None:
            target = rt.running_obj() or rt.default_stack.current
        if name == 'dispatch':
            r = rt.dispatch(target, msg, args)
            self.cmd_it = rt.dispatched        # it = handled / unhandled / passed (the interpreter puts it)
            return r if isinstance(r, str) else ''
        if delay is not None:
            return str(rt.after(delay, target, msg))
        rt.send_text(target, msg)
        return ''

    @staticmethod
    def wait_ms(parts):
        """wait N [ticks|milliseconds|seconds] (ticks when no unit); wait until/while: 0 here"""
        if parts and parts[0] in (('w', 'until'), ('w', 'while')):
            return 0
        try:
            n = to_num(parts[0][1]) if parts else 0
        except XtError:
            return 0
        unit = next((v for k, v in parts[1:] if k == 'w' and v != 'with'), 'ticks')
        return n * {'milliseconds': 1, 'millisecond': 1, 'seconds': 1000, 'second': 1000}.get(unit, 1000 / 60)

    def go(self, text):
        rt = self.rt
        t = re.sub(r'^\s*to\s+', '', text.strip(), flags=re.I)
        st = rt.default_stack
        low = t.lower()
        if low.startswith('next'):
            i = st.children.index(st.current)
            card = st.children[(i + 1) % len(st.children)]
        elif low.startswith(('prev', 'previous', 'back')):
            i = st.children.index(st.current)
            card = st.children[i - 1]
        elif low.startswith('first card'):
            card = st.children[0]
        elif low.startswith('last card'):
            card = st.children[-1]
        else:
            card = self.resolve(t)
            if card.type == 'stack':           # go_card makes it the default stack (after its same-card check)
                card = card.current
        rt.go_card(card)
        return ''

    # ------------------------------------------------------------ files
    @staticmethod
    def user_home():
        """the user's home: under WSL the Windows profile (/mnt/c/Users/<name>), else ~"""
        prof = os.environ.get('USERPROFILE', '')
        if not prof and os.path.isdir('/mnt/c/Users'):
            try:
                import subprocess
                prof = subprocess.run(['cmd.exe', '/c', 'echo %USERPROFILE%'], capture_output=True, text=True,
                                      stdin=subprocess.DEVNULL, timeout=5, cwd='/mnt/c').stdout.strip()
            except (OSError, subprocess.SubprocessError):
                prof = ''
        p = StackHost.real_path(prof) if prof else ''
        return p if p and os.path.isdir(p) else os.path.expanduser('~')

    @staticmethod
    def real_path(p):
        """a path as a script gives it -> one this Python can open: C:/x or C:\\x -> /mnt/c/x under WSL"""
        p = str(p).replace('\\', '/')
        m = re.match(r'(?i)^//(?:wsl\$|wsl\.localhost)/[^/]+(/.*)$', p)   # //wsl$/Ubuntu/home/... (his Windows
        if m:                                                            # LiveCode's name for a WSL file)
            return m.group(1)
        m = re.match(r'^([A-Za-z]):/(.*)$', p)
        if m and os.path.isdir('/mnt/%s' % m.group(1).lower()):
            return '/mnt/%s/%s' % (m.group(1).lower(), m.group(2))
        return p

    def list_dir(self, kind, path=None):
        """files() / folders(): the names in the defaultFolder (or path), one a line; folders() starts with .."""
        d = self.real_path(path) if path else self.default_folder
        try:
            names = sorted(os.listdir(d), key=str.lower)
        except OSError:
            return ''
        if kind == 'files':
            return '\n'.join(n for n in names if os.path.isfile(os.path.join(d, n)))
        return '\n'.join(['..'] + [n for n in names if os.path.isdir(os.path.join(d, n))])

    def write_path(self, p):
        """where a write to p goes: p itself in the owner's own window (rt.real_app), else the sandbox copy"""
        if getattr(self.rt, 'real_app', False):
            return os.path.abspath(self.real_path(p))
        return self.sandboxed(p)

    def sandboxed(self, p):
        home = os.path.abspath(getattr(self, 'sandbox_root', None) or self.folders.get('home', 'run_files'))
        full = os.path.abspath(p) if not re.match(r'^[A-Za-z]:/|^[a-z]+:', p) else None
        if full is not None and (full == home or full.startswith(home + os.sep)):
            return full
        safe = re.sub(r'[^A-Za-z0-9._/-]', '_', p.lstrip('/'))
        safe = '/'.join(x for x in safe.split('/') if x not in ('', '.', '..'))
        return os.path.join(home, 'elsewhere', safe or 'unnamed')

    def special_folder(self, name):
        return self.folders.get(name.lower(), '')

    def _path(self, ref):
        low = ref.lower()
        path = ref[5:] if low.startswith('file:') else ref[8:] if low.startswith('binfile:') else ref
        return self.real_path(path)

    @staticmethod
    def _kind(kind, ref):
        """URL ("binfile:" & x): the kind is in the text"""
        return 'binfile' if ref.lower().startswith('binfile:') else 'file' if ref.lower().startswith('file:') else kind

    def read_url(self, kind, ref):
        kind = self._kind(kind, ref)
        p = self._path(ref)
        sp = self.write_path(p)                # written here before: the sandbox copy is the file now (copy on
        if os.path.exists(sp):                 # write), so `put x after URL "file:..."` adds instead of replacing
            p = sp
        if not os.path.exists(p):
            return ''
        if kind == 'binfile':                  # one char a byte (measured 25 Nov: a 6-byte UTF-8 file is 6 long)
            return open(p, 'rb').read().decode('latin-1')
        # file: is UTF-8 text here; LiveCode gives one char a byte there too (also 6): NOT the same yet
        return open(p, encoding='utf-8', errors='replace').read()

    def write_url(self, kind, ref, text):
        """a real window writes the real file (owner 26 Nov: "as if they are real apps"); tests and surveys
        write in the sandbox (run_files): any other path is redirected under run_files/elsewhere/"""
        kind = self._kind(kind, ref)
        p = self.write_path(self._path(ref))
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
        if kind == 'binfile':                  # one char a byte back to the byte
            open(p, 'wb').write(text.encode('latin-1', 'replace'))
            return
        open(p, 'w', encoding='utf-8').write(text)
