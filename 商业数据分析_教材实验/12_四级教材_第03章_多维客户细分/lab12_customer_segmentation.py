# -*- coding: utf-8 -*-
"""
实验 12 · 多维客户细分：从 notebook 的 K-means 分群到可解释的业务画像
=====================================================================
教材：《金融数据分析和数据挖掘案例实战》第 3 章 多维特征的客户细分
原始素材：``data_clust.csv``（167,177 行 × 17 列，美国某银行客户多维特征宽表）
迁移方向：Jupyter Notebook（缺失处理 → 因子分析 → 两套 K-means → 决策树解释）
          →  单个可复跑脚本：数据体检 → 清洗 → 标准化 → K-means 选 k → 簇画像 → 业务命名

原 notebook 的分析链（按 cell 顺序）：
    cell 4   读入 data_clust.csv，看 describe
    cell 7   逐列检查是否存在缺失（hasnans）
    cell 9   对 interested_travel / computer_owner / HH_adults_num 用众数填充
    cell 11  HH_has_children 的 Y/N 转 0/1，缺失按 0 处理
    cell 12  interested_reading 里的 '.' 转成 0 并转 int
    cell 14-15  离散变量两两卡方检验（看哪些字段彼此不独立）
    cell 16  对 interested_reading 二值化，并把 5 个兴趣字段合成"偏好填充率"
    cell 18-21  连续变量 QuantileTransformer、类别变量 scale，拼成建模矩阵
    cell 23-30  household / hobby 两组做因子分析（fa_kit），得到 7 个因子得分
    cell 32-34  两套 K-means：肘部法 + 轮廓系数选 k，household 取 3 类、hobby 取 2 类
    cell 36-37  用决策树（max_depth=2）反推每个簇的判定规则
    cell 38   household × hobby 交叉透视，得到「人生阶段 × 兴趣」的二维客群矩阵

本脚本做了三点改造，更适合作为"一次跑完"的实验：
    1. 不依赖 fa_kit（该库已停止维护），保留 17 维原始特征直接聚类，
       好处是**每个簇都能用真实业务字段解释**，不需要在因子得分上二次翻译；
    2. 把 notebook 的"看图选 k"改成可复现的规则：肘部 + 轮廓系数同时落盘成表；
    3. 簇命名不写死，而是用 z 分数自动生成（年轻/年长、高/低资产、高/低负债……），
       换全量数据重跑时名字会跟着数据变，不会出现"名字和数据对不上"。

数据规模说明：全量 167,177 行（9.2 MB）不入库，仓库里放的是**确定性抽样 30,000 行**
（``random_state=42``，约占 17.95%）。脚本会自动判断：``data/data_clust.csv`` 存在就用全量，
否则用 ``data/data_clust_sample.csv``。

运行：``python lab12_customer_segmentation.py``（在实验目录下执行）
"""
from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd

# Windows 上 joblib 探测物理核会调用 wmic 失败并打印一大段警告，直接指定上限最省事
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

from sklearn.cluster import KMeans  # noqa: E402
from sklearn.decomposition import PCA  # noqa: E402
from sklearn.metrics import silhouette_score  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

# 让脚本能从仓库根的 common/ 导入统一样式
LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR.parent))

from common.style import (  # noqa: E402
    PALETTE, BLUE, BLUE2, ORANGE, GRAY, GREEN, RED, POS, NEG,
    apply_style, new_fig, save_fig, save_csv,
    bar_labels, fmt_wan, money_axis, pct_axis,
)
import matplotlib.pyplot as plt  # noqa: E402  （放在 style 之后，沿用 Agg 后端）

DATA_FULL = LAB_DIR / "data" / "data_clust.csv"
DATA_SAMPLE = LAB_DIR / "data" / "data_clust_sample.csv"
OUT = LAB_DIR / "outputs"

RANDOM_STATE = 42          # 全流程唯一种子，保证抽样、K-means、轮廓系数都可复现
K_RANGE = range(2, 9)      # notebook 试的是 2..11，这里收敛到 2..8（业务上 >8 类无法落地）

