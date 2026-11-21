"""Tokenizer and parser: xTalk text -> tuples (a small AST).

Expressions   ('str',s) ('num',s) ('var',name) ('const',name) ('call',name,args) ('bin',op,l,r)
              ('un',op,e) ('chunk',kind,a,b,inner) ('count',kind,e) ('prop',name) ('idx',base,keys)
Statements    see Parser.statement
"""
import re
from .values import XtError

CHUNKS = {'char': 'char', 'chars': 'char', 'character': 'char', 'characters': 'char',
          'word': 'word', 'words': 'word', 'item': 'item', 'items': 'item', 'line': 'line', 'lines': 'line'}
ORDINALS = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5, 'sixth': 6, 'seventh': 7,
            'eighth': 8, 'ninth': 9, 'tenth': 10, 'last': -1, 'middle': 0, 'any': 0}
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
  | (?P<id>[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*)
  | (?P<op><=|>=|<>|&&|[&+\-*/^=<>(),\[\]])
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
        handlers = {}
        self.skip_nl()
        while self.peek()[0] != 'eof':
            if self.is_word('global') or self.is_word('local'):
                self.statement()
                continue
            private = self.accept_word('private')
            kind = (self.accept_word('on', 'command', 'function', 'getprop', 'setprop'))
            if not kind:
                self.err('expected a handler (on, command, function)')
            name = self.next()[1]
            params = []
            while self.peek()[0] != 'nl':
                k, s, _ = self.next()
                if k == 'id':
                    params.append(s)
            self.skip_nl()
            body = self.block(('end',))
            self.expect_word('end')
            self.next()                        # the handler name
            self.skip_nl()
            kind = 'function' if kind == 'function' else 'command'
            handlers[name.lower()] = (kind, name, params, body)
        return handlers

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
        # a call to the script's own command
        self.i += 1
        args = []
        if self.peek()[0] not in ('nl', 'eof'):
            args.append(self.expr())
            while self.accept_op(','):
                args.append(self.expr())
        self.end_stmt()
        return ('callcmd', s, args)

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
        args = []
        if self.peek()[0] not in ('nl', 'eof') and not self.is_word('else'):
            args.append(self.expr())
            while self.accept_op(','):
                args.append(self.expr())
        return ('callcmd', s, args)

    def st_put(self):
        e = self.expr()
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
        self.expect_word('the')
        name = self.next()[1]
        self.expect_word('to')
        return ('setprop', name.lower(), self.expr())

    def st_return(self):
        if self.peek()[0] in ('nl', 'eof'):
            return ('return', ('str', ''))
        return ('return', self.expr())

    def st_global(self):
        names = [self.next()[1]]
        while self.accept_op(','):
            names.append(self.next()[1])
        return ('global', names)

    def st_local(self):
        names = [self.next()[1]]
        while self.accept_op(','):
            names.append(self.next()[1])
        return ('local', names)

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
        kind = CHUNKS.get(self.next()[1].lower())
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
        if self.accept_word('forever'):
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
            elif self.is_word('is') and not (self.is_word('in', 1) or self.is_word('among', 1)
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
                        self.accept_word('items')
                        self.accept_word('of')
                        e = ('bin', 'among', l, self.p_cat())
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
            self.expect_op(')')
            return e
        if k != 'id':
            self.i -= 1
            self.err('expected a value')
        w = s.lower()
        if w == 'the':
            return self.the_form()
        if w in ORDINALS and self.peek()[0] == 'id' and self.peek()[1].lower() in CHUNKS:
            return self.chunk_rest(CHUNKS[self.next()[1].lower()], ('num', str(ORDINALS[w])) if ORDINALS[w] else ('ord', w), None)
        if w in CHUNKS and self.starts_expr() and not self.is_op('('):
            kind = CHUNKS[w]
            a = self.p_add_nochunk_end()
            b = None
            if self.accept_word('to'):
                b = self.p_add_nochunk_end()
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
                args.append(self.expr())
                while self.accept_op(','):
                    args.append(self.expr())
            self.expect_op(')')
            return ('call', s, args)
        if w in CONSTANTS:
            return ('const', w)
        return self.postfix(('var', s))

    def p_add_nochunk_end(self):
        return self.p_add()

    def chunk_rest(self, kind, a, b):
        self.expect_word('of')
        inner = self.p_un() if not self.is_word('the') else self.p_un()
        return ('chunk', kind, a, b, inner)

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
        if w == 'number' and self.is_word('of', 1):
            self.i += 2
            ck = self.next()[1].lower()
            if ck in CHUNKS:
                self.expect_word_in('in', 'of')
                return ('count', CHUNKS[ck], self.p_un())
            if ck in ('elements', 'keys'):
                self.expect_word_in('in', 'of')
                return ('call', 'the number of elements', [self.p_un()])
            self.err('unknown "the number of"')
        if w in ORDINALS and self.peek(1)[0] == 'id' and self.peek(1)[1].lower() in CHUNKS:
            self.i += 1
            kind = CHUNKS[self.next()[1].lower()]
            return self.chunk_rest(kind, ('num', str(ORDINALS[w])) if ORDINALS[w] else ('ord', w), None)
        self.i += 1
        if self.is_word('of'):
            self.i += 1
            return ('call', w, [self.p_un()])
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
