# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第7张：蝴蝶图（REPT('|') 文本伪图）
源: 第二章 图表(前15).xlsx / 「7 蝴蝶图」右侧 Q7:U11 + 文本框 11/12
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

ROWS = [
    ("华东", 0.36, 0.42),
    ("西北", 0.31, 0.26),
    ("东北", 0.18, 0.19),
    ("华北", 0.13, 0.12),
    ("华南", 0.09, 0.05),
]


def n_bars(pct):
    return int(round(pct * 200))


C_L = "#0070C0"
C_R = "#E74E69"

TITLE = "2022年第一季度销售目标完成情况"
SUBTITLE = "华东区域完成率最高达到36%，但是相比去年的42%有所下降"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.03.31"

W_PX, H_PX = 868, 464
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

T_X, T_Y, T_PT = 48.0, 28.0, 28.0
SUB_Y = 88.0
FOOT_X, FOOT_Y, FOOT_PT = 40.0, 412.0, 14.0

ROW_Y0, ROW_DY = 148.0, 50.0

# 列布局：左% | 蓝条(右对齐到中缝左) | 区域 | 红条(左对齐) | 右%
X_PCT_L = 58.0
X_MID = 434.0
X_GAP = 16.0
X_PCT_R = 810.0
BAR_MAX_W_L = X_MID - X_GAP - 120.0  # 蓝条最长（120=左%区）
BAR_MAX_W_R = X_PCT_R - 50.0 - (X_MID + X_GAP)
TICK_H = 26.0  # 竖条高度（REPT 视觉）
TICK_LW = 2.0
PCT_PT = 16.0
NAME_PT = 16.0


def draw_ticks(ax, x_right, n, width_max, y, color, right_align=True):
    """在 [x_start, x_right] 或 [x_left, x_left+width] 画 n 根竖条"""
    w = width_max * (n / 84.0)
    if right_align:
        x0, x1 = x_right - w, x_right
    else:
        x0, x1 = x_right, x_right + w
    if n <= 0:
        return
    # 与 REPT('|') 一致：字符均匀分布
    step = w / n if n else 1
    xs = [x0 + step * (i + 0.5) for i in range(n)]
    for x in xs:
        ax.add_line(Line2D([x, x], [y - TICK_H / 2, y + TICK_H / 2],
                           color=color, linewidth=TICK_LW,
                           solid_capstyle="butt", zorder=5))


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
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=T_PT * 0.72,
            ha="left", va="top", zorder=6)

    for i, (name, p22, p21) in enumerate(ROWS):
        y = ROW_Y0 + i * ROW_DY
        bl, br = n_bars(p22), n_bars(p21)
        ax.text(X_PCT_L, y, f"{int(round(p22 * 100))}%",
                color=TXT, fontsize=PCT_PT, ha="right", va="center", zorder=6)
        draw_ticks(ax, X_MID - X_GAP, bl, BAR_MAX_W_L, y, C_L, right_align=True)
        ax.text(X_MID, y, name, color=TXT, fontsize=NAME_PT,
                ha="center", va="center", zorder=6)
        draw_ticks(ax, X_MID + X_GAP, br, BAR_MAX_W_R, y, C_R, right_align=False)
        ax.text(X_PCT_R, y, f"{int(round(p21 * 100))}%",
                color=TXT, fontsize=PCT_PT, ha="left", va="center", zorder=6)

    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "07_蝴蝶图.png")
    save_fig(fig, out, facecolor=BG)


if __name__ == "__main__":
    main()
