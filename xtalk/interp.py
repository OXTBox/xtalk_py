"""The xTalk interpreter: runs the parser's tuples. Everything is text."""
import os, copy
import math, random, time, base64, re
from . import chunks as ch
from .values import XtError, XtArray, CASE, to_num, fmt_num, numstr, plain, to_text, to_bool, is_numeric_text, compare, NUMBER_FORMAT
from .parser import parse_script, parse_expr, parse_statements, OBJTYPES
from .host import Host, wildcard

CONST = {'empty': '', 'true': 'true', 'false': 'false', 'space': ' ', 'comma': ',', 'return': '\n', 'cr': '\n',
         'lf': '\n', 'newline': '\n', 'quote': '"', 'tab': '\t', 'pi': numstr(math.pi), 'colon': ':',
         'slash': '/', 'backslash': '\\', 'null': '\0', 'formfeed': '\f', 'zero': '0', 'one': '1', 'two': '2',
         'three': '3', 'four': '4', 'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'}


class Return(Exception):
    def __init__(self, v):
        self.v = v

class ExitRepeat(Exception): pass
class NextRepeat(Exception): pass
class ExitHandler(Exception): pass
class Pass(ExitHandler): pass       # `pass msg`: the message goes on along the message path
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
        self.handlers = {}
        self.G = {}                     # global variables
        self.S = {}                     # script-level locals and constants (shared by all handlers)
        self.SG = {}                    # handler name -> the script-level globals declared above it
        self.host = Host()
        self.props = {'itemdelimiter': ',', 'linedelimiter': '\n', 'numberformat': '0.######',
                      'casesensitive': 'false'}
        self.output = []                # what `put x` with no target printed
        self.result = ''
        self.depth = 0
        self.refs = {}
        self.load_errors = []
        if script.strip():
            self.load(script)

    # ------------------------------------------------------------ public
    def load(self, script):
        h = parse_script(script)
        top = h.pop('#top', [])
        self.load_errors = h.pop('#errors', [])
        self.SG.update(h.pop('#sglobals', {}))
        self.handlers.update(h)
        fr = Frame([])
        for st in top:                  # script-level local / global / constant lines
            self.exec_stmt(st, fr, script_level=True)

    def call(self, name, *args):
        return to_text(self.invoke(name, [a if isinstance(a, dict) else to_text(a) for a in args]))

    def eval(self, text, frame=None):
        v = self.ev(parse_expr(text), frame or Frame([]))
        return '' if isinstance(v, dict) else to_text(v)   # LiveCode's eval shows an array as empty

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
    def lookup(self, name):
        """(the script context that has the handler, the handler) or (None, None). One script here;
        the stack runtime walks the message path (control, group, card, stack)"""
        h = self.handlers.get(name.lower())
        return (self, h) if h is not None else (None, None)

    def after_pass(self, name, args):
        """`pass name` ran: what the next object on the message path answers (none here)"""
        return ''

    def invoke(self, name, args):
        owner, h = self.lookup(name)
        if h is None:
            raise XtError("handler: can't find handler %s" % name)
        if owner is not self:                       # the handler lives further along the message path
            r = owner.invoke(name, args)
            self.refs, self.result = owner.refs, owner.result
            return r
        kind, _, params, body, byref = h[:5]
        pyfn = h[5] if len(h) > 5 else None     # a handler the translator turned into Python
        self.refs = {}
        self.depth += 1
        if self.depth > 400:
            self.depth = 0
            raise XtError('handler: stack overflow')
        fr = Frame(args)
        P = self.props                         # itemDel, lineDel, numberFormat belong to the handler: each one
        saved = (P['itemdelimiter'], P['linedelimiter'], P['numberformat'], NUMBER_FORMAT[0],   # starts at the
                 P.get('casesensitive', 'false'), CASE[0])                               # defaults; a change
        P['itemdelimiter'], P['linedelimiter'] = ',', '\n'          # never reaches the caller (caseSensitive too)
        if CASE[0]:
            P['casesensitive'], CASE[0] = 'false', False
        if saved[2] != '0.######' or saved[3] != '0.######':       # or the handlers it calls (measured 25 Nov)
            P['numberformat'] = NUMBER_FORMAT[0] = '0.######'
        pl = {p.lower() for p in params}       # a parameter named like a script global wins (measured 25 Nov)
        fr.globals.update(g for g in self.SG.get(name.lower(), ()) if g not in pl)
        for i, p in enumerate(params):    # full number kept (measured); an array is copied
            a = args[i] if i < len(args) else ''
            fr.vars[p.lower()] = copy.deepcopy(a) if isinstance(a, dict) else a
        try:
            if pyfn is not None:
                return pyfn(self, fr)
            self.exec_block(body, fr)
        except Return as r:
            return r.v               # a returned number keeps its full value (measured 25 Nov)
        except Pass:
            return self.after_pass(name, args)
        except ExitHandler:
            return ''
        finally:
            self.depth -= 1
            self.refs = {i: fr.vars.get(params[i].lower(), '') for i in byref if i < len(params)}
            P['itemdelimiter'], P['linedelimiter'], P['numberformat'], NUMBER_FORMAT[0], P['casesensitive'], CASE[0] = saved
        return ''

    # ------------------------------------------------------------ variables
    def getvar(self, fr, name):
        n = name.lower()
        if n in fr.globals:
            return self.G.get(n, '')
        if n in fr.vars:
            return fr.vars[n]
        if n in self.S:
            return self.S[n]
        return name                      # an unset variable is its own name

    def setvar(self, fr, name, v):
        n = name.lower()
        if n in fr.globals:
            self.G[n] = v
        elif n not in fr.vars and n in self.S:
            self.S[n] = v
        else:
            fr.vars[n] = v

    # ------------------------------------------------------------ statements
    def exec_block(self, body, fr):
        for st in body:
            self.exec_stmt(st, fr)

    def exec_stmt(self, st, fr, script_level=False):
        k = st[0]
        if script_level and k == 'local':
            for n, init in zip(st[1], st[2]):
                self.S[n.lower()] = to_text(self.ev(init, fr)) if init is not None else ''
            return
        try:
            m = self._xm[k]
        except KeyError:
            m = self._xm[k] = getattr(self, 'x_' + k)
        except AttributeError:
            m = getattr(self, 'x_' + k)
            self._xm = {k: m}
        return m(st, fr)

    def x_print(self, st, fr):
        self.output.append(to_text(self.ev(st[1], fr)))

    def x_global(self, st, fr):
        for n in st[1]:
            fr.globals.add(n.lower())
            self.G.setdefault(n.lower(), '')

    def x_local(self, st, fr):
        for n, init in zip(st[1], st[2]):
            fr.vars[n.lower()] = to_text(self.ev(init, fr)) if init is not None else fr.vars.get(n.lower(), '')

    def x_constant(self, st, fr):
        self.S[st[1].lower()] = to_text(self.ev(st[2], fr))

    def x_put(self, st, fr):
        v = self.ev(st[1], fr)
        self.assign(st[3], v, st[2], fr)

    def x_arith(self, st, fr):
        op, e, target = st[1], st[2], st[3]
        a = self.ev(e, fr)
        cur = self.ev(target, fr) if not (target[0] == 'var' and self.undefined(fr, target[1])) else ''
        self.assign(target, self.arith(op, a, cur), 'into', fr)

    def arith(self, op, a, cur):
        """add/subtract/multiply/divide: a is the operand, cur what the target holds"""
        a = to_num(to_text(a))
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
        return numstr(r)

    def undefined(self, fr, name):
        n = name.lower()
        return n not in fr.vars and n not in fr.globals and n not in self.S

    def delete_var(self, fr, name):
        """delete variable / local / global x: a handler variable goes; a script local or a global is
        emptied (measured: `delete local sA` leaves sA empty, not an array)"""
        n = name.lower()
        if n in fr.vars:
            fr.vars.pop(n)
        elif n in fr.globals:
            self.G[n] = ''
        elif n in self.S:
            self.S[n] = ''

    def x_delete(self, st, fr):
        t = st[1]
        if t[0] == 'var':
            self.delete_var(fr, t[1])
            return
        if t[0] == 'idx':
            self.del_idx(fr, t[1], self.key(t[2][:], fr))
            return
        if t[0] == 'chunk':
            kind, a, b, inner = t[1], t[2], t[3], t[4]
            cur = to_text(self.ev(inner, fr))
            a, b = self.range(a, b, fr, kind, cur)
            new = self.cut(cur, kind, a, b)
            self.assign(inner, new, 'keep' if inner[0] == 'obj' else 'into', fr)   # a field keeps its other styles
            return
        if t[0] == 'obj':
            self.host.delete_obj(self.desc(t, fr))
            return
        raise XtError("delete: can't delete that")

    def x_create(self, st, fr):
        _, typ, invisible, name, group = st
        self.do_create(fr, typ, invisible, None if name is None else to_text(self.ev(name, fr)),
                       None if group is None else self.desc(group, fr))

    def do_create(self, fr, typ, invisible, name, group):
        """create: the host makes the object; it = its long id (measured 25 Nov)"""
        self.put_var(fr, 'it', self.host.create(typ, name or '', invisible, group))

    def del_idx(self, fr, name, key):
        arr = self.getvar_arr(fr, name)
        if arr is not None:
            for kk in key[:-1]:
                arr = arr.get(kk, {})
            arr.pop(key[-1], None)

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
            if text[e:e + len(d)] == d:                  # the delimiter after it (also a trailing one:
                e += len(d)                              # delete item 1 of "3," is empty, measured 25 Nov)
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

    ALIAS = {'itemdel': 'itemdelimiter', 'linedel': 'linedelimiter', 'itemdelim': 'itemdelimiter'}

    def x_setprop(self, st, fr):
        _, name, obj, key, ex = st
        v = self.setprop_value(self.ev(ex, fr), obj is not None)
        if obj is None:
            if key is not None and hasattr(self.host, 'set_global_key'):     # set the clipboardData["text"] to x
                self.host.set_global_key(name, to_text(self.ev(key, fr)), to_text(v))
                return
            self.set_global_prop(name, v)
            return
        if obj[0] == 'chunk' and self.chunk_style_prop(name):     # set the textStyle of word 2 of field "F" to "bold"
            r = self.field_chunk(obj, fr)
            if r is not None and hasattr(self.host, 'set_chunk_prop'):
                self.host.set_chunk_prop(r[0], r[1], r[2], name, to_text(v))
                return
        self.host.set_prop(self.desc(obj, fr), self.prop_name(fr, name), v, None if key is None else to_text(self.ev(key, fr)))

    @staticmethod
    def setprop_value(raw, of_object):
        """an object's (custom) property may hold an array; everything else is text"""
        return raw if of_object and isinstance(raw, dict) else to_text(raw)

    def set_global_prop(self, name, v):
        name = self.ALIAS.get(name, name)
        self.props[name] = v
        f = getattr(self.host, 'on_global_prop', None)    # the stack runtime acts on some (screenMouseLoc)
        if f is not None:
            f(name, v)
        if name == 'numberformat':
            NUMBER_FORMAT[0] = v
        if name == 'casesensitive':
            CASE[0] = to_text(v).lower() == 'true'

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
        raise Pass()

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
                self.caught(e)
                if var:
                    self.setvar(fr, var, e.v if isinstance(e, Thrown) else str(e))
                self.exec_block(catch, fr)
        finally:
            self.exec_block(fin, fr)

    CATCH_LOG = None                   # a list: every error a script's try caught goes in (tools, debugging)

    def caught(self, e):
        if Interp.CATCH_LOG is not None:
            import traceback
            where = ['%s%s' % (f.name, (' [' + f.line.strip()[:400] + ']') if f.line and f.name.startswith('h_') else '')
                     for f in traceback.extract_tb(e.__traceback__)][-6:]
            Interp.CATCH_LOG.append('%s (in %s; %s)' % (e.v if isinstance(e, Thrown) else e, getattr(self, 'obj', ''),
                                                        ' > '.join(where)))

    def x_switch(self, st, fr):
        """the first case that matches (else the default) starts; from there every body runs,
        falling through the cases below, until a break (LIVECODE_FACTS)"""
        _, subject, cases, default = st[:4]
        dpos = st[4] if len(st) > 4 else len(cases)
        sv = to_text(self.ev(subject, fr)) if subject else None
        seq = [body for _, body in cases]
        if default is not None:
            seq.insert(dpos, default)
        start = None
        for i, (vals, body) in enumerate(cases):
            if any(self.case_hit(sv, self.ev(v, fr)) for v in vals):
                start = i + (1 if default is not None and dpos <= i else 0)
                break
        if start is None:
            if default is None:
                return
            start = dpos
        try:
            for body in seq[start:]:
                self.exec_block(body, fr)
        except Break:
            pass

    def case_hit(self, sv, x):
        """switch compares as text, ignoring case unless the caseSensitive is true (LIVECODE_FACTS)"""
        if sv is None:
            return to_bool(x)
        t = to_text(x)
        return t == sv if self.props.get('casesensitive') == 'true' else t.lower() == sv.lower()

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
                    self.setvar(fr, v, numstr(x))
                    run()
                    x += s
            elif kind == 'each':
                ck, v, e = p
                kind2 = ck.rstrip('s') if ck not in ('chars',) else 'char'
                if kind2 not in ('key', 'element'):
                    text = to_text(self.ev(e, fr))      # an array can't be text; keys loops read it below
                if kind2 in ('key',):
                    arr = self.ev(e, fr)
                    for key in list(arr):
                        self.setvar(fr, v, key)
                        run()
                elif kind2 == 'element':
                    for val in self.elements(self.ev(e, fr)):
                        self.setvar(fr, v, val)
                        run()
                else:
                    kind2 = {'character': 'char', 'chars': 'char'}.get(ck, kind2)
                    kw = self.delims()
                    for a, b in ch.spans(text, kind2, **kw):
                        self.setvar(fr, v, text[a:b])
                        run()
        except ExitRepeat:
            pass

    @staticmethod
    def elements(arr):
        """repeat for each element: the values of an array (a copy, as LiveCode)"""
        if not isinstance(arr, dict):
            raise XtError("repeat: can't treat text as an array")
        return [copy.deepcopy(x) if isinstance(x, dict) else x for x in list(arr.values())]

    def x_cmd(self, st, fr):
        name, parts = st[1], st[2]
        if self.lookup(name)[1] is not None:
            nodes = [p[1] for p in parts if p[0] == 'e']
            self.check_byref(name, [n[0] for n in nodes])
            r = self.invoke(name, [self.ev(n, fr) for n in nodes])
            self.result = r if isinstance(r, str) else ''
            for i, v in self.refs.items():
                if i < len(nodes) and nodes[i][0] in ('var', 'idx', 'chunk'):
                    self.assign(nodes[i], v, 'into', fr)
            return
        if name.lower() == 'convert' and parts and parts[0][0] == 'e':
            text = [to_text(self.ev(p[1], fr)) if p[0] == 'e' else p[1] for p in parts]
            target = ' '.join(text[text.index('to') + 1:]) if 'to' in text[1:] else ''
            v, self.result = convert_date(text[0], target)
            if v is not None:
                self.assign(parts[0][1], v, 'into', fr)
            return
        x = EXTERNALS.get(name.lower())
        if x is not None:                       # an extension's handler as a command: its value is the result
            self.result = to_text(x(*[self.ev(p[1], fr) for p in parts if p[0] == 'e']))
            return
        m = getattr(self, 'c_' + name, None)
        if m:
            return m(parts, fr)
        vals = [(p[0], to_text(self.arg(p[1], fr)) if p[0] == 'e' else p[1]) for p in parts]
        self.result = to_text(self.host.command(name, vals) or '')

    def check_byref(self, name, kinds):
        """a chunk given to an @ parameter is an error in LiveCode (measured, LIVECODE_FACTS)"""
        for i in self.lookup(name)[1][4]:
            if i < len(kinds) and kinds[i] == 'chunk':
                raise XtError('handler: parameter %d of %s is not a variable' % (i + 1, name))

    def c_do(self, parts, fr):
        code = to_text(self.ev(parts[0][1], fr))
        self.exec_block(parse_statements(code), fr)

    def c_filter(self, parts, fr):
        # filter [lines|items of] <container> with|without <pattern> [into <container>]
        i, kind = 0, 'line'
        if parts[0][0] == 'e' and parts[0][1][0] == 'var' and parts[0][1][1].lower() in ('lines', 'items') \
                and len(parts) > 1 and parts[1] == ('w', 'of'):
            kind = parts[0][1][1].lower().rstrip('s')
            i = 2
        target = parts[i][1]
        rest = parts[i + 1:]
        neg = rest[0] == ('w', 'without')
        pat = wildcard(to_text(self.ev(rest[1][1], fr)))
        dest = rest[3][1] if len(rest) >= 4 and rest[2] == ('w', 'into') else target
        text = to_text(self.ev(target, fr))
        kw = self.delims()
        d = kw['item_delim'] if kind == 'item' else kw['line_delim']
        keep = [text[a:b] for a, b in ch.spans(text, kind, **kw) if bool(pat.match(text[a:b])) != neg]
        self.assign(dest, d.join(keep), 'into', fr)

    def x_dialog(self, st, fr):
        _, kind, sub, icon, prompt, extra, title = st
        self.do_dialog(fr, kind, sub, icon, to_text(self.ev(prompt, fr)),
                       [to_text(self.ev(x, fr)) for x in extra], to_text(self.ev(title, fr)))

    def do_dialog(self, fr, kind, sub, icon, prompt, extra, title):
        """answer / ask (Dictionary): it = the button clicked (answer), the text typed (ask), a path (file);
        on Cancel it is empty and the result is "cancel". The host shows the dialog."""
        it, result = self.host.dialog(kind, sub, icon, prompt, extra, title)
        self.put_var(fr, 'it', it)
        self.result = result

    CHUNK_PROPS = {'textstyle', 'textfont', 'textsize', 'textcolor', 'foregroundcolor', 'forecolor', 'backgroundcolor',
                   'backcolor', 'textshift', 'htmltext'}

    @classmethod
    def chunk_style_prop(cls, name):
        """a property a chunk of a field has of its own (styled text); `effective` ones too"""
        n = name.lower()
        return (n[len('effective '):] if n.startswith('effective ') else n) in cls.CHUNK_PROPS

    def field_chunk(self, node, fr):
        """a chunk of a field (word 1 of line 2 of field "F") -> (the field, first char, end char), offsets into
        the field's text; None when the chunk is not of an object"""
        if node[0] == 'obj':
            desc = self.desc(node, fr)
            return desc, 0, len(to_text(self.host.get_prop(desc, 'text')))
        if node[0] != 'chunk':
            return None
        _, kind, a, b, inner = node
        r = self.field_chunk(inner, fr)
        if r is None:
            return None
        desc, s0, e0 = r
        text = to_text(self.host.get_prop(desc, 'text'))[s0:e0]
        a2, b2 = self.range(a, b, fr, kind, text)
        sp = ch.spans(text, kind, **self.delims())
        rr = ch._range(len(sp), a2, a2 if b is None else b2)
        s, e = (sp[rr[0]][0], sp[rr[1]][1]) if rr else (len(text), len(text))
        return desc, s0 + s, s0 + e

    def c_select(self, parts, fr):
        """select after/before text of field F, select text of F, select char a to b of F, select empty:
        the host puts the caret / selection there (a field) or takes it away"""
        words = [p[1] for p in parts if p[0] == 'w']
        nodes = [p[1] for p in parts if p[0] == 'e']
        if not nodes or nodes[0] == ('const', 'empty'):
            return self.host.select(None, 'none', 0, 0)
        n = nodes[0]
        mode = words[0] if words and words[0] in ('after', 'before') else 'all'
        if n[0] == 'propof' and n[1] == 'text' and n[2][0] == 'obj':
            return self.host.select(self.desc(n[2], fr), mode, 0, 0)
        if n[0] == 'chunk' and n[4][0] == 'obj':
            kind, a, b, inner = n[1], n[2], n[3], n[4]
            desc = self.desc(inner, fr)
            text = to_text(self.ev(inner, fr))
            a2, b2 = self.range(a, b, fr, kind, text)
            sp = ch.spans(text, kind, **self.delims())
            r = ch._range(len(sp), a2, a2 if b is None else b2)
            s, e = (sp[r[0]][0], sp[r[1]][1]) if r else (len(text), len(text))
            return self.host.select(desc, mode, s, e)
        return None                                        # select an object (the edit tool): not done here

    def c_wait(self, parts, fr):
        """wait: the host decides what waiting means (nothing in the plain host)"""
        vals = [(p[0], to_text(self.arg(p[1], fr)) if p[0] == 'e' else p[1]) for p in parts]
        self.host.command('wait', vals)

    def x_sort(self, st, fr):
        _, kind, target, desc, mode, by = st
        text = to_text(self.ev(target, fr))
        self.assign(target, self.sort_text(fr, kind, text, desc, mode, None if by is None else (lambda: self.ev(by, fr))),
                    'sort' if target[0] == 'obj' else 'into', fr)     # a field: each line keeps its styles (measured)

    def sort_text(self, fr, kind, text, desc, mode, by):
        """sort the chunks of text; by() gives the sort key with `each` set"""
        kw = self.delims()
        d = kw['item_delim'] if kind == 'item' else kw['line_delim']
        spans = list(ch.spans(text, kind, **kw))
        parts = [text[a:b] for a, b in spans]
        def key(p):
            if by is not None:
                fr.vars['each'] = p
                p = to_text(by())
            if mode == 'numeric':
                try:
                    return (0, to_num(p))
                except XtError:
                    return (0, 0)
            return (0, p.lower())
        order = sorted(range(len(parts)), key=lambda i: key(parts[i]), reverse=desc)
        self.host.last_sort = (text, spans, order, d)   # for a field: put_text(..., "sort") moves the styles too
        return d.join(parts[i] for i in order)

    # ------------------------------------------------------------ assignment
    def delims(self):
        return {'item_delim': self.props['itemdelimiter'], 'line_delim': self.props['linedelimiter']}

    def getvar_arr(self, fr, name):
        n = name.lower()
        v = (self.G if n in fr.globals else (self.S if n not in fr.vars and n in self.S else fr.vars)).get(n)
        return v if isinstance(v, dict) else None

    def key(self, keys, fr):
        return self.key_vals([self.ev(k, fr) for k in keys])

    @staticmethod
    def key_vals(vals):
        cur = [to_text(v) for v in vals]
        return [''.join(cur)] if len(cur) > 1 and ',' in cur else cur

    def assign(self, target, value, mode, fr):
        k = target[0]
        if k == 'var':
            self.put_var(fr, target[1], value, mode)
            return
        if k == 'idx':
            self.put_idx(fr, target[1], self.key(target[2], fr), value, mode)
            return
        if k == 'chunk':
            _, kind, a, b, inner = target
            cur = to_text(self.ev(inner, fr)) if not (inner[0] == 'var' and self.undefined(fr, inner[1])) else ''
            av = self.chunk_arg(a, fr)
            bv = None if b is None else self.chunk_arg(b, fr)
            # into a chunk of a field: the rest of its styles stay ('keep'); a whole `put into` clears them
            self.assign(inner, self.put_chunk(kind, cur, av, bv, value, mode), 'keep' if inner[0] == 'obj' else 'into', fr)
            return
        if k == 'obj':
            self.put_obj(self.desc(target, fr), value, mode)
            return
        if k == 'propof':
            self.host.set_prop(self.desc(target[2], fr), target[1], to_text(value))
            return
        if k == 'url':
            self.host.write_url(target[1], to_text(self.ev(target[2], fr)), to_text(value))
            return
        raise XtError("put: can't put into that")

    def put_obj(self, desc, value, mode='into'):
        """put into a field (or any object): its text. mode 'keep': the new whole text from a chunk put
        (the host keeps the styles of what did not change)"""
        v = to_text(value)
        if mode != 'into' and hasattr(self.host, 'put_text'):
            self.host.put_text(desc, v, mode)
            return
        if mode in ('keep', 'sort'):
            mode = 'into'
        cur = self.host.get_prop(desc, 'text') if mode != 'into' else ''
        self.host.set_prop(desc, 'text', v if mode == 'into' else (cur + v if mode == 'after' else v + cur))

    def put_var(self, fr, name, value, mode='into'):
        if mode == 'into':                  # LiveCode copies an array on put: no sharing
            self.setvar(fr, name, copy.deepcopy(value) if isinstance(value, dict) else to_text(value))
        else:
            cur = to_text(self.getvar(fr, name)) if not self.undefined(fr, name) else ''
            v = to_text(value)
            self.setvar(fr, name, cur + v if mode == 'after' else v + cur)

    def put_idx(self, fr, name, keys, value, mode='into'):
        n = name.lower()
        store = self.G if n in fr.globals else (self.S if n not in fr.vars and n in self.S else fr.vars)
        arr = store.get(n)
        if not isinstance(arr, dict):
            arr = XtArray()
            store[n] = arr
        for kk in keys[:-1]:
            nxt = arr.get(kk)
            if not isinstance(nxt, dict):
                nxt = XtArray()
                arr[kk] = nxt
            arr = nxt
        last = keys[-1]
        if mode == 'into':
            arr[last] = copy.deepcopy(value) if isinstance(value, dict) else to_text(value)   # full number kept (measured)
        else:
            cur = to_text(arr.get(last, ''))
            arr[last] = cur + to_text(value) if mode == 'after' else to_text(value) + cur

    # chunk positions: a value, or ('ord', 'middle'|'any') that needs the text to resolve
    def chunk_arg(self, e, fr):
        return e if e[0] == 'ord' else self.ev(e, fr)

    def chunk_idx(self, v, kind, text):
        if isinstance(v, tuple):
            n = ch.count(text, kind, **self.delims())
            if v[1] == 'any':
                return random.randint(1, max(n, 1))
            return (n + 1) // 2 if n else 1
        return int(math.floor(to_num(to_text(v))))

    def put_chunk(self, kind, cur, a, b, value, mode):
        """cur with chunk a..b set"""
        a2 = self.chunk_idx(a, kind, cur)
        b2 = a2 if b is None else self.chunk_idx(b, kind, cur)
        return ch.put(cur, kind, a2, b2, to_text(value), mode, **self.delims())

    def cut_chunk(self, kind, cur, a, b):
        a2 = self.chunk_idx(a, kind, cur)
        b2 = a2 if b is None else self.chunk_idx(b, kind, cur)
        return self.cut(cur, kind, a2, b2)

    def get_chunk(self, kind, text, a, b):
        text = to_text(text)
        a2 = self.chunk_idx(a, kind, text)
        b2 = a2 if b is None else self.chunk_idx(b, kind, text)
        return ch.get(text, kind, a2, b2, **self.delims())

    def range(self, a, b, fr, kind=None, text=''):
        av = self.chunk_idx(self.chunk_arg(a, fr), kind, text)
        bv = av if b is None else self.chunk_idx(self.chunk_arg(b, fr), kind, text)
        return av, bv

    # ------------------------------------------------------------ expressions
    def truth(self, v):
        return to_bool(v)

    def ev(self, e, fr):
        try:
            return self._evm[e[0]](e, fr)
        except KeyError:                 # first use of this node kind: look its method up once
            m = self._evm[e[0]] = getattr(self, 'e_' + e[0])
            return m(e, fr)
        except AttributeError:
            self._evm = {}
            return self.ev(e, fr)

    def e_str(self, e, fr):
        return e[1]

    def e_num(self, e, fr):
        return e[1]

    def e_const(self, e, fr):
        return CONST[e[1]]

    def e_var(self, e, fr):
        return self.getvar(fr, e[1])

    def e_propkey(self, e, fr):
        """the clipboardData["text"]: an engine property that is an array"""
        f = getattr(self.host, 'get_global_key', None)
        return f(e[1], to_text(self.ev(e[2], fr))) if f else ''

    def e_prop(self, e, fr):
        n = e[1]
        if n == 'result':
            return self.result
        n = self.ALIAS.get(n, n)                 # the itemDel = the itemDelimiter
        if n in self.props:
            return self.props[n]
        if n in ('seconds',):
            return numstr(int(time.time()))
        if n == 'long seconds':
            return numstr(round(time.time(), 3))
        if n in ('milliseconds', 'millisecs', 'ticks'):
            return numstr(int(time.time() * (60 if n == 'ticks' else 1000)))
        if n == 'paramcount':
            return numstr(len(fr.args))
        d = date_time(n)
        if d is not None:
            return d
        h = self.host.get_prop('', n)
        if h != '' or n in self.MAY_BE_EMPTY:
            return h
        raise XtError('expression: unknown property "the %s"' % n)

    MAY_BE_EMPTY = {'keysdown', 'pendingmessages', 'frontscripts', 'backscripts', 'focusedobject', 'selection', 'selectedtext', 'selectedfield', 'selectedline', 'selectedchunk',
                    'target', 'mousecontrol', 'clicktext', 'clickline', 'clickchunk', 'clickfield', 'foundtext'}

    def e_idx(self, e, fr):
        if self.getvar_arr(fr, e[1]) is None:
            return ''
        return self.get_idx(fr, e[1], self.key(e[2], fr))

    def get_idx(self, fr, name, keys):
        arr = self.getvar_arr(fr, name)
        if arr is None:
            return ''
        cur = arr
        for kk in keys:
            if not isinstance(cur, dict):
                return ''
            cur = cur.get(kk, '')
        return cur

    def e_join(self, e, fr):
        return ','.join(to_text(self.ev(x, fr)) for x in e[1])

    def desc(self, e, fr):
        """text naming an object node"""
        if e[0] == 'var' and e[1].lower() == 'me':     # the X of me: the object (its value may be its text)
            return to_text(self.getvar(fr, e[1]))
        if e[0] == 'obj':
            _, typ, ref, parent = e
            if ref[0] == 'this':
                base = self.host.current.get(typ, '%s "this"' % typ)
            elif ref[0] == 'ord':
                base = '%s %s' % (ref[1], typ)
            elif ref[0] == 'id':
                base = '%s id %s' % (typ, to_text(self.ev(ref[1], fr)))
            else:
                v = to_text(self.ev(ref, fr))
                if typ == 'stack' and v.startswith('stack "') and v.endswith('"'):
                    base = v               # stack (the defaultStack): stack "X" names X (measured 26 Nov)
                else:
                    base = '%s %s' % (typ, v if v.lstrip('-').isdigit() else '"%s"' % v)
            if parent is not None:
                base += ' of ' + (self.desc(parent, fr) if parent[0] == 'obj' else to_text(self.ev(parent[1], fr)))
            return base
        return to_text(self.ev(e, fr))

    CONTAINER_OBJS = ('field', 'fld', 'button', 'btn')

    def obj_value(self, typ, desc):
        """an object used as a value: a field or button is its text (line 1 of field "F", put field "F" into x);
        any other object stands for itself"""
        if typ in self.CONTAINER_OBJS:
            return self.host.get_prop(desc, 'text')
        return desc

    def e_obj(self, e, fr):
        return self.obj_value(e[1], self.desc(e, fr))

    def arg(self, n, fr):
        """a built-in command's argument: an object reference stays the object (hide field "F")"""
        return self.desc(n, fr) if n[0] == 'obj' or (n[0] == 'var' and n[1].lower() == 'me') else self.ev(n, fr)

    def e_exists(self, e, fr):
        ok = self.host.exists(self.desc(e[1], fr))
        return 'true' if ok != e[2] else 'false'

    def e_countobj(self, e, fr):
        return str(self.host.count(e[1], to_text(self.ev(e[2], fr))))

    def e_url(self, e, fr):
        return self.host.read_url(e[1], to_text(self.ev(e[2], fr)))

    ENGINE_PROPS = set('''
        altid angle arcangle armed armborder arrowsize autoarm autohilite backcolor backgroundcolor backpattern
        behavior blendlevel bordercolor borderwidth bottom bottomcolor bottomleft bottomright cantabort cantdelete
        cantmodify cantselect capstyle cardnames centered colors controls custompropertyset custompropertysets
        customkeys customproperties dashes decorations defaultbutton destroystack destroywindow disabled dontresize
        dontsearch dontwrap dropshadow dynamicpaths editmode effective enabled endarrow endvalue fillgradient filled
        fixedlineheight focuscolor forecolor foregroundcolor formattedheight formattedwidth formattedrect frame
        height hgrid hilite hilitecolor hilited hilitedbutton hilitedline hilitedlines hiliteborder hilitefill
        hiliteicon hilitepattern hscroll hscrollbar htmltext icon id imagedata ink label layer left linesize
        lineinc listbehavior location loc lockcursor locklocation lockloc lockscreen locktext long margins
        markerdrawn markerpoints menuhistory menuitems menulines menumode menuname minheight maxheight minwidth
        maxwidth mode multiplehilites name number opaque orientation owner pageinc pattern points polysides
        rect rectangle relativepoints resizable right rotation roundends roundradius scalefactor script
        scrollbarwidth selectedline selectedtext shadow shadowoffset sharedbehavior short showborder showfocusborder
        showicon showname showvalue startangle startarrow startvalue style text textalign textfont textheight
        textsize textstyle thumbposition thumbsize title tooltip top topleft topright traversalon threed
        unicodetext visible vgrid vscroll vscrollbar width wraparound
        '''.split())

    def prop_name(self, fr, name):
        """the tProp of x: a custom property named by a variable's value (measured 25 Nov), when tProp is not
        one of LiveCode's own properties and the variable holds something"""
        if ' ' in name or name in self.ENGINE_PROPS or self.undefined(fr, name):
            return name
        v = self.getvar(fr, name)
        return to_text(v) if not isinstance(v, dict) and to_text(v) != '' else name

    def e_propof(self, e, fr):
        _, name, operand, key = e
        if operand[0] == 'chunk' and self.chunk_style_prop(name) and hasattr(self.host, 'get_chunk_prop'):
            # the textStyle of word 2 of field 1 (the length of word 2 of field 1 stays a function)
            r = self.field_chunk(operand, fr)
            if r is not None:
                return self.host.get_chunk_prop(r[0], r[1], r[2], name)
        name = self.prop_name(fr, name)
        f = BUILTINS.get(name)
        if f is not None and operand[0] not in ('obj',):
            return f(self, fr, self.ev(operand, fr))
        return self.host.get_prop(self.desc(operand, fr), name, None if key is None else to_text(self.ev(key, fr)))

    def e_isa(self, e, fr):
        return self.isa(self.ev(e[1], fr), e[2])

    def isa(self, raw, t):
        if t == 'array':
            return 'true' if isinstance(raw, dict) else 'false'
        if isinstance(raw, dict):
            return 'false'
        v = to_text(raw)
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
        return self.unop(e[1], self.ev(e[2], fr))

    def unop(self, op, v):
        if op == 'not':
            return 'false' if to_bool(v) else 'true'
        n = to_num(to_text(v))
        return numstr(-n if op == '-' else n)

    def e_bin(self, e, fr):
        op = e[1]
        if op == 'and':
            return 'true' if (self.truth(self.ev(e[2], fr)) and self.truth(self.ev(e[3], fr))) else 'false'
        if op == 'or':
            return 'true' if (self.truth(self.ev(e[2], fr)) or self.truth(self.ev(e[3], fr))) else 'false'
        return self.binop(op, self.ev(e[2], fr), self.ev(e[3], fr))

    def binop(self, op, l, r):
        """every two-sided operator but and/or (those stop early)"""
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
        if op.startswith('among'):
            kind = {'among': 'item', 'among_lines': 'line', 'among_words': 'word', 'among_chars': 'char'}[op]
            items = [to_text(r)[a:b] for a, b in ch.spans(to_text(r), kind, **self.delims())]
            return 'true' if any(compare(to_text(l), i) == 0 for i in items) else 'false'
        if op == 'within':
            pt, rc = to_text(l).split(','), to_text(r).split(',')
            try:
                x, y = float(pt[0]), float(pt[1])
                x1, y1, x2, y2 = [float(v) for v in rc[:4]]
            except (ValueError, IndexError):
                raise XtError('expression: bad operand')
            return 'true' if x1 <= x < x2 and y1 <= y < y2 else 'false'
        a, b = to_num(to_text(l)), to_num(to_text(r))
        if op == '+':
            return numstr(a + b)
        if op == '-':
            return numstr(a - b)
        if op == '*':
            return numstr(a * b)
        if op == '/':
            if b == 0:
                raise XtError('expression: divide by zero')
            return numstr(a / b)
        if op == 'div':
            if b == 0:
                raise XtError('expression: divide by zero')
            return numstr(math.trunc(a / b))
        if op == 'mod':
            if b == 0:
                raise XtError('expression: divide by zero')
            return numstr(math.fmod(a, b) if isinstance(a, float) or isinstance(b, float) else a - b * math.trunc(a / b))
        if op == '^':
            try:
                return numstr(float(a) ** b if not (isinstance(a, int) and isinstance(b, int) and b >= 0) else a ** b)
            except (OverflowError, ZeroDivisionError):
                raise XtError('expression: bad operand')
        raise XtError('expression: unknown operator %s' % op)

    def e_call(self, e, fr):
        name = e[1]
        n = name.lower()
        args = [self.ev(a, fr) for a in e[2]]
        if n == 'within' and e[2] and (e[2][0][0] == 'obj' or (e[2][0][0] == 'var' and e[2][0][1].lower() == 'me')):   # within(me, pt): the object
            args[0] = self.desc(e[2][0], fr)
        hf = self.lookup(n)[1]
        if hf is not None and hf[0] == 'function':
            r = self.invoke(name, args)
            for i, v in self.refs.items():
                if i < len(e[2]) and e[2][i][0] in ('var', 'idx'):
                    self.assign(e[2][i], v, 'into', fr)
            return r
        x = EXTERNALS.get(n)
        if x is not None:                                      # xt3d_... (an extension's handler)
            return x(*args)
        f = BUILTINS.get(n)
        if f is None and (not args or n == 'mouse'):          # mouseLoc() is the mouseLoc (measured 25 Nov)
            return self.e_prop(('prop', n), fr)
        if f is None:
            raise XtError("expression: can't find function %s" % name)
        if n == 'matchtext':                                   # captures go into the variables named after the pattern
            m = _re_search(args[1], args[0])
            if m:
                for node, grp in zip(e[2][2:], m.groups()):
                    self.assign(node, grp or '', 'into', fr)
            return 'true' if m else 'false'
        return f(self, fr, *args)


