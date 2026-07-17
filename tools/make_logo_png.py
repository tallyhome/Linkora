"""Génère logo.png pour GitHub README (PNG fiable, SVG souvent bloqué)."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SIZE = 512


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def star(draw, cx, cy, r, color):
    pts = []
    for i in range(8):
        ang = math.radians(i * 45 - 90)
        rad = r if i % 2 == 0 else r * 0.35
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=color)


def main() -> None:
    (ROOT / "docs").mkdir(exist_ok=True)
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    c0, c1, c2 = (13, 148, 136), (15, 118, 110), (29, 78, 216)
    radius, margin = int(SIZE * 0.22), int(SIZE * 0.03)

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [margin, margin, SIZE - margin - 1, SIZE - margin - 1],
        radius=radius,
        fill=255,
    )

    grad = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    px = grad.load()
    for y in range(SIZE):
        for x in range(SIZE):
            t = (x + y) / (2 * (SIZE - 1))
            color = (
                lerp(c0, c1, t / 0.55)
                if t < 0.55
                else lerp(c1, c2, (t - 0.55) / 0.45)
            )
            px[x, y] = color + (255,)

    img = Image.composite(grad, img, mask)
    draw = ImageDraw.Draw(img)
    stroke = max(14, SIZE // 28)
    white = (255, 255, 255, 255)

    draw.arc(
        [SIZE * 0.22, SIZE * 0.38, SIZE * 0.55, SIZE * 0.72],
        start=40,
        end=250,
        fill=white,
        width=stroke,
    )
    draw.arc(
        [SIZE * 0.38, SIZE * 0.22, SIZE * 0.72, SIZE * 0.55],
        start=220,
        end=70,
        fill=white,
        width=stroke,
    )

    kx, ky, kr = int(SIZE * 0.68), int(SIZE * 0.68), int(SIZE * 0.09)
    accent = (94, 234, 212, 255)
    draw.ellipse([kx - kr, ky - kr, kx + kr, ky + kr], outline=accent, width=stroke - 2)
    draw.ellipse([kx - 6, ky - 6, kx + 6, ky + 6], fill=white)
    draw.line(
        [
            (kx + kr - 2, ky + kr - 2),
            (kx + kr + int(SIZE * 0.12), ky + kr + int(SIZE * 0.12)),
        ],
        fill=accent,
        width=stroke - 2,
    )

    star(draw, SIZE * 0.28, SIZE * 0.28, SIZE * 0.055, (253, 230, 138, 255))
    star(draw, SIZE * 0.78, SIZE * 0.30, SIZE * 0.035, (255, 255, 255, 230))

    img.save(ROOT / "static" / "img" / "logo.png")
    img.resize((192, 192), Image.Resampling.LANCZOS).save(ROOT / "docs" / "logo.png")
    print("OK -> static/img/logo.png + docs/logo.png")


if __name__ == "__main__":
    main()
