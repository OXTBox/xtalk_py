"""StackHost: the interpreter's host for real stack objects (the in-memory one is xtalk/host.py).

The interpreter names objects with text (`graphic "Box1" of stack "X"`, `button id 1004 of card id 1002
of stack "X"`, `field 1`); this host finds the object, reads and sets its properties, and runs the
engine's commands (show, hide, send, dispatch, go, answer...). Rules measured in LiveCode are in
docs/LIVECODE_FACTS.md ("Objects and messages").
"""
import math, os, re, subprocess, sys
from ..host import Host
from ..values import XtError, to_num
from ..parser import tokenize, ORDINALS
from .model import CONTROL_TYPES, to_xtalk, Obj, regular_points
from . import styled

TYPE = {'button': 'button', 'btn': 'button', 'field': 'field', 'fld': 'field', 'graphic': 'graphic',
        'grc': 'graphic', 'image': 'image', 'img': 'image', 'group': 'group', 'grp': 'group',
        'scrollbar': 'scrollbar', 'scrollbars': 'scrollbar', 'player': 'player', 'widget': 'widget',
        'control': 'control', 'card': 'card', 'cd': 'card', 'stack': 'stack', 'background': 'group',
        'bkgnd': 'group', 'bg': 'group', 'buttons': 'button', 'fields': 'field', 'graphics': 'graphic',
        'images': 'image', 'groups': 'group', 'controls': 'control', 'cards': 'card', 'players': 'player'}
GEOMETRY = {'rect', 'rectangle', 'left', 'top', 'right', 'bottom', 'width', 'height', 'loc', 'location',
            'topleft', 'topright', 'bottomleft', 'bottomright'}
SYNONYM = {'backcolor': 'backgroundcolor', 'forecolor': 'foregroundcolor', 'hilitecolor': 'hilitecolor',
           'bordercolor': 'bordercolor', 'hilited': 'hilite', 'vis': 'visible', 'textcolor': 'foregroundcolor'}


