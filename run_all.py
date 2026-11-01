"""run_all.py —— 一键复现入口

依次执行：下载 → 清洗 → 分析 → 出图 → 大屏，并在最后打印产物清单。
用法：
    python run_all.py            # 全流程
    python run_all.py --skip-load  # 已有 data/raw/online_retail.xlsx 时跳过下载
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"

STEPS = [
    ("01_load.py", "数据获取（UCI 官方文件下载 + 校验）"),
    ("02_clean.py", "数据清洗与治理"),
    ("03_analysis.py", "六个商业分析模型"),
    ("04_visuals.py", "23 张图表（模板复现 + 业务模型图）"),
    ("05_dashboard.py", "Pyecharts 数据大屏"),
]


def main() -> int:
    skip_load = "--skip-load" in sys.argv
    t_all = time.time()
    for name, desc in STEPS:
        if name == "01_load.py" and skip_load:
            print(f"[skip] {name}")
            continue
        print("\n" + "=" * 78)
        print(f"▶ {name}  {desc}")
        print("=" * 78)
        t0 = time.time()
        rc = subprocess.call([sys.executable, str(SCRIPTS / name)], cwd=ROOT)
        if rc != 0:
            print(f"[FAIL] {name} 退出码 {rc}")
            return rc
        print(f"[ok] {name}  用时 {time.time() - t0:.1f}s")

    print("\n" + "=" * 78)
    print(f"全部完成，总用时 {time.time() - t_all:.1f}s")
    figs = sorted((ROOT / "outputs" / "figures").glob("fig*.png"))
    tables = sorted((ROOT / "outputs" / "tables").glob("*.csv"))
    print(f"图表 {len(figs)} 张 -> outputs/figures/")
    print(f"结果表 {len(tables)} 张 -> outputs/tables/")
    dash = ROOT / "outputs" / "dashboard" / "dashboard.html"
    print(f"大屏 {'已生成' if dash.exists() else '缺失'} -> {dash.relative_to(ROOT)}")
    print("交互式大屏请运行：streamlit run app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
