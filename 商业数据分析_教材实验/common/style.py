# -*- coding: utf-8 -*-
"""
common/style.py
===============
全仓库统一的绘图风格与工具函数。

设计目标
--------
1. **中文不乱码**：统一指定微软雅黑 / 黑体字体，并修正负号显示；
2. **视觉一致**：所有实验共用一套主色、网格、坐标轴样式，图片风格统一；
3. **少写重复代码**：提供 ``save_fig`` / ``bar_labels`` / ``fmt_wan`` 等快捷函数，
   让每个实验脚本专注于"分析逻辑"本身，而不是 matplotlib 的样板代码。

使用方式
--------
在每个实验脚本开头：::

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from common.style import (
        PALETTE, apply_style, new_fig, save_fig,
        bar_labels, fmt_wan, save_csv,
    )
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 服务器 / 无界面环境也能出图
import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.lines import Line2D

# ---------------------------------------------------------------------------
# 配色：取自 Power BI 默认主题 + 商务报告常用色
# ---------------------------------------------------------------------------
PALETTE = [
    "#1F4E79",  # 深蓝（主色）
    "#2E86AB",  # 中蓝
    "#ED7D31",  # 橙色（对比色）
    "#F4B183",  # 浅橙
    "#4C9F70",  # 绿色（正向）
    "#C0504D",  # 红色（负向）
    "#8064A2",  # 紫色
    "#7F7F7F",  # 中性灰
]
BLUE, BLUE2, ORANGE, ORANGE_L, GREEN, RED, PURPLE, GRAY = PALETTE
POS, NEG = GREEN, RED
GRID_COLOR = "#DCE1E6"
TEXT_COLOR = "#333333"

FONT_CANDIDATES = ["Microsoft YaHei", "SimHei", "SimSun", "DengXian"]


def apply_style(font: str | None = None) -> str:
    """设置全局 rcParams（中文字体、网格、边框、分辨率），返回实际使用的字体名。"""
    import matplotlib.font_manager as fm

    installed = {f.name for f in fm.fontManager.ttflist}
    chosen = font if (font and font in installed) else next(
        (f for f in FONT_CANDIDATES if f in installed), "sans-serif"
    )

    plt.rcParams.update(
        {
            "font.sans-serif": [chosen, *FONT_CANDIDATES],
            "font.family": "sans-serif",
            "axes.unicode_minus": False,       # 负号 "-" 正常显示
            "figure.dpi": 110,
            "savefig.dpi": 160,
            "savefig.bbox": "tight",
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#BFC5CC",
            "axes.labelcolor": TEXT_COLOR,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.labelsize": 10.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID_COLOR,
            "grid.linewidth": 0.8,
            "grid.linestyle": "-",
            "xtick.color": "#555555",
            "ytick.color": "#555555",
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "legend.frameon": False,
            "legend.fontsize": 9.5,
        }
    )
    return chosen


def new_fig(width: float = 8.0, height: float = 4.6, nrows: int = 1, ncols: int = 1, **kw):
    """新建画布，返回 ``(fig, axes)``。"""
    return plt.subplots(nrows, ncols, figsize=(width, height), **kw)


def save_fig(fig, out_dir, name: str, dpi: int = 160) -> Path:
    """保存图片到 ``out_dir``，自动建目录、关画布，返回文件路径。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / name).parent.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.png"
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[图] {path}")
    return path


def save_csv(df, out_dir, name: str, **kw) -> Path:
    """保存表格到 ``out_dir``（UTF-8 with BOM，Excel 直接双击不乱码）。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig", **kw)
    print(f"[表] {path}")
    return path


# ---------------------------------------------------------------------------
# 标注小工具
# ---------------------------------------------------------------------------
def bar_labels(ax, fmt="{:.0f}", offset=3, fontsize=9, color=TEXT_COLOR, rotate=0):
    """给柱状图每根柱子顶部加数值标签。"""
    for rect in ax.patches:
        h = rect.get_height()
        if h != h:  # NaN
            continue
        ax.annotate(
            fmt.format(h),
            xy=(rect.get_x() + rect.get_width() / 2, h),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=fontsize,
            color=color,
            rotation=rotate,
        )


def fmt_wan(v: float, unit: str = "万") -> str:
    """把数字格式化成「1.2万」「3,500」这样便于阅读的字符串。"""
    if abs(v) >= 10000:
        return f"{v / 10000:.1f}{unit}"
    return f"{v:,.0f}"


def money_axis(ax, axis: str = "y"):
    """把坐标轴刻度改成「万」为单位。"""
    fmt = ticker.FuncFormatter(lambda x, _: f"{x / 10000:.0f}万" if x else "0")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def pct_axis(ax, axis: str = "y", decimals: int = 0):
    """把坐标轴刻度改成百分比。"""
    fmt = ticker.FuncFormatter(lambda x, _: f"{x * 100:.{decimals}f}%")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def legend_handle(color, label, marker: str = "s"):
    """自定义图例元素（用于手工组合图例）。"""
    return Line2D([0], [0], color=color, marker=marker, linestyle="", markersize=8, label=label)
