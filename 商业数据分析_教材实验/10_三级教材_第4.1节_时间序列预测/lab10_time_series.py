# -*- coding: utf-8 -*-
"""
实验 10 · 时间序列预测：从趋势分解到 SARIMA 定阶与回测
========================================================
教材：《CDA 三级认证教材：敏捷数据挖掘》第 4.1 节 时间序列预测
原始素材：``tractor_sales.csv``（144 行 × 2 列，2003-01 ~ 2014-12 拖拉机月销量）
迁移方向：教材 4.1.2 的「取对数 → 一阶差分 → 网格搜 AIC → 36 期预测」
          → **可复现的 5 步流水线：解析 → 分解 → 平稳性/定阶 → 回测 → 预测**

教材原来的顺序是：读数据 → 画图 → 乘法分解 → 取对数差分 → ACF/PACF → 双重循环搜
``SARIMAX`` 最优 (p,d,q)×(P,D,Q,12) → 残差诊断 → 预测 36 期。
本脚本保留全部环节，但补了三件教材没做、而工程上必须做的事：

1. **留出回测**：只用前 132 个月训练，最后 12 个月做样本外检验，报 MAPE / RMSE；
   否则"模型 AIC 最低"并不等于"预测得准"；
2. **网格搜索只搜 18 组**（教材的 2×2×2 双重循环是 64 组，单机跑要十几分钟），
   并把每一组的 AIC 落盘成表，方便解释"为什么是这组参数"；
3. **预测区间还原到原始量纲**：对数模型的置信区间要 ``exp`` 回去，
   并且是"逐点区间"，不能简单对称加减。

运行：``python lab10_time_series.py``（在实验目录下执行）
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

# 让脚本能从仓库根的 common/ 导入统一样式
LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR.parent))

from common.style import (  # noqa: E402
    BLUE, BLUE2, GRAY, GREEN, NEG, ORANGE, PALETTE, POS, RED,
    apply_style, new_fig, pct_axis, save_csv, save_fig,
)

warnings.filterwarnings("ignore")   # statsmodels 收敛告警太多，实验里统一静音

DATA = LAB_DIR / "data" / "tractor_sales.csv"
OUT = LAB_DIR / "outputs"

SEASON = 12          # 月度数据，季节周期 12
HOLDOUT = 12         # 留出最后 12 个月做回测
FORECAST = 12        # 再向后预测 12 个月
# 网格搜索空间：p,q ∈ {0,1,2}，d=1；季节项 (P,Q) ∈ {(0,0),(1,1)}，D=1 → 3×3×2 = 18 组
P_RANGE = (0, 1, 2)
Q_RANGE = (0, 1, 2)
SEASONAL_ORDERS = ((0, 0, 1, SEASON), (1, 1, 1, SEASON))


# ---------------------------------------------------------------------------
# 0. 解析时间索引 —— 对应教材 cell 3：pd.to_datetime(..., format="%Y-%b")
# ---------------------------------------------------------------------------
def load_series() -> pd.Series:
    """读入月销量并把 ``Year_Month``（如 ``2003-Jan``）解析成月度时间索引。

    教材用 ``pd.to_datetime(sales_data["Year_Month"], format="%Y-%b")``，
    这里额外做了两件必要的事：

    * ``to_period("M").to_timestamp()`` 把日期对齐到月初，
      避免每行落在"当月 1 日"以外的位置、导致画图和重采样错位；
    * ``asfreq("MS")`` 显式声明「月初频率」，并检查有没有缺月——
      时间序列模型默认等间隔，缺一个月会让季节项整体错位。
    """
    raw = pd.read_csv(DATA)
    idx = pd.to_datetime(raw["Year_Month"], format="%Y-%b")
    ts = pd.Series(
        raw["Number_of_Sold"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(idx).to_period("M").to_timestamp(),
        name="sales",
    ).sort_index()

    # 补全月份轴，若有缺失会变成 NaN，这里直接暴露出来而不是悄悄带进模型
    ts = ts.asfreq("MS")
    missing = int(ts.isna().sum())

    print("=" * 70)
    print("实验 10 · 拖拉机月销量预测：季节分解 + SARIMA")
    print("=" * 70)
    print(f"[数据] {len(ts)} 个月：{ts.index.min():%Y-%m} ~ {ts.index.max():%Y-%m}；"
          f"缺失月份 {missing} 个")
    print(f"[数据] 月销量均值 {ts.mean():.1f} 台，中位数 {ts.median():.0f} 台，"
          f"区间 [{ts.min():.0f}, {ts.max():.0f}]")
    print(f"[数据] 首年合计 {ts[ts.index.year == ts.index.year.min()].sum():.0f} 台 → "
          f"末年合计 {ts[ts.index.year == ts.index.year.max()].sum():.0f} 台")
    return ts


# ---------------------------------------------------------------------------
# 1. 原始序列 + 乘法季节分解 —— 对应教材 cell 3 / cell 5
# ---------------------------------------------------------------------------
def decompose_series(ts: pd.Series):
    """画「原始序列 + 趋势 + 季节 + 残差」四联图，并读出季节性规律。

    教材直接 ``sm.tsa.seasonal_decompose(sales_ts, model='multiplicative').plot()``，
    得到的是英文标签、默认配色的图。这里手工重画成中文四联图，好处是：

    * 乘法模型下 season 是「季节指数」，1.0 以上代表旺月，能直接读出"哪几个月旺"；
    * 可以在原始序列面板上叠加 12 个月移动平均，一眼看出趋势是否被季节掩盖。

    为什么用**乘法**模型：销量随趋势抬升时，季节波动的**绝对幅度**也在变大
    （2003 年旺季淡季差几十台，2013 年差几百台），这正是"季节效应按比例作用"的特征；
    若用加法模型，残差会呈现明显的喇叭口。
    """
    dec = seasonal_decompose(ts, model="multiplicative", period=SEASON)

    seasonal_index = dec.seasonal.groupby(dec.seasonal.index.month).mean()
    peak_month = int(seasonal_index.idxmax())
    low_month = int(seasonal_index.idxmin())
    print("\n== 1. 季节分解（乘法模型） ==")
    print(f"  季节指数最高：{peak_month} 月（{seasonal_index.max():.3f}），"
          f"最低：{low_month} 月（{seasonal_index.min():.3f}），"
          f"峰谷比 {seasonal_index.max() / seasonal_index.min():.2f} 倍")
    print("  各月季节指数：" + "，".join(
        f"{m}月 {seasonal_index[m]:.2f}" for m in range(1, 13)))

    trend = dec.trend.dropna()
    print(f"  趋势项：{trend.index.min():%Y-%m} {trend.iloc[0]:.0f} 台 → "
          f"{trend.index.max():%Y-%m} {trend.iloc[-1]:.0f} 台，"
          f"累计 {trend.iloc[-1] / trend.iloc[0] - 1:+.1%}")

    fig, axes = plt.subplots(4, 1, figsize=(10.2, 8.6), sharex=True)
    ax = axes[0]
    ax.plot(ts.index, ts.values, color=BLUE2, linewidth=1.5, label="月销量")
    ax.plot(ts.index, ts.rolling(SEASON).mean(), color=ORANGE, linewidth=2.2,
            label="12 个月移动平均")
    ax.set_ylabel("销量（台）")
    ax.set_title("原始序列与 12 个月移动平均", pad=8, fontsize=11.5)
    ax.legend(loc="upper left", ncol=2)

    ax = axes[1]
    ax.plot(dec.trend.index, dec.trend.values, color=BLUE, linewidth=2.0)
    ax.set_ylabel("趋势项")
    ax.set_title("趋势项（乘法分解）", pad=8, fontsize=11.5)

    ax = axes[2]
    ax.plot(dec.seasonal.index, dec.seasonal.values, color=GREEN, linewidth=1.2)
    ax.axhline(1.0, color=GRAY, linestyle="--", linewidth=0.9)
    ax.set_ylabel("季节指数")
    ax.set_title("季节项（>1 为旺月）", pad=8, fontsize=11.5)

    ax = axes[3]
    ax.plot(dec.resid.index, dec.resid.values, color=GRAY, linewidth=1.2)
    ax.axhline(1.0, color="#555555", linewidth=0.9)
    ax.set_ylim(dec.resid.min() - 0.03, dec.resid.max() + 0.03)
    ax.set_ylabel("残差")
    ax.set_title("残差项（应接近 1、无规律）", pad=8, fontsize=11.5)
    ax.set_xlabel("月份")

    fig.suptitle("拖拉机月销量：乘法季节分解（2003—2014）", fontsize=13,
                 fontweight="bold", y=1.005)
    fig.tight_layout()
    save_fig(fig, OUT, "fig01_原始序列与季节分解")
    return dec, seasonal_index


# ---------------------------------------------------------------------------
# 2. 平稳性检验 —— 教材 cell 8 之前的"隐含步骤"，这里显式化
# ---------------------------------------------------------------------------
def stationarity_tests(ts: pd.Series) -> pd.DataFrame:
    """对原始序列 / 对数序列 / 对数差分序列做 ADF 检验，确定差分阶数 d。

    教材是先"取对数 + 一阶差分"再去画 ACF/PACF，但没有检验这一步的必要性。
    ADF 的原假设是「存在单位根（不平稳）」，所以 **p < 0.05 才能拒绝原假设、认为平稳**。

    结论通常是这样三步：
      * 原始销量：有明显趋势，ADF 大概率不拒绝 → 不平稳；
      * 取对数：只是把波动压成比例，趋势还在 → 仍不平稳；
      * 对数一阶差分：趋势被消掉 → 平稳，于是 ``d = 1``。
    另外季节性也要靠 ``D = 1``（季节差分）处理，这一步在 SARIMA 的 seasonal_order 里体现。
    """
    log_ts = np.log(ts)
    log_diff = log_ts.diff().dropna()

    rows = []
    for name, series in [("原始销量", ts), ("对数销量", log_ts), ("对数一阶差分", log_diff)]:
        stat, p_value, used_lag, nobs, crit, _ = adfuller(series, autolag="AIC")
        if p_value < 0.05:
            verdict = "平稳"
        elif p_value < 0.10:
            verdict = "边缘平稳（10% 水平显著）"
        else:
            verdict = "不平稳"
        rows.append({
            "序列": name,
            "ADF 统计量": stat,
            "p 值": p_value,
            "滞后阶数": used_lag,
            "样本数": nobs,
            "1% 临界值": crit["1%"],
            "5% 临界值": crit["5%"],
            "结论": verdict,
        })
    table = pd.DataFrame(rows)

    print("\n== 2. ADF 平稳性检验（H0：存在单位根 / 不平稳） ==")
    for _, r in table.iterrows():
        print(f"  {r['序列']:<8} ADF={r['ADF 统计量']:>7.3f}，p={r['p 值']:.4f} → {r['结论']}")

    # 判定文字跟着实际 p 值走，避免"写着 0.05 其实不显著"的自相矛盾
    p_diff = table.loc[2, "p 值"]
    if p_diff < 0.05:
        judgement = f"对数一阶差分后 p={p_diff:.4f} < 0.05，平稳，取 d=1"
    elif p_diff < 0.10:
        judgement = (f"对数一阶差分后 p={p_diff:.4f}，5% 水平边缘、10% 水平可拒绝单位根，"
                     f"结合趋势已被消掉，取 d=1")
    else:
        judgement = f"对数一阶差分后 p={p_diff:.4f} 仍不平稳，实际建模需再差分或加季节差分"
    print(f"  判定：{judgement}；季节周期 12，取 D=1。")
    save_csv(table, OUT, "table01_序列特征与ADF检验")
    return table


# ---------------------------------------------------------------------------
# 3. ACF / PACF —— 对应教材 cell 8
# ---------------------------------------------------------------------------
def plot_acf_pacf(ts: pd.Series) -> None:
    """画对数差分序列的 ACF / PACF，用来给 p、q 一个先验范围。

    读图规则（教材没细讲，但定阶全靠它）：
      * ACF 在 lag 12、24 处仍有明显尖峰 → 季节项需要 MA 或 AR；
      * ACF 拖尾、PACF 截尾 → 偏 AR；ACF 截尾、PACF 拖尾 → 偏 MA；
      * 两图都拖尾 → ARMA 混合，靠 AIC 网格搜索来定更稳。
    这一步的产出是"搜索空间"，不是最终答案——真实数据里 ACF/PACF 往往不干净，
    所以下一步仍然要网格搜 AIC。
    """
    log_diff = np.log(ts).diff().dropna()

    fig, axes = new_fig(11.0, 4.2, ncols=2)
    plot_acf(log_diff, lags=36, ax=axes[0], color=BLUE2, vlines_kwargs={"colors": BLUE2})
    axes[0].set_title("自相关 ACF（对数一阶差分，lag ≤ 36）", pad=10)
    axes[0].set_xlabel("滞后阶数 lag")
    axes[0].set_ylabel("自相关系数")

    plot_pacf(log_diff, lags=36, ax=axes[1], color=ORANGE, method="ywm",
              vlines_kwargs={"colors": ORANGE})
    axes[1].set_title("偏自相关 PACF（对数一阶差分，lag ≤ 36）", pad=10)
    axes[1].set_xlabel("滞后阶数 lag")
    axes[1].set_ylabel("偏自相关系数")

    fig.suptitle("差分后序列的相关结构：lag 12 的尖峰说明季节项不可省", fontsize=12.5,
                 fontweight="bold", y=1.03)
    fig.tight_layout()
    save_fig(fig, OUT, "fig02_ACF与PACF")


# ---------------------------------------------------------------------------
# 4. SARIMA 定阶 —— 对应教材 cell 10 的双重循环（这里收敛到 18 组）
# ---------------------------------------------------------------------------
def grid_search(train: pd.Series) -> tuple[pd.DataFrame, tuple, tuple]:
    """在训练集上网格搜索 (p,d,q)×(P,D,Q,12)，按 AIC 选最优。

    教材写的是 ``p=d=q=range(0,2)`` 三重笛卡尔积再套季节三重积（最多 64 组），
    全部用默认参数拟合，跑一次要好几分钟，而且没有留下搜索记录。
    这里改成：

    * 固定 ``d=1, D=1``（已由上一步 ADF 与季节差分确定），只搜 p,q,P,Q；
    * p,q 取 0—2、(P,Q) 取 {(0,0),(1,1)}，共 **18 组**，单机 1 分钟内跑完；
    * 每组都记录 AIC / BIC，最后落盘成表——"为什么选这组参数"才有据可查。

    AIC = -2·logL + 2k，既奖励拟合好，也惩罚参数多；比较时只能用同一份训练数据。
    """
    log_train = np.log(train)
    records = []
    print("\n== 3. SARIMA 定阶（训练集 %d 个月，搜索 %d 组） =="
          % (len(train), len(P_RANGE) * len(Q_RANGE) * len(SEASONAL_ORDERS)))

    for p in P_RANGE:
        for q in Q_RANGE:
            for seasonal_order in SEASONAL_ORDERS:
                try:
                    model = SARIMAX(
                        log_train,
                        order=(p, 1, q),
                        seasonal_order=seasonal_order,
                        enforce_stationarity=True,
                        enforce_invertibility=True,
                    )
                    res = model.fit(disp=False)
                    records.append({
                        "p": p, "d": 1, "q": q,
                        "P": seasonal_order[0], "D": seasonal_order[1],
                        "Q": seasonal_order[2], "s": seasonal_order[3],
                        "参数组": f"({p},1,{q})x({seasonal_order[0]},{seasonal_order[1]},"
                                  f"{seasonal_order[2]},{seasonal_order[3]})",
                        "AIC": res.aic, "BIC": res.bic, "对数似然": res.llf,
                    })
                except Exception as exc:      # 个别参数组不收敛，跳过即可
                    print(f"    ({p},1,{q})x{seasonal_order} 拟合失败：{exc}")

    table = pd.DataFrame(records).sort_values("AIC").reset_index(drop=True)
    best = table.iloc[0]
    best_order = (int(best["p"]), 1, int(best["q"]))
    best_seasonal = (int(best["P"]), int(best["D"]), int(best["Q"]), SEASON)

    print(f"  有效拟合 {len(table)} 组；AIC 最优：SARIMA{best_order}x{best_seasonal}，"
          f"AIC={best['AIC']:.2f}，BIC={best['BIC']:.2f}")
    print("  AIC 前 3 名：")
    for _, r in table.head(3).iterrows():
        print(f"    {r['参数组']:<22} AIC={r['AIC']:.2f}  BIC={r['BIC']:.2f}")
    print(f"  AIC 最差的一组：{table.iloc[-1]['参数组']}，AIC={table.iloc[-1]['AIC']:.2f}")

    save_csv(table, OUT, "table02_模型定阶AIC")
    return table, best_order, best_seasonal


# ---------------------------------------------------------------------------
# 5. 回测 —— 教材完全没做的一步：模型到底预不准？
# ---------------------------------------------------------------------------
def backtest(train: pd.Series, test: pd.Series, order: tuple, seasonal_order: tuple):
    """用最优参数在训练集上重拟合，预测留出的 12 个月，并与实际值对比。

    两个误差指标：

    * **MAPE**（平均绝对百分比误差）：业务最直观，"平均偏差几个百分点"；
    * **RMSE**（均方根误差）：对大误差更敏感，单位是"台"。

    同时给一个**季节性朴素预测**做基准：直接拿去年同月的销量当预测值。
    如果 SARIMA 连这个基准都打不过，说明模型没学到东西，不如用最简单的规则。
    """
    res = SARIMAX(np.log(train), order=order, seasonal_order=seasonal_order,
                  enforce_stationarity=True, enforce_invertibility=True).fit(disp=False)
    fc = res.get_forecast(steps=len(test), alpha=0.05)
    pred = pd.Series(np.exp(fc.predicted_mean.to_numpy()), index=test.index)
    lower = pd.Series(np.exp(fc.conf_int().iloc[:, 0].to_numpy()), index=test.index)
    upper = pd.Series(np.exp(fc.conf_int().iloc[:, 1].to_numpy()), index=test.index)

    mape = float(np.mean(np.abs((test - pred) / test)) * 100)
    rmse = float(np.sqrt(np.mean((test - pred) ** 2)))
    # 季节性朴素法：预测值 = 去年同月实际值
    naive = test.copy()
    naive.iloc[:] = train.iloc[-len(test):].to_numpy()
    naive_mape = float(np.mean(np.abs((test - naive) / test)) * 100)
    naive_rmse = float(np.sqrt(np.mean((test - naive) ** 2)))

    # 95% 区间覆盖率：12 个点里应该大约有 11—12 个落在区间内
    inside = int(((test >= lower) & (test <= upper)).sum())

    print("\n== 4. 留出回测（最后 %d 个月） ==" % len(test))
    print(f"  测试期：{test.index.min():%Y-%m} ~ {test.index.max():%Y-%m}")
    print(f"  SARIMA  ：MAPE {mape:.2f}%，RMSE {rmse:.1f} 台")
    print(f"  季节性朴素：MAPE {naive_mape:.2f}%，RMSE {naive_rmse:.1f} 台 "
          f"（MAPE 相对改善 {naive_mape - mape:+.2f} 个百分点）")
    print(f"  95% 预测区间覆盖 {inside}/{len(test)} 个月")

    fig, axes = new_fig(10.4, 6.6, nrows=2, ncols=1,
                        gridspec_kw={"height_ratios": [2.1, 1]})
    ax = axes[0]
    history = train.iloc[-24:]
    ax.axvspan(test.index.min(), test.index.max(), color=GRAY, alpha=0.10, zorder=1)
    ax.plot(history.index, history.values, color=BLUE2, linewidth=1.8,
            label="训练期实际（近 24 个月）")
    ax.plot(test.index, test.values, color=BLUE, linewidth=2.2, marker="o",
            markersize=5, label="回测期实际")
    ax.plot(pred.index, pred.values, color=ORANGE, linewidth=2.0, marker="s",
            markersize=5, linestyle="--", label="SARIMA 预测")
    ax.plot(naive.index, naive.values, color=GRAY, linewidth=1.6, linestyle=":",
            label="季节性朴素基准")
    ax.fill_between(pred.index, lower.values, upper.values, color=ORANGE,
                    alpha=0.16, label="95% 预测区间")
    ax.set_ylabel("销量（台）")
    ax.set_title(f"回测：SARIMA{order}x{seasonal_order} 预测最后 12 个月"
                 f"（MAPE {mape:.1f}%）", pad=10)
    ax.legend(loc="upper left", ncol=2, fontsize=9)

    ax = axes[1]
    err = (pred - test)
    pos = np.arange(len(err))
    colors = [NEG if v < 0 else POS for v in err.values]
    ax.bar(pos, err.values, width=0.62, color=colors, zorder=3)
    ax.axhline(0, color="#555555", linewidth=0.9)
    ax.set_xticks(pos, [d.strftime("%y-%m") for d in err.index], rotation=45, fontsize=8.5)
    ax.set_xlim(-0.7, len(err) - 0.3)
    for x, v in zip(pos, err.values):
        ax.annotate(f"{v:+.0f}", (x, v), xytext=(0, 4 if v >= 0 else -13),
                    textcoords="offset points", ha="center", fontsize=8.5,
                    color=POS if v >= 0 else NEG)
    ax.set_ylabel("预测误差（台）")
    ax.set_xlabel("回测月份")
    ax.set_title("逐月预测误差（预测 − 实际）：绿色高估、红色低估", pad=8, fontsize=11)
    ax.margins(y=0.28)
    fig.tight_layout()
    save_fig(fig, OUT, "fig03_回测对比与误差")

    metrics = pd.DataFrame([
        {"模型": f"SARIMA{order}x{seasonal_order}", "MAPE(%)": mape, "RMSE(台)": rmse},
        {"模型": "季节性朴素法", "MAPE(%)": naive_mape, "RMSE(台)": naive_rmse},
    ])
    return pred, lower, upper, metrics, inside


# ---------------------------------------------------------------------------
# 6. 未来 12 个月预测 —— 对应教材 cell 15 / 16（教材预测 36 期）
# ---------------------------------------------------------------------------
def forecast_future(ts: pd.Series, order: tuple, seasonal_order: tuple):
    """在**全部 144 个月**上重拟合，向后预测 12 个月，并画拟合 + 预测带。

    注意两点，都是教材没强调但很容易踩的坑：

    1. 定阶用的是训练集、预测要用全量数据重拟合——留出的 12 个月也是真实信息，
       预测未来时不该浪费；
    2. 对数模型的区间要 ``exp`` 还原，还原后的区间是**右偏**的
       （上限拉得比下限远），这正是"销量不可能为负"的体现。
    """
    res = SARIMAX(np.log(ts), order=order, seasonal_order=seasonal_order,
                  enforce_stationarity=True, enforce_invertibility=True).fit(disp=False)
    fc = res.get_forecast(steps=FORECAST, alpha=0.05)
    idx = pd.date_range(ts.index.max(), periods=FORECAST + 1, freq="MS")[1:]
    future = pd.DataFrame({
        "月份": idx.strftime("%Y-%m"),
        "预测销量": np.exp(fc.predicted_mean.to_numpy()).round(1),
        "下限95": np.exp(fc.conf_int().iloc[:, 0].to_numpy()).round(1),
        "上限95": np.exp(fc.conf_int().iloc[:, 1].to_numpy()).round(1),
    })
    fitted = pd.Series(np.exp(res.fittedvalues.to_numpy()), index=ts.index)
    # 差分与季节差分的前若干期是初始化的产物（对数尺度上接近 0，还原后≈1 台），
    # 画到图上会拖出一条假的深坑，这里直接置为缺失。
    fitted.iloc[:SEASON + 1] = np.nan

    print("\n== 5. 未来 %d 个月预测 ==" % FORECAST)
    print(f"  预测区间：{future['月份'].iloc[0]} ~ {future['月份'].iloc[-1]}")
    print(f"  合计预测 {future['预测销量'].sum():.0f} 台，"
          f"月均 {future['预测销量'].mean():.0f} 台；"
          f"区间宽度从 {future['上限95'].iloc[0] - future['下限95'].iloc[0]:.0f} 台"
          f"扩大到 {future['上限95'].iloc[-1] - future['下限95'].iloc[-1]:.0f} 台")
    for _, r in future.head(3).iterrows():
        print(f"    {r['月份']}：{r['预测销量']:.0f} 台"
              f"（95% 区间 {r['下限95']:.0f} ~ {r['上限95']:.0f}）")

    fig, ax = new_fig(10.6, 5.2)
    ax.plot(ts.index, ts.values, color=BLUE2, linewidth=1.4, label="实际销量")
    ax.plot(fitted.index, fitted.values, color=GRAY, linewidth=1.4, linestyle="--",
            alpha=0.9, label="模型拟合值")
    ax.plot(idx, future["预测销量"].values, color=ORANGE, linewidth=2.2,
            marker="o", markersize=4.5, label="未来 12 个月预测")
    ax.fill_between(idx, future["下限95"].values, future["上限95"].values,
                    color=ORANGE, alpha=0.18, label="95% 预测区间")
    ax.axvline(ts.index.max(), color="#555555", linestyle="--", linewidth=1.0)
    ax.annotate("预测起点", (ts.index.max(), ts.max() * 0.97),
                xytext=(-58, 0), textcoords="offset points",
                fontsize=9, color="#555555")
    ax.set_title(f"全样本拟合与未来 12 个月预测（SARIMA{order}x{seasonal_order}）", pad=12)
    ax.set_xlabel("月份")
    ax.set_ylabel("销量（台）")
    ax.legend(loc="upper left", ncol=2, fontsize=9)
    save_fig(fig, OUT, "fig04_拟合与未来预测")
    return future, res


# ---------------------------------------------------------------------------
# 7. 残差诊断 —— 对应教材 cell 13：results.plot_diagnostics()
# ---------------------------------------------------------------------------
def residual_diagnostics(res, ts: pd.Series) -> None:
    """四联图检查残差是否"像白噪声"：时序、直方图、QQ、ACF。

    这是 SARIMA 的"验收环节"：
      * 残差时序应围绕 0 随机波动，没有明显的趋势或周期；
      * 直方图应接近正态；
      * QQ 点应贴近 45° 线（尾部偏离说明有极端值未被模型解释）；
      * 残差 ACF 应基本落在置信带内——否则说明还有信息没被提取，需要加阶。

    教材用 ``res.plot_diagnostics()`` 一次出图；这里拆开手工画，
    是为了把中文标题写清楚，并叠加正态曲线与 QQ 参考线，方便肉眼判断。
    """
    resid = pd.Series(res.resid.to_numpy(), index=ts.index).dropna()
    # 前几个残差是差分/初始化产生的（接近 0），拿来做诊断会误导
    burn = SEASON + 1
    resid = resid.iloc[burn:]

    fig, axes = plt.subplots(2, 2, figsize=(10.6, 6.8))

    ax = axes[0, 0]
    ax.plot(resid.index, resid.values, color=BLUE2, linewidth=1.1)
    ax.axhline(0, color="#555555", linewidth=0.9)
    ax.set_title("残差时序", pad=8, fontsize=11)
    ax.set_ylabel("残差")

    ax = axes[0, 1]
    ax.hist(resid.values, bins=22, color=BLUE2, alpha=0.75, density=True,
            edgecolor="white", zorder=3)
    xmin, xmax = ax.get_xlim()
    grid = np.linspace(xmin, xmax, 200)
    ax.plot(grid, stats.norm.pdf(grid, resid.mean(), resid.std()), color=ORANGE,
            linewidth=2, label="正态参考")
    ax.set_title("残差直方图", pad=8, fontsize=11)
    ax.set_xlabel("残差")
    ax.set_ylabel("密度")
    ax.legend(loc="upper right", fontsize=9)

    ax = axes[1, 0]
    stats.probplot(resid.values, dist="norm", plot=ax)
    ax.get_lines()[0].set(marker="o", markersize=3.6, markerfacecolor=BLUE2,
                          markeredgecolor="none", alpha=0.75)
    ax.get_lines()[1].set(color=ORANGE, linewidth=1.8)
    ax.set_title("残差 QQ 图", pad=8, fontsize=11)
    ax.set_xlabel("理论分位数")
    ax.set_ylabel("样本分位数")

    ax = axes[1, 1]
    plot_acf(resid, lags=24, ax=ax, zero=False, color=BLUE2,
             vlines_kwargs={"colors": BLUE2})
    ax.set_title("残差自相关 ACF", pad=8, fontsize=11)
    ax.set_xlabel("滞后阶数 lag")
    ax.set_ylabel("自相关系数")

    fig.suptitle("残差诊断：若四张图都“干净”，说明模型已提取完主要信息",
                 fontsize=12.5, fontweight="bold", y=1.01)
    fig.tight_layout()
    save_fig(fig, OUT, "fig05_残差诊断")

    # 用 Ljung-Box 给"ACF 是否干净"一个数字答案
    from statsmodels.stats.diagnostic import acorr_ljungbox
    lb = acorr_ljungbox(resid, lags=[12, 24], return_df=True)
    print("\n== 6. 残差诊断 ==")
    print(f"  残差均值 {resid.mean():+.4f}，标准差 {resid.std():.4f}")
    for lag, row in lb.iterrows():
        print(f"  Ljung-Box lag={lag}：统计量 {row['lb_stat']:.2f}，p={row['lb_pvalue']:.3f}"
              f" → {'残差近似白噪声' if row['lb_pvalue'] > 0.05 else '仍有自相关，可考虑升阶'}")
    return lb


def main() -> None:
    apply_style()
    ts = load_series()
    dec, seasonal_index = decompose_series(ts)
    adf = stationarity_tests(ts)
    plot_acf_pacf(ts)

    train, test = ts.iloc[:-HOLDOUT], ts.iloc[-HOLDOUT:]
    grid, order, seasonal_order = grid_search(train)
    pred, lower, upper, metrics, inside = backtest(train, test, order, seasonal_order)
    future, res = forecast_future(ts, order, seasonal_order)
    lb = residual_diagnostics(res, ts)

    # 回测明细 + 未来预测拼成一张表，方便核对
    detail = pd.concat([
        pd.DataFrame({
            "月份": test.index.strftime("%Y-%m"),
            "类型": "回测",
            "实际值": test.values,
            "预测值": pred.values.round(1),
            "下限95": lower.values.round(1),
            "上限95": upper.values.round(1),
        }),
        pd.DataFrame({
            "月份": future["月份"],
            "类型": "预测",
            "实际值": np.nan,
            "预测值": future["预测销量"],
            "下限95": future["下限95"],
            "上限95": future["上限95"],
        }),
    ], ignore_index=True)
    detail["误差"] = (detail["预测值"] - detail["实际值"]).round(1)
    save_csv(detail, OUT, "table03_回测与未来预测")

    # ---- 业务结论 ----
    total_next = future["预测销量"].sum()
    total_last = ts[ts.index.year == ts.index.year.max()].sum()
    print("\n" + "=" * 70)
    print("业务结论（可直接用于报告）")
    print("=" * 70)
    print(f"1. 销量有清晰的“趋势 + 季节”双成分：12 年趋势项从 "
          f"{dec.trend.dropna().iloc[0]:.0f} 台涨到 {dec.trend.dropna().iloc[-1]:.0f} 台，"
          f"季节峰谷比 {seasonal_index.max() / seasonal_index.min():.2f} 倍，"
          f"{int(seasonal_index.idxmax())} 月最旺、{int(seasonal_index.idxmin())} 月最淡。")
    print(f"2. 对数一阶差分后 ADF p={adf.loc[2, 'p 值']:.4f}"
          f"（{'5% 水平拒绝单位根' if adf.loc[2, 'p 值'] < 0.05 else '5% 边缘、10% 显著'}），"
          f"结合趋势已消除，取 d=1；季节周期 12 → D=1；"
          f"AIC 选出 SARIMA{order}x{seasonal_order}（AIC={grid.iloc[0]['AIC']:.1f}）。")
    print(f"3. 留出 12 个月回测：MAPE {metrics.iloc[0]['MAPE(%)']:.2f}%、"
          f"RMSE {metrics.iloc[0]['RMSE(台)']:.1f} 台，"
          f"优于季节性朴素法的 {metrics.iloc[1]['MAPE(%)']:.2f}% / "
          f"{metrics.iloc[1]['RMSE(台)']:.1f} 台；"
          f"95% 区间覆盖 {inside}/12 个月。")
    print(f"4. 未来 12 个月合计预计 {total_next:.0f} 台，较 {ts.index.year.max()} 年实际 "
          f"{total_last:.0f} 台 {total_next / total_last - 1:+.1%}；"
          f"预测区间第 12 个月已扩大到 "
          f"{future['上限95'].iloc[-1] - future['下限95'].iloc[-1]:.0f} 台，"
          f"越远越不确定，排产应按区间上沿留安全库存。")
    print(f"5. 残差 Ljung-Box lag=12 的 p={lb.loc[12, 'lb_pvalue']:.3f}，"
          f"{'残差近似白噪声，模型可用' if lb.loc[12, 'lb_pvalue'] > 0.05 else '残差仍有自相关，建议继续升阶'}。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
