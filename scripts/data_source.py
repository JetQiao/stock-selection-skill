"""
A 股数据获取模块（基于 akshare，免费、无需 token）。

数据流（全部走批量接口，避免逐股慢查询）：
- get_latest_quote()       → stock_zh_a_spot_em      代码/名称/市净率/市盈率/总市值
- get_financial_bulk()     → stock_yjbb_em           代码/ROE/所处行业/净利润增速/经营现金流
- get_debt_bulk()          → stock_zcfz_em           代码/资产负债率
- get_historical_roe()     → stock_financial_abstract_ths  (per-stock, 仅对预筛选后的小集合调用)

带本地磁盘缓存（默认 12 小时），避免重复请求。
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

CACHE_DIR = Path.home() / ".cache" / "pb_roe_skill"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL_HOURS = 12


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.parquet"


def _is_cache_fresh(path: Path, ttl_hours: int = CACHE_TTL_HOURS) -> bool:
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < ttl_hours * 3600


def _load_cache(key: str) -> Optional[pd.DataFrame]:
    p = _cache_path(key)
    if _is_cache_fresh(p):
        try:
            return pd.read_parquet(p)
        except Exception:
            return None
    return None


def _save_cache(key: str, df: pd.DataFrame) -> None:
    try:
        df.to_parquet(_cache_path(key))
    except Exception:
        pass


def _latest_filed_quarter() -> str:
    """
    返回最近一个"已大面积披露"的季度末（YYYYMMDD）。

    披露规则：
    - 年报：次年 4 月底前
    - Q1 季报：当年 4 月底前
    - 半年报：当年 8 月底前
    - Q3 季报：当年 10 月底前
    """
    today = date.today()
    candidates = [
        (date(today.year, 3, 31), date(today.year, 5, 5)),
        (date(today.year - 1, 12, 31), date(today.year, 5, 5)),
        (date(today.year, 6, 30), date(today.year, 9, 5)),
        (date(today.year, 9, 30), date(today.year, 11, 5)),
    ]
    for q_end, deadline in sorted(candidates, key=lambda x: x[0], reverse=True):
        if today >= deadline and q_end <= today:
            return q_end.strftime("%Y%m%d")
    return (date(today.year - 1, 12, 31)).strftime("%Y%m%d")


def get_latest_quote() -> pd.DataFrame:
    """
    全市场最新行情（批量，~60s 首次拉取）。

    返回字段：ts_code, name, close, pb, pe, total_mv, circ_mv
    """
    cached = _load_cache("latest_quote")
    if cached is not None:
        return cached

    import akshare as ak

    df = ak.stock_zh_a_spot_em()
    df = df.rename(
        columns={
            "代码": "ts_code",
            "名称": "name",
            "最新价": "close",
            "市净率": "pb",
            "市盈率-动态": "pe",
            "总市值": "total_mv",
            "流通市值": "circ_mv",
        }
    )
    df["ts_code"] = df["ts_code"].astype(str).str.zfill(6)

    keep = ["ts_code", "name", "close", "pb", "pe", "total_mv", "circ_mv"]
    df = df[[c for c in keep if c in df.columns]].copy()
    for col in ["close", "pb", "pe", "total_mv", "circ_mv"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    _save_cache("latest_quote", df)
    return df


def get_financial_bulk(quarter: Optional[str] = None) -> pd.DataFrame:
    """
    全市场财务概要（批量，~3s）。

    返回字段：
        ts_code, name, industry, roe_ttm, profit_growth_yoy,
        ocf_per_share, gross_margin, eps, bps
    """
    quarter = quarter or _latest_filed_quarter()
    cache_key = f"yjbb_{quarter}"
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    import akshare as ak

    df = ak.stock_yjbb_em(date=quarter)
    df = df.rename(
        columns={
            "股票代码": "ts_code",
            "股票简称": "name",
            "净资产收益率": "roe_ttm",
            "净利润-同比增长": "profit_growth_yoy",
            "营业总收入-同比增长": "revenue_growth_yoy",
            "每股经营现金流量": "ocf_per_share",
            "销售毛利率": "gross_margin",
            "所处行业": "industry",
            "每股收益": "eps",
            "每股净资产": "bps",
        }
    )
    df["ts_code"] = df["ts_code"].astype(str).str.zfill(6)

    keep = [
        "ts_code", "name", "industry", "roe_ttm",
        "profit_growth_yoy", "revenue_growth_yoy",
        "ocf_per_share", "gross_margin", "eps", "bps",
    ]
    df = df[[c for c in keep if c in df.columns]].copy()
    for col in ["roe_ttm", "profit_growth_yoy", "revenue_growth_yoy",
                "ocf_per_share", "gross_margin", "eps", "bps"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    _save_cache(cache_key, df)
    return df


def get_debt_bulk(quarter: Optional[str] = None) -> pd.DataFrame:
    """
    全市场资产负债率（批量，~3s）。

    返回字段：ts_code, debt_ratio
    """
    quarter = quarter or _latest_filed_quarter()
    cache_key = f"zcfz_{quarter}"
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    import akshare as ak

    df = ak.stock_zcfz_em(date=quarter)
    df = df.rename(columns={"股票代码": "ts_code", "资产负债率": "debt_ratio"})
    df["ts_code"] = df["ts_code"].astype(str).str.zfill(6)
    df = df[["ts_code", "debt_ratio"]].copy()
    df["debt_ratio"] = pd.to_numeric(df["debt_ratio"], errors="coerce")

    _save_cache(cache_key, df)
    return df


def get_market_snapshot(quarter: Optional[str] = None) -> pd.DataFrame:
    """
    一次性拉取并合并行情 + 财务 + 负债，返回完整选股数据集。

    包含字段：
        ts_code, name, industry, close, pb, pe, total_mv, circ_mv,
        roe_ttm, profit_growth_yoy, revenue_growth_yoy,
        ocf_per_share, gross_margin, eps, bps, debt_ratio,
        ocf_to_ni  (经营现金流/净利润，由 ocf_per_share / eps 推算)
    """
    quote = get_latest_quote()
    fin = get_financial_bulk(quarter=quarter)
    debt = get_debt_bulk(quarter=quarter)

    df = quote.merge(
        fin.drop(columns=["name"], errors="ignore"),
        on="ts_code",
        how="left",
    )
    df = df.merge(debt, on="ts_code", how="left")

    if "ocf_per_share" in df.columns and "eps" in df.columns:
        import numpy as np
        eps_safe = df["eps"].where(df["eps"].abs() > 1e-6)
        df["ocf_to_ni"] = (df["ocf_per_share"] / eps_safe).replace([np.inf, -np.inf], np.nan)

    df["dividend_yield"] = None
    df["profit_growth_3y"] = df.get("profit_growth_yoy")
    return df


def get_historical_roe(ts_codes: list[str], years: int = 5) -> dict[str, list[float]]:
    """
    获取历史年度 ROE（按代码分组）。
    仅对预筛选后的小集合调用（每只 ~0.3s）。
    返回 {ts_code: [年度ROE 从近到远]}
    """
    cache_key = f"hist_roe_{years}y_{len(ts_codes)}"
    cached = _load_cache(cache_key)
    if cached is not None:
        result: dict[str, list[float]] = {}
        for code, group in cached.groupby("ts_code"):
            result[code] = group["roe"].tolist()
        return result

    import akshare as ak

    rows: list[dict] = []
    for i, code in enumerate(ts_codes):
        try:
            df = ak.stock_financial_abstract_ths(symbol=code, indicator="按年度")
            if df is None or df.empty:
                continue
            roe_col = next(
                (c for c in df.columns if "净资产收益率" in c and "摊薄" not in c),
                None,
            )
            if roe_col is None:
                continue
            values = pd.to_numeric(df[roe_col], errors="coerce").dropna().tolist()[:years]
            for v in values:
                rows.append({"ts_code": code, "roe": float(v)})
        except Exception:
            continue
        time.sleep(0.05)

    out = pd.DataFrame(rows)
    if not out.empty:
        _save_cache(cache_key, out)

    result = {}
    if not out.empty:
        for code, group in out.groupby("ts_code"):
            result[code] = group["roe"].tolist()
    return result


def clear_cache() -> int:
    """清空本地缓存。返回删除文件数。"""
    n = 0
    for f in CACHE_DIR.glob("*.parquet"):
        try:
            f.unlink()
            n += 1
        except Exception:
            pass
    return n
