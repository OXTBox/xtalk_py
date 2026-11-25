"""Generated from corpus/libraries/lib_trace.livecodescript by xtalk_py/xtalk/transpile.py. Do not edit: the xTalk script is the source."""
from xtalk.pyrt import *  # noqa: F401,F403


def h_trace_contours(rt, fr):
    # function Trace.Contours pGrid
    fr.vars['tcell'] = fr.vars.get('tcell', "")
    fr.vars['tw'] = fr.vars.get('tw', "")
    fr.vars['th'] = fr.vars.get('th', "")
    fr.vars['tsweep'] = fr.vars.get('tsweep', "")
    fr.vars['tfound'] = fr.vars.get('tfound', "")
    fr.vars['tpoints'] = fr.vars.get('tpoints', "")
    fr.vars['trowno'] = fr.vars.get('trowno', "")
    fr.vars['tcol'] = fr.vars.get('tcol', "")
    fr.vars['trow'] = fr.vars.get('trow', "")
    fr.vars['tlast'] = fr.vars.get('tlast', "")
    fr.vars['tvalue'] = fr.vars.get('tvalue', "")
    fr.vars['tstart'] = fr.vars.get('tstart', "")
    fr.vars['tfirst'] = fr.vars.get('tfirst', "")
    fr.vars['tsecond'] = fr.vars.get('tsecond', "")
    fr.vars['tat'] = fr.vars.get('tat', "")
    fr.vars['tnext'] = fr.vars.get('tnext', "")
    fr.vars['tangle'] = fr.vars.get('tangle', "")
    fr.vars['tsteps'] = fr.vars.get('tsteps', "")
    fr.vars['tlimit'] = fr.vars.get('tlimit', "")
    _v1 = rt.fn(fr, 'Trace.SweepTable', [], [])
    rt.put_var(fr, 'tSweep', _v1, 'into')
    _v2 = str(ch.count(to_text(rt.getvar(fr, 'pGrid')), 'line', **rt.delims()))
    rt.put_var(fr, 'tH', _v2, 'into')
    _v3 = str(ch.count(to_text(rt.get_chunk('line', rt.getvar(fr, 'pGrid'), '1', None)), 'char', **rt.delims()))
    rt.put_var(fr, 'tW', _v3, 'into')
    _v4 = rt.binop('+', rt.binop('*', rt.binop('*', '4', rt.getvar(fr, 'tW')), rt.getvar(fr, 'tH')), '8')
    rt.put_var(fr, 'tLimit', _v4, 'into')
    _x5 = to_num(to_text('1'))
    _e6 = to_num(to_text(rt.getvar(fr, 'tH')))
    _s7 = 1
    while (_s7 > 0) and _x5 < _e6 + _s7:
        rt.setvar(fr, 'tRowNo', numstr(_x5))
        _x5 += _s7
        _v8 = rt.get_chunk('line', rt.getvar(fr, 'pGrid'), rt.getvar(fr, 'tRowNo'), None)
        rt.put_var(fr, 'tRow', _v8, 'into')
        _x9 = to_num(to_text('1'))
        _e10 = to_num(to_text(rt.getvar(fr, 'tW')))
        _s11 = 1
        while (_s11 > 0) and _x9 < _e10 + _s11:
            rt.setvar(fr, 'tCol', numstr(_x9))
            _x9 += _s11
            if to_bool(('true' if (rt.truth(rt.binop('<>', rt.get_chunk('char', rt.getvar(fr, 'tRow'), rt.getvar(fr, 'tCol'), None), '0')) and rt.truth(rt.binop('<>', rt.get_chunk('char', rt.getvar(fr, 'tRow'), rt.getvar(fr, 'tCol'), None), ''))) else 'false')):
                rt.put_idx(fr, 'tCell', rt.key_vals([rt.getvar(fr, 'tRowNo'), rt.getvar(fr, 'tCol')]), '1', 'into')
    _x12 = to_num(to_text('1'))
    _e13 = to_num(to_text(rt.getvar(fr, 'tH')))
    _s14 = 1
    while (_s14 > 0) and _x12 < _e13 + _s14:
        rt.setvar(fr, 'tRowNo', numstr(_x12))
        _x12 += _s14
        rt.put_var(fr, 'tLast', 'false', 'into')
        _x15 = to_num(to_text('1'))
        _e16 = to_num(to_text(rt.getvar(fr, 'tW')))
        _s17 = 1
        while (_s17 > 0) and _x15 < _e16 + _s17:
            rt.setvar(fr, 'tCol', numstr(_x15))
            _x15 += _s17
            _v18 = rt.binop('=', rt.get_idx(fr, 'tCell', rt.key_vals([rt.getvar(fr, 'tRowNo'), rt.getvar(fr, 'tCol')])), '1')
            rt.put_var(fr, 'tValue', _v18, 'into')
            if to_bool(('true' if (rt.truth(rt.unop('not', rt.getvar(fr, 'tValue'))) or rt.truth(rt.getvar(fr, 'tLast'))) else 'false')):
                _v19 = rt.getvar(fr, 'tValue')
                rt.put_var(fr, 'tLast', _v19, 'into')
                continue
            _v20 = rt.getvar(fr, 'tValue')
            rt.put_var(fr, 'tLast', _v20, 'into')
            _v21 = rt.binop('&', rt.binop('&', rt.getvar(fr, 'tCol'), ','), rt.getvar(fr, 'tRowNo'))
            rt.put_var(fr, 'tStart', _v21, 'into')
            if to_bool(rt.binop('=', rt.get_idx(fr, 'tFound', rt.key_vals([rt.getvar(fr, 'tStart')])), 'true')):
                continue
            _v22 = rt.binop('&', rt.getvar(fr, 'tStart'), '\n')
            rt.put_var(fr, 'tPoints', _v22, 'after')
            rt.put_idx(fr, 'tFound', rt.key_vals([rt.getvar(fr, 'tStart')]), 'true', 'into')
            rt.put_var(fr, 'tAngle', '180', 'into')
            _v23 = rt.fn(fr, 'Trace.Sweep', [rt.getvar(fr, 'tCol'), rt.getvar(fr, 'tRowNo'), rt.getvar(fr, 'tAngle'), rt.getvar(fr, 'tSweep'), rt.getvar(fr, 'tCell')], [('var', lambda _v: rt.put_var(fr, 'tCol', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tRowNo', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tAngle', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tSweep', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tCell', _v, 'into'))])
            rt.put_var(fr, 'tNext', _v23, 'into')
            if to_bool(rt.binop('=', rt.getvar(fr, 'tNext'), 'none')):
                rt.put_var(fr, 'tPoints', '\n', 'after')
                rt.put_var(fr, 'tLast', 'false', 'into')
                continue
            _v24 = rt.getvar(fr, 'tStart')
            rt.put_var(fr, 'tFirst', _v24, 'into')
            _v25 = rt.getvar(fr, 'tNext')
            rt.put_var(fr, 'tSecond', _v25, 'into')
            _v26 = rt.binop('&', rt.getvar(fr, 'tNext'), '\n')
            rt.put_var(fr, 'tPoints', _v26, 'after')
            rt.put_idx(fr, 'tFound', rt.key_vals([rt.getvar(fr, 'tNext')]), 'true', 'into')
            _v27 = rt.getvar(fr, 'tNext')
            rt.put_var(fr, 'tAt', _v27, 'into')
            rt.put_var(fr, 'tSteps', '0', 'into')
            while True:
                _v28 = rt.fn(fr, 'Trace.Sweep', [rt.get_chunk('item', rt.getvar(fr, 'tAt'), '1', None), rt.get_chunk('item', rt.getvar(fr, 'tAt'), '2', None), rt.getvar(fr, 'tAngle'), rt.getvar(fr, 'tSweep'), rt.getvar(fr, 'tCell')], [('chunk', lambda _v: rt.put_var(fr, 'tAt', rt.put_chunk('item', rt.cur_text(fr, 'tAt'), '1', None, _v, 'into'), 'into')), ('chunk', lambda _v: rt.put_var(fr, 'tAt', rt.put_chunk('item', rt.cur_text(fr, 'tAt'), '2', None, _v, 'into'), 'into')), ('var', lambda _v: rt.put_var(fr, 'tAngle', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tSweep', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tCell', _v, 'into'))])
                rt.put_var(fr, 'tNext', _v28, 'into')
                if to_bool(rt.binop('=', rt.getvar(fr, 'tNext'), 'none')):
                    break
                if to_bool(('true' if (rt.truth(rt.binop('=', rt.getvar(fr, 'tAt'), rt.getvar(fr, 'tFirst'))) and rt.truth(rt.binop('=', rt.getvar(fr, 'tNext'), rt.getvar(fr, 'tSecond')))) else 'false')):
                    break
                _v29 = rt.binop('&', rt.getvar(fr, 'tNext'), '\n')
                rt.put_var(fr, 'tPoints', _v29, 'after')
                rt.put_idx(fr, 'tFound', rt.key_vals([rt.getvar(fr, 'tNext')]), 'true', 'into')
                _v30 = rt.getvar(fr, 'tNext')
                rt.put_var(fr, 'tAt', _v30, 'into')
                _a31 = '1'
                _c32 = rt.cur_raw(fr, 'tSteps')
                rt.put_var(fr, 'tSteps', rt.arith('add', _a31, _c32), 'into')
                if to_bool(rt.binop('>', rt.getvar(fr, 'tSteps'), rt.getvar(fr, 'tLimit'))):
                    break
            rt.put_var(fr, 'tPoints', '\n', 'after')
    while to_bool(rt.binop('=', rt.get_chunk('char', rt.getvar(fr, 'tPoints'), rt.unop('-', '1'), None), '\n')):
        _c33 = to_text(rt.getvar(fr, 'tPoints'))
        rt.put_var(fr, 'tPoints', rt.cut_chunk('char', _c33, rt.unop('-', '1'), None), 'into')
    return rt.getvar(fr, 'tPoints')


