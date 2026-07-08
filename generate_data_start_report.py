"""Write a report with start/end dates for every cached history series."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path("data/market_cache.sqlite3")
OUT_PATH = Path("DATA_START_REPORT.md")


FALLBACK_NAMES = {
    "BTCUSD": "Bitcoin",
    "CAC40": "France CAC40",
    "CHINEXT": "ChiNext",
    "CN10Y": "China 10Y Treasury Yield",
    "CN10Y_1Y_SPREAD": "China 10Y-1Y Spread",
    "CN1Y": "China 1Y Treasury Yield",
    "CN30Y": "China 30Y Treasury Yield",
    "CNI_FREE_CASH_FLOW": "CNI Free Cash Flow",
    "CN_US_10Y_SPREAD": "China-US 10Y Spread",
    "CSI1000": "CSI 1000",
    "CSI2000": "CSI 2000",
    "CSI300": "CSI 300",
    "CSI300_DIVIDEND_LOW_VOL": "CSI 300 Dividend Low Volatility",
    "CSI500": "CSI A500",
    "CSI500_INDEX": "CSI 500",
    "CSI_ALL_DIVIDEND_QUALITY": "CSI Dividend Quality",
    "CSI_ALL_SHARE": "CSI All Share",
    "CSI_BAIJIU": "CSI Baijiu",
    "CSI_CASH_FLOW": "CSI Cash Flow",
    "CSI_DIVIDEND": "CSI Dividend Low Volatility",
    "CSI_DIVIDEND_100": "CSI Dividend Low Volatility 100",
    "CSI_DIVIDEND_QUALITY": "Dividend Quality",
    "DAX": "Germany DAX",
    "ETHUSD": "Ethereum",
    "EU10Y": "Euro Area 10Y AAA Yield",
    "FTSE100": "UK FTSE 100",
    "GOLD": "Gold",
    "HSI": "Hang Seng Index",
    "HSTECH": "Hang Seng Tech Index",
    "NDX": "Nasdaq 100",
    "OIL_WTI": "WTI Crude Oil",
    "SPX": "S&P 500",
    "STAR100": "STAR 100",
    "STAR50": "STAR 50",
    "US10Y": "US 10Y Treasury Yield",
    "US10Y_2Y_SPREAD": "US 10Y-2Y Spread",
    "US2Y": "US 2Y Treasury Yield",
    "US3M": "US 13 Week T-Bill Yield",
    "USDCNY": "USD/CNY",
    "VIX": "VIX",
    "WANJIA_GOLD": "Wanjia Cycle Vision C",
    "XOP": "SPDR S&P Oil & Gas ETF",
}


def load_snapshot_names(conn: sqlite3.Connection) -> dict[str, str]:
    names = {}
    for row in conn.execute("SELECT key, payload FROM snapshots"):
        try:
            payload = json.loads(row["payload"])
        except Exception:
            continue
        if payload.get("name"):
            names[row["key"]] = payload["name"]
    return names


def format_series(series_by_key: dict, key: str, series: str) -> str:
    row = series_by_key.get(key, {}).get(series)
    if not row:
        return "none"
    return f"{row['start_date']} -> {row['end_date']} ({row['row_count']}, {row['source'] or 'unknown'})"


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    names = load_snapshot_names(conn)

    series_by_key: dict[str, dict[str, sqlite3.Row]] = {}
    for row in conn.execute(
        """
        SELECT key, series, source, source_symbol, row_count, start_date, end_date
        FROM history_meta
        ORDER BY key, series
        """
    ):
        series_by_key.setdefault(row["key"], {})[row["series"]] = row

    keys = sorted(set(series_by_key) | set(names))
    lines = [
        "# Data Start Report",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| Key | Name | Price | Total return | Dividend return | Dividend yield |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for key in keys:
        name = names.get(key) or FALLBACK_NAMES.get(key) or key
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} |".format(
                key,
                name,
                format_series(series_by_key, key, "price"),
                format_series(series_by_key, key, "total_return"),
                format_series(series_by_key, key, "dividend_return"),
                format_series(series_by_key, key, "dividend_yield"),
            )
        )

    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
