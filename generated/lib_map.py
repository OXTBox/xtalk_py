"""Generated from corpus/libraries/lib_map.livecodescript by xtalk_py/xtalk/transpile.py. Do not edit: the xTalk script is the source."""
from xtalk.pyrt import *  # noqa: F401,F403


def h_map_stitch(rt, fr):
    # function Map.Stitch pSections, pLayout
    fr.vars['tw'] = fr.vars.get('tw', "")
    fr.vars['th'] = fr.vars.get('th', "")
    fr.vars['tname'] = fr.vars.get('tname', "")
    fr.vars['tkeys'] = fr.vars.get('tkeys', "")
    fr.vars['tworld'] = fr.vars.get('tworld', "")
    fr.vars['tlayoutrow'] = fr.vars.get('tlayoutrow', "")
    fr.vars['trowno'] = fr.vars.get('trowno', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['tsolidrow'] = fr.vars.get('tsolidrow', "")
    fr.vars['twordno'] = fr.vars.get('twordno', "")
    _v1 = B['keys'](rt, fr, rt.getvar(fr, 'pSections'))
    rt.put_var(fr, 'tKeys', _v1, 'into')
    if to_bool(rt.binop('=', rt.getvar(fr, 'tKeys'), '')):
        return 'ERROR: no sections'
    _v2 = rt.get_chunk('line', rt.getvar(fr, 'tKeys'), '1', None)
    rt.put_var(fr, 'tName', _v2, 'into')
    _v3 = str(ch.count(to_text(rt.get_chunk('line', rt.get_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tName')])), '1', None)), 'char', **rt.delims()))
    rt.put_var(fr, 'tW', _v3, 'into')
    _v4 = str(ch.count(to_text(rt.get_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tName')]))), 'line', **rt.delims()))
    rt.put_var(fr, 'tH', _v4, 'into')
    _t5 = to_text(rt.getvar(fr, 'tKeys'))
    for _a6, _b7 in ch.spans(_t5, 'line', **rt.delims()):
        rt.setvar(fr, 'tName', _t5[_a6:_b7])
        if to_bool(('true' if (rt.truth(rt.binop('<>', str(ch.count(to_text(rt.get_chunk('line', rt.get_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tName')])), '1', None)), 'char', **rt.delims())), rt.getvar(fr, 'tW'))) or rt.truth(rt.binop('<>', str(ch.count(to_text(rt.get_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tName')]))), 'line', **rt.delims())), rt.getvar(fr, 'tH')))) else 'false')):
            return rt.binop('&', rt.binop('&', rt.binop('&&', rt.binop('&&', rt.binop('&&', 'ERROR: section', rt.getvar(fr, 'tName')), 'is not'), rt.getvar(fr, 'tW')), 'x'), rt.getvar(fr, 'tH'))
    for _ in range(int(to_num(to_text(rt.getvar(fr, 'tW'))))):
        rt.put_var(fr, 'tSolidRow', '1', 'after')
    _t8 = to_text(rt.getvar(fr, 'pLayout'))
    for _a9, _b10 in ch.spans(_t8, 'line', **rt.delims()):
        rt.setvar(fr, 'tLayoutRow', _t8[_a9:_b10])
        if to_bool(rt.binop('=', rt.get_chunk('word', rt.getvar(fr, 'tLayoutRow'), '1', None), '')):
            continue
        _x11 = to_num(to_text('1'))
        _e12 = to_num(to_text(rt.getvar(fr, 'tH')))
        _s13 = 1
        while (_s13 > 0) and _x11 < _e12 + _s13:
            rt.setvar(fr, 'tRowNo', numstr(_x11))
            _x11 += _s13
            rt.put_var(fr, 'tOut', '', 'into')
            _x14 = to_num(to_text('1'))
            _e15 = to_num(to_text(str(ch.count(to_text(rt.getvar(fr, 'tLayoutRow')), 'word', **rt.delims()))))
            _s16 = 1
            while (_s16 > 0) and _x14 < _e15 + _s16:
                rt.setvar(fr, 'tWordNo', numstr(_x14))
                _x14 += _s16
                _v17 = rt.get_chunk('word', rt.getvar(fr, 'tLayoutRow'), rt.getvar(fr, 'tWordNo'), None)
                rt.put_var(fr, 'tName', _v17, 'into')
                if to_bool(rt.binop('=', rt.getvar(fr, 'tName'), '-')):
                    _v18 = rt.getvar(fr, 'tSolidRow')
                    rt.put_var(fr, 'tOut', _v18, 'after')
                elif to_bool(rt.binop('among_lines', rt.getvar(fr, 'tName'), rt.getvar(fr, 'tKeys'))):
                    _v19 = rt.get_chunk('line', rt.get_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tName')])), rt.getvar(fr, 'tRowNo'), None)
                    rt.put_var(fr, 'tOut', _v19, 'after')
                else:
                    return rt.binop('&&', 'ERROR: no section named', rt.getvar(fr, 'tName'))
            _v20 = rt.binop('&', rt.getvar(fr, 'tOut'), '\n')
            rt.put_var(fr, 'tWorld', _v20, 'after')
    _c21 = to_text(rt.getvar(fr, 'tWorld'))
    rt.put_var(fr, 'tWorld', rt.cut_chunk('char', _c21, '-1', None), 'into')
    return rt.getvar(fr, 'tWorld')


def h_map_seams(rt, fr):
    # function Map.Seams pSections, pLayout
    fr.vars['trows'] = fr.vars.get('trows', "")
    fr.vars['trowno'] = fr.vars.get('trowno', "")
    fr.vars['tcol'] = fr.vars.get('tcol', "")
    fr.vars['ta'] = fr.vars.get('ta', "")
    fr.vars['tb'] = fr.vars.get('tb', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['tlayoutrow'] = fr.vars.get('tlayoutrow', "")
    fr.vars['tnext'] = fr.vars.get('tnext', "")
    fr.vars['tkeys'] = fr.vars.get('tkeys', "")
    fr.vars['tname'] = fr.vars.get('tname', "")
    _v1 = B['keys'](rt, fr, rt.getvar(fr, 'pSections'))
    rt.put_var(fr, 'tKeys', _v1, 'into')
    _v2 = rt.get_chunk('line', rt.getvar(fr, 'tKeys'), '1', None)
    rt.put_var(fr, 'tName', _v2, 'into')
    rt.put_var(fr, 'tRowNo', '0', 'into')
    _t3 = to_text(rt.getvar(fr, 'pLayout'))
    for _a4, _b5 in ch.spans(_t3, 'line', **rt.delims()):
        rt.setvar(fr, 'tLayoutRow', _t3[_a4:_b5])
        if to_bool(rt.binop('=', rt.get_chunk('word', rt.getvar(fr, 'tLayoutRow'), '1', None), '')):
            continue
        _a6 = '1'
        _c7 = rt.cur_raw(fr, 'tRowNo')
        rt.put_var(fr, 'tRowNo', rt.arith('add', _a6, _c7), 'into')
        _v8 = rt.getvar(fr, 'tLayoutRow')
        rt.put_idx(fr, 'tRows', rt.key_vals([rt.getvar(fr, 'tRowNo')]), _v8, 'into')
    _x9 = to_num(to_text('1'))
    _e10 = to_num(to_text(str(ch.count(to_text(B['keys'](rt, fr, rt.getvar(fr, 'tRows'))), 'line', **rt.delims()))))
    _s11 = 1
    while (_s11 > 0) and _x9 < _e10 + _s11:
        rt.setvar(fr, 'tRowNo', numstr(_x9))
        _x9 += _s11
        _x12 = to_num(to_text('1'))
        _e13 = to_num(to_text(str(ch.count(to_text(rt.get_idx(fr, 'tRows', rt.key_vals([rt.getvar(fr, 'tRowNo')]))), 'word', **rt.delims()))))
        _s14 = 1
        while (_s14 > 0) and _x12 < _e13 + _s14:
            rt.setvar(fr, 'tCol', numstr(_x12))
            _x12 += _s14
            _v15 = rt.get_chunk('word', rt.get_idx(fr, 'tRows', rt.key_vals([rt.getvar(fr, 'tRowNo')])), rt.getvar(fr, 'tCol'), None)
            rt.put_var(fr, 'tA', _v15, 'into')
            if to_bool(rt.binop('=', rt.getvar(fr, 'tA'), '-')):
                continue
            _v16 = rt.get_chunk('word', rt.get_idx(fr, 'tRows', rt.key_vals([rt.getvar(fr, 'tRowNo')])), rt.binop('+', rt.getvar(fr, 'tCol'), '1'), None)
            rt.put_var(fr, 'tB', _v16, 'into')
            if to_bool(('true' if (rt.truth(rt.binop('<>', rt.getvar(fr, 'tB'), '')) and rt.truth(rt.binop('<>', rt.getvar(fr, 'tB'), '-'))) else 'false')):
                _v17 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',east,'), rt.fn(fr, 'Map.SeamCompare', [rt.fn(fr, 'Map.Column', [rt.get_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tA')])), rt.unop('-', '1')], [('idx', lambda _v: rt.put_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tA')]), _v, 'into')), None]), rt.fn(fr, 'Map.Column', [rt.get_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tB')])), '1'], [('idx', lambda _v: rt.put_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tB')]), _v, 'into')), None])], [None, None])), '\n')
                rt.put_var(fr, 'tOut', _v17, 'after')
            if to_bool(rt.binop('<', rt.getvar(fr, 'tRowNo'), str(ch.count(to_text(B['keys'](rt, fr, rt.getvar(fr, 'tRows'))), 'line', **rt.delims())))):
                _v18 = rt.get_chunk('word', rt.get_idx(fr, 'tRows', rt.key_vals([rt.binop('+', rt.getvar(fr, 'tRowNo'), '1')])), rt.getvar(fr, 'tCol'), None)
                rt.put_var(fr, 'tB', _v18, 'into')
                if to_bool(('true' if (rt.truth(rt.binop('<>', rt.getvar(fr, 'tB'), '')) and rt.truth(rt.binop('<>', rt.getvar(fr, 'tB'), '-'))) else 'false')):
                    _v19 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',south,'), rt.fn(fr, 'Map.SeamCompare', [rt.get_chunk('line', rt.get_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tA')])), rt.unop('-', '1'), None), rt.get_chunk('line', rt.get_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tB')])), '1', None)], [('chunk', lambda _v: rt.put_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tA')]), rt.put_chunk('line', to_text(rt.get_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tA')]))), rt.unop('-', '1'), None, _v, 'into'), 'into')), ('chunk', lambda _v: rt.put_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tB')]), rt.put_chunk('line', to_text(rt.get_idx(fr, 'pSections', rt.key_vals([rt.getvar(fr, 'tB')]))), '1', None, _v, 'into'), 'into'))])), '\n')
                    rt.put_var(fr, 'tOut', _v19, 'after')
    _c20 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c20, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_map_column(rt, fr):
    # function Map.Column pGrid, pCol
    fr.vars['trow'] = fr.vars.get('trow', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    _t1 = to_text(rt.getvar(fr, 'pGrid'))
    for _a2, _b3 in ch.spans(_t1, 'line', **rt.delims()):
        rt.setvar(fr, 'tRow', _t1[_a2:_b3])
        _v4 = rt.get_chunk('char', rt.getvar(fr, 'tRow'), rt.getvar(fr, 'pCol'), None)
        rt.put_var(fr, 'tOut', _v4, 'after')
    return rt.getvar(fr, 'tOut')


def h_map_seamcompare(rt, fr):
    # function Map.SeamCompare pEdgeA, pEdgeB
    fr.vars['ti'] = fr.vars.get('ti', "")
    fr.vars['tdoors'] = fr.vars.get('tdoors', "")
    fr.vars['tbad'] = fr.vars.get('tbad', "")
    rt.put_var(fr, 'tDoors', '0', 'into')
    _x1 = to_num(to_text('1'))
    _e2 = to_num(to_text(str(ch.count(to_text(rt.getvar(fr, 'pEdgeA')), 'char', **rt.delims()))))
    _s3 = 1
    while (_s3 > 0) and _x1 < _e2 + _s3:
        rt.setvar(fr, 'tI', numstr(_x1))
        _x1 += _s3
        if to_bool(('true' if (rt.truth(rt.binop('=', rt.get_chunk('char', rt.getvar(fr, 'pEdgeA'), rt.getvar(fr, 'tI'), None), '0')) and rt.truth(rt.binop('=', rt.get_chunk('char', rt.getvar(fr, 'pEdgeB'), rt.getvar(fr, 'tI'), None), '0'))) else 'false')):
            _a4 = '1'
            _c5 = rt.cur_raw(fr, 'tDoors')
            rt.put_var(fr, 'tDoors', rt.arith('add', _a4, _c5), 'into')
        elif to_bool(rt.binop('<>', rt.get_chunk('char', rt.getvar(fr, 'pEdgeA'), rt.getvar(fr, 'tI'), None), rt.get_chunk('char', rt.getvar(fr, 'pEdgeB'), rt.getvar(fr, 'tI'), None))):
            _v6 = rt.binop('&', rt.getvar(fr, 'tI'), ';')
            rt.put_var(fr, 'tBad', _v6, 'after')
    if to_bool(rt.binop('<>', rt.getvar(fr, 'tBad'), '')):
        _c7 = to_text(rt.getvar(fr, 'tBad'))
        rt.put_var(fr, 'tBad', rt.cut_chunk('char', _c7, '-1', None), 'into')
    return rt.binop('&', rt.binop('&', rt.getvar(fr, 'tDoors'), ','), rt.getvar(fr, 'tBad'))


def h_map_isopen(rt, fr):
    # function Map.IsOpen pWorld, pCol, pRow
    if to_bool(('true' if (rt.truth(('true' if (rt.truth(rt.binop('<', rt.getvar(fr, 'pCol'), '1')) or rt.truth(rt.binop('<', rt.getvar(fr, 'pRow'), '1'))) else 'false')) or rt.truth(rt.binop('>', rt.getvar(fr, 'pRow'), str(ch.count(to_text(rt.getvar(fr, 'pWorld')), 'line', **rt.delims()))))) else 'false')):
        return 'false'
    return rt.binop('=', rt.get_chunk('char', rt.get_chunk('line', rt.getvar(fr, 'pWorld'), rt.getvar(fr, 'pRow'), None), rt.getvar(fr, 'pCol'), None), '0')


def h_map_pieces(rt, fr):
    # function Map.Pieces pWorld
    fr.vars['th'] = fr.vars.get('th', "")
    fr.vars['tw'] = fr.vars.get('tw', "")
    fr.vars['trowno'] = fr.vars.get('trowno', "")
    fr.vars['tcol'] = fr.vars.get('tcol', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['trow'] = fr.vars.get('trow', "")
    _v1 = str(ch.count(to_text(rt.getvar(fr, 'pWorld')), 'line', **rt.delims()))
    rt.put_var(fr, 'tH', _v1, 'into')
    _x2 = to_num(to_text('1'))
    _e3 = to_num(to_text(rt.getvar(fr, 'tH')))
    _s4 = 1
    while (_s4 > 0) and _x2 < _e3 + _s4:
        rt.setvar(fr, 'tRowNo', numstr(_x2))
        _x2 += _s4
        _v5 = rt.get_chunk('line', rt.getvar(fr, 'pWorld'), rt.getvar(fr, 'tRowNo'), None)
        rt.put_var(fr, 'tRow', _v5, 'into')
        _v6 = str(ch.count(to_text(rt.getvar(fr, 'tRow')), 'char', **rt.delims()))
        rt.put_var(fr, 'tW', _v6, 'into')
        _x7 = to_num(to_text('1'))
        _e8 = to_num(to_text(rt.getvar(fr, 'tW')))
        _s9 = 1
        while (_s9 > 0) and _x7 < _e8 + _s9:
            rt.setvar(fr, 'tCol', numstr(_x7))
            _x7 += _s9
            if to_bool(rt.binop('<>', rt.get_chunk('char', rt.getvar(fr, 'tRow'), rt.getvar(fr, 'tCol'), None), '0')):
                continue
            _v10 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',floor'), '\n')
            rt.put_var(fr, 'tOut', _v10, 'after')
            _v11 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',roof'), '\n')
            rt.put_var(fr, 'tOut', _v11, 'after')
            if to_bool(rt.unop('not', rt.fn(fr, 'Map.IsOpen', [rt.getvar(fr, 'pWorld'), rt.getvar(fr, 'tCol'), rt.binop('-', rt.getvar(fr, 'tRowNo'), '1')], [('var', lambda _v: rt.put_var(fr, 'pWorld', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tCol', _v, 'into')), None]))):
                _v12 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',north'), '\n')
                rt.put_var(fr, 'tOut', _v12, 'after')
            if to_bool(rt.unop('not', rt.fn(fr, 'Map.IsOpen', [rt.getvar(fr, 'pWorld'), rt.getvar(fr, 'tCol'), rt.binop('+', rt.getvar(fr, 'tRowNo'), '1')], [('var', lambda _v: rt.put_var(fr, 'pWorld', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tCol', _v, 'into')), None]))):
                _v13 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',south'), '\n')
                rt.put_var(fr, 'tOut', _v13, 'after')
            if to_bool(rt.unop('not', rt.fn(fr, 'Map.IsOpen', [rt.getvar(fr, 'pWorld'), rt.binop('+', rt.getvar(fr, 'tCol'), '1'), rt.getvar(fr, 'tRowNo')], [('var', lambda _v: rt.put_var(fr, 'pWorld', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tRowNo', _v, 'into'))]))):
                _v14 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',east'), '\n')
                rt.put_var(fr, 'tOut', _v14, 'after')
            if to_bool(rt.unop('not', rt.fn(fr, 'Map.IsOpen', [rt.getvar(fr, 'pWorld'), rt.binop('-', rt.getvar(fr, 'tCol'), '1'), rt.getvar(fr, 'tRowNo')], [('var', lambda _v: rt.put_var(fr, 'pWorld', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tRowNo', _v, 'into'))]))):
                _v15 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',west'), '\n')
                rt.put_var(fr, 'tOut', _v15, 'after')
    _c16 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c16, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_map_blocks(rt, fr):
    # function Map.Blocks pGrid
    fr.vars['th'] = fr.vars.get('th', "")
    fr.vars['trowno'] = fr.vars.get('trowno', "")
    fr.vars['tcol'] = fr.vars.get('tcol', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['trow'] = fr.vars.get('trow', "")
    _v1 = str(ch.count(to_text(rt.getvar(fr, 'pGrid')), 'line', **rt.delims()))
    rt.put_var(fr, 'tH', _v1, 'into')
    _x2 = to_num(to_text('1'))
    _e3 = to_num(to_text(rt.getvar(fr, 'tH')))
    _s4 = 1
    while (_s4 > 0) and _x2 < _e3 + _s4:
        rt.setvar(fr, 'tRowNo', numstr(_x2))
        _x2 += _s4
        _v5 = rt.get_chunk('line', rt.getvar(fr, 'pGrid'), rt.getvar(fr, 'tRowNo'), None)
        rt.put_var(fr, 'tRow', _v5, 'into')
        _x6 = to_num(to_text('1'))
        _e7 = to_num(to_text(str(ch.count(to_text(rt.getvar(fr, 'tRow')), 'char', **rt.delims()))))
        _s8 = 1
        while (_s8 > 0) and _x6 < _e7 + _s8:
            rt.setvar(fr, 'tCol', numstr(_x6))
            _x6 += _s8
            if to_bool(rt.binop('=', rt.get_chunk('char', rt.getvar(fr, 'tRow'), rt.getvar(fr, 'tCol'), None), '0')):
                continue
            _v9 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',top'), '\n')
            rt.put_var(fr, 'tOut', _v9, 'after')
            if to_bool(rt.unop('not', rt.fn(fr, 'Map.IsFilled', [rt.getvar(fr, 'pGrid'), rt.getvar(fr, 'tCol'), rt.binop('-', rt.getvar(fr, 'tRowNo'), '1')], [('var', lambda _v: rt.put_var(fr, 'pGrid', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tCol', _v, 'into')), None]))):
                _v10 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',north'), '\n')
                rt.put_var(fr, 'tOut', _v10, 'after')
            if to_bool(rt.unop('not', rt.fn(fr, 'Map.IsFilled', [rt.getvar(fr, 'pGrid'), rt.getvar(fr, 'tCol'), rt.binop('+', rt.getvar(fr, 'tRowNo'), '1')], [('var', lambda _v: rt.put_var(fr, 'pGrid', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tCol', _v, 'into')), None]))):
                _v11 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',south'), '\n')
                rt.put_var(fr, 'tOut', _v11, 'after')
            if to_bool(rt.unop('not', rt.fn(fr, 'Map.IsFilled', [rt.getvar(fr, 'pGrid'), rt.binop('+', rt.getvar(fr, 'tCol'), '1'), rt.getvar(fr, 'tRowNo')], [('var', lambda _v: rt.put_var(fr, 'pGrid', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tRowNo', _v, 'into'))]))):
                _v12 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',east'), '\n')
                rt.put_var(fr, 'tOut', _v12, 'after')
            if to_bool(rt.unop('not', rt.fn(fr, 'Map.IsFilled', [rt.getvar(fr, 'pGrid'), rt.binop('-', rt.getvar(fr, 'tCol'), '1'), rt.getvar(fr, 'tRowNo')], [('var', lambda _v: rt.put_var(fr, 'pGrid', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tRowNo', _v, 'into'))]))):
                _v13 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo')), ',west'), '\n')
                rt.put_var(fr, 'tOut', _v13, 'after')
    if to_bool(rt.binop('<>', rt.getvar(fr, 'tOut'), '')):
        _c14 = to_text(rt.getvar(fr, 'tOut'))
        rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c14, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_map_blockedges(rt, fr):
    # function Map.BlockEdges pGrid, pCell, pHeight, pPanel
    fr.vars['tcols'] = fr.vars.get('tcols', "")
    fr.vars['trows'] = fr.vars.get('trows', "")
    fr.vars['tface'] = fr.vars.get('tface', "")
    fr.vars['tc'] = fr.vars.get('tc', "")
    fr.vars['tr'] = fr.vars.get('tr', "")
    fr.vars['tx0'] = fr.vars.get('tx0', "")
    fr.vars['tx1'] = fr.vars.get('tx1', "")
    fr.vars['ty0'] = fr.vars.get('ty0', "")
    fr.vars['ty1'] = fr.vars.get('ty1', "")
    fr.vars['th'] = fr.vars.get('th', "")
    fr.vars['tseen'] = fr.vars.get('tseen', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['ti'] = fr.vars.get('ti', "")
    fr.vars['tleft'] = fr.vars.get('tleft', "")
    fr.vars['ttop'] = fr.vars.get('ttop', "")
    if to_bool(rt.binop('=', rt.getvar(fr, 'pCell'), '')):
        rt.put_var(fr, 'pCell', '1', 'into')
    if to_bool(rt.binop('=', rt.getvar(fr, 'pHeight'), '')):
        _v1 = rt.getvar(fr, 'pCell')
        rt.put_var(fr, 'pHeight', _v1, 'into')
    _v2 = rt.getvar(fr, 'pHeight')
    rt.put_var(fr, 'tH', _v2, 'into')
    _v3 = str(ch.count(to_text(rt.get_chunk('line', rt.getvar(fr, 'pGrid'), '1', None)), 'char', **rt.delims()))
    rt.put_var(fr, 'tCols', _v3, 'into')
    _v4 = str(ch.count(to_text(rt.getvar(fr, 'pGrid')), 'line', **rt.delims()))
    rt.put_var(fr, 'tRows', _v4, 'into')
    _v5 = rt.binop('/', rt.binop('*', rt.unop('-', rt.getvar(fr, 'tCols')), rt.getvar(fr, 'pCell')), '2')
    rt.put_var(fr, 'tLeft', _v5, 'into')
    _v6 = rt.binop('/', rt.binop('*', rt.getvar(fr, 'tRows'), rt.getvar(fr, 'pCell')), '2')
    rt.put_var(fr, 'tTop', _v6, 'into')
    _t7 = to_text(rt.fn(fr, 'Map.Blocks', [rt.getvar(fr, 'pGrid')], [('var', lambda _v: rt.put_var(fr, 'pGrid', _v, 'into'))]))
    for _a8, _b9 in ch.spans(_t7, 'line', **rt.delims()):
        rt.setvar(fr, 'tFace', _t7[_a8:_b9])
        _v10 = rt.get_chunk('item', rt.getvar(fr, 'tFace'), '1', None)
        rt.put_var(fr, 'tC', _v10, 'into')
        _v11 = rt.get_chunk('item', rt.getvar(fr, 'tFace'), '2', None)
        rt.put_var(fr, 'tR', _v11, 'into')
        _v12 = rt.binop('+', rt.getvar(fr, 'tLeft'), rt.binop('*', rt.binop('-', rt.getvar(fr, 'tC'), '1'), rt.getvar(fr, 'pCell')))
        rt.put_var(fr, 'tX0', _v12, 'into')
        _v13 = rt.binop('+', rt.getvar(fr, 'tX0'), rt.getvar(fr, 'pCell'))
        rt.put_var(fr, 'tX1', _v13, 'into')
        _v14 = rt.binop('-', rt.getvar(fr, 'tTop'), rt.binop('*', rt.getvar(fr, 'tR'), rt.getvar(fr, 'pCell')))
        rt.put_var(fr, 'tY0', _v14, 'into')
        _v15 = rt.binop('+', rt.getvar(fr, 'tY0'), rt.getvar(fr, 'pCell'))
        rt.put_var(fr, 'tY1', _v15, 'into')
        _sv16 = to_text(rt.get_chunk('item', rt.getvar(fr, 'tFace'), '3', None))
        if rt.case_hit(_sv16, 'top'):
            rt.cmd(fr, 'map.addquad', [rt.getvar(fr, 'tSeen'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tY0'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tY0'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tY1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tY1'), rt.getvar(fr, 'tH')], [('var', lambda _v: rt.put_var(fr, 'tSeen', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into'))], [None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None])
        elif rt.case_hit(_sv16, 'north'):
            rt.cmd(fr, 'map.addquad', [rt.getvar(fr, 'tSeen'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tY1'), '0', rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tY1'), '0', rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tY1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tY1'), rt.getvar(fr, 'tH')], [('var', lambda _v: rt.put_var(fr, 'tSeen', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into'))], [None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None])
        elif rt.case_hit(_sv16, 'south'):
            rt.cmd(fr, 'map.addquad', [rt.getvar(fr, 'tSeen'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tY0'), '0', rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tY0'), '0', rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tY0'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tY0'), rt.getvar(fr, 'tH')], [('var', lambda _v: rt.put_var(fr, 'tSeen', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into'))], [None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None])
        elif rt.case_hit(_sv16, 'west'):
            rt.cmd(fr, 'map.addquad', [rt.getvar(fr, 'tSeen'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tY0'), '0', rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tY1'), '0', rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tY1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tY0'), rt.getvar(fr, 'tH')], [('var', lambda _v: rt.put_var(fr, 'tSeen', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into'))], [None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None])
        elif rt.case_hit(_sv16, 'east'):
            rt.cmd(fr, 'map.addquad', [rt.getvar(fr, 'tSeen'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tY0'), '0', rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tY1'), '0', rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tY1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tY0'), rt.getvar(fr, 'tH')], [('var', lambda _v: rt.put_var(fr, 'tSeen', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into'))], [None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None, ',', None])
    if to_bool(rt.binop('=', rt.getvar(fr, 'pPanel'), 'true')):
        _x17 = to_num(to_text('0'))
        _e18 = to_num(to_text(rt.getvar(fr, 'tCols')))
        _s19 = 1
        while (_s19 > 0) and _x17 < _e18 + _s19:
            rt.setvar(fr, 'tI', numstr(_x17))
            _x17 += _s19
            rt.cmd(fr, 'map.addedge', [rt.getvar(fr, 'tSeen'), rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('+', rt.getvar(fr, 'tLeft'), rt.binop('*', rt.getvar(fr, 'tI'), rt.getvar(fr, 'pCell'))), ','), rt.getvar(fr, 'tTop')), ',0'), rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('+', rt.getvar(fr, 'tLeft'), rt.binop('*', rt.getvar(fr, 'tI'), rt.getvar(fr, 'pCell'))), ','), rt.unop('-', rt.getvar(fr, 'tTop'))), ',0')], [('var', lambda _v: rt.put_var(fr, 'tSeen', _v, 'into')), None, None], [None, ',', None, ',', None])
        _x20 = to_num(to_text('0'))
        _e21 = to_num(to_text(rt.getvar(fr, 'tRows')))
        _s22 = 1
        while (_s22 > 0) and _x20 < _e21 + _s22:
            rt.setvar(fr, 'tI', numstr(_x20))
            _x20 += _s22
            rt.cmd(fr, 'map.addedge', [rt.getvar(fr, 'tSeen'), rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tLeft'), ','), rt.binop('-', rt.getvar(fr, 'tTop'), rt.binop('*', rt.getvar(fr, 'tI'), rt.getvar(fr, 'pCell')))), ',0'), rt.binop('&', rt.binop('&', rt.binop('&', rt.unop('-', rt.getvar(fr, 'tLeft')), ','), rt.binop('-', rt.getvar(fr, 'tTop'), rt.binop('*', rt.getvar(fr, 'tI'), rt.getvar(fr, 'pCell')))), ',0')], [('var', lambda _v: rt.put_var(fr, 'tSeen', _v, 'into')), None, None], [None, ',', None, ',', None])
    _v23 = B['keys'](rt, fr, rt.getvar(fr, 'tSeen'))
    rt.put_var(fr, 'tOut', _v23, 'into')
    _v24 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.sort_text(fr, 'line', _v24, False, 'text', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_map_addquad(rt, fr):
    # on Map.AddQuad pSeen, pAX, pAY, pAZ, pBX, pBY, pBZ, pCX, pCY, pCZ, pDX, pDY, pDZ
    rt.cmd(fr, 'map.addedge', [rt.getvar(fr, 'pSeen'), rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'pAX'), ','), rt.getvar(fr, 'pAY')), ','), rt.getvar(fr, 'pAZ')), rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'pBX'), ','), rt.getvar(fr, 'pBY')), ','), rt.getvar(fr, 'pBZ'))], [('var', lambda _v: rt.put_var(fr, 'pSeen', _v, 'into')), None, None], [None, ',', None, ',', None])
    rt.cmd(fr, 'map.addedge', [rt.getvar(fr, 'pSeen'), rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'pBX'), ','), rt.getvar(fr, 'pBY')), ','), rt.getvar(fr, 'pBZ')), rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'pCX'), ','), rt.getvar(fr, 'pCY')), ','), rt.getvar(fr, 'pCZ'))], [('var', lambda _v: rt.put_var(fr, 'pSeen', _v, 'into')), None, None], [None, ',', None, ',', None])
    rt.cmd(fr, 'map.addedge', [rt.getvar(fr, 'pSeen'), rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'pCX'), ','), rt.getvar(fr, 'pCY')), ','), rt.getvar(fr, 'pCZ')), rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'pDX'), ','), rt.getvar(fr, 'pDY')), ','), rt.getvar(fr, 'pDZ'))], [('var', lambda _v: rt.put_var(fr, 'pSeen', _v, 'into')), None, None], [None, ',', None, ',', None])
    rt.cmd(fr, 'map.addedge', [rt.getvar(fr, 'pSeen'), rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'pDX'), ','), rt.getvar(fr, 'pDY')), ','), rt.getvar(fr, 'pDZ')), rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'pAX'), ','), rt.getvar(fr, 'pAY')), ','), rt.getvar(fr, 'pAZ'))], [('var', lambda _v: rt.put_var(fr, 'pSeen', _v, 'into')), None, None], [None, ',', None, ',', None])
    return ''


