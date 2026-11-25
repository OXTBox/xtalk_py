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


def wildcard(pattern):
    """LiveCode filter patterns: * ? and [..], not case sensitive"""
    return re.compile(fnmatch.translate(pattern), re.I | re.S)
