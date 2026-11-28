"""xtalk.session - one stack or game kept open, hidden, answering steps (x1-12; the base of x1-14's MCP pack).

    s = Session('Thrmnlra')                 a game in LIB_GAMES/Vibecode3D_Games (through the xt3d test bench host)
    s = Session('~/projects/XTJSON/Foo')    a harvest folder (manifest.json)
    s.step('type `hello')                   -> (ok, answer text)
    s.close()

Steps (one line each, the first word says what):
    click OBJECT | click X,Y        a click (mouseDown, mouseUp)
    type TEXT                       typed the way a window does, one key a frame (\\b Backspace, \\n Return, \\t Tab)
    key K                           one key pressed for a frame and let go (K = a character, a key code, or a name:
                                    space return backspace tab escape left right up down shift control alt)
    hold K / release K              a key held down from now on (the keysDown) / let go
    frames N                        N frames (the game runs; timers and send ... in run)
    eval EXPR                       the value, as the card's script sees it, every global visible
    run STATEMENTS                  statements run as a script of the card (;; or a new line between them)
    snap FILE.png                   the window as a picture
    stats                           a game's stats line (xbGameStats)
    errors                          the script errors so far

One Session a process: raylib has one window a process, and some interpreter settings are shared. Many at once =
many processes (tools/xtpy.py, the x1-14 MCP pack); each gets its own folder under run_files/xtpy/, where the
stack's writes go too (never the owner's real files, GAME_NOTES.txt included).
Needs the .venv (raylib) for frames, snap and games; a harvest opens without it (frames then only run timers).
"""
import json, os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = os.path.expanduser('~/projects/LIB_GAMES/Vibecode3D_Games')
BRIDGE = os.path.expanduser('~/projects/xt3D_Raylib_Livecode_Bridge')
HOST = os.path.join(BRIDGE, 'testbench', 'xt3d_testBench_lib_mcp.livecodescript')
UNESCAPE = (('\\b', '\b'), ('\\n', '\n'), ('\\t', '\t'))


def make_stack(folder, w, h):
    """the xt3d testbench host (script-only) as a one-card harvest in folder (tools/xt3d_game_check.py, bench_xt3d)"""
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(os.path.join(folder, 'scripts'))
    shutil.copy(HOST, os.path.join(folder, 'scripts', 'host__stack.livecodescript'))
    stack = {'type': 'stack', 'name': 'xt3dTestBenchLibMCP', 'id': 1001, 'role': 'main', 'rect': [0, 0, w, h],
             'size': [w, h], 'effective': {'textFont': 'Segoe UI', 'textSize': 12},
             'script': {'file': 'scripts/host__stack.livecodescript'},
             'cards': [{'type': 'card', 'name': '', 'id': 1002, 'number': 1, 'controls': []}]}
    json.dump(stack, open(os.path.join(folder, 'stack_host.json'), 'w'), indent=1)
    json.dump({'format': 'livecode-harvest', 'formatVersion': 2, 'mainStack': 'xt3dTestBenchLibMCP',
               'note': 'made by xtalk/session.py: the xt3d testbench host (script-only) as a stack',
               'stacks': [{'name': 'xt3dTestBenchLibMCP', 'role': 'main', 'file': 'stack_host.json', 'cards': 1,
                           'controls': 0}], 'typeDefaults': {}, 'errors': []},
              open(os.path.join(folder, 'manifest.json'), 'w'), indent=1)


def is_game(target):
    return os.path.isfile(os.path.join(GAMES, 'Vibecode3D_Play_%s.livecodescript' % target))


KEY_CHARS = {'space': ' ', 'return': '\n', 'enter': '\n', 'backspace': '\b', 'tab': '\t'}
KEY_CODES = {'escape': 65307, 'left': 65361, 'up': 65362, 'right': 65363, 'down': 65364, 'shift': 65505,
             'control': 65507, 'alt': 65513}


def key_code(k):
    """a key as the View sends it: a character (letters lower case), a name (space, left, escape...) or a number"""
    if k in (' ', '\t', '\n', '\b'):
        return {' ': 32, '\t': 65289, '\n': 65293, '\b': 65288}[k]
    k = k.strip()
    if k.lower() in KEY_CHARS:
        return key_code(KEY_CHARS[k.lower()])
    if k.lower() in KEY_CODES:
        return KEY_CODES[k.lower()]
    if len(k) == 1:
        return ord(k.lower())
    return int(k)


