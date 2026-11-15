#!/usr/bin/env python3
"""xtalk_py's check that runs without LiveCode (A-50): the glossary census cleans comments and
strings the way xTalk does and splits one-line ifs into statements.

    python3 -I tests/run_tests.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import glossary_census as gl                # noqa: E402

CHECKS, FAILS = [0], []


def check(name, ok, got=None):
    CHECKS[0] += 1
    if not ok:
        FAILS.append(name)
        print("FAIL  %s%s" % (name, "" if got is None else "  (got %r)" % (got,)))
    else:
        print("ok    %s" % name)


def done():
    print("\n%d of %d passed" % (CHECKS[0] - len(FAILS), CHECKS[0]))
    return 1 if FAILS else 0


def main():
    lines = gl.clean_lines('put "a -- b" into x -- note\n/* block\ncomment */\n# hash\n\nbeep')
    check('comments go, -- inside a string stays a string', lines == ['put "" into x', 'beep'], lines)
    check('one-line if splits into statements', gl.statements('if x then put 1 into y else put 2 into y')
          == ['if x', 'put 1 into y', 'put 2 into y'])
    return done()


if __name__ == '__main__':
    sys.exit(main())
