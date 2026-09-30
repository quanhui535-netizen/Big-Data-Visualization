# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第10张：甘特图（水平堆叠 透明起点 + 项目天数，双色进度）
源: 第二章 图表(前15).xlsx / 「10 甘特图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__10_甘特图__chart1.png
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

tasks = ["制定计划", "方案设计", "资源调配", "第一阶段", "第二阶段", "第三阶段", "项目总结"]
starts = ["2022-03-01", "2022-03-13", "2022-03-22", "2022-04-02", "2022-04-16", "2022-05-11", "2022-05-26"]
durations = [11, 8, 10, 13, 24, 14, 7]
progress_ratio = [0.51, 0.32, 0.21, 0.85, 0.36, 0.68, 0.68]
progress_days = [5.61, 2.56, 2.1, 11.05, 8.64, 9.52, 4.76]

C_DONE = "#0070C0"
C_REST = "#00B0F0"

TITLE = "2022年化妆品类目采购项目进度"

W_IN = 416.0 / 72.0
H_IN = 308.0 / 72.0

# manualLayout chart9: x=0.16560 y=0.22376 w=0.74318 h=0.71790
PX, PY_TOP, PW, PH = 0.16559865007057803, 0.22376064832968201, 0.74318275115993693, 0.71789530120960543
PY = 1.0 - PY_TOP - PH

GAP_W = 100.0
BAR_FRAC = 1.0 / (1.0 + GAP_W / 100.0)  # 0.5


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([PX, PY, PW, PH])
    ax.set_facecolor(BG)

    # Excel 日期序列号 44621=2022-03-01, 轴 44621..44726
    d0 = datetime(2022, 3, 1)
    d1 = datetime(2022, 6, 14)
    x0, x1 = mdates.date2num(d0), mdates.date2num(d1)

    # 类目自上而下 = 数据顺序（Excel bar 首类在底，但甘特图原图首类在顶）
    # 原图：制定计划在顶 => 数据正序从上到下
    y = np.arange(len(tasks), dtype=float)[::-1]  # 顶=制定计划
    bh = BAR_FRAC

    for yi, st, dur, pd, ratio in zip(y, starts, durations, progress_days, progress_ratio):
        left = mdates.date2num(datetime.strptime(st, "%Y-%m-%d"))
        # 进度段（深）
        ax.barh(yi, pd, height=bh, left=left, color=C_DONE, zorder=2, linewidth=0)
        # 剩余段（浅）
        rest = dur - pd
        if rest > 0:
            ax.barh(yi, rest, height=bh, left=left + pd, color=C_REST, zorder=2, linewidth=0)
        # 进度标签 ctr 在深色段
        ax.text(left + pd / 2.0, yi, f"{ratio:.0%}", ha="center", va="center",
                color=TXT, fontsize=9, zorder=5)

    ax.set_xlim(x0, x1)
    ax.set_ylim(-0.5, len(tasks) - 0.5)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    # 顶部日期刻度（axes 坐标 y>1 固定在图区上方）
    from matplotlib.transforms import blended_transform_factory
    tr = blended_transform_factory(ax.transData, ax.transAxes)
    ticks = [mdates.date2num(datetime(2022, m, d))
             for m, d in [(3, 1), (3, 16), (3, 31), (4, 15), (4, 30), (5, 15), (5, 30), (6, 14)]]
    for t in ticks:
        ax.axvline(t, color=TXT, linewidth=0.8, alpha=0.25,
                   linestyle=(0, (6, 4)), zorder=1, clip_on=False)
        dt = mdates.num2date(t)
        ax.text(t, 1.04, f"{dt.year}/{dt.month}/{dt.day}",
                ha="center", va="bottom", color=TXT, fontsize=8,
                transform=tr, clip_on=False, zorder=5)

    # 类目左侧
    for yi, name in zip(y, tasks):
        ax.text(-0.02, yi, name, ha="right", va="center", color=TXT,
                fontsize=9, transform=ax.get_yaxis_transform(),
                clip_on=False, zorder=5)

    fig.text(0.5, 1.0 - 0.06, TITLE, color=TXT, fontsize=16,
             fontweight="bold", ha="center", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "10_甘特图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
