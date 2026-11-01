# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第19张：南丁格尔圆饼图（标准饼图+引线）
源: 第二章 图表(后15).xlsx / 「19 南丁格尔圆饼图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__19_南丁格尔圆饼图__chart1.png
实现: pieChart firstSliceAng=0，圆心(414,366) R=217；彩色引线+数据标签
"""
import os
import sys
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle
from matplotlib.lines import Line2D

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# name, 占比, color（ser0 dpts idx0..5）
SLICES = [
    ("销售部", 0.292, "#E74E69"),
    ("采购部", 0.227, "#F5C353"),
    ("工程部", 0.175, "#11A7AD"),
    ("财务部", 0.136, "#0070C0"),
    ("行政部", 0.103, "#37A2DA"),
    ("人力部", 0.067, "#7030A0"),
]
PCTS = ["29.2%", "22.7%", "17.5%", "13.6%", "10.3%", "6.7%"]

TITLE = "2021年各部门人数分布"
SUBTITLE = "公司总人数1664，销售部人数最多451，占比29.2%"
FOOTNOTE = "*注：数据来源于公司人力资源系统，统计日期截至2022.01.01"

W_PX, H_PX = 832, 622
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

CX, CY, R = 414.0, 366.0, 217.0

# ref 字形：title y=32-66 x=55；sub y=88-110；foot y=583-597 x=54
TITLE_Y, TITLE_PT = 33.0, 36.0  # sz=1800 * 2
SUB_Y, SUB_PT = 88.0, 24.0  # sz=1200 * 2
FOOT_X, FOOT_Y, FOOT_PT = 51.0, 582.0, 16.0  # sz=800 * 2
T_X = 53.0

# 引线（ref 实测，y 向下）：pie edge -> elbow -> horizontal end
# 各段为 (x0,y0)-(x1,y1) 折线
LEADERS = {
    0: [(586.0, 234.0), (652.0, 215.0), (773.0, 215.0)],  # 销售 E74E69
    1: [(560.0, 545.0), (596.0, 528.0), (716.0, 528.0)],  # 采购 F5C353
    2: [(300.0, 545.0), (258.0, 532.0), (133.0, 532.0)],  # 工程 11A7AD
    3: [(230.0, 420.0), (190.0, 393.0), (113.0, 393.0)],  # 财务 0070C0
    4: [(250.0, 300.0), (220.0, 252.0), (159.0, 252.0)],  # 行政 37A2DA
    # 人力 7030A0：ref 无外引线
}

# ref 实测：有彩色引线，无 dLbls 文字标签


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    # 饼：12 点起顺时针
    cum = 0.0
    mids = []
    for i, (name, frac, color) in enumerate(SLICES):
        a0 = cum * 360.0
        a1 = (cum + frac) * 360.0
        mids.append((a0 + a1) / 2.0)
        # y 向下：12点=-90，顺时针为 +
        ax.add_patch(Wedge((CX, CY), R, -90.0 + a0, -90.0 + a1,
                           facecolor=color, edgecolor="none", zorder=3))
        cum += frac

    # 引线
    for i, pts in LEADERS.items():
        color = SLICES[i][2]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, color=color, linewidth=1.5, solid_capstyle="butt",
                zorder=4)

    ax.text(T_X, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=6)
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=6)
    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "19_南丁格尔圆饼图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