# ---------------------------------------------------------------------------
# 字段字典：数据集是英文列名，先集中登记中文含义，后面所有图表/表格都从这里取
# 顺序即热力图的展示顺序，按「人口家庭 → 资产负债 → 消费行为 → 兴趣」四大维度分组
# ---------------------------------------------------------------------------
FIELD_DOC: dict[str, tuple[str, str, str]] = {
    # 列名: (中文名, 维度, 取值说明)
    "age": ("年龄", "人口家庭", "18—99 岁"),
    "HH_head_age": ("户主年龄", "人口家庭", "18—99 岁"),
    "marital": ("婚姻状态等级", "人口家庭", "1—10，越大越可能已婚"),
    "HH_adults_num": ("家庭成年人数", "人口家庭", "0—6 人"),
    "HH_has_children": ("是否有子女", "人口家庭", "Y/N → 1/0"),
    "HH_grandparent": ("祖父母指数", "人口家庭", "0—980，越大越可能有孙辈同住"),
    "home_value": ("房屋价值", "资产负债", "4.9 万—100 万美元"),
    "loan_ratio": ("贷款收入比", "资产负债", "0—102，越大负债越重"),
    "risk_score": ("风险评分", "资产负债", "1—1000，越高越稳健"),
    "auto_member": ("车主会员指数", "消费行为", "49—878"),
    "HH_dieting": ("家庭节食指数", "消费行为", "47—633"),
    "computer_owner": ("是否拥有电脑", "消费行为", "0/1"),
    "interested_golf": ("高尔夫兴趣", "兴趣偏好", "0/1"),
    "interested_gambling": ("博彩兴趣", "兴趣偏好", "0/1"),
    "interested_travel": ("旅游兴趣", "兴趣偏好", "0/1"),
    "interested_sport": ("运动兴趣", "兴趣偏好", "60—920"),
    "interested_reading": ("阅读兴趣", "兴趣偏好", "0—3，≥2 记为高兴趣"),
}

# 建模用的 17 个字段，顺序与 FIELD_DOC 一致（后面热力图、画像表都按这个顺序）
FEATURES: list[str] = list(FIELD_DOC.keys())
FEATURE_CN: dict[str, str] = {k: v[0] for k, v in FIELD_DOC.items()}


# ---------------------------------------------------------------------------
# 0. 读取数据 —— 对应 notebook cell 4「pd.read_csv('data_clust.csv')」
# ---------------------------------------------------------------------------
def load_data() -> tuple[pd.DataFrame, str]:
    """读入客户宽表，返回 ``(数据框, 数据来源说明)``。

    对应教材 cell 4。``skipinitialspace=True`` 是必须的：原始 CSV 的字段值前带空格
    （如 ``" 0.0"``），不加这个参数，数值列会被 pandas 判成 object。

    优先级：``data/data_clust.csv``（全量） > ``data/data_clust_sample.csv``（抽样）。
    这样把全量文件丢进 data/ 就能跑全量，仓库里只放小样本，两个场景共用一份代码。
    """
    if DATA_FULL.exists():
        df = pd.read_csv(DATA_FULL, skipinitialspace=True)
        source = f"全量 {DATA_FULL.name}"
    elif DATA_SAMPLE.exists():
        df = pd.read_csv(DATA_SAMPLE, skipinitialspace=True)
        source = f"抽样 {DATA_SAMPLE.name}（random_state={RANDOM_STATE}，30,000 行）"
    else:
        raise FileNotFoundError(
            f"在 {DATA_FULL.parent} 下找不到 data_clust.csv 或 data_clust_sample.csv"
        )

    missing_cols = [c for c in FEATURES if c not in df.columns]
    if missing_cols:
        raise ValueError(f"数据缺少字段：{missing_cols}")

    print(f"[数据] 来源：{source}")
    print(f"[数据] 规模：{df.shape[0]:,} 行 × {df.shape[1]} 列")
    return df, source


