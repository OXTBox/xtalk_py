"""Generated from corpus/libraries/lib_bit.livecodescript by xtalk_py/xtalk/transpile.py. Do not edit: the xTalk script is the source."""
from xtalk.pyrt import *  # noqa: F401,F403


def h_bit_blank(rt, fr):
    # function Bit.Blank pWidth, pHeight
    fr.vars['trow'] = fr.vars.get('trow', "")
    fr.vars['tgrid'] = fr.vars.get('tgrid', "")
    if to_bool(rt.binop('=', rt.getvar(fr, 'pHeight'), '')):
        _v1 = rt.getvar(fr, 'pWidth')
        rt.put_var(fr, 'pHeight', _v1, 'into')
    for _ in range(int(to_num(to_text(rt.getvar(fr, 'pWidth'))))):
        rt.put_var(fr, 'tRow', '0', 'after')
    for _ in range(int(to_num(to_text(rt.getvar(fr, 'pHeight'))))):
        _v2 = rt.binop('&', rt.getvar(fr, 'tRow'), '\n')
        rt.put_var(fr, 'tGrid', _v2, 'after')
    _c3 = to_text(rt.getvar(fr, 'tGrid'))
    rt.put_var(fr, 'tGrid', rt.cut_chunk('char', _c3, '-1', None), 'into')
    return rt.getvar(fr, 'tGrid')


def h_bit_width(rt, fr):
    # function Bit.Width pGrid
    return str(ch.count(to_text(rt.get_chunk('line', rt.getvar(fr, 'pGrid'), '1', None)), 'char', **rt.delims()))


def h_bit_height(rt, fr):
    # function Bit.Height pGrid
    return str(ch.count(to_text(rt.getvar(fr, 'pGrid')), 'line', **rt.delims()))


def h_bit_count(rt, fr):
    # function Bit.Count pGrid
    fr.vars['tall'] = fr.vars.get('tall', "")
    _v1 = rt.getvar(fr, 'pGrid')
    rt.put_var(fr, 'tAll', _v1, 'into')
    _a2 = '\n'
    _b3 = ''
    _c4 = to_text(rt.getvar(fr, 'tAll'))
    if _a2 != "":
        rt.put_var(fr, 'tAll', _c4.replace(_a2, _b3), 'into')
    _a5 = '0'
    _b6 = ''
    _c7 = to_text(rt.getvar(fr, 'tAll'))
    if _a5 != "":
        rt.put_var(fr, 'tAll', _c7.replace(_a5, _b6), 'into')
    return str(ch.count(to_text(rt.getvar(fr, 'tAll')), 'char', **rt.delims()))


def h_bit_invert(rt, fr):
    # function Bit.Invert pGrid
    _a1 = '1'
    _b2 = 'x'
    _c3 = to_text(rt.getvar(fr, 'pGrid'))
    if _a1 != "":
        rt.put_var(fr, 'pGrid', _c3.replace(_a1, _b2), 'into')
    _a4 = '0'
    _b5 = '1'
    _c6 = to_text(rt.getvar(fr, 'pGrid'))
    if _a4 != "":
        rt.put_var(fr, 'pGrid', _c6.replace(_a4, _b5), 'into')
    _a7 = 'x'
    _b8 = '0'
    _c9 = to_text(rt.getvar(fr, 'pGrid'))
    if _a7 != "":
        rt.put_var(fr, 'pGrid', _c9.replace(_a7, _b8), 'into')
    return rt.getvar(fr, 'pGrid')


def h_bit_fromlongstring(rt, fr):
    # function Bit.FromLongString pString, pWidth
    fr.vars['tgrid'] = fr.vars.get('tgrid', "")
    fr.vars['tstart'] = fr.vars.get('tstart', "")
    rt.put_var(fr, 'tStart', '1', 'into')
    while to_bool(rt.binop('<=', rt.getvar(fr, 'tStart'), str(ch.count(to_text(rt.getvar(fr, 'pString')), 'char', **rt.delims())))):
        _v1 = rt.binop('&', rt.get_chunk('char', rt.getvar(fr, 'pString'), rt.getvar(fr, 'tStart'), rt.binop('-', rt.binop('+', rt.getvar(fr, 'tStart'), rt.getvar(fr, 'pWidth')), '1')), '\n')
        rt.put_var(fr, 'tGrid', _v1, 'after')
        _a2 = rt.getvar(fr, 'pWidth')
        _c3 = rt.cur_raw(fr, 'tStart')
        rt.put_var(fr, 'tStart', rt.arith('add', _a2, _c3), 'into')
    _c4 = to_text(rt.getvar(fr, 'tGrid'))
    rt.put_var(fr, 'tGrid', rt.cut_chunk('char', _c4, '-1', None), 'into')
    return rt.getvar(fr, 'tGrid')


