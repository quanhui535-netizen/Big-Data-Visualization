# -*- coding: utf-8 -*-
"""第四章 销售看板 第8张：各月销售额(万)（面积图）
源: 第四章 销售看板参考.xlsx / chart8
参考原图: ...\\ch4_sales__数据大屏__chart8.png
实现: 面积垂直渐变 #4A5BD1 alpha 0.97->0.22 (y132->271.5)，y轴 0-200
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import TXT, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BG_PANEL = "#2C3560"
AREA = (74, 91, 209)  # #4A5BD1

W_PX, H_PX = 553, 324
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

TITLE = "各月销售额(万)"
CATS = ["1月", "2月", "3月", "4月", "5月", "6月",
        "7月", "8月", "9月", "10月", "11月", "12月"]
VALS = [145.224607, 118.62991244999999, 131.26952514999982,
        124.2604811999999, 116.50837705000008, 108.1053584,
        121.61598545000027, 111.74269720000008, 134.28874355000011,
        137.28172690000008, 119.55373105000004, 146.87382219999995]

T_X, T_Y, T_PT = W_PX / 2.0, 26.0, 24.0

Y0 = 271.5
Y200 = 80.5
PPU = (Y0 - Y200) / 200.0

X0 = 78.5
X1 = 513.0
DX = (X1 - X0) / 11.0

# vertical gradient measured: alpha 0.97 @ y=132 -> 0.22 @ y=271.5
GRAD_Y0 = 132.0
GRAD_A0 = 0.97
GRAD_A1 = 0.22

LBL_PT = 16.0
CAT_Y = 292.0
Y_TICK_PT = 16.0
Y_TICK_X = 62.0
Y_TICK_DY = 2.5  # out ink 2.5px high vs ref
Y_TICKS = [(200.0, "200.00"), (150.0, "150.00"), (100.0, "100.00"),
           (50.0, "50.00"), (0.0, "0.00")]


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG_PANEL)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG_PANEL)
    ax.axis("off")

    ax.text(T_X, T_Y, TITLE, color=TXT, fontsize=T_PT,
            ha="center", va="top", zorder=6)

    xs = [X0 + i * DX for i in range(12)]
    tops = [Y0 - v * PPU for v in VALS]
    poly_x = xs + [X1, X0]
    poly_y = tops + [Y0, Y0]
    path = Path(np.column_stack([poly_x, poly_y]))

    # vertical gradient RGBA clipped to area polygon
    n = 400
    ys = np.linspace(0.0, H_PX, n)
    a = GRAD_A0 + (GRAD_A1 - GRAD_A0) * (ys - GRAD_Y0) / (Y0 - GRAD_Y0)
    a = np.clip(a, 0.0, 1.0)
    rgba = np.zeros((n, 2, 4), dtype=float)
    rgba[:, :, 0] = AREA[0] / 255.0
    rgba[:, :, 1] = AREA[1] / 255.0
    rgba[:, :, 2] = AREA[2] / 255.0
    rgba[:, :, 3] = a[:, None]
    im = ax.imshow(rgba, extent=(0, W_PX, H_PX, 0), origin="upper",
                   aspect="auto", interpolation="bilinear", zorder=3)
    im.set_clip_path(path, transform=ax.transData)

    ax.plot(xs, tops, color="#4A5BD1", linewidth=1.5, zorder=4)

    for v, lab in Y_TICKS:
        y = Y0 - v * PPU + Y_TICK_DY
        ax.text(Y_TICK_X, y, lab, color=TXT,
                fontsize=Y_TICK_PT, ha="right", va="center", zorder=6)

    for i, c in enumerate(CATS):
        ax.text(xs[i], CAT_Y, c, color=TXT, fontsize=LBL_PT,
                ha="center", va="top", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "8_各月销售额.png")
    save_fig(fig, out, facecolor=BG_PANEL)


if __name__ == "__main__":
    main()
