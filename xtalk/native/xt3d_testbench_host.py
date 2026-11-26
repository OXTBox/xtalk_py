"""Native handlers for the xt3d testbench host (stack "xt3dTestBenchLibMCP",
xt3D_Raylib_Livecode_Bridge/testbench/xt3d_testBench_lib_mcp.livecodescript, read unchanged).

xbDrawGame draws a frame of a Vibecode3D game into the view image: one xt3d model per object (with its fill
when hiding is on), then the 2D lines (particles, weapon, HUD). The native version makes the same xt3d calls
with the same numbers, in the same order, straight to raylib: no text made for each argument and read back.
Everything it reads is checked before the first call, so a frame it was not written for (text where a
number belongs) goes to the xTalk handler whole (Fallback), never half drawn.
"""
import math
from ..values import NumStr, numstr, to_text, to_num, num_cmp, is_numeric_text, text_num, XtError
from .. import chunks as ch
from . import Fallback

STACK = 'xt3dTestBenchLibMCP'

# the commands and functions xbDrawGame calls: a script handler of the same name would take them (Fallback)
XT3D = ('xt3d_cameraset', 'xt3d_begintexturemode', 'xt3d_clearbackground', 'xt3d_beginmode3d',
        'xt3d_setbackfaceculling', 'xt3d_modelsettransform', 'xt3d_drawmodel', 'xt3d_drawmodelwiresex',
        'xt3d_endmode3d', 'xt3d_drawlineex', 'xt3d_drawtext', 'xt3d_endtexturemode', 'xt3d_drawtexturepro',
        'xt3d_rendertextureimagedata', 'atan')


def _num(v):
    """arithmetic's reading of a value (empty = 0); not a number: Fallback"""
    t = type(v)
    if t is float:
        return v
    if t is NumStr:
        return v.raw
    if isinstance(v, dict):
        raise Fallback()
    r = text_num(v) if t is str else None
    if r is not None:
        return r
    if to_text(v).strip() == '':
        return 0.0
    raise Fallback()


def _arg(v):
    """an xt3d argument that must not be empty (the bridge refuses an empty number)"""
    if isinstance(v, dict) or to_text(v).strip() == '':
        raise Fallback()
    try:
        to_num(v)
    except XtError:
        raise Fallback() from None
    return v


def _items(t, n):
    p = t.split(',')
    if len(p) < n:
        p += [''] * (n - len(p))
    return p