def h_trace_sweeptable(rt, fr):
    # function Trace.SweepTable 
    fr.vars['tt'] = fr.vars.get('tt', "")
    rt.put_idx(fr, 'tT', rt.key_vals(['0']), '1,1', 'into')
    rt.put_idx(fr, 'tT', rt.key_vals(['45']), '1,0', 'into')
    rt.put_idx(fr, 'tT', rt.key_vals(['90']), '1,-1', 'into')
    rt.put_idx(fr, 'tT', rt.key_vals(['135']), '0,-1', 'into')
    rt.put_idx(fr, 'tT', rt.key_vals(['180']), '-1,-1', 'into')
    rt.put_idx(fr, 'tT', rt.key_vals(['225']), '-1,0', 'into')
    rt.put_idx(fr, 'tT', rt.key_vals(['270']), '-1,1', 'into')
    rt.put_idx(fr, 'tT', rt.key_vals(['315']), '0,1', 'into')
    return rt.getvar(fr, 'tT')


def h_trace_sweep(rt, fr):
    # function Trace.Sweep pX, pY, pAngle, pSweep, pCell
    fr.vars['ti'] = fr.vars.get('ti', "")
    fr.vars['tnx'] = fr.vars.get('tnx', "")
    fr.vars['tny'] = fr.vars.get('tny', "")
    fr.vars['tdx'] = fr.vars.get('tdx', "")
    fr.vars['tdy'] = fr.vars.get('tdy', "")
    _v1 = rt.getvar(fr, 'pAngle')
    rt.put_var(fr, 'tI', _v1, 'into')
    for _ in range(int(to_num(to_text('8')))):
        _v2 = rt.binop('+', rt.getvar(fr, 'pX'), rt.get_chunk('item', rt.get_idx(fr, 'pSweep', rt.key_vals([rt.getvar(fr, 'tI')])), '1', None))
        rt.put_var(fr, 'tNX', _v2, 'into')
        _v3 = rt.binop('+', rt.getvar(fr, 'pY'), rt.get_chunk('item', rt.get_idx(fr, 'pSweep', rt.key_vals([rt.getvar(fr, 'tI')])), '2', None))
        rt.put_var(fr, 'tNY', _v3, 'into')
        if to_bool(rt.binop('=', rt.get_idx(fr, 'pCell', rt.key_vals([rt.getvar(fr, 'tNY'), rt.getvar(fr, 'tNX')])), '1')):
            _v4 = rt.binop('-', rt.getvar(fr, 'tNX'), rt.getvar(fr, 'pX'))
            rt.put_var(fr, 'tDX', _v4, 'into')
            _v5 = rt.binop('-', rt.getvar(fr, 'tNY'), rt.getvar(fr, 'pY'))
            rt.put_var(fr, 'tDY', _v5, 'into')
            _v6 = rt.binop('mod', rt.fn(fr, 'round', [rt.fn(fr, 'abs', [rt.binop('-', rt.binop('/', rt.binop('*', rt.fn(fr, 'atan2', [rt.getvar(fr, 'tDY'), rt.getvar(fr, 'tDX')], [('var', lambda _v: rt.put_var(fr, 'tDY', _v, 'into')), ('var', lambda _v: rt.put_var(fr, 'tDX', _v, 'into'))]), '180'), K['pi']), '180')], [None])], [None]), '360')
            rt.put_var(fr, 'pAngle', _v6, 'into')
            return rt.binop('&', rt.binop('&', rt.getvar(fr, 'tNX'), ','), rt.getvar(fr, 'tNY'))
        _v7 = rt.binop('mod', rt.binop('+', rt.binop('-', rt.getvar(fr, 'tI'), '45'), '360'), '360')
        rt.put_var(fr, 'tI', _v7, 'into')
    return 'none'


