#!/usr/bin/env python3
"""Every native handler (xtalk/native) against its xTalk handler: the same random inputs through both, the
same answers and the same globals afterwards, in both run modes (interpreted and fast-translated).

    python3 -I tests/test_native.py [-v] [--n 300]

Answers are compared as text (a number's text is what the scripts see); the globals as their sorted dump.
"""
import os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from xtalk import native                                      # noqa: E402
from xtalk.interp import Interp                               # noqa: E402
from xtalk.pyrt import Runtime                                # noqa: E402
from xtalk.transpile import translate_script                  # noqa: E402
from xtalk.values import XtArray, numstr                      # noqa: E402

ENGINE = os.path.expanduser('~/projects/xt3D_Raylib_Livecode_Bridge/testbench/vibe_engine_xt3d.livecodescript')


def load(mode, src, natives):
    if mode == 'interp':
        rt = Interp()
        rt.load(src)
    else:
        rt = Runtime()
        py, _ = translate_script(src, 'engine', fast=True)
        rt.install(py)
    if natives:
        os.environ['XTALK_NATIVE'] = '1'
        done = native.apply(rt, 'VibeEngineXt3d', src)
        assert done, 'no native handler applied'
    return rt


def dump(v):
    if isinstance(v, dict):
        return '{' + ';'.join('%s=%s' % (k, dump(v[k])) for k in sorted(v, key=str.lower)) + '}'
    return str(v)


def rnum(r):
    """a number as the scripts hold it: often a computed one (full value), sometimes text or empty"""
    k = r.random()
    x = r.choice([r.uniform(-4, 4), r.uniform(-500, 500), 0.0, r.uniform(-1e-7, 1e-7), float(r.randint(-3, 3))])
    if k < 0.5:
        return numstr(x)
    if k < 0.9:
        return repr(round(x, r.randint(0, 9)))
    return ''


def mat(r):
    return ','.join(str(rnum(r)) if r.random() < 0.9 else '%.9f' % r.uniform(-1, 1) for _ in range(9))


def transforms(r):
    a = XtArray()
    keys = ['rotSpeedX', 'rotSpeedY', 'rotSpeedZ', 'rotX', 'rotY', 'rotZ', 'localAx', 'localAy', 'localAz', 'vx',
            'vy', 'vz', 'localBrake', 'maxWorldSpeed', 'localVx', 'localVy', 'localVz', 'x', 'y', 'z']
    for i in range(r.randint(0, 6)):
        o = XtArray()
        for k in keys:
            if r.random() < 0.75:
                o[k if r.random() < 0.9 else k.upper()] = rnum(r)
        if r.random() < 0.3:
            o['localBrake'] = numstr(r.uniform(0, 3))
        if r.random() < 0.3:
            o['maxWorldSpeed'] = numstr(r.uniform(0, 3))
        if r.random() < 0.1:
            o['mesh'] = 'cube'
        if r.random() < 0.05:
            o['x'] = 'not a number'           # the xTalk's own error, through Fallback
        a['obj%d' % i] = o
    return a if a or r.random() < 0.8 else ''


def scene(r):
    """gSceneObjects: lines "mesh key [graphic]", with the odd ones a real list may hold"""
    keys = ['Squad.G3_12', 'squad.g3_12', 'BOX_1', 'box_1', 'Tower_7', '12', '12.0', 'x\u00e9', 'a']
    lines = []
    for _ in range(r.randint(0, 9)):
        k = r.random()
        if k < 0.6:
            ln = '%s %s' % (r.choice(['cube', 'Squad.G3', 'ship']), r.choice(keys))
            if r.random() < 0.3:
                ln += ' Batch_' + r.choice(['red', '120_200_90'])
        elif k < 0.7:
            ln = ''
        elif k < 0.8:
            ln = r.choice(['onlyone', '  cube\t%s ' % r.choice(keys), 'cube\r%s' % r.choice(keys)])
        else:
            ln = 'cube  %s' % r.choice(keys)
        lines.append(ln)
    t = '\n'.join(lines)
    return t + '\n' if t and r.random() < 0.2 else t


