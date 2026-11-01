"""app.py —— Streamlit 交互式分析仪表板（联动筛选，全 Python 实现）

启动：streamlit run app.py
组件：4 个 KPI 卡 + 月度趋势 + 国家 TOP10 + RFM 结构 + 星期×小时热力 + 客户帕累托 + 明细表
联动：侧边栏 4 个筛选器（市场 / 日期区间 / 客户分层 / 客单价区间）同时驱动以上全部组件
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "clean"
TABLES = ROOT / "outputs" / "tables"

BLUE, DARK, ORANGE, GRAY = "#4472C4", "#264478", "#ED7D31", "#A5A5A5"
SEG_ORDER = ["重要价值客户", "重要发展客户", "重要保持客户", "重要挽留客户",
             "一般价值客户", "一般发展客户", "一般保持客户", "一般挽留客户"]
SEG_COLORS = {
    "重要价值客户": "#264478", "重要发展客户": "#4472C4", "重要保持客户": "#8FAADC",
    "重要挽留客户": "#C00000", "一般价值客户": "#70AD47", "一般发展客户": "#A9D18E",
    "一般保持客户": "#FFC000", "一般挽留客户": "#A5A5A5",
}

st.set_page_config(page_title="在线零售商业分析仪表板", page_icon="📊", layout="wide")


@st.cache_data(show_spinner="正在加载交易数据 ...")
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    tx = pd.read_parquet(DATA / "transactions.parquet")
    rfm = pd.read_csv(TABLES / "rfm_customer_level.csv")[["CustomerID", "Segment"]]
    tx = tx.merge(rfm, on="CustomerID", how="left")
    tx["Segment"] = tx["Segment"].fillna("未分层")
    return tx, rfm


tx, rfm = load()

st.title("在线零售商业分析仪表板")
st.caption("数据源：UCI Online Retail Dataset（2010-12 ~ 2011-12，CC BY 4.0）｜"
           "全部图表由 Python 生成，未使用任何 BI 软件")

# ---------------------------------------------------------------- 侧边栏筛选器
with st.sidebar:
    st.header("筛选器")
    countries = sorted(tx["Country"].unique().tolist())
    default = ["United Kingdom", "Netherlands", "EIRE", "Germany", "France"]
    pick_countries = st.multiselect("市场（国家）", countries,
                                    default=[c for c in default if c in countries])
    dmin, dmax = tx["InvoiceDate"].min().date(), tx["InvoiceDate"].max().date()
    date_range = st.date_input("下单日期区间", value=(dmin, dmax), min_value=dmin, max_value=dmax)
    pick_seg = st.multiselect("客户分层（RFM）", SEG_ORDER + ["未分层"], default=SEG_ORDER)
    aov_min, aov_max = st.slider("单笔订单金额区间（英镑）", 0, 5000, (0, 5000), step=50)
    st.divider()
    st.caption("筛选条件实时联动右侧全部图表与指标卡。")

# ---------------------------------------------------------------- 应用筛选
df = tx[tx["Country"].isin(pick_countries)] if pick_countries else tx
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
    df = df[(df["InvoiceDate"] >= start) & (df["InvoiceDate"] < end)]
if pick_seg:
    df = df[df["Segment"].isin(pick_seg)]

order_value = df.groupby("InvoiceNo")["Revenue"].sum()
keep_orders = order_value[(order_value >= aov_min) & (order_value <= aov_max)].index
df = df[df["InvoiceNo"].isin(keep_orders)]

if df.empty:
    st.warning("当前筛选条件下没有数据，请放宽条件。")
    st.stop()

# ---------------------------------------------------------------- KPI 卡
revenue = df["Revenue"].sum()
orders = df["InvoiceNo"].nunique()
customers = df["CustomerID"].nunique()
aov = revenue / orders if orders else 0
repurchase = float((df.groupby("CustomerID")["InvoiceNo"].nunique() >= 2).mean())

c1, c2, c3, c4 = st.columns(4)
c1.metric("销售额", f"{revenue/1e4:,.1f} 万英镑")
c2.metric("订单数", f"{orders:,} 张")
c3.metric("客户数", f"{customers:,} 人")
c4.metric("客单价 / 复购率", f"{aov:,.0f} / {repurchase:.1%}")

st.divider()

# ---------------------------------------------------------------- 趋势 + 国家
left, right = st.columns((1.5, 1))
with left:
    m = (df.groupby("Month").agg(销售额=("Revenue", "sum"), 订单数=("InvoiceNo", "nunique"))
           .reset_index())
    fig = go.Figure()
    fig.add_bar(x=m["Month"], y=m["销售额"] / 1e4, name="销售额（万英镑）", marker_color=BLUE, opacity=0.85)
    fig.add_scatter(x=m["Month"], y=m["订单数"], name="订单数", yaxis="y2",
                    line=dict(color=ORANGE, width=3), mode="lines+markers")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10),
                      title="月度销售额与订单量（联动）",
                      yaxis=dict(title="销售额（万英镑）"),
                      yaxis2=dict(title="订单数", overlaying="y", side="right", showgrid=False),
                      legend=dict(orientation="h", y=1.12), plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

with right:
    c = (df.groupby("Country")["Revenue"].sum().sort_values(ascending=False).head(10).reset_index())
    fig = px.bar(c.iloc[::-1], x="Revenue", y="Country", orientation="h",
                 color_discrete_sequence=[DARK], title="市场销售额 TOP10")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10),
                      xaxis_title="销售额（英镑）", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- RFM + 热力
left, right = st.columns((1, 1.4))
with left:
    seg = (df.groupby("Segment")["Revenue"].sum().reindex(SEG_ORDER).dropna().reset_index())
    fig = px.pie(seg, names="Segment", values="Revenue", hole=0.45,
                 color="Segment", color_discrete_map=SEG_COLORS, title="客户价值结构（销售额）")
    fig.update_traces(textposition="inside", textinfo="percent")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10), showlegend=True,
                      legend=dict(font=dict(size=9)))
    st.plotly_chart(fig, use_container_width=True)

with right:
    dow_name = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    hm = (df.assign(星期=df["DOW"].map(dict(enumerate(dow_name))))
            .pivot_table(index="星期", columns="Hour", values="Revenue", aggfunc="sum")
            .reindex(dow_name))
    fig = px.imshow(hm, aspect="auto", color_continuous_scale="Blues",
                    labels=dict(x="下单小时", y="", color="销售额"),
                    title="星期 × 小时 销售额热力（联动）")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- 帕累托 + 明细
left, right = st.columns((1.2, 1))
with left:
    cust = df.groupby("CustomerID")["Revenue"].sum().sort_values(ascending=False)
    cum = cust.cumsum() / cust.sum()
    fig = go.Figure()
    fig.add_bar(x=np.arange(1, len(cust) + 1), y=cust.values, name="客户销售额", marker_color="#8FAADC")
    fig.add_scatter(x=np.arange(1, len(cust) + 1), y=cum.values * 100, name="累计占比",
                    yaxis="y2", line=dict(color=ORANGE, width=2.5))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=40, b=10), title="客户帕累托曲线（联动）",
                      xaxis_title="客户排名", yaxis=dict(title="销售额"),
                      yaxis2=dict(title="累计占比 %", overlaying="y", side="right", range=[0, 105]),
                      legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, use_container_width=True)

with right:
    top = (df.groupby("StockCode").agg(Description=("Description", "first"),
                                       销售额=("Revenue", "sum"), 销量=("Quantity", "sum"))
             .sort_values("销售额", ascending=False).head(8).reset_index())
    top["销售额"] = top["销售额"].map(lambda v: f"{v:,.0f}")
    st.markdown("**商品销售额 TOP8（联动明细）**")
    st.dataframe(top[["Description", "销售额", "销量"]].rename(
        columns={"Description": "商品", "销售额": "销售额（英镑）", "销量": "销量"}), height=340)

st.caption("提示：修改左侧任一筛选器，KPI、趋势、结构、热力、帕累托与明细表会同时刷新。")