def h_trace_masktogrid(rt, fr):
    # function Trace.MaskToGrid pMask, pWidth, pHeight, pThreshold
    fr.vars['tgrid'] = fr.vars.get('tgrid', "")
    fr.vars['trowno'] = fr.vars.get('trowno', "")
    fr.vars['tcol'] = fr.vars.get('tcol', "")
    fr.vars['tbyte'] = fr.vars.get('tbyte', "")
    if to_bool(rt.binop('=', rt.getvar(fr, 'pThreshold'), '')):
        rt.put_var(fr, 'pThreshold', '0', 'into')
    _x1 = to_num(to_text('0'))
    _e2 = to_num(to_text(rt.binop('-', rt.getvar(fr, 'pHeight'), '1')))
    _s3 = 1
    while (_s3 > 0) and _x1 < _e2 + _s3:
        rt.setvar(fr, 'tRowNo', numstr(_x1))
        _x1 += _s3
        _x4 = to_num(to_text('1'))
        _e5 = to_num(to_text(rt.getvar(fr, 'pWidth')))
        _s6 = 1
        while (_s6 > 0) and _x4 < _e5 + _s6:
            rt.setvar(fr, 'tCol', numstr(_x4))
            _x4 += _s6
            _v7 = rt.fn(fr, 'byteToNum', [rt.get_chunk('char', rt.getvar(fr, 'pMask'), rt.binop('+', rt.binop('*', rt.getvar(fr, 'tRowNo'), rt.getvar(fr, 'pWidth')), rt.getvar(fr, 'tCol')), None)], [('chunk', lambda _v: rt.put_var(fr, 'pMask', rt.put_chunk('char', rt.cur_text(fr, 'pMask'), rt.binop('+', rt.binop('*', rt.getvar(fr, 'tRowNo'), rt.getvar(fr, 'pWidth')), rt.getvar(fr, 'tCol')), None, _v, 'into'), 'into'))])
            rt.put_var(fr, 'tByte', _v7, 'into')
            if to_bool(rt.binop('>', rt.getvar(fr, 'tByte'), rt.getvar(fr, 'pThreshold'))):
                rt.put_var(fr, 'tGrid', '1', 'after')
            else:
                rt.put_var(fr, 'tGrid', '0', 'after')
        rt.put_var(fr, 'tGrid', '\n', 'after')
    _c8 = to_text(rt.getvar(fr, 'tGrid'))
    rt.put_var(fr, 'tGrid', rt.cut_chunk('char', _c8, '-1', None), 'into')
    return rt.getvar(fr, 'tGrid')


