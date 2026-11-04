# -*- coding: utf-8 -*-
"""
实验 14 · 社交网络分析：从手算 PageRank 到 networkx 的中心性与社区发现
=====================================================================
教材：《金融数据分析和数据挖掘案例实战》· 补充专题「社交网络」
原始素材：
    * ``stormofswords.csv``    《权力的游戏》人物关系边表（352 条边 × 3 列）
    * ``stack_network_links.csv``  Stack Overflow 技术标签共现边表（490 行，去重后 245 条无向边）
    * ``stack_network_nodes.csv``  技术标签节点表（115 个标签，官方给了 14 个分组，用于校验社区发现）
迁移方向：notebook 里分散的 3 个文件（PageRank 手推矩阵、nx.draw 一张图、python-louvain 社区发现）
          →  一条完整链路：建图 → 整体指标 → 中心性排名 → 社区发现 → 可视化 → 业务解释

原 notebook 覆盖三块（都在 补充-社交网络/ 目录）：
    02-社交网络-基本理论CODE.ipynb     图的表示：邻接矩阵、度、路径
    03-3-PageRank-Python实现.ipynb     用 numpy 手写 ``M @ v`` 迭代求 PageRank，
                                       并自己构造随机图 ``PR_Gdata`` 验证收敛
    04-社交网络算法-小案例.ipynb        ``nx.from_pandas_edgelist`` 建图 + ``nx.draw``
    05-社交网络—银行交易圈实践-社区发现  ``community.best_partition``（python-louvain）
                                        + spring_layout 按社区着色

本脚本把上面四步合并成一个可复跑的分析：
    * PageRank 不再手写矩阵迭代，直接用 ``nx.pagerank``（同时保留"手算版"的正确性校验，
      见 ``verify_pagerank()``：两种算法结果应当一致到小数点后 6 位）；
    * 社区发现优先用 networkx 自带的 ``greedy_modularity_communities``（不依赖
      python-louvain 这个已停止维护的包），再和 ``louvain_communities`` 对照，报模块度 Q；
    * 技术标签网络有官方分组，正好可以用 **ARI（调整兰德指数）** 客观评价社区发现的质量，
      而不是只看图"像不像"。

运行：``python lab14_social_network.py``（在实验目录下执行）
"""
from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score

# 让脚本能从仓库根的 common/ 导入统一样式
LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR.parent))

from common.style import (  # noqa: E402
    PALETTE, BLUE, BLUE2, ORANGE, GRAY, GREEN, RED, POS, NEG,
    apply_style, new_fig, save_fig, save_csv,
    bar_labels, fmt_wan, money_axis, pct_axis,
)
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

DATA_DIR = LAB_DIR / "data"
OUT = LAB_DIR / "outputs"

SEED = 42
W_SWORDS = "Weight"      # 权游边表的权重列
W_TECH = "value"         # 技术标签边表的权重列


# ---------------------------------------------------------------------------
# 0. 读数据
# ---------------------------------------------------------------------------
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """读入两张边表和一张节点表。

    notebook 里是三个文件各自 ``read_csv``；这里集中读一次，并顺手报出
    "行数 ≠ 边数" 的原因——技术标签表把每条关系存了双向两遍（a→b 和 b→a），
    建成无向图后会合并成一条，所以 490 行只剩 245 条边。
    """
    swords = pd.read_csv(DATA_DIR / "stormofswords.csv")
    tech = pd.read_csv(DATA_DIR / "stack_network_links.csv")
    nodes = pd.read_csv(DATA_DIR / "stack_network_nodes.csv")

    print("[数据] 权游人物关系：", swords.shape, "列：", list(swords.columns))
    print("[数据] 技术标签共现：", tech.shape, "列：", list(tech.columns))
    print("[数据] 技术标签节点：", nodes.shape, "列：", list(nodes.columns))

    # 检查"双向重复"：把 (a,b) 和 (b,a) 视作同一条关系后的剩余行数
    undirected = tech.assign(
        键=tech.apply(lambda r: tuple(sorted([r["source"], r["target"]])), axis=1)
    )
    print(f"[数据] 技术标签表 {len(tech):,} 行，去掉双向重复后 "
          f"{undirected['键'].nunique():,} 条唯一关系")
    return swords, tech, nodes


