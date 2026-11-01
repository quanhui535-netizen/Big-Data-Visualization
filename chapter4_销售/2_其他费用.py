# -*- coding: utf-8 -*-
"""第四章 销售看板 第2张：其他费用（细圆环卡片）
源: 第四章 销售看板参考.xlsx / chart2
参考原图: ...\\ch4_sales__数据大屏__chart2.png
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, FancyBboxPatch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

W_PX, H_PX = 251, 196
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

CYAN = "#7BBDD5"
GRAY = "#454866"
TITLE_C = "#F2F2F2"

# ring bbox x25-111 y80-166
CX, CY, R = 68.0, 123.0, 43.0
HOLE = 0.85
FRAC = 0.22424893200827004

TITLE = "其他"
LAB_L1 = "其他费"
LAB_L2 = "用合计"
VALUE1 = "208.3"
VALUE2 = "8"

# title y26-43 x37-75 w39 -> fs21
T_X, T_Y, T_PT = 37.0, 26.0, 20.0
# label y60 / y88 x132
LAB_X, LAB_Y, LAB_DY = 132.0, 60.0, 28.0
LAB_PT = 16.0
# value 208.3 best at fs18
VAL_X, VAL_Y, VAL_DY = 130.0, 118.0, 42.0
VAL_PT = 18.0
# pct
PCT_X, PCT_Y, PCT_PT = 68.5, 129.0, 16.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    ax.add_patch(FancyBboxPatch(
        (0.2, 0.2), W_PX - 0.4, H_PX - 0.4,
        boxstyle="round,pad=0,rounding_size=14",
        facecolor=CYAN, edgecolor="none", zorder=5))
    ax.add_patch(FancyBboxPatch(
        (1.8, 1.8), W_PX - 3.6, H_PX - 3.6,
        boxstyle="round,pad=0,rounding_size=12.4",
        facecolor=BG, edgecolor="none", zorder=6))

    r0 = R * HOLE
    sweep = 360.0 * FRAC
    ax.add_patch(Wedge((CX, CY), R, -90.0, -90.0 + sweep, width=R - r0,
                       facecolor=CYAN, edgecolor="none", zorder=7))
    ax.add_patch(Wedge((CX, CY), R, -90.0 + sweep, 270.0, width=R - r0,
                       facecolor=GRAY, edgecolor="none", zorder=7))

    ax.text(T_X, T_Y, TITLE, color=TITLE_C, fontsize=T_PT,
            ha="left", va="top", zorder=8)
    ax.text(LAB_X, LAB_Y, LAB_L1, color=TITLE_C, fontsize=LAB_PT,
            ha="left", va="top", zorder=8)
    ax.text(LAB_X, LAB_Y + LAB_DY, LAB_L2, color=TITLE_C, fontsize=LAB_PT,
            ha="left", va="top", zorder=8)
    ax.text(VAL_X, VAL_Y, VALUE1, color=TXT, fontsize=VAL_PT,
            ha="left", va="top", zorder=8)
    ax.text(VAL_X, VAL_Y + VAL_DY, VALUE2, color=TXT, fontsize=VAL_PT,
            ha="left", va="top", zorder=8)
    ax.text(PCT_X, PCT_Y, "22.42%", color=TXT, fontsize=PCT_PT,
            ha="center", va="center", zorder=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "2_其他费用.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
