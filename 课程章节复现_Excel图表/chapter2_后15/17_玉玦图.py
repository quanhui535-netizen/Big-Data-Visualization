# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第17张：玉玦图（同心圆环弧）
源: 第二章 图表(后15).xlsx / 「17 玉玦图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__17_玉玦图__chart1.png
实现: 多系列 doughnut（每系列 占比+占位 noFill），firstSliceAng=0，holeSize=35
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# 内->外: name, 占比, 占位, color
SERIES = [
    (">=50", 0.125, 0.375, "#37A2DA"),
    ("[40,50)", 0.20833333333333334, 0.29166666666666663, "#11A7AD"),
    ("[30,40)", 0.2916666666666667, 0.20833333333333331, "#F5C353"),
    ("[20,30)", 0.375, 0.125, "#E74E69"),
]
RING_LABELS = ["[20,30)", "[30,40)", "[40,50)", ">=50"]

TITLE = "2022年上半年龄分布"
SUBTITLE = "公司平均年龄32.5，23-30员工比例最高"
FOOTNOTE = "*注：数据来源于公司人力资源系统，统计日期截至2022.06.30"

W_PX, H_PX = 834, 594
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

# 参考图实测（px，y 向下）
CX, CY = 420.5, 345.5
RING_R = [(66.0, 92.0), (95.0, 121.0), (125.0, 151.0), (155.0, 181.0)]

# showVal 参考图实测中心
DLBL_PTS = [(495.0, 361.0), (450.0, 444.0), (341.0, 445.0), (264.0, 322.0)]

LAB_X = 353.0
LAB_Y0 = 179.0
LAB_ROW = 30.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.axis("off")
    ax.set_facecolor(BG)

    for i, (name, p, pad, color) in enumerate(SERIES):
        total = p + pad
        sweep = 360.0 * p / total
        r0, r1 = RING_R[i]
        # y 向下：数据 CCW 显示为顺时针；12 点 = -90°
        theta1 = -90.0
        theta2 = -90.0 + sweep
        ax.add_patch(Wedge((CX, CY), r1, theta1, theta2, width=r1 - r0,
                           facecolor=color, edgecolor=BG, linewidth=1.2,
                           zorder=3))
        lx, ly = DLBL_PTS[i]
        ax.text(lx, ly, f"{p * 100:.1f}%", color=TXT, fontsize=9,
                ha="center", va="center", zorder=6)

    for i, lab in enumerate(RING_LABELS):
        ax.text(LAB_X, LAB_Y0 + i * LAB_ROW, lab, color=TXT_DIM, fontsize=11,
                ha="left", va="center", zorder=6)

    ax.text(59, 48, TITLE, color=TXT, fontsize=20, fontweight="bold",
            ha="left", va="top", zorder=6)
    ax.text(57, 104, SUBTITLE, color=TXT, fontsize=14, ha="left", va="top",
            zorder=6)
    ax.text(57, 558, FOOTNOTE, color=TXT_DIM, fontsize=8, ha="left",
            va="top", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "17_玉玦图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
