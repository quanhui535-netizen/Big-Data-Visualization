# -*- coding: utf-8 -*-
"""第四章合成看板：00_公司销售数据可视化看板
源: 第四章 销售看板参考.xlsx / 数据大屏（11 图拼版 + 顶底栏/面板/标题/月份下拉）
实现: 读取本章 images\1~11 图 PNG，按 sheet 点坐标版式（scale=150/72）
      画顶栏/底栏/成本费用面板/标题/静态下拉后合成为整页看板
输出: images\00_公司销售数据可视化看板.png
运行: python -X utf8 00_公司销售数据可视化看板.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_SALES = os.path.join(HERE, "images", "00_公司销售数据可视化看板.png")

BG_SALES = (26, 30, 67)
PANEL = (44, 53, 96)
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


def rr(d, xy, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def make_sales():
    """销售看板：深底 + 面板 + 11 图 + 标题 + 月份下拉（静态）"""
    scale = 150.0 / 72.0
    # sheet 形状 bounds: L=206..1045, T=12..553
    x0, y0 = 200.0, 8.0
    x1, y1 = 1052.0, 558.0
    pad = 8.0
    W = int((x1 - x0 + pad * 2) * scale)
    H = int((y1 - y0 + pad * 2) * scale)
    canvas = Image.new("RGBA", (W, H), BG_SALES + (255,))
    d = ImageDraw.Draw(canvas)

    def xy(px, py):
        return ((px - x0 + pad) * scale, (py - y0 + pad) * scale)

    def box(L, T, Wc, Hc, fill=PANEL, outline=None, r=6):
        x, y = xy(L, T)
        x2, y2 = xy(L + Wc, T + Hc)
        rr(d, (x, y, x2, y2), r, fill=fill, outline=outline, width=2)

    # 顶栏 Rectangle 12
    box(208.1, 19.6, 837.0, 53.0, fill=(36, 40, 78), r=4)
    # 底栏 Rectangle 13
    box(206.2, 524.0, 838.9, 29.3, fill=(36, 40, 78), r=4)
    # 成本费用面板 Rectangle 14
    box(206.2, 277.6, 273.9, 241.5, fill=PANEL, r=8)

    # 大面板背景（三列）
    # 左列
    box(206.2, 78.2, 274.0, 191.3, fill=PANEL, r=8)       # chart9
    # 中上 chart7
    box(486.8, 78.2, 277.0, 117.9, fill=PANEL, r=8)
    # 中 chart10
    box(486.8, 202.4, 277.0, 146.7, fill=PANEL, r=8)
    # 中下 chart11
    box(486.8, 357.2, 277.0, 161.9, fill=PANEL, r=8)
    # 右上 chart8
    box(768.1, 78.2, 276.5, 161.9, fill=PANEL, r=8)
    # 右中 chart6
    box(768.0, 247.0, 276.5, 132.6, fill=PANEL, r=8)
    # 右下 chart5
    box(768.2, 386.6, 275.5, 132.6, fill=PANEL, r=8)

    # 标题
    font_t = get_font(30, True)
    tx, ty = xy(210.4, 12.7)
    d.text((tx + 10, ty + 32), "公司销售数据可视化看板",
           font=font_t, fill=WHITE, anchor="lm")

    # 月份下拉（静态）Drop Down 1 L=964 T=47.5 W=44 H=17.5 + 日历图标
    dx, dy = xy(964.0, 47.5)
    dw, dh = 44.0 * scale, 17.5 * scale
    # 日历小图标
    icx, icy = xy(943.0, 56.0)
    d.rectangle((icx - 14, icy - 12, icx + 14, icy + 12), fill=(70, 120, 200),
                outline=WHITE, width=1)
    d.rectangle((icx - 14, icy - 12, icx + 14, icy - 4), fill=(50, 90, 170))
    font_s = get_font(14, False)
    d.rectangle((dx, dy, dx + dw, dy + dh), fill=(245, 245, 245),
                outline=(180, 180, 180), width=1)
    d.text((dx + 6, dy + dh / 2), "9月", font=get_font(13), fill=(30, 30, 30),
           anchor="lm")
    # 箭头
    ax0 = dx + dw - 14
    ay0 = dy + dh / 2 - 3
    d.polygon([(ax0, ay0), (ax0 + 10, ay0), (ax0 + 5, ay0 + 7)], fill=(40, 40, 40))

    # 成本费用标签
    font_c = get_font(20, False)
    # 面板内标题居中
    px, py = xy(206.2, 277.6)
    px2, _ = xy(206.2 + 273.9, 0)
    d.text(((px + px2) / 2, py + 22), "成本费用", font=font_c, fill=WHITE,
           anchor="mm")

    # 粘贴 11 张图（各自画在透明底上）
    sales_dir = os.path.join(HERE, "images")
    # name, L, T, W, h  — 图本身含面板底/卡片
    charts = [
        ("9_产品类别销量", 206.2, 78.2, 274.0, 191.3),
        ("4_产品费用", 213.8, 415.4, 122.4, 97.0),
        ("1_推广费用", 213.7, 310.2, 122.4, 97.0),
        ("2_其他费用", 347.6, 416.1, 124.4, 97.0),
        ("3_人工费用", 348.0, 311.0, 124.4, 97.0),
        ("7_销量环比", 486.8, 78.2, 277.0, 117.9),
        ("10_商品销售额Top3", 486.8, 202.4, 277.0, 146.7),
        ("11_利润额占比销售额", 486.8, 357.2, 277.0, 161.9),
        ("8_各月销售额", 768.1, 78.2, 276.5, 161.9),
        ("6_区域销量", 768.0, 247.0, 276.5, 132.6),
        ("5_快递公司销量", 768.2, 386.6, 275.5, 132.6),
    ]
    for name, L, T, Wc, Hc in charts:
        p = os.path.join(sales_dir, name + ".png")
        im = load_png(p)
        if im is None:
            continue
        tw = max(1, int(Wc * scale))
        th = max(1, int(Hc * scale))
        im2 = im.resize((tw, th), Image.LANCZOS)
        x, y = xy(L, T)
        canvas.paste(im2, (int(x), int(y)), im2 if im2.mode == "RGBA" else None)

    os.makedirs(os.path.dirname(OUT_SALES), exist_ok=True)
    canvas.convert("RGB").save(OUT_SALES, "PNG")
    print("saved", OUT_SALES, canvas.size)


if __name__ == "__main__":
    make_sales()
