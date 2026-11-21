"""The xTalk interpreter: runs the parser's tuples. Everything is text."""
import math, random, time, base64
from . import chunks as ch
from .values import XtError, to_num, fmt_num, to_text, to_bool, is_numeric_text, compare, NUMBER_FORMAT
from .parser import parse_script, parse_expr, parse_statements

CONST = {'empty': '', 'true': 'true', 'false': 'false', 'space': ' ', 'comma': ',', 'return': '\n', 'cr': '\r',
         'lf': '\n', 'newline': '\n', 'quote': '"', 'tab': '\t', 'pi': fmt_num(math.pi), 'colon': ':',
         'slash': '/', 'backslash': '\\', 'null': '\0', 'formfeed': '\f', 'zero': '0', 'one': '1', 'two': '2',
         'three': '3', 'four': '4', 'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'}


class Return(Exception):
    def __init__(self, v):
        self.v = v

class ExitRepeat(Exception): pass
class NextRepeat(Exception): pass
class ExitHandler(Exception): pass
class Break(Exception): pass
class Thrown(Exception):
    def __init__(self, v):
        self.v = v


class Frame:
    def __init__(self, args):
        self.vars = {}
        self.globals = set()
        self.args = args


def rnd_half_away(x, places=0):
    f = 10 ** places
    y = abs(x) * f
    r = math.floor(y + 0.5)
    return math.copysign(r / f, x) if r else 0


