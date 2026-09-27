"""Draw og.png (1200x630) and apple-touch-icon.png (180x180) into src/. Needs: pip install pillow"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SRC = Path(__file__).resolve().parent.parent / "src"
BLUE, INK, MUTED, BG = (37, 99, 235), (16, 24, 40), (90, 101, 118), (245, 247, 250)
FONTS = "/System/Library/Fonts/Supplemental/"
bold = lambda s: ImageFont.truetype(FONTS + "Arial Bold.ttf", s)
reg = lambda s: ImageFont.truetype(FONTS + "Arial.ttf", s)

def globe(d, x, y, r, fill):
    d.ellipse([x - r, y - r, x + r, y + r], outline=fill, width=max(2, r // 7))
    d.ellipse([x - r // 2.4, y - r, x + r // 2.4, y + r], outline=fill, width=max(2, r // 9))
    d.line([x - r, y, x + r, y], fill=fill, width=max(2, r // 9))

img = Image.new("RGB", (1200, 630), BG)
d = ImageDraw.Draw(img)
d.rounded_rectangle([72, 72, 168, 168], 22, fill=BLUE)
globe(d, 120, 120, 30, (255, 255, 255))
d.text((72, 220), "Country Holiday +", font=bold(76), fill=INK)
d.text((72, 310), "Timezone Planner", font=bold(76), fill=INK)
d.text((72, 420), "Local time, public holidays and shared working hours", font=reg(34), fill=MUTED)
x = 72
for label, bg, fg in [("Working Day", (231, 246, 236), (21, 128, 61)), ("Public Holiday", (255, 241, 227), (194, 87, 12)), ("Too late", (253, 236, 236), (198, 40, 40))]:
    w = d.textlength(label, font=bold(28)) + 44
    d.rounded_rectangle([x, 500, x + w, 552], 26, fill=bg)
    d.text((x + 22, 510), label, font=bold(28), fill=fg)
    x += w + 16
img.save(SRC / "og.png", optimize=True)

icon = Image.new("RGB", (180, 180), BLUE)
globe(ImageDraw.Draw(icon), 90, 90, 52, (255, 255, 255))
icon.save(SRC / "apple-touch-icon.png", optimize=True)
print("ok")
