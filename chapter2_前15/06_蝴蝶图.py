# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第6张：蝴蝶图（水平堆叠 + 占位镜像）
源: 第二章 图表(前15).xlsx / 「6 蝴蝶图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__6_蝴蝶图__chart1.png
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

# 单元格 B2:F7（类目自上而下需与 Excel 横向条一致：Excel 底→顶 = 数据首→末）
# 数据顺序 华东..华南；原图自上而下 华南..华东
regions = ["华东", "西北", "东北", "华北", "华南"]
v2022 = [1215, 1321, 1426, 1531, 2238]
v2021 = [1003, 1265, 1531, 1436, 2066]

# 占位1 + 2022 ≡ 3453 => 蓝条右缘对齐；占位2 ≡ 1215 为中心沟
LEFT_EDGE = 3453.0
CENTER_GAP = 1215.0
RIGHT_BASE = LEFT_EDGE + CENTER_GAP  # 4668

C22 = "#0070C0"
C21 = "#E74E69"
C21_LEG = "#F94C66"

TITLE = "2022年上半年各区域对比去年销量"
SUBTITLE = "2022年整体销量高于2021年，只有东北区域较2021年有所下降"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.06.30"
LEG_22 = "2022"
LEG_21 = "2021"

W_IN = 416.0 / 72.0
H_IN = 294.0001525878906 / 72.0
GAP_W = 150.0
BAR_FRAC = 1.0 / (1.0 + GAP_W / 100.0)  # 0.4

# chart6 manualLayout inner: x=0.03431 y=0.28486 w=0.94608 h=0.59846
PX = 0.034313725490196081
PY_TOP = 0.28485616938848751
PW = 0.94607843137254899
PH = 0.59845576122345734
PY = 1.0 - PY_TOP - PH

# userShapes（Excel y 向下）
# 标题框 0.04749,0.03947 - 0.94456,0.25902  标题18 / 副标题11
# 脚注框 0.04381,0.90948 - 0.84529,0.98487  8pt
# 图例框 0.32598,0.24410 - 0.78462,0.29558  2022/2021 11pt


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([PX, PY, PW, PH])
    ax.set_facecolor(BG)

    # 类目自上而下 = 数据倒序（Excel 条形图首类在底）
    y = np.arange(len(regions), dtype=float)  # 0=华东(底) … 4=华南(顶)
    bh = BAR_FRAC

    for yi, v22, v21 in zip(y, v2022, v2021):
        # 左蓝：右缘固定 LEFT_EDGE，向左延伸 v22
        ax.barh(yi, v22, height=bh, left=LEFT_EDGE - v22,
                color=C22, zorder=2, linewidth=0)
        # 右红：起点 RIGHT_BASE，向右延伸 v21
        ax.barh(yi, v21, height=bh, left=RIGHT_BASE,
                color=C21, zorder=2, linewidth=0)

    xmax = RIGHT_BASE + max(v2021) + 200
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.5, len(regions) - 0.5)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    # 数据标签 9pt：2022 inBase（蓝条左端）；2021 inEnd（红条右端）
    for yi, v22, v21 in zip(y, v2022, v2021):
        ax.text(LEFT_EDGE - v22 + xmax * 0.012, yi, str(v22),
                ha="left", va="center", color=TXT, fontsize=9, zorder=5)
        ax.text(RIGHT_BASE + v21 - xmax * 0.012, yi, str(v21),
                ha="right", va="center", color=TXT, fontsize=9, zorder=5)

    # 中心类目（数据倒序显示：顶=华南）
    for yi, name in zip(y, regions):
        ax.text((LEFT_EDGE + RIGHT_BASE) / 2.0, yi, name,
                ha="center", va="center", color=TXT, fontsize=9, zorder=5)

    # 图例行：原图在 plot 上方，对应 userShapes 图例框
    fig.text(0.42, 1.0 - 0.268, LEG_22, color=C22, fontsize=11,
             ha="center", va="center")
    fig.text(0.665, 1.0 - 0.268, LEG_21, color=C21_LEG, fontsize=11,
             ha="center", va="center")

    # 标题 18 bold / 副标题 11
    fig.text(0.04749, 1.0 - 0.055, TITLE, color=TXT, fontsize=18,
             fontweight="bold", ha="left", va="top")
    fig.text(0.04749, 1.0 - 0.155, SUBTITLE, color=TXT, fontsize=11,
             ha="left", va="top")

    # 脚注 8
    fig.text(0.04381, 1.0 - 0.922, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "06_蝴蝶图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
