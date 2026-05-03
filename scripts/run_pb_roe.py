#!/usr/bin/env python3
"""
PB-ROE 选股一键脚本。

用法（可全部省略，使用默认值）：
    python run_pb_roe.py                           # 默认 strict 模式
    python run_pb_roe.py --mode loose              # 宽松阈值
    python run_pb_roe.py --industry 食品饮料 --top-n 10
    python run_pb_roe.py --output ~/my_report.html
    python run_pb_roe.py --skip-history            # 跳过历史 ROE 检查（更快）
    python run_pb_roe.py --clear-cache             # 清缓存后再跑

完成后会：
    1. 打印报告路径
    2. macOS 自动 open；Linux 用 xdg-open；Windows 用 start
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import data_source
import html_report
import pb_roe_filter as pf


def _open_in_browser(path: Path) -> None:
    try:
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        elif system == "Windows":
            subprocess.run(["cmd", "/c", "start", "", str(path)], check=False, shell=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass


def main() -> int:
    p = argparse.ArgumentParser(description="PB-ROE 选股 + HTML 报告")
    p.add_argument("--mode", choices=["strict", "loose"], default="strict", help="筛选严格度（默认 strict）")
    p.add_argument("--min-roe", type=float, default=None, help="最低 ROE(TTM) %% (覆盖 mode 默认值)")
    p.add_argument("--max-debt", type=float, default=60.0, help="最高资产负债率 %% (默认 60)")
    p.add_argument("--min-dividend", type=float, default=None, help="最低股息率 %%")
    p.add_argument("--top-n", type=int, default=20, help="输出股票数量（默认 20）")
    p.add_argument("--industry", type=str, default=None, help="只选指定行业（可选，模糊匹配）")
    p.add_argument("--output", type=str, default="~/pb_roe_report.html", help="HTML 输出路径")
    p.add_argument("--skip-history", action="store_true", help="跳过历史 ROE 持续性检查（更快）")
    p.add_argument("--clear-cache", action="store_true", help="清空本地缓存后重跑")
    p.add_argument("--no-open", action="store_true", help="跑完不自动打开浏览器")
    args = p.parse_args()

    if args.clear_cache:
        n = data_source.clear_cache()
        print(f"✓ 已清空缓存（{n} 个文件）")

    cfg = pf.FilterConfig(
        max_debt_ratio=args.max_debt,
        top_n=args.top_n,
        industry_filter=args.industry,
        mode=args.mode,
    )
    cfg.apply_mode()
    if args.min_roe is not None:
        cfg.min_roe = args.min_roe
    if args.min_dividend is not None:
        cfg.min_dividend = args.min_dividend

    print(f"=== PB-ROE 选股 [{cfg.mode}] ===")
    print(f"  · ROE ≥ {cfg.min_roe}%   PB分位 ≤ {cfg.max_pb_pct*100:.0f}%   "
          f"负债率 ≤ {cfg.max_debt_ratio}%   股息率 ≥ {cfg.min_dividend}%")
    if cfg.industry_filter:
        print(f"  · 行业：{cfg.industry_filter}")
    print()

    t0 = time.time()
    print("[1/2] 拉取行情 + 财务（首次约 60-90s，之后走缓存）...")
    df = data_source.get_market_snapshot()
    print(f"      · 合并后 {len(df)} 只股票")

    historical_roe = None
    if not args.skip_history:
        print("[2/2] 检查历史 ROE 持续性（每只约 0.3s，可加 --skip-history 跳过）...")
        prefilter = df[
            (df.get("roe_ttm", pd.Series(dtype=float)) >= cfg.min_roe)
            & (df.get("pb", pd.Series(dtype=float)) > 0)
            & (df.get("debt_ratio", pd.Series(dtype=float)).fillna(0) <= cfg.max_debt_ratio)
        ]
        codes = prefilter["ts_code"].head(150).tolist()
        print(f"      · 预筛选出 {len(codes)} 只候选，开始拉历史 ROE...")
        historical_roe = data_source.get_historical_roe(codes, years=5)
        print(f"      · 取得 {len(historical_roe)} 只历史 ROE")
    else:
        print("[2/2] 跳过历史 ROE 检查")

    print("\n[筛选] 运行 PB-ROE 模型...")
    selected, report = pf.select(df, cfg, historical_roe=historical_roe)

    for step in report.steps:
        print(f"  {step['name']:35s} {step['before']:>5d} → {step['after']:>5d}  (-{step['removed']})")
    print(f"\n  最终选出 {report.final} 只\n")

    config_view = {
        "模式": cfg.mode,
        "最低 ROE(TTM)": f"{cfg.min_roe}%",
        "PB 行业中位数": "≤" if cfg.use_industry_pb_median else "—",
        "最高资产负债率": f"{cfg.max_debt_ratio}%",
        "最低股息率": f"{cfg.min_dividend}%",
        "最低 3 年净利增速": f"{cfg.min_profit_growth_3y}%",
        "排序指标": "ROE / PB 降序",
        "输出数量": cfg.top_n,
    }
    if cfg.industry_filter:
        config_view["行业过滤"] = cfg.industry_filter

    out_path = html_report.render(
        selected=selected,
        config=config_view,
        pipeline_report=report,
        output_path=Path(args.output).expanduser(),
    )

    elapsed = time.time() - t0
    print(f"✅ 报告已生成：{out_path}")
    print(f"   耗时 {elapsed:.1f}s")

    if not args.no_open:
        _open_in_browser(out_path)
        print("   (已尝试在浏览器打开)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
