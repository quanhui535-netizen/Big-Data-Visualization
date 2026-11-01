"""05_dashboard.py —— Pyecharts 静态数据大屏（1920×1080，深色主题，可离线打开）

产物：outputs/dashboard/dashboard.html
组件：4 个 KPI 卡 + 月度趋势 + 世界地图 + 国家条形 + RFM 环形 + 星期分布 + TOP 商品 + 明细表
（图表 6 个 + KPI 4 个 + 明细表 1 个，超过「不少于 6 个组件」的要求）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Bar, Line, Map, Pie, Scatter
from pyecharts.globals import ThemeType

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, TBL_DIR  # noqa: E402

OUT = ROOT / "outputs" / "dashboard"
ASSETS = OUT / "assets"
OUT.mkdir(parents=True, exist_ok=True)

DARK = "#0B1B33"
ACCENT = "#3FA9F5"
GOLD = "#FFC000"

KPI = [
    ("年度销售额", "849.2", "万英镑", "+18.4%", "#3FA9F5"),
    ("付费客户", "4,333", "人", "复购 65.3%", "#4FD1C5"),
    ("成交订单", "18,400", "张", "客单价 462", "#FFC000"),
    ("覆盖市场", "37", "个国家/地区", "英国占 82.4%", "#F4735C"),
]


def base_opts(height: int) -> opts.InitOpts:
    return opts.InitOpts(theme=ThemeType.DARK, width="100%", height=f"{height}px", bg_color="transparent")


def chart_title(title: str, sub: str = "") -> opts.TitleOpts:
    return opts.TitleOpts(
        title=title,
        subtitle=sub,
        pos_left="2%",
        pos_top="3%",
        title_textstyle_opts=opts.TextStyleOpts(color="#E8F1FF", font_size=17, font_weight="bold"),
        subtitle_textstyle_opts=opts.TextStyleOpts(color="#7FA6CC", font_size=11),
    )


def build() -> dict[str, tuple[str, str]]:
    """返回 {组件 id: (echarts 配置 JSON, 高度 css)}"""
    monthly = pd.read_csv(TBL_DIR / "monthly_trend.csv")
    country = pd.read_csv(TBL_DIR / "country_summary.csv")
    week = pd.read_csv(TBL_DIR / "weekday_trend.csv")
    rfm = pd.read_csv(TBL_DIR / "rfm_segment_summary.csv")
    sku = pd.read_csv(TBL_DIR / "sku_top100.csv").head(10)
    charts: dict[str, tuple[str, str]] = {}

    # 1 月度趋势：柱 + 折线双轴
    m = monthly.copy()
    bar = (Bar(init_opts=base_opts(274))
           .add_xaxis([s[2:] for s in m["Month"]])
           .add_yaxis("销售额（万英镑）", (m["销售额"] / 1e4).round(1).tolist(), bar_width="45%",
                      itemstyle_opts=opts.ItemStyleOpts(color=ACCENT, opacity=0.85),
                      label_opts=opts.LabelOpts(is_show=False))
           .extend_axis(yaxis=opts.AxisOpts(name="订单数", name_textstyle_opts=opts.TextStyleOpts(color=GOLD),
                                            axislabel_opts=opts.LabelOpts(color=GOLD)))
           .set_global_opts(
               title_opts=chart_title("月度销售额与订单量", "柱：销售额（万英镑）；线：订单数（张）"),
               xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="#9DBBD8", rotate=35, font_size=10)),
               yaxis_opts=opts.AxisOpts(name="销售额（万）", axislabel_opts=opts.LabelOpts(color="#9DBBD8")),
               legend_opts=opts.LegendOpts(textstyle_opts=opts.TextStyleOpts(color="#9DBBD8"), pos_top="3%", pos_right="4%"),
               tooltip_opts=opts.TooltipOpts(trigger="axis"))
           )
    line = (Line()
            .add_xaxis([s[2:] for s in m["Month"]])
            .add_yaxis("订单数", m["订单数"].tolist(), yaxis_index=1, is_smooth=True,
                       linestyle_opts=opts.LineStyleOpts(color=GOLD, width=3),
                       itemstyle_opts=opts.ItemStyleOpts(color=GOLD),
                       label_opts=opts.LabelOpts(is_show=False)))
    bar.overlap(line)
    charts["c_trend"] = (bar.dump_options(), "")

    # 2 世界地图
    cmap = country.copy()
    map_df = [[str(r["Country"]), round(float(r["销售额"]) / 1e4, 1)] for _, r in cmap.iterrows()]
    mp = (Map(init_opts=base_opts(556))
          .add("销售额（万英镑）", map_df, "world", is_map_symbol_show=False,
               label_opts=opts.LabelOpts(is_show=False),
               itemstyle_opts=opts.ItemStyleOpts(area_color="#12345A", border_color="#2A5C8F"))
          .set_global_opts(
              title_opts=chart_title("全球市场分布", "颜色越亮＝销售额越高"),
              visualmap_opts=opts.VisualMapOpts(max_=30, min_=0, is_piecewise=False, pos_left="3%", pos_bottom="6%",
                                                textstyle_opts=opts.TextStyleOpts(color="#9DBBD8"),
                                                range_color=["#16324F", "#3FA9F5", "#FFD166"]),
              legend_opts=opts.LegendOpts(is_show=False),
              tooltip_opts=opts.TooltipOpts(trigger="item"))
          .set_series_opts(label_opts=opts.LabelOpts(is_show=False))
          )
    charts["c_map"] = (mp.dump_options(), "")

    # 3 国家 TOP10 横向条形
    c10 = country[country["Country"] != "United Kingdom"].head(6).iloc[::-1]
    bar2 = (Bar(init_opts=base_opts(226))
            .add_xaxis(c10["Country"].tolist())
            .add_yaxis("销售额（万英镑）", (c10["销售额"] / 1e4).round(1).tolist(), bar_width="55%",
                       itemstyle_opts=opts.ItemStyleOpts(color="#4FD1C5"),
                       label_opts=opts.LabelOpts(is_show=True, position="right", color="#CFE6FF", font_size=10))
            .reversal_axis()
            .set_global_opts(
                title_opts=chart_title("海外市场 TOP6", "英国本土已剔除（占比 82.4%）"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="#9DBBD8")),
                yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="#9DBBD8", font_size=9, interval=0)),
                legend_opts=opts.LegendOpts(is_show=False),
                tooltip_opts=opts.TooltipOpts(trigger="axis"))
            )
    charts["c_country"] = (bar2.dump_options(), "")

    # 4 RFM 环形
    pie = (Pie(init_opts=base_opts(248))
           .add("销售额占比", [[r["Segment"], round(float(r["销售额占比"]) * 100, 1)] for _, r in rfm.iterrows()],
                radius=["34%", "58%"], center=["32%", "56%"],
                label_opts=opts.LabelOpts(is_show=False))
           .set_global_opts(
               title_opts=chart_title("客户价值结构（RFM 八分群）", "环图面积＝销售额占比"),
               legend_opts=opts.LegendOpts(orient="vertical", pos_right="1%", pos_top="18%",
                                           item_width=9, item_height=9, item_gap=6,
                                           textstyle_opts=opts.TextStyleOpts(color="#9DBBD8", font_size=9)),
               tooltip_opts=opts.TooltipOpts(trigger="item", formatter="{b}: {c}%"))
           )
    charts["c_rfm"] = (pie.dump_options(), "")

    # 5 星期分布
    w = week.copy()
    bar3 = (Bar(init_opts=base_opts(226))
            .add_xaxis(w["星期"].tolist())
            .add_yaxis("销售额（万英镑）", (w["销售额"] / 1e4).round(1).tolist(), bar_width="50%",
                       itemstyle_opts=opts.ItemStyleOpts(color="#7C9CF5"),
                       label_opts=opts.LabelOpts(is_show=True, position="top", color="#CFE6FF", font_size=10))
            .set_global_opts(
                title_opts=chart_title("星期销售额分布", "周六门店歇业，故无数据"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="#9DBBD8")),
                yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="#9DBBD8")),
                legend_opts=opts.LegendOpts(is_show=False),
                tooltip_opts=opts.TooltipOpts(trigger="axis"))
            )
    charts["c_week"] = (bar3.dump_options(), "")

    # 6 TOP10 商品
    labels = [str(t)[:14] for t in sku["Description"].fillna(sku["StockCode"])]
    bar4 = (Bar(init_opts=base_opts(248))
            .add_xaxis(labels)
            .add_yaxis("销售额（万英镑）", (sku["销售额"] / 1e4).round(1).tolist(), bar_width="52%",
                       itemstyle_opts=opts.ItemStyleOpts(color="#FFC000"),
                       label_opts=opts.LabelOpts(is_show=True, position="top", color="#FFE08A", font_size=9))
            .set_global_opts(
                title_opts=chart_title("销售额 TOP10 商品", "商品名截断至 14 字"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="#9DBBD8", rotate=32, font_size=9)),
                yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="#9DBBD8")),
                legend_opts=opts.LegendOpts(is_show=False),
                tooltip_opts=opts.TooltipOpts(trigger="axis"))
            )
    charts["c_top"] = (bar4.dump_options(), "")
    return charts


def html_table() -> str:
    rules = pd.read_csv(TBL_DIR / "association_rules.csv").nlargest(4, "lift")
    rows = []
    for _, r in rules.iterrows():
        rows.append(
            f"<tr><td>{str(r['antecedent_name'])[:22]}</td><td>{str(r['consequent_name'])[:20]}</td>"
            f"<td>{r['confidence']*100:.0f}%</td><td>{r['lift']:.1f}</td><td>{int(r['count'])}</td></tr>")
    head = ("<tr><th>购买组合（前项）</th><th>连带购买（后项）</th><th>置信度</th><th>提升度</th><th>订单数</th></tr>")
    return f'<table class="tbl">{head}{"".join(rows)}</table>'


CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { width:1920px; height:1080px; overflow:hidden; background:#061223;
       font-family:"Microsoft YaHei","SimHei",sans-serif; color:#E8F1FF; }
.wrap { width:1920px; height:1080px; padding:26px 30px 20px;
        background:radial-gradient(1200px 600px at 50% -10%, #123159 0%, #061223 60%); }
header { display:flex; align-items:flex-end; justify-content:space-between; height:78px; }
h1 { font-size:34px; letter-spacing:2px; font-weight:800;
     background:linear-gradient(90deg,#7FD3FF,#3FA9F5 45%,#FFC000);
     -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.sub { color:#7FA6CC; font-size:13px; letter-spacing:1px; margin-top:6px; }
.stamp { color:#7FA6CC; font-size:12px; text-align:right; line-height:1.7; }
.kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:18px; margin:16px 0 14px; }
.kpi { background:linear-gradient(150deg,rgba(31,72,120,.75),rgba(10,26,46,.9));
       border:1px solid rgba(63,169,245,.28); border-radius:10px; padding:14px 18px; position:relative; }
.kpi .lab { color:#8FB5D8; font-size:13px; letter-spacing:1px; }
.kpi .val { font-size:40px; font-weight:800; margin-top:2px; }
.kpi .unit { font-size:14px; color:#8FB5D8; margin-left:4px; }
.kpi .delta { position:absolute; right:16px; top:16px; font-size:12px; color:#4FD1C5;
              border:1px solid rgba(79,209,197,.4); border-radius:20px; padding:2px 9px; }
.grid { display:grid; grid-template-columns: 1.55fr 1fr 1fr; grid-template-rows: 288px 262px 240px;
        gap:16px; }
.cell { background:linear-gradient(160deg,rgba(17,42,73,.65),rgba(8,20,36,.9));
        border:1px solid rgba(63,169,245,.18); border-radius:10px; padding:6px; }
.tbl { width:100%; border-collapse:collapse; font-size:11px; color:#CFE6FF; }
.tbl th { color:#8FB5D8; font-weight:600; text-align:left; padding:6px 8px;
          border-bottom:1px solid rgba(63,169,245,.25); font-size:12px; }
.tbl td { padding:5px 8px; border-bottom:1px dashed rgba(63,169,245,.12); }
.tbl tr:hover td { background:rgba(63,169,245,.08); }
.cell-title { color:#E8F1FF; font-size:16px; font-weight:700; padding:8px 10px 6px; }
"""


