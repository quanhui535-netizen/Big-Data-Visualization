# 商业数据分析 · 课程作业仓库

嘉兴大学 数据科学学院 · 大数据 241 · 廖全辉（2024459985122）

仓库按内容分为三个目录，互不干扰：

| 目录 | 内容 | 说明 |
|---|---|---|
| [`期末大作业_在线零售商业分析/`](./期末大作业_在线零售商业分析) | 期末大作业：UCI 在线零售数据端到端分析 | 六个模型、23 张图、双大屏、论文（docx + pdf）、一键复现 |
| [`课程章节复现_Excel图表/`](./课程章节复现_Excel图表) | 课程前期章节练习 | 对照《Excel数据可视化》复现第 2–4 章图表，含交互 HTML 与看板 |
| [`商业数据分析_教材实验/`](./商业数据分析_教材实验) | 教材实验：CDA 四本教材的 Python 迁移 | 14 个实验，Excel/Power BI 案例迁移 + ipynb 重构为 .py，约 70 张图 |

## 快速导航

- **项目说明**：[期末大作业 README](./期末大作业_在线零售商业分析/README.md)
- **教材实验**：[实验总览与 14 个实验索引](./商业数据分析_教材实验/README.md)
- **论文**：[Word 版](./期末大作业_在线零售商业分析/docs/期末大论文_基于在线零售数据的用户价值与复购洞察.docx) ／ [PDF 版](./期末大作业_在线零售商业分析/docs/期末大论文_基于在线零售数据的用户价值与复购洞察.pdf)
- **图表索引**：[outputs/figures/图表索引.csv](./期末大作业_在线零售商业分析/outputs/figures/图表索引.csv)
- **大屏**：[dashboard.html](./期末大作业_在线零售商业分析/outputs/dashboard/dashboard.html)（双击离线可开）

## 复现命令

```bash
# 期末大作业
cd 期末大作业_在线零售商业分析
pip install -r requirements.txt
python run_all.py          # 下载 → 清洗 → 建模 → 出图 → 大屏，约 1 分钟
streamlit run app.py       # 交互式仪表板（4 个筛选器联动 6 个组件）

# 教材实验（14 个实验，逐个运行，或在目录内一键跑全部）
cd 商业数据分析_教材实验
pip install -r requirements.txt
python run_all.py
```

## 数据合规

- 数据源：UCI Machine Learning Repository《Online Retail Data Set》（#352），官方公开 ZIP 一次性下载，**无爬虫**
- 授权：CC BY 4.0，仅用于课程学习
- 原始文件（23 MB）与 SQLite（64 MB）未入库，由 `scripts/01_load.py` 自动下载重建；来源、SHA-256 与获取时间记录于 `data/raw/source_meta.json`

## 声明

全部图表与大屏由 Python 生成，未使用 Power BI / Tableau / Fine BI 等 BI 软件；论文中的 AI 使用情况已在正文「7.3 AI 使用披露」中如实说明。