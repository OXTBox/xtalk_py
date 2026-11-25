#!/usr/bin/env python3
"""translate.py - turn xTalk scripts into Python (the translator, xtalk/transpile.py).

    python3 -I tools/translate.py SCRIPT [-o OUT.py]       write the Python (default: next to nothing, print it)
    python3 -I tools/translate.py --libs                   regenerate generated/*.py from the corpus libraries
    python3 -I tools/translate.py --run 'EXPR' SCRIPT...   translate the scripts, run one expression with them

The Python is generated: edit the xTalk and translate again.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from xtalk.transpile import translate_script, translate_expr   # noqa: E402
from xtalk.pyrt import Runtime, Frame                         # noqa: E402
import xtalk.pyrt as pyrt                                     # noqa: E402

LIBS = ['lib_bit', 'lib_map', 'lib_trace']          # pure libraries, tested against LiveCode (tests/golden.json)

def read(path):
    t = open(path, encoding='utf-8', errors='replace').read()
    return t.split('\n', 1)[1] if t.startswith('script ') else t

def one(src, out=None):
    py, rep = translate_script(read(src), os.path.relpath(src, ROOT) if src.startswith(ROOT) else os.path.basename(src))
    if out:
        open(out, 'w', encoding='utf-8').write(py)
    else:
        sys.stdout.write(py)
    print('%s: %d handlers became Python, %d kept as xTalk, %d do not parse'
          % (os.path.basename(src), len(rep['translated']), len(rep['interpreted']), len(rep['parse_errors'])), file=sys.stderr)
    for name, why in rep['interpreted']:
        print('  kept as xTalk: %s (%s)' % (name, why), file=sys.stderr)
    return rep

def main(a):
    if a[:1] == ['--libs']:
        os.makedirs(os.path.join(ROOT, 'generated'), exist_ok=True)
        for lib in LIBS:
            one(os.path.join(ROOT, 'corpus', 'libraries', lib + '.livecodescript'), os.path.join(ROOT, 'generated', lib + '.py'))
        return
    if a[:1] == ['--run']:
        rt = Runtime()
        for src in a[2:]:
            rt.install(translate_script(read(src), src)[0], src)
        v = eval(translate_expr(a[1]), dict(vars(pyrt), rt=rt, fr=Frame([])))
        print('' if isinstance(v, dict) else pyrt.to_text(v))
        return
    if not a:
        sys.exit(__doc__)
    out = a[a.index('-o') + 1] if '-o' in a else None
    one(a[0], out)

if __name__ == '__main__':
    main(sys.argv[1:])
