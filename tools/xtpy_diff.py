#!/usr/bin/env python3
"""xtpy diff (x1-13): one xTalk snippet in the interpreter, the translated and fast modes, and LiveCode, side by side.

    tools/xtpy diff '<expression>'                     e.g. tools/xtpy diff '7 mod -3'
    tools/xtpy diff 'put 1 into x;; put x + 1 into tOut'  statements (;; or new lines between): the answer is tOut
    tools/xtpy diff --no-lc '...'                      without LiveCode (the Python answers only)
    tools/xtpy diff --fact '...'                       also drafts the docs/LIVECODE_FACTS.md line (printed, not written)

Says AGREE when every answer is the same, else which ones differ from LiveCode. An error is ERR (as in
tests/golden.json). LiveCode is asked ONCE through lcmcp's standalone (no retry: a failed start can open a
command prompt on the owner's screen); if it does not answer, its column says "not asked" and why.
Exit status: 0 agree, 1 differ, 2 LiveCode asked but did not answer (with --no-lc: the Python answers decide).
"""
import os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
LCMCP = os.path.expanduser('~/projects/LIB_MCP/tools/lcmcp')
LC_TIMEOUT = 90


def kind_of(code):
    """'expr' when the whole snippet reads as one expression, else 'script'"""
    from xtalk.parser import parse_expr
    if '\n' in code:
        return 'script'
    try:
        parse_expr(code)
        return 'expr'
    except Exception:                                # noqa: BLE001
        return 'script'


def run_interp(kind, code):
    from xtalk import Interp
    from xtalk.interp import Frame
    from xtalk.parser import parse_statements
    it = Interp()
    try:
        if kind == 'expr':
            return str(it.eval(code))
        fr = Frame([])
        it.exec_block(parse_statements(code), fr)
        return str(fr.vars.get('tout', ''))
    except Exception:                                # noqa: BLE001  any error: ERR, as golden.json stores it
        return 'ERR'


def run_translated(kind, code, fast):
    from xtalk import pyrt
    from xtalk.pyrt import Runtime
    from xtalk.interp import Frame
    from xtalk.transpile import translate_statements
    env = {k: getattr(pyrt, k) for k in dir(pyrt) if not k.startswith('__')}
    try:
        src = code if kind == 'script' else 'put (%s) into tout' % code
        exec(translate_statements(src, fast=fast) if fast else translate_statements(src), env)
        fr = Frame([])
        env['_body'](Runtime(), fr)
        v = fr.vars.get('tout', '')
        return '' if isinstance(v, dict) else pyrt.to_text(v)
    except Exception:                                # noqa: BLE001
        return 'ERR'


def run_livecode(kind, code):
    """(answer, None) or (None, why not asked). One call, never retried."""
    import base64
    b = base64.b64encode(code.encode('utf-8')).decode()
    body = 'put value(tCode) into tOut' if kind == 'expr' else 'do tCode'
    stmts = ('put textDecode(base64Decode("%s"), "UTF-8") into tCode\nput empty into tOut\ntry\n  %s\n'
             'catch tErr\n  put "ERR" into tOut\nend try\nreturn base64Encode(textEncode(tOut, "UTF-8"))') % (b, body)
    try:
        r = subprocess.run([LCMCP, '--standalone', 'run', '--server', stmts], capture_output=True, text=True,
                           timeout=LC_TIMEOUT, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return None, 'no answer in %d s' % LC_TIMEOUT
    except OSError as e:
        return None, str(e)
    out = r.stdout.strip()
    if not out.startswith('result:'):
        return None, (out + ' ' + r.stderr.strip())[:200] or 'exit %d' % r.returncode
    return base64.b64decode(out[len('result:'):].strip()).decode('utf-8'), None


def diff(code, ask_lc=True):
    """-> (rows [(name, answer)], verdict text, status)"""
    code = code.replace(';;', '\n')
    kind = kind_of(code)
    rows = [('interpreter', run_interp(kind, code)), ('translated', run_translated(kind, code, False)),
            ('fast mode', run_translated(kind, code, True))]
    lc, why = run_livecode(kind, code) if ask_lc else (None, 'left out (--no-lc)')
    rows.append(('LiveCode', lc if lc is not None else 'not asked: %s' % why))
    if lc is None:
        same = len(set(r[1] for r in rows[:3])) == 1
        verdict = 'the Python answers %s; LiveCode not asked' % ('agree' if same else 'DIFFER')
        if not ask_lc:                               # left out on purpose: the status is the Python verdict
            return rows, kind, verdict, 0 if same else 1
        return rows, kind, verdict, 2
    off = [n for n, v in rows[:3] if v != lc]
    if not off:
        return rows, kind, 'AGREE', 0
    return rows, kind, 'DIFFER from LiveCode: ' + ', '.join(off), 1


def fact_line(code, kind, lc):
    show = code.replace('\n', '; ')
    return '- `%s`%s = `%s` (measured %s, standalone 9.6.3, xtpy diff)' % (
        show, '' if kind == 'expr' else ' (tOut)', lc, time.strftime('%d %b %Y'))


def main(a):
    if not a or a[0] in ('-h', '--help'):
        sys.exit(__doc__)
    ask_lc = '--no-lc' not in a
    fact = '--fact' in a
    a = [x for x in a if x not in ('--no-lc', '--fact')]
    code = ' '.join(a)
    rows, kind, verdict, status = diff(code, ask_lc)
    print('%s: %s' % ('expression' if kind == 'expr' else 'statements (answer = tOut)', code))
    for name, v in rows:
        print('  %-12s %s' % (name, v.replace('\n', '\\n')))
    print(verdict)
    if fact and status != 2:
        print(fact_line(code.replace(';;', '\n'), kind, rows[-1][1]))
    return status


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