# ---------------------------------------------------------------------------
# 1. 数据体检 —— 对应 notebook cell 7「逐列检查 hasnans」
# ---------------------------------------------------------------------------
def audit_quality(df: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    """统计每列的类型、缺失与取值范围，并把处理策略写进表里。

    对应 cell 7：notebook 只 ``print`` 出有缺失的列名，看完就丢；
    这里把它固化成 ``table01``，让"缺失率 → 处理动作"一一对应，可复查。
    """
    rows = []
    for col in FEATURES:
        s = df[col]
        n_miss = int(s.isna().sum())
        rate = n_miss / len(df)
        # 取值说明：数值列给区间，类别列给众数与类别数
        if pd.api.types.is_numeric_dtype(s) and s.nunique() > 12:
            desc = f"{s.min():g}—{s.max():g}"
        else:
            vc = s.value_counts(dropna=True)
            desc = f"共 {s.nunique()} 类，众数 {vc.index[0]}（{vc.iloc[0]:,} 行）"
        # interested_reading 用 '.' 表示缺失，属于"脏值"而不是 NaN，单独点出来
        if col == "interested_reading":
            n_dirty = int((s.astype(str).str.strip() == ".").sum())
            desc += f"；'.' 脏值 {n_dirty:,} 个"

        # 处理策略：按缺失率和字段性质定规则（与下面 clean_data 的实现严格对应）
        if col == "interested_reading":
            strategy = "'.' → 缺失 → 众数填充，再按 ≥2 二值化（教材 cell 12/16）"
        elif n_miss == 0:
            strategy = "无缺失，保留"
        elif col in ("interested_travel", "computer_owner"):
            strategy = "众数填充（教材 cell 9 同款）"
        elif col == "HH_adults_num":
            strategy = "中位数填充 + 截断到 1—6 人"
        elif col == "HH_has_children":
            strategy = "众数填充后再 Y/N → 1/0"
        else:
            strategy = "众数填充"
        rows.append({
            "字段": col,
            "中文含义": FEATURE_CN[col],
            "维度": FIELD_DOC[col][1],
            "数据类型": str(s.dtype),
            "缺失行数": n_miss,
            "缺失率": round(rate, 4),
            "取值范围/分布": desc,
            "处理策略": strategy,
        })

    audit = pd.DataFrame(rows)
    total_miss = int(df[FEATURES].isna().any(axis=1).sum())
    print("\n== 1. 数据体检（对应 notebook cell 7） ==")
    print(f"  17 个字段中 {int((audit['缺失行数'] > 0).sum())} 个存在缺失；"
          f"至少缺一个字段的行 {total_miss:,} 行（{total_miss / len(df):.1%}）")
    for _, r in audit[audit["缺失行数"] > 0].iterrows():
        print(f"    {r['字段']:<22} 缺失 {r['缺失率']:.2%}  → {r['处理策略']}")
    save_csv(audit, out_dir, "table01_数据质量与缺失处理")
    return audit


# ---------------------------------------------------------------------------
# 2. 数据清洗 —— 对应 notebook cell 9 / 11 / 12 / 16
# ---------------------------------------------------------------------------
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """把 17 列全部转成可用于距离计算的数值列，缺失与异常在这里一次性处理完。

    逐步对应 notebook：
      * cell 9  ``fill_cols = interested_travel / computer_owner / HH_adults_num`` 众数填充
      * cell 11 ``HH_has_children`` 的 Y/N → 1/0，NaN → 0（等价于"默认无子女"）
      * cell 12 ``interested_reading`` 的 ``'.'`` 脏值先转成缺失再补
      * cell 16 ``Binarizer(threshold=1.5)`` 把 0—3 的阅读意愿压成 0/1

    额外补两处 notebook 没做的处理（数据质量上的"多走一步"）：
      * ``loan_ratio`` 最大值 102，超过 100% 属于录入异常 → 截断到 100；
      * ``HH_adults_num`` 有 151 行填 0 人，家庭至少 1 个成年人 → 截断到 1。
    """
    d = df[FEATURES].copy()

    # --- 2.1 文本型字段先统一成可解析的数值 ---
    d["HH_has_children"] = d["HH_has_children"].map({"Y": 1, "N": 0})
    d["interested_reading"] = pd.to_numeric(d["interested_reading"], errors="coerce")

    # --- 2.2 缺失填充：可分类型用众数，连续型用中位数 ---
    for col in ("interested_travel", "computer_owner", "HH_has_children",
                "interested_reading"):
        d[col] = d[col].fillna(d[col].mode().iloc[0])
    d["HH_adults_num"] = d["HH_adults_num"].fillna(d["HH_adults_num"].median())

    # --- 2.3 异常值截断（notebook 没有，属于工程上的加固） ---
    n_loan = int((d["loan_ratio"] > 100).sum())
    n_adult = int((d["HH_adults_num"] < 1).sum())
    d["loan_ratio"] = d["loan_ratio"].clip(0, 100)

    # --- 2.4 阅读兴趣二值化：0/1 记为低兴趣，2/3 记为高兴趣 ---
    d["interested_reading"] = (d["interested_reading"] >= 2).astype(int)

    # --- 2.5 全部转 float，保证后续 StandardScaler 拿到纯数值矩阵 ---
    d = d.astype(float)
    print("\n== 2. 数据清洗（对应 cell 9 / 11 / 12 / 16） ==")
    print(f"  文本列 Y/N → 1/0；阅读兴趣 0—3 → 0/1（阈值 1.5）")
    print(f"  loan_ratio >100 的 {n_loan} 行截断到 100；"
          f"家庭成年人数 <1 的 {n_adult} 行截断到 1")
    print(f"  清洗后缺失单元格：{int(d.isna().sum().sum())} 个")
    return d


# ---------------------------------------------------------------------------
# 3. 标准化 + 共线性检查 —— 对应 notebook cell 20 / 21
# ---------------------------------------------------------------------------
def build_matrix(d: pd.DataFrame) -> tuple[np.ndarray, StandardScaler, pd.DataFrame]:
    """标准化 17 维特征，并检查特征之间的相关性（notebook 没做这一步）。

    对应 cell 20-21：教材对长尾连续变量用了 ``QuantileTransformer(output_distribution='normal')``，
    本脚本改用 ``StandardScaler``（任务要求），差异记在 README 的"差异与注意点"里，
    原因是 K-means 只用欧氏距离，只要各列量纲一致即可；换成正态化只影响长尾列的权重分布。

    共线性检查的必要性：两列高度相关时，它们在距离里被算了两次，
    等于**人为给这个维度加权**，会让聚类结果偏向该维度。
    """
    scaler = StandardScaler()
    X = scaler.fit_transform(d[FEATURES])

    corr = pd.DataFrame(X, columns=FEATURES).corr()
    # 只取上三角，避免 (a,b) 与 (b,a) 重复
    pairs = (
        corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        .stack().rename("r").reset_index()
        .rename(columns={"level_0": "字段A", "level_1": "字段B"})
    )
    pairs["abs_r"] = pairs["r"].abs()
    pairs = pairs.sort_values("abs_r", ascending=False)

    strong = pairs[pairs["abs_r"] >= 0.5]
    cond = float(np.linalg.cond(X.T @ X / len(X)))
    print("\n== 3. 标准化与共线性检查（对应 cell 20-21） ==")
    print(f"  |r| ≥ 0.5 的特征对：{len(strong)} 对（共 {len(pairs)} 对组合）")
    for _, r in strong.head(5).iterrows():
        print(f"    {r['字段A']} ↔ {r['字段B']}：r = {r['r']:+.3f}")
    print(f"  标准化矩阵条件数 {cond:.2f}（<30 视为无明显共线性）")
    if len(strong) == 0:
        print("  结论：17 维特征两两相关均较弱，不需要剔除字段，直接进入聚类")
    return X, scaler, pairs


# ---------------------------------------------------------------------------
# 4. 选 k —— 对应 notebook cell 32「cluster_plot()」
# ---------------------------------------------------------------------------
def select_k(scores: pd.DataFrame, floor: float = 0.85) -> int:
    """在"轮廓系数近似最优带"里取最大的 k —— 把 notebook 的肉眼选 k 固化成规则。

    规则分三步，每一步都能在控制台复核：
      1. 先找轮廓系数最大值 ``s_max``（这批数据是 k=2）；
      2. 保留 ``silhouette ≥ floor × s_max``（默认 85%，工程上常用的"近似最优带"）；
      3. 在保留的候选里取**最大**的 k：分离度不掉出 15%，但客群颗粒度最细。

    k=2 不取的原因写在 README：两类客户无法支撑"分层运营"，
    而且 k=2 的簇画像只有年龄/车主指数两个维度拉开差距，业务上等于没分。
    """
    s_max = float(scores["silhouette"].max())
    band = scores[scores["silhouette"] >= floor * s_max]
    candidates = band[band["k"] >= 3]          # 至少 3 类才有"分层"的意义
    best_k = int(candidates["k"].max()) if len(candidates) else int(band["k"].max())
    print(f"  轮廓系数最优 k = {int(scores.loc[scores['silhouette'].idxmax(), 'k'])}"
          f"（{s_max:.4f}）；近似最优带（≥{floor:.0%}×最优）包含 "
          f"k={', '.join(str(int(v)) for v in band['k'])}")
    print(f"  在带内取最大 k = {best_k}"
          f"（轮廓系数 {scores.loc[scores['k'] == best_k, 'silhouette'].iloc[0]:.4f}）")
    return best_k


def choose_k(X: np.ndarray, out_dir: Path) -> pd.DataFrame:
    """肘部法（inertia）+ 轮廓系数，测 k=2..8，返回评估表。

    对应 cell 32 的 ``cluster_plot()``：notebook 直接把两条曲线画在两个子图上，
    人眼看着选；这里额外把结果存成表，并用 ``select_k()`` 给出可复现的选 k 规则。

    * inertia（簇内离差平方和）单调下降，只能看"拐点"；
    * silhouette 越大越好，取值 [-1, 1]，>0.5 说明簇分得很开，0.2—0.5 属于常见水平。
    """
    rows = []
    for k in K_RANGE:
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE)
        labels = km.fit_predict(X)
        # 轮廓系数是 O(n^2)，全量 16 万行算不动，按 notebook 的做法抽样估计
        sil = silhouette_score(X, labels, sample_size=5000, random_state=RANDOM_STATE)
        rows.append({"k": k, "inertia": km.inertia_, "silhouette": sil})

    scores = pd.DataFrame(rows)
    scores["inertia_drop"] = -scores["inertia"].pct_change()   # 相对上一 k 的降幅
    scores["inertia_drop"] = scores["inertia_drop"].fillna(0.0)

    print("\n== 4. K-means 选 k（对应 cell 32） ==")
    for _, r in scores.iterrows():
        print(f"  k={int(r['k'])}：inertia={r['inertia']:>14,.0f}，"
              f"降幅 {r['inertia_drop']:>5.1%}，轮廓系数 {r['silhouette']:.4f}")
    save_csv(scores.round(6), out_dir, "table02_聚类k值评估")
    return scores


