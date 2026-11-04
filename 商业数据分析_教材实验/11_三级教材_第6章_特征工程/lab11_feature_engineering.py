# -*- coding: utf-8 -*-
"""
实验 11 · 特征工程：从原始账单到可入模的特征矩阵
==================================================
教材：《CDA 三级认证教材：敏捷数据挖掘》第 6 章 特征工程
原始素材：``telecom_bill.csv``（3000 行 × 10 列，运营商客户账单与流失标记）
迁移方向：教材 60 多个零散 cell（每个技巧一段代码）
          → **一条可复现的流水线：体检 → 清洗 → 派生 → 编码 → 分箱/WOE → 筛选**

教材这一章是"工具箱式"写法：异常值缩尾、log 变换、缺失填补、Binarizer、pd.cut/qcut、
get_dummies/OneHotEncoder、StandardScaler/MinMaxScaler/Normalizer、PCA/LDA、
方差过滤、卡方、ANOVA、RFE、随机森林重要性……每招一个 cell，但没有串成流程。
本脚本按真实建模顺序重排，并把教材只给代码、没给解释的地方补上"为什么"：

1. 先做**数据体检**（缺失率、目标比例、异常值），再决定怎么处理；
2. 把 ``join_time`` 变成**入网时长**这种有业务含义的连续变量；
3. 用**分箱 + WOE/IV** 检查"入网时长到底有没有区分度"（教材讲了分箱，没讲 WOE/IV）；
4. 最后用三种口径（方差、统计检验、模型重要性）交叉验证**该保留哪些特征**。

运行：``python lab11_feature_engineering.py``（在实验目录下执行）
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import chi2, f_classif

# 让脚本能从仓库根的 common/ 导入统一样式
LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR.parent))

from common.style import (  # noqa: E402
    BLUE, BLUE2, GRAY, GREEN, NEG, ORANGE, PALETTE, POS, RED,
    apply_style, new_fig, pct_axis, save_csv, save_fig,
)

warnings.filterwarnings("ignore")

DATA = LAB_DIR / "data" / "telecom_bill.csv"
OUT = LAB_DIR / "outputs"

REF_DATE = pd.Timestamp("2015-01-01")   # 教材 cell 27：以 2015-01-01 为"当前时点"算入网时长
CHURN_RATE = 0.26


# ---------------------------------------------------------------------------
# 0. 读取 + 异常值剔除 —— 对应教材 cell 2 / 4 / 5
# ---------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    """读取原始账单，剔除流量异常样本，并解析日期。

    教材 cell 4/5 的做法是 ``raw[raw.traffic >= 5000]`` 先看一眼，再
    ``data = raw[raw.traffic < 5000].copy()`` 剔除。这一步看着随意，其实是必要的：
    3000 行里有 3 行流量 ≥ 5000（最大 9428），量级是正常用户的几十倍，
    不剔除会把 log 变换、标准化、相关性全部带偏。

    这里额外把 ``join_time`` 解析成日期，后面所有派生特征都基于它。
    """
    raw = pd.read_csv(DATA)
    df = raw[raw["traffic"] < 5000].copy()
    df["join_time"] = pd.to_datetime(df["join_time"], errors="coerce")

    print("=" * 70)
    print("实验 11 · 电信客户特征工程：从原始账单到特征矩阵")
    print("=" * 70)
    print(f"[数据] 原始 {len(raw)} 行 × {raw.shape[1]} 列；"
          f"剔除 traffic ≥ 5000 的异常样本 {len(raw) - len(df)} 行，剩余 {len(df)} 行")
    print(f"[数据] 目标变量 churn：流失 {int(df['churn'].sum())} 人，"
          f"占比 {df['churn'].mean():.1%}")
    print(f"[数据] 入网时间跨度 {df['join_time'].min():%Y-%m-%d} ~ "
          f"{df['join_time'].max():%Y-%m-%d}")

    # join_time 若解析失败会变成 NaT，必须在派生特征前发现
    bad_date = int(df["join_time"].isna().sum())
    if bad_date:
        print(f"[警告] {bad_date} 行 join_time 解析失败，已在时长计算中按缺失处理")
    return df


# ---------------------------------------------------------------------------
# 1. 数据体检 —— 缺失率 / 目标比例 / 数值分布
# ---------------------------------------------------------------------------
def data_health(df: pd.DataFrame) -> pd.DataFrame:
    """统计缺失率、目标分布与数值变量偏度，画第一张"体检图"。

    教材的做法是 ``data.count()`` / ``data.isnull().sum()`` 各看一次，
    再单独画饼图看 state 分布。这里合并成一张表 + 一张双面板图，
    目的是先回答三个问题，再动手处理：

      * **缺多少**：IMEI 缺失 77%、state 缺失 2%，两者处理策略完全不同；
      * **目标偏不偏**：churn 26.1%，不算极度不平衡，但仍需 ``class_weight``；
      * **数值偏不偏**：expenditure/call/traffic 的偏度都远大于 1，
        所以后面要做 log 变换，而不是直接标准化。
    """
    miss = pd.DataFrame({
        "字段": df.columns,
        "缺失数": [df[c].isna().sum() for c in df.columns],
        "缺失率": [df[c].isna().mean() for c in df.columns],
        "数据类型": [str(df[c].dtype) for c in df.columns],
    })
    miss["唯一值"] = [df[c].nunique(dropna=True) for c in df.columns]
    miss = miss.sort_values("缺失率", ascending=False).reset_index(drop=True)

    num_cols = ["expenditure", "call", "traffic"]
    skew = df[num_cols].skew()

    print("\n== 1. 数据体检 ==")
    worst = miss[miss["缺失数"] > 0]
    print("  缺失最严重的字段：" + "、".join(
        f"{r['字段']} {r['缺失率']:.1%}" for _, r in worst.head(3).iterrows()))
    print(f"  churn 比例：{df['churn'].mean():.1%}"
          f"（流失 {int(df['churn'].sum())} / {len(df)}）")
    print("  数值变量偏度：" + "，".join(f"{c} {skew[c]:.2f}" for c in num_cols)
          + "（>1 说明右偏，需要 log 变换）")
    state_values = [int(x) for x in sorted(df["state"].dropna().unique())]
    print(f"  state 取值：{state_values}，缺失 {int(df['state'].isna().sum())} 行")

    fig, axes = new_fig(11.0, 4.6, ncols=2)
    ax = axes[0]
    m = miss[miss["缺失数"] > 0].sort_values("缺失率")
    y = np.arange(len(m))
    colors = [RED if v > 0.5 else ORANGE for v in m["缺失率"]]
    ax.barh(y, m["缺失率"], color=colors, height=0.6, zorder=3)
    ax.set_yticks(y, m["字段"])
    for yi, v, n in zip(y, m["缺失率"], m["缺失数"]):
        ax.annotate(f"{v:.1%}（{n} 行）", (v, yi), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=9)
    ax.set_xlim(0, max(m["缺失率"].max() * 1.3, 0.05))
    pct_axis(ax, axis="x", decimals=0)
    ax.set_title("有缺失的字段及缺失率", pad=10)
    ax.set_xlabel("缺失率")
    ax.set_ylabel("")
    ax.grid(axis="y", visible=False)

    ax = axes[1]
    counts = df["churn"].value_counts().sort_index()
    bars = ax.bar(["未流失（0）", "流失（1）"], counts.values,
                  color=[BLUE2, RED], width=0.5, zorder=3)
    for b, v in zip(bars, counts.values):
        ax.annotate(f"{v} 人\n{v / len(df):.1%}", (b.get_x() + b.get_width() / 2, v),
                    xytext=(0, 6), textcoords="offset points", ha="center",
                    fontsize=10, color="#333333")
    ax.set_ylim(0, counts.max() * 1.22)
    ax.set_title(f"目标变量分布：流失率 {df['churn'].mean():.1%}", pad=10)
    ax.set_ylabel("客户数")
    fig.suptitle(f"数据体检：{len(df)} 行 × {df.shape[1]} 列，1 个二分类目标",
                 fontsize=12.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_fig(fig, OUT, "fig01_缺失率与目标分布")
    save_csv(miss, OUT, "table01_数据体检与缺失率")
    return miss


# ---------------------------------------------------------------------------
# 2. 数值处理：3σ 缩尾 + log1p —— 对应教材 cell 10—14
# ---------------------------------------------------------------------------
def treat_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """对消费金额做 3σ 缩尾，再对金额/通话/流量取 log1p。

    教材的顺序是：先 ``boxplot`` 看箱线图 → 用 ``mu ± 3σ`` 截断 → ``np.log1p`` 压偏态。
    这里保留同样的逻辑，但补了两句"为什么"：

    * **为什么用 3σ 而不是 1.5 IQR**：expenditure 有大量 0 值（未消费），
      IQR 下界会是负数、上界被 0 拉得很低，会把正常的中高消费全判成异常；
    * **为什么 log1p 而不是 log**：有 0 值，``log(0) = -inf``，``log1p`` 可安全处理 0。

    缩尾只影响极端值，不改变中位数；log 变换把右偏拉回近似对称，
    这对后面做标准化、相关性分析都很重要。
    """
    mu, sigma = df["expenditure"].mean(), df["expenditure"].std()
    lower, upper = mu - 3 * sigma, mu + 3 * sigma
    clipped_low = int((df["expenditure"] < lower).sum())
    clipped_high = int((df["expenditure"] > upper).sum())

    df["expenditure_winsor"] = df["expenditure"].clip(lower, upper)
    df["log_expd"] = np.log1p(df["expenditure_winsor"])
    df["log_call"] = np.log1p(df["call"])
    df["log_traffic"] = np.log1p(df["traffic"])
    df["unit_price"] = df["expenditure"] / (df["traffic"] + 1.0)   # 教材 cell 45 的派生特征

    print("\n== 2. 数值处理（3σ 缩尾 + log1p） ==")
    print(f"  expenditure：均值 {mu:.2f}，标准差 {sigma:.2f}，"
          f"3σ 上界 {upper:.2f}、下界 {lower:.2f}")
    print(f"  截断：上侧 {clipped_high} 行、下侧 {clipped_low} 行"
          f"（共 {clipped_high + clipped_low} 行，占 {((clipped_high + clipped_low) / len(df)):.1%}）")
    print(f"  偏度：expenditure {df['expenditure_winsor'].skew():.2f} → "
          f"log_expd {df['log_expd'].skew():.2f}；"
          f"traffic {df['traffic'].skew():.2f} → log_traffic {df['log_traffic'].skew():.2f}")

    fig, axes = new_fig(13.2, 4.3, ncols=3)
    ax = axes[0]
    ax.boxplot([df["expenditure"], df["expenditure_winsor"]], widths=0.45,
               patch_artist=True, showfliers=True,
               boxprops=dict(facecolor="#D6E4F0", color=BLUE),
               medianprops=dict(color=ORANGE, linewidth=2),
               flierprops=dict(marker="o", markersize=3.5, markerfacecolor=GRAY,
                               markeredgecolor="none", alpha=0.6))
    ax.set_xticks([1, 2], ["缩尾前", "3σ 缩尾后"])
    ax.set_title("缩尾前后箱线图", pad=10)
    ax.set_ylabel("消费金额（元）")

    ax = axes[1]
    ax.hist(df["expenditure_winsor"], bins=45, color=BLUE2, alpha=0.8,
            edgecolor="white", zorder=3)
    ax.set_title(f"原始金额：右偏（偏度 {df['expenditure_winsor'].skew():.2f}）", pad=10)
    ax.set_xlabel("消费金额（元）")
    ax.set_ylabel("客户数")

    ax = axes[2]
    ax.hist(df["log_expd"], bins=30, color=ORANGE, alpha=0.8,
            edgecolor="white", zorder=3)
    ax.set_title(f"log1p 后：近似对称（偏度 {df['log_expd'].skew():.2f}）", pad=10)
    ax.set_xlabel("log1p(消费金额)")
    ax.set_ylabel("客户数")
    fig.suptitle("消费金额处理：3σ 缩尾压极端值，log1p 压右偏", fontsize=12.5,
                 fontweight="bold", y=1.03)
    fig.tight_layout()
    save_fig(fig, OUT, "fig02_消费金额分布与对数变换")
    return df


# ---------------------------------------------------------------------------
# 3. 日期特征 —— 对应教材 cell 27：入网时长
# ---------------------------------------------------------------------------
def build_date_features(df: pd.DataFrame) -> pd.DataFrame:
    """把 ``join_time`` 拆成入网天数 / 入网月数 / 入网年份 / 入网月份。

    教材只有一句 ``(datetime(2015,1,1) - to_datetime(join_time)).days / 30``。
    这里把四个派生列都建出来，是因为它们在建模里的作用不同：

      * ``duration_months``：连续变量，区分度最好，适合分箱和树模型；
      * ``join_year``：能抓到"某年入网的客户流失率异常"这种批次效应；
      * ``join_month``：可以看季节性（例如年底冲量入网的客户留存更差）。
    """
    delta = REF_DATE - df["join_time"]
    df["duration_days"] = delta.dt.days
    df["duration_months"] = df["duration_days"] / 30.0
    df["join_year"] = df["join_time"].dt.year
    df["join_month"] = df["join_time"].dt.month

    print("\n== 3. 日期特征 ==")
    print(f"  入网时长（月）：均值 {df['duration_months'].mean():.1f}，"
          f"中位数 {df['duration_months'].median():.1f}，"
          f"区间 [{df['duration_months'].min():.1f}, {df['duration_months'].max():.1f}]")
    by_year = df.groupby("join_year")["churn"].agg(["count", "mean"])
    churn_by_year = "，".join(f"{int(y)} 年 {r['mean']:.0%}（{int(r['count'])} 人）"
                              for y, r in by_year.iterrows())
    print(f"  按入网年份的流失率：{churn_by_year}")
    return df


# ---------------------------------------------------------------------------
# 4. 分箱 + WOE/IV —— 对应教材 cell 28—34（教材只有分箱，WOE/IV 是补充）
# ---------------------------------------------------------------------------
def _fmt_interval(value) -> str:
    """把 pd.cut 的区间对象格式化成「1.9 ~ 36.9」这种短标签（端点用 -∞/+∞）。"""
    if isinstance(value, pd.Interval):
        left = "-∞" if np.isneginf(value.left) else f"{value.left:.1f}"
        right = "+∞" if np.isposinf(value.right) else f"{value.right:.1f}"
        return f"{left} ~ {right}"
    return str(value)


def _woe_iv(bin_series: pd.Series, y: pd.Series) -> pd.DataFrame:
    """给定分箱结果，算每箱的样本数、流失率、WOE 与 IV。

    WOE（Weight of Evidence）= ln( 该箱流失占比 / 该箱未流失占比 )，
    衡量"这一箱比整体更容易流失还是更不容易"；正值越大越危险。

    IV（Information Value）= Σ (流失占比 − 未流失占比) × WOE，
    是把所有箱的区分度加总的标量，经验阈值：<0.02 无区分度、0.02—0.1 弱、
    0.1—0.3 中等、>0.3 强。它比"看流失率曲线"更适合横向比较不同变量。
    """
    tmp = pd.DataFrame({"bin": bin_series, "y": y})
    tmp["label"] = tmp["bin"].map(_fmt_interval)
    grouped = tmp.groupby("label", observed=True)["y"].agg(["count", "sum"])
    grouped["bad"] = grouped["sum"]
    grouped["good"] = grouped["count"] - grouped["bad"]
    grouped["churn_rate"] = grouped["bad"] / grouped["count"]

    # 加 0.5 做拉普拉斯平滑，避免某箱 0 流失导致 ln(0)
    bad_pct = (grouped["bad"] + 0.5) / (grouped["bad"].sum() + 0.5 * len(grouped))
    good_pct = (grouped["good"] + 0.5) / (grouped["good"].sum() + 0.5 * len(grouped))
    grouped["woe"] = np.log(bad_pct / good_pct)
    grouped["iv"] = (bad_pct - good_pct) * grouped["woe"]
    grouped["iv_total"] = grouped["iv"].sum()
    grouped = grouped.reset_index()
    return grouped


def binning_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """对入网时长做三种分箱（等宽 / 等频 / 人工），比较流失率曲线并算 IV。

    教材分别用 ``pd.cut(duration, 5)``、``pd.qcut(duration, 14)``、
    ``pd.cut(duration, [-inf,5,12,36,inf])`` 画了三张柱状图，但没说该选哪种。这里给出判断标准：

      * **等宽**：业务上最好解释（"每 2 年一档"），但样本量分布不均，
        极端箱可能只有几个人，流失率抖动大；
      * **等频**：每箱人数相同，曲线最平滑，适合看单调性，但箱边界不整齐；
      * **人工**：按业务节点切（5 个月 / 1 年 / 3 年），可解释性最强，前提是有业务依据。

    三种方式都算 IV，用数字而不是"看图感觉"来选。
    """
    y = df["churn"]
    schemes = {
        "等宽 5 箱": pd.cut(df["duration_months"], 5),
        "等频 14 箱": pd.qcut(df["duration_months"], 14, duplicates="drop"),
        "人工分箱（5/12/36 个月）": pd.cut(df["duration_months"],
                                    [-np.inf, 5, 12, 36, np.inf]),
    }

    tables = []
    for name, bins in schemes.items():
        t = _woe_iv(bins, y)
        t.insert(0, "分箱方式", name)
        tables.append(t)
        print(f"\n  {name}：{len(t)} 箱，IV = {t['iv_total'].iloc[0]:.3f}"
              f"（{'强' if t['iv_total'].iloc[0] > 0.3 else '中等' if t['iv_total'].iloc[0] > 0.1 else '弱'}区分度）")

    # 省份编码也按同样口径算 IV，用来和入网时长做横向对比
    state_bins = df["state"].fillna(-1).astype(int).astype(str)
    state_table = _woe_iv(state_bins, y)
    state_table.insert(0, "分箱方式", "省份编码（state，-1 为缺失）")
    tables.append(state_table)
    state_iv = state_table["iv_total"].iloc[0]
    print(f"  省份编码（state）：{len(state_table)} 档，IV = {state_iv:.3f}"
          f"（远超 0.3 的“强区分度”阈值，常见于信息泄露，需警惕）")

    table = pd.concat(tables, ignore_index=True)
    table = table.rename(columns={"label": "区间", "count": "样本数", "sum": "流失数",
                                  "churn_rate": "流失率", "woe": "WOE",
                                  "iv": "IV", "iv_total": "IV合计"})
    table = table.drop(columns=["bad", "good"])   # bad/good 是中间量，不落盘

    print("\n== 4. 入网时长分箱 ==")
    for _, r in table[table["分箱方式"] == "人工分箱（5/12/36 个月）"].iterrows():
        print(f"    {r['区间']:<18} {int(r['样本数']):>4} 人，"
              f"流失率 {r['流失率']:.1%}，WOE {r['WOE']:+.2f}")

    # 四联图：分布 + 三种分箱的流失率曲线
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 7.4))

    ax = axes[0, 0]
    for flag, color, label in [(0, BLUE2, "未流失"), (1, RED, "流失")]:
        sub = df.loc[df["churn"] == flag, "duration_months"]
        ax.hist(sub, bins=30, alpha=0.55, color=color, label=f"{label}（{len(sub)} 人）",
                density=True, edgecolor="white", zorder=3)
    ax.set_title("入网时长的分布（按流失分组）", pad=9, fontsize=11.5)
    ax.set_xlabel("入网时长（月）")
    ax.set_ylabel("密度")
    ax.legend(loc="upper right", fontsize=9)

    panels = [("等宽 5 箱", axes[0, 1], BLUE2),
              ("等频 14 箱", axes[1, 0], GREEN),
              ("人工分箱（5/12/36 个月）", axes[1, 1], ORANGE)]
    for name, ax, color in panels:
        t = table[table["分箱方式"] == name]
        x = np.arange(len(t))
        ax.bar(x, t["流失率"], color=color, width=0.66, zorder=3)
        overall = df["churn"].mean()
        ax.axhline(overall, color=GRAY, linestyle="--", linewidth=1.0)
        ax.annotate(f"整体 {overall:.0%}", (len(t) - 0.5, overall), xytext=(-4, 5),
                    textcoords="offset points", ha="right", fontsize=8.5, color=GRAY)
        ax.set_xticks(x, t["区间"].tolist(), rotation=45, ha="right",
                      fontsize=8 if len(t) <= 6 else 7)
        ax.set_ylim(0, max(t["流失率"].max() * 1.28, 0.35))
        pct_axis(ax)
        ax.set_title(f"{name}（IV={t['IV合计'].iloc[0]:.3f}）", pad=9, fontsize=11.5)
        ax.set_ylabel("流失率")
        ax.set_xlabel("入网时长区间（月）")

    fig.suptitle("分箱方式对比：等宽 / 等频 / 人工，看流失率是否单调",
                 fontsize=13, fontweight="bold", y=1.005)
    fig.tight_layout()
    save_fig(fig, OUT, "fig03_入网时长分箱与流失率")
    save_csv(table, OUT, "table02_分箱与WOE_IV")
    return table


# ---------------------------------------------------------------------------
# 5. 类别编码 + 缺失填补 —— 对应教材 cell 20—24 / 36—37
# ---------------------------------------------------------------------------
def encode_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """填补缺失、做频数编码与 one-hot，得到可入模的数值矩阵。

    教材分别演示了 ``fillna(0)``（并注明"不适用于一般情况"）、
    ``SimpleImputer(strategy='most_frequent')``、``Binarizer``、``get_dummies``、
    ``OneHotEncoder`` 五种写法。这里按字段性质分别处理，而不是一律填 0：

      * ``state``：只有 65 行缺失（2.2%），用**众数**填补，并保留一个
        ``state_missing`` 标记位——"没登记省份"本身可能就是风险信号；
      * ``IMEI``：缺失 77%，绝不能填 0 后当成真实值（0 不是合法 IMEI）。
        正确做法是 ``Binarizer`` 思路：只保留"有没有登记 IMEI"这个二值特征；
      * ``product``：91 个取值、且大部分只出现几次，直接 one-hot 会炸出 90 列，
        改用**频数编码**（该产品被多少客户订购），再用 top 8 + "其他" 做 one-hot。

    ``vip`` 的方差只有 0.0076，低于教材里 ``VarianceThreshold(0.09)`` 的阈值，
    这就是下一步方差过滤要把它筛掉的原因。
    """
    df = df.copy()

    # state：众数填补 + 缺失标记
    df["state_missing"] = df["state"].isna().astype(int)
    state_mode = df["state"].mode().iloc[0]
    df["state"] = df["state"].fillna(state_mode)
    df["state_code"] = df["state"].astype(int)

    # IMEI：只保留"是否登记"这个二值特征
    df["has_IMEI"] = (df["IMEI"].fillna(0) > 0).astype(int)

    # product：频数编码 + top 8 one-hot
    freq = df["product"].value_counts()
    df["product_freq"] = df["product"].map(freq).astype(int)
    top_products = freq.head(8).index.tolist()
    df["product_group"] = df["product"].where(df["product"].isin(top_products), -1)

    # 类别列 one-hot：state 8 档、product 9 档（top8 + 其他）、vip / has_IMEI
    cat_cols = ["state_code", "product_group", "vip", "has_IMEI"]
    dummies = pd.get_dummies(
        df[cat_cols].astype("category"), prefix=["state", "prod", "vip", "imei"],
        dtype=float,
    )
    # 只保留真正出现过的列，避免生成全 0 的哑变量
    dummies = dummies.loc[:, dummies.sum() > 0]
    df = pd.concat([df, dummies], axis=1)

    print("\n== 5. 编码与缺失填补 ==")
    print(f"  state 缺失 {int(df['state_missing'].sum())} 行，用众数 {int(state_mode)} 填补，"
          f"并保留 state_missing 标记")
    print(f"  IMEI 缺失率 {df['IMEI'].isna().mean():.1%}，不填 0，改为二值特征 has_IMEI"
          f"（有登记 {int(df['has_IMEI'].sum())} 人）")
    print(f"  product 共 {len(freq)} 个取值，频数编码 + top8 one-hot；"
          f"共生成 {dummies.shape[1]} 个哑变量")

    # 编码完顺手看一眼几个"可疑"特征和 churn 的关系，这决定了后面要不要警惕信息泄露
    state_churn = df.groupby("state_code")["churn"].mean().sort_index()
    zero_expd = df["expenditure"] == 0
    print("  按省份编码的流失率：" + "，".join(
        f"state={int(k)} {v:.0%}" for k, v in state_churn.items()))
    print(f"  零消费客户 {int(zero_expd.sum())} 人（{zero_expd.mean():.1%}），"
          f"其流失率 {df.loc[zero_expd, 'churn'].mean():.1%}，"
          f"非零消费仅 {df.loc[~zero_expd, 'churn'].mean():.1%}")
    print(f"  有 IMEI 登记的人流失率 {df.loc[df['has_IMEI'] == 1, 'churn'].mean():.1%}，"
          f"无登记 {df.loc[df['has_IMEI'] == 0, 'churn'].mean():.1%}")

    numeric_cols = ["duration_months", "log_expd", "log_call", "log_traffic", "unit_price"]
    return df, numeric_cols, list(dummies.columns)


# ---------------------------------------------------------------------------
# 6. 相关性热力图
# ---------------------------------------------------------------------------
def correlation_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """画核心数值特征与 churn 的相关矩阵，找共线与强相关特征。

    相关性在这里干两件事：

      * **找强相关特征**：expenditure / call / traffic 三个 log 变量彼此高度相关，
        说明它们本质是"消费强度"一个维度，树模型能容忍，线性模型就要考虑去掉；
      * **初筛**：与 churn 相关系数接近 0 的字段，单变量几乎没有区分度，
        但注意——**相关为 0 不代表无用**，可能是非线性关系（这正是后面要用
        随机森林重要性的原因）。
    """
    cols = {
        "duration_months": "入网月数",
        "log_expd": "log 消费金额",
        "log_call": "log 通话时长",
        "log_traffic": "log 流量",
        "unit_price": "单位流量单价",
        "vip": "VIP 标记",
        "has_IMEI": "登记 IMEI",
        "product_freq": "产品频数",
        "state_code": "省份编码",
        "churn": "是否流失",
    }
    corr = df[list(cols)].rename(columns=cols).corr()

    print("\n== 6. 相关性 ==")
    target_corr = corr["是否流失"].drop("是否流失").sort_values(key=abs, ascending=False)
    print("  与 churn 相关性最强的 4 个特征："
          + "，".join(f"{k} {v:+.3f}" for k, v in target_corr.head(4).items()))
    print("  特征间最强共线："
          + "，".join(f"{a}×{b} {corr.loc[a, b]:+.2f}"
                     for a, b in [("log 消费金额", "log 通话时长"),
                                  ("log 通话时长", "log 流量"),
                                  ("log 消费金额", "log 流量")]))

    fig, ax = new_fig(8.6, 6.8)
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                vmin=-1, vmax=1, square=True, linewidths=0.6,
                annot_kws={"fontsize": 8}, cbar_kws={"shrink": 0.78, "label": "相关系数"},
                ax=ax)
    ax.set_title("核心特征相关性矩阵（下三角）", pad=12)
    ax.tick_params(axis="x", rotation=32, labelsize=9)
    ax.tick_params(axis="y", rotation=0, labelsize=9)
    save_fig(fig, OUT, "fig04_特征相关性热力图")
    return corr


# ---------------------------------------------------------------------------
# 7. 特征筛选：方差 / 统计检验 / 模型重要性 —— 对应教材 cell 61—82
# ---------------------------------------------------------------------------
def select_features(df: pd.DataFrame, numeric_cols: list[str],
                    dummy_cols: list[str]) -> pd.DataFrame:
    """用三种口径给特征打分，再合并成一张"谁该留、谁该删"的表。

    教材把三种方法各写了一段：

      * ``VarianceThreshold(0.09)``：方差太小的特征（几乎不变）没有信息量；
      * ``chi2`` / ``f_classif``：类别特征用卡方、连续特征用 ANOVA，
        检验"该特征不同取值下的流失率是否显著不同"；
      * ``RandomForestClassifier.feature_importances_``：模型视角的重要性，
        能捕捉非线性和交互，但会偏向取值多的连续变量。

    三者结论经常不一致，这里**并列**而不是只信一个：
    方差过滤负责删"死特征"，统计检验负责单变量显著性，模型重要性负责联合贡献。
    最终保留规则写在 ``是否保留`` 列里（三种口径投票）。
    """
    feature_cols = numeric_cols + dummy_cols
    X = df[feature_cols].astype(float)
    y = df["churn"].astype(int)

    # 7.1 方差过滤（教材 cell 61）
    variances = X.var(ddof=0)

    # 7.2 单变量检验：类别（0/1 或 one-hot）用卡方，连续变量用 ANOVA F
    rows = []
    for col in feature_cols:
        is_binary = X[col].nunique() <= 2
        if is_binary:
            stat, p = chi2(X[[col]], y)
            method = "卡方"
        else:
            stat, p = f_classif(X[[col]], y)
            method = "ANOVA F"
        rows.append({"特征": col, "类型": "类别/二值" if is_binary else "连续",
                     "方差": variances[col], "检验方法": method,
                     "检验统计量": float(stat[0]), "p 值": float(p[0]),
                     "与churn相关": float(np.corrcoef(X[col], y)[0, 1])})
    table = pd.DataFrame(rows)

    # 7.3 随机森林重要性（教材 cell 80）：用 class_weight 抵消 26% / 74% 的不平衡
    rf = RandomForestClassifier(n_estimators=400, min_samples_leaf=5,
                                class_weight="balanced", random_state=42, n_jobs=-1)
    rf.fit(X, y)
    table["RF重要性"] = rf.feature_importances_
    table = table.sort_values("RF重要性", ascending=False).reset_index(drop=True)
    table["排名"] = np.arange(1, len(table) + 1)
    table["累计重要性"] = table["RF重要性"].cumsum()

    # 三种口径不一定一致，这里显式区分"该删"和"拿不准"两种情况：
    #   * 方差过低 + 重要性排名不进前 15 → 基本可以删；
    #   * 方差过低但模型很依赖它（例如稀有省份哑变量，样本少所以方差小）→ 保留但标注观察；
    #   * 单变量检验不显著、模型也不看重 → 删。
    def _verdict(r) -> str:
        low_var = r["方差"] < 0.09
        weak_test = r["p 值"] >= 0.05
        low_rank = r["排名"] > 15
        if low_var and low_rank:
            return "建议剔除"
        if low_var:
            return "观察（方差低但模型依赖）"
        if weak_test and low_rank:
            return "建议剔除"
        return "保留"

    table["建议"] = table.apply(_verdict, axis=1)

    print("\n== 7. 特征筛选 ==")
    print(f"  候选特征 {len(table)} 个（连续 {len(numeric_cols)} + 哑变量 {len(dummy_cols)}）")
    dead = table[table["方差"] < 0.09]
    if len(dead):
        print(f"  方差 < 0.09 的特征 {len(dead)} 个："
              + "、".join(dead["特征"].tolist()[:6]))
    else:
        print("  没有方差过低的特征")
    sig = int((table["p 值"] < 0.05).sum())
    print(f"  单变量检验 p < 0.05 的特征 {sig} 个（占 {sig / len(table):.0%}）")
    print("  随机森林重要性 Top 8：")
    for _, r in table.head(8).iterrows():
        print(f"    {r['特征']:<16} 重要性 {r['RF重要性']:.4f}，"
              f"p={r['p 值']:.4f}，{r['建议']}")
    print(f"  Top 15 特征累计解释 {table.loc[14, '累计重要性']:.1%} 的重要性")

    # 7.4 Top15 重要性条形图
    top = table.head(15).iloc[::-1]
    colors = [ORANGE if t == "连续" else BLUE2 for t in top["类型"]]
    fig, ax = new_fig(9.6, 6.4)
    y_pos = np.arange(len(top))
    ax.barh(y_pos, top["RF重要性"], color=colors, height=0.68, zorder=3)
    ax.set_yticks(y_pos, top["特征"])
    for yi, v in zip(y_pos, top["RF重要性"]):
        ax.annotate(f"{v:.3f}", (v, yi), xytext=(3, 0), textcoords="offset points",
                    va="center", fontsize=8.5)
    ax.set_xlim(0, top["RF重要性"].max() * 1.18)
    ax.set_title("随机森林特征重要性 Top 15（橙=连续变量，蓝=类别哑变量）", pad=12)
    ax.set_xlabel("重要性（impurity-based）")
    ax.set_ylabel("")
    ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=ORANGE),
               plt.Rectangle((0, 0), 1, 1, fc=BLUE2)]
    ax.legend(handles, ["连续变量", "类别哑变量"], loc="lower right", fontsize=9)
    save_fig(fig, OUT, "fig05_特征重要性Top15")

    save_csv(table.round(4), OUT, "table03_特征筛选汇总")
    return table


def main() -> None:
    apply_style()
    df = load_data()
    data_health(df)
    df = treat_numeric(df)
    df = build_date_features(df)
    bin_table = binning_analysis(df)
    df, numeric_cols, dummy_cols = encode_features(df)
    correlation_heatmap(df)
    table = select_features(df, numeric_cols, dummy_cols)

    top1 = table.iloc[0]
    kept = int((table["建议"] == "保留").sum())
    watch = int(table["建议"].str.startswith("观察").sum())

    manual = bin_table[bin_table["分箱方式"] == "人工分箱（5/12/36 个月）"]
    manual_iv = manual["IV合计"].iloc[0]
    risk_bin = manual.loc[manual["流失率"].idxmax()]
    young = df.loc[df["duration_months"] <= 5, "churn"].mean()
    old = df.loc[df["duration_months"] > 36, "churn"].mean()

    print("\n" + "=" * 70)
    print("业务结论（可直接用于报告）")
    print("=" * 70)
    print(f"1. 数据体检：{len(df)} 行中 churn 占 {df['churn'].mean():.1%}；"
          f"IMEI 缺失 {df['IMEI'].isna().mean():.1%}（只能做“是否登记”二值特征），"
          f"state 缺失 {df['state_missing'].mean():.1%}（众数填补 + 缺失标记）。")
    print(f"2. 入网时长是强特征：人工分箱 IV={manual_iv:.3f}，"
          f"流失率最高的是「{risk_bin['区间']}」这一档（{risk_bin['流失率']:.1%}），"
          f"5 个月内 {young:.1%}、超过 36 个月只有 {old:.1%}——"
          f"风险窗口不在“刚入网”，而在入网 1—3 年的续约期。")
    print(f"3. 消费类变量右偏严重（expenditure 偏度 "
          f"{df['expenditure'].skew():.2f}），3σ 缩尾 + log1p 后降到 "
          f"{df['log_expd'].skew():.2f}，标准化与相关性分析才可信。")
    print(f"4. 三种筛选口径投票后保留 {kept}/{len(table)} 个特征、{watch} 个待观察；"
          f"最重要的是 {top1['特征']}（重要性 {top1['RF重要性']:.3f}），"
          f"Top 15 累计解释 {table.loc[14, '累计重要性']:.1%} 的重要性。")
    print("5. 建议：线上模型用入网时长 + 消费强度 + 是否有 IMEI 三类特征即可，"
          "product 的 one-hot 贡献有限，可降级为频数编码以控制维度。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