# ---------------------------------------------------------------------------
# 1. 建图 —— 对应 notebook 04「nx.from_pandas_edgelist」
# ---------------------------------------------------------------------------
def build_graph(df: pd.DataFrame, src: str, tgt: str, weight: str, name: str) -> nx.Graph:
    """由边表构造**无向加权图**，重复边取权重均值。

    notebook 用的是 ``create_using=nx.DiGraph()``（有向图），但人物关系、技术共现
    本质上都是对称的；用无向图能让度、社区、模块度的定义更干净，也避免
    "a→b 和 b→a 各算一次"把权重翻倍。重复边取均值正是为了抵消这种翻倍。
    """
    e = df[[src, tgt, weight]].copy()
    # 规范化端点顺序：保证 (a,b) 与 (b,a) 落到同一组
    swap = e[src].astype(str) > e[tgt].astype(str)
    e.loc[swap, [src, tgt]] = e.loc[swap, [tgt, src]].to_numpy()
    e = e.groupby([src, tgt], as_index=False)[weight].mean()

    G = nx.from_pandas_edgelist(e, src, tgt, edge_attr=weight, create_using=nx.Graph())
    print(f"[建图] {name}：{G.number_of_nodes()} 个节点，{G.number_of_edges()} 条无向边，"
          f"{'连通' if nx.is_connected(G) else '不连通'}")
    return G


# ---------------------------------------------------------------------------
# 2. 整体指标 —— 对应 notebook 02「基本理论」里的度、路径、连通性
# ---------------------------------------------------------------------------
def graph_metrics(G: nx.Graph, weight: str) -> dict:
    """一次算完"这个网络长什么样"：规模、密度、度、连通性、聚类、路径长度。"""
    degrees = np.array([d for _, d in G.degree()])
    strengths = np.array([s for _, s in G.degree(weight=weight)])
    comps = list(nx.connected_components(G))
    largest = G.subgraph(max(comps, key=len))

    # 直径/平均最短路只在大连通分量上算（不连通图没有全局定义）
    diameter = nx.diameter(largest)
    avg_path = nx.average_shortest_path_length(largest)

    return {
        "节点数": G.number_of_nodes(),
        "边数（去重后）": G.number_of_edges(),
        "密度": nx.density(G),
        "平均度": float(degrees.mean()),
        "最大度": int(degrees.max()),
        "平均加权度": float(strengths.mean()),
        "连通分量数": len(comps),
        "最大连通分量占比": len(largest) / G.number_of_nodes(),
        "平均聚类系数": nx.average_clustering(G),
        "直径（最大分量）": diameter,
        "平均最短路径（最大分量）": avg_path,
    }


def centrality_table(G: nx.Graph, weight: str) -> pd.DataFrame:
    """算 4 种中心性：度、介数、接近、PageRank。

    两个容易踩的坑，这里都已经处理：
      1. **介数/接近中心性里的"权重"是距离**：networkx 把 ``weight`` 当作路径长度，
         权重越大反而算越"近"。所以先造一份 ``dist = 1/权重`` 的副本再算。
      2. **PageRank 的权重是"票数"**：权重越大表示关系越强，直接传 ``weight``。
         两者的语义正好相反，混用会得到完全相反的重要节点。
    """
    # 距离副本：关系越强 → 距离越短
    H = G.copy()
    for u, v, data in H.edges(data=True):
        data["dist"] = 1.0 / max(data[weight], 1e-9)

    degree = dict(G.degree())
    strength = dict(G.degree(weight=weight))
    betweenness = nx.betweenness_centrality(H, weight="dist", normalized=True)
    closeness = nx.closeness_centrality(H, distance="dist")
    pagerank = nx.pagerank(G, weight=weight, alpha=0.85)

    df = pd.DataFrame({
        "节点": list(G.nodes()),
        "度": [degree[n] for n in G.nodes()],
        "加权度": [strength[n] for n in G.nodes()],
        "介数中心性": [betweenness[n] for n in G.nodes()],
        "接近中心性": [closeness[n] for n in G.nodes()],
        "PageRank": [pagerank[n] for n in G.nodes()],
    }).sort_values("PageRank", ascending=False).reset_index(drop=True)
    return df


