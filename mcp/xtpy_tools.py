"""xtpy tool pack (x1-14): the Python runtime as MCP tools, for LIB_MCP's MCP server (and lib_mcp.ask_local).

    python3 ~/projects/LIB_MCP/python/lib_mcp/mcp_server.py --tools ~/projects/xtalk_py/mcp/xtpy_tools.py

Like the oxt-beyond bridge, but hidden: nothing appears on the owner's screen, many stacks may be open at once,
and what a stack writes stays in xtalk_py/run_files/xtpy/ (never the owner's files). Each open stack is its own
`tools/xtpy.py TARGET serve` process (raylib has one window a process). Standard library only (the server runs
on plain python3); the workers run with xtalk_py's .venv.

Tools: xtpy_primer (read first), xtpy_open, xtpy_eval, xtpy_run, xtpy_click, xtpy_type, xtpy_key, xtpy_frames, xtpy_snap, xtpy_step,
xtpy_close, xtpy_list, xtpy_games, xtpy_game (one game played N frames: stats, errors, a picture), xtpy_diff.
"""
import base64, json, os, selectors, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = os.path.join(ROOT, '.venv', 'bin', 'python')
XTPY = os.path.join(ROOT, 'tools', 'xtpy.py')
GAMES = os.path.expanduser('~/projects/LIB_GAMES/Vibecode3D_Games')
MAX_OPEN = 4                 # stacks open at once (each a process with a hidden window)
STEP_TIMEOUT = 180           # seconds for one step (frames 600 of a slow game fits)
_sessions = {}               # id -> {'proc', 'target', 'opened'}
_next = [1]


def _python():
    return VENV if os.path.isfile(VENV) else sys.executable


class _Worker:
    def __init__(self, target, size):
        cmd = [_python(), '-I', XTPY, target, 'serve']
        if size:
            cmd[3:3] = ['--size', size]
        self.proc = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, bufsize=1)

    def read(self, timeout):
        sel = selectors.DefaultSelector()
        sel.register(self.proc.stdout, selectors.EVENT_READ)
        try:
            if not sel.select(timeout):              # a late answer would be read as the next one's: end it
                self.proc.kill()
                return {'ok': False, 'answer': 'no answer in %d s: the stack was stopped; open it again' % timeout}
            line = self.proc.stdout.readline()
        finally:
            sel.close()
        if not line:
            return {'ok': False, 'answer': 'the stack process ended (exit %s)' % self.proc.poll()}
        return json.loads(line)

    def ask(self, step, timeout=STEP_TIMEOUT):
        if self.proc.poll() is not None:
            return {'ok': False, 'answer': 'the stack process has ended; open it again'}
        self.proc.stdin.write(step.replace('\n', '\\n') + '\n')   # one line a step: a Return in typed text as \\n
        self.proc.stdin.flush()
        return self.read(timeout)

    def close(self):
        try:
            self.proc.stdin.write('close\n')
            self.proc.stdin.flush()
            self.proc.wait(20)
        except (OSError, subprocess.TimeoutExpired, ValueError):
            self.proc.kill()


def _session(args):
    sid = str(args.get('session') or '')
    if sid not in _sessions:
        if len(_sessions) == 1 and not sid:
            return next(iter(_sessions.values()))
        raise ValueError('no open stack %r (xtpy_list shows them; xtpy_open opens one)' % sid)
    return _sessions[sid]


def _text(r):
    return ('' if r['ok'] else 'FAILED: ') + r['answer']


def _step(args, step):
    s = _session(args)
    r = s['w'].ask(step)
    if s['w'].proc.poll() is not None:               # stopped (a timeout) or ended: no longer open
        for k, v in list(_sessions.items()):
            if v is s:
                del _sessions[k]
    return _text(r)


