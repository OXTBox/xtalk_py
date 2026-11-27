#!/usr/bin/env python3
"""open_stack.py - open a harvested stack in the Python runtime (Phase 2). Needs the .venv packages.

    .venv/bin/python -I tools/open_stack.py HARVEST_FOLDER                  a window at 200,32; click away
        (scaled: XTALK_SCALE=1.5, else Ctrl + / Ctrl - in the window, remembered in run_files/window_scale.json)
    ... HARVEST_FOLDER --engine "V:/Program Files (x86)/Vibecode3D" [-- ARGS]
        specialFolderPath("engine") (where a standalone sits) and the stack's command line ($1, $2...)
    .venv/bin/python -I tools/open_stack.py HARVEST_FOLDER --snap OUT.png [--click 'button "OK"' ...]
                                                                           hidden: click, then save the card

Files the stack writes (specialFolderPath("Documents")...) land in xtalk_py/run_files/, never in yours.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

GAMES = os.path.expanduser('~/projects/LIB_GAMES/Vibecode3D_Games')


def second_copy(harvest, engine, args):
    """the stack starts itself again (a standalone's second copy: the Library's Play, -game <folder>).
    INTERIM (26 Nov, x1-02 step 1): a game folder opens the Python play window (tools/play_xt3d.sh) on the
    game's LIB_GAMES copy, through the xt3d test bench host, not the installed copy through game_player
    (that needs create stack / set the script of stack in the runtime: step 2). Anything else: this program
    again, in its own window, with those arguments."""
    import subprocess
    from xtalk.stack.host import StackHost
    game = args[1] if len(args) >= 2 and args[0].lower() == '-game' else None
    if game is None and len(args) == 1 and os.path.isfile(os.path.join(StackHost.real_path(args[0].replace('\\', '/')), 'game.txt')):
        game = args[0]                         # just <folder> (launch <folder> with <program>, LiveCode on Linux)
    if game is not None:
        folder = StackHost.real_path(game.replace('\\', '/'))
        script = ''
        try:
            for line in open(os.path.join(folder, 'game.txt'), encoding='utf-8', errors='replace'):
                k, _, v = line.replace('\t', ' ').strip().partition(' ')
                if k.lower() in ('script', 'script:', 'script='):
                    script = v.strip().lstrip(':=').strip()
        except OSError as e:
            print('play: no game.txt in', folder, e, flush=True)
            return
        name = script[len('Vibecode3D_Play_'):] if script.startswith('Vibecode3D_Play_') else script
        name = os.path.splitext(name)[0]
        if not name or not os.path.isfile(os.path.join(GAMES, script)):
            print('play: no LIB_GAMES copy of', script or folder, flush=True)
            return
        print('play (interim, LIB_GAMES copy):', name, flush=True)
        subprocess.Popen([os.path.join(ROOT, 'tools', 'play_xt3d.sh'), name], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return
    cmd = [os.path.join(ROOT, '.venv', 'bin', 'python'), '-I', os.path.join(ROOT, 'tools', 'open_stack.py'), harvest]
    if engine:
        cmd += ['--engine', engine]
    subprocess.Popen(cmd + ['--'] + list(args), cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def main(a):
    if not a:
        sys.exit(__doc__)
    args = []
    if '--' in a:                          # after --: the stack's own command line ($1, $2...)
        i = a.index('--')
        a, args = a[:i], a[i + 1:]
    engine = ''
    if '--engine' in a:                    # specialFolderPath("engine"): where this program "is installed"
        i = a.index('--engine')
        engine = a[i + 1]
        del a[i:i + 2]
    import xtalk.interp
    xtalk.interp.ARGS[:] = args
    if '--snap' not in a and not os.environ.get('XTALK_KEEP_WAYLAND'):
        os.environ['WAYLAND_DISPLAY'] = 'no-wayland'   # GLFW falls back to X11 under WSLg: the window can be placed at 200,32
    from xtalk.stack import StackRuntime
    from xtalk.stack.view import View
    rt = StackRuntime(a[0], real_app='--snap' not in a)   # his window: a real app (his files, shell: owner 26 Nov)
    if engine:
        rt.host.folders['engine'] = engine
    rt.on_self_launch = lambda args2: second_copy(a[0], engine, args2)
    if '--snap' in a:
        out = a[a.index('--snap') + 1]
        try:
            snap_scale = float(os.environ.get('XTALK_SCALE', '1'))
        except ValueError:
            snap_scale = 1.0
        v = View(rt, hidden=True, scale=snap_scale)
        rt.open()
        i = 0
        while '--click' in a[i:]:
            i = a.index('--click', i) + 1
            rt.click(a[i])
        v.snapshot(out)
        v.close()
        for e in rt.errors:
            print('script error:', *e)
        print('saved', out)
        return
    import time
    t0 = time.time()
    rt.log_clicks = []                     # what was clicked, for the report at the end
    from xtalk.stack.view import window_scale, remember_scale
    name = rt.default_stack.name
    v = View(rt, scale=window_scale(name))   # our scaleFactor: Windows' own (125% -> 1.25) or the remembered one
    v.on_scale = lambda s: remember_scale(name, s)
    print('scale %.2f (Ctrl + bigger, Ctrl - smaller, Ctrl 0 = Windows\' scaling; remembered per stack)' % v.scale, flush=True)
    v.run()
    keys = sum(1 for c in rt.log_clicks if c.startswith('key '))
    print('--- report: window open %.0f s, %d clicks, %d keys' % (time.time() - t0, len(rt.log_clicks) - keys, keys))
    for c in rt.log_clicks[-60:]:
        print('  ', c)
    for e in rt.errors:
        print('script error:', *e)
    for o, e in rt.load_errors:
        print('does not compile:', o, e)
    for m in rt.menus[-10:]:
        print('menu shown:', m)
    for p in rt.not_started + [' '.join(map(str, p.args)) for p in rt.started]:
        print('program:', p)

if __name__ == '__main__':
    main(sys.argv[1:])