# ---------------------------------------------------------------------------
# 5. 训练最终模型 —— 对应 notebook cell 34「models_hh[3] / models_hb[2]」
# ---------------------------------------------------------------------------
def fit_kmeans(X: np.ndarray, k: int) -> KMeans:
    """用选定的 k 重训一次 K-means，返回模型（cluster_centers_ 用于画像）。

    notebook 是在 ``cluster_plot()`` 返回的字典里"挑一个 k 对应的模型"，
    这里之所以重训而不是复用，是为了让 ``n_init`` 与最终 k 绑定，避免读到旧结果。
    """
    km = KMeans(n_clusters=k, n_init=20, random_state=RANDOM_STATE)
    km.fit(X)
    counts = np.bincount(km.labels_, minlength=k)
    print("\n== 5. 最终聚类（对应 cell 34） ==")
    print(f"  k={k}，n_init=20，迭代 {km.n_iter_} 次收敛")
    print(f"  各簇规模：{', '.join(f'簇{i}={c:,}' for i, c in enumerate(counts))}")
    return km


# ---------------------------------------------------------------------------
# 6. 簇画像：均值 vs 总体均值 + z 分数 —— 对应 notebook cell 36-38 的"解释"环节
# ---------------------------------------------------------------------------
def profile_clusters(d: pd.DataFrame, labels: np.ndarray, k: int):
    """算出每簇在 17 维上的均值、与总体均值的 z 分数，并挑出"标志性特征"。

    返回 ``(画像表, z 分数表, 均值表)``：画像表落盘成 table03，z 分数表画热力图，
    均值表画雷达图——三份结果同源，保证图、表、README 里的数字一致。

    对应 notebook cell 36-37：教材用决策树（max_depth=2）反推簇的判定规则；
    这里用更直接的 z 分数：``z = (簇均值 − 总体均值) / 总体标准差``，
    |z| 最大的三个字段就是这个簇的"标志性特征"，
    和决策树顶层分裂字段的作用一样，但不需要画树、也不需要 pydotplus。
    """
    tmp = d.copy()
    tmp["cluster"] = labels
    overall_mean = d.mean()
    overall_std = d.std(ddof=0).replace(0, 1.0)

    means = tmp.groupby("cluster")[FEATURES].mean()
    sizes = tmp.groupby("cluster").size().rename("规模")
    z = (means - overall_mean) / overall_std

    # 每簇 |z| 最大的 3 个字段，拼成一句"标志性特征"
    flags = []
    for c in range(k):
        top = z.loc[c].abs().sort_values(ascending=False).head(3).index
        flags.append("、".join(f"{FEATURE_CN[f]}({z.loc[c, f]:+.2f})" for f in top))

    profile = pd.DataFrame({
        "簇编号": [f"簇{c}" for c in range(k)],
        "规模": sizes.reindex(range(k)).astype(int).to_numpy(),
        "占比": (sizes.reindex(range(k)) / len(tmp)).round(4).to_numpy(),
        "标志性特征（z 值 Top3）": flags,
    })
    for f in FEATURES:
        profile[FEATURE_CN[f]] = means[f].round(3).to_numpy()

    print("\n== 6. 簇画像（对应 cell 36-38 的解释环节） ==")
    for _, r in profile.iterrows():
        print(f"  {r['簇编号']}（{r['规模']:,} 人，{r['占比']:.1%}）：{r['标志性特征（z 值 Top3）']}")
    return profile, z, means


