#!/usr/bin/env python3
"""native_sigs.py - the signature of each handler that has a native version, now and as written for

    python3 -I tools/native_sigs.py            prints them; "changed" = the xTalk changed: check the native
                                               function against it, then put the new signature in its SIGS
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from xtalk import native                       # noqa: E402
from xtalk.interp import Interp                # noqa: E402

SCRIPTS = {'vibeenginext3d': os.path.expanduser(
    '~/projects/xt3D_Raylib_Livecode_Bridge/testbench/vibe_engine_xt3d.livecodescript')}


def main():
    native._table()
    bad = 0
    for stack, path in SCRIPTS.items():
        it = Interp()
        it.load(open(path).read())
        from xtalk.native import vibe_engine_xt3d as m
        for name in m.HANDLERS:
            now = native.signature(it.handlers[name])
            was = native.SIGS.get(stack, {}).get(name)
            bad += now != was
            print('%-28s %s  %s' % (name, now, 'same' if now == was else 'changed (written for %s)' % was))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
