# -*- coding: utf-8 -*-
"""第四章 人力 第2张：婚姻状况（环形图）
源: chart2 / 参考 ch4_hr__chart2.png
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Rectangle

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BG = "#1D244A"
TXT = "#F2F2F2"

W_PX, H_PX = 252, 152
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

TITLE = "婚姻状况"
CATS = ["单身", "已婚", "离异"]
VALS = [470, 673, 327]
COLORS = ["#EDA530", "#0070C0", "#7AD5FE"]
PCTS = ["32%", "46%", "22%"]

CX, CY, R = 101.5, 94.0, 34.5
HOLE = 0.75

T_X, T_Y, T_PT = 125.5, 17.0, 14.0
LBL_PT = 10.0

# order matches VALS: 单身32% 右上, 已婚46% 下, 离异22% 左上
PL_XY = [(154.0, 68.5), (73.5, 138.5), (60.0, 57.5)]

LEG_SW_X, LEG_SW_W = 210.0, 6.0
LEG_TX_X = 218.0
LEG_Y0, LEG_DY = 72.5, 21.5


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    total = float(sum(VALS))
    # ylim(H,0) flipped: data 270°=top, increasing angle=CW on screen
    start = 270.0
    for v, c in zip(VALS, COLORS):
        sweep = 360.0 * v / total
        ax.add_patch(Wedge((CX, CY), R, start, start + sweep, width=R * (1 - HOLE),
                           facecolor=c, edgecolor="none", zorder=3))
        start += sweep

    ax.text(T_X, T_Y, TITLE, color=TXT, fontsize=T_PT,
            ha="center", va="top", zorder=6)

    for (px, py), p in zip(PL_XY, PCTS):
        ax.text(px, py, p, color=TXT, fontsize=LBL_PT,
                ha="center", va="center", zorder=6)

    for i, cat in enumerate(CATS):
        y = LEG_Y0 + i * LEG_DY
        ax.add_patch(Rectangle((LEG_SW_X, y - 3), LEG_SW_W, 6,
                               facecolor=COLORS[i], edgecolor="none", zorder=5))
        ax.text(LEG_TX_X, y, cat, color=TXT, fontsize=LBL_PT,
                ha="left", va="center", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "2_婚姻状况.png")
    save_fig(fig, out, facecolor=BG)


if __name__ == "__main__":
    main()
