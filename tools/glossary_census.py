#!/usr/bin/env python3
"""glossary_census.py - count the LiveCode vocabulary a set of scripts really uses.

    python3 tools/glossary_census.py [--out docs/GLOSSARY.md] [--json docs/glossary.json] PATH...

PATH can be a script file or a folder (searched for *.livecodescript and *.txt).
With no PATH, xtalk_py/corpus and the Vibecode3D harvest's control scripts are used.

This is a census, not a parser: it strips comments and string literals, then counts
  commands    first word of each statement (also after "then" / "else" on one line)
  functions   name( ... ) calls, and "the <fn> of" forms of built-in functions
  properties  "the <prop>" and "the <prop> of"
  chunks      char/word/item/line/byte/token ... of
Names defined as handlers in the scanned scripts are excluded, so what is left is
LiveCode's own vocabulary: the list the xTalk interpreter has to implement.
Duplicate files (same content) are counted once.
"""
import argparse, collections, hashlib, json, os, re, sys

HOME_PROJECTS = os.path.expanduser('~/projects')
DEFAULT_PATHS = [
    'xtalk_py/corpus',               # the script corpus (see corpus/README.md)
    'Vibecode3D/XTJSON/scripts',     # every control script of the harvested engine stack
]

CONTROL = set('''if then else end repeat exit next return pass switch case break default try catch
finally throw on command function private global local constant getprop setprop
with while until for each forever times'''.split())
# words that look like calls but are syntax or object references
NOT_FUNCS = set('''and or not is in of to into after before with a an the there be among within contains
begins ends stack card cd button btn field fld graphic grc image img group grp player scrollbar
control widget window me this it if return put get set send'''.split())
PLURAL = {'command': 'commands', 'function': 'functions', 'property': 'properties', 'chunk': 'chunks'}
CHUNK = ('char', 'character', 'word', 'item', 'line', 'byte', 'token', 'segment', 'paragraph')

def files_in(path):
    if os.path.isfile(path):
        yield path
        return
    for root, _, names in os.walk(path):
        for n in sorted(names):
            if n.endswith(('.livecodescript', '.txt')) and 'Zone.Identifier' not in n:
                yield os.path.join(root, n)

def clean_lines(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    out = []
    for line in text.split('\n'):
        line = re.sub(r'"[^"\n]*"', '""', line)          # strings first, so -- inside them survives
        line = re.sub(r'(--|#|//).*$', '', line).strip()
        if line.endswith('\\'):
            line = line[:-1]
        if line:
            out.append(line)
    return out

def statements(line):
    """split 'if x then put 1 into y else put 2 into y' into its statements"""
    parts = re.split(r'\b(?:then|else)\b', line, flags=re.I)
    return [p.strip() for p in parts if p.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='*')
    ap.add_argument('--out', default='docs/GLOSSARY.md')
    ap.add_argument('--json', default='docs/glossary.json')
    a = ap.parse_args()
    paths = a.paths or [os.path.join(HOME_PROJECTS, p) for p in DEFAULT_PATHS]

    seen, sources, all_lines = set(), [], []
    for p in paths:
        if not os.path.exists(p):
            print('missing:', p, file=sys.stderr)
            continue
        for f in files_in(p):
            raw = open(f, 'rb').read()
            h = hashlib.sha1(raw).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            lines = clean_lines(raw.decode('utf-8', errors='replace'))
            sources.append((f, len(lines)))
            all_lines += [(f, l) for l in lines]

    defined = set()
    for _, l in all_lines:
        m = re.match(r'(?:private\s+)?(?:on|command|function|getprop|setprop)\s+([\w.]+)', l, re.I)
        if m:
            defined.add(m.group(1).lower())

    use = {k: collections.Counter() for k in ('command', 'function', 'property', 'chunk')}
    where = {k: collections.defaultdict(set) for k in use}
    def count(kind, name, f):
        use[kind][name] += 1
        where[kind][name].add(f)

    for f, l in all_lines:
        if re.match(r'(?:private\s+)?(?:on|command|function|getprop|setprop|end|global|local|constant)\b', l, re.I):
            continue
        for st in statements(l):
            w = st.split()[0].lower()
            if re.match(r'^[a-z][\w.]*$', w) and w not in CONTROL and w not in defined:
                count('command', w, f)
        for fn in re.findall(r'\b([A-Za-z][\w.]*)\s*\(', l):
            n = fn.lower()
            if n not in defined and n not in NOT_FUNCS and n not in CONTROL:
                count('function', n, f)
        for pr in re.findall(r'\bthe\s+(?:(?:short|long|abbreviated|abbrev|effective|english|system|internet)\s+)?([A-Za-z]\w*)', l, re.I):
            n = pr.lower()
            if n not in defined:
                count('property', n, f)
        for ch in re.findall(r'\b(' + '|'.join(CHUNK) + r')s?\b\s+[^ ]+(?:\s+to\s+[^ ]+)?\s+of\b', l, re.I):
            count('chunk', ch.lower(), f)

    total_lines = len(all_lines)
    report = {
        'sources': [{'file': f, 'lines': n} for f, n in sources],
        'script_lines': total_lines,
        'handlers_defined': len(defined),
        'vocabulary': {k: [{'name': n, 'uses': c, 'files': len(where[k][n])}
                           for n, c in use[k].most_common()] for k in use},
    }
    os.makedirs(os.path.dirname(a.json) or '.', exist_ok=True)
    json.dump(report, open(a.json, 'w'), indent=1)

    def cover(c, n):
        t = sum(c.values())
        return 100 * sum(v for _, v in c.most_common(n)) / t if t else 0

    md = ['# xTalk glossary census', '',
          'Generated by `tools/glossary_census.py`; do not edit by hand. Re-run after adding scripts.', '',
          'What LiveCode\'s own vocabulary the owner\'s scripts use, most used first. This is the',
          'interpreter\'s to-do list: implement from the top down. Counts are approximate (a census,',
          'not a parser); names the scripts define themselves are left out. Custom properties',
          '(the owner\'s own `the gridHistory` and so on) appear under properties too: they need no',
          'code, only working custom-property support.', '',
          '| | |', '|---|---|',
          f'| script files (duplicates removed) | {len(sources)} |',
          f'| script lines | {total_lines} |',
          f'| handlers defined by the scripts | {len(defined)} |']
    for k in ('command', 'function', 'property', 'chunk'):
        c = use[k]
        md.append(f'| distinct {PLURAL[k]} | {len(c)} (top 25 = {cover(c, 25):.0f}% of uses, top 60 = {cover(c, 60):.0f}%) |')
    md += ['', 'Status column: `-` not started, `ok` implemented and tested against LiveCode 9.6.3.', '']
    for k in ('command', 'function', 'property', 'chunk'):
        md += [f'## {PLURAL[k].capitalize()}', '', '| name | uses | files | status |', '|---|---:|---:|---|']
        for n, c in use[k].most_common():
            md.append(f'| `{n}` | {c} | {len(where[k][n])} | - |')
        md.append('')
    md += ['## Sources', ''] + [f'- `{os.path.relpath(f, HOME_PROJECTS)}` ({n} lines)' for f, n in sources]
    open(a.out, 'w').write('\n'.join(md) + '\n')
    print(f'{len(sources)} files, {total_lines} lines, {len(defined)} handlers; '
          + ', '.join(f'{len(use[k])} {PLURAL[k]}' for k in use) + f' -> {a.out}, {a.json}')

if __name__ == '__main__':
    main()
