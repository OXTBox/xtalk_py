#!/usr/bin/env python3
"""xt3d_bench_check.py - the whole xt3d test bench (x1-04) opened hidden in Python, clicked, checked.

    .venv/bin/python -I tools/xt3d_bench_check.py [STEPS...] [--snap OUT.png] [--frames N] [--eval 'expr;;expr']

The bench is opened as his standalone opens it: the harvest of
xt3D_Raylib_Livecode_Bridge/testbench/xt3d_Bench_LibMCP.livecode (run_files/target_harvests/xt3d_Bench, remade by
tools/harvest_xt3d_bench.sh) starts, tries LIB_MCP's dev server (no sockets in Python: it says it could not
listen), then `go stack` the bench script (testbench/xt3d_testBench_lib_mcp.livecodescript, read as it is).

STEPS, done in order (each followed by --frames frames, default 30):
    click:NAME          a click on the control of that short name (gamesBtn, faceBtn, spinChk, checksBtn...)
    pick:NAME:LINE      click line LINE (a number or the text) of list field NAME (fileList:3, fileList:SquadBuggy)
    game:NAME           xbPlayGame NAME (as picking it from the Games list)
    key:CODE            rawKeyDown CODE (65307 = Escape)
    answer:TEXT         the reply to the next answer folder / answer file dialog
    frames:N            N more frames
    snap:FILE           a picture of the window now

The checks write nothing of his: real_folders, so files are read from where they are, writes go to run_files.
"""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
HARVEST = os.path.join(ROOT, 'run_files', 'target_harvests', 'xt3d_Bench')


def open_bench(hidden=True, real_app=False):
    """the runtime + view with the starter open and the bench shown"""
    if not os.path.isdir(HARVEST):
        sys.exit('no harvest at %s: run tools/harvest_xt3d_bench.sh' % HARVEST)
    from xtalk.stack import StackRuntime
    from xtalk.stack.view import View
    rt = StackRuntime(HARVEST, real_folders=True, real_app=real_app)
    if not getattr(rt.harvest.main, 'filename', ''):         # the effective filename: the starter finds the bench above it
        rt.harvest.main.filename = str(rt.harvest.manifest['sourceFile']).replace('\\', '/')
    v = View(rt, hidden=hidden)
    return rt, v


def main(a):
    os.environ.setdefault('WAYLAND_DISPLAY', 'no-wayland')
    if os.environ['WAYLAND_DISPLAY'] != 'no-wayland':
        os.environ['WAYLAND_DISPLAY'] = 'no-wayland'   # a hidden window's framebuffer resizes only on X11
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d       # noqa: E731
    frames = int(opt('--frames', 30))
    snap = opt('--snap', os.path.join(ROOT, 'run_files', 'xt3d_bench.png'))
    steps = []
    skip = False
    for x in a:
        if skip:
            skip = False
            continue
        if x in ('--frames', '--snap', '--eval'):
            skip = True
            continue
        steps.append(x)
    from xtalk.interp import Interp
    Interp.CATCH_LOG = []
    t0 = time.perf_counter()
    rt, v = open_bench()
    rt.open()
    for _ in range(frames):
        v.frame()
    print('opened in %.2f s; shown stack: %s' % (time.perf_counter() - t0, rt.default_stack.name))
    bench = rt.harvest.stack('xt3dTestBenchLibMCP')
    for s in steps:
        kind, _, arg = s.partition(':')
        t = time.perf_counter()
        n = frames
        if kind == 'click':
            o = rt.host.resolve('control "%s" of card 1 of stack "xt3dTestBenchLibMCP"' % arg)
            r = o.rect
            x, y = (r[0] + r[2]) // 2, (r[1] + r[3]) // 2
            if o.type == 'button' and str(o.props.get('style', '')).lower() == 'checkbox':
                x = r[0] + 6                   # the box itself
            down = rt.mouse_down(x, y)
            rt.mouse_up(x, y, down_on=down)
        elif kind == 'pick':
            name, _, line = arg.partition(':')
            o = rt.host.resolve('field "%s" of card 1 of stack "xt3dTestBenchLibMCP"' % name)
            lines = o.text.split('\n')
            print('   %s: %d lines: %s' % (name, len(lines), ', '.join(lines[:12])))
            i = int(line) if line.isdigit() else lines.index(line) + 1   # a line number or the line itself
            rt.host.set_prop('field "%s" of card 1 of stack "xt3dTestBenchLibMCP"' % name, 'hilitedLines', str(i), None)
            rt.message(o, 'mouseUp', ['1'])
        elif kind == 'game':
            rt.message(bench.children[0], 'xbPlayGame', [arg])
        elif kind == 'key':
            rt.raw_key(int(arg))
        elif kind == 'answer':
            rt.dialog_answers.append(arg)
            n = 0
        elif kind == 'frames':
            n = int(arg)
        elif kind == 'snap':
            v.snapshot(arg)
            n = 0
        else:
            sys.exit('unknown step %s' % s)
        f0 = time.perf_counter()
        for _ in range(n):
            v.frame()
        f1 = time.perf_counter()
        info = rt.host.resolve('field "info" of card 1 of stack "xt3dTestBenchLibMCP"', must=False)
        print('%-24s %.2f s (+%d frames %.1f a second)  info: %s' % (
            s, f0 - t, n, n / (f1 - f0) if n and f1 > f0 else 0,
            (info.text if info is not None else '')[:160].replace('\n', ' | ')))
    if '--eval' in a:
        from xtalk.parser import parse_expr
        from xtalk.interp import Frame
        c = rt.ctx[id(bench)]
        for ex in opt('--eval', '').split(';;'):
            fr = Frame([])
            try:
                print('eval %s = %r' % (ex, str(c.ev(parse_expr(ex), fr))[:400]))
            except Exception as e:             # noqa: BLE001
                print('eval %s: %s' % (ex, e))
    v.snapshot(snap)
    log = rt.host.resolve('field "log" of card 1 of stack "xt3dTestBenchLibMCP"', must=False)
    if log is not None and log.text.strip():
        print('log field:', log.text[-300:].replace('\n', ' | '))
    from collections import Counter
    for t, k in Counter(Interp.CATCH_LOG).most_common(12):
        print('caught by a try (%dx): %s' % (k, t[:400]))
    for e in rt.errors[:20]:
        print('script error:', *e)
    for o, e in rt.load_errors[:20]:
        print('does not compile:', o, e)
    print('script errors: %d; saved %s' % (len(rt.errors), snap))
    t = time.perf_counter()
    rt.close_stack() if hasattr(rt, 'close_stack') else None
    print('closed in %.2f s; errors after closing: %d' % (time.perf_counter() - t, len(rt.errors)))
    for e in rt.errors[:20]:
        print('script error:', *e)
    v.close()
    sys.stdout.flush()
    os._exit(1 if rt.errors else 0)


if __name__ == '__main__':
    main(sys.argv[1:])
