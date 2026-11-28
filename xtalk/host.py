"""The host: what objects (stacks, cards, controls) are. The interpreter only asks the host.

This default host is a plain in-memory registry so scripts run without any GUI. The stack runtime
(Phase 2, raylib + ImGui) will provide a real one with the same methods.
Objects are named by descriptor text: 'button "OK" of card "Main"'.
"""
import fnmatch, os, re
from .values import XtError


class Host:
    def __init__(self):
        self.objs = {}            # descriptor (lower) -> {prop: text}
        self.log = []             # [(command, [values])] of commands the script gave the host
        self.cmd_it = None        # a command's value for `it` (dispatch: handled / unhandled / passed)
        self.current = {'card': 'card "main"', 'stack': 'stack "main"', 'background': 'background "main"'}
        self.files = {}           # path -> text (a tiny in-memory disk; real file access when 'real_files')
        self.real_files = False

    # ---- objects
    def norm(self, d):
        return re.sub(r'\s+', ' ', d.strip().lower())

    def add(self, desc, **props):
        self.objs.setdefault(self.norm(desc), {}).update(props)

    def exists(self, desc):
        return self.norm(desc) in self.objs

    def get_prop(self, desc, prop, key=None):
        o = self.objs.get(self.norm(desc))
        if o is None:
            return ''
        if key is not None:
            return o.get('%s[%s]' % (prop, key), '')
        return o.get(prop, '')

    def set_prop(self, desc, prop, value, key=None):
        o = self.objs.setdefault(self.norm(desc), {})
        o[prop if key is None else '%s[%s]' % (prop, key)] = value

    def select(self, desc, mode, s, e):
        self.log.append(('select', [('e', desc or ''), ('w', mode)]))

    def create(self, typ, name, invisible, group):
        raise XtError("can't find handler create")

    def delete_obj(self, desc):
        raise XtError("delete: can't delete that")

    def dialog(self, kind, sub, icon, prompt, extra, title):
        """no window: answer picks the default (last) button, ask takes its default text"""
        self.log.append((kind, [('e', prompt)]))
        if kind == 'answer' and not sub:
            return (extra[-1] if extra else 'OK'), ''
        if kind == 'ask' and sub != 'file':
            return (extra[0] if extra else ''), ''
        return '', 'cancel'

    def shell(self, command):
        raise XtError("expression: can't find function shell")

    def within(self, desc, point):
        raise XtError("expression: can't find function within")

    def count(self, kind, parent):
        pre = kind.rstrip('s')
        return sum(1 for d in self.objs if d.startswith(pre + ' ') and (not parent or d.endswith(self.norm(parent))))

    # ---- commands the interpreter doesn't know (go, show, lock, answer...)
    def command(self, name, parts):
        self.log.append((name, parts))
        return ''

    def special_folder(self, name):
        """specialFolderPath(name): none in the plain in-memory host"""
        return ''

    # ---- files and urls
    def read_url(self, kind, ref):
        path = ref[5:] if ref.lower().startswith('file:') else ref
        if path in self.files:
            return self.files[path]
        if self.real_files and os.path.exists(path):
            return open(path, encoding='utf-8', errors='replace').read()
        return ''

    def write_url(self, kind, ref, text):
        path = ref[5:] if ref.lower().startswith('file:') else ref
        self.files[path] = text
        if self.real_files:
            open(path, 'w', encoding='utf-8').write(text)


def wildcard(pattern, regex=False):
    """LiveCode filter patterns: * ? and [..] matching the whole line; `regex pattern`: a regular expression found
    anywhere in the line. Both follow the caseSensitive (measured 27 Nov: false = "b" keeps "ABD")."""
    from .values import CASE
    flags = re.S if CASE[0] else re.I | re.S
    if regex:
        r = re.compile(pattern, flags)
        return type('Search', (), {'match': staticmethod(lambda t: r.search(t))})
    return re.compile(fnmatch.translate(pattern), flags)


FILTER_WORDS = ('regex', 'wildcard', 'pattern')


def filter_pattern_parts(rest):
    """filter X with [regex|wildcard] [pattern] P: the parser reads those words as variables; -> (regex?, the parts
    from P on)"""
    regex = False
    rest = list(rest)
    while len(rest) > 1 and rest[0][0] == 'e' and rest[0][1][0] == 'var' and rest[0][1][1].lower() in FILTER_WORDS \
            and rest[1][0] == 'e':
        regex = regex or rest[0][1][1].lower() == 'regex'
        rest.pop(0)
    return regex, rest
