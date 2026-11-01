"""03_analysis.py —— 商业分析模型

六个模型（要求 >= 3 个）：
  M1 RFM 八分类            —— 客户价值分层，R/F/M 均按中位数二分
  M2 同期群留存             —— 按首购月分群，观测 12 个月留存
  M3 关联规则（Apriori）    —— 英国市场购物篮，min_support=1%、lift>=1.2
  M4 SARIMA 销售额预测      —— 日粒度 + 周季节性(m=7)，95% 置信区间 + 回测 MAPE/RMSE
  M5 帕累托 / ABC 分类      —— 客户贡献与 SKU 贡献
  M6 波士顿矩阵            —— SKU 份额 × 增速四象限

全部结果落 outputs/tables/，指标汇总到 analysis_results.json
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_CLEAN, TBL_DIR, dump_json, save_table  # noqa: E402

warnings.filterwarnings("ignore")
REF_DATE = pd.Timestamp("2011-12-10")  # 数据最后一天 2011-12-09 的次日

RESULT: dict = {}


# ------------------------------------------------------------------ M1 RFM
def build_rfm(tx: pd.DataFrame) -> pd.DataFrame:
    rfm = (tx.groupby("CustomerID")
             .agg(R=("InvoiceDate", lambda s: (REF_DATE - s.max()).days),
                  F=("InvoiceNo", "nunique"),
                  M=("Revenue", "sum"))
             .reset_index())
    r_med, f_med, m_med = rfm["R"].median(), rfm["F"].median(), rfm["M"].median()
    # R 越小越近，故「近」= R <= 中位数
    rfm["R_high"] = rfm["R"] <= r_med
    rfm["F_high"] = rfm["F"] >= f_med
    rfm["M_high"] = rfm["M"] >= m_med

    def seg(row):
        r, f, m = row["R_high"], row["F_high"], row["M_high"]
        if m:
            return ("重要价值客户" if r and f else
                    "重要发展客户" if r and not f else
                    "重要保持客户" if not r and f else "重要挽留客户")
        return ("一般价值客户" if r and f else
                "一般发展客户" if r and not f else
                "一般保持客户" if not r and f else "一般挽留客户")

    rfm["Segment"] = rfm.apply(seg, axis=1)
    rfm["AvgOrder"] = rfm["M"] / rfm["F"]
    order = ["重要价值客户", "重要发展客户", "重要保持客户", "重要挽留客户",
             "一般价值客户", "一般发展客户", "一般保持客户", "一般挽留客户"]
    rfm["Segment"] = pd.Categorical(rfm["Segment"], categories=order, ordered=True)

    summary = (rfm.groupby("Segment", observed=True)
                  .agg(客户数=("CustomerID", "count"),
                       销售额=("M", "sum"),
                       客单价=("AvgOrder", "mean"),
                       平均R=("R", "mean"),
                       平均F=("F", "mean"))
                  .reset_index())
    summary["客户占比"] = summary["客户数"] / summary["客户数"].sum()
    summary["销售额占比"] = summary["销售额"] / summary["销售额"].sum()
    save_table(summary, "rfm_segment_summary.csv")
    save_table(rfm, "rfm_customer_level.csv")

    RESULT["rfm"] = {
        "thresholds": {"R_median_days": float(r_med), "F_median": float(f_med), "M_median": float(m_med)},
        "top_segment": summary.sort_values("销售额", ascending=False).iloc[0]["Segment"],
        "top_segment_rev_share": float(summary["销售额"].max() / summary["销售额"].sum()),
        "vip_share": float(summary.loc[summary["Segment"] == "重要价值客户", "客户占比"].sum()),
        "vip_rev_share": float(summary.loc[summary["Segment"] == "重要价值客户", "销售额占比"].sum()),
        "segments": summary.round(4).to_dict("records"),
    }
    print(f"[M1] RFM 阈值 R={r_med:.0f}天 F={f_med:.0f}次 M={m_med:,.0f}英镑；"
          f"八分群最大群体 = {RESULT['rfm']['top_segment']}")
    return rfm


# --------------------------------------------------------------- M2 同期群
def build_cohort(tx: pd.DataFrame) -> pd.DataFrame:
    first = tx.groupby("CustomerID")["InvoiceDate"].min().dt.to_period("M")
    d = tx[["CustomerID", "InvoiceDate"]].copy()
    d["Cohort"] = d["CustomerID"].map(first)
    d["Month"] = d["InvoiceDate"].dt.to_period("M")
    d["Offset"] = (d["Month"] - d["Cohort"]).apply(lambda x: x.n)
    sizes = d.groupby("Cohort")["CustomerID"].nunique()
    mat = (d.groupby(["Cohort", "Offset"])["CustomerID"].nunique()
             .unstack(fill_value=0)
             .reindex(columns=range(0, 12), fill_value=0))
    ret = mat.div(sizes, axis=0).round(4)
    ret.index = ret.index.astype(str)
    save_table(ret.reset_index().rename(columns={"index": "首购月"}), "cohort_retention.csv")
    save_table(mat.reset_index().rename(columns={"index": "首购月"}), "cohort_counts.csv")

    m1 = ret[1].mean()
    m11 = ret[11].dropna().mean() if 11 in ret else np.nan
    RESULT["cohort"] = {
        "cohorts": int(len(ret)),
        "avg_m1_retention": float(m1),
        "avg_m11_retention": float(m11),
        "decay": float(m1 - m11),
        "best_cohort": str(ret[1].idxmax()),
    }
    print(f"[M2] 同期群 {len(ret)} 个；次月留存均值 {m1:.1%}；第 11 月留存 {m11:.1%}")
    return ret


# ------------------------------------------------------------ M3 关联规则
def build_rules(tx: pd.DataFrame) -> pd.DataFrame:
    from mlxtend.frequent_patterns import apriori, association_rules
    from mlxtend.preprocessing import TransactionEncoder

    uk = tx[tx["Country"] == "United Kingdom"]
    baskets = uk.groupby("InvoiceNo")["StockCode"].apply(lambda s: sorted(set(s)))
    baskets = baskets[baskets.map(len) >= 2]
    print(f"[M3] 英国订单 {len(uk):,} 行 -> {len(baskets):,} 张多品订单，构建 one-hot ...")

    te = TransactionEncoder()
    arr = te.fit(baskets.values).transform(baskets.values, sparse=True)
    support = np.asarray(arr.mean(axis=0)).ravel()
    keep_mask = support >= 0.01
    cols_kept = np.array(te.columns_)[keep_mask]
    hot = pd.DataFrame.sparse.from_spmatrix(arr[:, keep_mask], columns=cols_kept)
    print(f"[M3] 保留支持度>=1% 的 {hot.shape[1]} 个 SKU，矩阵 {hot.shape}")

    freq = apriori(hot.astype(bool), min_support=0.01, use_colnames=True, max_len=3, low_memory=True)
    freq["length"] = freq["itemsets"].map(len)
    rules = association_rules(freq, metric="lift", min_threshold=1.2)
    rules = rules[rules["confidence"] >= 0.3].copy()
    rules["count"] = (rules["support"] * len(baskets)).round().astype(int)
    rules = rules[rules["count"] >= 15]
    rules = rules.sort_values(["lift", "support"], ascending=False).reset_index(drop=True)
    rules["antecedent"] = rules["antecedents"].map(lambda s: " + ".join(sorted(s)))
    rules["consequent"] = rules["consequents"].map(lambda s: " + ".join(sorted(s)))
    cols = ["antecedent", "consequent", "support", "confidence", "lift", "count"]
    out = rules[cols].round(4).head(200)
    desc = tx.drop_duplicates("StockCode").set_index("StockCode")["Description"].to_dict()

    def _name(code: str) -> str:
        return str(desc.get(code, code))[:18]

    out["antecedent_name"] = out["antecedent"].map(lambda s: " + ".join(_name(x) for x in s.split(" + ")))
    out["consequent_name"] = out["consequent"].map(lambda s: " + ".join(_name(x) for x in s.split(" + ")))
    save_table(out, "association_rules.csv")

    RESULT["rules"] = {
        "baskets": int(len(baskets)),
        "n_rules": int(len(rules)),
        "max_lift": float(rules["lift"].max()) if len(rules) else 0,
        "top_rule": f"{out.iloc[0]['antecedent']} -> {out.iloc[0]['consequent']}" if len(out) else "",
        "top_lift": float(out.iloc[0]["lift"]) if len(out) else 0,
        "support_threshold": 0.01,
        "lift_threshold": 1.2,
        "confidence_threshold": 0.3,
    }
    print(f"[M3] 频繁项集 {len(freq)}，规则 {len(rules)} 条，最高提升度 {rules['lift'].max():.2f}"
          if len(rules) else "[M3] 无规则")
    return out


# --------------------------------------------------------------- M4 SARIMA
def build_forecast(tx: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    import statsmodels.api as sm

    daily = tx.groupby("Date")["Revenue"].sum().asfreq("D").fillna(0.0)
    y = np.log1p(daily.values)
    idx = daily.index
    test_n = 56
    train, test = y[:-test_n], y[-test_n:]
    order, sorder = (1, 1, 1), (0, 1, 1, 7)

    def _ci(obj):
        ci = obj.conf_int(alpha=0.05)
        return np.asarray(ci)

    m = sm.tsa.statespace.SARIMAX(train, order=order, seasonal_order=sorder,
                                  enforce_stationarity=False, enforce_invertibility=False)
    fit = m.fit(disp=False)
    pred = fit.get_forecast(steps=test_n)
    pred_mean = np.expm1(pred.predicted_mean)
    pred_ci = np.expm1(_ci(pred))
    actual = np.expm1(test)

    valid = actual > 0
    mape = float(np.mean(np.abs((actual[valid] - pred_mean[valid]) / actual[valid])) * 100)
    rmse = float(np.sqrt(np.mean((actual - pred_mean) ** 2)))
    smape = float(np.mean(2 * np.abs(actual - pred_mean) / (np.abs(actual) + np.abs(pred_mean) + 1e-9)) * 100)

    # 基准：季节性朴素法（同星期几上周实际值），用于证明模型确实有增量价值
    naive = np.expm1(np.concatenate([y[-test_n - 7:-7]]))
    naive_mape = float(np.mean(np.abs((actual[valid] - naive[valid]) / actual[valid])) * 100)
    naive_rmse = float(np.sqrt(np.mean((actual - naive) ** 2)))
    bias_pct = float((pred_mean.sum() - actual.sum()) / actual.sum() * 100)

    # 全量重估后再预测未来 28 天
    m2 = sm.tsa.statespace.SARIMAX(y, order=order, seasonal_order=sorder,
                                   enforce_stationarity=False, enforce_invertibility=False)
    fit2 = m2.fit(disp=False)
    fut = fit2.get_forecast(steps=28)
    fut_ci = _ci(fut)
    future = pd.DataFrame({
        "date": pd.date_range(daily.index[-1] + pd.Timedelta(days=1), periods=28),
        "forecast": np.expm1(fut.predicted_mean),
        "lower95": np.clip(np.expm1(fut_ci[:, 0]), 0, None),
        "upper95": np.expm1(fut_ci[:, 1]),
    })
    backtest = pd.DataFrame({
        "date": idx[-test_n:], "actual": actual, "pred": pred_mean,
        "lower95": pred_ci[:, 0], "upper95": pred_ci[:, 1],
    })
    save_table(future.round(2), "sarima_forecast.csv")
    save_table(backtest.round(2), "sarima_backtest.csv")

    RESULT["sarima"] = {
        "order": f"SARIMA{order}x{sorder}", "aic": round(float(fit.aic), 2),
        "train_days": int(len(train)), "test_days": int(test_n),
        "mape": round(mape, 2), "rmse": round(rmse, 2), "smape": round(smape, 2),
        "naive_mape": round(naive_mape, 2), "naive_rmse": round(naive_rmse, 2),
        "mape_gain_vs_naive": round(naive_mape - mape, 2),
        "bias_pct": round(bias_pct, 2),
        "mape_note": "MAPE 仅在交易日（实际销售额>0）上计算，周六门店歇业导致分母为 0",
        "forecast_sum_28d": round(float(future["forecast"].sum()), 2),
        "series_days": int(len(daily)),
    }
    print(f"[M4] SARIMA{order}x{sorder} AIC={fit.aic:.0f} 回测 MAPE={mape:.1f}% "
          f"RMSE={rmse:,.0f} sMAPE={smape:.1f}% ｜ 季节朴素法 MAPE={naive_mape:.1f}%")
    return future, backtest


# ------------------------------------------------------- M5 帕累托 / ABC
def build_pareto(tx: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    c = customers.sort_values("Revenue", ascending=False).reset_index(drop=True)
    c["rev_share"] = c["Revenue"] / c["Revenue"].sum()
    c["cum_share"] = c["rev_share"].cumsum()
    c["rank_pct"] = (c.index + 1) / len(c)
    c["ABC"] = np.where(c["cum_share"] <= 0.7, "A", np.where(c["cum_share"] <= 0.9, "B", "C"))
    n80 = int((c["cum_share"] < 0.8).sum() + 1)
    save_table(c[["CustomerID", "Revenue", "rev_share", "cum_share", "ABC"]].round(6), "pareto_customers.csv")

    sku = (tx.groupby("StockCode")["Revenue"].sum().sort_values(ascending=False)
             .to_frame().reset_index())
    sku["cum_share"] = sku["Revenue"].cumsum() / sku["Revenue"].sum()
    sku["ABC"] = np.where(sku["cum_share"] <= 0.7, "A", np.where(sku["cum_share"] <= 0.9, "B", "C"))
    save_table(sku.round(6), "abc_skus.csv")

    abc = c.groupby("ABC").agg(客户数=("CustomerID", "count"), 销售额=("Revenue", "sum")).reset_index()
    abc["客户占比"] = abc["客户数"] / abc["客户数"].sum()
    abc["销售额占比"] = abc["销售额"] / abc["销售额"].sum()
    save_table(abc.round(4), "abc_summary.csv")

    RESULT["pareto"] = {
        "n_customers": int(len(c)),
        "customers_for_80pct": n80,
        "share_of_customers_for_80pct": round(n80 / len(c), 4),
        "top1pct_share": round(float(c["cum_share"].iloc[max(0, int(len(c) * 0.01) - 1)]), 4),
        "top10pct_share": round(float(c["cum_share"].iloc[int(len(c) * 0.10) - 1]), 4),
        "sku_A_share": round(float(sku.loc[sku["ABC"] == "A", "Revenue"].sum() / sku["Revenue"].sum()), 4),
        "sku_A_count": int((sku["ABC"] == "A").sum()),
    }
    print(f"[M5] {RESULT['pareto']['share_of_customers_for_80pct']:.1%} 客户贡献 80% 销售额；"
          f"前 10% 客户贡献 {RESULT['pareto']['top10pct_share']:.1%}")
    return c


# ---------------------------------------------------------- M6 波士顿矩阵
def build_bdc(tx: pd.DataFrame) -> pd.DataFrame:
    h1 = tx[tx["Month"] <= "2011-06"]
    h2 = tx[tx["Month"] >= "2011-07"]
    g = pd.DataFrame({
        "h1": h1.groupby("StockCode")["Revenue"].sum(),
        "h2": h2.groupby("StockCode")["Revenue"].sum(),
    }).fillna(0)
    g = g[(g["h1"] + g["h2"]) > 0]
    g["total"] = g["h1"] + g["h2"]
    g = g.sort_values("total", ascending=False).head(60).copy()
    g["share"] = g["total"] / tx["Revenue"].sum()
    g["growth"] = np.where(g["h1"] > 0, (g["h2"] - g["h1"]) / g["h1"], np.nan)
    g = g.dropna(subset=["growth"])
    g["growth"] = g["growth"].clip(-1, 3)

    med_share = g["share"].median()
    g["quadrant"] = np.select(
        [(g["share"] >= med_share) & (g["growth"] >= 0),
         (g["share"] >= med_share) & (g["growth"] < 0),
         (g["share"] < med_share) & (g["growth"] >= 0),
         (g["share"] < med_share) & (g["growth"] < 0)],
        ["明星", "金牛", "问题", "瘦狗"], default="瘦狗")

    desc = tx.drop_duplicates("StockCode").set_index("StockCode")["Description"].to_dict()
    g["Description"] = g.index.map(desc)
    out = g.reset_index()[["StockCode", "Description", "share", "growth", "total", "quadrant"]]
    out.columns = ["StockCode", "Description", "份额", "增速", "销售额", "象限"]
    save_table(out.round(4), "bdc_matrix.csv")

    q = out.groupby("象限").agg(SKU数=("StockCode", "count"), 销售额=("销售额", "sum")).reset_index()
    save_table(q.round(2), "bdc_summary.csv")
    RESULT["bdc"] = {
        "sku_analyzed": int(len(out)),
        "median_share": float(med_share),
        "quadrants": q.round(4).to_dict("records"),
        "star_share": float(out.loc[out["象限"] == "明星", "销售额"].sum() / out["销售额"].sum()),
    }
    print(f"[M6] 波士顿矩阵 {len(out)} 个 SKU；明星 {RESULT['bdc']['star_share']:.1%}")
    return out


# ------------------------------------------------------------- 时间序列聚合
def build_trends(tx: pd.DataFrame) -> None:
    monthly = (tx.groupby("Month").agg(销售额=("Revenue", "sum"),
                                      订单数=("InvoiceNo", "nunique"),
                                      客户数=("CustomerID", "nunique"))
                 .reset_index())
    monthly["环比"] = monthly["销售额"].pct_change().round(4)
    monthly["客单价"] = (monthly["销售额"] / monthly["订单数"]).round(2)
    save_table(monthly.round(2), "monthly_trend.csv")

    weekly = tx.groupby("Week")["Revenue"].sum().reset_index().rename(columns={"Revenue": "销售额"})
    save_table(weekly.round(2), "weekly_trend.csv")

    daily = tx.groupby("Date")["Revenue"].sum().reset_index().rename(columns={"Revenue": "销售额"})
    save_table(daily.round(2), "daily_trend.csv")

    dow = (tx.groupby("DOW").agg(销售额=("Revenue", "sum"), 订单数=("InvoiceNo", "nunique")).reset_index())
    dow["星期"] = dow["DOW"].map(dict(enumerate(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])))
    save_table(dow.round(2), "weekday_trend.csv")

    hourly = tx.groupby("Hour").agg(销售额=("Revenue", "sum"), 订单数=("InvoiceNo", "nunique")).reset_index()
    save_table(hourly.round(2), "hourly_trend.csv")

    country = tx.groupby("Country").agg(销售额=("Revenue", "sum"),
                                        订单数=("InvoiceNo", "nunique"),
                                        客户数=("CustomerID", "nunique")).reset_index()
    country = country.sort_values("销售额", ascending=False)
    country["占比"] = (country["销售额"] / country["销售额"].sum()).round(4)
    save_table(country.round(2), "country_summary.csv")

    sku = tx.groupby("StockCode").agg(销售额=("Revenue", "sum"),
                                      销量=("Quantity", "sum"),
                                      订单数=("InvoiceNo", "nunique")).reset_index()
    desc = tx.drop_duplicates("StockCode").set_index("StockCode")["Description"].to_dict()
    sku["Description"] = sku["StockCode"].map(desc)
    sku = sku.sort_values("销售额", ascending=False)
    save_table(sku.head(100).round(2), "sku_top100.csv")

    RESULT["trend"] = {
        "months": int(len(monthly)),
        "total_revenue": round(float(tx["Revenue"].sum()), 2),
        "best_month": str(monthly.loc[monthly["销售额"].idxmax(), "Month"]),
        "best_month_revenue": round(float(monthly["销售额"].max()), 2),
        "worst_month": str(monthly.loc[monthly["销售额"].idxmin(), "Month"]),
        "avg_monthly": round(float(monthly["销售额"].mean()), 2),
        "peak_weekday": str(dow.loc[dow["销售额"].idxmax(), "星期"]),
        "peak_hour": int(hourly.loc[hourly["销售额"].idxmax(), "Hour"]),
        "uk_share": float(country.iloc[0]["占比"]),
        "countries": int(len(country)),
        "avg_order_value": round(float(tx["Revenue"].sum() / tx["InvoiceNo"].nunique()), 2),
        "items_per_order": round(float(len(tx) / tx["InvoiceNo"].nunique()), 2),
        "monthly": monthly.round(2).to_dict("records"),
    }
    print(f"[趋势] {len(monthly)} 个月，合计 {tx['Revenue'].sum():,.0f} 英镑，"
          f"最佳 {RESULT['trend']['best_month']}")


def main() -> None:
    print("=" * 78)
    print("03_analysis —— 商业分析模型")
    print("=" * 78)
    tx = pd.read_parquet(DATA_CLEAN / "transactions.parquet")
    customers = pd.read_csv(DATA_CLEAN / "customers.csv")

    build_trends(tx)
    build_rfm(tx)
    build_cohort(tx)
    build_rules(tx)
    build_forecast(tx)
    build_pareto(tx, customers)
    build_bdc(tx)

    dump_json(RESULT, "analysis_results.json")
    print("=" * 78)
    print("03_analysis 完成 -> outputs/tables/analysis_results.json")


if __name__ == "__main__":
    main()
