"""transpile: xTalk text -> Python source (the translator, second after the interpreter).

    from xtalk.transpile import translate_script
    py, report = translate_script(open('lib_bit.livecodescript').read(), 'lib_bit.livecodescript')
    from xtalk.pyrt import Runtime
    rt = Runtime(); rt.install(py); rt.call('Bit.Blank', 3, 2)

xTalk stays the source; the Python is generated ("do not edit"). Control flow (if, repeat, switch,
try, handlers) becomes plain Python; values go through the same rules the interpreter uses
(xtalk/pyrt.py), so a translated script answers exactly as an interpreted one. `do` and value()
of text made at run time are interpreted. A handler the translator cannot turn into Python yet is
kept as parsed xTalk and interpreted (the report counts those).
"""
import ast, re, warnings
from .values import XtError
from .parser import Parser, parse_expr, parse_statements, tokenize
from .interp import CONST, BUILTINS, Interp, split_form
from .host import filter_pattern_parts

__all__ = ['translate_script', 'translate_expr', 'translate_statements', 'TranslateError']


class TranslateError(Exception):
    pass


def _r(x):
    return repr(x)


def _tt(code):
    """to_text(code), left out when code is already a text literal"""
    try:
        if isinstance(ast.literal_eval(code), str):
            return code
    except (ValueError, SyntaxError):
        pass
    return 'to_text(%s)' % code


def _lit(code):
    try:
        return isinstance(ast.literal_eval(code), str)
    except (ValueError, SyntaxError):
        return False