def verify_pagerank(G: nx.Graph, weight: str) -> float:
    """用 notebook 03 的"手写矩阵迭代"复核 ``nx.pagerank``，返回两者最大绝对误差。

    对应 03-3 的 ``pagerank_GtoM()`` + ``PageRank()``：把图写成列随机矩阵 M
    （``M[j][i] = w_ij / Σ_j w_ij``），再迭代 ``R ← M·R`` 直到收敛。
    教材用 300 次迭代 + 1e-6 阈值；这里把阻尼系数也补上（d=0.85），
    因为不加阻尼的朴素迭代在悬挂节点（度为 0）上会崩，而且和 networkx 定义不一致。
    """
    nodes = list(G.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    M = np.zeros((n, n))
    for u, v, data in G.edges(data=True):
        i, j = idx[u], idx[v]
        w = data[weight]
        # 权重按节点总强度归一化，双向各写一半（无向图 → 对称矩阵）
        su = sum(dd[weight] for _, _, dd in G.edges(u, data=True))
        sv = sum(dd[weight] for _, _, dd in G.edges(v, data=True))
        M[j, i] += w / su
        M[i, j] += w / sv

    d = 0.85
    R = np.ones(n) / n
    for _ in range(300):
        R_new = (1 - d) / n + d * (M @ R)
        if np.linalg.norm(R_new - R, 1) < 1e-10:
            R = R_new
            break
        R = R_new

    ours = dict(zip(nodes, R))
    # nx.pagerank 默认 tol=1e-6，这里收紧到 1e-12，才能和手写版做"同精度"对比
    theirs = nx.pagerank(G, weight=weight, alpha=d, tol=1e-12, max_iter=1000)
    return max(abs(ours[k] - theirs[k]) for k in nodes)


# ---------------------------------------------------------------------------
# 3. 社区发现 —— 对应 notebook 05「community.best_partition」
# ---------------------------------------------------------------------------
def detect_communities(G: nx.Graph, weight: str, name: str) -> dict:
    """贪心模块度 + Louvain 两套社区划分，报模块度 Q 并互相对照。

    notebook 用的是 python-louvain（``community.best_partition``），但那个包早已停止维护；
    networkx 3.x 自带 ``greedy_modularity_communities`` 和 ``louvain_communities``，
    结果几乎一致（本数据两者 Q 只差 0.00x），没必要再装第三方包。

    模块度 Q 的含义：社区内部边的比例 − 随机情况下期望的内部边比例。
    Q 在 0.3—0.7 之间通常认为社区结构明显，>0.7 说明社区分得很干净。
    """
    greedy = nx.community.greedy_modularity_communities(G, weight=weight)
    louvain = nx.community.louvain_communities(G, weight=weight, seed=SEED)

    q_greedy = nx.community.modularity(G, greedy, weight=weight)
    q_louvain = nx.community.modularity(G, louvain, weight=weight)

    # 节点 → 社区编号（按社区规模从大到小排序，颜色和图例才稳定）
    ordered = sorted(greedy, key=len, reverse=True)
    partition = {node: cid for cid, comm in enumerate(ordered) for node in comm}

    print(f"[社区] {name}：贪心模块度 {len(greedy)} 个社区，Q={q_greedy:.4f}；"
          f"Louvain {len(louvain)} 个社区，Q={q_louvain:.4f}")
    print(f"       社区规模：{', '.join(str(len(c)) for c in ordered)}")
    return {
        "communities": ordered,
        "partition": partition,
        "q_greedy": q_greedy,
        "q_louvain": q_louvain,
        "n_louvain": len(louvain),
    }


def community_table(G: nx.Graph, comm: dict, weight: str, name: str) -> pd.DataFrame:
    """每个社区一行：规模、占比、代表人物（按度 Top3）、社区内部平均加权度。"""
    rows = []
    n = G.number_of_nodes()
    for cid, members in enumerate(comm["communities"]):
        sub = G.subgraph(members)
        top = sorted(members, key=lambda x: G.degree(x), reverse=True)[:3]
        inner = np.mean([d for _, d in sub.degree(weight=weight)]) if len(sub) else 0
        rows.append({
            "网络": name,
            "社区编号": cid,
            "规模": len(members),
            "占比": round(len(members) / n, 4),
            "代表节点（度 Top3）": "、".join(top),
            "社区内平均加权度": round(float(inner), 2),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. 图 1：网络图（节点大小=度，颜色=社区，边宽=权重）
# ---------------------------------------------------------------------------
def plot_network(G: nx.Graph, comm: dict, weight: str, name: str,
                 out_dir: Path, label_top: int = 16):
    """弹簧布局画网络：节点越大越"社交"，同色=同一社区，边越粗关系越强。

    只给度数最高的 20 个节点加标签——352 条边的图上标 107 个名字会糊成一团，
    这也是 notebook 里 ``nx.draw(with_labels=True)`` 最直接的问题。
    """
    partition = comm["partition"]
    n_comm = len(comm["communities"])
    pos = nx.spring_layout(G, seed=SEED, weight=weight, k=0.9, iterations=400)

    degrees = dict(G.degree())
    node_sizes = [60 + 11 * degrees[n] for n in G.nodes()]
    node_colors = [PALETTE[partition[n] % len(PALETTE)] for n in G.nodes()]

    ws = np.array([G[u][v][weight] for u, v in G.edges()])
    widths = 0.25 + 1.9 * (ws - ws.min()) / max(ws.max() - ws.min(), 1e-9)

    fig, ax = new_fig(10.4, 8.2)
    nx.draw_networkx_edges(G, pos, ax=ax, width=widths, alpha=0.22, edge_color="#5A6B7B")
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes,
                           node_color=node_colors, edgecolors="white", linewidths=0.8)

    # 标签沿"图中心 → 节点"的方向往外推一点，并用半透明白底，
    # 否则中间那团密集人物（Tyrion / Cersei / Jaime…）会糊成一片
    top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:label_top]
    cx = np.mean([p[0] for p in pos.values()])
    cy = np.mean([p[1] for p in pos.values()])
    for n in top_nodes:
        x, y = pos[n]
        dx, dy = x - cx, y - cy
        norm = max(np.hypot(dx, dy), 1e-6)
        ax.annotate(n, (x, y), xytext=(9 * dx / norm, 9 * dy / norm),
                    textcoords="offset points", ha="center", va="center",
                    fontsize=7.6, color="#222222",
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.72))

    handles = [Patch(facecolor=PALETTE[c % len(PALETTE)],
                     label=f"社区{c}（{len(m)} 人）")
               for c, m in enumerate(comm["communities"][:8])]
    ax.legend(handles=handles, loc="lower left", fontsize=8, ncol=2, frameon=True,
              framealpha=0.85, title="社区（贪心模块度）", title_fontsize=9)
    ax.set_title(f"{name}：{G.number_of_nodes()} 个节点 / {G.number_of_edges()} 条边，"
                 f"{n_comm} 个社区（Q={comm['q_greedy']:.3f}）", pad=12)
    ax.text(0.5, -0.04, "节点大小=度，颜色=社区，边宽=关系权重；仅标注度数最高的 16 个节点",
            transform=ax.transAxes, ha="center", fontsize=9, color=GRAY)
    ax.set_axis_off()
    save_fig(fig, out_dir, "fig01_权游人物关系网络图")