def h_map_addedge(rt, fr):
    # on Map.AddEdge pSeen, pA, pB
    if to_bool(rt.binop('<', rt.getvar(fr, 'pA'), rt.getvar(fr, 'pB'))):
        rt.put_idx(fr, 'pSeen', rt.key_vals([rt.binop('&', rt.binop('&', rt.getvar(fr, 'pA'), ','), rt.getvar(fr, 'pB'))]), 'true', 'into')
    else:
        rt.put_idx(fr, 'pSeen', rt.key_vals([rt.binop('&', rt.binop('&', rt.getvar(fr, 'pB'), ','), rt.getvar(fr, 'pA'))]), 'true', 'into')
    return ''


def h_map_isfilled(rt, fr):
    # function Map.IsFilled pGrid, pCol, pRow
    fr.vars['tc'] = fr.vars.get('tc', "")
    if to_bool(('true' if (rt.truth(('true' if (rt.truth(rt.binop('<', rt.getvar(fr, 'pCol'), '1')) or rt.truth(rt.binop('<', rt.getvar(fr, 'pRow'), '1'))) else 'false')) or rt.truth(rt.binop('>', rt.getvar(fr, 'pRow'), str(ch.count(to_text(rt.getvar(fr, 'pGrid')), 'line', **rt.delims()))))) else 'false')):
        return 'false'
    _v1 = rt.get_chunk('char', rt.get_chunk('line', rt.getvar(fr, 'pGrid'), rt.getvar(fr, 'pRow'), None), rt.getvar(fr, 'pCol'), None)
    rt.put_var(fr, 'tC', _v1, 'into')
    return ('true' if (rt.truth(rt.binop('<>', rt.getvar(fr, 'tC'), '')) and rt.truth(rt.binop('<>', rt.getvar(fr, 'tC'), '0'))) else 'false')


