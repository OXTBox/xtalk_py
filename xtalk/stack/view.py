"""The stack window: raylib draws the card, ImGui the runtime panel (errors, answers). Needs .venv.

    .venv/bin/python -I tools/open_stack.py ~/projects/XTJSON/Game_card_reader_11_13_2025

Drawn: card colour; graphics (rectangle, roundrect, oval, line, polygon, curve, regular) with fill,
border and label; buttons (standard, rectangle, roundrect, transparent, checkbox, radio, menu kinds as
a plain button); fields (plain text, scroll, list hilite); scrollbars (track + thumb); images from the
harvest's assets. Styled text (htmlText runs: face, size, bold/italic, underline, strikeout, colours) and word wrap.
NOT drawn yet: players, widgets, gradients, ink effects, rotated images.
"""
import math, os, time
import pyray as rl
from imgui_bundle import imgui
from .host import canon
from ..values import to_num
from .styled import COLOR_NAMES, PLAIN
from . import styled

FONT_DIRS = ['/mnt/c/Windows/Fonts', '/usr/share/fonts/truetype/dejavu']
FAMILIES = {   # face -> (regular, bold, italic, bold italic) files in the Windows fonts folder
    'segoe ui': ('segoeui', 'segoeuib', 'segoeuii', 'segoeuiz'), 'arial': ('arial', 'arialbd', 'ariali', 'arialbi'),
    'consolas': ('consola', 'consolab', 'consolai', 'consolaz'), 'courier new': ('cour', 'courbd', 'couri', 'courbi'),
    'times new roman': ('times', 'timesbd', 'timesi', 'timesbi'), 'verdana': ('verdana', 'verdanab', 'verdanai', 'verdanaz'),
    'georgia': ('georgia', 'georgiab', 'georgiai', 'georgiaz'), 'tahoma': ('tahoma', 'tahomabd', 'tahoma', 'tahomabd')}
ALIASES = {'': 'segoe ui', 'lucida grande': 'segoe ui', 'helvetica': 'arial', 'geneva': 'verdana',
           'courier': 'courier new', 'monaco': 'consolas', 'times': 'times new roman', 'menlo': 'consolas'}
CODEPOINTS = list(range(32, 127)) + list(range(160, 384)) + list(range(0x2010, 0x2040)) + [0x20AC, 0x2122, 0x2190,
              0x2191, 0x2192, 0x2193, 0x2022, 0x2026]
NAMES = {k: v for k, v in COLOR_NAMES.items()}
SCALE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          'run_files', 'window_scale.json')
SCALE_MIN, SCALE_MAX, SCALE_STEP = 0.5, 3.0, 0.05


def windows_scale():
    """Windows' display scaling (Settings > Display > Scale: 125% -> 1.25). LiveCode on Windows draws at it;
    WSLg draws our window at one pixel a unit (measured 26 Nov: monitor 1920x1080, window DPI 1.0), so
    without our own scale a Python window is smaller than the same stack in LiveCode"""
    if not hasattr(windows_scale, 'v'):
        windows_scale.v = 1.0
        try:
            import subprocess
            out = subprocess.run(['reg.exe', 'query', r'HKCU\Control Panel\Desktop\WindowMetrics', '/v', 'AppliedDPI'],
                                 capture_output=True, text=True, timeout=10, cwd='/mnt/c').stdout
            dpi = int(out.split('REG_DWORD')[1].split()[0], 16)
            if 72 <= dpi <= 480:
                windows_scale.v = dpi / 96
        except Exception:
            pass
    return windows_scale.v