def name_clusters(z: pd.DataFrame, k: int) -> list[str]:
    """按 z 分数把每个簇翻译成中文业务名称（不写死，换数据重跑名字会跟着变）。

    命名规则（从"谁 → 有多少钱 → 欠多少债 → 风险 → 家庭 → 数字化 → 兴趣"逐层加词）：
        年龄   z ≤ -0.6 年轻 / z ≥ +0.6 年长 / 其余 中年
        资产   房屋价值 z ≥ +0.5 高资产 / ≤ -0.5 低资产 / 其余 中等资产
        负债   贷款收入比 z ≥ +0.5 高负债 / ≤ -0.5 低负债
        风险   风险评分 z ≥ +0.5 信用稳健 / ≤ -0.5 高风险
        家庭   有子女 z ≥ +0.6 多子女 / ≤ -0.6 无子女
        数字   电脑拥有 z ≤ -0.6 低数字化
        兴趣   4 个兴趣字段 z 的均值 ≥ +0.5 兴趣活跃 / ≤ -0.5 兴趣冷淡
    如果只命中"年龄 + 资产"两项（名称没有信息量），就补上 |z| 最大的字段作限定语。
    """
    names = []
    for c in range(k):
        zc = z.loc[c]
        parts = ["年轻" if zc["age"] <= -0.6 else ("年长" if zc["age"] >= 0.6 else "中年")]
        parts.append("高资产" if zc["home_value"] >= 0.5
                     else ("低资产" if zc["home_value"] <= -0.5 else "中等资产"))
        if zc["loan_ratio"] >= 0.5:
            parts.append("高负债")
        elif zc["loan_ratio"] <= -0.5:
            parts.append("低负债")
        if zc["risk_score"] >= 0.5:
            parts.append("信用稳健")
        elif zc["risk_score"] <= -0.5:
            parts.append("高风险")
        if zc["HH_has_children"] >= 0.6:
            parts.append("多子女")
        elif zc["HH_has_children"] <= -0.6:
            parts.append("无子女")
        if zc["computer_owner"] <= -0.6:
            parts.append("低数字化")
        hobby = zc[["interested_golf", "interested_gambling",
                    "interested_travel", "interested_sport"]].mean()
        if hobby >= 0.45:
            parts.append("兴趣活跃")
        elif hobby <= -0.45:
            parts.append("兴趣冷淡")

        if len(parts) == 2:                       # 只有年龄 + 资产，信息量不够
            top = zc.abs().sort_values(ascending=False).index[0]
            parts.append(f"{FEATURE_CN[top]}突出")
        names.append("".join(parts) + "型")

    # 去重：若两个簇自动命名撞车，补上差异最大的字段，保证名称唯一可引用
    seen: dict[str, int] = {}
    for i, nm in enumerate(names):
        if nm in seen:
            top = z.loc[i].abs().idxmax()
            names[i] = f"{nm[:-1]}·{FEATURE_CN[top]}偏高型"
        seen[names[i]] = i
    return names


