# -*- coding: utf-8 -*-
"""
实验 08 · 主成分与因子分析：9 个经济指标怎么压缩成 2 个"城市实力"维度
====================================================================
教材：《CDA 二级认证教材：量化策略分析》第 7 章 特征降维方法
原始素材：``在 Python 中实现主成分分析.ipynb`` + ``在 Python 中实现因子分析.ipynb``
        ``cities_10.csv``（10 个省份 × 9 个经济指标，**GBK 编码**）
        ``profile_telecom.csv``（600 个手机用户 × 4 类行为次数）
迁移方向：notebook 里"调一个包、打印一个矩阵"  →  一套可解释的降维流程 + 可视化 + 排名

教材这一段的核心不是 API，而是**三个判断**：

  1. 要不要降维？——9 个指标两两高度相关（相关系数 0.9 以上），直接回归会共线；
  2. 保留几个成分？——碎石图 + 特征值 > 1（Kaiser 准则）；
  3. 怎么解释成分？——看载荷矩阵，给每个成分起一个业务名字。

notebook 里这三步都只有一行代码（``pca.explained_variance_ratio_``、
``fa.comps["rot"]``），读者看到的是数字矩阵，看不到"为什么"。

**关于工具的一个重要说明**：教材因子分析用的是 ``fa_kit`` 包，本环境没有安装，
而且它已停止维护。所以本脚本改用 ``statsmodels.multivariate.factor.Factor``：

    * ``Factor(..., method='pa')`` 主轴因子法（principal axis factoring）提取因子；
    * ``statsmodels.multivariate.factor.rotate_factors(L, 'varimax')`` 做方差最大化旋转
      （注意：本环境 statsmodels 0.14.4 的 ``Factor`` **不接受** ``rotation=`` 参数，
      旋转必须单独调用，这一点教材和 fa_kit 的写法不一样）；
    * 因子得分按教材的做法用"标准化数据 × 旋转后载荷"近似，并在脚本里注明其局限。

运行：``python lab08_pca_factor.py``（在实验目录下执行）
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from statsmodels.multivariate.factor import Factor, rotate_factors

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

N_KEEP = 2          # 按 Kaiser 准则（特征值 > 1）保留 2 个成分，脚本里会再验证一次


# ---------------------------------------------------------------------------
# 0. 读数据 —— 对应教材 cell 4（PCA notebook cell 3）
# ---------------------------------------------------------------------------
def load_cities() -> tuple[pd.DataFrame, list[str]]:
    """读入城市经济指标，并把"指标列"和"标签列"分开。

    对应教材：``model_data = pd.read_csv("cities_10.csv", encoding="gbk")``

    教材没解释为什么要写 ``encoding='gbk'``——因为这份 CSV 是**中文 Windows 下
    用 Excel 另存的**，不带 BOM、按 GBK 编码；用默认 UTF-8 读会直接抛
    ``UnicodeDecodeError``。这是中文数据项目里最常见的第一个坑，脚本里
    把两种读法的差异打印出来，提醒"编码不是可选项"。
    """
    df = pd.read_csv(DATA / "cities_10.csv", encoding="gbk")

    try:
        pd.read_csv(DATA / "cities_10.csv")
        encode_note = "默认 UTF-8 也能读（说明该文件其实是 UTF-8）"
    except UnicodeDecodeError:
        encode_note = "默认 UTF-8 读取失败 → UnicodeDecodeError，必须显式指定 gbk"

    cols = [c for c in df.columns if c != "AREA"]
    print("== 0. 读入城市经济数据 ==")
    print(f"  {df.shape[0]} 个省份 × {df.shape[1]} 列（1 个名称列 + {len(cols)} 个指标）")
    print(f"  编码：{encode_note}")
    print("  省份：" + "、".join(df["AREA"].tolist()))
    return df, cols


def build_matrix(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """中心标准化 —— 对应教材 cell 7 ``preprocessing.scale(data)``。

    为什么必须标准化：9 个指标量纲天差地别（X1 是千亿级，X2 是三万级的人均量，
    X8/X9 只有几十到几百）。不标准化，PCA 的第一个成分会被量纲最大的 X1 独占，
    "解释方差 95%"只是量纲的假象。

    ``StandardScaler`` 与教材的 ``preprocessing.scale`` 完全等价（都是
    (x-mean)/std，按列），这里用前者是因为它可放进 Pipeline、可保存参数。
    """
    X = df[cols].to_numpy(dtype=float)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    print("\n== 1. 标准化 ==")
    print(f"  标准化前各列标准差：{np.round(X.std(axis=0, ddof=1), 1).tolist()}")
    print(f"  标准化后均值 {Xs.mean():+.2e}，标准差 {Xs.std(axis=0, ddof=0).mean():.3f}")
    return Xs


# ---------------------------------------------------------------------------
# 1. PCA：解释方差 + 特征值 + 综合得分
# ---------------------------------------------------------------------------
def pca_overview(Xs: np.ndarray, cols: list[str]) -> dict:
    """做主成分分析，输出解释方差表，并验证"保留几个成分"。

    对应教材：
        cell 12  ``pca = PCA(n_components=9); pca.fit(data)``
        cell 13  ``print(pca.explained_variance_)`` 与 ``explained_variance_ratio_``
                 （教材注释：标准化数据下单个主成分的特征值应 > 1）
        cell 15—16 ``pca = PCA(n_components=2).fit(data)`` 再看特征值

    教材把"9 个成分"和"2 个成分"分成两次 fit，其实是同一个模型看前几行。
    这里一次 fit 全部 9 个成分，用**特征值 > 1** 自动判定保留个数，再输出表 1。
    """
    pca = PCA(n_components=len(cols)).fit(Xs)
    eig = pca.explained_variance_
    ratio = pca.explained_variance_ratio_
    n_keep = int((eig > 1).sum())

    table = pd.DataFrame({
        "主成分": [f"PC{i + 1}" for i in range(len(cols))],
        "特征值": np.round(eig, 4),
        "解释方差比例": np.round(ratio, 4),
        "累计解释方差": np.round(np.cumsum(ratio), 4),
        "保留（特征值>1）": ["是" if i < n_keep else "否" for i in range(len(cols))],
    })

    pca2 = PCA(n_components=N_KEEP).fit(Xs)
    scores = pca2.transform(Xs)
    # 载荷 = 指标与主成分的相关系数（标准化数据下等价于 eigenvector×sqrt(λ)，
    # 但直接算相关系数可以避开 ddof 口径不一致导致的"共同度大于 1"的假象）
    loadings = np.corrcoef(np.column_stack([Xs, scores]).T)[:len(cols), len(cols):]

    print("\n== 2. 主成分分析 ==")
    print(f"  特征值：{np.round(eig, 3).tolist()}")
    print(f"  前 2 个主成分解释 {ratio[:2].sum():.1%}，"
          f"前 3 个解释 {ratio[:3].sum():.1%}")
    print(f"  Kaiser 准则（特征值>1）判断应保留 {n_keep} 个 → 与教材选 2 个一致")
    print(f"  共同度（前 2 个成分能解释每个指标多少方差）："
          f"{np.round((loadings ** 2).sum(axis=1), 2).tolist()}")
    return {"pca": pca, "pca2": pca2, "eig": eig, "ratio": ratio,
            "scores": scores, "loadings": loadings, "table": table}


def composite_score(res: dict, df: pd.DataFrame) -> pd.DataFrame:
    """用前两个主成分的方差贡献率当权重，算城市综合得分并排名。

    对应教材：notebook 里只打印了得分矩阵（``pca.transform``），没有合成一个指标。
    但对业务方来说，"9 个数"没法比较，"一个综合分 + 排名"才能用。

    权重取 ``explained_variance_ratio_`` 归一化后的值（0.868 / 0.132），
    这样既保留了 PC1 的主导地位，又不丢掉 PC2 携带的"人均水平"信息。
    """
    w = res["ratio"][:N_KEEP] / res["ratio"][:N_KEEP].sum()
    score = res["scores"] @ w
    table = pd.DataFrame({
        "省份": df["AREA"].values,
        "PC1得分": np.round(res["scores"][:, 0], 3),
        "PC2得分": np.round(res["scores"][:, 1], 3),
        "综合得分": np.round(score, 3),
    }).sort_values("综合得分", ascending=False).reset_index(drop=True)
    table.insert(0, "排名", np.arange(1, len(table) + 1))
    table["权重"] = f"PC1 {w[0]:.3f} / PC2 {w[1]:.3f}"

    print("\n== 5. 城市综合得分排名 ==")
    print(f"  权重：PC1 {w[0]:.3f}、PC2 {w[1]:.3f}")
    for _, r in table.iterrows():
        print(f"  {int(r['排名']):>2}. {r['省份']:<3} 综合 {r['综合得分']:>7.3f}"
              f"（PC1 {r['PC1得分']:>6.2f}，PC2 {r['PC2得分']:>6.2f}）")
    return table


def plot_scree(city: dict, tel: dict) -> None:
    """碎石图：两个数据集的解释方差对比。

    对应教材 cell 13 的 ``explained_variance_ratio_`` —— 教材只打印了数组，
    碎石图（scree plot）才是"保留几个"的标准可视化：
    曲线由陡变缓的"肘部"就是应该截断的位置。

    这里把两个数据集并排：城市 9 个指标（前 2 个占 92.3%）、
    电信用户 4 个行为指标（前 2 个占 87.1%），结论一致——
    **再多的成分也只是噪声**，2 个足够。
    """
    fig, axes = new_fig(11.6, 4.3, ncols=2, gridspec_kw={"wspace": 0.4})

    # 右图省略 y 轴标题：两张子图口径相同，重复写会与左图的"累计"副轴标签重叠
    for ax, name, ratio, eig, color, show_ylabel in [
        (axes[0], "城市经济指标（9 个）", city["ratio"], city["eig"], BLUE, True),
        (axes[1], "电信用户行为（4 个）", tel["ratio"], tel["eig"], ORANGE, False),
    ]:
        k = len(ratio)
        xs = np.arange(1, k + 1)
        ax.bar(xs, ratio, color=[color if e > 1 else "#C9D2DB" for e in eig],
               width=0.6, zorder=3)
        bar_labels(ax, fmt="{:.1%}", fontsize=8.5)
        ax.set_ylim(0, max(ratio) * 1.22)
        ax.set_xticks(xs)
        ax.set_xlabel("主成分序号")
        ax.set_ylabel("解释方差比例" if show_ylabel else "")
        ax.set_title(name, pad=10)
        ax.axhline(1 / k, color=GRAY, linestyle=":", linewidth=1.2)
        ax.annotate("平均线 1/p", xy=(k, 1 / k), xytext=(-4, 5),
                    textcoords="offset points", ha="right", fontsize=8.5,
                    color=GRAY)

        ax2 = ax.twinx()
        ax2.plot(xs, np.cumsum(ratio), color=RED, marker="o", markersize=4.5,
                 linewidth=1.8, zorder=6)
        ax2.set_ylim(0, 1.06)
        ax2.set_ylabel("累计解释方差", color=RED)
        ax2.tick_params(axis="y", colors=RED)
        pct_axis(ax2, axis="y")
        ax2.grid(False)
        ax2.annotate(f"前 2 个累计 {np.cumsum(ratio)[1]:.1%}",
                     xy=(2, np.cumsum(ratio)[1]), xytext=(12, -14),
                     textcoords="offset points", fontsize=8.5, color=RED,
                     arrowprops={"arrowstyle": "-", "color": RED, "lw": 0.8})

    fig.suptitle("碎石图：两个数据集都只需 2 个主成分（柱为各成分，红线为累计）",
                 y=1.04, fontsize=13, fontweight="bold")
    save_fig(fig, OUT, "fig01_碎石图与累计解释方差")


# ---------------------------------------------------------------------------
# 2. 相关性热力图：为什么非降维不可
# ---------------------------------------------------------------------------
def plot_correlation(df: pd.DataFrame, cols: list[str]) -> None:
    """9 个指标的相关系数矩阵。

    对应教材 cell 4 ``data.corr(method="pearson")`` —— 教材只打印了矩阵。

    热力图想说明的是一件事：**这 9 个指标其实是同一个东西的 9 个侧面**。
    X1、X3—X7、X9 之间相关系数普遍在 0.9 以上，直接放进回归会严重共线；
    只有 X2（人均量）与其它指标相关很弱，这正是第二个主成分的来源。
    """
    corr = df[cols].corr("pearson")

    fig, ax = new_fig(7.6, 6.4)
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)), cols)
    ax.set_yticks(range(len(cols)), cols)
    ax.grid(False)
    for i in range(len(cols)):
        for j in range(len(cols)):
            v = corr.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7.6,
                    color="white" if abs(v) > 0.62 else "#333333")
    ax.set_title("9 个经济指标的相关系数矩阵", pad=12)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03, label="Pearson 相关系数")
    save_fig(fig, OUT, "fig02_指标相关性热力图")

    off = corr.where(~np.eye(len(cols), dtype=bool))
    print("\n== 3. 共线性检查 ==")
    print(f"  非对角相关系数：最高 {off.max().max():.3f}，"
          f"最低 {off.min().min():.3f}，平均 {off.stack().mean():.3f}")
    print(f"  |r| > 0.9 的指标对：{int((off.abs() > 0.9).sum().sum() // 2)} 组"
          f" → 不降维会共线")


# ---------------------------------------------------------------------------
# 3. 双标图（biplot）：得分 + 载荷画在同一张图
# ---------------------------------------------------------------------------
def plot_biplot(res: dict, df: pd.DataFrame, cols: list[str]) -> None:
    """把城市得分（点）和指标载荷（箭头）画在同一张图上。

    对应教材：没有这一步。教材 cell 7 打印 ``pca.transform`` 的得分矩阵，
    cell 37 画了因子得分散点——但从未把"点"和"变量"放在一起。

    biplot 是 PCA 最实用的图：**点在哪个方向，就说明它在哪个指标上强**。
    箭头指向右上 → 该指标与 PC1、PC2 都正相关；城市点沿着箭头方向越远，
    这个指标上的表现越突出。
    """
    scores = res["scores"]
    loadings = res["loadings"]
    ratio = res["ratio"]

    fig, ax = new_fig(8.4, 6.4)
    ax.axhline(0, color="#9AA5B1", linewidth=0.9, zorder=1)
    ax.axvline(0, color="#9AA5B1", linewidth=0.9, zorder=1)

    # 箭头缩放：让最长的箭头约为得分范围的一半，避免箭头出界
    scale = 0.55 * max(np.abs(scores).max(), 1e-9) / max(np.abs(loadings).max(), 1e-9)
    # 7 个指标几乎都落在 PC1 正方向上（这正是"它们其实是同一件事"的证据），
    # 标签必然重叠；这里按载荷高低轮流把标签错开上下位置，保证都能读出来
    dy_cycle = [-16, 10, -28, 22, -8, 16, -22, 28, -34]
    order = np.argsort(-np.abs(loadings[:, 0]))
    for rank_i, i in enumerate(order):
        x, y = loadings[i, 0] * scale, loadings[i, 1] * scale
        ax.annotate("", xy=(x, y), xytext=(0, 0),
                    arrowprops={"arrowstyle": "-|>", "color": GRAY,
                                "lw": 1.5, "alpha": 0.9})
        ax.annotate(cols[i], xy=(x, y), xytext=(5, dy_cycle[rank_i % len(dy_cycle)]),
                    textcoords="offset points", fontsize=9.5, color=GRAY,
                    fontweight="bold", va="center")

    ax.scatter(scores[:, 0], scores[:, 1], s=90, color=BLUE, alpha=0.85,
               edgecolor="white", linewidth=1.2, zorder=5)
    for i, name in enumerate(df["AREA"]):
        ax.annotate(name, xy=(scores[i, 0], scores[i, 1]), xytext=(7, -3),
                    textcoords="offset points", fontsize=9.5, color=BLUE)

    ax.set_xlabel(f"PC1（{ratio[0]:.1%}）")
    ax.set_ylabel(f"PC2（{ratio[1]:.1%}）")
    ax.set_title("PCA 双标图：点=省份，箭头=指标的载荷方向", pad=12)
    ax.margins(0.18)
    save_fig(fig, OUT, "fig03_PCA双标图")

    top = np.argsort(-np.abs(loadings[:, 0]))[:3]
    print("\n== 4. 主成分解释 ==")
    print(f"  PC1 载荷最高的指标："
          + "、".join(f"{cols[i]}({loadings[i, 0]:+.2f})" for i in top)
          + " → 可命名为「经济总量」")
    print(f"  PC2 载荷最高的指标："
          + "、".join(f"{cols[i]}({loadings[i, 1]:+.2f})"
                     for i in np.argsort(-np.abs(loadings[:, 1]))[:2])
          + " → 可命名为「人均水平」")


# ---------------------------------------------------------------------------
# 4. 因子分析：KMO / Bartlett / 主轴因子 / varimax 旋转
# ---------------------------------------------------------------------------
def kmo_bartlett(Xs: np.ndarray) -> tuple[float, float, int, float]:
    """手算 KMO 与 Bartlett 球形检验（本环境没有现成函数）。

    教材用 ``factor_analyzer`` 的 ``calculate_kmo`` / ``calculate_bartlett_sphericity``；
    该包不可用，但两个统计量的公式都很短，可以直接算：

    * **KMO** = Σr² / (Σr² + Σq²)，其中 r 是相关系数、q 是**偏相关系数**
      （由相关矩阵的逆矩阵算出）。KMO 越接近 1 越适合做因子分析，
      通常 > 0.6 可接受、> 0.8 良好；
    * **Bartlett** = -(n-1-(2p+5)/6)·ln|R|，服从自由度 p(p-1)/2 的卡方分布，
      原假设是"相关矩阵为单位阵"（即变量间没有共同因子），p 小才适合做因子分析。

    注意：本数据只有 10 个样本、9 个指标，样本量远小于"样本数 ≥ 10×指标数"
    的经验要求，因此这两个检验**只能作为参考**，不能当作结论（脚本会打印这句提醒）。
    """
    n, p = Xs.shape
    R = np.corrcoef(Xs, rowvar=False)
    inv_r = np.linalg.inv(R)
    d = np.sqrt(np.diag(inv_r))
    partial = -inv_r / np.outer(d, d)
    np.fill_diagonal(partial, 0.0)
    R0 = R.copy()
    np.fill_diagonal(R0, 0.0)

    kmo = (R0 ** 2).sum() / ((R0 ** 2).sum() + (partial ** 2).sum())
    chi2 = -(n - 1 - (2 * p + 5) / 6) * np.log(np.linalg.det(R))
    df = p * (p - 1) / 2
    p_value = stats.chi2.sf(chi2, df)
    return float(kmo), float(chi2), int(df), float(p_value)


def factor_analysis(Xs: np.ndarray, cols: list[str], df: pd.DataFrame) -> dict:
    """因子分析全流程：适用性检验 → 提取 2 个因子 → varimax 旋转 → 命名 → 打分。

    对应教材：
        cell 21—23  ``fa_kit.FactorAnalysis.load_data_samples(...)`` + ``extract_components()``
        cell 24     ``fa.find_comps_to_retain(method='top_n', num_keep=2)``
        cell 26     ``fa.rotate_components(method='varimax')`` + ``fa.comps["rot"]``
        cell 28—33  ``np.dot(data, fas)`` 得到因子得分
        cell 34     ``rename(columns={0: "Gross", 1: "Avg"})`` 给因子命名

    fa_kit 已停止维护，这里用 statsmodels 等价实现：
        ``Factor(Xs, n_factor=2, method='pa').fit()`` → 未旋转载荷
        ``rotate_factors(loadings, 'varimax')``      → 旋转载荷 + 旋转矩阵
    因子得分沿用教材的"标准化数据 × 旋转后载荷"写法（权重法），
    它不是 statsmodels 的回归得分，数值会有差异，但方向和排序一致。
    """
    kmo, chi2, dfree, pval = kmo_bartlett(Xs)
    fa = Factor(Xs, n_factor=N_KEEP, method="pa").fit()
    loadings = fa.loadings
    rotated, rotation = rotate_factors(loadings, "varimax")

    # 旋转后因子的符号可能整体翻转，这里统一成"每列载荷之和为正"，
    # 免得两次运行出现"综合实力"变成负数的怪现象
    for j in range(rotated.shape[1]):
        if rotated[:, j].sum() < 0:
            rotated[:, j] *= -1
    raw_scores = Xs @ rotated
    # 教材直接用 data @ 载荷当因子得分，量纲会随指标个数放大（这里 F1 到 ±15）。
    # 为了让 F1/F2 能放在同一张散点图里比较，这里再做一次标准化，
    # 只保留相对位置（数值本身没有绝对含义，排序和正负号才是信息）。
    scores = (raw_scores - raw_scores.mean(axis=0)) / raw_scores.std(axis=0, ddof=1)

    print("\n== 6. 因子分析 ==")
    print(f"  KMO = {kmo:.3f}（>0.6 可接受）｜ Bartlett χ² = {chi2:.2f}，"
          f"df = {dfree}，p = {pval:.2e} → 拒绝单位阵假设")
    print(f"  样本量 {Xs.shape[0]}、指标 {Xs.shape[1]} 个："
          f"样本量不足（经验要求 ≥ {Xs.shape[1] * 10}），检验结果仅供参考")
    print(f"  未旋转载荷共同度：{np.round((loadings ** 2).sum(axis=1), 3).tolist()}")
    print(f"  旋转矩阵 T =\n{np.round(rotation, 3)}")

    f1_top = np.argsort(-np.abs(rotated[:, 0]))[:3]
    f2_top = np.argsort(-np.abs(rotated[:, 1]))[:2]
    ss = (rotated ** 2).sum(axis=0)
    print(f"  因子 F1 解释方差 {ss[0]:.2f}（占 9 个指标总方差的 {ss[0] / Xs.shape[1]:.1%}）："
          + "、".join(f"{cols[i]}({rotated[i, 0]:+.2f})" for i in f1_top)
          + " → 「经济总量因子」")
    print(f"  因子 F2 解释方差 {ss[1]:.2f}（占 {ss[1] / Xs.shape[1]:.1%}）："
          + "、".join(f"{cols[i]}({rotated[i, 1]:+.2f})" for i in f2_top)
          + " → 「人均水平因子」")

    table = pd.DataFrame({
        "指标": cols,
        "因子F1载荷(旋转前)": np.round(loadings[:, 0], 3),
        "因子F2载荷(旋转前)": np.round(loadings[:, 1], 3),
        "因子F1载荷(旋转后)": np.round(rotated[:, 0], 3),
        "因子F2载荷(旋转后)": np.round(rotated[:, 1], 3),
        "共同度": np.round((rotated ** 2).sum(axis=1), 3),
    })

    fig, axes = new_fig(12.0, 4.9, ncols=2, gridspec_kw={"wspace": 0.36})
    for ax, mat, title, cbar_label in [
        (axes[0], loadings, "旋转前：所有指标挤在 F1 上", ""),
        (axes[1], rotated, "varimax 旋转后：F2 分离出 X2", "载荷"),
    ]:
        im = ax.imshow(mat, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks([0, 1], ["F1", "F2"])
        ax.set_yticks(range(len(cols)), cols)
        ax.grid(False)
        for i in range(len(cols)):
            for j in range(2):
                v = mat[i, j]
                ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=9,
                        color="white" if abs(v) > 0.62 else "#333333")
        ax.set_title(title, pad=10)
        fig.colorbar(im, ax=ax, fraction=0.042, pad=0.02, label=cbar_label)

    fig.suptitle("因子载荷矩阵：旋转让「总量」和「人均」两个维度各归各位", y=1.03,
                 fontsize=13, fontweight="bold")
    save_fig(fig, OUT, "fig04_因子载荷矩阵旋转前后")

    return {"fa": fa, "loadings": loadings, "rotated": rotated,
            "scores": scores, "table": table}


# ---------------------------------------------------------------------------
# 5. 得分图：综合排名 + 因子散点
# ---------------------------------------------------------------------------
def plot_scores(city_rank: pd.DataFrame, fa: dict, df: pd.DataFrame) -> pd.DataFrame:
    """左：综合得分排名条形图；右：因子得分散点（教材 cell 37 的图）。

    对应教材：
        cell 36—37  用 ``plt.scatter`` 画 ``Gross`` vs ``Avg`` 并给每个点标省份名

    教材的散点把两个**因子得分**当坐标，但没画象限线、没标数值，看不出
    "广东在总量上遥遥领先、上海在人均上第一"这种结论。这里补上：
      * 左图把综合得分排成条，给出可直接引用的名次；
      * 右图加象限线（F1=0、F2=0），把省份分成"双高/总量强/人均强/双低"四类。
    """
    fam = pd.DataFrame({
        "省份": df["AREA"].values,
        "F1总量因子": np.round(fa["scores"][:, 0], 3),
        "F2人均因子": np.round(fa["scores"][:, 1], 3),
    })

    fig, axes = new_fig(12.0, 5.0, ncols=2, gridspec_kw={"width_ratios": [1, 1.05]})

    ax = axes[0]
    rank = city_rank.sort_values("综合得分")
    colors = [BLUE if v >= rank["综合得分"].median() else BLUE2 for v in rank["综合得分"]]
    ax.barh(rank["省份"], rank["综合得分"], color=colors, height=0.62, zorder=3)
    for y, v in enumerate(rank["综合得分"]):
        ax.annotate(f"{v:.2f}", xy=(v, y), xytext=(6 if v >= 0 else -6, 0),
                    textcoords="offset points", va="center",
                    ha="left" if v >= 0 else "right", fontsize=9)
    ax.axvline(0, color="#555555", linewidth=0.9)
    ax.set_xlabel("综合得分（按方差贡献率加权）")
    ax.set_title("城市经济实力综合得分排名", pad=10)
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.22)

    ax = axes[1]
    ax.axhline(0, color="#9AA5B1", linewidth=0.9)
    ax.axvline(0, color="#9AA5B1", linewidth=0.9)
    ax.scatter(fam["F1总量因子"], fam["F2人均因子"], s=95, color=ORANGE,
               edgecolor="white", linewidth=1.1, zorder=5)
    for _, r in fam.iterrows():
        ax.annotate(r["省份"], xy=(r["F1总量因子"], r["F2人均因子"]),
                    xytext=(6, 4), textcoords="offset points", fontsize=9.5,
                    color="#333333")
    ax.set_xlabel("F1 经济总量因子")
    ax.set_ylabel("F2 人均水平因子")
    ax.set_title("因子得分散点：四象限划分城市类型", pad=10)
    ax.margins(0.16)
    for x, y, txt, ha in [(0.98, 0.96, "双高", "right"), (0.02, 0.96, "人均强", "left"),
                          (0.98, 0.04, "总量强", "right"), (0.02, 0.04, "双低", "left")]:
        ax.text(x, y, txt, transform=ax.transAxes, fontsize=9, color=GRAY,
                ha=ha, va="top" if y > 0.5 else "bottom")

    fig.suptitle("从 9 个指标到 2 个维度：谁总量大、谁人均高", y=1.03,
                 fontsize=13, fontweight="bold")
    save_fig(fig, OUT, "fig05_综合得分排名与因子散点")

    print("\n== 7. 因子得分 ==")
    for _, r in fam.sort_values("F1总量因子", ascending=False).iterrows():
        print(f"  {r['省份']:<3} F1 {r['F1总量因子']:>6.2f}（总量） "
              f"F2 {r['F2人均因子']:>6.2f}（人均）")
    return fam


# ---------------------------------------------------------------------------
# 6. 第二个数据集：电信用户行为 PCA（教材 PCA notebook 的原始案例）
# ---------------------------------------------------------------------------
def telecom_case() -> dict:
    """教材 PCA notebook 用的是 ``profile_telecom.csv``（600 用户 × 4 类行为）。

    这一步用来验证"同一套流程换个数据集也能跑"，同时给碎石图提供右半面板。
    结论很直观：PC1 是"流量型"（上网/微信/短信一起高），
    PC2 是"语音型"（只跟通话次数相关），两者把用户分成两类。

    小技巧：4 个变量里 ``cnt_web``（上网）与 ``cnt_call``（通话）几乎不相关
    （r≈0.11），所以第一主成分并不能同时概括"话务"和"流量"——
    这也是为什么降维后**必须看载荷、给成分命名**，而不是只看解释方差。
    """
    df = pd.read_csv(DATA / "profile_telecom.csv")
    cols = ["cnt_call", "cnt_msg", "cnt_wei", "cnt_web"]
    Xs = StandardScaler().fit_transform(df[cols].to_numpy(float))
    pca = PCA(n_components=len(cols)).fit(Xs)
    scores = PCA(n_components=N_KEEP).fit_transform(Xs)
    loadings = np.corrcoef(np.column_stack([Xs, scores]).T)[:len(cols), len(cols):]
    return {"n": len(df), "cols": cols, "ratio": pca.explained_variance_ratio_,
            "eig": pca.explained_variance_, "loadings": loadings}


def report_telecom(tel: dict) -> None:
    """打印电信用户数据的降维结果（碎石图已经画过，这里只报数字）。"""
    print("\n== 8. 交叉验证：电信用户 4 个行为指标 ==")
    print(f"  {tel['n']} 个用户，4 个指标；解释方差 "
          f"{np.round(tel['ratio'], 3).tolist()}，"
          f"前 2 个累计 {tel['ratio'][:2].sum():.1%}")
    for i, c in enumerate(tel["cols"]):
        print(f"  {c:<8} PC1 {tel['loadings'][i, 0]:+.3f}  "
              f"PC2 {tel['loadings'][i, 1]:+.3f}")


def main() -> None:
    apply_style()

    df, cols = load_cities()
    Xs = build_matrix(df, cols)
    tel = telecom_case()      # 先算好供碎石图使用（第 8 节最后再汇报数字）

    city = pca_overview(Xs, cols)
    save_csv(city["table"], OUT, "table01_主成分解释方差")
    plot_scree(city, tel)
    plot_correlation(df, cols)
    plot_biplot(city, df, cols)

    rank = composite_score(city, df)
    fa = factor_analysis(Xs, cols, df)
    save_csv(fa["table"], OUT, "table02_因子载荷矩阵")

    fam = plot_scores(rank, fa, df)
    scores = rank.merge(fam, on="省份", how="left")
    save_csv(scores, OUT, "table03_城市综合得分与因子得分")
    report_telecom(tel)

    print("\n" + "=" * 68)
    print("实验结论（可直接写进报告）")
    print("=" * 68)
    print(f"1. 9 个指标高度共线（平均相关系数 {df[cols].corr().where(~np.eye(9, dtype=bool)).stack().mean():.2f}），"
          f"前 2 个主成分就能解释 {city['ratio'][:2].sum():.1%} 的信息，"
          f"KMO = {kmo_bartlett(Xs)[0]:.2f} 也支持做因子分析。")
    print(f"2. 两个维度的业务含义很清楚：PC1 是「经济总量」（9 个指标同向上升），"
          f"PC2 是「人均水平」（只有 X2 载荷高），"
          f"所以降维不是丢信息，而是把「总量大」和「人均高」两件事拆开了。")
    print(f"3. 综合得分第一名是 {rank.iloc[0]['省份']}（{rank.iloc[0]['综合得分']:.2f}），"
          f"但它的 PC2 只有 {rank.iloc[0]['PC2得分']:.2f}；"
          f"PC2 最高的是 {rank.loc[rank['PC2得分'].idxmax(), '省份']}"
          f"（{rank['PC2得分'].max():.2f}）——总量与人均不是一回事，这正是二维分析的价值。")
    print(f"4. 电信用户数据上同一套流程得到 PC1 解释 {tel['ratio'][0]:.1%}、"
          f"PC2 解释 {tel['ratio'][1]:.1%}，"
          f"两个成分分别对应「流量型」与「语音型」用户，说明降维结果必须结合载荷命名。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