def render(charts: dict[str, tuple[str, str]]) -> Path:
    echarts_js = (ASSETS / "echarts.min.js").read_text(encoding="utf-8", errors="ignore")
    world_js = (ASSETS / "world.js").read_text(encoding="utf-8", errors="ignore")
    table_html = html_table()
    kpi_html = "".join(
        f'<div class="kpi"><div class="lab">{lab}</div>'
        f'<div class="val" style="color:{col}">{val}<span class="unit">{unit}</span></div>'
        f'<div class="delta">{delta}</div></div>' for lab, val, unit, delta, col in KPI)

    init = "\n".join(
        f'var c_{k[2:]} = echarts.init(document.getElementById("{k}"), null, {{renderer:"canvas"}});\n'
        f'c_{k[2:]}.setOption({charts[k][0]});'
        for k in charts)
    resize = "window.addEventListener('resize', function(){ " + \
             "".join(f'c_{k[2:]}.resize();' for k in charts) + " });"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>在线零售商业分析大屏 · UCI Online Retail</title>
<style>{CSS}</style>
<script>{echarts_js}</script>
<script>{world_js}</script>
</head>
<body><div class="wrap">
<header>
  <div>
    <h1>在线零售商业分析大屏</h1>
    <div class="sub">UCI Online Retail Dataset · 2010-12 ~ 2011-12 · 8,491,574 英镑 / 4,333 位付费客户 / 18,400 张订单</div>
  </div>
  <div class="stamp">数据合规获取：UCI 官方公开数据集（CC BY 4.0）<br>全流程 Python 生成 · 未使用任何 BI 软件</div>
