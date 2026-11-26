"""Chunk expressions: char, word, item, line (and read/write them)."""
from .values import XtError

WS = ' \t\n\r'

_CACHE = {}          # (text, kind, delimiter) -> spans, for long texts read again and again (a game's map)


def spans(text, kind, item_delim=',', line_delim='\n'):
    """[(start, end)] of every chunk of this kind in text (do not change the list: it may be shared)"""
    if kind == 'char':
        return [(i, i + 1) for i in range(len(text))]
    if len(text) < 200:
        return _spans(text, kind, item_delim, line_delim)
    key = (text, kind, item_delim if kind == 'item' else line_delim if kind == 'line' else '')
    r = _CACHE.get(key)
    if r is None:
        if len(_CACHE) > 64:
            _CACHE.clear()
        r = _CACHE[key] = _spans(text, kind, item_delim, line_delim)
    return r


def _spans(text, kind, item_delim, line_delim):
    if kind == 'word':
        out, i, n = [], 0, len(text)
        while i < n:
            while i < n and text[i] in WS:
                i += 1
            if i >= n:
                break
            j = i
            while j < n and text[j] not in WS:
                j += 1
            out.append((i, j))
            i = j
        return out
    d = item_delim if kind == 'item' else line_delim
    if text == '':
        return []
    out, i = [], 0
    while True:
        j = text.find(d, i)
        if j < 0:
            out.append((i, len(text)))
            break
        out.append((i, j))
        i = j + len(d)
    if len(out) > 1 and out[-1][0] == len(text):   # one trailing delimiter starts no new item/line (measured 25 Nov)
        out.pop()
    return out

def count(text, kind, **k):
    return len(spans(text, kind, **k))

def _range(n, a, b):
    """1-based, negatives from the end -> (first, last) 0-based inclusive, or None"""
    if a < 0:
        a = n + 1 + a
    if b < 0:
        b = n + 1 + b
    if a < 1:
        a = 1
    if b > n:
        b = n
    if a > b or n == 0:
        return None
    return a - 1, b - 1

def get(text, kind, a, b=None, **k):
    if kind == 'char' and (b is None or b == a) and a >= 1:     # char n: no list of every char
        return text[a - 1:a]
    sp = spans(text, kind, **k)
    r = _range(len(sp), a, a if b is None else b)
    if r is None:
        return ''
    return text[sp[r[0]][0]:sp[r[1]][1]]

def put(text, kind, a, b, new, mode='into', **k):
    """text with chunk a..b replaced by / given new before / after"""
    b = a if b is None else b
    sp = spans(text, kind, **k)
    n = len(sp)
    d = {'item': k.get('item_delim', ','), 'line': k.get('line_delim', '\n'), 'word': ' ', 'char': ''}[kind]
    if a > 0 and a > n:                      # beyond the end: pad (a trailing delimiter counts as one)
        pad = d * (a - n - (1 if d and text.endswith(d) else 0)) if n else d * (a - 1)
        return text + pad + new
    r = _range(n, a, b)
    if r is None:
        raise XtError("chunk: can't find that chunk")
    s, e = sp[r[0]][0], sp[r[1]][1]
    if mode == 'into':
        return text[:s] + new + text[e:]
    if mode == 'after':
        return text[:e] + new + text[e:]
    return text[:s] + new + text[s:]

ORD = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5, 'sixth': 6, 'seventh': 7,
       'eighth': 8, 'ninth': 9, 'tenth': 10, 'last': -1}
