#!/usr/bin/env python3
"""xt3d on Python raylib against the real bridge (LiveCode + xt3d.dll): tests/xt3d_golden.json.

    .venv/bin/python tests/test_xt3d.py [-v]

Needs the raylib package, so it runs with the .venv Python (the core tests stay standard-library).
Every case runs three ways: interpreted, translated, and fast-translated (how stacks run).
A LiveCode error ("ERROR 899,...") only has to be an error here too.
Also checks the handle table rules of xt3d_shim.c (lowest free number, 0 = a zeroed stand-in).
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from xtalk import XtError                                     # noqa: E402
from xtalk.interp import Interp, Frame                        # noqa: E402
from xtalk.parser import parse_statements                     # noqa: E402
from xtalk.pyrt import Runtime                                # noqa: E402
from xtalk.transpile import translate_script                  # noqa: E402
from xtalk import xt3d                                        # noqa: E402
from xtalk.xt3d import tables                                 # noqa: E402

xt3d.install()
# the bench measured with its hidden raylib window open; so do we (some calls need a window)
xt3d.load()['xt3d_settraceloglevel']('5')                 # raylib: errors only (bad-input cases warn)
xt3d.load()['xt3d_inithidden']('64', '64', 'test_xt3d')
# known, wanted differences: case -> what ours starts with instead
KNOWN = {'xt3d_Version()': 'xt3d 0.1.0 / raylib '}   # the Python raylib package is built from raylib 6.5-dev
gold = json.load(open(os.path.join(ROOT, 'tests', 'xt3d_golden.json'), encoding='utf-8'))
verbose = '-v' in sys.argv
bad = []


def interp(case):
    it = Interp()
    fr = Frame([])
    it.exec_block(parse_statements('put (%s) into tOut' % case), fr)
    return it.getvar(fr, 'tOut')


def translated(case, fast):
    rt = Runtime()
    py, rep = translate_script('function t\n  return (%s)\nend t' % case, 'case', fast=fast) if fast else \
        translate_script('function t\n  return (%s)\nend t' % case, 'case')
    rt.install(py)
    return rt.call('t')


def norm(v):
    from xtalk.values import to_text
    return to_text(v)


n = 0
for case, want in gold.items():
    for mode, run in (('interp', interp), ('translated', lambda c: translated(c, False)),
                      ('fast', lambda c: translated(c, True))):
        n += 1
        try:
            got = norm(run(case))
        except XtError as e:
            got = 'ERROR ' + str(e)
        ok = got.startswith('ERROR') if want.startswith('ERROR') else (
            got.startswith(KNOWN[case]) if case in KNOWN else got == want)
        if not ok:
            bad.append((mode, case, want, got))
        elif verbose:
            print('ok   %-10s %s' % (mode, case))

# commands: an extension handler used as a command puts its value into the result
it = Interp()
fr = Frame([])
it.exec_block(parse_statements('xt3d_ColorToInt 255,0,0,255\nput the result into tOut'), fr)
n += 1
if it.getvar(fr, 'tOut') != '-16776961':
    bad.append(('command', 'xt3d_ColorToInt 255,0,0,255', '-16776961', it.getvar(fr, 'tOut')))

# handle tables (xt3d_shim.c XT_TABLE)
tables.reset()
F = xt3d.load()
checks = [
    ('first image is 1', F['xt3d_genimagecolor']('2', '2', '0', '0', '0', '255'), '1'),
    ('second image is 2', F['xt3d_genimagecolor']('3', '1', '0', '0', '0', '255'), '2'),
    ('unload 1', F['xt3d_unloadimage']('1'), ''),
    ('freed number is used again', F['xt3d_genimagecolor']('5', '5', '0', '0', '0', '255'), '1'),
    ('new 1 is the 5x5 one', F['xt3d_getimagecolor']('1', '0', '0'), '0,0,0,255'),
    ('a camera table of its own', F['xt3d_cameracreate']('1', '2', '3', '0', '0', '0', '0', '1', '0', '45', '0')
     if 'xt3d_cameracreate' in F else '1', '1'),
]
for label, got, want in checks:
    n += 1
    if got != want:
        bad.append(('table', label, want, got))
n += 1
if tables.T_Image.count() != 2:
    bad.append(('table', 'two images live', '2', str(tables.T_Image.count())))

# helpers with no text answer of their own: they run, and what they set reads back
tri = F['xt3d_meshfromtext']('0,0,0, 1,0,0, 0,1,0', '', '')
mdl = F['xt3d_loadmodelfrommesh'](tri)
rt8 = F['xt3d_loadrendertexture']('8', '4')
smoke = [
    ('transform round trip', lambda: (F['xt3d_modelsettransform'](mdl, *'2 0 0 0 0 2 0 0 0 0 2 0 1 2 3 1'.split()),
                                      F['xt3d_modelgettransform'](mdl))[1], '2,0,0,0,0,2,0,0,0,0,2,0,1,2,3,1'),
    ('material colour', lambda: F['xt3d_modelsetmaterialcolor'](mdl, '0', '0', '255', '0', '0', '255'), ''),
    ('material colour, bad index', lambda: F['xt3d_modelsetmaterialcolor'](mdl, '7', '0', '1', '2', '3', '4'), ''),
    ('camera 2D', lambda: F['xt3d_camera2dset'](F['xt3d_camera2dcreate']('0', '0', '0', '0', '0', '1'),
                                                 '1', '1', '1', '1', '0', '2'), ''),
    ('culling + wire + depth + width', lambda: ''.join(F[n](v) for n, v in (
        ('xt3d_setbackfaceculling', 'false'), ('xt3d_setcullface', '0'), ('xt3d_setwiremode', 'true'),
        ('xt3d_setwiremode', 'false'), ('xt3d_setdepthtest', 'true'), ('xt3d_setlinewidth', '2'))), ''),
    ('frame as imageData: 8x4x4 bytes', lambda: str(len(F['xt3d_rendertextureimagedata'](rt8))), '128'),
    ('alphaData: 8x4 bytes', lambda: str(len(F['xt3d_rendertexturealphadata'](rt8))), '32'),
    ('image data size', lambda: F['xt3d_imagedatasize'](), '128'),
    ('handle count', lambda: F['xt3d_handlecount']('Model'), '1'),
]
for label, fn, want in smoke:
    n += 1
    try:
        got = fn()
    except Exception as e:                                    # noqa: BLE001
        got = 'ERROR %r' % e
    if got != want:
        bad.append(('helper', label, want, got))

for mode, case, want, got in bad:
    print('FAIL %-10s %s\n     want %r\n     got  %r' % (mode, case, want, got))
print('%d/%d' % (n - len(bad), n))
sys.exit(1 if bad else 0)
