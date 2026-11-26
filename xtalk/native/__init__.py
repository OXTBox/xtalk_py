"""native: handlers written in plain Python that take the place of an xTalk handler (HANDOFF_NATIVE step 2).

One module a script, named after it; each has STACK (the stack's name, any case) and HANDLERS
{handler name in lower case: function}. A function is called like a translated handler: fn(rt, fr), where
rt is the script's runtime (rt.G = globals, rt.S = script locals) and fr.vars holds the parameters by their
lower-case names; it answers what the handler returns (text or an array: xTalk values at the edges, plain
numbers inside). The xTalk handler stays as the reference: tests run both and compare
(tests/test_native.py), and tools/frame_referee.py compares whole games.

Each module also has SIGS {handler: signature}: the xTalk handler it was written from. When the script
changes (the engine's xt3d edition is generated again from a newer engine), a handler whose statements
changed keeps its xTalk, with a warning, until the native function is checked and its signature updated.

A function may raise Fallback before it changes anything: the xTalk handler then runs instead (a value it
was not written for, e.g. text where a number belongs, gets the xTalk handler's own answer or error).

XTALK_NATIVE=0 turns every override off.
"""
import os


class Fallback(Exception):
    """this call is not one the native function handles: run the xTalk handler"""


def _table():
    from . import vibe_engine_xt3d, xt3d_testbench_host
    t = {}
    for m in (vibe_engine_xt3d, xt3d_testbench_host):
        t.setdefault(m.STACK.lower(), {}).update(m.HANDLERS)
        SIGS.setdefault(m.STACK.lower(), {}).update(m.SIGS)
        TRUSTS.setdefault(m.STACK.lower(), {}).update(getattr(m, 'TRUSTS', {}))
        DEPENDS.setdefault(m.STACK.lower(), {}).update(getattr(m, 'DEPENDS', {}))
    return t


def signature(h):
    """what a native function was written from: the handler's parameters and statements (comments, blank
    lines and where it sits in the file do not count). tools/native_sigs.py prints them."""
    import hashlib
    return hashlib.sha1(repr((tuple(p.lower() for p in h[2]), h[3])).encode()).hexdigest()[:12]


TABLE = None
SIGS = {}                                   # stack -> {handler: signature of the xTalk it was written from}
SKIPPED = set()
DEPENDS = {}                                # stack -> {handler: the handlers its native function copies inside}
TRUSTS = {}                                 # stack -> {handler: signature}: xTalk handlers that native code of
                                            # another script may stand in for (read their data directly) while
                                            # they are unchanged; rt.native_trusted names the ones that are
USED = {}                                   # (stack, handler) -> calls: what ran native (bench reports it)
FELL = {}                                   # (stack, handler) -> calls that went to the xTalk handler (Fallback)


def enabled():
    return os.environ.get('XTALK_NATIVE', '1') != '0'


def apply(rt, stack_name, script=None):
    """put the native functions in place of rt's handlers of that name (rt.handlers: name -> handler tuple,
    (kind, name, params, body, byref[, translated function])); answers the names replaced. script: the
    script's text (fast-mode handlers keep no statements to check the signature against)"""
    global TABLE
    if not enabled() or not stack_name:
        return []
    if TABLE is None:
        TABLE = _table()
    natives = TABLE.get(stack_name.lower())
    if not natives:
        return []
    done = []
    sigs = SIGS.get(stack_name.lower(), {})
    parsed = None
    rt.native_trusted = set()
    for name, want in TRUSTS.get(stack_name.lower(), {}).items():
        h = rt.handlers.get(name)
        if h is None:
            continue
        if h[3] is None:
            if parsed is None:
                from ..parser import parse_script
                parsed = parse_script(script) if script else {}
            h = parsed.get(name, h)
        if signature(h) == want:
            rt.native_trusted.add(name)
    for name, fn in natives.items():
        h = rt.handlers.get(name)
        if h is None:
            continue
        stated = h
        if h[3] is None:                     # fast mode keeps no statements: read them from the script
            if parsed is None:
                from ..parser import parse_script
                parsed = parse_script(script) if script else {}
            stated = parsed.get(name, h)
        stale = [d for d in DEPENDS.get(stack_name.lower(), {}).get(name, ()) if d not in rt.native_trusted]
        if stale:                             # a handler it copies inside changed: keep the xTalk
            if (stack_name, name) not in SKIPPED:
                SKIPPED.add((stack_name, name))
                import sys
                print('xtalk native: %s of stack %s copies %s, changed since: the xTalk handler runs'
                      % (h[1], stack_name, ', '.join(stale)), file=sys.stderr)
            continue
        if sigs.get(name) != signature(stated):    # the xTalk was changed since the native was written: keep the xTalk
            if (stack_name, name) not in SKIPPED:
                SKIPPED.add((stack_name, name))
                import sys
                print('xtalk native: %s of stack %s changed since its native version was written (signature %s, '
                      'native written for %s): the xTalk handler runs' % (h[1], stack_name, signature(stated),
                                                                          sigs.get(name)), file=sys.stderr)
            continue
        rt.handlers[name] = h[:5] + (_wrap(fn, h, stack_name),)
        done.append(name)
    return done


def _wrap(fn, h, stack_name):
    xt = h[5] if len(h) > 5 else None       # the translated handler (fast mode), or None: interpreted
    body = h[3]
    key = (stack_name, h[1])
    USED[key] = 0

    def native(rt, fr):
        USED[key] += 1
        try:
            return fn(rt, fr)
        except Fallback:
            FELL[key] = FELL.get(key, 0) + 1
            if xt is not None:
                return xt(rt, fr)
            rt.exec_block(body, fr)         # Return is caught by Interp.invoke, as for any handler
            return ''
    native.native = fn
    native.xtalk = xt
    return native
