"""games_survey.py - play every Vibecode3D game in Python (hidden window) and list what breaks.

    .venv/bin/python -I tools/games_survey.py                  every LIB_GAMES/Vibecode3D_Games/Vibecode3D_Play_*.livecodescript
    .venv/bin/python -I tools/games_survey.py NAME [NAME...]   just these (Name as in Vibecode3D_Play_<Name>)
    .venv/bin/python -I tools/games_survey.py --jobs 4 --frames 600 --timeout 300
    .venv/bin/python -I tools/games_survey.py --one NAME       (one game, one JSON line: what the others run)

Each game runs in its own process, through the same test host as uDead (xt3d testbench, xbPlayGame), on the bench's
test clock (the same run every time). The play, the same for every game: nothing until frame 240 (loading screens),
Return at 250, Space at 256, then W held (walk / thrust), left arrow 330-360, right 450-480, Space taps every 60
frames, a left click in the middle every 90 frames, from frame 270 on. No real mouse (gNoMouse).

It records: did it start, script errors at load and while playing (grouped by cause), errors a script caught itself
(try/catch), frames played, game step / scene / draw milliseconds, frames a second, and how much of the picture is
not black at the end. The full list goes to run_files/games_survey.txt (the JSON lines to games_survey.jsonl);
the screen gets one line a game and the most common causes over all games.
"""
import collections
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
GAMES = os.path.expanduser('~/projects/LIB_GAMES/Vibecode3D_Games')
OUT = os.path.join(ROOT, 'run_files')


def opt(a, name, default):
    return a[a.index(name) + 1] if name in a else default


def cause(text):
    """an error with the parts that differ (numbers, quoted names) blurred, so one cause counts once"""
    t = re.sub(r'"[^"]*"', '"…"', str(text))
    t = re.sub(r"'[^']*'", "'…'", t)
    return re.sub(r'\b\d+(\.\d+)?\b', 'N', t)[:140]


def keys_at(i):
    k = []
    if i == 250:
        k.append(65293)                  # Return
    if i == 256 or (i >= 270 and i % 60 == 0):
        k.append(32)                     # Space
    if i >= 270:
        k.append(ord('w'))
    if 330 <= i < 360:
        k.append(65361)
    if 450 <= i < 480:
        k.append(65363)
    return k


