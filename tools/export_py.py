#!/usr/bin/env python3
"""export_py.py - a Vibecode3D game as a Python program that runs on its own (HANDOFF_NATIVE step 4).

    .venv/bin/python -I tools/export_py.py [GAME] [--out DIR]       GAME default uDead_CullTest

Writes exports/<GAME>/ (git-ignored; DIR to put it elsewhere):
    main.py           plays the game in a window (as tools/play_xt3d.sh does); --bench [--frames N] [--dump F]
                      runs the bench's fixed run instead (tools/bench_xt3d.py), to check the export
    play.sh           main.py with this machine's .venv Python
    py/*.py           every script the game runs, translated to Python beforehand (no translating at start)
    manifest.json     which translation belongs to which script (by the sha1 of its text), and the native
                      handlers checked for it at export time
    files/...         the scripts and files the game reads, in the same folders as under ~/projects (the
                      host finds the engine, the game and the libraries above itself, as it does there)
    xtalk/            the runtime (the xTalk rules, the native handlers, xt3d on raylib)
    tools/            the bench and the window (bench_xt3d.py, xt3d_game_check.py)

How it learns what the game needs: it plays it here, hidden, for a few hundred frames, and notes every script
loaded and every file read under ~/projects. A file the game reads only later (a level not reached) is not
copied: the export then reads nothing and the game says so, as it would with a missing file.

The xTalk scripts go along (files/): they are the source, and `do`, value() and the like still read xTalk at
run time. What the export does NOT need: XTJSON harvests, the LiveCode IDE, ~/projects.
"""
import json, os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

MAIN = r'''#!/usr/bin/env python3
"""%(game)s, exported by xtalk_py/tools/export_py.py on %(date)s (git %(git)s).

    python3 main.py                      play (a window at 200,32; close it to stop)
    python3 main.py --bench [--frames N] [--dump FILE]     the bench's fixed run (checks the export)

Needs Python 3.14 with the raylib package (and imgui-bundle for menus and dialogs): play.sh uses the .venv
this was exported from.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
sys.path.insert(0, HERE)
GAME = %(game)r


def setup():
    from xtalk.stack import runtime
    man = json.load(open(os.path.join(HERE, 'manifest.json')))
    for sha, e in man['scripts'].items():
        e = dict(e)
        e['module'] = os.path.join(HERE, e['module'])
        runtime.PRECOMPILED[sha] = e
    import xt3d_game_check as gc
    gc.BRIDGE = os.path.join(HERE, 'files', man['bridge'])
    gc.HOST = os.path.join(HERE, 'files', man['host'])


def main(a):
    setup()
    if '--bench' in a:
        import bench_xt3d
        return bench_xt3d.main([GAME] + [x for x in a if x != '--bench'] + (['--no-save'] if '--save' not in a else []))
    import xt3d_game_check as gc
    return gc.main([GAME, '--window', '--size', '720x540'])


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) or 0)
'''


def learn(game, frames):
    """play the game hidden (the bench's run) and note the scripts loaded and the files read"""
    from xtalk.stack import runtime
    from xtalk.transpile import translate_script
    from xtalk import native
    scripts, reads = [], []

    def hook(ev, args):
        if ev == 'open' and isinstance(args[0], (str, bytes)):
            p = os.path.abspath(os.fsdecode(args[0]))
            mode = args[1] if len(args) > 1 and isinstance(args[1], str) else 'r'
            if p.startswith(PROJECTS + '/') and not p.startswith(ROOT + '/') and 'r' in mode and os.path.isfile(p):
                reads.append(p)
    sys.addaudithook(hook)
    plain_load = runtime.ObjInterp.load

    def load(self, script):
        name = self.rt.host.name_of(self.obj, 'long')
        py, rep = translate_script(script, name, fast=True, byref_fns=self.rt.byref_fns)
        r = plain_load(self, script)
        scripts.append({'name': name, 'text': script, 'py': py, 'rep': rep, 'ctx': self})
        return r
    runtime.ObjInterp.load = load
    import bench_xt3d
    bench_xt3d.main([game, '--frames', str(frames), '--no-save'])
    runtime.ObjInterp.load = plain_load
    for s in scripts:
        s['verified'] = native.verified_names(s['ctx']) if s['ctx'].obj.type == 'stack' else None
    return scripts, sorted(set(reads))


