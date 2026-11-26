"""pyrt: what translated xTalk (the Python that xtalk/transpile.py writes) runs on.

The Runtime is the interpreter itself plus a few helpers, so translated and interpreted code share
one set of LiveCode rules (values.py, chunks.py, interp.py) and can call each other's handlers:
a translated handler may `do` a string, and an interpreted one may call a translated handler.
"""
import warnings
from . import chunks as ch                                    # noqa: F401  (used by generated code)
from .values import XtError, to_text, to_num, to_bool, numstr, plain   # noqa: F401
from .interp import (Interp, Frame, BUILTINS as B, CONST as K, Thrown, Break, Pass,   # noqa: F401
                     ExitRepeat, NextRepeat, _re_search)
from .host import wildcard
from .parser import parse_statements

ASSIGNABLE_BYREF_FN = ('var', 'idx')           # what a function call writes back to (as interp.e_call)
ASSIGNABLE_BYREF_CMD = ('var', 'idx', 'chunk')  # what a command call writes back to (as interp.x_cmd)


class Runtime(Interp):
    """an Interp that also runs translated modules"""
    W = {}          # fast code: what @ parameters / matchText captures give back, until the caller takes it

    def install(self, module_text, name='<xtalk>'):
        """run a module the translator wrote and add its handlers"""
        env = {'__name__': 'xtalk_generated'}
        with warnings.catch_warnings():              # `return` inside `finally` is what the xTalk said
            warnings.simplefilter('ignore', SyntaxWarning)
            code = compile(module_text, name, 'exec')
        exec(code, env)
        env['install'](self)
        return env

    # ---- variables
    def cur_raw(self, fr, name):
        """a variable as add/subtract read it: empty while it was never set"""
        return '' if self.undefined(fr, name) else self.getvar(fr, name)

    def cur_text(self, fr, name):
        return '' if self.undefined(fr, name) else to_text(self.getvar(fr, name))

    def declare_global(self, fr, names):
        for n in names:
            fr.globals.add(n.lower())
            self.G.setdefault(n.lower(), '')

    def cant_put(self, *_):
        raise XtError("put: can't put into that")

    # ---- objects
    def this_obj(self, typ):
        return self.host.current.get(typ, '%s "this"' % typ)

    @staticmethod
    def obj_name(typ, v):
        v = to_text(v)
        return '%s %s' % (typ, v if v.lstrip('-').isdigit() else '"%s"' % v)

    # ---- values
    @staticmethod
    def join(vals):
        return ','.join(to_text(x) for x in vals)

    def filter_text(self, text, kind, pattern, neg):
        pat = wildcard(pattern)
        kw = self.delims()
        d = kw['item_delim'] if kind == 'item' else kw['line_delim']
        return d.join(text[a:b] for a, b in ch.spans(text, kind, **kw) if bool(pat.match(text[a:b])) != neg)

    def do_text(self, fr, code):
        """`do`: code made at run time is interpreted"""
        self.exec_block(parse_statements(code), fr)

    def has_handler(self, name):
        return self.lookup(name)[1] is not None

    # ---- calls
    def fn(self, fr, name, args, setters):
        """a function call: the script's own handlers first, then the built-in functions.
        setters[i] = (node kind, function that writes a value back into argument i) or None"""
        n = name.lower()
        h = self.lookup(n)[1]
        if h is not None and h[0] == 'function':
            r = self.invoke(name, args)
            for i, v in self.refs.items():
                if i < len(setters) and setters[i] is not None and setters[i][0] in ASSIGNABLE_BYREF_FN:
                    setters[i][1](v)
            return r
        f = B.get(n)
        if f is None and (not args or n == 'mouse'):   # mouseLoc() is the mouseLoc (measured 25 Nov)
            return self.e_prop(('prop', n), fr)
        if f is None:
            raise XtError("expression: can't find function %s" % name)
        if n == 'matchtext':                       # captures go into the variables named after the pattern
            m = _re_search(args[1], args[0])
            if m:
                for s, grp in zip(setters[2:], m.groups()):
                    if s is None:
                        self.cant_put()
                    s[1](grp or '')
            return 'true' if m else 'false'
        return f(self, fr, *args)

    @property
    def HN(self):
        """the names of every handler a call could reach (a script's own `function trunc` beats the built-in)"""
        return self.handlers

    def fcmd(self, fr, name, vals, kinds, words):
        """a command line from fast code: a handler of the script, else the host. Returns what the handler's
        @ parameters hold at its end ({argument index: value}), or None"""
        if self.lookup(name)[1] is not None:
            self.check_byref(name, kinds)
            r = self.invoke(name, vals)
            self.result = r if isinstance(r, str) else ''
            return self.refs
        it = iter(vals)
        parts = [('e', to_text(next(it))) if w is None else ('w', w) for w in words]
        self.result = to_text(self.host.command(name, parts) or '')
        return None

    def cmd(self, fr, name, vals, setters, words):
        """a command line: a handler of the script, else the host (go, show, answer...).
        words: the line's layout, a word for each word part and None for each expression"""
        if self.lookup(name)[1] is not None:
            self.check_byref(name, [None if st is None else st[0] for st in setters])
            r = self.invoke(name, vals)
            self.result = r if isinstance(r, str) else ''
            for i, v in self.refs.items():
                if i < len(setters) and setters[i] is not None and setters[i][0] in ASSIGNABLE_BYREF_CMD:
                    setters[i][1](v)
            return
        it = iter(vals)
        parts = [('e', to_text(next(it))) if w is None else ('w', w) for w in words]
        self.result = to_text(self.host.command(name, parts) or '')


