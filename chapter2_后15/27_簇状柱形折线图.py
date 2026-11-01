# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第27张：簇状柱形折线图
源: 第二章 图表(后15).xlsx / 「27 簇状柱形折线图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__27_簇状柱形折线图__chart1.png
实现: 簇状双柱(蓝0070C0 2022/粉E74E69 2021) gap=219 ov=-27
      + 黄FFC000折线圆点 + 右侧图例 2022/2021
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

W_PX, H_PX = 832, 616
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

CATS = ["华北", "华南", "东北", "西北", "西南", "华东"]
V22 = [2354, 1902, 3524, 2698, 2896, 2563]
V21 = [2021, 1563, 3213, 2531, 2631, 2361]
PCTS = ["16%", "22%", "10%", "7%", "10%", "9%"]

C_BLUE = "#0070C0"
C_PINK = "#E74E69"
C_LINE = "#FFC000"

BAR_BOTTOM = 520.0
BAR_W = 26.0
BLUE_CX = [108.5, 226.0, 343.0, 460.0, 577.5, 695.0]
PINK_CX = [142.5, 259.5, 376.5, 493.5, 610.5, 727.5]
BLUE_TOPS = [352.0, 385.0, 269.0, 328.0, 314.0, 337.0]
PINK_TOPS = [376.0, 409.0, 291.0, 340.0, 333.0, 352.0]

# 折线标记中心 (ref 实测)
LINE_CX = [125.5, 242.5, 359.5, 476.5, 593.5, 710.5]
LINE_CY = [199.0, 184.0, 214.0, 222.0, 214.0, 217.0]
LINE_R = 5.0

LAB_PT = 16.0
# 柱数据标签 y (va=top) ref 白字带
LAB22_Y = [327.0, 360.0, 244.0, 303.0, 289.0, 312.0]
LAB21_Y = [351.0, 384.0, 266.0, 310.0, 308.0, 322.0]
# 折线%标签 y (va=top)
PCT_Y = [168.0, 153.0, 183.0, 191.0, 183.0, 186.0]

TITLE = "上半年各月商品销量同比去年情况"
SUBTITLE = "2022年相比于2021年销量都有提升，半年整体提升17%"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06,30"

T_X = 45.0
TITLE_Y, TITLE_PT = 39.0, 36.0
SUB_Y, SUB_PT = 96.0, 24.0
FOOT_X, FOOT_Y, FOOT_PT = 38.0, 578.0, 16.0

CAT_Y = 535.0
AXIS_X0, AXIS_X1 = 67.0, 769.0
AXIS_Y = 520.5

# 图例 (右侧描边框，ref 实测)
LEG22 = (698.0, 407.0, 54.0, 30.0)   # x,y,w,h outline box
LEG21 = (701.0, 450.0, 54.0, 30.0)
LEG22_TX, LEG22_TY = 722.5, 417.0   # 文字中心 x, 顶 y
LEG21_TX, LEG21_TY = 725.5, 460.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    # 轴线
    ax.plot([AXIS_X0, AXIS_X1], [AXIS_Y, AXIS_Y], color="#4A4F7B",
            linewidth=1.0, zorder=2)

    # 簇状柱
    for i in range(6):
        x0 = BLUE_CX[i] - BAR_W / 2.0
        top = BLUE_TOPS[i]
        ax.add_patch(Rectangle((x0, top), BAR_W, BAR_BOTTOM - top,
                               facecolor=C_BLUE, edgecolor="none", zorder=3))
        x0 = PINK_CX[i] - BAR_W / 2.0
        top = PINK_TOPS[i]
        ax.add_patch(Rectangle((x0, top), BAR_W, BAR_BOTTOM - top,
                               facecolor=C_PINK, edgecolor="none", zorder=3))

    # 柱数据标签
    for i in range(6):
        ax.text(BLUE_CX[i], LAB22_Y[i], str(V22[i]), color=TXT,
                fontsize=LAB_PT, ha="center", va="top", zorder=6)
        ax.text(PINK_CX[i], LAB21_Y[i], str(V21[i]), color=TXT,
                fontsize=LAB_PT, ha="center", va="top", zorder=6)

    # 折线
    ax.plot(LINE_CX, LINE_CY, color=C_LINE, linewidth=2.5,
            solid_capstyle="round", solid_joinstyle="round", zorder=5)
    for i in range(6):
        ax.add_patch(Circle((LINE_CX[i], LINE_CY[i]), LINE_R,
                            facecolor=C_LINE, edgecolor="none", zorder=6))
        ax.text(LINE_CX[i], PCT_Y[i], PCTS[i], color=TXT,
                fontsize=LAB_PT, ha="center", va="top", zorder=7)

    # 类目标签
    for i in range(6):
        cx = (BLUE_CX[i] + PINK_CX[i]) / 2.0
        ax.text(cx, CAT_Y, CATS[i], color=TXT, fontsize=LAB_PT,
                ha="center", va="top", zorder=6)

    # 图例 (描边)
    x, y, w, h = LEG22
    ax.add_patch(Rectangle((x, y), w, h, facecolor="none",
                           edgecolor=C_BLUE, linewidth=1.5, zorder=8))
    ax.text(LEG22_TX, LEG22_TY, "2022", color=TXT, fontsize=14,
            ha="center", va="top", zorder=9)
    x, y, w, h = LEG21
    ax.add_patch(Rectangle((x, y), w, h, facecolor="none",
                           edgecolor=C_PINK, linewidth=1.5, zorder=8))
    ax.text(LEG21_TX, LEG21_TY, "2021", color=TXT, fontsize=14,
            ha="center", va="top", zorder=9)

    # 文本
    ax.text(T_X, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=10)
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=10)
    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=10)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "27_簇状柱形折线图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