def h_bit_shift(rt, fr):
    # function Bit.Shift pGrid, pDirection
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['trow'] = fr.vars.get('trow', "")
    _sv1 = to_text(rt.getvar(fr, 'pDirection'))
    if rt.case_hit(_sv1, 'left'):
        _t2 = to_text(rt.getvar(fr, 'pGrid'))
        for _a3, _b4 in ch.spans(_t2, 'line', **rt.delims()):
            rt.setvar(fr, 'tRow', _t2[_a3:_b4])
            _v5 = rt.binop('&', rt.binop('&', rt.get_chunk('char', rt.getvar(fr, 'tRow'), '2', rt.unop('-', '1')), rt.get_chunk('char', rt.getvar(fr, 'tRow'), '1', None)), '\n')
            rt.put_var(fr, 'tOut', _v5, 'after')
    elif rt.case_hit(_sv1, 'right'):
        _t6 = to_text(rt.getvar(fr, 'pGrid'))
        for _a7, _b8 in ch.spans(_t6, 'line', **rt.delims()):
            rt.setvar(fr, 'tRow', _t6[_a7:_b8])
            _v9 = rt.binop('&', rt.binop('&', rt.get_chunk('char', rt.getvar(fr, 'tRow'), rt.unop('-', '1'), None), rt.get_chunk('char', rt.getvar(fr, 'tRow'), '1', rt.unop('-', '2'))), '\n')
            rt.put_var(fr, 'tOut', _v9, 'after')
    elif rt.case_hit(_sv1, 'up'):
        _v10 = rt.binop('&', rt.binop('&', rt.binop('&', rt.get_chunk('line', rt.getvar(fr, 'pGrid'), '2', rt.unop('-', '1')), '\n'), rt.get_chunk('line', rt.getvar(fr, 'pGrid'), '1', None)), '\n')
        rt.put_var(fr, 'tOut', _v10, 'into')
    elif rt.case_hit(_sv1, 'down'):
        _v11 = rt.binop('&', rt.binop('&', rt.binop('&', rt.get_chunk('line', rt.getvar(fr, 'pGrid'), rt.unop('-', '1'), None), '\n'), rt.get_chunk('line', rt.getvar(fr, 'pGrid'), '1', rt.unop('-', '2'))), '\n')
        rt.put_var(fr, 'tOut', _v11, 'into')
    else:
        return rt.getvar(fr, 'pGrid')
    _c12 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c12, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_bit_fliphorizontal(rt, fr):
    # function Bit.FlipHorizontal pGrid
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['trow'] = fr.vars.get('trow', "")
    fr.vars['tnew'] = fr.vars.get('tnew', "")
    fr.vars['tcol'] = fr.vars.get('tcol', "")
    _t1 = to_text(rt.getvar(fr, 'pGrid'))
    for _a2, _b3 in ch.spans(_t1, 'line', **rt.delims()):
        rt.setvar(fr, 'tRow', _t1[_a2:_b3])
        rt.put_var(fr, 'tNew', '', 'into')
        _x4 = to_num(to_text(str(ch.count(to_text(rt.getvar(fr, 'tRow')), 'char', **rt.delims()))))
        _e5 = to_num(to_text('1'))
        _s6 = -1
        while (_s6 < 0) and _x4 > _e5 + _s6:
            rt.setvar(fr, 'tCol', numstr(_x4))
            _x4 += _s6
            _v7 = rt.get_chunk('char', rt.getvar(fr, 'tRow'), rt.getvar(fr, 'tCol'), None)
            rt.put_var(fr, 'tNew', _v7, 'after')
        _v8 = rt.binop('&', rt.getvar(fr, 'tNew'), '\n')
        rt.put_var(fr, 'tOut', _v8, 'after')
    _c9 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c9, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_bit_flipvertical(rt, fr):
    # function Bit.FlipVertical pGrid
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['tlineno'] = fr.vars.get('tlineno', "")
    _x1 = to_num(to_text(str(ch.count(to_text(rt.getvar(fr, 'pGrid')), 'line', **rt.delims()))))
    _e2 = to_num(to_text('1'))
    _s3 = -1
    while (_s3 < 0) and _x1 > _e2 + _s3:
        rt.setvar(fr, 'tLineNo', numstr(_x1))
        _x1 += _s3
        _v4 = rt.binop('&', rt.get_chunk('line', rt.getvar(fr, 'pGrid'), rt.getvar(fr, 'tLineNo'), None), '\n')
        rt.put_var(fr, 'tOut', _v4, 'after')
    _c5 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c5, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_bit_rotate(rt, fr):
    # function Bit.Rotate pGrid, pDegrees
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['tnew'] = fr.vars.get('tnew', "")
    fr.vars['tw'] = fr.vars.get('tw', "")
    fr.vars['th'] = fr.vars.get('th', "")
    fr.vars['tcol'] = fr.vars.get('tcol', "")
    fr.vars['trowno'] = fr.vars.get('trowno', "")
    _v1 = rt.fn(fr, 'Bit.Width', [rt.getvar(fr, 'pGrid')], [('var', lambda _v: rt.put_var(fr, 'pGrid', _v, 'into'))])
    rt.put_var(fr, 'tW', _v1, 'into')
    _v2 = rt.fn(fr, 'Bit.Height', [rt.getvar(fr, 'pGrid')], [('var', lambda _v: rt.put_var(fr, 'pGrid', _v, 'into'))])
    rt.put_var(fr, 'tH', _v2, 'into')
    if to_bool(rt.binop('=', rt.getvar(fr, 'pDegrees'), '90')):
        _x3 = to_num(to_text('1'))
        _e4 = to_num(to_text(rt.getvar(fr, 'tW')))
        _s5 = 1
        while (_s5 > 0) and _x3 < _e4 + _s5:
            rt.setvar(fr, 'tCol', numstr(_x3))
            _x3 += _s5
            rt.put_var(fr, 'tNew', '', 'into')
            _x6 = to_num(to_text(rt.getvar(fr, 'tH')))
            _e7 = to_num(to_text('1'))
            _s8 = -1
            while (_s8 < 0) and _x6 > _e7 + _s8:
                rt.setvar(fr, 'tRowNo', numstr(_x6))
                _x6 += _s8
                _v9 = rt.get_chunk('char', rt.get_chunk('line', rt.getvar(fr, 'pGrid'), rt.getvar(fr, 'tRowNo'), None), rt.getvar(fr, 'tCol'), None)
                rt.put_var(fr, 'tNew', _v9, 'after')
            _v10 = rt.binop('&', rt.getvar(fr, 'tNew'), '\n')
            rt.put_var(fr, 'tOut', _v10, 'after')
    elif to_bool(rt.binop('=', rt.getvar(fr, 'pDegrees'), rt.unop('-', '90'))):
        _x11 = to_num(to_text(rt.getvar(fr, 'tW')))
        _e12 = to_num(to_text('1'))
        _s13 = -1
        while (_s13 < 0) and _x11 > _e12 + _s13:
            rt.setvar(fr, 'tCol', numstr(_x11))
            _x11 += _s13
            rt.put_var(fr, 'tNew', '', 'into')
            _x14 = to_num(to_text('1'))
            _e15 = to_num(to_text(rt.getvar(fr, 'tH')))
            _s16 = 1
            while (_s16 > 0) and _x14 < _e15 + _s16:
                rt.setvar(fr, 'tRowNo', numstr(_x14))
                _x14 += _s16
                _v17 = rt.get_chunk('char', rt.get_chunk('line', rt.getvar(fr, 'pGrid'), rt.getvar(fr, 'tRowNo'), None), rt.getvar(fr, 'tCol'), None)
                rt.put_var(fr, 'tNew', _v17, 'after')
            _v18 = rt.binop('&', rt.getvar(fr, 'tNew'), '\n')
            rt.put_var(fr, 'tOut', _v18, 'after')
    else:
        return rt.getvar(fr, 'pGrid')
    _c19 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c19, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_bit_pad(rt, fr):
    # function Bit.Pad pGrid, pWidth, pHeight
    fr.vars['tw'] = fr.vars.get('tw', "")
    fr.vars['th'] = fr.vars.get('th', "")
    fr.vars['tleft'] = fr.vars.get('tleft', "")
    fr.vars['ttop'] = fr.vars.get('ttop', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['tside'] = fr.vars.get('tside', "")
    fr.vars['tright'] = fr.vars.get('tright', "")
    fr.vars['trow'] = fr.vars.get('trow', "")
    fr.vars['tlineno'] = fr.vars.get('tlineno', "")
    _v1 = rt.fn(fr, 'Bit.Width', [rt.getvar(fr, 'pGrid')], [('var', lambda _v: rt.put_var(fr, 'pGrid', _v, 'into'))])
    rt.put_var(fr, 'tW', _v1, 'into')
    _v2 = rt.fn(fr, 'Bit.Height', [rt.getvar(fr, 'pGrid')], [('var', lambda _v: rt.put_var(fr, 'pGrid', _v, 'into'))])
    rt.put_var(fr, 'tH', _v2, 'into')
    if to_bool(rt.binop('=', rt.getvar(fr, 'pHeight'), '')):
        _v3 = rt.getvar(fr, 'pWidth')
        rt.put_var(fr, 'pHeight', _v3, 'into')
    if to_bool(('true' if (rt.truth(rt.binop('<', rt.getvar(fr, 'pWidth'), rt.getvar(fr, 'tW'))) or rt.truth(rt.binop('<', rt.getvar(fr, 'pHeight'), rt.getvar(fr, 'tH')))) else 'false')):
        return rt.getvar(fr, 'pGrid')
    _v4 = rt.binop('div', rt.binop('-', rt.getvar(fr, 'pWidth'), rt.getvar(fr, 'tW')), '2')
    rt.put_var(fr, 'tLeft', _v4, 'into')
    _v5 = rt.binop('div', rt.binop('-', rt.getvar(fr, 'pHeight'), rt.getvar(fr, 'tH')), '2')
    rt.put_var(fr, 'tTop', _v5, 'into')
    _v6 = rt.get_chunk('line', rt.fn(fr, 'Bit.Blank', [rt.getvar(fr, 'tLeft'), '1'], [('var', lambda _v: rt.put_var(fr, 'tLeft', _v, 'into')), None]), '1', None)
    rt.put_var(fr, 'tSide', _v6, 'into')
    _v7 = rt.get_chunk('line', rt.fn(fr, 'Bit.Blank', [rt.binop('-', rt.binop('-', rt.getvar(fr, 'pWidth'), rt.getvar(fr, 'tW')), rt.getvar(fr, 'tLeft')), '1'], [None, None]), '1', None)
    rt.put_var(fr, 'tRight', _v7, 'into')
    _v8 = rt.get_chunk('line', rt.fn(fr, 'Bit.Blank', [rt.getvar(fr, 'pWidth'), '1'], [('var', lambda _v: rt.put_var(fr, 'pWidth', _v, 'into')), None]), '1', None)
    rt.put_var(fr, 'tRow', _v8, 'into')
    for _ in range(int(to_num(to_text(rt.getvar(fr, 'tTop'))))):
        _v9 = rt.binop('&', rt.getvar(fr, 'tRow'), '\n')
        rt.put_var(fr, 'tOut', _v9, 'after')
    _x10 = to_num(to_text('1'))
    _e11 = to_num(to_text(rt.getvar(fr, 'tH')))
    _s12 = 1
    while (_s12 > 0) and _x10 < _e11 + _s12:
        rt.setvar(fr, 'tLineNo', numstr(_x10))
        _x10 += _s12
        _v13 = rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tSide'), rt.get_chunk('line', rt.getvar(fr, 'pGrid'), rt.getvar(fr, 'tLineNo'), None)), rt.getvar(fr, 'tRight')), '\n')
        rt.put_var(fr, 'tOut', _v13, 'after')
    for _ in range(int(to_num(to_text(rt.binop('-', rt.binop('-', rt.getvar(fr, 'pHeight'), rt.getvar(fr, 'tH')), rt.getvar(fr, 'tTop')))))):
        _v14 = rt.binop('&', rt.getvar(fr, 'tRow'), '\n')
        rt.put_var(fr, 'tOut', _v14, 'after')
    _c15 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c15, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_bit_topbm(rt, fr):
    # function Bit.ToPBM pGrid
    fr.vars['tbits'] = fr.vars.get('tbits', "")
    _v1 = rt.getvar(fr, 'pGrid')
    rt.put_var(fr, 'tBits', _v1, 'into')
    _a2 = '1'
    _b3 = '1 '
    _c4 = to_text(rt.getvar(fr, 'tBits'))
    if _a2 != "":
        rt.put_var(fr, 'tBits', _c4.replace(_a2, _b3), 'into')
    _a5 = '0'
    _b6 = '0 '
    _c7 = to_text(rt.getvar(fr, 'tBits'))
    if _a5 != "":
        rt.put_var(fr, 'tBits', _c7.replace(_a5, _b6), 'into')
    return rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&&', rt.binop('&', rt.binop('&', 'P1', '\n'), rt.fn(fr, 'Bit.Width', [rt.getvar(fr, 'pGrid')], [('var', lambda _v: rt.put_var(fr, 'pGrid', _v, 'into'))])), rt.fn(fr, 'Bit.Height', [rt.getvar(fr, 'pGrid')], [('var', lambda _v: rt.put_var(fr, 'pGrid', _v, 'into'))])), '\n'), rt.getvar(fr, 'tBits')), '\n')


def h_bit_frompbm(rt, fr):
    # function Bit.FromPBM pPBM
    fr.vars['tline'] = fr.vars.get('tline', "")
    fr.vars['tbody'] = fr.vars.get('tbody', "")
    fr.vars['tw'] = fr.vars.get('tw', "")
    fr.vars['th'] = fr.vars.get('th', "")
    fr.vars['tbits'] = fr.vars.get('tbits', "")
    fr.vars['twordno'] = fr.vars.get('twordno', "")
    rt.put_var(fr, 'tBody', '', 'into')
    _t1 = to_text(rt.getvar(fr, 'pPBM'))
    for _a2, _b3 in ch.spans(_t1, 'line', **rt.delims()):
        rt.setvar(fr, 'tLine', _t1[_a2:_b3])
        if to_bool(rt.binop('=', rt.get_chunk('char', rt.get_chunk('word', rt.getvar(fr, 'tLine'), '1', None), '1', None), '#')):
            continue
        _v4 = rt.binop('&', rt.getvar(fr, 'tLine'), ' ')
        rt.put_var(fr, 'tBody', _v4, 'after')
    if to_bool(rt.binop('<>', rt.get_chunk('word', rt.getvar(fr, 'tBody'), '1', None), 'P1')):
        return ''
    _v5 = rt.get_chunk('word', rt.getvar(fr, 'tBody'), '2', None)
    rt.put_var(fr, 'tW', _v5, 'into')
    _v6 = rt.get_chunk('word', rt.getvar(fr, 'tBody'), '3', None)
    rt.put_var(fr, 'tH', _v6, 'into')
    _x7 = to_num(to_text('4'))
    _e8 = to_num(to_text(str(ch.count(to_text(rt.getvar(fr, 'tBody')), 'word', **rt.delims()))))
    _s9 = 1
    while (_s9 > 0) and _x7 < _e8 + _s9:
        rt.setvar(fr, 'tWordNo', numstr(_x7))
        _x7 += _s9
        _v10 = rt.get_chunk('word', rt.getvar(fr, 'tBody'), rt.getvar(fr, 'tWordNo'), None)
        rt.put_var(fr, 'tBits', _v10, 'after')
    return rt.fn(fr, 'Bit.FromLongString', [rt.get_chunk('char', rt.getvar(fr, 'tBits'), '1', rt.binop('*', rt.getvar(fr, 'tW'), rt.getvar(fr, 'tH'))), rt.getvar(fr, 'tW')], [('chunk', lambda _v: rt.put_var(fr, 'tBits', rt.put_chunk('char', rt.cur_text(fr, 'tBits'), '1', rt.binop('*', rt.getvar(fr, 'tW'), rt.getvar(fr, 'tH')), _v, 'into'), 'into')), ('var', lambda _v: rt.put_var(fr, 'tW', _v, 'into'))])


def h_bit_torows(rt, fr):
    # function Bit.ToRows pGrid
    fr.vars['trow'] = fr.vars.get('trow', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['ttotal'] = fr.vars.get('ttotal', "")
    fr.vars['tcol'] = fr.vars.get('tcol', "")
    _t1 = to_text(rt.getvar(fr, 'pGrid'))
    for _a2, _b3 in ch.spans(_t1, 'line', **rt.delims()):
        rt.setvar(fr, 'tRow', _t1[_a2:_b3])
        rt.put_var(fr, 'tTotal', '0', 'into')
        _x4 = to_num(to_text('1'))
        _e5 = to_num(to_text(str(ch.count(to_text(rt.getvar(fr, 'tRow')), 'char', **rt.delims()))))
        _s6 = 1
        while (_s6 > 0) and _x4 < _e5 + _s6:
            rt.setvar(fr, 'tCol', numstr(_x4))
            _x4 += _s6
            if to_bool(rt.binop('=', rt.get_chunk('char', rt.getvar(fr, 'tRow'), rt.getvar(fr, 'tCol'), None), '1')):
                _a7 = rt.binop('^', '2', rt.binop('-', rt.getvar(fr, 'tCol'), '1'))
                _c8 = rt.cur_raw(fr, 'tTotal')
                rt.put_var(fr, 'tTotal', rt.arith('add', _a7, _c8), 'into')
        _v9 = rt.binop('&', rt.getvar(fr, 'tTotal'), ',')
        rt.put_var(fr, 'tOut', _v9, 'after')
    _c10 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c10, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_bit_fromrows(rt, fr):
    # function Bit.FromRows pRows, pWidth
    fr.vars['tvalue'] = fr.vars.get('tvalue', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['tnew'] = fr.vars.get('tnew', "")
    fr.vars['tcol'] = fr.vars.get('tcol', "")
    if to_bool(rt.binop('=', rt.getvar(fr, 'pWidth'), '')):
        rt.put_var(fr, 'pWidth', '16', 'into')
    _t1 = to_text(rt.getvar(fr, 'pRows'))
    for _a2, _b3 in ch.spans(_t1, 'item', **rt.delims()):
        rt.setvar(fr, 'tValue', _t1[_a2:_b3])
        rt.put_var(fr, 'tNew', '', 'into')
        _x4 = to_num(to_text('1'))
        _e5 = to_num(to_text(rt.getvar(fr, 'pWidth')))
        _s6 = 1
        while (_s6 > 0) and _x4 < _e5 + _s6:
            rt.setvar(fr, 'tCol', numstr(_x4))
            _x4 += _s6
            _v7 = rt.binop('mod', rt.binop('div', rt.fn(fr, 'trunc', [rt.getvar(fr, 'tValue')], [('var', lambda _v: rt.put_var(fr, 'tValue', _v, 'into'))]), rt.binop('^', '2', rt.binop('-', rt.getvar(fr, 'tCol'), '1'))), '2')
            rt.put_var(fr, 'tNew', _v7, 'after')
        _v8 = rt.binop('&', rt.getvar(fr, 'tNew'), '\n')
        rt.put_var(fr, 'tOut', _v8, 'after')
    _c9 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c9, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_bit_maze(rt, fr):
    # function Bit.Maze pCols, pRows, pSeed
    fr.vars['tw'] = fr.vars.get('tw', "")
    fr.vars['th'] = fr.vars.get('th', "")
    fr.vars['tgrid'] = fr.vars.get('tgrid', "")
    fr.vars['trow'] = fr.vars.get('trow', "")
    fr.vars['tr'] = fr.vars.get('tr', "")
    fr.vars['tc'] = fr.vars.get('tc', "")
    fr.vars['tseen'] = fr.vars.get('tseen', "")
    fr.vars['tstack'] = fr.vars.get('tstack', "")
    fr.vars['ttop'] = fr.vars.get('ttop', "")
    fr.vars['tx'] = fr.vars.get('tx', "")
    fr.vars['ty'] = fr.vars.get('ty', "")
    fr.vars['tdirs'] = fr.vars.get('tdirs', "")
    fr.vars['tn'] = fr.vars.get('tn', "")
    fr.vars['tpick'] = fr.vars.get('tpick', "")
    fr.vars['tnx'] = fr.vars.get('tnx', "")
    fr.vars['tny'] = fr.vars.get('tny', "")
    fr.vars['tsteps'] = fr.vars.get('tsteps', "")
    fr.vars['td'] = fr.vars.get('td', "")
    fr.vars['tline'] = fr.vars.get('tline', "")
    if to_bool(rt.binop('=', rt.getvar(fr, 'pRows'), '')):
        _v1 = rt.getvar(fr, 'pCols')
        rt.put_var(fr, 'pRows', _v1, 'into')
    if to_bool(('true' if (rt.truth(rt.binop('<', rt.getvar(fr, 'pCols'), '1')) or rt.truth(rt.binop('<', rt.getvar(fr, 'pRows'), '1'))) else 'false')):
        return ''
    if to_bool(rt.unop('not', rt.isa(rt.getvar(fr, 'pSeed'), 'integer'))):
        rt.put_var(fr, 'pSeed', '1', 'into')
    _v2 = rt.binop('mod', rt.fn(fr, 'abs', [rt.getvar(fr, 'pSeed')], [('var', lambda _v: rt.put_var(fr, 'pSeed', _v, 'into'))]), '2147483647')
    rt.put_var(fr, 'tX', _v2, 'into')
    if to_bool(rt.binop('=', rt.getvar(fr, 'tX'), '0')):
        rt.put_var(fr, 'tX', '1', 'into')
    _v3 = rt.binop('+', rt.binop('*', '2', rt.getvar(fr, 'pCols')), '1')
    rt.put_var(fr, 'tW', _v3, 'into')
    _v4 = rt.binop('+', rt.binop('*', '2', rt.getvar(fr, 'pRows')), '1')
    rt.put_var(fr, 'tH', _v4, 'into')
    rt.put_var(fr, 'tR', '1', 'into')
    while to_bool(rt.binop('<=', rt.getvar(fr, 'tR'), rt.getvar(fr, 'tH'))):
        rt.put_var(fr, 'tC', '1', 'into')
        while to_bool(rt.binop('<=', rt.getvar(fr, 'tC'), rt.getvar(fr, 'tW'))):
            rt.put_idx(fr, 'tGrid', rt.key_vals([rt.getvar(fr, 'tR'), rt.getvar(fr, 'tC')]), '1', 'into')
            _a5 = '1'
            _c6 = rt.cur_raw(fr, 'tC')
            rt.put_var(fr, 'tC', rt.arith('add', _a5, _c6), 'into')
        _a7 = '1'
        _c8 = rt.cur_raw(fr, 'tR')
        rt.put_var(fr, 'tR', rt.arith('add', _a7, _c8), 'into')
    rt.put_idx(fr, 'tSeen', rt.key_vals(['1,1']), '1', 'into')
    rt.put_idx(fr, 'tGrid', rt.key_vals(['2', '2']), '0', 'into')
    rt.put_var(fr, 'tStack', '1,1', 'into')
    rt.put_var(fr, 'tSteps', '0', 'into')
    while to_bool(('true' if (rt.truth(rt.binop('<>', rt.getvar(fr, 'tStack'), '')) and rt.truth(rt.binop('<', rt.getvar(fr, 'tSteps'), rt.binop('+', rt.binop('*', rt.binop('*', '4', rt.getvar(fr, 'pCols')), rt.getvar(fr, 'pRows')), '10')))) else 'false')):
        _a9 = '1'
        _c10 = rt.cur_raw(fr, 'tSteps')
        rt.put_var(fr, 'tSteps', rt.arith('add', _a9, _c10), 'into')
        _v11 = rt.get_chunk('line', rt.getvar(fr, 'tStack'), rt.unop('-', '1'), None)
        rt.put_var(fr, 'tTop', _v11, 'into')
        _v12 = rt.get_chunk('item', rt.getvar(fr, 'tTop'), '1', None)
        rt.put_var(fr, 'tC', _v12, 'into')
        _v13 = rt.get_chunk('item', rt.getvar(fr, 'tTop'), '2', None)
        rt.put_var(fr, 'tR', _v13, 'into')
        rt.put_var(fr, 'tDirs', '', 'into')
        _t14 = to_text(rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', '0,-1', '\n'), '1,0'), '\n'), '0,1'), '\n'), '-1,0'))
        for _a15, _b16 in ch.spans(_t14, 'line', **rt.delims()):
            rt.setvar(fr, 'tD', _t14[_a15:_b16])
            _v17 = rt.binop('+', rt.getvar(fr, 'tC'), rt.get_chunk('item', rt.getvar(fr, 'tD'), '1', None))
            rt.put_var(fr, 'tNX', _v17, 'into')
            _v18 = rt.binop('+', rt.getvar(fr, 'tR'), rt.get_chunk('item', rt.getvar(fr, 'tD'), '2', None))
            rt.put_var(fr, 'tNY', _v18, 'into')
            if to_bool(('true' if (rt.truth(('true' if (rt.truth(('true' if (rt.truth(('true' if (rt.truth(rt.binop('>=', rt.getvar(fr, 'tNX'), '1')) and rt.truth(rt.binop('<=', rt.getvar(fr, 'tNX'), rt.getvar(fr, 'pCols')))) else 'false')) and rt.truth(rt.binop('>=', rt.getvar(fr, 'tNY'), '1'))) else 'false')) and rt.truth(rt.binop('<=', rt.getvar(fr, 'tNY'), rt.getvar(fr, 'pRows')))) else 'false')) and rt.truth(rt.binop('=', rt.get_idx(fr, 'tSeen', rt.key_vals([rt.binop('&', rt.binop('&', rt.getvar(fr, 'tNX'), ','), rt.getvar(fr, 'tNY'))])), ''))) else 'false')):
                _v19 = rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tNX'), ','), rt.getvar(fr, 'tNY')), '\n')
                rt.put_var(fr, 'tDirs', _v19, 'after')
        if to_bool(rt.binop('=', rt.getvar(fr, 'tDirs'), '')):
            _c20 = to_text(rt.getvar(fr, 'tStack'))
            rt.put_var(fr, 'tStack', rt.cut_chunk('line', _c20, rt.unop('-', '1'), None), 'into')
            continue
        _c21 = to_text(rt.getvar(fr, 'tDirs'))
        rt.put_var(fr, 'tDirs', rt.cut_chunk('char', _c21, '-1', None), 'into')
        _v22 = rt.binop('mod', rt.binop('*', rt.getvar(fr, 'tX'), '16807'), '2147483647')
        rt.put_var(fr, 'tX', _v22, 'into')
        _v23 = str(ch.count(to_text(rt.getvar(fr, 'tDirs')), 'line', **rt.delims()))
        rt.put_var(fr, 'tN', _v23, 'into')
        _v24 = rt.get_chunk('line', rt.getvar(fr, 'tDirs'), rt.binop('+', rt.binop('mod', rt.getvar(fr, 'tX'), rt.getvar(fr, 'tN')), '1'), None)
        rt.put_var(fr, 'tPick', _v24, 'into')
        _v25 = rt.get_chunk('item', rt.getvar(fr, 'tPick'), '1', None)
        rt.put_var(fr, 'tNX', _v25, 'into')
        _v26 = rt.get_chunk('item', rt.getvar(fr, 'tPick'), '2', None)
        rt.put_var(fr, 'tNY', _v26, 'into')
        rt.put_idx(fr, 'tSeen', rt.key_vals([rt.getvar(fr, 'tPick')]), '1', 'into')
        rt.put_idx(fr, 'tGrid', rt.key_vals([rt.binop('+', rt.getvar(fr, 'tR'), rt.getvar(fr, 'tNY')), rt.binop('+', rt.getvar(fr, 'tC'), rt.getvar(fr, 'tNX'))]), '0', 'into')
        rt.put_idx(fr, 'tGrid', rt.key_vals([rt.binop('*', '2', rt.getvar(fr, 'tNY')), rt.binop('*', '2', rt.getvar(fr, 'tNX'))]), '0', 'into')
        _v27 = rt.binop('&', '\n', rt.getvar(fr, 'tPick'))
        rt.put_var(fr, 'tStack', _v27, 'after')
    rt.put_var(fr, 'tRow', '', 'into')
    rt.put_var(fr, 'tR', '1', 'into')
    while to_bool(rt.binop('<=', rt.getvar(fr, 'tR'), rt.getvar(fr, 'tH'))):
        rt.put_var(fr, 'tLine', '', 'into')
        rt.put_var(fr, 'tC', '1', 'into')
        while to_bool(rt.binop('<=', rt.getvar(fr, 'tC'), rt.getvar(fr, 'tW'))):
            _v28 = rt.get_idx(fr, 'tGrid', rt.key_vals([rt.getvar(fr, 'tR'), rt.getvar(fr, 'tC')]))
            rt.put_var(fr, 'tLine', _v28, 'after')
            _a29 = '1'
            _c30 = rt.cur_raw(fr, 'tC')
            rt.put_var(fr, 'tC', rt.arith('add', _a29, _c30), 'into')
        _v31 = rt.binop('&', rt.getvar(fr, 'tLine'), '\n')
        rt.put_var(fr, 'tRow', _v31, 'after')
        _a32 = '1'
        _c33 = rt.cur_raw(fr, 'tR')
        rt.put_var(fr, 'tR', rt.arith('add', _a32, _c33), 'into')
    _c34 = to_text(rt.getvar(fr, 'tRow'))
    rt.put_var(fr, 'tRow', rt.cut_chunk('char', _c34, '-1', None), 'into')
    return rt.getvar(fr, 'tRow')


def install(rt):
    """add these handlers to rt, then run the script-level local/global/constant lines"""
    fr = Frame([])
    rt.handlers['bit.blank'] = ('function', 'Bit.Blank', ['pWidth', 'pHeight'], None, [], h_bit_blank)
    rt.handlers['bit.width'] = ('function', 'Bit.Width', ['pGrid'], None, [], h_bit_width)
    rt.handlers['bit.height'] = ('function', 'Bit.Height', ['pGrid'], None, [], h_bit_height)
    rt.handlers['bit.count'] = ('function', 'Bit.Count', ['pGrid'], None, [], h_bit_count)
    rt.handlers['bit.invert'] = ('function', 'Bit.Invert', ['pGrid'], None, [], h_bit_invert)
    rt.handlers['bit.fromlongstring'] = ('function', 'Bit.FromLongString', ['pString', 'pWidth'], None, [], h_bit_fromlongstring)
    rt.handlers['bit.shift'] = ('function', 'Bit.Shift', ['pGrid', 'pDirection'], None, [], h_bit_shift)
    rt.handlers['bit.fliphorizontal'] = ('function', 'Bit.FlipHorizontal', ['pGrid'], None, [], h_bit_fliphorizontal)
    rt.handlers['bit.flipvertical'] = ('function', 'Bit.FlipVertical', ['pGrid'], None, [], h_bit_flipvertical)
    rt.handlers['bit.rotate'] = ('function', 'Bit.Rotate', ['pGrid', 'pDegrees'], None, [], h_bit_rotate)
    rt.handlers['bit.pad'] = ('function', 'Bit.Pad', ['pGrid', 'pWidth', 'pHeight'], None, [], h_bit_pad)
    rt.handlers['bit.topbm'] = ('function', 'Bit.ToPBM', ['pGrid'], None, [], h_bit_topbm)
    rt.handlers['bit.frompbm'] = ('function', 'Bit.FromPBM', ['pPBM'], None, [], h_bit_frompbm)
    rt.handlers['bit.torows'] = ('function', 'Bit.ToRows', ['pGrid'], None, [], h_bit_torows)
    rt.handlers['bit.fromrows'] = ('function', 'Bit.FromRows', ['pRows', 'pWidth'], None, [], h_bit_fromrows)
    rt.handlers['bit.maze'] = ('function', 'Bit.Maze', ['pCols', 'pRows', 'pSeed'], None, [], h_bit_maze)