# ------------------------------------------------------------------ builtins
def _n(x):
    return to_num(x)


def _window_pos(it):
    rt = getattr(it.host, 'rt', None)
    return getattr(rt, 'window_pos', (0, 0))


def f_globalloc(it, fr, p):
    """globalLoc(x,y): a card point -> a screen point (the window's place added)"""
    x, y = (int(round(to_num(v))) for v in to_text(p).split(',')[:2])
    wx, wy = _window_pos(it)
    return '%d,%d' % (x + wx, y + wy)


def f_localloc(it, fr, p):
    x, y = (int(round(to_num(v))) for v in to_text(p).split(',')[:2])
    wx, wy = _window_pos(it)
    return '%d,%d' % (x - wx, y - wy)

def _t(x):
    return to_text(x)

def _list(a):
    """min/max/sum/average: several arguments, or one comma list (a trailing comma adds no item,
    an empty item counts as 0: measured 25 Nov)"""
    if len(a) > 1:
        return [_n(x) for x in a]
    t = _t(a[0])
    return [_n(t[i:j]) for i, j in ch.spans(t, 'item')]

def f_round(it, fr, x, places='0'):
    p = int(_n(places))
    return numstr(rnd_half_away(_n(x), p))

def f_min(it, fr, *a):
    return numstr(min(_list(a)))

