# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第13张：对比折线图
源: 第二章 图表(前15).xlsx / 「13 对比折线图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__13_对比折线图__chart1.png
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

cats = ["1月", "2月", "3月", "4月", "5月", "6月"]
v2021 = [1686, 1345, 1934, 1658, 1865, 1936]
v2022 = [1385, 1846, 1654, 1936, 2564, 2236]

C21 = "#E74E69"
C22 = "#0070C0"

TITLE = "2022年上半年各月同比去年销量"
SUBTITLE = "上半年同比去年增长明显，5月份同比增长最多，增长近40%"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06.30"

W_IN = 416.0 / 72.0
H_IN = 308.0 / 72.0

# manualLayout chart12: x=0.13012 y=0.35889 w=0.81351 h=0.48976
PX, PY_TOP, PW, PH = 0.13012042612320518, 0.3588933815705469, 0.81350702485718696, 0.48976042613837895
PY = 1.0 - PY_TOP - PH


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([PX, PY, PW, PH])
    ax.set_facecolor(BG)

    x = np.arange(len(cats), dtype=float)
    ax.plot(x, v2021, color=C21, linewidth=1.5, marker="o", markersize=5,
            markerfacecolor=C21, markeredgecolor=C21, zorder=3,
            label="2021年")
    ax.plot(x, v2022, color=C22, linewidth=1.5, marker="o", markersize=5,
            markerfacecolor=C22, markeredgecolor=C22, zorder=3,
            label="2022年")

    ymax = 3000
    ax.set_xlim(-0.3, len(cats) - 0.7)
    ax.set_ylim(0, ymax)
    ax.set_yticks([0, 500, 1000, 1500, 2000, 2500, 3000])
    ax.tick_params(axis="y", length=0, colors=TXT_DIM, labelsize=9, pad=4)
    ax.set_xticks(x)
    ax.set_xticklabels(cats, color=TXT, fontsize=9)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.yaxis.grid(True, linestyle=(0, (6, 4)), linewidth=0.9,
                  color=TXT, alpha=0.18)
    ax.set_axisbelow(True)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    # 数据标签 pos=t（两线接近时避让）
    for xi, v21, v22 in zip(x, v2021, v2022):
        if v21 >= v22:
            ax.text(xi, v21 + ymax * 0.03, str(v21), ha="center", va="bottom",
                    color=C21, fontsize=9, zorder=5)
            ax.text(xi, v22 - ymax * 0.03, str(v22), ha="center", va="top",
                    color=C22, fontsize=9, zorder=5)
        else:
            ax.text(xi, v22 + ymax * 0.03, str(v22), ha="center", va="bottom",
                    color=C22, fontsize=9, zorder=5)
            ax.text(xi, v21 - ymax * 0.03, str(v21), ha="center", va="top",
                    color=C21, fontsize=9, zorder=5)

    # 手绘图例（顶部横排：—●—2021年 —●—2022年，参考图）
    ly = 1.04
    x0 = 0.60
    for xo, col, lab in ((x0, C21, "2021年"), (x0 + 0.22, C22, "2022年")):
        ax.plot([xo, xo + 0.06], [ly, ly], color=col, linewidth=1.5,
                marker="o", markersize=5, transform=ax.transAxes,
                clip_on=False, zorder=6)
        ax.text(xo + 0.08, ly, lab, color=TXT, fontsize=9,
                ha="left", va="center", transform=ax.transAxes, zorder=6)

    fig.text(0.04657, 1.0 - 0.05, TITLE, color=TXT, fontsize=20,
             fontweight="bold", ha="left", va="top")
    fig.text(0.04657, 1.0 - 0.15, SUBTITLE, color=TXT, fontsize=12,
             ha="left", va="top")
    fig.text(0.04565, 1.0 - 0.925, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "13_对比折线图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