def xb_draw_game(rt, fr):
    """command xbDrawGame @pFrame"""
    from ..interp import EXTERNALS as X
    frame = fr.vars.get('pframe', '')
    if not isinstance(frame, dict):
        raise Fallback()
    for n in XT3D:
        if rt.lookup(n)[1] is not None:
            raise Fallback()
    S = rt.S
    for k in ('kgamescale', 'ksample'):
        if k not in S:
            raise Fallback()
    t_s = _num(S['kgamescale'])
    t_k = _num(S['ksample'])
    view = rt.obj_name('image', 'view')
    # ---- read and check everything first
    bg = frame.get('background', '')
    if isinstance(bg, dict):
        raise Fallback()
    bg = _items(to_text(bg), 3)
    back = [_arg(x) for x in bg[:3]]
    objs = []
    text = frame.get('objects', '')
    if isinstance(text, dict):
        raise Fallback()
    for a, b in ch.spans(to_text(text), 'line'):
        it = to_text(text)[a:b].split('\t')
        it += [''] * (4 - len(it))
        col = _items(it[2], 4)
        xf = _items(it[3], 12)
        objs.append((it[0], [_arg(c) for c in col[:4]], [_num(x) for x in xf[:12]], col, xf))
    lines2d = frame.get('lines2d', '')
    cols2d = frame.get('colors2d', '')
    strokes = []
    if isinstance(lines2d, dict):
        for name in list(lines2d):
            c = cols2d.get(name, '') if isinstance(cols2d, dict) else ''
            if isinstance(c, dict):
                raise Fallback()
            pts = lines2d[name]
            if isinstance(pts, dict):
                raise Fallback()
            pts = to_text(pts)
            seq, cc = [], None
            for a, b in ch.spans(pts, 'line'):
                p = pts[a:b]
                if ch.count(p, 'item') < 2:
                    seq.append(None)
                    continue
                q = _items(p, 2)
                seq.append((_num(q[0]), _num(q[1])))
                if cc is None:
                    c3 = _items(to_text(c), 3)
                    cc = [_arg(x) for x in c3[:3]]
            strokes.append((seq, cc))
    # ---- now the same calls as the xTalk, in the same order
    proj = rt.fn(fr, 'Vibe.Projection', [], [])
    if isinstance(proj, dict):
        raise Fallback()
    pi = _items(to_text(proj), 2)
    p1, p2 = _num(pi[0]), _num(pi[1])
    h = _num(rt.host.get_prop(view, 'height', None))
    if p1 == 0:
        raise Fallback()
    fov = 2.0 * math.atan(h / 2.0 * p2 / p1) * 180.0 / math.pi
    last = X['xt3d_cameraset'](S['scamera'], 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, -1.0, 0.0, fov, 0.0)
    hide = num_cmp(_num(rt.fn(fr, 'xbCullMode', [], [])), 1.0) >= 0
    S['sgamefillcount'] = '0'
    fills = 0
    X['xt3d_begintexturemode'](S['sbig'])
    X['xt3d_clearbackground'](back[0], back[1], back[2], 255.0)
    X['xt3d_beginmode3d'](S['scamera'])
    X['xt3d_setbackfaceculling']('false')
    set_t, draw_m, wires = X['xt3d_modelsettransform'], X['xt3d_drawmodel'], X['xt3d_drawmodelwiresex']
    for name, col, x, _, _ in objs:
        model = rt.fn(fr, 'xbGameModel', [name], [])
        if not _is_pos_number(model):
            continue
        if hide:
            fill = rt.fn(fr, 'xbGameFill', [name], [])
            if _is_pos_number(fill):
                f = t_s * 1.003
                set_t(fill, x[0] * f, x[3] * f, x[6] * f, 0.0, x[1] * f, x[4] * f, x[7] * f, 0.0,
                      x[2] * f, x[5] * f, x[8] * f, 0.0, x[9] * f, x[10] * f, x[11] * f, 1.0)
                draw_m(fill, 0.0, 0.0, 0.0, 1.0, back[0], back[1], back[2], 255.0)
                fills += 1
                S['sgamefillcount'] = numstr(float(fills))
        s = t_s
        set_t(model, x[0] * s, x[3] * s, x[6] * s, 0.0, x[1] * s, x[4] * s, x[7] * s, 0.0,
              x[2] * s, x[5] * s, x[8] * s, 0.0, x[9] * s, x[10] * s, x[11] * s, 1.0)
        last = wires(model, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, col[0], col[1], col[2], col[3])
    X['xt3d_setbackfaceculling']('true')
    last = X['xt3d_endmode3d']()
    tl = _num(rt.host.get_prop(view, 'left', None))
    tt = _num(rt.host.get_prop(view, 'top', None))
    line = X['xt3d_drawlineex']
    for seq, cc in strokes:
        prev = None
        for p in seq:
            if p is None:
                prev = None
                continue
            if prev is not None:
                last = line((prev[0] - tl) * t_k, (prev[1] - tt) * t_k, (p[0] - tl) * t_k, (p[1] - tt) * t_k, t_k,
                            cc[0], cc[1], cc[2], 255.0)
            prev = p
    if not (_is_true(S.get('sviewonly', ''))):
        txt = '%s fps   hiding %s   %s' % (to_text(S.get('sgamefps', '')), to_text(rt.fn(fr, 'xbCullMode', [], [])),
                                          to_text(S.get('sgamestats', '')))
        last = X['xt3d_drawtext'](txt, 10.0 * t_k, (_num(S.get('sviewh', '')) - 28.0) * t_k, 16.0 * t_k,
                                  120.0, 120.0, 120.0, 255.0)
    X['xt3d_endtexturemode']()
    X['xt3d_begintexturemode'](S['starget'])
    vw, vh = S.get('svieww', ''), S.get('sviewh', '')
    X['xt3d_drawtexturepro'](S['sbigtexture'], 0.0, 0.0, _num(vw) * t_k, -(_num(vh) * t_k), 0.0, 0.0, vw, vh,
                             0.0, 0.0, 0.0, 255.0, 255.0, 255.0, 255.0)
    last = X['xt3d_endtexturemode']()
    rt.result = to_text(last)
    data = rt.fn(fr, 'xt3d_RenderTextureImageData', [S['starget']], [])
    rt.host.set_prop(view, 'imagedata', rt.setprop_value(data, True), None)
    return ''


def _is_pos_number(v):
    """`v is a number and v > 0` (and the xTalk's `is not a number or <= 0` the other way round)"""
    if isinstance(v, dict):
        return False
    t = to_text(v)
    if not is_numeric_text(t):
        return False
    return num_cmp(_num(v), 0.0) > 0


def _is_true(v):
    return not isinstance(v, dict) and to_text(v).lower() == 'true'


SIGS = {'xbdrawgame': 'f3bf03ef86ea'}   # the xTalk it was written from (tools/native_sigs.py)

HANDLERS = {
    'xbdrawgame': xb_draw_game,
}
