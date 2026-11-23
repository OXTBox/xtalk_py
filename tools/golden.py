#!/usr/bin/env python3
"""golden.py - ask the real LiveCode 9.6.3 what each test case gives, write tests/golden.json.

    python3 -I tools/golden.py

Reads tests/expr_cases.txt (one expression a line) and tests/script_cases.txt (statements, blocks
split by a line of ----, each ends by putting its answer into tOut). LiveCode runs through
LIB_MCP's lcmcp standalone (starts itself). The interpreter's tests (tests/test_interp.py) compare
against this file, so the file is the referee and is committed.
"""
import base64, hashlib, json, os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LCMCP = os.path.expanduser('~/projects/LIB_MCP/tools/lcmcp')
sys.path.insert(0, os.path.expanduser('~/projects/LIB_MCP/python'))
from lib_mcp.client import Client
HANG_LOG = os.path.join(ROOT, 'tools', 'golden_hangs.log')
GROUP_TIMEOUT = 90 + int(os.environ.get('LIBMCP_WAIT', 30))   # per engine+game group; includes the copy's start (LIBMCP_WAIT), first load ~10 s
BULK_TIMEOUT = 300       # expression / script batches
SLOT = [0]               # the copy in use now; engine+game groups alternate 0 / 1 (never more than two)

class Hang(Exception):
    pass

def log_hang(case, lib, seconds, timeout):
    with open(HANG_LOG, 'a', encoding='utf-8') as f:
        f.write('%s\tcase=%s\tlibrary=%s\tseconds=%.0f\tslot=%d\ttimeout=%d\n'
                % (time.strftime('%Y-%m-%d %H:%M:%S'), case.replace('\n', ' ')[:80], lib, seconds, SLOT[0], timeout))

def lcmcp_run(stmts, timeout, case, lib):
    """run on the current slot; on a hang: log it, end that copy, raise Hang"""
    env = dict(os.environ, LIBMCP_SLOT=str(SLOT[0]))
    t0 = time.time()
    try:
        r = subprocess.run([LCMCP, '--standalone', 'run', '--server', stmts], capture_output=True, text=True,
                           timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        log_hang(case, lib, time.time() - t0, timeout)
        Client.kill_slot(SLOT[0])
        raise Hang()
    return r

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
    r = lcmcp_run(stmts, BULK_TIMEOUT, '%s batch of %d, first: %s' % (kind, len(items), items[0]), '-')
    out = r.stdout.strip()
    if not out.startswith('result:'):
        sys.exit('LiveCode run failed: ' + out + r.stderr)
    parts = out[len('result:'):].strip()[:-1].split(',')   # drop the one closing comma only: rstrip ate empty last answers
    return [base64.b64decode(p).decode('utf-8') if p else '' for p in parts]

def lib_text(spec):
    """'a.livecodescript+b.txt' -> the files joined (under corpus/, or tests/... from the project root)"""
    parts = []
    for f in spec.split('+'):
        base = ROOT if f.startswith('tests/') else os.path.join(ROOT, 'corpus')
        t = open(os.path.join(base, f), encoding='utf-8', errors='replace').read()
        if t.startswith('script '):
            t = t.split('\n', 1)[1]
        parts.append(t)
    return '\n'.join(parts)

def lib_files(spec):
    """'engine|game+wrapper' -> one real file per library (LiveCode loads each as its own stack, in order)"""
    d = os.path.join(ROOT, 'tests', '.combined')
    os.makedirs(d, exist_ok=True)
    out = []
    for part in spec.split('|'):
        f = os.path.join(d, 'lib_%s.txt' % hashlib.md5(part.encode()).hexdigest()[:10])
        open(f, 'w', encoding='utf-8').write(lib_text(part))
        out.append(f)
    return out

def lib_cases():
    out = {}
    for l in open(os.path.join(ROOT, 'tests/lib_cases.txt'), encoding='utf-8'):
        l = l.rstrip('\n')
        if l.strip() and not l.startswith('#') and '\t' in l:
            lib, e = l.split('\t', 1)
            out.setdefault(lib, []).append(e)
    return out

def fresh_slot():
    """A second game library loaded in the same LiveCode session hangs it (measured 21 Nov), so every
    engine+game group gets a fresh copy: switch to the other slot (0 <-> 1), end whatever ran there, start anew.
    Never more than two copies exist (LIB_MCP refuses a third)."""
    SLOT[0] = 1 - SLOT[0]
    Client.kill_slot(SLOT[0])
    Client.standalone(slot=SLOT[0])

def lc_lib(lib, exprs):
    """expressions evaluated in LiveCode with the library loaded (start using stack <file>)"""
    paths = [subprocess.run(['wslpath', '-m', f], capture_output=True, text=True).stdout.strip() for f in lib_files(lib)]
    clean = '''repeat for each line tU in the stacksInUse
  stop using stack tU
end repeat
repeat for each line tU in the mainStacks
  if tU begins with "xtT" then delete stack tU
end repeat
'''
    load = clean + ''.join('''put url "binfile:%s" into tLibText
put textDecode(tLibText, "UTF-8") into tLibText
if line 1 of tLibText begins with "script " then delete line 1 of tLibText
create invisible stack "xtT%d"
set the script of stack "xtT%d" to tLibText
start using stack "xtT%d"
''' % (p, i, i, i) for i, p in enumerate(paths))
    unload = ''.join('stop using stack "xtT%d"\ndelete stack "xtT%d"\n' % (i, i) for i in range(len(paths)))
    enc = ','.join(b64(i) for i in exprs)
    stmts = '''repeat for each line tU in the stacksInUse
  stop using stack tU
end repeat
%s
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
%s
return tAll''' % (load, enc, unload)
    r = lcmcp_run(stmts, GROUP_TIMEOUT, '%d cases, first: %s' % (len(exprs), exprs[0]), lib)
    out = r.stdout.strip()
    if not out.startswith('result:'):
        sys.exit('LiveCode run failed: ' + out + r.stderr)
    parts = out[len('result:'):].strip()[:-1].split(',')   # drop the one closing comma only: rstrip ate empty last answers
    return [base64.b64decode(p).decode('utf-8') if p else '' for p in parts]

def main():
    ex, sc = cases()
    gold = {'expr': {}, 'script': {}, 'lib': {}}
    for lib, exprs in lib_cases().items():
        if '|' in lib:
            fresh_slot()
        try:
            ans = lc_lib(lib, exprs)
            if len(ans) != len(exprs):
                sys.exit('%s: %d answers for %d cases' % (lib, len(ans), len(exprs)))
            gold['lib'][lib] = dict(zip(exprs, ans))
        except Hang:
            print('HANG (logged, group skipped):', lib, flush=True)
            continue
        print('ok', lib, len(exprs), flush=True)
    Client.kill_slot(1 - SLOT[0])   # leave only one copy for the bulk runs
    for case, ans in zip(ex, lc_run('expr', ex)):
        gold['expr'][case] = ans
    for case, ans in zip(sc, lc_run('script', sc)):
        gold['script'][case] = ans
    json.dump(gold, open(os.path.join(ROOT, 'tests/golden.json'), 'w'), indent=1, ensure_ascii=False)
    print('%d expressions, %d scripts, %d library calls -> tests/golden.json' % (len(ex), len(sc), sum(len(v) for v in gold['lib'].values())))

if __name__ == '__main__':
    main()