def f_max(it, fr, *a):
    return numstr(max(_list(a)))

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

def f_value(it, fr, text, obj=None):
    """value(expr) here; value(expr, object): as if in that object's script (its handlers, its path)"""
    if obj is not None and _t(obj) != '' and hasattr(it, 'value_in'):
        return it.value_in(_t(text), _t(obj))
    return it.ev(parse_expr(_t(text)), fr)

def f_random(it, fr, n):
    return str(random.randint(1, int(_n(n))))

def f_numtochar(it, fr, n):
    return chr(int(_n(n)))

def f_chartonum(it, fr, c):
    c = _t(c)
    return str(ord(c[0])) if c else '0'

def f_trunc(it, fr, x):
    return numstr(math.trunc(_n(x)))

def f_matheq(fn):
    return lambda it, fr, *a: numstr(fn(*[float(_n(x)) for x in a]))

def _pcre(p):
    """PCRE (LiveCode) -> Python re: \\z is the very end"""
    return re.sub(r'(?<!\\)\\z', r'\\Z', to_text(p))

def _re_search(pattern, text):
    try:
        return re.search(_pcre(pattern), to_text(text))
    except re.error:
        raise XtError('matchText: bad pattern')

def f_replacetext(it, fr, text, pattern, repl):
    try:
        r = re.sub(r'\\(\d)', r'\\g<\1>', to_text(repl))      # \1 in the replacement
        return re.sub(_pcre(pattern), r, to_text(text))
    except re.error:
        raise XtError('replaceText: bad pattern')