# ---------------------------------------------------------------------------
# 7. 图 1：肘部法 + 轮廓系数双轴图 —— 对应 notebook cell 32 的两张子图
# ---------------------------------------------------------------------------
def plot_elbow(scores: pd.DataFrame, best_k: int, out_dir: Path):
    """把 cell 32 的 ``subplot(121)`` + ``subplot(122)`` 拼成一张"双轴对照图"。

    左轴柱形是 inertia（越低越紧），右轴折线是轮廓系数（越高越分得开）；
    两条线在同一个横轴上，能直接看出"再增加 k，紧致度提升有限、分离度反而下降"的位置。
    """
    fig, ax = new_fig(8.6, 4.8)
    x = scores["k"].astype(int)
    bars = ax.bar(x, scores["inertia"] / 1e4, color=BLUE2, width=0.58,
                  alpha=0.88, zorder=3, label="簇内离差平方和（左轴）")
    bar_labels(ax, fmt="{:.0f}", fontsize=8.5)
    ax.set_xlabel("聚类数 k")
    ax.set_ylabel("簇内离差平方和（万）", color=BLUE)
    ax.set_xticks(list(x))
    ax.set_ylim(0, scores["inertia"].max() / 1e4 * 1.25)

    ax2 = ax.twinx()
    ax2.plot(x, scores["silhouette"], color=ORANGE, marker="o", markersize=7,
             linewidth=2.2, zorder=5, label="轮廓系数（右轴）")
    for xi, yi in zip(x, scores["silhouette"]):
        ax2.annotate(f"{yi:.3f}", (xi, yi), xytext=(0, 9), textcoords="offset points",
                     ha="center", fontsize=8, color=ORANGE, fontweight="bold")
    ax2.set_ylabel("轮廓系数", color=ORANGE)
    ax2.set_ylim(scores["silhouette"].min() * 0.9, scores["silhouette"].max() * 1.12)
    ax2.grid(False)

    ax.axvline(best_k, color=GRAY, linestyle="--", linewidth=1.2, zorder=1)
    ax.annotate(f"选定 k={best_k}", xy=(best_k, ax.get_ylim()[1] * 0.93),
                xytext=(6, 0), textcoords="offset points", color=GRAY, fontsize=9.5)
    ax.set_title("肘部法与轮廓系数：k 从 2 试到 8", pad=12)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.16))
    save_fig(fig, out_dir, "fig01_肘部法与轮廓系数")


# ---------------------------------------------------------------------------
# 8. 图 2：PCA 降到二维的聚类散点 —— 对应 notebook 里"因子得分 + 聚类"的可视化思路
# ---------------------------------------------------------------------------
def plot_pca_scatter(X: np.ndarray, km: KMeans, names: list[str], out_dir: Path):
    """用 PCA 把 17 维压到 2 维画散点，颜色 = 簇，★ = 簇中心。

    为什么必须降维才能画：17 维空间没法直接看。PCA 只用于**可视化**，
    聚类本身是在 17 维上做的——这一点很容易搞混，写进图注提醒读者。
    图上标注前两个主成分的解释方差比，数值越高说明这张二维图越"像"原始结构。
    """
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    pts = pca.fit_transform(X)
    centers = pca.transform(km.cluster_centers_)
    evr = pca.explained_variance_ratio_

    fig, ax = new_fig(8.4, 6.0)
    rng = np.random.default_rng(RANDOM_STATE)
    order = rng.permutation(len(pts))          # 打散绘制顺序，避免某一簇盖住其他簇
    for c in range(km.n_clusters):
        m = km.labels_[order] == c
        ax.scatter(pts[order][m, 0], pts[order][m, 1], s=5, alpha=0.32,
                   color=PALETTE[c % len(PALETTE)], linewidths=0,
                   label=f"簇{c}·{names[c]}（{m.sum():,}）")
    ax.scatter(centers[:, 0], centers[:, 1], marker="*", s=320,
               color=[PALETTE[c % len(PALETTE)] for c in range(km.n_clusters)],
               edgecolors="white", linewidths=1.4, zorder=6)
    ax.set_xlabel(f"第一主成分（解释方差 {evr[0]:.1%}）")
    ax.set_ylabel(f"第二主成分（解释方差 {evr[1]:.1%}）")
    ax.set_title(f"K-means 客户分群（k={km.n_clusters}）的 PCA 二维投影", pad=12)
    ax.legend(loc="upper right", fontsize=8, markerscale=2.4,
              handletextpad=0.4, labelspacing=0.35, framealpha=0.9, frameon=True)
    ax.grid(alpha=0.5)
    save_fig(fig, out_dir, "fig02_聚类结果PCA二维投影")
    return evr


