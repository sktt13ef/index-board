"""Repair known data-trust cache issues.

This script intentionally performs only targeted cache maintenance:
- rebuild spread histories so negative values are preserved;
- clear and recompute valuation payloads so stale DAX/price-percentile data is removed;
- checkpoint SQLite after the repair.
"""

from __future__ import annotations

import sqlite3

from history_data_manager import get_history_manager
from market_cache import get_market_cache
from stock_data import StockDataProvider


SPREAD_KEYS = ("CN_US_10Y_SPREAD", "US10Y_2Y_SPREAD", "CN10Y_1Y_SPREAD")


def main() -> int:
    db = get_market_cache()
    manager = get_history_manager()

    for key in SPREAD_KEYS:
        db.clear_history(key, "price")
        rows = manager.get_history_data(key, "all", force_update=True, series="price") or []
        negative_count = sum(1 for row in rows if float(row.get("close") or 0) < 0)
        print(f"{key}: rebuilt {len(rows)} rows, negatives={negative_count}")

    db.clear_valuation()
    provider = StockDataProvider()
    provider.update_valuation_cache()
    print("valuations: cleared and recomputed")

    with sqlite3.connect(db.db_path) as conn:
        print("integrity:", conn.execute("PRAGMA integrity_check").fetchone()[0])
        print("checkpoint:", conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