def f_format(it, fr, fmt, *args):
    vals = []
    for a in args:
        t = to_text(a)
        try:
            vals.append(to_num(t) if is_numeric_text(t) else t)
        except XtError:
            vals.append(t)
    conv = re.findall(r'%[-+ 0#]*\d*(?:\.\d+)?([a-zA-Z])', to_text(fmt))
    vals = [int(v) if c in 'dixXoc' and isinstance(v, float) else v for v, c in zip(vals, conv)] + vals[len(conv):]
    try:
        return to_text(fmt) % tuple(vals[:len(conv)])
    except (TypeError, ValueError):
        raise XtError('format: bad format')

def f_baseconvert(it, fr, num, frm, to):
    try:
        n = int(_t(num), int(_n(frm)))
    except ValueError:
        raise XtError('expression: bad operand')
    b = int(_n(to))
    if n == 0:
        return '0'
    digits, out = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', ''
    while n:
        out = digits[n % b] + out
        n //= b
    return out

# handlers of extensions (xt3d: xtalk/xt3d install()s them): lower-case name -> function(*values) -> text.
# Found after the script's own handlers, before the built-in functions and the host's commands.
EXTERNALS = {}

def date_time(n):
    """the date / the time in their forms, as LiveCode 9.6.3 gives them on the owner's Windows (US English),
    measured 25 Nov: 11/25/26 | Wednesday, November 25, 2026 | Wed, Nov 25, 2026 | 5:35 PM | 5:35:01 PM |
    Wed, 25 Nov 2026 17:35:01 -0800 (the internet date). None for any other name."""
    if not (n.endswith('date') or n.endswith('time')) or n not in DATE_FORMS:
        return None
    return date_form(DATE_FORMS[n], time.localtime())