class Interp:
    def __init__(self, script=''):
        self.handlers = parse_script(script) if script.strip() else {}
        self.G = {}                     # global variables
        self.props = {'itemdelimiter': ',', 'linedelimiter': '\n', 'numberformat': '0.######',
                      'casesensitive': 'false'}
        self.output = []                # what `put x` with no target printed
        self.result = ''
        self.depth = 0

    # ------------------------------------------------------------ public
    def load(self, script):
        self.handlers.update(parse_script(script))

    def call(self, name, *args):
        return self.invoke(name, [to_text(a) for a in args])

    def eval(self, text, frame=None):
        return to_text(self.ev(parse_expr(text), frame or Frame([])))

    def run(self, text):
        """run statements as if in a handler; returns the text `return` gave, or ''"""
        fr = Frame([])
        try:
            self.exec_block(parse_statements(text), fr)
        except Return as r:
            return to_text(r.v)
        return ''

    def var(self, fr, name):
        return fr.vars

    # ------------------------------------------------------------ handlers
    def invoke(self, name, args):
        h = self.handlers.get(name.lower())
        if h is None:
            raise XtError("handler: can't find handler %s" % name)
        kind, _, params, body = h
        self.depth += 1
        if self.depth > 400:
            self.depth = 0
            raise XtError('handler: stack overflow')
        fr = Frame(args)
        for i, p in enumerate(params):
            fr.vars[p.lower()] = args[i] if i < len(args) else ''
        try:
            self.exec_block(body, fr)
        except Return as r:
            return to_text(r.v)
        except ExitHandler:
            return ''
        finally:
            self.depth -= 1
        return ''

    # ------------------------------------------------------------ variables
    def getvar(self, fr, name):
        n = name.lower()
        if n in fr.globals:
            return self.G.get(n, '')
        if n in fr.vars:
            return fr.vars[n]
        return name                      # an unset variable is its own name

    def setvar(self, fr, name, v):
        n = name.lower()
        (self.G if n in fr.globals else fr.vars)[n] = v

    # ------------------------------------------------------------ statements
    def exec_block(self, body, fr):
        for st in body:
            self.exec_stmt(st, fr)

    def exec_stmt(self, st, fr):
        k = st[0]
        m = getattr(self, 'x_' + k)
        return m(st, fr)

    def x_print(self, st, fr):
        self.output.append(to_text(self.ev(st[1], fr)))

    def x_global(self, st, fr):
        for n in st[1]:
            fr.globals.add(n.lower())
            self.G.setdefault(n.lower(), '')

    def x_local(self, st, fr):
        for n in st[1]:
            fr.vars.setdefault(n.lower(), '')

    def x_put(self, st, fr):
        v = self.ev(st[1], fr)
        self.assign(st[3], v, st[2], fr)

    def x_arith(self, st, fr):
        op, e, target = st[1], st[2], st[3]
        a = to_num(to_text(self.ev(e, fr)))
        cur = self.ev(target, fr) if not (target[0] == 'var' and self.undefined(fr, target[1])) else ''
        b = to_num(to_text(cur))
        if op == 'add':
            r = b + a
        elif op == 'subtract':
            r = b - a
        elif op == 'multiply':
            r = b * a
        else:
            if a == 0:
                raise XtError('divide: divide by zero')
            r = b / a
        self.assign(target, fmt_num(r), 'into', fr)

    def undefined(self, fr, name):
        n = name.lower()
        return n not in fr.vars and n not in fr.globals

    def x_delete(self, st, fr):
        t = st[1]
        if t[0] == 'var':
            n = t[1].lower()
            fr.vars.pop(n, None)
            return
        if t[0] == 'idx':
            arr = self.getvar_arr(fr, t[1])
            if arr is not None:
                key = self.key(t[2][:], fr)
                for kk in key[:-1]:
                    arr = arr.get(kk, {})
                arr.pop(key[-1], None)
            return
        if t[0] == 'chunk':
            kind, a, b, inner = t[1], t[2], t[3], t[4]
            cur = to_text(self.ev(inner, fr))
            a, b = self.range(a, b, fr, kind, cur)
            new = self.cut(cur, kind, a, b)
            self.assign(inner, new, 'into', fr)
            return
        raise XtError("delete: can't delete that")

    def cut(self, text, kind, a, b):
        kw = self.delims()
        sp = ch.spans(text, kind, **kw)
        n = len(sp)
        r = ch._range(n, a, b)
        if r is None:
            return text
        s, e = sp[r[0]][0], sp[r[1]][1]
        if kind in ('item', 'line'):                     # take one delimiter with it
            d = kw['item_delim'] if kind == 'item' else kw['line_delim']
            if r[1] < n - 1:
                e += len(d)
            elif s >= len(d):
                s -= len(d)
        elif kind == 'word':
            while e < len(text) and text[e] in ' \t' and (s == 0 or True):
                e += 1
        return text[:s] + text[e:]

    def x_replace(self, st, fr):
        a, b = to_text(self.ev(st[1], fr)), to_text(self.ev(st[2], fr))
        cur = to_text(self.ev(st[3], fr))
        if a != '':
            self.assign(st[3], cur.replace(a, b), 'into', fr)

    def x_setprop(self, st, fr):
        self.props[st[1]] = to_text(self.ev(st[2], fr))
        if st[1] == 'numberformat':
            NUMBER_FORMAT[0] = self.props[st[1]]

    def x_return(self, st, fr):
        raise Return(self.ev(st[1], fr))

    def x_exit(self, st, fr):
        if st[1] == 'repeat':
            raise ExitRepeat()
        raise ExitHandler()

    def x_next(self, st, fr):
        raise NextRepeat()

    def x_break(self, st, fr):
        raise Break()

    def x_pass(self, st, fr):
        raise ExitHandler()

    def x_throw(self, st, fr):
        raise Thrown(to_text(self.ev(st[1], fr)))

    def x_if(self, st, fr):
        if to_bool(self.ev(st[1], fr)):
            self.exec_block(st[2], fr)
        else:
            self.exec_block(st[3], fr)

    def x_try(self, st, fr):
        _, body, var, catch, fin = st
        try:
            try:
                self.exec_block(body, fr)
            except (Thrown, XtError) as e:
                if var is None and not catch:
                    raise
                if var:
                    self.setvar(fr, var, e.v if isinstance(e, Thrown) else str(e))
                self.exec_block(catch, fr)
        finally:
            self.exec_block(fin, fr)

    def x_switch(self, st, fr):
        _, subject, cases, default = st
        sv = to_text(self.ev(subject, fr)) if subject else None
        try:
            for vals, body in cases:
                for v in vals:
                    x = self.ev(v, fr)
                    hit = (to_text(x) == sv) if sv is not None else to_bool(x)
                    if hit:
                        self.exec_block(body, fr)
                        return
            if default is not None:
                self.exec_block(default, fr)
        except Break:
            pass

    def x_repeat(self, st, fr):
        _, kind, p, body = st
        def run():
            try:
                self.exec_block(body, fr)
            except NextRepeat:
                pass
        try:
            if kind == 'forever':
                while True:
                    run()
            elif kind == 'times':
                for _ in range(int(to_num(to_text(self.ev(p, fr))))):
                    run()
            elif kind == 'while':
                while to_bool(self.ev(p, fr)):
                    run()
            elif kind == 'until':
                while not to_bool(self.ev(p, fr)):
                    run()
            elif kind == 'with':
                v, a, b, step, down = p
                x = to_num(to_text(self.ev(a, fr)))
                end = to_num(to_text(self.ev(b, fr)))
                s = to_num(to_text(self.ev(step, fr))) if step is not None else (-1 if down else 1)
                if (s >= 0) if down else (s <= 0):
                    return                         # a step that points away from the end: no passes
                while (x > end + s) if down else (x < end + s):    # LiveCode runs one pass past the end (LIVECODE_FACTS)
                    self.setvar(fr, v, fmt_num(x))
                    run()
                    x += s
            elif kind == 'each':
                ck, v, e = p
                text = to_text(self.ev(e, fr))
                kind2 = ck.rstrip('s') if ck not in ('chars',) else 'char'
                if kind2 in ('key',):
                    arr = self.ev(e, fr)
                    for key in list(arr):
                        self.setvar(fr, v, key)
                        run()
                else:
                    kind2 = {'character': 'char', 'chars': 'char'}.get(ck, kind2)
                    kw = self.delims()
                    for a, b in ch.spans(text, kind2, **kw):
                        self.setvar(fr, v, text[a:b])
                        run()
        except ExitRepeat:
            pass

    def x_callcmd(self, st, fr):
        name, args = st[1], [to_text(self.ev(a, fr)) for a in st[2]]
        r = self.invoke(name, args)
        self.result = r

    def x_sort(self, st, fr):
        _, kind, target, desc, mode, by = st
        text = to_text(self.ev(target, fr))
        kw = self.delims()
        d = kw['item_delim'] if kind == 'item' else kw['line_delim']
        parts = [text[a:b] for a, b in ch.spans(text, kind, **kw)]
        def key(p):
            if by is not None:
                fr.vars['each'] = p
                p = to_text(self.ev(by, fr))
            if mode == 'numeric':
                try:
                    return (0, to_num(p))
                except XtError:
                    return (0, 0)
            return (0, p.lower())
        parts.sort(key=key, reverse=desc)
        self.assign(target, d.join(parts), 'into', fr)

    # ------------------------------------------------------------ assignment
    def delims(self):
        return {'item_delim': self.props['itemdelimiter'], 'line_delim': self.props['linedelimiter']}

    def getvar_arr(self, fr, name):
        n = name.lower()
        v = (self.G if n in fr.globals else fr.vars).get(n)
        return v if isinstance(v, dict) else None

    def key(self, keys, fr):
        out, cur = [], []
        for k in keys:
            cur.append(to_text(self.ev(k, fr)))
        return [''.join(cur)] if len(cur) > 1 and ',' in cur else cur

    def assign(self, target, value, mode, fr):
        k = target[0]
        if k == 'var':
            if mode == 'into':
                self.setvar(fr, target[1], value if isinstance(value, dict) else to_text(value))
            else:
                cur = to_text(self.getvar(fr, target[1])) if not self.undefined(fr, target[1]) else ''
                v = to_text(value)
                self.setvar(fr, target[1], cur + v if mode == 'after' else v + cur)
            return
        if k == 'idx':
            n = target[1].lower()
            store = self.G if n in fr.globals else fr.vars
            arr = store.get(n)
            if not isinstance(arr, dict):
                arr = {}
                store[n] = arr
            keys = self.key(target[2], fr)
            for kk in keys[:-1]:
                nxt = arr.get(kk)
                if not isinstance(nxt, dict):
                    nxt = {}
                    arr[kk] = nxt
                arr = nxt
            last = keys[-1]
            if mode == 'into':
                arr[last] = value
            else:
                cur = to_text(arr.get(last, ''))
                arr[last] = cur + to_text(value) if mode == 'after' else to_text(value) + cur
            return
        if k == 'chunk':
            _, kind, a, b, inner = target
            cur = to_text(self.ev(inner, fr)) if not (inner[0] == 'var' and self.undefined(fr, inner[1])) else ''
            a2, b2 = self.range(a, b, fr, kind, cur)
            new = ch.put(cur, kind, a2, b2, to_text(value), mode, **self.delims())
            self.assign(inner, new, 'into', fr)
            return
        raise XtError("put: can't put into that")

    def range(self, a, b, fr, kind=None, text=''):
        av = self.chunk_index(a, fr, kind, text)
        bv = av if b is None else self.chunk_index(b, fr, kind, text)
        return av, bv

    def chunk_index(self, e, fr, kind, text):
        if e[0] == 'ord':
            n = ch.count(text, kind, **self.delims())
            if e[1] == 'any':
                return random.randint(1, max(n, 1))
            return (n + 1) // 2 if n else 1
        return int(math.floor(to_num(to_text(self.ev(e, fr)))))

    # ------------------------------------------------------------ expressions
    def truth(self, v):
        return to_text(v).strip().lower() == 'true'

    def ev(self, e, fr):
        return getattr(self, 'e_' + e[0])(e, fr)

    def e_str(self, e, fr):
        return e[1]

    def e_num(self, e, fr):
        return e[1]

    def e_const(self, e, fr):
        return CONST[e[1]]

    def e_var(self, e, fr):
        return self.getvar(fr, e[1])

    def e_prop(self, e, fr):
        n = e[1]
        if n == 'result':
            return self.result
        if n in self.props:
            return self.props[n]
        if n in ('seconds',):
            return fmt_num(int(time.time()))
        if n in ('milliseconds', 'millisecs', 'ticks'):
            return fmt_num(int(time.time() * (60 if n == 'ticks' else 1000)))
        if n == 'paramcount':
            return fmt_num(len(fr.args))
        raise XtError('expression: unknown property "the %s"' % n)

    def e_idx(self, e, fr):
        arr = self.getvar_arr(fr, e[1])
        if arr is None:
            return ''
        keys = self.key(e[2], fr)
        cur = arr
        for kk in keys:
            if not isinstance(cur, dict):
                return ''
            cur = cur.get(kk, '')
        return cur

    def e_isa(self, e, fr):
        v = to_text(self.ev(e[1], fr))
        t = e[2]
        if t == 'number':
            return 'true' if is_numeric_text(v) else 'false'
        if t == 'integer':
            return 'true' if is_numeric_text(v) and float(v) == int(float(v)) and 'e' not in v.lower() and '.' not in v else 'false'
        if t == 'boolean':
            return 'true' if v in ('true', 'false') else 'false'
        return 'false'

    def e_count(self, e, fr):
        return str(ch.count(to_text(self.ev(e[2], fr)), e[1], **self.delims()))

    def e_chunk(self, e, fr):
        _, kind, a, b, inner = e
        text = to_text(self.ev(inner, fr))
        a2, b2 = self.range(a, b, fr, kind, text)
        if b is None:
            b2 = a2
        return ch.get(text, kind, a2, b2, **self.delims())

    def e_un(self, e, fr):
        op = e[1]
        v = self.ev(e[2], fr)
        if op == 'not':
            return 'false' if to_bool(v) else 'true'
        n = to_num(to_text(v))
        return fmt_num(-n if op == '-' else n)

    def e_bin(self, e, fr):
        op = e[1]
        if op == 'and':
            return 'true' if (self.truth(self.ev(e[2], fr)) and self.truth(self.ev(e[3], fr))) else 'false'
        if op == 'or':
            return 'true' if (self.truth(self.ev(e[2], fr)) or self.truth(self.ev(e[3], fr))) else 'false'
        l = self.ev(e[2], fr)
        r = self.ev(e[3], fr)
        if op == 'among' or op == 'in':
            pass
        if op in ('&', '&&'):
            ls, rs = to_text(l), to_text(r)
            return ls + (' ' if op == '&&' else '') + rs
        if op in ('=', '<>', '<', '>', '<=', '>='):
            c = compare(to_text(l), to_text(r))
            return 'true' if {'=': c == 0, '<>': c != 0, '<': c < 0, '>': c > 0, '<=': c <= 0, '>=': c >= 0}[op] else 'false'
        if op == 'contains':
            return 'true' if to_text(r).lower() in to_text(l).lower() else 'false'
        if op == 'begins':
            return 'true' if to_text(l).lower().startswith(to_text(r).lower()) else 'false'
        if op == 'ends':
            return 'true' if to_text(l).lower().endswith(to_text(r).lower()) else 'false'
        if op == 'in':
            return 'true' if to_text(l).lower() in to_text(r).lower() else 'false'
        if op == 'among':
            items = [to_text(r)[a:b] for a, b in ch.spans(to_text(r), 'item', **self.delims())]
            return 'true' if any(compare(to_text(l), i) == 0 for i in items) else 'false'
        a, b = to_num(to_text(l)), to_num(to_text(r))
        if op == '+':
            return fmt_num(a + b)
        if op == '-':
            return fmt_num(a - b)
        if op == '*':
            return fmt_num(a * b)
        if op == '/':
            if b == 0:
                raise XtError('expression: divide by zero')
            return fmt_num(a / b)
        if op == 'div':
            if b == 0:
                raise XtError('expression: divide by zero')
            return fmt_num(math.trunc(a / b))
        if op == 'mod':
            if b == 0:
                raise XtError('expression: divide by zero')
            return fmt_num(math.fmod(a, b) if isinstance(a, float) or isinstance(b, float) else a - b * math.trunc(a / b))
        if op == '^':
            try:
                return fmt_num(float(a) ** b if not (isinstance(a, int) and isinstance(b, int) and b >= 0) else a ** b)
            except (OverflowError, ZeroDivisionError):
                raise XtError('expression: bad operand')
        raise XtError('expression: unknown operator %s' % op)

    def e_call(self, e, fr):
        name = e[1]
        n = name.lower()
        args = [self.ev(a, fr) for a in e[2]]
        if n in self.handlers and self.handlers[n][0] == 'function':
            return self.invoke(name, [to_text(a) for a in args])
        f = BUILTINS.get(n)
        if f is None:
            raise XtError("expression: can't find function %s" % name)
        return f(self, fr, *args)


