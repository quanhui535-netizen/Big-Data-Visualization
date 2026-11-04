# -*- coding: utf-8 -*-
"""
实验 01 · Excel 常用函数与透视表：公式思维 → 向量化 / 分组聚合思维
==================================================================
教材：《CDA 一级认证教材：商业数据分析》第 2 章 数据分析方法 ·
      WPS 电子表格「4、WPS电子表格的公式与函数」
原始素材：
    ``1EXCEL常用函数-讲解使用.xlsx``（4 个工作表：常用函数应用 / IF+AND+OR /
    COUNTIF 统计 / VLOOKUP 精确查找）
    ``2透视表&条件格式&引用&查找练习.xlsx``（数据透视表 / 条件格式 / 单元格引用 / 查找）
    ``sale.csv``（12 行 × 4 列，GBK 编码）
迁移方向：Excel/WPS 的 ``IF/AND/OR``、``COUNTIF/COUNTIFS/SUMIFS``、``VLOOKUP``、
          相对/绝对引用、数据透视表、条件格式  →  ``np.where/np.select``、
          布尔索引、``merge(how="left")``、向量化广播、``pivot_table``、``imshow``

这个实验的重点不是"把公式翻译成代码"，而是理解 **Excel 公式是"逐格计算"，
pandas 是"整列计算"**：
    * Excel 里一个公式写在第 2 行、往下拖 3376 行，是 3376 次求值；
    * pandas 里一个 ``merge`` 就是对整表做一次哈希连接，不存在"拖"。
理解了这一点，就会明白为什么同样的分析换成代码后，换一份数据只需重跑一次。

运行：``python lab01_excel_functions.py``（在实验目录下执行）
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

XLSX_FUNC = LAB_DIR / "data" / "1EXCEL常用函数-讲解使用.xlsx"
XLSX_PIVOT = LAB_DIR / "data" / "2透视表&条件格式&引用&查找练习.xlsx"
CSV_SALE = LAB_DIR / "data" / "sale.csv"
OUT = LAB_DIR / "outputs"

PASS_LINE = 60                       # 教材的及格线；写常量，避免散落的魔法数字


# ---------------------------------------------------------------------------
# 1. IF / AND / OR —— 逐格判断 → 布尔矩阵 + np.where / np.select
# ---------------------------------------------------------------------------
def if_and_or() -> pd.DataFrame:
    """学生成绩：三科「均及格」用 AND，「任一门及格」用 OR。

    Excel 写法（G2 单元格，向下拖）::

        =IF(AND(E2>=60,F2>=60,G2>=60),"通过","未通过")
        =IF(OR(E2>=60,F2>=60,G2>=60),"通过","未通过")

    pandas 写法：整列布尔运算 + ``np.where``；多分支用 ``np.select``。
    教材两列"评价"就是标准答案，脚本会逐行核对，确认迁移没有走样。
    """
    raw = pd.read_excel(XLSX_FUNC, sheet_name="1、IF+AND+OR例子")
    df = raw[raw["姓名"].notna() & raw["数学"].notna()].copy()
    df = df.rename(columns={
        "班级": "cls", "学号": "sid", "姓名": "name", "性别": "sex",
        "数学": "math", "计算机": "comp", "英语": "eng",
        "评价（三门均通过为通过）": "and_ref",
        "评价（三门之一通过为通过）": "or_ref",
    })
    df["sid"] = df["sid"].astype(int)
    for c in ("math", "comp", "eng"):
        df[c] = df[c].astype(float)

    m, c, e = df["math"], df["comp"], df["eng"]
    # AND：三列同时 >= 60；OR：任意一列 >= 60
    df["pass_all"] = np.where((m >= PASS_LINE) & (c >= PASS_LINE) & (e >= PASS_LINE),
                              "通过", "未通过")
    df["pass_any"] = np.where((m >= PASS_LINE) | (c >= PASS_LINE) | (e >= PASS_LINE),
                              "通过", "未通过")
    # 三分支以上就用 np.select（等价于 Excel 的 IFS 嵌套）
    df["avg"] = df[["math", "comp", "eng"]].mean(axis=1).round(1)
    df["level"] = np.select(
        [df["avg"] >= 90, df["avg"] >= 80, df["avg"] >= 70],
        ["优秀", "良好", "中等"], default="待提升",
    )
    df["fail_subjects"] = (df[["math", "comp", "eng"]] < PASS_LINE).sum(axis=1)

    ok_and = (df["pass_all"] == df["and_ref"]).mean()
    ok_or = (df["pass_any"] == df["or_ref"]).mean()
    print("\n== 1. IF + AND / OR：学生成绩判定 ==")
    print(f"  {len(df)} 名学生；均通过 {int((df['pass_all'] == '通过').sum())} 人，"
          f"未通过 {int((df['pass_all'] == '未通过').sum())} 人")
    print(f"  与教材「评价」列一致性：AND {ok_and:.0%}，OR {ok_or:.0%}"
          f"（逐行核对，验证迁移等价）")
    print("  各科不及格人数：" + "，".join(
        f"{n} {int((df[n] < PASS_LINE).sum())} 人" for n in ("math", "comp", "eng")))
    print(f"  注意：OR 口径下全部 {int((df['pass_any'] == '通过').sum())} 人通过 —— "
          f"「之一及格即通过」这个口径没有区分度，不能用来看教学效果")

    # ---- 图 1：成绩色阶热力图（Excel「条件格式 → 色阶」的等价物） ----
    subj_cn = {"math": "数学", "comp": "计算机", "eng": "英语"}
    mat = df[["math", "comp", "eng"]].to_numpy()
    mean_row = mat.mean(axis=0, keepdims=True)
    grid = np.vstack([mat, mean_row])
    rows = list(df["name"]) + ["三科均分"]

    fig, ax = new_fig(9.4, 5.2)
    im = ax.imshow(grid, cmap="RdYlGn", aspect="auto", vmin=50, vmax=100)
    ax.set_xticks(range(3), [subj_cn[c] for c in ("math", "comp", "eng")])
    ax.set_yticks(range(len(rows)), rows)
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            v = grid[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=10,
                    color="#222222" if v >= 60 else "white")
    # 分界线把「学生」与「均分」分开
    ax.axhline(len(df) - 0.5, color="#333333", linewidth=1.6)
    for lab in ax.get_yticklabels():
        if lab.get_text() in ("严冬", "董齐"):
            lab.set_color(RED)          # 未通过的学生名字标红
            lab.set_fontweight("bold")
        if lab.get_text() == "三科均分":
            lab.set_color(BLUE)
            lab.set_fontweight("bold")
    ax.set_title(f"学生三科成绩色阶图（红=低于 {PASS_LINE} 分；"
                 f"90 分以上为深绿）", pad=12)
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("分数", fontsize=9)
    cb.ax.tick_params(labelsize=8)
    ax.text(1.0, -0.115, f"全班 {len(df)} 人：{int((df['pass_all'] == '通过').sum())} 人三科全及格，"
                         f"严冬（数学 {int(df.loc[df['name'] == '严冬', 'math'].iloc[0])}）、"
                         f"董齐（计算机 {int(df.loc[df['name'] == '董齐', 'comp'].iloc[0])}/"
                         f"英语 {int(df.loc[df['name'] == '董齐', 'eng'].iloc[0])}）未通过",
            transform=ax.transAxes, ha="right", fontsize=9, color=GRAY)
    save_fig(fig, OUT, "fig01_学生成绩色阶与IF判定")

    tbl = df[["cls", "sid", "name", "sex", "math", "comp", "eng", "avg",
              "level", "pass_all", "pass_any", "fail_subjects"]].rename(columns={
        "cls": "班级", "sid": "学号", "name": "姓名", "sex": "性别", "math": "数学",
        "comp": "计算机", "eng": "英语", "avg": "三科均分", "level": "综合评级",
        "pass_all": "均通过(AND)", "pass_any": "任一通过(OR)", "fail_subjects": "不及格科目数",
    })
    save_csv(tbl, OUT, "table01_学生成绩与IF判定")
    return df


# ---------------------------------------------------------------------------
# 2. COUNTIF / COUNTIFS —— 整表条件计数 → 按行求和 + 多条件布尔掩码
# ---------------------------------------------------------------------------
def countif_attendance() -> pd.DataFrame:
    """课堂考勤：10 名学生 × 10 天的 a/b/c 记录（a=全勤, b=迟到, c=旷课）。

    Excel 写法::

        =COUNTIF(B2:K2,"b")      ' 迟到次数
        =COUNTIF(B2:K2,"c")      ' 旷课次数
        =COUNTIFS(B2:B11,"b",C2:C11,"b")   ' 第 1、2 天都迟到的人数

    pandas 写法：先把"宽表"熔成"长表"，再按行做条件求和；
    多条件计数就是"两个布尔列相乘再求和"，即 ``COUNTIFS`` 的直译。
    """
    raw = pd.read_excel(XLSX_FUNC, sheet_name="2、COUNTIF-统计", header=None)
    day_cols = list(range(1, 11))
    is_student = raw.iloc[1:, day_cols].isin(["a", "b", "c"]).all(axis=1)
    stu = raw.iloc[1:][is_student].copy()
    stu.columns = ["sid"] + [f"D{i}" for i in range(1, 11)] + ["late_ref", "absent_ref"] + \
        list(raw.columns[13:])

    codes = stu[[f"D{i}" for i in range(1, 11)]]
    out = pd.DataFrame({"学号": stu["sid"].astype(str).str.strip()})
    out["全勤天数"] = (codes == "a").sum(axis=1).values
    out["迟到次数"] = (codes == "b").sum(axis=1).values
    out["旷课次数"] = (codes == "c").sum(axis=1).values
    out["出勤率"] = (out["全勤天数"] / 10).round(3)

    # 与教材列核对（教材用 COUNTIF 算出来的 迟到次数/旷课次数）
    ref_late = pd.to_numeric(stu["late_ref"], errors="coerce")
    ref_abs = pd.to_numeric(stu["absent_ref"], errors="coerce")
    same = int(((out["迟到次数"] == ref_late.values) &
                (out["旷课次数"] == ref_abs.values)).sum())

    # COUNTIFS：两个条件同时满足 —— 布尔掩码相乘再 sum
    both_12 = int(((codes["D1"] == "b") & (codes["D2"] == "b")).sum())
    late3_abs2 = int(((out["迟到次数"] >= 3) & (out["旷课次数"] >= 2)).sum())

    print("\n== 2. COUNTIF / COUNTIFS：课堂考勤 ==")
    print(f"  {len(out)} 名学生 × 10 天；与教材 COUNTIF 列一致 {same}/{len(out)} 人")
    print(f"  迟到合计 {int(out['迟到次数'].sum())} 次，旷课合计 {int(out['旷课次数'].sum())} 次；"
          f"全勤 {int((out['全勤天数'] == 10).sum())} 人")
    print(f"  COUNTIFS 示例：第 1、2 天都迟到 {both_12} 人（与教材第 18 行答案一致）；"
          f"迟到≥3 且旷课≥2 的有 {late3_abs2} 人")

    # ---- 图 2：考勤矩阵（图标集/色阶）+ 迟到旷课排行 ----
    code2num = {"a": 0, "b": 1, "c": 2}
    mat = codes.map(lambda v: code2num[v]).to_numpy(dtype=float)

    fig, axes = new_fig(11.4, 4.8, ncols=2, gridspec_kw={"width_ratios": [1.45, 1]})
    ax = axes[0]
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    cmap = ListedColormap([GREEN, ORANGE, RED])
    ax.imshow(mat, cmap=cmap, aspect="auto", vmin=-0.5, vmax=2.5)
    ax.set_xticks(range(10), [f"第{i}天" for i in range(1, 11)], rotation=45, ha="right",
                  fontsize=8.5)
    ax.set_yticks(range(len(out)), out["学号"].str[-4:], fontsize=8.5)
    ax.set_ylabel("学号后 4 位", fontsize=9)
    ax.set_title("考勤矩阵：a 全勤 / b 迟到 / c 旷课（条件格式「图标集」迁移）", pad=10)
    ax.grid(False)
    ax.legend(handles=[Patch(color=GREEN, label="a 全勤"),
                       Patch(color=ORANGE, label="b 迟到"),
                       Patch(color=RED, label="c 旷课")],
              loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=9)

    ax = axes[1]
    y = np.arange(len(out))
    ax.barh(y - 0.19, out["迟到次数"], height=0.36, color=ORANGE, label="迟到次数", zorder=3)
    ax.barh(y + 0.19, out["旷课次数"], height=0.36, color=RED, label="旷课次数", zorder=3)
    ax.set_yticks(y, out["学号"].str[-4:], fontsize=8.5)
    ax.invert_yaxis()
    for yi, (a, b) in enumerate(zip(out["迟到次数"], out["旷课次数"])):
        if a > 0:
            ax.annotate(f"{a}", (a, yi - 0.19), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=8, color=ORANGE)
        if b > 0:
            ax.annotate(f"{b}", (b, yi + 0.19), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=8, color=RED)
    ax.set_xlabel("次数")
    ax.set_ylabel("学号后 4 位", fontsize=9)
    ax.set_title("每人迟到 / 旷课次数（COUNTIF 结果）", pad=10)
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(out[["迟到次数", "旷课次数"]].to_numpy().max() * 1.35, 1))
    save_fig(fig, OUT, "fig02_考勤矩阵与COUNTIF统计")

    save_csv(out, OUT, "table02_课堂考勤统计")
    return out


# ---------------------------------------------------------------------------
# 3. VLOOKUP 精确匹配 / 近似匹配 —— 逐行查找 → merge / pd.cut
# ---------------------------------------------------------------------------
def vlookup_products() -> pd.DataFrame:
    """商品销售明细回填商品名称：100 张订单 ← 3314 条商品档案。

    Excel 写法（B2 单元格，向下拖 100 行）::

        =VLOOKUP(A2,$G$2:$H$3315,2,FALSE)
        =IFERROR(VLOOKUP(...),"未匹配")     ' 处理 #N/A

    pandas 写法：``orders.merge(lookup, how="left")``，匹配不到的自然是 ``NaN``，
    等价于 Excel 的 #N/A；要显示成文字就 ``.fillna("未匹配")``。
    """
    raw = pd.read_excel(XLSX_FUNC, sheet_name="3、VLOOKUP精确查找")
    orders = raw[["商品编码", "日期", "销售数量", "销售金额"]].dropna(subset=["商品编码"]).copy()
    lookup = raw[["商品编码.1", "商品名称.1"]].dropna(subset=["商品编码.1"]).copy()
    lookup.columns = ["code", "pname"]
    lookup["code"] = lookup["code"].astype(int)
    orders["商品编码"] = orders["商品编码"].astype(int)
    orders["销售数量"] = orders["销售数量"].astype(int)

    m = orders.merge(lookup, how="left", left_on="商品编码", right_on="code")
    m["商品名称"] = m["pname"].fillna("#N/A")     # 对应 IFERROR 的兜底显示

    n_rows, n_miss = len(m), int(m["pname"].isna().sum())
    n_sku, n_sold = lookup["code"].nunique(), m["pname"].nunique()
    print("\n== 3. VLOOKUP 精确匹配：商品名称回填 ==")
    print(f"  订单 {n_rows} 行 × 商品档案 {n_sku:,} 条；匹配成功 {n_rows - n_miss} 行，"
          f"#N/A {n_miss} 行（匹配率 {(n_rows - n_miss) / n_rows:.0%}）")
    print(f"  有销售记录的商品 {n_sold} 个 → 动销率 {n_sold / n_sku:.1%}"
          f"（{n_sku - n_sold:,} 个 SKU 本期零动销）")
    print(f"  订单合计：{int(m['销售数量'].sum())} 件，{m['销售金额'].sum():,.1f} 元")

    top = (m.groupby("商品名称")
             .agg(订单行数=("商品编码", "size"), 件数=("销售数量", "sum"),
                  金额=("销售金额", "sum"))
             .sort_values("金额", ascending=False).reset_index())

    # ---- 图 3：左=精确匹配后的销售榜，右=近似匹配（成绩分档） ----
    fig, axes = new_fig(11.8, 5.0, ncols=2, gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    t10 = top.head(10).iloc[::-1]
    ax.barh(range(len(t10)), t10["金额"], color=BLUE, height=0.62, zorder=3)
    ax.set_yticks(range(len(t10)), t10["商品名称"], fontsize=9)
    for i, v in enumerate(t10["金额"]):
        ax.annotate(f"{v:.1f}", (v, i), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8.5, color="#333333")
    ax.set_xlabel("销售金额（元）")
    ax.set_title("VLOOKUP 精确匹配后的商品销售 Top10", pad=10)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, t10["金额"].max() * 1.28)
    ax.text(0.98, 0.04,
            f"匹配 {n_rows}/{n_rows} 行（#N/A = 0）\n动销 {n_sold}/{n_sku:,} SKU "
            f"= {n_sold / n_sku:.1%}",
            transform=ax.transAxes, fontsize=8.8, color="#333333", ha="right", va="bottom",
            bbox=dict(boxstyle="round,pad=0.35", fc="#F7F9FB", ec="#C9D2DC"))

    # 近似匹配：教材「查找」表的分数段 → 等级（VLOOKUP 第 4 参数省略 TRUE）
    grade_df, bins, labels = load_scores()
    counts = grade_df["等级"].value_counts().reindex(labels)
    ax = axes[1]
    ax.bar(range(len(labels)), counts.values, color=[RED, "#E8A33D", "#F4B183", "#8FB78A", GREEN],
           width=0.62, zorder=3)
    bar_labels(ax, fmt="{:.0f}", fontsize=9.5)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_xlabel("成绩分档（近似匹配）")
    ax.set_ylabel("学生人数")
    ax.set_ylim(0, counts.max() * 1.3)
    ax.set_title(f"VLOOKUP 近似匹配：{len(grade_df)} 名学生成绩分档", pad=10)
    ax.grid(axis="x", visible=False)
    save_fig(fig, OUT, "fig03_VLOOKUP精确匹配与近似分档")

    save_csv(top, OUT, "table03_VLOOKUP匹配与商品销售")
    return top

def load_scores() -> tuple[pd.DataFrame, list, list]:
    """另一个工作簿的「查找」表：40 名学生 + 5 档分数区间。

    教材要求"按照 F 列分数段填写 C 列等级"，用的是 VLOOKUP 的**近似匹配**
    （第 4 参数省略/TRUE）。近似匹配的本质是「找到 <= 查找值的最后一个分界点」，
    pandas 里用 ``pd.cut``（左闭右开区间）表达同一件事，比 merge 更直观。
    """
    raw = pd.read_excel(XLSX_PIVOT, sheet_name="查找")
    df = raw[["学生姓名", "成绩"]].dropna().copy()
    df["成绩"] = df["成绩"].astype(float)
    labels = ["不及格", "及格", "可以", "良好", "优秀"]
    bins = [-1, 60, 70, 80, 90, 101]          # 左闭右开：60 分归"及格"，90 分归"优秀"
    df["等级"] = pd.cut(df["成绩"], bins=bins, labels=labels, right=False)
    print(f"  近似匹配（pd.cut，左闭右开）：{len(df)} 名学生 → "
          + "，".join(f"{k} {int((df['等级'] == k).sum())} 人" for k in labels))
    return df, bins, labels


# ---------------------------------------------------------------------------
# 4. sale.csv：区域 × 年份透视（教材透视表 + 条件格式色阶）
# ---------------------------------------------------------------------------
def sale_region_year() -> pd.DataFrame:
    """只读 12 行的 sale.csv，练「透视表 + 色阶 + 利润率」的最小闭环。

    文件是 GBK 编码（Windows 中文环境导出），``encoding="gbk"`` 才能读对，
    这点在做数据迁移时经常踩坑：pandas 默认 UTF-8 会直接抛 UnicodeDecodeError。
    """
    sale = pd.read_csv(CSV_SALE, encoding="gbk")
    sale.columns = ["year", "market", "sale", "profit"]
    sale["margin"] = sale["profit"] / sale["sale"]

    pv = sale.pivot_table(index="market", columns="year", values="sale", aggfunc="sum")
    mg = sale.pivot_table(index="market", columns="year", values="margin", aggfunc="mean")

    print("\n== 4. 区域 × 年份销售额（sale.csv） ==")
    print(f"  {len(sale)} 行 = {sale['market'].nunique()} 个市场 × {sale['year'].nunique()} 年；"
          f"合计销售额 {sale['sale'].sum():,} 元，利润率 {sale['profit'].sum() / sale['sale'].sum():.2%}")
    for mk in pv.index:
        series = pv.loc[mk]
        print(f"  {mk}区：" + "，".join(f"{y} {v:,.0f}" for y, v in series.items())
              + f"（三年变化 {series.iloc[-1] / series.iloc[0] - 1:+.1%}）")
    best = pv.stack().idxmax()
    print(f"  三年销售额最高的组合：{best[0]}区 {best[1]} 年（{pv.stack().max():,.0f} 元）；"
          f"最低 {pv.stack().min():,.0f} 元，极差仅 {(pv.stack().max() / pv.stack().min() - 1):.1%}")

    fig, axes = new_fig(11.4, 4.6, ncols=2,
                        gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.38})
    ax = axes[0]
    vals = pv.values / 10000
    im = ax.imshow(vals, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(pv.columns)), [f"{y} 年" for y in pv.columns])
    ax.set_yticks(range(len(pv.index)), [f"{m}区" for m in pv.index])
    lo, hi = vals.min(), vals.max()
    for i in range(pv.shape[0]):
        for j in range(pv.shape[1]):
            v = vals[i, j]
            # 按"归一化后的深浅"决定文字颜色，浅色格子不能用白字
            frac = (v - lo) / (hi - lo)
            ax.text(j, i, f"{v:.2f}万", ha="center", va="center", fontsize=9.5,
                    color="white" if frac > 0.62 else "#333333")
    ax.set_title("区域 × 年份销售额热力图（色阶=条件格式）", pad=10)
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.04)
    cb.set_label("销售额（万元）", fontsize=9)
    cb.ax.tick_params(labelsize=8)

    ax = axes[1]
    x = np.arange(len(pv))
    w = 0.26
    for k, y in enumerate(pv.columns):
        vals = mg[y].reindex(pv.index) * 100
        ax.bar(x + (k - 1) * w, vals, width=w, color=PALETTE[k], label=f"{y} 年", zorder=3)
        for xi, v in zip(x + (k - 1) * w, vals):
            ax.annotate(f"{v:.1f}", (xi, v), xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=7.6, color="#333333")
    ax.set_xticks(x, [f"{m}区" for m in pv.index])
    ax.set_ylabel("利润率（%）")
    ax.set_xlabel("")
    ax.set_ylim(0, mg.to_numpy().max() * 100 * 1.35)
    ax.set_title("各区域逐年利润率（利润 ÷ 销售额）", pad=10)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.10), fontsize=8.5)
    ax.grid(axis="x", visible=False)
    save_fig(fig, OUT, "fig04_区域年份销售额与利润率")
    return pv


# ---------------------------------------------------------------------------
# 5. 数据透视表 —— 3 地区 × 3 销售员 × 4 品名，36 行明细
# ---------------------------------------------------------------------------
def pivot_sales() -> pd.DataFrame:
    """教材「数据透视表」练习：按地区 × 品名汇总销售金额，再按销售员排行。

    Excel：插入透视表 → 行=销售地区、列=品名、值=求和项:销售金额 → 加「数据条」。
    pandas：``pivot_table(index=..., columns=..., aggfunc="sum", margins=True)``，
    ``margins=True`` 就相当于透视表的"总计"行列。
    """
    raw = pd.read_excel(XLSX_PIVOT, sheet_name="数据透视表")
    df = raw.dropna(subset=["销售地区", "销售人员", "品名"]).copy()
    for c in ("数量", "单价", "销售金额"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    pv = df.pivot_table(index="销售地区", columns="品名", values="销售金额",
                        aggfunc="sum", margins=True, margins_name="合计")
    person = (df.groupby("销售人员")
                .agg(订单行数=("品名", "size"), 数量=("数量", "sum"), 金额=("销售金额", "sum"))
                .sort_values("金额", ascending=False))
    person["金额占比"] = person["金额"] / person["金额"].sum()

    # 校验教材式勾稽：数量 × 单价 应等于销售金额
    calc = (df["数量"] * df["单价"] - df["销售金额"]).abs()
    print("\n== 5. 数据透视表：地区 × 品名 ==")
    print(f"  明细 {len(df)} 行，合计 {df['销售金额'].sum():,.0f} 元 / {int(df['数量'].sum()):,} 件；"
          f"「数量×单价=金额」勾稽误差最大 {calc.max():.2f} 元")
    print("  地区小计：" + "，".join(
        f"{r} {v / 1e4:.1f}万" for r, v in pv["合计"].drop("合计").items()))
    print("  品名小计：" + "，".join(
        f"{c} {pv.loc['合计', c] / 1e4:.1f}万" for c in pv.columns if c != "合计"))
    print("  销售员排名：" + "；".join(
        f"{n} {r.金额 / 1e4:.1f}万({r.金额占比:.1%})" for n, r in person.iterrows()))

    fig, axes = new_fig(11.2, 4.8, ncols=2, gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    items = [c for c in pv.columns if c != "合计"]
    regions = [r for r in pv.index if r != "合计"]
    bottom = np.zeros(len(regions))
    for k, item in enumerate(items):
        vals = pv.loc[regions, item].to_numpy() / 1e4
        ax.bar(regions, vals, bottom=bottom, color=PALETTE[k], width=0.55,
               label=item, zorder=3)
        bottom += vals
    for xi, tot in zip(range(len(regions)), pv.loc[regions, "合计"].to_numpy() / 1e4):
        ax.annotate(f"{tot:.1f}万", (xi, tot), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=9, color="#333333")
    ax.set_ylabel("销售金额（万元）")
    ax.set_ylim(0, bottom.max() * 1.22)
    ax.set_title("各销售地区 × 品名销售金额（堆叠=透视表列区）", pad=10)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.08), fontsize=8.6)
    ax.grid(axis="x", visible=False)

    ax = axes[1]
    y = np.arange(len(person))
    ax.barh(y, person["金额"] / 1e4, color=BLUE, height=0.45, zorder=3)
    ax.set_yticks(y, person.index)
    ax.invert_yaxis()
    ax.set_ylim(len(person) - 0.45, -0.55)
    for yi, (v, s) in enumerate(zip(person["金额"] / 1e4, person["金额占比"])):
        ax.annotate(f"{v:.1f}万 ({s:.1%})", (v, yi), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=9, color="#333333")
    ax.set_xlabel("销售金额（万元）")
    ax.set_title("销售人员业绩排行（SUMIFS 视角）", pad=10)
    ax.set_xlim(0, person["金额"].max() / 1e4 * 1.35)
    ax.grid(axis="y", visible=False)
    save_fig(fig, OUT, "fig05_地区品名透视与销售员排行")
    save_csv(pv.reset_index(), OUT, "table04_地区品名销售透视")
    return pv, person


# ---------------------------------------------------------------------------
# 6. 相对/绝对引用 —— 1 个公式拖 81 格 → 1 次广播
# ---------------------------------------------------------------------------
def reference_demo() -> None:
    """教材「单元格引用」工作表：用混合引用做一个九九乘法表。

    Excel 的 ``=$A2*B$1`` 靠"列绝对/行相对"控制拖拽方向；
    pandas/numpy 没有"拖拽"，直接把两个一维数组变成"行向量 × 列向量"做外积，
    一次算出 81 个值，再用 ``np.tril`` 只保留下三角 45 个有效格。
    """
    n = np.arange(1, 10)
    grid = n[:, None] * n[None, :]                 # 广播：9×9 外积
    tri = np.tril(np.ones_like(grid, dtype=bool))  # 下三角掩码 = 教材"空白格"
    print("\n== 6. 相对/绝对引用 → 向量化广播（九九乘法表） ==")
    for i in range(3):
        cells = [f"{i + 1}*{j + 1}={grid[i, j]}" for j in range(i + 1)]
        print("  " + "  ".join(cells))
    print(f"  …… 共 {int(tri.sum())} 个有效格（Excel 里是 1 个公式向下向右拖满 81 格）；"
          f"上三角 {int((~tri).sum())} 格留空")


def main() -> None:
    apply_style()
    stu = if_and_or()
    att = countif_attendance()
    top = vlookup_products()
    pv = sale_region_year()
    pivot, person = pivot_sales()
    reference_demo()
    person_ratio = person["金额"].max() / person["金额"].min() - 1

    print("\n" + "=" * 70)
    print("业务结论（可直接用于报告）")
    print("=" * 70)
    print(f"1. 成绩判定：{len(stu)} 人中 {int((stu['pass_all'] == '未通过').sum())} 人未达三科全及格线，"
          f"瓶颈在数学（{int((stu['math'] < PASS_LINE).sum())} 人不及格）；"
          f"「任一门及格即通过」口径下 100% 通过，该口径没有区分度。")
    print(f"2. 考勤：{len(att)} 人共迟到 {int(att['迟到次数'].sum())} 次、旷课 "
          f"{int(att['旷课次数'].sum())} 次，旷课最多的学生达 "
          f"{int(att['旷课次数'].max())} 次，是可优先约谈的对象。")
    print(f"3. 商品：100 张订单全部匹配成功，但只有 {top.shape[0]} 个 SKU 有动销"
          f"（占档案 2.9%），Top1「{top.iloc[0]['商品名称']}」贡献 "
          f"{top.iloc[0]['金额'] / top['金额'].sum():.1%} 的销售额。")
    print(f"4. 透视：三地区销售额 "
          + "、".join(f"{r} {v / 1e4:.1f}万" for r, v in pivot["合计"].drop("合计").items())
          + f"，合计 {pivot.loc['合计', '合计'] / 1e4:.1f} 万；"
          f"销售员首尾业绩差 {person_ratio:.1%}，是月度激励要盯的抓手。")
    print("\n完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
