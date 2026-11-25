#!/usr/bin/env python3
"""open_stack.py - open a harvested stack in the Python runtime (Phase 2). Needs the .venv packages.

    .venv/bin/python -I tools/open_stack.py HARVEST_FOLDER                  a window at 200,32; click away
    .venv/bin/python -I tools/open_stack.py HARVEST_FOLDER --snap OUT.png [--click 'button "OK"' ...]
                                                                           hidden: click, then save the card

Files the stack writes (specialFolderPath("Documents")...) land in xtalk_py/run_files/, never in yours.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

def main(a):
    if not a:
        sys.exit(__doc__)
    if '--snap' not in a and not os.environ.get('XTALK_KEEP_WAYLAND'):
        os.environ['WAYLAND_DISPLAY'] = 'no-wayland'   # GLFW falls back to X11 under WSLg: the window can be placed at 200,32
    from xtalk.stack import StackRuntime
    from xtalk.stack.view import View
    rt = StackRuntime(a[0], real_folders='--snap' not in a)   # his window: his real folders (writes sandboxed)
    if '--snap' in a:
        out = a[a.index('--snap') + 1]
        v = View(rt, hidden=True)
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
    View(rt).run()
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
