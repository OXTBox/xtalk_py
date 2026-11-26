"""Styled field text: one style per character, read from and written to htmlText. Plain Python, no GUI.

A style is a tuple (flags, face, size, colour, bgcolour, shift, linktext): flags a frozenset of bold /
italic / underline / strikeout / link; face text; size int; colours (r, g, b); shift int (sub/sup); linktext
text. None = not set on the run (the field's own setting shows). A field with no styles has `styles` None.
The rules (tag order, entities, which style new text takes) were measured 26 Nov: docs/LIVECODE_FACTS.md.
"""
import html.entities
from html.parser import HTMLParser

PLAIN = (frozenset(), None, None, None, None, None, None)
FLAG_TAGS = (('italic', 'i'), ('bold', 'b'), ('strikeout', 'strike'), ('underline', 'u'))   # outer to inner
TAG_FLAGS = {'b': 'bold', 'strong': 'bold', 'i': 'italic', 'em': 'italic', 'u': 'underline',
             'strike': 'strikeout', 's': 'strikeout'}
SLOT = {'textstyle': 0, 'textfont': 1, 'textsize': 2, 'textcolor': 3, 'foregroundcolor': 3, 'forecolor': 3,
        'backgroundcolor': 4, 'backcolor': 4, 'textshift': 5, 'linktext': 6}
LINK_COLOUR = (0, 0, 239)      # the effective linkColor of a new stack (measured 26 Nov)

COLOR_NAMES = {'white': (255, 255, 255), 'black': (0, 0, 0), 'red': (255, 0, 0), 'green': (0, 255, 0),
               'blue': (0, 0, 255), 'yellow': (255, 255, 0), 'gray': (190, 190, 190), 'grey': (190, 190, 190),
               'darkgray': (169, 169, 169), 'darkgrey': (169, 169, 169), 'lightgray': (211, 211, 211),
               'lightgrey': (211, 211, 211), 'orange': (255, 165, 0), 'cyan': (0, 255, 255),
               'magenta': (255, 0, 255), 'purple': (160, 32, 240), 'brown': (165, 42, 42), 'pink': (255, 192, 203),
               'navy': (0, 0, 128), 'maroon': (176, 48, 96), 'olive': (128, 128, 0), 'teal': (0, 128, 128),
               'silver': (192, 192, 192), 'gold': (255, 215, 0), 'violet': (238, 130, 238),
               'darkgreen': (0, 100, 0), 'darkblue': (0, 0, 139), 'darkred': (139, 0, 0), 'lime': (0, 255, 0)}


def parse_colour(v):
    """r,g,b / #RRGGBB / a name -> (r, g, b), or None"""
    t = str(v or '').strip().lower()
    if not t:
        return None
    if t.startswith('#') and len(t) == 7:
        try:
            return (int(t[1:3], 16), int(t[3:5], 16), int(t[5:7], 16))
        except ValueError:
            return None
    if ',' in t:
        try:
            p = [int(float(x)) for x in t.split(',')[:3]]
            return tuple(p) if len(p) == 3 else None
        except ValueError:
            return None
    return COLOR_NAMES.get(t.replace(' ', ''))


def flags_of(text):
    """"bold,italic" -> frozenset; plain / empty -> none"""
    out = set()
    for w in str(text).lower().split(','):
        w = w.strip()
        if w in ('bold', 'italic', 'underline', 'strikeout', 'link'):
            out.add(w)
    return frozenset(out)


def flags_text(flags):
    order = ('bold', 'italic', 'underline', 'strikeout', 'link')
    return ','.join(f for f in order if f in flags)


# ---------------------------------------------------------------- reading htmlText
class _Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chars, self.styles = [], []
        self.stack = [PLAIN]           # the style in force; each open tag pushes one
        self.tags = []
        self.paras = 0                 # paragraphs started
        self.in_p = False
        self.after_p = False           # a </p> came: loose text after it is a new paragraph

    def cur(self):
        return self.stack[-1]

    def new_line(self):
        self.chars.append('\n')
        self.styles.append(None)

    def start_para(self):
        if self.paras:
            self.new_line()
        self.paras += 1

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        st = list(self.cur())
        if tag == 'p':
            self.start_para()
            self.in_p = True
            self.after_p = False
            return
        if tag == 'br':
            if not self.paras:
                self.paras = 1
            self.new_line()
            return
        if tag == 'img':
            self.text(' ')
            return
        if tag in TAG_FLAGS:
            st[0] = st[0] | {TAG_FLAGS[tag]}
        elif tag == 'font':
            if a.get('face'):
                st[1] = a['face']
            if a.get('size'):
                try:
                    st[2] = int(float(a['size']))
                except ValueError:
                    pass
            if a.get('color'):
                st[3] = parse_colour(a['color']) or st[3]
            if a.get('bgcolor'):
                st[4] = parse_colour(a['bgcolor']) or st[4]
        elif tag == 'a':               # <a href="x">: a link, linkText x; <a>: a link; <a name="x">: linkText only
            if 'href' in a:            # (measured 26 Nov)
                st[0] = st[0] | {'link'}
                st[6] = a['href'] or None
            elif 'name' in a:
                st[6] = a['name'] or None
            else:
                st[0] = st[0] | {'link'}
        elif tag in ('sub', 'sup'):
            try:
                st[5] = int(a.get('shift', 4 if tag == 'sub' else -4))
            except ValueError:
                st[5] = 4 if tag == 'sub' else -4
        else:
            return                     # span and other tags: ignored (measured)
        self.tags.append(tag)
        self.stack.append(tuple(st))

    def handle_endtag(self, tag):
        if tag == 'p':
            self.in_p = False
            self.after_p = True
            return
        if tag in self.tags:
            while self.tags:
                t = self.tags.pop()
                self.stack.pop()
                if t == tag:
                    break

    def handle_data(self, data):
        if not self.in_p:
            if not data.strip():
                return                 # returns between </p> and <p>
            if self.paras == 0 or self.after_p:
                self.start_para()
        self.after_p = False
        self.text(data.replace('\r', '').replace('\n', ''))

    def text(self, s):
        if not self.paras:
            self.paras = 1
        for c in s:
            self.chars.append(c)
            self.styles.append(self.cur())


