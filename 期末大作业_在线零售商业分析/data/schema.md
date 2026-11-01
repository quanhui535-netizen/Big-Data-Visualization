# 数据字典与口径说明

## 一、原始字段（data/raw/online_retail.xlsx）

| 字段 | 类型 | 说明 |
|---|---|---|
| InvoiceNo | string | 订单号；以 `C` 开头表示取消/退货单 |
| StockCode | string | 商品编码，5 位数字 + 可选字母后缀；`POST`/`DOT`/`M`/`BANK CHARGES` 等为非商品行 |
| Description | string | 商品名称（英文） |
| Quantity | int | 成交数量；负数表示退货 |
| InvoiceDate | datetime | 下单时间，精确到分钟 |
| UnitPrice | float | 单价（英镑） |
| CustomerID | float/int | 客户编号；约 25% 行为空 |
| Country | string | 客户所在国家 |

## 二、清洗后表结构（data/clean/）

### transactions.parquet / transactions.csv（明细表，391,148 行）

| 字段 | 说明 |
|---|---|
| InvoiceNo / StockCode / Description / Country | 同上（已统一为字符串并去空格） |
| Quantity / UnitPrice | 同上 |
| CustomerID | 已转为整数，无缺失 |
| InvoiceDate | datetime |
| Revenue | `Quantity × UnitPrice`（英镑） |
| Year / Month / Week / Date | 年、月（`YYYY-MM`）、周（`YYYY-MM-DD/…`）、日期 |
| DOW / Hour | 星期（0=周一）、下单小时 |
| IsReturn | 标识位，主表恒为 False（退货已单独拆出） |

### orders.csv（订单表，18,400 行，主键 InvoiceNo）

`CustomerID, InvoiceDate, Country, Items（SKU 数）, Quantity（件数）, Revenue（金额）`

### customers.csv（客户表，4,333 行，主键 CustomerID）

`FirstOrder, LastOrder, Orders（订单数）, Items（件数）, SKUs（品类数）, Revenue, Country`

### products.csv（商品表，3,658 行，主键 StockCode）

`Description, Orders, Quantity, Revenue, Customers`

### countries.csv（市场表，37 行）

`Orders, Customers, Revenue`

### cancellations.csv（取消单，9,251 行）

单独存放，用于观察退货规模，不进入销售口径。

## 三、口径约定

1. **销售额**：含税成交额，已剔除退货、邮费/手续费、游客订单与极端值。
2. **有效客户**：在清洗后数据中出现过至少一次交易的 CustomerID。
3. **客户价值**：以累计销售额（M）衡量；因数据不含成本，未计算毛利。
4. **时间基准**：RFM 的 Recency 以数据最后一天（2011-12-09）的次日 2011-12-10 为参照。
5. **留存定义**：客户在首购月之后的某月有任一交易，即视为该月留存。
6. **多表关系**：transactions.CustomerID → customers.CustomerID；
   transactions.InvoiceNo → orders.InvoiceNo；transactions.StockCode → products.StockCode。
   主外键一致性在 `02_clean.py` 中自动校验并写入 `clean_report.json` 的 `fk_check` 字段。

## 四、清洗日志

完整的十步清洗计数见 `data/clean/clean_report.json`（含每步处理前后行数与说明）。
