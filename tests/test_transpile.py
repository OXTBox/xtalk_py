#!/usr/bin/env python3
"""The translator against LiveCode 9.6.3's own answers: the same cases as test_interp.py
(tests/golden.json), but every case and every library is first turned into Python by
xtalk/transpile.py and the Python is run.

    python3 -I tests/test_transpile.py [-v]

Also prints how many library handlers became Python (the rest are kept as xTalk and interpreted).
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from xtalk import XtError                                     # noqa: E402
from xtalk.pyrt import Runtime, Frame                         # noqa: E402
import xtalk.pyrt as pyrt                                     # noqa: E402
from xtalk.transpile import translate_expr, translate_statements, translate_script   # noqa: E402
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from golden import lib_text                                   # noqa: E402

gold = json.load(open(os.path.join(ROOT, 'tests/golden.json'), encoding='utf-8'))
verbose = '-v' in sys.argv
ERRS = (XtError, RecursionError, ZeroDivisionError, ValueError, OverflowError, KeyError, IndexError, TypeError)
bad = []
ENV = {k: getattr(pyrt, k) for k in dir(pyrt) if not k.startswith('__')}

def py_eval(rt, code, fr):
    v = eval(code, dict(ENV, rt=rt, fr=fr))
    return '' if isinstance(v, dict) else pyrt.to_text(v)

def run(kind, case):
    rt = Runtime()
    try:
        if kind == 'expr':
            return py_eval(rt, translate_expr(case), Frame([]))
        env = dict(ENV)
        exec(translate_statements(case), env)
        fr = Frame([])
        env['_body'](rt, fr)
        return fr.vars.get('tout', '')
    except ERRS:
        return 'ERR'

n = 0
for kind in ('expr', 'script'):
    for case, want in gold[kind].items():
        n += 1
        got = run(kind, case)
        if got != want:
            bad.append((kind, case, want, got))
        elif verbose:
            print('ok    ', case.replace('\n', ' / ')[:70])
done = interp = 0
for lib, d in gold.get('lib', {}).items():
    rt = Runtime()
    for part in lib.split('|'):
        py, rep = translate_script(lib_text(part), part)
        done += len(rep['translated'])
        interp += len(rep['interpreted'])
        for name, why in rep['interpreted']:
            print('kept as xTalk:', part, name, why)
        rt.install(py, part)
    for case, want in d.items():
        n += 1
        try:
            got = py_eval(rt, translate_expr(case), Frame([]))
        except Exception as e:                       # noqa: BLE001  (any failure is a mismatch)
            got = 'ERR' if isinstance(e, XtError) else 'CRASH %s: %s' % (type(e).__name__, e)
        if got != want:
            bad.append(('lib ' + os.path.basename(lib), case, want, got))
        elif verbose:
            print('ok    ', case[:70])
# ---- self-checks (no LiveCode answer needed)
import xtalk.transpile as T                                   # noqa: E402
def check(name, ok):
    global n
    n += 1
    if not ok:
        bad.append(('self-check', name, 'ok', 'failed'))
SRC = 'function Twice x\n  return x * 2\nend Twice\non Go\n  do "put Twice(21) into gOut"\n  return gOut\nend Go\n'
rt = Runtime(); rt.install(translate_script(SRC)[0])
check('do-code calls a translated handler', rt.call('Go') == '42')
orig = T.Gen.s_return
T.Gen.s_return = lambda self, s, ind: (_ for _ in ()).throw(T.TranslateError('test'))
py, rep = translate_script(SRC)
T.Gen.s_return = orig
rt = Runtime(); rt.install(py)
check('a handler kept as xTalk still runs', len(rep['interpreted']) == 2 and rt.call('Go') == '42')
for lib in ('lib_bit', 'lib_map', 'lib_trace'):
    g = os.path.join(ROOT, 'generated', lib + '.py')
    fresh = translate_script(lib_text('libraries/%s.livecodescript' % lib), os.path.join('corpus', 'libraries', lib + '.livecodescript'))[0]
    check('generated/%s.py is up to date (python3 -I tools/translate.py --libs)' % lib,
          os.path.exists(g) and open(g, encoding='utf-8').read() == fresh)

for kind, case, want, got in bad:
    print('FAIL  [%s] %s\n        LiveCode: %r\n        ours:     %r' % (kind, case.replace('\n', ' / ')[:90], want, got))
print('\nlibrary handlers: %d became Python, %d kept as xTalk' % (done, interp))
print('%d of %d translated cases match LiveCode 9.6.3' % (n - len(bad), n))
sys.exit(1 if bad else 0)
