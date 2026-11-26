"""The bridge's hand-written helpers (xt3d_shim.c and the tail of xt3d.lcb), by hand, in the same order.

Each one does what its C twin does, including what it gives back with no window or a bad handle;
tests/test_xt3d.py checks them against the real bridge. Not the same yet:
- xt3d_SetTraceLogFile opens (or closes) the file but raylib's lines do not reach it: raylib hands its
  callback a C va_list that Python cannot format. It answers true/false as the shim does.
- xt3d_RenderTextureImageData / AlphaData give the bytes as text (one char a byte), as LiveCode's
  imageData is; step 4 (where the 3D view draws) will likely draw the texture straight instead.
"""
import re, struct
from . import rl, ffi, ready, numstr, I, F, B, C, S, R, W, MX, XtError   # noqa: F401
from .tables import TABLES, T_Image, T_Texture, T_RenderTexture, T_Mesh, T_Shader, T_Material, T_Model, \
    T_ModelAnimation, T_Camera3D, T_Camera2D

VERSION = '0.1.0'
G9 = '%.9g'


def _pad(a, k):
    return a + ('',) * (k - len(a))


def xt3d_Version(*a):
    return 'xt3d %s / raylib %s' % (VERSION, R(rl.RAYLIB_VERSION) if not isinstance(rl.RAYLIB_VERSION, str)
                                     else rl.RAYLIB_VERSION)


# ---- the window. In the stack runtime the stack's own window is raylib's window (HOST['view'] set by the
# view): a script's InitWindow / InitHidden find it ready and do nothing, as the shim does, and its
# CloseWindow must not close the stack, so it does nothing there either.
HOST = {'view': None}


def xt3d_CloseWindow(*a):
    if HOST['view'] is not None or not ready():
        return ''
    rl.CloseWindow()
    return ''


def xt3d_InitHidden(*a):
    a = _pad(a, 3)
    if ready():                     # a second InitWindow would orphan every GPU resource
        return ''
    rl.SetConfigFlags(rl.FLAG_WINDOW_HIDDEN)
    rl.InitWindow(I(a[0]), I(a[1]), S(a[2]))
    return ''


# ---- cameras
def _cam3(a):
    return ((F(a[0]), F(a[1]), F(a[2])), (F(a[3]), F(a[4]), F(a[5])), (F(a[6]), F(a[7]), F(a[8])), F(a[9]), I(a[10]))


def xt3d_CameraCreate(*a):
    return str(T_Camera3D.new(_cam3(_pad(a, 11))))


def xt3d_CameraSet(*a):
    a = _pad(a, 12)
    h = I(a[0])
    if T_Camera3D.valid(h):
        p = T_Camera3D.get(h)
        p[0] = _cam3(a[1:])
    return ''


def xt3d_CameraGet(*a):
    c = T_Camera3D.get(I(_pad(a, 1)[0]))
    return ','.join([G9 % v for v in (c.position.x, c.position.y, c.position.z, c.target.x, c.target.y, c.target.z,
                                      c.up.x, c.up.y, c.up.z, c.fovy)] + ['%d' % c.projection])


def xt3d_CameraFree(*a):
    T_Camera3D.free(I(_pad(a, 1)[0]))
    return ''


def _cam2(a):
    return ((F(a[0]), F(a[1])), (F(a[2]), F(a[3])), F(a[4]), F(a[5]))


def xt3d_Camera2DCreate(*a):
    return str(T_Camera2D.new(_cam2(_pad(a, 6))))


def xt3d_Camera2DSet(*a):
    a = _pad(a, 7)
    h = I(a[0])
    if T_Camera2D.valid(h):
        T_Camera2D.get(h)[0] = _cam2(a[1:])
    return ''


def xt3d_Camera2DFree(*a):
    T_Camera2D.free(I(_pad(a, 1)[0]))
    return ''


# ---- struct fields
def xt3d_ImageInfo(*a):
    i = T_Image.get(I(_pad(a, 1)[0]))
    return '%d,%d,%d,%d' % (i.width, i.height, i.mipmaps, i.format)


def xt3d_TextureInfo(*a):
    t = T_Texture.get(I(_pad(a, 1)[0]))
    return '%d,%d,%d,%d,%d' % (t.id, t.width, t.height, t.mipmaps, t.format)


def xt3d_RenderTextureGetTexture(*a):
    return str(T_Texture.new(T_RenderTexture.get(I(_pad(a, 1)[0])).texture))