class Gen:
    def __init__(self):
        self.lines = []
        self.n = 0
        self.loops = 0          # how many repeat loops we are inside (break / continue are allowed)
        self.in_switch = []     # for each open switch: does it need to catch a Break?

    def tmp(self, base='t'):
        self.n += 1
        return '_%s%d' % (base, self.n)

    def emit(self, ind, text):
        self.lines.append('    ' * ind + text)

    # ------------------------------------------------------------ expressions
    def ex(self, e):
        k = e[0]
        m = getattr(self, 'x_' + k, None)
        if m is None:
            raise TranslateError('expression kind %s' % k)
        return m(e)

    def x_str(self, e):
        return _r(e[1])

    def x_num(self, e):
        return _r(e[1])

    def x_const(self, e):
        return "K['pi']" if e[1] == 'pi' else _r(CONST[e[1]])     # pi keeps its full value

    def x_var(self, e):
        if e[1].lower() == 'me':                # in a field / button script, me as a value is its text
            return 'rt.e_var(%s, fr)' % _r(('var', e[1]))
        return 'rt.getvar(fr, %s)' % _r(e[1])

    def x_prop(self, e):
        return "rt.e_prop(('prop', %s), fr)" % _r(e[1])

    def x_idx(self, e):
        return 'rt.get_idx(fr, %s, rt.key_vals([%s]))' % (_r(e[1]), ', '.join(self.ex(x) for x in e[2]))

    def x_join(self, e):
        return 'rt.join([%s])' % ', '.join(self.ex(x) for x in e[1])

    def desc(self, e):
        """code for the text naming an object (button "OK" of card 2)"""
        if e[0] == 'var' and e[1].lower() == 'me':     # the X of me: the object itself
            return "to_text(rt.getvar(fr, 'me'))"
        if e[0] != 'obj':
            return 'to_text(%s)' % self.ex(e)
        _, typ, ref, parent = e
        if ref[0] == 'this':
            base = 'rt.this_obj(%s)' % _r(typ)
        elif ref[0] == 'ord':
            base = _r('%s %s' % (ref[1], typ))
        elif ref[0] == 'id':
            base = '(%s + to_text(%s))' % (_r(typ + ' id '), self.ex(ref[1]))
        else:
            base = 'rt.obj_name(%s, %s)' % (_r(typ), self.ex(ref))
        if parent is not None:
            p = self.desc(parent) if parent[0] == 'obj' else 'to_text(%s)' % self.ex(parent[1])
            base = '(%s + " of " + %s)' % (base, p)
        return base

    def x_obj(self, e):
        return 'rt.obj_value(%s, %s)' % (_r(e[1]), self.desc(e))

    def x_exists(self, e):
        return "('true' if rt.host.exists(%s) != %r else 'false')" % (self.desc(e[1]), e[2])

    def x_countobj(self, e):
        return 'str(rt.host.count(%s, to_text(%s)))' % (_r(e[1]), self.ex(e[2]))

    def x_url(self, e):
        return 'rt.host.read_url(%s, to_text(%s))' % (_r(e[1]), self.ex(e[2]))

    def x_propkey(self, e):
        return 'rt.e_propkey(%r, fr)' % (e,)

    def x_propof(self, e):
        _, name, operand, key = e
        if operand[0] == 'chunk' and Interp.chunk_style_prop(name):   # the textStyle of word 2 of field 1: the interpreter's rule
            return 'rt.e_propof(%r, fr)' % (e,)
        if BUILTINS.get(name) is not None and operand[0] != 'obj':
            return 'B[%s](rt, fr, %s)' % (_r(name), self.ex(operand))
        kc = 'None' if key is None else 'to_text(%s)' % self.ex(key)
        return 'rt.host.get_prop(%s, rt.prop_name(fr, %s), %s)' % (self.desc(operand), _r(name), kc)

    def x_isa(self, e):
        return 'rt.isa(%s, %s)' % (self.ex(e[1]), _r(e[2]))

    def x_count(self, e):
        return 'str(ch.count(to_text(%s), %s, **rt.delims()))' % (self.ex(e[2]), _r(e[1]))

    def pos(self, e):
        return _r(tuple(e)) if e[0] == 'ord' else self.ex(e)

    def x_chunk(self, e):
        _, kind, a, b, inner = e
        return 'rt.get_chunk(%s, %s, %s, %s)' % (_r(kind), self.ex(inner), self.pos(a),
                                                  'None' if b is None else self.pos(b))

    def x_un(self, e):
        return 'rt.unop(%s, %s)' % (_r(e[1]), self.ex(e[2]))

    def x_bin(self, e):
        op = e[1]
        if op in ('and', 'or'):
            return "('true' if (rt.truth(%s) %s rt.truth(%s)) else 'false')" % (self.ex(e[2]), op, self.ex(e[3]))
        return 'rt.binop(%s, %s, %s)' % (_r(op), self.ex(e[2]), self.ex(e[3]))

    def setter(self, node):
        """(kind, lambda that puts a value into node) for by-reference and matchText arguments"""
        if node[0] not in ('var', 'idx', 'chunk', 'obj', 'propof', 'url'):
            return 'None'
        return '(%s, lambda _v: %s)' % (_r(node[0]), self.assign(node, '_v', 'into'))

    def x_call(self, e):
        name, args = e[1], e[2]
        ex = [self.desc(a) if (i == 0 and name.lower() == 'within' and a[0] == 'obj') else self.ex(a)
              for i, a in enumerate(args)]
        return 'rt.fn(fr, %s, [%s], [%s])' % (_r(name), ', '.join(ex),
                                               ', '.join(self.setter(a) for a in args))

    # ------------------------------------------------------------ assignment (an expression)
    def assign(self, t, v, mode):
        k = t[0]
        if k == 'var' and t[1].lower() == 'me':
            return 'rt.assign(%s, %s, %s, fr)' % (_r(t), v, _r(mode))
        if k == 'var':
            return 'rt.put_var(fr, %s, %s, %s)' % (_r(t[1]), v, _r(mode))
        if k == 'idx':
            return 'rt.put_idx(fr, %s, rt.key_vals([%s]), %s, %s)' % (
                _r(t[1]), ', '.join(self.ex(x) for x in t[2]), v, _r(mode))
        if k == 'chunk':
            _, kind, a, b, inner = t
            cur = 'rt.cur_text(fr, %s)' % _r(inner[1]) if inner[0] == 'var' and inner[1].lower() != 'me' \
                else 'to_text(%s)' % self.ex(inner)
            new = 'rt.put_chunk(%s, %s, %s, %s, %s, %s)' % (_r(kind), cur, self.pos(a),
                                                            'None' if b is None else self.pos(b), v, _r(mode))
            return self.assign(inner, new, 'keep' if inner[0] == 'obj' else 'into')
        if k == 'obj':
            return 'rt.put_obj(%s, %s, %s)' % (self.desc(t), v, _r(mode))
        if k == 'propof':
            return 'rt.host.set_prop(%s, %s, to_text(%s))' % (self.desc(t[2]), _r(t[1]), v)
        if k == 'url':
            return 'rt.put_url(%s, to_text(%s), %s, %s)' % (_r(t[1]), self.ex(t[2]), v, _r(mode))
        return 'rt.cant_put(%s)' % v

    # ------------------------------------------------------------ statements
    def block(self, body, ind):
        start = len(self.lines)
        for st in body:
            self.st(st, ind)
        if len(self.lines) == start:
            self.emit(ind, 'pass')

    def st(self, s, ind):
        m = getattr(self, 's_' + s[0], None)
        if m is None:
            raise TranslateError('statement %s' % s[0])
        m(s, ind)

    def s_dialog(self, s, ind):
        _, kind, sub, icon, prompt, extra, title = s
        self.emit(ind, 'rt.do_dialog(fr, %s, %s, %s, to_text(%s), [%s], to_text(%s))' % (
            _r(kind), _r(sub), _r(icon), self.ex(prompt), ', '.join('to_text(%s)' % self.ex(x) for x in extra),
            self.ex(title)))

    def s_print(self, s, ind):
        self.emit(ind, 'rt.output.append(to_text(%s))' % self.ex(s[1]))

    def s_global(self, s, ind):
        self.emit(ind, 'rt.declare_global(fr, %s)' % _r(list(s[1])))

    def s_local(self, s, ind):
        for n, init in zip(s[1], s[2]):
            key = _r(n.lower())
            if init is not None:
                self.emit(ind, 'fr.vars[%s] = to_text(%s)' % (key, self.ex(init)))
            else:
                self.emit(ind, 'fr.vars[%s] = fr.vars.get(%s, "")' % (key, key))

    def s_constant(self, s, ind):
        self.emit(ind, 'rt.S[%s] = to_text(%s)' % (_r(s[1].lower()), self.ex(s[2])))

    def s_put(self, s, ind):
        code = self.ex(s[1])
        if _lit(code):                                   # a constant value needs no temporary
            self.emit(ind, self.assign(s[3], code, s[2]))
            return
        v = self.tmp('v')
        self.emit(ind, '%s = %s' % (v, code))
        self.emit(ind, self.assign(s[3], v, s[2]))

    def s_arith(self, s, ind):
        op, e, t = s[1], s[2], s[3]
        a, c = self.tmp('a'), self.tmp('c')
        self.emit(ind, '%s = %s' % (a, self.ex(e)))
        self.emit(ind, '%s = %s' % (c, 'rt.cur_raw(fr, %s)' % _r(t[1]) if t[0] == 'var' else self.ex(t)))
        self.emit(ind, self.assign(t, 'rt.arith(%s, %s, %s)' % (_r(op), a, c), 'into'))

    def s_delete(self, s, ind):
        t = s[1]
        if t[0] == 'var':
            self.emit(ind, 'rt.delete_var(fr, %s)' % _r(t[1].lower()))
        elif t[0] == 'idx':
            self.emit(ind, 'rt.del_idx(fr, %s, rt.key_vals([%s]))' % (_r(t[1]), ', '.join(self.ex(x) for x in t[2])))
        elif t[0] == 'chunk':
            _, kind, a, b, inner = t
            c = self.tmp('c')
            self.emit(ind, '%s = to_text(%s)' % (c, self.ex(inner)))
            self.emit(ind, self.assign(inner, 'rt.cut_chunk(%s, %s, %s, %s)' % (
                _r(kind), c, self.pos(a), 'None' if b is None else self.pos(b)), 'keep' if inner[0] == 'obj' else 'into'))
        elif t[0] == 'obj':
            self.emit(ind, 'rt.host.delete_obj(%s)' % self.desc(t))
        else:
            self.emit(ind, 'raise XtError("delete: can\'t delete that")')

    def s_create(self, s, ind):
        _, typ, invisible, name, group = s
        self.emit(ind, 'rt.do_create(fr, %s, %r, %s, %s)' % (
            _r(typ), invisible, 'None' if name is None else 'to_text(%s)' % self.ex(name),
            'None' if group is None else self.desc(group)))

    def s_replace(self, s, ind):
        a, b, c = self.tmp('a'), self.tmp('b'), self.tmp('c')
        self.emit(ind, '%s = %s' % (a, _tt(self.ex(s[1]))))
        self.emit(ind, '%s = %s' % (b, _tt(self.ex(s[2]))))
        self.emit(ind, '%s = to_text(%s)' % (c, self.ex(s[3])))
        self.emit(ind, 'if %s != "":' % a)
        self.emit(ind + 1, self.assign(s[3], '%s.replace(%s, %s)' % (c, a, b), 'into'))

    def s_setprop(self, s, ind):
        _, name, obj, key, e = s
        if (obj is not None and obj[0] == 'chunk' and Interp.chunk_style_prop(name)) or (obj is None and key is not None):
            # set the textStyle of word 2 of field 1 / set the clipboardData["text"]: the interpreter's rule
            self.emit(ind, 'rt.x_setprop(%r, fr)' % (s,))
            return
        v = self.tmp('v')
        self.emit(ind, '%s = %s' % (v, _tt(self.ex(e)) if obj is None else 'rt.setprop_value(%s, True)' % self.ex(e)))
        if obj is None:
            self.emit(ind, 'rt.set_global_prop(%s, %s)' % (_r(name), v))
        else:
            kc = 'None' if key is None else 'to_text(%s)' % self.ex(key)
            self.emit(ind, 'rt.result = rt.host.set_prop(%s, rt.prop_name(fr, %s), %s, %s) or \'\'' % (   # set empties
                self.desc(obj), _r(name), v, kc))     # the result; set the script: its compile errors (x1-04)

    def s_return(self, s, ind):
        self.emit(ind, 'return %s' % self.ex(s[1]))

    def s_exit(self, s, ind):
        if s[1] == 'repeat':
            self.emit(ind, 'break' if self.loops else 'raise ExitRepeat()')
        else:
            self.emit(ind, "return ''")

    def s_next(self, s, ind):
        self.emit(ind, 'continue' if self.loops else 'raise NextRepeat()')

    def s_pass(self, s, ind):
        self.emit(ind, 'raise Pass()')                 # the message goes on along the message path

    def s_break(self, s, ind):
        if self.in_switch:
            self.in_switch[-1] = True
        self.emit(ind, 'raise Break()')

    def s_throw(self, s, ind):
        self.emit(ind, 'raise Thrown(to_text(%s))' % self.ex(s[1]))

    def s_sort(self, s, ind):
        _, kind, t, desc, mode, by = s
        v = self.tmp('v')
        self.emit(ind, '%s = to_text(%s)' % (v, self.ex(t)))
        byc = 'None' if by is None else 'lambda: %s' % self.ex(by)
        self.emit(ind, self.assign(t, 'rt.sort_text(fr, %s, %s, %r, %s, %s)' % (_r(kind), v, desc, _r(mode), byc),
                                   'sort' if t[0] == 'obj' else 'into'))

    def s_if(self, s, ind, kw='if'):
        _, cond, then, els = s
        self.emit(ind, '%s to_bool(%s):' % (kw, self.ex(cond)))
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
            self.emit(ind, 'for _ in range(int(to_num(to_text(%s)))):' % self.ex(p))
        elif kind == 'while':
            self.emit(ind, 'while to_bool(%s):' % self.ex(p))
        elif kind == 'until':
            self.emit(ind, 'while not to_bool(%s):' % self.ex(p))
        elif kind == 'with':
            v, a, b, step, down = p
            x, e, st = self.tmp('x'), self.tmp('e'), self.tmp('s')
            self.emit(ind, '%s = to_num(to_text(%s))' % (x, self.ex(a)))
            self.emit(ind, '%s = to_num(to_text(%s))' % (e, self.ex(b)))
            self.emit(ind, '%s = %s' % (st, 'to_num(to_text(%s))' % self.ex(step) if step is not None else ('-1' if down else '1')))
            # a step that points away from the end gives no passes; LiveCode runs one step past the end (LIVECODE_FACTS)
            self.emit(ind, 'while (%s) and %s:' % (('%s < 0' % st) if down else ('%s > 0' % st),
                                                  ('%s > %s + %s' % (x, e, st)) if down else ('%s < %s + %s' % (x, e, st))))
            self.emit(ind + 1, 'rt.setvar(fr, %s, numstr(%s))' % (_r(v), x))
            self.emit(ind + 1, '%s += %s' % (x, st))
        elif kind == 'each':
            ck, v, e = p
            kind2 = ck.rstrip('s') if ck not in ('chars',) else 'char'
            if kind2 == 'element':
                k = self.tmp('k')
                self.emit(ind, 'for %s in rt.elements(%s):' % (k, self.ex(e)))
                self.emit(ind + 1, 'rt.setvar(fr, %s, %s)' % (_r(v), k))
            elif kind2 == 'key':
                k = self.tmp('k')
                self.emit(ind, 'for %s in list(%s):' % (k, self.ex(e)))
                self.emit(ind + 1, 'rt.setvar(fr, %s, %s)' % (_r(v), k))
            else:
                kind2 = {'character': 'char', 'chars': 'char'}.get(ck, kind2)
                t, a, b = self.tmp('t'), self.tmp('a'), self.tmp('b')
                self.emit(ind, '%s = to_text(%s)' % (t, self.ex(e)))
                self.emit(ind, 'for %s, %s in ch.spans(%s, %s, **rt.delims()):' % (a, b, t, _r(kind2)))
                self.emit(ind + 1, 'rt.setvar(fr, %s, %s[%s:%s])' % (_r(v), t, a, b))
        else:
            raise TranslateError('repeat %s' % kind)
        self.loops += 1                  # (a break inside the loop still belongs to the switch around it)
        self.block(body, ind + 1)
        self.loops -= 1

    def s_switch(self, s, ind):
        """the first matching case (else the default) starts; bodies fall through until a break"""
        _, subject, cases, default = s[:4]
        dpos = s[4] if len(s) > 4 else len(cases)
        sv = self.tmp('sv')
        mark = len(self.lines)
        self.emit(ind + 1, '%s = %s' % (sv, 'to_text(%s)' % self.ex(subject) if subject else 'None'))
        self.in_switch.append(False)
        segs = [(vals, body) for vals, body in cases]          # (values or None for the default, body)
        if default is not None:
            segs.insert(dpos, (None, default))
        ends = lambda b: bool(b) and b[-1][0] == 'break'
        # stacked cases (case "a" / case "b" / body) share one body: merge them
        merged, pend = [], []
        for vals, body in segs:
            if vals is not None and not body and merged is not None:
                pend.extend(vals)
                continue
            merged.append((None if vals is None else pend + vals, body) if not (vals is None and pend) else None)
            pend = []
        simple = None not in merged and not pend and all(ends(b) for _, b in merged[:-1]) \
            and all(v is not None for v, _ in merged[:-1])
        if simple:                                            # every case ends in break: if / elif / else
            first = True
            for vals, body in merged:
                body = body[:-1] if ends(body) else body
                if vals is None:
                    if first:
                        self.block(body, ind + 1)
                    else:
                        self.emit(ind + 1, 'else:')
                        self.block(body, ind + 2)
                    continue
                cond = ' or '.join('rt.case_hit(%s, %s)' % (sv, self.ex(v)) for v in vals)
                self.emit(ind + 1, '%s %s:' % ('if' if first else 'elif', cond))
                self.block(body, ind + 2)
                first = False
        else:                                                 # fall-through: find the start, then run on
            go, n = self.tmp('go'), len(segs)
            first = True
            for j, (vals, body) in enumerate(segs):
                if vals is None:
                    continue
                cond = ' or '.join('rt.case_hit(%s, %s)' % (sv, self.ex(v)) for v in vals)
                self.emit(ind + 1, '%s %s:' % ('if' if first else 'elif', cond))
                self.emit(ind + 2, '%s = %d' % (go, j))
                first = False
            start = dpos if default is not None else n
            if first:
                self.emit(ind + 1, '%s = %d' % (go, start))
            else:
                self.emit(ind + 1, 'else:')
                self.emit(ind + 2, '%s = %d' % (go, start))
            for j, (vals, body) in enumerate(segs):
                self.emit(ind + 1, 'if %s <= %d:' % (go, j))
                if ends(body):
                    self.block(body[:-1], ind + 2)
                    self.emit(ind + 2, '%s = %d' % (go, n))    # break: the bodies below do not run
                else:
                    self.block(body, ind + 2)
        catches = self.in_switch.pop()
        body = self.lines[mark:]
        del self.lines[mark:]
        if catches:
            self.emit(ind, 'try:')
            self.lines.extend(body)
            self.emit(ind, 'except Break:')
            self.emit(ind + 1, 'pass')
        else:
            self.lines.extend(l[4:] for l in body)

    def s_try(self, s, ind):
        _, body, var, catch, fin = s
        has_catch = not (var is None and not catch)
        if not has_catch and not fin:
            self.block(body, ind)
            return
        if fin:
            self.emit(ind, 'try:')
            ind += 1
        if has_catch:
            e = self.tmp('e')
            self.emit(ind, 'try:')
            self.block(body, ind + 1)
            self.emit(ind, 'except (Thrown, XtError) as %s:' % e)
            self.emit(ind + 1, 'rt.caught(%s)' % e)
            if var:
                self.emit(ind + 1, 'rt.setvar(fr, %s, %s.v if isinstance(%s, Thrown) else str(%s))' % (_r(var), e, e, e))
            self.block(catch, ind + 1)
        else:
            self.block(body, ind)
        if fin:
            ind -= 1
            self.emit(ind, 'finally:')
            self.block(fin, ind + 1)

    # ---- commands
    def s_cmd(self, s, ind):
        name, parts = s[1], s[2]
        if name == 'select':                   # needs the field and the chunk, not their text: interpreted
            self.emit(ind, 'rt.x_cmd(%r, fr)' % (s,))
            return
        nodes = [p[1] for p in parts if p[0] == 'e']
        words = [None if p[0] == 'e' else p[1] for p in parts]
        generic = 'rt.cmd(fr, %s, [%s], [%s], %s)' % (
            _r(name), ', '.join(self.desc(n) if n[0] == 'obj' or (n[0] == 'var' and n[1].lower() == 'me') else self.ex(n)
                                for n in nodes),
            ', '.join(self.setter(n) if n[0] in ('var', 'idx', 'chunk') else 'None' for n in nodes), _r(words))
        own = getattr(self, 'c_' + name, None)
        if own is None:
            self.emit(ind, generic)
            return
        self.emit(ind, 'if rt.has_handler(%s):' % _r(name))     # the script may define its own `filter`
        self.emit(ind + 1, generic)
        self.emit(ind, 'else:')
        start = len(self.lines)
        own(parts, ind + 1)
        if len(self.lines) == start:
            self.emit(ind + 1, 'pass')

    def c_do(self, parts, ind):
        if not parts or parts[0][0] != 'e':
            raise TranslateError('do without code')
        self.emit(ind, 'rt.do_text(fr, to_text(%s))' % self.ex(parts[0][1]))

    def c_split(self, parts, ind, fn='split_value'):
        try:
            target, mode, d1, d2 = split_form(parts)
        except XtError:
            raise TranslateError(fn[:-6] + ' form')
        ds = ['None' if d is None else 'to_text(%s)' % self.ex(d) for d in (d1, d2)]
        self.emit(ind, self.assign(target, 'rt_%s(%s, %r, %s, %s)' % (fn, self.ex(target), mode, ds[0], ds[1]), 'into'))

    def c_combine(self, parts, ind):
        self.c_split(parts, ind, 'combine_value')

    def c_filter(self, parts, ind):
        i, kind = 0, 'line'
        if parts[0][0] == 'e' and parts[0][1][0] == 'var' and parts[0][1][1].lower() in ('lines', 'items') \
                and len(parts) > 1 and parts[1] == ('w', 'of'):
            kind = parts[0][1][1].lower().rstrip('s')
            i = 2
        try:
            target = parts[i][1]
            rest = parts[i + 1:]
            neg = rest[0] == ('w', 'without')
            regex, after = filter_pattern_parts(rest[1:])
            rest = rest[:1] + after
            pat = rest[1][1]
            dest = rest[3][1] if len(rest) >= 4 and rest[2] == ('w', 'into') else target
        except IndexError:
            raise TranslateError('filter form')
        p, t = self.tmp('p'), self.tmp('t')
        self.emit(ind, '%s = %s' % (p, _tt(self.ex(pat))))
        self.emit(ind, '%s = to_text(%s)' % (t, self.ex(target)))
        self.emit(ind, self.assign(dest, 'rt.filter_text(%s, %s, %s, %r, %r)' % (t, _r(kind), p, neg, regex), 'into'))


