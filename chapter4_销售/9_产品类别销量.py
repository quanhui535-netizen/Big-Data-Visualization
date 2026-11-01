# -*- coding: utf-8 -*-
"""第四章 销售看板 第9张：产品类别销量（圆环+图例）
源: 第四章 销售看板参考.xlsx / chart9
参考原图: ...\\ch4_sales__数据大屏__chart9.png
实现: doughnut holeSize=85，三色 dpts，右侧图例，中心 总销量751
      ring bbox x79-302 y118-341 => C(190.5,229.5) R=111.5 T=16
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Rectangle

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import TXT, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BG_PANEL = "#2C3560"

W_PX, H_PX = 548, 383
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

TITLE = "产品类别销量"
# title band y26-48 x203-344
T_X, T_Y, T_PT = 273.5, 26.0, 22.0

# ring measured (legend excluded)
CX, CY = 190.5, 229.5
R_OUT = 111.5
RING_T = 16.0

CATS = ["办公用品", "家具产品", "数码电子"]
VALS = [409.0, 156.0, 186.0]
COLORS = ["#FC6C9D", "#4A5BD1", "#F6A576"]
TOTAL = 751.0

# percent labels outside ring
# 25% y121-132 x74-103; 54% y249-260 x318-346; 21% y305-321 x61-90
PCT_POS = [(74.0, 121.0), (318.0, 249.0), (61.0, 305.0)]
PCT_TXT = ["25%", "54%", "21%"]
PCT_PT = 16.0

# center 751 band y205-238 x157-222
CENTER_PT = 40.0
C751_X, C751_Y = 189.5, 221.0
# 总销量 wraps y270 / y305 x160
TSC_PT = 16.0
TSC_X = 160.0
TSC_Y1 = 270.0
TSC_Y2 = 305.0

# legend swatches x413-421 y163/227/291; text x426+
LEG_SW_X = 413.0
LEG_SW_W = 10.0
LEG_SW_Y = [163.0, 227.0, 291.0]
LEG_TXT_X = 426.0
LEG_TXT_Y = [160.0, 224.0, 288.0]
LEG_PT = 16.0


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

    cum = 0.0
    for v, col in zip(VALS, COLORS):
        sweep = 360.0 * v / TOTAL
        t1 = -90.0 + cum
        t2 = -90.0 + cum + sweep
        ax.add_patch(Wedge((CX, CY), R_OUT, t1, t2, width=RING_T,
                           facecolor=col, edgecolor="none", zorder=3))
        cum += sweep

    for (lx, ly), p in zip(PCT_POS, PCT_TXT):
        ax.text(lx, ly, p, color=TXT, fontsize=PCT_PT, ha="left", va="top",
                zorder=6)

    ax.text(C751_X, C751_Y, "751", color=TXT, fontsize=CENTER_PT,
            ha="center", va="top", zorder=6)
    ax.text(TSC_X, TSC_Y1, "总销", color="#D9D9D9", fontsize=TSC_PT,
            ha="left", va="top", zorder=6)
    ax.text(TSC_X, TSC_Y2, "量", color="#D9D9D9", fontsize=TSC_PT,
            ha="left", va="top", zorder=6)

    for lab, col, sy, ty in zip(CATS, COLORS, LEG_SW_Y, LEG_TXT_Y):
        ax.add_patch(Rectangle((LEG_SW_X, sy), LEG_SW_W, LEG_SW_W,
                               facecolor=col, edgecolor="none", zorder=5))
        ax.text(LEG_TXT_X, ty, lab, color=TXT,
                fontsize=LEG_PT, ha="left", va="top", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "9_产品类别销量.png")
    save_fig(fig, out, facecolor=BG_PANEL)


if __name__ == "__main__":
    main()