# ------------------------------------------------------------------ builtins
def _n(x):
    return to_num(to_text(x))

def _t(x):
    return to_text(x)

def f_round(it, fr, x, places='0'):
    p = int(_n(places))
    return fmt_num(rnd_half_away(_n(x), p))

def f_min(it, fr, *a):
    vals = [_n(x) for x in (a if len(a) > 1 else [p for p in _t(a[0]).split(',')])]
    return fmt_num(min(vals))

def f_max(it, fr, *a):
    vals = [_n(x) for x in (a if len(a) > 1 else [p for p in _t(a[0]).split(',')])]
    return fmt_num(max(vals))

def f_offset(it, fr, needle, hay, skip='0'):
    s = int(_n(skip))
    i = _t(hay).lower().find(_t(needle).lower(), s)
    return str(i + 1 if i >= 0 else 0)

def _offset_chunk(kind):
    def f(it, fr, needle, hay, skip='0'):
        text, nd = _t(hay), _t(needle)
        sp = ch.spans(text, kind, **it.delims())
        for idx, (a, b) in enumerate(sp):
            if idx >= int(_n(skip)) and text[a:b].lower() == nd.lower():
                return str(idx + 1)
        return '0'
    return f

def f_keys(it, fr, arr):
    if not isinstance(arr, dict):
        return ''
    return '\n'.join(arr.keys())