# ------------------------------------------------------------------ the fast translator's helpers
# (xtalk/fastgen.py). A handler's own variables are Python variables there and may hold a plain float (a
# number not yet turned into text); everything that leaves the handler goes through O() first, so the rest
# of the runtime only ever sees text, NumStr or arrays.
import copy
import math
import math as _m
from .values import NumStr, text_num, num_cmp, fmt_num, compare as _compare
from .interp import rnd_half_away   # noqa: F401


class Unset(str):
    """a variable not yet set: its value is its own name; add/put after treat it as empty"""
    __slots__ = ()


def N(v):
    """a value as a number (float)"""
    t = type(v)
    if t is float:
        return v
    if t is NumStr:
        return v.raw
    if t is str or t is Unset:
        r = text_num(v)
        if r is not None:
            return r
        if v.strip() == '':
            return 0.0
        raise XtError('expression: bad operand')
    if t is int:
        return float(v)
    return to_num(to_text(v))


def N0(v):
    """add/subtract/... to a variable: one never set counts as empty"""
    return 0.0 if type(v) is Unset else N(v)


def T(v):
    """a value as text (a number gets numberFormat)"""
    t = type(v)
    if t is str:
        return v
    if t is float:
        return numstr(v)
    if t is Unset:                       # an unset variable's value is its name, as plain text
        return str.__str__(v)
    return to_text(v)


def T0(v):
    """put after/before a variable: one never set counts as empty"""
    return '' if type(v) is Unset else T(v)


def O(v):
    """a value leaving the handler: a float becomes a NumStr (text that keeps the full number); an unset
    variable's name becomes plain text"""
    t = type(v)
    if t is float:
        return numstr(v)
    if t is Unset:
        return str.__str__(v)
    return v


def CP(v):
    """put a into b: an array is copied (an unset variable gives its name as plain text)"""
    t = type(v)
    if t is float:
        return v
    if t is Unset:
        return str.__str__(v)
    return copy.deepcopy(v) if isinstance(v, dict) else v


def KY(v):
    """an array key"""
    if type(v) is float and v.is_integer() and abs(v) < 1e15:
        return str(int(v))
    return to_text(v)


def fdiv(a, b):
    if b == 0:
        raise XtError('expression: divide by zero')
    return a / b


def adiv(cur, a):
    """divide x by a (the command)"""
    if a == 0:
        raise XtError('divide: divide by zero')
    return cur / a


def idiv(a, b):
    if b == 0:
        raise XtError('expression: divide by zero')
    return float(_m.trunc(a / b))


def fmod_(a, b):
    if b == 0:
        raise XtError('expression: divide by zero')
    return _m.fmod(a, b)


def fpow(a, b):
    try:
        return float(a) ** b
    except (OverflowError, ZeroDivisionError):
        raise XtError('expression: bad operand')


def ftrunc(x):
    return float(_m.trunc(x))


def fsqrt(x):
    if x < 0:
        raise XtError('expression: bad operand')
    return _m.sqrt(x)


def fround(x):
    return float(rnd_half_away(x))


