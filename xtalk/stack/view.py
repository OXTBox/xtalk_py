"""The stack window: raylib draws the card, ImGui the runtime panel (errors, answers). Needs .venv.

    .venv/bin/python -I tools/open_stack.py ~/projects/XTJSON/Game_card_reader_11_13_2025

Drawn: card colour; graphics (rectangle, roundrect, oval, line, polygon, curve, regular) with fill,
border and label; buttons (standard, rectangle, roundrect, transparent, checkbox, radio, menu kinds as
a plain button); fields (plain text, scroll, list hilite); scrollbars (track + thumb); images from the
harvest's assets. NOT drawn yet: styled text (htmlText), players, widgets, gradients, ink effects.
"""
import math, os
import pyray as rl
from imgui_bundle import imgui
from .host import canon

FONT_DIRS = ['/mnt/c/Windows/Fonts', '/usr/share/fonts/truetype/dejavu']
FONT_FILES = {'segoe ui': 'segoeui.ttf', 'arial': 'arial.ttf', 'consolas': 'consola.ttf', '': 'segoeui.ttf'}
NAMES = {'white': (255, 255, 255), 'black': (0, 0, 0), 'red': (255, 0, 0), 'green': (0, 255, 0),
         'blue': (0, 0, 255), 'yellow': (255, 255, 0), 'gray': (190, 190, 190), 'grey': (190, 190, 190),
         'darkgray': (169, 169, 169), 'lightgray': (211, 211, 211), 'orange': (255, 165, 0), 'cyan': (0, 255, 255),
         'magenta': (255, 0, 255), 'purple': (160, 32, 240), 'brown': (165, 42, 42), 'pink': (255, 192, 203)}


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
    def __init__(self, rt, hidden=False, pos=(200, 32)):
        self.rt = rt
        st = rt.default_stack
        w, h = st.size if st.size else (st.width, st.height)
        rl.set_trace_log_level(rl.LOG_WARNING)
        if hidden:
            rl.set_config_flags(rl.FLAG_WINDOW_HIDDEN)
        rl.init_window(int(w), int(h), st.props.get('title') or st.name)
        if not hidden:
            rl.set_window_position(*pos)
        rl.set_exit_key(0)
        rl.set_target_fps(60)
        self.fonts = {}
        self.textures = {}
        self.icons = {}                # (stack, icon value) -> the image it names
        self.menu = None               # a menu being shown: {'items', 'x', 'y', 'pick', 'opened', 'done'}
        self.dialog = None             # an answer/ask being shown
        self.down_on = None
        self.panel = True
        imgui.create_context()
        imgui.get_io().set_ini_filename('')
        imgui.backends.opengl3_init('#version 330')

    # ------------------------------------------------------------ helpers
    def font(self, o, size):
        name = (self.prop(o, 'textfont') or self.inherit(o, 'textFont') or '').lower()
        f = FONT_FILES.get(name, 'segoeui.ttf')
        if 'bold' in str(self.prop(o, 'textstyle') or self.inherit(o, 'textStyle') or '').lower():
            f = {'segoeui.ttf': 'segoeuib.ttf', 'arial.ttf': 'arialbd.ttf', 'consola.ttf': 'consolab.ttf'}.get(f, f)
        key = (f, size)
        if key not in self.fonts:
            path = next((os.path.join(d, f) for d in FONT_DIRS if os.path.exists(os.path.join(d, f))), None)
            self.fonts[key] = rl.load_font_ex(path, size * 2, None, 0) if path else rl.get_font_default()
            rl.set_texture_filter(self.fonts[key].texture, rl.TEXTURE_FILTER_BILINEAR)
        return self.fonts[key]

    def inherit(self, o, key):
        """a text or colour property: the object, its groups, card, stack, then the stack's effective value"""
        k = canon(key)
        x = o
        while x is not None:
            for pk, v in x.props.items():
                if canon(pk) == k and v != '':
                    return v
            x = x.parent if x.type != 'card' else x.stack
            if x is not None and x.type == 'stack':
                for pk, v in x.props.items():
                    if canon(pk) == k and v != '':
                        return v
                return next((v for ek, v in x.effective.items() if canon(ek) == k), None)
        return None

    def size(self, o):
        try:
            return int(float(self.inherit(o, 'textSize') or 12))
        except ValueError:
            return 12

    def text(self, o, s, x, y, col, size=None):
        size = size or self.size(o)
        f = self.font(o, size)
        rl.draw_text_ex(f, s, rl.Vector2(x, y), size * 4 / 3, 0, col)

    def measure(self, o, s, size=None):
        size = size or self.size(o)
        return rl.measure_text_ex(self.font(o, size), s, size * 4 / 3, 0).x

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
        for o in card.flat():
            if o.type == 'group' or not self.rt._shown(o):
                continue
            getattr(self, 'draw_' + o.type, self.draw_other)(o)

    def rect(self, o):
        l, t, r, b = o.rect
        return rl.Rectangle(l, t, r - l, b - t)

    def draw_graphic(self, o):
        style = self.prop(o, 'style') or 'rectangle'
        fill = colour(self.inherit(o, 'backgroundColor'), rl.Color(240, 240, 240, 255))
        line = colour(self.inherit(o, 'foregroundColor'), rl.BLACK)
        lw = max(1, int(float(self.prop(o, 'lineSize') or 1)))
        filled = self.on(o, 'filled') or self.on(o, 'opaque')
        rc = self.rect(o)
        if style in ('rectangle', 'roundrect'):
            if style == 'roundrect':
                rnd = min(1.0, 20.0 / max(1, min(rc.width, rc.height)))
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
            run = []
            for p in pts + [None]:
                if p is None:
                    for a, b in zip(run, run[1:]):
                        rl.draw_line_ex(rl.Vector2(*a), rl.Vector2(*b), lw, line)
                    run = []
                else:
                    run.append(p)
        elif style == 'regular':
            n = int(float(self.prop(o, 'polySides') or 4))
            cx, cy = rc.x + rc.width / 2, rc.y + rc.height / 2
            rl.draw_poly_lines_ex(rl.Vector2(cx, cy), n, min(rc.width, rc.height) / 2, 0, lw, line)
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
            rl.draw_rectangle_rec(rc, colour(self.inherit(o, 'backgroundColor'), rl.WHITE)
                                  if o.props.get('backgroundColor') not in (None, '') else rl.WHITE)
        if self.on(o, 'showBorder'):
            rl.draw_rectangle_lines_ex(rc, 1, colour(self.inherit(o, 'borderColor'), rl.Color(130, 135, 144, 255)))
        size, lh, m, scroll, sbw = self.rt.field_metrics(o)    # one rule for drawing and for clicks
        lines = o.text.split('\n')
        hl = set(self.rt.host.hilited_lines(o))
        rl.begin_scissor_mode(int(rc.x + 1), int(rc.y + 1), int(rc.width - 2 - sbw), int(rc.height - 2))
        fg = colour(self.inherit(o, 'foregroundColor'), rl.BLACK)
        y = rc.y + m / 2 - scroll
        for i, s in enumerate(lines, 1):
            if y > rc.y + rc.height:
                break
            if y + lh >= rc.y:
                if i in hl:
                    rl.draw_rectangle(int(rc.x + 1), int(y), int(rc.width - 2 - sbw), int(lh), rl.Color(0, 120, 215, 255))
                self.text(o, s, rc.x + m / 2 + 2, y, rl.WHITE if i in hl else fg, size)
            y += lh
        rl.end_scissor_mode()
        if sbw:
            tr = rl.Rectangle(rc.x + rc.width - sbw - 1, rc.y + 1, sbw, rc.height - 2)
            rl.draw_rectangle_rec(tr, rl.Color(240, 240, 240, 255))
            total = max(1, len(lines) * lh + m)
            if total > rc.height:
                th = max(12, tr.height * rc.height / total)
                ty = tr.y + (tr.height - th) * min(1, scroll / max(1, total - rc.height))
                rl.draw_rectangle_rec(rl.Rectangle(tr.x + 3, ty, sbw - 6, th), rl.Color(193, 193, 193, 255))

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
        if rc.width >= rc.height:
            x = rc.x + f * (rc.width - 12)
            rl.draw_rectangle_rec(rl.Rectangle(x, rc.y + 2, 12, rc.height - 4), rl.Color(120, 120, 120, 255))
        else:
            y = rc.y + f * (rc.height - 12)
            rl.draw_rectangle_rec(rl.Rectangle(rc.x + 2, y, rc.width - 4, 12), rl.Color(120, 120, 120, 255))

    def texture(self, o):
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
        tex = self.texture(o)
        rc = self.rect(o)
        if tex is not None:
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
            imgui.set_next_window_size(imgui.ImVec2(360, 120), imgui.Cond_.first_use_ever)
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
    def frame(self):
        rt = self.rt
        busy = False
        rl.begin_drawing()
        self.draw_card()
        busy = self.draw_panel()
        rl.end_drawing()
        m = rl.get_mouse_position()
        x, y = int(m.x), int(m.y)
        rt.mouse_move(x, y)
        if not busy:
            if rl.is_mouse_button_pressed(0):
                self.down_on = rt.mouse_down(x, y)
            if rl.is_mouse_button_released(0):
                rt.mouse_up(x, y, down_on=self.down_on)
                self.down_on = None
        held = set()
        for key, name in ((rl.KEY_LEFT_SHIFT, 'shiftkey'), (rl.KEY_RIGHT_SHIFT, 'shiftkey'), (rl.KEY_LEFT_ALT, 'optionkey'),
                          (rl.KEY_LEFT_CONTROL, 'controlkey'), (rl.KEY_RIGHT_CONTROL, 'controlkey')):
            if rl.is_key_down(key):
                held.add(name)
        rt.keys_down = held | ({'altkey'} if 'optionkey' in held else set())
        if rl.is_key_pressed(rl.KEY_F2):
            self.panel = not self.panel
        ch = rl.get_char_pressed()
        while ch:
            rt.key(chr(ch))
            ch = rl.get_char_pressed()
        wheel = rl.get_mouse_wheel_move()
        if wheel and not busy:
            o = rt.control_at(x, y)
            if o is not None and o.type == 'field':
                rt.scroll_field(o, -wheel * rt.field_metrics(o)[1] * 3)
        rt.tick(rl.get_frame_time() * 1000)

    def draw_menu(self):
        """the menu as a borderless window at x,y; submenus are ImGui menus. A click outside closes it,
        once the mouse has been up (the click that opened it does not count)"""
        m = self.menu
        if not imgui.is_mouse_down(0):
            m['armed'] = True
        imgui.set_next_window_pos(imgui.ImVec2(m['x'], m['y']), imgui.Cond_.always)
        imgui.set_next_window_focus()
        flags = (imgui.WindowFlags_.no_title_bar | imgui.WindowFlags_.always_auto_resize | imgui.WindowFlags_.no_move
                 | imgui.WindowFlags_.no_saved_settings | imgui.WindowFlags_.no_collapse)
        imgui.begin('##xtmenu', None, flags)
        items, i = m['items'], 0
        while i < len(items):
            label, pick, enabled, sub = items[i]
            kids = []
            while i + 1 + len(kids) < len(items) and items[i + 1 + len(kids)][3]:
                kids.append(items[i + 1 + len(kids)])
            if label == '-':
                imgui.separator()
            elif kids:
                if imgui.begin_menu(label, enabled):
                    for kl, kp, ke, _ in kids:
                        if kl == '-':
                            imgui.separator()
                        elif imgui.menu_item(kl, '', False, ke)[0]:
                            m['pick'] = kp
                    imgui.end_menu()
            elif imgui.menu_item(label, '', False, enabled)[0]:
                m['pick'] = pick
            i += 1 + len(kids)
        imgui.end()
        if m.get('armed') and imgui.is_mouse_clicked(0) and not imgui.get_io().want_capture_mouse:
            m['done'] = True                     # a click outside the menu: closed, no pick
        if rl.is_key_pressed(rl.KEY_ESCAPE):
            m['done'] = True

    def menu_frames(self, items, x, y):
        """a script shows a menu: draw until a pick or the menu closes (the handler waits)"""
        self.menu = {'items': items, 'x': x, 'y': y, 'pick': None, 'done': False}
        try:
            while not rl.window_should_close() and self.menu['pick'] is None and not self.menu['done']:
                rl.begin_drawing()
                self.draw_card()
                self.draw_panel()
                rl.end_drawing()
            return self.menu['pick']
        finally:
            self.menu = None

    KEYS = None

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
        imgui.push_text_wrap_pos(420)
        imgui.text_unformatted(d['prompt'])
        imgui.pop_text_wrap_pos()
        if d['typing']:
            if not d['focused']:
                imgui.set_keyboard_focus_here()
                d['focused'] = True
            fl = imgui.InputTextFlags_.password if d['sub'] == 'password' else 0
            imgui.set_next_item_width(380)
            _, d['text'] = imgui.input_text('##xtinput', d['text'], fl)
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

    def dialog_frames(self, kind, sub, icon, prompt, extra, title):
        """a script shows answer/ask: draw until a button is clicked (the handler waits) -> (it, the result)"""
        typing = kind == 'ask' or sub in ('file', 'files', 'folder', 'folders')
        text = ''
        if kind == 'ask' and extra and not sub:
            text = extra[0]
        if sub in ('file', 'files', 'folder', 'folders'):
            text = self.rt.host.folders['documents'] + '/'
        buttons = (extra or ['OK']) if (kind == 'answer' and not sub) else ['Cancel', 'OK']
        self.dialog = {'kind': kind, 'sub': sub, 'icon': icon, 'prompt': prompt, 'title': title, 'typing': typing,
                       'text': text, 'buttons': buttons, 'done': None, 'focused': False}
        try:
            while not rl.window_should_close() and self.dialog['done'] is None:
                rl.begin_drawing()
                self.draw_card()
                self.draw_panel()
                rl.end_drawing()
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
            return self.rt.host.sandboxed(text), ''
        return text, ''

    def wait_frames(self, ms):
        """a script waits: keep drawing (no clicks or timers, as LiveCode's wait without messages)"""
        end = rl.get_time() + ms / 1000.0
        while rl.get_time() < end and not rl.window_should_close():
            rl.begin_drawing()
            self.draw_card()
            self.draw_panel()
            rl.end_drawing()

    def run(self):
        self.rt.on_wait = self.wait_frames
        self.rt.on_menu = self.menu_frames
        self.rt.on_dialog = self.dialog_frames
        self.rt.open()
        while not rl.window_should_close() and not self.rt.closed:
            self.frame()
        self.close()

    def snapshot(self, path, frames=2):
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