def _pyname(name, used):
    base = 'h_' + re.sub(r'\W', '_', name).lower()
    n, i = base, 2
    while n in used:
        n, i = '%s_%d' % (base, i), i + 1
    used.add(n)
    return n


def translate_expr(text):
    """an xTalk expression -> a Python expression (names rt and fr must exist where it runs)"""
    return Gen().ex(parse_expr(text))


def translate_statements(text, fname='_body', fast=False):
    """xTalk statements -> `def fname(rt, fr):` (as if they were a handler's body). fast: the fast mode
    (xtalk/fastgen.py); its variables are copied into fr.vars at the end, so a caller can read them"""
    body = parse_statements(text)
    if fast:
        from .fastgen import FastGen, ScriptInfo, pyname
        unsets = {}
        g = FastGen(ScriptInfo({}, [], {}), fname, [], body, [], unsets)
        g.emit(0, 'def %s(rt, fr):' % fname)
        g.prologue(1)
        g.emit(1, 'try:')
        g.block(body, 2)
        g.emit(1, 'finally:')
        for n in g.locals:
            g.emit(2, 'if type(%s) is not Unset: V[%r] = O(%s)' % (pyname(n), n, pyname(n)))
        head = ['U_%s = Unset(%r)' % (pyname(n)[2:], unsets[n]) for n in sorted(unsets)]
        return '\n'.join(head + g.lines) + '\n'
    g = Gen()
    g.emit(0, 'def %s(rt, fr):' % fname)
    g.block(body, 1)
    g.emit(1, "return ''")
    return '\n'.join(g.lines) + '\n'


