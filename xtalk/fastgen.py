"""fastgen: the translator's fast mode. A handler becomes Python that runs at Python speed:

- the handler's own variables (parameters, `local` ones, ones it just uses) are Python variables, not a
  dictionary looked up by name; script locals and globals are dictionaries bound once on entry;
- a number stays a Python float while it is inside the handler (no text made and read back at every step);
  it becomes text (a NumStr that keeps the full value) only when it leaves: stored in a script local, a
  global, an array, a field, passed to another handler, returned;
- comparisons in `if` / `repeat while` are Python truths, not "true"/"false" text;
- script-level constants with a plain value are written into the code.

The rules stay the interpreter's: arithmetic, comparisons and chunks go through xtalk/pyrt.py helpers that
follow values.py / interp.py. A handler that needs the interpreter's frame by name (`do`, value(), `sort by`,
`select`, styled chunks, matchText captures, a global declared halfway down...) is translated the plain way
(xtalk/transpile.py Gen), which is slower but the same rules; translate_script reports those as 'plain'.
"""
import re
from .transpile import Gen, TranslateError, _r
from .interp import Interp

NUMOPS = {'+': '(%s + %s)', '-': '(%s - %s)', '*': '(%s * %s)', '/': 'fdiv(%s, %s)', 'div': 'idiv(%s, %s)',
          'mod': 'fmod_(%s, %s)', '^': 'fpow(%s, %s)'}
CMPOPS = ('=', '<>', '<', '>', '<=', '>=')
# built-in number functions done in Python: name -> (argument count, code); None = 2 or more
NUMFNS = {'trunc': (1, 'ftrunc(%s)'), 'abs': (1, 'abs(%s)'), 'sqrt': (1, 'fsqrt(%s)'),
          'sin': (1, 'math.sin(%s)'), 'cos': (1, 'math.cos(%s)'), 'tan': (1, 'math.tan(%s)'),
          'atan': (1, 'math.atan(%s)'), 'asin': (1, 'math.asin(%s)'), 'acos': (1, 'math.acos(%s)'),
          'exp': (1, 'math.exp(%s)'), 'ln': (1, 'math.log(%s)'), 'log10': (1, 'math.log10(%s)'),
          'floor': (1, 'float(math.floor(%s))'), 'ceiling': (1, 'float(math.ceil(%s))'),
          'round': (1, 'fround(%s)'), 'atan2': (2, 'math.atan2(%s)'),
          'min': (None, 'min(%s)'), 'max': (None, 'max(%s)')}
FRAME_FNS = {'value'}                 # built-in functions that read the frame's variables by name


class NeedFrame(TranslateError):
    """this handler needs the interpreter's frame: translate it the plain way"""


def pyname(n):
    return 'L_' + re.sub(r'\W', '_', n)


def walk(x, out):
    """every node (tuple) in a statement / expression tree"""
    if isinstance(x, tuple):
        out.append(x)
        for y in x:
            walk(y, out)
    elif isinstance(x, list):
        for y in x:
            walk(y, out)


class ScriptInfo:
    """what the fast translation needs to know about the whole script"""

    def __init__(self, handlers, top, sglobals, byref_fns=()):
        self.snames = set()             # script locals and constants (rt.S)
        self.consts = {}                # constant name -> its literal node (inlined)
        written = set()
        for st in top:
            if st[0] == 'local':
                self.snames.update(n.lower() for n in st[1])
            elif st[0] == 'constant':
                self.snames.add(st[1].lower())
                v = st[2]
                if v[0] == 'un' and v[1] == '-' and v[2][0] == 'num':
                    v = ('num', '-' + v[2][1])
                if v[0] in ('num', 'str'):
                    self.consts[st[1].lower()] = v
        for kind, name, params, body, byref in handlers.values():
            written.update(p.lower() for p in params)
            nodes = []
            walk(body, nodes)
            for nd in nodes:
                if nd[0] in ('put', 'arith') and nd[-1][0] in ('var', 'idx') if nd[0] == 'arith' else \
                        (nd[0] == 'put' and len(nd) == 4 and nd[3][0] in ('var', 'idx')):
                    written.add(nd[-1][1].lower() if nd[0] == 'arith' else nd[3][1].lower())
                elif nd[0] in ('local', 'global'):
                    written.update(n.lower() for n in nd[1])
                elif nd[0] == 'constant':
                    written.add(nd[1].lower())
                elif nd[0] == 'repeat' and nd[1] == 'with':
                    written.add(nd[2][0].lower())
                elif nd[0] == 'repeat' and nd[1] == 'each':
                    written.add(nd[2][1].lower())
                elif nd[0] == 'delete' and nd[1][0] in ('var', 'idx'):
                    written.add(nd[1][1].lower())
        for n in written:
            self.consts.pop(n, None)
        self.sglobals = sglobals
        self.byref_fns = {n.lower() for n in byref_fns} | {
            h[1].lower() for h in handlers.values() if h[0] == 'function' and h[4]}


