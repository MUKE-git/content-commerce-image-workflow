"""Small local decoration set; image processing never needs a media API."""

from __future__ import annotations

from PIL import Image, ImageDraw


def make_stickers(limit: int = 4) -> list[Image.Image]:
    """Draw repeatable transparent leaf, flower, dot and line patterns."""
    stickers: list[Image.Image] = []
    for kind in range(min(max(limit, 0), 4)):
        image = Image.new("RGBA", (320, 420), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        if kind == 0:
            for x in (45, 145, 245):
                draw.line((x, 0, x + 25, 420), fill=(89, 144, 112), width=5)
                for y in range(25, 410, 65):
                    draw.ellipse((x - 23, y, x + 13, y + 21), fill=(137, 177, 133))
                    draw.ellipse((x + 16, y + 25, x + 52, y + 46), fill=(89, 144, 112))
        elif kind == 1:
            for x in (60, 160, 260):
                for y in (55, 160, 265, 370):
                    for dx, dy in ((-20, 0), (20, 0), (0, -20), (0, 20)):
                        draw.ellipse((x + dx - 13, y + dy - 13, x + dx + 13, y + dy + 13),
                                     fill=(224, 155, 170))
                    draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(232, 188, 98))
        elif kind == 2:
            for y in range(20, 420, 48):
                for x in range(20 + (y % 96) // 2, 320, 55):
                    draw.ellipse((x, y, x + 11, y + 11), fill=(174, 164, 199))
                    draw.arc((x + 14, y - 7, x + 35, y + 14), 20, 310,
                             fill=(174, 164, 199), width=3)
        else:
            for y in range(25, 420, 70):
                for x in range(20, 320, 70):
                    draw.line((x, y + 16, x + 18, y, x + 36, y + 16),
                              fill=(127, 172, 188), width=4)
                    draw.rounded_rectangle((x + 45, y + 4, x + 58, y + 17), radius=3,
                                           outline=(127, 172, 188), width=3)
        stickers.append(image)
    return stickers
