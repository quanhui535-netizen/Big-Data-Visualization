# -*- coding: utf-8 -*-
"""第四章 人力 第5张：学历（条形）
源: chart5 / 参考 ch4_hr__chart5.png
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

W_PX, H_PX = 252, 216
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

TITLE = "学历"
# display top-to-bottom (Excel plots first cat at bottom)
CATS = ["博士研究生", "硕士研究生", "本科", "专科", "专科以下"]
VALS = [48, 398, 572, 170, 282]

T_X, T_Y, T_PT = 126.5, 17.0, 14.0
LBL_PT = 10.0
BAR_X0 = 68.0
BAR_HW = 5.0
CYS = [66.0, 95.5, 125.5, 155.0, 185.0]
PPU = 0.2115
CAT_X1 = 58.0
VAL_GAP = 9.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    ax.text(T_X, T_Y, TITLE, color=TXT, fontsize=T_PT,
            ha="center", va="top", zorder=6)

    for cy, v, cat in zip(CYS, VALS, CATS):
        w = v * PPU
        ax.plot([BAR_X0, BAR_X0 + w], [cy, cy], color=BAR,
                linewidth=BAR_HW * 2, solid_capstyle="butt", zorder=3)
        ax.text(CAT_X1, cy, cat, color=TXT, fontsize=LBL_PT,
                ha="right", va="center", zorder=6)
        ax.text(BAR_X0 + w + VAL_GAP, cy, str(v), color=TXT,
                fontsize=LBL_PT, ha="left", va="center", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "5_学历.png")
    save_fig(fig, out, facecolor=BG)


if __name__ == "__main__":
    main()