def h_trace_offset(rt, fr):
    # function Trace.Offset pPoints, pDX, pDY
    fr.vars['tline'] = fr.vars.get('tline', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    _t1 = to_text(rt.getvar(fr, 'pPoints'))
    for _a2, _b3 in ch.spans(_t1, 'line', **rt.delims()):
        rt.setvar(fr, 'tLine', _t1[_a2:_b3])
        if to_bool(rt.binop('=', rt.getvar(fr, 'tLine'), '')):
            rt.put_var(fr, 'tOut', '\n', 'after')
        else:
            _v4 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('+', rt.get_chunk('item', rt.getvar(fr, 'tLine'), '1', None), rt.getvar(fr, 'pDX')), ','), rt.binop('+', rt.get_chunk('item', rt.getvar(fr, 'tLine'), '2', None), rt.getvar(fr, 'pDY'))), '\n')
            rt.put_var(fr, 'tOut', _v4, 'after')
    _c5 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c5, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def h_trace_scale(rt, fr):
    # function Trace.Scale pPoints, pScale
    fr.vars['tline'] = fr.vars.get('tline', "")
    fr.vars['tout'] = fr.vars.get('tout', "")
    _t1 = to_text(rt.getvar(fr, 'pPoints'))
    for _a2, _b3 in ch.spans(_t1, 'line', **rt.delims()):
        rt.setvar(fr, 'tLine', _t1[_a2:_b3])
        if to_bool(rt.binop('=', rt.getvar(fr, 'tLine'), '')):
            rt.put_var(fr, 'tOut', '\n', 'after')
        else:
            _v4 = rt.binop('&', rt.binop('&', rt.binop('&', rt.binop('*', rt.get_chunk('item', rt.getvar(fr, 'tLine'), '1', None), rt.getvar(fr, 'pScale')), ','), rt.binop('*', rt.get_chunk('item', rt.getvar(fr, 'tLine'), '2', None), rt.getvar(fr, 'pScale'))), '\n')
            rt.put_var(fr, 'tOut', _v4, 'after')
    _c5 = to_text(rt.getvar(fr, 'tOut'))
    rt.put_var(fr, 'tOut', rt.cut_chunk('char', _c5, '-1', None), 'into')
    return rt.getvar(fr, 'tOut')


def install(rt):
    """add these handlers to rt, then run the script-level local/global/constant lines"""
    fr = Frame([])
    rt.handlers['trace.contours'] = ('function', 'Trace.Contours', ['pGrid'], None, [], h_trace_contours)
    rt.handlers['trace.sweeptable'] = ('function', 'Trace.SweepTable', [], None, [], h_trace_sweeptable)
    rt.handlers['trace.sweep'] = ('function', 'Trace.Sweep', ['pX', 'pY', 'pAngle', 'pSweep', 'pCell'], None, [2, 3, 4], h_trace_sweep)
    rt.handlers['trace.masktogrid'] = ('function', 'Trace.MaskToGrid', ['pMask', 'pWidth', 'pHeight', 'pThreshold'], None, [], h_trace_masktogrid)
    rt.handlers['trace.offset'] = ('function', 'Trace.Offset', ['pPoints', 'pDX', 'pDY'], None, [], h_trace_offset)
    rt.handlers['trace.scale'] = ('function', 'Trace.Scale', ['pPoints', 'pScale'], None, [], h_trace_scale)
