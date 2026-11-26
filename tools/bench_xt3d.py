#!/usr/bin/env python3
"""bench_xt3d.py - the same uDead run every time: a bench for speed work and a referee for native handlers.

    .venv/bin/python -I tools/bench_xt3d.py [GAME] [--frames 900] [--label NAME] [--dump OUT.txt] [--profile]
                                           [--no-save]

What makes it the same every time (HANDOFF_NATIVE step 0):
  - the scripts' clock is a test clock (xtalk.interp.CLOCK): it starts at a fixed moment, moves with the frames
    (FRAME_MS a frame) and a little (READ_MS) each time a script reads it, so a loop that works "until 7 ms
    went by" (uDead.FieldWork) does the same amount of work every run, however fast the computer;
  - `set the randomSeed to the milliseconds` (uDead.Generate) therefore always gets the same seed, and
    `set the randomSeed` now really seeds random() (it did nothing before 25 Nov);
  - no real input: the mouse stays in the middle, keys come from the KEYS script below, gNoMouse is true;
  - every frame lets exactly FRAME_MS of messages run (no real-time budget).

Timings are real (perf_counter), taken in Python around the host's own brackets: step = Vibe.Step,
scene = Vibe.Frame, draw = the rest of the host's tick (xbDrawGame) plus the window's card drawing.
The game's own stats line is in test-clock milliseconds, so it is not printed.

--dump writes the state after the last frame: the last Vibe.Frame() array and every global (sorted). Two runs
must give the same file byte for byte (tools/bench_xt3d.py --check runs it twice, in two processes).
Results go to run_files/bench/<date>_<label>.txt (the first one made is the baseline).
"""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

FRAME_MS = 50.0 / 3                      # 60 frames a second of game time
READ_MS = 0.05                           # each read of the clock moves it this much (see above)
START_MS = 1_000_000_000.0               # the test clock's first moment
# the bench keys: (from frame, to frame, key). Hiding mode 3, R (rush) at 60, then walk (W) and turn (left arrow)
KEYS = [(10, 14, '3'), (60, 64, 'r'), (120, 900, 'w'), (300, 360, 65361), (600, 640, 65363)]


def keys_at(i):
    return [ord(k) if isinstance(k, str) else k for a, b, k in KEYS if a <= i < b]


def dump_text(v, depth=0):
    """an xTalk value (text or array) as sorted lines, the same for the same value whatever the run"""
    if hasattr(v, 'keys') and not isinstance(v, str):
        out = []
        for k in sorted(v.keys(), key=lambda k: str(k).lower()):
            out.append('%s[%s]' % ('  ' * depth, k))
            out.append(dump_text(v[k], depth + 1))
        return '\n'.join(out)
    return '  ' * depth + str(v)


