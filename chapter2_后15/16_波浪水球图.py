# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第16张：波浪水球图
源: 第二章 图表(后15).xlsx / 「16 波浪水球图 」
参考: ch2_back__16_波浪水球图___chart1.png + COM 形状坐标
实现: 圆内波浪水位65% + 标题/副标题/脚注
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

TITLE = "本科及以上学历员占比"
SUBTITLE = "6月30日最新统计数据本科及以上员工占比65%"
FOOTNOTE = "*注：数据来源于公司人力资源系统"
CENTER_TEXT = "65%"

# 只保留水球区域（右侧装饰去掉后收窄）
W_PX, H_PX = 610, 579
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

T_X, TITLE_Y, SUB_Y = 0.75, 2.0, 58.0
TITLE_PT, SUB_PT = 40.0, 28.0
F_X, F_Y, FOOT_PT = 0.0, 538.0, 16.0

# chart 左上 + 内部几何（ref 405x400 局部，y 向下）
CH_X, CH_Y = 193.0, 128.25
CX_L, CY_L = 200.0, 198.0
R_OUT = 192.0
CX, CY = CH_X + CX_L, CH_Y + CY_L

BLUE = "#0070C0"
RING_LW = 3.0  # 1.5pt * 2

# ref 实测水位（chart 局部 x, y）
WAVE_XY = [
    (20.0, 175.0), (30.0, 166.0), (40.0, 151.0), (50.0, 148.0),
    (60.0, 147.0), (70.0, 147.0), (80.0, 149.0), (90.0, 152.0),
    (100.0, 154.0), (110.0, 158.0), (120.0, 161.0), (130.0, 164.0),
    (140.0, 167.0), (150.0, 168.5), (160.0, 169.5), (170.0, 170.0),
    (180.0, 168.0), (190.0, 165.5), (200.0, 164.0), (210.0, 164.5),
    (220.0, 165.5), (230.0, 166.5), (240.0, 167.5), (250.0, 168.5),
    (260.0, 169.5), (270.0, 170.0), (280.0, 168.5), (290.0, 164.0),
    (300.0, 161.0), (310.0, 164.0), (320.0, 167.0), (330.0, 169.0),
    (340.0, 171.0), (350.0, 170.5), (360.0, 169.0), (370.0, 167.0),
    (380.0, 168.0), (390.0, 175.0),
]


def wave_y(x):
    xs = [p[0] for p in WAVE_XY]
    ys = [p[1] for p in WAVE_XY]
    return float(np.interp(x, xs, ys))


def water_polygon():
    """波浪顶 + 圆底，顶点已落在圆内/圆上，避免 clip 横线"""
    cx_l, cy_l, r = CX_L, CY_L, R_OUT
    # 沿波浪从左到右
    pts = []
    for x in np.linspace(8.0, 392.0, 200):
        y = wave_y(float(x))
        pts.append((x, y))
    # 沿圆底从右到左（下半圆）
    x_r, x_l = pts[-1][0], pts[0][0]

    def circle_bottom(x):
        dx = x - cx_l
        dy2 = r * r - dx * dx
        return cy_l + np.sqrt(max(dy2, 0.0))

    for x in np.linspace(x_r, x_l, 80):
        pts.append((float(x), float(circle_bottom(float(x)))))
    # 转为画布坐标
    return [(CH_X + x, CH_Y + y) for x, y in pts]


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    # 外环外的圆面与背景同色（ref 内部即 #1A1E43）
    # 水体（已裁剪几何，无 clip_path）
    ax.add_patch(Polygon(water_polygon(), closed=True, facecolor=BLUE,
                         edgecolor="none", zorder=3))

    # 外环
    ax.add_patch(Circle((CX, CY), R_OUT, facecolor="none", edgecolor=BLUE,
                        linewidth=RING_LW, zorder=5))

    # 65%：ref 白字 bbox x145-275 y156-208，中心 (210, 182)，高52
    # 当前输出 y149-200，需下移 7
    ax.text(CH_X + 210.0, CH_Y + 189.0, CENTER_TEXT, color=TXT,
            fontsize=68.0, ha="center", va="center", zorder=6)

    # 标题 / 副标题 / 脚注
    ax.text(T_X, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=8)
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=8)
    ax.text(F_X, F_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "16_波浪水球图.png")
    save_fig(fig, out, facecolor=BG)


if __name__ == "__main__":
    main()
