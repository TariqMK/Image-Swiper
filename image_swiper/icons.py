"""Antialiased line icons and rounded shapes drawn with Pillow.

Icons follow Lucide's 24-unit grid and 2-unit stroke, so they read as one set at
any size. Everything is drawn at 4x and downsampled for smooth edges.
"""

import math
from PIL import Image, ImageDraw

SUPERSAMPLE = 4


def _rgba(color, alpha=255):
    if isinstance(color, tuple):
        return color if len(color) == 4 else (*color, alpha)
    color = color.lstrip('#')
    return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16), alpha)


def rounded_rect(width, height, radius, fill, outline=None):
    """Return an RGBA rounded rectangle with transparent corners."""
    k = SUPERSAMPLE
    img = Image.new('RGBA', (width * k, height * k), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, width * k - 1, height * k - 1), radius=radius * k,
                           fill=_rgba(fill), outline=_rgba(outline) if outline else None,
                           width=k if outline else 0)
    return img.resize((width, height), Image.Resampling.LANCZOS)


def circle(diameter, fill):
    k = SUPERSAMPLE
    img = Image.new('RGBA', (diameter * k, diameter * k), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((0, 0, diameter * k - 1, diameter * k - 1), fill=_rgba(fill))
    return img.resize((diameter, diameter), Image.Resampling.LANCZOS)


def _arc_points(cx, cy, r, start, end, steps=16):
    return [(cx + r * math.cos(math.radians(start + (end - start) * i / steps)),
             cy + r * math.sin(math.radians(start + (end - start) * i / steps)))
            for i in range(steps + 1)]


# Each icon is a list of strokes on a 24-unit grid. A stroke is a polyline, a
# closed polygon ('closed', points), a dot ('dot', x, y, r) or a filled shape.
ICONS = {
    'folder': [('closed', [(4, 3.5), (8, 3.5), (10, 6), (20, 6), (21.5, 7.5), (21.5, 18.5),
                           (20, 20), (4, 20), (2.5, 18.5), (2.5, 5)])],
    'chevron-down': [[(6, 9), (12, 15), (18, 9)]],
    'chevron-left': [[(15, 18), (9, 12), (15, 6)]],
    'chevron-right': [[(9, 18), (15, 12), (9, 6)]],
    'check': [[(20, 6), (9, 17), (4, 12)]],
    'trash': [[(3, 6), (21, 6)],
              [(5, 6), (5, 20), (7, 22), (17, 22), (19, 20), (19, 6)],
              [(8, 6), (8, 4), (10, 2), (14, 2), (16, 4), (16, 6)],
              [(10, 11), (10, 17)], [(14, 11), (14, 17)]],
    'undo': [[(9, 14), (4, 9), (9, 4)],
             [(4, 9), (14.5, 9)] + _arc_points(14.5, 14.5, 5.5, -90, 90) + [(11, 20)]],
    'more': [('dot', 5, 12, 1.4), ('dot', 12, 12, 1.4), ('dot', 19, 12, 1.4)],
    'image': [('closed', [(5, 3), (19, 3), (21, 5), (21, 19), (19, 21), (5, 21), (3, 19), (3, 5)]),
              ('ring', 9, 9, 2),
              [(21, 15), (16, 10), (5, 21)]],
    'play': [('fill', [(7, 4), (20, 12), (7, 20)])],
    'dice': [('closed', [(6, 3), (18, 3), (21, 6), (21, 18), (18, 21), (6, 21), (3, 18), (3, 6)]),
             ('dot', 8, 8, 1.5), ('dot', 16, 8, 1.5), ('dot', 12, 12, 1.5),
             ('dot', 8, 16, 1.5), ('dot', 16, 16, 1.5)],
}


def icon(name, size, color, stroke=2.0):
    """Return an RGBA image of the named icon, `size` pixels square."""
    k = SUPERSAMPLE
    px = size * k
    unit = px / 24
    width = max(1, round(stroke * unit))
    ink = _rgba(color)
    img = Image.new('RGBA', (px, px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    def scale(points):
        return [(x * unit, y * unit) for x, y in points]

    def cap(x, y):
        r = width / 2
        draw.ellipse((x - r, y - r, x + r, y + r), fill=ink)

    for stroke_def in ICONS[name]:
        if isinstance(stroke_def, tuple) and stroke_def[0] == 'dot':
            _, x, y, r = stroke_def
            draw.ellipse(((x - r) * unit, (y - r) * unit, (x + r) * unit, (y + r) * unit), fill=ink)
        elif isinstance(stroke_def, tuple) and stroke_def[0] == 'ring':
            _, x, y, r = stroke_def
            draw.ellipse(((x - r) * unit, (y - r) * unit, (x + r) * unit, (y + r) * unit),
                         outline=ink, width=width)
        elif isinstance(stroke_def, tuple) and stroke_def[0] == 'fill':
            draw.polygon(scale(stroke_def[1]), fill=ink)
        else:
            closed = isinstance(stroke_def, tuple) and stroke_def[0] == 'closed'
            points = scale(stroke_def[1] if closed else stroke_def)
            if closed:
                points = points + [points[0], points[1]]
            draw.line(points, fill=ink, width=width, joint='curve')
            for x, y in points if closed else (points[0], points[-1]):
                cap(x, y)
    return img.resize((size, size), Image.Resampling.LANCZOS)
