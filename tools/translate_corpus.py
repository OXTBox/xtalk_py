#!/usr/bin/env python3
"""translate_corpus.py - how much of the corpus the translator turns into Python.

    python3 -I tools/translate_corpus.py [-v] [PATH...]     (default: corpus/)

For every script: handlers that became Python, handlers kept as xTalk (interpreted) and why,
handlers that do not parse. Every generated module is also compiled by Python as a whole.
"""
import collections, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from xtalk.transpile import translate_script   # noqa: E402
from parse_corpus import files                 # noqa: E402

def main():
    args = [a for a in sys.argv[1:] if a != '-v']
    verbose = '-v' in sys.argv
    paths = args or [os.path.join(ROOT, 'corpus')]
    tot = collections.Counter()
    why = collections.Counter()
    examples = {}
    for f in files(paths):
        text = open(f, encoding='utf-8', errors='replace').read()
        try:
            py, rep = translate_script(text, os.path.relpath(f, ROOT))
            compile(py, f, 'exec')
        except Exception as e:                  # noqa: BLE001  (a whole-file failure is a finding)
            tot['files failed'] += 1
            why['whole file: %s' % type(e).__name__] += 1
            examples.setdefault('whole file: %s' % type(e).__name__, '%s: %s' % (os.path.relpath(f, ROOT), e))
            continue
        tot['files'] += 1
        tot['python'] += len(rep['translated'])
        tot['xtalk'] += len(rep['interpreted'])
        tot['parse'] += len(rep['parse_errors'])
        for name, w in rep['interpreted']:
            k = w.split(':')[0] + ':' + w.split(':')[1][:40] if ':' in w else w
            why[k] += 1
            examples.setdefault(k, '%s: %s' % (os.path.relpath(f, ROOT), name))
        if verbose:
            print('%5d py %3d xt %3d bad  %s' % (len(rep['translated']), len(rep['interpreted']),
                                                 len(rep['parse_errors']), os.path.relpath(f, ROOT)))
    hs = tot['python'] + tot['xtalk'] + tot['parse']
    print('%d scripts (%d could not be read as a whole)' % (tot['files'], tot['files failed']))
    print('%d handlers: %d became Python (%.1f%%), %d kept as xTalk, %d do not parse'
          % (hs, tot['python'], 100.0 * tot['python'] / max(hs, 1), tot['xtalk'], tot['parse']))
    for k, c in why.most_common(15):
        print('  %4d  %s\n        e.g. %s' % (c, k, examples[k]))

if __name__ == '__main__':
    main()
