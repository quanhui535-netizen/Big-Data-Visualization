# -*- coding: utf-8 -*-
"""build_paper.py —— 按课程模板排版生成期末大论文（Word）

用法：python docs/build_paper.py
产物：docs/期末大论文_基于在线零售数据的用户价值与复购洞察.docx
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
TBL = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
DOCS = ROOT / "docs"

R = json.loads((TBL / "analysis_results.json").read_text(encoding="utf-8"))
CLEAN = json.loads((ROOT / "data" / "clean" / "clean_report.json").read_text(encoding="utf-8"))
META = json.loads((ROOT / "data" / "raw" / "source_meta.json").read_text(encoding="utf-8"))

TITLE = "基于在线零售数据的用户价值与复购洞察"

# ------------------------------------------------------------------ 格式工具

def set_font(run, name="宋体", size=12, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if color:
        run.font.color.rgb = RGBColor(*color)


def para(doc, text="", *, size=12, name="宋体", bold=False, indent_chars=2,
         align=WD_ALIGN_PARAGRAPH.LEFT, space_after=0, line=1.5):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = line
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(0)
    if indent_chars:
        pf.first_line_indent = Pt(size * indent_chars)
    p.alignment = align
    if text:
        set_font(p.add_run(text), name, size, bold)
    return p


def heading(doc, text, level=1):
    sizes = {1: (14, "黑体"), 2: (12, "黑体")}
    size, name = sizes[level]
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(12 if level == 1 else 8)
    pf.space_after = Pt(6 if level == 1 else 4)
    pf.line_spacing = 1.5
    pf.first_line_indent = Pt(0)
    pf.keep_with_next = True
    set_font(p.add_run(text), name, size, bold=(level == 1))
    return p


def caption(doc, text, *, size=10.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.0
    set_font(p.add_run(text), "宋体", size)
    return p


def figure(doc, fname, cap, width=5.2):
    path = FIG / fname
    if not path.exists():
        print("  missing figure:", fname)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(width))
    caption(doc, cap)


def _set_cell_borders(cell, spec: dict[str, tuple[int, str]]):
    """spec: {'top': (sz_eighth_pt, 'single'|'nil'), ...}"""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = tcPr.find(qn("w:tcBorders"))
    if tcBorders is None:
        tcBorders = OxmlElement("w:tcBorders")
        tcPr.append(tcBorders)
    for edge, (sz, val) in spec.items():
        el = tcBorders.find(qn(f"w:{edge}"))
        if el is None:
            el = OxmlElement(f"w:{edge}")
            tcBorders.append(el)
        el.set(qn("w:val"), val)
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")


def _three_line_table(t):
    """把表格改成三线表：顶线 1.5 磅、栏目线 0.75 磅、底线 1.5 磅，其余边框全部去掉。"""
    n_rows = len(t.rows)
    for r_idx, row in enumerate(t.rows):
        for cell in row.cells:
            spec = {"top": (0, "nil"), "bottom": (0, "nil"),
                    "left": (0, "nil"), "right": (0, "nil"),
                    "insideH": (0, "nil"), "insideV": (0, "nil")}
            if r_idx == 0:
                spec["top"] = (12, "single")      # 顶线 1.5 磅
                spec["bottom"] = (6, "single")    # 栏目线 0.75 磅
            if r_idx == n_rows - 1:
                spec["bottom"] = (12, "single")   # 底线 1.5 磅
            _set_cell_borders(cell, spec)


def table(doc, header, rows, cap="", widths=None, font=9.5):
    if cap:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        set_font(p.add_run(cap), "宋体", 10.5, bold=True)
    t = doc.add_table(rows=1, cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = True
    for i, h in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        pp = cell.paragraphs[0]
        pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pp.paragraph_format.space_before = Pt(2)
        pp.paragraph_format.space_after = Pt(2)
        set_font(pp.add_run(str(h)), "宋体", font, bold=True)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            pp = cells[i].paragraphs[0]
            pp.alignment = WD_ALIGN_PARAGRAPH.CENTER if i else WD_ALIGN_PARAGRAPH.LEFT
            pp.paragraph_format.space_before = Pt(1)
            pp.paragraph_format.space_after = Pt(1)
            set_font(pp.add_run(str(v)), "宋体", font)
    if widths:
        total = sum(widths)
        scale = 15.0 / total  # 版心宽度 15cm（A4 21cm - 左右各 3cm）
        cm = [w * scale for w in widths]
        _fix_table_width(t, cm)
    _three_line_table(t)
    # 行不跨页拆分，且整表尽量不跨页（除末行外全部 keep_with_next）
    for idx, row in enumerate(t.rows):
        trPr = row._tr.get_or_add_trPr()
        if trPr.find(qn("w:cantSplit")) is None:
            trPr.append(OxmlElement("w:cantSplit"))
        if idx < len(t.rows) - 1:
            for cell in row.cells:
                for pp in cell.paragraphs:
                    pp.paragraph_format.keep_with_next = True
    return t


def _fix_table_width(t, cm_widths):
    """固定表格版式：显式设置表宽与列宽，避免 Word 自动收缩。"""
    t.autofit = False
    tbl = t._tbl
    tblPr = tbl.tblPr
    for el in tblPr.findall(qn("w:tblW")):
        tblPr.remove(el)
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:w"), str(int(round(15.0 / 2.54 * 1440))))
    tblW.set(qn("w:type"), "dxa")
    tblPr.append(tblW)
    for el in tblPr.findall(qn("w:tblLayout")):
        tblPr.remove(el)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    for i, w in enumerate(cm_widths):
        t.columns[i].width = Cm(w)
        for row in t.rows:
            row.cells[i].width = Cm(w)
    # 表头跨页重复
    trPr = t.rows[0]._tr.get_or_add_trPr()
    if trPr.find(qn("w:tblHeader")) is None:
        trPr.append(OxmlElement("w:tblHeader"))


# ------------------------------------------------------------------ 文档骨架
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(2.54)
sec.left_margin = sec.right_margin = Cm(3.0)

normal = doc.styles["Normal"]
normal.font.name = "宋体"
normal.font.size = Pt(12)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

# ---------------- 封面
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(30)
set_font(p.add_run("商业数据分析"), "黑体", 30, bold=True)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(10)
set_font(p.add_run("期末大作业（论文）"), "黑体", 18)

doc.add_paragraph()
for line in ["题　　目：", "学　　院：", "专业班级：", "学　　号：", "姓　　名：", "完成日期："]:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.left_indent = Cm(4.2)
    p.paragraph_format.line_spacing = 1.5
    set_font(p.add_run(line), "宋体", 14)
    if line == "题　　目：":
        set_font(p.add_run(TITLE), "宋体", 12)
    else:
        set_font(p.add_run("＿" * 13), "宋体", 12)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(26)
set_font(p.add_run("数据科学学院"), "宋体", 14)

doc.add_page_break()

# ---------------- 评分表
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_font(p.add_run("评分表"), "黑体", 14, bold=True)
score_rows = [
    ("1. 数据获取合规性与清洗质量（15分）", "① 来源合规、白名单方式、合规声明完整（5）；② 数据量达标（4）；③ 清洗完整、异常/缺失/重复处理、多表对齐（4）；④ 可导出 CSV/JSON/SQLite 复用（2）", ""),
    ("2. 商业分析模型应用深度（20分）", "① 模型≥3种、选型与场景匹配（6）；② 计算正确、参数与阈值有业务依据（6）；③ 预测类含置信区间与回测误差（4）；④ 结论与模型一一对应（4）", ""),
    ("3. 可视化复现与大屏质量（25分）", "① 图表≥10张、类别覆盖全面（6）；② 模板复现≥10种（7）；③ 业务模型图≥6张（6）；④ 交互大屏≥1个、组件≥6、有联动（6）", ""),
    ("4. 代码规范性与文档完整性（10分）", "① 目录结构清晰、注释充分（3）；② README 详实（3）；③ 可一键复现（2）；④ 图表命名与索引规范（2）", ""),
    ("5. 期末大论文质量（25分）", "① 题目创新性（4）；② 摘要与关键词（4）；③ 正文逻辑与技术深度（10）；④ 商业建议可行性与数据支撑（7）", ""),
    ("6. 创新性与商业洞察深度（5分）", "① 新工具/新方法（2）；② 有效商业建议（2）；③ 批判性思维（1）", ""),
]
table(doc, ["评分维度", "评分要点（子项及分值）", "得分"], score_rows,
      widths=[4.8, 10.2, 1.8], font=9)
doc.add_page_break()

# ---------------- 题目 / 作者 / 摘要
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(6)
set_font(p.add_run(TITLE), "黑体", 16, bold=True)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_font(p.add_run("作者：__________"), "宋体", 10.5)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_font(p.add_run("（嘉兴大学 数据科学学院）"), "宋体", 10.5)

p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.line_spacing = 1.5
set_font(p.add_run("摘　要："), "黑体", 14)
ABSTRACT_TEXT = (
    "以英国在线零售商 2010 年 12 月至 2011 年 12 月的 54 万条真实交易流水为对象，本文完成了一次"
    "端到端的商业数据分析实践：通过 UCI 官方公开文件合规获取数据，经十步清洗治理得到 39.1 万条有效"
    "交易、4333 位付费客户与 18400 张订单；在此基础上构建 RFM 八分类、同期群留存、Apriori 关联规则、"
    "SARIMA 预测、帕累托/ABC 与波士顿矩阵六个模型；使用 Matplotlib、Seaborn、Pyecharts 与 Streamlit "
    "复现 15 种 Excel 可视化模板、绘制 8 张业务模型图并搭建含 10 个组件的交互大屏。研究发现：26.8% 的"
    "客户贡献 80% 销售额，重要价值客户以 32.9% 的人数贡献 76.5% 的销售额；次月留存仅 18.9%，第 11 个月"
    "跌至 4.8%；销售额呈显著的年末爬坡与星期节律，周四为峰值、周六歇业。据此提出分层运营、次月挽回、"
    "连带陈列与备货节律四类可落地建议。")
set_font(p.add_run(ABSTRACT_TEXT), "宋体", 12)

p = doc.add_paragraph()
p.paragraph_format.line_spacing = 1.5
p.paragraph_format.space_before = Pt(6)
set_font(p.add_run("关键词："), "黑体", 14)
set_font(p.add_run("商业数据分析；RFM 模型；同期群留存；SARIMA 预测；Python 可视化；交互式大屏"), "宋体", 12)

doc.add_page_break()

# ================================================================== 1 引言
heading(doc, "1　引言")

heading(doc, "1.1　研究背景", 2)
para(doc,
     "在线零售把交易沉淀成了一种高频、细粒度、可持续观测的经营数据。对一家以批发客户为主、"
     "同时经营零散订单的英国在线零售商而言，订单表里同时记录着客户身份、商品编码、成交数量、"
     "单价与时间戳，这些字段天然构成“谁在买、买什么、什么时候买、买了多少”的完整证据链。"
     "但原始流水本身并不直接产生决策价值：它既包含退货与手工调整，也夹杂着邮费、银行手续费等"
     "非商品行；客户标识存在缺失；金额分布极度右偏。若不经治理就直接统计，得到的“平均客单价”"
     "与“客户价值”都会被少数大额订单扭曲。")
para(doc,
     "与此同时，商业分析的技术栈正在从“Excel 出图”转向“可复现的代码流水线”。课程要求以 Python "
     "完成从数据获取、清洗、建模到可视化大屏的全过程，本质上是在训练一种工程化的分析习惯：数据来源"
     "可追溯、清洗步骤可复述、模型参数可解释、图表结果可一键重跑。本文即以这一标准组织全部分析工作。")

heading(doc, "1.2　研究目的", 2)
para(doc,
     "本文试图用一条可复现的流水线回答四个具体问题：第一，这家零售商的收入究竟由哪些客户贡献，"
     "客户价值结构是“橄榄型”还是“金字塔型”；第二，新客在首购之后的留存曲线如何衰减，价值在哪个月份"
     "流失最快；第三，商品之间是否存在稳定的连带购买关系，可支撑组合陈列与打包定价；第四，销售额是否"
     "存在可被建模的季节性与星期节律，从而为备货与人力排班提供预测依据。")

heading(doc, "1.3　研究意义", 2)
para(doc,
     "方法层面，本文把六个商业分析模型放在同一份数据、同一套清洗口径下比较，避免“每个模型各用一份"
     "数据”的常见问题；工程层面，全部图表与大屏由脚本生成，配合 requirements.txt 与 run_all.py 可一键"
     "复现；商业层面，结论直接指向可执行动作——给谁发券、何时挽回、哪些商品该捆绑、旺季前备多少货。")

# ================================================================== 2 数据准备
heading(doc, "2　数据准备与预处理")

heading(doc, "2.1　数据源介绍（名称、URL、规模、字段说明）", 2)
para(doc,
     f"主数据源为 UCI Machine Learning Repository 的 Online Retail Data Set（数据集编号 352），"
     f"官方页面为 https://archive.ics.uci.edu/dataset/352/online+retail 。该数据集记录了一家注册于英国的"
     f"在线零售商在 {META['date_min'][:10]} 至 {META['date_max'][:10]} 期间的全部交易流水，"
     f"原始规模为 {META['rows']:,} 行 × {META['cols']} 列，是电商场景下少见的、同时具备客户标识、"
     f"商品明细与时间戳的公开长周期数据。")
table(doc,
      ["字段", "含义", "类型", "清洗后的用途"],
      [["InvoiceNo", "订单号，C 开头表示取消单", "字符串", "订单级聚合、取消单识别"],
       ["StockCode", "商品编码（5 位数字 + 可选字母后缀）", "字符串", "SKU 级分析、关联规则"],
       ["Description", "商品名称（英文）", "字符串", "图表标签、规则可读化"],
       ["Quantity", "成交数量，负值表示退货", "整数", "销量、退货识别"],
       ["InvoiceDate", "下单时间（精确到分钟）", "日期时间", "趋势、同期群、预测"],
       ["UnitPrice", "单价（英镑）", "浮点", "销售额计算"],
       ["CustomerID", "客户编号，存在缺失", "浮点/整数", "客户级 RFM、同期群"],
       ["Country", "客户所在国家", "字符串", "市场结构、地理可视化"]],
      cap="表 1　原始数据字段说明", widths=[2.8, 6.4, 2.2, 4.6], font=9)

heading(doc, "2.2　合规获取方式（白名单方式说明）", 2)
para(doc,
     "数据获取采用附件 A 白名单中的第一类方式——数据源官方提供的一次性文件下载：通过 UCI 官方静态链接"
     "直接下载公开 ZIP 包，解压得到 Online Retail.xlsx，全程未使用 Scrapy、Selenium、requests 网页解析"
     "或任何形式的模拟登录抓取。下载脚本 01_load.py 会记录下载地址、时间、字节数与 SHA-256 摘要，"
     f"本次获取的文件 SHA-256 前 16 位为 {META['sha256'][:16]}，可与官方文件逐字节比对。")

heading(doc, "2.3　数据来源合规声明", 2)
para(doc,
     "数据源名称：Online Retail Data Set（UCI #352）；来源 URL：https://archive.ics.uci.edu/dataset/352/online+retail ；"
     "获取方式：官方公开 ZIP 文件直接下载（非爬虫）；"
     f"获取日期：{META['downloaded_at'][:10]}；授权说明：数据集页面标注为 CC BY 4.0，允许在署名前提下"
     "用于研究与教学。本文仅将该数据用于课程作业的分析与展示，不再二次分发原始文件；仓库中保留下载脚本"
     "与校验信息，评审者可自行从官方地址复现获取过程。")

heading(doc, "2.4　数据集概述（主表/维度表结构、主外键关系）", 2)
para(doc,
     "原始文件为单表事务型结构，但逻辑上可无损拆分为四张表：以 InvoiceNo 为主键的订单表、以 CustomerID "
     "为主键的客户表、以 StockCode 为主键的商品表，以及以 Country 为主键的市场表。拆分后，交易明细表"
     "通过三个外键与维度表对齐，既符合星型模型的组织方式，也让后续的 RFM（客户维度）、关联规则"
     "（订单×商品）、波士顿矩阵（商品维度）可以各自在正确的粒度上计算，避免在明细层反复去重。")

# ================================================================== 3 清洗
heading(doc, "3　数据清洗与治理")

heading(doc, "3.1　数据清洗（缺失值、异常值、重复值处理）", 2)
para(doc,
     f"清洗遵循“先剔除结构性噪声、再处理缺失、最后处理极端值”的顺序，每一步都记录行数变化，"
     f"形成可复述的清洗日志（表 2）。原始 {CLEAN['raw_rows']:,} 行最终保留 {CLEAN['clean_rows']:,} 行，"
     f"保留率 {CLEAN['keep_ratio']*100:.1f}%，共剔除 {CLEAN['raw_rows']-CLEAN['clean_rows']:,} 行。")
rows = []
NOTE = {"1": "统一为字符串/日期类型", "2": "与全表完全重复", "3": "拆出，单列统计",
        "4": "邮费/手工调整/银行费用", "5": "数量≤0 或单价≤0", "6": "游客交易，单列统计",
        "7": "数量>10000 的调整行"}
for s in CLEAN["steps"]:
    rows.append([s["step"], f"{s['rows_before']:,}", f"{s['rows_after']:,}", f"{s['removed']:,}",
                 NOTE.get(s["step"][:1], "")])
table(doc, ["步骤", "处理前", "处理后", "剔除", "说明"], rows,
      cap="表 2　十步清洗日志", widths=[4.8, 1.9, 1.9, 1.9, 5.9], font=8.5)
para(doc,
     f"其中，取消单 {CLEAN['cancelled_rows']:,} 行被单独拆出，用于后续观察退货规模而不污染销售口径；"
     f"邮费、手工调整、银行手续费等非商品行 2406 行被剔除，因为它们不对应任何真实 SKU，会污染商品维度；"
     f"客户标识缺失的 {CLEAN['guest_rows']:,} 行（约 150.96 万英镑）被单列为“游客交易”，"
     f"既不进入客户级模型，也不直接丢弃——它们的规模本身说明约 15% 的销售额无法归因到具体客户，"
     f"这构成了后续商业建议中“注册转化”的量化依据。")

heading(doc, "3.2　数据转换（类型统一、日期对齐、指标派生）", 2)
para(doc,
     "类型统一环节修正了原始 Excel 中 Description 列混入数字、InvoiceNo 被识别为数值等问题，"
     "统一为字符串并去除首尾空格；日期列转为 datetime 后派生年、月、周、日、星期、小时六个时间维度，"
     "为“月度趋势—星期节律—小时分布”的三级下钻提供支撑；金额指标派生 Revenue = Quantity × UnitPrice，"
     "并明确全篇口径：销售额均指“已剔除退货、邮费与游客订单后的含税成交额”。")

heading(doc, "3.3　数据整合（多表关联逻辑、抽样方法与随机种子）", 2)
para(doc,
     f"整合后得到 {CLEAN['orders']:,} 张订单、{CLEAN['customers']:,} 位客户、{CLEAN['skus']:,} 个 SKU 与 "
     f"{CLEAN['countries']} 个市场，主外键一致性校验（客户表与商品表主键唯一、明细外键全部可匹配）通过。"
     "由于清洗后仍有 39 万行、远超“不少于 500 条”的要求，本文未做抽样，全部模型均基于全量数据计算，"
     "因此不存在随机种子问题；仅在关联规则中因购物篮矩阵规模限制，将商品限定为支持度不低于 1% 的 680 个"
     "高频 SKU，这一筛选同样以支持度阈值而非随机抽样实现，可完全复现。")

# ================================================================== 4 模型
heading(doc, "4　商业分析模型")

heading(doc, "4.1　模型选型（≥3 种）", 2)
para(doc,
     "课程要求至少选择 3 种模型，本文选择 6 种，覆盖“结构与价值”“用户与客群”“关联与转化”“预测与预警”"
     "四类，并保证每种模型都产出至少一张核心图与一条可验证结论。选型遵循“业务问题—数据条件—模型能力”"
     "三者匹配的原则：客户维度有标识与时间戳，适合 RFM 与同期群；订单×商品矩阵稠密，适合 Apriori；"
     "日销售额具备 374 个观测，适合带周季节项的 SARIMA；金额分布长尾，适合帕累托/ABC；商品有份额与增速，"
     "适合波士顿矩阵。")
table(doc, ["#", "模型", "回答的业务问题", "核心产出"],
      [["M1", "RFM 八分类", "谁贡献了收入，客户价值如何分层", "分群结构表、RFM 气泡散点图"],
       ["M2", "同期群留存", "新客在首购后第几个月流失最快", "13×12 留存热力图"],
       ["M3", "Apriori 关联规则", "哪些商品被稳定地一起购买", "规则表、规则气泡图"],
       ["M4", "SARIMA 预测", "未来 4 周销售额落在什么区间", "预测曲线 + 95% 置信区间"],
       ["M5", "帕累托 / ABC", "多少客户（商品）贡献 80% 销售额", "帕累托图、ABC 分层表"],
       ["M6", "波士顿矩阵", "哪些商品该加投、维持、淘汰", "四象限气泡图"]],
      cap="表 3　六个模型与业务问题的对应关系", widths=[1.2, 3.8, 6.4, 5.0], font=9)

heading(doc, "4.2　参数与阈值设定依据", 2)
para(doc,
     f"（1）RFM 的中位数切分。R、F、M 三个指标均呈明显右偏：销售额前 10% 的客户贡献了 60.3% 的销售额，"
     f"若用均值切分，绝大多数客户会被判为“低价值”，分层失去意义。中位数对极端值稳健，且能保证高低两组"
     f"人数各半，符合课程要求的“八分类”均衡性。本次切分结果为 R = {R['rfm']['thresholds']['R_median_days']:.0f} 天、"
     f"F = {R['rfm']['thresholds']['F_median']:.0f} 次、M = {R['rfm']['thresholds']['M_median']:.0f} 英镑；"
     f"方向上也做了业务化处理——R 越小代表越近，故“R 高”定义为 R ≤ 中位数。")
para(doc,
     "（2）Apriori 的三重阈值。最小支持度取 1%（约 154 张订单），低于该值的规则在 1.5 万张购物篮中"
     "一年只出现数十次，备货与陈列价值有限；最小提升度取 1.2，排除“本来就很畅销所以经常同时出现”的伪关联；"
     "最小置信度取 0.3，保证后项在 30% 以上的前项订单中真的出现；同时要求规则覆盖订单数不少于 15 张，"
     "避免长尾噪声规则进入结论。")
para(doc,
     "（3）SARIMA 的粒度与阶数。数据仅覆盖 13 个完整月份，月度序列不足以估计 12 阶季节项，"
     "因此改用日粒度（374 天）并将季节周期设为 7，以刻画“周六歇业、周四峰值”的周内节律；"
     "差分阶数 d=1、D=1 用于消除趋势与周季节，p、q 与 P、Q 通过 AIC 比较确定，"
     "最终选定 SARIMA(1,1,1)(0,1,1,7)，AIC 为 1259.7。为稳定方差，建模在 log(1+y) 空间进行，"
     "预测值再指数还原。")
para(doc,
     "（4）帕累托与 ABC 的分界。按累计销售额 70% / 90% 切分为 A / B / C 三层，这是库存管理的通行口径；"
     "波士顿矩阵的分割线取“份额中位数 + 零增长”，前者对应组合内部的中位水平，后者对应“下半年是否跑赢上半年”。")

heading(doc, "4.3　模型计算与验证", 2)

para(doc,
     f"RFM 结果显示（表 4），重要价值客户共 {R['rfm']['segments'][0]['客户数']:,} 人、占客户总数 "
     f"{R['rfm']['vip_share']*100:.1f}%，却贡献了 {R['rfm']['vip_rev_share']*100:.1f}% 的销售额，"
     f"人均消费约 {R['rfm']['segments'][0]['销售额']/R['rfm']['segments'][0]['客户数']:,.0f} 英镑；"
     f"而一般挽留客户人数占 23.5%，销售额占比仅 3.0%，是典型的“高人数、低价值”群体。"
     f"两类人群的错配，构成了后文分层运营建议的直接依据。")
seg_rows = []
for s in R["rfm"]["segments"]:
    seg_rows.append([s["Segment"], f"{s['客户数']:,}", f"{s['客户占比']*100:.1f}%",
                     f"{s['销售额']/1e4:,.1f}", f"{s['销售额占比']*100:.1f}%",
                     f"{s['平均R']:.0f}", f"{s['平均F']:.1f}"])
table(doc, ["客户分群", "客户数", "人数占比", "销售额(万)", "销售额占比", "平均R(天)", "平均F(次)"],
      seg_rows, cap="表 4　RFM 八分群结构（M 中位数 661 英镑）",
      widths=[3.3, 1.8, 1.9, 2.3, 2.3, 2.0, 2.3], font=9)
figure(doc, "fig16_RFM气泡散点图.png", "图 1　RFM 客户分布：R×F 平面上的价值分层（气泡面积＝累计消费金额）")
figure(doc, "fig17_八分群价值对比.png", "图 2　八类客户的人数占比与销售额占比错配")

para(doc,
     f"同期群分析按首购月把客户分为 {R['cohort']['cohorts']} 个群，追踪其后 12 个月的活跃率。"
     f"结果显示次月留存平均仅 {R['cohort']['avg_m1_retention']*100:.1f}%，到第 11 个月降至 "
     f"{R['cohort']['avg_m11_retention']*100:.1f}%，首月之后的“断崖”集中在第 1—2 个月，"
     f"说明挽回动作的窗口应当前移到首购后的 30 天内，而不是等到季度末。")
figure(doc, "fig18_同期群留存热力图.png", "图 3　同期群留存热力图（行＝首购月，列＝距首购的月数）")

para(doc,
     f"关联规则在英国市场 {R['rules']['baskets']:,} 张多品订单上运行，得到 {R['rules']['n_rules']} 条满足约束的规则。"
     f"提升度最高的一组集中在“HERB MARKER（香草标记牌）”系列商品上（提升度 {R['rules']['max_lift']:.1f}），"
     f"即三款香味标记牌经常被同一笔订单一次性买齐；覆盖订单数最多的一组则是“REGENCY TEACUP”系列茶具"
     f"（单一规则覆盖 476 张订单），说明该系列存在稳定的成套购买行为。这两类商品都适合做成组合装而非单品促销。")
figure(doc, "fig21_关联规则气泡图.png", "图 4　关联规则气泡图（横轴＝覆盖订单数，纵轴＝提升度，气泡＝置信度）")

para(doc,
     f"SARIMA 在末 56 天上的回测结果为 MAPE {R['sarima']['mape']:.1f}%、RMSE {R['sarima']['rmse']:,.0f} 英镑、"
     f"sMAPE {R['sarima']['smape']:.1f}%；作为对照的季节朴素法（取上周同一天）MAPE 为 {R['sarima']['naive_mape']:.1f}%，"
     f"即纯时序模型并未战胜朴素基准，预测总量偏低约 {abs(R['sarima']['bias_pct']):.0f}%。这一结果并不意外："
     f"回测窗恰好覆盖 11—12 月的圣诞备货高峰，销售额在四周内近乎翻倍，而 SARIMA 的均值回复特性使其倾向于"
     f"低估这种由促销日历驱动的脉冲。该发现的价值在于明确了模型的适用边界——它适合给出“无促销干预下的"
     f"基线区间”，而不能替代促销计划的量化；改进方向是把促销日历、节假日作为外生变量引入 SARIMAX。")
figure(doc, "fig22_SARIMA预测图.png", "图 5　SARIMA 日销售额预测与 95% 置信区间（含 56 天回测段）")

para(doc,
     f"帕累托与 ABC 给出了收入集中度的量化答案：仅 {R['pareto']['share_of_customers_for_80pct']*100:.1f}% 的客户"
     f"（{R['pareto']['customers_for_80pct']:,} 人）贡献 80% 销售额，前 1% 客户贡献 "
     f"{R['pareto']['top1pct_share']*100:.1f}%，前 10% 贡献 {R['pareto']['top10pct_share']*100:.1f}%；"
     f"商品侧同样集中，{R['pareto']['sku_A_count']} 个 A 类 SKU 贡献了 {R['pareto']['sku_A_share']*100:.1f}% 的销售额。")
figure(doc, "fig19_帕累托图.png", "图 6　客户帕累托图：26.8% 的客户贡献 80% 销售额")

para(doc,
     f"波士顿矩阵对 59 个主力 SKU 做了份额—增速定位：明星类 17 个，合计销售额占比 "
     f"{R['bdc']['star_share']*100:.1f}%；金牛类 13 个（高份额、低增速），是现金流来源；问题类 20 个增速快但份额低，"
     f"需要判断是否值得投入；瘦狗类 9 个应当逐步压缩陈列与库存。")
figure(doc, "fig20_波士顿矩阵.png", "图 7　商品波士顿矩阵：份额 × 增速四象限")

# ================================================================== 5 可视化
heading(doc, "5　Python 数据分析与可视化")

heading(doc, "5.1　数据探索性分析", 2)
para(doc,
     f"从时间维度看，销售额呈显著的“年末爬坡”：2011 年 11 月达到峰值 {R['trend']['best_month_revenue']/1e4:,.1f} 万英镑，"
     f"为月均 {R['trend']['avg_monthly']/1e4:,.1f} 万的 1.7 倍；12 月因数据仅覆盖 9 天而显著偏低，分析时须单独标注，"
     f"不能误读为“12 月销售崩塌”。从星期维度看，周四为峰值、周六完全歇业，说明这是一家以工作日发货为主的"
     f"批发型零售商；从小时维度看，下单集中在 10—14 点，12 点为峰值，与欧洲买手的工作节奏吻合。"
     f"从市场结构看，英国本土贡献 {R['trend']['uk_share']*100:.1f}% 的销售额，其余 36 个市场合计不足 18%，"
     f"呈现“单一大本营 + 长尾出口”的格局；平均客单价 {R['trend']['avg_order_value']:,.0f} 英镑、"
     f"单笔 21.3 个商品行，进一步印证其批发属性。")
figure(doc, "fig01_渐变柱形图_月度销售额.png", "图 8　月度销售额（渐变柱形图）")
figure(doc, "fig08_平滑折线图_日销售额.png", "图 9　日销售额与 7 个营业日移动平均")
figure(doc, "fig15_柱形折线图_销售额与订单.png", "图 10　月度销售额与订单量：量价齐升还是单价驱动")
figure(doc, "fig10_对比折线图_新老客.png", "图 11　新客首购与老客复购的月度销售额对比")

heading(doc, "5.2　可视化模板复现（对照《Excel数据可视化》≥10 种）", 2)
para(doc,
     "教材第 2 章把图表分为柱形/条形、折线、圆饼/圆环、组合四类共 30 个模板。本文复现其中 15 种，"
     "在图表类型、布局结构、配色方案、标签样式、图例位置与标题设计六个维度上尽量贴近原作，"
     "同时用 Matplotlib 的底层图元解决 Excel 中最具辨识度的几类“手工效果”：用 imshow 的渐变矩阵"
     "裁剪出渐变色柱体；用 FancyBboxPatch 的圆角矩形复现圆角柱；用 axhline 加白底标注实现平均线；"
     "用极坐标柱状图实现南丁格尔玫瑰；用带缺口的 Wedge 实现玉玦图；用 fill_between 加圆形裁剪"
     "模拟水球图的液面。配色统一采用 Office 主题色（#4472C4、#ED7D31、#A5A5A5、#FFC000 等），"
     "这是“贴近原作”的关键细节——Excel 默认图表即为该套色板。")
table(doc, ["#", "复现模板", "本文数据载体", "关键还原手法"],
      [["1", "渐变柱形图", "月度销售额", "imshow 垂直渐变 + 柱体裁剪"],
       ["2", "带平均线柱形图", "海外市场 TOP10", "axhline + 白底文字标注"],
       ["3", "渐变圆角柱形图", "TOP10 商品", "FancyBboxPatch 圆角 + 渐变裁剪"],
       ["4", "层叠柱形图(100%)", "季度客户结构", "累计 bottom 堆叠 + 段内百分比"],
       ["5", "蝴蝶图", "上下半年市场对比", "左右对称 barh + 绝对值刻度"],
       ["6", "数值百分比条形图", "国家销售额占比", "条形末端双标签（占比+绝对值）"],
       ["7", "甘特图", "TOP12 客户生命周期", "barh(left=首购, width=跨度)"],
       ["8", "平滑折线图", "日销售额", "7 期移动平均 + 面积填充"],
       ["9", "菱形走势图", "周销售额", "marker='D' + vlines 引线"],
       ["10", "对比折线图", "新客 vs 老客", "双序列 + 分色面积"],
       ["11", "单值圆环图", "年度目标完成率", "wedgeprops 环宽 + 中心大字"],
       ["12", "南丁格尔玫瑰图", "海外市场", "极坐标 bar + 角度刻度"],
       ["13", "玉玦图", "八分群销售额占比", "带缺口 Wedge + 外侧图例"],
       ["14", "水球图", "老客复购率", "正弦波面 + 圆形裁剪"],
       ["15", "柱形折线图", "销售额+订单量", "twinx 双轴 + 图例合并"]],
      cap="表 5　15 种模板的复现清单与实现要点", widths=[1.0, 4.0, 4.4, 6.4], font=9)
figure(doc, "fig02_带平均线柱形图_海外市场TOP10.png", "图 12　带平均线柱形图：海外市场 TOP10")
figure(doc, "fig03_渐变圆角柱形图_TOP10商品.png", "图 13　渐变圆角柱形图：销售额 TOP10 商品")
figure(doc, "fig04_层叠柱形图_季度客户结构.png", "图 14　层叠柱形图（100%）：季度销售额的客户结构")
figure(doc, "fig07_甘特图_客户生命周期.png", "图 15　甘特图：TOP12 客户的采购生命周期")
para(doc,
     "与 Excel 实现相比，Python 版本的差异主要体现在三处：一是版式可编程，同一套样式函数可复用到 23 张图，"
     "不存在手工对齐误差；二是数据与图层分离，改一个阈值即可整批重绘；三是可嵌入真实统计对象，"
     "例如甘特图的颜色直接取自 RFM 分群、玫瑰图的角度与半径由数据排序决定，而 Excel 版本通常需要手工摆位。"
     "劣势在于“所见即所得”的拖拽体验缺失，单张图的试错成本高于 Excel，这要求把样式抽象成函数一次性调好。")
figure(doc, "fig05_蝴蝶图_上下半年对比.png", "图 16　蝴蝶图：主要海外市场上半年 vs 下半年")
figure(doc, "fig06_数值百分比条形图_国家占比.png", "图 17　数值百分比条形图：国家销售额占比")
figure(doc, "fig09_菱形走势图_周销售额.png", "图 18　菱形走势图：周销售额")
figure(doc, "fig12_南丁格尔玫瑰图_国家.png", "图 19　南丁格尔玫瑰图：TOP12 海外市场")
figure(doc, "fig13_玉玦图_客户分群占比.png", "图 20　玉玦图：RFM 八分群销售额占比")
figure(doc, "fig14_水球图_复购率.png", "图 21　水球图：老客复购率 65.3%")
figure(doc, "fig11_单值圆环图_目标完成率.png", "图 22　单值圆环图：年度目标完成率 94.4%")

heading(doc, "5.3　业务模型图（≥6 张）", 2)
para(doc,
     "第 4 章的六个模型各自对应一张核心业务图：RFM 气泡散点图（图 1）、八分群价值对比图（图 2）、"
     "同期群留存热力图（图 3）、关联规则气泡图（图 4）、SARIMA 预测图（图 5）、帕累托图（图 6）"
     "与波士顿矩阵（图 7），共 7 张，超过“≥6 张”的要求，且每张图都与一条可检验的商业结论绑定。"
     "此外补充了 ABC 分层对比图以衔接帕累托结论。")
figure(doc, "fig23_ABC分层对比.png", "图 23　ABC 分层：A 类客户以 16.5% 的人数贡献 70.0% 销售额")

heading(doc, "5.4　交互式可视化大屏", 2)
para(doc,
     "大屏采用双实现：一份是基于 Pyecharts 的静态大屏（dashboard.html，1920×1080 深色主题，"
     "可直接双击打开、断网可用），另一份是基于 Streamlit 的交互应用（app.py），两者共用同一批清洗后数据。"
     "Pyecharts 版本包含 4 个 KPI 卡、月度趋势双轴图、世界地图、海外市场条形图、RFM 环形图、"
     "星期分布柱状图、TOP10 商品柱状图与关联规则明细表，共 10 个组件；Streamlit 版本在同样的组件基础上"
     "增加了 4 个筛选器（市场、日期区间、客户分层、客单价区间），筛选条件会同时驱动 KPI 卡、趋势图、"
     "结构图、热力图、帕累托曲线与明细表刷新，实现真正的联动与下钻。全部图表由 Python 生成，"
     "未使用 Power BI、Tableau、Fine BI 等任何 BI 软件。")
if (ROOT / "outputs" / "dashboard" / "dashboard_preview.png").exists():
    figure(doc, "../../outputs/dashboard/dashboard_preview.png", "图 24　Pyecharts 数据大屏（1920×1080 深色主题）", width=6.3)

# ================================================================== 6 案例
heading(doc, "6　商业案例分析")

heading(doc, "6.1　案例背景", 2)
para(doc,
     "该商家是一家注册于英国的在线零售商，主营礼品、家居装饰、厨房用具与派对用品，客户以中小批发商、"
     "礼品店主与少量个人买家为主。经营的典型特征是“旺季极短、单笔金额大、客户重复采购但节奏不稳定”："
     "11 月的销售额是月均水平的 1.7 倍，而单笔订单平均包含 21 个商品行，说明客户多为一次性补货。"
     "在这种模式下，客户关系的维护比拉新更划算——获取一位新批发客户的成本远高于让一位老客户提前一个月下单。")

heading(doc, "6.2　结果解读", 2)
para(doc,
     f"第一，收入高度集中且集中在“近期活跃”的人群。重要价值客户（R、F、M 均高于中位数）仅占 "
     f"{R['rfm']['vip_share']*100:.1f}% 的人数，却贡献 {R['rfm']['vip_rev_share']*100:.1f}% 的销售额，"
     f"其平均购买频次为 8.8 次、平均最近购买仅 17 天。这意味着该商家的收入并不依赖“广撒网”，"
     f"而是依赖约 1400 位批发客户的持续补货。")
para(doc,
     f"第二，客户在首购后的第一个月内大量流失。次月平均留存 {R['cohort']['avg_m1_retention']*100:.1f}%，"
     f"第 11 个月仅 {R['cohort']['avg_m11_retention']*100:.1f}%。结合 RFM 中“一般挽留客户”人数占比高达 23.5%，"
     f"可以判断：大量客户只在一次促销或一次补货中成交，未形成稳定采购节奏。")
para(doc,
     "第三，商品之间存在明确的成套购买结构。香草标记牌系列三款商品的提升度高达 81.7，"
     "茶具系列单条规则覆盖 476 张订单，说明客户的真实需求是“成套购买”而非“单件选购”，"
     "这与该商家经营礼品、派对用品的定位一致。")
para(doc,
     "第四，销售节律稳定但预测受促销脉冲干扰。星期四为每周峰值、12 点为每日峰值，"
     "这类节律可以支撑排班与发货计划；但 11—12 月的促销爬坡无法被纯时序模型捕捉（MAPE 35.4%，"
     "略逊于季节朴素法的 31.6%），说明该商家的销售额更大程度由“促销日历”而非“自然趋势”驱动。")

heading(doc, "6.3　商业建议（5 条，可操作、有数据支撑）", 2)
para(doc,
     f"（1）对重要价值客户做“账期 + 专属补货提醒”而非打折。这类客户 {R['rfm']['segments'][0]['客户数']:,} 人、"
     f"贡献 {R['rfm']['vip_rev_share']*100:.1f}% 销售额，价格敏感度低而对断货、账期敏感。"
     f"建议为其配置 30 天账期与 SKU 级缺货预警，并在其历史补货周期（平均 8.8 次/年，约每 6 周一次）"
     f"前 7 天推送补货清单。按该群体人均年贡献 "
     f"{R['rfm']['segments'][0]['销售额']/R['rfm']['segments'][0]['客户数']:,.0f} 英镑测算，"
     f"补货频次每提升 5%，约可带来 32 万英镑增量。")
para(doc,
     f"（2）把挽回窗口前移到首购后 30 天。当前次月留存仅 {R['cohort']['avg_m1_retention']*100:.1f}%，"
     f"若通过“首购后第 14 天发送关联商品推荐 + 第 25 天发送限时复购券”把次月留存提升到 25%，"
     f"按平均客户年贡献 1,959 英镑估算，留存率每提升 1 个百分点约带来 8.5 万英镑年增量，"
     f"6 个百分点对应约 51 万英镑。该动作的边际成本仅为邮件与优惠券，投入产出比高于大规模拉新。")
para(doc,
     "（3）把高提升度商品做成组合装。香草标记牌三件套（提升度 81.7）与 Regency 茶具系列"
     "（单规则覆盖 476 张订单）应改为“组合 SKU”上架，并在详情页互相导流；组合装还能降低拣货行数，"
     "缓解单笔 21 个商品行带来的仓储作业压力。")
para(doc,
     "（4）按“周四峰值 + 11 月峰值”重排备货与人力。备货节奏应在 10 月中旬前完成圣诞品类入库，"
     "客服与仓配排班向周四、每日 10—14 点倾斜；由于周六歇业，周五下午应完成下周初订单的预打包。"
     f"结合 SARIMA 给出的未来 28 天基线区间（合计约 {R['sarima']['forecast_sum_28d']/1e4:.1f} 万英镑），"
     "可将其作为“无促销情形”的库存下限，再叠加促销计划作为上限。")
para(doc,
     f"（5）把游客订单转化为可运营的客户资产。清洗中发现 {CLEAN['guest_rows']:,} 行交易没有客户标识，"
     f"对应约 150.96 万英镑销售额（约占总销售额的 15%）。建议在下单流程中增加“注册即享首单 95 折”，"
     f"把匿名交易比例压到 5% 以下；即便只转化其中三分之一，也能让客户级模型多覆盖约 5% 的收入，"
     f"使后续 RFM 分层与留存分析更接近真实。")

# ================================================================== 7 结论
heading(doc, "7　结论与展望")

heading(doc, "7.1　研究结论", 2)
para(doc,
     "本文以一份 54 万行的真实在线零售流水为对象，完成了从合规获取、十步清洗、六模型建模到"
     "23 张图表与双大屏呈现的端到端分析。主要结论有四：其一，收入高度集中于少数近期活跃的批发客户，"
     "26.8% 的客户贡献 80% 销售额；其二，客户留存的最大断点出现在首购后第一个月，次月留存仅 18.9%；"
     "其三，商品存在稳定的成套购买结构，成套化陈列与组合定价的空间明确；其四，销售节律由星期与促销日历"
     "共同驱动，纯时序模型只能刻画基线、无法替代促销计划。")

heading(doc, "7.2　局限性与展望", 2)
para(doc,
     "本文的局限主要有四：一是时间跨度仅 13 个月，且末月只有 9 天数据，无法做严格的同比分析，"
     "月度季节项也无法估计；二是数据不含成本与毛利，所有“价值”均以销售额衡量，未能识别“高销售额、低毛利”的"
     "伪优质客户；三是约 15% 的销售额缺少客户标识，客户级模型存在系统性低估；四是促销活动未被标注，"
     "导致 SARIMA 在圣诞窗口出现明显低估（偏差约 -23%）。后续可将成本表、促销日历作为外生变量接入 "
     "SARIMAX，或改用 Prophet 等支持节假日效应的模型，并把 RFM 与 K-Means 结合做更细的分群。")

heading(doc, "7.3　AI 使用披露", 2)
para(doc,
     "本文在以下环节使用了 AI 编程助手（DeepSeek / ChatGPT 类大模型）：① 生成脚本骨架与 matplotlib "
     "样式函数，再逐图人工调参与核对；② 排查环境依赖与编码问题；③ 对论文初稿的语句做学术化润色。"
     "关键提示词示例：“用 matplotlib 复现 Excel 的渐变柱形图，柱体自上而下渐变，颜色取 Office 主题蓝"
     "（#9DC3E6 → #2F5597），并在柱顶标注数值”“对日销售额序列做 SARIMA 建模，季节周期 7，"
     "输出 56 天回测的 MAPE 与 RMSE 并画出 95% 置信区间”。所有数据结论均由脚本计算得出并人工复核，"
     "AI 未参与数据生成或结果篡改。")

# ================================================================== 参考文献
heading(doc, "参考文献")
refs = [
    "[1] 郭宏远. Excel 数据可视化——从图表到数据大屏[M]. 北京: 清华大学出版社, 2023.",
    "[2] Chen D. Online Retail Data Set[DB/OL]. UCI Machine Learning Repository, 2015. https://archive.ics.uci.edu/dataset/352/online+retail.",
    "[3] Hughes A M. Strategic Database Marketing[M]. Chicago: Probus Publishing, 1994.",
    "[4] Agrawal R, Srikant R. Fast Algorithms for Mining Association Rules[C]// Proceedings of the 20th VLDB Conference. 1994: 487-499.",
    "[5] Hyndman R J, Athanasopoulos G. Forecasting: Principles and Practice[M]. 3rd ed. Melbourne: OTexts, 2021.",
    "[6] McKinney W. Python for Data Analysis[M]. 3rd ed. Sebastopol: O'Reilly Media, 2022.",
    "[7] Raschka S. MLxtend: Providing machine learning and data science utilities and extensions to Python's scientific computing stack[J]. Journal of Open Source Software, 2018, 3(24): 638.",
    "[8] 贾俊平, 何晓群, 金勇进. 统计学[M]. 8版. 北京: 中国人民大学出版社, 2021.",
]
for r in refs:
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.left_indent = Cm(0.75)
    p.paragraph_format.first_line_indent = Cm(-0.75)
    set_font(p.add_run(r), "宋体", 10.5)

# ================================================================== 附录
doc.add_page_break()
heading(doc, "附录")
heading(doc, "A　核心代码片段", 2)
code = """# 03_analysis.py —— RFM 八分类核心逻辑
REF_DATE = pd.Timestamp("2011-12-10")   # 数据最后一天的次日
rfm = (tx.groupby("CustomerID")
         .agg(R=("InvoiceDate",
                 lambda s: (REF_DATE - s.max()).days),
              F=("InvoiceNo", "nunique"),
              M=("Revenue", "sum"))
         .reset_index())
