# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第4张：标注柱形图
源: 第二章 图表(前15).xlsx / 「4 标注柱形图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__4_标注柱形图__chart1.png
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, GRID, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

categories = ["口红", "面膜", "隔离", "防晒", "精华", "面霜", "眼影", "气垫"]
sales = [9221, 5102, 6571, 5760, 6321, 8612, 2645, 5321]
# dPt 逐点着色（idx0 用系列默认色）
COLORS = [
    "#7BBDD5",  # 0 default
    "#49A098",
    "#E66B4C",
    "#FFC000",
    "#0097E0",
    "#0070C0",
    "#4A5BD1",
    "#464CAC",
]

TITLE = "2021年商品销量情况"
SUBTITLE = "口红销量最好达9221，是眼影最低值2645近3.5倍"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.08.31"

W_IN = 416.0 / 72.0
H_IN = 308.0000915527344 / 72.0
GAP_W = 100.0
BAR_FRAC = 1.0 / (1.0 + GAP_W / 100.0)
YMAX = 11000  # majorUnit 2000, max 到 10000+


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    # 从原图估 plot 区
    ax = fig.add_axes([0.11, 0.16, 0.86, 0.55])
    ax.set_facecolor(BG)

    x = np.arange(len(categories))
    hw = BAR_FRAC / 2.0
    for xi, v, c in zip(x, sales, COLORS):
        ax.bar(xi, v, width=BAR_FRAC, color=c, zorder=2, linewidth=0)

    ax.set_xlim(-0.5, len(categories) - 0.5)
    ax.set_ylim(0, YMAX)
    yticks = list(range(0, 10001, 2000))
    ax.set_yticks(yticks)
    ax.set_xticks(x)
    ax.set_xticklabels(categories)

    ax.tick_params(axis="y", length=0, colors=TXT_DIM, labelsize=9, pad=3)
    ax.tick_params(axis="x", length=0, pad=4)
    for lab in ax.get_xticklabels():
        lab.set_fontsize(9)
        lab.set_color(TXT)
    ax.yaxis.grid(True, linestyle=(0, (5, 4)), linewidth=0.9,
                  color=GRID, alpha=0.2)
    ax.set_axisbelow(True)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    # 标注气泡标签（圆角矩形 + 指向柱顶的小三角近似用圆角块+圆点）
    for xi, v, c in zip(x, sales, COLORS):
        # 气泡底
        bx, by = xi - 0.16, v + YMAX * 0.035
        bubble = FancyBboxPatch(
            (bx, by), 0.32, YMAX * 0.07,
            boxstyle="round,pad=0.012,rounding_size=0.03",
            facecolor="#3D4670", edgecolor="none", zorder=4,
            mutation_aspect=0.4, transform=ax.transData, clip_on=False,
        )
        ax.add_patch(bubble)
        # 连接圆点（柱顶）
        ax.plot([xi], [v + YMAX * 0.018], marker="o", markersize=5,
                color=c, zorder=5, clip_on=False)
        ax.text(xi, by + YMAX * 0.035, str(v), ha="center", va="center",
                color=TXT, fontsize=9, zorder=6)

    fig.text(0.04779, 1.0 - 0.04899, TITLE, color=TXT, fontsize=18,
             fontweight="bold", ha="left", va="top")
    fig.text(0.04779, 1.0 - 0.135, SUBTITLE, color=TXT, fontsize=12,
             ha="left", va="top")
    fig.text(0.03984, 1.0 - 0.92048, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "04_标注柱形图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
