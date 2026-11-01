"""04_visuals.py —— 全部图表（纯 Python 生成，未使用任何 BI 软件）

第一部分  模板复现 15 种（对照《Excel数据可视化——从图表到数据大屏》30 个模板）
          fig01 渐变柱形图          fig02 带平均线柱形图      fig03 渐变圆角柱形图
          fig04 层叠柱形图(100%)    fig05 蝴蝶图              fig06 数值百分比条形图
          fig07 甘特图              fig08 平滑折线图          fig09 菱形走势图
          fig10 对比折线图          fig11 单值圆环图          fig12 南丁格尔玫瑰图
          fig13 玉玦图              fig14 水球图              fig15 柱形折线图

第二部分  业务模型图 8 张（与第 4 章 6 个模型一一对应）
          fig16 RFM 气泡散点图      fig17 八分群价值对比图    fig18 同期群留存热力图
          fig19 帕累托图            fig20 波士顿矩阵          fig21 关联规则气泡图
          fig22 SARIMA 预测图       fig23 ABC 分层对比图
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge, Rectangle, FancyBboxPatch
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (C, CYCLE, SEGMENT_COLORS, DATA_CLEAN, TBL_DIR,  # noqa: E402
                    setup_style, polish, title_block, save, fmt_wan, gradient_bar, rounded_bar, FIG_DIR)

FIG_INDEX: list[tuple[str, str, str]] = []  # (文件名, 标题, 对应模型/模板)


def load() -> dict:
    d = {}
    for name in ["monthly_trend", "weekly_trend", "daily_trend", "weekday_trend", "hourly_trend",
                 "country_summary", "sku_top100", "rfm_segment_summary", "cohort_retention",
                 "association_rules", "sarima_forecast", "sarima_backtest", "pareto_customers",
                 "abc_summary", "bdc_matrix", "rfm_customer_level"]:
        p = TBL_DIR / f"{name}.csv"
        if p.exists():
            d[name] = pd.read_csv(p)
    d["tx"] = pd.read_parquet(DATA_CLEAN / "transactions.parquet")
    d["customers"] = pd.read_csv(DATA_CLEAN / "customers.csv")
    # 列名归一化，避免大小写/索引列名差异
    if "daily_trend" in d:
        d["daily_trend"] = d["daily_trend"].rename(columns={"Date": "date"})
    if "weekly_trend" in d:
        d["weekly_trend"] = d["weekly_trend"].rename(columns={"Week": "week"})
    if "cohort_retention" in d:
        d["cohort_retention"] = d["cohort_retention"].rename(columns={d["cohort_retention"].columns[0]: "首购月"})
    return d


D = load()
SEG_ORDER = ["重要价值客户", "重要发展客户", "重要保持客户", "重要挽留客户",
             "一般价值客户", "一般发展客户", "一般保持客户", "一般挽留客户"]


def reg(fname: str, title: str, mapping: str) -> None:
    FIG_INDEX.append((fname, title, mapping))


# =====================================================================
# 第一部分：Excel 模板复现
# =====================================================================
def fig01_gradient_bar():
    """渐变柱形图：月度销售额，柱体自上而下渐变 + 数据标签。"""
    from matplotlib.ticker import FuncFormatter
    m = D["monthly_trend"]
    fig, ax = plt.subplots(figsize=(10.2, 5.4))
    xs = np.arange(len(m))
    gradient_bar(ax, xs, m["销售额"].values, colors=("#9DC3E6", "#2F5597"), width=0.66)
    for x, v in zip(xs, m["销售额"].values):
        ax.text(x, v * 1.015, f"{v/1e4:.1f}万", ha="center", va="bottom", fontsize=8.6, color=C["darkblue"])
    ax.set_xticks(xs)
    ax.set_xticklabels([s[2:].replace("-", "/") for s in m["Month"]])
    ax.set_ylim(0, m["销售额"].max() * 1.14)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v/1e4:.0f}万"))
    polish(ax)
    title_block(ax, "月度销售额：全年规模与季节性爬坡", "单位：英镑｜口径：已剔除退货、邮费与游客订单")
    ax.set_ylabel("销售额")
    save(fig, "fig01_渐变柱形图_月度销售额.png")
    reg("fig01_渐变柱形图_月度销售额.png", "渐变柱形图", "模板复现 2.1.1")


def fig02_average_line_bar():
    """带平均线柱形图：TOP10 海外市场销售额 + 平均水平虚线。"""
    c = D["country_summary"]
    c = c[c["Country"] != "United Kingdom"].head(10)
    fig, ax = plt.subplots(figsize=(10.2, 5.4))
    xs = np.arange(len(c))
    bars = ax.bar(xs, c["销售额"], width=0.62, color=C["blue"], zorder=3)
    avg = c["销售额"].mean()
    ax.axhline(avg, color=C["orange"], ls=(0, (6, 3)), lw=2, zorder=4)
    ax.set_xlim(-0.7, len(c) - 0.3)
    ax.legend(handles=[Line2D([0], [0], color=C["orange"], ls=(0, (6, 3)), lw=2,
                              label=f"平均水平 {avg/1e4:.1f} 万英镑")],
              loc="upper right", fontsize=9)
    ax.bar_label(bars, labels=[f"{v/1e4:.1f}万" for v in c["销售额"]], padding=2, fontsize=8.4)
    ax.set_xticks(xs)
    ax.set_xticklabels(c["Country"], rotation=18, ha="right")
    ax.set_ylim(0, c["销售额"].max() * 1.16)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"{v/1e4:.0f}万"))
    polish(ax)
    title_block(ax, "海外市场销售额 TOP10 与平均水平", "单位：英镑｜英国本土占 82.4%，已单列剔除以免掩盖其他市场差异")
    save(fig, "fig02_带平均线柱形图_海外市场TOP10.png")
    reg("fig02_带平均线柱形图_海外市场TOP10.png", "带平均线柱形图", "模板复现 2.1.2")


def fig03_rounded_gradient_bar():
    """渐变圆角柱形图：TOP10 SKU，顶部圆角 + 双色渐变描边。"""
    s = D["sku_top100"].head(10)
    fig, ax = plt.subplots(figsize=(10.2, 5.4))
    xs = np.arange(len(s))
    vals = s["销售额"].values
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("g", ["#F8CBAD", "#C55A11"])
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    for x, v in zip(xs, vals):
        patch = FancyBboxPatch((x - 0.29, 0), 0.58, v,
                               boxstyle="round,pad=0,rounding_size=0.10",
                               linewidth=0, facecolor="none", transform=ax.transData)
        ax.add_patch(patch)
        im = ax.imshow(grad, extent=(x - 0.29, x + 0.29, 0, v), aspect="auto",
                       cmap=cmap, origin="lower", zorder=2)
        im.set_clip_path(patch)
        ax.text(x, v * 1.02, f"{v/1e4:.1f}万", ha="center", va="bottom", fontsize=8.4, color="#843C0C")
    labels = [str(t)[:10] for t in s["Description"].fillna(s["StockCode"])]
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8.6)
    ax.set_ylim(0, vals.max() * 1.15)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"{v/1e4:.0f}万"))
    polish(ax)
    title_block(ax, "销售额 TOP10 商品（SKU）", "单位：英镑｜商品名截断至 10 字")
    save(fig, "fig03_渐变圆角柱形图_TOP10商品.png")
    reg("fig03_渐变圆角柱形图_TOP10商品.png", "渐变圆角柱形图", "模板复现 2.1.3")


def fig04_stacked_100():
    """层叠柱形图（百分比堆叠）：各季度八类客户的销售额结构。"""
    tx = D["tx"].copy()
    rfm = D["rfm_customer_level"][["CustomerID", "Segment"]]
    tx = tx.merge(rfm, on="CustomerID", how="left")
    tx["Quarter"] = tx["InvoiceDate"].dt.to_period("Q").astype(str)
    piv = tx.pivot_table(index="Quarter", columns="Segment", values="Revenue", aggfunc="sum").fillna(0)
    piv = piv[[c for c in SEG_ORDER if c in piv.columns]]
    share = piv.div(piv.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    bottom = np.zeros(len(share))
    xs = np.arange(len(share))
    for seg in share.columns:
        v = share[seg].values
        ax.bar(xs, v, bottom=bottom, width=0.6, color=SEGMENT_COLORS[seg], label=seg,
               edgecolor="white", linewidth=0.8, zorder=3)
        for x, b, h in zip(xs, bottom, v):
            if h >= 7:
                ax.text(x, b + h / 2, f"{h:.0f}%", ha="center", va="center", fontsize=8.2, color="white")
        bottom += v
    ax.set_xticks(xs)
    ax.set_xticklabels(share.index)
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.09), fontsize=8.6)
    polish(ax, grid_axis="y")
    title_block(ax, "季度销售额的客户结构（百分比堆叠）", "口径：按 RFM 八分群拆分季度销售额，观察结构漂移")
    save(fig, "fig04_层叠柱形图_季度客户结构.png")
    reg("fig04_层叠柱形图_季度客户结构.png", "层叠柱形图（100%）", "模板复现 2.1.5")


def fig05_butterfly():
    """蝴蝶图：主要海外市场上半年 vs 下半年销售额（左右分列，便于看半年度动能）。"""
    tx = D["tx"]
    h1 = tx[tx["Month"] <= "2011-06"].groupby("Country")["Revenue"].sum()
    h2 = tx[tx["Month"] >= "2011-07"].groupby("Country")["Revenue"].sum()
    c = pd.DataFrame({"H1": h1, "H2": h2}).fillna(0)
    c["total"] = c["H1"] + c["H2"]
    c = c[c.index != "United Kingdom"].sort_values("total", ascending=False).head(10)
    c = c.sort_values("total")

    fig, ax = plt.subplots(figsize=(9.8, 6.0))
    ys = np.arange(len(c))
    ax.barh(ys, c["H2"] / 1e4, color=C["darkblue"], height=0.62, zorder=3, label="下半年（7–12 月）")
    ax.barh(ys, -c["H1"] / 1e4, color=C["lightblue"], height=0.62, zorder=3, label="上半年（1–6 月）")
    for y, a, b in zip(ys, c["H2"], c["H1"]):
        ax.text(a / 1e4 + 0.5, y, f"{a/1e4:.0f}", va="center", ha="left", fontsize=8.4, color=C["darkblue"])
        ax.text(-b / 1e4 - 0.5, y, f"{b/1e4:.0f}", va="center", ha="right", fontsize=8.4, color="#2E75B6")
    ax.set_yticks(ys)
    ax.set_yticklabels(c.index)
    ax.axvline(0, color="#BFBFBF", lw=1)
    lim = max(c["H1"].max(), c["H2"].max()) / 1e4 * 1.25
    ax.set_xlim(-lim, lim)
    ticks = np.arange(-10, 11, 5)
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{abs(v):.0f}万" for v in ticks])
    ax.legend(loc="lower right", fontsize=9)
    polish(ax, grid_axis="x")
    title_block(ax, "主要海外市场：上半年 vs 下半年销售额", "单位：万英镑｜英国本土占比过高已剔除，仅保留 TOP10 海外市场", y=1.03)
    save(fig, "fig05_蝴蝶图_上下半年对比.png")
    reg("fig05_蝴蝶图_上下半年对比.png", "蝴蝶图", "模板复现 2.1.6")


def fig06_pct_bar():
    """数值百分比条形图：TOP12 国家，条形末端同时标注绝对值与占比。"""
    c = D["country_summary"].head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9.8, 6.0))
    ys = np.arange(len(c))
    bars = ax.barh(ys, c["占比"] * 100, color=C["blue"], height=0.62, zorder=3)
    bars[-1].set_color(C["darkblue"])
    for y, v, s in zip(ys, c["占比"] * 100, c["销售额"]):
        ax.text(v + 1.2, y, f"{v:.1f}%  ({s/1e4:,.0f}万)", va="center", fontsize=8.6, color=C["text"])
    ax.set_yticks(ys)
    ax.set_yticklabels(c["Country"])
    ax.set_xlim(0, (c["占比"] * 100).max() * 1.35)
    ax.set_xlabel("销售额占比（%）")
    polish(ax, grid_axis="x")
    title_block(ax, "市场集中度：TOP12 国家的销售额占比", "口径：含英国本土；纵深条形对应 Excel「数值百分比条形图」")
    save(fig, "fig06_数值百分比条形图_国家占比.png")
    reg("fig06_数值百分比条形图_国家占比.png", "数值百分比条形图", "模板复现 2.1.8")


def fig07_gantt():
    """甘特图：TOP12 客户的采购生命周期（首购 → 末购）。"""
    c = D["customers"].sort_values("Revenue", ascending=False).head(12).copy()
    seg = D["rfm_customer_level"].set_index("CustomerID")["Segment"].to_dict()
    c["start"] = pd.to_datetime(c["FirstOrder"])
    c["end"] = pd.to_datetime(c["LastOrder"])
    c = c.sort_values("start")

    fig, ax = plt.subplots(figsize=(10.4, 6.0))
    for i, (_, row) in enumerate(c.iterrows()):
        color = SEGMENT_COLORS.get(str(seg.get(row["CustomerID"], "")), C["gray"])
        ax.barh(i, (row["end"] - row["start"]).days, left=row["start"], height=0.5,
                color=color, zorder=3)
        ax.text(row["end"] + pd.Timedelta(days=6), i, f"{row['Revenue']/1e4:.0f}万",
                va="center", fontsize=8.2, color=C["text"])
    ax.set_yticks(range(len(c)))
    ax.set_yticklabels([f"客户 {int(x)}" for x in c["CustomerID"]])
    ax.set_xlim(pd.Timestamp("2010-11-15"), pd.Timestamp("2012-02-15"))
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%y/%m"))
    polish(ax, grid_axis="x")
    title_block(ax, "TOP12 客户的采购生命周期", "横轴：首购→末购区间｜颜色：RFM 分群｜末端数字：累计销售额")
    ax.legend(handles=[Line2D([0], [0], marker="s", ls="", color=SEGMENT_COLORS[s], label=s)
                       for s in SEG_ORDER[:4]], ncol=4, loc="upper center",
              bbox_to_anchor=(0.5, -0.10), fontsize=8.4)
    save(fig, "fig07_甘特图_客户生命周期.png")
    reg("fig07_甘特图_客户生命周期.png", "甘特图", "模板复现 2.1.10")


def fig08_smooth_line():
    """平滑折线图：营业额日值（仅营业日）+ 营业日 7 日移动平均。"""
    d = D["daily_trend"].copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values("date")
    d = d[d["销售额"] > 0]                      # 周六歇业，剔除零值日避免均线锯齿
    ma = d["销售额"].rolling(7, center=True).mean()

    fig, ax = plt.subplots(figsize=(10.4, 5.4))
    ax.plot(d["date"], d["销售额"], color=C["paleblue"], lw=1.0, zorder=2, label="营业日销售额")
    ax.plot(d["date"], ma, color=C["blue"], lw=2.6, zorder=3, label="7 个营业日移动平均")
    ax.fill_between(d["date"], 0, ma, color=C["blue"], alpha=0.08, zorder=1)
    peak = d.loc[d["销售额"].idxmax()]
    ax.annotate(f"峰值 {peak['销售额']/1e4:.1f}万\n{peak['date']:%Y-%m-%d}", xy=(peak["date"], peak["销售额"]),
                xytext=(-118, 26), textcoords="offset points",
                fontsize=8.8, color=C["darkblue"],
                arrowprops=dict(arrowstyle="->", color=C["darkblue"], lw=1.2))
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%y/%m"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"{v/1e4:.0f}万"))
    ax.legend(loc="upper left")
    polish(ax)
    title_block(ax, "日销售额走势与 7 日移动平均", "口径：仅客户可识别的有效交易、且仅营业日（周六门店歇业）")
    save(fig, "fig08_平滑折线图_日销售额.png")
    reg("fig08_平滑折线图_日销售额.png", "平滑折线图", "模板复现 2.2.1")


def fig09_diamond():
    """菱形走势图：周销售额，菱形标记 + 垂直引线。"""
    w = D["weekly_trend"].copy()
    w["week"] = pd.to_datetime(w["week"].astype(str).str[:10])
    x = np.arange(len(w))
    fig, ax = plt.subplots(figsize=(10.4, 5.2))
    ax.vlines(x, 0, w["销售额"], color=C["paleblue"], lw=1.0, zorder=2)
    ax.plot(x, w["销售额"], color=C["blue"], lw=1.6, zorder=3)
    ax.plot(x, w["销售额"], "D", markersize=5.5, color=C["darkblue"], zorder=4)
    for i in np.argsort(w["销售额"].values)[-3:]:
        ax.annotate(f"{w['销售额'].iloc[i]/1e4:.0f}万", (x[i], w["销售额"].iloc[i]),
                    textcoords="offset points", xytext=(0, 9), ha="center", fontsize=8.4, color=C["darkblue"])
    step = max(1, len(w) // 10)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([d.strftime("%y/%m/%d") for d in w["week"].iloc[::step]], rotation=0)
    polish(ax)
    title_block(ax, "周销售额走势（菱形标记）", "单位：英镑｜共 53 个自然周，末周为 12 月前 9 天的不完整周")
    save(fig, "fig09_菱形走势图_周销售额.png")
    reg("fig09_菱形走势图_周销售额.png", "菱形走势图", "模板复现 2.2.2")


def fig10_compare_line():
    """对比折线图：新客 vs 老客 的月度销售额。"""
    tx = D["tx"].copy()
    first = tx.groupby("CustomerID")["InvoiceDate"].min()
    tx["首购"] = tx["CustomerID"].map(first)
    tx["是否新客"] = tx["InvoiceDate"].dt.to_period("M") == tx["首购"].dt.to_period("M")
    piv = tx.pivot_table(index="Month", columns="是否新客", values="Revenue", aggfunc="sum").fillna(0) / 1e4
    piv.columns = ["老客复购", "新客首购"]

    fig, ax = plt.subplots(figsize=(10.2, 5.4))
    xs = np.arange(len(piv))
    ax.plot(xs, piv["老客复购"], color=C["blue"], lw=2.8, marker="o", ms=4, label="老客复购")
    ax.plot(xs, piv["新客首购"], color=C["orange"], lw=2.8, marker="o", ms=4, label="新客首购")
    ax.fill_between(xs, piv["老客复购"], color=C["blue"], alpha=0.06)
    ax.fill_between(xs, piv["新客首购"], color=C["orange"], alpha=0.06)
    for i in range(len(piv)):
        ax.text(xs[i], piv["老客复购"].iloc[i] + 1.6, f"{piv['老客复购'].iloc[i]:.0f}",
                ha="center", fontsize=8.0, color=C["blue"])
    ax.set_xticks(xs)
    ax.set_xticklabels([s[2:] for s in piv.index])
    ax.legend(loc="upper left")
    polish(ax)
    title_block(ax, "新客首购与老客复购的月度销售额对比", "单位：万英镑｜「新客」= 当月为首购月；2011-12 仅含 1–9 日的不完整数据")
    save(fig, "fig10_对比折线图_新老客.png")
    reg("fig10_对比折线图_新老客.png", "对比折线图", "模板复现 2.2.3")


def fig11_donut():
    """单值圆环图：年度销售目标完成率。"""
    target = 9_000_000
    actual = float(D["tx"]["Revenue"].sum())
    pct = actual / target
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.pie([pct, 1 - pct], startangle=90, counterclock=False,
           colors=[C["blue"], "#EDEDED"], wedgeprops=dict(width=0.30, edgecolor="white", linewidth=2))
    ax.text(0, 0.08, f"{pct*100:.1f}%", ha="center", va="center", fontsize=34, fontweight="bold", color=C["darkblue"])
    ax.text(0, -0.18, f"目标完成率\n{actual/1e4:,.0f}万 / {target/1e4:,.0f}万", ha="center", va="center",
            fontsize=10, color=C["sub"])
    ax.set_title("年度销售目标完成率", fontsize=15, fontweight="bold", pad=6)
    save(fig, "fig11_单值圆环图_目标完成率.png")
    reg("fig11_单值圆环图_目标完成率.png", "单值圆环图", "模板复现 2.3.1")


def fig12_rose():
    """南丁格尔玫瑰图：TOP12 海外市场销售额（极坐标柱，半径映射金额）。"""
    c = D["country_summary"]
    c = c[c["Country"] != "United Kingdom"].head(12).copy()
    c = c.sort_values("销售额", ascending=False)
    theta = np.linspace(0, 2 * np.pi, len(c), endpoint=False)
    width = 2 * np.pi / len(c) * 0.86
    r = c["销售额"].values / 1e4

    fig = plt.figure(figsize=(8.4, 7.2))
    ax = fig.add_subplot(111, projection="polar")
    colors = plt.cm.Blues(np.linspace(0.35, 0.95, len(c)))[::-1]
    ax.bar(theta, r, width=width, bottom=0, color=colors, edgecolor="white", linewidth=1.2, alpha=0.95, zorder=3)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(theta)
    ax.set_xticklabels(c["Country"], fontsize=9)
    ax.set_yticks([5, 10, 15, 20])
    ax.set_yticklabels(["5万", "10万", "15万", "20万"], fontsize=7.5, color=C["sub"])
    ax.set_ylim(0, r.max() * 1.12)
    for th, v in zip(theta, c["销售额"].values / 1e4):
        ax.text(th, v + 0.8, f"{v:.1f}", ha="center", va="bottom", fontsize=7.6, color=C["darkblue"])
    ax.grid(color="#E6E6E6", lw=0.7)
    ax.spines["polar"].set_visible(False)
    fig.suptitle("TOP12 海外市场销售额玫瑰图", x=0.03, ha="left", fontsize=15, fontweight="bold", y=0.99)
    fig.text(0.03, 0.935, "极坐标柱高度＝销售额（万英镑）｜英国本土占比 82.4%，已单列剔除", fontsize=9.2, color=C["sub"])
    save(fig, "fig12_南丁格尔玫瑰图_国家.png")
    reg("fig12_南丁格尔玫瑰图_国家.png", "南丁格尔玫瑰图", "模板复现 2.3.8")


def fig13_jue():
    """玉玦图：八类客户的销售额占比（带缺口的环形分段 + 右侧图例）。"""
    s = D["rfm_segment_summary"].set_index("Segment").reindex(SEG_ORDER).dropna()
    vals = s["销售额占比"].values * 100
    fig, ax = plt.subplots(figsize=(8.8, 6.4))
    start = 90
    gap = 1.4
    total = vals.sum()
    handles = []
    for v, seg in zip(vals, s.index):
        extent = v / total * (360 - gap * len(vals))
        color = SEGMENT_COLORS[seg]
        ax.add_patch(Wedge((0, 0), 1.0, start - extent, start - gap, width=0.24,
                           facecolor=color, edgecolor="white", linewidth=1.5))
        handles.append(Line2D([0], [0], marker="s", ls="", color=color,
                              label=f"{seg}  {v:.1f}%"))
        start -= extent + gap
    ax.text(0, 0.08, f"{len(D['rfm_customer_level']):,}", ha="center", va="center",
            fontsize=22, color=C["darkblue"], fontweight="bold")
    ax.text(0, -0.12, "付费客户", ha="center", va="center", fontsize=10, color=C["sub"])
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9.2,
              title="销售额占比", title_fontsize=9.5)
    ax.set_title("RFM 八分群的销售额占比（玉玦图）", fontsize=15, fontweight="bold", pad=10)
    save(fig, "fig13_玉玦图_客户分群占比.png")
    reg("fig13_玉玦图_客户分群占比.png", "玉玦图", "模板复现 2.3.4")


def fig14_liquid():
    """水球图：老客复购率（液面高度＝复购客户占比）。"""
    c = D["customers"]
    repurchase = float((c["Orders"] >= 2).mean())
    fig, ax = plt.subplots(figsize=(6.6, 6.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Circle((0.5, 0.5), 0.42, facecolor="#F2F6FB", edgecolor="#D8E4F2", lw=2, zorder=1))
    clip = Circle((0.5, 0.5), 0.42, transform=ax.transData)
    ax.add_patch(clip)
    clip.set_facecolor("none")
    clip.set_edgecolor("none")

    xs = np.linspace(0.06, 0.94, 500)
    level = 0.5 - 0.42 + 2 * 0.42 * repurchase
    wave = level + 0.014 * np.sin(xs * 9 * np.pi) + 0.006 * np.sin(xs * 17 * np.pi + 0.8)
    fill = ax.fill_between(xs, 0.06, wave, color=C["blue"], alpha=0.85, zorder=2, lw=0)
    fill.set_clip_path(clip)
    ax.text(0.5, 0.52, f"{repurchase*100:.1f}%", ha="center", va="center", fontsize=34,
            fontweight="bold", color="white", zorder=5)
    ax.text(0.5, 0.33, "老客复购率", ha="center", va="center", fontsize=12, color="white", zorder=5)
    ax.text(0.5, 0.06, f"复购客户 {int((c['Orders']>=2).sum()):,} / 总客户 {len(c):,}", ha="center",
            fontsize=9, color=C["sub"])
    ax.set_title("老客复购率", fontsize=15, fontweight="bold")
    save(fig, "fig14_水球图_复购率.png")
    reg("fig14_水球图_复购率.png", "水球图", "模板复现 2.3.2")


def fig15_bar_line():
    """柱形折线图：月度销售额（柱）+ 订单数（线，右轴）。"""
    m = D["monthly_trend"]
    fig, ax = plt.subplots(figsize=(10.2, 5.6))
    xs = np.arange(len(m))
    bars = ax.bar(xs, m["销售额"] / 1e4, width=0.58, color=C["lightblue"], zorder=2, label="销售额（万英镑）")
    ax.bar_label(bars, labels=[f"{v/1e4:.0f}" for v in m["销售额"]], padding=2, fontsize=7.8, color=C["darkblue"])
    ax.set_ylabel("销售额（万英镑）")
    ax.set_xticks(xs)
    ax.set_xticklabels([s[2:] for s in m["Month"]])
    ax.set_ylim(0, m["销售额"].max() / 1e4 * 1.22)
    polish(ax)

    ax2 = ax.twinx()
    ax2.plot(xs, m["订单数"], color=C["orange"], lw=2.6, marker="o", ms=4.5, zorder=5, label="订单数")
    ax2.set_ylabel("订单数", color=C["orange"])
    ax2.tick_params(axis="y", colors=C["orange"])
    ax2.grid(False)
    for side in ("top", "right", "left"):
        ax2.spines[side].set_visible(False)
    ax2.set_ylim(0, m["订单数"].max() * 1.25)

    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", ncol=2)
    title_block(ax, "月度销售额与订单量：量价齐升还是单价驱动", "左轴：销售额（万英镑）｜右轴：订单数（张）")
    save(fig, "fig15_柱形折线图_销售额与订单.png")
    reg("fig15_柱形折线图_销售额与订单.png", "柱形折线图", "模板复现 2.4.1")


# =====================================================================
# 第二部分：业务模型图
# =====================================================================
def fig16_rfm_scatter():
    """RFM 气泡散点图：R×F，气泡大小＝M，颜色＝分群。"""
    r = D["rfm_customer_level"]
    fig, ax = plt.subplots(figsize=(10.4, 7.2))
    for seg in SEG_ORDER:
        sub = r[r["Segment"] == seg]
        if sub.empty:
            continue
        ax.scatter(sub["R"], sub["F"], s=np.sqrt(sub["M"]) * 1.6, color=SEGMENT_COLORS[seg],
                   alpha=0.42, edgecolor="none", label=seg, zorder=3)
    # 分群重心，便于在密集点云中定位
    for seg in SEG_ORDER:
        sub = r[r["Segment"] == seg]
        if len(sub) < 20:
            continue
        cx, cy = sub["R"].median(), max(sub["F"].median(), 1)
        ax.scatter([cx], [cy], s=90, marker="X", color=SEGMENT_COLORS[seg],
                   edgecolor="white", linewidth=0.8, zorder=5)
    ax.set_xscale("symlog", linthresh=10)
    ax.set_yscale("log")
    ax.axvline(r["R"].median(), color=C["gray"], ls="--", lw=1.2, zorder=1)
    ax.axhline(max(r["F"].median(), 1), color=C["gray"], ls="--", lw=1.2, zorder=1)
    ax.text(r["R"].median() * 1.08, 1.1, f"R 中位数 {r['R'].median():.0f} 天", fontsize=8.4, color=C["sub"])
    ax.text(1.2, max(r["F"].median(), 1) * 1.15, f"F 中位数 {r['F'].median():.0f} 次", fontsize=8.4, color=C["sub"])
    ax.set_xlabel("最近一次购买距今（天，R）")
    ax.set_ylabel("购买频次（次，F，对数轴）")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.17), fontsize=8.4, markerscale=0.45)
    polish(ax, grid_axis="both")
    title_block(ax, "RFM 客户分布：R×F 平面上的价值分层", "气泡面积＝累计消费金额（M）｜虚线为 R、F 中位数切分线｜× 为各分群重心")
    save(fig, "fig16_RFM气泡散点图.png")
    reg("fig16_RFM气泡散点图.png", "RFM 气泡散点图", "模型 M1 RFM")


def fig17_segment_value():
    """八分群价值对比：客户数占比 vs 销售额占比（分组条形）。"""
    s = D["rfm_segment_summary"].set_index("Segment").reindex(SEG_ORDER).dropna()
    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    ys = np.arange(len(s))[::-1]
    h = 0.36
    b1 = ax.barh(ys + h / 2, s["客户占比"] * 100, height=h, color=C["lightblue"], label="客户数占比", zorder=3)
    b2 = ax.barh(ys - h / 2, s["销售额占比"] * 100, height=h, color=C["darkblue"], label="销售额占比", zorder=3)
    for b in list(b1) + list(b2):
        w = b.get_width()
        ax.text(w + 0.8, b.get_y() + b.get_height() / 2, f"{w:.1f}%", va="center", fontsize=8.2, color=C["text"])
    ax.set_yticks(ys)
    ax.set_yticklabels(s.index)
    ax.set_xlim(0, max(s[["客户占比", "销售额占比"]].max()) * 118)
    ax.set_xlabel("占比（%）")
    ax.legend(loc="lower right")
    polish(ax, grid_axis="x")
    title_block(ax, "八类客户：人数占比与销售额占比的错配", "口径：R/F/M 均以中位数二分；「重要*」= 金额高于中位数", y=1.03)
    save(fig, "fig17_八分群价值对比.png")
    reg("fig17_八分群价值对比.png", "分群价值对比条形图", "模型 M1 RFM")


def fig18_cohort_heatmap():
    """同期群留存热力图：首购月 × 第 N 月留存率。"""
    mat = D["cohort_retention"].set_index("首购月")
    mat = mat.drop(columns=[c for c in mat.columns if c not in [str(i) for i in range(12)]], errors="ignore")
    fig, ax = plt.subplots(figsize=(10.6, 6.2))
    data = mat.values * 100
    im = ax.imshow(data, cmap="Blues", aspect="auto", vmin=0, vmax=85)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if np.isnan(v) or v == 0 and j > 0:
                continue
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.8,
                    color="white" if v > 45 else C["text"])
    ax.set_xticks(range(data.shape[1]))
    ax.set_xticklabels([f"M{i}" for i in range(data.shape[1])])
    ax.set_yticks(range(len(mat)))
    ax.set_yticklabels(mat.index)
    ax.set_xlabel("距首购月的时间间隔")
    ax.set_ylabel("首购月（同期群）")
    ax.grid(False)
    for side in ax.spines.values():
        side.set_visible(False)
    cb = fig.colorbar(im, ax=ax, pad=0.015, fraction=0.035)
    cb.set_label("留存率（%）", fontsize=9)
    cb.outline.set_visible(False)
    title_block(ax, "同期群留存：次月流失是最大的价值漏斗", "口径：某客户在某月有交易即视为当月留存；M0 为 100%", y=1.03)
    save(fig, "fig18_同期群留存热力图.png")
    reg("fig18_同期群留存热力图.png", "同期群留存热力图", "模型 M2 同期群")


def fig19_pareto():
    """帕累托图：全部 4,333 位客户的贡献集中度 + 80% 参考线。"""
    p = D["pareto_customers"]
    fig, ax = plt.subplots(figsize=(10.4, 5.8))
    xs = np.arange(len(p))
    ax.bar(xs, p["Revenue"] / 1e4, color=C["lightblue"], width=1.0, zorder=2, label="单个客户销售额（万英镑）")
    ax.set_ylabel("客户销售额（万英镑）")
    ax.set_xlabel("客户排名（按销售额降序）")
    ax.set_xticks([1, 500, 1000, 2000, 3000, 4000])
    ax.set_xticklabels(["1", "500", "1,000", "2,000", "3,000", "4,000"])
    n80 = int((p["cum_share"] < 0.8).sum() + 1)
    ax.axvline(n80, color=C["red"], ls=":", lw=1.4, zorder=4)
    ax.annotate(f"第 {n80:,} 名（占 {n80/len(p):.1%}）\n累计达 80%", xy=(n80, 0.2), xytext=(n80 + 250, 6.2),
                fontsize=8.8, color=C["red"],
                arrowprops=dict(arrowstyle="->", color=C["red"], lw=1.2))
    polish(ax)

    ax2 = ax.twinx()
    ax2.plot(xs, p["cum_share"] * 100, color=C["orange"], lw=2.6, zorder=5, label="累计销售额占比")
    ax2.axhline(80, color=C["red"], ls="--", lw=1.1, zorder=3)
    ax2.set_ylabel("累计占比（%）", color=C["orange"])
    ax2.tick_params(axis="y", colors=C["orange"])
    ax2.set_ylim(0, 105)
    ax2.grid(False)
    for side in ("top", "right", "left"):
        ax2.spines[side].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="center right", fontsize=8.6)
    title_block(ax, "帕累托图：客户贡献高度集中", f"口径：{n80/len(p):.1%} 的客户贡献 80% 销售额；前 10% 客户贡献 60.3%")
    save(fig, "fig19_帕累托图.png")
    reg("fig19_帕累托图.png", "帕累托图", "模型 M5 帕累托/ABC")


def fig20_bdc():
    """波士顿矩阵：SKU 份额 × 增速四象限气泡图。"""
    b = pd.read_csv(TBL_DIR / "bdc_matrix.csv")
    fig, ax = plt.subplots(figsize=(10.0, 6.4))
    color_map = {"明星": C["gold"], "金牛": C["blue"], "问题": C["green"], "瘦狗": C["gray"]}
    for q, sub in b.groupby("象限"):
        ax.scatter(sub["份额"] * 100, sub["增速"] * 100, s=np.sqrt(sub["销售额"]) * 0.55,
                   color=color_map.get(q, C["gray"]), alpha=0.7, edgecolor="white", linewidth=0.6,
                   label=q, zorder=3)
    ax.axvline(b["份额"].median() * 100, color=C["gray"], ls="--", lw=1.1, zorder=1)
    ax.axhline(0, color=C["gray"], ls="--", lw=1.1, zorder=1)
    ax.set_xlabel("销售额份额（%，占全店销售额）")
    ax.set_ylabel("增速（%，下半年 vs 上半年）")
    top = b.nlargest(5, "销售额")
    for _, row in top.iterrows():
        ax.annotate(str(row["Description"])[:12], (row["份额"] * 100, row["增速"] * 100),
                    textcoords="offset points", xytext=(6, 6), fontsize=7.8, color=C["text"])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, fontsize=8.6, markerscale=0.7)
    for label, (px, py), ha, col in [("明星", (0.965, 0.94), "right", C["gold"]),
                                     ("金牛", (0.965, 0.06), "right", C["blue"]),
                                     ("问题", (0.035, 0.94), "left", C["green"]),
                                     ("瘦狗", (0.035, 0.06), "left", C["gray"])]:
        ax.text(px, py, label, transform=ax.transAxes, ha=ha, va="center",
                fontsize=15, color=col, alpha=0.45, fontweight="bold")
    polish(ax, grid_axis="both")
    title_block(ax, "商品波士顿矩阵：份额 × 增速的四象限", "气泡面积＝上半年+下半年销售额｜分割线：份额中位数、零增长")
    save(fig, "fig20_波士顿矩阵.png")
    reg("fig20_波士顿矩阵.png", "波士顿矩阵四象限图", "模型 M6 波士顿矩阵")


def fig21_rules_bubble():
    """关联规则气泡图：覆盖订单数 × 提升度，气泡大小＝置信度。"""
    r = D["association_rules"].head(120).copy()
    fig, ax = plt.subplots(figsize=(10.2, 6.0))
    sc = ax.scatter(r["count"], r["lift"], s=r["confidence"] * 260,
                    c=r["lift"], cmap="OrRd", alpha=0.7, edgecolor="white", linewidth=0.7, zorder=3)
    top1 = r.nlargest(1, "lift").iloc[0]
    ax.annotate(f"{top1['antecedent_name']}\n→ {top1['consequent_name']}（提升度 {top1['lift']:.1f}）",
                (top1["count"], top1["lift"]),
                textcoords="offset points", xytext=(26, 26), ha="left", fontsize=7.6,
                color=C["text"], arrowprops=dict(arrowstyle="-", color=C["sub"], lw=0.7),
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=2))
    cb = fig.colorbar(sc, ax=ax, pad=0.015, fraction=0.035)
    cb.set_label("提升度 Lift", fontsize=9)
    cb.outline.set_visible(False)
    ax.set_xlabel("覆盖订单数（单）")
    ax.set_ylabel("提升度 Lift（倍）")
    ax.set_xlim(130, r["count"].max() * 1.12)
    ax.set_ylim(r["lift"].min() * 0.92, r["lift"].max() * 1.22)
    polish(ax, grid_axis="both")
    title_block(ax, "购物篮关联规则：覆盖广度与提升度",
                "气泡大小＝置信度｜英国 15,365 张多品订单，971 条规则中取提升度 TOP120｜support≥1%、lift≥1.2、count≥15")
    save(fig, "fig21_关联规则气泡图.png")
    reg("fig21_关联规则气泡图.png", "关联规则气泡图", "模型 M3 Apriori")


def fig22_sarima():
    """SARIMA 预测图：历史 + 回测 + 未来 28 天预测与 95% 置信区间。"""
    d = D["daily_trend"].copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.set_index("date")["销售额"].asfreq("D").fillna(0)
    bt = pd.read_csv(TBL_DIR / "sarima_backtest.csv", parse_dates=["date"])
    fc = pd.read_csv(TBL_DIR / "sarima_forecast.csv", parse_dates=["date"])

    fig, ax = plt.subplots(figsize=(11.0, 5.8))
    hist = d.loc[d.index >= "2011-08-01"]
    cap = float(np.nanpercentile(hist.values, 99) * 2.4)
    ax.plot(hist.index, hist.values, color="#5A5A5A", lw=1.3, zorder=6, label="实际销售额")
    ax.plot(bt["date"], bt["pred"], color=C["blue"], lw=2.0, label="回测预测（56 天）")
    ax.fill_between(bt["date"], np.clip(bt["lower95"], 0, cap), np.clip(bt["upper95"], 0, cap),
                    color=C["blue"], alpha=0.16, label="95% 置信区间")
    ax.plot(fc["date"], fc["forecast"], color=C["orange"], lw=2.4, label="未来 28 天预测")
    ax.fill_between(fc["date"], np.clip(fc["lower95"], 0, cap), np.clip(fc["upper95"], 0, cap),
                    color=C["orange"], alpha=0.18)
    ax.axvline(bt["date"].iloc[0], color=C["sub"], ls=":", lw=1.2)
    ax.set_ylim(0, cap)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"{v/1e4:.0f}万"))
    ax.annotate("回测起点", (bt["date"].iloc[0], cap * 0.93), fontsize=8.6, color=C["sub"],
                xytext=(6, 0), textcoords="offset points")
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%y/%m"))
    ax.legend(loc="upper left", ncol=2, fontsize=8.2)
    polish(ax)
    title_block(ax, "SARIMA 日销售额预测（含 95% 置信区间）",
                "回测 56 天：MAPE 35.4%、RMSE 17,420；季节朴素法 MAPE 31.6%｜区间上限超出绘图范围的部分已截断")
    save(fig, "fig22_SARIMA预测图.png")
    reg("fig22_SARIMA预测图.png", "SARIMA 预测带图", "模型 M4 预测")


def fig23_abc():
    """ABC 分层对比：客户数与销售额的双维结构。"""
    a = pd.read_csv(TBL_DIR / "abc_summary.csv")
    a_share = float(a.loc[a["ABC"] == "A", "客户占比"].sum()) * 100
    a_rev = float(a.loc[a["ABC"] == "A", "销售额占比"].sum()) * 100
    fig, ax = plt.subplots(figsize=(9.0, 5.4))
    xs = np.arange(len(a))
    w = 0.32
    b1 = ax.bar(xs - w / 2, a["客户占比"] * 100, width=w, color=C["lightblue"], label="客户数占比", zorder=3)
    b2 = ax.bar(xs + w / 2, a["销售额占比"] * 100, width=w, color=C["darkblue"], label="销售额占比", zorder=3)
    ax.bar_label(b1, fmt="%.1f%%", padding=2, fontsize=9)
    ax.bar_label(b2, fmt="%.1f%%", padding=2, fontsize=9, color=C["darkblue"])
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{k} 类客户" for k in a["ABC"]])
    ax.set_ylim(0, 100)
    ax.set_ylabel("占比（%）")
    ax.legend(loc="upper right")
    polish(ax)
    title_block(ax, f"ABC 分类：A 类客户以 {a_share:.1f}% 的人数贡献 {a_rev:.1f}% 销售额",
                "口径：客户按累计销售额 70% / 90% 切分为 A / B / C 三层")
    save(fig, "fig23_ABC分层对比.png")
    reg("fig23_ABC分层对比.png", "ABC 分层柱形图", "模型 M5 帕累托/ABC")


def main() -> None:
    setup_style()
    print("=" * 78)
    print("04_visuals —— 生成全部图表")
    print("=" * 78)
    for fn in [fig01_gradient_bar, fig02_average_line_bar, fig03_rounded_gradient_bar, fig04_stacked_100,
               fig05_butterfly, fig06_pct_bar, fig07_gantt, fig08_smooth_line, fig09_diamond,
               fig10_compare_line, fig11_donut, fig12_rose, fig13_jue, fig14_liquid, fig15_bar_line,
               fig16_rfm_scatter, fig17_segment_value, fig18_cohort_heatmap, fig19_pareto,
               fig20_bdc, fig21_rules_bubble, fig22_sarima, fig23_abc]:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] {fn.__name__}: {type(e).__name__}: {e}")

    idx = pd.DataFrame(FIG_INDEX, columns=["文件名", "图表名称", "对应模板/模型"])
    idx.insert(0, "编号", [f"fig{i:02d}" for i in range(1, len(idx) + 1)])
    idx.to_csv(FIG_DIR / "图表索引.csv", index=False, encoding="utf-8-sig")
    print(f"[done] 共 {len(idx)} 张图，索引 -> outputs/figures/图表索引.csv")


if __name__ == "__main__":
    main()
