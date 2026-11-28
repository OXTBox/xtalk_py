#!/usr/bin/env python3
"""Graphic effects (x1-09, docs/SHADERS.md) on a HIDDEN window: the effect properties, a stack without effects
makes nothing, and the pixels of a glow, a drop shadow, an inner glow and a color overlay. Needs the .venv.

    .venv/bin/python -I tests/test_effects.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ['WAYLAND_DISPLAY'] = 'no-wayland'
from xtalk.stack import StackRuntime           # noqa: E402
from xtalk.stack.view import View, rl          # noqa: E402

N, BAD = [0], []
def check(name, got, want):
    N[0] += 1
    if got != want:
        BAD.append(name)
        print('FAIL  %s\n        want %r\n        got  %r' % (name, want, got))


MINI = os.path.join(ROOT, 'tests/stacks/mini')
rt = StackRuntime(MINI, files_dir=os.path.join(ROOT, 'run_files', 'test'))
v = View(rt, hidden=True)
rt.open()
SHOT = os.path.join(ROOT, 'run_files', 'test', 'effects.png')
os.makedirs(os.path.dirname(SHOT), exist_ok=True)


def pixels():
    """the window as drawn -> a function (x, y) -> (r, g, b)"""
    v.snapshot(SHOT)
    img = rl.load_image(SHOT)
    cols = rl.load_image_colors(img)
    w = img.width
    def at(x, y):
        c = cols[y * w + x]
        return (c.r, c.g, c.b)
    return at, (lambda: (rl.unload_image_colors(cols), rl.unload_image(img)))


def frame():
    rl.begin_drawing(); v.draw_card(); v.draw_panel(); rl.end_drawing()


# the properties
rt.run('set the backgroundColor of this card to "255,255,255"')
for c in ('button "B"', 'field "F"'):
    rt.run('hide %s' % c)
rt.run('hide group "Grp"')
rt.run('set the rect of graphic "G" to 100,60,160,120\nset the filled of graphic "G" to true\n'
       'set the backgroundColor of graphic "G" to "0,0,0"\nset the foregroundColor of graphic "G" to "0,0,0"')
frame()
check('no effects: no object looked after', len(v.fx.objs), 0)
check('no effects: no shader loaded, no texture', (v.fx.shaders, len(v.fx.cache)), (None, 0))
check('no effect: its size reads empty', rt.eval('the outerGlow["size"] of graphic "G"'), '')
rt.run('set the outerGlow["color"] of graphic "G" to "255,0,0"\nset the outerGlow["size"] of graphic "G" to 12\n'
       'set the outerGlow["opacity"] of graphic "G" to 255')
check('set one key, read it back', rt.eval('the outerGlow["size"] of graphic "G"'), '12')
check('the whole array', sorted(rt.eval('the keys of the outerGlow of graphic "G"').split('\n')), ['color', 'opacity', 'size'])
frame()
check('an effect: the object is looked after', len(v.fx.objs), 1)
at, free = pixels()
check('outer glow: red just outside the shape', at(161, 90)[0] == 255 and at(161, 90)[1] < 200, True)
check('outer glow: fades out', at(176, 90), (255, 255, 255))
check('outer glow: under the object (black stays black)', at(130, 90), (0, 0, 0))
free()
made = v.fx.cache[id(rt.obj('graphic "G"'))]['sig']
frame(); frame()
check('nothing changed: textures not made again', v.fx.cache[id(rt.obj('graphic "G"'))]['sig'] is made, True)
rt.run('set the outerGlow of graphic "G" to empty')
frame()
check('set to empty: gone', (len(v.fx.objs), len(v.fx.cache)), (0, 0))

# drop shadow: distance 10 at angle 0 -> to the right only
rt.run('set the dropShadow["color"] of graphic "G" to "0,0,255"\nset the dropShadow["size"] of graphic "G" to 2\n'
       'set the dropShadow["distance"] of graphic "G" to 10\nset the dropShadow["angle"] of graphic "G" to 0\n'
       'set the dropShadow["opacity"] of graphic "G" to 255')
frame()
at, free = pixels()
check('drop shadow: to the right of the shape', at(165, 90)[2] > 150 and at(165, 90)[0] < 100, True)
check('drop shadow: not to the left', at(95, 90), (255, 255, 255))
free()
rt.run('set the dropShadow of graphic "G" to empty')

# inner glow and color overlay, on a white shape
rt.run('set the backgroundColor of graphic "G" to "255,255,255"\nset the foregroundColor of graphic "G" to "255,255,255"\n'
       'set the innerGlow["color"] of graphic "G" to "0,255,0"\nset the innerGlow["size"] of graphic "G" to 10\n'
       'set the innerGlow["opacity"] of graphic "G" to 255')
frame()
at, free = pixels()
check('inner glow: green inside near the edge', at(102, 90)[1] > at(102, 90)[0] + 60, True)
check('inner glow: not in the middle', at(130, 90), (255, 255, 255))
check('inner glow: not outside', at(97, 90), (255, 255, 255))
free()
rt.run('set the innerGlow of graphic "G" to empty\nset the colorOverlay["color"] of graphic "G" to "255,0,0"\n'
       'set the colorOverlay["opacity"] of graphic "G" to 255')
frame()
at, free = pixels()
check('color overlay: the shape in the colour', at(130, 90), (255, 0, 0))
check('color overlay: only the shape', at(90, 90), (255, 255, 255))
free()
v.close()

print('%d of %d effect checks pass' % (N[0] - len(BAD), N[0]))
sys.exit(1 if BAD else 0)
