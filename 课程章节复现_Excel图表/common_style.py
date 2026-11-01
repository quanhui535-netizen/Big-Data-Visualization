# -*- coding: utf-8 -*-
"""公共样式与工具：严格按 Excel 原图复现"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# 深色主题
BG = "#1A1E43"
TXT = "#FFFFFF"
TXT_DIM = "#D9D9D9"
GRID = "#FFFFFF"


def pt_to_in(pt):
    return pt / 72.0


def excel_manual_plot_axes(fig, x, y_top, w, h):
    """Excel manualLayout (y 从上往下) -> matplotlib axes [x,y,w,h] y 从下往上"""
    y = 1.0 - y_top - h
    return fig.add_axes([x, y, w, h])


def style_axes_dark(ax, y_ticks, y_step=None, y_labels=True,
                    x_labels=True, grid_alpha=0.22, grid_dash=(0, (5, 4)),
                    label_fs=9, tick_color=None):
    ax.set_facecolor(BG)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)
    if y_labels:
        ax.tick_params(axis="y", length=0, colors=tick_color or TXT_DIM,
                       labelsize=label_fs, pad=3)
    else:
        ax.yaxis.set_visible(False)
    if x_labels:
        ax.tick_params(axis="x", length=0, pad=4, colors=TXT)
        for lab in ax.get_xticklabels():
            lab.set_fontsize(label_fs)
            lab.set_color(TXT)
    else:
        ax.xaxis.set_visible(False)
    if y_ticks is not None:
        ax.set_yticks(y_ticks)
    if grid_alpha and y_ticks is not None:
        ax.yaxis.grid(True, linestyle=grid_dash, linewidth=0.9,
                      color=GRID, alpha=grid_alpha)
        ax.set_axisbelow(True)


def gradient_column(ax, xi, value, color_from, color_to, half_width,
                    bottom=0.0):
    cmap = LinearSegmentedColormap.from_list("g", [color_from, color_to])
    grad = cmap(np.linspace(0, 1, 256).reshape(-1, 1))
    ax.imshow(grad, extent=(xi - half_width, xi + half_width, bottom, value),
              aspect="auto", interpolation="bilinear", zorder=2, origin="upper")


def save_fig(fig, out_path, facecolor=BG):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, facecolor=facecolor)
    plt.close(fig)
    print("saved:", out_path)


def flatten_user_shapes(user_shapes):
    """userShapes -> list of strings (每框一段拼接文本)"""
    texts = []
    for box in user_shapes or []:
        paras = []
        for p in box.get("paras") or []:
            t = "".join(r.get("t") or "" for r in p.get("runs") or [])
            if t:
                paras.append(t)
        if paras:
            texts.append({
                "name": box.get("name"),
                "from": box.get("from"),
                "to": box.get("to"),
                "paragraphs": paras,
                "runs": [r for p in box.get("paras") or [] for r in p.get("runs") or []],
            })
    return texts
