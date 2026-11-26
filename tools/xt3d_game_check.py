#!/usr/bin/env python3
"""xt3d_game_check.py - play a Vibecode3D game through the xt3d testbench host, unchanged, in Python (Phase 3).

    .venv/bin/python -I tools/xt3d_game_check.py [GAME] [--frames N] [--keys "0:60,1:120"] [--snap OUT.png]
                                                 [--size 720x540] [--profile] [--eval 'expr;;expr']

GAME is a name in LIB_GAMES/Vibecode3D_Games (Vibecode3D_Play_<GAME>.livecodescript; default uDead_CullTest).
The host is the bridge's testbench/xt3d_testBench_lib_mcp.livecodescript (read from the bridge, never changed),
opened in its view-only mode (the global gXbViewRect: one image filling the window, as the owner wants for
games). It loads the engine's xt3d edition (testbench/vibe_engine_xt3d.livecodescript) with start using, then
xbPlayGame GAME. A hidden window runs N frames; --keys holds a key down from a frame on ("0:60" = the 0 key
from frame 60: uDead's culling modes are keys 0-3; a number is a key code, 65361 = left arrow; "-65361:90"
lets it go at frame 90). Prints the host's stats line (fps, step, scene, draw...)
each second of frames, script errors, and saves a snapshot (default run_files/xt3d_game.png).
"""
import json, os, shutil, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
BRIDGE = os.path.expanduser('~/projects/xt3D_Raylib_Livecode_Bridge')
HOST = os.path.join(BRIDGE, 'testbench', 'xt3d_testBench_lib_mcp.livecodescript')


def make_stack(folder, w, h):
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(os.path.join(folder, 'scripts'))
    shutil.copy(HOST, os.path.join(folder, 'scripts', 'host__stack.livecodescript'))
    stack = {'type': 'stack', 'name': 'xt3dTestBenchLibMCP', 'id': 1001, 'role': 'main', 'rect': [0, 0, w, h],
             'size': [w, h], 'effective': {'textFont': 'Segoe UI', 'textSize': 12},
             'script': {'file': 'scripts/host__stack.livecodescript'},
             'cards': [{'type': 'card', 'name': '', 'id': 1002, 'number': 1, 'controls': []}]}
    json.dump(stack, open(os.path.join(folder, 'stack_host.json'), 'w'), indent=1)
    json.dump({'format': 'livecode-harvest', 'formatVersion': 2, 'mainStack': 'xt3dTestBenchLibMCP',
               'note': 'made by tools/xt3d_game_check.py: the xt3d testbench host (script-only) as a stack',
               'stacks': [{'name': 'xt3dTestBenchLibMCP', 'role': 'main', 'file': 'stack_host.json', 'cards': 1,
                           'controls': 0}], 'typeDefaults': {}, 'errors': []},
              open(os.path.join(folder, 'manifest.json'), 'w'), indent=1)


def main(a):
    game = a[0] if a and not a[0].startswith('--') else 'uDead_CullTest'
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d       # noqa: E731
    frames = int(opt('--frames', 150))
    out = opt('--snap', os.path.join(ROOT, 'run_files', 'xt3d_game.png'))
    w, h = (int(x) for x in opt('--size', '720x540').split('x'))
    keys = []
    for k in opt('--keys', '').split(','):
        if k:
            key, at = k.split(':')
            keys.append((int(at), key))
    folder = os.path.join(ROOT, 'run_files', 'xt3d_bench')
    make_stack(folder, w, h)
    from xtalk.interp import Interp
    Interp.CATCH_LOG = []                      # errors the scripts' own try caught: printed at the end
    from xtalk.stack import StackRuntime
    from xtalk.stack.view import View
    t0 = time.perf_counter()
    rt = StackRuntime(folder, real_folders=True)
    rt.harvest.main.filename = HOST            # the effective filename: the host finds LIB_GAMES above it
    rt.G['gxbviewrect'] = '0,0,%d,%d' % (w, h)  # view-only mode
    v = View(rt, hidden=True)
    rt.open()
    card = rt.default_stack.children[0]
    t1 = time.perf_counter()
    rt.message(card, 'xbPlayGame', [game])
    t2 = time.perf_counter()
    print('host opened in %.2f s; %s started in %.2f s (engine load included)' % (t1 - t0, game, t2 - t1))
    prof = None
    if '--profile' in a:
        import cProfile
        prof = cProfile.Profile()
        prof.enable()
    t3 = time.perf_counter()
    for i in range(frames):
        for at, key in keys:
            if at == i:
                if key.startswith('-'):        # -65361:90 lets the key go at frame 90
                    code = int(key[1:])
                    rt.test_keys = [k for k in rt.test_keys if k != code]
                    continue
                code = ord(key) if len(key) == 1 else int(key)
                rt.test_keys = rt.test_keys + [code]
                rt.raw_key(code)
        v.frame()
        if i % 30 == 29:
            st = rt.ctx[id(rt.harvest.main)].invoke('xbGameStats', [])
            print('frame %4d  %s' % (i + 1, st))
    dt = time.perf_counter() - t3
    if prof is not None:
        prof.disable()
        import pstats
        pstats.Stats(prof).sort_stats('tottime').print_stats(25)
    v.snapshot(out)
    if '--eval' in a:                          # expressions asked of the game card (its path: stack, libraries)
        from xtalk.parser import parse_expr
        from xtalk.interp import Frame
        c = rt.ctx.get(id(card)) or rt.ctx[id(rt.harvest.main)]
        for ex in opt('--eval', '').split(';;'):
            fr = Frame([])
            fr.globals.update(rt.G.keys())     # every global the game made is visible
            try:
                print('eval %s = %r' % (ex, str(c.ev(parse_expr(ex), fr))[:400]))
            except Exception as e:             # noqa: BLE001
                print('eval %s: %s' % (ex, e))
    img = rt.host.resolve('image "view"', must=False)
    d = getattr(img, 'imagedata', None) if img is not None else None
    if d is not None:
        print('image "view": %d of %d pixels not black' % (sum(1 for i in range(1, len(d), 4)
                                                               if d[i] != '\x00' or d[i + 1] != '\x00' or d[i + 2] != '\x00'), len(d) // 4))
    for o in rt.default_stack.current.flat():
        print('  control %s %r rect %s visible %s blend %s' % (o.type, o.name, o.rect, o.props.get('visible', ''),
                                                           o.props.get('blendLevel', '')))
    info = rt.host.resolve('field "info"', must=False)
    rt.message(card, 'xbStopGame')
    v.close()
    if info is not None:
        print('info field:', info.text[:300].replace('\n', ' | '))
    from collections import Counter
    for t, n in Counter(Interp.CATCH_LOG).most_common(12):
        print('caught by a try (%dx): %s' % (n, t[:700]))
    for e in rt.errors[:20]:
        print('script error:', *e)
    for o, e in rt.load_errors[:20]:
        print('does not compile:', o, e)
    print('%d frames in %.2f s (%.1f a second); saved %s' % (frames, dt, frames / dt, out))


if __name__ == '__main__':
    main(sys.argv[1:])
