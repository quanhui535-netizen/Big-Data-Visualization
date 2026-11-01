# -*- coding: utf-8 -*-
"""第二章 图表(前15) 第14张：单值圆环图（渐变 85%）
源: 第二章 图表(前15).xlsx / 「14 单值圆环图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_front__14_单值圆环图__chart1.png
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

PCT = 0.85
C_FROM = "#7030A0"
C_TO = "#E74E69"
C_REST = "#2A2F55"  # 原图残余段：接近底色略亮

TITLE = "2022年上半年目标完成率"
SUBTITLE = "截至6月30日销售目标总体完成率达到85%"
CENTER_MAIN = "85%"
CENTER_SUB = "目标完成率"
FOOTNOTE = "*注：数据来源于公司销售系统"

W_IN = 416.0 / 72.0
H_IN = 308.0 / 72.0


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_aspect("equal")
    ax.axis("off")

    # 圆环：manualLayout chart13 中心约 (0.508, 0.559) h=0.565
    # 在 fig 归一化圆：cx=0.508, cy=1-0.559=0.441? y 向下 => cy=0.2767+0.5647/2=0.559 from top => fig y=0.441
    cx, cy = 0.508, 1.0 - (0.27674437501209154 + 0.56470093572455782 / 2.0)
    # 半径：按高度 0.565*H / 2，用 data 单位 = fig 单位，需按宽高比
    # 用圆：r 以 min 尺寸
    r_out = 0.56470093572455782 / 2.0
    # 宽方向 0.4225/2 更小，圆用宽度约束
    r_out = min(0.42248764860274818 / 2.0, 0.56470093572455782 / 2.0) * 1.0
    # 实际椭圆区域，圆环 thickness
    # 参考图环较粗：thickness ≈ 0.08 of diameter
    r_in = r_out * 0.86

    # 起始角：Excel 渐变 ang=5400000 = 90°，85% 从顶部逆时针？
    # 参考图：紫色在顶，粉在底，缺口在左上；完成段逆时针从顶开始？
    # 图：从约 10 点方向缺口，顺时针紫->粉 85%，残段左上灰
    # Excel doughnut 默认从 12 点顺时针。85% => 306°，残 54° 在左侧偏上
    theta1 = 90 - PCT * 360  # 从12点顺时针：结束角
    # matplotlib Wedge: 从 theta1 逆时针到 theta2
    # 画残段先
    ax.add_patch(Wedge((cx, cy), r_out, 90 - 360 + PCT * 360, 90 + 0.001,
                       width=r_out - r_in, facecolor=C_REST, edgecolor="none",
                       zorder=2))
    # 完成段用渐变：分段
    n = 64
    from matplotlib.colors import to_rgb
    c0 = np.array(to_rgb(C_FROM))
    c1 = np.array(to_rgb(C_TO))
    start = 90.0
    end = 90.0 - PCT * 360.0  # 顺时针减角
    for i in range(n):
        a0 = start + (end - start) * i / n
        a1 = start + (end - start) * (i + 1) / n
        t = i / (n - 1)
        col = c0 + (c1 - c0) * t
        # Wedge 逆时针 from smaller to larger
        lo, hi = min(a0, a1), max(a0, a1)
        if hi - lo < 0.01:
            continue
        ax.add_patch(Wedge((cx, cy), r_out, lo, hi + 0.05,
                           width=r_out - r_in,
                           facecolor=col, edgecolor="none", zorder=3))

    ax.text(cx, cy + 0.04, CENTER_MAIN, color=TXT, fontsize=36,
            ha="center", va="center", zorder=5)
    ax.text(cx, cy - 0.14, CENTER_SUB, color=TXT_DIM, fontsize=11,
            ha="center", va="center", zorder=5)

    fig.text(0.04197, 1.0 - 0.055, TITLE, color=TXT, fontsize=18,
             fontweight="bold", ha="left", va="top")
    fig.text(0.04197, 1.0 - 0.16, SUBTITLE, color=TXT, fontsize=12,
             ha="left", va="top")
    fig.text(0.03646, 1.0 - 0.925, FOOTNOTE, color=TXT_DIM, fontsize=8,
             ha="left", va="top")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "14_单值圆环图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