class FastGen(Gen):
    def __init__(self, info, hname, params, body, byref, unsets):
        super().__init__()
        self.info = info
        self.unsets = unsets            # {lower name: as written}: the module-level Unset('name') each needs
        self.params = [p.lower() for p in params]
        self.byref = byref
        self.in_lambda = False           # inside sort's `by` (a lambda: no := there)
        self.setup(hname, body)

    # ------------------------------------------------------------ names
    def setup(self, hname, body):
        info = self.info
        P = set(self.params)
        G = {g for g in info.sglobals.get(hname.lower(), ()) if g.lower() not in P}
        G = {g.lower() for g in G}
        leading = True
        D = set()
        self.spell = self.unsets          # lower name -> as written (an unset variable reads as its name)
        for st in body:
            if st[0] == 'global' and leading:
                G.update(n.lower() for n in st[1])
                continue
            if st[0] == 'local' and leading:
                D.update(n.lower() for n in st[1])
                continue
            leading = False
            break
        nodes = []
        walk(body, nodes)
        used = set()
        for nd in nodes:
            k = nd[0]
            if k == 'global':
                names = {n.lower() for n in nd[1]}
                if not names <= G:
                    raise NeedFrame('global declared after other lines')
            elif k == 'local':
                for n in nd[1]:
                    n = n.lower()
                    if n not in D and n in info.snames:
                        raise NeedFrame('local %s declared after other lines hides a script local' % n)
                    D.add(n)
            elif k in ('var', 'idx') and isinstance(nd[1], str):
                used.add(nd[1].lower())
                self.spell.setdefault(nd[1].lower(), nd[1])
            elif k == 'repeat' and nd[1] == 'with':
                used.add(nd[2][0].lower())
            elif k == 'repeat' and nd[1] == 'each':
                used.add(nd[2][1].lower())
            elif k == 'try' and nd[2]:
                used.add(nd[2].lower())
            elif k in ('dialog', 'create'):
                used.add('it')
        if (D | P) & G:
            raise NeedFrame('a name is both global and local')
        self.cls = {}
        for n in used | D | P:
            if n in G:
                self.cls[n] = 'G'
            elif n in P or n in D:
                self.cls[n] = 'L'
            elif n == 'me':
                self.cls[n] = 'ME'
            elif n in info.consts:
                self.cls[n] = 'C'
            elif n in info.snames:
                self.cls[n] = 'S'
            else:
                self.cls[n] = 'L'
        for n in G:
            self.cls.setdefault(n, 'G')
        if 'each' in self.cls and self.cls['each'] == 'L' and any(nd[0] == 'sort' and nd[5] is not None for nd in nodes):
            self.cls['each'] = 'EACH'          # sort ... by <expression with each>: sort_text sets it in the frame
        self.locals = sorted(n for n, c in self.cls.items() if c == 'L')
        self.declared = P

    def klass(self, name):
        n = name.lower()
        c = self.cls.get(n)
        if c is None:                        # a name only `do` could have made: not here
            raise NeedFrame('unknown name %s' % name)
        return n, c

    def prologue(self, ind):
        self.emit(ind, 'V = fr.vars; S = rt.S; G = rt.G; HN = rt.HN')
        for n in self.locals:
            if n in self.declared:
                self.emit(ind, '%s = V[%s]' % (pyname(n), _r(n)))
            else:
                self.unsets.setdefault(n, n)
                self.emit(ind, '%s = U_%s' % (pyname(n), pyname(n)[2:]))
        for n, c in sorted(self.cls.items()):
            if c == 'G':
                self.emit(ind, 'G.setdefault(%s, "")' % _r(n))

    # ------------------------------------------------------------ expressions
    def isnum(self, e):
        k = e[0]
        if k == 'num':
            return True
        if k == 'bin':
            return e[1] in NUMOPS
        if k == 'un':
            return e[1] == '-'
        if k == 'call':
            f = NUMFNS.get(e[1].lower())
            return f is not None and (len(e[2]) == f[0] if f[0] else len(e[2]) >= 2)
        if k == 'var':
            n = e[1].lower()
            return self.cls.get(n) == 'C' and self.info.consts[n][0] == 'num'
        return False

    def num(self, e):
        """code for a float"""
        k = e[0]
        if k == 'num':
            try:
                return repr(float(e[1]))
            except ValueError:
                return 'N(%s)' % _r(e[1])
        if k == 'var':
            n, c = self.klass(e[1])
            if c == 'C' and self.info.consts[n][0] == 'num':
                try:
                    return repr(float(self.info.consts[n][1]))
                except ValueError:
                    pass
            return 'N(%s)' % self.val(e)
        if k == 'bin' and e[1] in NUMOPS:
            return NUMOPS[e[1]] % (self.num(e[2]), self.num(e[3]))
        if k == 'un' and e[1] == '-':
            return '(-%s)' % self.num(e[2])
        if k == 'call' and self.isnum(e):
            name = e[1].lower()
            args = [self.num(a) for a in e[2]]
            fast = NUMFNS[name][1] % ', '.join(args)
            slow = 'N(rt.fn(fr, %s, [%s], []))' % (_r(e[1]), ', '.join('O(%s)' % a for a in args))
            return '(%s if %s not in HN else %s)' % (fast, _r(name), slow)
        return 'N(%s)' % self.val(e)

    def cond(self, e):
        """code for a Python truth"""
        k = e[0]
        if k == 'bin' and e[1] in ('and', 'or'):
            return '(%s %s %s)' % (self.cond(e[2]), e[1], self.cond(e[3]))
        if k == 'un' and e[1] == 'not':
            return '(not %s)' % self.cond(e[2])
        if k == 'bin' and e[1] in CMPOPS:
            op, l, r = e[1], e[2], e[3]
            if self.isnum(l) and self.isnum(r):
                a, b = self.num(l), self.num(r)
                return {'=': 'feq(%s, %s)', '<>': '(not feq(%s, %s))', '<': 'flt(%s, %s)', '>': 'fgt(%s, %s)',
                        '<=': '(not fgt(%s, %s))', '>=': '(not flt(%s, %s))'}[op] % (a, b)
            if op in ('=', '<>') and r == ('const', 'empty'):
                return '(isempty(%s) %s True)' % (self.val(l), '==' if op == '=' else '!=')
            return '(xcmp(%s, %s) %s 0)' % (self.val(l), self.val(r), {'=': '==', '<>': '!='}.get(op, op))
        if k == 'bin' and e[1] in ('among', 'among_lines'):
            return 'among_items(rt, %s, %s, %s)' % (self.val(e[2]), self.val(e[3]),
                                                    _r('item' if e[1] == 'among' else 'line'))
        return 'to_bool(%s)' % self.ex(e)

    def may_float(self, e):
        if self.isnum(e):
            return True
        return e[0] == 'var' and self.cls.get(e[1].lower()) == 'L'

    def ex(self, e):
        """code for a value that is never a bare float (what the rest of the runtime takes)"""
        c = self.val(e)
        return 'O(%s)' % c if self.may_float(e) else c

    def container(self, name):
        """code reading a variable as an array holder"""
        n, c = self.klass(name)
        if c == 'L':
            return pyname(n)
        if c == 'S':
            return 'S[%s]' % _r(n)
        if c == 'G':
            return 'G.get(%s, "")' % _r(n)
        if c == 'C':
            return _r(self.info.consts[n][1])
        raise NeedFrame('me as an array')

    def keys(self, ks):
        if len(ks) == 1:
            return '[KY(%s)]' % self.val(ks[0])
        return 'rt.key_vals([%s])' % ', '.join(self.ex(x) for x in ks)

    def val(self, e):
        """code for a value; a float is allowed (for a handler variable)"""
        if e[0] == 'num':
            return _r(e[1])                    # put 0.10 into x: x is "0.10" (a literal keeps its text)
        if self.isnum(e):
            return self.num(e)
        k = e[0]
        if k == 'var':
            n, c = self.klass(e[1])
            if c == 'L':
                return pyname(n)
            if c == 'S':
                return 'S[%s]' % _r(n)
            if c == 'G':
                return 'G.get(%s, "")' % _r(n)
            if c == 'C':
                return _r(self.info.consts[n][1])
            if c == 'EACH':
                return 'V.get("each", %s)' % _r(e[1])
            return 'rt.e_var(%s, fr)' % _r(('var', e[1]))
        if k == 'idx':
            if len(e[2]) == 1:
                return 'aget1(%s, KY(%s))' % (self.container(e[1]), self.val(e[2][0]))
            return 'aget(%s, %s)' % (self.container(e[1]), self.keys(e[2]))
        if k == 'bin' and e[1] in ('&', '&&'):
            return '(T(%s) + %s%s)' % (self.val(e[2]), "' ' + " if e[1] == '&&' else '', 'T(%s)' % self.val(e[3]))
        if (k == 'bin' and e[1] in CMPOPS + ('and', 'or', 'among', 'among_lines')) or (k == 'un' and e[1] == 'not'):
            return 'tb(%s)' % self.cond(e)
        if k == 'chunk' and e[3] is None and e[2][0] != 'ord':
            return 'gchunk(rt, %s, %s, %s)' % (_r(e[1]), self.val(e[4]), self.num(e[2]))
        return Gen.ex(self, e)

    def x_var(self, e):
        return self.ex(e)

    def x_idx(self, e):
        return self.val(e)

    def desc(self, e):
        if e[0] == 'var' and e[1].lower() == 'me' and self.cls.get('me') == 'ME':
            return "to_text(rt.getvar(fr, 'me'))"
        if e[0] != 'obj':
            return 'T(%s)' % self.val(e)
        return Gen.desc(self, e)

    def x_propkey(self, e):
        return self.in_frame('rt.e_propkey(%r, fr)' % (e,))

    def prop_code(self, name):
        """the property's name: `the tProp of x` may name it by a variable"""
        if ' ' in name or name in Interp.ENGINE_PROPS:
            return _r(name)
        n = name.lower()
        c = self.cls.get(n)
        if c is None:
            return _r(name)
        if c == 'ME':
            return 'rt.prop_name(fr, %s)' % _r(name)
        return 'pname(%s, %s)' % (_r(name), self.val(('var', name)))

    def x_propof(self, e):
        _, name, operand, key = e
        if operand[0] == 'chunk' and Interp.chunk_style_prop(name):
            return self.in_frame('rt.e_propof(%r, fr)' % (e,))
        from .interp import BUILTINS
        if BUILTINS.get(name) is not None and operand[0] != 'obj' and name.lower() not in FRAME_FNS:
            return 'B[%s](rt, fr, %s)' % (_r(name), self.ex(operand))
        kc = 'None' if key is None else 'T(%s)' % self.val(key)
        return 'rt.host.get_prop(%s, %s, %s)' % (self.desc(operand), self.prop_code(name), kc)

    def x_call(self, e):
        name, args = e[1], e[2]
        n = name.lower()
        ex = [self.desc(a) if (i == 0 and n == 'within' and (a[0] == 'obj' or (a[0] == 'var' and a[1].lower() == 'me')))
              else self.ex(a) for i, a in enumerate(args)]
        if n in FRAME_FNS:
            return self.in_frame('rt.fn(fr, %s, [%s], [])' % (_r(name), ', '.join(ex)))
        if n in self.info.byref_fns or (n == 'matchtext' and len(args) > 2):
            # @ parameters / matchText captures: the values come back through rt.W, then into the variables
            if self.in_lambda:
                raise NeedFrame('by-reference call inside sort by')
            reload = []
            mt = n == 'matchtext'
            setters = ['None' if mt and i < 2 else self.setter(a, reload, mt) for i, a in enumerate(args)]
            t = self.tmp('f')
            parts = ['(%s := rt.fn(fr, %s, [%s], [%s]))' % (t, _r(name), ', '.join(ex), ', '.join(setters))]
            parts += ['(%s := rt.W.pop(%s, %s))' % (pyname(v), _r(v), pyname(v)) for v in reload]
            return '(%s)[0]' % ', '.join(parts + ([] if reload else ['None']))
        return 'rt.fn(fr, %s, [%s], [])' % (_r(name), ', '.join(ex))

    def setter(self, node, reload, must=False):
        """(kind, a function that takes the value back) for an argument that may be written to. must: a matchText
        capture (anything but a variable or array element is put into by the interpreter's rules)"""
        if node[0] == 'var':
            n, c = self.klass(node[1])
            if c == 'L':
                reload.append(n)
                return "('var', lambda _v: rt.W.__setitem__(%s, _v))" % _r(n)
            if c in ('S', 'G', 'C'):                # (a constant: into rt.S, as the interpreter)
                return "('var', lambda _v: %s.__setitem__(%s, O(_v)))" % ('S' if c == 'C' else c, _r(n))
            raise NeedFrame('by-reference argument %s' % node[1])
        if node[0] == 'idx':
            n, c = self.klass(node[1])
            if c in ('S', 'G'):
                return "('idx', lambda _v: %s.__setitem__(%s, aput(%s, %s, _v, 'into')))" % (
                    c, _r(n), self.container(node[1]), self.keys(node[2]))
            raise NeedFrame('by-reference array element')
        if must and node[0] in ('chunk', 'obj', 'propof', 'url'):
            raise NeedFrame('matchText capture into a %s' % node[0])
        return 'None'                         # an @ parameter given a chunk or a value: nothing comes back

    # ------------------------------------------------------------ assignment (a statement here)
    def set_var(self, name, code):
        """name = code (code may be a float)"""
        n, c = self.klass(name)
        if c == 'L':
            return '%s = %s' % (pyname(n), code)
        if c == 'S':
            return 'S[%s] = O(%s)' % (_r(n), code)
        if c == 'G':
            return 'G[%s] = O(%s)' % (_r(n), code)
        if c == 'ME':
            return 'rt.assign(%s, O(%s), "into", fr)' % (_r(('var', name)), code)
        if c == 'EACH':
            return 'V["each"] = O(%s)' % code
        return 'S[%s] = O(%s)' % (_r(n), code)   # a constant given to an @ parameter (as the interpreter: rt.S)

    def assign(self, t, v, mode, raw=False):
        """a statement putting value code v into t. raw: v may be a float or an array (not yet copied)"""
        k = t[0]
        if k == 'var':
            n, c = self.klass(t[1])
            if c == 'ME':
                return 'rt.assign(%s, O(%s), %s, fr)' % (_r(('var', t[1])), v, _r(mode))
            if mode == 'into':
                return self.set_var(t[1], ('CP(%s)' % v) if raw else v)
            cur = self.val(t)
            if c == 'L' and n not in self.declared:
                cur = 'T0(%s)' % cur
            else:
                cur = 'T(%s)' % cur
            new = ('%s + T(%s)' % (cur, v)) if mode == 'after' else ('T(%s) + %s' % (v, cur))
            return self.set_var(t[1], new)
        if k == 'idx':
            n, c = self.klass(t[1])
            code = 'aput(%s, %s, %s, %s)' % (self.container(t[1]), self.keys(t[2]), v, _r(mode))
            if c == 'S':
                return 'S[%s] = %s' % (_r(n), code)
            if c == 'G':
                return 'G[%s] = %s' % (_r(n), code)
            if c == 'L':
                return '%s = %s' % (pyname(n), code)
            raise NeedFrame('array of me')
        if k == 'chunk':
            _, kind, a, b, inner = t
            if inner[0] == 'var':
                n, c = self.klass(inner[1])
                cur = ('T0(%s)' if c == 'L' and n not in self.declared else 'T(%s)') % self.val(inner)
            else:
                cur = 'to_text(%s)' % self.ex(inner)
            new = 'rt.put_chunk(%s, %s, %s, %s, O(%s), %s)' % (_r(kind), cur, self.pos(a),
                                                              'None' if b is None else self.pos(b), v, _r(mode))
            return self.assign(inner, new, 'keep' if inner[0] == 'obj' else 'into')
        return Gen.assign(self, t, 'O(%s)' % v, mode)

    # ------------------------------------------------------------ statements
    def s_put(self, s, ind):
        e, mode, t = s[1], s[2], s[3]
        raw = e[0] in ('var', 'idx', 'call')             # may be an array: copied on put
        code = self.val(e)
        if t[0] == 'var' and mode == 'into' and self.cls.get(t[1].lower()) != 'ME':
            self.emit(ind, self.assign(t, code, mode, raw))
            return
        v = self.tmp('v')
        self.emit(ind, '%s = %s' % (v, ('CP(%s)' % code) if raw else code))
        self.emit(ind, self.assign(t, v, mode))

    def s_arith(self, s, ind):
        op, e, t = s[1], s[2], s[3]
        pyop = {'add': '+', 'subtract': '-', 'multiply': '*'}.get(op)
        a = self.tmp('a')
        self.emit(ind, '%s = %s' % (a, self.num(e)))
        if t[0] == 'var':
            n, c = self.klass(t[1])
            if c != 'ME':
                cur = 'N0(%s)' % self.val(t) if c == 'L' else 'N(%s)' % self.val(t)
                new = ('(%s %s %s)' % (cur, pyop, a)) if pyop else 'adiv(%s, %s)' % (cur, a)
                self.emit(ind, self.set_var(t[1], new))
                return
        if t[0] == 'idx':
            n, c = self.klass(t[1])
            if c in ('L', 'S', 'G'):
                ks = self.tmp('k')
                self.emit(ind, '%s = %s' % (ks, self.keys(t[2])))
                cur = 'N(aget(%s, %s))' % (self.container(t[1]), ks)
                new = ('(%s %s %s)' % (cur, pyop, a)) if pyop else 'adiv(%s, %s)' % (cur, a)
                code = 'aput(%s, %s, %s, "into")' % (self.container(t[1]), ks, new)
                self.emit(ind, ('%s = %s' % (pyname(n), code)) if c == 'L' else ('%s[%s] = %s' % (c, _r(n), code)))
                return
        cur = self.tmp('c')
        self.emit(ind, '%s = %s' % (cur, self.ex(t)))
        self.emit(ind, self.assign(t, 'rt.arith(%s, O(%s), %s)' % (_r(op), a, cur), 'into'))

    def s_local(self, s, ind):
        for n, init in zip(s[1], s[2]):
            n = n.lower()
            if init is not None:
                self.emit(ind, self.set_var(n, 'T(%s)' % self.val(init)))
            elif n not in self.declared:
                self.emit(ind, 'if type(%s) is Unset: %s = ""' % (pyname(n), pyname(n)))

    def s_global(self, s, ind):
        for n in s[1]:
            self.emit(ind, 'G.setdefault(%s, "")' % _r(n.lower()))

    def s_return(self, s, ind):
        self.emit(ind, 'return O(%s)' % self.val(s[1]))

    def s_if(self, s, ind, kw='if'):
        _, cond, then, els = s
        self.emit(ind, '%s %s:' % (kw, self.cond(cond)))
        self.block(then, ind + 1)
        if len(els) == 1 and els[0][0] == 'if':
            self.s_if(els[0], ind, 'elif')
        elif els:
            self.emit(ind, 'else:')
            self.block(els, ind + 1)

    def s_repeat(self, s, ind):
        _, kind, p, body = s
        if kind == 'forever':
            self.emit(ind, 'while True:')
        elif kind == 'times':
            self.emit(ind, 'for _ in range(int(%s)):' % self.num(p))
        elif kind == 'while':
            self.emit(ind, 'while %s:' % self.cond(p))
        elif kind == 'until':
            self.emit(ind, 'while not %s:' % self.cond(p))
        elif kind == 'with':
            v, a, b, step, down = p
            x, e, st = self.tmp('x'), self.tmp('e'), self.tmp('s')
            self.emit(ind, '%s = %s' % (x, self.num(a)))
            self.emit(ind, '%s = %s' % (e, self.num(b)))
            self.emit(ind, '%s = %s' % (st, self.num(step) if step is not None else ('-1.0' if down else '1.0')))
            self.emit(ind, 'while (%s) and %s:' % (('%s < 0' % st) if down else ('%s > 0' % st),
                                                  ('%s > %s + %s' % (x, e, st)) if down else ('%s < %s + %s' % (x, e, st))))
            self.emit(ind + 1, self.set_var(v, x))
            self.emit(ind + 1, '%s += %s' % (x, st))
        elif kind == 'each':
            ck, v, e = p
            kind2 = ck.rstrip('s') if ck not in ('chars',) else 'char'
            if kind2 == 'element':
                k = self.tmp('k')
                self.emit(ind, 'for %s in rt.elements(%s):' % (k, self.ex(e)))
                self.emit(ind + 1, self.set_var(v, k))
            elif kind2 == 'key':
                k = self.tmp('k')
                self.emit(ind, 'for %s in list(%s):' % (k, self.ex(e)))
                self.emit(ind + 1, self.set_var(v, k))
            else:
                kind2 = {'character': 'char', 'chars': 'char'}.get(ck, kind2)
                t, a, b = self.tmp('t'), self.tmp('a'), self.tmp('b')
                self.emit(ind, '%s = to_text(%s)' % (t, self.ex(e)))
                self.emit(ind, 'for %s, %s in ch.spans(%s, %s, **rt.delims()):' % (a, b, t, _r(kind2)))
                self.emit(ind + 1, self.set_var(v, '%s[%s:%s]' % (t, a, b)))
        else:
            raise TranslateError('repeat %s' % kind)
        self.loops += 1
        self.block(body, ind + 1)
        self.loops -= 1

    def s_try(self, s, ind):
        _, body, var, catch, fin = s
        if not var:
            return Gen.s_try(self, s, ind)
        if fin:
            self.emit(ind, 'try:')
            ind += 1
        e = self.tmp('e')
        self.emit(ind, 'try:')
        self.block(body, ind + 1)
        self.emit(ind, 'except (Thrown, XtError) as %s:' % e)
        self.emit(ind + 1, self.set_var(var, '(%s.v if isinstance(%s, Thrown) else str(%s))' % (e, e, e)))
        self.block(catch, ind + 1)
        if fin:
            ind -= 1
            self.emit(ind, 'finally:')
            self.block(fin, ind + 1)

    def s_delete(self, s, ind):
        t = s[1]
        if t[0] == 'var':
            n, c = self.klass(t[1])
            if c == 'L':
                self.unsets.setdefault(n, n)
                self.emit(ind, '%s = U_%s' % (pyname(n), pyname(n)[2:]))
            elif c in ('S', 'G'):
                self.emit(ind, '%s[%s] = ""' % (c, _r(n)))
            else:
                raise NeedFrame('delete me')
            return
        if t[0] == 'idx':
            self.emit(ind, 'adel(%s, %s)' % (self.container(t[1]), self.keys(t[2])))
            return
        Gen.s_delete(self, s, ind)

    def reload_it(self, ind):
        if self.cls.get('it') == 'L':
            self.emit(ind, 'L_it = V.get("it", L_it)')

    def s_dialog(self, s, ind):
        Gen.s_dialog(self, s, ind)
        self.reload_it(ind)

    def s_create(self, s, ind):
        Gen.s_create(self, s, ind)
        self.reload_it(ind)

    def s_sort(self, s, ind):
        if s[5] is not None and self.cls.get('each') != 'EACH':
            raise NeedFrame('sort by (each)')
        self.in_lambda = True
        try:
            Gen.s_sort(self, s, ind)
        finally:
            self.in_lambda = False

    def s_setprop(self, s, ind):
        _, name, obj, key, e = s
        if (obj is not None and obj[0] == 'chunk' and Interp.chunk_style_prop(name)) or (obj is None and key is not None):
            self.sync_out(ind)                 # set the textStyle of word 2 of field 1: the interpreter's rule
            self.emit(ind, 'rt.x_setprop(%r, fr)' % (s,))
            return
        v = self.tmp('v')
        self.emit(ind, '%s = %s' % (v, 'T(%s)' % self.val(e) if obj is None else 'rt.setprop_value(%s, True)' % self.ex(e)))
        if obj is None:
            self.emit(ind, 'rt.set_global_prop(%s, %s)' % (_r(name), v))
        else:
            kc = 'None' if key is None else 'T(%s)' % self.val(key)
            self.emit(ind, 'rt.host.set_prop(%s, %s, %s, %s)' % (self.desc(obj), self.prop_code(name), v, kc))

    def s_cmd(self, s, ind):
        name, parts = s[1], s[2]
        if name == 'select':                   # the interpreter's select reads the field and chunk by name
            self.sync_out(ind)
            self.emit(ind, 'rt.x_cmd(%r, fr)' % (s,))
            return
        nodes = [p[1] for p in parts if p[0] == 'e']
        words = [None if p[0] == 'e' else p[1] for p in parts]
        is_me = lambda n: n[0] == 'var' and self.cls.get(n[1].lower()) == 'ME'
        vals = ', '.join(self.desc(n) if n[0] == 'obj' or is_me(n) else self.ex(n) for n in nodes)
        kinds = [n[0] for n in nodes]
        r = self.tmp('r')
        back = [(i, n) for i, n in enumerate(nodes) if n[0] in ('var', 'idx', 'chunk') and not is_me(n)]

        def generic(i2):
            self.emit(i2, '%s = rt.fcmd(fr, %s, [%s], %s, %s)' % (r, _r(name), vals, _r(kinds), _r(words)))
            if back:
                self.emit(i2, 'if %s:' % r)
                for i, n in back:
                    self.emit(i2 + 1, 'if %d in %s:' % (i, r))
                    self.emit(i2 + 2, self.assign(n, '%s[%d]' % (r, i), 'into'))
        own = getattr(self, 'c_' + name, None)
        if own is None:
            generic(ind)
            return
        self.emit(ind, 'if rt.has_handler(%s):' % _r(name))
        generic(ind + 1)
        self.emit(ind, 'else:')
        start = len(self.lines)
        own(parts, ind + 1)
        if len(self.lines) == start:
            self.emit(ind + 1, 'pass')

    def c_do(self, parts, ind):
        """`do`: the handler's variables go into the frame, the interpreter runs the code there, and they come
        back (the code may have changed or made them)"""
        if not parts or parts[0][0] != 'e':
            raise TranslateError('do without code')
        code = self.tmp('d')
        self.emit(ind, '%s = to_text(%s)' % (code, self.ex(parts[0][1])))
        self.sync_out(ind)
        self.emit(ind, 'try:')
        self.emit(ind + 1, 'rt.do_text(fr, %s)' % code)
        self.emit(ind, 'finally:')
        self.emit(ind + 1, 'pass')
        for n in self.locals:
            self.unsets.setdefault(n, n)
            self.emit(ind + 1, '%s = V.get(%s, U_%s)' % (pyname(n), _r(n), pyname(n)[2:]))

    def sync_code(self):
        """an expression (None) that puts the handler's variables into its frame, for code the interpreter
        evaluates there by name (do, value(), select, styled chunks...)"""
        gl = tuple(sorted(n for n, c in self.cls.items() if c == 'G'))
        return 'sync_out(V, {%s}, fr, %s)' % (', '.join('%s: %s' % (_r(n), pyname(n)) for n in self.locals), _r(gl))

    def sync_out(self, ind):
        self.emit(ind, self.sync_code())

    def in_frame(self, code):
        """an expression evaluated by the interpreter in the frame (variables only read)"""
        return '(%s or %s)' % (self.sync_code(), code)