def from_html(text):
    """htmlText -> (text, styles); styles None when nothing is styled"""
    r = _Reader()
    r.feed(str(text))
    r.close()
    t = ''.join(r.chars)
    styles = r.styles
    if all(s is None or s == PLAIN for s in styles):
        return t, None
    return t, styles


# ---------------------------------------------------------------- writing htmlText
def _escape(c):
    if c == '&':
        return '&amp;'
    if c == '<':
        return '&lt;'
    if c == '>':
        return '&gt;'
    if c == '\t':
        return '&#9;'
    o = ord(c)
    if o < 128:
        return c
    name = html.entities.codepoint2name.get(o)
    return '&%s;' % name if name else '&#%d;' % o


def _font_tag(st):
    attrs = []
    if st[1]:
        attrs.append('face="%s"' % st[1])
    if st[2]:
        attrs.append('size="%d"' % st[2])
    if st[3]:
        attrs.append('color="#%02X%02X%02X"' % st[3])
    if st[4]:
        attrs.append('bgcolor="#%02X%02X%02X"' % st[4])
    return ('font ' + ' '.join(attrs)) if attrs else None


def _a_tag(st):
    """<a href="x"> (link + linkText) / <a> (link) / <a name="x"> (linkText only): outside the font tag
    (measured 26 Nov: <a href="remove"><font color="#FF8C8C">Remove it</font></a>)"""
    lt = st[6] if len(st) > 6 else None
    if 'link' in st[0]:
        return 'a href="%s"' % lt if lt else 'a'
    return 'a name="%s"' % lt if lt else None


def _wanted(st):
    """the tags a run needs, outer to inner when opened together: a, style tags, sub/sup, then font"""
    a = _a_tag(st)
    out = ([a] if a else []) + [tag for flag, tag in FLAG_TAGS if flag in st[0]]
    if st[5]:
        out.append('%s shift="%d"' % ('sub' if st[5] > 0 else 'sup', st[5]))
    f = _font_tag(st)
    if f:
        out.append(f)
    return out


def to_html(text, styles):
    paras, pos = [], 0
    for line in text.split('\n'):
        out, open_ = [], []
        for i, c in enumerate(line):
            st = (styles[pos + i] if styles and pos + i < len(styles) else None) or PLAIN
            want = _wanted(st)
            k = 0                      # tags already open stay open; new ones open inside them, even inside
            while k < len(open_) and open_[k] in want:       # a font tag (measured: <b>bold <i>bi</i></b>,
                k += 1                                         # nine-ball's <font ..>1) <b>Play</b></font>)
            while len(open_) > k:
                out.append('</%s>' % open_.pop().split(' ')[0])
            for t in [t for t in want if t not in open_]:
                out.append('<%s>' % t)
                open_.append(t)
            out.append(_escape(c))
        while open_:
            out.append('</%s>' % open_.pop().split(' ')[0])
        paras.append('<p>%s</p>' % ''.join(out))
        pos += len(line) + 1
    return '\n'.join(paras)


# ---------------------------------------------------------------- editing
def replace(styles, s, e, new_len, keep_old=True):
    """the text s..e became new_len characters: the new ones take the style of the character before s,
    or of the first character when s is 0 (measured 26 Nov)"""
    if styles is None:
        return None
    src = styles[s - 1] if s > 0 and s - 1 < len(styles) else (styles[0] if styles else None)
    return styles[:s] + [src] * new_len + styles[e:]


def set_range(styles, n, s, e, prop, value):
    """set a style property on characters s..e of an n-character text -> the new styles list"""
    slot = SLOT[prop]
    if styles is None:
        styles = [PLAIN] * n
    if slot == 0:
        v = flags_of(value)
    elif slot in (1, 6):
        v = str(value) or None
    elif slot in (2, 5):
        try:
            v = int(float(value)) if str(value).strip() else None
        except ValueError:
            v = None
    else:
        v = parse_colour(value)
    out = list(styles)
    for i in range(max(0, s), min(e, n)):
        st = list(out[i] or PLAIN)
        st[slot] = v
        out[i] = tuple(st)
    return out


def get_range(styles, text, s, e, prop):
    """a style property of characters s..e: its value, `mixed`, or empty when not set on them"""
    slot = SLOT[prop]
    vals = set()
    for i in range(max(0, s), min(e, len(text))):
        if text[i] == '\n':
            continue
        st = (styles[i] if styles and i < len(styles) else None) or PLAIN
        vals.add(st[slot])
    if not vals:
        return ''
    if len(vals) > 1:
        return 'mixed'
    v = vals.pop()
    if v is None:
        return ''
    if slot == 0:
        return flags_text(v)
    if slot in (3, 4):
        return '%d,%d,%d' % v
    return str(v)


def runs(text, styles, a, b):
    """characters a..b split into (start, end, style) pieces of one style each"""
    out = []
    i = a
    while i < b:
        st = (styles[i] if styles and i < len(styles) else None) or PLAIN
        j = i + 1
        while j < b and ((styles[j] if styles and j < len(styles) else None) or PLAIN) == st:
            j += 1
        out.append((i, j, st))
        i = j
    return out