def f_param(it, fr, n):
    i = int(_n(n))
    return fr.args[i - 1] if 1 <= i <= len(fr.args) else ''

def f_value(it, fr, text):
    return it.ev(parse_expr(_t(text)), fr)

def f_random(it, fr, n):
    return str(random.randint(1, int(_n(n))))

def f_numtochar(it, fr, n):
    return chr(int(_n(n)))

def f_chartonum(it, fr, c):
    c = _t(c)
    return str(ord(c[0])) if c else '0'

def f_trunc(it, fr, x):
    return fmt_num(math.trunc(_n(x)))

def f_matheq(fn):
    return lambda it, fr, *a: fmt_num(fn(*[float(_n(x)) for x in a]))

BUILTINS = {
    'length': lambda it, fr, x: str(len(_t(x))),
    'round': f_round,
    'abs': lambda it, fr, x: fmt_num(abs(_n(x))),
    'sqrt': lambda it, fr, x: fmt_num(math.sqrt(_n(x))) if _n(x) >= 0 else (_ for _ in ()).throw(XtError('expression: bad operand')),
    'trunc': f_trunc,
    'min': f_min, 'max': f_max,
    'sin': f_matheq(math.sin), 'cos': f_matheq(math.cos), 'tan': f_matheq(math.tan),
    'atan': f_matheq(math.atan), 'atan2': f_matheq(math.atan2), 'exp': f_matheq(math.exp),
    'ln': f_matheq(math.log), 'log10': f_matheq(math.log10),
    'toupper': lambda it, fr, x: _t(x).upper(),
    'tolower': lambda it, fr, x: _t(x).lower(),
    'offset': f_offset, 'itemoffset': _offset_chunk('item'), 'lineoffset': _offset_chunk('line'),
    'wordoffset': _offset_chunk('word'),
    'random': f_random, 'numtochar': f_numtochar, 'chartonum': f_chartonum,
    'keys': f_keys, 'the number of elements': lambda it, fr, a: str(len(a)) if isinstance(a, dict) else '0',
    'param': f_param, 'paramcount': lambda it, fr: str(len(fr.args)), 'value': f_value,
    'base64encode': lambda it, fr, x: base64.b64encode(_t(x).encode('utf-8')).decode(),
    'base64decode': lambda it, fr, x: base64.b64decode(_t(x)).decode('utf-8', 'replace'),
    'sum': lambda it, fr, *a: fmt_num(sum(_n(x) for x in (a if len(a) > 1 else _t(a[0]).split(',')))),
    'average': lambda it, fr, *a: fmt_num(sum(_n(x) for x in a) / len(a)),
    'isnumber': lambda it, fr, x: 'true' if is_numeric_text(_t(x)) else 'false',
}
