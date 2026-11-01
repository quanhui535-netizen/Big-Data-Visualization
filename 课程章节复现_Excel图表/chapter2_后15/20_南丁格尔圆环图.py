# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第20张：南丁格尔圆环图
源: 第二章 图表(后15).xlsx / 「20 南丁格尔圆环图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__20_南丁格尔圆环图__chart1.png
实现: doughnut holeSize=60 firstSliceAng=0；内缘对齐阶梯环
      （共享 R_IN，段外径=R_IN+n*W，环数 紫5/蓝4/青3/黄2）+ 引线标签
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle, Arc
from matplotlib.colors import to_rgb

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def darken(color, f=0.62):
    r, g, b = to_rgb(color)
    return (r * f, g * f, b * f)


# cat, frac, color, n_rings（内缘对齐，外径= R_IN + n*W）
SLICES = [
    ("[20,30)", 0.375, "#512DCB", 5),
    ("[30,40)", 0.29166666666666669, "#6073F3", 4),
    ("[40,50)", 0.20833333333333334, "#66CBDD", 3),
    (">=50", 0.125, "#F5C353", 2),
]
PCTS = ["37.5%", "29.2%", "20.8%", "12.5%"]

TITLE = "2022年上半各年龄段人数分布"
SUBTITLE = "公司平均年龄32.5，20-30员工比例最高占比37.5%"
FOOTNOTE = "*注：数据来源于公司人力资源系统，统计日期截至2022.06.30"

W_PX, H_PX = 835, 624
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

CX, CY = 417.0, 375.0
R_IN = 107.0
RING_W = 14.2  # 5环=71 → 外径紫=178

TITLE_Y, TITLE_PT = 31.0, 36.0
SUB_Y, SUB_PT = 87.0, 24.0
FOOT_X, FOOT_Y, FOOT_PT = 51.0, 585.0, 16.0
T_X = 53.0

LAB_PT = 16.0
LABELS = [
    ("[20,30)", (674.0, 179.0), "37.5%", (676.0, 201.0), 0),
    (">=50", (219.0, 142.0), "12.5%", (218.0, 163.0), 3),
    ("[40,50)", (126.0, 329.0), "20.8%", (126.0, 347.0), 2),
    ("[30,40)", (609.0, 523.0), "29.2%", (609.0, 541.0), 1),
]

LEADERS = [
    (0, [(769.0, 221.0), (645.0, 221.0), (612.0, 259.0)], (612.0, 259.0)),
    (3, [(241.0, 191.0), (266.0, 191.0), (320.0, 226.0)], (320.0, 226.0)),
    (2, [(79.0, 379.0), (217.0, 379.0), (246.0, 341.0)], (246.0, 341.0)),
    (1, [(694.0, 572.0), (558.0, 572.0), (532.0, 532.0)], (532.0, 532.0)),
]


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    cum = 0.0
    for name, frac, color, n_show in SLICES:
        t1 = -90.0 + cum * 360.0
        t2 = -90.0 + (cum + frac) * 360.0
        r_out = R_IN + n_show * RING_W
        ax.add_patch(Wedge((CX, CY), r_out, t1, t2,
                           width=r_out - R_IN, facecolor=color,
                           edgecolor="none", zorder=3))
        dc = darken(color, 0.62)
        for i in range(1, n_show):
            r = R_IN + i * RING_W
            ax.add_patch(Arc((CX, CY), 2 * r, 2 * r, theta1=t1, theta2=t2,
                             linewidth=1.1, edgecolor=dc, zorder=4))
        cum += frac

    for si, pts, dot in LEADERS:
        color = SLICES[si][2]
        ax.plot([p[0] for p in pts], [p[1] for p in pts],
                color=color, linewidth=1.5, solid_capstyle="butt",
                solid_joinstyle="miter", zorder=4)
        ax.add_patch(Circle(dot, 4.0, facecolor=color, edgecolor="none",
                            zorder=5))

    for cat, cxy, pct, pxy, si in LABELS:
        color = SLICES[si][2]
        ax.text(cxy[0], cxy[1], cat, color=TXT, fontsize=LAB_PT,
                ha="left", va="top", zorder=6)
        ax.text(pxy[0], pxy[1], pct, color=color, fontsize=LAB_PT,
                ha="left", va="top", zorder=6)

    ax.text(T_X, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=6)
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=6)
    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "20_南丁格尔圆环图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
