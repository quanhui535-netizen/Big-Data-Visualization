# -*- coding: utf-8 -*-
"""
实验 02 · 收入趋势分析：从 Excel 数据透视表到 pandas 多层下钻
==============================================================
教材：《CDA 一级认证教材：商业数据分析》第 3 章 商业数据分析框架 · 案例 1
原始素材：``案例1：收入趋势分析原始数据.xlsx``（1187 行 × 4 列）
迁移方向：Excel/WPS 数据透视表 + 组合图 + 切片器  →  pandas groupby + matplotlib

教材用 Excel 做了 5 层分析（见原文件「准备区」）：
    1. 年度销售趋势            —— 透视表：行=订单年份，值=求和项:销售额
    2. 2020 年各月销售趋势      —— 透视表：行=订单月份，筛选年份=2020
    3. 2020 年各月同比          —— 透视表：列=订单年份，计算同比增速（差异百分比）
    4. 2020 年 11 月各省份同比  —— 透视表：行=销售省份，列=年份，发现异常月份 11 月
    5. 四川省各月同比（下钻）    —— 在「省份」维度上继续下钻到「月份」
本脚本把这 5 层分析完整迁移为 Python，并把每一步的中间结果落盘成 CSV，
便于和教材里的透视表逐格核对。

运行：``python lab02_revenue_trend.py``（在实验目录下执行）
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# 让脚本能从仓库根的 common/ 导入统一样式
LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR.parent))

from common.style import (  # noqa: E402
    BLUE, BLUE2, GRAY, NEG, ORANGE, POS,
    apply_style, bar_labels, new_fig, pct_axis, save_csv, save_fig,
)

DATA = LAB_DIR / "data" / "案例1：收入趋势分析原始数据.xlsx"
OUT = LAB_DIR / "outputs"


# ---------------------------------------------------------------------------
# 0. 读取数据 —— 对应 Excel 里「原始数据」工作表
# ---------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    """读取原始订单明细，并做最基本的字段规范化。

    Excel 里这步只是「打开工作表」；Python 里多做两件事：
      * 把中文列名换成英文别名，后续代码更短（保留原列名映射，方便对照）；
      * 把年份/月份统一转成整数，并用 ``period`` 生成连续月份轴，
        避免 2019-12 到 2020-01 在折线图上被画成"相邻"却看不出跨年。
    """
    df = pd.read_excel(DATA)
    df.columns = ["year", "month", "province", "sales"]

    # 数据质量检查：教材没写，但 Python 里可以顺手做，避免脏数据污染透视结果
    df = df.dropna(subset=["year", "month", "province", "sales"])
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)
    df["sales"] = df["sales"].astype(float)

    # 生成「年-月」周期，用于折线图横轴排序
    df["period"] = pd.to_datetime(
        dict(year=df["year"], month=df["month"], day=1)
    ).dt.to_period("M")
    print(f"[数据] 订单明细 {df.shape[0]} 行，时间跨度 "
          f"{df['period'].min()} ~ {df['period'].max()}，"
          f"覆盖 {df['province'].nunique()} 个省份")
    return df


# ---------------------------------------------------------------------------
# 1. 年度销售趋势 —— 透视表「行=订单年份，值=求和项:销售额」+ 同比增速
# ---------------------------------------------------------------------------
def yearly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """按年汇总销售额，并计算同比增速。

    Excel 对应操作：
        插入 → 数据透视表 → 行:订单年份 / 值:求和项:销售额 → 再添加「差异百分比」计算项
    pandas 对应：
        ``groupby('year')['sales'].sum()`` + ``pct_change()``
    """
    yearly = (
        df.groupby("year", as_index=False)["sales"].sum()
        .sort_values("year")
        .reset_index(drop=True)
    )
    yearly["yoy"] = yearly["sales"].pct_change()          # 同比增速（第一年为 NaN）
    yearly["share"] = yearly["sales"] / yearly["sales"].sum()  # 各年占比

    print("\n== 1. 年度销售趋势 ==")
    for _, r in yearly.iterrows():
        yoy = "—" if pd.isna(r["yoy"]) else f"{r['yoy']:+.1%}"
        print(f"  {int(r['year'])} 年：销售额 {r['sales']:>10,.0f} 元，同比 {yoy}")
    save_csv(yearly, OUT, "table01_年度销售汇总")

    fig, ax = new_fig(8.2, 4.6)
    bars = ax.bar(yearly["year"].astype(str), yearly["sales"] / 10000,
                  color=[BLUE2, BLUE2, BLUE, BLUE], width=0.55, zorder=3)
    bar_labels(ax, fmt="{:.0f}万", fontsize=9.5)
    ax.set_title("2017—2020 年度销售额及同比增速", pad=12)
    ax.set_xlabel("订单年份")
    ax.set_ylabel("销售额（万元）")
    ax.set_ylim(0, yearly["sales"].max() / 10000 * 1.22)

    # 次坐标轴画同比增速折线（Excel 组合图里「次坐标轴」的等价实现）
    ax2 = ax.twinx()
    ax2.plot(yearly["year"].astype(str), yearly["yoy"], color=ORANGE,
             marker="o", markersize=7, linewidth=2.2, zorder=5)
    for x, y in zip(yearly["year"].astype(str), yearly["yoy"]):
        if pd.notna(y):
            ax2.annotate(f"{y:+.1%}", (x, y), xytext=(0, 10),
                         textcoords="offset points", ha="center",
                         color=ORANGE, fontsize=9.5, fontweight="bold")
    ax2.set_ylabel("同比增速", color=ORANGE)
    ax2.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax2.set_ylim(0, yearly["yoy"].max() * 1.6)
    ax2.grid(False)
    save_fig(fig, OUT, "fig01_年度销售额与同比增速")
    return yearly


# ---------------------------------------------------------------------------
# 2. 2020 年各月销售趋势 —— 透视表筛选年份
# ---------------------------------------------------------------------------
def monthly_2020(df: pd.DataFrame) -> pd.DataFrame:
    """2020 年逐月销售额 + 环比增速 + 累计完成度。

    Excel 对应：「订单年份」筛选 2020 → 行放「订单月份」→ 值求和；
    再插入折线图看趋势。Python 里额外算「环比」和「累计占比」，用于回答
    "全年销售是前高后低还是靠某几个月冲量"。
    """
    m = (
        df[df["year"] == 2020]
        .groupby("month", as_index=False)["sales"].sum()
        .sort_values("month")
    )
    m["mom"] = m["sales"].pct_change()                       # 环比
    m["cum_share"] = m["sales"].cumsum() / m["sales"].sum()  # 累计占比

    peak = m.loc[m["sales"].idxmax()]
    print("\n== 2. 2020 年各月销售 ==")
    print(f"  全年合计 {m['sales'].sum():,.0f} 元；最高月为 {int(peak['month'])} 月 "
          f"（{peak['sales']:,.0f} 元，占全年 {peak['sales'] / m['sales'].sum():.1%}）")
    print(f"  上半年（1—6 月）占全年 {m.loc[m['month'] <= 6, 'sales'].sum() / m['sales'].sum():.1%}，"
          f"下半年占 {m.loc[m['month'] >= 7, 'sales'].sum() / m['sales'].sum():.1%}")

    fig, ax = new_fig(8.4, 4.4)
    colors = [ORANGE if v == m["sales"].max() else BLUE2 for v in m["sales"]]
    ax.bar(m["month"].astype(int).astype(str), m["sales"] / 10000,
           color=colors, width=0.62, zorder=3)
    bar_labels(ax, fmt="{:.0f}", fontsize=8.5)
    ax.set_title("2020 年逐月销售额（万元）", pad=12)
    ax.set_xlabel("月份")
    ax.set_ylabel("销售额（万元）")
    ax.set_ylim(0, m["sales"].max() / 10000 * 1.25)

    # 用折线叠加"累计占比"，一眼看出全年销售节奏（帕累托视角）
    ax2 = ax.twinx()
    ax2.plot(m["month"].astype(int).astype(str), m["cum_share"],
             color=GRAY, linestyle="--", marker="D", markersize=4, linewidth=1.6)
    ax2.set_ylabel("累计占比", color=GRAY)
    ax2.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax2.set_ylim(0, 1.05)
    ax2.grid(False)
    save_fig(fig, OUT, "fig02_2020年逐月销售额与累计占比")
    save_csv(m, OUT, "table02_2020年月度销售")
    return m


# ---------------------------------------------------------------------------
# 3. 2020 年各月同比 —— 透视表「列=年份 + 差异百分比」
# ---------------------------------------------------------------------------
def monthly_yoy(df: pd.DataFrame) -> pd.DataFrame:
    """2019 vs 2020 月度对比 + 同比增速。

    Excel 对应：透视表列区放「订单年份」，加「差异百分比（年份）」计算项；
    再用簇状柱形图 + 折线图的组合图呈现。
    pandas 对应：``pivot_table(index='month', columns='year')``，再做列间运算。
    """
    pv = df[df["year"].isin([2019, 2020])].pivot_table(
        index="month", columns="year", values="sales", aggfunc="sum"
    )
    pv["yoy"] = pv[2020] / pv[2019] - 1
    pv = pv.reset_index()
    print("\n== 3. 2020 年各月同比 ==")
    neg = pv[pv["yoy"] < 0]
    print(f"  12 个月中有 {len(neg)} 个月同比下滑："
          + "、".join(f"{int(r.month)}月({r.yoy:+.1%})" for r in neg.itertuples()))
    print(f"  同比增幅最大的月份：{int(pv.loc[pv['yoy'].idxmax(), 'month'])} 月"
          f"（{pv['yoy'].max():+.1%}）")

    fig, axes = new_fig(10.5, 4.6, ncols=2)
    ax = axes[0]
    x = pv["month"].astype(int).astype(str)
    width = 0.38
    ax.bar(np.arange(len(x)) - width / 2, pv[2019] / 10000, width,
           label="2019", color=BLUE2, zorder=3)
    ax.bar(np.arange(len(x)) + width / 2, pv[2020] / 10000, width,
           label="2020", color=ORANGE, zorder=3)
    ax.set_xticks(np.arange(len(x)), x)
    ax.set_title("2019 vs 2020 月度销售额（万元）", pad=10)
    ax.set_xlabel("月份")
    ax.set_ylabel("销售额（万元）")
    ax.legend(loc="upper left")

    ax = axes[1]
    colors = [POS if v >= 0 else NEG for v in pv["yoy"]]
    ax.bar(x, pv["yoy"], color=colors, width=0.62, zorder=3)
    ax.axhline(0, color="#555555", linewidth=0.9)
    pct_axis(ax)
    for xi, v in zip(x, pv["yoy"]):
        ax.annotate(f"{v:+.1%}", (xi, v), xytext=(0, 6 if v >= 0 else -16),
                    textcoords="offset points", ha="center", fontsize=8,
                    color=POS if v >= 0 else NEG)
    ax.set_title("2020 年各月同比增速", pad=10)
    ax.set_xlabel("月份")
    ax.set_ylabel("同比")
    ax.set_ylim(pv["yoy"].min() * 1.9, pv["yoy"].max() * 1.3)
    fig.suptitle("月度销售额与同比：2019 年基数 vs 2020 年表现", y=1.02,
                 fontsize=13, fontweight="bold")
    save_fig(fig, OUT, "fig03_月度销售额对比与同比")
    save_csv(pv, OUT, "table03_2020年月度同比")
    return pv


# ---------------------------------------------------------------------------
# 4. 2020 年 11 月各省份同比 —— 发现异常省份（教材的"异常月份"分析法）
# ---------------------------------------------------------------------------
def province_yoy_nov(df: pd.DataFrame) -> pd.DataFrame:
    """聚焦 2020 年 11 月，按省份做同比，找出拖累大盘的异常省份。

    教材在这里的思路值得迁移：**同比异常 → 定位到具体月份 → 再定位到具体省份**，
    这是商业分析里最典型的「下钻（drill-down）」路径。
    Excel 用切片器逐级筛选，Python 用布尔索引 + groupby，可以批量算出所有省份。
    """
    nov = df[(df["month"] == 11) & (df["year"].isin([2019, 2020]))]
    pv = nov.pivot_table(index="province", columns="year", values="sales", aggfunc="sum")
    pv = pv.fillna(0.0)                      # 某省某年 11 月无数据 → 0
    pv.columns = ["y2019", "y2020"]          # 列名不能是纯数字，转成可读别名
    pv["yoy"] = np.where(pv["y2019"] > 0, pv["y2020"] / pv["y2019"] - 1, np.nan)
    pv["diff"] = pv["y2020"] - pv["y2019"]
    pv = pv.reset_index().sort_values("diff")

    print("\n== 4. 2020 年 11 月各省份同比 ==")
    print(f"  11 月总额：2019 {pv['y2019'].sum():,.0f} → 2020 {pv['y2020'].sum():,.0f}，"
          f"同比 {pv['y2020'].sum() / pv['y2019'].sum() - 1:+.1%}")
    print("  同比拖累最大的 3 个省份：")
    for _, r in pv.head(3).iterrows():
        print(f"    {r['province']}: 2019 {r['y2019']:,.0f} → 2020 {r['y2020']:,.0f}"
              f"（{r['yoy']:+.1%}，减少 {abs(r['diff']):,.0f} 元）")

    # 把"为什么是 11 月"落成一张排序条形图：只展示同比变化额最大的 12 个省份
    sel = pd.concat([pv.head(6), pv.tail(6)]).sort_values("diff")
    fig, ax = new_fig(9.0, 5.0)
    colors = [NEG if v < 0 else POS for v in sel["diff"]]
    ax.barh(sel["province"], sel["diff"] / 10000, color=colors, height=0.62, zorder=3)
    ax.axvline(0, color="#555555", linewidth=0.9)
    for y, v in zip(range(len(sel)), sel["diff"] / 10000):
        ax.annotate(f"{v:+.1f}万", (v, y), xytext=(8 if v >= 0 else -8, 0),
                    textcoords="offset points", va="center", fontsize=8.5,
                    ha="left" if v >= 0 else "right",
                    color=POS if v >= 0 else NEG)
    ax.set_title("2020 年 11 月各省份销售额同比变化（前 6 增 / 后 6 减）", pad=12)
    ax.set_xlabel("同比变化额（万元）")
    ax.set_ylabel("")
    ax.set_xlim(sel["diff"].min() / 10000 * 1.35, sel["diff"].max() / 10000 * 1.35)
    ax.grid(axis="y", visible=False)
    save_fig(fig, OUT, "fig04_11月省份同比变化")
    save_csv(pv, OUT, "table04_2020年11月省份同比")
    return pv


# ---------------------------------------------------------------------------
# 5. 四川省各月同比 —— 在"省份"维度上继续下钻到"月份"
# ---------------------------------------------------------------------------
def sichuan_drilldown(df: pd.DataFrame) -> pd.DataFrame:
    """教材第 5 层：锁定四川省，看它 12 个月的同比走势。

    这一步回答的是"异常到底出在哪几个月、是偶发还是持续"。
    Excel 里靠切片器把省份切到四川；Python 用一行过滤即可，
    还能顺手算出"四川省对全省 11 月缺口的贡献度"。
    """
    sc = df[df["province"] == "四川"]
    pv = sc.pivot_table(index="month", columns="year", values="sales", aggfunc="sum")
    pv = pv.reindex(range(1, 13))            # 月份补全 1—12
    pv["yoy"] = pv[2020] / pv[2019] - 1
    pv = pv.reset_index()

    print("\n== 5. 四川省月度同比（下钻） ==")
    print(f"  四川 2020 年合计 {pv[2020].sum():,.0f} 元，同比 "
          f"{pv[2020].sum() / pv[2019].sum() - 1:+.1%}")
    bad = pv[pv["yoy"] < -0.5]
    print(f"  同比跌幅超过 50% 的月份：{len(bad)} 个 —— "
          + "、".join(f"{int(r.month)}月" for r in bad.itertuples()))

    fig, axes = new_fig(9.2, 6.0, nrows=2, sharex=True,
                        gridspec_kw={"height_ratios": [2.2, 1]})
    x = pv["month"].astype(int)

    ax = axes[0]
    ax.plot(x, pv[2019] / 10000, marker="o", color=BLUE2, linewidth=2,
            label="2019 年", zorder=3)
    ax.plot(x, pv[2020] / 10000, marker="s", color=ORANGE, linewidth=2,
            label="2020 年", zorder=3)
    ax.set_title("四川省 2019 vs 2020 逐月销售额（万元）", pad=10)
    ax.set_ylabel("销售额（万元）")
    ax.legend(loc="upper left", ncol=2)
    ax.set_xticks(x)

    # 下方面板专门画同比增速，避免和绝对值挤在同一个 y 轴上。
    # 注意：四川 12 月基数极低（682 → 21,686，+3080%），会把坐标轴拉爆，
    # 因此把超过 +300% 的柱子截断显示，并在标签里写明真实值——这本身也是一个教学点：
    # **省级小样本的同比会被低基数放大，不能直接当增长质量看。**
    ax = axes[1]
    cap = 3.0
    yoy_plot = pv["yoy"].clip(upper=cap)
    colors = [POS if v >= 0 else NEG for v in pv["yoy"]]
    ax.bar(x, yoy_plot, color=colors, width=0.62, zorder=3)
    ax.axhline(0, color="#555555", linewidth=0.9)
    pct_axis(ax)
    for xi, v, vp in zip(x, pv["yoy"], yoy_plot):
        if pd.isna(v):
            continue
        label = f"{v:+.0%}" + (" ↑" if v > cap else "")
        ax.annotate(label, (xi, vp), xytext=(0, 5 if v >= 0 else -15),
                    textcoords="offset points", ha="center", fontsize=7.5,
                    color=POS if v >= 0 else NEG)
    ax.set_xlabel("月份")
    ax.set_ylabel("同比增速")
    ax.set_ylim(-1.55, cap * 1.18)
    save_fig(fig, OUT, "fig05_四川省月度下钻")
    save_csv(pv, OUT, "table05_四川省月度同比")
    return pv


def main() -> None:
    apply_style()
    df = load_data()
    yearly = yearly_trend(df)
    monthly_2020(df)
    m_yoy = monthly_yoy(df)
    prov = province_yoy_nov(df)
    sichuan_drilldown(df)

    # ---- 汇总几条可以直接写进分析报告的业务结论 ----
    print("\n" + "=" * 66)
    print("业务结论（可直接用于报告）")
    print("=" * 66)
    print(f"1. 四年销售额从 {yearly.loc[0, 'sales'] / 1e4:.0f} 万增至 "
          f"{yearly.loc[len(yearly) - 1, 'sales'] / 1e4:.0f} 万，"
          f"年均复合增速 {((yearly.loc[len(yearly) - 1, 'sales'] / yearly.loc[0, 'sales']) ** (1 / 3) - 1):.1%}；")
    print(f"2. 2020 年 11 月是全年唯一同比大幅下滑的月份（"
          f"{m_yoy.loc[m_yoy['month'] == 11, 'yoy'].iloc[0]:+.1%}），"
          f"是全年趋势中的异常点；")
    print(f"3. 11 月的缺口集中在 {prov.head(1)['province'].iloc[0]} 等少数省份，"
          f"其中 {prov.head(1)['province'].iloc[0]} 单省同比减少 "
          f"{abs(prov.head(1)['diff'].iloc[0]) / 1e4:.0f} 万元；")
    print("4. 建议：对上述省份做专项复盘（渠道/大客户流失/口径变更），"
          "并在 12 月预算中预留回补资源。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