def xt3d_ModelInfo(*a):
    m = T_Model.get(I(_pad(a, 1)[0]))
    return '%d,%d,%d' % (m.meshCount, m.materialCount, m.skeleton.boneCount)


def xt3d_ModelGetMesh(*a):
    a = _pad(a, 2)
    m = T_Model.get(I(a[0]))
    k = I(a[1])
    if k < 0 or k >= m.meshCount:
        return '0'
    return str(T_Mesh.new(m.meshes[k]))


def xt3d_ModelSetTransform(*a):
    a = _pad(a, 17)
    T_Model.get(I(a[0])).transform = MX(*[F(x) for x in a[1:17]])
    return ''


def xt3d_ModelGetTransform(*a):
    r = T_Model.get(I(_pad(a, 1)[0])).transform
    return ','.join(G9 % getattr(r, 'm%d' % i) for i in range(16))


def _model_material(model, material):
    m = T_Model.get(model)
    if material < 0 or material >= m.materialCount or m.materials == ffi.NULL:
        return None
    return m.materials + material


def xt3d_ModelSetMaterialTexture(*a):
    a = _pad(a, 4)
    mat = _model_material(I(a[0]), I(a[1]))
    if mat is not None and mat.maps != ffi.NULL:
        rl.SetMaterialTexture(mat, I(a[2]), T_Texture.get(I(a[3]))[0])
    return ''


def _map_color(mat, a):
    k = I(a[0])
    if mat is not None and mat.maps != ffi.NULL and 0 <= k <= rl.MATERIAL_MAP_BRDF:
        mat.maps[k].color = (C(a[1]), C(a[2]), C(a[3]), C(a[4]))


def xt3d_ModelSetMaterialColor(*a):
    a = _pad(a, 7)
    _map_color(_model_material(I(a[0]), I(a[1])), a[2:])
    return ''


def xt3d_ModelSetMaterialShader(*a):
    a = _pad(a, 3)
    mat = _model_material(I(a[0]), I(a[1]))
    if mat is not None:
        mat.shader = T_Shader.get(I(a[2]))[0]
    return ''


def xt3d_MaterialSetColor(*a):
    a = _pad(a, 6)
    _map_color(T_Material.get(I(a[0])), a[1:])
    return ''


def xt3d_MaterialSetShader(*a):
    a = _pad(a, 2)
    T_Material.get(I(a[0])).shader = T_Shader.get(I(a[1]))[0]
    return ''


# ---- animation sets: handles of one set are consecutive
ANIMSETS = {}                       # first handle -> (the raylib array, count)
MAX_ANIMSETS = 256


def xt3d_LoadModelAnimations(*a):
    n = ffi.new('int *')
    anims = rl.LoadModelAnimations(S(_pad(a, 1)[0]), n)
    count = n[0]
    if anims == ffi.NULL or count <= 0:
        return '0,0'
    if len(ANIMSETS) >= MAX_ANIMSETS:
        rl.UnloadModelAnimations(anims, count)
        return '0,0'
    t = T_ModelAnimation
    first = 1
    while any(t.valid(first + k) for k in range(count)):
        first += 1
    while len(t.slots) < first + count:
        t.slots.append(None)
    for k in range(count):
        # the table points into raylib's array (the shim copies the structs; the arrays inside are shared)
        t.slots[first + k] = anims + k
    ANIMSETS[first] = (anims, count)
    return '%d,%d' % (first, count)


def xt3d_UnloadModelAnimations(*a):
    first = I(_pad(a, 1)[0])
    s = ANIMSETS.pop(first, None)
    if s is not None:
        for k in range(s[1]):
            T_ModelAnimation.free(first + k)
        rl.UnloadModelAnimations(s[0], s[1])
    return ''


def xt3d_ModelAnimationInfo(*a):
    m = T_ModelAnimation.get(I(_pad(a, 1)[0]))
    name = ffi.string(m.name, 32).decode('latin-1')
    return '%s,%d,%d' % (name, m.boneCount, m.keyframeCount)


# ---- shader uniforms
def xt3d_SetShaderValueFloats(*a):
    a = _pad(a, 7)
    if not ready():
        return ''
    v = ffi.new('float[4]', [F(x) for x in a[3:7]])
    count = min(max(I(a[2]), 1), 4)
    rl.SetShaderValue(T_Shader.get(I(a[0]))[0], I(a[1]), v, rl.SHADER_UNIFORM_FLOAT + count - 1)
    return ''


