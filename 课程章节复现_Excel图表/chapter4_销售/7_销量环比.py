# -*- coding: utf-8 -*-
"""第四章 销售看板 第7张：销量环比（条形）
源: 第四章 销售看板参考.xlsx / chart7
参考原图: ...\\ch4_sales__数据大屏__chart7.png
实现: 横向条 8月蓝/9月青；数据标签 outEnd；userShapes 同比/5.18%
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import TXT, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BG_PANEL = "#2C3560"
C_CYAN = "#7BBDD5"
C_BLUE = "#4A5BD1"

W_PX, H_PX = 554, 236
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

TITLE = "销量环比"
T_X, T_Y, T_PT = W_PX / 2.0, 26.0, 16.0

# measured: 9月 top bar cyan x54-393 y106-127; 8月 blue x54-216 y170-192
X0 = 54.0
BAR_H = 22.0
ROW9_Y = 116.5  # center
ROW8_Y = 181.0
LEN9 = 393.0 - X0  # 339
LEN8 = 216.0 - X0  # 162

CAT_PT = 18.0  # catAx 900 * 2
VAL_PT = 16.0
PCT_PT = 24.0  # bold-ish big
FOOT_PT = 18.0

CAT_X = 36.0  # right-aligned near 32
V9_X = 407.0
PCT_X = 474.0
YR_Y = 181.0
TONG_Y = 198.0  # 同比 lower right - from drawing y~0.75


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

    # 9月
    ax.plot([X0 + LEN9 / 2, X0 + LEN9 / 2], [ROW9_Y, ROW9_Y],
            color=C_CYAN, linewidth=0)  # noop keep style simple
    ax.fill([X0, X0 + LEN9, X0 + LEN9, X0],
            [ROW9_Y - BAR_H / 2, ROW9_Y - BAR_H / 2,
             ROW9_Y + BAR_H / 2, ROW9_Y + BAR_H / 2],
            color=C_CYAN, zorder=3)
    # 8月
    ax.fill([X0, X0 + LEN8, X0 + LEN8, X0],
            [ROW8_Y - BAR_H / 2, ROW8_Y - BAR_H / 2,
             ROW8_Y + BAR_H / 2, ROW8_Y + BAR_H / 2],
            color=C_BLUE, zorder=3)

    ax.text(CAT_X, ROW9_Y, "9月", color=TXT, fontsize=CAT_PT,
            ha="right", va="center", zorder=6)
    ax.text(CAT_X, ROW8_Y, "8月", color=TXT, fontsize=CAT_PT,
            ha="right", va="center", zorder=6)

    ax.text(V9_X, ROW9_Y, "751", color=TXT, fontsize=VAL_PT,
            ha="left", va="center", zorder=6)
    ax.text(X0 + LEN8 + 14, ROW8_Y, "714", color=TXT, fontsize=VAL_PT,
            ha="left", va="center", zorder=6)

    ax.text(PCT_X, ROW9_Y, "5.18%", color=TXT, fontsize=PCT_PT,
            fontweight="bold", ha="left", va="center", zorder=6)
    ax.text(PCT_X, ROW8_Y, "同比", color="#D9D9D9", fontsize=FOOT_PT,
            ha="left", va="center", zorder=6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "7_销量环比.png")
    save_fig(fig, out, facecolor=BG_PANEL)


if __name__ == "__main__":
    main()