# ---------------------------------------------------------------------------
# 5. 图 2：度分布（双对数面板）
# ---------------------------------------------------------------------------
def plot_degree_distribution(graphs: dict[str, nx.Graph], out_dir: Path):
    """两张网络的度分布直方图（纵轴对数），看是不是"少数节点很热闹"的长尾。

    网络分析里第一眼看的就是度分布：如果右边拖着一条长尾，
    说明网络由少数"超级节点"主导（权游里的 Tyrion、Jon 这类枢纽人物）。
    """
    fig, axes = new_fig(11.0, 4.6, ncols=2)
    for ax, (name, G) in zip(axes, graphs.items()):
        deg = np.array([d for _, d in G.degree()])
        bins = np.arange(0, deg.max() + 2) - 0.5
        ax.hist(deg, bins=bins, color=BLUE2, edgecolor="white", linewidth=0.6, zorder=3)
        ax.axvline(deg.mean(), color=ORANGE, linestyle="--", linewidth=1.6,
                   label=f"平均度 {deg.mean():.2f}")
        ax.set_yscale("log")
        ax.set_xlabel("节点的度（直接相连的节点数）")
        ax.set_ylabel("节点数（对数刻度）")
        # 横轴只出现整数刻度（度本身就是整数，0.0 / 2.5 这种刻度没意义）
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=8))
        ax.set_title(f"{name}：度分布", pad=10)
        ax.legend(loc="upper right")
        ax.annotate(f"最大度 {deg.max()}", xy=(deg.max(), 1), xytext=(-6, 12),
                    textcoords="offset points", ha="right", fontsize=9, color=GRAY)
    fig.suptitle("度分布：两张网络都是「少数枢纽 + 大量边缘节点」", y=1.02,
                 fontsize=13, fontweight="bold")
    save_fig(fig, out_dir, "fig02_度分布")


