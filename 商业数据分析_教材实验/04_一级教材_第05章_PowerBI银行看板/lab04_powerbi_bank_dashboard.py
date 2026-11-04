# -*- coding: utf-8 -*-
"""
实验 04 · Power BI 银行理财产品经营看板：从 DAX 度量值到 pandas 聚合
====================================================================
教材：《CDA 一级认证教材：商业数据分析》第 5 章 业务数据分析 · Power BI 业务看板案例（银行）
原始素材：``银行案例数据 - 学员用.xlsx``（销售数据 440 行 × 11 列 + 3 张码表 + 1 张业务描述）
迁移方向：Power BI 星型模型 + DAX 度量值 + 切片器 + 卡片图/矩阵  →  pandas merge + 聚合函数 + matplotlib

教材的业务场景（业务描述工作表原文）：
    某分支行本月理财产品销售目标 **2500 万**，本月共 **31 天**，手上是 **29 日**的时点数据，
    机构负责人要在月底前判断"能不能完成、还差多少、靠哪些客群和品类补"。

Power BI 里的 5 个动作，本脚本逐个用 Python 复现：
    1. 维度表建模/关系        → ``merge`` 把 风险编号/品类编号/学历编号 翻译成中文名称
    2. DAX 度量值             → ``safe_div`` / ``kpi_metrics`` 等纯函数（SUM、DIVIDE、CALCULATE）
    3. 时间进度与线性外推      → 29/31 的进度、按当前日均外推月底
    4. 切片器/交互筛选        → 布尔过滤 + 函数参数（如只看 S2 中风险客群）
    5. 卡片图/矩阵/交叉表     → ``FancyBboxPatch`` 画 KPI 卡、``pivot_table`` 做矩阵、热力图

运行：``python lab04_powerbi_bank_dashboard.py``（在实验目录下执行）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# 让脚本能从仓库根的 common/ 导入统一样式
LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR.parent))

from common.style import (  # noqa: E402
    BLUE, BLUE2, GRAY, GREEN, NEG, ORANGE, PALETTE, POS, RED,
    apply_style, bar_labels, fmt_wan, money_axis, new_fig, pct_axis, save_csv, save_fig,
)

DATA = LAB_DIR / "data" / "银行案例数据 - 学员用.xlsx"
OUT = LAB_DIR / "outputs"

# 客群维度的固定展示顺序（不写死中文名，仅规定"排序"，名称仍来自码表）
AGE_ORDER = ["18-30岁", "31-40岁", "41-50岁", "50-60岁", "61岁以上"]
INCOME_ORDER = ["5万以下", "5万-10万", "10万-20万", "20万-50万", "50万-100万", "100万以上"]


# ---------------------------------------------------------------------------
# 0. 读工作簿：销售事实表 + 3 张维表 + 业务描述
# ---------------------------------------------------------------------------
def load_workbook() -> tuple[pd.DataFrame, dict]:
    """读取 Excel 的 5 张工作表，完成 Power BI 里的"建模"这一步。

    Power BI 的做法：把「销售数据」设为事实表，把三张说明表设为维度表，
    再在"模型"视图里拖关系（销售数据[风险编号] → 风险偏好说明表[风险编号]，1:*）。
    pandas 的做法：``merge`` 一条左连接，等价于在查询里把维表带进来。

    业务描述里的目标/天数/时点用正则提取，**不写死**，换一个月的数据也能跑。
    """
    sales = pd.read_excel(DATA, sheet_name="销售数据")
    risk = pd.read_excel(DATA, sheet_name="风险偏好说明表")
    cat = pd.read_excel(DATA, sheet_name="品类说明表")
    edu = pd.read_excel(DATA, sheet_name="学历说明表")
    desc = pd.read_excel(DATA, sheet_name="业务描述", header=None)

    # 业务描述工作表是「A1=业务背景、B1=整段说明」的版式，直接摊平所有非空单元格
    text = " ".join(str(v) for v in desc.values.ravel() if str(v) != "nan")
    target_wan = float(re.search(r"销售目标为\s*([\d.]+)\s*万", text).group(1))
    days_in_month = int(re.search(r"本月共\s*(\d+)\s*天", text).group(1))
    current_day = int(re.search(r"本月\s*(\d+)\s*日的时点数据", text).group(1))

    # ---- 维度表映射（对应 Power BI 的"关系"）----
    sales["风险说明"] = sales["风险编号"].map(dict(zip(risk["风险编号"], risk["风险说明"])))
    sales["品类名称"] = sales["品类编号"].map(dict(zip(cat["品类编号"], cat["品类名称"])))
    sales["学历名称"] = sales["学历编号"].map(dict(zip(edu["学历编号"], edu["学历名称"])))

    n_unmapped = int(sales[["风险说明", "品类名称", "学历名称"]].isna().sum().sum())
    print(f"[建模] 事实表 {sales.shape[0]} 行 × {sales.shape[1]} 列；"
          f"维表 3 张（风险 {len(risk)} / 品类 {len(cat)} / 学历 {len(edu)} 条）；"
          f"未匹配编码 {n_unmapped} 个")

    # ---- 数据质量检查（教材没写，但报表上线前必须做）----
    dup = int(sales.duplicated().sum())
    print(f"[质量] 重复行 {dup}；购买金额 {sales['购买金额'].min():,.0f} ~ "
          f"{sales['购买金额'].max():,.0f} 元；收益为负 {int((sales['收益'] < 0).sum())} 单"
          f"（高风险产品的实际亏损，保留不删）")

    meta = dict(
        target=target_wan * 10000,
        target_text=f"{target_wan:,.0f} 万",
        days_in_month=days_in_month,
        current_day=current_day,
        time_progress=current_day / days_in_month,
        desc=text,
    )
    print(f"[业务] 目标 {meta['target_text']}；本月 {days_in_month} 天，当前为第 "
          f"{current_day} 天；时间进度 {meta['time_progress']:.1%}")
    return sales, meta


# ---------------------------------------------------------------------------
# 1. KPI 度量值 —— DAX 的 DIVIDE / SUM / CALCULATE / 时间进度 / 线性外推
# ---------------------------------------------------------------------------
def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """DAX ``DIVIDE(分子, 分母)`` 的 Python 版：分母为 0 或空时返回默认值，不抛 ZeroDivisionError。"""
    if denominator is None or denominator == 0 or pd.isna(denominator):
        return default
    return numerator / denominator


def kpi_metrics(df: pd.DataFrame, meta: dict) -> dict:
    """一次算齐报表顶部 KPI 卡需要的 8 个度量值。

    对应 Power BI 里新建的度量值：
        销售额 = SUM(销售数据[购买金额])
        完成率 = DIVIDE([销售额], [目标])
        时间进度 = DIVIDE(DAY(今天), DAY(EOMONTH(今天, 0)))   -- 本案例用 29/31 代入
        缺口   = [目标] - [销售额]
        日均   = DIVIDE([销售额], [已过天数])
        月底外推 = [日均] * [本月天数]
    """
    sales = float(df["购买金额"].sum())
    target = float(meta["target"])
    days, today = meta["days_in_month"], meta["current_day"]

    metrics = {
        "销售额": sales,
        "目标": target,
        "完成率": safe_div(sales, target),
        "时间进度": safe_div(today, days),
        "缺口": target - sales,
        "日均销售额": safe_div(sales, today),
        "月底外推": safe_div(sales, today) * days,
        "外推达成率": safe_div(safe_div(sales, today) * days, target),
        "订单数": int(len(df)),
        "件均金额": safe_div(sales, len(df)),
        "剩余天数": days - today,
        "剩余日均需求": safe_div(target - sales, days - today),
    }
    # 完成率 - 时间进度 = "进度差"，>0 代表跑在时间前面
    metrics["进度差"] = metrics["完成率"] - metrics["时间进度"]

    print("\n== 1. KPI 度量值 ==")
    print(f"  销售额 {metrics['销售额']:,.0f} 元（{metrics['销售额'] / 1e4:,.1f} 万），"
          f"目标 {target / 1e4:,.0f} 万，完成率 {metrics['完成率']:.2%}")
    print(f"  时间进度 {today}/{days} = {metrics['时间进度']:.2%}，"
          f"进度差 {metrics['进度差']:+.2%}（{'领先' if metrics['进度差'] >= 0 else '落后'}时间）")
    print(f"  缺口 {metrics['缺口'] / 1e4:,.1f} 万；日均 {metrics['日均销售额'] / 1e4:,.2f} 万；"
          f"剩余 {metrics['剩余天数']} 天需日均 {metrics['剩余日均需求'] / 1e4:,.2f} 万")
    print(f"  按当前日均线性外推月底：{metrics['月底外推'] / 1e4:,.1f} 万，"
          f"预计达成率 {metrics['外推达成率']:.2%}")

    tbl = pd.DataFrame([{
        "销售额_元": round(metrics["销售额"], 2),
        "目标_元": metrics["目标"],
        "完成率": round(metrics["完成率"], 6),
        "时间进度": round(metrics["时间进度"], 6),
        "进度差": round(metrics["进度差"], 6),
        "缺口_元": round(metrics["缺口"], 2),
        "日均销售额_元": round(metrics["日均销售额"], 2),
        "月底线性外推_元": round(metrics["月底外推"], 2),
        "外推达成率": round(metrics["外推达成率"], 6),
        "订单笔数": metrics["订单数"],
        "件均金额_元": round(metrics["件均金额"], 2),
    }])
    save_csv(tbl, OUT, "table01_KPI度量值汇总")
    return metrics


def _card(ax, x, y, w, h, label, value, sub="", color=BLUE):
    """在给定 axes 上画一张 KPI 卡片（Power BI「卡片图」视觉对象的等价物）。

    用 ``FancyBboxPatch`` 画圆角底框，再叠三行文字：指标名 / 主数值 / 辅助说明。
    坐标用 ``transform=ax.transAxes``（0~1 相对坐标），这样换画布尺寸也不会错位。
    """
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.018",
        facecolor="#F5F8FC", edgecolor=color, linewidth=1.1,
        transform=ax.transAxes, zorder=2,
    ))
    ax.text(x + w / 2, y + h * 0.72, label, ha="center", va="center", fontsize=9.5,
            color="#5A6570", transform=ax.transAxes, zorder=3)
    ax.text(x + w / 2, y + h * 0.43, value, ha="center", va="center", fontsize=16.5,
            fontweight="bold", color=color, transform=ax.transAxes, zorder=3)
    if sub:
        ax.text(x + w / 2, y + h * 0.15, sub, ha="center", va="center", fontsize=8.2,
                color="#5A6570", transform=ax.transAxes, zorder=3)


def kpi_overview(df: pd.DataFrame, meta: dict, m: dict) -> None:
    """fig01：KPI 卡片区 + 完成率 vs 时间进度 vs 月底外推的进度对比。"""
    fig, ax = new_fig(12.6, 5.0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.grid(False)

    cards = [
        ("销售额", f"{m['销售额'] / 1e4:,.1f} 万", f"{m['订单数']} 笔成交", BLUE),
        ("本月目标", f"{m['目标'] / 1e4:,.0f} 万", "业务描述给定", GRAY),
        ("完成率", f"{m['完成率']:.1%}", f"进度差 {m['进度差']:+.1%}", ORANGE),
        ("时间进度", f"{m['时间进度']:.1%}", f"{meta['current_day']}/{meta['days_in_month']} 天", BLUE2),
        ("缺口", f"{m['缺口'] / 1e4:,.1f} 万", "剩余 2 天", RED),
        ("月底外推", f"{m['月底外推'] / 1e4:,.1f} 万", f"预计 {m['外推达成率']:.1%}", GREEN),
    ]
    n = len(cards)
    w, gap = 0.148, 0.022
    x0 = (1 - (n * w + (n - 1) * gap)) / 2
    for i, (label, value, sub, color) in enumerate(cards):
        _card(ax, x0 + i * (w + gap), 0.62, w, 0.30, label, value, sub, color)

    # ---- 下半部分：三条进度条（完成率 / 时间进度 / 外推），共用 0~110% 刻度 ----
    left, scale = 0.26, 0.52 / 1.10          # 1.10 表示 110% 占满进度条区
    rows = [
        ("完成率", m["完成率"], ORANGE, 0.36),
        ("时间进度", m["时间进度"], BLUE2, 0.22),
        ("月底外推", m["外推达成率"], GREEN, 0.08),
    ]
    ax.text(0.02, 0.47, "进度对比", fontsize=11.5, fontweight="bold", color="#333333")
    # 100% 目标线
    target_x = left + scale * 1.0
    ax.plot([target_x, target_x], [0.03, 0.46], color=RED, linestyle="--", linewidth=1.2, zorder=1)
    ax.text(target_x, 0.475, "目标 100%", ha="center", va="bottom", fontsize=9, color=RED)

    for label, value, color, y in rows:
        ax.text(0.02, y, label, fontsize=10, color="#333333", va="center")
        ax.barh(y, scale * value, left=left, height=0.08, color=color, zorder=3)
        # 数值写在柱子内部右端（白色、垂直居中），避免和 100% 目标虚线叠字
        ax.text(left + scale * value - 0.006, y, f"{value:.1%}",
                ha="right", va="center", fontsize=10, fontweight="bold",
                color="white", zorder=4)
    ax.text(0.02, 0.015, "注：进度条刻度 0~110%，红色虚线为 100% 目标线；"
                         "月底外推 = 当前日均 × 本月天数（线性假设）。",
            fontsize=8.5, color="#6B7580")
    ax.set_title(
        f"KPI 总览：销售额 {m['销售额'] / 1e4:,.0f} 万、完成 {m['完成率']:.1%}，"
        f"时间已过 {m['时间进度']:.1%}，月底线性外推 {m['月底外推'] / 1e4:,.0f} 万"
        f"（{m['外推达成率']:.1%}）", pad=14)
    save_fig(fig, OUT, "fig01_KPI经营总览")


# ---------------------------------------------------------------------------
# 2. 品类结构 —— 矩阵表 + 帕累托（Power BI 的簇状条形图 + 累计线）
# ---------------------------------------------------------------------------
def category_structure(df: pd.DataFrame, m: dict) -> pd.DataFrame:
    """10 个品类按销售额排序，算占比与累计占比，回答"主力品类是谁"。"""
    g = (
        df.groupby("品类名称", as_index=False)
        .agg(销售额=("购买金额", "sum"), 笔数=("购买金额", "size"), 件均金额=("购买金额", "mean"))
        .sort_values("销售额", ascending=False)
        .reset_index(drop=True)
    )
    g["占比"] = g["销售额"] / g["销售额"].sum()
    g["累计占比"] = g["占比"].cumsum()
    top3 = g.head(3)

    print("\n== 2. 品类结构 ==")
    for r in g.itertuples():
        print(f"  {r.品类名称:<8} 销售额 {r.销售额 / 1e4:>7,.1f} 万  占比 {r.占比:>6.1%}  "
              f"{r.笔数:>3} 笔  件均 {r.件均金额:,.0f} 元")
    print(f"  前 3 品类合计占 {top3['占比'].sum():.1%}，"
          f"最大单品「{top3.iloc[0]['品类名称']}」占 {top3.iloc[0]['占比']:.1%}")

    fig, ax = new_fig(9.6, 5.2)
    x = np.arange(len(g))
    colors = [ORANGE if i < 3 else BLUE2 for i in range(len(g))]
    ax.bar(x, g["销售额"] / 1e4, color=colors, width=0.64, zorder=3)
    # 金额/占比写在柱子内部顶端（白色），累计折线从柱顶掠过，两者互不遮挡
    for xi, v, s in zip(x, g["销售额"] / 1e4, g["占比"]):
        ax.annotate(f"{v:,.0f}万\n{s:.1%}", (xi, v), xytext=(0, -10), textcoords="offset points",
                    ha="center", va="top", fontsize=8.2, color="white",
                    fontweight="bold", zorder=4)
    ax.set_xticks(x, g["品类名称"], rotation=28, ha="right", fontsize=9)
    ax.set_ylabel("销售额（万元）")
    ax.set_ylim(0, g["销售额"].max() / 1e4 * 1.30)

    ax2 = ax.twinx()
    ax2.plot(x, g["累计占比"], color=GRAY, marker="D", markersize=4.5,
             linewidth=1.8, linestyle="--", zorder=5)
    for i, (xi, v) in enumerate(zip(x, g["累计占比"])):
        # 累计折线紧贴柱子生长，全量标注必然叠字：每 3 根标一次，末点必标
        if i % 3 != 0 and i != len(x) - 1:
            continue
        ax2.annotate(f"{v:.0%}", (xi, v), xytext=(0, 9), textcoords="offset points",
                     ha="center", fontsize=8, color="#3D464F", fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.92))
    ax2.set_ylim(0, 1.18)
    ax2.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax2.set_ylabel("累计占比", color=GRAY)
    ax2.grid(False)
    ax.set_title("品类结构：银行理财产品为第一主力，10 类分布相对均衡", pad=12)
    save_fig(fig, OUT, "fig02_品类结构与帕累托")
    save_csv(g, OUT, "table02_品类结构汇总")
    return g


# ---------------------------------------------------------------------------
# 3. 风险偏好 × 品类 —— 矩阵/热力图（Power BI 的"矩阵"视觉对象）
# ---------------------------------------------------------------------------
def risk_category_matrix(df: pd.DataFrame, m: dict) -> pd.DataFrame:
    """行=风险偏好，列=品类，值=销售额；同时看"每类风险的钱花在哪"。

    Power BI 用两行矩阵：一个放销售额，一个放"占本行合计的百分比"。
    这里把两个口径合成一张热力图：底色是销售额，标注是行内占比。
    """
    pv = df.pivot_table(index="风险说明", columns="品类名称", values="购买金额",
                        aggfunc="sum", fill_value=0.0)
    # 风险等级按编号 S1/S2/S3 排序，而不是按字母
    order = (df[["风险编号", "风险说明"]].drop_duplicates()
             .sort_values("风险编号")["风险说明"].tolist())
    pv = pv.reindex(order)
    # 列按总销售额降序，和 fig02 的顺序保持一致
    pv = pv[[c for c in pv.sum().sort_values(ascending=False).index]]
    row_share = pv.div(pv.sum(axis=1), axis=0)
    pv_out = pv.copy()
    pv_out.insert(0, "风险合计_万元", (pv.sum(axis=1) / 1e4).round(2))
    pv_out["占总额"] = (pv.sum(axis=1) / pv.values.sum()).round(6)

    print("\n== 3. 风险偏好 × 品类 ==")
    s2_amount_share = pv.loc["中风险中收益"].sum() / pv.values.sum()
    print(f"  S2 中风险贡献 {s2_amount_share:.1%} 的销售额、"
          f"{(df['风险编号'] == 'S2').mean():.1%} 的笔数，是绝对主力客群")
    for r in order:
        top_cat = row_share.loc[r].idxmax()
        print(f"  {r}：合计 {pv.loc[r].sum() / 1e4:>7,.1f} 万，"
              f"最偏好的品类是「{top_cat}」（占本类 {row_share.loc[r, top_cat]:.1%}）")

    fig, ax = new_fig(11.2, 4.6)
    data = pv.values / 1e4
    im = ax.imshow(data, cmap="Blues", aspect="auto")
    ax.set_xticks(np.arange(pv.shape[1]), pv.columns, rotation=32, ha="right", fontsize=9)
    ax.set_yticks(np.arange(pv.shape[0]), pv.index, fontsize=10)
    ax.grid(False)
    # 数值标注：金额（万）+ 行内占比
    vmax = data.max()
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            dark = data[i, j] > vmax * 0.55
            ax.text(j, i, f"{data[i, j]:,.0f}\n{row_share.values[i, j]:.0%}",
                    ha="center", va="center", fontsize=8,
                    color="white" if dark else "#1F2D3D")
    ax.set_title("风险偏好 × 品类矩阵：底色=销售额（万元），标注=该风险等级内的占比", pad=12)
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015)
    cbar.set_label("销售额（万元）", fontsize=9)
    save_fig(fig, OUT, "fig03_风险偏好品类矩阵")
    save_csv(pv_out.reset_index(), OUT, "table03_风险偏好品类矩阵")
    return pv_out


# ---------------------------------------------------------------------------
# 4. 客群画像 —— 年龄 / 性别 / 学历 / 家庭年收入（Power BI 的四个切片器维度）
# ---------------------------------------------------------------------------
def customer_profile(df: pd.DataFrame, m: dict) -> pd.DataFrame:
    """四个客群维度的销售额、占比、件均金额。

    教材看板里用四个切片器切同一套度量值；Python 里把它做成"一张长表 + 四联图"，
    好处是一次跑完四个维度，还能直接比较"谁的人多、谁的钱多、谁的单笔大"。
    """
    rows = []
    for dim, order in [("年龄", AGE_ORDER), ("性别", None),
                       ("学历名称", None), ("家庭年收入", INCOME_ORDER)]:
        g = (df.groupby(dim, as_index=False)
             .agg(销售额=("购买金额", "sum"), 笔数=("购买金额", "size"),
                  件均金额=("购买金额", "mean")))
        g["占比"] = g["销售额"] / g["销售额"].sum()
        if order:
            g["__o"] = g[dim].map({v: i for i, v in enumerate(order)})
            g = g.sort_values("__o").drop(columns="__o")
        else:
            g = g.sort_values("销售额", ascending=False)
        g.insert(0, "维度", dim)
        rows.append(g.rename(columns={dim: "取值"}))
    profile = pd.concat(rows, ignore_index=True)
    profile["销售额"] = profile["销售额"].round(2)
    profile["件均金额"] = profile["件均金额"].round(2)
    profile["占比"] = profile["占比"].round(6)

    print("\n== 4. 客群画像 ==")
    for dim in ["年龄", "性别", "学历名称", "家庭年收入"]:
        sub = profile[profile["维度"] == dim].sort_values("销售额", ascending=False)
        top = sub.iloc[0]
        print(f"  {dim}：{top['取值']} 贡献最高（{top['销售额'] / 1e4:,.1f} 万，"
              f"占 {top['占比']:.1%}，{int(top['笔数'])} 笔，"
              f"件均 {top['件均金额']:,.0f} 元）")

    fig, axes = new_fig(13.0, 7.4, nrows=2, ncols=2)
    fig.subplots_adjust(hspace=0.55, wspace=0.30)
    panels = [
        ("年龄", "年龄段", "31—50 岁贡献 78.8% 销售额", BLUE),
        ("性别", "性别", "男女金额接近，女性笔数略多", ORANGE),
        ("学历名称", "学历", "本科占一半，博士件均最高", BLUE2),
        ("家庭年收入", "家庭年收入", "10 万—20 万客群贡献近半", GREEN),
    ]
    for ax, (dim, title, note, color) in zip(axes.ravel(), panels):
        sub = profile[profile["维度"] == dim].copy()
        sub = sub.sort_values("销售额", ascending=True)      # 条形图从下往上画
        y = np.arange(len(sub))
        bars = ax.barh(y, sub["销售额"] / 1e4, color=color, height=0.62, zorder=3, alpha=0.88)
        for yi, v, share, cnt, avg in zip(y, sub["销售额"] / 1e4, sub["占比"],
                                         sub["笔数"], sub["件均金额"]):
            ax.annotate(f"{v:,.0f}万 · {share:.0%} · {int(cnt)}笔 · 件均{avg / 1e4:.1f}万",
                        (v, yi), xytext=(5, 0), textcoords="offset points",
                        va="center", fontsize=8, color="#333333")
        ax.set_yticks(y, sub["取值"], fontsize=9)
        ax.set_xlim(0, (sub["销售额"].max() / 1e4) * 1.62)
        ax.set_xlabel("销售额（万元）")
        ax.set_title(f"{title}｜{note}", pad=8, fontsize=11.5)
        ax.grid(axis="y", visible=False)
    fig.suptitle("客群画像四维对比：人多的不等于钱多的，件均要靠「高学历 + 高龄」拉",
                 y=1.00, fontsize=13.5, fontweight="bold")
    save_fig(fig, OUT, "fig04_客群画像四维对比")
    save_csv(profile, OUT, "table04_客群画像汇总")
    return profile


# ---------------------------------------------------------------------------
# 5. 购买目的 / 选择本行的原因 —— 排行（Power BI 的排序条形图）
# ---------------------------------------------------------------------------
def purpose_reason(df: pd.DataFrame, m: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """两个"动机类"维度的金额排行，用来指导话术与产品推荐。"""
    def rank(dim: str) -> pd.DataFrame:
        g = (df.groupby(dim, as_index=False)
             .agg(销售额=("购买金额", "sum"), 笔数=("购买金额", "size"),
                  件均金额=("购买金额", "mean"))
             .sort_values("销售额", ascending=False).reset_index(drop=True))
        g["占比"] = g["销售额"] / g["销售额"].sum()
        return g

    pur = rank("购买目的")
    rea = rank("选择本行的原因")

    print("\n== 5. 购买目的 / 选择本行的原因 ==")
    for name, g in [("购买目的", pur), ("选择本行的原因", rea)]:
        col = g.columns[0]
        print(f"  {name} TOP3：" + "；".join(
            f"{r[col]} {r['销售额'] / 1e4:.1f}万" for _, r in g.head(3).iterrows()))

    fig, axes = new_fig(12.4, 5.0, ncols=2)
    fig.subplots_adjust(wspace=0.42)
    goal_share = pur[pur["购买目的"].str.contains("保值增值|资金")]["占比"].sum()
    for ax, (g, dim, color, title) in zip(axes, [
        (pur, "购买目的", BLUE, f"购买目的：保值增值 + 资金安排类合计 {goal_share:.1%}"),
        (rea, "选择本行的原因", ORANGE, "选择本行：收益率是第一理由（过半客户）"),
    ]):
        gg = g.sort_values("销售额")           # 横向条形从下往上
        y = np.arange(len(gg))
        ax.barh(y, gg["销售额"] / 1e4, color=color, height=0.62, zorder=3, alpha=0.9)
        for yi, v, cnt, avg in zip(y, gg["销售额"] / 1e4, gg["笔数"], gg["件均金额"]):
            ax.annotate(f"{v:,.0f}万｜{int(cnt)}笔\n件均 {avg / 1e4:.1f} 万",
                        (v, yi), xytext=(5, 0), textcoords="offset points",
                        va="center", fontsize=7.8, color="#333333")
        ax.set_yticks(y, gg[dim], fontsize=9)
        ax.set_xlim(0, gg["销售额"].max() / 1e4 * 1.42)
        ax.set_xlabel("销售额（万元）")
        ax.set_title(title, pad=10, fontsize=11.5)
        ax.grid(axis="y", visible=False)
    save_fig(fig, OUT, "fig05_购买目的与选择原因")
    save_csv(pur, OUT, "table05_购买目的排行")
    save_csv(rea, OUT, "table06_选择本行原因排行")
    return pur, rea


# ---------------------------------------------------------------------------
# 6. 期限结构 & 收益与金额的关系
# ---------------------------------------------------------------------------
def term_and_return(df: pd.DataFrame, m: dict) -> pd.DataFrame:
    """期限 1—5 年的金额结构，以及"买得多是不是赚得多"。

    这里要小心：``收益`` 是**持有期总收益金额**，不是年化收益率。
    42 单负收益（9.5%）分散在 S1/S2/S3 三个风险等级上，其中 S1 低风险还有 18 单亏损，
    与"低风险低收益"的业务定义相矛盾 —— 这是需要向数据源核实的口径问题，
    做报表时既不能当成脏数据直接删，也不能不提示。
    """
    term = (df.groupby("期限", as_index=False)
            .agg(销售额=("购买金额", "sum"), 笔数=("购买金额", "size"),
                 件均金额=("购买金额", "mean"), 平均收益=("收益", "mean")))
    term["占比"] = term["销售额"] / term["销售额"].sum()
    term["收益率均值"] = term["平均收益"] / term["件均金额"]

    neg = df[df["收益"] < 0]
    df = df.copy()
    df["收益率"] = df["收益"] / df["购买金额"]
    corr = df[["购买金额", "收益", "期限", "收益率"]].corr()

    print("\n== 6. 期限结构与收益 ==")
    print(f"  期限 1—5 年占比：" + "、".join(
        f"{int(r.期限)}年 {r.占比:.1%}" for r in term.itertuples()))
    neg_by_risk = neg.groupby("风险编号").size().to_dict()
    print(f"  负收益 {len(neg)} 单（{len(neg) / len(df):.1%}），按风险等级分布 "
          + "、".join(f"{k} {v} 单" for k, v in sorted(neg_by_risk.items()))
          + f"；件均亏损 {neg['收益'].mean():,.0f} 元")
    print("  注意：S1 是「低风险低收益」，却也出现 "
          f"{neg_by_risk.get('S1', 0)} 单亏损，收益字段口径需向数据源核实")
    print(f"  购买金额与收益的相关系数 {corr.loc['购买金额', '收益']:+.3f}"
          f"（几乎无关：金额大不等于收益高，关键看品类与风险）")

    fig, axes = new_fig(13.0, 5.0, ncols=2)
    fig.subplots_adjust(wspace=0.52)
    ax = axes[0]
    x = term["期限"].astype(int)
    ax.bar(x, term["销售额"] / 1e4, color=[BLUE2] * len(term), width=0.6, zorder=3)
    bar_labels(ax, fmt="{:.0f}万", fontsize=9)
    ax.set_xticks(x, [f"{v}年" for v in x])
    ax.set_xlabel("产品期限")
    ax.set_ylabel("销售额（万元）")
    ax.set_ylim(0, term["销售额"].max() / 1e4 * 1.22)

    ax2 = ax.twinx()
    ax2.plot(x, term["占比"], color=ORANGE, marker="o", linewidth=2, zorder=5)
    for xi, v in zip(x, term["占比"]):
        ax2.annotate(f"{v:.1%}", (xi, v), xytext=(0, 9), textcoords="offset points",
                     ha="center", fontsize=8.5, color=ORANGE, fontweight="bold")
    ax2.set_ylim(0, term["占比"].max() * 1.6)
    ax2.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax2.set_ylabel("占比", color=ORANGE)
    ax2.grid(False)
    ax.set_title("期限结构：5 年期占比最高，各期限分布较均衡", pad=12, fontsize=11.5)

    # 右图：购买金额 vs 收益，按风险等级着色，负收益区域标灰
    ax = axes[1]
    # 颜色按风险编号 S1→低、S2→中、S3→高 固定映射（蓝=低、橙=中、红=高）
    code_of = dict(zip(df["风险说明"], df["风险编号"]))
    code_color = {"S1": BLUE2, "S2": ORANGE, "S3": RED}
    order = sorted(df["风险说明"].unique(), key=lambda r: code_of[r])
    for r in order:
        sub = df[df["风险说明"] == r]
        ax.scatter(sub["购买金额"] / 1e4, sub["收益"] / 1e4, s=26, alpha=0.65,
                   color=code_color[code_of[r]], label=f"{r}（{len(sub)} 单）", edgecolors="none")
    ax.axhline(0, color="#555555", linestyle="--", linewidth=1)
    ax.fill_between([0, 11], -1.2, 0, color=NEG, alpha=0.07, zorder=0)
    ax.set_xlim(0, 11)
    ax.set_ylim(-1.2, 4.6)
    ax.set_xlabel("购买金额（万元）")
    ax.set_ylabel("收益（万元）")
    ax.legend(loc="upper left", fontsize=8.5)
    ax.annotate(f"{len(neg)} 单负收益（亏损区）", xy=(1.0, -0.55), fontsize=9, color=NEG)
    ax.set_title("金额与收益：散点呈「竖条」状，收益与金额几乎无关", pad=12, fontsize=11.5)
    save_fig(fig, OUT, "fig06_期限结构与收益分布")
    save_csv(term, OUT, "table07_期限结构汇总")
    return term


# ---------------------------------------------------------------------------
# 7. 经营看板大图 —— Power BI 单页报表的等价物（2×3 面板 + KPI 卡带）
# ---------------------------------------------------------------------------
def dashboard(df: pd.DataFrame, meta: dict, m: dict) -> None:
    """把前 6 节的核心图浓缩到一张 2×3 的"经营看板"。

    版式对应 Power BI 报表页：
        顶部 KPI 卡带（6 张卡片）
        ├─ 完成率进度（子弹图）   ├─ 品类 TOP6          ├─ 风险×品类热力
        ├─ 年龄段金额             ├─ 期限金额           └─ 金额 vs 收益散点
    KPI 卡用 ``fig.text`` + ``FancyBboxPatch`` 画在 figure 坐标上，
    所以它可以横跨所有子图，不受 3 列网格限制。
    """
    fig, axes = new_fig(16.2, 9.6, nrows=2, ncols=3)
    fig.subplots_adjust(top=0.775, bottom=0.085, left=0.055, right=0.975,
                        hspace=0.58, wspace=0.30)

    # ---------- 顶部 KPI 卡带 ----------
    cards = [
        ("销售额", f"{m['销售额'] / 1e4:,.1f} 万", f"{m['订单数']} 笔", BLUE),
        ("目标", f"{m['目标'] / 1e4:,.0f} 万", "本月", GRAY),
        ("完成率", f"{m['完成率']:.1%}", f"进度差 {m['进度差']:+.1%}", ORANGE),
        ("时间进度", f"{m['时间进度']:.1%}", f"{meta['current_day']}/{meta['days_in_month']} 天", BLUE2),
        ("缺口", f"{m['缺口'] / 1e4:,.1f} 万", "剩 2 天", RED),
        ("月底外推", f"{m['月底外推'] / 1e4:,.1f} 万", f"预计 {m['外推达成率']:.1%}", GREEN),
    ]
    n = len(cards)
    w, gap = 0.144, 0.017
    x0 = (1 - (n * w + (n - 1) * gap)) / 2
    for i, (label, value, sub, color) in enumerate(cards):
        x = x0 + i * (w + gap)
        fig.patches.append(FancyBboxPatch(
            (x, 0.825), w, 0.105, boxstyle="round,pad=0.004,rounding_size=0.012",
            facecolor="#F5F8FC", edgecolor=color, linewidth=1.1,
            transform=fig.transFigure, zorder=2,
        ))
        fig.text(x + w / 2, 0.906, label, ha="center", va="center", fontsize=9, color="#5A6570")
        fig.text(x + w / 2, 0.873, value, ha="center", va="center", fontsize=15,
                 fontweight="bold", color=color)
        fig.text(x + w / 2, 0.842, sub, ha="center", va="center", fontsize=7.8, color="#5A6570")
    fig.text(0.012, 0.962, f"银行理财产品销售经营看板（截至本月 {meta['current_day']} 日）",
             fontsize=17, fontweight="bold", color="#1F2D3D", va="center")
    fig.text(0.988, 0.962, f"数据：{m['订单数']} 笔成交 · 分支行本月目标 "
                           f"{m['目标'] / 1e4:,.0f} 万", fontsize=9,
             color="#6B7580", ha="right", va="center")

    # ---------- [0,0] 完成率子弹图 ----------
    ax = axes[0, 0]
    ax.set_xlim(0, 1.15)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.barh(0.55, 1.0, height=0.22, color="#E8EEF5", zorder=2)
    ax.barh(0.55, m["完成率"], height=0.22, color=ORANGE, zorder=3)
    ax.plot([1, 1], [0.40, 0.70], color=RED, linewidth=1.6, zorder=4)
    ax.plot([m["月底外推"] / m["目标"]] * 2, [0.36, 0.74], color=GREEN,
            linestyle="--", linewidth=1.4, zorder=4)
    ax.text(m["完成率"] / 2, 0.55, f"完成率 {m['完成率']:.1%}", ha="center", va="center",
            color="white", fontsize=10, fontweight="bold", zorder=5)
    ax.text(0.40, 0.80, f"已卖 {m['销售额'] / 1e4:,.0f} 万", ha="center",
            fontsize=8.5, color=ORANGE)
    ax.text(1.0, 0.28, "目标 100%", ha="center", fontsize=8, color=RED)
    ax.text(m["月底外推"] / m["目标"] + 0.01, 0.14, f"外推 {m['外推达成率']:.1%}",
            ha="center", fontsize=8, color=GREEN)
    ax.text(m["时间进度"], 0.93, "时间进度 93.5%", ha="center", fontsize=8.5, color=BLUE2)
    ax.axvline(m["时间进度"], ymin=0.18, ymax=0.88, color=BLUE2, linestyle=":", linewidth=1.2)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_title("① 完成率 vs 目标 vs 时间进度", fontsize=11, pad=8)
    ax.grid(axis="y", visible=False)

    # ---------- [0,1] 品类 TOP6 ----------
    ax = axes[0, 1]
    top = (df.groupby("品类名称")["购买金额"].sum().sort_values(ascending=False)
           .head(6).sort_values())
    ax.barh(np.arange(len(top)), top.values / 1e4, color=BLUE2, height=0.6, zorder=3)
    for yi, v in zip(range(len(top)), top.values / 1e4):
        ax.annotate(f"{v:,.0f}万", (v, yi), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8, color="#333333")
    ax.set_yticks(np.arange(len(top)), top.index, fontsize=8.8)
    ax.set_xlim(0, top.max() / 1e4 * 1.35)
    ax.set_title("② 品类销售额 TOP6（万元）", fontsize=11, pad=8)
    ax.grid(axis="y", visible=False)

    # ---------- [0,2] 风险 × 品类热力（缩略版） ----------
    ax = axes[0, 2]
    pv = df.pivot_table(index="风险说明", columns="品类名称", values="购买金额",
                        aggfunc="sum", fill_value=0.0)
    order = (df[["风险编号", "风险说明"]].drop_duplicates()
             .sort_values("风险编号")["风险说明"].tolist())
    pv = pv.reindex(order)
    pv = pv[[c for c in pv.sum().sort_values(ascending=False).index]]
    im = ax.imshow(pv.values / 1e4, cmap="Blues", aspect="auto")
    ax.set_xticks(np.arange(pv.shape[1]), pv.columns, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(np.arange(pv.shape[0]), ["S1 低", "S2 中", "S3 高"], fontsize=8.5)
    ax.grid(False)
    for i in range(pv.shape[0]):
        for j in range(pv.shape[1]):
            dark = pv.values[i, j] / 1e4 > (pv.values / 1e4).max() * 0.55
            ax.text(j, i, f"{pv.values[i, j] / 1e4:,.0f}", ha="center", va="center",
                    fontsize=6.5, color="white" if dark else "#1F2D3D")
    ax.set_title("③ 风险偏好 × 品类（万元）", fontsize=11, pad=8)

    # ---------- [1,0] 年龄段 ----------
    ax = axes[1, 0]
    age = (df.groupby("年龄")["购买金额"].sum()
           .reindex([a for a in AGE_ORDER if a in set(df["年龄"])]))
    ax.bar(np.arange(len(age)), age.values / 1e4, color=[BLUE if i < 2 else BLUE2
                                                          for i in range(len(age))],
           width=0.62, zorder=3)
    bar_labels(ax, fmt="{:.0f}", fontsize=8)
    ax.set_xticks(np.arange(len(age)), age.index, rotation=18, fontsize=8.5)
    ax.set_ylim(0, age.max() / 1e4 * 1.25)
    ax.set_ylabel("销售额（万元）")
    ax.set_title("④ 年龄段销售额：31—50 岁占 78.8%", fontsize=11, pad=8)

    # ---------- [1,1] 期限 ----------
    ax = axes[1, 1]
    term = df.groupby("期限")["购买金额"].sum()
    ax.bar([f"{int(v)}年" for v in term.index], term.values / 1e4,
           color=[ORANGE if v == term.max() else BLUE2 for v in term.values],
           width=0.62, zorder=3)
    bar_labels(ax, fmt="{:.0f}", fontsize=8)
    ax.set_ylim(0, term.max() / 1e4 * 1.25)
    ax.set_ylabel("销售额（万元）")
    ax.set_title("⑤ 期限结构：5 年期最高（23.2%）", fontsize=11, pad=8)

    # ---------- [1,2] 金额 vs 收益 ----------
    ax = axes[1, 2]
    code_of = dict(zip(df["风险说明"], df["风险编号"]))
    code_color = {"S1": BLUE2, "S2": ORANGE, "S3": RED}
    for r in sorted(df["风险说明"].unique(), key=lambda r: code_of[r]):
        sub = df[df["风险说明"] == r]
        ax.scatter(sub["购买金额"] / 1e4, sub["收益"] / 1e4, s=16, alpha=0.6,
                   color=code_color[code_of[r]], edgecolors="none")
    ax.axhline(0, color="#555555", linestyle="--", linewidth=0.9)
    ax.set_xlim(0, 11)
    ax.set_ylim(-1.2, 4.6)
    ax.set_xlabel("购买金额（万元）", fontsize=9)
    ax.set_ylabel("收益（万元）", fontsize=9)
    ax.set_title("⑥ 金额 vs 收益：42 单负收益，S1 低风险也有 18 单", fontsize=11, pad=8)

    fig.text(0.055, 0.018,
             f"读图顺序：① 目标达成风险 → ② 靠哪些品类补 → ③ 哪类风险客群贡献最大 → "
             f"④~⑥ 客群/期限/收益结构；结论：缺口 {m['缺口'] / 1e4:,.1f} 万，"
             f"按当前日均 {m['日均销售额'] / 1e4:,.1f} 万算，剩余 {m['剩余天数']} 天只需 "
             f"{m['剩余日均需求'] / 1e4:,.1f} 万/天即可达成。",
             fontsize=8.8, color="#4A5560")
    save_fig(fig, OUT, "fig07_银行经营看板大图")


# ---------------------------------------------------------------------------
def main() -> None:
    apply_style()
    df, meta = load_workbook()
    m = kpi_metrics(df, meta)
    kpi_overview(df, meta, m)
    cat = category_structure(df, m)
    risk_cat = risk_category_matrix(df, m)
    profile = customer_profile(df, m)
    pur, rea = purpose_reason(df, m)
    term = term_and_return(df, m)
    dashboard(df, meta, m)

    # ---- 汇总几条可以直接写进分析报告的业务结论 ----
    s2_share = df.loc[df["风险编号"] == "S2", "购买金额"].sum() / m["销售额"]
    print("\n" + "=" * 66)
    print("业务结论（可直接用于报告）")
    print("=" * 66)
    print(f"1. 截至第 {meta['current_day']} 天，销售额 {m['销售额'] / 1e4:,.1f} 万，"
          f"完成率 {m['完成率']:.1%}，比时间进度（{m['时间进度']:.1%}）"
          f"高 {m['进度差']:.1%}；按当前日均 {m['日均销售额'] / 1e4:.1f} 万外推月底 "
          f"{m['月底外推'] / 1e4:,.1f} 万，预计达成率 {m['外推达成率']:.1%}，属于险过。")
    print(f"2. 品类集中度不高：第一主力「{cat.iloc[0]['品类名称']}」占 "
          f"{cat.iloc[0]['占比']:.1%}，前 3 类合计 {cat.head(3)['占比'].sum():.1%}；"
          f"客群上 S2 中风险贡献 {s2_share:.1%}，31—50 岁贡献 "
          f"{profile[(profile['维度'] == '年龄') & (profile['取值'].isin(['31-40岁', '41-50岁']))]['占比'].sum():.1%}。")
    print(f"3. 选择本行的首要原因是「{rea.iloc[0]['选择本行的原因']}」（{int(rea.iloc[0]['笔数'])} 笔，"
          f"占 {rea.iloc[0]['占比']:.1%}），说明本月成交高度依赖收益率驱动；"
          f"期限 5 年占 {term.loc[term['期限'] == term['期限'].max(), '占比'].iloc[0]:.1%}，"
          f"负收益 42 单里有 18 单是 S1「低风险」产品，收益口径需要核实。")
    print("4. 建议：剩余 2 天优先向 S2 中风险客群的「银行存款/理财」品类追加额度；"
          "对 S3 亏损客户单独做回访，避免月底冲量时口碑反噬。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
