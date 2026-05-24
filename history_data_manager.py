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

import akshare as ak
import pandas as pd
import requests


class HistoryDataManager:
    """Local CSV-backed history cache."""

    DATA_DIR = Path(__file__).parent / "data" / "history"
    DATA_TTL_HOURS = 24
    PERIOD_DAYS = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "10y": 3650}

    INDICES = {
        "CSI300": {"name": "沪深300", "symbol": "sh000300", "source": "tx"},
        "CSI500": {"name": "中证A500", "symbol": "sh000510", "source": "tx"},
        "CSI_BAIJIU": {"name": "中证白酒指数", "symbol": "sz399997", "source": "tx"},
        "CHINEXT":    {"name": "创业板指",     "symbol": "sz399006", "source": "tx"},
        "STAR50":     {"name": "科创50",       "symbol": "sh000688", "source": "tx"},
        "STAR100":    {"name": "科创100",      "symbol": "sh000698", "source": "tx"},
        "HSTECH": {
            "name": "恒生科技指数",
            "symbol": "HSTECH",
            "source": "hk_sina",
        },
        "HSI": {
            "name": "恒生指数",
            "symbol": "HSI",
            "source": "hsi_daily_bulletin",
            "series_code": "hsi",
        },
        "NDX": {"name": "纳斯达克100", "symbol": ".NDX", "source": "us_sina"},
        "SPX": {"name": "标普500", "symbol": ".INX", "source": "us_sina"},
        "XOP": {"name": "标普油气ETF", "symbol": "XOP", "source": "us_sina"},
        "WANJIA_GOLD": {"name": "万家周期视野C", "symbol": "025446", "source": "fund_nav"},
        "DAX": {
            "name": "德国DAX",
            "symbol": "GDAXI",
            "source": "stoxx_dax",
            "history_available": True,
            "history_max_period": "3mo",
            "history_note": "STOXX 公开免费历史文件仅提供近3个月数据；1月/3月可展示，6月/1年暂不开放。",
        },
        "GOLD": {"name": "黄金", "symbol": "GC", "source": "futures"},
        "OIL_WTI": {"name": "WTI原油", "symbol": "CL", "source": "futures"},
        "CN10Y": {"name": "中国国债十年收益率", "symbol": "CN10Y", "source": "chinabond"},
        "US10Y": {"name": "美国国债十年收益率", "symbol": "US10Y", "source": "us_treasury"},
        "CSI_DIVIDEND": {
            "name": "中证红利低波动",
            "symbol": "sh560150",
            "source": "tx",
            "is_etf": True,
        },
    }

    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.DATA_DIR / "meta.json"
        self.meta = self._load_meta()

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

    def _get_file_path(self, key: str) -> Path:
        return self.DATA_DIR / f"{key}.csv"

    def _period_to_days(self, period: str) -> int:
        return self.PERIOD_DAYS.get(period, 365)

    def _is_period_supported(self, config: dict, period: str) -> bool:
        max_period = config.get("history_max_period")
        if not max_period:
            return True
        return self._period_to_days(period) <= self._period_to_days(max_period)

    def _is_data_valid(self, key: str) -> bool:
        if key not in self.meta:
            return False
        last_update = self.meta[key].get("last_update", 0)
        elapsed_hours = (time.time() - last_update) / 3600
        return elapsed_hours < self.DATA_TTL_HOURS

    def load_local_data(self, key: str, period: str = "1y") -> list | None:
        file_path = self._get_file_path(key)
        config = self.INDICES.get(key, {})
        if config.get("history_available") is False:
            return None
        if not self._is_period_supported(config, period):
            return None
        if not file_path.exists():
            return None

        try:
            df = pd.read_csv(file_path)
            df["date"] = pd.to_datetime(df["date"])

            days = self._period_to_days(period)
            start_date = datetime.now() - timedelta(days=days)
            df = df[df["date"] >= start_date].sort_values("date")

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
            return result
        except Exception:
            return None

    def save_local_data(self, key: str, data: list):
        if not data:
            return

        try:
            file_path = self._get_file_path(key)
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])

            if file_path.exists():
                try:
                    existing_df = pd.read_csv(file_path)
                    existing_df["date"] = pd.to_datetime(existing_df["date"])
                    df = pd.concat([existing_df, df], ignore_index=True)
                    df = df.drop_duplicates(subset=["date"], keep="last")
                except Exception:
                    pass

            cutoff_date = datetime.now() - timedelta(days=3700)
            df = df[df["date"] >= cutoff_date].sort_values("date")
            df.to_csv(file_path, index=False)

            self.meta[key] = {
                "last_update": time.time(),
                "record_count": len(df),
                "date_range": {
                    "start": df["date"].min().strftime("%Y-%m-%d"),
                    "end": df["date"].max().strftime("%Y-%m-%d"),
                },
            }
            self._save_meta()
        except Exception:
            pass

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

    def _fetch_chinabond_yield_history(self, days: int = 3650) -> list | None:
        """中债接口超过~2年会超时，分段拉取再合并。"""
        url = "https://yield.chinabond.com.cn/cbweb-mn/pgxh/historyQuery"
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}

        end_overall = datetime.now()
        start_overall = end_overall - timedelta(days=days)
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
                    value = row.get("tenYear")
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

    def _fetch_us_treasury_yield_history(self, months: int = 120) -> list | None:
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
                value_text = props.findtext("d:BC_10YEAR", default="", namespaces=ns)
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

    def _fetch_stoxx_dax_history(self) -> list | None:
        """Fetch the public STOXX 3-month DAX history file."""
        url = "https://www.stoxx.com/documents/stoxxnet/Documents/Indices/Current/HistoricalData/h_3mdax.txt"
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

    def _fetch_fund_nav_history(self, fund_code: str) -> list | None:
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
                nav = float(rec.get("DWJZ") or 0)
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

    def fetch_from_remote(self, key: str) -> list | None:
        config = self.INDICES.get(key)
        if not config:
            return None
        if config.get("history_available") is False:
            return None

        source = config.get("source")
        symbol = config.get("symbol")

        try:
            if source == "global_em":
                return self._fetch_eastmoney_global_history(symbol)

            if source == "chinabond":
                return self._fetch_chinabond_yield_history()

            if source == "us_treasury":
                return self._fetch_us_treasury_yield_history()

            if source == "hsi_daily_bulletin":
                return self._fetch_hsi_daily_bulletin_history(config.get("series_code", "hsi"))

            if source == "stoxx_dax":
                return self._fetch_stoxx_dax_history()

            if source == "tx":
                df = ak.stock_zh_index_daily_tx(symbol=symbol)
                return self._normalize_history_frame(df)

            if source == "hk_sina":
                df = ak.stock_hk_index_daily_sina(symbol=symbol)
                return self._normalize_history_frame(df)

            if source == "us_sina":
                df = ak.index_us_stock_sina(symbol=symbol)
                return self._normalize_history_frame(df)

            if source == "futures":
                df = ak.futures_foreign_hist(symbol=symbol)
                return self._normalize_history_frame(df)

            if source == "fund_nav":
                return self._fetch_fund_nav_history(symbol)

            return None
        except Exception:
            return None

    def get_history_data(self, key: str, period: str = "1y", force_update: bool = False) -> list | None:
        config = self.INDICES.get(key, {})
        if config and config.get("history_available") is not False and not self._is_period_supported(config, period):
            return None

        need_update = force_update or not self._is_data_valid(key)

        local_data = None
        if not force_update:
            local_data = self.load_local_data(key, period)

        if need_update or local_data is None:
            remote_data = self.fetch_from_remote(key)
            if remote_data:
                self.save_local_data(key, remote_data)
                return self.load_local_data(key, period) or remote_data

        return local_data

    def update_all_data(self):
        for key in self.INDICES:
            try:
                data = self.fetch_from_remote(key)
                if data:
                    self.save_local_data(key, data)
            except Exception:
                pass

    def get_data_info(self) -> dict:
        info = {
            "data_dir": str(self.DATA_DIR),
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
