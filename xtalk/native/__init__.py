"""native: handlers written in plain Python that take the place of an xTalk handler (HANDOFF_NATIVE step 2).

One module a script, named after it; each has STACK (the stack's name, any case) and HANDLERS
{handler name in lower case: function}. A function is called like a translated handler: fn(rt, fr), where
rt is the script's runtime (rt.G = globals, rt.S = script locals) and fr.vars holds the parameters by their
lower-case names; it answers what the handler returns (text or an array: xTalk values at the edges, plain
numbers inside). The xTalk handler stays as the reference: tests run both and compare
(tests/test_native.py), and tools/frame_referee.py compares whole games.

A function may raise Fallback before it changes anything: the xTalk handler then runs instead (a value it
was not written for, e.g. text where a number belongs, gets the xTalk handler's own answer or error).

XTALK_NATIVE=0 turns every override off.
"""
import os


class Fallback(Exception):
    """this call is not one the native function handles: run the xTalk handler"""


def _table():
    from . import vibe_engine_xt3d
    t = {}
    for m in (vibe_engine_xt3d,):
        t.setdefault(m.STACK.lower(), {}).update(m.HANDLERS)
    return t


TABLE = None
USED = {}                                   # (stack, handler) -> calls: what ran native (bench reports it)


def enabled():
    return os.environ.get('XTALK_NATIVE', '1') != '0'


def apply(rt, stack_name):
    """put the native functions in place of rt's handlers of that name (rt.handlers: name -> handler tuple,
    (kind, name, params, body, byref[, translated function])); answers the names replaced"""
    global TABLE
    if not enabled() or not stack_name:
        return []
    if TABLE is None:
        TABLE = _table()
    natives = TABLE.get(stack_name.lower())
    if not natives:
        return []
    done = []
    for name, fn in natives.items():
        h = rt.handlers.get(name)
        if h is None:
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
            if xt is not None:
                return xt(rt, fr)
            rt.exec_block(body, fr)         # Return is caught by Interp.invoke, as for any handler
            return ''
    native.native = fn
    native.xtalk = xt
    return native
