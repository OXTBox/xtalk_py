#!/usr/bin/env python3
"""frame_referee.py - do two runs of a game leave the same state? (HANDOFF_NATIVE step 1)

    .venv/bin/python -I tools/frame_referee.py A.dump B.dump [--tol 1e-6]
        compare two state dumps made by tools/bench_xt3d.py --dump: text must be equal, numbers equal to a
        relative tolerance (default 1e-6; 1e-9 absolute near zero)
    .venv/bin/python -I tools/frame_referee.py --run [GAME] [--frames 120] [--modes fast,native0,interp]
        make the dumps itself, one process each, and compare every one with the first:
          fast     the translated handlers with the native ones (the default way a game runs)
          native0  XTALK_NATIVE=0: every native handler off, only the translated xTalk
          interp   XTALK_INTERP=1: the interpreter, the reference the translator is checked against

The dumps hold the last Vibe.Frame() (every object line: mesh, colour, 3x3 rotation, position) and every
global (the camera is gCameraYaw, gCameraPitch and the engine's camera globals).
Answers 0 when all agree.
"""
import os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUM = re.compile(r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')


def same_line(a, b, tol):
    if a == b:
        return True
    pa, pb = NUM.split(a), NUM.split(b)
    if pa != pb:                         # the text between the numbers differs
        return False
    for x, y in zip(NUM.findall(a), NUM.findall(b)):
        fx, fy = float(x), float(y)
        if abs(fx - fy) > max(tol * max(abs(fx), abs(fy)), 1e-9):
            return False
    return True


def compare(fa, fb, tol=1e-6, quiet=False):
    a, b = open(fa).read().split('\n'), open(fb).read().split('\n')
    bad = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if not same_line(x, y, tol)]
    if len(a) != len(b):
        bad.append((min(len(a), len(b)), '(%d lines)' % len(a), '(%d lines)' % len(b)))
    if not quiet:
        for i, x, y in bad[:8]:
            print('  line %d differs:\n    %s\n    %s' % (i + 1, x[:220], y[:220]))
        if len(bad) > 8:
            print('  ... %d lines differ in all' % len(bad))
    return not bad


def run(game, frames, modes):
    d = os.path.join(ROOT, 'run_files', 'bench')
    os.makedirs(d, exist_ok=True)
    env_for = {'fast': {}, 'native0': {'XTALK_NATIVE': '0'}, 'interp': {'XTALK_INTERP': '1', 'XTALK_NATIVE': '0'}}
    py = os.path.join(ROOT, '.venv', 'bin', 'python')
    dumps = []
    for m in modes:
        p = os.path.join(d, 'referee_%s.dump' % m)
        env = dict(os.environ, **env_for[m])
        r = subprocess.run([py, '-I', os.path.join(ROOT, 'tools', 'bench_xt3d.py'), game, '--frames', str(frames),
                            '--dump', p, '--no-save', '--label', 'referee_' + m], capture_output=True, text=True, env=env)
        wall = [l for l in r.stdout.splitlines() if l.startswith(('wall', 'script errors'))]
        print('%-8s %s' % (m, ' | '.join(wall)))
        if r.returncode:
            print(r.stderr[-1500:])
            return 1
        dumps.append((m, p))
    ok = True
    for m, p in dumps[1:]:
        same = compare(dumps[0][1], p)
        print('%s vs %s: %s' % (dumps[0][0], m, 'AGREE' if same else 'DIFFER'))
        ok = ok and same
    return 0 if ok else 1


def main(a):
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d       # noqa: E731
    if '--run' in a:
        rest = [x for x in a if not x.startswith('--')]
        game = rest[0] if rest and rest[0] not in (opt('--frames', ''), opt('--modes', '')) else 'uDead_CullTest'
        return run(game, int(opt('--frames', 120)), opt('--modes', 'fast,native0,interp').split(','))
    files = [x for x in a if not x.startswith('--') and x != opt('--tol', None)]
    ok = compare(files[0], files[1], float(opt('--tol', 1e-6)))
    print('AGREE' if ok else 'DIFFER')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
