"""Tokenizer and parser: xTalk text -> tuples (a small AST).

Expressions   ('str',s) ('num',s) ('var',name) ('const',name) ('call',name,args) ('bin',op,l,r)
              ('un',op,e) ('chunk',kind,a,b,inner) ('count',kind,e) ('prop',name) ('idx',base,keys)
Statements    see Parser.statement
"""
import re
from .values import XtError

CHUNKS = {'char': 'char', 'chars': 'char', 'character': 'char', 'characters': 'char',
          'byte': 'char', 'bytes': 'char',
          'word': 'word', 'words': 'word', 'item': 'item', 'items': 'item', 'line': 'line', 'lines': 'line'}
ORDINALS = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5, 'sixth': 6, 'seventh': 7,
            'eighth': 8, 'ninth': 9, 'tenth': 10, 'last': -1, 'middle': 0, 'any': 0}
OBJTYPES = {'button', 'btn', 'field', 'fld', 'graphic', 'grc', 'image', 'img', 'group', 'grp', 'card', 'cd',
            'stack', 'background', 'bkgnd', 'bg', 'player', 'scrollbar', 'widget', 'control', 'audioclip',
            'videoclip', 'menu', 'sprite'}
OBJPLURAL = {'buttons', 'fields', 'graphics', 'images', 'groups', 'cards', 'controls', 'players', 'stacks',
             'scrollbars', 'widgets', 'backgrounds'}
PREPS = {'to', 'in', 'of', 'with', 'into', 'from', 'by', 'at', 'for', 'after', 'before', 'as', 'on', 'without',
         'using', 'where', 'and', 'or', 'seconds', 'second', 'milliseconds', 'millisecond', 'ticks', 'tick'}
KNOWN_PROPS = {'width', 'height', 'left', 'right', 'top', 'bottom', 'loc', 'location', 'rect', 'name', 'id', 'label',
               'text', 'visible', 'style', 'topleft', 'bottomright', 'script', 'hilite', 'enabled', 'number',
               'foregroundcolor', 'backgroundcolor', 'selectedline', 'imagedata', 'rotation', 'opaque'}
PROP_ADJ = {'short', 'long', 'abbreviated', 'abbrev', 'effective', 'default', 'system', 'internet'}
CONSTANTS = {'empty', 'true', 'false', 'space', 'comma', 'return', 'cr', 'lf', 'quote', 'tab', 'pi',
             'colon', 'slash', 'backslash', 'newline', 'null', 'zero', 'one', 'two', 'three', 'four',
             'five', 'six', 'seven', 'eight', 'nine', 'ten', 'formfeed'}
TOKEN = re.compile(r'''
    (?P<ws>[ \t\r]+)
  | (?P<cont>\\[ \t\r]*\n)
  | (?P<block>/\*.*?\*/)
  | (?P<comment>(--|\#|//)[^\n]*)
  | (?P<nl>\n)
  | (?P<str>"[^"\n]*")
  | (?P<num>(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?)
  | (?P<id>[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*)
  | (?P<op><=|>=|<>|&&|[&+\-*/^=<>(),\[\]])
  | (?P<other>.)
''', re.X | re.S)

def tokenize(text):
    toks, pos, line = [], 0, 1
    text = text.replace('\r\n', '\n')
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise XtError('line %d: unexpected character %r' % (line, text[pos]))
        k = m.lastgroup
        s = m.group(k)
        if k in ('cont', 'block'):
            line += s.count('\n')
        elif k == 'nl':
            toks.append(('nl', '\n', line))
            line += 1
        elif k == 'str':
            toks.append(('str', s[1:-1], line))
        elif k == 'other':
            toks.append(('op', s, line))
        elif k not in ('ws', 'comment'):
            toks.append((k, s, line))
        pos = m.end()
    toks.append(('nl', '\n', line))
    toks.append(('eof', '', line))
    return toks