def one(name, frames):
    """play one game; returns a dict (printed as one JSON line)"""
    import bench_xt3d as B
    from xt3d_game_check import make_stack, HOST
    from xtalk import interp
    from xtalk.interp import Interp
    Interp.CATCH_LOG = []
    from xtalk.stack import StackRuntime
    from xtalk.stack.view import View, rl
    from xtalk.stack.runtime import ObjInterp as StackContext
    import random
    random.seed(1)
    r = {'game': name, 'started': False, 'frames': 0}
    w, h = 720, 540
    folder = os.path.join(OUT, 'games_survey_host', name)
    make_stack(folder, w, h)
    rt = StackRuntime(folder, real_folders=True)
    clock = {'ms': B.START_MS}

    def test_clock():
        clock['ms'] = max(clock['ms'] + B.READ_MS, B.START_MS + rt.clock)
        return clock['ms']
    interp.CLOCK[0] = test_clock
    rt.harvest.main.filename = HOST
    rt.G['gxbviewrect'] = '0,0,%d,%d' % (w, h)
    rt.G['gnomouse'] = 'true'
    v = View(rt, hidden=True)
    rt.open()
    card = rt.default_stack.children[0]
    spent = {'vibe.step': 0.0, 'vibe.frame': 0.0, 'xbdrawgame': 0.0}
    inside = set()
    plain = StackContext.invoke

    def timed(self, n, args):
        k = n.lower()
        if k not in spent or k in inside:
            return plain(self, n, args)
        inside.add(k)
        t = time.perf_counter()
        try:
            return plain(self, n, args)
        finally:
            inside.discard(k)
            spent[k] += time.perf_counter() - t
    StackContext.invoke = timed
    t0 = time.perf_counter()
    try:
        rt.message(card, 'xbPlayGame', [name])
        r['started'] = True
    except Exception as e:
        r['crash'] = '%s: %s' % (type(e).__name__, e)
    r['start_s'] = round(time.perf_counter() - t0, 2)
    r['load_errors'] = [[str(x) for x in e] for e in rt.load_errors]
    held = []
    t_all = time.perf_counter()
    if r['started']:
        try:
            for i in range(frames):
                now = keys_at(i)
                for c in now:
                    if c not in held:
                        rt.raw_key(c)
                held = now
                rt.test_keys = list(now)
                rt.held_codes, rt.keys_down, rt.buttons_down = list(now), set(), set()
                rt.mouse_move(w // 2, h // 2)
                if i >= 270 and i % 90 == 0:
                    rt.mouse_down(w // 2, h // 2, 1)
                    rt.mouse_up(w // 2, h // 2, 1)
                rl.begin_drawing()
                v.draw_card()
                rl.end_drawing()
                rt.tick(B.FRAME_MS)
                r['frames'] = i + 1
                if i % 30 == 0:
                    print('frame %d' % i, file=sys.stderr, flush=True)
                if rt.closed:
                    r['closed_at'] = i + 1
                    break
        except Exception as e:
            r['crash'] = '%s: %s' % (type(e).__name__, e)
    wall = time.perf_counter() - t_all
    n = max(1, r['frames'])
    r['fps'] = round(n / wall, 1) if wall > 0 else 0
    r['step_ms'] = round(spent['vibe.step'] * 1000 / n, 2)
    r['scene_ms'] = round(spent['vibe.frame'] * 1000 / n, 2)
    r['draw_ms'] = round(spent['xbdrawgame'] * 1000 / n, 2)
    r['errors'] = [[str(x) for x in e] for e in rt.errors]
    r['caught'] = [str(x)[:300] for x in (Interp.CATCH_LOG or [])][:50]
    r['caught_n'] = len(Interp.CATCH_LOG or [])
    try:
        d = rt.host.resolve('image "view"', must=False).imagedata.encode('latin-1')
        lit = sum(1 for i in range(0, len(d), 4) if d[i + 1] | d[i + 2] | d[i + 3])
        r['lit_pct'] = round(100.0 * lit / max(1, len(d) // 4), 2)
    except Exception as e:
        r['lit_pct'] = None
        r['picture'] = str(e)[:200]
    return r


def run_one(name, frames, timeout):
    env = dict(os.environ)
    t = time.time()
    try:
        p = subprocess.run([sys.executable, '-I', os.path.abspath(__file__), '--one', name, '--frames', str(frames),
                            '--timeout', str(timeout)],
                           capture_output=True, text=True, timeout=timeout, env=env, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return {'game': name, 'timeout': timeout, 'started': None, 'frames': None}
    if p.returncode and 'Timeout (' in (p.stderr or ''):
        return {'game': name, 'timeout': timeout, 'started': None, 'frames': last_frame(p.stderr),
                'crash': 'hung: ' + hang_where(p.stderr)}
    for line in reversed(p.stdout.splitlines()):
        if line.startswith('{"game"'):
            r = json.loads(line)
            r['wall_s'] = round(time.time() - t, 1)
            return r
    tail = [x for x in (p.stderr or '').splitlines() if x.strip() and not x.startswith(('INFO', 'WARNING', 'libEGL', 'MESA'))]
    return {'game': name, 'started': None, 'frames': None, 'crash': 'process ended: ' + ' | '.join(tail[-3:])[:400]}


def last_frame(err):
    f = re.findall(r'^frame (\d+)$', err or '', re.M)
    return int(f[-1]) if f else 0


def hang_where(err):
    """the innermost lines of the dumped stack that are in translated scripts or the runtime"""
    st = (err or '')[(err or '').find('Timeout ('):]
    lines = [x.strip() for x in st.splitlines() if x.strip().startswith('File')]
    return ' <- '.join(re.sub(r'File ".*/', '', x) for x in lines[:6])[:500]


def verdict(r):
    if r.get('timeout'):
        return 'HANG'
    if r.get('crash'):
        return 'CRASH'
    if r.get('errors') or r.get('load_errors'):
        return 'ERRORS'
    if r.get('lit_pct') == 0:
        return 'BLACK'
    return 'ok'


def main(a):
    frames = int(opt(a, '--frames', 600))
    if '--one' in a:
        import faulthandler                  # a hang: say where, before the survey's time runs out
        faulthandler.dump_traceback_later(int(opt(a, '--timeout', 300)) - 15, exit=True)
        print(json.dumps(one(opt(a, '--one', ''), frames)))
        return 0
    names = [x for x in a if not x.startswith('--') and not x.isdigit()]
    if not names:
        names = sorted(f[len('Vibecode3D_Play_'):-len('.livecodescript')] for f in os.listdir(GAMES)
                       if f.startswith('Vibecode3D_Play_') and f.endswith('.livecodescript'))
    jobs, timeout = int(opt(a, '--jobs', 4)), int(opt(a, '--timeout', 300))
    print('games survey: %d games, %d frames each, %d at a time' % (len(names), frames, jobs), flush=True)
    results = []
    with ThreadPoolExecutor(jobs) as ex:
        for r in ex.map(lambda n: run_one(n, frames, timeout), names):
            results.append(r)
            print('%-7s %-32s frames %-4s fps %-5s step %-6s errors %-3s caught %-3s lit %s%%' % (
                verdict(r), r['game'], r.get('frames'), r.get('fps'), r.get('step_ms'),
                len(r.get('errors') or []) + len(r.get('load_errors') or []), r.get('caught_n'), r.get('lit_pct')),
                flush=True)
    stamp = time.strftime('%Y-%m-%d %H:%M')
    with open(os.path.join(OUT, 'games_survey.jsonl'), 'w') as f:
        for r in results:
            f.write(json.dumps(r) + '\n')
    causes, games_of = collections.Counter(), collections.defaultdict(set)
    lines = ['games survey %s: %d games, %d frames' % (stamp, len(results), frames)]
    for r in results:
        lines.append('\n==== %s  %s  frames %s  fps %s  step %s ms  scene %s ms  draw %s ms  lit %s%%' % (
            r['game'], verdict(r), r.get('frames'), r.get('fps'), r.get('step_ms'), r.get('scene_ms'),
            r.get('draw_ms'), r.get('lit_pct')))
        for k in ('crash', 'timeout', 'closed_at', 'picture'):
            if r.get(k):
                lines.append('  %s: %s' % (k, r[k]))
                if k == 'crash' or (k == 'timeout' and not r.get('crash')):
                    c = '(%s) %s' % (k, cause(r[k]))
                    causes[c] += 1
                    games_of[c].add(r['game'])
        for e in r.get('load_errors') or []:
            lines.append('  load error  %s' % ' | '.join(e))
            c = '(load) ' + cause(e[-1])
            causes[c] += 1
            games_of[c].add(r['game'])
        seen = collections.Counter()
        for e in r.get('errors') or []:
            seen[' | '.join(e)] += 1
            c = cause(e[-1])
            causes[c] += 1
            games_of[c].add(r['game'])
        for t, n in seen.most_common(15):
            lines.append('  error x%d  %s' % (n, t[:400]))
        for t in sorted(set(r.get('caught') or []))[:5]:
            lines.append('  caught  %s' % t[:300])
    lines.append('\n==== causes, by how many games they hit')
    for c, n in sorted(causes.items(), key=lambda x: (-len(games_of[x[0]]), -x[1])):
        lines.append('  %2d games  x%-5d %s   (%s)' % (len(games_of[c]), n, c, ', '.join(sorted(games_of[c]))[:300]))
    open(os.path.join(OUT, 'games_survey.txt'), 'w').write('\n'.join(lines) + '\n')
    v = collections.Counter(verdict(r) for r in results)
    print('\n' + ', '.join('%s %d' % kv for kv in v.most_common()))
    print('\n'.join(lines[lines.index('\n==== causes, by how many games they hit'):][:25]))
    print('full list: run_files/games_survey.txt')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
