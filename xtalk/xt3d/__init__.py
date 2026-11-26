"""xt3d on Python raylib (Phase 3): the xt3d_<Name> handlers of the LiveCode bridge, in Python.

A script written against xt3d (~/projects/xt3D_Raylib_Livecode_Bridge) calls the same names here.
- generated.py: one function per wrapped raylib function (tools/gen_xt3d_py.py; never edit it)
- helpers.py:   the bridge's hand-written helpers (xt3d_shim.c), by hand
- tables.py:    the integer handles for images, textures, models, cameras...

Every function takes the script's values (text) and gives back text, like the bridge:
numbers as numbers, booleans as true/false, struct results as comma-separated numbers.

This package needs the `raylib` package (.venv). The core interpreter does not import it; the
stack runtime installs it (install()) when raylib is there.
"""
import raylib as rl
from raylib import ffi
from ..values import XtError, to_num, to_text, numstr  # noqa: F401  (numstr is used by generated.py)


def ready():
    return rl.IsWindowReady()


# ---- script values -> C values (the LiveCode Builder side of the bridge does these).
# Measured against the real bridge 25 Nov (tests/xt3d_golden.json): a fraction is cut toward zero
# (2.7 -> 2, -2.7 -> -2); an empty argument is an error (LiveCode: 899); a negative number for an
# unsigned parameter is an error (863).
def N(x):
    if isinstance(x, float):
        return x
    if to_text(x).strip() == '':
        raise XtError('xt3d: a number is needed (empty)')
    return float(to_num(x))


def F(x):
    return N(x)


def I(x):
    return int(N(x))


def U(x):
    v = int(N(x))
    if v < 0:
        raise XtError('xt3d: a number of 0 or more is needed')
    return v & 0xFFFFFFFF


def W(v):
    """an int result as LiveCode Builder's CInt gives it: signed 32 bits (ColorToInt(255,0,0,255) = -16776961)"""
    return str(((int(v) + 0x80000000) & 0xFFFFFFFF) - 0x80000000)


def B(x):
    return to_text(x).lower() == 'true'


def C(x):
    return int(N(x)) & 0xFF                  # (unsigned char) in the shim: 256 -> 0, -1 -> 255


def S(x):
    # ZStringNative: the platform's native 8-bit text (Latin-1 here), not UTF-8
    return to_text(x).encode('latin-1', 'replace')


def R(p):
    """a C string result -> text (read back byte by byte in the bridge: Latin-1)"""
    return '' if p == ffi.NULL else ffi.string(p).decode('latin-1')


FUNCS = {}


def install():
    """make every xt3d_ name callable from scripts (functions and commands), in both run modes"""
    from .. import interp
    interp.EXTERNALS.update(load())


def load():
    """every xt3d function by lower-case name; helpers replace generated functions of the same name"""
    if not FUNCS:
        from . import generated
        FUNCS.update(generated.FUNCS)
        try:
            from . import helpers
            FUNCS.update(helpers.FUNCS)
        except ImportError:
            pass
    return FUNCS
