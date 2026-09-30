# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第11张：平滑折线图
源: 第二章 图表(前15).xlsx / 「11 平滑折线图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__11_平滑折线图__chart1.png
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

cats = ["5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月", "1月", "2月", "3月"]
vals = [146, 198, 296, 412, 506, 615, 789, 1021, 3782, 3215, 2936]

C_LINE = "#E66B4C"
C_2021 = "#5BC8D8"  # 底部2021条（原图青色）
C_2022 = "#F5C842"  # 2022黄条

TITLE = "化妆品品类月度销量走势"
SUBTITLE = "2022年销量迅速增加，1月最高，销量达到3782"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2022.03.31"

W_IN = 416.0 / 72.0
H_IN = 308.0 / 72.0

# manualLayout chart10: x=0.11690 y=0.29238 w=0.84360 h=0.47011
PX, PY_TOP, PW, PH = 0.11689671144048171, 0.2923847646798442, 0.84359618650609847, 0.4701066067940679
PY = 1.0 - PY_TOP - PH


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([PX, PY, PW, PH])
    ax.set_facecolor(BG)

    x = np.arange(len(cats), dtype=float)
    # Excel 平滑线：PCHIP 单调三次（无过冲/振铃）
    try:
        from scipy.interpolate import PchipInterpolator
        xs = np.linspace(x[0], x[-1], 400)
        ys = PchipInterpolator(x, vals)(xs)
    except Exception:
        def _cr(p0, p1, p2, p3, t):
            t2, t3 = t * t, t * t * t
            return 0.5 * ((2 * p1) + (-p0 + p2) * t
                          + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
        pad_v = [vals[0]] + list(vals) + [vals[-1]]
        xs, ys = [], []
        for i in range(len(vals) - 1):
            t = np.linspace(0, 1, 40, endpoint=False)
            seg = [_cr(pad_v[i], pad_v[i + 1], pad_v[i + 2],
                       pad_v[i + 3], ti) for ti in t]
            xs.extend(x[i] + t)
            ys.extend(seg)
        xs.append(x[-1]); ys.append(vals[-1])
        xs = np.asarray(xs); ys = np.asarray(ys)
    ax.plot(xs, ys, color=C_LINE, linewidth=1.5, zorder=3,
            solid_capstyle="round")

    ymax = 4000
    ax.set_xlim(-0.2, len(cats) - 0.8)
    ax.set_ylim(0, ymax)
    ax.set_yticks([0, 1000, 2000, 3000, 4000])
    ax.set_yticklabels(["0", "1,000", "2,000", "3,000", "4,000"])
    ax.tick_params(axis="y", length=0, colors=C_LINE, labelsize=9, pad=4)
    ax.tick_params(axis="x", length=0, pad=4, colors=TXT)
    for lab in ax.get_xticklabels():
        lab.set_fontsize(9)
        lab.set_color(TXT)
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(TXT)
    ax.spines["bottom"].set_linewidth(1.0)

    # 3782 标注
    i_pk = cats.index("1月")
    ax.text(i_pk, vals[i_pk] + ymax * 0.04, "3782", ha="center", va="bottom",
            color=TXT, fontsize=9, zorder=5)

    # 1月竖虚线
    ax.axvline(i_pk, color=C_LINE, linewidth=1.0, linestyle=(0, (4, 3)),
               zorder=2, alpha=0.9)

    # 底部 2021/2022 圆角条（userShapes 矩形）
    # 2021: x 0.093-0.733, 2022: 0.742-0.777 (相对整图 y~0.835-0.887)
    from matplotlib.patches import FancyBboxPatch
    # 转 fig 坐标
    def fig_box(x0, x1, y0, y1, color, label):
        w = x1 - x0
        h = y1 - y0
        patch = FancyBboxPatch(
            (x0, 1.0 - y1), w, h,
            boxstyle="round,pad=0.004,rounding_size=0.015",
            facecolor=color, edgecolor="none",
            transform=fig.transFigure, zorder=4, mutation_aspect=2.5,
        )
        fig.patches.append(patch)
        fig.text((x0 + x1) / 2.0, 1.0 - (y0 + y1) / 2.0, label,
                 color=TXT, fontsize=10, ha="center", va="center", zorder=5)

    fig_box(0.09325, 0.73338, 0.83552, 0.88698, C_2021, "2021")
    fig_box(0.74219, 0.97702, 0.83427, 0.88943, C_2022, "2022")

    fig.text(0.03554, 1.0 - 0.04, TITLE, color=TXT, fontsize=20,
             fontweight="bold", ha="left", va="top")
    fig.text(0.03554, 1.0 - 0.14, SUBTITLE, color=TXT, fontsize=14,
             ha="left", va="top")
    fig.text(0.02819, 1.0 - 0.92, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "11_平滑折线图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