def date_form(f, t):
    """one of DATE_FORMS' values for a time.struct_time"""
    h12 = t.tm_hour % 12 or 12
    ampm = 'AM' if t.tm_hour < 12 else 'PM'
    if f == 'short date':
        return '%d/%d/%02d' % (t.tm_mon, t.tm_mday, t.tm_year % 100)
    if f == 'long date':
        return time.strftime('%A, %B ', t) + '%d, %d' % (t.tm_mday, t.tm_year)
    if f == 'abbr date':
        return time.strftime('%a, %b ', t) + '%d, %d' % (t.tm_mday, t.tm_year)
    if f == 'short time':
        return '%d:%02d %s' % (h12, t.tm_min, ampm)
    if f == 'long time':
        return '%d:%02d:%02d %s' % (h12, t.tm_min, t.tm_sec, ampm)
    return time.strftime('%a, ', t) + '%d ' % t.tm_mday + time.strftime('%b %Y %H:%M:%S %z', t)


DATE_FORMS = {'date': 'short date', 'short date': 'short date', 'long date': 'long date',
              'abbreviated date': 'abbr date', 'abbrev date': 'abbr date', 'abbr date': 'abbr date',
              'time': 'short time', 'short time': 'short time', 'abbreviated time': 'short time',
              'abbrev time': 'short time', 'abbr time': 'short time', 'long time': 'long time',
              'internet date': 'internet date',
              # English = US forms; the system forms are the same on the owner's US-English Windows
              'english date': 'short date', 'short english date': 'short date', 'long english date': 'long date',
              'abbreviated english date': 'abbr date', 'system date': 'short date', 'short system date': 'short date',
              'long system date': 'long date', 'abbreviated system date': 'abbr date', 'english time': 'short time',
              'long english time': 'long time', 'system time': 'short time', 'long system time': 'long time'}


