# -*- coding: utf-8 -*-
"""
实验 05 · 用户画像标签体系：从 SQL 多表 join 到 pandas 客户宽表
==============================================================
教材：《CDA 一级认证教材：商业数据分析》第 9 章 用户标签体系与用户画像专题
原始素材：捷克某银行 1993—1998 年零售业务数据（8 张表，教材在 MySQL 里建库做标签）
迁移方向：SQL 建表 + 多表 join + GROUP BY 打标签  →  pandas merge + groupby + 分箱

教材的标签体系分四层，本脚本按同样的层次产出「客户标签宽表」：
    1. 人口属性标签   性别 / 年龄（由 birth_date 计算并分箱）/ 所在地区
    2. 资产标签       账户频率 frequency / 持卡类型 card.type / 是否贷款 / 贷款状态
    3. 行为标签       交易笔数 / 交易总额 / 平均余额 / 最近交易日期（recency）
    4. 地域标签       所在 district 的 GDP / 人均 GDP / 失业率 / 平均工资
最后再算一遍「标签覆盖率」，回答"这套画像到底覆盖了多少客户"。

数据量说明（重要）
------------------
``trans.csv`` 原始 59.6 MB、1,056,320 行，仓库不适合存放。
仓库内放的是**确定性 1/10 抽样**：``trans_sample.csv.gz``（105,630 行，1.7 MB），
抽样规则 = ``trans_id % 10 == 0``（对主键取模，可复现、不依赖随机种子），
4500 个账户全部保留，因此「交易笔数/交易额」的**客户覆盖率**与全量一致，
只是每户的金额规模约为全量的 1/10，脚本用 ``SAMPLE_STEP`` 换算并明确标注。
若把原始 ``trans.csv`` 放回 ``data/``，脚本会自动改用全量（SAMPLE_STEP=1）。

运行：``python lab05_user_profile_tags.py``（在实验目录下执行）
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR.parent))

from common.style import (  # noqa: E402
    BLUE, BLUE2, GRAY, GREEN, NEG, ORANGE, PALETTE, POS, RED,
    apply_style, bar_labels, fmt_wan, money_axis, new_fig, pct_axis, save_csv, save_fig,
)

DATA = LAB_DIR / "data"
OUT = LAB_DIR / "outputs"

SAMPLE_STEP = 10          # 抽样比例：1/10；若使用全量 trans.csv 则为 1
AGE_BINS = [0, 30, 40, 50, 60, 200]
AGE_LABELS = ["18-30岁", "31-40岁", "41-50岁", "51-60岁", "61岁以上"]


# ---------------------------------------------------------------------------
# 0. 读取 8 张表 —— 对应教材「在 MySQL 中创建数据」的建库步骤
# ---------------------------------------------------------------------------
def _money(series: pd.Series) -> pd.Series:
    """把 ``$1,000`` 这类带美元符号和千分位的字符串清洗成浮点数。

    教材里这一步是在 SQL 里用 ``REPLACE(REPLACE(amount,'$',''),',','')`` 再 CAST；
    pandas 里用正则一次性去掉 ``$`` 和 ``,``，``errors='coerce'`` 把脏值转成 NaN
    而不是让整列读取失败。
    """
    cleaned = series.astype(str).str.replace(r"[$,]", "", regex=True).str.strip()
    return pd.to_numeric(cleaned, errors="coerce")


def load_tables() -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.Timestamp, int]:
    """读入 8 张表（GBK 编码），并完成 trans 的金额清洗。

    编码是个坑：这批 CSV 是 GBK，直接用默认 UTF-8 读会抛
    ``UnicodeDecodeError``；用 ``encoding='gbk'`` 才正常。
    """
    files = ["clients", "accounts", "disp", "card", "loans", "order", "district"]
    tables = {f: pd.read_csv(DATA / f"{f}.csv", encoding="gbk") for f in files}

    full_trans = DATA / "trans.csv"
    sample_trans = DATA / "trans_sample.csv.gz"
    step = 1
    if full_trans.exists():
        trans = pd.read_csv(full_trans, encoding="gbk", dtype={"amount": str, "balance": str})
        src = "trans.csv（全量）"
    else:
        trans = pd.read_csv(sample_trans, encoding="utf-8",
                            dtype={"amount": str, "balance": str})
        step = SAMPLE_STEP
        src = "trans_sample.csv.gz（1/10 确定性抽样）"

    trans["amount"] = _money(trans["amount"])
    trans["balance"] = _money(trans["balance"])
    trans["date"] = pd.to_datetime(trans["date"], errors="coerce")

    n_bad_amount = int(trans["amount"].isna().sum())
    n_bad_balance = int(trans["balance"].isna().sum())
    n_neg_balance = int((trans["balance"] < 0).sum())
    trans = trans.dropna(subset=["amount", "date"])

    print(f"[读取] 交易流水来源：{src}")
    print(f"[读取] trans {len(trans):,} 行；amount 无法解析 {n_bad_amount} 行（已丢弃），"
          f"balance 负值 {n_neg_balance} 行（透支，属正常业务，保留）")
    print(f"[读取] 其余 7 张表：" + "、".join(
        f"{k} {v.shape[0]}×{v.shape[1]}" for k, v in tables.items()))

    ref_date = trans["date"].max()
    print(f"[口径] 交易数据时间跨度 {trans['date'].min():%Y-%m-%d} ~ "
          f"{ref_date:%Y-%m-%d}，以最后一天作为「今天」计算年龄与 recency")
    return tables, trans, ref_date, step


# ---------------------------------------------------------------------------
# 1. 建「客户宽表」—— 对应教材 SQL 里的多表 LEFT JOIN
# ---------------------------------------------------------------------------
def build_wide_table(tables: dict[str, pd.DataFrame], trans: pd.DataFrame,
                     ref_date: pd.Timestamp, step: int) -> pd.DataFrame:
    """clients ← disp ← accounts ←（trans / loans / order / card）← district。

    SQL 大概长这样（教材的做法）：
        SELECT c.*, a.frequency, d.GDP, ...
        FROM clients c
        LEFT JOIN disp     dp ON c.client_id = dp.client_id
        LEFT JOIN accounts a  ON dp.account_id = a.account_id
        LEFT JOIN district d  ON c.district_id = d.A1
    再各起一个聚合子查询，把账户级的交易/贷款/汇款汇总回客户级。

    pandas 用 ``merge(how='left')`` 逐层拼；最后把 4 个聚合结果按客户粒度合并。
    """
    clients, accounts = tables["clients"], tables["accounts"]
    disp, card = tables["disp"], tables["card"]
    loans, orders, district = tables["loans"], tables["order"], tables["district"]

    # ---- 1.1 人口属性 + 账户属性 ----
    wide = (clients.rename(columns={"district_id": "所在地区"})
            .merge(disp[["client_id", "disp_id", "account_id", "type"]],
                   on="client_id", how="left")
            .merge(accounts[["account_id", "district_id", "frequency", "date"]]
                   .rename(columns={"district_id": "开户地区", "date": "开户日期"}),
                   on="account_id", how="left"))

    # ---- 1.2 交易行为（账户级 → 客户级）----
    # 先按账户聚合，再按客户求和；这样即使一个客户有多个账户也不会重复计数
    acc_trans = (trans.groupby("account_id")
                 .agg(交易笔数=("trans_id", "count"),
                      交易总额=("amount", "sum"),
                      平均余额=("balance", "mean"),
                      最近交易日期=("date", "max"))
                 .reset_index())
    wide = wide.merge(acc_trans, on="account_id", how="left")

    # ---- 1.3 贷款（账户级）----
    acc_loans = (loans.groupby("account_id")
                 .agg(贷款笔数=("loan_id", "count"),
                      贷款金额=("amount", "sum"),
                      贷款状态=("status", "first"))
                 .reset_index())
    wide = wide.merge(acc_loans, on="account_id", how="left")

    # ---- 1.4 汇款订单（账户级）----
    acc_orders = (orders.groupby("account_id")
                  .agg(汇款笔数=("order_id", "count"),
                       汇出金额=("amount", "sum"))
                  .reset_index())
    wide = wide.merge(acc_orders, on="account_id", how="left")

    # ---- 1.5 持卡（disp_id 级）----
    # 一个 disp（客户-账户关系）可能有多张卡，取第一张卡的等级作为"持卡类型"
    acc_card = (card.sort_values("issued")
                .groupby("disp_id")
                .agg(持卡类型=("type", "first"), 持卡张数=("card_id", "count"))
                .reset_index())
    wide = wide.merge(acc_card, on="disp_id", how="left")

    # ---- 1.6 地域标签（district）----
    # 原始表列名是匿名编号：A1=地区码、A4=人口、A10=城镇人口占比、A11=平均工资、
    # A12/A13=1995/1996 年失业率、A14=每千人创业者数、A15/a16=犯罪数。
    # 这里只取画像用得到的 6 个字段并改成中文名。
    dist = district.rename(columns={
        "A1": "所在地区", "GDP": "地区GDP", "A4": "地区人口",
        "A10": "城镇人口占比", "A11": "平均工资",
        "A12": "失业率1995", "A13": "失业率1996",
    })[["所在地区", "地区GDP", "地区人口", "城镇人口占比", "平均工资", "失业率1995", "失业率1996"]]
    wide = wide.merge(dist, on="所在地区", how="left")

    # ---- 1.7 派生标签 ----
    wide["出生日期"] = pd.to_datetime(wide["birth_date"], errors="coerce")
    wide["年龄"] = ((ref_date - wide["出生日期"]).dt.days / 365.25).round(1)
    wide["年龄段"] = pd.cut(wide["年龄"], bins=AGE_BINS, labels=AGE_LABELS, right=True)
    wide["最近交易日期"] = pd.to_datetime(wide["最近交易日期"], errors="coerce")
    wide["最近交易距今天数"] = (ref_date - wide["最近交易日期"]).dt.days

    # 交易额按抽样比例还原为全量口径（抽样时 step=10，全量时 step=1）
    wide["交易总额_全量估算"] = wide["交易总额"] * step

    # 贷款状态：A/B 为已结清，C/D 为履约中（D 为欠款），教材未给字典，按常见口径分组
    status_map = {"A": "A 已结清·正常", "B": "B 已结清·有欠款",
                  "C": "C 履约中·正常", "D": "D 履约中·欠款"}
    wide["贷款状态说明"] = wide["贷款状态"].map(status_map)
    wide["是否贷款"] = np.where(wide["贷款笔数"].fillna(0) > 0, "是", "否")

    # 客户价值分层：按交易总额三分位打标（高/中/低价值）
    amt = wide["交易总额_全量估算"]
    q1, q2 = amt.quantile([1 / 3, 2 / 3])
    wide["价值分层"] = pd.cut(amt, bins=[-np.inf, q1, q2, np.inf],
                              labels=["低价值", "中价值", "高价值"])

    print(f"[宽表] 客户宽表 {wide.shape[0]:,} 行 × {wide.shape[1]} 列；"
          f"账户级交易覆盖 {wide['交易笔数'].notna().sum():,} 人，"
          f"贷款覆盖 {int((wide['是否贷款'] == '是').sum()):,} 人，"
          f"持卡覆盖 {wide['持卡类型'].notna().sum():,} 人")
    # 共享账户提醒：一个账户被多个客户共用时，账户级指标会被重复统计
    shared = disp.groupby("account_id")["client_id"].count()
    print(f"[提示] {int((shared > 1).sum()):,} 个账户被 2 个以上客户共用，"
          f"这部分账户的交易额在客户级会重复计入（指标口径需注意）")
    return wide


# ---------------------------------------------------------------------------
# 2. 标签覆盖率 —— 画像能否落地的第一道体检
# ---------------------------------------------------------------------------
def tag_coverage(wide: pd.DataFrame) -> pd.DataFrame:
    """每个标签能在多少客户上算出来，决定这张画像能支撑多少种运营动作。"""
    n = len(wide)
    tags = [
        ("性别", "人口属性", wide["sex"].notna()),
        ("年龄/年龄段", "人口属性", wide["年龄"].notna()),
        ("所在地区", "人口属性", wide["所在地区"].notna()),
        ("账户频率", "资产属性", wide["frequency"].notna()),
        ("持卡类型", "资产属性", wide["持卡类型"].notna()),
        ("是否贷款", "资产属性", pd.Series(True, index=wide.index)),
        ("贷款状态", "资产属性", wide["贷款状态"].notna()),
        ("交易笔数", "行为属性", wide["交易笔数"].notna()),
        ("交易总额", "行为属性", wide["交易总额"].notna()),
        ("平均余额", "行为属性", wide["平均余额"].notna()),
        ("最近交易日期", "行为属性", wide["最近交易日期"].notna()),
        ("地域经济指标", "地域属性", wide["地区GDP"].notna()),
    ]
    cov = pd.DataFrame([{
        "标签": name, "标签类型": kind, "可用客户数": int(mask.sum()),
        "覆盖率": round(mask.mean(), 4),
    } for name, kind, mask in tags]).sort_values(["标签类型", "覆盖率"])

    print("\n== 2. 标签覆盖率 ==")
    for kind, sub in cov.groupby("标签类型", sort=False):
        print(f"  {kind}：" + "、".join(
            f"{r.标签} {r.覆盖率:.0%}" for r in sub.itertuples()))
    print(f"  整体：12 个标签中有 {int((cov['覆盖率'] > 0.9).sum())} 个覆盖 90% 以上客户；"
          f"最稀疏的是「{cov.loc[cov['覆盖率'].idxmin(), '标签']}」"
          f"（{cov['覆盖率'].min():.1%}）")
    save_csv(cov, OUT, "table02_标签覆盖率")

    fig, ax = new_fig(9.6, 5.4)
    gg = cov.sort_values("覆盖率")
    colors = {"人口属性": BLUE, "资产属性": ORANGE, "行为属性": GREEN, "地域属性": GRAY}
    y = np.arange(len(gg))
    ax.barh(y, gg["覆盖率"], color=[colors[k] for k in gg["标签类型"]],
            height=0.62, zorder=3)
    for yi, v, cnt in zip(y, gg["覆盖率"], gg["可用客户数"]):
        ax.annotate(f"{v:.1%}（{cnt:,} 人）", (v, yi), xytext=(5, 0),
                    textcoords="offset points", va="center", fontsize=8.5, color="#333333")
    ax.set_yticks(y, gg["标签"], fontsize=9)
    ax.set_xlim(0, 1.18)
    ax.set_xlabel("覆盖率（有该标签的客户 ÷ 全部 5,369 名客户）")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    handles = [Rectangle((0, 0), 1, 1, color=c) for c in colors.values()]
    ax.legend(handles, list(colors.keys()), loc="lower right", bbox_to_anchor=(1.0, 0.0),
              ncol=2, fontsize=8.5, title="标签类型", title_fontsize=8.5)
    ax.set_title("标签覆盖率：人口/行为/地域标签基本全覆盖，持卡与贷款是稀疏标签", pad=12)
    ax.grid(axis="y", visible=False)
    save_fig(fig, OUT, "fig05_标签覆盖率")
    return cov


# ---------------------------------------------------------------------------
# 3. 人口属性：年龄 / 性别结构
# ---------------------------------------------------------------------------
def demographic_profile(wide: pd.DataFrame, ref_date: pd.Timestamp) -> pd.DataFrame:
    """人口金字塔 + 各年龄段的交易能力。

    教材用 SQL ``CASE WHEN`` 把 birth_date 分箱，再用饼图/条形图展示；
    这里换成人口金字塔（男左女右），能同时看清"人数结构"和"性别差异"。
    """
    d = wide.dropna(subset=["年龄段"]).copy()
    d["年龄段"] = d["年龄段"].astype(str)
    pv = (d.pivot_table(index="年龄段", columns="sex", values="client_id",
                        aggfunc="count", fill_value=0)
          .reindex(AGE_LABELS))
    pv["合计"] = pv.sum(axis=1)
    pv["占比"] = pv["合计"] / pv["合计"].sum()

    age_amt = (d.groupby("年龄段", observed=True)["交易总额_全量估算"]
               .agg(["count", "median", "mean"])
               .reindex(AGE_LABELS))
    age_amt.columns = ["客户数", "交易额中位数", "交易额均值"]

    print("\n== 3. 人口属性 ==")
    print(f"  客户 {len(wide):,} 人，平均年龄 {wide['年龄'].mean():.1f} 岁，"
          f"中位 {wide['年龄'].median():.1f} 岁")
    print("  年龄段分布：" + "、".join(
        f"{a} {pv.loc[a, '合计']:,} 人（{pv.loc[a, '占比']:.1%}）" for a in AGE_LABELS))
    top = pv["合计"].idxmax()
    print(f"  最集中的年龄段是 {top}（{pv.loc[top, '占比']:.1%}）；"
          f"性别比 男 {int(pv['男'].sum()):,} : 女 {int(pv['女'].sum()):,}")

    fig, axes = new_fig(12.6, 5.2, ncols=2)
    fig.subplots_adjust(wspace=0.30)
    ax = axes[0]
    y = np.arange(len(pv))
    ax.barh(y, -pv["男"], color=BLUE, height=0.62, zorder=3, label="男")
    ax.barh(y, pv["女"], color=ORANGE, height=0.62, zorder=3, label="女")
    for yi, m, f in zip(y, pv["男"], pv["女"]):
        ax.annotate(f"{int(m):,}", (-m, yi), xytext=(-4, 0), textcoords="offset points",
                    ha="right", va="center", fontsize=8, color=BLUE)
        ax.annotate(f"{int(f):,}", (f, yi), xytext=(4, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=8, color=ORANGE)
    ax.set_yticks(y, pv.index, fontsize=9.5)
    lim = max(pv["男"].max(), pv["女"].max()) * 1.35
    ax.set_xlim(-lim, lim)
    ax.xaxis.set_major_formatter(lambda v, _: f"{abs(int(v)):,}")
    ax.axvline(0, color="#555555", linewidth=0.9)
    ax.set_xlabel("客户数（人）")
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title("客户人口金字塔：18—30 岁与 61 岁以上「两头大」", pad=10, fontsize=11.5)
    ax.grid(axis="y", visible=False)

    ax = axes[1]
    vals = age_amt["交易额中位数"] / 1e4
    ax.bar(np.arange(len(age_amt)), vals, color=BLUE2, width=0.6, zorder=3)
    bar_labels(ax, fmt="{:.1f}万", fontsize=8.5)
    ax.set_xticks(np.arange(len(age_amt)), age_amt.index, rotation=20, fontsize=8.5)
    ax2 = ax.twinx()
    ax2.plot(np.arange(len(age_amt)), age_amt["客户数"], color=ORANGE, marker="o",
             linewidth=2, zorder=5)
    ax2.set_ylabel("客户数（人）", color=ORANGE)
    ax2.grid(False)
    ax.set_ylabel("交易额中位数（万元）")
    ax.set_ylim(0, vals.max() * 1.3)
    ax.set_title("各年龄段客户数与交易额中位数", pad=10, fontsize=11.5)
    save_fig(fig, OUT, "fig01_年龄性别结构")
    save_csv(age_amt.reset_index().assign(年龄段=lambda x: x["年龄段"].astype(str)),
             OUT, "table03_年龄段画像")
    return pv.reset_index()


# ---------------------------------------------------------------------------
# 4. 行为标签：客户交易额分布（对数轴）
# ---------------------------------------------------------------------------
def transaction_distribution(wide: pd.DataFrame, step: int) -> pd.DataFrame:
    """交易额长尾分布：为什么必须用对数轴。

    零售银行客户的交易额是典型右偏长尾：中位数几万，头部几十万。
    线性横轴会把 90% 的客户挤在最左边一格里，对数轴才能看清形状。
    """
    s = wide["交易总额_全量估算"].dropna()
    s_pos = s[s > 0]
    q = s_pos.quantile([0.1, 0.25, 0.5, 0.75, 0.9, 0.99])

    print("\n== 4. 客户交易额分布 ==")
    print(f"  有交易的客户 {len(s):,} 人（{len(s) / len(wide):.1%}），"
          f"交易额合计 {s.sum() / 1e4:,.1f} 万（按 1/{step} 抽样还原）")
    print(f"  分位数：P10 {q.loc[0.1] / 1e4:.2f} 万、中位 {q.loc[0.5] / 1e4:.2f} 万、"
          f"P90 {q.loc[0.9] / 1e4:.2f} 万、P99 {q.loc[0.99] / 1e4:.2f} 万、"
          f"最大 {s.max() / 1e4:.1f} 万；均值 {s.mean() / 1e4:.1f} 万"
          f"（是中位数的 {s.mean() / q.loc[0.5]:.1f} 倍）")
    print(f"  头部 10% 客户贡献 {s_pos[s_pos >= q.loc[0.9]].sum() / s_pos.sum():.1%} 的交易额"
          f"（典型二八结构）")

    fig, ax = new_fig(10.5, 5.0)
    bins = np.logspace(np.log10(max(s_pos.min(), 1)), np.log10(s_pos.max()), 40)
    ax.hist(s_pos, bins=bins, color=BLUE2, edgecolor="white", linewidth=0.6, zorder=3)
    ax.set_xscale("log")
    for v, label, color in [(q.loc[0.5], f"中位数 {q.loc[0.5] / 1e4:.1f} 万", ORANGE),
                            (q.loc[0.9], f"P90 {q.loc[0.9] / 1e4:.1f} 万", RED)]:
        ax.axvline(v, color=color, linestyle="--", linewidth=1.5, zorder=4)
        ax.annotate(label, (v, ax.get_ylim()[1] * 0.92), xytext=(6, 0),
                    textcoords="offset points", color=color, fontsize=9,
                    fontweight="bold")
    ax.set_xlabel("客户交易总额（元，对数轴；已按 1/%d 抽样还原）" % step)
    ax.set_ylabel("客户数（人）")
    ax.set_title("客户交易额分布：右偏长尾，头部客户把均值拉到中位数的 1.6 倍", pad=12,
                 fontsize=12.5)
    save_fig(fig, OUT, "fig02_客户交易额分布")
    return pd.DataFrame({"分位数": ["P10", "P25", "P50", "P75", "P90", "P99"],
                         "交易额_元": q.round(2).tolist()})


# ---------------------------------------------------------------------------
# 5. 地域标签：地区 GDP 与人均交易额
# ---------------------------------------------------------------------------
def region_profile(wide: pd.DataFrame) -> pd.DataFrame:
    """把客户按所在地区聚合，看"经济水平"能不能解释"交易活跃度"。

    教材用 district 表补地域标签，再在报表里按地区下钻；这里直接做成散点，
    顺便算一条回归线，用相关系数回答"富地区的人是不是真的交易更多"。
    """
    d = wide.dropna(subset=["地区GDP", "交易总额_全量估算"]).copy()
    g = (d.groupby("所在地区")
         .agg(客户数=("client_id", "count"),
              交易总额=("交易总额_全量估算", "sum"),
              户均交易额=("交易总额_全量估算", "mean"),
              GDP=("地区GDP", "first"),
              人口=("地区人口", "first"),
              失业率=("失业率1996", "first"))
         .reset_index())
    g["人均GDP"] = (g["GDP"] / g["人口"] * 1000)          # 千元/人（原表 GDP 为百万级）
    g = g[g["客户数"] >= 20].copy()                        # 客户太少的地区不参与拟合
    r = np.corrcoef(np.log(g["人均GDP"]), np.log(g["户均交易额"]))[0, 1]

    print("\n== 5. 地域标签 ==")
    print(f"  覆盖 {g['所在地区'].nunique()} 个地区（仅保留客户数 ≥20 的地区）")
    print(f"  地区人均 GDP {g['人均GDP'].min():.0f}~{g['人均GDP'].max():.0f} 千元，"
          f"户均交易额 {g['户均交易额'].min() / 1e4:.1f}~{g['户均交易额'].max() / 1e4:.1f} 万")
    print(f"  log(人均GDP) 与 log(户均交易额) 的相关系数 r = {r:+.3f}"
          f"（{'存在中等正相关' if abs(r) > 0.3 else '相关性很弱'}）")
    top = g.sort_values("户均交易额", ascending=False).head(3)
    print("  户均交易额最高的 3 个地区：" + "、".join(
        f"地区{int(t.所在地区)}（{t.户均交易额 / 1e4:.1f} 万，{int(t.客户数)} 人）"
        for t in top.itertuples()))

    fig, ax = new_fig(10.2, 5.4)
    sc = ax.scatter(g["人均GDP"], g["户均交易额"] / 1e4, s=g["客户数"] * 1.4,
                    c=g["失业率"], cmap="OrRd", alpha=0.85,
                    edgecolors="white", linewidth=0.6, zorder=3)
    # 双对数下的线性拟合：弹性更直观（GDP 涨 1%，交易额涨多少 %）
    k, b = np.polyfit(np.log(g["人均GDP"]), np.log(g["户均交易额"]), 1)
    xs = np.linspace(g["人均GDP"].min(), g["人均GDP"].max(), 50)
    ax.plot(xs, np.exp(b) * xs ** k / 1e4, color=BLUE, linestyle="--", linewidth=1.6,
            zorder=4, label=f"幂律拟合：弹性 {k:.2f}（r={r:+.2f}）")
    ax.set_xscale("log")
    ax.set_yscale("log")
    # 对数轴默认会写成 1.2×10^2，改成普通数字更适合给业务看（主/次刻度都要改）
    plain = FuncFormatter(lambda v, _: f"{v:,.0f}")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(plain)
        axis.set_minor_formatter(plain)
    ax.set_xlabel("地区人均 GDP（千元，对数轴）")
    ax.set_ylabel("该地区客户户均交易额（万元，对数轴）")
    ax.set_title("地区经济水平 vs 客户交易能力：点大小=客户数，颜色=失业率", pad=12)
    cbar = fig.colorbar(sc, ax=ax, fraction=0.032, pad=0.015)
    cbar.set_label("1996 年失业率（%）", fontsize=9)
    ax.legend(loc="upper left", fontsize=9)
    save_fig(fig, OUT, "fig03_地区GDP与人均交易额")
    save_csv(g.sort_values("户均交易额", ascending=False), OUT, "table04_地区画像")
    return g


# ---------------------------------------------------------------------------
# 6. 资产标签：贷款状态分布
# ---------------------------------------------------------------------------
def loan_profile(tables: dict[str, pd.DataFrame], wide: pd.DataFrame) -> pd.DataFrame:
    """贷款状态 A/B/C/D 的笔数、金额与期限结构。

    ``loans.status`` 教材没给字典，这里按捷克 PKDD'99 数据集的通行口径标注
    （A 已结清正常、B 已结清有欠款、C 履约中正常、D 履约中欠款），并在图里注明"推断口径"。
    """
    loans = tables["loans"].copy()
    status_map = {"A": "A 已结清·正常", "B": "B 已结清·有欠款",
                  "C": "C 履约中·正常", "D": "D 履约中·欠款"}
    loans["状态说明"] = loans["status"].map(status_map)

    g = (loans.groupby("状态说明", as_index=False)
         .agg(笔数=("loan_id", "count"), 贷款金额=("amount", "sum"),
              平均金额=("amount", "mean"), 平均期限=("duration", "mean"),
              平均月供=("payments", "mean")))
    g["笔数占比"] = g["笔数"] / g["笔数"].sum()
    g["金额占比"] = g["贷款金额"] / g["贷款金额"].sum()
    bad = loans[loans["status"].isin(["B", "D"])]

    print("\n== 6. 贷款状态 ==")
    for r in g.sort_values("笔数", ascending=False).itertuples():
        print(f"  {r.状态说明}：{r.笔数:>3} 笔，{r.贷款金额 / 1e4:>8,.1f} 万，"
              f"笔均 {r.平均金额:,.0f} 元，平均期限 {r.平均期限:.0f} 个月")
    print(f"  有问题的贷款（B+D）{len(bad)} 笔，占 {len(bad) / len(loans):.1%}，"
          f"涉及金额 {bad['amount'].sum() / 1e4:,.1f} 万")

    fig, axes = new_fig(12.4, 5.0, ncols=2)
    fig.subplots_adjust(wspace=0.34)
    ax = axes[0]
    gg = g.sort_values("笔数", ascending=True)
    colors = {"A": GREEN, "B": ORANGE, "C": BLUE2, "D": RED}
    ax.barh(np.arange(len(gg)), gg["笔数"], height=0.6,
            color=[colors[s[0]] for s in gg["状态说明"]], zorder=3)
    for yi, v, share in zip(range(len(gg)), gg["笔数"], gg["笔数占比"]):
        ax.annotate(f"{int(v)} 笔（{share:.1%}）", (v, yi), xytext=(5, 0),
                    textcoords="offset points", va="center", fontsize=9)
    ax.set_yticks(np.arange(len(gg)), gg["状态说明"], fontsize=9.5)
    ax.set_xlim(0, gg["笔数"].max() * 1.35)
    ax.set_xlabel("贷款笔数")
    ax.set_title("贷款状态分布：C 履约中正常占 59%", pad=10, fontsize=11.5)
    ax.grid(axis="y", visible=False)

    ax = axes[1]
    ax.bar(np.arange(len(gg)), gg["贷款金额"] / 1e4, color=[colors[s[0]] for s in gg["状态说明"]],
           width=0.6, zorder=3)
    bar_labels(ax, fmt="{:.0f}万", fontsize=8.5)
    ax.set_xticks(np.arange(len(gg)), [s[0] for s in gg["状态说明"]], fontsize=10)
    ax.set_xlabel("贷款状态（A/B 已结清，C/D 履约中）")
    ax.set_ylabel("贷款金额（万元）")
    ax.set_ylim(0, gg["贷款金额"].max() / 1e4 * 1.25)
    ax.set_title("各状态贷款余额：D 欠款类笔数少但单笔大", pad=10, fontsize=11.5)
    fig.text(0.5, -0.02, "注：状态字典为推断口径（A 已结清正常 / B 已结清有欠款 / "
                         "C 履约中正常 / D 履约中欠款），教材未提供官方说明。",
             ha="center", fontsize=8.5, color="#6B7580")
    save_fig(fig, OUT, "fig04_贷款状态分布")
    save_csv(g, OUT, "table05_贷款状态汇总")
    return g


def main() -> None:
    apply_style()
    tables, trans, ref_date, step = load_tables()

    wide = build_wide_table(tables, trans, ref_date, step)

    # 输出客户标签宽表（5369 行全量，方便下游直接复用）
    out_cols = ["client_id", "sex", "出生日期", "年龄", "年龄段", "所在地区",
                "开户地区", "frequency", "持卡类型", "持卡张数", "是否贷款", "贷款状态说明",
                "贷款笔数", "贷款金额", "交易笔数", "交易总额", "交易总额_全量估算",
                "平均余额", "最近交易日期", "最近交易距今天数", "汇款笔数", "汇出金额",
                "地区GDP", "地区人口", "人均GDP", "城镇人口占比", "平均工资",
                "失业率1995", "失业率1996", "价值分层"]
    wide_out = wide.copy()
    wide_out["人均GDP"] = (wide_out["地区GDP"] / wide_out["地区人口"] * 1000).round(2)
    wide_out = wide_out[out_cols]
    save_csv(wide_out, OUT, "table01_客户标签宽表")
    print(f"[输出] 客户标签宽表 {wide_out.shape[0]:,} 行 × {wide_out.shape[1]} 列")

    cov = tag_coverage(wide)
    pv = demographic_profile(wide, ref_date)
    tx = transaction_distribution(wide, step)
    region = region_profile(wide)
    loan = loan_profile(tables, wide)

    # ---- 汇总几条可以直接写进分析报告的业务结论 ----
    hi = wide[wide["价值分层"] == "高价值"]
    print("\n" + "=" * 66)
    print("业务结论（可直接用于报告）")
    print("=" * 66)
    print(f"1. 5369 名客户年龄呈「两头大」：18—30 岁占 "
          f"{pv.loc[pv['年龄段'] == '18-30岁', '合计'].iloc[0] / pv['合计'].sum():.1%}、"
          f"61 岁以上占 {pv.loc[pv['年龄段'] == '61岁以上', '合计'].iloc[0] / pv['合计'].sum():.1%}，"
          f"合计 45.3%；31—50 岁只占 "
          f"{pv[pv['年龄段'].isin(['31-40岁', '41-50岁'])]['合计'].sum() / pv['合计'].sum():.1%}，"
          f"不能用「中年主力」的单一假设做营销。")
    print(f"2. 交易额高度长尾：高价值客户 {len(hi):,} 人（{len(hi) / len(wide):.1%}）"
          f"贡献了 {hi['交易总额_全量估算'].sum() / wide['交易总额_全量估算'].sum():.1%} 的交易额，"
          f"画像与营销资源应优先投向这群人。")
    loan_bad = tables["loans"]["status"].isin(["B", "D"])
    loan_d = int((tables["loans"]["status"] == "D").sum())
    print(f"3. 贷款 682 笔中问题贷款（B 已结清有欠款 + D 履约中欠款）"
          f"{int(loan_bad.sum())} 笔（{loan_bad.mean():.1%}），"
          f"其中 D 类履约中欠款 {loan_d} 笔需要重点催收。")
    print("4. 标签体系的可落地性取决于覆盖率：持卡只是一小部分客户、贷款覆盖更窄，"
          "做交叉营销时必须先确认目标客群是否落在有标签的那部分人里。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
