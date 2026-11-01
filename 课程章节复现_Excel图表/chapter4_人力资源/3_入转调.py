# -*- coding: utf-8 -*-
"""第四章 人力 第3张：入转调（柱形）
源: chart3 / userShapes 总人数：1470 / 参考 ch4_hr__chart3.png
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BG = "#1D244A"
TXT = "#F2F2F2"
BAR = "#7AD5FE"

W_PX, H_PX = 256, 216
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

US_X, US_Y, US_PT = 131.5, 20.0, 15.0
US_TEXT = "总人数：1470"

TITLE = "入转调"
T_X, T_Y, T_PT = 131.5, 57.0, 14.0

CATS = ["入职", "转入", "转出"]
VALS = [40, 5, 5]
CXS = [53.0, 127.5, 202.0]
BASE_Y = 182.0
PPU = 2.0
BAR_HW = 11.5
LBL_PT = 10.0
CAT_Y = 192.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    ax.text(US_X, US_Y, US_TEXT, color=TXT, fontsize=US_PT,
            ha="center", va="top", zorder=7, fontweight="bold")
    ax.text(T_X, T_Y, TITLE, color=TXT, fontsize=T_PT,
            ha="center", va="top", zorder=6)

    for cx, v, cat in zip(CXS, VALS, CATS):
        h = v * PPU
        ax.plot([cx, cx], [BASE_Y, BASE_Y - h], color=BAR,
                linewidth=BAR_HW * 2, solid_capstyle="butt", zorder=3)
        ax.text(cx, BASE_Y - h - 5, str(v), color=TXT,
                fontsize=LBL_PT, ha="center", va="bottom", zorder=6)
        ax.text(cx, CAT_Y, cat, color=TXT, fontsize=LBL_PT,
                ha="center", va="top", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "3_入转调.png")
    save_fig(fig, out, facecolor=BG)


if __name__ == "__main__":
    main()
