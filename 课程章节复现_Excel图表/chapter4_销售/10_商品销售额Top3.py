# -*- coding: utf-8 -*-
"""第四章 销售看板 第10张：商品销售额Top3
源: 第四章 销售看板参考.xlsx / chart10
参考原图: ...\\ch4_sales__数据大屏__chart10.png
实现: 奖牌图标 + 产品名 + 蓝底销售额 + 销量列；表头 userShapes
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import TXT, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BG_PANEL = "#2C3560"
C_BLUE = "#4A5BD1"

W_PX, H_PX = 553, 293
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

TITLE = "商品销售额Top3"
T_X, T_Y, T_PT = W_PX / 2.0, 25.0, 16.0

# header band y85-100 x176-469: 产品 / 销售额(万) / 销量
HDR_Y = 85.0
HDR_PT = 16.0
HDR_PROD_X = 176.0
HDR_SALES_X = 350.0
HDR_QTY_X = 439.0

# rows: blue value boxes x343-395
# row bands: y122-154 (rank1 has medal above), y177-209, y232-265
ROWS = [
    (1, "KI Conference Tables", "16.98", "30", 154.0),  # value box bottom
    (2, "Xerox 193", "16.81", "29", 209.0),
    (3, "Phone 918", "15.35", "31", 265.0),
]
# medal positions: left ~66-91, centers y around row
MEDAL_X = 78.0
MEDAL_R = 14.0
# from bands: rank1 number ~y122-153 medal, product text y130-153
ROW_TEXT_Y = [141.0, 196.0, 251.0]  # centers of product/value text

PROD_X = 152.0
VAL_BOX_X0, VAL_BOX_X1 = 343.0, 395.0
VAL_BOX_H = 33.0
QTY_X = 433.0

LBL_PT = 16.0
MEDAL_COLORS = ["#F5C353", "#7BBDD5", "#E8A06A"]  # gold, silver-ish, bronze-ish from image
MEDAL_TEXT = ["1", "2", "3"]


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG_PANEL)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG_PANEL)
    ax.axis("off")

    ax.text(T_X, T_Y, TITLE, color=TXT, fontsize=T_PT,
            ha="left", va="top", zorder=6)
    # title measured x190-361 — left-align at 190
    # redraw with measured x
    ax.texts[-1].set_x(190.0)
    ax.texts[-1].set_ha("left")

    ax.text(HDR_PROD_X, HDR_Y, "产品", color="#D9D9D9", fontsize=HDR_PT,
            ha="left", va="top", zorder=6)
    ax.text(HDR_SALES_X, HDR_Y, "销售额(万)", color="#D9D9D9",
            fontsize=HDR_PT, ha="left", va="top", zorder=6)
    ax.text(HDR_QTY_X, HDR_Y, "销量", color="#D9D9D9", fontsize=HDR_PT,
            ha="left", va="top", zorder=6)

    for i, (rank, name, sales, qty, _) in enumerate(ROWS):
        cy = ROW_TEXT_Y[i]
        # medal circle
        col = MEDAL_COLORS[i]
        ax.add_patch(Circle((MEDAL_X, cy), MEDAL_R, facecolor=col,
                            edgecolor="white", linewidth=1.5, zorder=5))
        # ribbon hint (small rectangle above)
        ax.add_patch(Rectangle((MEDAL_X - 5, cy - MEDAL_R - 8), 10, 10,
                               facecolor=col, edgecolor="none", zorder=4))
        ax.text(MEDAL_X, cy, MEDAL_TEXT[i], color="#1A1E43",
                fontsize=14, fontweight="bold", ha="center", va="center",
                zorder=6)

        ax.text(PROD_X, cy, name, color=TXT, fontsize=LBL_PT,
                ha="left", va="center", zorder=6)

        # blue value box
        ax.add_patch(Rectangle((VAL_BOX_X0, cy - VAL_BOX_H / 2),
                               VAL_BOX_X1 - VAL_BOX_X0, VAL_BOX_H,
                               facecolor=C_BLUE, edgecolor="none", zorder=3))
        ax.text((VAL_BOX_X0 + VAL_BOX_X1) / 2, cy, sales, color=TXT,
                fontsize=LBL_PT, ha="center", va="center", zorder=6)

        ax.text(QTY_X, cy, qty, color=TXT, fontsize=LBL_PT,
                ha="left", va="center", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "10_商品销售额Top3.png")
    save_fig(fig, out, facecolor=BG_PANEL)


if __name__ == "__main__":
    main()
