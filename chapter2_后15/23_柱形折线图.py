# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第23张：柱形折线图
源: 第二章 图表(后15).xlsx / 「23 柱形折线图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__23_柱形折线图__chart1.png
实现: barChart gapWidth=219 overlap=-27 + lineChart 双轴；
      柱 0070C0 数据标签在上；折线 E74E69 marker circle5 百分比标签在上
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

W_PX, H_PX = 832, 594
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

CATS = ["2017", "2018", "2019", "2020", "2021", "2022"]
BARS = [1603, 2106, 2406, 3265, 3721, 3921]
PCTS = [0.27, 0.31378665003119144, 0.14245014245014254,
        0.35702410640066495, 0.1396630934150076, 5.3748992206396062e-2]
PCT_LAB = ["27%", "31%", "14%", "36%", "14%", "5%"]

BAR_COLOR = "#0070C0"
LINE_COLOR = "#E74E69"

TITLE = "近六年销售量及增长率"
SUBTITLE = "平台销量近6年持续增长，但近两年增长率有所放缓"
FOOTNOTE = "*注：数据来源于公司销售系统"

T_X = 53.0
TITLE_Y, TITLE_PT = 41.0, 36.0
SUB_Y, SUB_PT = 96.0, 23.0
FOOT_X, FOOT_Y, FOOT_PT = 50.0, 559.0, 16.0

# ref 实测：柱底 y=498，柱宽~37，中心 x
BAR_BOTTOM = 498.0
BAR_W = 37.0
BAR_CX = [121.0, 238.5, 356.0, 473.0, 590.0, 707.5]
BAR_TOPS = [405.0, 376.0, 358.0, 308.0, 281.0, 270.0]

# 折线点 y（右轴 min=-1.2 max=0.5，plot y=148..498）
LINE_Y = [195.4, 186.3, 221.8, 177.4, 222.1, 239.7]

BAR_LAB_Y = [380.0, 351.0, 333.0, 283.0, 253.0, 253.0]
PCT_LAB_Y = [160.0, 160.0, 191.0, 155.0, 191.0, 209.0]
PCT_LAB_X = [121.0, 238.0, 355.5, 472.0, 590.5, 707.5]

LAB_PT = 16.0

# legend top-right
LEG = [
    ("bar", 558.0, 150.0, 37.0, 8.0, "销售量", 601.0, 154.0),
    ("line", 665.0, 152.5, 41.0, 0.0, "同比", 711.0, 154.0),
]


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    # 柱
    from matplotlib.patches import Rectangle
    for i in range(6):
        x0 = BAR_CX[i] - BAR_W / 2.0
        h = BAR_BOTTOM - BAR_TOPS[i]
        ax.add_patch(Rectangle((x0, BAR_BOTTOM - h), BAR_W, h,
                               facecolor=BAR_COLOR, edgecolor="none", zorder=3))

    # 柱数据标签
    for i in range(6):
        ax.text(BAR_CX[i], BAR_LAB_Y[i], str(BARS[i]), color=TXT,
                fontsize=LAB_PT, ha="center", va="top", zorder=6)

    # 折线
    ax.plot(BAR_CX, LINE_Y, color=LINE_COLOR, linewidth=2.5,
            solid_capstyle="round", zorder=5)
    for i in range(6):
        ax.scatter([BAR_CX[i]], [LINE_Y[i]], s=50, color=LINE_COLOR,
                   edgecolors="none", zorder=6)

    # 百分比标签
    for i in range(6):
        ax.text(PCT_LAB_X[i], PCT_LAB_Y[i], PCT_LAB[i], color=TXT,
                fontsize=LAB_PT, ha="center", va="top", zorder=6)

    # 类目标签
    for i in range(6):
        ax.text(BAR_CX[i], 516.0, CATS[i], color=TXT, fontsize=LAB_PT,
                ha="center", va="top", zorder=6)

    # legend
    for kind, lx, ly, lw, lh, text, tx, ty in LEG:
        if kind == "bar":
            ax.add_patch(Rectangle((lx, ly), lw, lh, facecolor=BAR_COLOR,
                                   edgecolor="none", zorder=6))
        else:
            ax.plot([lx, lx + lw], [ly, ly], color=LINE_COLOR, linewidth=2.5,
                    zorder=6)
            ax.scatter([lx + lw / 2.0], [ly], s=40, color=LINE_COLOR,
                       edgecolors="none", zorder=6)
        ax.text(tx, ty, text, color=TXT, fontsize=LAB_PT,
                ha="left", va="center", zorder=6)

    # 文本
    ax.text(T_X, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=8)
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=8)
    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "23_柱形折线图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
