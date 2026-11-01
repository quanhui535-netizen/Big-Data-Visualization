"""公共配置与绘图样式：路径、配色、中文字体、保存工具。

所有脚本共享此模块，保证 23 张图在配色/字体/字号/边距上完全统一。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---------------------------------------------------------------- 路径
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_CLEAN = ROOT / "data" / "clean"
FIG_DIR = ROOT / "outputs" / "figures"
TBL_DIR = ROOT / "outputs" / "tables"
DOCS = ROOT / "docs"
for _d in (DATA_RAW, DATA_CLEAN, FIG_DIR, TBL_DIR, DOCS):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 配色（Office 主题色，贴近 Excel 原图）
C = {
    "blue": "#4472C4",
    "darkblue": "#264478",
    "lightblue": "#8FAADC",
    "paleblue": "#B4C7E7",
    "orange": "#ED7D31",
    "lightorange": "#F4B183",
    "gray": "#A5A5A5",
    "lightgray": "#D9D9D9",
    "gold": "#FFC000",
    "green": "#70AD47",
    "red": "#C00000",
    "teal": "#2F9E9E",
    "purple": "#7030A0",
    "brown": "#843C0C",
    "navy": "#1F3864",
    "bg": "#FFFFFF",
    "grid": "#E6E6E6",
    "text": "#262626",
    "sub": "#7F7F7F",
}
CYCLE = [C["blue"], C["orange"], C["gray"], C["gold"], C["lightblue"], C["green"], C["purple"], C["red"]]

# 8 个 RFM 客户的固定配色（全篇一致）
SEGMENT_COLORS = {
    "重要价值客户": "#264478",
    "重要发展客户": "#4472C4",
    "重要保持客户": "#8FAADC",
    "重要挽留客户": "#C00000",
    "一般价值客户": "#70AD47",
    "一般发展客户": "#A9D18E",
    "一般保持客户": "#FFC000",
    "一般挽留客户": "#A5A5A5",
}

FONT_CANDIDATES = ["Microsoft YaHei", "SimHei", "Noto Sans SC", "Source Han Sans SC", "SimSun"]


def _pick_font() -> str:
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in FONT_CANDIDATES:
        if name in installed:
            return name
    return "SimHei"


def setup_style() -> None:
    """统一图表风格：白底、无边框、浅灰网格、中文字体。"""
    font = _pick_font()
    plt.rcParams.update({
        "font.sans-serif": [font, "SimHei", "Microsoft YaHei"],
        "font.family": "sans-serif",
        "axes.unicode_minus": False,
        "figure.facecolor": C["bg"],
        "axes.facecolor": C["bg"],
        "savefig.facecolor": C["bg"],
        "axes.edgecolor": "#BFBFBF",
        "axes.linewidth": 0.8,
        "axes.labelcolor": C["text"],
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "axes.titlepad": 12,
        "axes.labelsize": 10.5,
        "axes.grid": True,
        "grid.color": C["grid"],
        "grid.linewidth": 0.7,
        "xtick.color": C["text"],
        "ytick.color": C["text"],
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.frameon": False,
        "legend.fontsize": 9.5,
        "lines.linewidth": 2.0,
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.25,
    })


def polish(ax, *, grid_axis: str = "y", hide=(  "top", "right")) -> None:
    """去掉多余边框，只保留需要的网格。"""
    for side in hide:
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color=C["grid"], linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)


def title_block(ax, title: str, subtitle: str = "", *, x: float = 0.0, y: float = 1.02):
    """Excel 风格标题：左上角大标题 + 灰色副标题/口径说明。"""
    ax.set_title(title, loc="left", x=x, y=y, fontsize=15, fontweight="bold",
                 color=C["text"], pad=26 if subtitle else 10)
    if subtitle:
        ax.annotate(subtitle, xy=(x, 1.0), xycoords="axes fraction", xytext=(0, 8),
                    textcoords="offset points", fontsize=9.2, color=C["sub"], ha="left", va="bottom")


def source_note(fig, text: str = "数据来源：UCI Online Retail Dataset（2010-12 ~ 2011-12）｜Python 绘制") -> None:
    fig.text(0.005, 0.005, text, fontsize=8, color=C["sub"], ha="left", va="bottom")


def save(fig, name: str, *, note: bool = True) -> Path:
    """保存图表：统一命名 figXX_描述.png，200 dpi。"""
    if note:
        source_note(fig)
    path = FIG_DIR / name
    fig.savefig(path)
    plt.close(fig)
    print(f"[figure] {path.name}")
    return path


def save_table(df, name: str, *, index: bool = False) -> Path:
    path = TBL_DIR / name
    df.to_csv(path, index=index, encoding="utf-8-sig")
    print(f"[table ] {path.name}  shape={df.shape}")
    return path


def _json_clean(o):
    """把 NaN/Inf 转成 None，保证输出是合法 JSON。"""
    import math
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    if isinstance(o, dict):
        return {k: _json_clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json_clean(v) for v in o]
    return o


def dump_json(obj, name: str, folder: Path | None = None) -> Path:
    folder = folder or TBL_DIR
    path = folder / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_json_clean(obj), f, ensure_ascii=False, indent=2, default=str)
    return path


def fmt_wan(x, _=None) -> str:
    """把金额格式化为「万 / 亿」。"""
    x = float(x)
    if abs(x) >= 1e8:
        return f"{x/1e8:.1f}亿"
    if abs(x) >= 1e4:
        return f"{x/1e4:.0f}万"
    return f"{x:.0f}"


def gradient_bar(ax, xs, heights, colors=("#8FAADC", "#264478"), width=0.62, zorder=3, **kw):
    """Excel「渐变柱形图」：柱体自上而下线性渐变。"""
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.patches import Rectangle
    import numpy as np

    cmap = LinearSegmentedColormap.from_list("grad", list(colors))
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    for x, h in zip(xs, heights):
        if h == 0:
            continue
        ax.imshow(grad, extent=(x - width / 2, x + width / 2, 0, h), aspect="auto",
                  cmap=cmap, origin="lower", zorder=zorder, **kw)
        ax.add_patch(Rectangle((x - width / 2, 0), width, h, fill=False, lw=0, zorder=zorder + 0.1))


def rounded_bar(ax, xs, heights, color=C["blue"], width=0.6, radius_frac=0.35, zorder=3, alpha=1.0):
    """Excel「渐变圆角柱形图」：顶部圆角矩形。"""
    from matplotlib.patches import FancyBboxPatch
    for x, h in zip(xs, heights):
        if h <= 0:
            continue
        r = min(width * radius_frac, h * 0.5)
        box = FancyBboxPatch((x - width / 2, 0), width, h,
                             boxstyle=f"round,pad=0,rounding_size={r}",
                             linewidth=0, facecolor=color, alpha=alpha, zorder=zorder,
                             mutation_aspect=1)
        ax.add_patch(box)
