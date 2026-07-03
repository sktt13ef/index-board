"""
Local history data manager.

This module stores historical series in local CSV files and refreshes them from
the currently supported remote sources. It keeps the implementation simple and
truthful: if an official free source exists, use it; otherwise refuse to
fabricate history.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
import requests
from urllib3.exceptions import InsecureRequestWarning

from market_cache import get_market_cache
from market_sources import get_source_entry

try:
    import akshare as ak
except Exception:  # pragma: no cover - keep requests-based sources usable without akshare.
    ak = None

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class HistoryDataManager:
    """SQLite-backed history cache with CSV kept as a compatibility backup."""

    DATA_DIR = Path(__file__).parent / "data" / "history"
    DATA_TTL_HOURS = 24
    PERIOD_DAYS = {
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "3y": 365 * 3,
        "5y": 365 * 5,
        "10y": 3650,
        "all": None,
    }

    INDICES = {
        "CSI300": {
            "name": "沪深300",
            "symbol": "sh000300",
            "source": "tx",
            "series": {
                "price": {"symbol": "sh000300", "source": "tx", "label": "指数收益"},
                "total_return": {"symbol": "H00300", "source": "csindex_perf", "label": "全收益"},
            },
        },
        "CSI500": {
            "name": "中证A500",
            "symbol": "sh000510",
            "source": "tx",
            "series": {
                "price": {"symbol": "sh000510", "source": "tx", "label": "指数收益"},
                "total_return": {"symbol": "000510CNY010", "source": "csindex_perf", "label": "全收益"},
            },
        },
        "CSI500_INDEX": {
            "name": "中证500",
            "symbol": "000905",
            "source": "csindex_perf",
            "series": {
                "price": {"symbol": "000905", "label": "指数收益"},
                "total_return": {"symbol": "H00905", "label": "全收益"},
            },
        },
        "CSI_BAIJIU": {
            "name": "中证白酒指数",
            "symbol": "sz399997",
            "source": "tx",
            "series": {
                "price": {"symbol": "sz399997", "source": "tx", "label": "指数收益"},
                "total_return": {"symbol": "H20539", "source": "csindex_perf", "label": "全收益"},
            },
        },
        "CHINEXT": {
            "name": "创业板指",
            "symbol": "sz399006",
            "source": "tx",
            "series": {
                "price": {"symbol": "sz399006", "source": "tx", "label": "指数收益"}
            },
        },
        "STAR50": {
            "name": "科创50",
            "symbol": "sh000688",
            "source": "tx",
            "series": {
                "price": {"symbol": "sh000688", "source": "tx", "label": "指数收益"},
                "total_return": {"symbol": "000688CNY01", "source": "csindex_perf", "label": "全收益"},
            },
        },
        "STAR100": {
            "name": "科创100",
            "symbol": "sh000698",
            "source": "tx",
            "series": {
                "price": {"symbol": "sh000698", "source": "tx", "label": "指数收益"},
                "total_return": {"symbol": "000698CNY010", "source": "csindex_perf", "label": "全收益"},
            },
        },
        "HSTECH": {
            "name": "恒生科技指数",
            "symbol": "HSTECH",
            "source": "hk_sina",
            "series": {
                "price": {
                    "symbol": "HSTECH",
                    "source": "hk_sina",
                    "label": "指数收益",
                }
            },
        },
        "HSI": {
            "name": "恒生指数",
            "symbol": "HSI",
            "source": "hk_sina",
            "series": {
                "price": {"symbol": "HSI", "source": "hk_sina", "label": "指数收益"}
            },
        },
        "NDX": {
            "name": "纳斯达克100",
            "symbol": "^NDX",
            "source": "yahoo_chart",
            "series": {
                "price": {"symbol": "^NDX", "source": "yahoo_chart", "label": "指数收益"}
            },
        },
        "SPX": {
            "name": "标普500",
            "symbol": "^GSPC",
            "source": "yahoo_chart",
            "series": {
                "price": {"symbol": "^GSPC", "source": "yahoo_chart", "label": "指数收益"}
            },
        },
        "XOP": {
            "name": "标普油气ETF",
            "symbol": "XOP",
            "source": "yahoo_chart",
            "series": {
                "price": {"symbol": "XOP", "source": "yahoo_chart", "label": "价格收益"}
            },
        },
        "WANJIA_GOLD": {
            "name": "万家周期视野C",
            "symbol": "025446",
            "source": "fund_nav",
            "series": {
                "price": {"symbol": "025446", "source": "fund_nav", "label": "单位净值"}
            },
        },
        "DAX": {
            "name": "德国DAX",
            "symbol": "DAX",
            "source": "stoxx_dax",
            "history_available": True,
            "history_max_period": "3mo",
            "series": {
                "price": {"symbol": "DAXK", "source": "stoxx_dax", "label": "指数收益", "history_max_period": "3mo", "merge_snapshot": False},
                "total_return": {"symbol": "DAX", "source": "stoxx_dax", "label": "全收益", "history_max_period": "3mo"},
            },
        },
        "GOLD": {
            "name": "黄金",
            "symbol": "GC=F",
            "source": "yahoo_chart",
            "series": {
                "price": {"symbol": "GC=F", "source": "yahoo_chart", "label": "价格收益"}
            },
        },
        "OIL_WTI": {
            "name": "WTI原油",
            "symbol": "CL=F",
            "source": "yahoo_chart",
            "series": {
                "price": {"symbol": "CL=F", "source": "yahoo_chart", "label": "价格收益"}
            },
        },
        "CN10Y": {
            "name": "中国国债十年收益率",
            "symbol": "CN10Y",
            "source": "chinabond",
            "series": {
                "price": {"symbol": "CN10Y", "source": "chinabond", "label": "收益率"}
            },
        },
        "US10Y": {
            "name": "美国国债十年收益率",
            "symbol": "US10Y",
            "source": "us_treasury",
            "series": {
                "price": {"symbol": "US10Y", "source": "us_treasury", "label": "收益率", "treasury_field": "BC_10YEAR"}
            },
        },
        "US2Y": {
            "name": "美国国债两年收益率",
            "symbol": "US2Y",
            "source": "us_treasury",
            "series": {
                "price": {"symbol": "US2Y", "source": "us_treasury", "label": "收益率", "treasury_field": "BC_2YEAR"}
            },
        },
        "US3M": {
            "name": "美国13周T-Bill收益率",
            "symbol": "^IRX",
            "source": "yahoo_chart",
            "series": {
                "price": {"symbol": "^IRX", "source": "yahoo_chart", "label": "收益率"}
            },
        },
        "CN1Y": {
            "name": "中国国债一年收益率",
            "symbol": "CN1Y",
            "source": "chinabond",
            "series": {
                "price": {"symbol": "CN1Y", "source": "chinabond", "label": "收益率", "chinabond_field": "oneYear"}
            },
        },
        "CN30Y": {
            "name": "中国国债三十年收益率",
            "symbol": "CN30Y",
            "source": "chinabond",
            "series": {
                "price": {"symbol": "CN30Y", "source": "chinabond", "label": "收益率", "chinabond_field": "thirtyYear"}
            },
        },
        "CN10Y_1Y_SPREAD": {
            "name": "中国10Y-1Y利差",
            "symbol": "CN10Y_1Y_SPREAD",
            "source": "computed_spread",
            "series": {
                "price": {"symbol": "CN10Y_1Y_SPREAD", "source": "computed_spread", "label": "利差", "components": ["CN10Y", "CN1Y"]}
            },
        },
        "US10Y_2Y_SPREAD": {
            "name": "美国10Y-2Y利差",
            "symbol": "US10Y_2Y_SPREAD",
            "source": "computed_spread",
            "series": {
                "price": {"symbol": "US10Y_2Y_SPREAD", "source": "computed_spread", "label": "利差", "components": ["US10Y", "US2Y"]}
            },
        },
        "CN_US_10Y_SPREAD": {
            "name": "中美10年利差",
            "symbol": "CN_US_10Y_SPREAD",
            "source": "computed_spread",
            "series": {
                "price": {"symbol": "CN_US_10Y_SPREAD", "source": "computed_spread", "label": "利差", "components": ["CN10Y", "US10Y"]}
            },
        },
        "EU10Y": {
            "name": "欧元区10年AAA收益率",
            "symbol": "EU10Y",
            "source": "ecb_yield",
            "series": {
                "price": {"symbol": "EU10Y", "source": "ecb_yield", "label": "收益率", "ecb_series_key": "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y"}
            },
        },
        "VIX": {
            "name": "VIX恐慌指数",
            "symbol": "VIX",
            "source": "cboe_vix",
            "series": {
                "price": {"symbol": "VIX", "source": "cboe_vix", "label": "指数"}
            },
        },
        "STLFSI4": {
            "name": "圣路易斯联储金融压力指数",
            "symbol": "STLFSI4",
            "source": "fred_csv",
            "history_available": False,
            "series": {
                "price": {"symbol": "STLFSI4", "source": "fred_csv", "label": "指数"}
            },
        },
        "CSI_ALL_SHARE": {
            "name": "中证全指",
            "symbol": "000985",
            "source": "csindex_perf",
            "series": {
                "price": {"symbol": "000985", "label": "指数收益"},
                "total_return": {"symbol": "H00985", "label": "全收益"},
            },
        },
        "CSI1000": {
            "name": "中证1000",
            "symbol": "000852",
            "source": "csindex_perf",
            "series": {
                "price": {"symbol": "000852", "label": "指数收益"},
                "total_return": {"symbol": "H00852", "label": "全收益"},
            },
        },
        "CSI2000": {
            "name": "中证2000",
            "symbol": "932000",
            "source": "csindex_perf",
            "series": {
                "price": {"symbol": "932000", "label": "指数收益"},
                "total_return": {"symbol": "932000CNY010", "label": "全收益"},
            },
        },
        "CAC40": {
            "name": "法国CAC40",
            "symbol": "^FCHI",
            "source": "yahoo_chart",
            "series": {
                "price": {"symbol": "^FCHI", "source": "yahoo_chart", "label": "指数收益"}
            },
        },
        "FTSE100": {
            "name": "英国FTSE100",
            "symbol": ".FTSE",
            "source": "lse_dory",
            "series": {
                "price": {"symbol": ".FTSE", "source": "lse_dory", "label": "指数收益", "history_start_date": "1984-01-01"},
                "total_return": {"symbol": ".TRIUKX", "source": "lse_dory", "label": "全收益", "history_start_date": "2017-10-06"},
            },
        },
        "BTCUSD": {
            "name": "比特币",
            "symbol": "BTC-USD",
            "source": "coinbase_candles",
            "series": {
                "price": {"symbol": "BTC-USD", "source": "coinbase_candles", "label": "价格"}
            },
        },
        "ETHUSD": {
            "name": "以太币",
            "symbol": "ETH-USD",
            "source": "coinbase_candles",
            "series": {
                "price": {"symbol": "ETH-USD", "source": "coinbase_candles", "label": "价格"}
            },
        },
        "CSI_DIVIDEND": {
            "name": "中证红利低波动",
            "symbol": "H30269",
            "source": "csindex_perf",
            "series": {
                "price": {"symbol": "H30269", "label": "指数收益"},
                "total_return": {"symbol": "H20269", "label": "全收益"},
                "dividend_return": {"symbol": "H30269", "source": "computed_dividend_yield", "label": "滚动一年红利回报率", "components": ["price", "total_return"], "rolling_days": 252, "derivation_version": "daily-compounded-252-v2"},
                "dividend_yield": {"symbol": "H30269", "source": "csindex_indicator", "label": "官方股息率", "value_field": "股息率1", "limited_history": True},
            },
        },
        "CSI_DIVIDEND_100": {
            "name": "中证红利低波100",
            "symbol": "930955",
            "source": "csindex_perf",
            "series": {
                "price": {"symbol": "930955", "label": "指数收益"},
                "total_return": {"symbol": "H20955", "label": "全收益"},
                "dividend_return": {"symbol": "930955", "source": "computed_dividend_yield", "label": "滚动一年红利回报率", "components": ["price", "total_return"], "rolling_days": 252, "derivation_version": "daily-compounded-252-v2"},
                "dividend_yield": {"symbol": "930955", "source": "csindex_indicator", "label": "官方股息率", "value_field": "股息率1", "limited_history": True},
            },
        },
        "CSI300_DIVIDEND_LOW_VOL": {
            "name": "沪深300红利低波",
            "symbol": "930740",
            "source": "csindex_perf",
            "series": {
                "price": {"symbol": "930740", "label": "指数收益"},
                "total_return": {"symbol": "H20740", "label": "全收益"},
                "dividend_return": {"symbol": "930740", "source": "computed_dividend_yield", "label": "滚动一年红利回报率", "components": ["price", "total_return"], "rolling_days": 252, "derivation_version": "daily-compounded-252-v2"},
                "dividend_yield": {"symbol": "930740", "source": "csindex_indicator", "label": "官方股息率", "value_field": "股息率1", "limited_history": True},
            },
        },
        "CSI_DIVIDEND_QUALITY": {
            "name": "红利质量",
            "symbol": "931468",
            "source": "csindex_perf",
            "series": {
                "price": {"symbol": "931468", "label": "指数收益"},
                "total_return": {"symbol": "921468", "label": "全收益"},
                "dividend_return": {"symbol": "931468", "source": "computed_dividend_yield", "label": "滚动一年红利回报率", "components": ["price", "total_return"], "rolling_days": 252, "derivation_version": "daily-compounded-252-v2"},
                "dividend_yield": {"symbol": "931468", "source": "csindex_indicator", "label": "官方股息率", "value_field": "股息率1", "limited_history": True},
            },
        },
        "CSI_ALL_DIVIDEND_QUALITY": {
            "name": "中证红利质量",
            "symbol": "932315",
            "source": "csindex_perf",
            "series": {
                "price": {"symbol": "932315", "label": "指数收益"},
                "total_return": {"symbol": "932315CNY010", "label": "全收益"},
                "dividend_return": {"symbol": "932315", "source": "computed_dividend_yield", "label": "滚动一年红利回报率", "components": ["price", "total_return"], "rolling_days": 252, "derivation_version": "daily-compounded-252-v2"},
                "dividend_yield": {"symbol": "932315", "source": "csindex_indicator", "label": "官方股息率", "value_field": "股息率1", "limited_history": True},
            },
        },
        "CSI_CASH_FLOW": {
            "name": "中证现金流",
            "symbol": "932365",
            "source": "csindex_perf",
            "series": {
                "price": {"symbol": "932365", "label": "指数收益"},
                "total_return": {"symbol": "932365CNY010", "label": "全收益"},
                "dividend_return": {"symbol": "932365", "source": "computed_dividend_yield", "label": "滚动一年红利回报率", "components": ["price", "total_return"], "rolling_days": 252, "derivation_version": "daily-compounded-252-v2"},
                "dividend_yield": {"symbol": "932365", "source": "csindex_indicator", "label": "官方股息率", "value_field": "股息率1", "limited_history": True},
            },
        },
        "CNI_FREE_CASH_FLOW": {
            "name": "国证自由现金流",
            "symbol": "980092",
            "source": "cni_official",
            "series": {
                "price": {"symbol": "980092", "source": "cni_official", "label": "指数收益"},
                "total_return": {"symbol": "480092", "source": "cni_official", "label": "全收益"},
                "dividend_return": {"symbol": "980092", "source": "computed_dividend_yield", "label": "滚动一年红利回报率", "components": ["price", "total_return"], "rolling_days": 252, "derivation_version": "daily-compounded-252-v2"},
            },
        },
    }

    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.DATA_DIR / "meta.json"
        self.meta = self._load_meta()
        self.db = get_market_cache()
        self._lse_dory_token = None
        self._lse_dory_token_expiry = 0

    def _load_meta(self) -> dict:
        if self.meta_file.exists():
            try:
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_meta(self):
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)

    def _meta_key(self, key: str, series: str = "price") -> str:
        return key if series == "price" else f"{key}:{series}"

    def _get_file_path(self, key: str, series: str = "price") -> Path:
        suffix = "" if series == "price" else f"_{series}"
        return self.DATA_DIR / f"{key}{suffix}.csv"

    def _get_series_config(self, key: str, series: str = "price") -> dict | None:
        config = self.INDICES.get(key)
        if not config:
            return None

        merged = dict(config)
        merged["registry_key"] = key
        series_map = config.get("series") or {}
        if series_map:
            selected = series_map.get(series)
            if not selected:
                return None
            merged.update(selected)
        elif series != "price":
            return None

        return merged

    def _source_signature(self, key: str, series: str = "price") -> str:
        config = self._get_series_config(key, series) or {}
        parts = [
            "history-v5-provenance",
            str(config.get("source") or ""),
            str(config.get("symbol") or ""),
            str(config.get("series_code") or ""),
            str(config.get("history_max_period") or ""),
            str(config.get("treasury_field") or ""),
            str(config.get("chinabond_field") or ""),
            str(config.get("ecb_series_key") or ""),
            str(config.get("history_start_date") or ""),
            ",".join(config.get("components") or []),
            str(config.get("rolling_days") or ""),
            str(config.get("derivation_version") or ""),
        ]
        if config.get("value_field") or config.get("limited_history"):
            parts.extend([
                str(config.get("value_field") or ""),
                str(bool(config.get("limited_history"))),
            ])
        return "|".join(parts)

    def _period_to_days(self, period: str) -> int | None:
        return self.PERIOD_DAYS.get(period, 365)

    def _is_period_supported(self, config: dict, period: str) -> bool:
        registry_entry = get_source_entry(config.get("registry_key") or "")
        if registry_entry and period not in registry_entry.get("allowed_periods", []):
            return False
        max_period = config.get("history_max_period")
        if period == "all":
            return not max_period or max_period == "all"
        if not max_period:
            return True
        period_days = self._period_to_days(period)
        max_days = self._period_to_days(max_period)
        if period_days is None or max_days is None:
            return True
        return period_days <= max_days

    def _is_data_valid(self, key: str, series: str = "price") -> bool:
        signature = self._source_signature(key, series)
        if self.db.is_history_fresh(key, series, signature, self.DATA_TTL_HOURS):
            return True

        meta_key = self._meta_key(key, series)
        if meta_key not in self.meta:
            return False
        meta_signature = self.meta[meta_key].get("source_signature")
        if meta_signature != signature:
            return False
        last_update = self.meta[meta_key].get("last_update", 0)
        elapsed_hours = (time.time() - last_update) / 3600
        return elapsed_hours < self.DATA_TTL_HOURS

    def _provenance_for_series(self, key: str, series: str) -> dict:
        config = self._get_series_config(key, series) or {}
        registry = get_source_entry(key) or {}
        source = config.get("source", "")
        source_label = {
            "csindex_perf": "中证指数官网",
            "cni_official": "国证指数网",
            "tx": "腾讯/akshare免费日线",
            "hk_sina": "新浪财经港股历史",
            "yahoo_chart": "Yahoo Finance Chart",
            "chinabond": "中国债券信息网",
            "us_treasury": "U.S. Treasury",
            "computed_spread": "由本地官方收益率曲线计算",
            "computed_dividend_yield": "官方价格/全收益指数反推",
            "ecb_yield": "European Central Bank",
            "cboe_vix": "Cboe",
            "fred_csv": "FRED",
            "coinbase_candles": "Coinbase Exchange",
            "stoxx_dax": "STOXX/Deutsche Börse公开历史",
            "lse_dory": "London Stock Exchange / Refinitiv",
            "csindex_indicator": "中证指数官网估值指标文件",
            "fund_nav": "东方财富基金净值",
            "fund_nav_accum": "东方财富基金累计净值",
        }.get(source, source or "unknown")
        label = config.get("label", series)
        is_proxy = "代理" in label
        is_same_source = "同源" in label
        is_official = source in {
            "csindex_perf",
            "cni_official",
            "chinabond",
            "us_treasury",
            "computed_spread",
            "computed_dividend_yield",
            "ecb_yield",
            "cboe_vix",
            "fred_csv",
            "coinbase_candles",
            "stoxx_dax",
            "lse_dory",
            "csindex_indicator",
            "hsi_daily_bulletin",
        }
        return {
            "series": series,
            "source_label": source_label,
            "source_type": source,
            "source_signature": self._source_signature(key, series),
            "is_official": is_official,
            "is_proxy": is_proxy,
            "is_same_source": is_same_source,
            "data_as_of": None,
            "source_url": registry.get("source_url", ""),
        }

    def _annotate_rows(self, key: str, series: str, rows: list | None) -> list | None:
        if not rows:
            return rows
        provenance = self._provenance_for_series(key, series)
        annotated = []
        for row in rows:
            item = dict(row)
            item.setdefault("series", provenance["series"])
            item.setdefault("source_label", provenance["source_label"])
            item.setdefault("source_type", provenance["source_type"])
            item.setdefault("source_signature", provenance["source_signature"])
            item.setdefault("is_official", provenance["is_official"])
            item.setdefault("is_proxy", provenance["is_proxy"])
            item.setdefault("is_same_source", provenance["is_same_source"])
            item.setdefault("is_merged_snapshot", False)
            item.setdefault("merged_from_snapshot_at", None)
            item.setdefault("merge_rule", None)
            item.setdefault("data_as_of", item.get("date"))
            item.setdefault("fetched_at", None)
            annotated.append(item)
        return annotated

    def load_local_data(self, key: str, period: str = "1y", series: str = "price") -> list | None:
        config = self._get_series_config(key, series) or {}
        if config.get("history_available") is False:
            return None
        if not self._is_period_supported(config, period):
            return None

        signature = self._source_signature(key, series)
        db_rows = self.db.load_history(
            key,
            series,
            period_days=self._period_to_days(period),
            source_signature=signature,
        )
        if db_rows:
            return self._annotate_rows(key, series, db_rows)

        file_path = self._get_file_path(key, series)
        if not file_path.exists():
            return None

        try:
            df = pd.read_csv(file_path)
            df["date"] = pd.to_datetime(df["date"])

            days = self._period_to_days(period)
            if days is not None:
                start_date = datetime.now() - timedelta(days=days)
                df = df[df["date"] >= start_date]
            df = df.sort_values("date")

            result = []
            for _, row in df.iterrows():
                result.append(
                    {
                        "date": row["date"].strftime("%Y-%m-%d"),
                        "open": round(float(row["open"]), 2),
                        "high": round(float(row["high"]), 2),
                        "low": round(float(row["low"]), 2),
                        "close": round(float(row["close"]), 2),
                        "volume": int(row["volume"]) if "volume" in df.columns else 0,
                    }
                )
            return self._annotate_rows(key, series, result)
        except Exception:
            return None

    def _local_data_covers_period(self, key: str, period: str, series: str, rows: list | None) -> bool:
        if not rows:
            return False
        config = self._get_series_config(key, series) or {}
        if config.get("limited_history"):
            return True
        days = self._period_to_days(period)
        try:
            first_date = pd.to_datetime(rows[0].get("date"))
        except Exception:
            return False
        if days is None:
            if config.get("history_start_date"):
                try:
                    expected_start = pd.to_datetime(config["history_start_date"])
                    return first_date <= expected_start + pd.Timedelta(days=45)
                except Exception:
                    return False
            if config.get("history_max_period"):
                return True
            return len(rows) >= 500
        expected_start = pd.Timestamp.now() - pd.Timedelta(days=days)
        return first_date <= expected_start + pd.Timedelta(days=7)

    def _remote_days_for_period(self, period: str) -> int | None:
        days = self._period_to_days(period)
        if days is None:
            return None
        return max(days + 14, 45)

    def save_local_data(self, key: str, data: list, series: str = "price"):
        if not data:
            return

        try:
            config = self._get_series_config(key, series) or {}
            signature = self._source_signature(key, series)
            file_path = self._get_file_path(key, series)
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])

            existing_meta = self.meta.get(self._meta_key(key, series), {})
            existing_signature = existing_meta.get("source_signature")
            if file_path.exists() and existing_signature == signature:
                try:
                    existing_df = pd.read_csv(file_path)
                    existing_df["date"] = pd.to_datetime(existing_df["date"])
                    df = pd.concat([existing_df, df], ignore_index=True)
                    df = df.drop_duplicates(subset=["date"], keep="last")
                except Exception:
                    pass

            cutoff_date = datetime.now() - timedelta(days=36500)
            df = df[df["date"] >= cutoff_date].sort_values("date")
            df.to_csv(file_path, index=False)

            merged_rows = []
            for _, row in df.iterrows():
                close = float(row["close"])
                volume = row.get("volume", 0)
                if pd.isna(volume):
                    volume = 0
                merged_rows.append({
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "open": float(row.get("open", close)),
                    "high": float(row.get("high", close)),
                    "low": float(row.get("low", close)),
                    "close": close,
                    "volume": int(volume or 0),
                })
            self.db.save_history(
                key,
                series,
                merged_rows,
                source=config.get("source"),
                source_symbol=config.get("symbol"),
                source_signature=signature,
            )

            self.meta[self._meta_key(key, series)] = {
                "last_update": time.time(),
                "record_count": len(df),
                "series": series,
                "source": config.get("source"),
                "source_symbol": config.get("symbol"),
                "source_signature": signature,
                "date_range": {
                    "start": df["date"].min().strftime("%Y-%m-%d"),
                    "end": df["date"].max().strftime("%Y-%m-%d"),
                },
            }
            self._save_meta()
        except Exception:
            pass

    def _fetch_csindex_perf_history(self, symbol: str, days: int | None = None) -> list | None:
        """Fetch official CSI daily index history, including total return symbols."""
        end = datetime.now()
        start = datetime(1990, 1, 1) if days is None else end - timedelta(days=days)
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        response = session.get(
            "https://www.csindex.com.cn/csindex-home/perf/index-perf",
            params={
                "indexCode": symbol,
                "startDate": start.strftime("%Y%m%d"),
                "endDate": end.strftime("%Y%m%d"),
            },
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": f"https://www.csindex.com.cn/#/indices/family/detail?indexCode={symbol}",
                "Accept": "application/json, text/plain, */*",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data") or []
        result = []

        def number(value, fallback=None):
            try:
                if value in (None, "") or pd.isna(value):
                    return fallback
                return float(value)
            except Exception:
                return fallback

        for row in rows:
            raw_date = str(row.get("tradeDate") or "").strip()
            if not raw_date:
                continue
            try:
                trade_date = datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                try:
                    trade_date = pd.to_datetime(raw_date).strftime("%Y-%m-%d")
                except Exception:
                    continue
            if trade_date == "1990-01-01":
                continue

            close = number(row.get("close"))
            if close is None or close <= 0:
                continue
            open_value = number(row.get("open"), close)
            high = number(row.get("high"), close)
            low = number(row.get("low"), close)
            volume = number(row.get("tradingVol"), 0)
            result.append(
                {
                    "date": trade_date,
                    "open": round(open_value, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close, 2),
                    "volume": int(volume or 0),
                }
            )

        return sorted(result, key=lambda item: item["date"]) or None

    def _fetch_csindex_indicator_history(self, symbol: str, value_field: str = "股息率1") -> list | None:
        """Fetch CSI official valuation indicator file.

        The public indicator workbook currently exposes recent valuation rows
        including 股息率1/股息率2. If CSI blocks the OSS file, return None instead
        of fabricating a dividend-yield series.
        """
        url = (
            "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/"
            f"file/autofile/indicator/{symbol}indicator.xls"
        )
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        response = session.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                "Referer": "https://www.csindex.com.cn/",
                "Accept": "application/vnd.ms-excel,application/octet-stream,*/*",
            },
            timeout=60,
        )
        response.raise_for_status()
        content_type = (response.headers.get("content-type") or "").lower()
        if "text/html" in content_type:
            return None

        df = pd.read_excel(BytesIO(response.content))
        if df is None or df.empty:
            return None

        columns = [str(col).strip() for col in df.columns]
        df.columns = columns

        date_col = next((col for col in columns if col == "日期" or col.startswith("日期")), None)
        field = value_field if value_field in columns else None
        if field is None:
            field = next((col for col in columns if value_field and value_field in col), None)
        if field is None:
            field = next((col for col in columns if col.startswith("股息率1") or "D/P1" in col), None)
        if not date_col or not field:
            return None

        result = []
        for _, row in df.iterrows():
            try:
                raw_date = str(row[date_col]).strip()
                if raw_date.endswith(".0"):
                    raw_date = raw_date[:-2]
                if raw_date.isdigit() and len(raw_date) == 8:
                    date = pd.to_datetime(raw_date, format="%Y%m%d").strftime("%Y-%m-%d")
                else:
                    date = pd.to_datetime(row[date_col]).strftime("%Y-%m-%d")
                value = float(row[field])
            except Exception:
                continue
            if value < 0:
                continue
            value = round(value, 4)
            result.append({
                "date": date,
                "open": value,
                "high": value,
                "low": value,
                "close": value,
                "volume": 0,
            })

        return sorted(result, key=lambda item: item["date"]) or None

    def _fetch_cni_history(self, symbol: str, days: int | None = None) -> list | None:
        """Fetch CNI official daily index history through the public CNI feed."""
        if ak is None:
            return None

        end = datetime.now()
        start = datetime(1990, 1, 1) if days is None else end - timedelta(days=days)
        df = ak.index_hist_cni(
            symbol=str(symbol),
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )
        if df is None or df.empty:
            return None

        result = []
        for _, row in df.iterrows():
            try:
                trade_date = pd.to_datetime(row.get("日期")).strftime("%Y-%m-%d")
                close = float(row.get("收盘价"))

                def number(field: str, fallback: float = 0) -> float:
                    value = row.get(field)
                    try:
                        if value in (None, "") or pd.isna(value):
                            return fallback
                        return float(value)
                    except Exception:
                        return fallback

                open_value = number("开盘价", close)
                high = number("最高价", close)
                low = number("最低价", close)
                volume = number("成交量", 0)
                result.append(
                    {
                        "date": trade_date,
                        "open": round(open_value, 2),
                        "high": round(high, 2),
                        "low": round(low, 2),
                        "close": round(close, 2),
                        "volume": int(volume * 10000),
                    }
                )
            except Exception:
                continue

        return sorted(result, key=lambda item: item["date"]) or None

    def _fetch_eastmoney_global_history(self, symbol: str) -> list | None:
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": f"100.{symbol}",
            "klt": "101",
            "fqt": "0",
            "lmt": "5000",
            "end": "20500000",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        }
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        response = session.get(url, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()

        klines = payload.get("data", {}).get("klines") or []
        result = []
        for item in klines:
            parts = item.split(",")
            if len(parts) < 6:
                continue
            result.append(
                {
                    "date": parts[0],
                    "open": round(float(parts[1]), 2),
                    "close": round(float(parts[2]), 2),
                    "high": round(float(parts[3]), 2),
                    "low": round(float(parts[4]), 2),
                    "volume": int(float(parts[5] or 0)),
                }
            )
        return result or None

    def _fetch_yahoo_chart_history(self, symbol: str, days: int | None = None) -> list | None:
        """Fetch daily Yahoo chart data; adjusted close is used when available."""
        def yahoo_range(value: int | None) -> str:
            if value is None:
                return "max"
            if value <= 35:
                return "1mo"
            if value <= 100:
                return "3mo"
            if value <= 200:
                return "6mo"
            if value <= 400:
                return "1y"
            if value <= 365 * 3 + 30:
                return "3y"
            if value <= 365 * 5 + 30:
                return "5y"
            if value <= 365 * 10 + 30:
                return "10y"
            return "max"

        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        response = session.get(
            f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={
                "range": yahoo_range(days),
                "interval": "1d",
                "events": "history",
                "includeAdjustedClose": "true",
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        result_items = payload.get("chart", {}).get("result") or []
        if not result_items:
            return None

        item = result_items[0]
        timestamps = item.get("timestamp") or []
        quote = (item.get("indicators", {}).get("quote") or [{}])[0]
        adjclose = (item.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose") or []

        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        rows = []
        for idx, ts in enumerate(timestamps):
            try:
                close = closes[idx]
                if close is None or float(close) <= 0:
                    continue
                adjusted = adjclose[idx] if idx < len(adjclose) and adjclose[idx] is not None else close
                ratio = float(adjusted) / float(close) if close else 1.0
                open_value = opens[idx] if idx < len(opens) and opens[idx] is not None else close
                high_value = highs[idx] if idx < len(highs) and highs[idx] is not None else close
                low_value = lows[idx] if idx < len(lows) and lows[idx] is not None else close
                volume = volumes[idx] if idx < len(volumes) and volumes[idx] is not None else 0
                rows.append(
                    {
                        "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
                        "open": round(float(open_value) * ratio, 4),
                        "high": round(float(high_value) * ratio, 4),
                        "low": round(float(low_value) * ratio, 4),
                        "close": round(float(adjusted), 4),
                        "volume": int(volume or 0),
                    }
                )
            except Exception:
                continue

        return rows or None

    def _fetch_tencent_index_history(self, symbol: str, days: int | None = None) -> list | None:
        """Fetch Tencent daily index history in chunks so 10y charts have enough rows."""
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        end = datetime.now()
        start = datetime(1990, 1, 1) if days is None else end - timedelta(days=days)
        chunk_days = 1800
        cursor_start = start
        rows_by_date = {}

        while cursor_start <= end:
            cursor_end = min(cursor_start + timedelta(days=chunk_days), end)
            response = session.get(
                "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
                params={
                    "param": (
                        f"{symbol},day,{cursor_start.strftime('%Y-%m-%d')},"
                        f"{cursor_end.strftime('%Y-%m-%d')},2000,qfq"
                    )
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=25,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") or {}
            item = data.get(symbol)
            if isinstance(item, dict):
                rows = item.get("qfqday") or item.get("day") or []
                for row in rows:
                    if len(row) < 6:
                        continue
                    try:
                        rows_by_date[row[0]] = {
                            "date": row[0],
                            "open": round(float(row[1]), 2),
                            "close": round(float(row[2]), 2),
                            "high": round(float(row[3]), 2),
                            "low": round(float(row[4]), 2),
                            "volume": int(float(row[5] or 0)),
                        }
                    except Exception:
                        continue
            cursor_start = cursor_end + timedelta(days=1)

        return sorted(rows_by_date.values(), key=lambda item: item["date"]) or None

    def _fetch_chinabond_yield_history(self, days: int | None = None, field: str = "tenYear") -> list | None:
        """中债接口超过~2年会超时，分段拉取再合并。"""
        url = "https://yield.chinabond.com.cn/cbweb-mn/pgxh/historyQuery"
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}

        end_overall = datetime.now()
        start_overall = datetime(2002, 1, 1) if days is None else end_overall - timedelta(days=days)
        chunk_days = 700  # 留点余量
        all_rows = []
        cursor_end = end_overall
        while cursor_end > start_overall:
            cursor_start = max(cursor_end - timedelta(days=chunk_days), start_overall)
            try:
                response = session.post(
                    url,
                    params={
                        "startDate": cursor_start.strftime("%Y-%m-%d"),
                        "endDate": cursor_end.strftime("%Y-%m-%d"),
                        "gjqx": 0,
                        "locale": "cn_ZH",
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Referer": "https://yield.chinabond.com.cn/",
                        "Accept": "application/json, text/plain, */*",
                    },
                    timeout=25,
                )
                response.raise_for_status()
                payload = response.json()
                for row in payload:
                    date = row.get("workTime")
                    value = row.get(field)
                    if not date or value in (None, ""):
                        continue
                    try:
                        close = float(value)
                    except Exception:
                        continue
                    all_rows.append({
                        "date": date,
                        "open": round(close, 2),
                        "high": round(close, 2),
                        "low": round(close, 2),
                        "close": round(close, 2),
                        "volume": 0,
                    })
            except Exception:
                # 某段失败就不再向前拉
                break
            cursor_end = cursor_start - timedelta(days=1)

        # 去重并按日期排序
        seen = {}
        for r in all_rows:
            seen[r["date"]] = r
        result = sorted(seen.values(), key=lambda x: x["date"])
        return result or None

    def _fetch_us_treasury_yield_history(self, months: int = 360, field: str = "BC_10YEAR") -> list | None:
        url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        ns = {
            "a": "http://www.w3.org/2005/Atom",
            "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
            "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
        }

        def previous_month_start(value: datetime) -> datetime:
            first_of_month = value.replace(day=1)
            return (first_of_month - timedelta(days=1)).replace(day=1)

        month_cursor = datetime.now().replace(day=1)
        rows = []
        seen_dates = set()
        for _ in range(months):
            response = session.get(
                url,
                params={
                    "data": "daily_treasury_yield_curve",
                    "field_tdr_date_value_month": month_cursor.strftime("%Y%m"),
                },
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates",
                    "Accept": "application/atom+xml, application/xml, text/xml, */*",
                },
                timeout=20,
            )
            response.raise_for_status()
            root = ET.fromstring(response.text)
            for entry in root.findall("a:entry", ns):
                props = entry.find(".//m:properties", ns)
                if props is None:
                    continue
                date_text = props.findtext("d:NEW_DATE", default="", namespaces=ns)
                value_text = props.findtext(f"d:{field}", default="", namespaces=ns)
                if not date_text or value_text in (None, ""):
                    continue
                date = str(date_text)[:10]
                if date in seen_dates:
                    continue
                try:
                    close = float(value_text)
                except Exception:
                    continue
                seen_dates.add(date)
                rows.append(
                    {
                        "date": date,
                        "open": round(close, 2),
                        "high": round(close, 2),
                        "low": round(close, 2),
                        "close": round(close, 2),
                        "volume": 0,
                    }
                )
            month_cursor = previous_month_start(month_cursor)

        return sorted(rows, key=lambda item: item["date"]) or None

    def _fetch_computed_spread_history(self, components: list[str], period: str = "all") -> list | None:
        """Build a local spread series from two already-audited history series."""
        if not components or len(components) != 2:
            return None

        left_rows = self.get_history_data(components[0], period, series="price")
        right_rows = self.get_history_data(components[1], period, series="price")
        if not left_rows or not right_rows:
            return None

        left = {row.get("date"): row for row in left_rows if row.get("date") and row.get("close") is not None}
        right = {row.get("date"): row for row in right_rows if row.get("date") and row.get("close") is not None}
        dates = sorted(set(left) & set(right))
        result = []
        for date in dates:
            try:
                close = float(left[date]["close"]) - float(right[date]["close"])
            except Exception:
                continue
            result.append({
                "date": date,
                "open": round(close, 4),
                "high": round(close, 4),
                "low": round(close, 4),
                "close": round(close, 4),
                "volume": 0,
            })
        return result or None

    def _fetch_computed_dividend_yield_history(
        self,
        key: str,
        rolling_days: int = 252,
    ) -> list | None:
        """Derive rolling dividend contribution from price and total-return indices.

        Formula:
            daily contribution = (TR_t / TR_t-1) / (Price_t / Price_t-1) - 1
            rolling contribution = product(1 + daily contribution, n days) - 1

        This is not the point-in-time D/P field published in CSI's short
        valuation workbook. It is an auditable local derivation from two
        index-company history series.
        """
        if rolling_days <= 0:
            return None

        price_rows = self.get_history_data(key, "all", series="price") or []
        total_rows = self.get_history_data(key, "all", series="total_return") or []
        if len(price_rows) <= rolling_days or len(total_rows) <= rolling_days:
            return None

        price_by_date = {
            row.get("date"): float(row.get("close"))
            for row in price_rows
            if row.get("date") and row.get("close") not in (None, "")
        }
        total_by_date = {
            row.get("date"): float(row.get("close"))
            for row in total_rows
            if row.get("date") and row.get("close") not in (None, "")
        }
        dates = sorted(set(price_by_date).intersection(total_by_date))
        if len(dates) <= rolling_days:
            return None

        daily_factors = []
        for idx in range(1, len(dates)):
            date = dates[idx]
            prev_date = dates[idx - 1]
            price_prev = price_by_date.get(prev_date)
            price_now = price_by_date.get(date)
            total_prev = total_by_date.get(prev_date)
            total_now = total_by_date.get(date)
            if not price_prev or not price_now or not total_prev or not total_now:
                continue
            price_return = price_now / price_prev
            total_return = total_now / total_prev
            if price_return <= 0 or total_return <= 0:
                continue
            factor = total_return / price_return
            if factor <= 0 or factor > 1.3:
                continue
            daily_factors.append((date, factor))

        if len(daily_factors) < rolling_days:
            return None

        result = []
        rolling_factor = 1.0
        for idx, (date, factor) in enumerate(daily_factors):
            rolling_factor *= factor
            if idx >= rolling_days:
                old_factor = daily_factors[idx - rolling_days][1]
                if old_factor:
                    rolling_factor /= old_factor
            if idx < rolling_days - 1:
                continue

            value = (rolling_factor - 1) * 100
            if -0.05 < value < 0:
                value = 0.0
            if value < 0 or value > 30:
                continue
            value = round(value, 4)
            result.append({
                "date": date,
                "open": value,
                "high": value,
                "low": value,
                "close": value,
                "volume": 0,
            })
        return result or None

    def _fetch_ecb_yield_history(self, series_key: str, last_n: int | None = None) -> list | None:
        """Fetch an ECB Statistical Data Warehouse yield curve CSV series."""
        if not series_key:
            return None
        flow = "YC"
        key = series_key
        if "." in series_key:
            possible_flow, rest = series_key.split(".", 1)
            if possible_flow.isupper() and len(possible_flow) <= 8:
                flow, key = possible_flow, rest
        url = f"https://data-api.ecb.europa.eu/service/data/{flow}/{key}"
        params = {"format": "csvdata"}
        if last_n:
            params["lastNObservations"] = str(last_n)

        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        response = session.get(
            url,
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/csv, */*",
            },
            timeout=35,
        )
        response.raise_for_status()
        df = pd.read_csv(BytesIO(response.content))
        if df is None or df.empty or "TIME_PERIOD" not in df.columns or "OBS_VALUE" not in df.columns:
            return None

        result = []
        for _, row in df.iterrows():
            date = str(row.get("TIME_PERIOD") or "").strip()
            value = row.get("OBS_VALUE")
            if not date or value in (None, ""):
                continue
            try:
                close = float(value)
            except Exception:
                continue
            result.append({
                "date": date[:10],
                "open": round(close, 4),
                "high": round(close, 4),
                "low": round(close, 4),
                "close": round(close, 4),
                "volume": 0,
            })
        return sorted(result, key=lambda item: item["date"]) or None

    def _fetch_cboe_vix_history(self) -> list | None:
        """Fetch the official Cboe VIX historical CSV."""
        response = requests.get(
            "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/csv, */*",
            },
            timeout=25,
        )
        response.raise_for_status()
        df = pd.read_csv(BytesIO(response.content))
        if df is None or df.empty:
            return None

        result = []
        for _, row in df.iterrows():
            try:
                date = pd.to_datetime(row.get("DATE")).strftime("%Y-%m-%d")
                open_value = float(row.get("OPEN"))
                high_value = float(row.get("HIGH"))
                low_value = float(row.get("LOW"))
                close = float(row.get("CLOSE"))
            except Exception:
                continue
            result.append({
                "date": date,
                "open": round(open_value, 2),
                "high": round(high_value, 2),
                "low": round(low_value, 2),
                "close": round(close, 2),
                "volume": 0,
            })
        return sorted(result, key=lambda item: item["date"]) or None

    def _fetch_coinbase_candles(self, product_id: str, days: int | None = None) -> list | None:
        """Fetch Coinbase Exchange daily candles in 300-day chunks."""
        if not product_id:
            return None
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        end_overall = datetime.utcnow()
        start_overall = datetime(2015, 1, 1) if days is None else end_overall - timedelta(days=days)
        cursor_start = start_overall
        rows_by_date = {}

        while cursor_start < end_overall:
            cursor_end = min(cursor_start + timedelta(days=299), end_overall)
            response = session.get(
                f"https://api.exchange.coinbase.com/products/{product_id}/candles",
                params={
                    "granularity": "86400",
                    "start": cursor_start.isoformat(timespec="seconds"),
                    "end": cursor_end.isoformat(timespec="seconds"),
                },
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                break
            for row in payload:
                if not isinstance(row, list) or len(row) < 6:
                    continue
                try:
                    ts, low, high, open_value, close, volume = row[:6]
                    date = datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
                    rows_by_date[date] = {
                        "date": date,
                        "open": round(float(open_value), 2),
                        "high": round(float(high), 2),
                        "low": round(float(low), 2),
                        "close": round(float(close), 2),
                        "volume": int(float(volume or 0)),
                    }
                except Exception:
                    continue
            cursor_start = cursor_end + timedelta(days=1)

        return sorted(rows_by_date.values(), key=lambda item: item["date"]) or None

    def _fetch_hsi_daily_bulletin_history(self, series_code: str) -> list | None:
        bulletin_url = "https://www.hsi.com.hk/data/eng/download/daily-bulletin.json"
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        response = session.get(
            bulletin_url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.hsi.com.hk/index360/eng/indexes?id=00014.00",
                "Accept": "application/json, text/plain, */*",
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        series_item = next(
            (item for item in payload.get("indexSeriesList", []) if item.get("seriesCode") == series_code),
            None,
        )
        if not series_item:
            return None

        report = next((item for item in series_item.get("reportList", []) if item.get("reportType") == "idx"), None)
        if not report:
            return None

        report_dates = report.get("reportDate") or []
        if not report_dates:
            return None

        result = []
        for entry in sorted(report_dates, key=lambda item: item.get("date", "")):
            csv_url = entry.get("url")
            if not csv_url:
                continue
            csv_response = session.get(
                f"https://www.hsi.com.hk{csv_url}",
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": bulletin_url,
                    "Accept": "text/csv, text/plain, */*",
                },
                timeout=15,
            )
            csv_response.raise_for_status()
            df = pd.read_csv(BytesIO(csv_response.content), encoding="utf-16", sep="\t", header=1)
            if df is None or df.empty:
                continue
            row = df.iloc[0]
            trade_date_raw = str(row.get("Trade Date") or "").strip()
            if not trade_date_raw:
                continue
            try:
                trade_date = datetime.strptime(trade_date_raw, "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                trade_date = trade_date_raw

            close = float(row.get("Index Close") or 0)
            high = float(row.get("Daily High") or close)
            low = float(row.get("Daily Low") or close)
            change = float(row.get("Point Change") or 0)
            result.append(
                {
                    "date": trade_date,
                    "open": round(close - change, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close, 2),
                    "volume": 0,
                }
            )

        return result or None

    def _fetch_stoxx_dax_history(self, symbol: str = "DAX") -> list | None:
        """Fetch the public STOXX 3-month DAX/DAXK history file."""
        code = (symbol or "DAX").strip().upper()
        if code not in {"DAX", "DAXK"}:
            return None
        url = f"https://www.stoxx.com/documents/stoxxnet/Documents/Indices/Current/HistoricalData/h_3m{code.lower()}.txt"
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        response = session.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.stoxx.com/",
                "Accept": "text/plain, */*",
            },
            verify=False,
            timeout=20,
        )
        response.raise_for_status()

        result = []
        for raw_line in response.text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("Date;"):
                continue
            parts = [part.strip() for part in line.split(";")]
            if len(parts) < 3:
                continue
            date_text, _symbol, value_text = parts[:3]
            if not date_text or value_text in (None, ""):
                continue
            try:
                trade_date = datetime.strptime(date_text, "%d.%m.%Y").strftime("%Y-%m-%d")
                close = float(value_text)
            except Exception:
                continue
            result.append(
                {
                    "date": trade_date,
                    "open": round(close, 2),
                    "high": round(close, 2),
                    "low": round(close, 2),
                    "close": round(close, 2),
                    "volume": 0,
                }
            )

        return sorted(result, key=lambda item: item["date"]) or None

    def _get_lse_dory_token(self) -> str | None:
        """Get the anonymous chart token used by London Stock Exchange pages."""
        if self._lse_dory_token and self._lse_dory_token_expiry > time.time() + 60:
            return self._lse_dory_token

        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.londonstockexchange.com",
            "Referer": "https://www.londonstockexchange.com/",
        }
        saml_response = session.get(
            "https://api.londonstockexchange.com/api/gw/feedhandler/token/saml",
            headers=headers,
            timeout=20,
        )
        saml_response.raise_for_status()
        encoded_token = saml_response.json().get("encodedToken")
        if not encoded_token:
            return None

        token_response = session.post(
            "https://refinitiv-widgets.financial.com/auth/api/v1/sessions/samllogin?fetchToken=true",
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
            data={"SAMLResponse": encoded_token},
            timeout=20,
        )
        token_response.raise_for_status()
        payload = token_response.json()
        token = payload.get("token")
        if not token:
            return None
        self._lse_dory_token = token
        self._lse_dory_token_expiry = float(payload.get("expiresAt") or (time.time() + 1800))
        return token

    @staticmethod
    def _lse_number(value, fallback: float | None = None) -> float | None:
        if value in (None, "", "-"):
            return fallback
        try:
            return float(value)
        except Exception:
            return fallback

    def _fetch_lse_dory_history(self, ric: str, days: int | None = None) -> list | None:
        """Fetch LSE page time-series data through its Refinitiv widget endpoint."""
        if not ric:
            return None

        end = datetime.utcnow()
        start = datetime(1984, 1, 1) if days is None else end - timedelta(days=days)
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}

        for attempt in range(2):
            token = self._get_lse_dory_token()
            if not token:
                return None
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Origin": "https://www.londonstockexchange.com",
                "Referer": "https://www.londonstockexchange.com/",
                "jwt": token,
                "X-Component-Id": "stock-dashboard",
            }
            response = session.get(
                "https://refinitiv-widgets.financial.com/rest/api/timeseries/historical",
                params={
                    "ric": ric,
                    "fids": "_DATE_END,CLOSE_PRC,OPEN_PRC,HIGH_1,LOW_1,ACVOL_1",
                    "samples": "D",
                    "appendRecentData": "all",
                    "fromDate": start.strftime("%Y-%m-%d"),
                    "toDate": end.strftime("%Y-%m-%d"),
                },
                headers=headers,
                timeout=60,
            )
            if response.status_code in {401, 403} and attempt == 0:
                self._lse_dory_token = None
                self._lse_dory_token_expiry = 0
                continue
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "OK":
                return None

            result = []
            for item in payload.get("data") or []:
                date_text = item.get("_DATE_END")
                close = self._lse_number(item.get("CLOSE_PRC"))
                if not date_text or close is None or close <= 0:
                    continue
                open_value = self._lse_number(item.get("OPEN_PRC"), close)
                high = self._lse_number(item.get("HIGH_1"), max(open_value or close, close))
                low = self._lse_number(item.get("LOW_1"), min(open_value or close, close))
                volume = self._lse_number(item.get("ACVOL_1"), 0) or 0
                try:
                    trade_date = pd.to_datetime(date_text).strftime("%Y-%m-%d")
                except Exception:
                    continue
                result.append(
                    {
                        "date": trade_date,
                        "open": round(open_value or close, 2),
                        "high": round(max(high or close, open_value or close, close), 2),
                        "low": round(min(low or close, open_value or close, close), 2),
                        "close": round(close, 2),
                        "volume": int(volume),
                    }
                )
            return sorted(result, key=lambda item: item["date"]) or None

        return None

    def _fetch_fund_nav_history(self, fund_code: str, value_field: str = "DWJZ") -> list | None:
        """从东方财富获取基金历史净值（最近两年）。"""
        try:
            session = requests.Session()
            session.trust_env = False
            session.proxies = {"http": None, "https": None}

            all_records = []
            page = 1
            while True:
                response = session.get(
                    "https://api.fund.eastmoney.com/f10/lsjz",
                    params={
                        "callback": "jQuery",
                        "fundCode": fund_code,
                        "pageIndex": page,
                        "pageSize": 200,
                        "_": int(time.time() * 1000),
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Referer": f"https://fund.eastmoney.com/{fund_code}.html",
                        "Host": "api.fund.eastmoney.com",
                    },
                    timeout=20,
                )
                text = response.text
                start = text.find("(")
                end = text.rfind(")")
                if start < 0 or end <= start:
                    break
                import json as _json
                payload = _json.loads(text[start + 1 : end])
                records = payload.get("Data", {}).get("LSJZList") or []
                if not records:
                    break
                all_records.extend(records)
                total_pages = int(payload.get("TotalCount", 0))
                if len(all_records) >= total_pages:
                    break
                page += 1
                if page > 30:
                    break

            if not all_records:
                return None

            result = []
            cutoff = (datetime.now() - timedelta(days=3650)).strftime("%Y-%m-%d")
            for rec in all_records:
                trade_date = str(rec.get("FSRQ") or "")
                if not trade_date or trade_date < cutoff:
                    continue
                nav = float(rec.get(value_field) or rec.get("DWJZ") or 0)
                if nav <= 0:
                    continue
                result.append({
                    "date": trade_date,
                    "open": round(nav, 4),
                    "high": round(nav, 4),
                    "low": round(nav, 4),
                    "close": round(nav, 4),
                    "volume": 0,
                })

            return sorted(result, key=lambda x: x["date"]) or None
        except Exception:
            return None

    def _normalize_history_frame(self, df: pd.DataFrame) -> list | None:
        if df is None or len(df) == 0:
            return None

        column_mapping = {
            "開盤": "open",
            "Open": "open",
            "open": "open",
            "最高": "high",
            "High": "high",
            "high": "high",
            "最低": "low",
            "Low": "low",
            "low": "low",
            "收盤": "close",
            "Close": "close",
            "close": "close",
            "成交量": "volume",
            "Volume": "volume",
            "volume": "volume",
            "日期": "date",
            "Date": "date",
            "date": "date",
        }

        rename_dict = {col: column_mapping[col] for col in df.columns if col in column_mapping}
        df = df.rename(columns=rename_dict)
        if "date" not in df.columns:
            return None

        result = []
        for _, row in df.iterrows():
            try:
                date = pd.to_datetime(row["date"]).strftime("%Y-%m-%d")
            except Exception:
                continue

            open_value = row.get("open", row.get("close", 0))
            high_value = row.get("high", row.get("close", 0))
            low_value = row.get("low", row.get("close", 0))
            close_value = row.get("close", 0)
            volume_value = row.get("volume", 0)
            result.append(
                {
                    "date": date,
                    "open": round(float(open_value or 0), 2),
                    "high": round(float(high_value or 0), 2),
                    "low": round(float(low_value or 0), 2),
                    "close": round(float(close_value or 0), 2),
                    "volume": int(float(volume_value or 0)),
                }
            )

        return result or None

    def fetch_from_remote(self, key: str, series: str = "price", period: str = "all") -> list | None:
        config = self._get_series_config(key, series)
        if not config:
            return None
        if config.get("history_available") is False:
            return None

        source = config.get("source")
        symbol = config.get("symbol")
        days = self._remote_days_for_period(period)

        try:
            if source == "global_em":
                return self._fetch_eastmoney_global_history(symbol)

            if source == "yahoo_chart":
                return self._fetch_yahoo_chart_history(symbol, days=days)

            if source == "chinabond":
                return self._fetch_chinabond_yield_history(
                    days=days,
                    field=config.get("chinabond_field", "tenYear")
                )

            if source == "us_treasury":
                months = 360 if days is None else max(2, int(days / 30) + 2)
                return self._fetch_us_treasury_yield_history(
                    months=months,
                    field=config.get("treasury_field", "BC_10YEAR")
                )

            if source == "computed_spread":
                return self._fetch_computed_spread_history(config.get("components") or [], period=period)

            if source == "computed_dividend_yield":
                return self._fetch_computed_dividend_yield_history(
                    key,
                    rolling_days=int(config.get("rolling_days") or 252),
                )

            if source == "ecb_yield":
                last_n = None if days is None else max(40, int(days * 1.6))
                return self._fetch_ecb_yield_history(config.get("ecb_series_key"), last_n=last_n)

            if source == "cboe_vix":
                return self._fetch_cboe_vix_history()

            if source == "coinbase_candles":
                return self._fetch_coinbase_candles(symbol, days=days)

            if source == "hsi_daily_bulletin":
                return self._fetch_hsi_daily_bulletin_history(config.get("series_code", "hsi"))

            if source == "stoxx_dax":
                return self._fetch_stoxx_dax_history(symbol)

            if source == "lse_dory":
                return self._fetch_lse_dory_history(symbol, days=days)

            if source == "csindex_perf":
                return self._fetch_csindex_perf_history(symbol, days=days)

            if source == "csindex_indicator":
                return self._fetch_csindex_indicator_history(
                    symbol,
                    value_field=config.get("value_field", "股息率1"),
                )

            if source == "cni_official":
                return self._fetch_cni_history(symbol, days=days)

            if source == "tx":
                if ak is not None:
                    df = ak.stock_zh_index_daily_tx(symbol=symbol)
                    return self._normalize_history_frame(df)
                return self._fetch_tencent_index_history(symbol, days=days)

            if source == "hk_sina":
                if ak is None:
                    return None
                df = ak.stock_hk_index_daily_sina(symbol=symbol)
                return self._normalize_history_frame(df)

            if source == "us_sina":
                if ak is None:
                    return None
                df = ak.index_us_stock_sina(symbol=symbol)
                return self._normalize_history_frame(df)

            if source == "futures":
                if ak is None:
                    return None
                df = ak.futures_foreign_hist(symbol=symbol)
                return self._normalize_history_frame(df)

            if source == "fund_nav":
                return self._fetch_fund_nav_history(symbol)

            if source == "fund_nav_accum":
                return self._fetch_fund_nav_history(symbol, value_field="LJJZ")

            return None
        except Exception:
            return None

    def get_history_data(
        self,
        key: str,
        period: str = "1y",
        force_update: bool = False,
        series: str = "price",
    ) -> list | None:
        config = self._get_series_config(key, series) or {}
        if config and config.get("history_available") is not False and not self._is_period_supported(config, period):
            return None

        local_data = None
        if not force_update:
            local_data = self.load_local_data(key, period, series)

        need_update = (
            force_update
            or not self._is_data_valid(key, series)
            or not self._local_data_covers_period(key, period, series, local_data)
        )

        if need_update or local_data is None:
            remote_data = self.fetch_from_remote(key, series, period=period)
            if remote_data:
                self.save_local_data(key, remote_data, series)
                return self.load_local_data(key, period, series) or self._annotate_rows(key, series, remote_data)

        return local_data

    def update_all_data(self):
        for key in self.INDICES:
            try:
                series_keys = list((self.INDICES[key].get("series") or {"price": {}}).keys())
                for series in series_keys:
                    data = self.fetch_from_remote(key, series)
                    if data:
                        self.save_local_data(key, data, series)
            except Exception:
                pass

    def get_data_info(self) -> dict:
        info = {
            "data_dir": str(self.DATA_DIR),
            "database": self.db.status(),
            "total_files": 0,
            "total_size_mb": 0,
            "indices": {},
        }

        if self.DATA_DIR.exists():
            for file_path in self.DATA_DIR.glob("*.csv"):
                key = file_path.stem
                size_mb = file_path.stat().st_size / (1024 * 1024)
                info["total_files"] += 1
                info["total_size_mb"] += size_mb
                info["indices"][key] = {
                    "size_mb": round(size_mb, 2),
                    "valid": self._is_data_valid(key),
                    "meta": self.meta.get(key, {}),
                }

        return info


_history_manager = None


def get_history_manager():
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryDataManager()
    return _history_manager