</header>
<div class="kpis">{kpi_html}</div>
<div class="grid">
  <div class="cell" style="grid-column:1 / span 2;grid-row:1"><div id="c_trend" style="width:100%;height:100%"></div></div>
  <div class="cell" style="grid-column:3;grid-row:1 / span 2"><div id="c_map" style="width:100%;height:100%"></div></div>
  <div class="cell" style="grid-column:1;grid-row:2"><div id="c_rfm" style="width:100%;height:100%"></div></div>
  <div class="cell" style="grid-column:2;grid-row:2"><div id="c_top" style="width:100%;height:100%"></div></div>
  <div class="cell" style="grid-column:1;grid-row:3"><div id="c_country" style="width:100%;height:100%"></div></div>
  <div class="cell" style="grid-column:2;grid-row:3"><div id="c_week" style="width:100%;height:100%"></div></div>
  <div class="cell" style="grid-column:3;grid-row:3;padding:8px 10px">
    <div class="cell-title">购物篮关联规则 TOP4（mlxtend · Apriori）</div>
    {table_html}
  </div>
</div>
</div>
<script>
{init}
{resize}
</script>
</body></html>"""
    path = OUT / "dashboard.html"
    path.write_text(html, encoding="utf-8")
    return path


def main() -> None:
    print("=" * 78)
    print("05_dashboard —— Pyecharts 数据大屏")
    print("=" * 78)
    charts = build()
    path = render(charts)
    print(f"[dash] 组件 {len(charts)} 个 + KPI 4 个 + 明细表")
    print(f"[dash] 已生成 {path}  ({path.stat().st_size/1024:.0f} KB，含离线 echarts)")


if __name__ == "__main__":
    main()
