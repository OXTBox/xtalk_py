#!/usr/bin/env python3
"""x1-15: Spark (the local model in LM Studio) tries the xtpy MCP tools, and ONLY them (never LiveCode's).

    python3 -I tools/spark_try_xtpy.py [--model NAME] [--effort low] ["one question" ...]

LM Studio must be running with its server on (port 1234) and the model loaded. With no questions, asks the four
standard ones. Prints each tool call and the answer; everything also goes to run_files/spark_try_xtpy.log.
Uses LIB_MCP's ask_local chat (LM Studio through Windows' curl.exe), but its own tool list and system prompt.
"""
import importlib.util, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser('~/projects/LIB_MCP/python'))
from lib_mcp.ask_local import chat          # noqa: E402

LOG = os.path.join(ROOT, 'run_files', 'spark_try_xtpy.log')
SYSTEM = ('You test xTalk (LiveCode Script) stacks and games with the xtpy tools. They run hidden in Python. '
          'Call xtpy_primer first and follow it. xTalk is not JavaScript or Python. Answer briefly, and say '
          'plainly when a tool call failed.')
QUESTIONS = [
    'List the games and tell me how many there are.',
    'Open the game SquadBuggy, let it load, hold the d key for 120 frames, let it go, and tell me the game\'s '
    'stats line. Close it after.',
    'Open Thrmnlra, let it load, open its note box with the backtick key, type hello, and tell me the text of '
    'field "GameNote". Close it after.',
    'Use xtpy_diff to find what the xTalk expression 7 mod -3 gives.',
]


def load_pack():
    spec = importlib.util.spec_from_file_location('xtpy_tools', os.path.join(ROOT, 'mcp', 'xtpy_tools.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ask(pack, question, model, effort, log, max_steps=14):
    by = {t[0]: t for t in pack.TOOLS}
    tools = [{'type': 'function', 'function': {'name': n, 'description': d, 'parameters': s}}
             for n, _, d, s in pack.TOOLS if n != 'xtpy_snap']           # a text model: no pictures
    messages = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': question}]
    say = lambda t: (print(t), log.write(t + '\n'), log.flush())        # noqa: E731
    say('=== ' + question)
    try:
        for _ in range(max_steps):
            m = chat(model, messages, tools, effort)
            calls = m.get('tool_calls') or []
            if not calls:
                say('ANSWER: ' + (m.get('content') or '(no answer)'))
                return
            messages.append({'role': 'assistant', 'content': m.get('content') or '', 'tool_calls': calls})
            for c in calls:
                name = c['function']['name']
                try:
                    args = json.loads(c['function'].get('arguments') or '{}')
                except ValueError:
                    args = {}
                try:
                    out = by[name][1](args) if name in by else 'Unknown tool ' + name
                except (KeyError, ValueError, OSError) as e:
                    out = 'Tool failed: %s' % e
                text = out if isinstance(out, str) else '\n'.join(x.get('text', '') for x in out)
                say('[tool] %s %s -> %s' % (name, json.dumps(args), text[:200].replace('\n', ' | ')))
                messages.append({'role': 'tool', 'tool_call_id': c.get('id', ''), 'content': text})
        say('(stopped after %d steps)' % max_steps)
    finally:
        pack.t_close({'session': 'all'})


def main(a):
    if a[:1] in (['-h'], ['--help']):
        sys.exit(__doc__)
    model, effort = 'spark-x2.6-4b', 'low'
    if '--model' in a:
        i = a.index('--model'); model = a[i + 1]; del a[i:i + 2]
    if '--effort' in a:
        i = a.index('--effort'); effort = a[i + 1]; del a[i:i + 2]
    pack = load_pack()
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'w', encoding='utf-8') as log:
        for q in (a or QUESTIONS):
            ask(pack, q, model, effort, log)
    print('log:', LOG)


if __name__ == '__main__':
    main(sys.argv[1:])
