# -*- coding: utf-8 -*-
"""第四章 销售看板 第11张：利润额占比销售额（圆环 KPI）
源: 第四章 销售看板参考.xlsx / chart11
参考原图: ...\\ch4_sales__数据大屏__chart11.png
实现: doughnut holeSize=85 粉弧+灰；中心12.19%利润率；
      右侧 利润额(万)/16.37 销售额(万)/134.29；底部圆角按钮标题
      ring C(154,138) R=92 T=14
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, FancyBboxPatch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import TXT, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BG_PANEL = "#2C3560"
PINK = "#FC6C9D"
GRAY = "#535A7D"
BTN_EDGE = "#6C7CE0"

W_PX, H_PX = 553, 324
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

# ring h-scans: outer x62-246 at y138; v outer y46-230 at x154
CX, CY = 154.0, 138.0
R_OUT = 92.0
RING_T = 14.0
FRAC = 0.12193592277824238

# center: 12.19% ref ink ~x114-224 y106-148 (larger than out fs28)
# 利润率 band y161-181 x129-182 -> center (155.5,171)
PCT_PT = 34.0
PCT_X, PCT_Y = 169.0, 127.0
LAB_PT = 16.0
LAB_X, LAB_Y = 155.5, 171.0

# right labels: 利润额(万) y~117, 销售额(万) y~171, x313-385 center 349
R_LAB_X, R_LAB_PT = 349.0, 16.0
R_LAB_Y1, R_LAB_Y2 = 117.0, 171.0
SLASH_X, SLASH_Y = 349.0, 144.0

# pink values: 16.37 y102-119 x412-474; 134.29 y164-181 x407-483
R_VAL_PT = 22.0
R_VAL_X1, R_VAL_Y1 = 443.0, 111.0
R_VAL_X2, R_VAL_Y2 = 445.0, 173.0

# button userShapes x161-376 y251-308; title band y267-289 x181-371
# ref text w=191 h=23 for 8 chars -> fs~24
BTN_X0, BTN_Y0 = 161.0, 251.0
BTN_X1, BTN_Y1 = 376.0, 308.0
BTN_TEXT_X, BTN_TEXT_Y = 276.0, 267.0
BTN_PT = 24.0

TITLE = "利润额占比销售额"


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG_PANEL)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG_PANEL)
    ax.axis("off")

    sweep = 360.0 * FRAC
    ax.add_patch(Wedge((CX, CY), R_OUT, -90.0, -90.0 + sweep,
                       width=RING_T, facecolor=PINK,
                       edgecolor="none", zorder=3))
    ax.add_patch(Wedge((CX, CY), R_OUT, -90.0 + sweep, 270.0,
                       width=RING_T, facecolor=GRAY,
                       edgecolor="none", zorder=3))

    ax.text(PCT_X, PCT_Y, "12.19%", color=TXT, fontsize=PCT_PT,
            ha="center", va="center", zorder=6)
    ax.text(LAB_X, LAB_Y, "利润率", color=TXT, fontsize=LAB_PT,
            ha="center", va="center", zorder=6)

    ax.text(R_LAB_X, R_LAB_Y1, "利润额(万)", color=TXT, fontsize=R_LAB_PT,
            ha="center", va="center", zorder=6)
    ax.text(R_LAB_X, R_LAB_Y2, "销售额(万)", color=TXT, fontsize=R_LAB_PT,
            ha="center", va="center", zorder=6)
    ax.text(SLASH_X, SLASH_Y, "/", color=TXT, fontsize=R_LAB_PT,
            ha="center", va="center", zorder=6)

    ax.text(R_VAL_X1, R_VAL_Y1, "16.37", color=PINK, fontsize=R_VAL_PT,
            ha="center", va="center", zorder=6, fontweight="bold")
    ax.text(R_VAL_X2, R_VAL_Y2, "134.29", color=PINK, fontsize=R_VAL_PT,
            ha="center", va="center", zorder=6, fontweight="bold")

    ax.add_patch(FancyBboxPatch(
        (BTN_X0, BTN_Y0), BTN_X1 - BTN_X0, BTN_Y1 - BTN_Y0,
        boxstyle="round,pad=0,rounding_size=14",
        facecolor="none", edgecolor=BTN_EDGE, linewidth=1.5, zorder=5))
    ax.text(BTN_TEXT_X, BTN_TEXT_Y, TITLE, color=TXT,
            fontsize=BTN_PT, ha="center", va="top", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "11_利润额占比销售额.png")
    save_fig(fig, out, facecolor=BG_PANEL)


if __name__ == "__main__":
    main()
