#!/usr/bin/env python3
"""The interpreter against LiveCode 9.6.3's own answers (tests/golden.json, made by tools/golden.py).

    python3 -I tests/test_interp.py [-v]

An error in LiveCode is stored as "ERR"; the interpreter must raise one too.
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from xtalk import Interp, XtError   # noqa: E402

gold = json.load(open(os.path.join(ROOT, 'tests/golden.json'), encoding='utf-8'))
verbose = '-v' in sys.argv
bad = []

def run(kind, case):
    it = Interp()
    try:
        if kind == 'expr':
            return it.eval(case)
        fr = None
        from xtalk.interp import Frame
        from xtalk.parser import parse_statements
        fr = Frame([])
        it.exec_block(parse_statements(case), fr)
        return fr.vars.get('tout', '')
    except (XtError, RecursionError, ZeroDivisionError, ValueError, OverflowError, KeyError, IndexError, TypeError) as e:
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
for kind, case, want, got in bad:
    print('FAIL  [%s] %s\n        LiveCode: %r\n        ours:     %r' % (kind, case.replace('\n', ' / ')[:90], want, got))
print('\n%d of %d match LiveCode 9.6.3' % (n - len(bad), n))
sys.exit(1 if bad else 0)
