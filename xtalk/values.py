"""Values: everything is text. Numbers are text that looks like a number."""
import math, re

class XtError(Exception):
    pass

_NUM = re.compile(r'^\s*[+-]?(\d+\.?\d*([eE][+-]?\d+)?|\.\d+([eE][+-]?\d+)?)\s*$')

def is_number(s):
    return isinstance(s, str) and bool(_NUM.match(s)) or (isinstance(s, str) and s.strip() == '' and False)

class NumStr(str):
    """the text of a number that still remembers its full-precision value: LiveCode rounds a
    number to numberFormat only when it is stored (put ... into x), not between operators"""
    raw = 0.0

    def __copy__(self):                # never changed in place: a copy can be itself (arrays copy fast)
        return self

    def __deepcopy__(self, memo):
        return self

def numstr(n):
    if isinstance(n, bool):
        return 'true' if n else 'false'
    r = NumStr(fmt_num(n))
    r.raw = float(n)
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