class Session:
    def __init__(self, target, size=(720, 540), window=True, keep=False):
        from .interp import Interp
        from .stack import StackRuntime
        self.target, self.keep = target, keep
        self.folder = os.path.join(ROOT, 'run_files', 'xtpy', '%d' % os.getpid())
        if os.path.isdir(self.folder):
            shutil.rmtree(self.folder)
        files = os.path.join(self.folder, 'files')
        os.makedirs(files)
        Interp.CATCH_LOG = []
        self.game = is_game(target)
        if self.game:
            stack = os.path.join(self.folder, 'stack')
            w, h = size
            make_stack(stack, w, h)
            self.rt = StackRuntime(stack, files_dir=files, real_folders=True)
            self.rt.harvest.main.filename = HOST     # the host finds LIB_GAMES above its own file
            self.rt.G['gxbviewrect'] = '0,0,%d,%d' % (w, h)
        else:
            path = os.path.expanduser(target)
            if not os.path.isfile(os.path.join(path, 'manifest.json')):
                alt = os.path.join(os.path.expanduser('~/projects/XTJSON'), target)
                if os.path.isfile(os.path.join(alt, 'manifest.json')):
                    path = alt
                else:
                    raise ValueError('not a game in LIB_GAMES/Vibecode3D_Games nor a harvest folder: %s' % target)
            self.rt = StackRuntime(path, files_dir=files)
        self.rt.log_clicks = []
        self.view = None
        if window:
            try:
                from .stack.view import View
                self.view = View(self.rt, hidden=True)
            except ImportError:                      # no raylib (python3 -I without the .venv): no frames drawn
                self.view = None
        self.rt.open()
        self.card = self.rt.default_stack.children[0] if self.game else self.rt.default_stack.current
        if self.game:
            self.rt.message(self.card, 'xbPlayGame', [target])
        self.seen_errors = 0
        self.held = []

    # ------------------------------------------------------------ steps
    def frames(self, n=1):
        for _ in range(int(n)):
            if self.view is not None:
                self.view.frame()
            else:
                self.rt.tick(16)

    def ctx(self):
        rt = self.rt
        c = rt.ctx.get(id(rt.default_stack.current)) or rt.ctx.get(id(self.card))
        if c is None:
            from .stack.runtime import ObjInterp
            c = ObjInterp(rt, rt.default_stack.current)
        return c

    def eval(self, expr):
        from .parser import parse_expr
        from .interp import Frame
        fr = Frame([])
        fr.globals.update(self.rt.G.keys())          # every global the stack made is visible
        return str(self.ctx().ev(parse_expr(expr), fr))

    def step(self, line):
        """one step -> (ok, answer). ok is False when the step failed or a script error came during it"""
        verb, _, arg = line.strip().partition(' ')
        verb = verb.lower()
        rt = self.rt
        try:
            if verb == 'click':
                o = rt.click(arg.strip())
                self.frames(1)
                answer = 'clicked %s' % (getattr(o, 'name', '') or arg.strip())
            elif verb == 'type':
                for a, b in UNESCAPE:
                    arg = arg.replace(a, b)
                for ch in arg:
                    rt.type_char(ch)
                    self.frames(1)
                answer = 'typed %d keys' % len(arg)
            elif verb == 'key':
                code = key_code(arg)
                ch = KEY_CHARS.get(arg.strip().lower(), arg.strip())
                rt.test_keys = list(rt.test_keys) + [code]
                if len(ch) == 1:
                    rt.type_char(ch)             # rawKeyDown, then keyDown (or Backspace...) unless it was taken
                else:
                    rt.raw_key(code)
                self.frames(1)
                rt.test_keys = [k for k in rt.test_keys if k != code]
                self.frames(1)
                answer = 'key %d' % code
            elif verb == 'hold':
                code = key_code(arg)
                rt.test_keys = list(rt.test_keys) + [code]
                rt.raw_key(code)
                answer = 'holding %d' % code
            elif verb == 'release':
                code = key_code(arg)
                rt.test_keys = [k for k in rt.test_keys if k != code]
                answer = 'let go %d' % code
            elif verb == 'frames':
                self.frames(int(arg or 1))
                answer = '%s frames' % (arg or 1)
            elif verb == 'eval':
                answer = self.eval(arg)
            elif verb == 'run':
                self.ctx().run(arg.replace(';;', '\n'))
                answer = 'ran'
            elif verb == 'snap':
                if self.view is None:
                    return False, 'snap needs the .venv (raylib)'
                path = os.path.abspath(os.path.expanduser(arg.strip() or os.path.join(self.folder, 'snap.png')))
                self.view.snapshot(path)
                answer = 'saved %s' % path
            elif verb == 'stats':
                answer = str(rt.ctx[id(rt.harvest.main)].invoke('xbGameStats', [])) if self.game else 'not a game'
            elif verb == 'errors':
                answer = '\n'.join(' '.join(str(x) for x in e) for e in rt.errors) or 'none'
            else:
                return False, 'unknown step %r (click type key hold release frames eval run snap stats errors)' % verb
        except Exception as e:                       # noqa: BLE001  a step that fails says why; the session goes on
            return False, '%s: %s' % (type(e).__name__, e)
        new = rt.errors[self.seen_errors:]
        self.seen_errors = len(rt.errors)
        if new and verb != 'errors':
            answer += '\n' + '\n'.join('script error: ' + ' '.join(str(x) for x in e) for e in new)
            return False, answer
        return True, answer

    def close(self):
        if self.game:
            try:
                self.rt.message(self.card, 'xbStopGame')
            except Exception:                        # noqa: BLE001
                pass
        if self.view is not None:
            self.view.close()
            self.view = None
        if not self.keep:
            shutil.rmtree(self.folder, ignore_errors=True)
