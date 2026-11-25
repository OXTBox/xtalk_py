#!/usr/bin/env python3
"""survey_stacks.py - open every harvested stack in the Python runtime (no window) and click
every button on every card, to see what Phase 2 still lacks.

    python3 -I tools/survey_stacks.py                     all harvests in ~/projects/XTJSON
    python3 -I tools/survey_stacks.py FOLDER [FOLDER...]   just these
    python3 -I tools/survey_stacks.py --seconds 3          time allowed per click (default 5)

What it clicks: each visible button, and each other control whose own script has a
mouseUp or mouseDown handler, on each card in turn (a fresh copy of the stack per card, so
one card's clicks cannot spoil the next). After each click 1 second of virtual time passes,
so `send ... in` messages run too.

Prints a short table per stack, then the most common error causes over all stacks.
The full list (every click and what happened) goes to run_files/survey.txt.
"""
import collections, os, re, signal, sys, traceback
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from xtalk.stack import StackRuntime   # noqa: E402

XTJSON = os.path.expanduser('~/projects/XTJSON')
FILES = os.path.join(ROOT, 'run_files', 'survey')


class TooLong(BaseException):
    """a click ran past its time (a BaseException, so no script error handler swallows it)"""


def _alarm(signum, frame):
    raise TooLong()


def harvests(args):
    if args:
        return [os.path.expanduser(a) for a in args]
    return sorted(os.path.join(XTJSON, d) for d in os.listdir(XTJSON)
                  if os.path.isfile(os.path.join(XTJSON, d, 'manifest.json')))


def cause(text):
    """an error text with the details that differ (numbers, names in quotes) blurred,
    so the same cause in different places counts as one"""
    t = re.sub(r'"[^"]*"', '"…"', text)
    t = re.sub(r"'[^']*'", "'…'", t)
    return re.sub(r'\b\d+(\.\d+)?\b', 'N', t)[:120]


def targets(card, rt):
    out = []
    for o in card.flat():
        if o.type == 'group' or not rt._shown(o):
            continue
        s = o.script.lower()
        if o.type == 'button' or re.search(r'^\s*on\s+mouse(up|down)\b', s, re.M):
            out.append(o)
    return out


def timed(seconds, fn, *a):
    signal.alarm(seconds)
    try:
        return fn(*a)
    finally:
        signal.alarm(0)


def survey(folder, seconds, log):
    name = os.path.basename(folder.rstrip('/'))
    res = collections.Counter()
    causes = collections.Counter()
    log.append('\n==== %s' % name)
    try:
        first = StackRuntime(folder, files_dir=FILES)
    except Exception as e:  # the harvest itself does not load
        log.append('  does not load: %s' % e)
        res['no load'] += 1
        return name, res, causes
    res['load errors'] = len(first.load_errors)
    for where, e in first.load_errors:
        log.append('  load error  %s: %s' % (where, e))
        causes['(load) ' + cause(str(e))] += 1
    cards = list(first.default_stack.children)
    for ci in range(len(cards)):
        rt = StackRuntime(folder, files_dir=FILES)
        rt.start_programs = False          # shell() of a .py: noted, never started (no windows on the screen)
        card = rt.default_stack.children[ci]
        try:
            timed(seconds, rt.open)
            if rt.default_stack.current is not card:
                timed(seconds, rt.go_card, card)
        except TooLong:
            log.append('  card %d: opening it ran past %d s' % (ci + 1, seconds))
            res['too long'] += 1
            continue
        except Exception as e:
            log.append('  card %d: opening it broke the runtime: %s' % (ci + 1, e))
            res['runtime bug'] += 1
            continue
        if rt.closed:                      # the window would end right after opening (he saw it "open and quit")
            log.append('  card %d: the window closes itself while opening' % (ci + 1))
            causes['(window) closes itself while opening'] += 1
            res['errors'] += 1
        for err in rt.errors:
            log.append('  card %d open: %s' % (ci + 1, ' | '.join(err)))
            causes[cause(err[2])] += 1
            res['errors'] += 1
        for o in targets(card, rt):
            label = rt.host.name_of(o, 'short') or ('%s id %s' % (o.type, o.props.get('id', '?')))
            n_err, n_ans = len(rt.errors), len(rt.answers)
            if rt.default_stack.current is not card:   # an earlier click went to another card
                rt.go_card(card)
            try:
                timed(seconds, rt.click, '%s,%s' % o.loc)
                timed(seconds, rt.tick, 1000)
            except TooLong:
                log.append('  card %d  %-24s ran past %d s' % (ci + 1, label, seconds))
                res['too long'] += 1
                continue
            except Exception as e:
                log.append('  card %d  %-24s RUNTIME BUG %s' % (ci + 1, label,
                                                               traceback.format_exception_only(type(e), e)[-1].strip()))
                causes['(runtime bug) ' + cause('%s: %s' % (type(e).__name__, e))] += 1
                res['runtime bug'] += 1
                continue
            new = rt.errors[n_err:]
            res['clicks'] += 1
            if new:
                res['errors'] += 1
                for err in new:
                    log.append('  card %d  %-24s error  %s' % (ci + 1, label, ' | '.join(err)))
                    causes[cause(err[2])] += 1
            else:
                res['ok'] += 1
                log.append('  card %d  %-24s ok%s' % (ci + 1, label,
                                                     '  (answer: %s)' % rt.answers[n_ans][:60] if len(rt.answers) > n_ans else ''))
    return name, res, causes


def main(a):
    seconds = 5
    if '--seconds' in a:
        i = a.index('--seconds')
        seconds = int(a[i + 1])
        del a[i:i + 2]
    signal.signal(signal.SIGALRM, _alarm)
    sys.setrecursionlimit(5000)
    os.makedirs(FILES, exist_ok=True)
    log, total = [], collections.Counter()
    print('%-38s %6s %4s %6s %8s %7s %6s' % ('stack', 'clicks', 'ok', 'errors', 'too long', 'rt bug', 'load'))
    for folder in harvests(a):
        name, res, causes = survey(folder, seconds, log)
        total.update(causes)
        print('%-38s %6d %4d %6d %8d %7d %6s' % (name[:38], res['clicks'], res['ok'], res['errors'],
                                                 res['too long'], res['runtime bug'],
                                                 'NO' if res['no load'] else res['load errors']))
    print('\nMost common causes (all stacks):')
    for c, n in total.most_common(15):
        print('  %4d  %s' % (n, c))
    out = os.path.join(ROOT, 'run_files', 'survey.txt')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log) + '\n\nCauses:\n' + '\n'.join('%5d  %s' % (n, c) for c, n in total.most_common()) + '\n')
    print('\nEvery click: %s' % os.path.relpath(out, ROOT))


if __name__ == '__main__':
    main(sys.argv[1:])