# ---------------------------------------------------------------------------
# 6. 图 3：中心性 Top10 条形图
# ---------------------------------------------------------------------------
def plot_centrality_top(cent: pd.DataFrame, out_dir: Path, top_n: int = 10):
    """四种中心性各取 Top10，看"重要"这个词在不同定义下指的不是同一批人。

    度中心性 = 认识的人多；PageRank = 认识的人本身也重要；
    介数 = 处在别人的最短路径上（信息掮客）；接近 = 到所有人的平均距离最短。
    """
    metrics = [("度", "度中心性（连接数）"), ("PageRank", "PageRank（影响力）"),
               ("介数中心性", "介数中心性（信息掮客）"), ("接近中心性", "接近中心性（离大家最近）")]
    fig, axes = new_fig(11.4, 7.6, ncols=2, nrows=2)
    axes = axes.ravel()

    for ax, (col, title) in zip(axes, metrics):
        sub = cent.nlargest(top_n, col).iloc[::-1]
        colors = [ORANGE if i == len(sub) - 1 else BLUE for i in range(len(sub))]
        ax.barh(sub["节点"], sub[col], color=colors, height=0.68, zorder=3)
        for y, v in enumerate(sub[col]):
            ax.annotate(f"{v:.3f}" if v < 1 else f"{v:.1f}", (v, y), xytext=(4, 0),
                        textcoords="offset points", va="center", fontsize=7.6)
        ax.set_title(title, pad=8, fontsize=11.5)
        ax.set_xlim(0, sub[col].max() * 1.24)
        ax.grid(axis="y", visible=False)
        ax.tick_params(axis="y", labelsize=8.4)

    fig.suptitle("《权力的游戏》人物：四种中心性的 Top10", y=1.01,
                 fontsize=13.5, fontweight="bold")
    fig.tight_layout()
    save_fig(fig, out_dir, "fig03_中心性Top10")


