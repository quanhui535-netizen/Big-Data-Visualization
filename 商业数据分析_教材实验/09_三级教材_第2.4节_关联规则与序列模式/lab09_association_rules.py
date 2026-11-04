# -*- coding: utf-8 -*-
"""
实验 09 · 关联规则与序列模式：银行产品交叉销售分析
====================================================
教材：《CDA 三级认证教材：敏捷数据挖掘》第 2.4 节 交叉销售（关联规则与序列模式）
原始素材：``bank_prod_order.csv``（1914 行 × 3 列，GBK 编码）
迁移方向：教材自写 ``myscript/apriori.py`` + Orange3 ``associate`` + ``myscript/prefixspan.py``
          → **mlxtend（apriori / association_rules）+ 纯 Python PrefixSpan + networkx**

教材 2.4.1 用「一个客户买过的产品集合」做 Apriori，得到 support / confidence / lift 三张表；
2.4.2 把粒度换成「一个客户的多次订单」，用 PrefixSpan 挖「先买 A 再买 B」的顺序规律。
本脚本把这两条线重排为「事务化 → 频繁项集 → 关联规则 → 序列模式」四步，
每一步的中间结果都落盘成 CSV，便于和教材 notebook 的单元格输出逐行核对。

运行：``python lab09_association_rules.py``（在实验目录下执行）
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import cm, colors
import networkx as nx
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

# 让脚本能从仓库根的 common/ 导入统一样式
LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR.parent))

from common.style import (  # noqa: E402
    BLUE, BLUE2, GRAY, GREEN, NEG, ORANGE, PALETTE, POS, RED,
    apply_style, new_fig, save_csv, save_fig,
)

DATA = LAB_DIR / "data" / "bank_prod_order.csv"
OUT = LAB_DIR / "outputs"

# 教材 2.4.1 的参数：min_support=0.02（约 14 个客户），lift 阈值 1.0
MIN_SUPPORT = 0.02
MIN_LIFT = 1.0
MIN_CONFIDENCE = 0.10
# 教材 2.4.2 用 threshold=100（绝对客户数）。本数据只有 720 个客户，
# 100 相当于 13.9%，已接近主产品渗透率，故主分析放宽到 80，另做一组敏感性对比。
SEQ_MIN_COUNT = 80
SEQ_THRESHOLDS = (100, 80, 60, 40)


# ---------------------------------------------------------------------------
# 0. 读取数据 —— 对应教材 cell 1：pd.read_csv('bank_prod_order.csv', encoding='gbk')
# ---------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    """读取银行产品订单流水，并做基础体检。

    教材这一步只是 ``read_csv`` + ``head()``。这里多打印几项「事务化之前必须搞清的事」：
    有多少订单、多少客户、多少产品、同一订单是否会出现多个产品——
    因为这些数字直接决定下一步选「订单」还是「客户」做事务粒度。
    """
    df = pd.read_csv(DATA, encoding="gbk")   # 原始文件是 GBK，读成 UTF-8 会乱码
    df.columns = ["order_no", "cust_id", "prod"]   # 中文列名转英文别名，便于书写

    df = df.dropna(subset=["order_no", "cust_id", "prod"])
    df["order_no"] = df["order_no"].astype(int)
    df["cust_id"] = df["cust_id"].astype(int)
    df["prod"] = df["prod"].str.strip()

    print("=" * 70)
    print("实验 09 · 银行产品交叉销售：关联规则与序列模式")
    print("=" * 70)
    print(f"[数据] 订单流水 {df.shape[0]} 行；订单 {df['order_no'].nunique()} 个；"
          f"客户 {df['cust_id'].nunique()} 位；产品 {df['prod'].nunique()} 种")

    # 一个订单里最多出现几个产品？决定「订单粒度」够不够用
    per_order = df.groupby("order_no")["prod"].nunique()
    print(f"[数据] 每张订单的产品数：均值 {per_order.mean():.3f}，"
          f"最多 {per_order.max()} 个；含 2 个产品的订单 {(per_order > 1).sum()} 张")

    # 同一订单是否只属于一个客户（若跨客户，订单粒度的事务就有歧义）
    cross = df.groupby("order_no")["cust_id"].nunique().max()
    print(f"[数据] 同一订单涉及的客户数最大值 = {cross}（=1 说明订单与客户一一归属）")
    return df


# ---------------------------------------------------------------------------
# 1. 事务化 —— 教材 2.4.1 cell 2：
#    baskets = data['PROD'].groupby(data['CSR_ID']).apply(list)
# ---------------------------------------------------------------------------
def build_baskets(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """把「订单流水」压成「一个客户买了哪些产品」，这才是关联规则的事务。

    教材用 ``groupby('CSR_ID').apply(list)`` 一行完成，但这一步其实有三个隐含选择，
    教材没展开讲，而它们会显著改变 support 的分母：

    1. **粒度选客户还是订单**：本数据 1907 张订单里有 1900 张只含 1 个产品，
       若按订单做事务，绝大多数「项集」只有 1 项，Apriori 几乎挖不出规则；
       按客户做事务，平均每个客户 2.63 个产品，才能反映"同一个人的产品组合"。
    2. **去重**：教材的 ``list`` 会保留重复产品（同一客户重复购买），
       本项目用 ``set`` 去重——关联规则衡量的是"是否买过"，不是"买了几次"。
    3. **排序**：固定排序后输出稳定，便于逐个核对。

    返回 ``(baskets, order_baskets)``：前者是客户级事务（主分析用），
    后者是订单级事务（仅用于上面的粒度对比）。
    """
    baskets = df.groupby("cust_id")["prod"].apply(lambda s: sorted(set(s)))
    order_baskets = df.groupby("order_no")["prod"].apply(lambda s: sorted(set(s)))

    print("\n== 1. 事务粒度对比 ==")
    print(f"  订单粒度：{len(order_baskets)} 个事务，平均 {order_baskets.apply(len).mean():.2f} 项/事务，"
          f"多产品事务 {(order_baskets.apply(len) > 1).sum()} 个")
    print(f"  客户粒度：{len(baskets)} 个事务，平均 {baskets.apply(len).mean():.2f} 项/事务，"
          f"多产品事务 {(baskets.apply(len) > 1).sum()} 个")
    print(f"  结论：选「客户」作事务粒度（教材同款），共 {len(baskets)} 条事务、"
          f"{baskets.apply(len).sum()} 个产品持有记录")
    return baskets, order_baskets


# ---------------------------------------------------------------------------
# 2. 单产品渗透率 —— 交叉销售的"底仓"，也是后面解读 lift 的基准
# ---------------------------------------------------------------------------
def product_penetration(df: pd.DataFrame) -> pd.DataFrame:
    """算每个产品被多少客户持有（渗透率），画出「底仓图」。

    support(单个产品) = 持有该产品的客户数 / 客户总数，正是 Apriori 的 1 项集支持度。
    先看这张图有两个用处：
      * 判断 min_support=0.02 是否合理（2% 约等于 14 位客户，属于长尾产品线）；
      * 后面看到 lift 很高的规则时，能马上判断是不是「两个长尾产品偶然撞上」。
    """
    n_cust = df["cust_id"].nunique()
    pen = (
        df.groupby("prod")["cust_id"].nunique()
        .rename("customers").reset_index()
        .sort_values("customers", ascending=False)
    )
    pen["penetration"] = pen["customers"] / n_cust
    pen["rows"] = pen["prod"].map(df["prod"].value_counts())

    print("\n== 2. 单产品渗透率（%d 位客户） ==" % n_cust)
    for _, r in pen.head(5).iterrows():
        print(f"  {r['prod']:<6}：{r['customers']:>4} 位客户，渗透率 {r['penetration']:.1%}")
    print(f"  长尾产品（渗透率 < 2%）{(pen['penetration'] < 0.02).sum()} 个："
          + "、".join(pen.loc[pen["penetration"] < 0.02, "prod"].tolist()))

    fig, ax = new_fig(9.0, 6.4)
    y = np.arange(len(pen))
    colors = [ORANGE if i < 3 else BLUE2 for i in range(len(pen))]
    ax.barh(y, pen["penetration"], color=colors, height=0.68, zorder=3)
    ax.set_yticks(y, pen["prod"])
    ax.invert_yaxis()
    for yi, v, c in zip(y, pen["penetration"], pen["customers"]):
        ax.annotate(f"{v:.1%}（{c} 人）", (v, yi), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8.5,
                    color="#333333")
    ax.set_xlim(0, pen["penetration"].max() * 1.28)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_title("21 个银行产品的客户渗透率（橙色为前 3 大产品）", pad=12)
    ax.set_xlabel("渗透率（持有该产品的客户 / 720 位客户）")
    ax.set_ylabel("")
    ax.grid(axis="y", visible=False)
    save_fig(fig, OUT, "fig01_单产品渗透率")
    return pen


# ---------------------------------------------------------------------------
# 3. 频繁项集 —— 教材 2.4.1 cell 3：arules(baskets, min_support=0.02)
# ---------------------------------------------------------------------------
def mine_itemsets(baskets: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """one-hot 编码 + Apriori，得到所有支持度 ≥ 2% 的频繁项集。

    教材调的是自写 ``myscript/apriori.py``（``arules`` 内含 Apriori + 规则生成），
    这里拆成 mlxtend 的两步：

    * ``TransactionEncoder`` 把「客户 → 产品列表」转成 720 × 21 的 0/1 矩阵，
      等价于教材里 ``data['PROD'].replace(inverse_mapping)`` 之后交给 Orange3 的整数事务；
    * ``apriori(min_support=0.02, max_len=4)`` 逐层生成候选项集，``max_len=4`` 是为了
      避免出现又长又没业务含义的组合（本数据 4 项集也只有 8 个）。

    返回 ``(onehot, itemsets)``，itemsets 带 ``项数`` 列方便后面分长度阅读。
    """
    te = TransactionEncoder()
    onehot = pd.DataFrame(te.fit(baskets).transform(baskets), columns=te.columns_)

    itemsets = apriori(onehot, min_support=MIN_SUPPORT, use_colnames=True, max_len=4)
    itemsets["项数"] = itemsets["itemsets"].apply(len)
    itemsets["组合"] = itemsets["itemsets"].apply(lambda s: " + ".join(sorted(s)))
    itemsets["客户数"] = (itemsets["support"] * len(onehot)).round().astype(int)
    itemsets = itemsets.sort_values(["support", "项数"], ascending=[False, True]).reset_index(drop=True)

    print("\n== 3. 频繁项集（min_support=%.2f，即 ≥ %d 位客户） =="
          % (MIN_SUPPORT, int(np.ceil(MIN_SUPPORT * len(onehot)))))
    print(f"  共 {len(itemsets)} 个频繁项集："
          + "，".join(f"{k} 项 {v} 个" for k, v in itemsets["项数"].value_counts().sort_index().items()))
    print("  支持度最高的 5 个：")
    for _, r in itemsets.head(5).iterrows():
        print(f"    {r['组合']:<18} support={r['support']:.3f}（{r['客户数']} 位客户）")

    # 只画 Top 15，且用颜色区分项集长度，避免 112 根柱子糊成一片
    top = itemsets.head(15).iloc[::-1]
    color_map = {1: GRAY, 2: BLUE2, 3: BLUE, 4: ORANGE}
    fig, ax = new_fig(9.2, 6.0)
    y = np.arange(len(top))
    ax.barh(y, top["support"], color=[color_map.get(k, GRAY) for k in top["项数"]],
            height=0.68, zorder=3)
    ax.set_yticks(y, top["组合"])
    for yi, v, n in zip(y, top["support"], top["客户数"]):
        ax.annotate(f"{v:.1%}（{n} 人）", (v, yi), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8.5)
    ax.set_xlim(0, top["support"].max() * 1.22)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_title("频繁项集支持度 Top 15（灰=单品，蓝=2 项，深蓝=3 项及以上）", pad=12)
    ax.set_xlabel("支持度（同时持有该项集的客户占比）")
    ax.set_ylabel("")
    ax.grid(axis="y", visible=False)
    save_fig(fig, OUT, "fig02_频繁项集支持度")
    save_csv(itemsets[["组合", "项数", "support", "客户数"]], OUT, "table01_频繁项集")
    return onehot, itemsets


# ---------------------------------------------------------------------------
# 4. 关联规则 —— 教材 2.4.1 cell 4/5：confidence>0.1 且 lift>1
# ---------------------------------------------------------------------------
def mine_rules(onehot: pd.DataFrame, itemsets: pd.DataFrame, pen: pd.DataFrame) -> pd.DataFrame:
    """由频繁项集生成规则，并筛出「提升度 > 1 且置信度 > 10%」的强规则。

    三个指标的口径（教材重点解释的部分，这里用一句话各自锚定业务含义）：

    * **support** = P(A∪B)：同时买 A 和 B 的客户占比，衡量"这条规则覆盖多少人"；
    * **confidence** = P(B|A)：买了 A 的人里有多大比例也买了 B，衡量"推荐准不准"；
    * **lift** = P(B|A) / P(B)：相对"闭眼推荐"提升了多少倍，>1 才是正相关，
      但它对长尾产品极敏感（分母 P(B) 很小，lift 就会虚高），必须和 support 一起看。

    教材 ``conf = rules[(rules.confidence > 0.1) & (rules.lift > 1)]``，
    这里保留同样的阈值，并额外按 lift 降序输出，方便对比"虚高"和"可落地"两类规则。
    """
    rules = association_rules(itemsets, metric="lift", min_threshold=MIN_LIFT,
                              num_itemsets=len(onehot))
    rules["antecedent"] = rules["antecedents"].apply(lambda s: " + ".join(sorted(s)))
    rules["consequent"] = rules["consequents"].apply(lambda s: " + ".join(sorted(s)))
    rules["客户数"] = (rules["support"] * len(onehot)).round().astype(int)

    strong = rules[(rules["confidence"] > MIN_CONFIDENCE) & (rules["lift"] > 1)].copy()
    strong = strong.sort_values(["lift", "support"], ascending=False).reset_index(drop=True)

    print("\n== 4. 关联规则 ==")
    print(f"  lift > {MIN_LIFT} 的候选规则 {len(rules)} 条；"
          f"再叠加 confidence > {MIN_CONFIDENCE:.0%} 后剩 {len(strong)} 条强规则")
    print("  提升度最高的 5 条（注意看 support 有多小）：")
    for _, r in strong.head(5).iterrows():
        print(f"    {r['antecedent']} → {r['consequent']}："
              f"support={r['support']:.3f}（{r['客户数']} 人），"
              f"confidence={r['confidence']:.3f}，lift={r['lift']:.2f}")

    # 4.1 散点图：x=support, y=confidence, 点大小/颜色=lift（教材 cell 7 的升级版）
    fig, ax = new_fig(9.4, 5.6)
    sc = ax.scatter(strong["support"], strong["confidence"],
                    s=18 + 26 * strong["lift"], c=strong["lift"],
                    cmap="YlOrRd", alpha=0.85, edgecolors="#7F7F7F", linewidths=0.4, zorder=3)
    cb = fig.colorbar(sc, ax=ax, pad=0.015)
    cb.set_label("提升度 lift", fontsize=9.5)

    # 标出三条"值得看"的规则：lift 最高、support 最高、以及高 support×高 confidence 的
    marks = pd.concat([
        strong.nlargest(1, "lift"),
        strong.nlargest(1, "support"),
        strong[(strong["support"] > 0.15) & (strong["confidence"] > 0.6)].nlargest(1, "confidence"),
    ]).drop_duplicates(subset=["antecedent", "consequent"])
    for _, r in marks.iterrows():
        # 靠右的点把标签放到左侧，避免被坐标轴或色标裁掉
        to_left = r["support"] < 0.08 or r["support"] > strong["support"].max() * 0.55
        ax.annotate(f"{r['antecedent']}→{r['consequent']}\n"
                    f"lift={r['lift']:.1f}, conf={r['confidence']:.0%}",
                    (r["support"], r["confidence"]),
                    xytext=(-16 if to_left else 14, 8 if r["confidence"] < 0.9 else -18),
                    textcoords="offset points", fontsize=8, color="#333333",
                    ha="right" if to_left else "left",
                    arrowprops=dict(arrowstyle="-", color=GRAY, linewidth=0.7))
    ax.axhline(strong["confidence"].median(), color=GRAY, linestyle="--", linewidth=1.0)
    ax.set_xlim(0, strong["support"].max() * 1.15)
    ax.set_ylim(0, min(1.02, strong["confidence"].max() * 1.12))
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_title(f"{len(strong)} 条强规则：支持度 × 置信度，越靠右上越可落地", pad=12)
    ax.set_xlabel("支持度 support（覆盖多少客户）")
    ax.set_ylabel("置信度 confidence（推荐命中率）")
    save_fig(fig, OUT, "fig03_规则散点图")

    # 4.2 网络图：只保留「单品 → 单品」的规则，边宽/颜色 = lift
    draw_rule_network(rules, pen)
    save_csv(strong[["antecedent", "consequent", "support", "confidence", "lift", "客户数"]],
             OUT, "table02_强关联规则")
    return strong


def draw_rule_network(rules: pd.DataFrame, pen: pd.DataFrame,
                      min_lift: float = 1.5, min_conf: float = 0.25) -> None:
    """把「单品 → 单品」的强规则画成有向网络：节点=产品，边=共现关系。

    几点设计取舍，都是为了"图能读得懂"：

    * 只取**单前提、单结论**的规则（由 2 项集生成的规则），多前提规则会让箭头数量爆炸；
    * 门槛设 lift ≥ 1.5 且 confidence ≥ 0.25：网银对几乎所有产品的 lift 都只有 1.1 左右，
      画进来会变成一张"蜘蛛网"，真正的产品组合反而看不见（网银的角色放到正文里讨论）；
    * 每一对产品只保留 confidence 更高的方向，箭头含义是"买 A 的人里 X% 也买 B"；
    * **圆周布局**：这些产品构成一个近乎全连接的簇（黄金1号/外汇保/想分就分/定存…），
      力导向布局会把它们挤成一团、标签互相压住；把节点均匀摆在圆周上、标签放到圆外，
      无论簇多密都不会重叠；
    * 节点大小 = 该产品客户数，边宽与颜色深浅 = lift。
    """
    one2one = rules[
        (rules["antecedents"].apply(len) == 1) & (rules["consequents"].apply(len) == 1)
    ].copy()
    one2one = one2one[(one2one["lift"] >= min_lift) & (one2one["confidence"] >= min_conf)]

    # 一对产品两个方向的规则只留一条：取置信度更高的方向作为箭头方向
    one2one["pair"] = one2one.apply(
        lambda r: tuple(sorted([r["antecedent"], r["consequent"]])), axis=1
    )
    edges = (
        one2one.sort_values("confidence", ascending=False)
        .drop_duplicates(subset="pair", keep="first")
    )

    graph = nx.DiGraph()
    for _, r in edges.iterrows():
        graph.add_edge(r["antecedent"], r["consequent"],
                       lift=r["lift"], confidence=r["confidence"], support=r["support"])

    # 连通分量从大到小排、分量内按度数排，让同一簇的产品在圆周上相邻
    undirected = graph.to_undirected()
    order: list[str] = []
    for comp in sorted(nx.connected_components(undirected), key=len, reverse=True):
        order.extend(sorted(comp, key=lambda n: -undirected.degree(n, weight="lift")))

    angles = np.pi / 2 - np.linspace(0, 2 * np.pi, len(order), endpoint=False)
    pos = {node: (float(np.cos(a)), float(np.sin(a))) for node, a in zip(order, angles)}

    fig, ax = new_fig(9.4, 7.8)
    ax.set_xlim(-1.42, 1.42)
    ax.set_ylim(-1.42, 1.42)
    ax.set_aspect("equal")
    ax.axis("off")

    cust_of = dict(zip(pen["prod"], pen["customers"]))
    node_size = [420 + 4.0 * cust_of.get(n, 10) for n in graph.nodes]

    lifts = [graph[u][v]["lift"] for u, v in graph.edges]
    norm = colors.Normalize(vmin=min(lifts), vmax=max(lifts))
    cmap = plt.get_cmap("OrRd")

    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=node_size,
                           node_color=BLUE2, edgecolors="white", linewidths=1.8)
    nx.draw_networkx_edges(graph, pos, ax=ax,
                           width=[0.9 + 0.42 * v for v in lifts],
                           edge_color=[cmap(norm(v)) for v in lifts], alpha=0.85,
                           arrows=True, arrowsize=12, node_size=node_size,
                           connectionstyle="arc3,rad=0.16")
    for node, (x, y) in pos.items():
        ax.annotate(node, (x, y), xytext=(17 * x, 17 * y), textcoords="offset points",
                    ha="left" if x > 0.05 else ("right" if x < -0.05 else "center"),
                    va="center", fontsize=10.5, color="#333333")

    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, fraction=0.030, pad=0.02)
    cb.set_label("提升度 lift（边宽同向增加）", fontsize=9.5)

    ax.set_title(f"产品关联网络：单品规则 lift≥{min_lift}、confidence≥{min_conf:.0%}"
                 f"（节点=客户数，共 {graph.number_of_nodes()} 个产品 / "
                 f"{graph.number_of_edges()} 条边）", pad=10)
    save_fig(fig, OUT, "fig04_规则网络图")
    print(f"\n  网络图：{graph.number_of_nodes()} 个产品、{graph.number_of_edges()} 条边"
          f"（单品规则 lift≥{min_lift} 且 confidence≥{min_conf:.0%}）")


# ---------------------------------------------------------------------------
# 5. 序列模式 —— 教材 2.4.2：按订单编号排成序列，再用 PrefixSpan 挖"先 A 后 B"
# ---------------------------------------------------------------------------
def build_sequences(df: pd.DataFrame) -> list[list[frozenset]]:
    """构造每个客户的产品序列：一次订单 = 序列里的一个元素（可能有多个产品）。

    教材 2.4.2 的两步就是这个函数：
        baskets = data.groupby(['OrderNumber', 'CSR_ID'])['PROD'].apply(list)   # 订单内聚
        baskets = baskets.groupby(level=1).apply(list)                           # 客户内聚
    这里用 ``groupby(sort=False)`` + ``frozenset`` 实现同样的效果，
    既保留「同一订单多个产品」的共现，又保证元素内的产品不分先后。
    """
    sequences = []
    for _, g in df.sort_values(["cust_id", "order_no"]).groupby("cust_id", sort=False):
        seq = [frozenset(prod) for _, prod in g.groupby("order_no", sort=False)["prod"]]
        if seq:
            sequences.append(seq)
    print(f"\n== 5. 序列构造 ==")
    print(f"  客户序列 {len(sequences)} 条，平均长度 {np.mean([len(s) for s in sequences]):.2f} 个订单，"
          f"最长 {max(len(s) for s in sequences)} 个订单")
    return sequences


def prefix_span(sequences: list[list[frozenset]], min_count: int,
                max_len: int = 4) -> list[tuple[tuple[str, ...], int]]:
    """纯 Python 版 PrefixSpan：按「前缀投影」逐层生长序列模式。

    教材 ``myscript/prefixspan.py`` 用「投影数据库 + 占位符 ``_``」实现，
    额外支持在同一订单内继续加产品（itemset-extension）。本实现做了两点简化，
    目的是让代码短到能读懂，同时结论不受影响：

    1. 只做**序列扩展**（sequence-extension）：前缀之后的下一个元素是新订单，
       不再把一个新元素并进前缀的最后一个订单。本数据 99.6% 的订单只含 1 个产品，
       同订单内的共现已经由上一步的关联规则刻画，这里不重复；
    2. 用「对全库重扫 + 最早匹配」代替维护投影数据库：
       720 条序列 × 几十个候选前缀，代价可以接受，而且少了``_``占位符这类易错细节。

    参数
    ----
    sequences : 每条元素是 frozenset 的序列列表（一个元素 = 一次订单）
    min_count : 绝对支持计数（教材的 ``threshold``）
    max_len   : 模式最大长度，防止长尾组合把结果撑爆

    返回 ``[(('好享贷', '网银'), 304), ...]``，按支持计数降序。
    """
    patterns: list[tuple[tuple[str, ...], int]] = []

    def suffix_start(seq: list[frozenset], prefix: tuple[str, ...]) -> int | None:
        """返回 prefix 在 seq 中「最早匹配完成」之后的下标；匹配不上返回 None。"""
        start = 0
        for item in prefix:
            for idx in range(start, len(seq)):
                if item in seq[idx]:
                    start = idx + 1
                    break
            else:
                return None          # 这个元素里找不到 item，前缀匹配失败
        return start

    def grow(prefix: tuple[str, ...]) -> None:
        # 统计"在 prefix 之后还出现过"的每个产品，覆盖多少条序列
        counts: Counter[str] = Counter()
        for seq in sequences:
            start = suffix_start(seq, prefix)
            if start is None:
                continue
            seen: set[str] = set()
            for element in seq[start:]:
                seen |= element
            for item in seen:
                counts[item] += 1

        for item, cnt in counts.items():
            if cnt < min_count:
                continue          # 支持度不足，整条前缀分支都可以剪掉（Apriori 性质）
            pattern = prefix + (item,)
            patterns.append((pattern, cnt))
            if len(pattern) < max_len:
                grow(pattern)

    grow(())
    return sorted(patterns, key=lambda p: (-p[1], len(p[0]), p[0]))


def mine_sequences(df: pd.DataFrame) -> pd.DataFrame:
    """在客户序列上跑 PrefixSpan，输出高频购买顺序，并和教材阈值做敏感性对比。

    教材 2.4.2 的调用是 ``prefixSpan(SquencePattern([], 1e4), baskets, threshold=100)``，
    threshold 是绝对客户数。这里先按 100/80/60/40 跑一遍看模式数量的变化，
    再取 80 作为主结果——100 只能留下 7 条（且 5 条是单品），信息量太少；
    40 以下开始出现大量 3 阶组合，样本噪声上升。
    """
    sequences = build_sequences(df)
    n_cust = len(sequences)

    for th in SEQ_THRESHOLDS:
        pats = prefix_span(sequences, th)
        multi = sum(1 for p, _ in pats if len(p) > 1)
        print(f"  threshold={th:>3}（{th / n_cust:.1%}）：{len(pats):>2} 条模式，"
              f"其中多阶（≥2 个产品）{multi} 条")

    patterns = prefix_span(sequences, SEQ_MIN_COUNT)
    rows = []
    for pattern, cnt in patterns:
        rows.append({
            "序列模式": " → ".join(pattern),
            "阶数": len(pattern),
            "支持计数": cnt,
            "支持度": cnt / n_cust,
        })
    seq_df = pd.DataFrame(rows)

    print(f"\n  主结果（threshold={SEQ_MIN_COUNT}，≥{SEQ_MIN_COUNT / n_cust:.1%} 客户）："
          f"{len(seq_df)} 条模式")
    for _, r in seq_df.head(8).iterrows():
        print(f"    {r['序列模式']:<24} 支持 {r['支持计数']:>3} 人（{r['支持度']:.1%}）")

    plot = seq_df.head(12).iloc[::-1]
    color_map = {1: GRAY, 2: BLUE2, 3: BLUE, 4: ORANGE}
    fig, ax = new_fig(9.4, 5.8)
    y = np.arange(len(plot))
    ax.barh(y, plot["支持计数"], color=[color_map.get(k, GRAY) for k in plot["阶数"]],
            height=0.66, zorder=3)
    ax.set_yticks(y, plot["序列模式"])
    for yi, v, s in zip(y, plot["支持计数"], plot["支持度"]):
        ax.annotate(f"{v} 人（{s:.0%}）", (v, yi), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8.5)
    ax.set_xlim(0, plot["支持计数"].max() * 1.24)
    ax.set_title(f"高频购买顺序 Top 12（PrefixSpan，支持计数 ≥ {SEQ_MIN_COUNT} 位客户）", pad=12)
    ax.set_xlabel("支持计数（含该顺序的客户数）")
    ax.set_ylabel("")
    ax.grid(axis="y", visible=False)
    save_fig(fig, OUT, "fig05_序列模式支持度")
    save_csv(seq_df, OUT, "table03_序列模式")
    return seq_df


def main() -> None:
    apply_style()
    df = load_data()
    baskets, _ = build_baskets(df)
    pen = product_penetration(df)
    onehot, itemsets = mine_itemsets(baskets)
    strong = mine_rules(onehot, itemsets, pen)
    seq_df = mine_sequences(df)

    # ---- 写进分析报告的业务结论 ----
    top_pen = pen.iloc[0]
    best_lift = strong.iloc[0]
    best_support = strong.nlargest(1, "support").iloc[0]
    trade_rule = strong[
        (strong["antecedent"] == "手机银行") & (strong["consequent"] == "网银")
    ]
    one2one = strong[(strong["antecedents"].apply(len) == 1)
                     & (strong["consequents"].apply(len) == 1)]
    main_seq = seq_df[seq_df["阶数"] > 1].iloc[0] if (seq_df["阶数"] > 1).any() else seq_df.iloc[0]

    huangjin = pen.loc[pen["prod"] == "好享贷", "penetration"].iloc[0]
    third_pen = pen.iloc[2]["penetration"]
    print("\n" + "=" * 70)
    print("业务结论（可直接用于报告）")
    print("=" * 70)
    print(f"1. 网银渗透率 {top_pen['penetration']:.1%}（{top_pen['customers']} 人）、"
          f"好享贷 {huangjin:.1%}，两者构成全行产品的“底仓”，"
          f"其余产品渗透率均不高于 {third_pen:.0%}。")
    print(f"2. lift 最高的规则是「{best_lift['antecedent']} → {best_lift['consequent']}」"
          f"（lift={best_lift['lift']:.1f}），但只有 {best_lift['客户数']} 位客户、"
          f"support={best_lift['support']:.1%}，属于小样本虚高；")
    print(f"   覆盖最广的强规则是「{best_support['antecedent']} → {best_support['consequent']}」"
          f"（{best_support['客户数']} 人，confidence={best_support['confidence']:.1%}，"
          f"lift={best_support['lift']:.2f}），可落地性更强。")
    if len(trade_rule):
        tr = trade_rule.iloc[0]
        print(f"3. 渠道类产品「手机银行 → 网银」：{tr['客户数']} 人，"
              f"confidence={tr['confidence']:.1%}，lift={tr['lift']:.2f}——"
              "手机银行客户几乎必然开通网银，适合做“一次开通、双端激活”。")
    print(f"4. 序列模式「{main_seq['序列模式']}」覆盖 {main_seq['支持计数']} 位客户"
          f"（{main_seq['支持度']:.1%}），说明产品持有存在先后顺序，"
          "可在前一产品开通后 30 天内做后一产品的定向触达。")
    print(f"5. 共 {len(one2one)} 条单品规则、{len(strong)} 条强规则；"
          f"频繁项集 {len(itemsets)} 个，全部落在 4 项以内。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()


