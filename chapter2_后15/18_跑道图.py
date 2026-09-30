# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第18张：跑道图（多层圆环弧）
源: 第二章 图表(后15).xlsx / 「18 跑道图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__18_跑道图__chart1.png
实现: 6 系列 doughnut（每系列 人数+占位），holeSize=45，firstSliceAng=0，
      描边 #1A1E43 w=3pt；userShapes 三文本框（标题/侧标签/脚注）
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# name, 人数, 占位, color（内->外 = ser0..ser5）
SERIES = [
    ("人力部", 130, 702, "#7030A0"),
    ("行政部", 226, 606, "#0070C0"),
    ("财务部", 238, 594, "#37A2DA"),
    ("工程部", 293, 539, "#11A7AD"),
    ("采购部", 326, 506, "#F5C353"),
    ("销售部", 451, 381, "#E74E69"),
]

TITLE = "2022年上半年各部门人数"
SUBTITLE = "公司总人数1664，销售部人数最多451，占比27%"
FOOTNOTE = "*注：数据来源于公司人力资源系统，统计日期截止2022.06.30"

# 参考图 832x622（y 向下像素坐标系）
W_PX, H_PX = 832, 622
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

# manualLayout inner + doughnut 外径实测
CX, CY = 374.2, 356.85
R_OUT = 201.5
HOLE = 0.45  # holeSize
LINE_W = 3.0  # 38100 EMU = 3pt

# 文本框 5（侧标签）from/to -> px；段落自上而下=销售->人力（外->内）
# ref 为 ~2px/pt 导出：sz/100 pt -> 2*sz/100 px
LAB_X0 = 301.0  # ref 字形左缘
LAB_PT = 14.0  # 7pt * 2
LAB_PITCH = 18.0  # lnSpc 9pt * 2
LAB_Y_C0 = 163.0  # 首行中心（ref y=157-169）

# 文本框 11（标题）：ref 标题字形 y=46-83, x=57；副标题 y=104-130
T_X0 = 57.0
TITLE_Y = 48.0  # va=top，字形顶≈46
SUB_Y = 105.0  # 字形顶≈104
TITLE_PT = 40.0  # 20pt * 2
SUB_PT = 28.0  # 14pt * 2

# 文本框 12（脚注）：ref y=582-596, x=40
F_X0 = 40.0
FOOT_Y = 582.0
FOOT_PT = 16.0  # 8pt * 2

# bg1 lumMod 95% / 85% 近似
LAB_C = "#F2F2F2"
FOOT_C = "#D9D9D9"


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    r_in_full = R_OUT * HOLE
    slot = (R_OUT - r_in_full) / len(SERIES)

    for i, (name, val, pad, color) in enumerate(SERIES):
        r0 = r_in_full + i * slot
        r1 = r_in_full + (i + 1) * slot
        sweep = 360.0 * val / (val + pad)
        # y 向下：12 点 = -90°，顺时针为正
        ax.add_patch(Wedge((CX, CY), r1, -90.0, -90.0 + sweep,
                           width=r1 - r0, facecolor=color,
                           edgecolor=BG, linewidth=LINE_W, zorder=3))

    # userShapes 段落顺序：销售->采购->工程->财务->行政->人力（外->内）
    for i, (name, val, pad, color) in enumerate(reversed(SERIES)):
        ly = LAB_Y_C0 + i * LAB_PITCH
        ax.text(LAB_X0, ly, f"{name} {val}", color=LAB_C, fontsize=LAB_PT,
                ha="left", va="center", zorder=6)

    ax.text(T_X0, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=6)
    ax.text(T_X0, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=6)
    ax.text(F_X0, FOOT_Y, FOOTNOTE, color=FOOT_C, fontsize=FOOT_PT,
            ha="left", va="top", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "18_跑道图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
