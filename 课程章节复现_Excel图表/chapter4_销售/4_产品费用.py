# -*- coding: utf-8 -*-
"""第四章 销售看板 第4张：产品费用（细圆环卡片）
源: 第四章 销售看板参考.xlsx / chart4
参考原图: ...\\ch4_sales__数据大屏__chart4.png
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

W_PX, H_PX = 246, 196
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

CYAN = "#7BBDD5"
GRAY = "#454866"
TITLE_C = "#F2F2F2"

# ring bbox x32-116 y86-171
CX, CY, R = 74.0, 128.5, 42.0
HOLE = 0.85
FRAC = 0.10800167364777508

TITLE = "产品"
LAB_L1 = "产品费"
LAB_L2 = "用合计"
VALUE1 = "100.3"
VALUE2 = "6"

# title y25-42 x58-96 w39 -> fs21
T_X, T_Y, T_PT = 58.0, 25.0, 20.0
# label y59 / y87 x139
LAB_X, LAB_Y, LAB_DY = 139.0, 59.0, 28.0
LAB_PT = 16.0
# value 100.3 best at fs18
VAL_X, VAL_Y, VAL_DY = 138.0, 122.0, 30.0
VAL_PT = 18.0
# pct
PCT_PT = 16.0
PCT1_X, PCT1_Y = 77.0, 122.0
PCT2_X, PCT2_Y = 60.0, 152.0


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
    ax.text(PCT1_X, PCT1_Y, "10.80", color=TXT, fontsize=PCT_PT,
            ha="center", va="top", zorder=8)
    ax.text(PCT2_X, PCT2_Y, "%", color=TXT, fontsize=PCT_PT,
            ha="center", va="top", zorder=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "4_产品费用.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
