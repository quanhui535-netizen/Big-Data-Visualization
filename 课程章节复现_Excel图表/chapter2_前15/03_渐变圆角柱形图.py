# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第3张：渐变圆角柱形图
源: 第二章 图表(前15).xlsx / 「3 渐变圆角柱形图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__3_渐变圆角柱形图__chart1.png
柱体: Excel 用图片填充（圆角+渐变），此处用圆角矩形渐变近似，严格对齐数据/文案/布局
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, GRID, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

categories = ["口红", "面膜", "隔离", "防晒", "精华", "面霜"]
sales = [653, 523, 648, 856, 714, 785]

TITLE = "3月商品销量对比"
SUBTITLE = "防晒销量最多，3月销量856；面膜最少，3月销量523"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.03.31"

# chart3: gapWidth=500, valAx max=1200, grid lgDash alpha20
# manualLayout 需与原图一致（近似用对称布局）
W_IN = 416.0 / 72.0
H_IN = 308.1250305175781 / 72.0
GAP_W = 500.0
BAR_FRAC = 1.0 / (1.0 + GAP_W / 100.0)  # ≈0.1667
YMAX = 1200

# 柱渐变：Excel 图片为上浅下深青蓝（参考导出图）
C_TOP = "#7DE2FC"
C_BOTTOM = "#2E7CE8"
# 标签徽章底色
BADGE_BG = "#2A3160"
BADGE_CIRCLE = "#8EB8E5"


def rounded_gradient_bar(ax, xi, value, half_width):
    cmap = LinearSegmentedColormap.from_list("g", [C_TOP, C_BOTTOM])
    grad = cmap(np.linspace(0, 1, 256).reshape(-1, 1))
    # 用 imshow 画渐变，再叠圆角遮罩效果：直接 FancyBbox 渐变难，
    # 使用 imshow + 上端圆角近似（原图柱顶为圆角胶囊形）
    # 胶囊形：width 很窄，用 FancyBboxPatch 纯色不渐变会差；
    # 组合：imshow 矩形 + 顶部圆形帽
    hw = half_width
    ax.imshow(grad, extent=(xi - hw, xi + hw, 0, value), aspect="auto",
              interpolation="bilinear", zorder=2, origin="upper")
    # 顶部圆帽
    cap_r = hw
    circ = plt.Circle((xi, value), cap_r, facecolor=C_TOP, edgecolor="none",
                      zorder=3, clip_on=False)
    ax.add_patch(circ)
    # 底部圆帽
    circ2 = plt.Circle((xi, 0), cap_r, facecolor=C_BOTTOM, edgecolor="none",
                       zorder=3, clip_on=False)
    ax.add_patch(circ2)


def main():
    # manualLayout from chart3.xml — use tight layout similar to ref
    # 从原图目测: plot 区约 x0.11 y0.30 w0.85 h0.52
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0.115, 0.175, 0.855, 0.55])
    ax.set_facecolor(BG)

    x = np.arange(len(categories))
    hw = BAR_FRAC / 2.0
    for xi, v in zip(x, sales):
        rounded_gradient_bar(ax, float(xi), float(v), hw)

    ax.set_xlim(-0.5, len(categories) - 0.5)
    ax.set_ylim(0, YMAX)
    ax.set_xticks(x)
    ax.set_xticklabels(categories)

    # 网格 + Y 轴 0..1200 step 200
    yticks = list(range(0, YMAX + 1, 200))
    ax.set_yticks(yticks)
    ax.tick_params(axis="y", length=0, colors=TXT_DIM, labelsize=9, pad=3)
    ax.tick_params(axis="x", length=0)
    for lab in ax.get_xticklabels():
        lab.set_fontsize(9)
        lab.set_color(TXT)
    ax.yaxis.grid(True, linestyle=(0, (5, 4)), linewidth=0.9,
                  color=GRID, alpha=0.22)
    ax.set_axisbelow(True)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    # 数据标签：圆点 + 深色圆角徽章 + 数值（对应 userShapes 圆角矩形）
    for xi, v in zip(x, sales):
        # 圆点略高于柱顶
        ax.plot([xi], [v + YMAX * 0.025], marker="o", markersize=7,
                color=BADGE_CIRCLE, zorder=5, clip_on=False)
        # 徽章
        badge = FancyBboxPatch(
            (xi - 0.14, v + YMAX * 0.008), 0.28, YMAX * 0.055,
            boxstyle="round,pad=0.01,rounding_size=0.04",
            facecolor=BADGE_BG, edgecolor="none", zorder=4,
            mutation_aspect=0.35, transform=ax.transData, clip_on=False,
        )
        ax.add_patch(badge)
        ax.text(xi + 0.02, v + YMAX * 0.035, str(v), ha="left", va="center",
                color=TXT, fontsize=9, zorder=6)

    fig.text(0.05116, 1.0 - 0.03399, TITLE, color=TXT, fontsize=20,
             fontweight="bold", ha="left", va="top")
    fig.text(0.05116, 1.0 - 0.135, SUBTITLE, color=TXT, fontsize=14,
             ha="left", va="top")
    fig.text(0.04289, 1.0 - 0.91196, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "03_渐变圆角柱形图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
