# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第1张图：渐变柱形图
严格对照 Excel 原图复现（可用 Excel 导出 PNG 校验）:
- 图表尺寸 416x308.75 pt (chart1 绘图区 manualLayout)
- gapWidth=219 -> 柱宽占类别槽 1/(1+2.19)≈31.3%
- 字号: 标题20 副标题14 轴/标签9 脚注8 (Excel pt)
- 文案取自 userShapes (drawing2.xml)
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BG = "#1A1E43"
C_TOP = "#0070C0"
C_BOTTOM = "#00B0F0"
TXT = "#FFFFFF"
TXT_DIM = "#D9D9D9"

# Excel 原始数据 B2:C8
categories = ["华北", "华南", "东北", "西北", "西南", "华东"]
sales = [2354, 1902, 3524, 2698, 2896, 2563]

# userShapes 文案
TITLE = "3月各区域销量分布"
SUBTITLE = "东北销量最多占比总销量的22%，华南销量最低"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.03.31"

# Excel chart 尺寸 (pt) -> inch
W_IN = 416.0 / 72.0
H_IN = 308.75 / 72.0

# chart1 manualLayout (Excel 从上往下 y): inner plot
# x=0.14399 y=0.31886 w=0.76023 h=0.52541
PX, PY_TOP, PW, PH = 0.14399451906746949, 0.31885801039575934, 0.7602323606607998, 0.5254068241469817
PY = 1.0 - PY_TOP - PH  # matplotlib 从下往上

# userShapes 相对位置 (from/to, Excel y 向下)
# 标题框: (0.06036,0.06209)-(0.95742,0.26225)
# 脚注框: (0.04198,0.91625)-(0.84345,0.98121)

GAP_W = 219.0
BAR_FRAC = 1.0 / (1.0 + GAP_W / 100.0)  # ≈0.3135


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)

    ax = fig.add_axes([PX, PY, PW, PH])
    ax.set_facecolor(BG)

    cmap = LinearSegmentedColormap.from_list("g", [C_TOP, C_BOTTOM])
    grad = cmap(np.linspace(0, 1, 256).reshape(-1, 1))

    x = np.arange(len(categories))
    hw = BAR_FRAC / 2.0
    for xi, v in zip(x, sales):
        ax.imshow(grad, extent=(xi - hw, xi + hw, 0, v), aspect="auto",
                  interpolation="bilinear", zorder=2, origin="upper")

    ymax = 4000
    ax.set_xlim(-0.5, len(categories) - 0.5)
    ax.set_ylim(0, ymax)

    # 数据标签 9pt 白 outEnd
    for xi, v in zip(x, sales):
        ax.text(xi, v + ymax * 0.02, str(v), ha="center", va="bottom",
                color=TXT, fontsize=9, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, color=TXT, fontsize=9)
    ax.tick_params(axis="x", length=0, pad=4)

    ax.set_yticks(range(0, ymax + 1, 1000))
    ax.tick_params(axis="y", length=0, colors=TXT_DIM, labelsize=9, pad=3)
    ax.yaxis.grid(True, linestyle=(0, (5, 4)), linewidth=0.9,
                  color="#FFFFFF", alpha=0.22)
    ax.set_axisbelow(True)

    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    # 标题 20pt bold
    fig.text(0.06036, 1.0 - 0.06209, TITLE, color=TXT, fontsize=20,
             fontweight="bold", ha="left", va="top")
    # 副标题 14pt（标题框下半段）
    fig.text(0.06036, 1.0 - 0.155, SUBTITLE, color=TXT, fontsize=14,
             ha="left", va="top")
    # 脚注 8pt
    fig.text(0.04198, 1.0 - 0.91625, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "01_渐变柱形图.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, facecolor=BG)
    plt.close(fig)
    print("saved:", out)


if __name__ == "__main__":
    main()