def _compiles(src, fn):
    with warnings.catch_warnings():              # `return` inside `finally` is what the xTalk said
        warnings.simplefilter('ignore', SyntaxWarning)
        compile(src, fn, 'exec')


def _fast_handler(info, fn, kind, name, params, body, byref, unsets):
    """the fast mode's Python for one handler (raises TranslateError / NeedFrame when it can't)"""
    from .fastgen import FastGen
    mine = {}
    g = FastGen(info, name, params, body, byref, mine)
    g.emit(0, 'def %s(rt, fr):' % fn)
    g.emit(1, '# %s %s %s  (fast)' % ('function' if kind == 'function' else 'on', name, ', '.join(params)))
    g.prologue(1)
    ind = 1
    if byref:                                    # @ parameters: what they hold at the end goes back
        g.emit(1, 'try:')
        ind = 2
    g.block(body, ind)
    if byref:
        g.emit(1, 'finally:')
        for i in byref:
            if i < len(params):
                g.emit(2, "V[%s] = O(%s)" % (_r(params[i].lower()), 'L_' + re.sub(r'\W', '_', params[i].lower())))
    if not g.lines[-1].startswith('    return '):
        g.emit(1, "return ''")
    src = '\n'.join(g.lines)
    _compiles(src, fn)
    for k, v in mine.items():
        unsets.setdefault(k, v)
    return src


