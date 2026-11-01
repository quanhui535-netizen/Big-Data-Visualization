# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第8张：数值百分比（水平堆叠 销量+占位1+占位2）
源: 第二章 图表(前15).xlsx / 「8 数值百分比」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__8_数值百分比__chart1.png
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

regions = ["华北", "华南", "东北", "西北", "西南", "华东"]
sales = [4321, 1946, 1536, 1872, 1369, 2109]
pad1 = [0, 2375, 2785, 2449, 2952, 2212]
pad2 = [1080.25] * 6
yoy = [-0.136, -0.208, -0.093, -0.159, -0.179, -0.058]

C_SALES = "#09387E"
C_PAD1 = "#82ADD7"
C_PAD2 = "#9B3D4F"

TITLE = "2021年各区域销量及同比情况"
SUBTITLE = "各区域商品销量同比去年均有下降，其中华南下降最多，同比下降20.8%"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.01.01"

W_IN = 416.0 / 72.0
H_IN = 308.0 / 72.0
GAP_W = 30.0
BAR_FRAC = 1.0 / (1.0 + GAP_W / 100.0)

# manualLayout chart7: x=0.12708 y=0.28142 w=0.81655 h=0.60875
PX, PY_TOP, PW, PH = 0.12708121043693066, 0.28142424339873146, 0.81654624054346148, 0.60875166161639771
PY = 1.0 - PY_TOP - PH


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([PX, PY, PW, PH])
    ax.set_facecolor(BG)

    y = np.arange(len(regions), dtype=float)
    bh = BAR_FRAC

    for yi, s, p1, p2, r in zip(y, sales, pad1, pad2, yoy):
        left = 0.0
        ax.barh(yi, s, height=bh, left=left, color=C_SALES, zorder=2, linewidth=0)
        left += s
        if p1 > 0:
            ax.barh(yi, p1, height=bh, left=left, color=C_PAD1, zorder=2, linewidth=0)
            left += p1
        ax.barh(yi, p2, height=bh, left=left, color=C_PAD2, zorder=2, linewidth=0)

    xmax = max(s + p1 + p2 for s, p1, p2 in zip(sales, pad1, pad2)) * 1.02
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.5, len(regions) - 0.5)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    # 销量标签 inEnd（深蓝条右端，白字）
    for yi, s in zip(y, sales):
        if s > xmax * 0.08:
            ax.text(s - xmax * 0.012, yi, str(s), ha="right", va="center",
                    color=TXT, fontsize=9, zorder=5)
        else:
            ax.text(s + xmax * 0.012, yi, str(s), ha="left", va="center",
                    color=TXT, fontsize=9, zorder=5)

    # 同比标签在红条内 ctr
    for yi, r in zip(y, yoy):
        left_end = (sales[yi] if False else 0)  # placeholder
    for i, (yi, s, p1, p2, r) in enumerate(zip(y, sales, pad1, pad2, yoy)):
        cx = s + p1 + p2 / 2.0
        ax.text(cx, yi, f"{r:.1%}", ha="center", va="center",
                color=TXT, fontsize=9, zorder=5)

    # 类目左侧
    trans = ax.get_yaxis_transform()
    for yi, name in zip(y, regions):
        ax.text(-0.02, yi, name, ha="right", va="center", color=TXT,
                fontsize=9, transform=trans, clip_on=False, zorder=5)

    fig.text(0.04657, 1.0 - 0.065, TITLE, color=TXT, fontsize=18,
             fontweight="bold", ha="left", va="top")
    fig.text(0.04657, 1.0 - 0.17, SUBTITLE, color=TXT, fontsize=11,
             ha="left", va="top")
    fig.text(0.03646, 1.0 - 0.925, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "08_数值百分比.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