def t_open(args):
    target = (args.get('target') or '').strip()
    if not target:
        raise ValueError('target: a game name (xtpy_games lists them) or a harvest folder')
    if len(_sessions) >= MAX_OPEN:
        raise ValueError('%d stacks are open already; xtpy_close one first' % MAX_OPEN)
    w = _Worker(target, args.get('size'))
    r = w.read(STEP_TIMEOUT)
    if not r['ok']:
        w.close()
        return 'FAILED: ' + r['answer']
    sid = str(_next[0])
    _next[0] += 1
    _sessions[sid] = {'w': w, 'target': target, 'opened': time.strftime('%H:%M:%S')}
    return 'session %s: %s is open (hidden). Use session "%s" in the other xtpy tools.' % (sid, target, sid)


def t_close(args):
    sid = str(args.get('session') or '')
    if sid == 'all':
        n = len(_sessions)
        for s in list(_sessions.values()):
            s['w'].close()
        _sessions.clear()
        return 'closed %d' % n
    s = _session(args)
    s['w'].close()
    for k, v in list(_sessions.items()):
        if v is s:
            del _sessions[k]
    return 'closed %s' % s['target']


def t_list(args):
    if not _sessions:
        return 'no stacks open'
    return '\n'.join('session %s: %s (opened %s)%s' % (k, v['target'], v['opened'],
                                                        '' if v['w'].proc.poll() is None else ' ENDED')
                     for k, v in _sessions.items())


def t_primer(args):
    return open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xtpy_primer.md'), encoding='utf-8').read()


def t_games(args):
    names = sorted(f[len('Vibecode3D_Play_'):-len('.livecodescript')] for f in os.listdir(GAMES)
                   if f.startswith('Vibecode3D_Play_') and f.endswith('.livecodescript'))
    return '%d games: %s' % (len(names), ', '.join(names))


def _snap(sess):
    fd, path = tempfile.mkstemp(suffix='.png', prefix='xtpy_snap_')
    os.close(fd)
    r = sess['w'].ask('snap ' + path)
    if not r['ok']:
        return [{'type': 'text', 'text': 'FAILED: ' + r['answer']}]
    data = base64.b64encode(open(path, 'rb').read()).decode()
    os.remove(path)
    return [{'type': 'image', 'data': data, 'mimeType': 'image/png'}]


def t_snap(args):
    return _snap(_session(args))


def t_eval(args):
    return _step(args, 'eval ' + args['expression'])


def t_run(args):
    return _step(args, 'run ' + args['code'].replace('\n', ';;'))


def t_click(args):
    return _step(args, 'click ' + args['target'])


def t_type(args):
    return _step(args, 'type ' + args['text'])


def t_key(args):
    s = _session(args)
    k = str(args['key'])
    if args.get('hold') is True:
        return _text(s['w'].ask('hold ' + k))
    if args.get('hold') is False:
        return _text(s['w'].ask('release ' + k))
    return _text(s['w'].ask('key ' + k))


def t_frames(args):
    return _step(args, 'frames %d' % int(args.get('count') or 1))


def t_step(args):
    if args['step'].strip().lower().startswith('snap'):
        raise ValueError('use xtpy_snap for a picture')   # snap FILE would write anywhere
    return _step(args, args['step'])


def t_game(args):
    """one game: open, N frames, stats, errors, a picture, close"""
    name = args['game']
    frames = int(args.get('frames') or 450)
    out = t_open({'target': name})
    if out.startswith('FAILED'):
        return out
    sid = out.split(':')[0].split()[1]
    s = _sessions[sid]
    try:
        t0 = time.time()
        fr = s['w'].ask('frames %d' % frames)
        took = time.time() - t0
        stats = s['w'].ask('stats')
        errs = s['w'].ask('errors')
        pic = _snap(s)
    finally:
        t_close({'session': sid})
    text = '%s: %d frames in %.1f s (%.0f a second)%s\nstats: %s\nscript errors: %s' % (
        name, frames, took, frames / max(took, 0.001), '' if fr['ok'] else '\nframes FAILED: ' + fr['answer'],
        stats['answer'] or '(none)', errs['answer'])
    return [{'type': 'text', 'text': text}] + pic