class Parser:
    def __init__(self, text):
        self.t = tokenize(text)
        self.i = 0
        self.no_prop = 0

    # ---- token helpers
    def peek(self, o=0):
        return self.t[min(self.i + o, len(self.t) - 1)]

    def is_word(self, w, o=0):
        k, s, _ = self.peek(o)
        return k == 'id' and s.lower() == w

    def is_op(self, op, o=0):
        k, s, _ = self.peek(o)
        return k == 'op' and s == op

    def next(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def accept_word(self, *ws):
        for w in ws:
            if self.is_word(w):
                self.i += 1
                return w
        return None

    def expect_word(self, w):
        if not self.accept_word(w):
            self.err('expected "%s"' % w)

    def accept_op(self, op):
        if self.is_op(op):
            self.i += 1
            return True
        return False

    def expect_op(self, op):
        if not self.accept_op(op):
            self.err('expected "%s"' % op)

    def err(self, msg):
        k, s, line = self.peek()
        raise XtError('line %d: %s (at %r)' % (line, msg, s))

    def skip_nl(self):
        while self.peek()[0] == 'nl':
            self.i += 1

    def end_stmt(self):
        if self.peek()[0] not in ('nl', 'eof'):
            self.err('unexpected word')
        self.skip_nl()

    # ---- script
    def script(self):
        handlers, top, errors = {}, [], []
        self.skip_nl()
        while self.peek()[0] != 'eof':
            start = self.i
            try:
                self.one_item(handlers, top)
            except XtError as e:                  # a handler that doesn't parse costs that handler only
                errors.append(str(e))
                self.i = max(self.i, start + 1)
                while self.peek()[0] != 'eof' and not (self.peek()[0] == 'nl' and self.peek(1)[0] == 'id'
                                                       and self.peek(1)[1].lower() in ('on', 'command', 'function', 'private', 'getprop', 'setprop')):
                    self.i += 1
                self.skip_nl()
        if top:
            handlers['#top'] = top
        if errors:
            handlers['#errors'] = errors
        return handlers

    def one_item(self, handlers, top):
        if True:
            if self.is_word('script') and self.peek(1)[0] == 'str':
                while self.peek()[0] != 'nl':
                    self.i += 1
                self.skip_nl()
                return
            if self.is_word('global') or self.is_word('local') or self.is_word('constant'):
                top.append(self.statement())
                self.skip_nl()
                return
            private = self.accept_word('private')
            kind = (self.accept_word('on', 'command', 'function', 'getprop', 'setprop'))
            if not kind:
                self.err('expected a handler (on, command, function)')
            name = self.next()[1]
            params, byref = [], []
            while self.peek()[0] != 'nl':
                k, s, _ = self.next()
                if k == 'op' and s == '@':
                    byref.append(len(params))        # the next name is passed by reference
                elif k == 'id':
                    params.append(s)
            self.skip_nl()
            body = self.block(('end',))
            self.expect_word('end')
            self.next()                        # the handler name
            self.skip_nl()
            kind = 'function' if kind == 'function' else 'command'
            handlers[name.lower()] = (kind, name, params, body, byref)

    def block(self, stops):
        """statements until a line starting with one of the stop words"""
        out = []
        self.skip_nl()
        while not (self.peek()[0] == 'id' and self.peek()[1].lower() in stops) and self.peek()[0] != 'eof':
            out.append(self.statement())
            self.skip_nl()
        return out

    def statements(self, text_stmt=None):
        out = self.block(())
        return out

    # ---- statements
    def statement(self):
        k, s, line = self.peek()
        if k != 'id':
            self.err('expected a command')
        w = s.lower()
        m = getattr(self, 'st_' + w, None)
        if m and w not in ('end',):
            self.i += 1
            r = m()
            if w not in ('if', 'repeat', 'switch', 'try'):
                self.end_stmt()
            return r
        self.i += 1
        r = ('cmd', w, self.cmd_parts())
        self.end_stmt()
        return r

    def cmd_parts(self):
        """the rest of a line as words and expressions: used for the script's own commands and the
        engine's (go, send, show, lock...). ('w', word) or ('e', expr)"""
        parts = []
        while self.peek()[0] not in ('nl', 'eof') and not self.is_word('else'):
            k, s, _ = self.peek()
            if k == 'id' and s.lower() in PREPS:
                parts.append(('w', s.lower()))
                self.i += 1
            elif k == 'op' and s == ',':
                parts.append(('w', ','))
                self.i += 1
            elif self.starts_expr():
                parts.append(('e', self.expr()))
            else:
                parts.append(('w', s.lower()))
                self.i += 1
        return parts

    def one_stmt(self):
        """a single statement on the same line (after then / else)"""
        r = self.statement_noend()
        return r

    def statement_noend(self):
        k, s, line = self.peek()
        w = s.lower()
        m = getattr(self, 'st_' + w, None)
        if m and k == 'id':
            self.i += 1
            return m()
        self.i += 1
        return ('cmd', w, self.cmd_parts())

    def list_expr(self):
        e = self.expr()
        if self.is_op(','):
            es = [e]
            while self.accept_op(','):
                es.append(self.expr())
            return ('join', es)
        return e

    def st_put(self):
        e = self.list_expr()
        for w in ('into', 'after', 'before'):
            if self.accept_word(w):
                return ('put', e, w, self.expr())
        return ('print', e)

    def st_get(self):
        return ('put', self.expr(), 'into', ('var', 'it'))

    def st_add(self):
        e = self.expr()
        self.expect_word('to')
        return ('arith', 'add', e, self.expr())

    def st_subtract(self):
        e = self.expr()
        self.expect_word('from')
        return ('arith', 'subtract', e, self.expr())

    def st_multiply(self):
        t = self.expr()
        self.expect_word('by')
        return ('arith', 'multiply', self.expr(), t)

    def st_divide(self):
        t = self.expr()
        self.expect_word('by')
        return ('arith', 'divide', self.expr(), t)

    def st_delete(self):
        self.accept_word('variable')
        return ('delete', self.expr())

    def st_replace(self):
        a = self.expr()
        self.expect_word('with')
        b = self.expr()
        self.expect_word('in')
        return ('replace', a, b, self.expr())

    def st_set(self):
        self.accept_word('the')
        words = []
        while self.peek()[0] == 'id' and not self.is_word('of') and not self.is_word('to') and len(words) < 3:
            words.append(self.next()[1].lower())
        if not words:
            self.err('expected a property name')
        key = None
        if self.is_op('['):
            self.i += 1
            key = self.expr()
            self.expect_op(']')
        obj = None
        if self.accept_word('of'):
            self.accept_word('of')                       # LiveCode lets a doubled "of of" through
            obj = self.p_un()
        self.expect_word('to')
        return ('setprop', ' '.join(words), obj, key, self.list_expr())

    def st_return(self):
        if self.peek()[0] in ('nl', 'eof'):
            return ('return', ('str', ''))
        return ('return', self.list_expr())

    def st_global(self):
        names = [self.next()[1]]
        while self.accept_op(','):
            names.append(self.next()[1])
        return ('global', names)

    def st_local(self):
        names, inits = [], []
        while True:
            names.append(self.next()[1])
            inits.append(self.expr() if self.accept_op('=') else None)
            if not self.accept_op(','):
                break
        return ('local', names, inits)

    def st_constant(self):
        name = self.next()[1]
        self.expect_op('=')
        return ('constant', name, self.expr())

    def st_exit(self):
        w = self.next()[1].lower()
        if w == 'to':
            self.next()
        return ('exit', w)

    def st_next(self):
        self.expect_word('repeat')
        return ('next',)

    def st_pass(self):
        return ('pass', self.next()[1])

    def st_break(self):
        return ('break',)

    def st_throw(self):
        return ('throw', self.expr())

    def st_sort(self):
        kind = 'line'
        if self.peek()[0] == 'id' and self.peek()[1].lower() in CHUNKS:
            kind = CHUNKS[self.next()[1].lower()]
            self.accept_word('of')
        target = self.expr()
        desc, mode, by = False, 'text', None
        while True:
            if self.accept_word('descending'):
                desc = True
            elif self.accept_word('ascending'):
                desc = False
            elif self.accept_word('numeric'):
                mode = 'numeric'
            elif self.accept_word('text', 'international'):
                mode = 'text'
            elif self.accept_word('by'):
                by = self.expr()
            else:
                break
        return ('sort', kind, target, desc, mode, by)

    def st_if(self):
        cond = self.expr()
        self.accept_word('then')
        return self.if_rest(cond)

    def if_rest(self, cond):
        if self.peek()[0] == 'nl':                         # block form
            then = self.block(('else', 'end'))
            els = []
            if self.accept_word('else'):
                if self.is_word('if'):
                    self.i += 1
                    c2 = self.expr()
                    self.accept_word('then')
                    els = [self.if_rest(c2)]
                    return ('if', cond, then, els)
                if self.peek()[0] == 'nl':
                    els = self.block(('end',))
                else:
                    els = [self.one_stmt()]
                    self.skip_nl()
            self.expect_word('end')
            self.expect_word('if')
            return ('if', cond, then, els)
        then = [self.one_stmt()]                            # one-line form
        save = self.i
        self.skip_nl()
        if self.accept_word('else'):
            if self.peek()[0] == 'nl':
                els = self.block(('end',))
                self.expect_word('end')
                self.expect_word('if')
            else:
                els = [self.one_stmt()]
            return ('if', cond, then, els)
        self.i = save
        return ('if', cond, then, [])

    def st_repeat(self):
        kind, params = 'forever', None
        if self.accept_word('forever') or self.peek()[0] == 'nl':
            pass
        elif self.accept_word('while'):
            kind, params = 'while', self.expr()
        elif self.accept_word('until'):
            kind, params = 'until', self.expr()
        elif self.accept_word('with'):
            v = self.next()[1]
            self.expect_op('=')
            a = self.expr()
            down = False
            if self.accept_word('down'):
                down = True
            self.expect_word('to')
            b = self.expr()
            step = None
            if self.accept_word('step'):
                step = self.expr()
            kind, params = 'with', (v, a, b, step, down)
        elif self.accept_word('for'):
            if self.accept_word('each'):
                ck = self.next()[1].lower()
                v = self.next()[1]
                self.expect_word('in')
                kind, params = 'each', (ck, v, self.expr())
            else:
                kind, params = 'times', self.expr()
                self.accept_word('times')
        else:
            kind, params = 'times', self.expr()
            self.accept_word('times')
        body = self.block(('end',))
        self.expect_word('end')
        self.expect_word('repeat')
        return ('repeat', kind, params, body)

    def st_switch(self):
        subject = None if self.peek()[0] == 'nl' else self.expr()
        self.skip_nl()
        cases, default = [], None
        while self.is_word('case') or self.is_word('default'):
            if self.accept_word('case'):
                vals = [self.expr()]
                while self.accept_op(','):
                    vals.append(self.expr())
                cases.append((vals, self.block(('case', 'default', 'end'))))
            else:
                self.i += 1
                default = self.block(('case', 'default', 'end'))
        self.expect_word('end')
        self.expect_word('switch')
        return ('switch', subject, cases, default)

    def st_try(self):
        body = self.block(('catch', 'finally', 'end'))
        var, catch, fin = None, [], []
        if self.accept_word('catch'):
            var = self.next()[1]
            catch = self.block(('finally', 'end'))
        if self.accept_word('finally'):
            fin = self.block(('end',))
        self.expect_word('end')
        self.expect_word('try')
        return ('try', body, var, catch, fin)

    # ---- expressions (precedence, lowest first)
    def expr(self):
        return self.p_or()

    def p_or(self):
        l = self.p_and()
        while self.accept_word('or'):
            l = ('bin', 'or', l, self.p_and())
        return l

    def p_and(self):
        l = self.p_eq()
        while self.accept_word('and'):
            l = ('bin', 'and', l, self.p_eq())
        return l

    def p_eq(self):
        l = self.p_rel()
        while True:
            if self.accept_op('='):
                l = ('bin', '=', l, self.p_rel())
            elif self.accept_op('<>'):
                l = ('bin', '<>', l, self.p_rel())
            elif self.is_word('is') and not (self.is_word('in', 1) or self.is_word('among', 1) or self.is_word('within', 1)
                                             or (self.is_word('not', 1) and self.is_word('within', 2))
                                             or self.is_word('a', 1) or self.is_word('an', 1)
                                             or (self.is_word('not', 1) and (self.is_word('in', 2) or self.is_word('among', 2)
                                                                             or self.is_word('a', 2) or self.is_word('an', 2)))):
                self.i += 1
                op = '<>' if self.accept_word('not') else '='
                l = ('bin', op, l, self.p_rel())
            else:
                return l

    def p_rel(self):
        l = self.p_cat()
        while True:
            for op in ('<=', '>=', '<', '>'):
                if self.accept_op(op):
                    l = ('bin', op, l, self.p_cat())
                    break
            else:
                if self.accept_word('contains'):
                    l = ('bin', 'contains', l, self.p_cat())
                elif self.is_word('begins') and self.is_word('with', 1):
                    self.i += 2
                    l = ('bin', 'begins', l, self.p_cat())
                elif self.is_word('ends') and self.is_word('with', 1):
                    self.i += 2
                    l = ('bin', 'ends', l, self.p_cat())
                elif self.is_word('is') and (self.is_word('within', 1) or (self.is_word('not', 1) and self.is_word('within', 2))):
                    self.i += 1
                    neg = bool(self.accept_word('not'))
                    self.i += 1
                    e = ('bin', 'within', l, self.p_cat())
                    l = ('un', 'not', e) if neg else e
                elif self.is_word('is') and (self.is_word('in', 1) or self.is_word('among', 1)
                                             or self.is_word('a', 1) or self.is_word('an', 1)
                                             or (self.is_word('not', 1) and (self.is_word('in', 2) or self.is_word('among', 2)
                                                                             or self.is_word('a', 2) or self.is_word('an', 2)))):
                    self.i += 1
                    neg = bool(self.accept_word('not'))
                    w = self.next()[1].lower()
                    if w == 'in':
                        e = ('bin', 'in', l, self.p_cat())
                    elif w == 'among':
                        self.accept_word('the')
                        which = self.accept_word('items', 'lines', 'words', 'chars') or 'items'
                        self.accept_word('of')
                        e = ('bin', 'among' if which == 'items' else 'among_' + which, l, self.p_cat())
                    else:                                    # is a number / integer / ...
                        e = ('isa', l, self.next()[1].lower())
                    l = ('un', 'not', e) if neg else e
                else:
                    return l

    def p_cat(self):
        l = self.p_add()
        while True:
            if self.accept_op('&&'):
                l = ('bin', '&&', l, self.p_add())
            elif self.accept_op('&'):
                l = ('bin', '&', l, self.p_add())
            else:
                return l

    def p_add(self):
        l = self.p_mul()
        while True:
            if self.accept_op('+'):
                l = ('bin', '+', l, self.p_mul())
            elif self.accept_op('-'):
                l = ('bin', '-', l, self.p_mul())
            else:
                return l

    def p_mul(self):
        l = self.p_un()
        while True:
            if self.accept_op('*'):
                l = ('bin', '*', l, self.p_un())
            elif self.accept_op('/'):
                l = ('bin', '/', l, self.p_un())
            elif self.accept_word('div'):
                l = ('bin', 'div', l, self.p_un())
            elif self.accept_word('mod'):
                l = ('bin', 'mod', l, self.p_un())
            else:
                return l

    def p_un(self):
        if self.accept_word('not'):
            return ('un', 'not', self.p_un())
        return self.p_pow()

    def p_pow(self):
        sign = None
        if self.is_op('-') or self.is_op('+'):
            sign = self.next()[1]
        l = self.primary()
        if sign:
            l = ('un', sign, l)
        if self.accept_op('^'):
            return ('bin', '^', l, self.p_pow())
        return l

    def starts_expr(self, o=0):
        k, s, _ = self.peek(o)
        if k in ('num', 'str'):
            return True
        if k == 'op':
            return s in ('(', '-', '+')
        if k == 'id':
            return s.lower() not in ('to', 'of', 'into', 'after', 'before', 'then', 'else', 'with', 'by',
                                     'from', 'in', 'and', 'or', 'is', 'step', 'times', 'for', 'down', 'mod', 'div')
        return False

    def primary(self):
        k, s, line = self.next()
        if k == 'num':
            return self.postfix(('num', s))
        if k == 'str':
            return ('str', s)
        if k == 'op' and s == '(':
            e = self.expr()
            if self.is_op(','):
                es = [e]
                while self.accept_op(','):
                    es.append(self.expr())
                e = ('join', es)
            self.expect_op(')')
            return e
        if k != 'id':
            self.i -= 1
            self.err('expected a value')
        w = s.lower()
        if w == 'the':
            return self.the_form()
        if w == 'number' and self.is_word('of'):
            self.i -= 1
            return self.the_form()
        if w in PROP_ADJ and self.peek()[0] == 'id' and self.is_word('of', 1):
            name = w + ' ' + self.next()[1].lower()
            self.i += 1
            return ('propof', name, self.p_un(), None)
        if w in ('url', 'file', 'binfile') and (self.peek()[0] == 'str' or (self.peek()[0] == 'id' and not self.is_word('into') and not self.is_word('is') and not self.is_word('and'))):
            return ('url', w, self.primary())
        if w == 'there' and self.is_word('is'):
            self.i += 1
            neg = bool(self.accept_word('not'))
            self.accept_word('a', 'an')
            return ('exists', self.obj_ref(), neg)
        if (w in OBJTYPES or (w == 'this' and self.peek()[0] == 'id' and self.peek()[1].lower() in OBJTYPES)) \
                and self.obj_follows(w):
            self.i -= 1
            return self.obj_ref()
        if w in ('keys', 'length', 'abs', 'sqrt', 'trunc', 'round', 'toupper', 'tolower', 'average', 'sum') \
                and self.is_word('of'):
            self.i += 1
            return ('call', w, [self.p_un()])
        if self.is_word('of') and w not in CHUNKS and w not in ORDINALS and w not in CONSTANTS \
                and not self.no_prop and (self.obj_starts(1) or w in KNOWN_PROPS):
            self.i += 1                                    # a property named without "the": width of this stack
            return ('propof', w, self.p_un(), None)
        if w in ORDINALS and self.peek()[0] == 'id' and self.peek()[1].lower() in CHUNKS:
            return self.chunk_rest(CHUNKS[self.next()[1].lower()], ('num', str(ORDINALS[w])) if ORDINALS[w] else ('ord', w), None)
        if w in CHUNKS and self.starts_expr() and not self.is_op('('):
            kind = CHUNKS[w]
            self.no_prop += 1
            a = self.p_add_nochunk_end()
            self.no_prop -= 1
            b = None
            if self.accept_word('to'):
                self.no_prop += 1
                b = self.p_add_nochunk_end()
                self.no_prop -= 1
            return self.chunk_rest(kind, a, b)
        if w in CHUNKS and self.is_op('('):
            kind = CHUNKS[w]
            a = self.p_add_nochunk_end()
            b = None
            if self.accept_word('to'):
                b = self.p_add_nochunk_end()
            return self.chunk_rest(kind, a, b)
        if self.is_op('('):
            self.i += 1
            args = []
            if not self.is_op(')'):
                args.append(('str', '') if self.is_op(',') else self.expr())
                while self.accept_op(','):
                    args.append(('str', '') if (self.is_op(',') or self.is_op(')')) else self.expr())
            self.expect_op(')')
            return ('call', s, args)
        if w in CONSTANTS:
            return ('const', w)
        return self.postfix(('var', s))

    def p_add_nochunk_end(self):
        return self.p_add()

    def chunk_rest(self, kind, a, b):
        if not self.accept_word('of'):
            if not (self.is_word('the') or (self.peek()[0] == 'id' and self.is_word('of', 1))):
                self.err('expected "of"')
        inner = self.p_un() if not self.is_word('the') else self.p_un()
        return ('chunk', kind, a, b, inner)

    def obj_follows(self, w):
        """is the word just read the start of an object reference (button "x", this card)?"""
        if w == 'this':
            return True
        k, s, _ = self.peek()
        return k in ('num', 'str') or (k == 'op' and s == '(') or (k == 'id' and s.lower() not in PREPS
                                                                   and s.lower() not in ('then', 'else', 'is', 'mod', 'div'))

    def obj_starts(self, o=0):
        k, s, _ = self.peek(o)
        if k != 'id':
            return False
        w = s.lower()
        return w in OBJTYPES or w == 'me' or (w == 'this' and self.peek(o + 1)[0] == 'id' and self.peek(o + 1)[1].lower() in OBJTYPES)

    def obj_ref(self):
        k, s, _ = self.next()
        w = s.lower()
        if w == 'this':
            typ = self.next()[1].lower()
            ref = ('this',)
        else:
            typ = w
            if self.accept_word('id'):
                ref = ('id', self.primary())
            else:
                ref = self.primary()
        parent = None
        if self.is_word('of'):
            if self.is_word('this', 1) or (self.peek(1)[0] == 'id' and self.peek(1)[1].lower() in OBJTYPES):
                self.i += 1
                parent = self.obj_ref()
            elif self.peek(1)[0] in ('id', 'str') and not self.is_word('the', 1) \
                    and self.peek(1)[1].lower() not in CHUNKS and self.peek(1)[1].lower() not in ORDINALS:
                self.i += 1                                  # control J of tCardID: the card is a value
                parent = ('expr', self.primary())
        return ('obj', typ, ref, parent)

    def postfix(self, base):
        if self.is_op('[') and base[0] == 'var':
            keys = []
            while self.accept_op('['):
                keys.append(self.expr())
                while self.accept_op(','):
                    keys.append(('str', ','))
                    keys.append(self.expr())
                self.expect_op(']')
            return ('idx', base[1], keys)
        return base

    def the_form(self):
        k, s, _ = self.peek()
        w = s.lower() if k == 'id' else ''
        if w == 'current' and self.peek(1)[0] == 'id' and self.peek(1)[1].lower() in OBJTYPES:
            self.i += 1
            return ('obj', self.next()[1].lower(), ('this',), None)
        if w in PROP_ADJ and self.peek(1)[0] == 'id' and not self.is_word('of', 1) and not self.is_word('of', 2):
            self.i += 2
            return ('prop', w + ' ' + self.t[self.i - 1][1].lower())
        if w == 'number' and self.is_word('of', 1):
            self.i += 2
            ck = self.peek()[1].lower()
            if not (ck in CHUNKS or ck in ('elements', 'keys', 'bytes', 'byte') or ck in OBJPLURAL):
                return ('propof', 'number', self.p_un(), None)
            self.i += 1
            if ck in CHUNKS:
                self.expect_word_in('in', 'of')
                return ('count', CHUNKS[ck], self.p_un())
            if ck in ('elements', 'keys'):
                self.expect_word_in('in', 'of')
                return ('call', 'the number of elements', [self.p_un()])
            if ck in ('bytes', 'byte'):
                self.expect_word_in('in', 'of')
                return ('count', 'char', self.p_un())
            if ck in OBJPLURAL:
                self.expect_word_in('in', 'of')
                return ('countobj', ck, self.p_un())
            self.err('unknown "the number of"')
        if w in ORDINALS and self.peek(1)[0] == 'id' and self.peek(1)[1].lower() in OBJTYPES:
            self.i += 1
            return ('obj', self.next()[1].lower(), ('ord', w), None)
        if w in ORDINALS and self.peek(1)[0] == 'id' and self.peek(1)[1].lower() in CHUNKS:
            self.i += 1
            kind = CHUNKS[self.next()[1].lower()]
            return self.chunk_rest(kind, ('num', str(ORDINALS[w])) if ORDINALS[w] else ('ord', w), None)
        # the [short|long|effective ...] <property> [of <object or value>]
        j = 0
        while self.peek(j)[0] == 'id' and self.peek(j)[1].lower() in PROP_ADJ and self.peek(j + 1)[0] == 'id':
            j += 1
        if self.peek(j)[0] == 'id' and not self.is_word('of', j):
            j += 1
        else:
            j = 0
        if j and self.is_word('of', j):
            words = [self.peek(n)[1].lower() for n in range(j)]
            self.i += j + 1
            self.accept_word('of')
            return ('propof', ' '.join(words), self.p_un(), None)
        self.i += 1
        key = None
        if self.is_op('['):
            self.i += 1
            key = self.expr()
            self.expect_op(']')
            if self.accept_word('of'):
                return ('propof', w, self.p_un(), key)
        return ('prop', w)

    def expect_word_in(self, *ws):
        if not self.accept_word(*ws):
            self.err('expected in/of')


def parse_script(text):
    return Parser(text).script()

def parse_expr(text):
    p = Parser(text)
    e = p.expr()
    if p.peek()[0] not in ('nl', 'eof'):
        p.err('extra words after the expression')
    return e

def parse_statements(text):
    p = Parser(text)
    return p.block(())
