"""Values: everything is text. Numbers are text that looks like a number."""
import math, re

class XtError(Exception):
    pass

_NUM = re.compile(r'^\s*[+-]?(\d+\.?\d*([eE][+-]?\d+)?|\.\d+([eE][+-]?\d+)?)\s*$')

def is_number(s):
    return isinstance(s, str) and bool(_NUM.match(s)) or (isinstance(s, str) and s.strip() == '' and False)

_MISS = object()
CASE = [False]                         # the caseSensitive (the Interp keeps it in step; per handler)


class XtArray(dict):
    """an xTalk array: a key finds its element whatever its case while the caseSensitive is false (measured
    25 Nov: a["x"] finds the element put as a["X"]; putting a["name"] after a["Name"] changes that element and
    the keys still say Name; with caseSensitive true they are two elements). Keys keep their first spelling."""
    __slots__ = ('lk',)

    def __init__(self, *a, **k):
        dict.__init__(self, *a, **k)
        self.lk = None                     # lower-case key -> the key as stored (made when first needed)

    def _real(self, k):
        if dict.__contains__(self, k) or CASE[0] or type(k) is not str:
            return k
        lk = self.lk
        if lk is None:
            lk = self.lk = {}
            for x in dict.keys(self):
                if type(x) is str:
                    lk.setdefault(x.lower(), x)
        return lk.get(k.lower(), k)

    def __getitem__(self, k):
        try:
            return dict.__getitem__(self, k)       # the exact key: the usual case, no index needed
        except KeyError:
            return dict.__getitem__(self, self._real(k))

    def get(self, k, d=None):
        v = dict.get(self, k, _MISS)
        if v is not _MISS:
            return v
        return dict.get(self, self._real(k), d)

    def __contains__(self, k):
        return dict.__contains__(self, k) or dict.__contains__(self, self._real(k))

    def __setitem__(self, k, v):
        r = self._real(k)
        if r is k and self.lk is not None and type(k) is str and not dict.__contains__(self, k):
            self.lk.setdefault(k.lower(), k)
        dict.__setitem__(self, r, v)

    def __delitem__(self, k):
        dict.__delitem__(self, self._real(k))
        self.lk = None

    def pop(self, k, *d):
        self.lk = None
        return dict.pop(self, self._real(k), *d)

    def setdefault(self, k, d=None):
        if k in self:
            return self[k]
        self[k] = d
        return d

    def update(self, *a, **k):
        for kk, v in dict(*a, **k).items():
            self[kk] = v

    def clear(self):
        dict.clear(self)
        self.lk = None

    def __copy__(self):
        return XtArray(self)

    def __deepcopy__(self, memo):
        import copy
        n = XtArray()
        for k, v in dict.items(self):
            dict.__setitem__(n, k, copy.deepcopy(v, memo) if isinstance(v, dict) else v)
        return n


class NumStr(str):
    """the text of a number that still remembers its full-precision value: LiveCode rounds a
    number to numberFormat only when it is stored (put ... into x), not between operators"""
    raw = 0.0
    fmt = '0.######'                   # the numberFormat its text was made with

    def __copy__(self):                # never changed in place: a copy can be itself (arrays copy fast)
        return self

    def __deepcopy__(self, memo):
        return self

def numstr(n):
    if isinstance(n, bool):
        return 'true' if n else 'false'
    r = NumStr(fmt_num(n))
    r.raw = float(n)
    r.fmt = NUMBER_FORMAT[0]
    return r

def plain(v):
    """what gets stored: the text, without the memory of the full number"""
    return str.__str__(v) if type(v) is NumStr else v

def to_num(s, what='operand'):
    """text -> int or float; empty is 0, anything else non-numeric is an error"""
    if type(s) is NumStr:
        return s.raw
    if isinstance(s, (int, float)):
        return float(s)
    if not isinstance(s, str):
        raise XtError('expression: bad %s' % what)
    t = s.strip()
    if t == '':
        return 0
    if _NUM.match(t):
        return float(t)
    raise XtError('expression: bad %s' % what)

NUMBER_FORMAT = ['0.######']          # the numberFormat property; the Interp keeps it in step

def fmt_num(n):
    """number -> text the way LiveCode shows it: whole numbers plain, others with the
    decimals of numberFormat (default 0.######: up to 6, trailing zeros dropped)"""
    if isinstance(n, bool):
        return 'true' if n else 'false'
    if n != n:
        return 'nan'
    if isinstance(n, float) and math.isinf(n):
        return 'inf' if n > 0 else '-inf'
    if n == int(n):
        return str(int(n))
    fmt = NUMBER_FORMAT[0]
    dec = len(fmt.split('.')[1]) if '.' in fmt else 0
    s = '%.*f' % (dec, n)
    if '.' in s and '#' in fmt:
        s = s.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s

def to_text(v):
    if isinstance(v, str):
        if type(v) is NumStr and v.fmt != NUMBER_FORMAT[0]:   # numberFormat applies when a number becomes
            return numstr(v.raw)                                 # text (measured 25 Nov), not when computed
        return v
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return numstr(v)
    if isinstance(v, dict):
        raise XtError("expression: can't treat an array as text")
    return str(v)

def to_bool(v):
    """if / not / and / or: only "true" (any case, no spaces) is true; anything else is false,
    with no error (measured 25 Nov: empty, "x", " true", "1", "yes" are all false)"""
    return to_text(v).lower() == 'true'

def is_numeric_text(s):
    return isinstance(s, str) and bool(_NUM.match(s))

_NUMC = {}           # text -> its number (or None): the same texts are compared again and again


def text_num(s):
    """the number a text stands for (a computed number's full value), or None when it is not a number"""
    if type(s) is NumStr:
        return s.raw
    r = _NUMC.get(s, _NUMC)
    if r is _NUMC:
        r = float(s) if _NUM.match(s) else None
        if len(_NUMC) > 20000:
            _NUMC.clear()
        _NUMC[s] = r
    return r


def num_cmp(x, y):
    """-1/0/1 for two numbers, equal within LiveCode's tolerance (measured 25 Nov: about 10 steps of a double
    relative to the bigger one, 2.2e-16 near zero: 1+2e-15 = 1 but not 1+5e-15; 1e-16 = 0 but not 1e-14)"""
    d = x - y
    if d == 0 or abs(d) <= max(2.220446049250313e-15 * max(abs(x), abs(y)), 2.220446049250313e-16):
        return 0
    return 1 if d > 0 else -1


def compare(a, b):
    """-1/0/1 the LiveCode way: numbers as numbers (full value) when both are, else text ignoring case"""
    x = text_num(a)
    if x is not None:
        y = text_num(b)
        if y is not None:
            return num_cmp(x, y)
    x, y = a.lower(), b.lower()
    return (x > y) - (x < y)