r_med = rfm["R"].median()
f_med = rfm["F"].median()
m_med = rfm["M"].median()
rfm["R_high"] = rfm["R"] <= r_med       # R 越小越近
rfm["F_high"] = rfm["F"] >= f_med
rfm["M_high"] = rfm["M"] >= m_med
# 8 种组合 -> 八分群名（重要/一般 × 价值/发展/保持/挽留）"""
for line in code.split("\n"):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.left_indent = Cm(0.5)
    set_font(p.add_run(line if line else " "), "Consolas", 8.5)

heading(doc, "B　Gitee/GitHub 仓库链接与目录结构", 2)
para(doc, "仓库地址：https://github.com/<your-name>/online-retail-analysis（提交前替换为公开链接）", indent_chars=0)
tree = """repo/
├── data/raw/          原始数据与 source_meta.json
├── data/clean/        清洗后四表 + schema + SQLite
├── scripts/           01_load ~ 05_dashboard + common.py
├── outputs/figures/   23 张 PNG + 图表索引.csv
├── outputs/tables/    20 张结果表 + analysis_results.json
├── outputs/dashboard/ dashboard.html（离线可开）
├── docs/              论文 docx/pdf、合规声明、build_paper.py
├── app.py             Streamlit 交互式仪表板
├── requirements.txt   依赖清单
├── run_all.py         一键复现入口
└── README.md          项目说明、复现步骤、图表索引"""
for line in tree.split("\n"):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.left_indent = Cm(0.5)
    set_font(p.add_run(line), "Consolas", 8.5)

heading(doc, "C　图表索引（fig01–fig23）", 2)
idx = pd.read_csv(FIG / "图表索引.csv")
table(doc, ["编号", "图表名称", "对应模板/模型"],
      [[r["编号"], r["图表名称"], r["对应模板/模型"]] for _, r in idx.iterrows()],
      widths=[1.6, 8.0, 6.2], font=9)

out = DOCS / "期末大论文_基于在线零售数据的用户价值与复购洞察.docx"
doc.save(out)
print("saved:", out)
