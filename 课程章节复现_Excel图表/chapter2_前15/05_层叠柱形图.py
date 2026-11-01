# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第5张：层叠柱形图（实际为簇状双系列，overlap=30）
源: 第二章 图表(前15).xlsx / 「5 层叠柱形图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__5_层叠柱形图__chart1.png
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

categories = ["2021Q1", "Q2", "Q3", "Q4", "2022Q1", "Q2"]
sales = [3121, 4086, 4321, 4601, 4936, 4231]
profit = [1020, 1421, 1502, 1623, 1781, 1432]

C_SALES = "#0070C0"
C_PROFIT = "#E74E69"

TITLE = "2021年至今季度销售额(万)和利润额(万)"
SUBTITLE = "2022年第二季度销售额首次出现下降，降幅达到15%"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06.30"
LEGEND_SALES = "销售额"
LEGEND_PROFIT = "利润额"

W_IN = 416.0 / 72.0
H_IN = 294.0001525878906 / 72.0
GAP_W = 219.0
OVERLAP = 30.0
group_w = 1.0 / (1.0 + GAP_W / 100.0)
bar_w = group_w * 0.35
offset = group_w * 0.17

# 布局：底部留足空间，类目一行、脚注一行互不重叠
# axes: [left, bottom, width, height]
PLOT = [0.055, 0.235, 0.92, 0.50]


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes(PLOT)
    ax.set_facecolor(BG)

    x = np.arange(len(categories), dtype=float)
    for xi, v in zip(x, sales):
        ax.bar(xi - offset, v, width=bar_w, color=C_SALES, zorder=2, linewidth=0)
    for xi, v in zip(x, profit):
        ax.bar(xi + offset, v, width=bar_w, color=C_PROFIT, zorder=2, linewidth=0)

    ymax = 5600
    ax.set_xlim(-0.5, len(categories) - 0.5)
    ax.set_ylim(0, ymax)
    ax.yaxis.set_visible(False)
    ax.xaxis.set_visible(False)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    # 底部白线
    ax.axhline(0, color=TXT, linewidth=1.0, zorder=3)

    # 类目标签：紧贴白线下方
    trans = ax.get_xaxis_transform()
    for xi, c in zip(x, categories):
        ax.text(xi, -0.06, c, ha="center", va="top", color=TXT,
                fontsize=9, zorder=4, transform=trans, clip_on=False)

    # 数据标签 outEnd
    for xi, v in zip(x, sales):
        ax.text(xi - offset, v + ymax * 0.018, str(v), ha="center",
                va="bottom", color=TXT, fontsize=9, zorder=5)
    for xi, v in zip(x, profit):
        ax.text(xi + offset, v + ymax * 0.018, str(v), ha="center",
                va="bottom", color=TXT, fontsize=9, zorder=5)

    # 自定义图例：放在 2022Q1 与 Q2 柱组之间的上方空白，避开所有数字
    # 2022Q1 柱顶约 4936，其左侧空白；或放图区中部偏右无柱处
    # 最稳妥：图区左上角空白（max 柱 4936 在中间，左侧较低）
    # 原图在右侧，但必须避开 4231/1432 —— 放 4231 左侧、4936 右下空白
    ax.text(5.02, 3200, LEGEND_SALES, ha="left", va="center",
            color=TXT, fontsize=8, zorder=6,
            bbox=dict(boxstyle="round,pad=0.28", facecolor=C_SALES,
                      edgecolor=TXT, linewidth=0.8))
    ax.text(5.02, 2700, LEGEND_PROFIT, ha="left", va="center",
            color=TXT, fontsize=8, zorder=6,
            bbox=dict(boxstyle="round,pad=0.28", facecolor="none",
                      edgecolor=C_PROFIT, linewidth=1.0))

    # 标题 / 副标题（图区上方）
    fig.text(0.03921, 0.945, TITLE, color=TXT, fontsize=20,
             fontweight="bold", ha="left", va="top")
    fig.text(0.03921, 0.855, SUBTITLE, color=TXT, fontsize=12,
             ha="left", va="top")

    # 脚注：与类目行明显分开，贴底
    fig.text(0.02911, 0.035, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "05_层叠柱形图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
