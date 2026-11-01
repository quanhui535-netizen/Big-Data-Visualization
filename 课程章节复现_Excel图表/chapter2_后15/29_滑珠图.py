# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第29张：滑珠图
源: 第二章 图表(后15).xlsx / 「29 滑珠图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__29_滑珠图__chart1.png
实现: 横向胶囊堆积条(蓝完成/灰未完成) + 值位白圈蓝珠 + 百分比标签
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

W_PX, H_PX = 844, 593
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

# 自上而下 (类目, 完成率)
ROWS = [
    ("华南", 0.86),
    ("华北", 0.74),
    ("东北", 0.62),
    ("西北", 0.51),
    ("华东", 0.35),
]
PCT = ["86%", "74%", "62%", "51%", "35%"]

C_BLUE = "#0070C0"
C_GRAY = "#7F7F7F"
C_BEAD = "#0070C0"

X0 = 136.0
TRACK_W = 476.0          # value=1.0 时条长 (实测珠心: 136+0.86*476≈545)
BAR_H = 30.0
Y_C = [187.5, 260.0, 333.0, 406.0, 478.0]
BEAD_R = 14.0            # 直径28
BEAD_LW = 3.0

TITLE = "2022年上半年产品销量目标达成率情况"
SUBTITLE = "华南完成率最高达到86%，华东最低35%"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06.30"

T_X = 65.0
TITLE_Y, TITLE_PT = 36.0, 36.0
SUB_Y, SUB_PT = 92.0, 22.0
FOOT_X, FOOT_Y, FOOT_PT = 65.0, 551.0, 16.0

CAT_X = 120.0
LAB_PT = 18.0
PCT_DX = 20.0            # 百分比标签右缘相对珠心的偏移


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    x1 = X0 + TRACK_W

    for i, (cat, val) in enumerate(ROWS):
        yc = Y_C[i]
        bx = X0 + val * TRACK_W  # 珠心 / 蓝灰分界

        # 灰色轨道（全宽，圆角帽）
        ax.plot([X0, x1], [yc, yc], color=C_GRAY,
                linewidth=BAR_H, solid_capstyle="round", zorder=3)
        # 蓝色完成段
        ax.plot([X0, bx], [yc, yc], color=C_BLUE,
                linewidth=BAR_H, solid_capstyle="round", zorder=4)

        # 珠（白圈蓝底）
        ax.plot([bx], [yc], marker="o", markersize=BEAD_R * 2,
                markerfacecolor=C_BEAD, markeredgecolor="white",
                markeredgewidth=BEAD_LW, zorder=6)

        # 类目标签
        ax.text(CAT_X, yc, cat, color=TXT, fontsize=LAB_PT,
                ha="right", va="center", zorder=7)

        # 百分比（蓝条内、珠左侧）
        ax.text(bx - PCT_DX, yc, PCT[i], color=TXT, fontsize=LAB_PT,
                ha="right", va="center", zorder=7)

    # 文本
    ax.text(T_X, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=8)
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=8)
    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "29_滑珠图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
