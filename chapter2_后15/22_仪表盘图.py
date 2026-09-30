# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第22张：仪表盘图
源: 第二章 图表(后15).xlsx / 「22 仪表盘图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__22_仪表盘图__chart1.png
实现: doughnut holeSize=70 firstSliceAng=225，3 层同心环；
      中环色带 teal/yellow/red + 底部缺口，外环全蓝；BG 刻度线每 27°
"""
import os
import sys
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

W_PX, H_PX = 832, 638
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

CX, CY = 430.5, 393.5
R_OUT = 197.5
R_HOLE = 138.25  # 0.7 * R_OUT
# 3 环均分
RING_W = (R_OUT - R_HOLE) / 3.0
R0_IN, R0_OUT = R_HOLE, R_HOLE + RING_W          # 内环 BG（不可见）
R1_IN, R1_OUT = R0_OUT + 0.5, R0_OUT + RING_W - 0.5  # 中环色带
R2_IN, R2_OUT = R1_OUT + 0.5, R_OUT              # 外环蓝

# firstSliceAng=225，0°=北，顺时针
START = 225.0
TICK_STEP = 27.0  # 每 27° 一刻度（0,27,...,90 模式）

# 刻度值 -> 角度：50@225° 顺时针到 150@135°（跨 270°）
def val_angle(v):
    return (START + (v - 50.0) / 100.0 * 270.0) % 360.0

# 中环色带（ref 实测角域）
# teal 50-80 (225-306), yellow 80-120 (306-54), red 120-150 (54-135), 缺口 150-50
ZONE_BANDS = [
    ("#087E8B", 225.0, 306.0),
    ("#FFC54D", 306.0, 54.0 + 360.0),  # 跨 0
    ("#F94C66", 54.0, 135.0),
]

BLUE = "#0070C0"

# 刻度标签（ref 实测中心）
LABELS = [
    (50, 325.5, 499.0),
    (60, 289.5, 440.0),
    (70, 283.5, 370.0),
    (80, 310.5, 306.0),
    (90, 362.5, 261.0),
    (100, 431.0, 245.0),
    (110, 498.0, 261.0),
    (120, 551.0, 306.0),
    (130, 577.0, 370.0),
    (140, 572.0, 440.0),
    (150, 536.0, 499.0),
]
LAB_PT = 16.0

TITLE = "2022年6月29公司整体运营指数良好"
TITLE_Y, TITLE_PT = 63.0, 36.0

CENTER_VAL = "76"
VAL_CX, VAL_CY, VAL_PT = 431.5, 488.0, 48.0

NEEDLE_ANG = val_angle(76.0)  # 295.2
NEEDLE_R = 137.6
NEEDLE_LW = 2.5


def sweep(a0, a1):
    """返回可用于 Wedge 的 (theta1, theta2)（y 向下坐标系，12点=-90）"""
    # 内部用 0=北 顺时针；Wedge 用标准角（0=东 逆时针）
    # 转换: math_angle = 90 - clockwise_from_north
    def to_wedge(cw):
        return 90.0 - cw
    # 处理跨 0
    span = (a1 - a0) % 360.0
    if span == 0:
        span = 360.0
    # y 向下：Wedge 的角度也是 y 向下时 0=东 顺时针？
    # matplotlib Wedge: 角度逆时针从东起，在 y 向下的轴上视觉为顺时针。
    # 我们用 ax 时 y 向下，Wedge(theta1, theta2) 从 theta1 逆时针到 theta2（数学逆时针 = 屏幕顺时针因 y 翻转）。
    # 统一：clockwise_from_north cw -> math angle = 90 - cw (standard math, y-up)
    # 在 y-down axes 上，Wedge 仍按数据坐标角度画：theta 增大方向 = x 轴向 y 轴正方向（向下）转...
    # 实践：与 19/20 相同，12点用 -90，顺时针增大。
    # cw=0 (北) -> -90; cw=90 (东) -> 0; 即 wedge_angle = cw - 90
    t1 = a0 - 90.0
    t2 = a0 - 90.0 + span
    return t1, t2


def draw_ring(ax, r_in, r_out, a0, a1, color, zorder=3):
    t1, t2 = sweep(a0, a1)
    ax.add_patch(Wedge((CX, CY), r_out, t1, t2, width=r_out - r_in,
                       facecolor=color, edgecolor="none", zorder=zorder))


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    # 内环 BG（覆盖中心区，等效 hole）
    # 实际 hole 内为 BG 背景，无需画

    # 中环色带
    for color, a0, a1 in ZONE_BANDS:
        draw_ring(ax, R1_IN, R1_OUT, a0, a1, color, zorder=3)

    # 外环全蓝
    draw_ring(ax, R2_IN, R2_OUT, 0.0, 360.0, BLUE, zorder=4)

    # 刻度线：从 START 每 27°，贯穿中+外环（跳过底部缺口的中环仍画外环刻度）
    n_ticks = int(360.0 / TICK_STEP)
    for k in range(n_ticks + 1):
        ang = (START + k * TICK_STEP) % 360.0
        rad = math.radians(ang)
        # 0=北顺时针: x=sin, y=-cos (y 向下)
        sx, sy = math.sin(rad), -math.cos(rad)
        # 外环刻度
        x0, y0 = CX + R2_IN * sx, CY + R2_IN * sy
        x1, y1 = CX + R2_OUT * sx, CY + R2_OUT * sy
        ax.plot([x0, x1], [y0, y1], color=BG, linewidth=1.4, zorder=6)
        # 中环刻度（仅在有色区域）
        if 225.0 <= (ang if ang >= 225 else ang + 360) <= 495.0:  # 225..135+360
            x0, y0 = CX + R1_IN * sx, CY + R1_IN * sy
            x1, y1 = CX + R1_OUT * sx, CY + R1_OUT * sy
            ax.plot([x0, x1], [y0, y1], color=BG, linewidth=1.4, zorder=6)

    # 中环与外环之间的分隔（已有 0.5 缝隙，BG 底色可见）

    # 刻度标签
    for v, lx, ly in LABELS:
        ax.text(lx, ly, str(v), color=TXT, fontsize=LAB_PT,
                ha="center", va="center", zorder=7)

    # 指针
    rad = math.radians(NEEDLE_ANG)
    dx, dy = math.sin(rad), -math.cos(rad)
    # 从中心略内到 NEEDLE_R
    ax.plot([CX, CX + NEEDLE_R * dx], [CY, CY + NEEDLE_R * dy],
            color=TXT, linewidth=NEEDLE_LW, solid_capstyle="round", zorder=8)

    # 中心数值
    ax.text(VAL_CX, VAL_CY, CENTER_VAL, color=TXT, fontsize=VAL_PT,
            fontweight="bold", ha="center", va="top", zorder=8)

    # 标题
    ax.text(W_PX / 2.0, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="center", va="top", zorder=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "22_仪表盘图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
