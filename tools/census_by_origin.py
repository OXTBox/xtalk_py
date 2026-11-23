#!/usr/bin/env python3
"""census_by_origin.py - the xTalk vocabulary census, split by who wrote the script.

    python3 tools/census_by_origin.py [--out docs/GLOSSARY.md] [--json docs/glossary.json]

Groups (a script found in several places is counted once, the first group wins):
  owner       the owner's own stacks, harvested to scripts by XTJSON (the 13 Nov 2026 batch,
              ~/projects/XTJSON stacks, corpus/originals); written 2011-2026
  claude      every other .livecodescript tracked in the project repos (libraries, games,
              editors, Spark drafts that were kept): written by Claude/Spark since 11 Nov 2026
  third       other people's scripts (Scott Rossi etc.): counted for nothing, listed only

It reuses the counting rules of glossary_census.py (a census, not a parser).
"""
import argparse, collections, hashlib, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import glossary_census as gc

P = os.path.expanduser('~/projects')
BATCH = P + '/LIB_LLMOUT/Read/LIB_XTJSON/XTJSON_batch_11_13_2026'
THIRD = re.compile(r'scott_rossi|rossi', re.I)
# the project's own externals (LCB extension names), not LiveCode's vocabulary
CONTINUATION = set('and or before after char chars character word words item items line lines the to into of is not'.split())
PROJECT_API = re.compile(r'^(xt3d_|entity\.|mat3\.|mesh\.|game\.|xform\.|rendermesh)', re.I)


def scripts_under(root):
    for r, _, names in os.walk(root):
        if '/.git' in r:
            continue
        for n in sorted(names):
            if n.endswith('.livecodescript') or (n.endswith('.txt') and 'originals' in r):
                yield os.path.join(r, n)


