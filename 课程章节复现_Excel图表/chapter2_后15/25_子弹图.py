# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第25张：子弹图 (chart2)
源: 第二章 图表(后15).xlsx / 「25 子弹图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__25_子弹图__chart2.png
      (chart1 为 0 字节，使用 chart2)
实现: 堆叠背景(及格/良好/优秀)全宽33 + 实际亮蓝19居中 + 目标黄线20
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

W_PX, H_PX = 842, 589
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

CATS = ["口红", "面膜", "隔离", "防晒", "精华", "面霜"]
ACT = [653, 523, 648, 856, 714, 785]
TGT = [700, 500, 600, 900, 600, 600]

C_QUAL1 = "#82ADD7"  # 及格 0-600 (130,173,215)
C_QUAL2 = "#0885BC"  # 良好 600-800 (8,133,188)
C_QUAL3 = "#0070C0"  # 优秀 800-1000 (0,112,192)
C_ACT = "#0E5DFF"    # 实际 (14,93,255)
C_TGT = "#FFC000"    # 目标 (255,192,0)

BASE_Y = 489.0
PPU = 0.2637         # px per data unit (ref 实测)


def yv(v):
    return BASE_Y - v * PPU


BAR_CX = [165.0, 280.0, 396.0, 511.0, 627.0, 742.0]
FULL_W = 33.0
ACT_W = 19.0
TGT_W = 20.0
TGT_H = 4.0

QUAL_TOPS = [1000.0, 800.0, 600.0]  # stacked segments tops
QUAL_BOT = [800.0, 600.0, 0.0]
QUAL_COLS = [C_QUAL3, C_QUAL2, C_QUAL1]

TITLE = "2022年上半年各商品销量完成情况"
SUBTITLE = "防晒整体销量最好，达到856，面霜远超目标，超额完成30%"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06.30"

T_X = 54.0
TITLE_Y, TITLE_PT = 39.0, 36.0
SUB_Y, SUB_PT = 95.0, 22.0
FOOT_X, FOOT_Y, FOOT_PT = 53.0, 550.0, 16.0

LAB_PT = 16.0
# y-axis labels (right-aligned x=88, va=center)
Y_LAB = [(1200, 170.0), (1000, 224.0), (800, 277.0),
         (600, 330.0), (400, 383.0), (200, 436.0), (0, 489.0)]
CAT_Y = 505.0

# legend: swatch_x, text_x, color, label, is_line
LEG_CY = 174.0
LEGEND = [
    (152.0, 167.0, C_QUAL1, "及格", False),
    (219.0, 236.0, C_QUAL2, "良好", False),
    (286.0, 301.0, C_QUAL3, "优秀", False),
    (352.0, 369.0, C_ACT, "实际", False),
    (419.0, 437.0, C_TGT, "目标", True),
]
LEG_SW = 10.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    # 底部轴线
    ax.plot([140.0, 760.0], [489.5, 489.5], color="#3A3F6B",
            linewidth=1.0, zorder=2)

    # 堆叠背景条
    for i in range(6):
        cx = BAR_CX[i]
        x0 = cx - FULL_W / 2.0
        for j in range(3):
            top = yv(QUAL_TOPS[j])
            bot = yv(QUAL_BOT[j])
            ax.add_patch(Rectangle((x0, top), FULL_W, bot - top,
                                   facecolor=QUAL_COLS[j],
                                   edgecolor="none", zorder=3))

    # 实际条
    for i in range(6):
        cx = BAR_CX[i]
        x0 = cx - ACT_W / 2.0
        top = yv(ACT[i])
        ax.add_patch(Rectangle((x0, top), ACT_W, BASE_Y - top,
                               facecolor=C_ACT, edgecolor="none", zorder=4))

    # 目标线
    for i in range(6):
        cx = BAR_CX[i]
        x0 = cx - TGT_W / 2.0
        y = yv(TGT[i])
        ax.add_patch(Rectangle((x0, y - TGT_H / 2.0), TGT_W, TGT_H,
                               facecolor=C_TGT, edgecolor="none", zorder=5))

    # y 轴标签
    for val, y in Y_LAB:
        ax.text(88.0, y, str(val), color=TXT, fontsize=LAB_PT,
                ha="right", va="center", zorder=6)

    # 类目标签
    for i in range(6):
        ax.text(BAR_CX[i], CAT_Y, CATS[i], color=TXT, fontsize=LAB_PT,
                ha="center", va="top", zorder=6)

    # legend
    for sx, tx, col, lab, is_line in LEGEND:
        if is_line:
            ax.plot([sx, sx + LEG_SW], [LEG_CY, LEG_CY], color=col,
                    linewidth=2.5, solid_capstyle="butt", zorder=6)
        else:
            ax.add_patch(Rectangle((sx, LEG_CY - LEG_SW / 2.0),
                                   LEG_SW, LEG_SW, facecolor=col,
                                   edgecolor="none", zorder=6))
        ax.text(tx, LEG_CY, lab, color=TXT, fontsize=LAB_PT,
                ha="left", va="center", zorder=6)

    # 文本
    ax.text(T_X, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=8)
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=8)
    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "25_子弹图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
