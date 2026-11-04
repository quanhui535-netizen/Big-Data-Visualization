# -*- coding: utf-8 -*-
"""
run_all.py · 一键运行全部教材实验
=================================
遍历本目录下所有 ``*/lab*.py``，按编号顺序逐个执行，并汇总成功/失败情况。

用法::

    python run_all.py                # 跑全部 14 个实验
    python run_all.py 05 09          # 只跑编号里含 05、09 的实验

说明：
* 每个脚本都在自己的目录下运行，只读写自己的 ``data/`` 与 ``outputs/``，互不影响；
* 实验 09 依赖 ``mlxtend``（见 requirements.txt）；
* 全部脚本均为无界面绘图（matplotlib Agg），不需要图形界面。
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def find_scripts() -> list[Path]:
    """找出所有实验脚本（每个实验目录下的 labNN_*.py）。"""
    return sorted(ROOT.glob("*/lab*.py"), key=lambda p: p.parent.name)


def main(argv: list[str]) -> int:
    scripts = find_scripts()
    if not scripts:
        print("[错误] 没有找到任何 lab*.py，请确认目录结构。")
        return 1

    # 支持按编号筛选，例如 `python run_all.py 05 09`
    keywords = [a for a in argv if a.isdigit()]
    if keywords:
        scripts = [s for s in scripts if any(k in s.parent.name for k in keywords)]
        if not scripts:
            print(f"[错误] 没有匹配 {keywords} 的实验。")
            return 1

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")

    total = len(scripts)
    ok, failed = [], []
    print(f"共 {total} 个实验待运行\n")

    for i, script in enumerate(scripts, 1):
        rel = f"{script.parent.name}/{script.name}"
        print("=" * 78)
        print(f"[{i}/{total}] {rel}")
        print("=" * 78)
        t0 = time.time()
        result = subprocess.run(
            [sys.executable, script.name], cwd=script.parent, env=env
        )
        cost = time.time() - t0
        if result.returncode == 0:
            ok.append(rel)
            print(f"-- 完成，用时 {cost:.1f}s\n")
        else:
            failed.append((rel, result.returncode))
            print(f"-- 失败（退出码 {result.returncode}），用时 {cost:.1f}s\n")

    print("=" * 78)
    print(f"运行结束：成功 {len(ok)} / {total}，失败 {len(failed)} / {total}")
    if failed:
        for rel, code in failed:
            print(f"  [失败] {rel}（退出码 {code}）")
        return 1
    print("全部实验运行成功，结果见各自目录下的 outputs/。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
