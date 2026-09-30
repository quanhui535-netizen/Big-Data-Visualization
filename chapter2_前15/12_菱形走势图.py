# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第12张：菱形走势图（折线无连线可见 + 菱形标记 + 竖线）
源: 第二章 图表(前15).xlsx / 「12 菱形走势图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__12_菱形走势图__chart1.png
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

cats = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月"]
vals = [0.536, 0.498, 0.527, 0.708, 0.609, 0.496, 0.586, 0.704]

C_LINE = "#E74E69"

TITLE = "2022年1-8月公司计划完成率"
SUBTITLE = "公司整体完成率55%，4月和8月超过70%，2月和6月较低未过半"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.08.31"

W_IN = 416.0 / 72.0
H_IN = 308.0 / 72.0

# manualLayout chart11: x=0.08085 y=0.27728 w=0.86526 h=0.54678
PX, PY_TOP, PW, PH = 0.080845188119866157, 0.27727852489010746, 0.8652580198002231, 0.54677535345127803
PY = 1.0 - PY_TOP - PH


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([PX, PY, PW, PH])
    ax.set_facecolor(BG)

    x = np.arange(len(cats), dtype=float)
    # 竖线 stem + 菱形（原图线系列 line noFill 近似，实际是柱状竖线+菱形标记）
    for xi, v in zip(x, vals):
        ax.plot([xi, xi], [0, v], color=C_LINE, linewidth=1.4, zorder=2)
        # 菱形空心
        ax.plot([xi], [v], marker="D", markersize=8, markerfacecolor=BG,
                markeredgecolor=C_LINE, markeredgewidth=1.4, zorder=4)
        ax.text(xi, v + 0.04, f"{v:.2%}", ha="center", va="bottom",
                color=TXT, fontsize=9, zorder=5)

    ax.set_xlim(-0.5, len(cats) - 0.5)
    ax.set_ylim(0, 0.90)
    ax.set_xticks(x)
    ax.set_xticklabels(cats, color=TXT, fontsize=9)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.yaxis.set_visible(False)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(TXT)
    ax.spines["bottom"].set_linewidth(1.0)

    fig.text(0.0493, 1.0 - 0.05, TITLE, color=TXT, fontsize=20,
             fontweight="bold", ha="left", va="top")
    fig.text(0.0493, 1.0 - 0.16, SUBTITLE, color=TXT, fontsize=12,
             ha="left", va="top")
    fig.text(0.0539, 1.0 - 0.92, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "12_菱形走势图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
