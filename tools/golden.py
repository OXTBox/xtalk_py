#!/usr/bin/env python3
"""golden.py - ask the real LiveCode 9.6.3 what each test case gives, write tests/golden.json.

    python3 -I tools/golden.py

Reads tests/expr_cases.txt (one expression a line) and tests/script_cases.txt (statements, blocks
split by a line of ----, each ends by putting its answer into tOut). LiveCode runs through
LIB_MCP's lcmcp standalone (starts itself). The interpreter's tests (tests/test_interp.py) compare
against this file, so the file is the referee and is committed.
"""
import base64, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LCMCP = os.path.expanduser('~/projects/LIB_MCP/tools/lcmcp')

def cases():
    ex = [l for l in open(os.path.join(ROOT, 'tests/expr_cases.txt'), encoding='utf-8').read().split('\n') if l.strip()]
    sc = [b.strip('\n') for b in open(os.path.join(ROOT, 'tests/script_cases.txt'), encoding='utf-8').read().split('\n----\n')]
    return ex, [s for s in sc if s.strip()]

def b64(s):
    return base64.b64encode(s.encode('utf-8')).decode()

def lc_run(kind, items):
    """one LiveCode run for a list of cases; returns [answer text or 'ERR: ...']"""
    enc = ','.join(b64(i) for i in items)
    body = 'value(tCode)' if kind == 'expr' else None
    stmts = '''put "%s" into tList
put empty into tAll
repeat for each item tB in tList
  put textDecode(base64Decode(tB), "UTF-8") into tCode
  put empty into tOut
  try
    %s
  catch tErr
    put "ERR" into tOut
  end try
  put base64Encode(textEncode(tOut, "UTF-8")) & "," after tAll
end repeat
return tAll''' % (enc, 'put value(tCode) into tOut' if kind == 'expr' else 'do tCode')
    r = subprocess.run([LCMCP, '--standalone', 'run', '--server', stmts], capture_output=True, text=True, timeout=600)
    out = r.stdout.strip()
    if not out.startswith('result:'):
        sys.exit('LiveCode run failed: ' + out + r.stderr)
    parts = out[len('result:'):].strip().rstrip(',').split(',')
    return [base64.b64decode(p).decode('utf-8') if p else '' for p in parts]

def lib_cases():
    out = {}
    for l in open(os.path.join(ROOT, 'tests/lib_cases.txt'), encoding='utf-8'):
        l = l.rstrip('\n')
        if l.strip() and not l.startswith('#') and '\t' in l:
            lib, e = l.split('\t', 1)
            out.setdefault(lib, []).append(e)
    return out

def lc_lib(lib, exprs):
    """expressions evaluated in LiveCode with the library loaded (start using stack <file>)"""
    path = subprocess.run(['wslpath', '-m', os.path.join(ROOT, 'corpus', lib)], capture_output=True, text=True).stdout.strip()
    enc = ','.join(b64(i) for i in exprs)
    stmts = '''put url "binfile:%s" into tLibText
put textDecode(tLibText, "UTF-8") into tLibText
if line 1 of tLibText begins with "script " then delete line 1 of tLibText
create invisible stack "xtLibTmp"
set the script of stack "xtLibTmp" to tLibText
start using stack "xtLibTmp"
put "%s" into tList
put empty into tAll
repeat for each item tB in tList
  put textDecode(base64Decode(tB), "UTF-8") into tCode
  try
    put value(tCode) into tOut
  catch tErr
    put "ERR" into tOut
  end try
  put base64Encode(textEncode(tOut, "UTF-8")) & "," after tAll
end repeat
return tAll''' % (path, enc)
    r = subprocess.run([LCMCP, '--standalone', 'run', '--server', stmts], capture_output=True, text=True, timeout=600)
    out = r.stdout.strip()
    if not out.startswith('result:'):
        sys.exit('LiveCode run failed: ' + out + r.stderr)
    parts = out[len('result:'):].strip().rstrip(',').split(',')
    return [base64.b64decode(p).decode('utf-8') if p else '' for p in parts]

def main():
    ex, sc = cases()
    gold = {'expr': {}, 'script': {}, 'lib': {}}
    for lib, exprs in lib_cases().items():
        gold['lib'][lib] = dict(zip(exprs, lc_lib(lib, exprs)))
    for case, ans in zip(ex, lc_run('expr', ex)):
        gold['expr'][case] = ans
    for case, ans in zip(sc, lc_run('script', sc)):
        gold['script'][case] = ans
    json.dump(gold, open(os.path.join(ROOT, 'tests/golden.json'), 'w'), indent=1, ensure_ascii=False)
    print('%d expressions, %d scripts, %d library calls -> tests/golden.json' % (len(ex), len(sc), sum(len(v) for v in gold['lib'].values())))

if __name__ == '__main__':
    main()
