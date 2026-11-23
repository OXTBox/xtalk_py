#!/usr/bin/env python3
"""parse_corpus.py - how much of the corpus the xtalk parser reads.

    python3 -I tools/parse_corpus.py [-v] [PATH...]     (default: corpus/)

Each failing script is parsed handler by handler, so one bad line costs one handler, not the file.
Prints the share of handlers that parse and the most common failures, with the source line.
"""
import collections, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from xtalk.parser import Parser   # noqa: E402
from xtalk import XtError          # noqa: E402

def files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        for r, _, fs in os.walk(p):
            for f in sorted(fs):
                if f.endswith(('.livecodescript', '.txt')) and 'Zone.Identifier' not in f \
                        and not f.endswith('.md'):
                    yield os.path.join(r, f)

def main():
    args = [a for a in sys.argv[1:] if a != '-v']
    verbose = '-v' in sys.argv
    paths = args or [os.path.join(ROOT, 'corpus')]
    tot = ok = 0
    errs = collections.Counter()
    where = {}
    for f in files(paths):
        text = open(f, encoding='utf-8', errors='replace').read()
        lines = text.replace('\r\n', '\n').split('\n')
        p = Parser(text)
        p.skip_nl()
        while p.peek()[0] != 'eof':
            start = p.i
            try:
                # one handler (or a global/local line)
                if p.is_word('script') and p.peek(1)[0] == 'str':
                    while p.peek()[0] != 'nl':
                        p.i += 1
                    p.skip_nl()
                    continue
                if p.is_word('global') or p.is_word('local') or p.is_word('constant'):
                    p.statement()
                    p.skip_nl()
                    continue
                p.accept_word('private')
                kind = p.accept_word('on', 'command', 'function', 'getprop', 'setprop')
                if not kind:
                    p.err('expected a handler (on, command, function)')
                p.next()
                while p.peek()[0] != 'nl':
                    p.next()
                p.skip_nl()
                p.block(('end',))
                p.expect_word('end')
                p.next()
                p.skip_nl()
                tot += 1
                ok += 1
            except XtError as e:
                tot += 1
                msg = str(e)
                m = re.match(r'line (\d+): (.*)', msg)
                ln = int(m.group(1)) if m else 0
                key = re.sub(r"\(at '.*'\)", '', m.group(2) if m else msg).strip() + ' @ ' + \
                    (re.search(r"\(at '(.*)'\)", msg).group(1) if re.search(r"\(at '(.*)'\)", msg) else '')
                errs[key] += 1
                where.setdefault(key, (os.path.relpath(f, ROOT), ln, lines[ln - 1].strip()[:90] if 0 < ln <= len(lines) else ''))
                # resync: skip to the next handler start
                p.i = max(p.i, start + 1)
                while p.peek()[0] != 'eof' and not (p.peek()[0] == 'nl' and p.peek(1)[0] == 'id'
                                                    and p.peek(1)[1].lower() in ('on', 'command', 'function', 'private', 'getprop', 'setprop')):
                    p.i += 1
                p.skip_nl()
    print('%d of %d handlers parse (%.0f%%)' % (ok, tot, 100.0 * ok / max(tot, 1)))
    for k, n in errs.most_common(25 if not verbose else 200):
        f, ln, src = where[k]
        print('%4d  %s\n        %s:%d  %s' % (n, k, f, ln, src))

if __name__ == '__main__':
    main()