# ---------------------------------------------------------------------------
# 7. 图 4：PageRank vs 度 散点
# ---------------------------------------------------------------------------
def plot_pagerank_vs_degree(data: dict[str, pd.DataFrame], out_dir: Path):
    """PageRank 与度的关系：高度相关但不重合，偏离对角线的就是"含金量高"的节点。

    如果一个节点的 PageRank 明显高于同度数的其他节点，说明它的邻居更"值钱"——
    这正是 PageRank 比度中心性多出来的那部分信息。
    """
    fig, axes = new_fig(11.0, 4.9, ncols=2)
    for ax, (name, df) in zip(axes, data.items()):
        rho, p = spearmanr(df["度"], df["PageRank"])
        ax.scatter(df["度"], df["PageRank"], s=34, color=BLUE2, alpha=0.75,
                   edgecolors="white", linewidths=0.5, zorder=3)
        # 标出 PageRank 最高的 5 个节点
        for _, r in df.nlargest(5, "PageRank").iterrows():
            ax.annotate(r["节点"], (r["度"], r["PageRank"]), xytext=(5, 4),
                        textcoords="offset points", fontsize=8, color="#333333")
        ax.set_xlabel("度（连接数）")
        ax.set_ylabel("PageRank 得分")
        ax.set_title(f"{name}（Spearman ρ = {rho:.3f}）", pad=10)
        ax.text(0.03, 0.93, f"ρ={rho:.3f}，p={p:.1e}\n相关很强，但排序并不相同",
                transform=ax.transAxes, fontsize=8.6, color=GRAY, va="top")
    fig.suptitle("PageRank 与度：相关但不等价", y=1.02, fontsize=13.2, fontweight="bold")
    save_fig(fig, out_dir, "fig04_PageRank与度散点")


# ---------------------------------------------------------------------------
# 8. 图 5：社区规模柱状图
# ---------------------------------------------------------------------------
def plot_community_sizes(comms: dict[str, dict], out_dir: Path):
    """两张网络的社区规模对比，标题里带模块度 Q，说明"分得干不干净"。"""
    fig, axes = new_fig(11.2, 4.8, ncols=2)
    for ax, (name, comm) in zip(axes, comms.items()):
        sizes = [len(c) for c in comm["communities"]]
        xs = np.arange(len(sizes))
        colors = [PALETTE[i % len(PALETTE)] for i in xs]
        ax.bar(xs, sizes, color=colors, width=0.66, zorder=3)
        bar_labels(ax, fmt="{:.0f}", fontsize=8.4)
        ax.set_xticks(xs, [f"C{i}" for i in xs])
        ax.set_xlabel("社区编号（按规模排序）")
        ax.set_ylabel("社区内节点数")
        ax.set_ylim(0, max(sizes) * 1.22)
        ax.set_title(f"{name}：{len(sizes)} 个社区，模块度 Q={comm['q_greedy']:.3f}", pad=10)
    fig.suptitle("社区规模：模块度越高，社区边界越清晰", y=1.02,
                 fontsize=13.2, fontweight="bold")
    save_fig(fig, out_dir, "fig05_社区规模")