def main(a):
    game = a[0] if a and not a[0].startswith('--') else 'uDead_CullTest'
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d       # noqa: E731
    if '--check' in a:
        return check(game, opt('--frames', '300'))
    frames = int(opt('--frames', 900))
    label = opt('--label', 'run')
    from xt3d_game_check import make_stack, HOST
    from xtalk import interp
    from xtalk.interp import Interp
    Interp.CATCH_LOG = []
    from xtalk.stack import StackRuntime
    from xtalk.stack.view import View, rl
    import random
    random.seed(1)                       # anything random before the game seeds it itself
    w, h = 720, 540
    folder = os.path.join(ROOT, 'run_files', 'xt3d_bench')
    make_stack(folder, w, h)
    rt = StackRuntime(folder, real_folders=True)
    clock = {'ms': START_MS}

    def test_clock():
        clock['ms'] = max(clock['ms'] + READ_MS, START_MS + rt.clock)
        return clock['ms']
    interp.CLOCK[0] = test_clock
    rt.harvest.main.filename = HOST
    rt.G['gxbviewrect'] = '0,0,%d,%d' % (w, h)
    rt.G['gnomouse'] = 'true'
    v = View(rt, hidden=True)
    rt.open()
    card = rt.default_stack.children[0]
    t0 = time.perf_counter()
    rt.message(card, 'xbPlayGame', [game])
    start_s = time.perf_counter() - t0

    # timing brackets: the engine's Vibe.Step and Vibe.Frame, wherever they are called from
    from xtalk.stack.runtime import ObjInterp as StackContext
    spent = {'vibe.step': 0.0, 'vibe.frame': 0.0}
    last = {}
    inside = set()
    plain_invoke = StackContext.invoke

    def timed_invoke(self, name, args):
        n = name.lower()
        if n not in spent or n in inside:    # a call passed along the message path is timed once, outermost
            return plain_invoke(self, name, args)
        inside.add(n)
        t = time.perf_counter()
        try:
            r = plain_invoke(self, name, args)
        finally:
            inside.discard(n)
        spent[n] += time.perf_counter() - t
        if n == 'vibe.frame':
            last['frame'] = r
        return r
    StackContext.invoke = timed_invoke

    prof = None
    if '--profile' in a:
        import cProfile
        prof = cProfile.Profile()
        prof.enable()
    per = []                             # (step, scene, rest) ms a frame
    held = []
    t_all = time.perf_counter()
    for i in range(frames):
        now = keys_at(i)
        for code in now:
            if code not in held:
                rt.raw_key(code)
        held = now
        rt.test_keys = list(now)
        rt.held_codes, rt.keys_down, rt.buttons_down = list(now), set(), set()
        rt.mouse_move(w // 2, h // 2)
        s0, f0 = spent['vibe.step'], spent['vibe.frame']
        t = time.perf_counter()
        rl.begin_drawing()
        v.draw_card()
        rl.end_drawing()
        rt.tick(FRAME_MS)
        whole = time.perf_counter() - t
        st, sc = spent['vibe.step'] - s0, spent['vibe.frame'] - f0
        per.append((st * 1000, sc * 1000, (whole - st - sc) * 1000))
    wall = time.perf_counter() - t_all
    if prof is not None:
        prof.disable()
        import pstats
        pstats.Stats(prof).sort_stats('tottime').print_stats(30)
    StackContext.invoke = plain_invoke

    objects = len([x for x in str((last.get('frame') or {}).get('objects', '') if hasattr(last.get('frame'), 'get') else '').split('\n') if x])
    lines = ['bench %s  game %s  frames %d  %s' % (label, game, frames, time.strftime('%Y-%m-%d %H:%M:%S')),
             'git %s' % git_head(),
             'native %s  mode %s' % (os.environ.get('XTALK_NATIVE', '(default)'),
                                      'interpreter' if os.environ.get('XTALK_INTERP') else 'fast'),
             'start (engine load + level) %.2f s' % start_s,
             'wall %.2f s  (%.1f frames a second)' % (wall, frames / wall),
             'objects in the last frame %d' % objects]
    from xtalk import native
    if native.USED:
        lines.append('native calls: ' + ', '.join('%s %d' % (k[1], n) for k, n in sorted(native.USED.items())))
    busy = [p for p in per if p[0] + p[1] > 0]   # frames where the game stepped or drew
    for name, k in (('step', 0), ('scene', 1), ('draw+rest', 2)):
        xs = [p[k] for p in busy] or [0]
        lines.append('%-10s avg %6.2f ms   worst %7.2f ms' % (name, sum(xs) / len(xs), max(xs)))
    lines.append('game frames %d of %d' % (len(busy), frames))
    if rt.errors:
        lines.append('script errors %d, first: %s' % (len(rt.errors), ' '.join(map(str, rt.errors[0]))[:300]))
    print('\n'.join(lines))
    if '--dump' in a:
        out = [dump_text(last.get('frame', ''))]
        for k in sorted(rt.G):
            out.append('global %s' % k)
            out.append(dump_text(rt.G[k], 1))
        open(opt('--dump', ''), 'w').write('\n'.join(out) + '\n')
        print('dumped the state to', opt('--dump', ''))
    if '--no-save' not in a:
        d = os.path.join(ROOT, 'run_files', 'bench')
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, '%s_%s.txt' % (time.strftime('%Y-%m-%d_%H%M'), label))
        open(p, 'w').write('\n'.join(lines) + '\n')
        print('saved', p)
    v.close()
    return 0


def git_head():
    try:
        return subprocess.run(['git', '-C', ROOT, 'log', '--oneline', '-1'], capture_output=True, text=True).stdout.strip()
    except OSError:
        return '?'


def check(game, frames):
    """two runs in two processes; their state dumps must be the same byte for byte"""
    d = os.path.join(ROOT, 'run_files', 'bench')
    os.makedirs(d, exist_ok=True)
    outs = []
    for n in (1, 2):
        p = os.path.join(d, 'check_dump_%d.txt' % n)
        r = subprocess.run([sys.executable, '-I', os.path.abspath(__file__), game, '--frames', str(frames),
                            '--dump', p, '--no-save', '--label', 'check%d' % n], capture_output=True, text=True)
        print('\n'.join(l for l in r.stdout.splitlines() if not l.startswith('libEGL')))
        if r.returncode:
            print(r.stderr[-2000:])
            return 1
        outs.append(open(p).read())
    if outs[0] == outs[1]:
        print('SAME: the two runs left the same state (%d lines)' % outs[0].count('\n'))
        return 0
    a, b = outs[0].split('\n'), outs[1].split('\n')
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            print('DIFFERENT from line %d:\n  1: %s\n  2: %s' % (i + 1, x[:200], y[:200]))
            break
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