def h_map_findpath(rt, fr):
    # function Map.FindPath pWorld, pFrom, pTo, pDiagonal
    fr.vars['tdirs'] = fr.vars.get('tdirs', "")
    fr.vars['tg'] = fr.vars.get('tg', "")
    fr.vars['tcame'] = fr.vars.get('tcame', "")
    fr.vars['tclosed'] = fr.vars.get('tclosed', "")
    fr.vars['tbucket'] = fr.vars.get('tbucket', "")
    fr.vars['tminf'] = fr.vars.get('tminf', "")
    fr.vars['tmaxf'] = fr.vars.get('tmaxf', "")
    fr.vars['tat'] = fr.vars.get('tat', "")
    fr.vars['tx'] = fr.vars.get('tx', "")
    fr.vars['ty'] = fr.vars.get('ty', "")
    fr.vars['tgx'] = fr.vars.get('tgx', "")
    fr.vars['tgy'] = fr.vars.get('tgy', "")
    fr.vars['td'] = fr.vars.get('td', "")
    fr.vars['tnx'] = fr.vars.get('tnx', "")
    fr.vars['tny'] = fr.vars.get('tny', "")
    fr.vars['tkey'] = fr.vars.get('tkey', "")
    fr.vars['tcost'] = fr.vars.get('tcost', "")
    fr.vars['tnewg'] = fr.vars.get('tnewg', "")
    fr.vars['tf'] = fr.vars.get('tf', "")
    fr.vars['tpath'] = fr.vars.get('tpath', "")
    fr.vars['tlimit'] = fr.vars.get('tlimit', "")
    fr.vars['tsteps'] = fr.vars.get('tsteps', "")
    if to_bool(rt.unop('not', rt.fn(fr, 'Map.IsOpen', [rt.getvar(fr, 'pWorld'), rt.get_chunk('item', rt.getvar(fr, 'pFrom'), '1', None), rt.get_chunk('item', rt.getvar(fr, 'pFrom'), '2', None)], [('var', lambda _v: rt.put_var(fr, 'pWorld', _v, 'into')), ('chunk', lambda _v: rt.put_var(fr, 'pFrom', rt.put_chunk('item', rt.cur_text(fr, 'pFrom'), '1', None, _v, 'into'), 'into')), ('chunk', lambda _v: rt.put_var(fr, 'pFrom', rt.put_chunk('item', rt.cur_text(fr, 'pFrom'), '2', None, _v, 'into'), 'into'))]))):
        return ''
    if to_bool(rt.unop('not', rt.fn(fr, 'Map.IsOpen', [rt.getvar(fr, 'pWorld'), rt.get_chunk('item', rt.getvar(fr, 'pTo'), '1', None), rt.get_chunk('item', rt.getvar(fr, 'pTo'), '2', None)], [('var', lambda _v: rt.put_var(fr, 'pWorld', _v, 'into')), ('chunk', lambda _v: rt.put_var(fr, 'pTo', rt.put_chunk('item', rt.cur_text(fr, 'pTo'), '1', None, _v, 'into'), 'into')), ('chunk', lambda _v: rt.put_var(fr, 'pTo', rt.put_chunk('item', rt.cur_text(fr, 'pTo'), '2', None, _v, 'into'), 'into'))]))):
        return ''
    _v1 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', '1,0,10', '\n'), '-1,0,10'), '\n'), '0,1,10'), '\n'), '0,-1,10')
    rt.put_var(fr, 'tDirs', _v1, 'into')
    if to_bool(rt.binop('=', rt.getvar(fr, 'pDiagonal'), 'true')):
        _v2 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', '\n', '1,1,14'), '\n'), '1,-1,14'), '\n'), '-1,1,14'), '\n'), '-1,-1,14')
        rt.put_var(fr, 'tDirs', _v2, 'after')
    _v3 = rt.get_chunk('item', rt.getvar(fr, 'pTo'), '1', None)
    rt.put_var(fr, 'tGX', _v3, 'into')
    _v4 = rt.get_chunk('item', rt.getvar(fr, 'pTo'), '2', None)
    rt.put_var(fr, 'tGY', _v4, 'into')
    rt.put_idx(fr, 'tG', rt.key_vals([rt.getvar(fr, 'pFrom')]), '0', 'into')
    _v5 = rt.fn(fr, 'Map.Guess', [rt.get_chunk('item', rt.getvar(fr, 'pFrom'), '1', None), rt.get_chunk('item', rt.getvar(fr, 'pFrom'), '2', None), rt.getvar(fr, 'tGX'), rt.getvar(fr, 'tGY'), rt.getvar(fr, 'pDiagonal')], [('chunk', lambda _v: rt.put_var(fr, 'pFrom', rt.put_chunk('item', rt.cur_text(fr, 'pFrom'), '1', None, _v, 'into'), 'into')), ('chunk', lambda _v: rt.put_var(fr, 'pFrom', rt.put_chunk('item', rt.cur_text(fr, 'pFrom'), '2', None, _v, 'into'), 'into')), ('var', lambda _v: rt.put_var(fr, 'tGX', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tGY', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'pDiagonal', _v, 'into'))])
    rt.put_var(fr, 'tMinF', _v5, 'into')
    _v6 = rt.getvar(fr, 'pFrom')
    rt.put_idx(fr, 'tBucket', rt.key_vals([rt.getvar(fr, 'tMinF')]), _v6, 'into')
    _v7 = rt.getvar(fr, 'tMinF')
    rt.put_var(fr, 'tMaxF', _v7, 'into')
    _v8 = rt.binop('*', rt.binop('*', '20', str(ch.count(to_text(rt.getvar(fr, 'pWorld')), 'line', **rt.delims()))), str(ch.count(to_text(rt.get_chunk('line', rt.getvar(fr, 'pWorld'), '1', None)), 'char', **rt.delims())))
    rt.put_var(fr, 'tLimit', _v8, 'into')
    rt.put_var(fr, 'tSteps', '0', 'into')
    while True:
        while to_bool(('true' if (rt.truth(rt.binop('=', rt.get_idx(fr, 'tBucket', rt.key_vals([rt.getvar(fr, 'tMinF')])), '')) and rt.truth(rt.binop('<=', rt.getvar(fr, 'tMinF'), rt.getvar(fr, 'tMaxF')))) else 'false')):
            _a9 = '1'
            _c10 = rt.cur_raw(fr, 'tMinF')
            rt.put_var(fr, 'tMinF', rt.arith('add', _a9, _c10), 'into')
        if to_bool(rt.binop('>', rt.getvar(fr, 'tMinF'), rt.getvar(fr, 'tMaxF'))):
            return ''
        _v11 = rt.get_chunk('line', rt.get_idx(fr, 'tBucket', rt.key_vals([rt.getvar(fr, 'tMinF')])), '1', None)
        rt.put_var(fr, 'tAt', _v11, 'into')
        _c12 = to_text(rt.get_idx(fr, 'tBucket', rt.key_vals([rt.getvar(fr, 'tMinF')])))
        rt.put_idx(fr, 'tBucket', rt.key_vals([rt.getvar(fr, 'tMinF')]), rt.cut_chunk('line', _c12, '1', None), 'into')
        if to_bool(rt.binop('=', rt.get_idx(fr, 'tClosed', rt.key_vals([rt.getvar(fr, 'tAt')])), 'true')):
            continue
        rt.put_idx(fr, 'tClosed', rt.key_vals([rt.getvar(fr, 'tAt')]), 'true', 'into')
        if to_bool(rt.binop('=', rt.getvar(fr, 'tAt'), rt.getvar(fr, 'pTo'))):
            break
        _a13 = '1'
        _c14 = rt.cur_raw(fr, 'tSteps')
        rt.put_var(fr, 'tSteps', rt.arith('add', _a13, _c14), 'into')
        if to_bool(rt.binop('>', rt.getvar(fr, 'tSteps'), rt.getvar(fr, 'tLimit'))):
            return ''
        _v15 = rt.get_chunk('item', rt.getvar(fr, 'tAt'), '1', None)
        rt.put_var(fr, 'tX', _v15, 'into')
        _v16 = rt.get_chunk('item', rt.getvar(fr, 'tAt'), '2', None)
        rt.put_var(fr, 'tY', _v16, 'into')
        _t17 = to_text(rt.getvar(fr, 'tDirs'))
        for _a18, _b19 in ch.spans(_t17, 'line', **rt.delims()):
            rt.setvar(fr, 'tD', _t17[_a18:_b19])
            _v20 = rt.binop('+', rt.getvar(fr, 'tX'), rt.get_chunk('item', rt.getvar(fr, 'tD'), '1', None))
            rt.put_var(fr, 'tNX', _v20, 'into')
            _v21 = rt.binop('+', rt.getvar(fr, 'tY'), rt.get_chunk('item', rt.getvar(fr, 'tD'), '2', None))
            rt.put_var(fr, 'tNY', _v21, 'into')
            if to_bool(rt.unop('not', rt.fn(fr, 'Map.IsOpen', [rt.getvar(fr, 'pWorld'), rt.getvar(fr, 'tNX'), rt.getvar(fr, 'tNY')], [('var', lambda _v: rt.put_var(fr, 'pWorld', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tNX', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tNY', _v, 'into'))]))):
                continue
            if to_bool(('true' if (rt.truth(rt.binop('<>', rt.get_chunk('item', rt.getvar(fr, 'tD'), '1', None), '0')) and rt.truth(rt.binop('<>', rt.get_chunk('item', rt.getvar(fr, 'tD'), '2', None), '0'))) else 'false')):
                if to_bool(('true' if (rt.truth(rt.unop('not', rt.fn(fr, 'Map.IsOpen', [rt.getvar(fr, 'pWorld'), rt.getvar(fr, 'tNX'), rt.getvar(fr, 'tY')], [('var', lambda _v: rt.put_var(fr, 'pWorld', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tNX', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tY', _v, 'into'))]))) or rt.truth(rt.unop('not', rt.fn(fr, 'Map.IsOpen', [rt.getvar(fr, 'pWorld'), rt.getvar(fr, 'tX'), rt.getvar(fr, 'tNY')], [('var', lambda _v: rt.put_var(fr, 'pWorld', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tNY', _v, 'into'))])))) else 'false')):
                    continue
            _v22 = rt.binop('&', rt.binop('&', rt.getvar(fr, 'tNX'), ','), rt.getvar(fr, 'tNY'))
            rt.put_var(fr, 'tKey', _v22, 'into')
            if to_bool(rt.binop('=', rt.get_idx(fr, 'tClosed', rt.key_vals([rt.getvar(fr, 'tKey')])), 'true')):
                continue
            _v23 = rt.binop('+', rt.get_idx(fr, 'tG', rt.key_vals([rt.getvar(fr, 'tAt')])), rt.get_chunk('item', rt.getvar(fr, 'tD'), '3', None))
            rt.put_var(fr, 'tNewG', _v23, 'into')
            if to_bool(('true' if (rt.truth(rt.binop('=', rt.get_idx(fr, 'tG', rt.key_vals([rt.getvar(fr, 'tKey')])), '')) or rt.truth(rt.binop('<', rt.getvar(fr, 'tNewG'), rt.get_idx(fr, 'tG', rt.key_vals([rt.getvar(fr, 'tKey')]))))) else 'false')):
                _v24 = rt.getvar(fr, 'tNewG')
                rt.put_idx(fr, 'tG', rt.key_vals([rt.getvar(fr, 'tKey')]), _v24, 'into')
                _v25 = rt.getvar(fr, 'tAt')
                rt.put_idx(fr, 'tCame', rt.key_vals([rt.getvar(fr, 'tKey')]), _v25, 'into')
                _v26 = rt.binop('+', rt.getvar(fr, 'tNewG'), rt.fn(fr, 'Map.Guess', [rt.getvar(fr, 'tNX'), rt.getvar(fr, 'tNY'), rt.getvar(fr, 'tGX'), rt.getvar(fr, 'tGY'), rt.getvar(fr, 'pDiagonal')], [('var', lambda _v: rt.put_var(fr, 'tNX', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tNY', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tGX', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tGY', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'pDiagonal', _v, 'into'))]))
                rt.put_var(fr, 'tF', _v26, 'into')
                if to_bool(rt.binop('=', rt.get_idx(fr, 'tBucket', rt.key_vals([rt.getvar(fr, 'tF')])), '')):
                    _v27 = rt.getvar(fr, 'tKey')
                    rt.put_idx(fr, 'tBucket', rt.key_vals([rt.getvar(fr, 'tF')]), _v27, 'into')
                else:
                    _v28 = rt.binop('&', '\n', rt.getvar(fr, 'tKey'))
                    rt.put_idx(fr, 'tBucket', rt.key_vals([rt.getvar(fr, 'tF')]), _v28, 'after')
                if to_bool(rt.binop('>', rt.getvar(fr, 'tF'), rt.getvar(fr, 'tMaxF'))):
                    _v29 = rt.getvar(fr, 'tF')
                    rt.put_var(fr, 'tMaxF', _v29, 'into')
                if to_bool(rt.binop('<', rt.getvar(fr, 'tF'), rt.getvar(fr, 'tMinF'))):
                    _v30 = rt.getvar(fr, 'tF')
                    rt.put_var(fr, 'tMinF', _v30, 'into')
    _v31 = rt.getvar(fr, 'pTo')
    rt.put_var(fr, 'tAt', _v31, 'into')
    _v32 = rt.getvar(fr, 'tAt')
    rt.put_var(fr, 'tPath', _v32, 'into')
    while to_bool(rt.binop('<>', rt.getvar(fr, 'tAt'), rt.getvar(fr, 'pFrom'))):
        _v33 = rt.get_idx(fr, 'tCame', rt.key_vals([rt.getvar(fr, 'tAt')]))
        rt.put_var(fr, 'tAt', _v33, 'into')
        _v34 = rt.binop('&', rt.getvar(fr, 'tAt'), '\n')
        rt.put_var(fr, 'tPath', _v34, 'before')
    return rt.getvar(fr, 'tPath')


def h_map_guess(rt, fr):
    # function Map.Guess pX, pY, pGX, pGY, pDiagonal
    fr.vars['tdx'] = fr.vars.get('tdx', "")
    fr.vars['tdy'] = fr.vars.get('tdy', "")
    _v1 = rt.fn(fr, 'abs', [rt.binop('-', rt.getvar(fr, 'pX'), rt.getvar(fr, 'pGX'))], [None])
    rt.put_var(fr, 'tDX', _v1, 'into')
    _v2 = rt.fn(fr, 'abs', [rt.binop('-', rt.getvar(fr, 'pY'), rt.getvar(fr, 'pGY'))], [None])
    rt.put_var(fr, 'tDY', _v2, 'into')
    if to_bool(rt.binop('=', rt.getvar(fr, 'pDiagonal'), 'true')):
        return rt.binop('+', rt.binop('*', '10', rt.fn(fr, 'max', [rt.getvar(fr, 'tDX'), rt.getvar(fr, 'tDY')], [('var', lambda _v: rt.put_var(fr, 'tDX', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tDY', _v, 'into'))])), rt.binop('*', '4', rt.fn(fr, 'min', [rt.getvar(fr, 'tDX'), rt.getvar(fr, 'tDY')], [('var', lambda _v: rt.put_var(fr, 'tDX', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tDY', _v, 'into'))])))
    return rt.binop('*', '10', rt.binop('+', rt.getvar(fr, 'tDX'), rt.getvar(fr, 'tDY')))


def h_map_regions(rt, fr):
    # function Map.Regions pWorld
    fr.vars['th'] = fr.vars.get('th', "")
    fr.vars['tw'] = fr.vars.get('tw', "")
    fr.vars['tused'] = fr.vars.get('tused', "")
    fr.vars['trowno'] = fr.vars.get('trowno', "")
    fr.vars['tcol'] = fr.vars.get('tcol', "")
    fr.vars['tright'] = fr.vars.get('tright', "")
    fr.vars['tbottom'] = fr.vars.get('tbottom', "")
    fr.vars['tok'] = fr.vars.get('tok', "")
    fr.vars['tc'] = fr.vars.get('tc', "")
    fr.vars['tid'] = fr.vars.get('tid', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['tr'] = fr.vars.get('tr', "")
    _v1 = str(ch.count(to_text(rt.getvar(fr, 'pWorld')), 'line', **rt.delims()))
    rt.put_var(fr, 'tH', _v1, 'into')
    _v2 = str(ch.count(to_text(rt.get_chunk('line', rt.getvar(fr, 'pWorld'), '1', None)), 'char', **rt.delims()))
    rt.put_var(fr, 'tW', _v2, 'into')
    rt.put_var(fr, 'tId', '0', 'into')
    _x3 = to_num(to_text('1'))
    _e4 = to_num(to_text(rt.getvar(fr, 'tH')))
    _s5 = 1
    while (_s5 > 0) and _x3 < _e4 + _s5:
        rt.setvar(fr, 'tRowNo', numstr(_x3))
        _x3 += _s5
        _x6 = to_num(to_text('1'))
        _e7 = to_num(to_text(rt.getvar(fr, 'tW')))
        _s8 = 1
        while (_s8 > 0) and _x6 < _e7 + _s8:
            rt.setvar(fr, 'tCol', numstr(_x6))
            _x6 += _s8
            if to_bool(('true' if (rt.truth(rt.binop('<>', rt.get_chunk('char', rt.get_chunk('line', rt.getvar(fr, 'pWorld'), rt.getvar(fr, 'tRowNo'), None), rt.getvar(fr, 'tCol'), None), '0')) or rt.truth(rt.binop('=', rt.get_idx(fr, 'tUsed', rt.key_vals([rt.getvar(fr, 'tCol'), ',', rt.getvar(fr, 'tRowNo')])), 'true'))) else 'false')):
                continue
            _v9 = rt.getvar(fr, 'tCol')
            rt.put_var(fr, 'tRight', _v9, 'into')
            while to_bool(rt.binop('<', rt.getvar(fr, 'tRight'), rt.getvar(fr, 'tW'))):
                if to_bool(('true' if (rt.truth(rt.binop('<>', rt.get_chunk('char', rt.get_chunk('line', rt.getvar(fr, 'pWorld'), rt.getvar(fr, 'tRowNo'), None), rt.binop('+', rt.getvar(fr, 'tRight'), '1'), None), '0')) or rt.truth(rt.binop('=', rt.get_idx(fr, 'tUsed', rt.key_vals([rt.binop('+', rt.getvar(fr, 'tRight'), '1'), ',', rt.getvar(fr, 'tRowNo')])), 'true'))) else 'false')):
                    break
                _a10 = '1'
                _c11 = rt.cur_raw(fr, 'tRight')
                rt.put_var(fr, 'tRight', rt.arith('add', _a10, _c11), 'into')
            _v12 = rt.getvar(fr, 'tRowNo')
            rt.put_var(fr, 'tBottom', _v12, 'into')
            while to_bool(rt.binop('<', rt.getvar(fr, 'tBottom'), rt.getvar(fr, 'tH'))):
                rt.put_var(fr, 'tOK', 'true', 'into')
                _x13 = to_num(to_text(rt.getvar(fr, 'tCol')))
                _e14 = to_num(to_text(rt.getvar(fr, 'tRight')))
                _s15 = 1
                while (_s15 > 0) and _x13 < _e14 + _s15:
                    rt.setvar(fr, 'tC', numstr(_x13))
                    _x13 += _s15
                    if to_bool(('true' if (rt.truth(rt.binop('<>', rt.get_chunk('char', rt.get_chunk('line', rt.getvar(fr, 'pWorld'), rt.binop('+', rt.getvar(fr, 'tBottom'), '1'), None), rt.getvar(fr, 'tC'), None), '0')) or rt.truth(rt.binop('=', rt.get_idx(fr, 'tUsed', rt.key_vals([rt.getvar(fr, 'tC'), ',', rt.binop('+', rt.getvar(fr, 'tBottom'), '1')])), 'true'))) else 'false')):
                        rt.put_var(fr, 'tOK', 'false', 'into')
                        break
                if to_bool(rt.unop('not', rt.getvar(fr, 'tOK'))):
                    break
                _a16 = '1'
                _c17 = rt.cur_raw(fr, 'tBottom')
                rt.put_var(fr, 'tBottom', rt.arith('add', _a16, _c17), 'into')
            _a18 = '1'
            _c19 = rt.cur_raw(fr, 'tId')
            rt.put_var(fr, 'tId', rt.arith('add', _a18, _c19), 'into')
            _x20 = to_num(to_text(rt.getvar(fr, 'tRowNo')))
            _e21 = to_num(to_text(rt.getvar(fr, 'tBottom')))
            _s22 = 1
            while (_s22 > 0) and _x20 < _e21 + _s22:
                rt.setvar(fr, 'tR', numstr(_x20))
                _x20 += _s22
                _x23 = to_num(to_text(rt.getvar(fr, 'tCol')))
                _e24 = to_num(to_text(rt.getvar(fr, 'tRight')))
                _s25 = 1
                while (_s25 > 0) and _x23 < _e24 + _s25:
                    rt.setvar(fr, 'tC', numstr(_x23))
                    _x23 += _s25
                    rt.put_idx(fr, 'tUsed', rt.key_vals([rt.getvar(fr, 'tC'), ',', rt.getvar(fr, 'tR')]), 'true', 'into')
            _v26 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'tId'), ','), rt.getvar(fr, 'tCol')), ','), rt.getvar(fr, 'tRowNo')), ','), rt.getvar(fr, 'tRight')), ','), rt.getvar(fr, 'tBottom')), '\n')
            rt.put_var(fr, 'tOut', _v26, 'after')
    _c27 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c27, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_map_regionlinks(rt, fr):
    # function Map.RegionLinks pWorld, pRegions
    fr.vars['towner'] = fr.vars.get('towner', "")
    fr.vars['tline'] = fr.vars.get('tline', "")
    fr.vars['tc'] = fr.vars.get('tc', "")
    fr.vars['tr'] = fr.vars.get('tr', "")
    fr.vars['tseen'] = fr.vars.get('tseen', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['ta'] = fr.vars.get('ta', "")
    fr.vars['tb'] = fr.vars.get('tb', "")
    fr.vars['tpair'] = fr.vars.get('tpair', "")
    _t1 = to_text(rt.getvar(fr, 'pRegions'))
    for _a2, _b3 in ch.spans(_t1, 'line', **rt.delims()):
        rt.setvar(fr, 'tLine', _t1[_a2:_b3])
        _x4 = to_num(to_text(rt.get_chunk('item', rt.getvar(fr, 'tLine'), '3', None)))
        _e5 = to_num(to_text(rt.get_chunk('item', rt.getvar(fr, 'tLine'), '5', None)))
        _s6 = 1
        while (_s6 > 0) and _x4 < _e5 + _s6:
            rt.setvar(fr, 'tR', numstr(_x4))
            _x4 += _s6
            _x7 = to_num(to_text(rt.get_chunk('item', rt.getvar(fr, 'tLine'), '2', None)))
            _e8 = to_num(to_text(rt.get_chunk('item', rt.getvar(fr, 'tLine'), '4', None)))
            _s9 = 1
            while (_s9 > 0) and _x7 < _e8 + _s9:
                rt.setvar(fr, 'tC', numstr(_x7))
                _x7 += _s9
                _v10 = rt.get_chunk('item', rt.getvar(fr, 'tLine'), '1', None)
                rt.put_idx(fr, 'tOwner', rt.key_vals([rt.getvar(fr, 'tC'), ',', rt.getvar(fr, 'tR')]), _v10, 'into')
    _t11 = to_text(rt.getvar(fr, 'pRegions'))
    for _a12, _b13 in ch.spans(_t11, 'line', **rt.delims()):
        rt.setvar(fr, 'tLine', _t11[_a12:_b13])
        _v14 = rt.get_chunk('item', rt.getvar(fr, 'tLine'), '1', None)
        rt.put_var(fr, 'tA', _v14, 'into')
        _x15 = to_num(to_text(rt.get_chunk('item', rt.getvar(fr, 'tLine'), '3', None)))
        _e16 = to_num(to_text(rt.get_chunk('item', rt.getvar(fr, 'tLine'), '5', None)))
        _s17 = 1
        while (_s17 > 0) and _x15 < _e16 + _s17:
            rt.setvar(fr, 'tR', numstr(_x15))
            _x15 += _s17
            _x18 = to_num(to_text(rt.get_chunk('item', rt.getvar(fr, 'tLine'), '2', None)))
            _e19 = to_num(to_text(rt.get_chunk('item', rt.getvar(fr, 'tLine'), '4', None)))
            _s20 = 1
            while (_s20 > 0) and _x18 < _e19 + _s20:
                rt.setvar(fr, 'tC', numstr(_x18))
                _x18 += _s20
                _v21 = rt.get_idx(fr, 'tOwner', rt.key_vals([rt.binop('+', rt.getvar(fr, 'tC'), '1'), ',', rt.getvar(fr, 'tR')]))
                rt.put_var(fr, 'tB', _v21, 'into')
                if to_bool(('true' if (rt.truth(rt.binop('<>', rt.getvar(fr, 'tB'), '')) and rt.truth(rt.binop('<>', rt.getvar(fr, 'tB'), rt.getvar(fr, 'tA')))) else 'false')):
                    _v22 = rt.binop('&', rt.binop('&', rt.fn(fr, 'min', [rt.getvar(fr, 'tA'), rt.getvar(fr, 'tB')], [('var', lambda _v: rt.put_var(fr, 'tA', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tB', _v, 'into'))]), ','), rt.fn(fr, 'max', [rt.getvar(fr, 'tA'), rt.getvar(fr, 'tB')], [('var', lambda _v: rt.put_var(fr, 'tA', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tB', _v, 'into'))]))
                    rt.put_idx(fr, 'tSeen', rt.key_vals([rt.binop('&', rt.binop('&', rt.fn(fr, 'min', [rt.getvar(fr, 'tA'), rt.getvar(fr, 'tB')], [('var', lambda _v: rt.put_var(fr, 'tA', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tB', _v, 'into'))]), ','), rt.fn(fr, 'max', [rt.getvar(fr, 'tA'), rt.getvar(fr, 'tB')], [('var', lambda _v: rt.put_var(fr, 'tA', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tB', _v, 'into'))]))]), _v22, 'into')
                _v23 = rt.get_idx(fr, 'tOwner', rt.key_vals([rt.getvar(fr, 'tC'), ',', rt.binop('+', rt.getvar(fr, 'tR'), '1')]))
                rt.put_var(fr, 'tB', _v23, 'into')
                if to_bool(('true' if (rt.truth(rt.binop('<>', rt.getvar(fr, 'tB'), '')) and rt.truth(rt.binop('<>', rt.getvar(fr, 'tB'), rt.getvar(fr, 'tA')))) else 'false')):
                    _v24 = rt.binop('&', rt.binop('&', rt.fn(fr, 'min', [rt.getvar(fr, 'tA'), rt.getvar(fr, 'tB')], [('var', lambda _v: rt.put_var(fr, 'tA', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tB', _v, 'into'))]), ','), rt.fn(fr, 'max', [rt.getvar(fr, 'tA'), rt.getvar(fr, 'tB')], [('var', lambda _v: rt.put_var(fr, 'tA', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tB', _v, 'into'))]))
                    rt.put_idx(fr, 'tSeen', rt.key_vals([rt.binop('&', rt.binop('&', rt.fn(fr, 'min', [rt.getvar(fr, 'tA'), rt.getvar(fr, 'tB')], [('var', lambda _v: rt.put_var(fr, 'tA', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tB', _v, 'into'))]), ','), rt.fn(fr, 'max', [rt.getvar(fr, 'tA'), rt.getvar(fr, 'tB')], [('var', lambda _v: rt.put_var(fr, 'tA', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tB', _v, 'into'))]))]), _v24, 'into')
    _v25 = B['keys'](rt, fr, rt.getvar(fr, 'tSeen'))
    rt.put_var(fr, 'tOut', _v25, 'into')
    _v26 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.sort_text(fr, 'line', _v26, False, 'numeric', lambda: rt.get_chunk('item', rt.getvar(fr, 'each'), '2', None)), 'into')
    _v27 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.sort_text(fr, 'line', _v27, False, 'numeric', lambda: rt.get_chunk('item', rt.getvar(fr, 'each'), '1', None)), 'into')
    return rt.getvar(fr, 'tOut')


def h_map_meshtext(rt, fr):
    # function Map.MeshText pWorld, pCell, pHeight, pRoof
    fr.vars['tpiece'] = fr.vars.get('tpiece', "")
    fr.vars['tx0'] = fr.vars.get('tx0', "")
    fr.vars['tx1'] = fr.vars.get('tx1', "")
    fr.vars['tz0'] = fr.vars.get('tz0', "")
    fr.vars['tz1'] = fr.vars.get('tz1', "")
    fr.vars['th'] = fr.vars.get('th', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    fr.vars['tcount'] = fr.vars.get('tcount', "")
    fr.vars['tresult'] = fr.vars.get('tresult', "")
    if to_bool(rt.binop('=', rt.getvar(fr, 'pCell'), '')):
        rt.put_var(fr, 'pCell', '1', 'into')
    if to_bool(rt.binop('=', rt.getvar(fr, 'pHeight'), '')):
        _v1 = rt.getvar(fr, 'pCell')
        rt.put_var(fr, 'pHeight', _v1, 'into')
    _v2 = rt.getvar(fr, 'pHeight')
    rt.put_var(fr, 'tH', _v2, 'into')
    rt.put_var(fr, 'tCount', '0', 'into')
    _t3 = to_text(rt.fn(fr, 'Map.Pieces', [rt.getvar(fr, 'pWorld')], [('var', lambda _v: rt.put_var(fr, 'pWorld', _v, 'into'))]))
    for _a4, _b5 in ch.spans(_t3, 'line', **rt.delims()):
        rt.setvar(fr, 'tPiece', _t3[_a4:_b5])
        _v6 = rt.binop('*', rt.binop('-', rt.get_chunk('item', rt.getvar(fr, 'tPiece'), '1', None), '1'), rt.getvar(fr, 'pCell'))
        rt.put_var(fr, 'tX0', _v6, 'into')
        _v7 = rt.binop('+', rt.getvar(fr, 'tX0'), rt.getvar(fr, 'pCell'))
        rt.put_var(fr, 'tX1', _v7, 'into')
        _v8 = rt.binop('*', rt.binop('-', rt.get_chunk('item', rt.getvar(fr, 'tPiece'), '2', None), '1'), rt.getvar(fr, 'pCell'))
        rt.put_var(fr, 'tZ0', _v8, 'into')
        _v9 = rt.binop('+', rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'pCell'))
        rt.put_var(fr, 'tZ1', _v9, 'into')
        _sv10 = to_text(rt.get_chunk('item', rt.getvar(fr, 'tPiece'), '3', None))
        if rt.case_hit(_sv10, 'floor'):
            _v11 = rt.binop('&', rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX0'), '0', rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX1'), '0', rt.getvar(fr, 'tZ1'), rt.getvar(fr, 'tX1'), '0', rt.getvar(fr, 'tZ0')], [('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into'))]), rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX0'), '0', rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX0'), '0', rt.getvar(fr, 'tZ1'), rt.getvar(fr, 'tX1'), '0', rt.getvar(fr, 'tZ1')], [('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into'))]))
            rt.put_var(fr, 'tOut', _v11, 'after')
        elif rt.case_hit(_sv10, 'roof'):
            if to_bool(rt.binop('<>', rt.getvar(fr, 'pRoof'), 'true')):
                continue
            _v12 = rt.binop('&', rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ1')], [('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into'))]), rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ1'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ1')], [('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into'))]))
            rt.put_var(fr, 'tOut', _v12, 'after')
        elif rt.case_hit(_sv10, 'north'):
            _v13 = rt.binop('&', rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX0'), '0', rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX1'), '0', rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ0')], [('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into'))]), rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX0'), '0', rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ0')], [('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into'))]))
            rt.put_var(fr, 'tOut', _v13, 'after')
        elif rt.case_hit(_sv10, 'south'):
            _v14 = rt.binop('&', rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX0'), '0', rt.getvar(fr, 'tZ1'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ1'), rt.getvar(fr, 'tX1'), '0', rt.getvar(fr, 'tZ1')], [('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into'))]), rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX0'), '0', rt.getvar(fr, 'tZ1'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ1'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ1')], [('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into'))]))
            rt.put_var(fr, 'tOut', _v14, 'after')
        elif rt.case_hit(_sv10, 'west'):
            _v15 = rt.binop('&', rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX0'), '0', rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ1'), rt.getvar(fr, 'tX0'), '0', rt.getvar(fr, 'tZ1')], [('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into'))]), rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX0'), '0', rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX0'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ1')], [('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into'))]))
            rt.put_var(fr, 'tOut', _v15, 'after')
        elif rt.case_hit(_sv10, 'east'):
            _v16 = rt.binop('&', rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX1'), '0', rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX1'), '0', rt.getvar(fr, 'tZ1'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ1')], [('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into'))]), rt.fn(fr, 'Map.Tri', [rt.getvar(fr, 'tX1'), '0', rt.getvar(fr, 'tZ0'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ1'), rt.getvar(fr, 'tX1'), rt.getvar(fr, 'tH'), rt.getvar(fr, 'tZ0')], [('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), None, ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tX1', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tH', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tZ0', _v, 'into'))]))
            rt.put_var(fr, 'tOut', _v16, 'after')
        _a17 = '2'
        _c18 = rt.cur_raw(fr, 'tCount')
        rt.put_var(fr, 'tCount', rt.arith('add', _a17, _c18), 'into')
    if to_bool(rt.binop('<>', rt.getvar(fr, 'pRoof'), 'true')):
        _v19 = rt.binop('div', str(ch.count(to_text(rt.getvar(fr, 'tOut')), 'line', **rt.delims())), '3')
        rt.put_var(fr, 'tCount', _v19, 'into')
    if to_bool(rt.binop('<>', rt.getvar(fr, 'tOut'), '')):
        _c20 = to_text(rt.getvar(fr, 'tOut'))
        rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c20, '-1', None), 'into')
    _v21 = rt.getvar(fr, 'tOut')
    rt.put_idx(fr, 'tResult', rt.key_vals(['vertices']), _v21, 'into')
    _v22 = rt.getvar(fr, 'tCount')
    rt.put_idx(fr, 'tResult', rt.key_vals(['triangles']), _v22, 'into')
    return rt.getvar(fr, 'tResult')


