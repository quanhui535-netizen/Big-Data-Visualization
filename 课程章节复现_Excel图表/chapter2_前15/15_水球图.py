# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第15张：水球图（圆内 65% 水位）
源: 第二章 图表(前15).xlsx / 「15 水球图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__15_水球图__chart1.png
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge, FancyBboxPatch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

PCT = 0.65
C_WATER = "#0070C0"
C_RING = "#1F4E8C"  # 外圈深蓝
C_RING2 = "#2A5FA8"

CENTER_TEXT = "65%"

# userShapes 椭圆几乎铺满图；文本框 65% 在中上
W_IN = 416.0 / 72.0
H_IN = 416.0 / 72.0  # 近似正方（drawing 较小区域）


def main():
    # 参考图 360x360 正方
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.axis("off")

    cx, cy = 0.5, 0.5
    r = 0.47

    # 外圈双线（参考图：外细环 + 内粗环，中间深色缝）
    ax.add_patch(Circle((cx, cy), r, fill=False, edgecolor=C_RING,
                        linewidth=2.0, zorder=2))
    ax.add_patch(Circle((cx, cy), r * 0.93, fill=False, edgecolor=C_RING,
                        linewidth=3.5, zorder=2))

    r_in = r * 0.88
    # 空白上半（底色）+ 下半水
    ax.add_patch(Circle((cx, cy), r_in, facecolor=BG, edgecolor="none", zorder=3))
    # 水位：65% 面积从底部 => 水位线 y
    # 圆面积在高度 h 以下比例 = 0.65
    # 用角度扇形近似水位：简单水平切割
    # 面积比从底部: (1/π)*(θ - sinθ cosθ) 类公式；数值解 h
    from scipy.optimize import brentq
    # 若无 scipy，二分
    def frac_above(h):
        # h in [-1,1] from center, area below y=h for unit circle / π
        if h <= -1:
            return 0.0
        if h >= 1:
            return 1.0
        # area below h: (acos(-h) - (-h)*sqrt(1-h^2)) / π wait
        # segment area above y=h: r^2 * acos(h/r) - h*sqrt(r^2-h^2), / (π r^2)
        # unit r=1
        import math
        if abs(h) >= 1:
            return 1.0 if h >= 1 else 0.0
        seg = math.acos(h) - h * math.sqrt(max(0.0, 1 - h * h))
        return 1.0 - seg / math.pi  # fraction below h

    lo, hi = -1.0, 1.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if frac_above(mid) < PCT:
            lo = mid
        else:
            hi = mid
    h = (lo + hi) / 2

    # 水：矩形裁剪圆
    theta = np.linspace(0, np.pi, 128)
    # 底部圆弧 + 水平顶
    xs = np.concatenate([
        np.linspace(-np.sqrt(max(0, 1 - h * h)), np.sqrt(max(0, 1 - h * h)), 32),
        np.linspace(np.sqrt(max(0, 1 - h * h)), -np.sqrt(max(0, 1 - h * h)), 96),
    ])
    # 上边界水平，下边界圆弧
    top_x = np.linspace(-np.sqrt(max(0.0, 1 - h * h)), np.sqrt(max(0.0, 1 - h * h)), 64)
    bot_x = np.linspace(np.sqrt(max(0.0, 1 - h * h)), -np.sqrt(max(0.0, 1 - h * h)), 96)
    bot_y = -np.sqrt(np.clip(1 - bot_x ** 2, 0, None))
    poly_x = np.concatenate([top_x, bot_x])
    poly_y = np.concatenate([np.full_like(top_x, h), bot_y])
    # scale to fig
    px = cx + poly_x * r_in
    py = cy + poly_y * r_in
    ax.fill(px, py, color=C_WATER, zorder=4, linewidth=0)

    # 参考图：65% 骑在水位线上（中心略低于线）
    water_y = cy + h * r_in
    ax.text(cx, water_y - r_in * 0.06, CENTER_TEXT, color=TXT, fontsize=56,
            ha="center", va="center", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "15_水球图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
