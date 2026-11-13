#!/usr/bin/env python3
"""spark_catalogue.py - Spark's first-look catalogue of the scripts waiting in
~/projects/LIB_LLMIN/xtalk_py/toCorpus/.

    python3 tools/spark_catalogue.py                  every script in toCorpus/ without notes yet
    python3 tools/spark_catalogue.py FILE...          just these files (anywhere)
    python3 tools/spark_catalogue.py --dry-run FILE   show how a file is split; ask nothing
    options: --model spark-x2.6-4b  --max-lines 80  --pause 3  --effort none  --force (redo notes)

Each script is split into parts of a few handlers (Spark is a small model), each part is
sent with the PART prompt from prompts/spark_catalogue_prompt.md, then Spark summarises
its own part notes with the SUMMARY prompt. The result goes to LIB_LLMIN/xtalk_py/toCorpus/_spark/<file>.md
for Claude to review. Gentle on the GPU: one request at a time, capped answers, a pause
between requests. LM Studio must be running with the model loaded (port 1234); it is
reached through Windows' curl.exe, as in LIB_MCP's ask_local.py.
"""
import argparse, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# the shared inbox (~/projects/LIB_LLMIN/<project>/...), outside every repo
INBOX = os.path.join(os.path.dirname(ROOT), 'LIB_LLMIN', 'xtalk_py', 'toCorpus')
NOTES = os.path.join(INBOX, '_spark')
PROMPT = os.path.join(ROOT, 'prompts', 'spark_catalogue_prompt.md')
URL = 'http://127.0.0.1:1234/v1/chat/completions'
START = re.compile(r'^\s*(?:private\s+)?(on|function|command|getprop|setprop)\s+([A-Za-z0-9_.]+)', re.I)


def prompts():
    text = open(PROMPT, encoding='utf-8').read()
    parts = re.split(r'^## (SYSTEM|PART|SUMMARY)\s*$', text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def fill(template, **values):
    # only {name} placeholders the runner knows; braces elsewhere stay as they are
    return re.sub(r'\{(\w+)\}', lambda m: str(values.get(m.group(1), m.group(0))), template)


def split(lines, max_lines):
    """Parts that start at handler boundaries; a part holds whole handlers up to max_lines
    (a longer handler gets a part of its own, cut into max_lines pieces if it must be)."""
    blocks, cur = [], []
    for line in lines:
        if START.match(line) and cur:
            # comments and blank lines just above a handler belong to that handler
            keep = len(cur)
            while keep > 0 and (not cur[keep - 1].strip() or cur[keep - 1].lstrip().startswith(('--', '#', '//'))):
                keep -= 1
            if keep > 0:
                blocks.append(cur[:keep])
                cur = cur[keep:]
        cur.append(line)
    if cur:
        blocks.append(cur)
    parts, cur = [], []
    for b in blocks:
        if cur and len(cur) + len(b) > max_lines:
            parts.append(cur)
            cur = []
        if len(b) > max_lines * 2:
            for i in range(0, len(b), max_lines):
                parts.append(b[i:i + max_lines])
            continue
        cur += b
    if cur:
        parts.append(cur)
    return parts


def chat(model, system, user, max_tokens, effort):
    body = {'model': model, 'temperature': 0.2, 'max_tokens': max_tokens, 'reasoning_effort': effort,
            'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}
    r = subprocess.run(['curl.exe', '-sS', '-m', '900', URL, '-H', 'Content-Type: application/json',
                        '--data-binary', '@-'], input=json.dumps(body).encode('utf-8'), capture_output=True)
    if r.returncode != 0:
        sys.exit('LM Studio is not answering at %s (start it and load the model): %s'
                 % (URL, r.stderr.decode(errors='replace').strip()))
    d = json.loads(r.stdout.decode('utf-8', 'replace'))
    if 'choices' not in d:
        sys.exit('LM Studio error: %s' % d)
    out = d['choices'][0]['message'].get('content') or ''
    return re.sub(r'<think>.*?</think>', '', out, flags=re.S).strip()


def header_of(lines):
    out = []
    for line in lines[:40]:
        s = line.strip()
        if s.lower().startswith('script "'):
            continue
        if s.startswith(('--', '#', '//')):
            out.append(s)
        elif s:
            break
    return '\n'.join(out[:12]) or '(none)'


def catalogue(path, a, p):
    name = os.path.basename(path)
    out = os.path.join(a.notes, name + '.md')
    if os.path.exists(out) and not a.force and not a.dry_run:
        print('skip (notes exist):', name)
        return
    text = open(path, encoding='utf-8', errors='replace').read().replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    handlers = [m.group(2) for m in (START.match(l) for l in lines) if m]
    parts = split(lines, a.max_lines)
    print('%s: %d lines, %d handlers, %d parts' % (name, len(lines), len(handlers), len(parts)))
    if a.dry_run:
        for i, part in enumerate(parts, 1):
            names = [m.group(2) for m in (START.match(l) for l in part) if m]
            print('  part %d: %d lines: %s' % (i, len(part), ', '.join(names) or '(declarations)'))
        return
    os.makedirs(a.notes, exist_ok=True)
    notes = []
    for i, part in enumerate(parts, 1):
        here = [m.group(2) for m in (START.match(l) for l in part) if m]
        context = 'This part is the start of the file.' if i == 1 else 'It continues from earlier parts.'
        user = fill(p['PART'], file=name, part=i, parts=len(parts), context=context, script='\n'.join(part),
                    names=', '.join(here) or '(none: declarations and comments only)')
        print('  part %d/%d ...' % (i, len(parts)), flush=True)
        count = sum(1 for l in part if START.match(l))
        budget = min(a.max_tokens, 400 + 330 * max(1, count))   # about 250 tokens a handler, with room
        notes.append('## Part %d of %d\n\n%s' % (i, len(parts), chat(a.model, p['SYSTEM'], user, budget, a.effort)))
        with open(out + '.partial', 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(notes))
        time.sleep(a.pause)
    user = fill(p['SUMMARY'], file=name, lines=len(lines), handlers=len(handlers),
                header=header_of(lines), notes='\n\n'.join(notes), names=', '.join(handlers))
    print('  summary ...', flush=True)
    summary = chat(a.model, p['SYSTEM'], user, 3000, a.effort)
    with open(out, 'w', encoding='utf-8') as f:
        f.write('<!-- Spark first-look catalogue of %s (model %s, %s). DRAFT for Claude to review. -->\n\n'
                % (name, a.model, time.strftime('%Y-%m-%d %H:%M')))
        f.write(summary + '\n\n---\n\n# Handler notes\n\n' + '\n\n'.join(notes) + '\n')
    os.remove(out + '.partial')
    print('  wrote', os.path.relpath(out, ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--model', default='spark-x2.6-4b')
    ap.add_argument('--max-lines', type=int, default=80)
    ap.add_argument('--max-tokens', type=int, default=4000, help='cap per part (the budget grows with the handlers in it)')
    ap.add_argument('--effort', default='none', help='reasoning effort; "none" (thinking off) works best: '
                    'with thinking on, Spark spends its whole answer budget thinking')
    ap.add_argument('--pause', type=float, default=3)
    ap.add_argument('--notes', default=NOTES)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    files = a.files or sorted(os.path.join(INBOX, n) for n in os.listdir(INBOX)
                              if n.lower().endswith(('.livecodescript', '.txt'))
                              and n != 'README.md' and 'Zone.Identifier' not in n)
    if not files:
        print('nothing waiting in', INBOX)
    p = prompts()
    for f in files:
        catalogue(f, a, p)


if __name__ == '__main__':
    main()