def repo_files():
    """tracked .livecodescript files of every repo under ~/projects"""
    out = []
    for d in sorted(os.listdir(P)):
        g = os.path.join(P, d)
        if not os.path.isdir(os.path.join(g, '.git')) or d == 'LIB_LLMOUT':
            continue
        r = subprocess.run(['git', '-C', g, 'ls-files', '*.livecodescript'], capture_output=True, text=True)
        out += [os.path.join(g, f) for f in r.stdout.split('\n') if f]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='docs/GLOSSARY.md')
    ap.add_argument('--json', default='docs/glossary.json')
    a = ap.parse_args()

    owner_files = list(scripts_under(BATCH)) + list(scripts_under(P + '/XTJSON')) \
        + list(scripts_under(P + '/xtalk_py/corpus/originals'))
    claude_files = repo_files()
    seen, groups = set(), {'owner': [], 'claude': [], 'third': []}
    for grp, files in (('owner', owner_files), ('claude', claude_files)):
        for f in files:
            if '/.git/' in f or 'Zone.Identifier' in f:
                continue
            raw = open(f, 'rb').read()
            h = hashlib.sha1(raw).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            g = 'third' if THIRD.search(f) else grp
            groups[g].append((f, raw))

    defined, lines_of = set(), {}
    for g in ('owner', 'claude'):
        lines_of[g] = []
        for f, raw in groups[g]:
            for l in gc.clean_lines(raw.decode('utf-8', errors='replace')):
                lines_of[g].append((f, l))
                m = re.match(r'(?:private\s+)?(?:on|command|function|getprop|setprop)\s+([\w.]+)', l, re.I)
                if m:
                    defined.add(m.group(1).lower())

    kinds = ('command', 'function', 'property', 'chunk')
    use = {g: {k: collections.Counter() for k in kinds} for g in lines_of}
    where = {g: {k: collections.defaultdict(set) for k in kinds} for g in lines_of}
    for g, lines in lines_of.items():
        def count(kind, name, f):
            use[g][kind][name] += 1
            where[g][kind][name].add(f)
        for f, l in lines:
            if re.match(r'(?:private\s+)?(?:on|command|function|getprop|setprop|end|global|local|constant)\b', l, re.I):
                continue
            for st in gc.statements(l):
                w0 = st.split()[0]
                w = w0.lower()
                if re.match(r'^[gtpsu][A-Z]', w0) or w in CONTINUATION:   # a variable, or a wrapped line
                    continue
                if re.match(r'^[a-z][\w.]*$', w) and w not in gc.CONTROL and w not in defined:
                    count('command', w, f)
            for fn in re.findall(r'\b([A-Za-z][\w.]*)\s*\(', l):
                n = fn.lower()
                if n not in defined and n not in gc.NOT_FUNCS and n not in gc.CONTROL:
                    count('function', n, f)
            for pr in re.findall(r'\bthe\s+(?:(?:short|long|abbreviated|abbrev|effective|english|system|internet)\s+)?([A-Za-z]\w*)', l, re.I):
                if pr.lower() not in defined:
                    count('property', pr.lower(), f)
            for ch in re.findall(r'\b(' + '|'.join(gc.CHUNK) + r')s?\b\s+[^ ]+(?:\s+to\s+[^ ]+)?\s+of\b', l, re.I):
                count('chunk', ch.lower(), f)

    nlines = {g: len(lines_of[g]) for g in lines_of}
    report = {'groups': {g: {'files': len(groups[g]), 'lines': nlines.get(g, 0)} for g in groups},
              'handlers_defined': len(defined), 'vocabulary': {}}
    for k in kinds:
        names = set(use['owner'][k]) | set(use['claude'][k])
        rows = []
        for n in names:
            o, c = use['owner'][k][n], use['claude'][k][n]
            rows.append({'name': n, 'owner': o, 'claude': c,
                         'owner_files': len(where['owner'][k][n]), 'claude_files': len(where['claude'][k][n]),
                         'project_api': bool(PROJECT_API.match(n))})
        rows.sort(key=lambda r: -(r['owner'] + r['claude']))
        report['vocabulary'][k] = rows
    os.makedirs(os.path.dirname(a.json) or '.', exist_ok=True)
    json.dump(report, open(a.json, 'w'), indent=1)

    def per1k(n, g):
        return 1000 * n / nlines[g] if nlines[g] else 0

    md = ['# xTalk glossary census', '',
          'Generated by `tools/census_by_origin.py`; do not edit by hand. Re-run after adding scripts.', '',
          'What LiveCode vocabulary the scripts use, split by who wrote them: **owner** = his own stacks',
          'harvested to scripts by XTJSON (2011-2026); **claude** = every other script in the project',
          'repos (written by Claude/Spark since 11 Nov 2026). This is the interpreter\'s to-do list:',
          'implement from the top down. Counts are approximate (a census, not a parser); names the',
          'scripts define themselves are left out; the project\'s own externals (`xt3d_*`, `entity.*`)',
          'are marked *project API* and are not LiveCode vocabulary. Custom properties appear under',
          'properties: they need no code, only working custom-property support.', '',
          '| | owner | claude |', '|---|---:|---:|',
          f'| script files (duplicates removed) | {len(groups["owner"])} | {len(groups["claude"])} |',
          f'| script lines | {nlines["owner"]} | {nlines["claude"]} |',
          f'| other people\'s scripts left out | {len(groups["third"])} | |']
    for k in kinds:
        co, cc = use['owner'][k], use['claude'][k]
        md.append(f'| distinct {gc.PLURAL[k]} | {len(co)} | {len(cc)} |')
    md += ['', '`/1k` = uses per 1000 script lines, so the two sides compare fairly. Status: `-` not started,',
           '`ok` implemented and tested against LiveCode 9.6.3.', '']
    for k in kinds:
        md += [f'## {gc.PLURAL[k].capitalize()}', '',
               '| name | owner | owner /1k | claude | claude /1k | files | status |', '|---|---:|---:|---:|---:|---:|---|']
        for r in report['vocabulary'][k]:
            tag = ' *(project API)*' if r['project_api'] else ''
            md.append(f"| `{r['name']}`{tag} | {r['owner']} | {per1k(r['owner'], 'owner'):.1f} | {r['claude']} | "
                      f"{per1k(r['claude'], 'claude'):.1f} | {r['owner_files'] + r['claude_files']} | - |")
        md.append('')
    open(a.out, 'w').write('\n'.join(md) + '\n')
    print({g: (len(groups[g]), nlines.get(g, 0)) for g in groups}, 'handlers', len(defined))
    for k in kinds:
        print(k, len(use['owner'][k]), 'owner,', len(use['claude'][k]), 'claude')


if __name__ == '__main__':
    main()
