# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第9张：对比柱形图（簇状柱 + 差值箭头折线）
源: 第二章 图表(前15).xlsx / 「9 对比柱形图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__9_对比柱形图__chart1.png
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

cats = ["口红", "面膜", "隔离", "防晒", "精华"]
v2021 = [3568, 4135, 4436, 4106, 4936]
v2022 = [2569, 3241, 2965, 3209, 3541]
diff = [999, 894, 1471, 897, 1395]

C21 = "#0070C0"
C22 = "#82ADD7"

TITLE = "2022年商品对比去年销售情况"
SUBTITLE = "商品整体比去年销量有所下降，其中隔离下降最多，下降33%"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.01.01"
LEG21 = "2021销量"
LEG22 = "2022销量"

W_IN = 416.0 / 72.0
H_IN = 308.0 / 72.0
GAP_W = 219.0
OVERLAP = -27.0
group_w = 1.0 / (1.0 + GAP_W / 100.0)
bar_w = group_w * (1.0 - OVERLAP / 100.0) / 2.0  # clustered two bars
# Excel: bar width = group/(1+gap) then split by overlap; standard clustered:
# each bar width ≈ (1 - gap_frac) related...
# For gap=219, slot=1, group=1/(1+2.19)=0.3135; with overlap -27:
# effective group wider. Simpler: match visual - two bars side by side within slot.
bar_w = group_w * 0.42
offset = group_w * 0.21

# manualLayout chart8: x=0.06373 y=0.29142 w=0.85539 h=0.54478
PX, PY_TOP, PW, PH = 0.063725490196078427, 0.29142189259162665, 0.85539215686274506, 0.54477585977600662
PY = 1.0 - PY_TOP - PH


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([PX, PY, PW, PH])
    ax.set_facecolor(BG)

    x = np.arange(len(cats), dtype=float)
    for xi, v in zip(x, v2021):
        ax.bar(xi - offset, v, width=bar_w, color=C21, zorder=2, linewidth=0)
    for xi, v in zip(x, v2022):
        ax.bar(xi + offset, v, width=bar_w, color=C22, zorder=2, linewidth=0)

    ymax = 5600
    ax.set_xlim(-0.5, len(cats) - 0.5)
    ax.set_ylim(0, ymax)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    # 底部白线
    ax.axhline(0, color=TXT, linewidth=1.0, zorder=3)

    # 数据标签
    for xi, v in zip(x, v2021):
        ax.text(xi - offset, v + ymax * 0.015, str(v), ha="center",
                va="bottom", color=TXT, fontsize=9, zorder=5)
    for xi, v, d in zip(x, v2022, diff):
        ax.text(xi + offset, v * 0.5, str(v), ha="center", va="center",
                color=TXT, fontsize=9, zorder=5)

    # 差值箭头：从2022柱顶指向2021柱顶附近，旁标差值
    for xi, a, b, d in zip(x, v2022, v2021, diff):
        x0 = xi + offset + bar_w / 2.0 + 0.02
        y0 = a + ymax * 0.04
        y1 = b + ymax * 0.04
        ax.annotate("", xy=(x0, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=TXT, lw=1.2,
                                    mutation_scale=10), zorder=5)
        ax.text(x0 + 0.04, (y0 + y1) / 2.0, str(d), ha="left", va="center",
                color=TXT, fontsize=9, zorder=5)

    # 类目
    trans = ax.get_xaxis_transform()
    for xi, c in zip(x, cats):
        ax.text(xi, -0.07, c, ha="center", va="top", color=TXT,
                fontsize=9, transform=trans, clip_on=False, zorder=4)

    # 图例（原图 legend 在下方偏左上位置——实际在副标题下左上）
    # 参考图：图例在标题区下方左侧，非底部
    fig.text(0.10, 1.0 - 0.24, "■", color=C21, fontsize=10, ha="left", va="center")
    fig.text(0.14, 1.0 - 0.24, LEG21, color=TXT, fontsize=9, ha="left", va="center")
    fig.text(0.28, 1.0 - 0.24, "■", color=C22, fontsize=10, ha="left", va="center")
    fig.text(0.32, 1.0 - 0.24, LEG22, color=TXT, fontsize=9, ha="left", va="center")

    fig.text(0.04105, 1.0 - 0.055, TITLE, color=TXT, fontsize=20,
             fontweight="bold", ha="left", va="top")
    fig.text(0.04105, 1.0 - 0.16, SUBTITLE, color=TXT, fontsize=12,
             ha="left", va="top")
    fig.text(0.02819, 1.0 - 0.925, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "09_对比柱形图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
