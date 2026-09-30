# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第20张：南丁格尔（PPT）
源: 第二章 图表(后15).xlsx / 「20 南丁格尔（PPT）」
参考: 无饼（noFill）+ 引线标签；标题/脚注来自 sheet userShapes
数据: 销售29.2 采购22.7 工程17.5 财务13.6 行政10.3 人力5（总1664）
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

W_PX, H_PX = 832, 622
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

TITLE = "2021年各部门人数分布"
SUB = "公司总人数1664，销售部人数最多451，占比29.2%"
FOOTNOTE = "*注：数据来源于公司人力资源系统，统计日期截至2022.01.01"

# ref 引线几何；标签放在水平段外侧（不压线）
# side: 'R'=标签在水平端右侧 ha=left；'L'=标签在水平端左侧 ha=right
LEADERS = [
    # 销售 右上（缩短水平段避免出界）
    ("#E74E69", [(624.0, 252.0), (653.0, 213.0), (700.0, 213.0)],
     "销售部  29.2%", "R"),
    # 采购 右下
    ("#F5C353", [(574.0, 492.0), (598.0, 528.0), (655.0, 528.0)],
     "采购部  22.7%", "R"),
    # 工程 左下
    ("#11A7AD", [(283.0, 497.0), (251.0, 536.0), (200.0, 536.0)],
     "工程部  17.5%", "L"),
    # 财务 左中
    ("#0070C0", [(261.0, 357.0), (231.0, 393.0), (175.0, 393.0)],
     "财务部  13.6%", "L"),
    # 行政 左上
    ("#37A2DA", [(338.0, 289.0), (315.0, 252.0), (255.0, 252.0)],
     "行政部  10.3%", "L"),
    # 人力 上中偏左
    ("#7030A0", [(394.0, 257.0), (371.0, 220.0), (320.0, 220.0)],
     "人力部  5.0%", "L"),
]

DOT_R = 5.0
LAB_PT = 16.0
T_X, T_Y, T_PT = 40.0, 24.0, 22.0
SUB_Y = 58.0
SUB_PT = 16.0
FOOT_X, FOOT_Y, FOOT_PT = 32.0, 572.0, 14.0
PAD = 8.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    ax.text(T_X, T_Y, TITLE, color=TXT, fontsize=T_PT,
            fontweight="bold", ha="left", va="top", zorder=6)
    ax.text(T_X, SUB_Y, SUB, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=6)

    for color, pts, lab, side in LEADERS:
        ax.plot([p[0] for p in pts], [p[1] for p in pts],
                color=color, linewidth=1.4, solid_capstyle="butt",
                solid_joinstyle="miter", zorder=4)
        ax.add_patch(Circle((pts[0][0], pts[0][1]), DOT_R,
                            facecolor=color, edgecolor="none", zorder=5))
        lx, ly = pts[-1]
        if side == "R":
            tx, ha = lx + PAD, "left"
        else:
            tx, ha = lx - PAD, "right"
        ax.text(tx, ly, lab, color=TXT, fontsize=LAB_PT,
                ha=ha, va="center", zorder=6)

    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "20_南丁格尔（PPT）.png")
    save_fig(fig, out, facecolor=BG)


if __name__ == "__main__":
    main()
