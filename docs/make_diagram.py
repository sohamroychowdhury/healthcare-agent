"""Generate the architecture diagram (PNG) with Pillow.

Run:  python3 docs/make_diagram.py
Produces docs/images/architecture.png
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "images" / "architecture.png"
SCALE = 2  # render at 2x for crisp text

W, H = 1100, 600

INK = (15, 23, 42)
GREY = (71, 85, 105)
LINE = (71, 85, 105)
SOFT = (148, 163, 184)
BLUE = (37, 99, 235)
BLUE_BG = (239, 246, 255)
GREEN = (5, 150, 105)
GREEN_BG = (236, 253, 245)
WHITE = (255, 255, 255)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"]
        if bold
        else ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size * SCALE)
    return ImageFont.load_default()


def s(v: int) -> int:
    return v * SCALE


def box(d, x, y, w, h, title, subs, fill=WHITE, outline=GREY):
    d.rounded_rectangle(
        [s(x), s(y), s(x + w), s(y + h)], radius=s(12), fill=fill, outline=outline, width=s(2)
    )
    cx = s(x + w / 2)
    d.text((cx, s(y + 16)), title, font=font(15, bold=True), fill=INK, anchor="mm")
    for i, line in enumerate(subs):
        d.text((cx, s(y + 38 + i * 18)), line, font=font(11), fill=GREY, anchor="mm")


def _head(d, x2, y2, ang, color):
    size = s(9)
    for a in (ang + 2.5, ang - 2.5):
        d.line([x2, y2, x2 - size * math.cos(a), y2 - size * math.sin(a)], fill=color, width=s(2))


def arrow(d, p1, p2, color=LINE, dashed=False):
    x1, y1, x2, y2 = s(p1[0]), s(p1[1]), s(p2[0]), s(p2[1])
    if dashed:
        total = math.hypot(x2 - x1, y2 - y1)
        dash, gap = s(6), s(5)
        n = int(total // (dash + gap))
        for i in range(n + 1):
            t1 = (i * (dash + gap)) / total
            t2 = min((i * (dash + gap) + dash) / total, 1)
            d.line(
                [x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1,
                 x1 + (x2 - x1) * t2, y1 + (y2 - y1) * t2],
                fill=color, width=s(2),
            )
    else:
        d.line([x1, y1, x2, y2], fill=color, width=s(2))
    _head(d, x2, y2, math.atan2(y2 - y1, x2 - x1), color)


def label(d, x, y, text, color=(51, 65, 85)):
    d.text((s(x), s(y)), text, font=font(11), fill=color, anchor="lm")


def main() -> None:
    img = Image.new("RGB", (s(W), s(H)), WHITE)
    d = ImageDraw.Draw(img)

    d.text((s(40), s(34)), "Healthcare Q&A Agent — Architecture",
           font=font(20, bold=True), fill=INK, anchor="lm")

    box(d, 40, 90, 160, 72, "User", ["health question"], BLUE_BG, BLUE)
    box(d, 250, 90, 170, 72, "Guard-rails", ["validate input"])
    box(d, 470, 70, 230, 112, "Agent — ReAct loop",
        ["Think -> Act -> Observe", "LLM: Groq (Llama 3)", "structured JSON step"], BLUE_BG, BLUE)
    box(d, 760, 90, 180, 72, "Grounded answer", ["+ cited sources"], BLUE_BG, BLUE)
    box(d, 980, 70, 90, 112, "Fallback", ["on error /", "step limit:", "safe answer"])

    box(d, 470, 300, 230, 92, "Tool: medical search",
        ["search_medical_database()", 'prepends "medical clinical"'], GREEN_BG, GREEN)
    box(d, 360, 450, 180, 72, "DuckDuckGo", ["live web (free, no key)"], GREEN_BG, GREEN)
    box(d, 580, 450, 180, 72, "Offline fixtures", ["deterministic fallback"])
    box(d, 760, 300, 180, 92, "Trace logger", ["every step ->", "console + JSONL"])

    arrow(d, (200, 126), (248, 126))
    arrow(d, (420, 126), (468, 126))
    arrow(d, (700, 126), (758, 126))
    # Fallback link routed along the very top so it doesn't cross the answer box.
    arrow(d, (690, 74), (978, 80), dashed=True)
    label(d, 800, 66, "on failure")

    arrow(d, (520, 182), (520, 298))
    label(d, 405, 240, "Action: search")
    arrow(d, (590, 298), (590, 184))
    label(d, 598, 240, "Observation")

    arrow(d, (520, 392), (470, 448))
    arrow(d, (610, 392), (660, 448), dashed=True)
    label(d, 668, 420, "if web fails")

    arrow(d, (700, 150), (770, 298), dashed=True)

    img.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
