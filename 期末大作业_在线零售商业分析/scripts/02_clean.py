"""02_clean.py —— 数据清洗与治理

治理步骤（每一步都计数并写入 clean_report.json，便于论文复述）：
  1  类型统一（InvoiceNo/StockCode/Description/Country -> string，日期 -> datetime）
  2  重复值去除
  3  取消单（InvoiceNo 以 C 开头）拆分到 cancellations
  4  非商品行剔除（邮费/手工调整/银行费用等 StockCode 非商品编码）
  5  负数量、零/负单价剔除
  6  客户标识缺失拆分（guest 交易仅用于销售额口径，不进入客户级分析）
  7  极端值识别（单价 > 1000 英镑、数量 > 10000 的批发调整行）
  8  指标派生（Revenue、年/月/周/星期/小时、是否退货）
  9  多表对齐（订单表 / 客户表 / 商品表 / 国家表，主外键一致）
 10  导出 CSV / Parquet / SQLite
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_CLEAN, DATA_RAW, dump_json  # noqa: E402

RAW = DATA_RAW / "online_retail.parquet"
REPORT = DATA_CLEAN / "clean_report.json"
STEPS: list[dict] = []


def log(step: str, before: int, after: int, note: str = "") -> None:
    STEPS.append({"step": step, "rows_before": before, "rows_after": after,
                  "removed": before - after, "note": note})
    print(f"  {step:38s} {before:>8,} -> {after:>8,}  (-{before-after:,}) {note}")


def main() -> None:
    print("=" * 78)
    print("02_clean —— 数据清洗与治理")
    print("=" * 78)
    df = pd.read_parquet(RAW)
    n0 = len(df)
    print(f"[clean] 原始 {n0:,} 行")
    print(f"[clean] 缺失：CustomerID {df['CustomerID'].isna().sum():,} / "
          f"Description {df['Description'].isna().sum():,} / "
          f"重复行 {df.duplicated().sum():,}")

    # ---- 1 类型统一 -------------------------------------------------------
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["InvoiceNo"] = df["InvoiceNo"].str.strip()
    df["StockCode"] = df["StockCode"].str.strip().str.upper()
    df["Country"] = df["Country"].str.strip()
    before = len(df)
    log("1 类型与日期格式统一", before, len(df))

    # ---- 2 重复值 ---------------------------------------------------------
    before = len(df)
    df = df.drop_duplicates().copy()
    log("2 完全重复记录去除", before, len(df))

    # ---- 3 取消单 ---------------------------------------------------------
    before = len(df)
    cancel_mask = df["InvoiceNo"].str.startswith("C", na=False)
    cancels = df[cancel_mask].copy()
    df = df[~cancel_mask].copy()
    log("3 取消单拆分", before, len(df), f"取消单 {len(cancels):,} 行")

    # ---- 4 非商品行 -------------------------------------------------------
    before = len(df)
    product_code = re.compile(r"^\d{5}[A-Z]{0,2}$")
    is_product = df["StockCode"].astype(str).str.match(product_code)
    non_product = df[~is_product]
    df = df[is_product].copy()
    log("4 非商品行剔除（邮费/调整/费用）", before, len(df),
        f"剔除 {len(non_product):,} 行，如 {sorted(set(non_product['StockCode'].head(50)))[:5]}")

    # ---- 5 负数量 / 非正单价 ---------------------------------------------
    before = len(df)
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)].copy()
    log("5 负数量与零/负单价剔除", before, len(df))

    # ---- 6 客户标识缺失 ---------------------------------------------------
    before = len(df)
    guest = df[df["CustomerID"].isna()].copy()
    df = df[df["CustomerID"].notna()].copy()
    df["CustomerID"] = df["CustomerID"].astype(int)
    log("6 客户标识缺失拆分", before, len(df),
        f"游客交易 {len(guest):,} 行（{guest['Quantity'].mul(guest['UnitPrice']).sum():,.0f} 英镑）")

    # ---- 7 极端值 ---------------------------------------------------------
    before = len(df)
    q_price = df["UnitPrice"].quantile(0.999)
    price_out = df["UnitPrice"] > 1000
    qty_out = df["Quantity"] > 10000
    df = df[~(price_out | qty_out)].copy()
    log("7 极端值识别与剔除", before, len(df),
        f"单价>1000 ({price_out.sum()} 行) / 数量>10000 ({qty_out.sum()} 行)；P99.9 单价={q_price:.1f}")

    # ---- 8 指标派生 -------------------------------------------------------
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    df["Year"] = df["InvoiceDate"].dt.year
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    df["Week"] = df["InvoiceDate"].dt.to_period("W").astype(str)
    df["Date"] = df["InvoiceDate"].dt.normalize()
    df["DOW"] = df["InvoiceDate"].dt.dayofweek
    df["Hour"] = df["InvoiceDate"].dt.hour
    df["IsReturn"] = False
    cancels = cancels[(cancels["Quantity"] != 0)]
    cancels["Revenue"] = cancels["Quantity"] * cancels["UnitPrice"]

    print(f"[clean] 有效交易 {len(df):,} 行 / {df['InvoiceNo'].nunique():,} 张订单 / "
          f"{df['CustomerID'].nunique():,} 位客户 / {df['StockCode'].nunique():,} 个 SKU")

    # ---- 9 多表对齐 -------------------------------------------------------
    orders = (df.groupby("InvoiceNo")
                .agg(CustomerID=("CustomerID", "first"),
                     InvoiceDate=("InvoiceDate", "min"),
                     Country=("Country", "first"),
                     Items=("StockCode", "nunique"),
                     Quantity=("Quantity", "sum"),
                     Revenue=("Revenue", "sum"))
                .reset_index())
    customers = (df.groupby("CustomerID")
                   .agg(FirstOrder=("InvoiceDate", "min"),
                        LastOrder=("InvoiceDate", "max"),
                        Orders=("InvoiceNo", "nunique"),
                        Items=("Quantity", "sum"),
                        SKUs=("StockCode", "nunique"),
                        Revenue=("Revenue", "sum"),
                        Country=("Country", "first"))
                   .reset_index())
    products = (df.groupby("StockCode")
                  .agg(Orders=("InvoiceNo", "nunique"),
                       Quantity=("Quantity", "sum"),
                       Revenue=("Revenue", "sum"),
                       Customers=("CustomerID", "nunique"),
                       Description=("Description", "first"))
                  .reset_index()
                  .sort_values("Revenue", ascending=False))
    products = products[["StockCode", "Description", "Orders", "Quantity", "Revenue", "Customers"]]
    countries = (df.groupby("Country")
                   .agg(Orders=("InvoiceNo", "nunique"),
                        Customers=("CustomerID", "nunique"),
                        Revenue=("Revenue", "sum"))
                   .reset_index()
                   .sort_values("Revenue", ascending=False))

    # 主外键一致性自检
    fk_ok = (
        customers["CustomerID"].is_unique
        and products["StockCode"].is_unique
        and orders["InvoiceNo"].is_unique
        and df["CustomerID"].isin(customers["CustomerID"]).all()
        and df["InvoiceNo"].isin(orders["InvoiceNo"]).all()
    )
    print(f"[clean] 主外键对齐自检：{'通过' if fk_ok else '失败'}")

    # ---- 10 导出 ----------------------------------------------------------
    df.to_parquet(DATA_CLEAN / "transactions.parquet", index=False)
    df.to_csv(DATA_CLEAN / "transactions.csv", index=False, encoding="utf-8-sig")
    orders.to_csv(DATA_CLEAN / "orders.csv", index=False, encoding="utf-8-sig")
    customers.to_csv(DATA_CLEAN / "customers.csv", index=False, encoding="utf-8-sig")
    products.to_csv(DATA_CLEAN / "products.csv", index=False, encoding="utf-8-sig")
    countries.to_csv(DATA_CLEAN / "countries.csv", index=False, encoding="utf-8-sig")
    cancels[["InvoiceNo", "StockCode", "Quantity", "InvoiceDate", "UnitPrice", "Revenue", "CustomerID"]].to_csv(
        DATA_CLEAN / "cancellations.csv", index=False, encoding="utf-8-sig")

    import sqlite3
    db = DATA_CLEAN / "online_retail.db"
    with sqlite3.connect(db) as conn:
        df.to_sql("transactions", conn, if_exists="replace", index=False)
        orders.to_sql("orders", conn, if_exists="replace", index=False)
        customers.to_sql("customers", conn, if_exists="replace", index=False)
        products.to_sql("products", conn, if_exists="replace", index=False)
    print(f"[clean] 已导出 SQLite: {db.name}")

    report = {
        "raw_rows": n0,
        "clean_rows": int(len(df)),
        "keep_ratio": round(len(df) / n0, 4),
        "rows": int(len(df)),
        "orders": int(df["InvoiceNo"].nunique()),
        "customers": int(df["CustomerID"].nunique()),
        "skus": int(df["StockCode"].nunique()),
        "countries": int(df["Country"].nunique()),
        "revenue": round(float(df["Revenue"].sum()), 2),
        "date_min": str(df["InvoiceDate"].min()),
        "date_max": str(df["InvoiceDate"].max()),
        "cancelled_rows": int(len(cancels)),
        "guest_rows": int(len(guest)),
        "missing_customer_rows": int(guest.shape[0]),
        "duplicate_rows": int(n0 - len(pd.read_parquet(RAW).drop_duplicates())),
        "fk_check": bool(fk_ok),
        "steps": STEPS,
    }
    dump_json(report, "clean_report.json", DATA_CLEAN)
    print("[clean] 完成，报告 -> data/clean/clean_report.json")


if __name__ == "__main__":
    main()