def xt3d_SetShaderValueInt(*a):
    a = _pad(a, 3)
    if not ready():
        return ''
    v = ffi.new('int *', I(a[2]))
    rl.SetShaderValue(T_Shader.get(I(a[0]))[0], I(a[1]), v, rl.SHADER_UNIFORM_INT)
    return ''


# ---- picking
def xt3d_GetRayCollisionModel(*a):
    a = _pad(a, 7)
    ray = ((F(a[0]), F(a[1]), F(a[2])), (F(a[3]), F(a[4]), F(a[5])))
    m = T_Model.get(I(a[6]))
    best = None
    for i in range(m.meshCount):
        c = rl.GetRayCollisionMesh(ray, m.meshes[i], m.transform)
        if c.hit and (best is None or c.distance < best.distance):
            best = c
    if best is None:
        return '0,0,0,0,0,0,0,0'
    return '%d,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g' % (best.hit, best.distance, best.point.x, best.point.y,
                                                      best.point.z, best.normal.x, best.normal.y, best.normal.z)


# ---- frames for LiveCode: imageData is 4 bytes a pixel (an unused byte, then r g b), rows from the top;
# alphaData one byte a pixel. Render textures come back from the GPU bottom row first.
FRAME = {'data': b'', 'alpha': b''}


def _grab(target):
    img = rl.LoadImageFromTexture(T_RenderTexture.get(target).texture)
    if img.data != ffi.NULL and img.format != rl.PIXELFORMAT_UNCOMPRESSED_R8G8B8A8:
        p = ffi.new('Image *', img)
        rl.ImageFormat(p, rl.PIXELFORMAT_UNCOMPRESSED_R8G8B8A8)
        img = p[0]
    return img


def xt3d_RenderTextureExport(*a):
    a = _pad(a, 2)
    if not ready():
        return 'false'
    img = _grab(I(a[0]))
    if img.data == ffi.NULL:
        return 'false'
    p = ffi.new('Image *', img)
    rl.ImageFlipVertical(p)
    ok = rl.ExportImage(p[0], S(a[1]))
    rl.UnloadImage(p[0])
    return 'true' if ok else 'false'


def _to_image_data(target):
    if not ready():
        FRAME['data'] = FRAME['alpha'] = b''
        return
    img = _grab(target)
    if img.data == ffi.NULL:
        FRAME['data'] = FRAME['alpha'] = b''
        return
    w, h = img.width, img.height
    src = bytes(ffi.buffer(img.data, w * h * 4))
    rl.UnloadImage(img)
    rows = [src[(h - 1 - y) * w * 4:(h - y) * w * 4] for y in range(h)]
    flat = b''.join(rows)
    out = bytearray(w * h * 4)
    out[1::4] = flat[0::4]
    out[2::4] = flat[1::4]
    out[3::4] = flat[2::4]
    FRAME['data'] = bytes(out)
    FRAME['alpha'] = flat[3::4]


def xt3d_RenderTextureToImageData(*a):
    _to_image_data(I(_pad(a, 1)[0]))
    return ''                       # a pointer in C: means nothing to a script


def xt3d_ImageDataSize(*a):
    return str(len(FRAME['data']))


