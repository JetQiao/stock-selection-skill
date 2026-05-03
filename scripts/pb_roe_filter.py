"""
PB-ROE 选股核心筛选逻辑。

输入：合并后的全市场数据（基础信息 + 行情 + 财务）
输出：选出的股票 DataFrame，附带每只股票的"入选理由"和"风险点"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

EXCLUDE_INDUSTRIES = {
    "银行", "银行Ⅱ", "保险", "保险Ⅱ", "证券", "证券Ⅱ", "多元金融",
    "房地产开发", "房地产服务", "房地产",
}


@dataclass
class FilterConfig:
    min_roe: float = 15.0
    min_roe_3y: float = 12.0
    min_roe_5y_avg: float = 15.0

    use_industry_pb_median: bool = True
    max_pb_pct: float = 0.50

    max_debt_ratio: float = 60.0
    min_ocf_ratio: float = 0.8
    min_dividend: float = 1.0
    min_profit_growth_3y: float = 10.0

    top_n: int = 20
    industry_filter: Optional[str] = None
    mode: str = "strict"  # strict | loose | custom

    def apply_mode(self) -> "FilterConfig":
        if self.mode == "loose":
            self.min_roe = 12.0
            self.min_roe_3y = 10.0
            self.min_roe_5y_avg = 12.0
            self.max_pb_pct = 0.70
            self.min_dividend = 0.5
            self.min_profit_growth_3y = 5.0
        return self


@dataclass
class FilterReport:
    initial: int = 0
    after_basic: int = 0
    after_core: int = 0
    after_advanced: int = 0
    final: int = 0
    steps: list[dict] = field(default_factory=list)

    def add(self, name: str, before: int, after: int, note: str = "") -> None:
        self.steps.append({
            "name": name,
            "before": before,
            "after": after,
            "removed": before - after,
            "note": note,
        })


def _add_reason(reasons: list[str], cond: bool, msg: str) -> None:
    if cond:
        reasons.append(msg)


def basic_filter(df: pd.DataFrame, report: FilterReport) -> pd.DataFrame:
    """基础过滤：剔除 ST、新股、金融地产、负净资产、亏损。"""
    n0 = len(df)

    if "name" in df.columns:
        df = df[~df["name"].astype(str).str.contains("ST|退", case=False, na=False)]
    report.add("剔除 ST/退市", n0, len(df))

    n = len(df)
    if "list_date" in df.columns:
        try:
            df["_list_dt"] = pd.to_datetime(df["list_date"], errors="coerce")
            cutoff = pd.Timestamp.now() - pd.DateOffset(years=1)
            df = df[df["_list_dt"].isna() | (df["_list_dt"] < cutoff)]
            df = df.drop(columns=["_list_dt"])
        except Exception:
            pass
    report.add("剔除上市不满 1 年", n, len(df))

    n = len(df)
    if "industry" in df.columns:
        df = df[~df["industry"].isin(EXCLUDE_INDUSTRIES)]
    report.add("剔除金融/地产", n, len(df))

    n = len(df)
    if "pb" in df.columns:
        df = df[df["pb"].notna() & (df["pb"] > 0)]
    report.add("剔除净资产为负 (PB<=0)", n, len(df))

    n = len(df)
    if "roe_ttm" in df.columns:
        df = df[df["roe_ttm"].notna() & (df["roe_ttm"] > 0)]
    report.add("剔除亏损 (ROE<=0)", n, len(df))

    return df


def core_filter(
    df: pd.DataFrame,
    cfg: FilterConfig,
    report: FilterReport,
    historical_roe: Optional[dict[str, list[float]]] = None,
) -> pd.DataFrame:
    """核心条件：ROE 持续性 + PB 相对低估。"""
    n0 = len(df)

    df = df[df["roe_ttm"] >= cfg.min_roe]
    report.add(f"ROE(TTM) ≥ {cfg.min_roe}%", n0, len(df))

    if historical_roe:
        def _check_history(code: str) -> bool:
            roes = historical_roe.get(code, [])
            if len(roes) >= 3 and not all(r >= cfg.min_roe_3y for r in roes[:3]):
                return False
            if len(roes) >= 5 and (sum(roes[:5]) / 5) < cfg.min_roe_5y_avg:
                return False
            return True

        n = len(df)
        df = df[df["ts_code"].apply(_check_history)]
        report.add(f"历史 ROE 持续性 (3y≥{cfg.min_roe_3y}%, 5y均值≥{cfg.min_roe_5y_avg}%)", n, len(df))

    if cfg.use_industry_pb_median and "industry" in df.columns:
        n = len(df)
        med = df.groupby("industry")["pb"].median().to_dict()
        df["_industry_pb_median"] = df["industry"].map(med)
        df = df[df["pb"] <= df["_industry_pb_median"]]
        report.add("PB ≤ 行业 PB 中位数", n, len(df))

    return df


def advanced_filter(df: pd.DataFrame, cfg: FilterConfig, report: FilterReport) -> pd.DataFrame:
    """进阶条件：负债率 / 现金流 / 股息率 / 成长性。"""
    if "debt_ratio" in df.columns:
        n = len(df)
        df = df[df["debt_ratio"].isna() | (df["debt_ratio"] <= cfg.max_debt_ratio)]
        report.add(f"资产负债率 ≤ {cfg.max_debt_ratio}%", n, len(df))

    if "ocf_to_ni" in df.columns:
        n = len(df)
        df = df[df["ocf_to_ni"].isna() | (df["ocf_to_ni"] >= cfg.min_ocf_ratio)]
        report.add(f"经营现金流/净利润 ≥ {cfg.min_ocf_ratio}", n, len(df))

    if "dividend_yield" in df.columns:
        n = len(df)
        df = df[df["dividend_yield"].isna() | (df["dividend_yield"] >= cfg.min_dividend)]
        report.add(f"股息率 ≥ {cfg.min_dividend}%", n, len(df))

    if "profit_growth_3y" in df.columns:
        n = len(df)
        df = df[df["profit_growth_3y"].isna() | (df["profit_growth_3y"] >= cfg.min_profit_growth_3y)]
        report.add(f"3年净利润复合增速 ≥ {cfg.min_profit_growth_3y}%", n, len(df))

    return df


def _build_reason_and_risk(row: pd.Series, cfg: FilterConfig) -> tuple[str, str]:
    reasons = []
    risks = []

    roe = row.get("roe_ttm")
    pb = row.get("pb")
    if pd.notna(roe) and pd.notna(pb):
        reasons.append(f"ROE {roe:.1f}% / PB {pb:.2f}（性价比比 {roe / pb:.1f}）")

    if pd.notna(row.get("dividend_yield")):
        reasons.append(f"股息率 {row['dividend_yield']:.2f}%")

    if pd.notna(row.get("debt_ratio")):
        if row["debt_ratio"] > 50:
            risks.append(f"负债率偏高 ({row['debt_ratio']:.1f}%)")
        else:
            reasons.append(f"低负债 ({row['debt_ratio']:.1f}%)")

    industry = str(row.get("industry", ""))
    cyclical_kw = ["钢铁", "煤炭", "有色", "化工", "建材", "航运", "造纸"]
    if any(k in industry for k in cyclical_kw):
        risks.append("强周期行业，注意景气拐点")

    if pd.notna(row.get("roe_ttm")) and row["roe_ttm"] > 30:
        risks.append("超高 ROE，警惕一次性收益或可持续性")

    return "；".join(reasons), "；".join(risks) if risks else "—"


def select(
    df: pd.DataFrame,
    cfg: FilterConfig,
    historical_roe: Optional[dict[str, list[float]]] = None,
) -> tuple[pd.DataFrame, FilterReport]:
    """运行全套筛选流程，返回 (Top N 结果, 过滤过程报告)。"""
    cfg.apply_mode()
    report = FilterReport(initial=len(df))

    if cfg.industry_filter:
        df = df[df["industry"].astype(str).str.contains(cfg.industry_filter, na=False)]

    df = basic_filter(df.copy(), report)
    report.after_basic = len(df)

    df = core_filter(df, cfg, report, historical_roe)
    report.after_core = len(df)

    df = advanced_filter(df, cfg, report)
    report.after_advanced = len(df)

    if df.empty:
        report.final = 0
        return df, report

    df = df.copy()
    df["roe_pb"] = df["roe_ttm"] / df["pb"]
    df = df.sort_values("roe_pb", ascending=False).head(cfg.top_n)

    reasons, risks = [], []
    for _, row in df.iterrows():
        r, risk = _build_reason_and_risk(row, cfg)
        reasons.append(r)
        risks.append(risk)
    df["reason"] = reasons
    df["risk"] = risks

    report.final = len(df)
    return df.reset_index(drop=True), report