def t_diff(args):
    # LiveCode is left out until LIB_MCP starts its standalone hidden (a failed start opens a command prompt
    # on the owner's screen): the column says so
    cmd = [_python(), '-I', XTPY, 'diff', '--no-lc', args['code']]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
    return r.stdout.strip() or r.stderr.strip()


S = {'type': 'string'}
SESSION = {'session': dict(S, description='the session id xtpy_open gave (may be left out when one stack is open)')}


def schema(props=None, required=None):
    p = dict(SESSION)
    p.update(props or {})
    return {'type': 'object', 'properties': p, 'required': required or []}


TOOLS = [
    ('xtpy_primer', t_primer, 'Read this first: how to open, play and test xTalk stacks and games with the xtpy '
     'tools, with example expressions (xTalk is not JavaScript or Python).', {'type': 'object', 'properties': {}}),
    ('xtpy_games', t_games, 'List the Vibecode3D games xtpy can open (names for xtpy_open / xtpy_game).',
     {'type': 'object', 'properties': {}}),
    ('xtpy_open', t_open, 'Open a stack or game in the Python xTalk runtime, hidden (nothing on screen), and keep it '
     'open between calls. Returns a session id. Up to %d at once.' % MAX_OPEN,
     {'type': 'object', 'properties': {
         'target': dict(S, description='a game name (xtpy_games), a harvest folder path, or a name in ~/projects/XTJSON'),
         'size': dict(S, description='a game view size like 720x540 (default)')}, 'required': ['target']}),
    ('xtpy_eval', t_eval, 'Evaluate one xTalk (LiveCode Script) expression as the open card\'s script sees it; '
     'every global is visible. Example: the text of field "Score"', schema({'expression': S}, ['expression'])),
    ('xtpy_run', t_run, 'Run xTalk statements as a script of the open card (one per line). Use global to reach globals.',
     schema({'code': S}, ['code'])),
    ('xtpy_click', t_click, 'Click an object (button "OK", field 2...) or a point "x,y" on the open card.',
     schema({'target': S}, ['target'])),
    ('xtpy_type', t_type, 'Type text the way a keyboard does (rawKeyDown, keyDown, into the focused field), one key '
     'a frame. \\b = Backspace, \\n = Return, \\t = Tab.', schema({'text': S}, ['text'])),
    ('xtpy_key', t_key, 'Press one key for a frame (a character, a key code, or a name: space return backspace tab '
     'escape left right up down). hold true keeps it down (the keysDown) until hold false lets it go.',
     schema({'key': S, 'hold': {'type': 'boolean'}}, ['key'])),
    ('xtpy_frames', t_frames, 'Let the stack run N frames, 60 a second (a game plays on; timers fire). A game shows '
     'its loading screen for its first 200-400 frames.',
     schema({'count': {'type': 'integer'}}, ['count'])),
    ('xtpy_snap', t_snap, 'A PNG picture of the hidden window.', schema()),
    ('xtpy_step', t_step, 'Any one xtpy step (click, type, key, hold, release, frames, eval, run, snap FILE, stats, '
     'errors; snap: use xtpy_snap), for what the other tools do not cover.', schema({'step': S}, ['step'])),
    ('xtpy_close', t_close, 'Close an open stack (session "all" closes every one).', schema()),
    ('xtpy_list', t_list, 'The stacks open now.', {'type': 'object', 'properties': {}}),
    ('xtpy_game', t_game, 'Play one game hidden for N frames (default 450; 60 a second): speed, stats line, script errors, a '
     'picture. Opens and closes it. The first 3-6 seconds of a game are its loading screen (a black picture).', {'type': 'object', 'properties': {'game': S, 'frames': {'type': 'integer'}},
                                       'required': ['game']}),
    ('xtpy_diff', t_diff, 'Run an xTalk snippet (an expression, or statements that put the answer into tOut) in the '
     'interpreter, the translated and the fast mode; says whether they agree.',
     {'type': 'object', 'properties': {'code': S},
                                     'required': ['code']}),
]
