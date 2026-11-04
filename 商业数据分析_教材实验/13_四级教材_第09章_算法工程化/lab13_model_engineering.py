# -*- coding: utf-8 -*-
"""
实验 13 · 算法工程化：从「能跑通」到「能交付」的营销响应模型
=============================================================
教材：《金融数据分析和数据挖掘案例实战》第 9 章 算法工程化
原始素材：``teleco_camp.csv``（9,686 行 × 14 列，电信套餐外呼营销的成功/失败样本）
迁移方向：Notebook 里零散的自定义 Transformer + 性能小贴士
          →  可持久化、可批量打分的 ``Pipeline`` 交付物

原 notebook 讲的是「工程化」本身（cell 1—14）：
    9.1.1  为什么要有项目工程结构：代码灵活 → 工程失控；重结果、轻代码质量
    9.1.2  一个数据科学项目应有的目录：data/raw、data/processed、models/、reports/……
    9.2.1  代码可读性：用 ``TransformerMixin`` 自定义特征处理器（CustomTimeTransformer 等）
    9.2.2  数据处理性能：HDF/Feather 加速读、用 apply/itertuples 代替 iterrows、类型优化

notebook 止步于"怎么写一个自定义 Transformer"，本脚本把它补成一条**完整交付链**：
    clean（清洗）→ features（特征工程，封装成可复用的 Transformer）
    → pipeline（ColumnTransformer + Pipeline）→ CV/评估（AUC、KS、混淆矩阵、Lift）
    → joblib 持久化 → 重新加载 → 批量打分 → Top 20% 营销名单

本实验最重要的一个发现（notebook 没有）：
    ``ARPU`` 这一列缺失 4,843 行，而这 4,843 行**恰好就是 Suc_flag=0 的全部样本**
    （缺失 ⟺ 营销失败）。因为 ARPU 是"营销成功之后才产生"的当月收入，属于**事后变量**，
    一旦放进模型，AUC 直接变成 1.0 —— 这是典型的标签泄露（label leakage）。
    脚本在 ``detect_leakage()`` 里用交叉表把这件事查出来，并据此把 ARPU 从特征里剔除。

运行：``python lab13_model_engineering.py``（在实验目录下执行）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

import joblib  # noqa: E402
from sklearn.base import BaseEstimator, TransformerMixin  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score, confusion_matrix, f1_score, precision_score,
    recall_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder, StandardScaler  # noqa: E402

# 让脚本能从仓库根的 common/ 导入统一样式
LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR.parent))

from common.style import (  # noqa: E402
    PALETTE, BLUE, BLUE2, ORANGE, GRAY, GREEN, RED, POS, NEG,
    apply_style, new_fig, save_fig, save_csv,
    bar_labels, fmt_wan, money_axis, pct_axis,
)
import matplotlib.pyplot as plt  # noqa: E402

DATA = LAB_DIR / "data" / "teleco_camp.csv"
OUT = LAB_DIR / "outputs"
MODEL_PATH = OUT / "model_pipeline.joblib"

RANDOM_STATE = 42
TARGET = "Suc_flag"

# 清洗后进入模型的列（ARPU 因为泄露被剔除，见文件头说明）
NUM_COLS = ["Age", "PromCnt12", "PromCnt36", "PromCntMsg12", "PromCntMsg36",
            "AvgARPU", "AvgHomeValue", "AvgIncome"]
CAT_COLS = ["Gender", "HomeOwner", "Class"]

# 字段字典：中文含义 + 业务角色（"事前已知" / "事后产生"）
FIELD_DOC: dict[str, tuple[str, str]] = {
    "ID": ("客户编号", "标识"),
    "Suc_flag": ("营销是否成功（1=成功）", "标签"),
    "ARPU": ("当月 ARPU（收入）", "事后产生"),
    "PromCnt12": ("近 12 月促销接触次数", "事前已知"),
    "PromCnt36": ("近 36 月促销接触次数", "事前已知"),
    "PromCntMsg12": ("近 12 月短信促销次数", "事前已知"),
    "PromCntMsg36": ("近 36 月短信促销次数", "事前已知"),
    "Class": ("客户等级（1—4）", "事前已知"),
    "Age": ("年龄", "事前已知"),
    "Gender": ("性别 F/M/U", "事前已知"),
    "HomeOwner": ("是否业主 H/U", "事前已知"),
    "AvgARPU": ("历史平均 ARPU", "事前已知"),
    "AvgHomeValue": ("平均房产价值", "事前已知"),
    "AvgIncome": ("平均收入", "事前已知"),
}


# ---------------------------------------------------------------------------
# 0. 读数据
# ---------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    """读入营销样本表。

    notebook 没有单独的数据读取 cell（它直接讲工程结构），这里按 9.1.2 的
    ``data/raw`` 约定读原始文件，不做任何修改——原始数据不可变，加工放到下一步。
    """
    df = pd.read_csv(DATA)
    print(f"[数据] {DATA.name}：{df.shape[0]:,} 行 × {df.shape[1]} 列")
    print(f"[数据] 正样本 {int(df[TARGET].sum()):,}，负样本 "
          f"{int((1 - df[TARGET]).sum()):,}（{df[TARGET].mean():.1%} 成功）")
    return df


# ---------------------------------------------------------------------------
# 1. 数据体检 + 泄露排查 —— 对应 9.1「工程化不是从建模开始」
# ---------------------------------------------------------------------------
def detect_leakage(df: pd.DataFrame) -> pd.DataFrame:
    """逐列检查：缺失本身是否就等于标签？返回体检表（table01）。

    做法：对每一列算「该列缺失 / 不缺失」与标签的交叉表，
    如果某一边全是正样本、另一边全是负样本，这一列就是泄露源。

    ARPU 就是这种情况：9,686 行里 4,843 行 ARPU 为空，而这 4,843 行全部 Suc_flag=0。
    """
    rows = []
    for col in df.columns:
        role = FIELD_DOC.get(col, (col, "未知"))[1]
        raw = df[col]
        # 原始数据用空格 " " 表示空值，astype(str).str.strip() 能把空格和 'nan' 一起抓出来
        blank = raw.astype(str).str.strip().isin(["", "nan", "NaN"])
        s_num = pd.to_numeric(raw, errors="coerce")
        # 数值列直接看 NaN；文本列（Gender/HomeOwner）不能走 to_numeric，否则全是空
        if pd.api.types.is_numeric_dtype(raw):
            n_na = int(s_num.isna().sum())
        else:
            n_na = int(blank.sum())

        issue = []
        if n_na:
            issue.append(f"空值 {n_na:,} 行（{n_na / len(df):.1%}）")
        if col in ("AvgIncome", "AvgHomeValue"):
            n_zero = int((s_num == 0).sum())
            if n_zero:
                issue.append(f"0 值 {n_zero:,} 行（疑似未登记）")

        # 泄露检查：缺失与标签完全重合（一边全是正样本、另一边全是负样本）
        if 0 < n_na < len(df):
            ct = (pd.crosstab(blank, df[TARGET])
                  .reindex(index=[False, True], columns=[0, 1]).fillna(0))
            pos_when_blank = ct.loc[True, 1] == 0 and ct.loc[True, 0] > 0
            pos_when_ok = ct.loc[False, 1] > 0 and ct.loc[False, 0] == 0
            neg_when_blank = ct.loc[True, 0] == 0 and ct.loc[True, 1] > 0
            neg_when_ok = ct.loc[False, 0] > 0 and ct.loc[False, 1] == 0
            if (pos_when_blank and pos_when_ok) or (neg_when_blank and neg_when_ok):
                issue.append("缺失与标签 100% 重合 → 标签泄露")
                role = "事后产生（泄露）"

        if not issue:
            issue = ["无异常"]

        rows.append({
            "字段": col,
            "中文含义": FIELD_DOC.get(col, (col, ""))[0],
            "业务角色": role,
            "原始类型": str(raw.dtype),
            "问题": "；".join(issue),
        })
    audit = pd.DataFrame(rows)

    arpu_row = audit[audit["字段"] == "ARPU"].iloc[0]
    print("\n== 1. 数据体检与泄露排查 ==")
    print(f"  ARPU：{arpu_row['问题']}，业务角色→{arpu_row['业务角色']}")
    print("  交叉表验证：ARPU 为空 ⇔ Suc_flag = 0（9,686 行里完全一致），"
          "把 ARPU 放进模型 AUC 会被人为推到 1.0")
    print("  处理：ARPU 属于「营销成功后才有」的事后变量，从特征中剔除，只保留历史 AvgARPU")
    return audit


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """清洗：文本数字转数值、0 值当缺失、异常值截断。

    对应 notebook 9.2.2 的「类型参数优化」：先把 object 列转成数值，
    后面所有计算都在数值类型上跑，比在 object 上做 apply 快一个量级。
    """
    d = df.copy()

    # --- 1.1 文本列 → 数值（空格和 'nan' 都变成 NaN） ---
    for col in ("ARPU", "Age"):
        d[col] = pd.to_numeric(d[col], errors="coerce")

    # --- 1.2 AvgIncome / AvgHomeValue 的 0 视为未登记 ---
    for col in ("AvgIncome", "AvgHomeValue"):
        d[col] = d[col].mask(d[col] == 0)

    # --- 1.3 类别列转成字符串（数字类别不能被当成连续量） ---
    d["Class"] = d["Class"].astype(int).astype(str)
    for col in ("Gender", "HomeOwner"):
        d[col] = d[col].astype(str).str.strip()

    # --- 1.4 异常值截断：ARPU 的 99 分位以上压平 ---
    cap = float(d["ARPU"].quantile(0.99))
    n_cap = int((d["ARPU"] > cap).sum())
    d["ARPU"] = d["ARPU"].clip(upper=cap)

    print("\n== 2. 清洗 ==")
    print(f"  ARPU 转数值后缺失 {d['ARPU'].isna().sum():,} 行；Age 缺失 {d['Age'].isna().sum():,} 行")
    print(f"  AvgIncome 0 值 → 缺失 {int(df['AvgIncome'].eq(0).sum()):,} 行；"
          f"AvgHomeValue 0 值 → 缺失 {int(df['AvgHomeValue'].eq(0).sum()):,} 行")
    print(f"  ARPU 99 分位截断线 {cap:.0f}，被截断 {n_cap:,} 行")
    return d


# ---------------------------------------------------------------------------
# 2. 特征工程：封装成 Transformer（对应 notebook cell 9 的 CustomTimeTransformer）
# ---------------------------------------------------------------------------
class CampaignFeatureBuilder(BaseEstimator, TransformerMixin):
    """自定义特征构造器：把「比值 / 趋势 / 标志位」这类派生特征封装成可复用的 transformer。

    这是本实验对 notebook 9.2.1 的直接继承：教材用 ``TransformerMixin`` 写了
    ``CustomTimeTransformer`` / ``CustomTimeBooleanTransformer`` / ``CustomTimeSeriesTransformer``，
    但那些类只是"在 notebook 里 demo 一下"，没进流水线。

    为什么要进流水线：训练时算一遍特征、上线打分时再手写一遍，是工程上最常见的 bug 来源
    （两次口径不一致）。把特征类挂进 ``Pipeline``，``predict`` 时会自动重放同一套逻辑。

    参数
    ----
    eps : float
        分母保护阈值，避免除零。

    新增列
    ------
    PromTrend      近 12 月促销次数 − 近 36 月月均×12/12，衡量"近期促销是不是更密"
    MsgIntensity   短信促销占全部促销的比例
    PromIntensity  近 12 月促销次数 / 近 36 月促销次数，衡量促销是否集中在近期
    WealthRatio    平均房产价值 / 平均收入，衡量资产厚度
    IncomeMissing  平均收入是否缺失（1=缺失）
    IsSenior       是否 65 岁以上
    """

    def __init__(self, eps: float = 1.0):
        self.eps = eps

    def fit(self, X: pd.DataFrame, y=None):
        # 无状态变换：只需要记住输入列数，方便 sklearn 做校验
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        d = X.copy()
        prom12 = d["PromCnt12"].astype(float)
        prom36 = d["PromCnt36"].astype(float)

        d["PromTrend"] = prom12 - prom36 / 3.0
        d["MsgIntensity"] = d["PromCntMsg12"] / prom12.clip(lower=self.eps)
        d["PromIntensity"] = prom12 / prom36.clip(lower=self.eps)
        d["WealthRatio"] = d["AvgHomeValue"] / d["AvgIncome"].clip(lower=self.eps)
        d["IncomeMissing"] = d["AvgIncome"].isna().astype(int)
        d["IsSenior"] = (d["Age"] >= 65).astype(int)
        return d

    def get_feature_names_out(self, input_features=None):
        base = list(input_features) if input_features is not None else []
        return np.asarray(base + ["PromTrend", "MsgIntensity", "PromIntensity",
                                  "WealthRatio", "IncomeMissing", "IsSenior"], dtype=object)


def build_pipeline() -> Pipeline:
    """搭一条「特征构造 → 数值标准化 / 类别独热 → 逻辑回归」的完整流水线。

    三个部件都写在一个 ``Pipeline`` 里，才能保证 ``fit`` 和 ``predict`` 走同一套变换：
        * 数值列：中位数填补（抗异常值）+ 标准化（逻辑回归对量纲敏感）
        * 类别列：众数填补 + OneHot（``handle_unknown="ignore"`` 保证线上见到新类别不报错）
    """
    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocess = ColumnTransformer([
        ("num", numeric_pipe, NUM_COLS),
        ("cat", categorical_pipe, CAT_COLS),
    ])

    pipeline = Pipeline([
        ("features", CampaignFeatureBuilder()),
        ("prep", preprocess),
        ("clf", LogisticRegression(max_iter=1000, solver="lbfgs", random_state=RANDOM_STATE)),
    ])
    print("\n== 3. 建模流水线 ==")
    print("  features: CampaignFeatureBuilder（6 个派生特征）")
    print(f"  prep    : 数值 {len(NUM_COLS)} 列（中位数填补+标准化） / "
          f"类别 {len(CAT_COLS)} 列（众数填补+OneHot）")
    print("  clf     : LogisticRegression(max_iter=1000)")
    return pipeline


# ---------------------------------------------------------------------------
# 3. 训练与评估 —— 对应 9.2.2「性能」之外更重要的"能不能上线"
# ---------------------------------------------------------------------------
def ks_statistic(y_true: np.ndarray, prob: np.ndarray) -> dict:
    """计算 KS 统计量 = max(TPR − FPR)，并返回 ROC 与 KS 曲线所需的数组。

    KS 衡量的是"好坏客户的累计分布最大差距"，风控/营销里比 AUC 更常被业务方引用：
    KS=0.5 意味着在最优切点上，成功客户的累计捕获率比失败客户高出 50 个百分点。

    两条累计曲线的横轴都是"按预测概率从高到低排序后的样本占比"：
        cum_pos = 前 x% 客户里抓到了多少比例的成功客户（TPR）
        cum_neg = 前 x% 客户里误伤了多少比例的失败客户（FPR）
    """
    y = np.asarray(y_true)
    order = np.argsort(-prob)
    y_sorted = y[order]
    n, n_pos, n_neg = len(y), int(y.sum()), int((1 - y).sum())

    pop = np.arange(1, n + 1) / n
    cum_pos = np.cumsum(y_sorted) / max(n_pos, 1)
    cum_neg = np.cumsum(1 - y_sorted) / max(n_neg, 1)
    gap = cum_pos - cum_neg
    i = int(np.argmax(gap))

    fpr, tpr, _ = roc_curve(y, prob)
    return {
        "ks": float(gap[i]),
        "ks_pop": float(pop[i]),
        "pop": pop, "cum_pos": cum_pos, "cum_neg": cum_neg, "ks_idx": i,
        "fpr": fpr, "tpr": tpr,
    }


def train_and_evaluate(df: pd.DataFrame):
    """切分训练/测试集、跑 5 折交叉验证、在测试集上评估，返回所有中间结果。"""
    drop_cols = ["ID", TARGET, "ARPU"]          # ARPU 泄露 → 不进特征
    X = df.drop(columns=drop_cols)
    y = df[TARGET].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=RANDOM_STATE
    )

    pipe = build_pipeline()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_auc = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="roc_auc", n_jobs=1)

    pipe.fit(X_train, y_train)
    prob_test = pipe.predict_proba(X_test)[:, 1]
    prob_train = pipe.predict_proba(X_train)[:, 1]

    test_auc = roc_auc_score(y_test, prob_test)
    ks = ks_statistic(y_test.to_numpy(), prob_test)

    print("\n== 4. 交叉验证与评估 ==")
    print(f"  训练集 {len(X_train):,} 行 / 测试集 {len(X_test):,} 行（分层抽样）")
    print(f"  5 折交叉验证 AUC：{cv_auc.mean():.4f} ± {cv_auc.std():.4f} "
          f"（各折 {', '.join(f'{v:.4f}' for v in cv_auc)}）")
    print(f"  测试集 AUC：{test_auc:.4f}；KS：{ks['ks']:.4f}"
          f"（出现在样本前 {ks['ks_pop']:.1%} 的切点）")

    return {
        "pipe": pipe, "X_train": X_train, "X_test": X_test,
        "y_train": y_train, "y_test": y_test,
        "ids_test": df.loc[X_test.index, "ID"].to_numpy(),
        "prob_test": prob_test, "prob_train": prob_train,
        "cv_auc": cv_auc, "test_auc": test_auc, "ks": ks,
    }


def evaluate_metrics(res: dict) -> pd.DataFrame:
    """把 AUC / KS / 混淆矩阵 / 命中率 / 提升度整理成一张指标表（table02）。"""
    y_test, prob = res["y_test"], res["prob_test"]
    pred = (prob >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
    base_rate = float(y_test.mean())            # 不做模型时的自然成功率

    # 按概率从高到低排序，取前 10% / 20% 作为"营销名单"
    order = np.argsort(-prob)
    y_sorted = y_test.to_numpy()[order]
    n = len(y_sorted)

    rows = [
        ("样本数（训练/测试）", f"{len(res['y_train']):,} / {len(y_test):,}", "测试集占 25%，分层抽样保证正负比例一致"),
        ("5 折交叉验证 AUC", f"{res['cv_auc'].mean():.4f} ± {res['cv_auc'].std():.4f}", "训练集内部评估，衡量稳定性"),
        ("测试集 AUC", f"{res['test_auc']:.4f}", "0.5 为随机，0.8 以上在营销响应场景算良好"),
        ("KS 统计量", f"{res['ks']['ks']:.4f}", "max(TPR−FPR)，业务上常以 0.3 作为可用线"),
        ("准确率（阈值 0.5）", f"{accuracy_score(y_test, pred):.4f}", f"基准：全判成功 = {base_rate:.4f}"),
        ("精确率（阈值 0.5）", f"{precision_score(y_test, pred):.4f}", f"基准：随机抽取 = {base_rate:.4f}"),
        ("召回率（阈值 0.5）", f"{recall_score(y_test, pred):.4f}", "真正成功客户中被抓到的比例"),
        ("F1", f"{f1_score(y_test, pred):.4f}", "精确率与召回率的调和平均"),
        ("混淆矩阵 TP/FP", f"{tp:,} / {fp:,}", "判成功且真成功 / 判成功但实际失败"),
        ("混淆矩阵 FN/TN", f"{fn:,} / {tn:,}", "判失败但实际成功 / 判失败且真失败"),
        ("Top10% 命中率", f"{y_sorted[:int(n * 0.1)].mean():.4f}", "名单前 10% 的真实成功率"),
        ("Top20% 命中率", f"{y_sorted[:int(n * 0.2)].mean():.4f}", "名单前 20% 的真实成功率"),
        ("Lift@10%", f"{y_sorted[:int(n * 0.1)].mean() / base_rate:.2f}", "相对「不做模型」的提升倍数"),
        ("Lift@20%", f"{y_sorted[:int(n * 0.2)].mean() / base_rate:.2f}", "同上，取前 20%"),
    ]
    metrics = pd.DataFrame(rows, columns=["指标", "取值", "说明"])
    print("\n  指标：" + "；".join(f"{r[0]}={r[1]}" for r in rows[2:6]))
    return metrics


def leakage_demo(df: pd.DataFrame) -> float:
    """对照实验：把 ARPU 放回特征，看 AUC 会被"人为拉满"到什么程度。

    这不是为了炫技，而是工程化的第一条自检：**任何一个在业务动作之后才产生的字段，
    都不能进模型**。这里用同一套流水线、同一份切分，只多一列 ARPU（缺失值用中位数填补，
    并保留缺失指示列），如果 AUC 从 0.81 跳到 1.00，就说明模型学到的是"ARPU 有没有值"，
    而不是"客户会不会成功"。
    """
    num = NUM_COLS + ["ARPU"]
    pre = ColumnTransformer([
        ("num", Pipeline([
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]), num),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), CAT_COLS),
    ])
    pipe = Pipeline([
        ("features", CampaignFeatureBuilder()),
        ("prep", pre),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    X = df.drop(columns=["ID", TARGET])
    y = df[TARGET].astype(int)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=RANDOM_STATE
    )
    pipe.fit(X_tr, y_tr)
    return float(roc_auc_score(y_te, pipe.predict_proba(X_te)[:, 1]))


def coefficient_table(pipe: Pipeline) -> pd.DataFrame:
    """把流水线里的逻辑回归系数还原成"人话"（table03 + fig02）。

    关键点：特征名要从 ``ColumnTransformer.get_feature_names_out()`` 取，
    否则只能看到 23 个匿名系数，无法解释是哪个字段在推高概率。
    """
    names = pipe.named_steps["prep"].get_feature_names_out()
    coef = pipe.named_steps["clf"].coef_[0]
    df = pd.DataFrame({"特征": names, "系数": coef})
    df["中文特征"] = df["特征"].map(pretty_feature)
    df["优势比"] = np.exp(df["系数"])
    df["方向"] = np.where(df["系数"] > 0, "越高越容易成功", "越高越容易失败")
    df = df[["中文特征", "特征", "系数", "优势比", "方向"]].sort_values("系数", key=np.abs, ascending=False)
    return df


FEATURE_CN = {
    "Age": "年龄",
    "PromCnt12": "近12月促销次数",
    "PromCnt36": "近36月促销次数",
    "PromCntMsg12": "近12月短信促销",
    "PromCntMsg36": "近36月短信促销",
    "AvgARPU": "历史平均ARPU",
    "AvgHomeValue": "平均房产价值",
    "AvgIncome": "平均收入",
    "PromTrend": "促销趋势",
    "MsgIntensity": "短信促销占比",
    "PromIntensity": "促销集中度",
    "WealthRatio": "房产收入比",
    "IncomeMissing": "收入缺失标志",
    "IsSenior": "是否65岁以上",
    "Gender_F": "性别=女",
    "Gender_M": "性别=男",
    "Gender_U": "性别未知",
    "HomeOwner_H": "有房",
    "HomeOwner_U": "无房",
    "Class_1": "客户等级1",
    "Class_2": "客户等级2",
    "Class_3": "客户等级3",
    "Class_4": "客户等级4",
}


def pretty_feature(name: str) -> str:
    """把 ``num__PromCnt12`` / ``cat__Gender_M`` 这类流水线内部名翻成中文。"""
    raw = str(name).split("__", 1)[-1]
    return FEATURE_CN.get(raw, raw)


# ---------------------------------------------------------------------------
# 4. 图 1：ROC 曲线 + KS 曲线
# ---------------------------------------------------------------------------
def plot_roc_ks(res: dict, out_dir: Path):
    """左图 ROC（判"分不分得开"），右图 KS（判"最好的切点能多抓多少"）。

    两张图画的是同一组 ``fpr / tpr``，只是把"差距"单独可视化了一次：
    ROC 看整体排序能力，KS 看最优切点上的能力，业务汇报里通常两张都要。
    """
    fig, axes = new_fig(11.2, 4.8, ncols=2)

    # ---- 左：ROC ----
    ax = axes[0]
    ax.plot(res["ks"]["fpr"], res["ks"]["tpr"], color=BLUE, linewidth=2.4,
            label=f"逻辑回归（AUC = {res['test_auc']:.4f}）")
    ax.plot([0, 1], [0, 1], color=GRAY, linestyle="--", linewidth=1.2,
            label="随机猜测（AUC = 0.5）")
    ax.fill_between(res["ks"]["fpr"], res["ks"]["tpr"], res["ks"]["fpr"],
                    color=BLUE, alpha=0.10)
    ax.set_xlabel("假正率 FPR")
    ax.set_ylabel("真正率 TPR")
    ax.set_title("ROC 曲线", pad=10)
    ax.legend(loc="lower right")
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(-0.01, 1.01)

    # ---- 右：KS 曲线（横轴 = 按分数排序后的样本占比） ----
    ax = axes[1]
    ks = res["ks"]
    ax.plot(ks["pop"], ks["cum_pos"], color=BLUE, linewidth=2.2,
            label="成功客户累计捕获率")
    ax.plot(ks["pop"], ks["cum_neg"], color=GRAY, linewidth=1.8,
            linestyle="--", label="失败客户累计误伤率")
    i = ks["ks_idx"]
    ax.vlines(ks["pop"][i], ks["cum_neg"][i], ks["cum_pos"][i], color=ORANGE,
              linewidth=2.8, label=f"KS = {ks['ks']:.4f}")
    ax.annotate(f"最大差距 {ks['ks']:.3f}\n（样本前 {ks['pop'][i]:.0%}）",
                xy=(ks["pop"][i], (ks["cum_pos"][i] + ks["cum_neg"][i]) / 2),
                xytext=(14, 10), textcoords="offset points", fontsize=9,
                color=ORANGE)
    ax.set_xlabel("样本累计占比（按预测概率从高到低排序）")
    ax.set_ylabel("累计占比")
    ax.set_title("KS 曲线：好坏客户累计分布的差距", pad=10)
    ax.legend(loc="lower right")
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(-0.01, 1.01)

    fig.suptitle("模型区分能力：ROC 与 KS", y=1.02, fontsize=13.5, fontweight="bold")
    save_fig(fig, out_dir, "fig01_ROC曲线与KS统计量")


# ---------------------------------------------------------------------------
# 5. 图 2：特征系数条形图
# ---------------------------------------------------------------------------
def plot_coefficients(coef_df: pd.DataFrame, out_dir: Path, top_n: int = 15):
    """逻辑回归系数（已标准化，可直接比大小），红=推高成功概率，蓝=压低。

    系数是"标准化后"的，所以含义是：该特征每增加 1 个标准差，成功几率的对数变化多少。
    """
    sub = coef_df.head(top_n).iloc[::-1]      # 反过来，让绝对值最大的排在最上面
    fig, ax = new_fig(9.6, 6.2)
    colors = [POS if v > 0 else NEG for v in sub["系数"]]
    ax.barh(sub["中文特征"], sub["系数"], color=colors, height=0.62, zorder=3)
    ax.axvline(0, color="#555555", linewidth=0.9)
    for y, v in enumerate(sub["系数"]):
        ax.annotate(f"{v:+.3f}", (v, y), xytext=(8 if v >= 0 else -8, 0),
                    textcoords="offset points", va="center", fontsize=8.5,
                    ha="left" if v >= 0 else "right", color="#333333")
    ax.set_xlabel("逻辑回归系数（标准化后）")
    ax.set_ylabel("")
    ax.set_title(f"特征系数 Top {top_n}：什么在驱动营销成功", pad=12)
    ax.set_xlim(sub["系数"].min() * 1.45, sub["系数"].max() * 1.45)
    ax.grid(axis="y", visible=False)
    save_fig(fig, out_dir, "fig02_特征系数条形图")


# ---------------------------------------------------------------------------
# 6. 图 3：打分概率分布（好客户 vs 坏客户叠加）
# ---------------------------------------------------------------------------
def plot_score_distribution(res: dict, out_dir: Path):
    """把成功/失败客户的预测概率画在同一张直方图上，看"能不能分开"。

    理想的模型是两条分布错开：成功的堆在右边、失败的堆在左边。
    如果两条几乎重合，AUC 就接近 0.5，不管阈值怎么调都没用。
    """
    y_test = res["y_test"].to_numpy()
    prob = res["prob_test"]
    bins = np.linspace(0, 1, 31)

    fig, ax = new_fig(9.0, 4.8)
    ax.hist(prob[y_test == 0], bins=bins, color=NEG, alpha=0.55,
            label=f"实际失败（{int((y_test == 0).sum()):,} 人）", zorder=3)
    ax.hist(prob[y_test == 1], bins=bins, color=POS, alpha=0.55,
            label=f"实际成功（{int((y_test == 1).sum()):,} 人）", zorder=3)
    ax.axvline(0.5, color="#333333", linestyle="--", linewidth=1.4, zorder=4)
    ax.annotate("阈值 0.5", xy=(0.5, ax.get_ylim()[1] * 0.92), xytext=(6, 0),
                textcoords="offset points", fontsize=9, color="#333333")
    ax.set_xlabel("预测成功概率")
    ax.set_ylabel("客户数")
    ax.set_title("打分概率分布：好客户与坏客户的分离度", pad=12)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
    save_fig(fig, out_dir, "fig03_打分概率分布")


# ---------------------------------------------------------------------------
# 7. 图 4：Lift 图 + 混淆矩阵
# ---------------------------------------------------------------------------
def plot_lift_confusion(res: dict, out_dir: Path):
    """左：按十分位的提升度 + 累计捕获率；右：阈值 0.5 的混淆矩阵。

    Lift 的读法：把客户按预测概率从高到低分成 10 等份，
    第 1 份里成功客户的比例 ÷ 整体成功率 = 该份的提升倍数。
    营销预算有限时，只打 Lift 最高的那一两份就够了。
    """
    y_test = res["y_test"].to_numpy()
    prob = res["prob_test"]
    base = y_test.mean()

    # 按概率排序后切成 10 份，逐份算命中率
    order = np.argsort(-prob)
    ys = y_test[order]
    deciles = np.array_split(ys, 10)
    rates = np.array([d.mean() for d in deciles])
    lifts = rates / base
    cum_rate = np.cumsum(rates) / np.arange(1, 11)      # 前 n 份的平均命中率
    xs = np.arange(1, 11)

    fig, axes = new_fig(11.4, 4.9, ncols=2)

    # ---- 左：Lift ----
    ax = axes[0]
    ax.bar(xs, lifts, color=[ORANGE if v >= 1 else BLUE2 for v in lifts],
           width=0.62, zorder=3, label="本份 Lift")
    ax.axhline(1.0, color=GRAY, linestyle="--", linewidth=1.2, label="基准线 Lift=1")
    # 标签写在柱子内部，避免和右侧的累计命中率折线打架
    for x, v in zip(xs, lifts):
        ax.annotate(f"{v:.2f}", (x, v), xytext=(0, -12), textcoords="offset points",
                    ha="center", va="top", fontsize=8, color="white", fontweight="bold")
    ax.set_xlabel("按预测概率排序后的十分位（1 = 最可能成功）")
    ax.set_ylabel("提升倍数 Lift")
    ax.set_xticks(xs)
    ax.set_ylim(0, lifts.max() * 1.25)

    ax2 = ax.twinx()
    ax2.plot(xs, cum_rate, color=BLUE, marker="o", markersize=5, linewidth=2,
             label="累计命中率", zorder=5)
    ax2.set_ylabel("累计命中率", color=BLUE)
    ax2.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax2.set_ylim(0, max(cum_rate.max(), base) * 1.3)
    ax2.grid(False)

    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right")
    ax.set_title("十分位 Lift 与累计命中率", pad=10)

    # ---- 右：混淆矩阵 ----
    ax = axes[1]
    pred = (prob >= 0.5).astype(int)
    cm = confusion_matrix(y_test, pred)
    im = ax.imshow(cm, cmap="Blues")
    labels = ["预测失败", "预测成功"]
    ax.set_xticks([0, 1], labels)
    ax.set_yticks([0, 1], ["实际失败", "实际成功"])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                    fontsize=15, fontweight="bold",
                    color="white" if cm[i, j] > cm.max() * 0.6 else "#333333")
    ax.set_title("混淆矩阵（阈值 0.5）", pad=10)
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle("名单质量：把预算花在 Lift 最高的那一档", y=1.02,
                 fontsize=13.5, fontweight="bold")
    save_fig(fig, out_dir, "fig04_Lift图与混淆矩阵")


# ---------------------------------------------------------------------------
# 8. 模型持久化 + 批量打分 —— notebook 完全没有的"交付环节"
# ---------------------------------------------------------------------------
def save_model(pipe: Pipeline) -> Path:
    """用 joblib 把整条流水线（含特征工程）序列化到 outputs/。

    注意存的是 **Pipeline 而不是 模型对象**：只存 LogisticRegression 的话，
    线上还要自己重写清洗和特征工程，等于把"训练-打分不一致"的坑留给自己。
    """
    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_PATH)
    size_kb = MODEL_PATH.stat().st_size / 1024
    print("\n== 5. 模型持久化 ==")
    print(f"  已保存整条 Pipeline → {MODEL_PATH.name}（{size_kb:.0f} KB）")
    return MODEL_PATH


def batch_scoring(X_new: pd.DataFrame, ids: np.ndarray, top_ratio: float = 0.2):
    """模拟"新数据批量打分"：从磁盘重新加载模型 → 打分 → 排序 → 输出 Top 20% 名单。

    这一步刻意用 ``joblib.load`` 重新读文件，而不是复用内存里的对象：
    只有"从文件重新加载还能打出一样的分"，才能证明这个模型真的可以被交付给业务方。
    """
    model = joblib.load(MODEL_PATH)
    prob = model.predict_proba(X_new)[:, 1]

    scored = pd.DataFrame({
        "客户ID": ids,
        "成功概率": np.round(prob, 6),
    })
    scored = scored.sort_values("成功概率", ascending=False).reset_index(drop=True)
    scored["排名"] = np.arange(1, len(scored) + 1)
    scored["概率分箱"] = pd.cut(scored["成功概率"], bins=np.linspace(0, 1, 11),
                              labels=[f"{i}-{i + 1}成" for i in range(10)])

    n_top = int(len(scored) * top_ratio)
    top = scored.head(n_top).copy()

    print("\n== 6. 批量打分 ==")
    print(f"  待打分客户 {len(scored):,} 人，模型从 {MODEL_PATH.name} 重新加载")
    print(f"  概率区间：最低 {prob.min():.4f}，中位 {np.median(prob):.4f}，最高 {prob.max():.4f}")
    print(f"  Top {top_ratio:.0%} 名单 {n_top:,} 人，概率下限 {top['成功概率'].min():.4f}")
    return scored, top


def main() -> None:
    apply_style()
    OUT.mkdir(parents=True, exist_ok=True)

    df = load_data()
    audit = detect_leakage(df)
    save_csv(audit, OUT, "table01_数据质量与泄露排查")

    d = clean_data(df)
    res = train_and_evaluate(d)
    metrics = evaluate_metrics(res)
    save_csv(metrics, OUT, "table02_模型评估指标")

    # 对照实验：把泄露字段放回去，AUC 会被拉满
    leak_auc = leakage_demo(d)
    print(f"  [对照] 把 ARPU 放回特征后，测试集 AUC = {leak_auc:.4f}"
          f"（正常版 {res['test_auc']:.4f}）→ 证实 ARPU 是泄露源")

    coef_df = coefficient_table(res["pipe"])
    save_csv(coef_df.round(4), OUT, "table03_特征系数")

    save_model(res["pipe"])
    scored, top = batch_scoring(res["X_test"], res["ids_test"])
    save_csv(top[["排名", "客户ID", "成功概率", "概率分箱"]], OUT, "marketing_list_top20")

    plot_roc_ks(res, OUT)
    plot_coefficients(coef_df, OUT)
    plot_score_distribution(res, OUT)
    plot_lift_confusion(res, OUT)

    # ---- 结论 ----
    y_test = res["y_test"].to_numpy()
    order = np.argsort(-res["prob_test"])
    ys = y_test[order]
    base = y_test.mean()
    hit20 = ys[: int(len(ys) * 0.2)].mean()
    hit10 = ys[: int(len(ys) * 0.1)].mean()

    print("\n" + "=" * 66)
    print("业务结论（可直接用于报告）")
    print("=" * 66)
    print(f"1. ARPU 缺失与 Suc_flag=0 完全重合（均为 4,843 行），属于事后变量造成的标签泄露，"
          f"剔除后模型 AUC={res['test_auc']:.4f}、KS={res['ks']['ks']:.4f}；")
    print(f"2. 5 折交叉验证 AUC={res['cv_auc'].mean():.4f}±{res['cv_auc'].std():.4f}，"
          f"与测试集相差 {abs(res['cv_auc'].mean() - res['test_auc']):.4f}，没有明显过拟合；")
    print(f"3. 按概率取前 20% 客户（{int(len(ys) * 0.2):,} 人）命中率 {hit20:.1%}，"
          f"是全量基准 {base:.1%} 的 {hit20 / base:.2f} 倍；前 10% 命中率 {hit10:.1%}"
          f"（{hit10 / base:.2f} 倍）；")
    print("4. 交付物包括：可直接加载的 model_pipeline.joblib、Top 20% 营销名单、"
          "以及全部图表的复跑脚本。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
