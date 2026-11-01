# -*- coding: utf-8 -*-
"""第四章 销售看板 第6张：区域销量（柱形）
源: 第四章 销售看板参考.xlsx / chart6
参考原图: ...\\ch4_sales__数据大屏__chart6.png
实现: 青柱 #7BBDD5，bg #2C3560，柱顶数据标签
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import TXT, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BG_PANEL = "#2C3560"
CYAN = "#7BBDD5"

W_PX, H_PX = 553, 265
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

TITLE = "区域销量"
CATS = ["华北", "华南", "东北", "西北", "西南", "华东"]
VALS = [128, 295, 109, 51, 29, 139]

BASE_Y = 212.5
PPU = 96.5 / 295.0
BAR_HW = 13.0
CXS = [64.0, 148.5, 233.5, 318.5, 403.0, 488.0]

T_X, T_Y, T_PT = W_PX / 2.0, 25.0, 16.0
LBL_PT = 16.0
CAT_Y = 232.0
VAL_DY = -8.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG_PANEL)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG_PANEL)
    ax.axis("off")

    ax.text(T_X, T_Y, TITLE, color=TXT, fontsize=T_PT,
            ha="center", va="top", zorder=6)

    for i, (cx, v) in enumerate(zip(CXS, VALS)):
        h = v * PPU
        ax.plot([cx, cx], [BASE_Y, BASE_Y - h], color=CYAN,
                linewidth=BAR_HW * 2, solid_capstyle="butt", zorder=3)
        ax.text(cx, BASE_Y - h + VAL_DY, str(v), color=TXT,
                fontsize=LBL_PT, ha="center", va="bottom", zorder=6)
        ax.text(cx, CAT_Y, CATS[i], color=TXT, fontsize=LBL_PT,
                ha="center", va="top", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "6_区域销量.png")
    save_fig(fig, out, facecolor=BG_PANEL)


if __name__ == "__main__":
    main()
