#!/usr/bin/env python3
"""xt3d_golden.py - ask the real xt3d bridge (LiveCode + xt3d.dll) what each xt3d test case gives.

    python3 -I tools/xt3d_golden.py

Reads tests/xt3d_cases.txt (one expression a line), evaluates each in the xt3d bench standalone
(~/projects/xt3D_Raylib_Livecode_Bridge/tools/bench, LIB_MCP port 8768; it starts the bench when it
is not running: a window on the owner's screen) and writes tests/xt3d_golden.json. The bench has
a hidden raylib window open, so window-only calls answer too. tests/test_xt3d.py compares with it.
"""
import json, os, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.expanduser('~/projects/xt3D_Raylib_Livecode_Bridge/tools/bench')


def cases():
    for ln in open(os.path.join(ROOT, 'tests', 'xt3d_cases.txt'), encoding='utf-8'):
        ln = ln.rstrip('\n')
        if ln.strip() and not ln.startswith('#'):
            yield ln


def main():
    out = {}
    for c in cases():
        # an error comes back as text starting "ERROR" rather than stopping the run
        stm = 'try\n put (%s) into tX\ncatch e\n put "ERROR " & line 1 of e into tX\nend try\nput tX' % c
        r = subprocess.run([BENCH, 'run', stm], capture_output=True, text=True, timeout=60)
        v = r.stdout.rstrip('\n')
        out[c] = v
        print('%-60s %s' % (c, v))
    json.dump(out, open(os.path.join(ROOT, 'tests', 'xt3d_golden.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
