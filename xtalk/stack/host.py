"""StackHost: the interpreter's host for real stack objects (the in-memory one is xtalk/host.py).

The interpreter names objects with text (`graphic "Box1" of stack "X"`, `button id 1004 of card id 1002
of stack "X"`, `field 1`); this host finds the object, reads and sets its properties, and runs the
engine's commands (show, hide, send, dispatch, go, answer...). Rules measured in LiveCode are in
docs/LIVECODE_FACTS.md ("Objects and messages").
"""
import math, os, re
from ..host import Host
from ..values import XtError, to_num
from ..parser import tokenize, ORDINALS
from .model import CONTROL_TYPES, to_xtalk

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


COMMANDS_QUIET = {'lock', 'unlock', 'beep', 'focus', 'select', 'flushevents', 'set'}


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
    def resolve(self, desc, must=True):
        d = desc.strip()
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
        if p == 'target':
            return self.name_of(rt.target) if rt.target is not None else ''
        if p in ('defaultstack', 'topstack'):
            return rt.default_stack.name
        if p == 'mouseloc':
            return '%d,%d' % rt.mouse
        if p in ('mouseh', 'mousev'):
            return str(rt.mouse[0 if p == 'mouseh' else 1])
        if p == 'screenrect':
            return '0,0,1536,864'
        if p == 'mainstacks':
            return rt.harvest.main.name
        if p == 'tool':
            return 'browse tool'
        if p in ('optionkey', 'shiftkey', 'commandkey', 'controlkey', 'altkey', 'capslockkey'):
            return 'down' if p in rt.keys_down else 'up'
        return ''

    def obj_prop(self, o, p):
        r = o.rect
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
        if p == 'customkeys':
            return '\n'.join(o.custom)
        if p == 'custompropertysets':
            return '\n'.join(o.sets)
        cp = canon(p)
        for k, v in o.props.items():
            if canon(k) == cp:
                return to_xtalk(v) if not isinstance(v, str) else v
        k, v = o.stack.default(o.type, p if p != 'hilite' else 'hilited')
        if k is not None:
            return to_xtalk(v) if not isinstance(v, str) else v
        for k, v in o.custom.items():
            if k.lower() == p:
                return v
        return ''

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
        if p in GEOMETRY:
            old = list(o.rect)
            self.set_geometry(o, p, value)
            self.move_points(o, old)
            return
        if p in ('points', 'relativepoints'):
            self.set_points(o, value, p == 'relativepoints')
            return
        if p == 'name':
            o.name = value
            return
        if p in ('text', 'menuitems'):
            o.text = value
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
        ck = next((k for k in o.custom if k.lower() == p), prop)
        o.custom[ck] = value

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
        if name in ('enable', 'disable'):
            if es:
                self.resolve(es[0]).props['disabled'] = 'true' if name == 'disable' else 'false'
                rt.changed = True
            return ''
        if name == 'close':
            rt.closed = True               # close stack / close this stack: the window ends
            return ''
        if name == 'wait':
            rt.wait(self.wait_ms(parts))
            return ''
        if name == 'answer':
            rt.answers.append(' '.join(es))
            return ''
        if name == 'put':
            return ''
        if name in ('send', 'dispatch'):
            return self.send(name, parts)
        if name == 'go':
            return self.go(' '.join(v for k, v in parts))
        if name == 'click':
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
            if card.type == 'stack':
                rt.default_stack = card
                card = card.current
        rt.go_card(card)
        return ''

    # ------------------------------------------------------------ files
    def special_folder(self, name):
        return self.folders.get(name.lower(), '')

    def _path(self, ref):
        path = ref[5:] if ref.lower().startswith('file:') else ref
        return path.replace('\\', '/')

    def read_url(self, kind, ref):
        p = self._path(ref)
        return open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else ''

    def write_url(self, kind, ref, text):
        p = self._path(ref)
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
        open(p, 'w', encoding='utf-8').write(text)