def remembered_scales():
    try:
        import json
        with open(SCALE_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def window_scale(stack_name):
    """the scale a real window opens at: XTALK_SCALE, else the one remembered for this stack (Ctrl + / -),
    else the one remembered for every stack ('*'), else Windows' own scaling"""
    try:
        return max(SCALE_MIN, min(SCALE_MAX, float(os.environ['XTALK_SCALE'])))
    except (KeyError, ValueError):
        pass
    saved = remembered_scales()
    for k in (str(stack_name).lower(), '*'):
        try:
            return max(SCALE_MIN, min(SCALE_MAX, float(saved[k])))
        except (KeyError, ValueError, TypeError):
            pass
    return windows_scale()


def remember_scale(stack_name, s):
    import json
    saved = remembered_scales()
    saved[str(stack_name).lower()] = s
    try:
        os.makedirs(os.path.dirname(SCALE_FILE), exist_ok=True)
        with open(SCALE_FILE, 'w') as f:
            json.dump(saved, f, indent=1, sort_keys=True)
    except OSError:
        pass


def colour(v, default=None):
    """a LiveCode colour (r,g,b text, [r,g,b], name or #hex) -> rl.Color, or default"""
    if v is None or v == '':
        return default
    if isinstance(v, (list, tuple)):
        rgb = v
    else:
        t = str(v).strip().lower()
        if t.startswith('#') and len(t) == 7:
            rgb = (int(t[1:3], 16), int(t[3:5], 16), int(t[5:7], 16))
        elif ',' in t:
            rgb = [int(float(x)) for x in t.split(',')[:3]]
        else:
            rgb = NAMES.get(t.replace(' ', ''))
            if rgb is None:
                return default
    return rl.Color(int(rgb[0]), int(rgb[1]), int(rgb[2]), 255)


class View:
    def __init__(self, rt, hidden=False, pos=(200, 32), scale=1.0):
        """scale: our own scaleFactor (owner 26 Nov, x1-00: \"so I can read it\"). Everything is drawn that much
        bigger with sharp text; the scripts never see it (rects, the mouseLoc, the screenRect stay in units)"""
        self.rt = rt
        st = rt.default_stack
        w, h = st.size if st.size else (st.width, st.height)
        self.base_size = (int(w), int(h))
        self.scale = max(SCALE_MIN, min(SCALE_MAX, float(scale)))
        self.on_scale = None           # called with the new scale after Ctrl + / - / 0 (open_stack remembers it)
        rl.set_trace_log_level(rl.LOG_WARNING)
        if hidden:
            rl.set_config_flags(rl.FLAG_WINDOW_HIDDEN)
        rl.init_window(*self.scaled_size(), st.props.get('title') or st.name)
        if not hidden:                 # 200,32 in units, as LiveCode places it on a scaled Windows screen
            rl.set_window_position(int(pos[0] * self.scale), int(pos[1] * self.scale))
        rl.set_exit_key(0)
        rl.set_target_fps(60)
        try:                           # xt3d scripts draw with this window; their CloseWindow must not close it
            from ..xt3d import helpers as xt3d_helpers
            xt3d_helpers.HOST['view'] = self
        except ImportError:
            pass
        self.fonts = {}
        self.textures = {}
        self.icons = {}                # (stack, icon value) -> the image it names
        self.pixels = {}               # id(image) -> (its imageData text, texture): pictures set by script
        self.menu = None               # a menu being shown: {'items', 'x', 'y', 'pick', 'opened', 'done'}
        self.dialog = None             # an answer/ask being shown
        self.down_on = None
        self.panel = True
        rt.measure = lambda o, s, st=None: self.measure(o, s, None, st)   # the layout measures with the real fonts
        rt.measure_key = 'font'
        rt.on_clipboard_get = lambda: rl.get_clipboard_text() or ''
        rt.on_clipboard_set = lambda t: rl.set_clipboard_text(t)
        self.cursor_hidden = False
        self.captured, self.vmouse, self.last_real = False, (0, 0), (0, 0)
        self.warped = None             # where the scripts last put the mouse while lockCursor was true (mouse look)
        # soft grab (WSL): raylib's disable_cursor needs the pointer warped back each frame, which WSLg does not
        # allow; instead the movement of the real pointer is counted (no grab; XTALK_HARD_GRAB=1 for the old way)
        self.soft_grab = 'microsoft' in os.uname().release.lower() and not os.environ.get('XTALK_HARD_GRAB')
        self.other_down = {}           # right / middle button: the object it went down on
        self.look = {'right presses': 0, 'grabs': 0, 'moved x': 0, 'moved y': 0, 'frames grabbed': 0, 'recentre failed': 0}
        try:                           # soft grab: the pointer's movement times this (owner 25 Nov: not sensitive enough)
            self.look_speed = float(os.environ.get('XTALK_LOOK_SPEED', '2'))
        except ValueError:
            self.look_speed = 2.0
        self.settle = 0                # frames to wait after moving the pointer back (WSL moves it late)
        self.recentre = True           # soft grab: put the hidden pointer back in the middle each frame (off if WSL refuses)
        self.on_close = None           # play mode: called the moment the close box is clicked (it ends the program)
        self.esc_frees = False         # play mode: Escape frees the mouse and keys (and again takes them back)
        self.freed = False
        if not hidden:                 # a hidden (test) window never moves the real mouse
            rt.window_pos = tuple(pos)
            rt.on_warp = self.warp
        imgui.create_context()
        imgui.get_io().set_ini_filename('')
        imgui.backends.opengl3_init('#version 330')
        self.imgui_scale = 1.0
        self.scale_imgui()

    # ------------------------------------------------------------ scale
    def scaled_size(self):
        return int(round(self.base_size[0] * self.scale)), int(round(self.base_size[1] * self.scale))

    def scale_imgui(self):
        """menus, dialogs and the runtime panel grow with the window (ImGui draws its font at the size, sharp)"""
        style = imgui.get_style()
        if not hasattr(self, 'imgui_base'):    # its sizes at scale 1: scaling step on step rounds them away
            self.imgui_base = {}
            for k in dir(style):
                if k.startswith('_') or k in ('font_scale_main', 'font_scale_dpi', 'mouse_cursor_scale', 'alpha'):
                    continue
                v = getattr(style, k, None)
                if isinstance(v, float):
                    self.imgui_base[k] = v
                elif isinstance(v, imgui.ImVec2):
                    self.imgui_base[k] = imgui.ImVec2(v.x, v.y)
        for k, v in self.imgui_base.items():
            setattr(style, k, imgui.ImVec2(v.x, v.y) if isinstance(v, imgui.ImVec2) else v)
        style.scale_all_sizes(self.scale)
        style.font_scale_main = self.scale
        self.imgui_scale = self.scale

    def set_scale(self, s):
        """Ctrl + / Ctrl - / Ctrl 0: the window and everything in it bigger or smaller"""
        s = round(max(SCALE_MIN, min(SCALE_MAX, s)), 2)
        if s == self.scale:
            return
        self.scale = s
        for k in [k for k in self.fonts if len(k) == 3]:   # bigger letter sets made for the old scale
            rl.unload_font(self.fonts.pop(k))
        rl.set_window_size(*self.scaled_size())
        self.scale_imgui()
        self.cache_dirty = True
        self.wake()
        if self.on_scale is not None:
            self.on_scale(s)

    def mouse_units(self):
        """the real pointer in the window -> the card's units"""
        m = rl.get_mouse_position()
        return m.x / self.scale, m.y / self.scale

    def scissor(self, x, y, w, h):
        """clip to a card rect (scissors work in real pixels: the scale's matrix does not reach them)"""
        s = self.scale
        if s == 1:
            rl.begin_scissor_mode(int(x), int(y), max(0, int(w)), max(0, int(h)))
            return
        x0, y0 = math.floor(x * s), math.floor(y * s)     # edges rounded outward: truncating the top and the
        x1, y1 = math.ceil((x + w) * s), math.ceil((y + h) * s)   # height cut the last row's descenders
        rl.begin_scissor_mode(x0, y0, max(0, x1 - x0), max(0, y1 - y0))

    # ------------------------------------------------------------ helpers
    def capture(self):
        """set the cursor to none + set the lockCursor to true (Raycasting_101's mouse look): the window grabs
        the mouse (raylib disable_cursor: hidden, endless movement) and the scripts see a virtual mouseLoc that
        `set the screenMouseLoc` can put back in the middle. Under WSL a program may not move the real pointer,
        so this is the only way a mouse-look game works. The cursor back / lockCursor false lets it go."""
        rt = self.rt
        hide = str(rt.props.get('cursor', '')).lower() == 'none'
        locked = str(rt.props.get('lockcursor', '')).lower() == 'true'
        if not locked:
            self.warped = None
        # mouse look is lockCursor + either cursor none (Raycasting_101) or the mouse put back by script each
        # frame (uDead: lockCursor, then set the screenMouseLoc to the centre); Escape in play mode lets it go
        want = locked and (hide or self.warped is not None) and not self.freed
        if want and not self.captured:
            m = rl.get_mouse_position()
            self.last_real = (m.x, m.y)
            self.vmouse = self.warped if self.warped is not None else self.mouse_units()   # no jump on the first frame
            if not self.soft_grab:
                rl.disable_cursor()
            else:
                rl.hide_cursor()              # hidden while it looks; put back in the middle each frame (below)
                self.cursor_hidden = True
                self.settle = 0
            self.captured = True
            self.look['grabs'] += 1
        elif not want and self.captured:
            if not self.soft_grab:
                rl.enable_cursor()
            else:
                rl.show_cursor()
            self.captured = False
            self.cursor_hidden = False
        hide = hide and not self.freed
        if not self.captured and hide != self.cursor_hidden:
            (rl.hide_cursor if hide else rl.show_cursor)()
            self.cursor_hidden = hide

    def warp(self, x, y):
        """set the screenMouseLoc: x,y on the screen -> inside this window. While the mouse is grabbed the
        virtual mouse moves (always works); otherwise the real pointer is asked to move (WSL may ignore it)"""
        wx, wy = self.rt.window_pos
        if str(self.rt.props.get('lockcursor', '')).lower() == 'true':
            self.warped = (x - wx, y - wy)
            if not self.captured and not self.freed:
                self.capture()                # the grab starts now: the next read in this frame sees the warp
        if self.captured or self.freed:       # freed (Escape in play mode): the real pointer is his alone
            self.vmouse = (x - wx, y - wy)
            self.rt.mouse = (int(x - wx), int(y - wy))   # the mouseLoc changes at once (as in LiveCode)
            return
        rl.set_mouse_position(int((x - wx) * self.scale), int((y - wy) * self.scale))

    def font(self, o, size, st=None, drawn=1.0):
        """the font for o's text, or for a styled run st (its face and bold/italic over the field's). Its letters
        are made at twice the size, enough to stay sharp up to a scale of 1.5; drawn bigger than that, a bigger
        set is made for drawing (measuring keeps the first, so the text wraps the same at every scale)"""
        face = (st[1] if st and st[1] else None) or self.prop(o, 'textfont') or self.inherit(o, 'textFont') or ''
        flags = st[0] if st and st[0] else styled.flags_of(self.prop(o, 'textstyle') or self.inherit(o, 'textStyle') or '')
        face = str(face).lower().strip()
        fam = FAMILIES.get(ALIASES.get(face, face), FAMILIES['segoe ui'])
        f = fam[('bold' in flags) + 2 * ('italic' in flags)] + '.ttf'
        made = size * 2 if drawn <= 1.5 else int(math.ceil(size * 2 * drawn / 1.5))
        key = (f, size) if made == size * 2 else (f, size, made)
        if key not in self.fonts:
            path = next((os.path.join(d, f) for d in FONT_DIRS if os.path.exists(os.path.join(d, f))), None)
            if path is None and f != 'segoeui.ttf':
                path = next((os.path.join(d, x) for d in FONT_DIRS for x in ('segoeui.ttf', 'DejaVuSans.ttf')
                             if os.path.exists(os.path.join(d, x))), None)
            if path:
                cps = rl.ffi.new('int[]', CODEPOINTS)          # curly quotes, accents, the euro...
                rl.set_trace_log_level(rl.LOG_ERROR)   # a face lacks a few of the asked letters (Segoe: 11 of 375):
                self.fonts[key] = rl.load_font_ex(path, made, rl.ffi.cast('int *', cps), len(CODEPOINTS))
                rl.set_trace_log_level(rl.LOG_WARNING)  # raylib warns once per missing letter; they draw as a box
            else:
                self.fonts[key] = rl.get_font_default()
            rl.set_texture_filter(self.fonts[key].texture, rl.TEXTURE_FILTER_BILINEAR)
        return self.fonts[key]

    def inherit(self, o, key):
        """a text or colour property: the object, its groups, card, stack, then the stack's effective value"""
        k = canon(key)
        x = o
        while x is not None:
            for pk in x.props.keys_for(k):
                v = x.props[pk]
                if v != '':
                    return v
            x = x.parent if x.type != 'card' else x.stack
            if x is not None and x.type == 'stack':
                for pk in x.props.keys_for(k):
                    v = x.props[pk]
                    if v != '':
                        return v
                return next((v for ek, v in x.effective.items() if canon(ek) == k), None)
        return None

    def size(self, o):
        try:
            return int(float(self.inherit(o, 'textSize') or 12))
        except ValueError:
            return 12

    def text(self, o, s, x, y, col, size=None, st=None):
        size = (st[2] if st and st[2] else None) or size or self.size(o)
        f = self.font(o, size, st, self.scale)
        fm = self.font(o, size, st)
        px = size * 4 / 3
        if f is fm:
            rl.draw_text_ex(f, s, rl.Vector2(x, y), px, 0, col)
            return
        # scale over 1.5: the bigger letters, each placed where the measuring set puts it (its advances are
        # whole numbers at a smaller size: placed by the big set, a bold word ran into the next space)
        k = px / fm.baseSize
        for ch in s:
            cp = ord(ch)
            if ch not in ' \t':
                rl.draw_text_codepoint(f, cp, rl.Vector2(x, y), px, col)
            i = rl.get_glyph_index(fm, cp)
            g = fm.glyphs[i]
            x += (g.advanceX or (fm.recs[i].width + g.offsetX)) * k

    def measure(self, o, s, size=None, st=None):
        size = (st[2] if st and st[2] else None) or size or self.size(o)
        return rl.measure_text_ex(self.font(o, size, st), s, size * 4 / 3, 0).x

    # raylib key -> LiveCode key code (as rawKeyDown and the keysDown give them; letters lower case; from memory,
    # not measured: these need a real keyboard)
    KEYCODES = ([(getattr(rl, 'KEY_%s' % c), ord(c.lower())) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']
                + [(getattr(rl, 'KEY_%s' % w), ord(d)) for w, d in zip(['ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE',
                                                                         'SIX', 'SEVEN', 'EIGHT', 'NINE'], '0123456789')]
                + [(rl.KEY_SPACE, 32), (rl.KEY_LEFT, 65361), (rl.KEY_UP, 65362), (rl.KEY_RIGHT, 65363),
                   (rl.KEY_DOWN, 65364), (rl.KEY_LEFT_SHIFT, 65505), (rl.KEY_RIGHT_SHIFT, 65506),
                   (rl.KEY_LEFT_CONTROL, 65507), (rl.KEY_RIGHT_CONTROL, 65508), (rl.KEY_LEFT_ALT, 65513),
                   (rl.KEY_ENTER, 65293), (rl.KEY_ESCAPE, 65307), (rl.KEY_TAB, 65289), (rl.KEY_BACKSPACE, 65288),
                   (rl.KEY_GRAVE, 96)])

    def prop(self, o, p):
        return self.rt.host.obj_prop(o, p.lower())

    def on(self, o, p):
        return self.prop(o, p) == 'true'

    # ------------------------------------------------------------ drawing
    def draw_card(self):
        st = self.rt.default_stack
        card = st.current
        bg = colour(self.inherit(card, 'backgroundColor'), rl.Color(240, 240, 240, 255))
        rl.clear_background(bg)
        scaled = self.scale != 1
        if scaled:                         # one matrix: every object drawn in units, shown at the scale
            rl.rl_draw_render_batch_active()
            rl.rl_push_matrix()
            rl.rl_scalef(self.scale, self.scale, 1)
        for o in card.flat():
            if o.type == 'group' or not self.rt._shown(o):
                continue
            getattr(self, 'draw_' + o.type, self.draw_other)(o)
        if scaled:
            rl.rl_draw_render_batch_active()
            rl.rl_pop_matrix()
        if self.esc_frees:
            self.draw_escape_label()

    def fronts_take(self, code):
        """play mode: Escape (or another key the View keeps) goes first to the front scripts only, as rawKeyDown
        reaches them first in LiveCode. True when one took it (did not pass it): GameNotes closing its box,
        whatever has the focus (a click on the card had taken it from the box, and Escape then freed the mouse
        instead, leaving the box up and the game paused: g1-02). Passed by them all: the View's, the game never
        sees it."""
        rt = self.rt
        fronts = [rt.ctx[id(x)] for x in rt.fronts if id(x) in rt.ctx]
        if not any('rawkeydown' in c.handlers for c in fronts):
            return False
        rt.engine_contexts = lambda o, f=fronts: f        # for this one message, the path is the front scripts
        try:
            return rt.handled(rt.default_stack.current, 'rawKeyDown', [str(code)])
        finally:
            del rt.engine_contexts

    def draw_escape_label(self):
        """play mode: a corner line that says whether the game has the mouse and keys"""
        if self.freed:
            t, bg = 'FREE: mouse and keys are yours.  Esc = back to the game', rl.Color(150, 30, 30, 230)
        else:
            t, bg = 'Esc = free the mouse', rl.Color(0, 0, 0, 140)
        w = rl.measure_text(t, 10)
        rl.draw_rectangle(rl.get_screen_width() - w - 12, 2, w + 10, 16, bg)
        rl.draw_text(t, rl.get_screen_width() - w - 7, 5, 10, rl.Color(255, 255, 255, 255))

    def rect(self, o):
        l, t, r, b = o.rect
        return rl.Rectangle(l, t, r - l, b - t)

    @staticmethod
    def fill_polygon(pts, fill):
        """fill a polygon (closed for you), even-odd like within(): one horizontal line per pixel row"""
        if len(pts) < 3:
            return
        edges = list(zip(pts, pts[1:] + pts[:1]))
        top, bottom = min(p[1] for p in pts), max(p[1] for p in pts)
        for y in range(int(top), int(bottom) + 1):
            yc = y + 0.5
            xs = sorted(x1 + (yc - y1) * (x2 - x1) / (y2 - y1) for (x1, y1), (x2, y2) in edges
                        if (y1 <= yc < y2) or (y2 <= yc < y1))
            for a, b in zip(xs[0::2], xs[1::2]):
                xa, xb = int(round(a)), int(round(b))
                if xb > xa:
                    rl.draw_rectangle(xa, y, xb - xa, 1, fill)

    def dash_pattern(self, o):
        """the dashes of a graphic ("2,5,10,20": 2 drawn, 5 left out, 10 drawn, 20 left out, again); empty or
        not numbers: a solid line"""
        t = str(self.prop(o, 'dashes') or '').strip()
        if not t:
            return None
        try:
            d = [float(x) for x in t.split(',') if x.strip()]
        except ValueError:
            return None
        if len(d) % 2:
            d = d + d                              # an odd list: on and off swap the second time round
        return d if d and sum(d) > 0 and all(x >= 0 for x in d) else None

    @staticmethod
    def draw_dashed(run, dashes, lw, col):
        """one stroke (connected points) drawn with a dash pattern; the pattern runs on over the corners
        (Thrmnlra's missile trails: Term.Path ... "2,5,10,20")"""
        i, left, on = 0, dashes[0], True
        for (x0, y0), (x1, y1) in zip(run, run[1:]):
            seg = math.hypot(x1 - x0, y1 - y0)
            pos = 0.0
            while pos < seg:
                step = min(left, seg - pos)
                if on and step > 0:
                    a, b = pos / seg, (pos + step) / seg
                    rl.draw_line_ex(rl.Vector2(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a),
                                    rl.Vector2(x0 + (x1 - x0) * b, y0 + (y1 - y0) * b), lw, col)
                pos += step
                left -= step
                if left <= 0:
                    i = (i + 1) % len(dashes)
                    left, on = dashes[i], not on

    def draw_graphic(self, o):
        style = self.prop(o, 'style') or 'rectangle'
        fill = colour(self.inherit(o, 'backgroundColor'), rl.Color(240, 240, 240, 255))
        line = colour(self.inherit(o, 'foregroundColor'), rl.BLACK)
        lw = max(1, int(float(self.prop(o, 'lineSize') or 1)))
        filled = self.on(o, 'filled') or self.on(o, 'opaque')
        rc = self.rect(o)
        if style in ('rectangle', 'roundrect'):
            if style == 'roundrect':
                # roundRadius is the corner's diameter, held to half the width / height; default 15 (measured 26 Nov:
                # LiveCode's corners are ellipses min(r/2, w/2) x min(r/2, h/2); raylib's are circles of the smaller)
                try:
                    rr = float(self.prop(o, 'roundRadius') or 15)
                except ValueError:
                    rr = 15.0
                rnd = min(1.0, max(0.0, rr) / max(1, min(rc.width, rc.height)))
                if filled:
                    rl.draw_rectangle_rounded(rc, rnd, 8, fill)
                rl.draw_rectangle_rounded_lines_ex(rc, rnd, 8, lw, line)
            else:
                if filled:
                    rl.draw_rectangle_rec(rc, fill)
                rl.draw_rectangle_lines_ex(rc, lw, line)
        elif style == 'oval':
            cx, cy = rc.x + rc.width / 2, rc.y + rc.height / 2
            if filled:
                rl.draw_ellipse(int(cx), int(cy), rc.width / 2, rc.height / 2, fill)
            rl.draw_ellipse_lines(int(cx), int(cy), rc.width / 2, rc.height / 2, line)
        elif style in ('line', 'polygon', 'curve'):
            pts = o.points or [[o.rect[0], o.rect[1]], [o.rect[2], o.rect[3]]]
            if style == 'polygon' and filled:
                self.fill_polygon([p for p in pts if p is not None], fill)
            run = []
            dashes = self.dash_pattern(o)
            for p in pts + [None]:
                if p is None:
                    if dashes:
                        self.draw_dashed(run, dashes, lw, line)
                    else:
                        for a, b in zip(run, run[1:]):
                            rl.draw_line_ex(rl.Vector2(*a), rl.Vector2(*b), lw, line)
                    run = []
                else:
                    run.append(p)
        elif style == 'regular':                  # the same corners as within() and LiveCode (angle turns them)
            pts = self.rt.host.regular(o)
            if filled:
                cx, cy = (o.rect[0] + o.rect[2]) // 2, (o.rect[1] + o.rect[3]) // 2
                for a, b in zip(pts, pts[1:]):        # clockwise on screen: raylib wants counter-clockwise
                    rl.draw_triangle(rl.Vector2(cx, cy), rl.Vector2(*b), rl.Vector2(*a), fill)
            for a, b in zip(pts, pts[1:]):
                rl.draw_line_ex(rl.Vector2(*a), rl.Vector2(*b), lw, line)
        if self.on(o, 'showName'):
            s = self.prop(o, 'label') or o.name
            self.text(o, s, rc.x + (rc.width - self.measure(o, s)) / 2, rc.y + (rc.height - self.size(o) * 4 / 3) / 2,
                      colour(self.inherit(o, 'foregroundColor'), rl.BLACK))

    def draw_button(self, o):
        style = self.prop(o, 'style') or 'standard'
        rc = self.rect(o)
        lit = self.on(o, 'hilited') or (self.down_on is o and rl.is_mouse_button_down(0))
        fg = colour(self.inherit(o, 'foregroundColor'), rl.BLACK)
        label = (self.prop(o, 'label') or o.name) if self.on(o, 'showName') else ''
        if style in ('checkbox', 'radiobutton'):
            bx = rl.Rectangle(rc.x + 2, rc.y + (rc.height - 13) / 2, 13, 13)
            if style == 'checkbox':
                rl.draw_rectangle_rec(bx, rl.WHITE)
                rl.draw_rectangle_lines_ex(bx, 1, rl.DARKGRAY)
                if self.on(o, 'hilited'):
                    rl.draw_line_ex(rl.Vector2(bx.x + 3, bx.y + 7), rl.Vector2(bx.x + 6, bx.y + 10), 2, rl.BLACK)
                    rl.draw_line_ex(rl.Vector2(bx.x + 6, bx.y + 10), rl.Vector2(bx.x + 11, bx.y + 3), 2, rl.BLACK)
            else:
                c = rl.Vector2(bx.x + 6.5, bx.y + 6.5)
                rl.draw_circle_v(c, 6.5, rl.WHITE)
                rl.draw_circle_lines_v(c, 6.5, rl.DARKGRAY)
                if self.on(o, 'hilited'):
                    rl.draw_circle_v(c, 3.5, rl.BLACK)
            self.text(o, label, rc.x + 20, rc.y + (rc.height - self.size(o) * 4 / 3) / 2, fg)
            return
        if style != 'transparent':
            base = colour(self.inherit(o, 'backgroundColor'), rl.Color(225, 225, 225, 255))
            if lit:
                base = colour(self.inherit(o, 'hiliteColor'), rl.Color(204, 228, 247, 255))
            rnd = 0.3 if style == 'roundrect' else 0.08 if style == 'standard' else 0
            if self.on(o, 'opaque') or style == 'standard':
                rl.draw_rectangle_rounded(rc, rnd, 6, base) if rnd else rl.draw_rectangle_rec(rc, base)
            if self.on(o, 'showBorder'):
                bc = colour(self.inherit(o, 'borderColor'), rl.Color(173, 173, 173, 255))
                rl.draw_rectangle_rounded_lines_ex(rc, rnd, 6, 1, bc) if rnd else rl.draw_rectangle_lines_ex(rc, 1, bc)
        if self.draw_icon(o, rc):
            label = ''                     # icon and name together: the name is not drawn yet
        tw = self.measure(o, label)
        al = self.prop(o, 'textAlign') or 'center'
        x = rc.x + (rc.width - tw) / 2 if al == 'center' else rc.x + 4 if al == 'left' else rc.x + rc.width - tw - 4
        self.text(o, label, x, rc.y + (rc.height - self.size(o) * 4 / 3) / 2, fg)

    def draw_field(self, o):
        rc = self.rect(o)
        if self.on(o, 'opaque'):
            own = o.props.get('backgroundColor') not in (None, '')
            dark = getattr(o.stack, 'theme', '') == 'oxt-dark'    # OXT's dark theme: fields dark too
            rl.draw_rectangle_rec(rc, colour(self.inherit(o, 'backgroundColor'), rl.WHITE) if (own or dark) else rl.WHITE)
        if self.on(o, 'showBorder'):
            rl.draw_rectangle_lines_ex(rc, 1, colour(self.inherit(o, 'borderColor'), rl.Color(130, 135, 144, 255)))
        rt = self.rt
        size, lh, m, scroll, sbw = rt.field_metrics(o)    # one rule for drawing and for clicks
        rows = rt.field_rows(o)
        hl = set(rt.host.hilited_lines(o))
        self.scissor(rc.x + 1, rc.y + 1, rc.width - 2 - sbw, rc.height - 2)
        fg = colour(self.inherit(o, 'foregroundColor'), rl.BLACK)
        if rt.focused is o and rt.editable(o):     # a focused list field shows its hilite, no caret
            self.draw_selection(o, rc, rows, lh, m, scroll)
        x0 = rc.x + m / 2 + 2
        y = rc.y + m / 2 - scroll
        for n, a, b in rows:
            if y > rc.y + rc.height:
                break
            if y + lh >= rc.y:
                lit = n in hl
                if lit:
                    rl.draw_rectangle(int(rc.x + 1), int(y), int(rc.width - 2 - sbw), int(lh), rl.Color(0, 120, 215, 255))
                x = x0
                for i, j, st in styled.runs(o.text, o.styles, a, b):
                    piece = o.text[i:j]
                    w = self.measure(o, piece, size, st)
                    if st[4] and not lit:
                        rl.draw_rectangle(int(x), int(y), int(w + 0.5), int(lh), colour(st[4]))
                    link = 'link' in st[0]     # a link: its own colour, else the linkColor; underlined (measured)
                    col = rl.WHITE if lit else (colour(st[3]) if st[3] else colour(styled.LINK_COLOUR) if link else fg)
                    rsize = st[2] or size
                    ty = y + (st[5] or 0) + (lh - 2 - rsize * 4 / 3) / 2 + 1
                    self.text(o, piece, x, ty, col, size, st)
                    if 'underline' in st[0] or link:
                        rl.draw_line(int(x), int(ty + rsize * 4 / 3), int(x + w), int(ty + rsize * 4 / 3), col)
                    if 'strikeout' in st[0]:
                        rl.draw_line(int(x), int(ty + rsize * 2 / 3 + 1), int(x + w), int(ty + rsize * 2 / 3 + 1), col)
                    x += w
            y += lh
        rl.end_scissor_mode()
        if sbw:
            tr = rl.Rectangle(rc.x + rc.width - sbw - 1, rc.y + 1, sbw, rc.height - 2)
            rl.draw_rectangle_rec(tr, rl.Color(240, 240, 240, 255))
            total = max(1, len(rows) * lh + m)
            if total > rc.height:
                th = max(12, tr.height * rc.height / total)
                ty = tr.y + (tr.height - th) * min(1, scroll / max(1, total - rc.height))
                rl.draw_rectangle_rec(rl.Rectangle(tr.x + 3, ty, sbw - 6, th), rl.Color(193, 193, 193, 255))

    def draw_selection(self, o, rc, rows, lh, m, scroll):
        """the focused field: its selection (blue) or a blinking caret, row by row as drawn"""
        rt = self.rt
        n = len(o.text)
        s, e = sorted(max(0, min(n, v)) for v in rt.sel)
        x0, y0 = rc.x + m / 2 + 2, rc.y + m / 2 - scroll
        caret_row = rt.row_of(o, s) if s == e else -1
        for r, (ln, a, b) in enumerate(rows):
            y = y0 + r * lh
            if s != e and s <= b and e >= a:
                ls, le = max(s, a), min(e, b)
                xa = x0 + rt.text_width(o, a, ls)
                xb = x0 + rt.text_width(o, a, le) + (4 if e > b else 0)
                if xb > xa:
                    rl.draw_rectangle(int(xa), int(y), int(xb - xa), int(lh), rl.Color(173, 214, 255, 255))
            if r == caret_row and (rl.get_time() % 1.0) < 0.6:
                xc = x0 + rt.text_width(o, a, s)
                rl.draw_line(int(xc), int(y + 1), int(xc), int(y + lh - 1), rl.BLACK)

    def draw_scrollbar(self, o):
        rc = self.rect(o)
        rl.draw_rectangle_rec(rc, rl.Color(230, 230, 230, 255))
        rl.draw_rectangle_lines_ex(rc, 1, rl.Color(180, 180, 180, 255))
        try:
            a = float(self.prop(o, 'startValue') or 0)
            b = float(self.prop(o, 'endValue') or 65535)
            v = float(self.prop(o, 'thumbPosition') or 0)
        except ValueError:
            return
        f = 0 if b == a else max(0.0, min(1.0, (v - a) / (b - a)))
        show = self.on(o, 'showValue')
        label = ('%d' % v) if v == int(v) else ('%.2f' % v)
        if rc.width >= rc.height:
            x = rc.x + f * (rc.width - 12)
            top = rc.y + (14 if show else 2)
            rl.draw_rectangle_rec(rl.Rectangle(x, top, 12, rc.height - (top - rc.y) - 2), rl.Color(120, 120, 120, 255))
            if show:                                  # the value above the thumb
                self.text(o, label, x + 6 - self.measure(o, label, 11) / 2, rc.y, rl.BLACK, 11)
        else:
            y = rc.y + f * (rc.height - 12)
            rl.draw_rectangle_rec(rl.Rectangle(rc.x + 2, y, rc.width - 4, 12), rl.Color(120, 120, 120, 255))
            if show:
                self.text(o, label, rc.x + rc.width + 2, y, rl.BLACK, 11)

    def pixel_texture(self, o):
        """an image whose imageData a script set: a texture of those pixels, made again only when the text
        changes (an xt3d view sets a new frame every tick). Text that does not fit the rect is not drawn."""
        data = o.imagedata
        w, h = int(o.rect[2] - o.rect[0]), int(o.rect[3] - o.rect[1])
        old = self.pixels.get(id(o))
        if old is not None and old[0] is data:
            return old[1]
        if w <= 0 or h <= 0 or len(data) != w * h * 4:
            return old[1] if old is not None else None
        src = data.encode('latin-1', 'replace')
        rgba = bytearray(w * h * 4)
        rgba[0::4], rgba[1::4], rgba[2::4] = src[1::4], src[2::4], src[3::4]
        alpha = getattr(o, 'alphadata', None)
        rgba[3::4] = alpha.encode('latin-1', 'replace') if alpha is not None and len(alpha) == w * h else b'\xff' * (w * h)
        tex = old[1] if old is not None and old[1].width == w and old[1].height == h else None
        if tex is None:
            if old is not None:
                rl.unload_texture(old[1])
            img = rl.gen_image_color(w, h, rl.BLACK)
            tex = rl.load_texture_from_image(img)
            rl.unload_image(img)
        rl.update_texture(tex, rl.ffi.cast('void *', rl.ffi.from_buffer(rgba)))
        self.pixels[id(o)] = (data, tex)
        return tex

    def texture(self, o):
        if getattr(o, 'imagedata', None) is not None:
            return self.pixel_texture(o)
        fn = str(self.prop(o, 'fileName') or '')
        if fn:                                    # set the fileName of image: the picture comes from that file
            full = self.rt.host.real_path(fn)
            if not os.path.isabs(full):
                full = os.path.join(self.rt.host.default_folder, full)
            if full not in self.textures:
                if len(self.textures) > 64:       # an image viewer goes through many files: keep the cache small
                    for k in [k for k in self.textures if k != full][:32]:
                        rl.unload_texture(self.textures.pop(k))
                self.textures[full] = rl.load_texture(full) if os.path.isfile(full) else None
            if self.textures[full] is not None and self.textures[full].id:
                return self.textures[full]
            return None
        path = o.node.get('asset')
        if not path:
            return None
        full = os.path.join(o.stack.folder, path)
        if full not in self.textures and os.path.exists(full):
            self.textures[full] = rl.load_texture(full)
        return self.textures.get(full)

    def icon_image(self, o):
        """the image a button's icon names (an id, or a name): this stack first, then the others"""
        v = str(self.prop(o, 'icon') or '').strip()
        if v in ('', '0') or self.prop(o, 'showIcon') in (False, 'false'):
            return None
        key = (id(o.stack), v)
        if key not in self.icons:
            found = None
            for st in [o.stack] + [s for s in self.rt.harvest.stacks if s is not o.stack]:
                for card in st.children:
                    for c in card.flat():
                        if c.type == 'image' and (str(c.props.get('id', getattr(c, 'id', ''))) == v or c.name == v):
                            found = c
                            break
                    if found:
                        break
                if found:
                    break
            self.icons[key] = found
        return self.icons[key]

    def draw_icon(self, o, rc):
        img = self.icon_image(o)
        tex = self.texture(img) if img is not None else None
        if tex is None:
            return False
        x, y = rc.x + (rc.width - tex.width) / 2, rc.y + (rc.height - tex.height) / 2
        rl.draw_texture(tex, int(x), int(y), rl.WHITE)
        return True

    def draw_image(self, o):
        rc = self.rect(o)
        dt = o.direct_tex if o.pixels_from is not None else None
        if dt is not None and self.scale > 1:     # a scaled window: the 2x frame xt3d made before shrinking it,
            dt = getattr(o, 'direct_big', None) or dt   # so the 3D is drawn sharp at the window's size (g1-03)
        if dt is not None:                        # an xt3d frame still on the graphics card: drawn as it is
            rl.draw_texture_pro(dt, rl.Rectangle(0, 0, dt.width, -dt.height), rc, rl.Vector2(0, 0), 0, rl.WHITE)
            return                                # (a render texture is upside down: the source is flipped)
        tex = self.texture(o)
        a = to_num(self.prop(o, 'angle') or 0) % 360
        un = getattr(o, 'unturned', None)
        if tex is not None and a and un:          # turned by a script: counterclockwise about the centre (measured)
            w, h = un[2] - un[0], un[3] - un[1]
            cx, cy = rc.x + rc.width / 2.0, rc.y + rc.height / 2.0
            rl.draw_texture_pro(tex, rl.Rectangle(0, 0, tex.width, tex.height), rl.Rectangle(cx, cy, w, h),
                                rl.Vector2(w / 2.0, h / 2.0), -a, rl.WHITE)
        elif tex is not None:
            rl.draw_texture_pro(tex, rl.Rectangle(0, 0, tex.width, tex.height), rc, rl.Vector2(0, 0), 0, rl.WHITE)
        else:
            rl.draw_rectangle_lines_ex(rc, 1, rl.Color(200, 200, 200, 255))

    def draw_other(self, o):
        rl.draw_rectangle_lines_ex(self.rect(o), 1, rl.Color(200, 200, 200, 255))

    # ------------------------------------------------------------ the runtime panel (ImGui)
    def draw_panel(self):
        rl.rl_draw_render_batch_active()
        imgui.backends.opengl3_new_frame()
        io = imgui.get_io()
        io.display_size = imgui.ImVec2(rl.get_screen_width(), rl.get_screen_height())
        io.delta_time = max(rl.get_frame_time(), 1 / 1000)
        m = rl.get_mouse_position()
        io.add_mouse_pos_event(m.x, m.y)
        io.add_mouse_button_event(0, rl.is_mouse_button_down(0))
        imgui.new_frame()
        rt = self.rt
        if self.dialog is not None:
            self.feed_keys(io)
        if self.panel and (rt.errors or rt.load_errors):
            imgui.set_next_window_size(imgui.ImVec2(360 * self.scale, 120 * self.scale), imgui.Cond_.first_use_ever)
            imgui.begin('Runtime  (F2 hides)')
            for msg, obj, err in rt.errors[-8:]:
                imgui.text_colored(imgui.ImVec4(1, 0.4, 0.4, 1), '%s in %s: %s' % (msg, obj, err))
            for a in rt.answers[-5:]:
                imgui.text('dialog: ' + a)
            for obj, err in rt.load_errors[:5]:
                imgui.text_colored(imgui.ImVec4(1, 0.7, 0.3, 1), 'does not compile: %s %s' % (obj, err))
            imgui.end()
        if self.menu is not None:
            self.draw_menu()                     # last, and focused: always in front of the panel
        if self.dialog is not None:
            self.draw_dialog()
        imgui.render()
        imgui.backends.opengl3_render_draw_data(imgui.get_draw_data())
        return io.want_capture_mouse

    # ------------------------------------------------------------ the loop
    def follow_stack_size(self):
        """a script set the stack's size (the Library: set the width of me to 960): the window follows"""
        st = self.rt.default_stack
        try:
            w, h = int(st.width), int(st.height)
        except (TypeError, ValueError):
            return
        if w > 0 and h > 0 and (w, h) != self.base_size:
            self.base_size = (w, h)
            rl.set_window_size(*self.scaled_size())
            self.cache_dirty = True

    def frame(self):
        rt = self.rt
        busy = False
        self.follow_stack_size()
        rl.begin_drawing()
        if self.idling and rt.focused is None:    # nothing happening: the last picture of the card, not a redraw
            self.draw_cached_card()               # (a focused field keeps drawing: its caret blinks)
        else:
            self.draw_card()
        busy = self.draw_panel()
        rl.end_drawing()
        self.after_frame()
        esc_mine = self.esc_frees and rt.focused is None   # play mode: Escape is the View's, not the game's
        if esc_mine and rl.is_key_pressed(rl.KEY_ESCAPE):  # (typing in a field, e.g. GameNotes: the script's)
            if self.fronts_take(65307):           # a front script took it first (GameNotes closing its box)
                if hasattr(rt, 'log_clicks'):
                    rt.log_clicks.append('key escape (taken by a front script)')
            else:
                self.freed = not self.freed
                if hasattr(rt, 'log_clicks'):
                    rt.log_clicks.append('key escape (%s)' % ('mouse and keys freed' if self.freed else 'back to the game'))
                self.capture()
        if self.freed:                            # the game gets no mouse moves, clicks or keys; it plays on
            rt.keys_down, rt.held_codes, rt.buttons_down = set(), list(rt.test_keys), set()
            rt.mouse_move(int(self.vmouse[0]), int(self.vmouse[1]))   # where the game last put it: no turning
            if rl.is_key_pressed(rl.KEY_F2):
                self.panel = not self.panel
            rt.tick(min(rl.get_frame_time() * 1000, 100), budget=0.02)
            return
        self.capture()                            # a grab the scripts asked for last frame starts before they read
        if self.captured:                         # a mouse-look game: only the movement counts (see capture())
            d, m = rl.get_mouse_delta(), rl.get_mouse_position()
            dx, dy = (0, 0) if self.soft_grab else (d.x, d.y)
            if dx == 0 and dy == 0:               # WSL may give no movement for a grabbed mouse: use the pointer
                dx, dy = m.x - self.last_real[0], m.y - self.last_real[1]
            if self.soft_grab:
                if self.settle > 0:               # just moved back: measure from where the pointer really is
                    self.settle -= 1
                    dx = dy = 0
                    if self.settle == 0:          # did it get there? three refusals in a row: stop asking
                        w, h = rl.get_screen_width(), rl.get_screen_height()
                        if abs(m.x - w // 2) > w // 3 or abs(m.y - h // 2) > h // 3:
                            self.look['recentre failed'] += 1
                            self.refused = getattr(self, 'refused', 0) + 1
                            if self.refused >= 3:
                                self.recentre = False
                        else:
                            self.refused = 0
                dx, dy = max(-40, min(40, dx)), max(-40, min(40, dy))     # one bad reading can't spin the view
                dx, dy = dx * self.look_speed, dy * self.look_speed
            self.look['frames grabbed'] += 1
            self.look['moved x'] += abs(dx)
            self.look['moved y'] += abs(dy)
            self.last_real = (m.x, m.y)
            if self.soft_grab and self.recentre and self.settle == 0:   # near the edge: back to the middle
                w, h = rl.get_screen_width(), rl.get_screen_height()
                e = min(w, h) // 6
                if not (e < m.x < w - e and e < m.y < h - e):
                    rl.set_mouse_position(w // 2, h // 2)
                    self.settle = 2
                    self.look['moved back'] = self.look.get('moved back', 0) + 1
            self.vmouse = (self.vmouse[0] + dx, self.vmouse[1] + dy)
            x, y = int(self.vmouse[0]), int(self.vmouse[1])
        else:
            mx, my = self.mouse_units()
            x, y = int(mx), int(my)
        rt.buttons_down = {b for b, k in (('2', 2), ('3', 1)) if rl.is_mouse_button_down(k)}   # mouse(3) = right
        if rl.is_mouse_button_pressed(1):
            self.look['right presses'] += 1
        rt.mouse_move(x, y)
        if not busy:
            if rl.is_mouse_button_pressed(0):
                self.down_on = rt.mouse_down(x, y)
            if rl.is_mouse_button_released(0):
                rt.mouse_up(x, y, down_on=self.down_on)
                self.down_on = None
            for k, b in ((1, 3), (2, 2)):          # right = mouseDown 3, middle = 2 (Priority Tube's bubble menu)
                if rl.is_mouse_button_pressed(k):
                    self.other_down[b] = rt.mouse_down(x, y, b)
                if rl.is_mouse_button_released(k):
                    rt.mouse_up(x, y, b, down_on=self.other_down.pop(b, None))
        held = set()
        for key, name in ((rl.KEY_LEFT_SHIFT, 'shiftkey'), (rl.KEY_RIGHT_SHIFT, 'shiftkey'), (rl.KEY_LEFT_ALT, 'optionkey'),
                          (rl.KEY_LEFT_CONTROL, 'controlkey'), (rl.KEY_RIGHT_CONTROL, 'controlkey')):
            if rl.is_key_down(key):
                held.add(name)
        rt.keys_down = held | ({'altkey'} if 'optionkey' in held else set())
        rt.held_codes = [code for key, code in self.KEYCODES if rl.is_key_down(key)
                         and not (code == 65307 and esc_mine)] + list(rt.test_keys)   # the keysDown
                                                   # (test_keys: keys a check tool holds down, tools/xt3d_game_check.py)
        taken = set()                              # rawKeyDown not passed: LiveCode sends no keyDown for it
        for key, code in self.KEYCODES:            # rawKeyDown (Raycasting_101: Esc / ` free the mouse)
            if rl.is_key_pressed(key):
                if code == 65307:
                    if esc_mine:                  # play mode: Escape belongs to the View (above)
                        continue
                    if hasattr(rt, 'log_clicks'):
                        rt.log_clicks.append('key escape')
                if rt.raw_key(code) and code < 128:
                    taken.add(code)
        self.capture()
        if rl.is_key_pressed(rl.KEY_F2):
            self.panel = not self.panel
        if 'controlkey' in held:                  # Ctrl + / Ctrl - / Ctrl 0: our scaleFactor (x1-00)
            if rl.is_key_pressed(rl.KEY_EQUAL) or rl.is_key_pressed(rl.KEY_KP_ADD):
                self.set_scale(self.scale + SCALE_STEP)
            elif rl.is_key_pressed(rl.KEY_MINUS) or rl.is_key_pressed(rl.KEY_KP_SUBTRACT):
                self.set_scale(self.scale - SCALE_STEP)
            elif rl.is_key_pressed(rl.KEY_ZERO) or rl.is_key_pressed(rl.KEY_KP_0):
                self.set_scale(windows_scale())
        ch = rl.get_char_pressed()
        while ch:
            if ch < 128 and ord(chr(ch).lower()) in taken:   # its rawKeyDown was taken (GameNotes' `: the
                taken.discard(ord(chr(ch).lower()))           # box opens, no ` typed into it)
            elif 'controlkey' not in held:        # Control + a letter is a command key (below), not typing
                rt.key(chr(ch))
            ch = rl.get_char_pressed()
        if 'controlkey' in held:
            for k in range(rl.KEY_A, rl.KEY_Z + 1):
                if rl.is_key_pressed(k):
                    rt.control_key(chr(ord('a') + k - rl.KEY_A))
        for k, name in self.SPECIAL_KEYS:
            if rl.is_key_pressed(k) or rl.is_key_pressed_repeat(k):
                rt.special_key(name)
        wheel = rl.get_mouse_wheel_move()
        if wheel and not busy:
            o = rt.control_at(x, y)
            if not rt.wheel(o, wheel) and o is not None and o.type == 'field':
                rt.scroll_field(o, -wheel * rt.field_metrics(o)[1] * 3)
        rt.tick(min(rl.get_frame_time() * 1000, 100), budget=0.02)   # at most 20 ms of messages a frame

    def draw_menu(self):
        """the menu as a borderless window at x,y; submenus are ImGui menus. A click outside closes it,
        once the mouse has been up (the click that opened it does not count)"""
        m = self.menu
        if not imgui.is_mouse_down(0):
            m['armed'] = True
        imgui.set_next_window_pos(imgui.ImVec2(m['x'] * self.scale, m['y'] * self.scale), imgui.Cond_.always)
        if not m.get('focused'):                 # focus once: focusing every frame closes any open submenu
            imgui.set_next_window_focus()
            m['focused'] = True
        flags = (imgui.WindowFlags_.no_title_bar | imgui.WindowFlags_.always_auto_resize | imgui.WindowFlags_.no_move
                 | imgui.WindowFlags_.no_saved_settings | imgui.WindowFlags_.no_collapse)
        imgui.begin('##xtmenu', None, flags)
        self.menu_level(m['items'], 0)
        imgui.end()
        if m.get('armed') and imgui.is_mouse_clicked(0) and not imgui.get_io().want_capture_mouse:
            m['done'] = True                     # a click outside the menu: closed, no pick
        if rl.is_key_pressed(rl.KEY_ESCAPE):
            m['done'] = True

    def menu_level(self, items, depth):
        """draw the items of one menu level; an item with deeper items after it opens them as a submenu"""
        m, i = self.menu, 0
        while i < len(items):
            label, pick, enabled, d = items[i]
            j = i + 1
            while j < len(items) and items[j][3] > depth:
                j += 1
            kids = items[i + 1:j]
            if label == '-':
                imgui.separator()
            elif kids:
                if imgui.begin_menu(label + '##%d' % i, enabled):
                    self.menu_level(kids, depth + 1)
                    imgui.end_menu()
            elif imgui.menu_item(label + '##%d' % i, '', False, enabled)[0]:
                m['pick'] = pick
            i = j

    def menu_frames(self, items, x, y):
        """a script shows a menu: draw until a pick or the menu closes (the handler waits)"""
        self.wake()
        self.menu = {'items': items, 'x': x, 'y': y, 'pick': None, 'done': False}
        try:
            while not self.should_close() and self.menu['pick'] is None and not self.menu['done']:
                rl.begin_drawing()
                self.draw_card()
                self.draw_panel()
                rl.end_drawing()
                self.after_frame()
            return self.menu['pick']
        finally:
            self.menu = None
            # the click on the menu was taken inside this loop: if the button is up now, the release the
            # runtime waited for will never come (it would eat the next click's mouseUp)
            if not rl.is_mouse_button_down(0):
                self.rt.swallow_up = False
                self.rt.button_down = False
                self.rt.pressed = None
                self.down_on = None

    KEYS = None
    SPECIAL_KEYS = [(rl.KEY_BACKSPACE, 'backspace'), (rl.KEY_DELETE, 'delete'), (rl.KEY_ENTER, 'return'),
                    (rl.KEY_KP_ENTER, 'enter'), (rl.KEY_LEFT, 'left'), (rl.KEY_RIGHT, 'right'), (rl.KEY_UP, 'up'),
                    (rl.KEY_DOWN, 'down'), (rl.KEY_TAB, 'tab'), (rl.KEY_HOME, 'home'), (rl.KEY_END, 'end')]

    def feed_keys(self, io):
        """typing goes to ImGui while a dialog is up (characters, and the keys a text box needs)"""
        if View.KEYS is None:
            View.KEYS = [(rl.KEY_BACKSPACE, imgui.Key.backspace), (rl.KEY_DELETE, imgui.Key.delete),
                         (rl.KEY_ENTER, imgui.Key.enter), (rl.KEY_KP_ENTER, imgui.Key.keypad_enter),
                         (rl.KEY_ESCAPE, imgui.Key.escape), (rl.KEY_LEFT, imgui.Key.left_arrow),
                         (rl.KEY_RIGHT, imgui.Key.right_arrow), (rl.KEY_HOME, imgui.Key.home),
                         (rl.KEY_END, imgui.Key.end), (rl.KEY_TAB, imgui.Key.tab),
                         (rl.KEY_LEFT_CONTROL, imgui.Key.left_ctrl), (rl.KEY_LEFT_SHIFT, imgui.Key.left_shift),
                         (rl.KEY_A, imgui.Key.a), (rl.KEY_C, imgui.Key.c), (rl.KEY_V, imgui.Key.v), (rl.KEY_X, imgui.Key.x)]
        for rk, ik in View.KEYS:
            io.add_key_event(ik, rl.is_key_down(rk))
        io.add_key_event(imgui.Key.mod_ctrl, rl.is_key_down(rl.KEY_LEFT_CONTROL) or rl.is_key_down(rl.KEY_RIGHT_CONTROL))
        io.add_key_event(imgui.Key.mod_shift, rl.is_key_down(rl.KEY_LEFT_SHIFT) or rl.is_key_down(rl.KEY_RIGHT_SHIFT))
        ch = rl.get_char_pressed()
        while ch:
            io.add_input_character(ch)
            ch = rl.get_char_pressed()

    def draw_dialog(self):
        """answer: the prompt and its buttons (the last is the default: Return); ask: a text box, OK, Cancel
        (Escape); file/folder: a path in the stack's files folder"""
        d = self.dialog
        imgui.set_next_window_pos(imgui.ImVec2(rl.get_screen_width() / 2, rl.get_screen_height() / 3),
                                  imgui.Cond_.always, imgui.ImVec2(0.5, 0.5))
        imgui.set_next_window_focus()
        flags = (imgui.WindowFlags_.no_collapse | imgui.WindowFlags_.always_auto_resize | imgui.WindowFlags_.no_move
                 | imgui.WindowFlags_.no_saved_settings)
        imgui.begin((d['title'] or ' ') + '##xtdialog', None, flags)
        if d['icon']:
            col = {'error': (1, 0.4, 0.4, 1), 'warning': (1, 0.8, 0.3, 1)}.get(d['icon'], (0.5, 0.8, 1, 1))
            imgui.text_colored(imgui.ImVec4(*col), d['icon'].upper())
        imgui.push_text_wrap_pos(420 * self.scale)
        imgui.text_unformatted(d['prompt'])
        imgui.pop_text_wrap_pos()
        if d['typing']:
            if not d['focused']:
                imgui.set_keyboard_focus_here()
                d['focused'] = True
            fl = imgui.InputTextFlags_.password if d['sub'] == 'password' else 0
            imgui.set_next_item_width(380 * self.scale)
            _, d['text'] = imgui.input_text('##xtinput', d['text'], fl)
            if d['sub'] in ('file', 'files', 'folder', 'folders'):
                self.draw_browser(d)
        for i, b in enumerate(d['buttons']):
            if i:
                imgui.same_line()
            if imgui.button(b + '##b%d' % i):
                d['done'] = b
        imgui.end()
        if d['done'] is None and (imgui.is_key_pressed(imgui.Key.enter) or imgui.is_key_pressed(imgui.Key.keypad_enter)):
            d['done'] = d['buttons'][-1]
        if d['done'] is None and d['typing'] and imgui.is_key_pressed(imgui.Key.escape):
            d['done'] = 'Cancel'

    def draw_browser(self, d):
        """answer folder / file: the folders (and files) where the path points; a click goes in or picks"""
        here = d['text'].rstrip('/') or '/'
        if not os.path.isdir(here):
            here = os.path.dirname(here) or '/'
        try:
            names = sorted(os.listdir(here), key=str.lower)
        except OSError:
            names = []
        dirs = [n for n in names if not n.startswith('.') and os.path.isdir(os.path.join(here, n))]
        files = [] if d['sub'].startswith('folder') else [n for n in names if os.path.isfile(os.path.join(here, n))]
        imgui.begin_child('##xtbrowse', imgui.ImVec2(380 * self.scale, 260 * self.scale), imgui.ChildFlags_.borders)
        if imgui.selectable('..##up', False)[0]:
            d['text'] = (os.path.dirname(here) or '/') + '/'
        for n in dirs:
            if imgui.selectable('[%s]##d%s' % (n, n), False)[0]:
                d['text'] = os.path.join(here, n) + '/'
        for n in files:
            if imgui.selectable(n + '##f' + n, d['text'] == os.path.join(here, n))[0]:
                d['text'] = os.path.join(here, n)
        imgui.end_child()

    def dialog_frames(self, kind, sub, icon, prompt, extra, title):
        """a script shows answer/ask: draw until a button is clicked (the handler waits) -> (it, the result)"""
        self.wake()
        typing = kind == 'ask' or sub in ('file', 'files', 'folder', 'folders')
        text = ''
        if kind == 'ask' and extra and not sub:
            text = extra[0]
        if sub in ('file', 'files', 'folder', 'folders'):
            text = self.rt.host.folders['documents'] + '/'
            if extra and self.rt.real_folders:       # answer folder "..." with "<where to start>"
                start = self.rt.host.real_path(extra[0])
                if os.path.isdir(start):
                    text = start.rstrip('/') + '/'
        buttons = (extra or ['OK']) if (kind == 'answer' and not sub) else ['Cancel', 'OK']
        self.dialog = {'kind': kind, 'sub': sub, 'icon': icon, 'prompt': prompt, 'title': title, 'typing': typing,
                       'text': text, 'buttons': buttons, 'done': None, 'focused': False}
        try:
            while not self.should_close() and self.dialog['done'] is None:
                rl.begin_drawing()
                self.draw_card()
                self.draw_panel()
                rl.end_drawing()
                self.after_frame()
            done, text = self.dialog['done'], self.dialog['text']
        finally:
            self.dialog = None
        if done is None:                          # the window closed while the dialog was up
            return '', 'cancel'
        if kind == 'answer' and not sub:
            return done, ''
        if done == 'Cancel':
            return '', 'cancel'
        if sub in ('file', 'files', 'folder', 'folders'):
            if self.rt.real_folders:                  # a real folder: the real path (real_app also writes there)
                return (text.rstrip('/') if sub.startswith('folder') else text) or '/', ''
            return self.rt.host.sandboxed(text), ''
        return text, ''

    def wait_frames(self, ms):
        """a script waits: keep drawing (no clicks or timers, as LiveCode's wait without messages)"""
        self.wake()
        end = rl.get_time() + ms / 1000.0
        while rl.get_time() < end and not self.should_close():
            rl.begin_drawing()
            self.draw_card()
            self.draw_panel()
            rl.end_drawing()
            self.after_frame()

    def after_frame(self):
        """after every drawn frame (the main loop, waits, menus, dialogs): a close-box click in play mode ends
        the program at once, whatever the scripts are doing (the owner, 25 Nov: the close box is absolute)"""
        self.should_close()

    def should_close(self):
        """the close box was clicked; in play mode (on_close) the program ends here and never returns"""
        c = rl.window_should_close()
        if c and self.on_close is not None:
            cb, self.on_close = self.on_close, None
            cb()
        return c

    idling = False
    sleeping = False
    card_cache = None

    def wake(self):
        """a wait, menu or dialog loop starts: frames must keep coming even with no input"""
        if self.sleeping:
            self.sleeping = False
            rl.disable_event_waiting()

    def draw_cached_card(self):
        """the card from a picture made once when the window went idle (and again if the window's size changed)"""
        w, h = rl.get_screen_width(), rl.get_screen_height()
        c = self.card_cache
        if c is None or (c.texture.width, c.texture.height) != (w, h) or self.cache_dirty:
            if c is None or (c.texture.width, c.texture.height) != (w, h):
                if c is not None:
                    rl.unload_render_texture(c)
                c = self.card_cache = rl.load_render_texture(w, h)
            rl.end_drawing()                      # drawing into the picture happens outside the window's frame
            rl.begin_texture_mode(c)
            rl.clear_background(rl.BLANK)
            self.draw_card()
            rl.end_texture_mode()
            rl.begin_drawing()
            self.cache_dirty = False
        rl.rl_set_blend_factors(1, 0, 0x8006)     # copied as it is (GL ONE, ZERO, ADD): blending it again would
        rl.begin_blend_mode(rl.BLEND_CUSTOM)      # darken soft edges, whose alpha the picture keeps
        rl.draw_texture_rec(c.texture, rl.Rectangle(0, 0, w, -h), rl.Vector2(0, 0), rl.WHITE)
        rl.end_blend_mode()

    IDLE_AFTER = 0.5          # seconds with nothing happening before the window slows down
    IDLE_FPS = 10             # frames a second while idle: a click or key is seen within 0.1 s, then back to 60

    def active(self):
        """did anything happen this frame that wants smooth drawing: the mouse moved, a button or key, the
        wheel, a script changed an object, a `send ... in` due soon, a mouse-look game"""
        rt = self.rt
        changed, rt.changed = getattr(rt, 'changed', False), False
        if changed or self.captured or rt.held_codes or rt.keys_down or rt.button_down:
            return True
        d = rl.get_mouse_delta()
        if d.x or d.y or rl.get_mouse_wheel_move() or rl.get_key_pressed() or rl.is_window_resized():
            return True
        if any(rl.is_mouse_button_down(b) for b in (0, 1, 2)):
            return True
        return bool(rt.timers) and rt.timers[0][0] - rt.clock < 250

    def run(self):
        self.rt.on_wait = self.wait_frames
        self.rt.on_menu = self.menu_frames
        self.rt.on_dialog = self.dialog_frames
        self.rt.open()
        last_active, fps = time.perf_counter(), 60
        while not self.should_close() and not self.rt.closed:
            self.frame()
            now = time.perf_counter()
            if self.active():
                last_active = now
            want = 60 if now - last_active < self.IDLE_AFTER else self.IDLE_FPS
            if want != fps:                       # nothing happening: fewer frames (owner 26 Nov: CPU while idle)
                fps = want
                rl.set_target_fps(fps)
                self.idling = fps == self.IDLE_FPS
                self.cache_dirty = True           # going idle: one fresh picture; back to work: drawn each frame
            # idle with no `send ... in` waiting: sleep until the mouse, a key, the close box or the window
            # system wakes it (nothing else can make a script run); else the frames go on
            sleep = self.idling and not self.rt.timers and not self.cache_dirty and self.rt.focused is None   # (a caret blinks)
            if sleep != self.sleeping:
                self.sleeping = sleep
                (rl.enable_event_waiting if sleep else rl.disable_event_waiting)()
        self.rt.close_stack()
        self.close()

    def snapshot(self, path, frames=2):
        self.follow_stack_size()
        for _ in range(frames):
            rl.begin_drawing()
            self.draw_card()
            self.draw_panel()
            if _ == frames - 1:
                img = rl.load_image_from_screen()
                rl.export_image(img, path)
                rl.unload_image(img)
            rl.end_drawing()

    def close(self):
        imgui.backends.opengl3_shutdown()
        imgui.destroy_context()
        rl.close_window()
