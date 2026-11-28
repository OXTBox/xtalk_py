"""LiveCode's graphic effects in the Python window: outerGlow, innerGlow, dropShadow, innerShadow, colorOverlay
(x1-09, docs/SHADERS.md). Needs .venv (raylib). The shaders are LIB_SHADERS/shaders/*.fs.

Per object with an effect, at the window's scale:
  1. its shape: the object drawn alone into a texture, padded by the effect's size (+ distance, + line width);
  2. blurred (blur.fs, across then down), radius = size;
  3. drawn: dropShadow and outerGlow UNDER the object (glow.fs), colorOverlay, innerShadow, innerGlow OVER it
     (glow.fs / inner.fs). LiveCode's order: shadow, glow, object, overlay, inner shadow, inner glow.
The textures are made again only when the object changes (rect, points, text, props, scale).
A stack with no effects costs one number compare a frame (rt.fx_version, View.draw_card).
"""
import math, os
import pyray as rl
from .host import EFFECTS, effect_of

SHADER_DIR = os.environ.get('XTALK_SHADERS') or os.path.expanduser('~/projects/LIB_SHADERS/shaders')
UNDER = ('dropshadow', 'outerglow')
OVER = ('coloroverlay', 'innershadow', 'innerglow')
# what an effect draws when a key is not set (LiveCode's documented defaults; not measured yet, see LIVECODE_FACTS)
DEFAULTS = {'color': '255,255,255', 'opacity': 255, 'size': 5, 'spread': 0, 'distance': 5, 'angle': 60,
            'source': 'edge'}


def num(d, k, default=None):
    v = next((v for x, v in d.items() if x.lower() == k), None)
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(DEFAULTS[k] if default is None else default)


def rgba(d, view):
    from .view import colour
    c = colour(next((v for x, v in d.items() if x.lower() == 'color'), None) or DEFAULTS['color'], rl.WHITE)
    op = max(0.0, min(255.0, num(d, 'opacity'))) / 255.0
    return (c.r / 255.0, c.g / 255.0, c.b / 255.0, op)


