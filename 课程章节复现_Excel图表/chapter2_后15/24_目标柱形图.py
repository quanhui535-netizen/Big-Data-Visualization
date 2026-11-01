# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第24张：目标柱形图 (chart2)
源: 第二章 图表(后15).xlsx / 「24 目标柱形图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__24_目标柱形图__chart2.png
      (chart1 为 0 字节，使用 chart2)
实现: gapWidth=350 overlap=100 双系列；实柱 0070C0 + 目标灰轮廓(更宽)
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

W_PX, H_PX = 844, 589
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

CATS = ["口红", "面膜", "隔离", "防晒", "精华", "面霜"]
ACT = [653, 523, 648, 856, 714, 785]
TGT = [700, 500, 600, 900, 600, 600]

BAR_COLOR = "#0070C0"
TGT_COLOR = "#86889A"  # ref 实测 (134,136,154)
BAR_BOTTOM = 475.0

# ref 实测
ACT_CX = [122.5, 241.5, 361.0, 480.0, 599.5, 718.5]
ACT_W = 22.0
ACT_TOPS = [267.0, 308.0, 268.0, 202.0, 247.0, 224.0]
TGT_W = 32.0
TGT_TOPS = [252.0, 315.0, 284.0, 188.0, 284.0, 284.0]

LAB_PT = 16.0
# ref 实测标签顶部 y (va=top)
LAB_TOPS = [222.0, 283.0, 243.0, 167.0, 222.0, 200.0]

TITLE = "2022年上半年各商品销量完成情况"
SUBTITLE = "防晒整体销量最好，达到856，面霜远超目标，超额完成30%"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06.30"

T_X = 62.0
TITLE_Y, TITLE_PT = 39.0, 36.0
SUB_Y, SUB_PT = 95.0, 22.0
FOOT_X, FOOT_Y, FOOT_PT = 58.0, 548.0, 16.0

CAT_Y = 490.0

# legend: 目标销量 outline swatch + text, 实际销量 fill swatch + text
LEG_Y = 156.0
LEG_SWH = 9.0
LEG1_X, LEG1_SW_W = 96.0, 13.0   # outline swatch
LEG1_TX = 111.0
LEG2_X = 188.0                    # fill swatch
LEG2_TX = 203.0
LEG_SW_W = 9.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    # 目标轮廓（先画，实柱盖在上面）
    for i in range(6):
        cx = ACT_CX[i]
        x0 = cx - TGT_W / 2.0
        top = TGT_TOPS[i]
        h = BAR_BOTTOM - top
        ax.add_patch(Rectangle((x0, top), TGT_W, h, facecolor="none",
                               edgecolor=TGT_COLOR, linewidth=1.5, zorder=3))

    # 实柱
    for i in range(6):
        cx = ACT_CX[i]
        x0 = cx - ACT_W / 2.0
        top = ACT_TOPS[i]
        h = BAR_BOTTOM - top
        ax.add_patch(Rectangle((x0, top), ACT_W, h, facecolor=BAR_COLOR,
                               edgecolor="none", zorder=4))

    # 数据标签
    for i in range(6):
        ax.text(ACT_CX[i], LAB_TOPS[i], str(ACT[i]), color=TXT,
                fontsize=LAB_PT, ha="center", va="top", zorder=6)

    # 类目
    for i in range(6):
        ax.text(ACT_CX[i], CAT_Y, CATS[i], color=TXT, fontsize=LAB_PT,
                ha="center", va="top", zorder=6)

    # legend
    ax.add_patch(Rectangle((LEG1_X, LEG_Y), LEG1_SW_W, LEG_SWH,
                           facecolor="none", edgecolor=TGT_COLOR,
                           linewidth=1.2, zorder=6))
    ax.text(LEG1_TX, LEG_Y + LEG_SWH / 2.0, "目标销量", color=TXT,
            fontsize=LAB_PT, ha="left", va="center", zorder=6)
    ax.add_patch(Rectangle((LEG2_X, LEG_Y), LEG_SW_W, LEG_SWH,
                           facecolor=BAR_COLOR, edgecolor="none", zorder=6))
    ax.text(LEG2_TX, LEG_Y + LEG_SWH / 2.0, "实际销量", color=TXT,
            fontsize=LAB_PT, ha="left", va="center", zorder=6)

    # 文本
    ax.text(T_X, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=8)
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=8)
    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "24_目标柱形图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