def _num_or_none(v):
    t = type(v)
    if t is float:
        return v
    if t is NumStr:
        return v.raw
    if t is str or t is Unset:
        return text_num(v)
    return None


def xcmp(a, b):
    """-1/0/1 of two values (as values.compare, for values that may be floats)"""
    if type(a) is float and type(b) is float:
        return num_cmp(a, b)
    x = _num_or_none(a)
    if x is not None:
        y = _num_or_none(b)
        if y is not None:
            return num_cmp(x, y)
    return _compare(T(a), T(b))


def feq(x, y):
    return num_cmp(x, y) == 0


def flt(x, y):
    return num_cmp(x, y) < 0


def fgt(x, y):
    return num_cmp(x, y) > 0


def tb(b):
    """a Python truth as xTalk text"""
    return 'true' if b else 'false'


def isempty(v):
    return T(v) == ''


def aget1(arr, k):
    """arr[k] (one key)"""
    return arr.get(k, '') if type(arr) is dict else ''


def aget(arr, keys):
    cur = arr
    for k in keys:
        if type(cur) is not dict:
            return ''
        cur = cur.get(k, '')
    return cur


def aput(arr, keys, value, mode):
    """put value into arr[keys...]: returns the array (a new one when arr was not an array)"""
    if type(arr) is not dict:
        arr = {}
    top, cur = arr, arr
    for k in keys[:-1]:
        nxt = cur.get(k)
        if type(nxt) is not dict:
            nxt = {}
            cur[k] = nxt
        cur = nxt
    last = keys[-1]
    if mode == 'into':
        cur[last] = copy.deepcopy(value) if isinstance(value, dict) else T(value)
    else:
        old = to_text(cur.get(last, ''))
        cur[last] = old + T(value) if mode == 'after' else T(value) + old
    return top


def adel(arr, keys):
    """delete arr[keys...]"""
    if type(arr) is not dict:
        return
    for k in keys[:-1]:
        arr = arr.get(k)
        if type(arr) is not dict:
            return
    arr.pop(keys[-1], None)


def sync_out(V, vals, fr=None, globs=()):
    """a fast handler's variables into its frame (before `do`, value()...): one never set is not there.
    globs: the names it uses as globals (the interpreter finds them in fr.globals). Returns None"""
    if globs:
        fr.globals.update(globs)
    for k, v in vals.items():
        if type(v) is Unset:
            V.pop(k, None)
        else:
            V[k] = O(v)


def pname(name, v):
    """the tProp of x: a custom property named by a variable's value (as Interp.prop_name)"""
    if type(v) is Unset or isinstance(v, dict):
        return name
    t = T(v)
    return t if t != '' else name


_AMONG = {}


def among_items(rt, l, r, kind='item'):
    """l is among the items of r (numbers compare as numbers): r's items are kept for the next time"""
    r = T(r)
    kw = rt.delims()
    d = kw['item_delim'] if kind == 'item' else kw['line_delim']
    key = (r, kind, d)
    ent = _AMONG.get(key)
    if ent is None:
        if len(_AMONG) > 256:
            _AMONG.clear()
        items = [r[a:b] for a, b in ch.spans(r, kind, **kw)]
        nums = [text_num(i) for i in items]
        ent = _AMONG[key] = (items, [n for n in nums if n is not None],
                             {i.lower() for i, n in zip(items, nums) if n is None})
    items, nums, texts = ent
    x = _num_or_none(l)
    if x is not None:
        return any(num_cmp(x, y) == 0 for y in nums)    # (a number's text is never like a non-number's)
    return T(l).lower() in texts


_PARTS = {}


def gchunk(rt, kind, text, n):
    """chunk n of text, n a number"""
    text = T(text)
    i = int(_m.floor(n))
    if i >= 1:
        if kind == 'char':
            return text[i - 1:i]
        if kind in ('line', 'item'):        # the text's lines / items, kept for the next time
            d = rt.props['linedelimiter' if kind == 'line' else 'itemdelimiter']
            key = (text, d)
            parts = _PARTS.get(key)
            if parts is None:
                parts = text.split(d) if text else []
                if len(parts) > 1 and parts[-1] == '':     # one trailing delimiter starts no new line
                    parts.pop()
                if len(_PARTS) > 256:
                    _PARTS.clear()
                _PARTS[key] = parts
            return parts[i - 1] if i <= len(parts) else ''
    return ch.get(text, kind, i, i, **rt.delims())
