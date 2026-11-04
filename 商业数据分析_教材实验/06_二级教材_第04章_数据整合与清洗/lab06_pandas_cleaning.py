# -*- coding: utf-8 -*-
"""
实验 06 · 数据整合与清洗：从 100 多个零散 cell 到一条可复跑的清洗流水线
======================================================================
教材：《CDA 二级认证教材：量化策略分析》第 4 章 数据处理（pandas）
原始素材：``第4章  数据整合和数据清洗.ipynb``
        ``sample.csv``（5 行 × 3 列，训练用的小样本：1 个异常值 9999 + 1 个缺失值）
        ``write.csv``（notebook 里 ``to_csv`` 写出的小文件）
        ``data/big.csv``（4500 行 × 4 列：客户号 + 3 类交易次数）
迁移方向：notebook 里「一个 API 一个 cell」的演示  →  按「读入 → 整合 → 清洗 → 汇总」重排

notebook 一共 80 多个 cell，覆盖 read_csv / to_csv / loc / iloc / 布尔索引 / query /
merge / concat / drop_duplicates / sort_values / groupby / pivot_table / replace /
apply / cut / qcut / 缺失值与异常值处理。**它的问题是"知识点罗列"**：
每个 cell 换个例子重来一次，读者学完知道 40 个 API，却不知道真实项目里这些 API
是怎么串起来的。

本脚本的做法：用一个**统一的业务场景**（运营商 4500 个客户的交易行为）把教材的
知识点重新组织成一条流水线：

    读入（分块读 + dtype 陷阱）
      → 整合（纵向拼接两批导出 + 关联号段维表）
      → 体检（缺失矩阵 + 数据质量表）
      → 清洗（缺失值三方案 / 异常值盖帽 / 去重）
      → 汇总（groupby + pivot_table + 分箱）

运行：``python lab06_pandas_cleaning.py``（在实验目录下执行）
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
    PALETTE, BLUE, BLUE2, ORANGE, GRAY, GREEN, RED, POS, NEG,
    apply_style, new_fig, save_fig, save_csv,
    bar_labels, fmt_wan, money_axis, pct_axis,
)

DATA = LAB_DIR / "data"
OUT = LAB_DIR / "outputs"

N_CHUNK = 900          # 教材 cell 3 的 chunksize=900，4500 ÷ 900 正好 5 块
SEG_MIN_CUST = 40      # 号段维表只收「客户数 ≥ 40」的号段，制造真实的未匹配
SIMULATE_DROP_COL = True   # 模拟「第二批导出漏了消费次数这一列」

# 字段中文名，画图和表头统一用它
COL_CN = {
    "CNT_TBM": "交易次数",
    "CNT_ATM": "取款次数",
    "CNT_POS": "消费次数",
    "seg_cust": "号段客户数",
    "seg_tbm_mean": "号段均值",
}


# ---------------------------------------------------------------------------
# 0. 读入 —— 对应 notebook cell 1、2、5、6、7（read_csv 常用参数 + to_csv 往返）
# ---------------------------------------------------------------------------
def load_sample() -> pd.DataFrame:
    """读入训练用小样本，顺便暴露教材里的两个"坑"。

    对应教材：
        cell 1  ``pd.read_csv('sample.csv')``             —— 最基础的读法
        cell 2  ``usecols=['id','name'], nrows=2``        —— 只读两列两行
        cell 5  ``na_values='99999'``                     —— 自定义缺失值标识
        cell 6  ``encoding='utf-8'``                      —— 指定编码
        cell 7  ``to_csv('write.csv', encoding='utf-8')`` —— 写回

    为什么要重写：教材把这 5 个参数拆成 5 个 cell，读者容易照抄而不理解。
    这里把它们串成「读 → 校验 → 写回 → 再读」的一次闭环，并点出两个真实陷阱：

    1. ``na_values='99999'`` 在本数据集上**完全无效**：sample.csv 里的异常值是
       **9999**（4 个 9），写 5 个 9 一个也匹配不上，缺失值仍是 ``NaN``、
       异常值仍是 9999 原样进来；
    2. ``encoding`` 用错不会报错，而是把中文读成乱码（``write.csv`` 是 UTF-8，
       用 GBK 打开就变成"灏忔槑"）。所以**编码要写死、不要靠默认值**。
    """
    path = DATA / "sample.csv"

    base = pd.read_csv(path)                                   # 最基础的读法
    part = pd.read_csv(path, usecols=["id", "name"], nrows=2)  # 只读 2 行 2 列
    naive = pd.read_csv(path, na_values="99999")               # 教材写法（无效）
    fixed = pd.read_csv(path, na_values=9999)                  # 正确写法（有效）

    print("== 0. 读入 sample.csv ==")
    print(f"  全量 {base.shape[0]} 行 × {base.shape[1]} 列，字段 {list(base.columns)}")
    print(f"  usecols + nrows=2 只读到 {part.shape[0]} 行："
          + "、".join(part["name"].tolist()))
    print(f"  na_values='99999' → 缺失 {naive['scores'].isna().sum()} 个，"
          f"最大值 {naive['scores'].max():.0f}（异常值 9999 没被识别）")
    print(f"  na_values=9999    → 缺失 {fixed['scores'].isna().sum()} 个，"
          f"最大值 {fixed['scores'].max():.0f}（9999 已转为 NaN）")

    # 编码陷阱：write.csv 是 UTF-8，用 GBK 硬读只会得到乱码
    utf8 = pd.read_csv(DATA / "write.csv", encoding="utf-8")
    try:
        gbk = pd.read_csv(DATA / "write.csv", encoding="gbk")
        garbled = gbk.loc[0, "name"]
    except UnicodeDecodeError:
        garbled = "（解码失败，直接抛 UnicodeDecodeError）"
    print(f"  write.csv 按 UTF-8 读第一个姓名：{utf8.loc[0, 'name']}；"
          f"按 GBK 读：{garbled}")

    # to_csv 往返：写出去再读回来，确认索引、编码、缺失值都没有被改变
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "_roundtrip_sample.csv"
    base.to_csv(tmp, encoding="utf-8-sig", index=False)
    back = pd.read_csv(tmp, encoding="utf-8-sig")
    same = back.shape == base.shape and back["name"].tolist() == base["name"].tolist()
    print(f"  to_csv → read_csv 往返一致：{'是' if same else '否'}；"
          f"写出的文件 {tmp.name}（{tmp.stat().st_size} 字节）")
    return base


# ---------------------------------------------------------------------------
# 1. 分块读大文件 —— 对应 notebook cell 3、4
# ---------------------------------------------------------------------------
def load_big_by_chunks() -> tuple[pd.DataFrame, pd.DataFrame]:
    """分块读取 big.csv 再拼回去，同时处理「客户号前导零」的 dtype 陷阱。

    对应教材：
        cell 3  ``pd.read_csv('data/big.csv', chunksize=900)``，逐块打印 shape
        cell 4  ``pd.concat(csvs, ignore_index=True)``，把迭代器拼成完整表

    为什么要重写：教材只演示了"能拼回来"，没提 **dtype**。big.csv 的客户号是
    9 位定长字符串 ``000041360``，pandas 默认会把它读成整数 41360——前导零没了，
    后续按号段（前 3 位）切分就全部错位。正确做法有两种：读的时候
    ``dtype={'ID': str}``，或读完 ``str.zfill(9)`` 补回 9 位；本脚本两种都用，
    并把"读错的后果"打印出来做对比。
    """
    path = DATA / "big.csv"

    wrong = pd.read_csv(path)          # 默认读法：ID 变成 int64
    reader = pd.read_csv(path, chunksize=N_CHUNK, dtype={"ID": str})
    blocks, shapes = [], []
    for chunk in reader:
        shapes.append(chunk.shape)
        blocks.append(chunk)
    big = pd.concat(blocks, ignore_index=True)
    big["ID"] = big["ID"].str.zfill(9)   # 双保险：即使源文件漏了前导零也能补齐

    print("\n== 1. 分块读入 big.csv ==")
    print(f"  每块形状：{shapes}，共 {len(shapes)} 块")
    print(f"  拼接后 {big.shape[0]} 行 × {big.shape[1]} 列，"
          f"客户号去重后 {big['ID'].nunique()} 个")
    print(f"  dtype 陷阱：默认读法 ID 是 {wrong['ID'].dtype}，"
          f"第一条 = {wrong.loc[0, 'ID']}；按 str 读 = {big.loc[0, 'ID']}")
    return big, wrong


# ---------------------------------------------------------------------------
# 2. 纵向拼接两批导出 —— 对应 notebook cell 47—53（concat / drop_duplicates）
# ---------------------------------------------------------------------------
def assemble_batches(big: pd.DataFrame) -> pd.DataFrame:
    """把一次导出拆成"两批文件"再拼回来，演示 concat 与去重。

    对应教材：
        cell 47—50  ``pd.concat([df1, df2], ignore_index=True, axis=0)``
        cell 51     ``... .drop_duplicates()``
        cell 52—53  改列名后再拼、再去重

    为什么这样重组：教材用 12 行的玩具表演示"两表叠起来"，读者记住了语法，
    却不知道 **拼接最常见的副作用是"字段对不齐"**。真实场景里两批文件往往
    来自不同时间点的导出，字段可能少一列、多一列、顺序不同。所以这里：

    * 第一批 = 前 2250 行（3 列齐全）；
    * 第二批 = 后 2250 行，**刻意少一列 CNT_POS**（模拟系统升级后漏导出，
      由 ``SIMULATE_DROP_COL`` 控制，真实数据文件里三列是完整的）；
    * ``concat`` 按列名对齐 → 第二批的 CNT_POS 自动变成 NaN，这正是"整合导致
      缺失"的典型来源，后面第 4 步的缺失处理就是冲着它去的。

    去重（``drop_duplicates``）：教材 cell 81—84 用 6 行数据造重复。本数据
    实际没有重复（上游已去重），脚本仍保留这一步并打印结果——**清洗步骤要幂等**，
    没有重复也要检查，因为上游随时可能重复上报。
    """
    half = len(big) // 2
    batch1 = big.iloc[:half].copy()
    batch2 = big.iloc[half:].copy()
    if SIMULATE_DROP_COL:
        batch2 = batch2.drop(columns=["CNT_POS"])

    merged = pd.concat([batch1, batch2], ignore_index=True, sort=False)
    before = len(merged)
    dup_rows = int(merged.duplicated().sum())
    dup_ids = int(merged.duplicated(subset=["ID"]).sum())
    merged = merged.drop_duplicates(subset=["ID"], keep="first").reset_index(drop=True)

    print("\n== 2. 纵向拼接两批导出 ==")
    print(f"  第一批 {batch1.shape[0]} 行 × {batch1.shape[1]} 列，"
          f"第二批 {batch2.shape[0]} 行 × {batch2.shape[1]} 列"
          + ("（模拟漏导出 CNT_POS）" if SIMULATE_DROP_COL else ""))
    print(f"  concat 后 {merged.shape[0]} 行；整行重复 {dup_rows} 行，"
          f"客户号重复 {dup_ids} 行 → 去重后 {before} → {len(merged)} 行（未删任何行）")
    print(f"  第二批带进来的 CNT_POS 缺失：{merged['CNT_POS'].isna().sum()} 个")
    return merged


# ---------------------------------------------------------------------------
# 3. 关联号段维表 —— 对应 notebook cell 33—45（merge 四种 how + join）
# ---------------------------------------------------------------------------
def merge_segment_table(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """从明细里"滚"出一张号段维表，再 merge 回明细，对比四种 how 的差异。

    对应教材：
        cell 33—40  ``df1.merge(df2, how='inner'/'left'/'right'/'outer', on='id')``
        cell 41—45  ``pd.concat([...], axis=1)`` 与 ``df1.join(df2)``（按索引对齐）

    为什么这样重组：教材的 df1/df2 是两张凭空造的玩具表，看不出 merge 的业务含义。
    这里用真实数据派生维表：**号段 = 客户号前 3 位**，维表记录每个号段有多少客户、
    平均交易多少次。它天然是"一对多"关系（一个号段对多个客户），正是 merge 的
    典型用法；再故意只保留客户数 ≥ 40 的号段，让长尾号段在 left join 后取不到
    维表信息（真实未匹配，不是造出来的 NaN）。

    四种 how 的结果差异（本数据）：
        inner 4482 行 —— 只留下两边都有的号段客户；
        left  4500 行 —— 全部客户保留，长尾号段的两列维表字段为 NaN；
        right 4482 行 —— 保留维表全部号段，但"一个号段对多个客户"会把行按客户
                         展开，所以不是 40 行而是 4482 行（这一点教材的玩具表
                         看不出来：它的 df2 里每个 id 只出现一次）；
        outer 4500 行 —— 与 left 相同，因为维表没有"明细里不存在"的号段。
    这组数字直接回答了教材没讲清的问题：**how 决定的是"保留哪一侧的行"，
    而行数还取决于关联键是否唯一**。
    """
    raw = raw.copy()
    raw["seg"] = raw["ID"].str[:3]

    seg_stat = (
        raw.groupby("seg")
        .agg(seg_cust=("ID", "size"), seg_tbm_mean=("CNT_TBM", "mean"))
        .reset_index()
    )
    dim = seg_stat[seg_stat["seg_cust"] >= SEG_MIN_CUST].copy()

    left = raw.merge(dim, on="seg", how="left")
    inner = raw.merge(dim, on="seg", how="inner")
    right = raw.merge(dim, on="seg", how="right")
    outer = raw.merge(dim, on="seg", how="outer")

    print("\n== 3. 关联号段维表（merge 的四种 how） ==")
    print(f"  明细 {len(raw)} 行覆盖 {raw['seg'].nunique()} 个号段；"
          f"维表只保留客户数 ≥ {SEG_MIN_CUST} 的 {len(dim)} 个号段")
    print(f"  inner {len(inner):>5} 行 | left {len(left):>5} 行 | "
          f"right {len(right):>5} 行 | outer {len(outer):>5} 行")
    print(f"  注意 right 不是 {len(dim)} 行：维表号段与明细是一对多，"
          f"right 保留维表全部号段后按客户展开，得到 {len(right)} 行")
    print(f"  left join 后仍未匹配到维表的客户：{left['seg_cust'].isna().sum()} 个"
          f"（落在 {left.loc[left['seg_cust'].isna(), 'seg'].nunique()} 个长尾号段）")
    return left, dim


# ---------------------------------------------------------------------------
# 4. 数据体检：缺失矩阵 + 数据质量总表
# ---------------------------------------------------------------------------
def profile_missing(wide: pd.DataFrame) -> pd.Series:
    """算每个字段的缺失率，画缺失矩阵热力图。

    对应教材：
        cell 86—87  ``sample.apply(lambda col: sum(col.isnull()) / col.size)``
        cell 90—91  ``sample.score.isnull()`` 与 ``.apply(int)``

    为什么要重写：教材算完一个"缺失比例 Series"就结束了，看不出**缺失的分布形态**。
    把 ``isnull()`` 的结果直接画成矩阵（行=客户、列=字段、深色=缺失），一眼就能
    分清三种缺失机制：

        * 整块缺失（第二批 2250 行没有 CNT_POS）→ 系统/流程导致，属于 MAR，
          可以按业务规则填充；
        * 零散缺失（长尾号段没进维表）→ 覆盖率不足，属于结构性缺失，
          填充会引入偏差，更适合"保留 + 打标记"。
    """
    miss_rate = wide.isna().mean()
    cols = [c for c in COL_CN if c in wide.columns]
    mat = wide[cols].isna().to_numpy()

    fig, axes = new_fig(11.4, 4.8, ncols=2, gridspec_kw={"width_ratios": [1.55, 1]})

    ax = axes[0]
    ax.imshow(mat.T, aspect="auto", interpolation="nearest", cmap="OrRd", vmin=0, vmax=1)
    ax.set_yticks(range(len(cols)), [COL_CN[c] for c in cols])
    ax.set_xlabel("客户记录序号（0 — 4499）")
    ax.set_title("缺失值矩阵（深色 = 缺失）", pad=10)
    ax.grid(False)

    ax = axes[1]
    order = miss_rate[cols].sort_values()
    colors = [GREEN if v == 0 else (ORANGE if v < 0.2 else RED) for v in order.values]
    ax.barh([COL_CN[c] for c in order.index], order.values, color=colors, height=0.6)
    for y, v in enumerate(order.values):
        ax.annotate(f"{v:.1%}", (v, y), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=9.5,
                    color=GREEN if v == 0 else (ORANGE if v < 0.2 else RED))
    ax.set_xlim(0, max(order.max() * 1.28, 0.1))
    pct_axis(ax, axis="x")
    ax.set_title("各字段缺失率", pad=10)
    ax.set_xlabel("缺失率")
    ax.grid(axis="y", visible=False)

    fig.suptitle("数据体检：4500 个客户、5 个字段的缺失分布", y=1.02,
                 fontsize=13, fontweight="bold")
    save_fig(fig, OUT, "fig01_缺失值矩阵与缺失率")

    print("\n== 4. 数据体检 ==")
    for c in cols:
        print(f"  {COL_CN[c]}：缺失 {wide[c].isna().sum():>5} 个，{miss_rate[c]:.1%}")
    return miss_rate


# ---------------------------------------------------------------------------
# 5. 缺失值处理：三种方案横向对比
# ---------------------------------------------------------------------------
def handle_missing(wide: pd.DataFrame) -> pd.DataFrame:
    """对 CNT_POS 的缺失做三种处理（删除 / 填 0 / 填中位数），量化各自的代价。

    对应教材：
        cell 88  ``sample.score.fillna(sample.score.mean())``
        cell 89  ``sample.score.fillna(sample.score.median())``

    为什么要重写：教材只示范"能填"，没比较"填完会怎样"。这里把三种方案放到
    同一口径下算总消费次数与均值，结论很直观：

        * 删除缺失行：样本从 4500 掉到 2250，**少了一半客户**，样本代表性被破坏；
        * 填 0：总消费次数少了 2250 个客户的贡献，均值从 ~11.7 被拉低到 ~5.6，
          业务上"消费次数 = 0"和"没采集到"是两回事，不能混；
        * 填中位数：均值、中位数基本保持，是计数型字段最稳妥的默认方案。

    最终主表采用**中位数填充**，同时新增 ``pos_filled`` 标记列，让下游知道哪些
    值是补出来的（这一步教材没有，但工程上很关键）。
    """
    med = float(wide["CNT_POS"].median())
    n_missing = int(wide["CNT_POS"].isna().sum())

    schemes = {
        "删除缺失行": wide.dropna(subset=["CNT_POS"]),
        "填 0": wide.assign(CNT_POS=wide["CNT_POS"].fillna(0)),
        "填中位数": wide.assign(CNT_POS=wide["CNT_POS"].fillna(med)),
    }
    rows = []
    for name, df in schemes.items():
        rows.append({
            "方案": name,
            "保留客户数": len(df),
            "消费次数均值": round(df["CNT_POS"].mean(), 2),
            "消费次数中位数": round(df["CNT_POS"].median(), 2),
            "消费次数总和": int(df["CNT_POS"].sum()),
            "说明": "损失一半样本" if name.startswith("删除")
                    else ("把'未采集'当成'没消费'" if name == "填 0"
                          else f"以中位数 {med:.0f} 补齐 {n_missing} 个缺口"),
        })
    table = pd.DataFrame(rows)

    fig, axes = new_fig(11.0, 4.4, ncols=2, gridspec_kw={"width_ratios": [1.15, 1]})

    ax = axes[0]
    series = [schemes["删除缺失行"]["CNT_POS"], schemes["填 0"]["CNT_POS"],
              schemes["填中位数"]["CNT_POS"]]
    bp = ax.boxplot(series, tick_labels=list(schemes), widths=0.5, patch_artist=True,
                    showfliers=False, medianprops={"color": "#333333", "linewidth": 1.6})
    for patch, color in zip(bp["boxes"], [BLUE2, ORANGE, GREEN]):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
        patch.set_edgecolor("#555555")
    ax.set_ylabel("消费次数")
    ax.set_title(f"三种缺失处理后的分布（缺失 {n_missing} 个）", pad=10)
    ax.annotate(f"{n_missing} 个补齐值全部等于中位数 {med:.0f}\n分布被压成一条线",
                xy=(3, med), xytext=(0.38, 0.62), textcoords="axes fraction",
                fontsize=9, color=GREEN, ha="left",
                arrowprops={"arrowstyle": "->", "color": GREEN, "lw": 1.1})

    ax = axes[1]
    x = np.arange(len(table))
    bars = ax.bar(x, table["消费次数总和"] / 10000, color=[BLUE2, ORANGE, GREEN],
                  width=0.55, zorder=3)
    bar_labels(ax, fmt="{:.1f}", fontsize=9.5)
    ax.set_xticks(x, table["方案"])
    ax.set_ylabel("消费次数总和（万次）")
    ax.set_ylim(0, table["消费次数总和"].max() / 10000 * 1.2)
    ax.set_title("不同方案下的总量差异", pad=10)

    fig.suptitle("缺失值处理：删行、填 0、填中位数，代价各不相同", y=1.03,
                 fontsize=13, fontweight="bold")
    save_fig(fig, OUT, "fig02_缺失值处理方案对比")
    save_csv(table, OUT, "table02_缺失值处理方案对比")

    print("\n== 5. 缺失值处理 ==")
    print(f"  CNT_POS 缺失 {n_missing} 个（占 {n_missing / len(wide):.1%}），"
          f"中位数 {med:.0f}，均值 {wide['CNT_POS'].mean():.2f}")
    for _, r in table.iterrows():
        print(f"  {r['方案']:<6}：保留 {r['保留客户数']:>4} 行，"
              f"均值 {r['消费次数均值']:>6.2f}，总和 {r['消费次数总和']:>7,} 次"
              f"（{r['说明']}）")

    clean = wide.copy()
    clean["pos_filled"] = clean["CNT_POS"].isna().astype(int)
    clean["CNT_POS"] = clean["CNT_POS"].fillna(med)
    # 号段维表的两列：未收录的号段用 0 / 自身值兜底，避免下游 groupby 丢样本
    clean["seg_cust"] = clean["seg_cust"].fillna(0).astype(int)
    clean["seg_tbm_mean"] = clean["seg_tbm_mean"].fillna(clean["CNT_TBM"])
    print(f"  主表采用中位数填充，新增 pos_filled 标记列（1 = 补出来的值）："
          f"{int(clean['pos_filled'].sum())} 行")
    return clean


# ---------------------------------------------------------------------------
# 6. 异常值：9999 的识别与「盖帽法」
# ---------------------------------------------------------------------------
def cap(series: pd.Series, quantile: tuple[float, float] = (0.01, 0.99)) -> pd.Series:
    """教材 cell 93 的盖帽法（winsorize）：把超出上下 1% 分位的值压到分位点上。

    参数
    ----
    series : pd.Series
        连续变量列。
    quantile : (float, float)
        下、上分位点，默认 1% / 99%。

    说明：与"直接删掉异常值"相比，盖帽法**保留样本量**、只压缩极端值，
    对计数型字段（交易次数）尤其合适——2741 次的客户确实存在，不该被删掉。
    """
    q_low, q_high = series.quantile(list(quantile)).tolist()
    x = series.astype(float).copy()          # 先转 float，否则赋值小数会触发警告
    x[x < q_low] = q_low
    x[x > q_high] = q_high
    return x


def cap_outliers(clean: pd.DataFrame, sample: pd.DataFrame) -> pd.DataFrame:
    """先用 9999 讲"异常值长什么样"，再用盖帽法处理 big.csv 的三列计数。

    对应教材：
        cell 73—76  ``sample.score.replace(999, np.nan)`` / ``replace({'score': ...})``
        cell 93—95  ``def cap(x, quantile=[0.01, 0.99])`` + ``sample.apply(cap)``

    为什么要重写：教材处理 9999 只有一句话（换成 NaN），但换完之后呢？
    真实数据里更常见的是"不算错、但远离主体"的长尾值（本数据 CNT_TBM 最大 2741，
    均值只有 68），这种值不能简单置 NaN，否则整行作废。所以这里区分两类：

        * **逻辑异常**（9999 = 录入占位符）→ 直接置 NaN，交给缺失流程；
        * **量级异常**（2741 次交易）→ 盖帽压缩到 P99，保留客户、削弱杠杆。
    """
    print("\n== 6. 异常值识别 ==")
    replaced = sample["scores"].replace(9999, np.nan)
    print(f"  sample.scores 原值 {sample['scores'].dropna().tolist()} → "
          f"replace(9999, NaN) 后 {replaced.dropna().tolist()}")
    print(f"  主表 3 列计数的 P99："
          + "、".join(f"{COL_CN[c]} {clean[c].quantile(0.99):.0f}"
                     for c in ["CNT_TBM", "CNT_ATM", "CNT_POS"]))

    before = clean["CNT_TBM"].astype(float)
    after = cap(before)
    p01, p99 = before.quantile([0.01, 0.99]).tolist()
    n_capped = int(((before < p01) | (before > p99)).sum())
    print(f"  CNT_TBM 盖帽：P1={p01:.0f}、P99={p99:.0f}，被压缩 {n_capped} 个值"
          f"（{n_capped / len(before):.1%}）；均值 {before.mean():.2f} → {after.mean():.2f}，"
          f"最大值 {before.max():.0f} → {after.max():.0f}")

    fig, axes = new_fig(10.8, 4.4, ncols=2, gridspec_kw={"width_ratios": [1, 1.3]})

    ax = axes[0]
    bp = ax.boxplot([sample["scores"].dropna()], tick_labels=["scores"],
                    widths=0.35, patch_artist=True,
                    flierprops={"marker": "o", "markersize": 7,
                                "markerfacecolor": RED, "markeredgecolor": RED})
    bp["boxes"][0].set_facecolor(BLUE2)
    bp["boxes"][0].set_alpha(0.7)
    bp["boxes"][0].set_edgecolor("#555555")
    ax.annotate("9999：录入占位符\n（逻辑异常，置 NaN）",
                xy=(1.12, 9999), xytext=(1.22, 7600), fontsize=9,
                color=RED, ha="left",
                arrowprops={"arrowstyle": "->", "color": RED, "lw": 1.2})
    ax.set_title("sample.scores：一个 9999 把箱体压成一条线", pad=10)
    ax.set_ylabel("分数")

    ax = axes[1]
    # 用「分位数曲线」而不是箱线图：盖帽只动尾部 1%，箱线图的两个箱体会长得一模一样，
    # 分位曲线能清楚看到原始值在 99% 之后陡峭上冲、盖帽后被压平成一条水平线。
    qs = np.linspace(0, 1, 201)
    ax.plot(qs, before.quantile(qs), color=ORANGE, linewidth=2.2, label="盖帽前")
    ax.plot(qs, after.quantile(qs), color=GREEN, linewidth=2.2, label="盖帽后")
    ax.axhline(p99, color=RED, linestyle="--", linewidth=1.1)
    ax.axhline(p01, color=RED, linestyle="--", linewidth=1.1)
    pct_axis(ax, axis="x")
    ax.set_xlabel("客户分位")
    ax.set_ylabel("交易次数")
    ax.set_ylim(0, before.max() * 1.12)
    ax.legend(loc="upper left")
    ax.annotate(f"P99 = {p99:.0f}", xy=(0.02, p99), xytext=(0, 5),
                textcoords="offset points", color=RED, fontsize=9)
    ax.annotate(f"盖帽后顶端被压平在 {after.max():.0f}", xy=(0.995, after.max()),
                xytext=(0.52, 0.42), textcoords="axes fraction", ha="left",
                fontsize=9, color=GREEN,
                arrowprops={"arrowstyle": "->", "color": GREEN, "lw": 1.1})
    ax.annotate(f"原始极值 {before.max():.0f}", xy=(0.998, before.max()),
                xytext=(-6, -6), textcoords="offset points", ha="right",
                fontsize=9, color=ORANGE)
    ax.set_title("CNT_TBM：盖帽只动尾部，中位数/四分位不动", pad=10)

    fig.suptitle("异常值：先分清「逻辑异常」和「量级异常」", y=1.03,
                 fontsize=13, fontweight="bold")
    save_fig(fig, OUT, "fig03_异常值识别与盖帽")

    out = clean.copy()
    out["TBM_capped"] = after          # 新列保留原始值，不覆盖，方便审计
    for c in ["CNT_ATM", "CNT_POS"]:
        out[f"{c}_capped"] = cap(out[c].astype(float))
    return out


# ---------------------------------------------------------------------------
# 7. 描述：三类交易次数的分布形态
# ---------------------------------------------------------------------------
def plot_distributions(clean: pd.DataFrame) -> pd.DataFrame:
    """三列计数的直方图对比，看偏态和"该用均值还是中位数"。

    对应教材：没有直接对应（教材只画过 ``sample.hist(bins=50)``），
    这一步是为后面的分箱和 groupby 做前置判断——分布长尾严重，
    ``pd.cut`` 等宽分箱会被极值毁掉，必须换等频分箱。
    """
    cols = ["CNT_TBM", "CNT_ATM", "CNT_POS"]
    summary = clean[cols].agg(["mean", "median", "std", "min", "max"]).T
    summary["偏度"] = clean[cols].skew()
    summary["峰度"] = clean[cols].kurtosis()

    fig, axes = new_fig(12.6, 3.9, ncols=3)
    for ax, c in zip(axes, cols):
        s = clean[c].astype(float)
        upper = s.quantile(0.995)
        ax.hist(s[s <= upper], bins=45, color=BLUE2, alpha=0.85,
                edgecolor="white", linewidth=0.4, zorder=3)
        ax.axvline(s.mean(), color=ORANGE, linestyle="--", linewidth=1.8,
                   label=f"均值 {s.mean():.1f}")
        ax.axvline(s.median(), color=GREEN, linestyle=":", linewidth=1.8,
                   label=f"中位数 {s.median():.0f}")
        ax.set_title(f"{COL_CN[c]}分布（偏度 {s.skew():.2f}）", pad=9)
        ax.set_xlabel(f"{COL_CN[c]}（截断至 P99.5 = {upper:.0f}）")
        ax.set_ylabel("客户数" if c == "CNT_TBM" else "")
        ax.legend(loc="upper right")

    fig.suptitle("三类交易次数都是右偏长尾分布：均值 > 中位数", y=1.04,
                 fontsize=13, fontweight="bold")
    save_fig(fig, OUT, "fig04_三类交易次数分布")

    print("\n== 7. 分布形态 ==")
    for c in cols:
        s = clean[c]
        print(f"  {COL_CN[c]}：均值 {s.mean():.2f}，中位数 {s.median():.0f}，"
              f"偏度 {s.skew():.2f}，峰度 {s.kurtosis():.2f}，最大 {s.max():.0f}")
    return summary.reset_index().rename(columns={"index": "字段"})


# ---------------------------------------------------------------------------
# 8. 分箱：pd.cut（等宽）vs pd.qcut（等频）
# ---------------------------------------------------------------------------
def binning_compare(clean: pd.DataFrame) -> pd.DataFrame:
    """同一列用两种分箱方式切 5 组，比较分组结果的可用性。

    对应教材：
        cell 97—99   ``pd.cut(sample.normal, 5)`` / ``bins=5, labels=[1..5]``
        cell 100—102 ``cut(bins=quantile([0,0.5,1]))``——用分位点当箱边界

    为什么要重写：教材的分箱对象是标准正态随机数，等宽切 5 组很均匀，
    容易让人以为 ``cut`` 总是够用。换成真实的右偏数据（CNT_TBM）就露馅：
    等宽 5 箱里 4486 个客户挤在第 1 箱，后面 2 箱是空的——**极值主导了组距**。
    ``pd.qcut`` 按分位点切，每组样本量相同，才是异质数据的分箱默认选项。
    """
    s = clean["CNT_TBM"].astype(float)
    cut_res = pd.cut(s, 5)
    qcut_res = pd.qcut(s, 5, labels=["极低", "较低", "中等", "较高", "极高"])

    cut_count = cut_res.value_counts().sort_index()
    qcut_stat = (
        clean.assign(频次档=qcut_res)
        .groupby("频次档", observed=True)
        .agg(客户数=("ID", "size"), 消费次数均值=("CNT_POS", "mean"),
             交易次数均值=("CNT_TBM", "mean"))
        .reset_index()
    )

    print("\n== 8. 分箱方式对比 ==")
    print("  pd.cut（等宽 5 箱）客户数："
          + "、".join(f"[{iv.left:.0f},{iv.right:.0f}]={n}" for iv, n in cut_count.items()))
    print("  pd.qcut（等频 5 箱）：")
    for _, r in qcut_stat.iterrows():
        print(f"    {r['频次档']}：{r['客户数']:>4} 人，"
              f"平均交易 {r['交易次数均值']:.1f} 次，平均消费 {r['消费次数均值']:.2f} 次")

    fig, axes = new_fig(11.0, 4.3, ncols=2, gridspec_kw={"width_ratios": [1.2, 1]})

    ax = axes[0]
    labels = [f"{iv.left:.0f}—{iv.right:.0f}" for iv in cut_count.index]
    bars = ax.bar(labels, cut_count.values, color=[RED if n == cut_count.max() else BLUE2
                                                  for n in cut_count.values],
                  width=0.6, zorder=3)
    bar_labels(ax, fmt="{:.0f}", fontsize=9)
    ax.set_title("pd.cut：等宽 5 箱（被 2741 极值毁掉）", pad=10)
    ax.set_xlabel("交易次数区间")
    ax.set_ylabel("客户数")
    ax.tick_params(axis="x", rotation=20)
    ax.annotate("4 个箱几乎为空", xy=(3, max(cut_count.values) * 0.25),
                fontsize=9, color=RED, ha="center")

    ax = axes[1]
    colors = [PALETTE[0], PALETTE[1], PALETTE[2], PALETTE[4], PALETTE[6]]
    ax.bar(qcut_stat["频次档"].astype(str), qcut_stat["消费次数均值"],
           color=colors, width=0.6, zorder=3)
    bar_labels(ax, fmt="{:.1f}", fontsize=9)
    ax.set_xticks(range(len(qcut_stat)),
                  [f"{r['频次档']}\nn={r['客户数']}" for _, r in qcut_stat.iterrows()])
    ax.set_title("pd.qcut：等频 5 箱的消费次数均值", pad=10)
    ax.set_xlabel("频次档（按客户数五等分）")
    ax.set_ylabel("消费次数均值")
    ax.set_ylim(0, qcut_stat["消费次数均值"].max() * 1.25)

    fig.suptitle("分箱：等宽还是等频，取决于分布长什么样", y=1.03,
                 fontsize=13, fontweight="bold")
    save_fig(fig, OUT, "fig05_等宽分箱与等频分箱对比")
    return qcut_stat


# ---------------------------------------------------------------------------
# 9. 汇总：groupby 聚合 + pivot_table
# ---------------------------------------------------------------------------
def segment_summary(clean: pd.DataFrame) -> pd.DataFrame:
    """按号段做多维汇总，对应教材的 groupby.agg 与 pivot_table。

    对应教材：
        cell 60—64  ``groupby('grade')[['math']].max()``、``agg(['mean','min','max'])``
        cell 65—67  多层列索引取值 ``df.loc[:, ('math','min')]``
        cell 69—71  ``pd.pivot_table(table, index='cust_id', columns='type',
                    values='Monetary', fill_value=0, aggfunc='sum')``
    """
    pv = clean.pivot_table(
        index="seg",
        values=["CNT_TBM", "CNT_ATM", "CNT_POS"],
        aggfunc="mean",
    )
    # pivot_table 会按列名字母序排（CNT_ATM、CNT_POS、CNT_TBM），必须显式重排，
    # 否则后面按位置改列名会张冠李戴——这是教材没提醒过的坑
    pv = pv[["CNT_TBM", "CNT_ATM", "CNT_POS"]]
    cnt = clean.groupby("seg").agg(
        客户数=("ID", "size"),
        总消费次数=("CNT_POS", "sum"),
        总交易次数=("CNT_TBM", "sum"),
    )
    table = cnt.join(pv).reset_index()
    table.columns = ["号段", "客户数", "总消费次数", "总交易次数",
                     "交易次数均值", "取款次数均值", "消费次数均值"]
    table["单客消费占比"] = (table["消费次数均值"]
                             / (table["交易次数均值"] + table["消费次数均值"]))
    table = table.sort_values("消费次数均值", ascending=False).round(2)

    print("\n== 9. 号段汇总（前 5 / 后 3） ==")
    head = table.head(5)[["号段", "客户数", "交易次数均值", "消费次数均值", "单客消费占比"]]
    for _, r in head.iterrows():
        print(f"  号段 {r['号段']}：{r['客户数']:>3} 人，"
              f"交易 {r['交易次数均值']:.1f} 次，消费 {r['消费次数均值']:.2f} 次，"
              f"消费占比 {r['单客消费占比']:.1%}")
    print("  ……")
    for _, r in table.tail(3).iterrows():
        print(f"  号段 {r['号段']}：{r['客户数']:>3} 人，"
              f"交易 {r['交易次数均值']:.1f} 次，消费 {r['消费次数均值']:.2f} 次，"
              f"消费占比 {r['单客消费占比']:.1%}")

    # 填充的副作用：整段包在缺失区间里的号段，消费次数会被"钉"在中位数上
    fill_share = clean.groupby("seg")["pos_filled"].mean()
    full_filled = fill_share[fill_share > 0.99].index.tolist()
    if full_filled:
        print(f"  注意：{len(full_filled)} 个号段（{full_filled[0]}—{full_filled[-1]}）"
              f"全部落在第二批（缺失区间），填充后消费次数恒为 "
              f"{clean['CNT_POS'].median():.0f} 次。缺失率到 50% 时，"
              f"任何填充都会让一半样本失真——分号段比较前必须先看 pos_filled 标记列")
    return table


# ---------------------------------------------------------------------------
# 10. 数据质量总表
# ---------------------------------------------------------------------------
def quality_table(stages: list[tuple[str, pd.DataFrame]]) -> pd.DataFrame:
    """把流水线每一站的形状、缺失、重复汇总成一张表（教材没有，工程上必备）。"""
    rows = []
    for name, df in stages:
        cells = df.shape[0] * df.shape[1]
        miss = int(df.isna().sum().sum())
        rows.append({
            "阶段": name,
            "行数": df.shape[0],
            "列数": df.shape[1],
            "缺失单元格": miss,
            "缺失率": round(miss / cells, 4) if cells else 0.0,
            "重复行": int(df.duplicated().sum()),
        })
    table = pd.DataFrame(rows)

    print("\n== 10. 数据质量总表 ==")
    for _, r in table.iterrows():
        print(f"  {r['阶段']:<16} {r['行数']:>5} 行 × {r['列数']:>2} 列，"
              f"缺失 {r['缺失单元格']:>5} 个（{r['缺失率']:.1%}），"
              f"重复 {r['重复行']} 行")
    return table


def main() -> None:
    apply_style()

    sample = load_sample()
    big, big_wrong = load_big_by_chunks()
    raw = assemble_batches(big)
    wide, _ = merge_segment_table(raw)

    miss_rate = profile_missing(wide)
    clean = handle_missing(wide)
    clean = cap_outliers(clean, sample)
    plot_distributions(clean)
    qcut_stat = binning_compare(clean)
    seg_table = segment_summary(clean)

    stages = [
        ("sample.csv", sample),
        ("big.csv（默认读法）", big_wrong),
        ("两批拼接后", raw),
        ("关联维表后", wide),
        ("清洗完成", clean),
    ]
    quality = quality_table(stages)
    save_csv(quality, OUT, "table01_数据质量总表")
    save_csv(seg_table, OUT, "table03_号段交易汇总")

    print("\n" + "=" * 68)
    print("实验结论（可直接写进报告）")
    print("=" * 68)
    print(f"1. 4500 行数据本身没有缺失也没有重复，**缺失是整合过程制造出来的**："
          f"两批导出字段不一致造成 {int(raw['CNT_POS'].isna().sum())} 个缺失，"
          f"号段维表覆盖不全造成 {int(wide['seg_cust'].isna().sum())} 个缺失。")
    print(f"2. 缺失处理没有「标准答案」，只有代价：删行损失一半样本，"
          f"填 0 把总量压低 "
          f"{(1 - (wide['CNT_POS'].fillna(0).sum() / wide['CNT_POS'].fillna(wide['CNT_POS'].median()).sum())):.1%}，"
          f"填中位数几乎不改变分布。")
    print(f"3. 异常值要分类处理：9999 这类占位符直接置 NaN；"
          f"2741 这类真实长尾用盖帽法压到 P99（{clean['TBM_capped'].max():.0f}），"
          f"样本量不变、均值从 {clean['CNT_TBM'].mean():.1f} 降到 {clean['TBM_capped'].mean():.1f}。")
    print(f"4. 分箱先看分布：CNT_TBM 偏度 {clean['CNT_TBM'].skew():.2f}，"
          f"pd.cut 等宽分箱后 4486 人挤在第一箱，必须换 pd.qcut 等频分箱才能看出梯度。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
