"""Colors, type and sizing shared by every widget.

One graphite ramp carries the chrome so photos supply the color. The single
accent is the teal from the app icon; red only marks deletion.
"""

import tkinter.font as tkfont

UI_FAMILIES = ('Segoe UI Variable Text', 'Segoe UI', 'SF Pro Text', '.AppleSystemUIFont',
               'Helvetica Neue', 'Inter', 'Cantarell', 'Noto Sans', 'DejaVu Sans')
DISPLAY_FAMILIES = ('Segoe UI Variable Display', 'Segoe UI', 'SF Pro Display',
                    '.AppleSystemUIFont', 'Helvetica Neue', 'Inter', 'Cantarell', 'Noto Sans')
MONO_FAMILIES = ('Cascadia Mono', 'SF Mono', 'Menlo', 'JetBrains Mono', 'DejaVu Sans Mono',
                 'Consolas', 'Courier New')
# Windows ships semibold as separate families; elsewhere Tk falls back to bold.
SEMIBOLD_FAMILIES = {
    'Segoe UI Variable Text': 'Segoe UI Variable Text Semibold',
    'Segoe UI Variable Display': 'Segoe UI Variable Display Semib',
    'Segoe UI': 'Segoe UI Semibold',
}


class Theme:
    window = '#111213'
    bar = '#1a1b1d'
    control = '#232427'
    control_hover = '#2c2d31'
    control_active = '#3a3c41'
    hairline = '#2a2b2e'

    text = '#ececec'
    text_secondary = '#a3a6ab'
    text_muted = '#8a8e95'
    text_disabled = '#56595e'

    accent = '#55e0c6'
    accent_hover = '#6bedd0'
    on_accent = '#0b1a2d'
    danger = '#c93c3f'
    danger_text = '#f08a8c'

    strip_upcoming = '#2a2c30'
    strip_reviewed = '#5a5d63'

    def __init__(self, root):
        # Tk reports 72 dpi on macOS, where coordinates are already in points.
        self.scale = max(1.0, root.winfo_fpixels('1i') / 96)
        available = set(tkfont.families(root))
        self.ui_family = self._pick(UI_FAMILIES, available, 'TkDefaultFont')
        self.display_family = self._pick(DISPLAY_FAMILIES, available, self.ui_family)
        self.mono_family = self._pick(MONO_FAMILIES, available, 'TkFixedFont')
        self._available = available

    @staticmethod
    def _pick(families, available, fallback):
        return next((family for family in families if family in available), fallback)

    def px(self, value):
        return max(1, round(value * self.scale))

    def font(self, size, role='ui', semibold=False):
        family = {'ui': self.ui_family, 'display': self.display_family,
                  'mono': self.mono_family}[role]
        weight = 'normal'
        if semibold:
            heavier = SEMIBOLD_FAMILIES.get(family)
            if heavier in self._available:
                family = heavier
            else:
                weight = 'bold'
        return (family, -self.px(size), weight)