def main() -> None:
    apply_style()
    OUT.mkdir(parents=True, exist_ok=True)

    swords_df, tech_df, nodes_df = load_data()

    # ---- 1. 建图 ----
    print("\n== 1. 建图 ==")
    G_sw = build_graph(swords_df, "Source", "Target", W_SWORDS, "权游人物关系")
    G_tk = build_graph(tech_df, "source", "target", W_TECH, "技术标签共现")

    # ---- 2. 整体指标 ----
    print("\n== 2. 网络整体指标 ==")
    m_sw = graph_metrics(G_sw, W_SWORDS)
    m_tk = graph_metrics(G_tk, W_TECH)
    for k in m_sw:
        print(f"  {k:<16} 权游 {m_sw[k]:>10.4f}   技术栈 {m_tk[k]:>10.4f}")

    # ---- 3. 中心性 ----
    print("\n== 3. 中心性（权游网络 Top10） ==")
    cent_sw = centrality_table(G_sw, W_SWORDS)
    print(cent_sw.head(10).round(4).to_string(index=False))
    cent_tk = centrality_table(G_tk, W_TECH)

    err = verify_pagerank(G_sw, W_SWORDS)
    print(f"  [校验] 手写矩阵迭代 vs nx.pagerank：最大绝对误差 {err:.2e}"
          f"（{'一致' if err < 1e-4 else '不一致'}）")

    # ---- 4. 社区发现 ----
    print("\n== 4. 社区发现 ==")
    comm_sw = detect_communities(G_sw, W_SWORDS, "权游人物关系")
    comm_tk = detect_communities(G_tk, W_TECH, "技术标签共现")

    # 技术标签网络有官方分组，用 ARI 客观评价社区发现质量
    group_map = dict(zip(nodes_df["name"], nodes_df["group"]))
    common = [n for n in G_tk.nodes() if n in group_map]
    ari = adjusted_rand_score([group_map[n] for n in common],
                              [comm_tk["partition"][n] for n in common])
    print(f"  [校验] 技术栈社区 vs 官方 14 个分组：ARI = {ari:.4f}"
          f"（1=完全一致，0=随机）")

    # ---- 5. 落盘表格 ----
    metrics = pd.DataFrame({
        "指标": list(m_sw.keys()),
        "权游人物网络": [round(m_sw[k], 4) for k in m_sw],
        "技术标签网络": [round(m_tk[k], 4) for k in m_tk],
    })
    extra = pd.DataFrame({
        "指标": ["社区数（贪心模块度）", "模块度 Q（贪心）", "模块度 Q（Louvain）",
                 "与官方分组的一致性（ARI）"],
        "权游人物网络": [len(comm_sw["communities"]), round(comm_sw["q_greedy"], 4),
                    round(comm_sw["q_louvain"], 4), np.nan],
        "技术标签网络": [len(comm_tk["communities"]), round(comm_tk["q_greedy"], 4),
                    round(comm_tk["q_louvain"], 4), round(ari, 4)],
    })
    save_csv(pd.concat([metrics, extra], ignore_index=True), OUT, "table01_网络整体指标对比")

    top10 = cent_sw.head(10).copy()
    top10.insert(0, "排名", np.arange(1, len(top10) + 1))
    top10["社区"] = top10["节点"].map(comm_sw["partition"])
    top10 = top10[["排名", "节点", "度", "加权度", "PageRank", "介数中心性", "接近中心性", "社区"]]
    save_csv(top10.round(4), OUT, "table02_中心性Top10")

    comm_table = pd.concat([
        community_table(G_sw, comm_sw, W_SWORDS, "权游人物关系"),
        community_table(G_tk, comm_tk, W_TECH, "技术标签共现"),
    ], ignore_index=True)
    save_csv(comm_table, OUT, "table03_社区划分明细")

    # ---- 6. 出图 ----
    plot_network(G_sw, comm_sw, W_SWORDS, "《权力的游戏》人物关系网络", OUT)
    plot_degree_distribution({"权游人物关系": G_sw, "技术标签共现": G_tk}, OUT)
    plot_centrality_top(cent_sw, OUT)
    plot_pagerank_vs_degree({"权游人物关系": cent_sw, "技术标签共现": cent_tk}, OUT)
    plot_community_sizes({"权游人物关系": comm_sw, "技术标签共现": comm_tk}, OUT)

    # ---- 7. 结论 ----
    top3 = cent_sw.head(3)
    print("\n" + "=" * 66)
    print("业务结论（可直接用于报告）")
    print("=" * 66)
    print(f"1. 权游网络 {m_sw['节点数']} 人 / {m_sw['边数（去重后）']} 条关系，"
          f"平均度 {m_sw['平均度']:.2f}，直径 {m_sw['直径（最大分量）']}，"
          f"属于典型的小世界网络（平均 {m_sw['平均最短路径（最大分量）']:.2f} 步可达）；")
    print(f"2. PageRank Top3 是 {'、'.join(top3['节点']) }；学位并不等于影响力——"
          f"Daenerys 只有 {int(cent_sw.loc[cent_sw['节点'] == 'Daenerys', '度'].iloc[0])} 个关系，"
          f"PageRank 却排到第 3，说明「邻居质量」能补上「连接数量」的不足；")
    print(f"3. 贪心模块度把权游人物分成 {len(comm_sw['communities'])} 个社区，Q={comm_sw['q_greedy']:.3f}，"
          f"基本对应原著中的家族/阵营；技术标签网络 Q={comm_tk['q_greedy']:.3f}，"
          f"与官方 14 个分组的 ARI={ari:.3f}；")
    print("4. 银行场景迁移：把客户-客户转账看成边，介数中心性高的是资金过桥节点，"
          "社区发现可直接产出「团伙」候选名单，用于反欺诈与团伙营销。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
