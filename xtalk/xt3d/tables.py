"""Handle tables: images, textures, models, cameras... are positive integers in a script, 0 = invalid.

The same rules as xt3d_shim.c (XT_TABLE), so handle numbers match the real bridge:
- a new handle takes the lowest free number, from 1;
- an invalid or freed handle gives a zeroed struct (slot 0), never an error;
- freeing a handle only forgets it (Unload... frees the GPU side first).
"""
from . import ffi


class Table:
    def __init__(self, ctype):
        self.ctype = ctype
        self.slots = [None]                       # slot 0: the zeroed stand-in

    def get(self, h):
        """a pointer to the struct (pass p[0] by value, p where raylib wants a pointer)"""
        if 0 < h < len(self.slots):
            p = self.slots[h]
            if p is not None:
                return p
        return ffi.new(self.ctype + ' *')         # zeroed each time, as the shim clears slot 0

    def new(self, value):
        p = ffi.new(self.ctype + ' *', value)     # copies the struct raylib returned
        for h in range(1, len(self.slots)):
            if self.slots[h] is None:
                self.slots[h] = p
                return h
        self.slots.append(p)
        return len(self.slots) - 1

    def free(self, h):
        if 0 < h < len(self.slots):
            self.slots[h] = None

    def valid(self, h):
        return 0 < h < len(self.slots) and self.slots[h] is not None

    def count(self):
        return sum(1 for p in self.slots[1:] if p is not None)


TYPES = ['Image', 'Texture', 'RenderTexture', 'Font', 'Mesh', 'Shader', 'Material', 'Model', 'ModelAnimation',
         'Wave', 'Sound', 'Music', 'AudioStream', 'Camera3D', 'Camera2D']
TABLES = {t: Table(t) for t in TYPES}
T_Image, T_Texture, T_RenderTexture, T_Font, T_Mesh, T_Shader, T_Material, T_Model, T_ModelAnimation, \
    T_Wave, T_Sound, T_Music, T_AudioStream, T_Camera3D, T_Camera2D = (TABLES[t] for t in TYPES)


def reset():
    """forget every handle (a new run; tests)"""
    for t in TABLES.values():
        t.slots[1:] = []
