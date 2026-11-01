# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第26张：柱形圆
源: 第二章 图表(后15).xlsx / 「26 柱形圆」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__26_柱形圆__chart1.png
实现: 粉柱 E74E69 + 顶部蓝圆 0070C0(内百分比) + 柱顶数据标签；
      gapWidth=219 overlap=-27；无线连接
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

W_PX, H_PX = 831, 591
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

CATS = ["华北", "华南", "东北", "西北", "西南", "华东"]
BARS = [2354, 1902, 3524, 2698, 2896, 2563]
PCTS = ["12%", "25%", "16%", "21%", "18%", "25%"]

BAR_COLOR = "#E74E69"
CIR_COLOR = "#0070C0"

BAR_BOTTOM = 500.0
BAR_W = 36.0
# ref 实测
BAR_CX = [124.5, 238.5, 353.0, 467.5, 581.5, 696.5]
BAR_TOPS = [335.0, 367.0, 252.0, 310.0, 296.0, 320.0]

# 圆：cy=182.5 d=50
CIR_CY = 182.5
CIR_R = 25.0
CIR_CX = [124.5, 238.5, 352.5, 466.5, 581.5, 695.5]
PCT_CX = [124.5, 238.0, 352.5, 467.0, 581.5, 696.0]
PCT_CY = 182.5

# 柱顶数据标签 (ref 白字带 top, va=top)
LAB_TOPS = [310.0, 342.0, 227.0, 286.0, 272.0, 295.0]
LAB_PT = 16.0

TITLE = "各区域上半年销量以同比"
SUBTITLE = "东北区域销量持续保持第一，华东和华南同比去年增长最多"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06,30"

T_X = 52.0
TITLE_Y, TITLE_PT = 36.0, 36.0
SUB_Y, SUB_PT = 92.0, 22.0
FOOT_X, FOOT_Y, FOOT_PT = 36.0, 550.0, 16.0

CAT_Y = 515.0
AXIS_X0, AXIS_X1 = 65.0, 755.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    # 底部轴线
    ax.plot([AXIS_X0, AXIS_X1], [500.5, 500.5], color="#4A4F7B",
            linewidth=1.0, zorder=2)

    # 柱
    for i in range(6):
        x0 = BAR_CX[i] - BAR_W / 2.0
        top = BAR_TOPS[i]
        ax.add_patch(Rectangle((x0, top), BAR_W, BAR_BOTTOM - top,
                               facecolor=BAR_COLOR, edgecolor="none", zorder=3))

    # 柱数据标签
    for i in range(6):
        ax.text(BAR_CX[i], LAB_TOPS[i], str(BARS[i]), color=TXT,
                fontsize=LAB_PT, ha="center", va="top", zorder=6)

    # 蓝圆 + 百分比
    for i in range(6):
        ax.add_patch(Circle((CIR_CX[i], CIR_CY), CIR_R,
                            facecolor=CIR_COLOR, edgecolor="none", zorder=4))
    for i in range(6):
        ax.text(PCT_CX[i], PCT_CY, PCTS[i], color=TXT,
                fontsize=LAB_PT, ha="center", va="center", zorder=5)

    # 类目标签
    for i in range(6):
        ax.text(BAR_CX[i], CAT_Y, CATS[i], color=TXT, fontsize=LAB_PT,
                ha="center", va="top", zorder=6)

    # 文本
    ax.text(T_X, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=8)
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=8)
    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "26_柱形圆.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