def main(a):
    n = int(a[a.index('--n') + 1]) if '--n' in a else 300
    src = open(ENGINE).read()
    fails = total = 0
    counts = {}
    for mode in ('interp', 'fast'):
        ref, nat = load(mode, src, False), load(mode, src, True)
        r = random.Random(7)
        for i in range(n):
            g = transforms(r)
            locals_ = {'sscenecamm': mat(r), 'scamm': mat(r),
                       'sframet': ' '.join(str(rnum(r)) for _ in range(r.choice([3, 3, 3, 2])))}
            obj = r.choice(sorted(g) + ['nobody']) if isinstance(g, dict) and g else 'nobody'
            if isinstance(g, dict) and g and r.random() < 0.3:
                o = g[r.choice(sorted(g))]
                o[r.choice(['rotX', 'rotY', 'x', 'Z'])] = r.choice(['', 'abc', ' 2', '1e2', numstr(r.uniform(-9, 9))])
            colours = ['', 'red', 'GREY', '#3F6FB0', '#3f6', '10,20,30', '1,2', 'nonsense', numstr(5.0)]
            view = XtArray()
            if r.random() < 0.3:
                view['mono'] = r.choice(colours)
            if r.random() < 0.7:
                view['fade'] = r.choice(['', '50', numstr(r.uniform(0, 100)), 'x'])
            orig = XtArray({'g%d' % k: r.choice(colours) for k in range(4)})
            locals_.update({'sview': view if r.random() < 0.9 else '', 'sorigcolor': orig,
                            'sviewbands': r.choice(['', '1', '4', numstr(r.uniform(1, 8)), 'q']),
                            'sviewnear': rnum(r), 'sviewfar': r.choice([rnum(r), '100', '0'])})
            for rt in (ref, nat):
                rt.S.update(locals_)
            cases = [('Vibe.Color', [r.choice(['g0', 'g1', 'g3', 'g9']), r.choice([rnum(r), '', 'x', numstr(r.uniform(-50, 300))])], None),
                     ('Mat3.Mul', [mat(r), mat(r)], None),
                     ('Xform.Object', [obj], g),
                     ('RotateLocalVector', [rnum(r) for _ in range(6)], None),
                     ('UpdateObjectTransforms', [], transforms(r)),
                     ('SetObjectPosition', [r.choice([obj, obj, 'newOne', '', 'BOX'])] +
                      [r.choice([rnum(r), '', 'abc', numstr(r.uniform(-50, 50)), '0', ' 3'])
                       for _ in range(r.choice([3, 3, 3, 2, 1]))], r.choice([g, g, transforms(r), ''])),
                     ('SetObjectVelocity', [r.choice([obj, obj, 'newOne', '', 'BOX'])] +
                      [r.choice([rnum(r), '', 'abc', numstr(r.uniform(-50, 50)), '0', ' 3'])
                       for _ in range(r.choice([3, 3, 3, 2, 1]))] + ([r.choice(['', 'true', 'x'])] if r.random() < 0.3 else []),
                      r.choice([g, g, transforms(r), ''])),
                     ('Scene.Has', [r.choice(['Squad.G3_12', 'SQUAD.g3_12', 'box_1', 'Tower_7', 'nope', '12', '', 'x\u00c9',
                                              'a', 'Tower_7 x'])], None),
                     ('Scene.Remove', [r.choice(['Squad.G3_12', 'BOX_1', 'tower_7', 'nope', '12', '', 'A', 'x\u00e9'])], None)]
            sc = scene(r)
            for name, args, g in cases:
                outs = []
                for rt in (ref, nat):
                    rt.G['gsceneobjects'] = sc
                    if g is not None:
                        import copy
                        rt.G['gobjecttransforms'] = copy.deepcopy(g)
                    try:
                        got = str(rt.invoke(name, list(args)))
                    except Exception as e:     # noqa: BLE001  (the same error is the same answer)
                        got = 'ERROR %s: %s' % (type(e).__name__, e)
                    outs.append(got + ' | ' + dump(rt.G.get('gobjecttransforms', '')) + ' | ' +
                                repr(rt.G.get('gsceneobjects', '')))
                total += 1
                if outs[0] != outs[1]:
                    fails += 1
                    if fails <= 5 or '-v' in a:
                        print('DIFFER %s %s %s\n  xtalk : %s\n  native: %s' % (mode, name, args, outs[0][:400], outs[1][:400]))
        counts[mode] = {k[1]: (n, native.FELL.get(k, 0)) for k, n in native.USED.items()}
    # a changed handler, or a changed helper a native copies inside, keeps its xTalk
    import io, contextlib
    for old, new, off in (('   return tX3 && tY3 && tZ3\n   \nend RotateLocalVector', '   return tX3 && tY3 && tZ3 && 0\nend RotateLocalVector', ('rotatelocalvector', 'updateobjecttransforms')),
                          ('   return tX,tY,tZ\nend GetObjectRotation\n', '   return tX,tY,tZ,0\nend GetObjectRotation\n', ('xform.object',)),
                          ('put tCZ,-tSZ,0,tSZ,tCZ,0,0,0,1 into tRZ', 'put tCZ,tSZ,0,tSZ,tCZ,0,0,0,1 into tRZ', ('xform.object',))):
        assert src.count(old) == 1, old
        native.SKIPPED.clear()
        with contextlib.redirect_stderr(io.StringIO()):
            rt = load('fast', src.replace(old, new), False)
            done = native.apply(rt, 'VibeEngineXt3d', src.replace(old, new))
        total += 1
        if any(n in done for n in off) or 'mat3.mul' not in done:
            fails += 1
            print('EDIT NOT NOTICED: %r -> natives %s' % (new, done))
    print('%d of %d native answers match their xTalk handler (interp + fast), edits noticed' % (total - fails, total))
    for mode, c in counts.items():
        print('%s: ' % mode + ', '.join('%s %d native, %d to the xTalk' % (k, n - f, f) for k, (n, f) in sorted(c.items())))
        if any(n - f < 50 for k, (n, f) in c.items()):
            print('TOO FEW native runs in %s: the cases mostly went to the xTalk' % mode)
            fails += 1
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
