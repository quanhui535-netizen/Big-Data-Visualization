# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第30张：对比滑珠图
源: 第二章 图表(后15).xlsx / 「30 对比滑珠图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__30_对比滑珠图__chart1.png
实现: 横向细条(蓝完成/灰未完成) + 2022蓝珠 + 2021灰珠 + 珠上方百分比
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

W_PX, H_PX = 831, 593
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

# 自上而下: (类目, 2022, 2021)
ROWS = [
    ("华南", 0.86, 0.92),
    ("华北", 0.74, 0.69),
    ("东北", 0.62, 0.53),
    ("西北", 0.51, 0.39),
    ("华东", 0.35, 0.45),
]
PCT = ["86%", "74%", "62%", "51%", "35%"]

C_BLUE = "#0070C0"
C_GRAY = "#7F7F7F"
C_BEAD22 = "#0070C0"
C_BEAD21 = "#A5A5A5"

X0 = 124.0
TRACK_W = 536.0          # value=1.0 → x=660 (实测)
BAR_H = 13.0
Y_C = [197.0, 271.0, 345.0, 419.0, 493.0]
BEAD_R = 9.0             # 直径18
BEAD_LW = 2.0

TITLE = "2022年上半年销量目标达成率同比去年情况"
SUBTITLE = "华南完成率最高达到86%，华东最低35%，其中华南和华东不及2021年"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06.30"

T_X = 58.0
TITLE_Y, TITLE_PT = 42.0, 36.0
SUB_Y, SUB_PT = 98.0, 22.0
FOOT_X, FOOT_Y, FOOT_PT = 67.0, 553.0, 16.0

CAT_X = 110.0
LAB_PT = 18.0
PCT_PT = 16.0
PCT_DY = 18.0            # 百分比在珠心上方

# 图例
LEG_CY = 155.5
LEG22_CX = 77.5
LEG21_CX = 206.5
LEG22_TX = 92.0
LEG21_TX = 221.0
LEG_PT = 16.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    x1 = X0 + TRACK_W

    for i, (cat, v22, v21) in enumerate(ROWS):
        yc = Y_C[i]
        bx22 = X0 + v22 * TRACK_W
        bx21 = X0 + v21 * TRACK_W

        # 灰色轨道（全宽，方头）
        ax.plot([X0, x1], [yc, yc], color=C_GRAY,
                linewidth=BAR_H, solid_capstyle="butt", zorder=3)
        # 蓝色完成段（到2022珠心）
        ax.plot([X0, bx22], [yc, yc], color=C_BLUE,
                linewidth=BAR_H, solid_capstyle="butt", zorder=4)

        # 2021 灰珠（可能压在蓝条上）
        ax.plot([bx21], [yc], marker="o", markersize=BEAD_R * 2,
                markerfacecolor=C_BEAD21, markeredgecolor="white",
                markeredgewidth=BEAD_LW, zorder=5)
        # 2022 蓝珠
        ax.plot([bx22], [yc], marker="o", markersize=BEAD_R * 2,
                markerfacecolor=C_BEAD22, markeredgecolor="white",
                markeredgewidth=BEAD_LW, zorder=6)

        # 类目标签
        ax.text(CAT_X, yc, cat, color=TXT, fontsize=LAB_PT,
                ha="right", va="center", zorder=7)

        # 百分比（珠上方）
        ax.text(bx22, yc - PCT_DY, PCT[i], color=TXT, fontsize=PCT_PT,
                ha="center", va="bottom", zorder=7)

    # 图例
    ax.plot([LEG22_CX], [LEG_CY], marker="o", markersize=BEAD_R * 2,
            markerfacecolor=C_BEAD22, markeredgecolor="white",
            markeredgewidth=BEAD_LW, zorder=7)
    ax.text(LEG22_TX, LEG_CY, "2022完成率", color=TXT, fontsize=LEG_PT,
            ha="left", va="center", zorder=7)
    ax.plot([LEG21_CX], [LEG_CY], marker="o", markersize=BEAD_R * 2,
            markerfacecolor=C_BEAD21, markeredgecolor="white",
            markeredgewidth=BEAD_LW, zorder=7)
    ax.text(LEG21_TX, LEG_CY, "2021完率", color=TXT, fontsize=LEG_PT,
            ha="left", va="center", zorder=7)

    # 文本
    ax.text(T_X, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=8)
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=8)
    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "30_对比滑珠图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
