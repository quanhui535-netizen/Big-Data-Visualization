# -*- coding: utf-8 -*-
"""第四章 销售看板 第1张：推广费用（细圆环卡片）
源: 第四章 销售看板参考.xlsx / chart1
参考原图: D:\\Software\\node\\bipviz\\references\\ch4_sales__数据大屏__chart1.png
实现: doughnut holeSize=85 cyan 弧 + 灰占位；青边框圆角卡片；
      userShapes 推广费用合计/405.84/43.67%
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

W_PX, H_PX = 247, 197
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

CYAN = "#7BBDD5"
GRAY = "#454866"
TITLE_C = "#F2F2F2"

# ring measured cyan+gray bbox x33-117 y77-161
CX, CY, R = 75.0, 119.0, 42.0
HOLE = 0.85
FRAC = 0.43673875021477609

TITLE = "推广"
# label wraps 3+3 in ref bands y63-78 / y92-106
LAB_L1 = "推广费"
LAB_L2 = "用合计"
VALUE = "405.84"

# title band y25-43 x57-96 w40 -> fs21
T_X, T_Y, T_PT = 57.0, 25.0, 20.0
# label line tops
LAB_X, LAB_Y, LAB_DY = 141.0, 63.0, 29.0
LAB_PT = 16.0
# value 405.84 best at fs20 (mean/pct minimized)
VAL_X, VAL_Y, VAL_PT = 137.0, 132.0, 20.0
# percent
PCT_PT = 16.0
PCT1_X, PCT1_Y = 72.0, 114.0
PCT2_X, PCT2_Y = 57.0, 140.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    # solid fill border (no stroke AA): outer cyan + inner BG
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
    ax.text(VAL_X, VAL_Y, VALUE, color=TXT, fontsize=VAL_PT,
            ha="left", va="top", zorder=8)
    ax.text(PCT1_X, PCT1_Y, "43.67", color=TXT, fontsize=PCT_PT,
            ha="center", va="top", zorder=8)
    ax.text(PCT2_X, PCT2_Y, "%", color=TXT, fontsize=PCT_PT,
            ha="center", va="top", zorder=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "1_推广费用.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
