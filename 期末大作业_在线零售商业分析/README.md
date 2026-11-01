# 基于在线零售数据的用户价值与复购洞察

> 《商业数据分析》期末大作业 · 嘉兴大学 数据科学学院 · 大数据 241 · 廖全辉（2024459985122）
> 仓库：https://github.com/quanhui535-netizen/Big-Data-Visualization
> 数据：UCI Online Retail Data Set（541,909 条真实交易，2010-12 ~ 2011-12）
> 全流程 Python 实现，未使用任何 BI 软件；数据经官方公开文件合规获取，无爬虫。

---

## 1. 项目简介

以一家英国在线零售商的真实交易流水为对象，完成「合规取数 → 清洗治理 → 六模型分析 → 23 张图表 → 双大屏 →
论文」的端到端分析。核心结论：

> 说明：仓库根目录同时保留了课程前期章节复现（`chapter2_前15`、`chapter2_后15`、`chapter3_动态图表`、
> `chapter4_人力资源`、`chapter4_销售`、`common_style.py`）；**期末大作业的全部代码与产物**位于
> `data/`、`scripts/`、`outputs/`、`docs/` 及根目录的 `app.py`、`run_all.py`。

| 发现 | 量化证据 |
|---|---|
| 收入高度集中 | 26.8% 的客户贡献 80% 销售额；前 10% 客户贡献 60.3% |
| 高价值客户是少数派 | 重要价值客户占 32.9% 人数，贡献 76.5% 销售额 |
| 首月即流失 | 次月留存 18.9%，第 11 个月仅 4.8% |
| 商品成套购买 | 香草标记牌三条规则提升度 81.7；茶具系列单规则覆盖 476 单 |
| 节律由日历驱动 | 周四峰值、周六歇业、12 点峰值；SARIMA 于圣诞窗口低估 23% |

## 2. 数据来源与合规声明

| 项目 | 说明 |
|---|---|
| 数据源 | Online Retail Data Set（UCI Machine Learning Repository，数据集 352） |
| 官方地址 | https://archive.ics.uci.edu/dataset/352/online+retail |
| 获取方式 | **官方公开 ZIP 文件一次性下载**（白名单第 1 类），全程无 Scrapy / Selenium / requests 网页解析 / 模拟登录 |
| 授权 | CC BY 4.0（数据集页标注） |
| 规模 | 541,909 行 × 8 列；清洗后 391,148 行 / 18,400 订单 / 4,333 客户 / 3,658 SKU / 37 市场 |
| 校验 | 下载文件的 SHA-256 与字节数记录于 `data/raw/source_meta.json` |
| 声明 | 仅用于课程作业的分析与展示，不再二次分发；复现请从官方地址自行下载 |

> 若官方直链在网络受限环境下不可达，`01_load.py` 会自动回落到 Hugging Face 上的同文件镜像
> （`michaelmallari/online-retail`，字节数与官方文件一致），并在 `source_meta.json` 中如实记录实际下载地址。

## 3. 目录结构

```
.
├── data/
│   ├── raw/                原始数据（由 01_load.py 下载）+ source_meta.json
│   ├── clean/              transactions / orders / customers / products / countries + clean_report.json
│   └── schema.md           数据字典与字段口径
├── scripts/
│   ├── common.py           路径、配色、中文字体、Excel 风格绘图工具
│   ├── 01_load.py          合规下载 + 校验 + 存 parquet
│   ├── 02_clean.py         十步清洗、指标派生、四表对齐、CSV/Parquet/SQLite 导出
│   ├── 03_analysis.py      六个模型 + 趋势聚合，产出 20 张结果表
│   ├── 04_visuals.py       23 张图（15 种模板复现 + 8 张业务模型图）
│   └── 05_dashboard.py     Pyecharts 静态大屏（离线可开）
├── outputs/
│   ├── figures/            23 张 PNG（200 dpi）+ 图表索引.csv
│   ├── tables/             结果表 + analysis_results.json
│   └── dashboard/          dashboard.html（内联 echarts，断网可用）+ 大屏截图
├── docs/                   论文 docx + pdf、合规声明、验收自检、论文生成脚本
├── app.py                  Streamlit 交互式仪表板（4 筛选器联动 6 组件）
├── requirements.txt
├── run_all.py              一键复现
└── README.md
```

## 4. 环境与依赖

