"""uDead's red target dots (the owner's 2008 design, LIB_GAMES branch udead-grid-dots): do they show in the picture?

    .venv/bin/python -I tools/udead_dots_check.py [GAME] [--mode 0|3]

GAME: uDead_CullTest (default) or uDead. A hidden window plays the game on the bench's test clock; after the loading
screen (and hiding mode --mode, a key) it checks, each in the game's own image "view" (never the screen):
  1. three real clicks = three zombies sent to one cell: one shared map ("Oc..."), three dots;
  2. ground: a zombie sent to another zombie's spot, the camera 1.6 m off it: red pixels before / after;
  3. person: one zombie sent at a living person, the camera looking down at their feet: red pixels before / after,
     and the person's map made again when they move a cell;
  4. door: one zombie sent at door 1 (as a door click does): the door's red pixels before / after.
Orders 2-4 are written into the game's state (the camera aims at no particular thing in a test).
Prints PASS / FAIL a check; exit code 1 when one fails.
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import bench_xt3d as B                                        # noqa: E402
from xt3d_game_check import make_stack, HOST                 # noqa: E402
from xtalk import interp                                     # noqa: E402
from xtalk.stack import StackRuntime                         # noqa: E402
from xtalk.stack.view import View, rl                        # noqa: E402

NL = chr(10)


def main(a):
    game = a[0] if a and not a[0].startswith('--') else 'uDead_CullTest'
    mode = a[a.index('--mode') + 1] if '--mode' in a else '0'
    import random
    random.seed(1)
    w, h = 720, 540
    folder = os.path.join(ROOT, 'run_files', 'xt3d_dots_check')
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
    rt.message(card, 'xbPlayGame', [game])
    ud = [c for c in rt.ctx.values() if 'kcellm' in c.S][0]
    S = ud.S
    frame = [0]
    results = []

    def step(n=1, keys=()):
        for _ in range(n):
            codes = [ord(k) for k in keys]
            for c in codes:
                rt.raw_key(c)
            rt.test_keys = codes
            rt.held_codes, rt.keys_down, rt.buttons_down = codes, set(), set()
            rt.mouse_move(w // 2, h // 2)
            rl.begin_drawing()
            v.draw_card()
            rl.end_drawing()
            rt.tick(B.FRAME_MS)
            frame[0] += 1

    def keys(x):
        return list(x.keys()) if hasattr(x, 'keys') else []

    def num(x):
        return float(str(x))

    def red():
        d = rt.host.resolve('image "view"', must=False).imagedata.encode('latin-1')
        n = 0
        for i in range(0, len(d), 4):
            r, g, b = d[i + 1], d[i + 2], d[i + 3]
            if r > 170 and g < 110 and b < 110 and r > g + 90:
                n += 1
        return n

    def check(name, ok, info):
        results.append(ok)
        print('%s  %s  (%s)' % ('PASS' if ok else 'FAIL', name, info))

    def place(x, z, yaw, pitch):
        rt.message(ud.obj, 'uDead.TestPlace', [str(x), str(z), str(yaw), str(pitch)])

    def free_zombies():
        se = S['se']
        return [z for z in str(S['sz']).split(NL) if z and str(se[z]['order']) == ''
                and str(se[z]['state']) == 'alive']

    def clear_orders():
        se = S['se']
        for z in str(S['sz']).split(NL):
            if z:
                se[z]['order'] = ''
                se[z]['target'] = ''

    step(240)
    if mode != '0':
        step(6, keys=mode)
        step(4)
    # 1. three real clicks
    for _ in range(3):
        rt.message(ud.obj, 'Game.OnClick', ['360', '270', '1'])
        step(6)
    jobs = [k for k in keys(S['sjob']) if str(k).startswith('O')]
    check('three clicks: one shared map, three dots', len(jobs) == 1 and len(keys(S['sdot'])) == 3,
          'maps %s, dots %d' % (jobs, len(keys(S['sdot']))))
    clear_orders()
    step(3)
    # 2. ground: a cell 1.6 m ahead of the camera (looking along +Z, down at it)
    se = S['se']
    fz = free_zombies()                     # the spot: where one zombie stands; the walker: one at least 2 m off
    zx, zz = num(se[fz[0]]['x']), num(se[fz[0]]['z'])
    z = [y for y in fz[1:] if abs(num(se[y]['x']) - zx) + abs(num(se[y]['z']) - zz) > 2][0]
    place(zx, zz - 1.6, 0, -math.atan2(1.15, 1.6))
    step(3)
    before = red()
    se[z]['order'] = 'goto'
    se[z]['gx'], se[z]['gz'] = str(zx), str(zz)
    step(3)
    after = red()
    check('ground dot shows', after > before, 'red pixels %d -> %d' % (before, after))
    clear_orders()
    step(3)
    # 3. person: the camera 1.6 m off, looking down at the feet
    hs = [p for p in str(S['sh']).split(NL) if p and str(se[p]['state']) == 'alive']
    p = hs[0]
    px, pz = num(se[p]['x']), num(se[p]['z'])
    place(px, pz - 1.6, 0, -math.atan2(1.15, 1.6))
    step(3)
    before = red()
    zs = free_zombies()[:2]
    for z in zs:
        se[z]['order'] = 'attack'
        se[z]['target'] = p
    step(3)
    after = red()
    check('person dots show (two zombies)', after > before and len(keys(S['sdot'])) == 2,
          'red pixels %d -> %d, dots %d' % (before, after, len(keys(S['sdot']))))
    step(20)
    made = str(S['sjob']['Op' + p]['made'])
    se[p]['x'] = str(num(se[p]['x']) + 0.6)
    step(40)
    made2 = str(S['sjob']['Op' + p]['made']) if 'Op' + p in keys(S['sjob']) else 'gone'
    check("person's map made again after a move", made2 not in (made, 'gone'), 'made %s -> %s' % (made, made2))
    clear_orders()
    step(3)
    # 4. door 1: the camera 2 m off, looking along +Z at it
    d = S['sdoor']['1']
    dx, dz = num(d['x']), num(d['z'])
    place(dx, dz - 2.0, 0, -0.25)
    step(3)
    before = red()
    z = free_zombies()[0]
    se[z]['order'] = 'goto'
    se[z]['gx'], se[z]['gz'] = str(dx), str(dz)
    step(3)
    after = red()
    check('door %s turns red' % d['kind'], after > before and str(S['sdoorred']['1']) == 'true',
          'red pixels %d -> %d' % (before, after))
    clear_orders()
    step(3)
    check('door back to its own colour', str(S['sdoorred']['1']) == 'false', 'sDoorRed %s' % S['sdoorred']['1'])
    check('no script errors', not rt.errors, rt.errors[:1])
    print('%s %s mode %s: %s' % (game, frame[0], mode, 'PASS' if all(results) else 'FAIL'))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