_DATE_IN = [('%m/%d/%y', 'd'), ('%m/%d/%Y', 'd'), ('%A, %B %d, %Y', 'd'), ('%a, %b %d, %Y', 'd'),
            ('%I:%M %p', 't'), ('%I:%M:%S %p', 't'), ('%a, %d %b %Y %H:%M:%S %z', 'dt')]


def convert_date(text, target):
    """convert x to dateItems / seconds / long date / short date and long time ... (measured 25 Nov):
    -> (new text, '') or (None, 'invalid date'). dateItems = year,month,day,hour,minute,second,weekday
    (1 = Sunday) and may overflow (day 40 of November = 10 December); a date alone is midnight, a time
    alone is today."""
    import datetime as _dt
    v = text.strip()
    t = None
    try:
        if is_numeric_text(v):
            t = time.localtime(float(v))
        elif v.count(',') == 6 and all(is_numeric_text(x.strip()) for x in v.split(',')):
            y, mo, d, h, mi, sec = (int(float(x)) for x in v.split(',')[:6])
            t = time.localtime(time.mktime((y, mo, d, h, mi, sec, 0, 0, -1)))
        else:
            today = time.localtime()
            parts = v.rsplit(' ', 2) if ' ' in v else [v]
            cands = [(v, None)] + ([(' '.join(parts[:-2]), ' '.join(parts[-2:]))] if len(parts) == 3 else [])
            for dpart, tpart in cands:
                for fmt, kind in _DATE_IN:
                    try:
                        p = _dt.datetime.strptime(dpart, fmt)
                    except ValueError:
                        continue
                    if kind == 't':
                        p = p.replace(year=today.tm_year, month=today.tm_mon, day=today.tm_mday)
                    if tpart is not None:
                        q = next((_dt.datetime.strptime(tpart, f2) for f2, k2 in _DATE_IN if k2 == 't'
                                  and _try_time(tpart, f2)), None)
                        if q is None:
                            continue
                        p = p.replace(hour=q.hour, minute=q.minute, second=q.second)
                    t = time.localtime(p.timestamp()) if kind == 'dt' else time.localtime(time.mktime(p.timetuple()[:8] + (-1,)))
                    break
                if t is not None:
                    break
    except (ValueError, OverflowError, OSError):
        t = None
    if t is None:
        return None, 'invalid date'
    out = []
    for f in re.split(r'\s+and\s+', target.strip().lower()):
        f = re.sub(r'\s+', ' ', f)
        if f == 'dateitems':
            out.append('%d,%d,%d,%d,%d,%d,%d' % (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec,
                                                 (t.tm_wday + 1) % 7 + 1))
        elif f == 'seconds':
            out.append(str(int(time.mktime(t))))
        elif f in DATE_FORMS:
            out.append(date_form(DATE_FORMS[f], t))
        else:
            raise XtError('convert: unknown format %s' % f)
    return ' '.join(out), ''


