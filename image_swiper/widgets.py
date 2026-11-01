"""Canvas-drawn controls: buttons, a segmented control and a switch.

Tk's native buttons cannot round corners or antialias, so these draw Pillow
images onto a canvas and handle hover, press and disabled states themselves.
"""

import tkinter as tk
import tkinter.font as tkfont
from PIL import ImageTk
from . import icons


class _CanvasControl(tk.Canvas):
    def __init__(self, parent, theme, bg):
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0)
        self.theme = theme
        self._images = []
        self._hover = False
        self.bind('<Enter>', lambda e: self._set_hover(True))
        self.bind('<Leave>', lambda e: self._set_hover(False))

    def _set_hover(self, hover):
        self._hover = hover
        self.redraw()

    def _photo(self, image):
        photo = ImageTk.PhotoImage(image)
        self._images.append(photo)
        return photo

    def _measure(self, font, text):
        return tkfont.Font(root=self, font=font).measure(text)

    def redraw(self):
        raise NotImplementedError


class FlatButton(_CanvasControl):
    def __init__(self, parent, theme, text='', command=None, variant='secondary',
                 icon=None, key=None, height=36, bg=None, font=None):
        super().__init__(parent, theme, bg or theme.bar)
        t = theme
        self.variants = {
            'primary': (t.accent, t.accent_hover, t.on_accent, t.on_accent),
            'secondary': (t.control, t.control_hover, t.text, t.text),
            'danger': (t.control, t.danger, t.danger_text, '#ffffff'),
            'ghost': (None, t.control, t.text_secondary, t.text),
        }
        self.text = text
        self.command = command
        self.variant = variant
        self.icon_name = icon
        self.key = key
        self.enabled = True
        self.font = font or t.font(13, semibold=variant in ('primary', 'danger'))
        self.key_font = t.font(11)

        self.h = t.px(height)
        self.pad = t.px(14 if text else 0)
        self.icon_size = t.px(16)
        self.gap = t.px(8)
        self.key_h = t.px(20)
        self.key_w = max(self.key_h, self._measure(self.key_font, key) + t.px(12)) if key else 0
        width = self.pad * 2 + self._measure(self.font, text)
        if icon:
            width += self.icon_size + (self.gap if text else 0)
        if key:
            width += t.px(12) + self.key_w
        if not text:
            width = self.h
        self.configure(width=width, height=self.h)
        self.w = width
        self._cache = {}
        self.bind('<ButtonRelease-1>', self._release)
        self.redraw()

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.redraw()

    def _release(self, event):
        inside = 0 <= event.x < self.w and 0 <= event.y < self.h
        if self.enabled and inside and self.command:
            self.command()

    def _state_images(self, state):
        if state in self._cache:
            return self._cache[state]
        fill, hover_fill, ink, hover_ink = self.variants[self.variant]
        if state == 'hover':
            fill, ink = hover_fill, hover_ink
        elif state == 'disabled':
            fill = self.theme.control if fill else None
            ink = self.theme.text_disabled
        t = self.theme
        bg = self._photo(icons.rounded_rect(self.w, self.h, t.px(8), fill)) if fill else None
        glyph = self._photo(icons.icon(self.icon_name, self.icon_size, ink)) if self.icon_name else None
        cap = None
        if self.key:
            cap_fill = (0, 0, 0, 40) if self.variant == 'primary' and state != 'disabled' else (255, 255, 255, 18)
            cap = self._photo(icons.rounded_rect(self.key_w, self.key_h, t.px(4), cap_fill))
        self._cache[state] = (bg, glyph, cap, ink)
        return self._cache[state]

    def redraw(self):
        state = 'disabled' if not self.enabled else 'hover' if self._hover else 'normal'
        bg, glyph, cap, ink = self._state_images(state)
        self.configure(cursor='hand2' if self.enabled else '')
        self.delete('all')
        mid = self.h // 2
        if bg:
            self.create_image(0, 0, image=bg, anchor='nw')
        if not self.text:
            self.create_image(self.w // 2, mid, image=glyph)
            return
        x = self.pad
        if glyph:
            self.create_image(x, mid, image=glyph, anchor='w')
            x += self.icon_size + self.gap
        self.create_text(x, mid, text=self.text, font=self.font, fill=ink, anchor='w')
        if cap:
            cx = self.w - self.pad - self.key_w
            self.create_image(cx, mid, image=cap, anchor='w')
            self.create_text(cx + self.key_w // 2, mid, text=self.key, font=self.key_font, fill=ink)


class Segmented(_CanvasControl):
    def __init__(self, parent, theme, options, value, command, bg=None):
        super().__init__(parent, theme, bg or theme.bar)
        self.options = options
        self.value = value
        self.command = command
        self.font = theme.font(13)
        self.h = theme.px(32)
        self.inset = theme.px(3)
        self.seg_w = max(self._measure(self.font, label) for _, label in options) + theme.px(28)
        self.w = self.seg_w * len(options) + self.inset * 2
        self.configure(width=self.w, height=self.h, cursor='hand2')
        self._track = self._photo(icons.rounded_rect(self.w, self.h, theme.px(8), theme.control))
        self._thumb = self._photo(icons.rounded_rect(self.seg_w, self.h - self.inset * 2,
                                                     theme.px(6), theme.control_active))
        self._hover_index = None
        self.bind('<Motion>', self._motion)
        self.bind('<ButtonRelease-1>', self._release)
        self.redraw()

    def _index_at(self, x):
        index = (x - self.inset) // self.seg_w
        return index if 0 <= index < len(self.options) else None

    def _motion(self, event):
        index = self._index_at(event.x)
        if index != self._hover_index:
            self._hover_index = index
            self.redraw()

    def _set_hover(self, hover):
        if not hover:
            self._hover_index = None
        self.redraw()

    def _release(self, event):
        index = self._index_at(event.x)
        if index is None:
            return
        value = self.options[index][0]
        if value != self.value:
            self.set_value(value)
            self.command(value)

    def set_value(self, value):
        self.value = value
        self.redraw()

    def redraw(self):
        self.delete('all')
        self.create_image(0, 0, image=self._track, anchor='nw')
        for index, (value, label) in enumerate(self.options):
            x = self.inset + index * self.seg_w
            selected = value == self.value
            if selected:
                self.create_image(x, self.inset, image=self._thumb, anchor='nw')
            color = self.theme.text if selected or index == self._hover_index else self.theme.text_secondary
            self.create_text(x + self.seg_w // 2, self.h // 2, text=label, font=self.font, fill=color)


class Switch(_CanvasControl):
    def __init__(self, parent, theme, text, variable, command, bg=None):
        super().__init__(parent, theme, bg or theme.bar)
        self.text = text
        self.variable = variable
        self.command = command
        self.font = theme.font(13)
        self.track_w, self.track_h = theme.px(30), theme.px(18)
        self.knob = theme.px(14)
        self.h = theme.px(32)
        self.w = self.track_w + theme.px(8) + self._measure(self.font, text)
        self.configure(width=self.w, height=self.h, cursor='hand2')
        self._tracks = {
            True: self._photo(icons.rounded_rect(self.track_w, self.track_h, self.track_h // 2, theme.accent)),
            False: self._photo(icons.rounded_rect(self.track_w, self.track_h, self.track_h // 2,
                                                  theme.control_active)),
        }
        self._knob = self._photo(icons.circle(self.knob, '#f4f5f6'))
        self.bind('<ButtonRelease-1>', self._release)
        self.redraw()

    def _release(self, event):
        if 0 <= event.x < self.w and 0 <= event.y < self.h:
            self.variable.set(not self.variable.get())
            self.redraw()
            self.command()

    def redraw(self):
        on = bool(self.variable.get())
        self.delete('all')
        top = (self.h - self.track_h) // 2
        self.create_image(0, top, image=self._tracks[on], anchor='nw')
        inset = (self.track_h - self.knob) // 2
        knob_x = self.track_w - inset - self.knob if on else inset
        self.create_image(knob_x, top + inset, image=self._knob, anchor='nw')
        color = self.theme.text if on or self._hover else self.theme.text_secondary
        self.create_text(self.track_w + self.theme.px(8), self.h // 2, text=self.text,
                         font=self.font, fill=color, anchor='w')