class Effects:
    def __init__(self, view):
        self.view = view
        self.shaders = None            # name -> (shader, {uniform: location}); False: could not load
        self.cache = {}                # id(object) -> {'sig', 'origin', 'size', 'mask', 'tmp', 'blur': {effect: rt}}
        self.objs = {}                 # id -> object: the current card's objects with an effect
        self.seen = None               # (rt.fx_version, card) the list was made for
        self.ms = 0.0                  # time spent making textures (the last frame), for checks

    # ------------------------------------------------------------ which objects
    def refresh(self):
        """the objects of the shown card with an effect: looked for again only when an effect was set, an
        object made, or another card shown (one compare a frame otherwise)"""
        rt = self.view.rt
        card = rt.default_stack.current
        key = (getattr(rt, 'fx_version', 0), id(card))
        if key == self.seen:
            return self.objs
        self.seen = key
        objs = {}
        if card is not None:
            for o in card.flat():
                if any(effect_of(o, p) for p in EFFECTS):
                    objs[id(o)] = o
        for k in [k for k in self.cache if k not in objs]:
            self.forget(k)
        self.objs = objs
        return objs

    def forget(self, k):
        c = self.cache.pop(k, None)
        if c:
            for rt_ in [c['mask'], c['tmp']] + list(c['blur'].values()):
                rl.unload_render_texture(rt_)

    def close(self):
        for k in list(self.cache):
            self.forget(k)
        if self.shaders:
            for sh, _ in self.shaders.values():
                rl.unload_shader(sh)
        self.shaders = None

    # ------------------------------------------------------------ shaders
    def load(self):
        if self.shaders is not None:
            return bool(self.shaders)
        self.shaders = {}
        names = {'blur': ('texel', 'dir', 'radius'), 'glow': ('glowColor', 'spread'),
                 'inner': ('mask', 'shift', 'glowColor', 'spread', 'center')}
        for n, uniforms in names.items():
            path = os.path.join(SHADER_DIR, n + '.fs')
            if not os.path.isfile(path):
                print('effects: no shader', path, '- graphic effects are not drawn', flush=True)
                self.shaders = False
                return False
            sh = rl.load_shader(rl.ffi.NULL, path)
            if not sh.id or not rl.is_shader_valid(sh):
                print('effects: shader did not compile', path, flush=True)
                self.shaders = False
                return False
            self.shaders[n] = (sh, {u: rl.get_shader_location(sh, u) for u in uniforms})
        return True

    def uniform(self, name, u, v):
        sh, loc = self.shaders[name]
        if isinstance(v, (int, float)):
            rl.set_shader_value(sh, loc[u], rl.ffi.new('float *', float(v)), rl.SHADER_UNIFORM_FLOAT)
        else:
            kind = {2: rl.SHADER_UNIFORM_VEC2, 4: rl.SHADER_UNIFORM_VEC4}[len(v)]
            rl.set_shader_value(sh, loc[u], rl.ffi.new('float[]', [float(x) for x in v]), kind)

    # ------------------------------------------------------------ the textures
    def effects(self, o):
        return {p: effect_of(o, p) for p in EFFECTS if effect_of(o, p)}

    def prepare(self):
        """before the card is drawn (outside its scale matrix: a texture pass resets it): make the shapes and
        blurs of the objects whose look changed"""
        objs = self.refresh()
        if not objs or not self.load():
            return
        import time
        t0 = time.perf_counter()
        for k, o in objs.items():
            if self.view.rt._shown(o):
                self.make(k, o)
        self.ms = (time.perf_counter() - t0) * 1000

    def sig(self, o, fx):
        v = self.view
        return (tuple(o.rect), v.scale, repr(sorted(fx.items())), repr(o.points), o.text, str(o.props),
                id(getattr(o, 'imagedata', None)))

    def make(self, k, o):
        v = self.view
        fx = self.effects(o)
        s = self.sig(o, fx)
        c = self.cache.get(k)
        if c is not None and c['sig'] == s:
            return
        pad = 2
        for p, d in fx.items():
            extra = num(d, 'distance') if p in ('dropshadow', 'innershadow') else 0
            pad = max(pad, num(d, 'size') + extra + 2)
        try:
            pad += float(v.prop(o, 'lineSize') or 1)
        except ValueError:
            pad += 1
        l, t, r, b = o.rect
        ox, oy = l - pad, t - pad
        w = max(1, int(math.ceil((r - l + 2 * pad) * v.scale)))
        h = max(1, int(math.ceil((b - t + 2 * pad) * v.scale)))
        w, h = min(w, 4096), min(h, 4096)
        if c is None or c['size'] != (w, h):
            self.forget(k)
            c = {'mask': rl.load_render_texture(w, h), 'tmp': rl.load_render_texture(w, h), 'blur': {}, 'size': (w, h)}
            self.cache[k] = c
        c['sig'], c['origin'] = s, (ox, oy)
        # 1. the shape
        rl.begin_texture_mode(c['mask'])
        rl.clear_background(rl.BLANK)
        rl.rl_push_matrix()
        rl.rl_scalef(v.scale, v.scale, 1)
        rl.rl_translatef(-ox, -oy, 0)
        v.fx_origin = (ox, oy)                   # fields clip with scissors in pixels: from this texture's corner
        try:
            getattr(v, 'draw_' + o.type, v.draw_other)(o)
        finally:
            v.fx_origin = None
        rl.rl_draw_render_batch_active()
        rl.rl_pop_matrix()
        rl.end_texture_mode()
        # 2. a blur per effect that blurs (its own size)
        for p, d in fx.items():
            if p == 'coloroverlay':
                continue
            radius = max(0.0, num(d, 'size')) * v.scale
            dst = c['blur'].get(p)
            if dst is None:
                dst = c['blur'][p] = rl.load_render_texture(w, h)
            self.blur(c['mask'], c['tmp'], radius, (1, 0), w, h)
            self.blur(c['tmp'], dst, radius, (0, 1), w, h)
        for p in [p for p in c['blur'] if p not in fx or p == 'coloroverlay']:
            rl.unload_render_texture(c['blur'].pop(p))

    def blur(self, src, dst, radius, direction, w, h):
        sh = self.shaders['blur'][0]
        rl.begin_texture_mode(dst)
        rl.clear_background(rl.BLANK)
        rl.begin_shader_mode(sh)
        self.uniform('blur', 'texel', (1.0 / w, 1.0 / h))
        self.uniform('blur', 'dir', direction)
        self.uniform('blur', 'radius', radius)
        rl.rl_set_blend_factors(1, 0, 0x8006)    # copied as it is (no blending with the cleared texture);
        rl.begin_blend_mode(rl.BLEND_CUSTOM)     # the factors first: BeginBlendMode takes them as they are
        rl.draw_texture_rec(src.texture, rl.Rectangle(0, 0, w, -h), rl.Vector2(0, 0), rl.WHITE)
        rl.end_blend_mode()
        rl.end_shader_mode()
        rl.end_texture_mode()

    # ------------------------------------------------------------ drawing (inside the card's scale matrix)
    def draw(self, o, which):
        """which = UNDER (before the object is drawn) or OVER (after)"""
        c = self.cache.get(id(o))
        if c is None or not self.shaders:
            return
        v = self.view
        fx = self.effects(o)
        w, h = c['size']
        ox, oy = c['origin']
        for p in which:
            d = fx.get(p)
            if d is None:
                continue
            col = rgba(d, v)
            spread = max(0.0, min(255.0, num(d, 'spread'))) / 255.0
            dx = dy = 0.0
            if p in ('dropshadow', 'innershadow'):
                a = math.radians(num(d, 'angle'))
                dist = num(d, 'distance')
                dx, dy = dist * math.cos(a), dist * math.sin(a)
            dest = rl.Rectangle(ox + dx if p == 'dropshadow' else ox, oy + dy if p == 'dropshadow' else oy,
                                w / v.scale, h / v.scale)
            if p in ('innerglow', 'innershadow'):
                name = 'inner'
                tex = c['blur'][p].texture
            else:
                name = 'glow'
                tex = (c['mask'] if p == 'coloroverlay' else c['blur'][p]).texture
                if p == 'coloroverlay':
                    spread = 0.0
            sh = self.shaders[name][0]
            rl.rl_draw_render_batch_active()
            rl.begin_shader_mode(sh)
            self.uniform(name, 'glowColor', col)
            self.uniform(name, 'spread', spread)
            if name == 'inner':
                rl.set_shader_value_texture(sh, self.shaders['inner'][1]['mask'], c['mask'].texture)
                # the sampled texture is drawn upside down (source height negative): down in the card is -v
                self.uniform('inner', 'shift', (dx * v.scale / w, -dy * v.scale / h) if p == 'innershadow' else (0.0, 0.0))
                src = next((x for k, x in d.items() if k.lower() == 'source'), 'edge')
                self.uniform('inner', 'center', 1.0 if str(src).lower() == 'center' else 0.0)
            rl.draw_texture_pro(tex, rl.Rectangle(0, 0, w, -h), dest, rl.Vector2(0, 0), 0, rl.WHITE)
            rl.end_shader_mode()