def main(a):
    game = a[0] if a and not a[0].startswith('--') else 'uDead_CullTest'
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d       # noqa: E731
    out = os.path.abspath(opt('--out', os.path.join(ROOT, 'exports', game)))
    scripts, reads = learn(game, int(opt('--frames', 300)))
    import xt3d_game_check as gc
    reads = [p for p in reads if p != os.path.abspath(gc.HOST)]
    from xtalk.stack.runtime import _sha
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, 'py'))
    for p in reads + [gc.HOST]:                         # the files, in their folders as under ~/projects
        dst = os.path.join(out, 'files', os.path.relpath(p, PROJECTS))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(p, dst)
    man = {'game': game, 'bridge': os.path.relpath(gc.BRIDGE, PROJECTS), 'host': os.path.relpath(gc.HOST, PROJECTS),
           'scripts': {}, 'files': [os.path.relpath(p, PROJECTS) for p in reads]}
    used = set()
    for s in scripts:
        slug = ''.join(c if c.isalnum() else '_' for c in s['name']).strip('_')[:60]
        while slug in used:
            slug += '_'
        used.add(slug)
        rel = 'py/%s.py' % slug
        with open(os.path.join(out, rel), 'w', encoding='utf-8') as f:
            f.write('# %s, translated from xTalk by xtalk_py (fast mode)\n' % s['name'])
            f.write(s['py'])
        man['scripts'][_sha(s['text'])] = {
            'object': s['name'], 'module': rel, 'parse_errors': s['rep']['parse_errors'],
            'plain': s['rep']['plain'] + s['rep']['interpreted'], 'natives_verified': s['verified']}
    json.dump(man, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    shutil.copytree(os.path.join(ROOT, 'xtalk'), os.path.join(out, 'xtalk'),
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    os.makedirs(os.path.join(out, 'tools'))
    for t in ('bench_xt3d.py', 'xt3d_game_check.py'):
        shutil.copy2(os.path.join(ROOT, 'tools', t), os.path.join(out, 'tools', t))
    import time
    git = subprocess.run(['git', '-C', ROOT, 'log', '--oneline', '-1'], capture_output=True, text=True).stdout.strip()
    with open(os.path.join(out, 'main.py'), 'w') as f:
        f.write(MAIN % {'game': game, 'date': time.strftime('%Y-%m-%d %H:%M'), 'git': git[:7]})
    with open(os.path.join(out, 'play.sh'), 'w') as f:
        f.write('#!/bin/sh\n# %s in Python (exported). What it prints goes to play.log.\ncd "$(dirname "$0")" || exit 1\n'
                '%s -I main.py "$@" > play.log 2>&1\n' % (game, os.path.join(ROOT, '.venv', 'bin', 'python')))
    os.chmod(os.path.join(out, 'play.sh'), 0o755)
    print('exported %s to %s' % (game, out))
    print('  %d scripts translated beforehand:' % len(scripts))
    for s in scripts:
        print('    %-50s %5d lines of xTalk -> %5d of Python; still read as xTalk at run time: %s; native: %s'
              % (s['name'][:50], s['text'].count('\n'), s['py'].count('\n'),
                 ', '.join(str(x[0] if isinstance(x, (tuple, list)) else x)
                           for x in s['rep']['plain'] + s['rep']['interpreted']) or 'none',
                 ', '.join(s['verified']) if s['verified'] else '-'))
    print('  %d files copied (as under ~/projects):' % (len(reads) + 1))
    for p in reads + [gc.HOST]:
        print('    ' + os.path.relpath(p, PROJECTS))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