def _try_time(s, f):
    import datetime as _dt
    try:
        _dt.datetime.strptime(s, f)
        return True
    except ValueError:
        return False


_ENC = {'utf-8': 'utf-8', 'utf8': 'utf-8', 'utf-16': 'utf-16-le', 'utf16': 'utf-16-le', 'native': 'latin-1',
        'ascii': 'ascii', 'iso-8859-1': 'latin-1', 'macroman': 'mac-roman', 'windows-1252': 'cp1252'}


def f_textdecode(it, fr, x, enc='native'):
    """binary (one char a byte, as binfile: gives) -> text (measured 25 Nov: 6 bytes of UTF-8 -> 5 chars).
    Text that is not one char a byte (a file: read here is already text) comes back as it is."""
    t = _t(x)
    try:
        return t.encode('latin-1').decode(_ENC.get(_t(enc).lower(), 'utf-8'), 'replace')
    except UnicodeEncodeError:
        return t


def f_textencode(it, fr, x, enc='native'):
    """text -> binary, one char a byte (measured: textEncode of h + e-acute in UTF-8 is 3 long)"""
    return _t(x).encode(_ENC.get(_t(enc).lower(), 'utf-8'), 'replace').decode('latin-1')


BUILTINS = {
    'baseconvert': f_baseconvert,
    'textdecode': f_textdecode, 'textencode': f_textencode,
    '$env': lambda it, fr, n: os.environ.get(_t(n), ''),
    'globalloc': f_globalloc,
    'files': lambda it, fr, *a: it.host.list_dir('files', _t(a[0]) if a else None) if hasattr(it.host, 'list_dir') else '',
    'folders': lambda it, fr, *a: it.host.list_dir('folders', _t(a[0]) if a else None) if hasattr(it.host, 'list_dir') else '',
    'localloc': f_localloc,
    'within': lambda it, fr, o, p: it.host.within(_t(o), _t(p)),
    'shell': lambda it, fr, c: it.host.shell(_t(c)),
    'matchtext': lambda it, fr, s_, p_, *r: 'true' if _re_search(p_, s_) else 'false',
    'replacetext': f_replacetext, 'format': f_format,
    'numtocodepoint': lambda it, fr, n: chr(int(_n(n))),
    'codepointtonum': lambda it, fr, c: str(ord(_t(c)[0])) if _t(c) else '0',
    'length': lambda it, fr, x: str(len(_t(x))),
    'round': f_round,
    'abs': lambda it, fr, x: numstr(abs(_n(x))),
    'sqrt': lambda it, fr, x: numstr(math.sqrt(_n(x))) if _n(x) >= 0 else (_ for _ in ()).throw(XtError('expression: bad operand')),
    'trunc': f_trunc,
    'min': f_min, 'max': f_max,
    'sin': f_matheq(math.sin), 'cos': f_matheq(math.cos), 'tan': f_matheq(math.tan),
    'atan': f_matheq(math.atan), 'asin': f_matheq(math.asin), 'acos': f_matheq(math.acos), 'atan2': f_matheq(math.atan2), 'exp': f_matheq(math.exp),
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
    'sum': lambda it, fr, *a: numstr(sum(_list(a))),
    'average': lambda it, fr, *a: numstr(sum(_list(a)) / len(_list(a))),
    'isnumber': lambda it, fr, x: 'true' if is_numeric_text(_t(x)) else 'false',
    'specialfolderpath': lambda it, fr, x: it.host.special_folder(_t(x)),
    'floor': lambda it, fr, x: numstr(math.floor(_n(x))),
    'ceiling': lambda it, fr, x: numstr(math.ceil(_n(x))),
    'exists': lambda it, fr, x: 'true' if it.host.exists(_t(x)) else 'false',
}
