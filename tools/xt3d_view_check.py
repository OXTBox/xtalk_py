#!/usr/bin/env python3
"""xt3d_view_check.py - run an xt3d demo script unchanged in the Python runtime (Phase 3 step 5, first target).

    .venv/bin/python -I tools/xt3d_view_check.py [OUT.png] [--frames N] [--model PATH]

Makes a one-card stack in run_files/xt3d_view/ whose card script is the bridge's
demos/xt3d_view_demo.livecodescript (read from the bridge project, never changed), answers its
"choose a model" dialog with the bridge's test model, sends xt3dStart, runs N frames in a hidden
window (the 3D view is drawn inside the image "xt3dView", as the owner wants for test stacks) and
saves a snapshot (default run_files/xt3d_view.png). Prints script errors and the frames a second.
"""
import json, os, shutil, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
BRIDGE = os.path.expanduser('~/projects/xt3D_Raylib_Livecode_Bridge')
DEMO = os.path.join(BRIDGE, 'demos', 'xt3d_view_demo.livecodescript')
MODEL = os.path.join(BRIDGE, 'test_models', 'skinned_bend.glb')


def make_stack(folder, script_path, w=660, h=500):
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(os.path.join(folder, 'scripts'))
    shutil.copy(script_path, os.path.join(folder, 'scripts', 'xt3dView__card_1002.livecodescript'))
    stack = {'type': 'stack', 'name': 'xt3dView', 'id': 1001, 'role': 'main', 'rect': [200, 32, 200 + w, 32 + h],
             'size': [w, h], 'effective': {'textFont': 'Segoe UI', 'textSize': 12},
             'cards': [{'type': 'card', 'name': 'View', 'id': 1002, 'number': 1, 'controls': [],
                        'script': {'file': 'scripts/xt3dView__card_1002.livecodescript'}}]}
    json.dump(stack, open(os.path.join(folder, 'stack_xt3dView.json'), 'w'), indent=1)
    json.dump({'format': 'livecode-harvest', 'formatVersion': 2, 'mainStack': 'xt3dView',
               'note': 'made by tools/xt3d_view_check.py: the xt3d view demo script on one card',
               'stacks': [{'name': 'xt3dView', 'role': 'main', 'file': 'stack_xt3dView.json', 'cards': 1,
                           'controls': 0}], 'typeDefaults': {}, 'errors': []},
              open(os.path.join(folder, 'manifest.json'), 'w'), indent=1)


def main(a):
    out = a[0] if a and not a[0].startswith('--') else os.path.join(ROOT, 'run_files', 'xt3d_view.png')
    frames = int(a[a.index('--frames') + 1]) if '--frames' in a else 60
    model = a[a.index('--model') + 1] if '--model' in a else MODEL
    folder = os.path.join(ROOT, 'run_files', 'xt3d_view')
    make_stack(folder, DEMO)
    from xtalk.stack import StackRuntime
    from xtalk.stack.view import View
    rt = StackRuntime(folder, real_folders=True)
    rt.dialog_answers = [model]
    v = View(rt, hidden=True)
    rt.open()
    card = rt.default_stack.children[0]
    rt.message(card, 'xt3dStart')
    t0 = time.perf_counter()
    for _ in range(frames):
        v.frame()
    dt = time.perf_counter() - t0
    v.snapshot(out)
    rt.message(card, 'xt3dStop')
    v.close()
    for e in rt.errors:
        print('script error:', *e)
    for o, e in rt.load_errors:
        print('does not compile:', o, e)
    print('%d frames in %.2f s (%.0f a second); saved %s' % (frames, dt, frames / dt, out))


if __name__ == '__main__':
    main(sys.argv[1:])
