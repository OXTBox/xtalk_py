#!/usr/bin/env python3
"""tests for xtpy (x1-12): xtalk/session.py steps and tools/xtpy.py, two at once.

    python3 -I tests/test_xtpy.py           the session on tests/stacks/mini (no window, standard library only)
    .venv/bin/python -I tests/test_xtpy.py  the same, plus tools/xtpy runs: two at once, serve mode, a game
"""
import base64, json, os, subprocess, sys, time

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
s.step('run set the script of this card to "on arrowKey k" & cr & "global gK" & cr & "put k after gK" & cr & "end arrowKey"')
s.step('key left')
s.step('key down')
check('key left / down: rawKeyDown, then arrowKey (as the window)', s.step('eval gK'), (True, 'leftdown'))
check('a session starts no programs (shell, launch only noted)', s.rt.start_programs, False)
folder = s.folder
s.close()
check('close removes the session folder', os.path.isdir(folder), False)

sys.path.insert(0, os.path.join(ROOT, 'tools'))
import xtpy_diff   # noqa: E402
rows, kind, verdict, status = xtpy_diff.diff('7 mod -3', ask_lc=False)
check('diff: an expression, three Python answers, LiveCode left out',
      (kind, [v for _, v in rows[:3]], status), ('expr', ['1', '1', '1'], 0))
rows, kind, verdict, status = xtpy_diff.diff('put "a,b" into x;; put item 2 of x into tOut', ask_lc=False)
check('diff: statements answer with tOut', (kind, [v for _, v in rows[:3]]), ('script', ['b', 'b', 'b']))
check('diff: an error is ERR', [v for _, v in xtpy_diff.diff('1/0', ask_lc=False)[0][:3]], ['ERR'] * 3)
check('diff: the fact line', xtpy_diff.fact_line('7 mod -3', 'expr', '1').split(' (measured')[0], '- `7 mod -3` = `1`')

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

    # x1-14: the MCP pack through LIB_MCP's server (plain python3, as LM Studio / Claude Code start it)
    server = os.path.expanduser('~/projects/LIB_MCP/python/lib_mcp/mcp_server.py')
    if os.path.isfile(server):
        msgs = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
                {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'xtpy_open', 'arguments': {'target': MINI}}},
                {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'xtpy_eval', 'arguments': {'expression': '6 * 7'}}},
                {'jsonrpc': '2.0', 'id': 5, 'method': 'tools/call', 'params': {'name': 'xtpy_run', 'arguments': {'code': 'global gA\nput 5 into gA'}}},
                {'jsonrpc': '2.0', 'id': 6, 'method': 'tools/call', 'params': {'name': 'xtpy_eval', 'arguments': {'session': '1', 'expression': 'gA'}}},
                {'jsonrpc': '2.0', 'id': 7, 'method': 'tools/call', 'params': {'name': 'xtpy_snap', 'arguments': {}}},
                {'jsonrpc': '2.0', 'id': 8, 'method': 'tools/call', 'params': {'name': 'xtpy_close', 'arguments': {}}},
                {'jsonrpc': '2.0', 'id': 9, 'method': 'tools/call', 'params': {'name': 'xtpy_diff', 'arguments': {'code': '7 mod -3'}}}]
        p = subprocess.run(['python3', '-I', server, '--tools', os.path.join(ROOT, 'mcp', 'xtpy_tools.py')],
                           input=''.join(json.dumps(m) + '\n' for m in msgs), capture_output=True, text=True, timeout=300)
        r = {m['id']: m.get('result', {}) for m in map(json.loads, p.stdout.splitlines())}
        names = [t['name'] for t in r[2].get('tools', [])]
        check('mcp: the pack\'s tools are listed', all(n in names for n in ('xtpy_primer', 'xtpy_open', 'xtpy_eval', 'xtpy_game')), True)
        txt = lambda i: r[i]['content'][0].get('text', '')  # noqa: E731
        check('mcp: open, eval, run + eval a global', (txt(3)[:9], txt(4), txt(6)), ('session 1', '42', '5'))
        check('mcp: snap is a PNG picture', (r[7]['content'][0]['type'], base64.b64decode(r[7]['content'][0]['data'])[:4]),
              ('image', b'\x89PNG'))
        check('mcp: close; diff without LiveCode', (txt(8)[:6], 'the Python answers agree' in txt(9)), ('closed', True))
        p = subprocess.run(['python3', '-I', os.path.join(ROOT, 'mcp', 'xtpy_server.py')], capture_output=True, text=True,
                           timeout=60, input=json.dumps(msgs[0]) + '\n' + json.dumps(msgs[1]) + '\n')
        r = [json.loads(x)['result'] for x in p.stdout.splitlines()]
        names = [t['name'] for t in r[1]['tools']]
        check('xtpy_server: its own name, xtpy tools only (no livecode_*)',
              (r[0]['serverInfo']['name'], 'xtpy_open' in names, any(n.startswith('livecode') for n in names)),
              ('xtpy', True, False))

print('%d of %d xtpy checks pass' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
