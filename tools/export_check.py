#!/usr/bin/env python3
"""export_check.py - does an exported game run on its own and play exactly as it does here?

    .venv/bin/python -I tools/export_check.py [GAME] [--frames 900]

Runs exports/GAME/main.py --bench from an empty folder elsewhere, watching every file it opens, and compares
its state dump with the same bench run here (in memory, translating at load). Passes when:
  - the dumps are the same byte for byte (state, script locals, the picture every 30 frames), the export's
    files/ folder read as ~/projects (the game keeps the folder it found its games in);
  - the native handlers ran as often;
  - no script was translated at start (all came translated);
  - nothing was opened (Python's open()) in ~/projects outside the export (the sources, XTJSON, LIB_GAMES...).
    Not seen by it: files raylib opens itself (xt3d_Load*: models, textures, sounds) and `there is a file`
    tests (they look, not open); a file a later level reads is not in this run either.
"""
import os, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS = os.path.dirname(ROOT)
PY = os.path.join(ROOT, '.venv', 'bin', 'python')

WATCH = r'''
import os, sys, runpy
EXPORT, PROJECTS, LOG = sys.argv[1], sys.argv[2], sys.argv[3]
seen = []
def hook(ev, args):
    if ev == 'open' and isinstance(args[0], (str, bytes)):
        p = os.path.abspath(os.fsdecode(args[0]))
        if p.startswith(PROJECTS + '/') and not p.startswith(EXPORT + '/') and '/.venv/' not in p:   # (the cwd: below)
            seen.append(p)
sys.addaudithook(hook)
sys.path.insert(0, EXPORT)
from xtalk.stack import runtime
n = {'translated': 0}
plain = runtime.translate_script
def counted(*a, **k):
    n['translated'] += 1
    return plain(*a, **k)
runtime.translate_script = counted
sys.argv = [os.path.join(EXPORT, 'main.py')] + sys.argv[4:]
try:
    runpy.run_path(sys.argv[0], run_name='__main__')
except SystemExit:
    pass
with open(LOG, 'w') as f:
    f.write('translated %d\n' % n['translated'])
    for p in sorted(set(seen)):
        f.write('read %s\n' % p)
'''


def main(a):
    game = a[0] if a and not a[0].startswith('--') else 'uDead_CullTest'
    frames = a[a.index('--frames') + 1] if '--frames' in a else '900'
    export = os.path.join(ROOT, 'exports', game)
    os.makedirs(os.path.join(ROOT, 'run_files'), exist_ok=True)
    work = tempfile.mkdtemp(prefix='export_check_', dir=os.path.join(ROOT, 'run_files'))
    d_here, d_there, log = (os.path.join(work, x) for x in ('here.dump', 'there.dump', 'watch.log'))
    watch = os.path.join(work, 'watch.py')
    open(watch, 'w').write(WATCH)
    r1 = subprocess.run([PY, '-I', os.path.join(ROOT, 'tools', 'bench_xt3d.py'), game, '--frames', frames, '--dump',
                         d_here, '--no-save'], capture_output=True, text=True)
    r2 = subprocess.run([PY, '-I', watch, export, PROJECTS, log, '--bench', '--frames', frames, '--dump', d_there],
                        capture_output=True, text=True, cwd=work)
    pick = lambda out: [l for l in out.splitlines() if l.startswith(('wall', 'native calls', 'script errors'))]  # noqa
    print('here  :', ' | '.join(pick(r1.stdout)))
    print('export:', ' | '.join(pick(r2.stdout)))
    ok = True
    if r2.returncode or not os.path.exists(d_there):
        print(r2.stdout[-1500:], r2.stderr[-2500:])
        return 1
    there = open(d_there).read().replace(os.path.join(export, 'files'), PROJECTS)   # a path the game keeps: the
    same = open(d_here).read() == there                                                # export's own folders
    print('state, locals, pictures:', 'SAME' if same else 'DIFFERENT')
    calls = [l for l in pick(r1.stdout) if l.startswith('native')] == [l for l in pick(r2.stdout) if l.startswith('native')]
    print('native calls:', 'same' if calls else 'DIFFERENT')
    w = open(log).read().splitlines()
    print('scripts translated at start:', w[0].split()[1])
    outside = [l[5:] for l in w[1:] if not l[5:].startswith(work + '/')]   # its own folder (cwd) is fine
    print('files opened (Python open) in ~/projects outside the export: %d' % len(outside))
    for p in outside[:10]:
        print('   ', p)
    ok = same and calls and w[0] == 'translated 0' and not outside
    print('PASS' if ok else 'FAIL', '(work folder %s)' % work)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
