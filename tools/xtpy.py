#!/usr/bin/env python3
"""xtpy - a command line like lcmcp, for the Python runtime (x1-12). A stack or game opened hidden, steps run in order.

    tools/xtpy TARGET [do] 'STEP' 'STEP' ...     the answers printed, one block a step
    tools/xtpy TARGET serve                      one step a line on stdin, one JSON answer a line on stdout
                                                 ({"ok": true, "answer": "..."}); "close" or end of input stops
                                                 (the x1-14 MCP pack runs one of these a stack)

TARGET: a game name in LIB_GAMES/Vibecode3D_Games (Thrmnlra, SquadBuggy...), a harvest folder, or a name in
~/projects/XTJSON. Steps (xtalk/session.py has them all):
    click OBJECT|X,Y   type TEXT (\\b \\n \\t)   key K   hold K   release K   frames N
    eval EXPR   run STATEMENTS (;; between)   snap FILE.png   stats   errors
Example:
    tools/xtpy Thrmnlra 'frames 40' 'type `hello' 'eval the text of field "GameNote"'

Options: --size 720x540 (a game's view), --keep (keep run_files/xtpy/<pid>: the stack's writes).
Exit status 1 when a step failed or a script error came. Any number may run at once (each its own folder);
the stack's writes stay in that folder, never in your files.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main(a):
    if not a or a[0] in ('-h', '--help'):
        sys.exit(__doc__)
    # answers go to the real stdout; everything else printed (raylib's INFO lines, the stacks' own puts,
    # the C library's lines too) goes to stderr, so the answers can be read by a program (serve, x1-14)
    out = os.fdopen(os.dup(1), 'w', buffering=1)
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    size, keep = (720, 540), False
    if '--size' in a:
        i = a.index('--size')
        size = tuple(int(x) for x in a[i + 1].split('x'))
        del a[i:i + 2]
    if '--keep' in a:
        a.remove('--keep')
        keep = True
    target, steps = a[0], a[1:]
    from xtalk.session import Session
    try:
        s = Session(target, size=size, keep=keep)
    except Exception as e:                           # noqa: BLE001
        if steps[:1] == ['serve']:
            out.write(json.dumps({'ok': False, 'answer': 'could not open %s: %s' % (target, e)}) + '\n')
        else:
            out.write('could not open %s: %s\n' % (target, e))
        return 1
    failed = 0
    try:
        if steps[:1] == ['serve']:
            out.write(json.dumps({'ok': True, 'answer': 'open %s' % target}) + '\n')
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                if line.lower() in ('close', 'quit'):
                    break
                ok, answer = s.step(line)
                out.write(json.dumps({'ok': ok, 'answer': answer}) + '\n')
            return 0
        if steps[:1] == ['do']:
            steps = steps[1:]
        for st in steps:
            ok, answer = s.step(st)
            out.write('%s %s\n%s\n' % ('>' if ok else '! FAILED', st, answer))
            failed += not ok
    finally:
        s.close()
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
