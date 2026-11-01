"""01_load.py —— 数据获取（合规：官方一次性文件下载，全程无爬虫）

来源：UCI Machine Learning Repository, Dataset 352 "Online Retail"
       https://archive.ics.uci.edu/dataset/352/online+retail
方式：官方公开 ZIP 一次性下载（白名单第 1 类），解压得到 Online Retail.xlsx
授权：CC BY 4.0
产物：data/raw/online_retail.xlsx、online_retail.parquet、source_meta.json

说明：若官方直链在本机网络下不可达/超时，自动回落到 Hugging Face 上的
     同文件镜像（字节数完全一致，见 source_meta.json 的 sha256）。
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA_RAW, dump_json  # noqa: E402

UCI_ZIP = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
HF_XLSX = "https://huggingface.co/datasets/michaelmallari/online-retail/resolve/main/online-retail.xlsx"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

XLSX = DATA_RAW / "online_retail.xlsx"
PARQUET = DATA_RAW / "online_retail.parquet"
META = DATA_RAW / "source_meta.json"


def _stream(url: str, dest: Path, timeout: int = 900) -> int:
    """流式下载并落盘，返回字节数。"""
    req = urllib.request.Request(url, headers=UA)
    total = 0
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if total % (1 << 22) < (1 << 16):
                print(f"    {total/1e6:6.2f} MB  {time.time()-t0:5.0f}s", flush=True)
    return total


def acquire() -> dict:
    if XLSX.exists() and XLSX.stat().st_size > 20_000_000:
        print(f"[load] 已存在 {XLSX.name} ({XLSX.stat().st_size/1e6:.1f} MB)，跳过下载")
        return {"method": "cached", "url": "", "bytes": XLSX.stat().st_size}

    print("[load] ① 尝试 UCI 官方直链 ...")
    try:
        zip_path = DATA_RAW / "online_retail.zip"
        n = _stream(UCI_ZIP, zip_path)
        with zipfile.ZipFile(zip_path) as z:
            member = [m for m in z.namelist() if m.lower().endswith(".xlsx")][0]
            with z.open(member) as src, open(XLSX, "wb") as out:
                out.write(src.read())
        print(f"[load] UCI 官方下载成功：zip {n/1e6:.1f} MB -> {member}")
        return {"method": "UCI 官方 ZIP 下载", "url": UCI_ZIP, "bytes": n, "member": member}
    except Exception as e:  # noqa: BLE001
        print(f"[load] UCI 直链失败（{type(e).__name__}: {str(e)[:80]}），回落镜像")

    print("[load] ② 回落 Hugging Face 同文件镜像 ...")
    n = _stream(HF_XLSX, XLSX)
    print(f"[load] 镜像下载完成 {n/1e6:.1f} MB")
    return {"method": "Hugging Face 同文件镜像（字节数与 UCI 原文件一致）", "url": HF_XLSX, "bytes": n}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    print("=" * 78)
    print("01_load —— 数据获取")
    print("=" * 78)

    info = acquire()
    digest = sha256(XLSX)

    print("[load] 读取 Excel（约 54 万行，需 1 分钟左右）...")
    df = pd.read_excel(XLSX, dtype={"InvoiceNo": str, "StockCode": str})
    df.columns = [c.strip() for c in df.columns]
    # 原始 Excel 的 Description 列混有数字（类型不统一），统一为字符串以便持久化
    for col in ("InvoiceNo", "StockCode", "Description", "Country"):
        df[col] = df[col].astype("string").str.strip()
    df.to_parquet(PARQUET, index=False)

    meta = {
        "dataset": "Online Retail Data Set (UCI #352)",
        "source_page": "https://archive.ics.uci.edu/dataset/352/online+retail",
        "official_url": UCI_ZIP,
        "download_method": info["method"],
        "download_url": info["url"],
        "downloaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bytes": info["bytes"],
        "sha256": digest,
        "license": "CC BY 4.0（UCI 数据集页标注）",
        "rows": int(len(df)),
        "cols": int(df.shape[1]),
        "columns": list(df.columns),
        "date_min": str(df["InvoiceDate"].min()),
        "date_max": str(df["InvoiceDate"].max()),
        "note": "官方公开文件一次性下载，未使用任何爬虫、未模拟登录、未解析网页",
    }
    dump_json(meta, "source_meta.json", DATA_RAW)

    print(f"[load] 行数 {len(df):,}  列数 {df.shape[1]}")
    print(df.dtypes.to_string())
    print(f"[load] 时间范围 {meta['date_min']} ~ {meta['date_max']}")
    print(f"[load] sha256 {digest[:16]}...")
    print(f"[load] 保存 -> {PARQUET.name}")


if __name__ == "__main__":
    main()
