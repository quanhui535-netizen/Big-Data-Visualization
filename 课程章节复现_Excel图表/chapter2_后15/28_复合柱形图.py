# -*- coding: utf-8 -*-
"""第二章 图表(后15) 第28张：复合柱形图
源: 第二章 图表(后15).xlsx / 「28 复合柱形图」
参考原图: D:\\Software\\node\\bipviz\\references\\ch2_back__28_复合柱形图__chart1.png
实现: 双 barChart——季度宽背景柱(半透明色) + 月度窄柱(季度色系)
      宽柱季度总额标签在上；窄柱月度标签在上；按季度分4组
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common_style import BG, TXT, TXT_DIM, save_fig

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

W_PX, H_PX = 844, 603
W_IN, H_IN = W_PX / 72.0, H_PX / 72.0

MONTHS = ["1月", "2月", "3月", "4月", "5月", "6月",
          "7月", "8月", "9月", "10月", "11月", "12月"]
M_VALS = [2354, 1902, 3524, 2698, 2896, 2563,
          3156, 2896, 3621, 2635, 2963, 2789]
Q_VALS = ["7780", "8157", "9673", "8387"]

BAR_BOTTOM = 500.0

# 宽季度柱: x0, x1, top, color
WIDE = [
    (82.0, 214.0, 243.0, (36, 42, 96)),
    (260.0, 393.0, 231.0, (71, 46, 57)),
    (438.0, 571.0, 181.0, (70, 57, 56)),
    (616.0, 749.0, 223.0, (53, 37, 79)),
]
# 季度标签 (va=top y, 中心 x)
QLAB_Y = [218.0, 206.0, 156.0, 198.0]
QLAB_CX = [147.5, 325.5, 504.5, 682.5]

# 窄月柱: x0, top, color, label_y
NARROW_X = [95.0, 139.0, 184.0, 273.0, 318.0, 362.0,
            452.0, 496.0, 541.0, 630.0, 674.0, 719.0]
NARROW_TOPS = [423.0, 438.0, 384.0, 411.0, 405.0, 416.0,
               396.0, 405.0, 381.0, 414.0, 403.0, 408.0]
NARROW_LAB_Y = [399.0, 414.0, 361.0, 388.0, 381.0, 392.0,
                373.0, 381.0, 357.0, 390.0, 379.0, 385.0]
NARROW_CX = [103.5, 147.5, 192.5, 281.5, 326.5, 370.5,
             460.0, 504.5, 549.5, 638.5, 682.5, 727.5]
NARROW_W = 18.0
NARROW_COLS = [
    (74, 91, 209), (74, 91, 209), (74, 91, 209),
    (252, 108, 15), (252, 108, 15), (252, 108, 15),
    (246, 165, 11), (246, 165, 11), (246, 165, 11),
    (162, 65, 123), (162, 65, 123), (162, 65, 123),
]

LAB_PT = 16.0
CAT_Y = 516.0

TITLE = "2021年各月化妆品销量走势"
SUBTITLE = "2021年第三季度销量最多9673，9月单月销量最大3621"
FOOTNOTE = "*注：数据来源于公司销售系统，统计日期截至2021.12.31"

T_X = 59.0
TITLE_Y, TITLE_PT = 42.0, 36.0
SUB_Y, SUB_PT = 97.0, 22.0
FOOT_X, FOOT_Y, FOOT_PT = 50.0, 567.0, 16.0

AXIS_X0, AXIS_X1 = 82.0, 749.0
AXIS_Y = 500.5


def rgb(c):
    return "#%02X%02X%02X" % c


def main():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=150)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX)
    ax.set_ylim(H_PX, 0)
    ax.set_facecolor(BG)
    ax.axis("off")

    # 轴线
    ax.plot([AXIS_X0, AXIS_X1], [AXIS_Y, AXIS_Y], color="#4A4F7B",
            linewidth=1.0, zorder=2)

    # 宽季度柱
    for i, (x0, x1, top, col) in enumerate(WIDE):
        ax.add_patch(Rectangle((x0, top), x1 - x0, BAR_BOTTOM - top,
                               facecolor=rgb(col), edgecolor="none", zorder=3))
        ax.text(QLAB_CX[i], QLAB_Y[i], Q_VALS[i], color=TXT,
                fontsize=LAB_PT, ha="center", va="top", zorder=6)

    # 窄月柱
    for i in range(12):
        x0 = NARROW_X[i]
        top = NARROW_TOPS[i]
        ax.add_patch(Rectangle((x0, top), NARROW_W, BAR_BOTTOM - top,
                               facecolor=rgb(NARROW_COLS[i]),
                               edgecolor="none", zorder=4))
        ax.text(NARROW_CX[i], NARROW_LAB_Y[i], str(M_VALS[i]), color=TXT,
                fontsize=LAB_PT, ha="center", va="top", zorder=7)

    # 类目标签
    for i in range(12):
        ax.text(NARROW_CX[i], CAT_Y, MONTHS[i], color=TXT, fontsize=LAB_PT,
                ha="center", va="top", zorder=6)

    # 文本
    ax.text(T_X, TITLE_Y, TITLE, color=TXT, fontsize=TITLE_PT,
            fontweight="bold", ha="left", va="top", zorder=10)
    ax.text(T_X, SUB_Y, SUBTITLE, color=TXT, fontsize=SUB_PT,
            ha="left", va="top", zorder=10)
    ax.text(FOOT_X, FOOT_Y, FOOTNOTE, color=TXT_DIM, fontsize=FOOT_PT,
            ha="left", va="top", zorder=10)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "images", "28_复合柱形图.png")
    save_fig(fig, out)


if __name__ == "__main__":
    main()
