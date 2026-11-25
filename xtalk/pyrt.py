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
