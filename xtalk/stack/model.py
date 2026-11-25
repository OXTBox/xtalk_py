"""The objects of a stack, loaded from an XTJSON harvest (LIB_XTJSON/docs/HARVEST_FORMAT.md).

Plain Python, no GUI. A property is looked up as the harvest says: the object's own props, then the
manifest's typeDefaults for its type, then empty. Geometry lives in `rect` only.
"""
import json, math, os

CONTROL_TYPES = ('button', 'field', 'graphic', 'image', 'group', 'scrollbar', 'player', 'widget')


def num_text(v):
    """a JSON number as xTalk shows it"""
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def to_xtalk(v):
    """a harvested value -> xTalk text, or an array (dict) for custom arrays"""
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return num_text(v)
    if isinstance(v, list):
        if all(isinstance(x, (int, float, str)) and not isinstance(x, bool) for x in v):
            return ','.join(num_text(x) if not isinstance(x, str) else x for x in v)
        return {str(i + 1): to_xtalk(x) for i, x in enumerate(v)}
    if isinstance(v, dict):
        return {str(k): to_xtalk(x) for k, x in v.items()}
    return str(v)


class Obj:
    """a stack, card or control"""

    def __init__(self, kind, node, stack=None, parent=None):
        self.type = kind
        self.node = node
        self.name = node.get('name', '')
        self.id = int(node.get('id', 0))
        self.props = dict(node.get('props', {}))
        self.rect = [int(round(x)) for x in node.get('rect', [0, 0, 0, 0])]
        self.text = node.get('text', '')
        self.points = node.get('points')
        self.custom, self.sets = {}, {}
        self.script = ''
        self.children = []          # cards of a stack; controls of a card or group (layer order)
        self.parent = parent        # stack of a card; card or group of a control
        self.stack = stack
        self.layer = node.get('layer', 0)

    def __repr__(self):
        return '<%s %r id %d>' % (self.type, self.name, self.id)

    # ---- where it sits
    @property
    def card(self):
        o = self
        while o is not None and o.type != 'card':
            o = o.parent
        return o

    def flat(self):
        """controls in layer order, a group's children right after the group"""
        out = []
        for c in self.children:
            out.append(c)
            if c.type == 'group':
                out.extend(c.flat())
        return out

    # ---- geometry
    @property
    def width(self):
        return self.rect[2] - self.rect[0]

    @property
    def height(self):
        return self.rect[3] - self.rect[1]

    @property
    def loc(self):
        return (math.trunc((self.rect[0] + self.rect[2]) / 2), math.trunc((self.rect[1] + self.rect[3]) / 2))


class Stack(Obj):
    def __init__(self, node, folder, defaults):
        super().__init__('stack', node)
        self.stack = self
        self.folder = folder
        self.defaults = defaults           # typeDefaults of the manifest
        self.effective = node.get('effective', {})
        self.role = node.get('role', 'main')
        self.size = node.get('size', [self.width, self.height])
        self.ids = {}
        self.current = None                # the card shown
        self._load_common(self, node)
        shared = []
        for cn in node.get('cards', []):
            card = Obj('card', cn, self, self)
            card.number = cn.get('number', len(self.children) + 1)
            self._load_common(card, cn)
            self.children.append(card)
            card.children = self._controls(cn.get('controls', []), card, shared)
        for slot, parent, ref in shared:   # a background group placed on several cards: the same object
            real = self.ids.get(ref.get('id'))
            if real is not None:
                parent.children[slot] = real
        self.current = self.children[0] if self.children else None

    def _controls(self, nodes, parent, shared):
        out = []
        for n in nodes:
            if n.get('sharedRef'):
                shared.append((len(out), parent, n))
                out.append(Obj(n.get('type', 'group'), n, self, parent))
                continue
            o = Obj(n.get('type', 'control'), n, self, parent)
            self._load_common(o, n)
            if o.type == 'group':
                o.children = self._controls(n.get('controls', []), o, shared)
            out.append(o)
        return out

    def _load_common(self, o, node):
        self.ids[o.id] = o
        cust = dict(node.get('custom', {}))
        sets = cust.pop('$sets', {})
        o.custom = {k: self._value(v) for k, v in cust.items()}
        o.sets = {k: {kk: self._value(vv) for kk, vv in v.items()} if isinstance(v, dict) else self._value(v)
                  for k, v in sets.items()}
        sc = node.get('script')
        if isinstance(sc, dict):
            if 'text' in sc:
                o.script = sc['text']
            elif sc.get('file'):
                p = os.path.join(self.folder, sc['file'])
                if os.path.exists(p):
                    o.script = open(p, encoding='utf-8', errors='replace').read()

    def _value(self, v):
        if isinstance(v, dict) and '$file' in v:
            if v.get('$binary'):
                return ''
            p = os.path.join(self.folder, v['$file'])
            return open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else ''
        return to_xtalk(v)

    # ---- properties
    def default(self, kind, prop):
        """(the harvest's key, value) of a type default, matched without case, or (None, None)"""
        d = self.defaults.get(kind, {})
        for k, v in d.items():
            if k.lower() == prop:
                return k, v
        return None, None


class Harvest:
    """a harvest folder: the mainstack and its substacks"""

    def __init__(self, folder):
        self.folder = folder
        self.manifest = json.load(open(os.path.join(folder, 'manifest.json'), encoding='utf-8'))
        defaults = self.manifest.get('typeDefaults', {})
        self.stacks = []
        for s in self.manifest.get('stacks', []):
            node = json.load(open(os.path.join(folder, s['file']), encoding='utf-8'))
            self.stacks.append(Stack(node, folder, defaults))
        self.main = next((s for s in self.stacks if s.role == 'main'), self.stacks[0] if self.stacks else None)
        for s in self.stacks:
            s.mainstack = self.main
        self.errors = self.manifest.get('errors', [])

    def stack(self, name):
        for s in self.stacks:
            if s.name.lower() == name.lower():
                return s
        return None