- Python 3.13（3.10+ 均可）
- 依赖见 `requirements.txt`：pandas / numpy / matplotlib / seaborn / plotly / pyecharts /
  mlxtend / statsmodels / scikit-learn / streamlit / openpyxl / pyarrow / python-docx
- 中文字体：Windows 自带 SimHei 或微软雅黑即可（代码会自动探测）

```bash
pip install -r requirements.txt
```

## 5. 复现步骤

```bash
# 一键复现（下载→清洗→分析→出图→大屏）
python run_all.py

# 分步执行
python scripts/01_load.py        # 约 23 MB 下载，或直接放入 data/raw/online_retail.xlsx
python scripts/02_clean.py       # 约 1 分钟
python scripts/03_analysis.py    # 约 3 分钟（Apriori + SARIMA）
python scripts/04_visuals.py     # 生成 23 张图
python scripts/05_dashboard.py   # 生成 outputs/dashboard/dashboard.html

# 交互式大屏
streamlit run app.py

# 重新生成论文
python docs/build_paper.py
```

> 说明：`data/raw/online_retail.xlsx`、`data/clean/online_retail.db`、`data/clean/transactions.csv`
> 体积较大（23 MB / 64 MB / 57 MB），未纳入版本库，运行 `01_load.py`、`02_clean.py` 可完整重建。

## 6. 模型与参数

| 模型 | 关键参数 | 业务依据 |
|---|---|---|
| RFM 八分类 | R ≤ 50 天 / F ≥ 2 次 / M ≥ 661 英镑 | 三项均右偏，用中位数切分对极端值稳健且分组均衡 |
| 同期群留存 | 首购月分群，追踪 12 个月 | 观察价值衰减的真实节奏，而非整体平均 |
| Apriori | support ≥ 1%、lift ≥ 1.2、confidence ≥ 0.3、订单数 ≥ 15 | 1% ≈ 154 单，低于此规模无备货意义；lift 过滤伪关联 |
| SARIMA | (1,1,1)(0,1,1,7)，log(1+y) | 仅 13 个月，月度季节项不可估；改用日粒度捕捉周内节律 |
| 帕累托 / ABC | 累计 70% / 90% | 库存管理通行口径 |
| 波士顿矩阵 | 份额中位数 × 零增长 | 组内中位与「下半年是否跑赢上半年」 |

模型回测：SARIMA MAPE 35.4%、RMSE 17,420、sMAPE 67.3%，对照季节朴素法 31.6%——
圣诞促销脉冲无法被纯时序捕捉，已在论文「局限性」中讨论并给出 SARIMAX + 促销日历的改进方向。

## 7. 图表索引

| 编号 | 图表 | 类型 |
|---|---|---|
| fig01–fig15 | 渐变柱形、带平均线柱形、渐变圆角柱形、层叠柱形(100%)、蝴蝶、数值百分比条形、甘特、平滑折线、菱形走势、对比折线、单值圆环、南丁格尔玫瑰、玉玦、水球、柱形折线 | **模板复现 15 种**（对照教材 30 个模板） |
| fig16–fig23 | RFM 气泡散点、八分群价值对比、同期群留存热力、帕累托、波士顿矩阵、关联规则气泡、SARIMA 预测带、ABC 分层 | **业务模型图 8 张** |
| 大屏 | Pyecharts 静态大屏（10 组件，截图 `dashboard_preview.png`）+ Streamlit 交互应用（4 筛选器 / 6 组件联动） | 交互可视化 |

完整清单见 `outputs/figures/图表索引.csv`。

## 8. 可复现性说明

- 全部图表由脚本生成，随机性来源仅 Apriori 的项集枚举（确定性）与 SARIMA 优化（确定性初值），无需设随机种子；
- 未做抽样，所有模型基于全量清洗后数据；
- 依赖版本在 `requirements.txt` 中锁定下限，输出文件名与图表编号固定，便于逐项核对。

## 9. 分工说明

| 成员 | 分工 |
|---|---|
| 廖全辉（2024459985122，大数据 241） | 数据获取与清洗、六模型实现、可视化与双大屏、论文撰写与排版 |

## 10. 声明

本项目为课程作业，数据分析结论由脚本计算并人工复核；论文中使用 AI 编程助手的情况已在正文
「7.3 AI 使用披露」中如实说明。未使用 Power BI / Tableau / Fine BI 等 BI 软件出图，
未使用爬虫获取数据。