def canon(p):
    """one name for LiveCode's synonyms (backColor = backgroundColor...)"""
    p = p.lower()
    return SYNONYM.get(p, p)


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

    # ------------------------------------------------------------ names
    def long_id(self, o):
        if o.type == 'stack':
            return 'stack "%s"' % o.name
        if o.type == 'card':
            return 'card id %d of stack "%s"' % (o.id, o.stack.name)
        out = '%s id %d' % (o.type, o.id)
        p = o.parent
        while p is not None and p.type == 'group':
            out += ' of group id %d' % p.id
            p = p.parent
        return out + ' of card id %d of stack "%s"' % (o.card.id if o.card else 0, o.stack.name)

    def name_of(self, o, form=''):
        if form == 'short':
            return o.name if o.name else ('%s id %d' % (o.type, o.id))
        if o.type == 'stack':
            return 'stack "%s"' % o.name
        base = '%s "%s"' % (o.type, o.name) if o.name else '%s id %d' % (o.type, o.id)
        if form == 'long':
            if o.type == 'card':
                return base + ' of stack "%s"' % o.stack.name
            return base + ' of card id %d of stack "%s"' % (o.card.id if o.card else 0, o.stack.name)
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

    def _find_stack(self, how, val):
        if how == 'name':
            v = val.replace('\\', '/').split('/')[-1]
            for s in self.rt.harvest.stacks:
                if s.name.lower() in (val.lower(), v.lower()) or os.path.basename(s.node.get('file', '')).lower() == v.lower():
                    return s
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
            o.props = dict(t.props)
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

    def delete_obj(self, desc):
        """delete graphic "x": it goes; anything pointing at it lets go"""
        rt = self.rt
        o = self.resolve(desc)
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
        for attr in ('hover', 'pressed', 'thumb_drag', 'scroll_drag'):
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
            if sub in ('file', 'files', 'folder', 'folders'):
                v = self.sandboxed(v if v.startswith('/') else os.path.join(self.folders['documents'], v))
            return v, ''
        return super().dialog(kind, sub, icon, prompt, extra, title)

    def shell(self, command):
        """shell(): in LiveCode the owner's stacks use it to start a Python script. Here only that is done
        (owner, 25 Nov): a .py file inside the stack's files folder starts with Python, as its own program,
        and the stack goes on (LiveCode's shell waits). Any other command is refused.
        Which Python: XTALK_SCRIPT_PYTHON if set (one with Tkinter, say), else the one running this."""
        path = command.strip().strip('"').replace('\\', '/')
        full = self.sandboxed(path)
        if not path.lower().endswith('.py') or full != os.path.abspath(path) or not os.path.isfile(full):
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
        if key is not None:
            s = next((v for k, v in o.sets.items() if k.lower() == p), None)
            if isinstance(s, dict):
                return next((v for k, v in s.items() if k.lower() == key.lower()), '')
            arr = next((v for k, v in o.custom.items() if k.lower() == p), None)
            return arr.get(key, '') if isinstance(arr, dict) else ''
        r = self.obj_prop(o, p)
        return r

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
        if p in ('defaultstack', 'topstack'):
            return rt.default_stack.name
        if p == 'mouseloc':
            return '%d,%d' % rt.mouse
        if p in ('mouseh', 'mousev'):
            return str(rt.mouse[0 if p == 'mouseh' else 1])
        if p == 'mouse':                   # the mouse / mouse(1): up or down
            return 'down' if rt.button_down else 'up'
        if p == 'screenrect':
            return '0,0,1536,864'
        if p == 'mainstacks':
            return rt.harvest.main.name
        if p == 'clipboard':                   # what is on it: text, or empty (measured 26 Nov)
            return 'text' if rt.get_clipboard() != '' else 'empty'
        if p == 'navigationarrows':
            return rt.props.get('navigationarrows', 'true')
        if p == 'tool':
            return 'browse tool'
        if p in ('optionkey', 'shiftkey', 'commandkey', 'controlkey', 'altkey', 'capslockkey'):
            return 'down' if p in rt.keys_down else 'up'
        return ''

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

    def obj_prop(self, o, p):
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
        for k, v in o.props.items():
            if canon(k) == cp:
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
        p = prop.lower()
        if not desc:
            return
        o = self.resolve(desc)
        self.rt.changed = True
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
        if p == 'style':                       # set the style to "Line": stored as line (measured 25 Nov)
            value = str(value).lower()
        if p == 'angle':                       # 390 reads back 30, -30 reads 330 (measured 26 Nov)
            a = to_num(value) % 360
            value = str(int(a)) if a == int(a) else str(a)
        if p in ('hilitedline', 'hilitedlines'):
            o.props['hilitedLines'] = ','.join(x.strip() for x in str(value).split(',') if x.strip().isdigit())
            return
        if p in GEOMETRY:
            old = list(o.rect)
            self.set_geometry(o, p, value)
            self.move_points(o, old)
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
        for k in o.props:
            if canon(k) == cp:
                o.props[k] = value
                return
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

    def set_points(self, o, value, relative):
        dx, dy = (o.rect[0], o.rect[1]) if relative else (0, 0)
        pts = []
        for line in str(value).split('\n'):
            if line.strip() == '':
                pts.append(None)
                continue
            x, y = ints(line, 2)
            pts.append([x + dx, y + dy])
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
            l, t = math.floor(x - w / 2), math.floor(y - h / 2)
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
    def command(self, name, parts):
        rt = self.rt
        self.log.append((name, parts))
        es = [v for k, v in parts if k == 'e']
        words = [v for k, v in parts if k == 'w']
        if name in ('show', 'hide'):
            if es:
                o = self.resolve(es[0])
                o.props['visible'] = 'true' if name == 'show' else 'false'
                rt.changed = True
            return ''
        if name in COMMANDS_QUIET:
            return ''
        if name == 'create' and words[:1] == ['folder'] and es:
            os.makedirs(self.sandboxed(self._path(es[0])), exist_ok=True)     # create folder: inside the sandbox
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
        if name == 'close':
            rt.close_stack()
            rt.closed = True               # close stack / close this stack: the window ends
            return ''
        if name == 'wait':
            rt.wait(self.wait_ms(parts))
            return ''
        if name == 'put':
            return ''
        if name in ('send', 'dispatch'):
            return self.send(name, parts)
        if name == 'go':
            return self.go(' '.join(v for k, v in parts))
        if name == 'click':
            return ''
        if name == 'popup':
            if es:
                o = self.resolve(es[0])
                x, y = ints(es[1], 2) if len(es) > 1 else rt.mouse
                rt.show_menu(o, x, y)
            return ''
        if name == 'grab':
            if es:
                rt.grab(self.resolve(es[0]))
            return ''
        raise XtError("can't find handler %s" % name)

    def send(self, name, parts):
        rt = self.rt
        msg = parts[0][1] if parts and parts[0][0] == 'e' else ''
        i, target, delay, args = 1, None, None, []
        while i < len(parts):
            k, v = parts[i]
            if (k, v) == ('w', 'to') and i + 1 < len(parts):
                target = self.resolve(parts[i + 1][1])
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
            rt.dispatch(target, msg, args)
            return ''
        if delay is not None:
            rt.after(delay, target, msg)
            return ''
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
    def sandboxed(self, p):
        home = os.path.abspath(self.folders.get('home', 'run_files'))
        full = os.path.abspath(p) if not re.match(r'^[A-Za-z]:/|^[a-z]+:', p) else None
        if full is not None and (full == home or full.startswith(home + os.sep)):
            return full
        safe = re.sub(r'[^A-Za-z0-9._/-]', '_', p.lstrip('/'))
        safe = '/'.join(x for x in safe.split('/') if x not in ('', '.', '..'))
        return os.path.join(home, 'elsewhere', safe or 'unnamed')

    def special_folder(self, name):
        return self.folders.get(name.lower(), '')

    def _path(self, ref):
        path = ref[5:] if ref.lower().startswith('file:') else ref
        return path.replace('\\', '/')

    def read_url(self, kind, ref):
        p = self._path(ref)
        return open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else ''

    def write_url(self, kind, ref, text):
        """writes stay in the sandbox (run_files): any other path is redirected under run_files/elsewhere/"""
        p = self.sandboxed(self._path(ref))
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
        open(p, 'w', encoding='utf-8').write(text)