def xt3d_AlphaDataSize(*a):
    return str(len(FRAME['data']) // 4)


def xt3d_RenderTextureToAlphaData(*a):
    if not FRAME['alpha']:
        _to_image_data(I(_pad(a, 1)[0]))
    return ''


def xt3d_RenderTextureImageData(*a):
    """the LCB handler: the frame's imageData (binary: one char a byte)"""
    _to_image_data(I(_pad(a, 1)[0]))
    return FRAME['data'].decode('latin-1')


def xt3d_RenderTextureAlphaData(*a):
    if not FRAME['alpha']:
        _to_image_data(I(_pad(a, 1)[0]))
    return FRAME['alpha'].decode('latin-1')


# ---- meshes from numbers: x,y,z per vertex; optional u,v per vertex; optional 0-based triangle indices.
# Numbers separated by anything (strtod skips what is not a number). Normals: smooth when indexed, flat
# otherwise. Indexed meshes at most 65535 vertices. 0 on bad input.
_FLOAT = re.compile(r'[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?')


def _floats(text):
    return [float(m.group()) for m in _FLOAT.finditer(text)]


def xt3d_MeshFromText(*a):
    a = _pad(a, 3)
    if not ready():
        return '0'
    from ..values import to_text
    vf, tf, xf = (_floats(to_text(x)) for x in a[:3])
    nv, nt, ni = len(vf) // 3, len(tf) // 2, len(xf)
    ok = nv >= 3 and (nt == 0 or nt == nv) and ni % 3 == 0 and (nv <= 65535 if ni > 0 else nv % 3 == 0)
    if ok and any(x < 0 or int(x) >= nv for x in xf):
        ok = False
    if not ok:
        return '0'
    vf32 = list(struct.unpack('%df' % (3 * nv), struct.pack('%df' % (3 * nv), *vf[:3 * nv])))   # floats, as C
    mesh = ffi.new('Mesh *')
    mesh.vertexCount = nv
    mesh.triangleCount = ni // 3 if ni else nv // 3
    mesh.vertices = ffi.cast('float *', rl.MemAlloc(4 * 3 * nv))
    mesh.normals = ffi.cast('float *', rl.MemAlloc(4 * 3 * nv))
    for i, v in enumerate(vf32):
        mesh.vertices[i] = v
    if nt:
        mesh.texcoords = ffi.cast('float *', rl.MemAlloc(4 * 2 * nv))
        for i in range(2 * nv):
            mesh.texcoords[i] = tf[i]
    idx = [int(x) & 0xFFFF for x in xf]
    if ni:
        mesh.indices = ffi.cast('unsigned short *', rl.MemAlloc(2 * ni))
        for i, x in enumerate(idx):
            mesh.indices[i] = x
    nrm = [0.0] * (3 * nv)
    for t in range(mesh.triangleCount):
        ia, ib, ic = (idx[t * 3], idx[t * 3 + 1], idx[t * 3 + 2]) if ni else (t * 3, t * 3 + 1, t * 3 + 2)
        pa, pb, pc = vf32[ia * 3:ia * 3 + 3], vf32[ib * 3:ib * 3 + 3], vf32[ic * 3:ic * 3 + 3]
        ux, uy, uz = pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]
        wx, wy, wz = pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2]
        nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
        for k in (ia, ib, ic):
            nrm[k * 3] += nx
            nrm[k * 3 + 1] += ny
            nrm[k * 3 + 2] += nz
    for i in range(nv):
        x, y, z = nrm[i * 3:i * 3 + 3]
        l2 = x * x + y * y + z * z
        if l2 > 0:
            inv = 1.0 / l2 ** 0.5
            mesh.normals[i * 3], mesh.normals[i * 3 + 1], mesh.normals[i * 3 + 2] = x * inv, y * inv, z * inv
        else:
            mesh.normals[i * 3], mesh.normals[i * 3 + 1], mesh.normals[i * 3 + 2] = x, 1.0, z
    rl.UploadMesh(mesh, False)
    return str(T_Mesh.new(mesh[0]))


def xt3d_MeshInfo(*a):
    m = T_Mesh.get(I(_pad(a, 1)[0]))
    return '%d,%d,%d' % (m.vertexCount, m.triangleCount, 1 if m.indices != ffi.NULL else 0)


# ---- render state (rlgl): each change first draws what is waiting, so it applies only to what follows
def _gl(fn):
    def f(*a):
        if not ready():
            return ''
        rl.rlDrawRenderBatchActive()
        fn(_pad(a, 1)[0])
        return ''
    return f


xt3d_SetBackfaceCulling = _gl(lambda v: rl.rlEnableBackfaceCulling() if B(v) else rl.rlDisableBackfaceCulling())
xt3d_SetCullFace = _gl(lambda v: rl.rlSetCullFace(I(v)))
xt3d_SetWireMode = _gl(lambda v: rl.rlEnableWireMode() if B(v) else rl.rlDisableWireMode())
xt3d_SetDepthTest = _gl(lambda v: rl.rlEnableDepthTest() if B(v) else rl.rlDisableDepthTest())
xt3d_SetLineWidth = _gl(lambda v: rl.rlSetLineWidth(F(v)))


# ---- diagnostics
LOG = {'file': None}


def xt3d_SetTraceLogFile(*a):
    from ..values import to_text
    name = to_text(_pad(a, 1)[0])
    if LOG['file']:
        LOG['file'].close()
        LOG['file'] = None
    if not name:
        return 'true'
    try:
        LOG['file'] = open(name, 'w')
    except OSError:
        return 'false'
    return 'true'


def xt3d_ResultLength(*a):
    return '0'              # no result buffer here: text results come back whole


def xt3d_ResultByte(*a):
    return '0'


def xt3d_HandleCount(*a):
    from ..values import to_text
    t = TABLES.get(to_text(_pad(a, 1)[0]))
    return '-1' if t is None else str(t.count())


FUNCS = {k.lower(): v for k, v in list(globals().items()) if k.startswith('xt3d_') and callable(v)}
