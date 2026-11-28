#!/usr/bin/env python3
"""gen_xt3d_py.py - write xtalk/xt3d/generated.py from the xt3d manifest (Phase 3, step 1)

  .venv/bin/python tools/gen_xt3d_py.py [path/to/xt3d_raylib_manifest.json]

xt3d (~/projects/xt3D_Raylib_Livecode_Bridge) gives LiveCode one handler per raylib function,
xt3d_<Name>, with structs spread into numbers and resources as integer handles. This makes the
same handlers in Python, on the `raylib` package (raylib's own C names through cffi), so a
script written against xt3d runs unchanged here.

The manifest keeps only the spread parameter names (position_x, position_y...). The grouping
back into structs comes from each entry's C prototype, with the same rules as the bridge's
gen_xt3d.py (flatten). Generation fails if a count does not match the manifest, or if the
raylib package lacks a function. Never edit the generated file: run this again.

The 43 hand-written helpers of xt3d_shim.c are in xtalk/xt3d/helpers.py (by hand, step 2).
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.expanduser('~/projects/xt3D_Raylib_Livecode_Bridge/xt3d_raylib_manifest.json')
OUT = os.path.join(ROOT, 'xtalk', 'xt3d', 'generated.py')

# the bridge's flatten rules (gen_xt3d.py)
VALUE = {
    'Vector2': (['x', 'y'], 'f'), 'Vector3': (['x', 'y', 'z'], 'f'),
    'Vector4': (['x', 'y', 'z', 'w'], 'f'), 'Quaternion': (['x', 'y', 'z', 'w'], 'f'),
    'Rectangle': (['x', 'y', 'width', 'height'], 'f'),
    'Color': (['r', 'g', 'b', 'a'], 'i'),
    'Matrix': (['m%d' % i for i in range(16)], 'f'),
    'Ray': (['position.x', 'position.y', 'position.z', 'direction.x', 'direction.y', 'direction.z'], 'f'),
    'BoundingBox': (['min.x', 'min.y', 'min.z', 'max.x', 'max.y', 'max.z'], 'f'),
}
RES = {'Image': 'Image', 'Texture': 'Texture', 'Texture2D': 'Texture', 'TextureCubemap': 'Texture',
       'RenderTexture': 'RenderTexture', 'RenderTexture2D': 'RenderTexture', 'Font': 'Font', 'Mesh': 'Mesh',
       'Shader': 'Shader', 'Material': 'Material', 'Model': 'Model', 'ModelAnimation': 'ModelAnimation',
       'Wave': 'Wave', 'Sound': 'Sound', 'Music': 'Music', 'AudioStream': 'AudioStream',
       'Camera3D': 'Camera3D', 'Camera': 'Camera3D', 'Camera2D': 'Camera2D'}
SCALAR = {'int': 'i', 'unsigned int': 'u', 'float': 'f', 'double': 'f', 'bool': 'b', 'long': 'i'}
CONV = {'i': 'I', 'u': 'U', 'f': 'F', 'b': 'B'}     # text -> Python, defined in xtalk/xt3d/__init__.py


def split_proto(proto):
    """'Ray GetScreenToWorldRay(Vector2 position, Camera camera)' -> ('Ray', [('Vector2', 'position'), ...])"""
    m = re.match(r'(.*?)(\w+)\((.*)\)$', proto)
    ret, params = m.group(1).strip(), m.group(3).strip()
    out = []
    if params != 'void':
        for p in params.split(','):
            pm = re.match(r'(.*?)(\w+)$', p.strip())
            out.append((re.sub(r'\s+', ' ', pm.group(1)).strip(), pm.group(2)))
    return ret, out


PATH_PARAMS = ('fileName', 'filePath', 'dirPath', 'path', 'basePath', 'srcPath', 'dstPath', 'fileRename',
               'vsFileName', 'fsFileName')
OPENS = re.compile(r'^(Load|Export|Save|TakeScreenshot|File|DirectoryExists|ChangeDirectory|MakeDirectory|'
                   r'GetFileLength|GetFileModTime|IsPathFile|IsPathDirectory)')
WRITES = re.compile(r'^(Export|Save|TakeScreenshot|FileRemove|FileRename|FileTextReplace|MakeDirectory)')


def path_kind(fname, param):
    """x1-04: a path the call opens is taken as a script gives it (C:/xt3d/..., //wsl$/...): P() maps it for
    reading, PW() for writing (the owner's window: his real file; checks: the sandbox). String-only calls
    (GetFileName, GetDirectoryPath...) keep the text as it is."""
    if param not in PATH_PARAMS or not OPENS.match(fname):
        return ''
    if param == 'dstPath' or param == 'fileRename' or (WRITES.match(fname) and param != 'srcPath'):
        return 'PW'
    return 'P'


def args_code(params, keep=False, fname=''):
    """the Python argument expressions for the raylib call, and how many spread values they use.
    keep: string arguments go into locals k0, k1... first (raylib may return a pointer into one, as
    GetFileExtension does: a temporary would be freed before the result is read)"""
    code, k, pre = [], 0, []

    def take(c):
        nonlocal k
        s = '%s(a[%d])' % (CONV[c], k) if c != 'C' else 'C(a[%d])' % k
        k += 1
        return s
    for t, n in params:
        base = t.replace('const ', '').strip()
        if base in SCALAR:
            code.append(take(SCALAR[base]))
        elif base == 'char *' and t.startswith('const') and not keep and path_kind(fname, n):
            code.append('%s(a[%d])' % (path_kind(fname, n), k))   # a file the call opens: C:/ -> /mnt/c (x1-04)
            k += 1
        elif base == 'char *' and t.startswith('const'):
            if keep:
                pre.append("k%d = ffi.new('char[]', S(a[%d]))" % (k, k))
                code.append('k%d' % k)
            else:
                code.append('S(a[%d])' % k)
            k += 1
        elif base in VALUE:
            fields, c = VALUE[base]
            vals = [take('C' if base == 'Color' else c) for _ in fields]
            if base == 'Matrix':            # by field name: raylib declares m0, m4, m8, m12, m1...
                code.append('MX(%s)' % ', '.join(vals))
            elif base in ('Ray', 'BoundingBox'):
                code.append('((%s), (%s))' % (', '.join(vals[:3]), ', '.join(vals[3:])))
            else:
                code.append('(%s)' % ', '.join(vals))
        elif base == 'NPatchInfo':
            vals = [take('f') for _ in range(4)] + [take('i') for _ in range(5)]
            code.append('((%s), %s)' % (', '.join(vals[:4]), ', '.join(vals[4:])))
        elif base in RES:
            code.append('T_%s.get(I(a[%d]))[0]' % (RES[base], k))
            k += 1
        elif base.endswith(' *') and base[:-2] in RES and not t.startswith('const'):
            code.append('T_%s.get(I(a[%d]))' % (RES[base[:-2]], k))
            k += 1
        else:
            raise ValueError('parameter type ' + t)
    return code, k, pre


def ret_code(ret, call):
    """(Python lines that make the xTalk result of `call`, idle result without a window)"""
    rb = ret.replace('const ', '').strip()
    if ret == 'void':
        return ['%s' % call, "return ''"], "''"
    if rb in SCALAR:
        c = SCALAR[rb]
        if c == 'b':
            return ["return 'true' if %s else 'false'" % call], "'false'"
        if c == 'f':
            return ['return numstr(%s)' % call], "'0'"
        if rb == 'int':
            return ['return W(%s)' % call], "'0'"      # signed, as the bridge gives it (measured)
        return ['return str(int(%s))' % call], "'0'"
    if rb == 'char *' and ret.startswith('const'):
        return ['return R(%s)' % call], "''"
    if ret == 'void *':
        return ['%s' % call, "return ''"], "''"       # GetWindowHandle: a pointer means nothing in a script
    if rb in VALUE:
        fields, c = VALUE[rb]
        if c == 'i':
            return ['r = %s' % call, "return '%s' %% (%s)" % (','.join(['%d'] * len(fields)),
                                                          ', '.join('r.' + f for f in fields))], "''"
        return ['r = %s' % call, "return '%s' %% (%s)" % (','.join(['%.9g'] * len(fields)),
                                                      ', '.join('r.' + f for f in fields))], "''"
    if rb == 'RayCollision':
        return ['r = %s' % call,
                "return '%d,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g' % (r.hit, r.distance, r.point.x, r.point.y, "
                "r.point.z, r.normal.x, r.normal.y, r.normal.z)"], "''"
    if rb in RES:
        return ['return str(T_%s.new(%s))' % (RES[rb], call)], "'0'"
    raise ValueError('return type ' + ret)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else MANIFEST
    m = json.load(open(path))
    import raylib as rl
    lines = ['"""GENERATED by tools/gen_xt3d_py.py from xt3d_raylib_manifest.json (raylib %s). Do not edit."""'
             % m['raylib_version'],
             'from . import rl, ffi, ready, numstr, I, U, F, B, C, S, P, PW, R, W, MX  # noqa: F401',
             'from .tables import %s  # noqa: F401' % ', '.join('T_' + t for t in sorted(set(RES.values()))),
             '', '']
    names, missing, n = [], [], 0
    for e in m['functions']:
        if e['status'] != 'wrapped':
            continue
        name = e['raylib']
        if not hasattr(rl, name):
            missing.append(name)
            continue
        ret, params = split_proto(e['c_prototype'])
        code, k, pre = args_code(params, keep=ret.replace(' ', '') == 'constchar*', fname=name)
        if k != len(e['params']):
            raise SystemExit('%s: %d values from the prototype, %d in the manifest' % (name, k, len(e['params'])))
        call = 'rl.%s(%s)' % (name, ', '.join(code))
        body, idle = ret_code(ret, call)
        unload = name.startswith('Unload') and params and params[0][0] in RES
        fn = e['xt3d']
        lines.append('def %s(*a):' % fn)
        lines.append('    """%s"""' % e['c_prototype'].replace('\\', '\\\\'))
        if k:
            lines.append("    a = a + ('',) * (%d - len(a))" % k)    # a missing argument is empty (0)
        if e.get('needs_window'):
            idle_lines = (['T_%s.free(I(a[0]))' % RES[params[0][0]]] if unload else []) + ['return ' + idle]
            lines.append('    if not ready():')
            lines += ['        ' + x for x in idle_lines]
        if unload:
            body = [body[0], 'T_%s.free(I(a[0]))' % RES[params[0][0]]] + body[1:]
        if name == 'InitWindow':           # a second InitWindow would orphan every GPU resource (the shim)
            body = ['if not ready():', '    ' + body[0]] + body[1:]
        lines += ['    ' + x for x in pre + body]
        lines.append('')
        names.append(fn)
        n += 1
    lines.append('FUNCS = {')
    lines += ['    %r: %s,' % (x.lower(), x) for x in names]
    lines.append('}')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w').write('\n'.join(lines) + '\n')
    print('wrote %s: %d functions' % (os.path.relpath(OUT, ROOT), n))
    if missing:
        print('NOT in the raylib package (left out):', ' '.join(missing))


if __name__ == '__main__':
    main()
