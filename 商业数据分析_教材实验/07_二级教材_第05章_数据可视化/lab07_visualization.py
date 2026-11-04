# -*- coding: utf-8 -*-
"""
实验 07 · 数据可视化：把 matplotlib 的零散示例变成一套"能讲故事"的图
====================================================================
教材：《CDA 二级认证教材：量化策略分析》第 5 章 数据可视化（含"描述性统计分析与绘图"）
原始素材：``第5章 python数据可视化.ipynb`` + ``第5章 描述性统计分析与绘图.ipynb``
        ``2017股价.xlsx``（15 个交易日 × 8 列，上证指数日线，按日期倒序）
        ``sndHsPr.csv``（16210 条北京二手房挂牌记录 × 8 列）
迁移方向：notebook 里"一个图形一个 cell、用随机数当数据"  →  真实业务数据 + 统一风格 + 组合图/子图

两个 notebook 的问题是一样的：**图形是孤立的**。
折线图用 ``range(15)`` 当横轴、柱状图用随机投票数、直方图用 ``np.random.normal``——
每个 cell 都在教"这个函数怎么调"，但没有一张图回答了业务问题。

本脚本按"**图要回答什么问题**"重新组织 6 张图：

    1. 股价这 15 天怎么走的？          → 四价折线（趋势）
    2. 量价是否配合？                  → 收盘价 + 成交量双轴组合图
    3. 房价是什么分布？贵不贵？        → 直方图 + 均值/中位数线
    4. 哪个区域最贵？                  → 分区域均价条形图（含中位数、样本量）
    5. 面积越大越贵吗？地铁/学区值多少？→ 面积-单价散点（分组建模线）
    6. 区域差异和变量相关性有多强？    → 区域箱线图 + 相关性热力图

运行：``python lab07_visualization.py``（在实验目录下执行）
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 让脚本能从仓库根的 common/ 导入统一样式
LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR.parent))

from common.style import (  # noqa: E402
    PALETTE, BLUE, BLUE2, ORANGE, GRAY, GREEN, RED, POS, NEG,
    apply_style, new_fig, save_fig, save_csv,
    bar_labels, fmt_wan, money_axis, pct_axis,
)

DATA = LAB_DIR / "data"
OUT = LAB_DIR / "outputs"

# 原始数据是英文类别，画图必须换成中文，否则图标题和坐标轴中英混杂
DIST_CN = {
    "chaoyang": "朝阳", "haidian": "海淀", "fengtai": "丰台",
    "dongcheng": "东城", "xicheng": "西城", "shijingshan": "石景山",
}
FLOOR_CN = {"low": "低楼层", "middle": "中楼层", "high": "高楼层"}

# A 股习惯：红涨绿跌（与仓库里 POS=绿 / NEG=红 的通用语义相反，图例里会写明）
UP_COLOR, DOWN_COLOR = RED, GREEN


# ---------------------------------------------------------------------------
# 0. 读数据 —— 对应两个 notebook 的第一个 cell
# ---------------------------------------------------------------------------
def load_stock() -> pd.DataFrame:
    """读入 2017 年上证指数日线，并做两件教材没做的事。

    对应教材：cell 1 ``df = pd.read_excel("2017股价.xlsx")``；cell 3 直接用
    ``range(15)`` 当横轴、``df.日期`` 当刻度标签。

    教材的问题：
      * 文件是**按日期倒序**的（第一行 2017-09-14，最后一行 2017-08-25），
        直接画折线，"时间"是从右往左流的，涨跌方向会被看反；
      * 用整数 ``range(15)`` 当横轴，横轴间距与真实交易日无关，遇到休市
        （如 8/26—8/27 周末、9/2—9/3 周末）会被画成等距，产生"连续交易"的错觉。

    这里改成：日期转 ``datetime`` → 升序排序 → 用真实日期当横轴刻度。
    """
    df = pd.read_excel(DATA / "2017股价.xlsx")
    df["日期"] = pd.to_datetime(df["日期"])
    df = df.sort_values("日期").reset_index(drop=True)
    df["日期标签"] = df["日期"].dt.strftime("%m-%d")

    print("== 0. 读入股价数据 ==")
    print(f"  {df.shape[0]} 个交易日，{df['日期'].min():%Y-%m-%d} ~ "
          f"{df['日期'].max():%Y-%m-%d}（已由倒序改为升序）")
    print(f"  收盘价 {df['收盘价'].min():.2f} ~ {df['收盘价'].max():.2f}，"
          f"区间振幅 {df['收盘价'].max() - df['收盘价'].min():.2f} 点"
          f"（{(df['收盘价'].max() / df['收盘价'].min() - 1):.2%}）")
    print(f"  成交量 {df['成交量'].min() / 1e8:.2f} ~ {df['成交量'].max() / 1e8:.2f} 亿手")
    return df


def load_housing() -> pd.DataFrame:
    """读入北京二手房数据，并把英文类别映射成中文（教材没有做这一步）。

    对应教材（描述性统计 notebook）：cell 1 ``data = pd.read_csv('sndHsPr.csv')``，
    之后直接 ``data.price.agg(...)``、``data.price.hist(bins=20)``。

    教材的数据是英文类别（``chaoyang`` / ``middle`` / ``1``），画出来的图
    中英混杂、读者要猜"1 是有地铁还是没有"。这里统一加两列中文标签，
    原始列保留不动（分析逻辑仍用原列，只有画图用中文列）。
    """
    df = pd.read_csv(DATA / "sndHsPr.csv")
    df["区域"] = df["dist"].map(DIST_CN)
    df["楼层"] = df["floor"].map(FLOOR_CN)
    df["地铁"] = df["subway"].map({1: "地铁房", 0: "非地铁房"})
    df["学区"] = df["school"].map({1: "学区房", 0: "非学区房"})

    print("\n== 0. 读入二手房数据 ==")
    print(f"  {df.shape[0]:,} 条挂牌记录 × {df.shape[1]} 列，"
          f"{df['区域'].nunique()} 个区域，无缺失值")
    print("  区域分布：" + "、".join(
        f"{k} {v}" for k, v in df["区域"].value_counts().items()))
    return df


# ---------------------------------------------------------------------------
# 1. 折线图：四价走势 —— 对应教材 cell 3
# ---------------------------------------------------------------------------
def plot_stock_lines(df: pd.DataFrame) -> None:
    """四价折线图：收盘/开盘/最高/最低。

    对应教材：cell 3
        ``plt.plot(range(15), df.loc[:,"收盘价"], '-*')`` 等 4 条线 +
        ``plt.xticks(range(15), df.日期, rotation=30)`` + ``plt.legend([...])``

    改进三处：
      1. 横轴用真实日期标签（不再用 ``range(15)`` 制造的等距假象）；
      2. 用 ``fill_between(最低, 最高)`` 画出当日振幅带——教材 4 条线颜色相近，
         高低点根本看不出差别，加了振幅带才读得出"哪天波动大"；
      3. 标出区间最高/最低收盘价，直接给出结论，而不是让读者自己找。
    """
    d = df
    fig, ax = new_fig(9.6, 4.8)
    ax.fill_between(d["日期标签"], d["最低价"], d["最高价"],
                    color=BLUE2, alpha=0.18, zorder=1, label="当日振幅（最低—最高）")
    ax.plot(d["日期标签"], d["收盘价"], color=BLUE, marker="*", markersize=10,
            linewidth=2.0, zorder=5, label="收盘价")
    ax.plot(d["日期标签"], d["开盘价"], color=ORANGE, marker="o", markersize=4.5,
            linewidth=1.3, zorder=4, label="开盘价")
    ax.plot(d["日期标签"], d["最高价"], color=GRAY, linestyle="--", linewidth=1.0,
            zorder=3, label="最高价")
    ax.plot(d["日期标签"], d["最低价"], color=GRAY, linestyle=":", linewidth=1.0,
            zorder=3, label="最低价")

    hi, lo = d["收盘价"].idxmax(), d["收盘价"].idxmin()
    for idx, color, xytext, ha in [(hi, RED, (0, 14), "center"),
                                   (lo, GREEN, (10, -26), "left")]:
        ax.annotate(f"{d.loc[idx, '收盘价']:.2f}（{d.loc[idx, '日期标签']}）",
                    xy=(d.loc[idx, "日期标签"], d.loc[idx, "收盘价"]),
                    xytext=xytext, textcoords="offset points",
                    ha=ha, fontsize=8.5, color=color,
                    arrowprops={"arrowstyle": "-", "color": color, "lw": 0.8})

    ax.set_title("上证指数 15 个交易日四价走势（2017-08-25 — 2017-09-14）", pad=12)
    ax.set_xlabel("交易日")
    ax.set_ylabel("指数点位")
    ax.legend(loc="lower right", ncol=2)
    ax.margins(x=0.02)
    save_fig(fig, OUT, "fig01_股价四价走势")


# ---------------------------------------------------------------------------
# 2. 双轴组合图：收盘价 + 成交量 —— 教材没有，但这是最常用的行情图
# ---------------------------------------------------------------------------
def plot_price_volume(df: pd.DataFrame) -> None:
    """收盘价（折线）+ 成交量（柱状）双轴组合图。

    对应教材：cell 3 只画了价格，没有量。但"量价配合"是行情分析的第一课，
    而双坐标轴（``twinx``）恰好是教材第 5 章想讲的组合图技巧。

    约定：A 股习惯**红涨绿跌**，所以成交量柱按当日涨跌方向上色，
    和仓库里 POS/NEG 的通用语义（绿正红负）相反，图例里明确标注。
    """
    d = df
    fig, ax = new_fig(9.6, 4.8)
    colors = [UP_COLOR if v >= 0 else DOWN_COLOR for v in d["涨跌幅"]]
    ax.bar(d["日期标签"], d["成交量"] / 1e8, color=colors, alpha=0.55,
           width=0.6, zorder=3, label="成交量（红涨绿跌）")
    ax.set_xlabel("交易日")
    ax.set_ylabel("成交量（亿手）")
    ax.set_ylim(0, d["成交量"].max() / 1e8 * 1.35)

    ax2 = ax.twinx()
    ax2.plot(d["日期标签"], d["收盘价"], color=BLUE, marker="o", markersize=5,
             linewidth=2.2, zorder=6, label="收盘价")
    ax2.set_ylabel("收盘价（点）", color=BLUE)
    ax2.tick_params(axis="y", colors=BLUE)
    ax2.set_ylim(d["收盘价"].min() * 0.995, d["收盘价"].max() * 1.006)
    ax2.grid(False)

    top = d["成交量"].idxmax()
    ax.annotate(f"最大成交量 {d.loc[top, '成交量'] / 1e8:.2f} 亿手",
                xy=(d.loc[top, "日期标签"], d.loc[top, "成交量"] / 1e8),
                xytext=(d.loc[top, "日期标签"], d.loc[top, "成交量"] / 1e8 * 1.12),
                ha="center", fontsize=8.5, color="#555555",
                arrowprops={"arrowstyle": "->", "color": "#555555", "lw": 0.9})

    handles = [
        plt.Line2D([], [], color=BLUE, marker="o", linewidth=2.2, label="收盘价（右轴）"),
        plt.Rectangle((0, 0), 1, 1, color=UP_COLOR, alpha=0.55, label="上涨日成交量"),
        plt.Rectangle((0, 0), 1, 1, color=DOWN_COLOR, alpha=0.55, label="下跌日成交量"),
    ]
    ax.legend(handles=handles, loc="upper left", ncol=3)
    ax.set_title("量价配合：成交量放大时指数怎么走", pad=12)
    save_fig(fig, OUT, "fig02_收盘价与成交量双轴图")

    up_days = int((d["涨跌幅"] > 0).sum())
    print("\n== 2. 量价关系 ==")
    print(f"  15 个交易日里 {up_days} 天上涨、{15 - up_days} 天下跌；"
          f"成交量与涨跌幅的相关系数 "
          f"{d['成交量'].corr(d['涨跌幅']):.3f}（量能并不跟随涨跌方向）")


# ---------------------------------------------------------------------------
# 3. 直方图：房价分布 —— 对应教材描述性统计 notebook 的 cell 2—14
# ---------------------------------------------------------------------------
def describe_price(df: pd.DataFrame) -> pd.DataFrame:
    """房价的描述性统计 + 分布直方图。

    对应教材：
        cell 2  ``data.price.agg(['mean','median','std'])``
        cell 3  ``data.price.quantile([0.25,0.5,0.75])``
        cell 4  ``data.price.hist(bins=20)``
        cell 6—8 ``max-min``（极差）、``var()``（方差）、``std()``（标准差）
        cell 12—13 ``normal.skew()`` / ``normal.kurtosis()``（教材用随机数演示）

    教材把统计量和图分开在两个 cell：算完数字看不到形状，画完图不知道数字。
    这里合成一步：**先算指标 → 再画图 → 把关键指标直接标在图上**，
    读者一眼就能对上"均值 6.12 万、中位数 5.75 万、右偏 0.68"。
    """
    price, area = df["price"], df["AREA"]
    stats = {
        "样本数": (len(price), len(area), len(df)),
        "均值": (price.mean(), area.mean(), df["roomnum"].mean()),
        "中位数": (price.median(), area.median(), df["roomnum"].median()),
        "标准差": (price.std(), area.std(), df["roomnum"].std()),
        "方差": (price.var(), area.var(), df["roomnum"].var()),
        "最小值": (price.min(), area.min(), df["roomnum"].min()),
        "最大值": (price.max(), area.max(), df["roomnum"].max()),
        "极差": (price.max() - price.min(), area.max() - area.min(),
                 df["roomnum"].max() - df["roomnum"].min()),
        "P25": (price.quantile(0.25), area.quantile(0.25), df["roomnum"].quantile(0.25)),
        "P75": (price.quantile(0.75), area.quantile(0.75), df["roomnum"].quantile(0.75)),
        "偏度": (price.skew(), area.skew(), df["roomnum"].skew()),
        "峰度": (price.kurtosis(), area.kurtosis(), df["roomnum"].kurtosis()),
    }
    table = pd.DataFrame(stats, index=["单价（元/㎡）", "面积（㎡）", "室数"]).T
    table.index.name = "指标"
    table = table.round(2).reset_index()   # 指标名要落成列，否则 CSV 丢标签

    # 三种相关系数（教材 ch5_desc cell 14—16 分别算了 pearson/spearman/kendall）
    corr = {m: df[["AREA", "price"]].corr(method=m).iloc[0, 1]
            for m in ["pearson", "spearman", "kendall"]}

    fig, ax = new_fig(9.4, 4.9)
    n_bins = 45
    ax.hist(price, bins=n_bins, color=BLUE2, alpha=0.85, edgecolor="white",
            linewidth=0.4, zorder=3)
    ax.axvline(price.mean(), color=ORANGE, linestyle="--", linewidth=2.2,
               label=f"均值 {price.mean() / 1e4:.2f} 万")
    ax.axvline(price.median(), color=GREEN, linestyle=":", linewidth=2.2,
               label=f"中位数 {price.median() / 1e4:.2f} 万")
    ax.axvspan(price.quantile(0.25), price.quantile(0.75), color=ORANGE, alpha=0.10,
               zorder=1, label="中间 50%（P25—P75）")
    ax.set_title(f"北京二手房单价分布（{len(price):,} 条挂牌，偏度 {price.skew():.2f}）",
                 pad=12)
    ax.set_xlabel("单价（元/㎡）")
    ax.set_ylabel("挂牌套数")
    money_axis(ax, axis="x")
    ax.legend(loc="upper right")
    ax.text(0.985, 0.60,
            f"均值 {price.mean():,.0f} 元\n中位数 {price.median():,.0f} 元\n"
            f"标准差 {price.std():,.0f} 元\n极差 {price.max() - price.min():,.0f} 元",
            transform=ax.transAxes, ha="right", va="top", fontsize=9,
            bbox={"boxstyle": "round,pad=0.45", "facecolor": "#F7F9FB",
                  "edgecolor": "#DCE1E6"})
    save_fig(fig, OUT, "fig03_房价分布直方图")

    print("\n== 3. 房价分布 ==")
    print(f"  均值 {price.mean():,.0f} 元/㎡，中位数 {price.median():,.0f} 元/㎡，"
          f"标准差 {price.std():,.0f}，极差 {price.max() - price.min():,.0f}")
    print(f"  偏度 {price.skew():.2f}、峰度 {price.kurtosis():.2f} → "
          f"{'右偏（少数高价拉高均值）' if price.skew() > 0 else '左偏'}")
    print("  面积与单价的相关性：" + "、".join(
        f"{m} {v:+.3f}" for m, v in corr.items()) + "（几乎无关，见 fig05）")
    return table


# ---------------------------------------------------------------------------
# 4. 条形图：分区域均价 —— 对应教材 cell 8、9（bar / barh）
# ---------------------------------------------------------------------------
def plot_dist_avg(df: pd.DataFrame) -> pd.DataFrame:
    """分区域均价条形图，同时标出中位数与样本量。

    对应教材：cell 8 ``plt.bar(df.方案, df.投票人数, width=0.6)``
             cell 9 ``plt.barh(...)``（条形图，类别多时更合适）

    教材用的是 5 个方案的随机投票数，排序、样本量、参考线都没有。换成真实数据后，
    这三件事恰好是"区域对比"必须交代的：**排序**决定读者先看谁，**样本量**决定
    结论可不可信（石景山只有 1947 套，样本最少），**全市均价线**给出比较基准。
    """
    g = (df.groupby("区域")["price"]
         .agg(样本数="size", 均价="mean", 中位数="median", 标准差="std")
         .sort_values("均价"))
    overall = df["price"].mean()

    fig, ax = new_fig(9.2, 4.8)
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(g))]
    ax.barh(g.index, g["均价"] / 1e4, color=colors, height=0.62, zorder=3,
            alpha=0.9)
    ax.scatter(g["中位数"] / 1e4, range(len(g)), marker="D", s=40,
               color="white", edgecolor="#222222", linewidth=1.1, zorder=6,
               label="中位数")
    ax.axvline(overall / 1e4, color=RED, linestyle="--", linewidth=1.4,
               label=f"全市均价 {overall / 1e4:.2f} 万")
    for y, (name, row) in enumerate(g.iterrows()):
        # 数值标在「均价」和「中位数」两者更靠外的那个右侧，避免和菱形标记打架
        x_text = max(row["均价"], row["中位数"]) / 1e4 + 0.16
        ax.annotate(f"{row['均价'] / 1e4:.2f} 万", xy=(x_text, y), va="center",
                    ha="left", fontsize=9.5, color="#333333")
        ax.annotate(f"n={int(row['样本数']):,}", xy=(0.35, y), va="center",
                    fontsize=8.5, color="white")
    ax.set_xlim(0, g["均价"].max() / 1e4 * 1.22)
    ax.set_xlabel("挂牌均价（万元/㎡）")
    ax.set_ylabel("")
    ax.set_title(f"各区域二手房均价：{g.index[-1]}最高，是{g.index[0]}的 "
                 f"{g['均价'].iloc[-1] / g['均价'].iloc[0]:.1f} 倍", pad=12)
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    save_fig(fig, OUT, "fig04_各区域均价条形图")

    table = g.reset_index().round(2)
    table["高于全市均价"] = (table["均价"] / overall - 1).round(4)

    print("\n== 4. 区域均价 ==")
    print(f"  全市均价 {overall:,.0f} 元/㎡")
    for _, r in table.sort_values("均价", ascending=False).iterrows():
        print(f"  {r['区域']:<4} {r['均价']:>7,.0f} 元/㎡（中位数 {r['中位数']:>7,.0f}，"
              f"{int(r['样本数']):>4} 套，较全市 {r['高于全市均价']:+.1%}）")
    return table


# ---------------------------------------------------------------------------
# 5. 散点图：面积 vs 单价 —— 对应教材 cell 14、15
# ---------------------------------------------------------------------------
def plot_area_price(df: pd.DataFrame) -> None:
    """面积-单价散点，按"是否地铁房 / 是否学区房"分组上色并拟合趋势线。

    对应教材：cell 14 ``df = pd.DataFrame({"产量":..., "降水量":...})``；
             cell 15 ``plt.scatter(df.降水量, df.产量)``

    教材的散点只有 7 个点、一条"看着像正相关"的云。真实数据 16210 个点，
    直接 ``scatter`` 会糊成一团黑，必须：
      * 调小点尺寸、加透明度（``s=6, alpha=0.15``），让密度而不是点数说话；
      * 截断极端面积（99 分位以上只占 1%，会把画布拉扁）；
      * 分组上色 + 分组拟合线，才能回答"地铁/学区到底值多少钱"。
    """
    upper = df["AREA"].quantile(0.99)
    sub = df[df["AREA"] <= upper].copy()

    fig, axes = new_fig(11.4, 4.7, ncols=2)
    group_orders = {
        "地铁": ["非地铁房", "地铁房"],
        "学区": ["非学区房", "学区房"],
    }
    for ax, col, title in [
        (axes[0], "地铁", "按是否地铁房分组"),
        (axes[1], "学区", "按是否学区房分组"),
    ]:
        handles = []
        for k, name in enumerate(group_orders[col]):
            g = sub[sub[col] == name]
            color = [GRAY, BLUE][k]
            ax.scatter(g["AREA"], g["price"], s=6, alpha=0.16, color=color,
                       zorder=3)
            handles.append(plt.Line2D([], [], marker="o", linestyle="", markersize=8,
                                      color=color, alpha=0.75, label=name))
            # 拟合线用面积 30—150㎡ 的区间，避免被两头极端值带偏
            seg = g[(g["AREA"] >= 30) & (g["AREA"] <= 150)]
            slope, intercept = np.polyfit(seg["AREA"], seg["price"], 1)
            xs = np.array([30, 150])
            ax.plot(xs, slope * xs + intercept, color=color, linewidth=2.4, zorder=5)
            r = g["AREA"].corr(g["price"])
            ax.annotate(f"{name}：n={len(g):,}，均价 {g['price'].mean() / 1e4:.2f} 万/㎡，"
                        f"r = {r:+.2f}",
                        xy=(0.03, 0.96 - k * 0.085), xycoords="axes fraction",
                        fontsize=8.5, color=color, va="top",
                        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white",
                              "edgecolor": "none", "alpha": 0.72})
        ax.set_title(title, pad=10)
        ax.set_xlabel(f"建筑面积（㎡，截断至 P99 = {upper:.0f}）")
        ax.set_ylabel("单价（元/㎡）" if col == "地铁" else "")
        ax.set_xlim(20, upper * 0.95)
        money_axis(ax)
        ax.legend(handles=handles, loc="lower right", frameon=True,
                  facecolor="white", framealpha=0.85, edgecolor="#DCE1E6")

    fig.suptitle("面积与单价基本无关，但分组后仍能看出学区的分化", y=1.03,
                 fontsize=13, fontweight="bold")
    save_fig(fig, OUT, "fig05_面积单价散点")

    print("\n== 5. 面积与单价 ==")
    print(f"  AREA 与 price 的 Pearson 相关 {df['AREA'].corr(df['price']):+.3f}"
          f"（面积解释不了单价，真正拉开价差的是位置与配套）")
    for col, yes, no in [("地铁", "地铁房", "非地铁房"), ("学区", "学区房", "非学区房")]:
        g = df.groupby(col)["price"].mean()
        gap = g[yes] / g[no] - 1
        print(f"  {col}：{no} 均价 {g[no]:,.0f} → {yes} {g[yes]:,.0f}，溢价 {gap:+.1%}")


# ---------------------------------------------------------------------------
# 6. 子图：区域箱线图 + 相关性热力图
# ---------------------------------------------------------------------------
def plot_box_and_corr(df: pd.DataFrame) -> None:
    """左：分区域箱线图（看分布形态，不只均值）；右：变量相关性热力图。

    对应教材：
        cell 17—18 ``plt.boxplot([df.语文, df.英语, df.数学], labels=[...])``
                    —— 教材用 3 个随机科目演示箱线图
        cell 29—30 ``sns.heatmap(df0)`` —— 用 7×7 均匀随机数演示热力图

    箱线图的价值在于**同一张图里同时看到中位数、四分位和异常值**：
    西城的箱体整体上移且更长（内部价差大），石景山的箱体又低又窄（同质化）。
    热力图则回答"哪些变量该进模型"：面积与室/厅强相关（0.72/0.64），
    但与单价几乎无关（-0.07），说明**共线性风险在面积与户型之间，而不在价格**。
    """
    order = df.groupby("区域")["price"].median().sort_values().index.tolist()
    data = [df.loc[df["区域"] == k, "price"].values / 1e4 for k in order]

    fig, axes = new_fig(11.6, 4.9, ncols=2, gridspec_kw={"width_ratios": [1.15, 1]})

    ax = axes[0]
    bp = ax.boxplot(data, tick_labels=order, widths=0.55, patch_artist=True,
                    showfliers=False,
                    medianprops={"color": "#333333", "linewidth": 1.6})
    for patch, color in zip(bp["boxes"], PALETTE):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
        patch.set_edgecolor("#555555")
    ax.set_title("各区域单价箱线图（按中位数升序）", pad=10)
    ax.set_ylabel("单价（万元/㎡）")
    ax.set_xlabel("")
    ax.axhline(df["price"].median() / 1e4, color=RED, linestyle="--", linewidth=1.1)
    ax.annotate(f"全市中位数 {df['price'].median() / 1e4:.2f} 万",
                xy=(0.02, df["price"].median() / 1e4), xytext=(0, 5),
                textcoords="offset points", fontsize=8.5, color=RED)

    ax = axes[1]
    cols = ["AREA", "roomnum", "halls", "price"]
    names = ["面积", "室数", "厅数", "单价"]
    corr = df[cols].corr()
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(names)), names)
    ax.set_yticks(range(len(names)), names)
    ax.grid(False)
    for i in range(len(names)):
        for j in range(len(names)):
            v = corr.values[i, j]
            ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=9.5,
                    color="white" if abs(v) > 0.6 else "#333333")
    ax.set_title("数值变量相关性（Pearson）", pad=10)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03, label="相关系数")

    fig.suptitle("区域差异看箱体，变量关系看热力图", y=1.03,
                 fontsize=13, fontweight="bold")
    save_fig(fig, OUT, "fig06_区域箱线图与相关性热力图")

    print("\n== 6. 分布与相关性 ==")
    q = df.groupby("区域")["price"].agg(
        中位数="median", P25=lambda s: s.quantile(0.25), P75=lambda s: s.quantile(0.75))
    for name, r in q.sort_values("中位数", ascending=False).iterrows():
        print(f"  {name}：中位数 {r['中位数'] / 1e4:.2f} 万，"
              f"四分位距 {(r['P75'] - r['P25']) / 1e4:.2f} 万")
    print(f"  面积-室数相关 {corr.loc['AREA', 'roomnum']:+.2f}、"
          f"面积-厅数 {corr.loc['AREA', 'halls']:+.2f}、"
          f"面积-单价 {corr.loc['AREA', 'price']:+.2f}")


def main() -> None:
    apply_style()

    stock = load_stock()
    plot_stock_lines(stock)
    plot_price_volume(stock)

    house = load_housing()
    desc = describe_price(house)
    dist_stat = plot_dist_avg(house)
    plot_area_price(house)
    plot_box_and_corr(house)

    save_csv(desc, OUT, "table01_房价描述统计")
    save_csv(dist_stat, OUT, "table02_分区域房价汇总")

    top, bottom = dist_stat.iloc[-1], dist_stat.iloc[0]
    metro = house.groupby("地铁")["price"].mean()
    school = house.groupby("学区")["price"].mean()
    metro_gap = metro["地铁房"] / metro["非地铁房"] - 1
    school_gap = school["学区房"] / school["非学区房"] - 1
    print("\n" + "=" * 68)
    print("实验结论（可直接写进报告）")
    print("=" * 68)
    print(f"1. 房价右偏（偏度 {house['price'].skew():.2f}）：均值 "
          f"{house['price'].mean():,.0f} 元/㎡ 比中位数高 "
          f"{house['price'].mean() / house['price'].median() - 1:.1%}，"
          f"报告里应同时给两个数以说明'被少数豪宅拉高'。")
    print(f"2. 区域是第一价差来源：{top['区域']} {top['均价'] / 1e4:.2f} 万/㎡，"
          f"{bottom['区域']} {bottom['均价'] / 1e4:.2f} 万/㎡，相差 "
          f"{top['均价'] / bottom['均价']:.1f} 倍；全市均价 "
          f"{house['price'].mean() / 1e4:.2f} 万。")
    print(f"3. 配套溢价：地铁房比非地铁房贵 {metro_gap:.1%}，"
          f"学区房比非学区房贵 {school_gap:.1%}，学区的解释力更强。")
    print(f"4. 面积与单价几乎不相关（r = {house['AREA'].corr(house['price']):+.2f}），"
          f"说明'大房子便宜'是单价口径下的错觉，总价仍然随面积线性上升。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
