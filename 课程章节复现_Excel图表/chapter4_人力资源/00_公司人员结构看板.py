# -*- coding: utf-8 -*-
"""第三章外 第四章合成看板：00_公司人员结构看板
源: 第四章 人力资源可视化看板.xlsx / 202203人员基础信息（6 图拼版 + 标题）
实现: 读取本章 images\1~6 图 PNG，按 COM 点坐标版式（scale=150/72）合成为整页看板
输出: images\00_公司人员结构看板.png
运行: python -X utf8 00_公司人员结构看板.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_HR = os.path.join(HERE, "images", "00_公司人员结构看板.png")

BG_HR = (29, 36, 74)
WHITE = (242, 242, 242)

FONT_PATHS = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]


def get_font(size, bold=False):
    paths = FONT_PATHS if bold else FONT_PATHS[1:] + FONT_PATHS[:1]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def load_png(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        print("MISSING", path)
        return None
    return Image.open(path).convert("RGBA")


def paste_bg(img, bg):
    out = Image.new("RGBA", img.size, bg + (255,))
    out.alpha_composite(img)
    return out


def make_hr():
    """按 COM 布局合成：点坐标 -> 像素 (scale≈2.083 @150dpi/72)
    原点取看板左上：title T=2.6, charts L 840..1412, T 35..312
    padding 20pt
    """
    scale = 150.0 / 72.0
    # bounds in points
    x0, y0 = 820.0, 0.0
    x1, y1 = 1432.0, 330.0
    pad = 16.0
    W = int((x1 - x0 + pad * 2) * scale)
    H = int((y1 - y0 + pad * 2) * scale)
    canvas = Image.new("RGBA", (W, H), BG_HR + (255,))
    d = ImageDraw.Draw(canvas)

    def xy(px, py):
        return ((px - x0 + pad) * scale, (py - y0 + pad) * scale)

    # title 公司人员结构看板 L=1061 T=3 W=134 H=30
    tx, ty = xy(1061.0, 3.0)
    tw, th = 134.5 * scale, 30.1 * scale
    font_t = get_font(28, True)
    d.text((tx + tw / 2, ty + th / 2), "公司人员结构看板",
           font=font_t, fill=WHITE, anchor="mm")

    # charts: name, left, top, w, h, image
    charts = [
        ("1_年龄", 840.0, 35.2, 180.6, 110.0),
        ("4_性别", 1034.1, 35.2, 184.1, 110.0),
        ("2_婚姻状况", 1231.6, 35.2, 180.6, 110.0),
        ("5_学历", 841.1, 156.4, 180.6, 156.1),
        ("3_入转调", 1033.5, 156.4, 184.1, 156.1),
        ("6_部门", 1231.2, 156.4, 180.6, 156.1),
    ]
    hr_dir = os.path.join(HERE, "images")
    for name, L, T, Wc, Hc in charts:
        p = os.path.join(hr_dir, name + ".png")
        im = load_png(p)
        if im is None:
            continue
        im = paste_bg(im, BG_HR)
        tw = max(1, int(Wc * scale))
        th = max(1, int(Hc * scale))
        im = im.resize((tw, th), Image.LANCZOS)
        x, y = xy(L, T)
        canvas.paste(im, (int(x), int(y)))

    os.makedirs(os.path.dirname(OUT_HR), exist_ok=True)
    canvas.convert("RGB").save(OUT_HR, "PNG")
    print("saved", OUT_HR, canvas.size)


if __name__ == "__main__":
    make_hr()