def h_map_tri(rt, fr):
    # function Map.Tri pAX, pAY, pAZ, pBX, pBY, pBZ, pCX, pCY, pCZ
    return rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('&', rt.getvar(fr, 'pAX'), ','), rt.getvar(fr, 'pAY')), ','), rt.getvar(fr, 'pAZ')), '\n'), rt.getvar(fr, 'pBX')), ','), rt.getvar(fr, 'pBY')), ','), rt.getvar(fr, 'pBZ')), '\n'), rt.getvar(fr, 'pCX')), ','), rt.getvar(fr, 'pCY')), ','), rt.getvar(fr, 'pCZ')), '\n')


def install(rt):
    """add these handlers to rt, then run the script-level local/global/constant lines"""
    fr = Frame([])
    rt.handlers['map.stitch'] = ('function', 'Map.Stitch', ['pSections', 'pLayout'], None, [], h_map_stitch)
    rt.handlers['map.seams'] = ('function', 'Map.Seams', ['pSections', 'pLayout'], None, [], h_map_seams)
    rt.handlers['map.column'] = ('function', 'Map.Column', ['pGrid', 'pCol'], None, [], h_map_column)
    rt.handlers['map.seamcompare'] = ('function', 'Map.SeamCompare', ['pEdgeA', 'pEdgeB'], None, [], h_map_seamcompare)
    rt.handlers['map.isopen'] = ('function', 'Map.IsOpen', ['pWorld', 'pCol', 'pRow'], None, [], h_map_isopen)
    rt.handlers['map.pieces'] = ('function', 'Map.Pieces', ['pWorld'], None, [], h_map_pieces)
    rt.handlers['map.blocks'] = ('function', 'Map.Blocks', ['pGrid'], None, [], h_map_blocks)
    rt.handlers['map.blockedges'] = ('function', 'Map.BlockEdges', ['pGrid', 'pCell', 'pHeight', 'pPanel'], None, [], h_map_blockedges)
    rt.handlers['map.addquad'] = ('command', 'Map.AddQuad', ['pSeen', 'pAX', 'pAY', 'pAZ', 'pBX', 'pBY', 'pBZ', 'pCX', 'pCY', 'pCZ', 'pDX', 'pDY', 'pDZ'], None, [0], h_map_addquad)
    rt.handlers['map.addedge'] = ('command', 'Map.AddEdge', ['pSeen', 'pA', 'pB'], None, [0], h_map_addedge)
    rt.handlers['map.isfilled'] = ('function', 'Map.IsFilled', ['pGrid', 'pCol', 'pRow'], None, [], h_map_isfilled)
    rt.handlers['map.findpath'] = ('function', 'Map.FindPath', ['pWorld', 'pFrom', 'pTo', 'pDiagonal'], None, [], h_map_findpath)
    rt.handlers['map.guess'] = ('function', 'Map.Guess', ['pX', 'pY', 'pGX', 'pGY', 'pDiagonal'], None, [], h_map_guess)
    rt.handlers['map.regions'] = ('function', 'Map.Regions', ['pWorld'], None, [], h_map_regions)
    rt.handlers['map.regionlinks'] = ('function', 'Map.RegionLinks', ['pWorld', 'pRegions'], None, [], h_map_regionlinks)
    rt.handlers['map.meshtext'] = ('function', 'Map.MeshText', ['pWorld', 'pCell', 'pHeight', 'pRoof'], None, [], h_map_meshtext)
    rt.handlers['map.tri'] = ('function', 'Map.Tri', ['pAX', 'pAY', 'pAZ', 'pBX', 'pBY', 'pBZ', 'pCX', 'pCY', 'pCZ'], None, [], h_map_tri)