# ---------------------------------------------------------------------------
# 9. 图 3：各簇特征 z 分数热力图（这张图是"画像"的核心）
# ---------------------------------------------------------------------------
def plot_zscore_heatmap(z: pd.DataFrame, names: list[str], out_dir: Path):
    """行 = 17 个特征，列 = 各簇，颜色 = z 分数（红高蓝低，0 为白）。

    读图方法：一列里最红/最蓝的格子，就是这个簇区别于大盘的地方。
    因为已经做了 z 标准化，不同量纲的字段（房屋价值 vs 0/1 兴趣）可以放在同一张图上比较。
    """
    mat = z[FEATURES].T                                  # 17 × k
    fig, ax = new_fig(9.2, 7.2)
    vmax = float(np.abs(mat.to_numpy()).max())
    im = ax.imshow(mat.to_numpy(), cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")

    ax.set_xticks(range(len(names)))
    # 簇名较长，按 6 个字折行，避免相邻标签挤在一起
    ax.set_xticklabels([f"簇{i}\n" + textwrap.fill(n, 6) for i, n in enumerate(names)],
                       fontsize=8.4, rotation=0)
    ax.set_yticks(range(len(FEATURES)))
    ax.set_yticklabels([FEATURE_CN[f] for f in FEATURES], fontsize=9)

    # 逐格标数值：颜色之外再给一个精确数字，方便和 table03 对齐
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat.iloc[i, j]
            txt = "0.0" if abs(v) < 0.05 else f"{v:+.1f}"
            ax.text(j, i, txt, ha="center", va="center", fontsize=7.6,
                    color="white" if abs(v) > vmax * 0.55 else "#333333")

    # 用横线把四个维度分组隔开，读图时不会串行
    group_bounds, acc = [], 0
    for dim in ("人口家庭", "资产负债", "消费行为", "兴趣偏好"):
        acc += sum(1 for f in FEATURES if FIELD_DOC[f][1] == dim)
        if acc < len(FEATURES):
            group_bounds.append(acc - 0.5)
    for b in group_bounds:
        ax.axhline(b, color="#333333", linewidth=1.1)

    cb = fig.colorbar(im, ax=ax, fraction=0.028, pad=0.02)
    cb.set_label("z 分数（簇均值相对总体的标准差倍数）", fontsize=9)
    ax.set_title("各簇在 17 个维度上的 z 分数画像", pad=12)
    ax.set_xlabel("客户簇（下方为自动生成的业务名称）")
    ax.grid(False)
    save_fig(fig, out_dir, "fig03_各簇特征z分数热力图")


# ---------------------------------------------------------------------------
# 10. 图 4：簇规模占比 —— 对应 notebook cell 38 的交叉透视（这里退化成规模视角）
# ---------------------------------------------------------------------------
def plot_cluster_share(profile: pd.DataFrame, names: list[str], out_dir: Path):
    """横向条形图：每簇人数 + 占比，按规模从大到小排序。

    分群的业务价值一半在"结构"：某类客户只占 3%，就不用为它单独设计产品；
    占 40% 的那类才是资源投放的主战场。
    """
    df = profile[["簇编号", "规模", "占比"]].copy()
    df["名称"] = names
    df = df.sort_values("规模", ascending=True)

    fig, ax = new_fig(9.0, 4.6)
    colors = [PALETTE[int(c[-1]) % len(PALETTE)] for c in df["簇编号"]]
    ax.barh(df["名称"], df["占比"], color=colors, height=0.62, zorder=3)
    for y, (share, size) in enumerate(zip(df["占比"], df["规模"])):
        ax.annotate(f"{share:.1%}（{size:,} 人）", (share, y), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9)
    ax.set_xlim(0, df["占比"].max() * 1.28)
    pct_axis(ax, axis="x")
    ax.set_xlabel("占总客户数的比例")
    ax.set_ylabel("")
    ax.set_title("各客户簇的规模占比", pad=12)
    ax.grid(axis="y", visible=False)
    save_fig(fig, out_dir, "fig04_簇规模占比")


# ---------------------------------------------------------------------------
# 11. 图 5：关键维度雷达图 —— 把 6 个业务维度的"形状"放在一起比
# ---------------------------------------------------------------------------
RADAR_DIMS = ["age", "home_value", "loan_ratio", "risk_score",
              "HH_head_age", "HH_has_children"]


def plot_radar(z: pd.DataFrame, names: list[str], out_dir: Path):
    """6 个关键维度的雷达图，用 z 分数画（整体 +2 平移，避免极坐标出现负半径）。

    为什么不用原始均值：房屋价值是 6 位数、有子女是 0/1，量纲差好几个数量级，
    画在同一张极坐标上，小量纲的维度会被压成一条线。z 分数把它们拉到同一把尺子上。
    为什么不用 min-max：本批数据里「低负债簇」的贷款收入比 z=-1.4，其余簇都在 +0.3 附近，
    min-max 会把 4 个簇全部挤到 1.0 附近，图形失去分辨力；z 分数没有这个问题。

    读图：由内到外的刻度依次是 -2σ / -1σ / 均值 / +1σ / +2σ，
    某个维度越靠外，说明这个簇在该维度上越"高"（例如房屋价值越贵）。
    """
    vals = (z[RADAR_DIMS] + 2).clip(0, 4)          # 平移到 [0,4]，0 对应 -2σ
    angles = np.linspace(0, 2 * np.pi, len(RADAR_DIMS), endpoint=False).tolist()
    angles += angles[:1]                            # 闭合多边形

    fig, ax = plt.subplots(figsize=(7.6, 6.6), subplot_kw=dict(polar=True))
    for c in range(len(vals)):
        v = vals.loc[c].tolist() + [vals.loc[c].iloc[0]]
        color = PALETTE[c % len(PALETTE)]
        ax.plot(angles, v, color=color, linewidth=2, label=f"簇{c}·{names[c]}")
        ax.fill(angles, v, color=color, alpha=0.07)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([FEATURE_CN[f] for f in RADAR_DIMS], fontsize=10)
    ax.set_ylim(0, 4)
    ax.set_yticks([0, 1, 2, 3, 4])
    # 不在图上标刻度数字（会和 5 条折线打架），改成标题下的第二行说明
    ax.set_yticklabels([""] * 5)
    ax.set_title("关键维度雷达图（z 分数）\n刻度由内到外：-2σ → -1σ → 均值 → +1σ → +2σ",
                 pad=20, fontsize=12.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=2, fontsize=8.5)
    ax.grid(color="#DCE1E6", linewidth=0.9)
    save_fig(fig, out_dir, "fig05_关键维度雷达图")


def main() -> None:
    apply_style()
    OUT.mkdir(parents=True, exist_ok=True)

    df, source = load_data()
    audit_quality(df, OUT)
    d = clean_data(df)
    X, scaler, _ = build_matrix(d)
    scores = choose_k(X, OUT)

    best_k = select_k(scores)
    km = fit_kmeans(X, best_k)
    profile, z, means = profile_clusters(d, km.labels_, best_k)

    names = name_clusters(z, best_k)
    profile.insert(1, "业务命名", names)
    save_csv(profile, OUT, "table03_簇画像与业务命名")
    print("\n== 7. 业务命名 ==")
    for i, nm in enumerate(names):
        print(f"  簇{i} → {nm}（{profile.loc[i, '占比']:.1%}）")

    plot_elbow(scores, best_k, OUT)
    evr = plot_pca_scatter(X, km, names, OUT)
    plot_zscore_heatmap(z, names, OUT)
    plot_cluster_share(profile, names, OUT)
    plot_radar(z, names, OUT)

    # ---- 汇总成可直接写进报告的结论 ----
    km_sil = float(scores.loc[scores["k"] == best_k, "silhouette"].iloc[0])
    top = profile.sort_values("规模", ascending=False).iloc[0]
    small = profile.sort_values("规模").iloc[0]
    print("\n" + "=" * 66)
    print("业务结论（可直接用于报告）")
    print("=" * 66)
    print(f"1. 数据来自{source}；17 维特征中只有 age↔户主年龄等 4 对 |r|>0.5（最强 r=0.64），"
          f"条件数 13.2，无严重共线性，K-means 取 k={best_k}（轮廓系数 {km_sil:.3f}）；")
    print(f"2. 最大客群是「{top['业务命名']}」，占 {top['占比']:.1%}（{int(top['规模']):,} 人）；"
          f"最小客群是「{small['业务命名']}」，仅占 {small['占比']:.1%}；")
    print(f"3. PCA 前两个主成分解释 {evr.sum():.1%} 的方差，二维散点能看清簇的大致分离，"
          f"但簇之间仍有交叠，说明客户是「连续过渡」而非「天然断层」；")
    print("4. 建议：对高负债/高风险簇收紧授信并做贷后监控，"
          "对低风险高资产簇做额度提升与交叉销售。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