def translate_script(text, source='<script>', fast=False, byref_fns=()):
    """a whole script -> a Python module with install(rt). Returns (python text, report).
    report: {'translated': [names], 'interpreted': [(name, why)], 'parse_errors': [...],
    'plain': [(name, why)] (fast mode: handlers translated the plain way)}.
    fast: handler variables as Python variables and numbers as floats (xtalk/fastgen.py); byref_fns: names of
    functions anywhere on the message path that have @ parameters (a call to one needs the plain way)"""
    p = Parser(text)
    handlers = p.script()
    top = handlers.pop('#top', [])
    parse_errors = handlers.pop('#errors', [])
    sglobals = handlers.pop('#sglobals', {})
    report = {'translated': [], 'interpreted': [], 'parse_errors': parse_errors, 'plain': []}
    used = set()
    out = ['"""Generated from %s by xtalk_py/xtalk/transpile.py. Do not edit: the xTalk script is the source."""' % source,
           'from xtalk.pyrt import *  # noqa: F401,F403', '', '']
    table = []
    unsets = {}
    info = None
    if fast:
        from .fastgen import ScriptInfo
        info = ScriptInfo(handlers, top, sglobals, byref_fns)
    for key, (kind, name, params, body, byref) in handlers.items():
        fn = _pyname(name, used)
        src = None
        if fast:
            try:
                src = _fast_handler(info, fn, kind, name, params, body, byref, unsets)
            except (TranslateError, XtError, SyntaxError, KeyError, IndexError, TypeError) as e:
                report['plain'].append((name, '%s: %s' % (type(e).__name__, e)))
        g = Gen()
        try:
            if src is None:
                g.emit(0, 'def %s(rt, fr):' % fn)
                g.emit(1, '# %s %s %s' % ('function' if kind == 'function' else 'on', name, ', '.join(params)))
                g.block(body, 1)
                if not g.lines[-1].startswith('    return '):
                    g.emit(1, "return ''")
                src = '\n'.join(g.lines)
                _compiles(src, fn)
        except (TranslateError, XtError, SyntaxError, KeyError, IndexError, TypeError) as e:
            report['interpreted'].append((name, '%s: %s' % (type(e).__name__, e)))
            table.append('    rt.handlers[%s] = %s' % (_r(key), _r((kind, name, params, body, byref))))
            continue
        report['translated'].append(name)
        out.append(src)
        out.append('')
        out.append('')
        table.append('    rt.handlers[%s] = (%s, %s, %s, None, %s, %s)' % (
            _r(key), _r(kind), _r(name), _r(list(params)), _r(list(byref)), fn))
    if unsets:
        out[3:3] = ['U_%s = Unset(%s)' % (re.sub(r'\W', '_', n), _r(unsets[n])) for n in sorted(unsets)] + ['', '']
    g = Gen()
    g.emit(0, 'def install(rt):')
    g.emit(1, '"""add these handlers to rt, then run the script-level local/global/constant lines"""')
    g.emit(1, 'fr = Frame([])')
    for line in table:
        g.lines.append(line)
    for key, names in sglobals.items():          # script-level globals declared above each handler
        g.emit(1, 'rt.SG[%s] = %s' % (_r(key), _r(tuple(names))))
    for st in top:
        if st[0] == 'local':
            for n, init in zip(st[1], st[2]):
                g.emit(1, 'rt.S[%s] = %s' % (_r(n.lower()), "to_text(%s)" % g.ex(init) if init is not None else "''"))
        elif st[0] == 'global':
            for n in st[1]:
                g.emit(1, 'rt.G.setdefault(%s, "")' % _r(n.lower()))
        else:
            g.st(st, 1)
    out.extend(g.lines)
    return '\n'.join(out) + '\n', report
