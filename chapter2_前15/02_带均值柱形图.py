# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第2张：带均值柱形图
源: 第二章 图表(前15).xlsx / 「2 带均值柱形图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__2_带均值柱形图__chart1.png
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig, gradient_column

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

categories = ["华北", "华南", "东北", "西北", "西南", "华东"]
sales = [2354, 1902, 3524, 2698, 2896, 2563]
MEAN = 2656.1666666666665

TITLE = "3月各区域销量分布"
SUBTITLE = "东北销量最多占比总销量的22%，华南销量最低"
FOOTNOTE = " *注：数据来源于公司销售系统，统计日期截至2022.03.31"
MEAN_LABEL = "平均值：2656"

# chart2 manualLayout
PX, PY_TOP, PW, PH = 0.058831442025629149, 0.23438164632405159, 0.90466463398940655, 0.55987055911086651
PY = 1.0 - PY_TOP - PH

W_IN = 416.0 / 72.0
H_IN = 296.8748779296875 / 72.0
GAP_W = 219.0
BAR_FRAC = 1.0 / (1.0 + GAP_W / 100.0)
BAR_COLOR = "#0070C0"
MEAN_COLOR = "#FFC000"


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([PX, PY, PW, PH])
    ax.set_facecolor(BG)

    x = np.arange(len(categories))
    hw = BAR_FRAC / 2.0
    for xi, v in zip(x, sales):
        ax.bar(xi, v, width=BAR_FRAC, color=BAR_COLOR, zorder=2,
               linewidth=0, edgecolor="none")

    ymax = 4000
    ax.set_xlim(-0.5, len(categories) - 0.5)
    ax.set_ylim(0, ymax)

    # 均值线
    ax.axhline(MEAN, color=MEAN_COLOR, linewidth=1.5, zorder=3)

    # 数据标签 outEnd 9pt 白
    for xi, v in zip(x, sales):
        # 华东 2563 标签为蓝色（原图特殊色）
        col = "#5B9BD5" if categories[xi] == "华东" else TXT
        ax.text(xi, v + ymax * 0.02, str(v), ha="center", va="bottom",
                color=col, fontsize=9, zorder=4)

    # 均值标注（userShapes 文本框1, FFC000 8pt）
    ax.text(0.97, MEAN + ymax * 0.03, MEAN_LABEL, ha="right", va="bottom",
            color=MEAN_COLOR, fontsize=8, zorder=4)

    # 数值轴删除（delete=1）：无刻度无网格
    ax.yaxis.set_visible(False)
    ax.xaxis.set_visible(False)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)
    # 类别轴白线 + 白字（画在 axes 下方）
    ax.axhline(0, color=TXT, linewidth=1.0, zorder=3)
    trans = ax.get_xaxis_transform()
    for xi, c in zip(x, categories):
        ax.text(xi, -0.06, c, ha="center", va="top", color=TXT,
                fontsize=9, zorder=4, transform=trans, clip_on=False)

    # title / subtitle / footnote（userShapes）
    fig.text(0.04882, 1.0 - 0.04231, TITLE, color=TXT, fontsize=20,
             fontweight="bold", ha="left", va="top")
    fig.text(0.04882, 1.0 - 0.140, SUBTITLE, color=TXT, fontsize=14,
             ha="left", va="top")
    fig.text(0.03844, 1.0 - 0.91398, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "02_带均值柱形图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
