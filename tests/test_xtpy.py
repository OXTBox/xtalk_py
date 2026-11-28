#!/usr/bin/env python3
"""tests for xtpy (x1-12): xtalk/session.py steps and tools/xtpy.py, two at once.

    python3 -I tests/test_xtpy.py           the session on tests/stacks/mini (no window, standard library only)
    .venv/bin/python -I tests/test_xtpy.py  the same, plus tools/xtpy runs: two at once, serve mode, a game
"""
import json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
MINI = os.path.join(ROOT, 'tests', 'stacks', 'mini')
VENV = os.path.join(ROOT, '.venv', 'bin', 'python')
results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    if not ok:
        print('FAIL %s\n   got  %r\n   want %r' % (name, got, want))


from xtalk.session import Session, key_code   # noqa: E402

check('key_code: letters lower case, numbers as given', (key_code('A'), key_code('65361'), key_code('space'), key_code('Left'), key_code('return')),
      (97, 65361, 32, 65361, 65293))
s = Session(MINI, window=False)
check('eval', s.step('eval 1 + 2'), (True, '3'))
check('run, then eval a global it set', (s.step('run global gX;; put 7 into gX')[0], s.step('eval gX')),
      (True, (True, '7')))
check('a bad expression fails with why', s.step('eval 1 +')[0], False)
check('an unknown step fails', s.step('jump')[0], False)
ok, ans = s.step('run put 1 into field "nope"')
check('a script error fails the step', ok, False)
check('frames with no window run timers', s.step('frames 3'), (True, '3 frames'))
check('snap without a window says why', s.step('snap x.png'), (False, 'snap needs the .venv (raylib)'))
folder = s.folder
s.close()
check('close removes the session folder', os.path.isdir(folder), False)

try:
    import raylib  # noqa: F401
    have_raylib = True
except ImportError:
    have_raylib = False
if have_raylib or os.path.isfile(VENV):
    py = VENV if os.path.isfile(VENV) else sys.executable
    cmd = [py, '-I', os.path.join(ROOT, 'tools', 'xtpy.py')]
    t0 = time.time()
    procs = [subprocess.Popen(cmd + [MINI, 'eval %d * 10' % n, 'frames 5'], stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, text=True) for n in (1, 2)]
    outs = [p.communicate(timeout=120)[0] for p in procs]
    check('two at once: each answers its own',
          [o.split('\n')[:2] for o in outs], [['> eval 1 * 10', '10'], ['> eval 2 * 10', '20']])
    check('two at once: both exit 0', [p.returncode for p in procs], [0, 0])
    p = subprocess.run(cmd + [MINI, 'eval 1 +'], capture_output=True, text=True, timeout=120)
    check('a failed step: exit 1', p.returncode, 1)
    p = subprocess.Popen(cmd + [MINI, 'serve'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True)
    out, _ = p.communicate('eval 6 * 7\nclose\n', timeout=120)
    lines = [json.loads(x) for x in out.splitlines()]
    check('serve: stdout is JSON only (raylib lines go to stderr)',
          lines, [{'ok': True, 'answer': 'open %s' % MINI}, {'ok': True, 'answer': '42'}])
    p = subprocess.run(cmd + ['Thrmnlra', 'frames 40', 'type `hellx\\bo', 'eval the text of field "GameNote"'],
                       capture_output=True, text=True, timeout=300)
    check('a game: type into its note box', p.stdout.split('\n')[-2:], ['hello', ''])

print('%d of %d xtpy checks pass' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
