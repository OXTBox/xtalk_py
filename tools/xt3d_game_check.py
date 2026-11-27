#!/usr/bin/env python3
"""xt3d_game_check.py - play a Vibecode3D game through the xt3d testbench host, unchanged, in Python (Phase 3).

    .venv/bin/python -I tools/xt3d_game_check.py [GAME] [--frames N] [--keys "0:60,1:120"] [--snap OUT.png]
                                                 [--size 720x540] [--profile] [--eval 'expr;;expr']
    .venv/bin/python -I tools/xt3d_game_check.py [GAME] --window [--size 720x540]
                                                 a real window at 200,32 to play in; close it to stop
                                                 (tools/play_xt3d.sh is the owner's command for this)

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
    if '--window' in a:
        return play(game, folder, w, h)
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
    slow_ms = float(opt('--slow', '0') or 0)
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
        if slow_ms:                            # --slow MS: what ran in a frame that took longer than MS
            import cProfile, pstats, io
            fp = cProfile.Profile()
            f0 = time.perf_counter()
            fp.enable()
            v.frame()
            fp.disable()
            took = (time.perf_counter() - f0) * 1000
            if took > slow_ms:
                s = io.StringIO()
                st_ = pstats.Stats(fp, stream=s).sort_stats('cumulative')
                st_.print_stats(r'h_|native|helpers', 14)
                print('---- slow frame %d: %.0f ms' % (i + 1, took))
                print('\n'.join(l for l in s.getvalue().splitlines() if 'h_' in l or 'native' in l or 'helpers' in l))
        else:
            v.frame()
        if i % 30 == 29:
            st = rt.ctx[id(rt.harvest.main)].invoke('xbGameStats', [])
            print('frame %4d  %s' % (i + 1, st))
    dt = time.perf_counter() - t3
    if prof is not None:
        prof.disable()
        import pstats
        pstats.Stats(prof).sort_stats('tottime').print_stats(25)
        if os.environ.get("XTALK_PROF_OUT"): prof.dump_stats(os.environ["XTALK_PROF_OUT"])
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
    t4 = time.perf_counter()
    rt.message(card, 'xbStopGame')
    t5 = time.perf_counter()
    v.close()
    print('closing: xbStopGame %.2f s, View.close %.2f s' % (t5 - t4, time.perf_counter() - t5))
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


def play(game, folder, w, h):
    """The owner's window: the game plays until he closes it (or the game ends); a report goes to the end of
    what is printed. The close box is absolute: the report is written and the program ends at once, whatever
    the scripts are doing (no xbStopGame: the program ends, nothing is left to free). Escape frees the mouse
    and keys (the game plays on without them); Escape again gives them back."""
    if not os.environ.get('XTALK_KEEP_WAYLAND'):
        os.environ['WAYLAND_DISPLAY'] = 'no-wayland'   # GLFW falls back to X11 under WSLg: placed at 200,32
    from collections import Counter
    from xtalk.interp import Interp
    Interp.CATCH_LOG = []
    from xtalk.stack import StackRuntime
    from xtalk.stack.view import View
    from xtalk.stack.view import rl
    rt = StackRuntime(folder, real_app=True)   # his play window: a real app (owner 26 Nov)
    rt.harvest.main.filename = HOST
    rt.G['gxbviewrect'] = '0,0,%d,%d' % (w, h)
    rt.log_clicks = []
    test = dict(x.split(':') for x in os.environ.get('XTALK_PLAY_TEST', '').split(',') if ':' in x)
    v = View(rt, hidden=bool(test))      # XTALK_PLAY_TEST="note:100;150,close:300" (or end:300): a hidden check
    at = lambda k: str(n[0]) in test.get(k, '').split(';')   # noqa: E731 - this frame has a k: event
    pressed, real_pressed = set(), rl.is_key_pressed       # esc:N = Escape pressed at frame N, as the window
    rl.is_key_pressed = lambda k: k in pressed or real_pressed(k)   # sees it (View.frame decides who gets it)
    rt.on_wait, rt.on_menu, rt.on_dialog = v.wait_frames, v.menu_frames, v.dialog_frames
    v.esc_frees = True
    rt.open()
    card = rt.default_stack.children[0]
    info = rt.host.resolve('field "info"', must=False)
    stats, n, t1, slow = [], [0], [time.perf_counter()], [0.0]
    notes_file = os.path.join(ROOT, 'run_files', 'elsewhere') + os.path.expanduser('~/projects/LIB_LLMIN/LIB_GAMES/GAME_NOTES.txt')
    real_notes = os.path.expanduser('~/projects/LIB_LLMIN/LIB_GAMES/GAME_NOTES.txt')
    notes_before = ''                             # GameNotes (`) writes there: the scripts' writes stay in
    for f in (notes_file, real_notes):            # run_files/elsewhere (a copy of the real file, then the notes)
        if os.path.exists(f):
            notes_before = open(f, encoding='utf-8', errors='replace').read()
            break

    def report(why):
        dt = time.perf_counter() - t1[0]
        print('\n==== report ====')
        print('%s: %d frames in %.0f s (%.1f a second on average); %s' % (game, n[0], dt, n[0] / dt if dt else 0, why))
        print('longest frame %.2f s (the close box is seen at the end of a frame)' % slow[0])
        keys = Counter(c for c in rt.log_clicks if c.startswith('key '))
        print('keys pressed:', ', '.join('%s x%d' % kv for kv in keys.most_common(20)) or 'none')
        print('last stats:', stats[-1] if stats else 'none')
        print('mouse look:', ', '.join('%s %d' % kv for kv in v.look.items()),
              '(soft grab, speed %g, recentre %s)' % (v.look_speed, 'on' if v.recentre else 'OFF') if v.soft_grab
              else '(raylib grab)')
        print('camera yaw, pitch at the end:', rt.G.get('gcamerayaw', ''), rt.G.get('gcamerapitch', ''))
        if info is not None:
            print('info field:', info.text[:300].replace('\n', ' | '))
        for t, k in Counter(Interp.CATCH_LOG).most_common(12):
            print('caught by a try (%dx): %s' % (k, t[:700]))
        for e in rt.errors[:20]:
            print('script error:', *e)
        print('script errors: %d' % len(rt.errors))
        box = rt.host.resolve('field "GameNote"', must=False)
        if box is not None:
            print('note box at the end: %s; game paused %s; mouse and keys freed %s' % (
                'OPEN' if rt._shown(box) else 'closed', rt.G.get('bpaused', ''), v.freed))
        after = open(notes_file, encoding='utf-8', errors='replace').read() if os.path.exists(notes_file) else ''
        new = after[len(notes_before):] if after.startswith(notes_before) else after
        for line in new.splitlines():
            if line.strip():
                print('his note:', line)
        sys.stdout.flush()

    def closed():                                         # the close box, from any loop (View.after_frame)
        t = time.perf_counter()
        report('closed with the close box')
        print('report written in %.2f s; ending now' % (time.perf_counter() - t), flush=True)
        os._exit(0)
    v.on_close = closed
    t0 = time.perf_counter()
    rt.message(card, 'xbPlayGame', [game])
    print('%s started in %.2f s (engine load included)' % (game, time.perf_counter() - t0), flush=True)
    t1[0] = time.perf_counter()
    while not rt.closed:
        tf = time.perf_counter()
        if str(n[0]) in test.get('note', '').split(';'):   # the owner's note: ` , a line, Return (note:100;150)
            rt.raw_key(96)
            for ch in 'a note from the play test at frame %d' % n[0]:
                rt.key(ch)
            rt.special_key('return')
        if at('typenote'):                               # ` then a line typed (no Return): the box stays open
            rt.raw_key(96)
            for ch in 'typed at frame %d' % n[0]:
                rt.key(ch)
        if at('click'):                                  # click:N = a click in the middle of the view
            down = rt.mouse_down(w // 2, h // 2)
            rt.mouse_up(w // 2, h // 2, down_on=down)
        if at('esc'):
            pressed.add(rl.KEY_ESCAPE)
        if test.get('close') == str(n[0]):               # as if the close box was clicked
            rl.window_should_close = lambda: True
        if test.get('end') == str(n[0]):                 # as if the game ended itself
            rt.message(card, 'xbGameEnded')
        v.frame()
        pressed.clear()
        slow[0] = max(slow[0], time.perf_counter() - tf)
        n[0] += 1
        if n[0] % 60 == 0:
            try:
                st = rt.ctx[id(rt.harvest.main)].invoke('xbGameStats', [])
            except Exception as e:                        # noqa: BLE001
                st = 'stats: %s' % e
            stats.append(st)
            print('frame %5d  %s' % (n[0], st), flush=True)
        if info is not None and n[0] % 15 == 0 and not info.text.startswith('Playing'):
            break                                         # the game ended itself (or stopped with an error)
    report('the game ended: ' + (info.text.split('\n')[0] if info is not None else '?'))
    os._exit(0)


if __name__ == '__main__':
    main(sys.argv[1:])
