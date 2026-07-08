"""Rebuild history series that should have deeper free/official coverage."""

from __future__ import annotations

from history_data_manager import HistoryDataManager


REBUILD_SERIES = [
    ("CSI300", "total_return"),
    ("CSI500", "total_return"),
    ("CSI_ALL_SHARE", "total_return"),
    ("CSI_BAIJIU", "total_return"),
    ("STAR50", "total_return"),
    ("STAR100", "total_return"),
    ("FTSE100", "total_return"),
    ("CSI_DIVIDEND", "price"),
    ("CSI_DIVIDEND", "total_return"),
    ("CSI_DIVIDEND_100", "price"),
    ("CSI_DIVIDEND_100", "total_return"),
    ("CSI300_DIVIDEND_LOW_VOL", "price"),
    ("CSI300_DIVIDEND_LOW_VOL", "total_return"),
]

DERIVED_SERIES = [
    ("CSI_DIVIDEND", "dividend_return"),
    ("CSI_DIVIDEND_100", "dividend_return"),
    ("CSI300_DIVIDEND_LOW_VOL", "dividend_return"),
    ("CSI_DIVIDEND_QUALITY", "dividend_return"),
    ("CSI_ALL_DIVIDEND_QUALITY", "dividend_return"),
    ("CSI_CASH_FLOW", "dividend_return"),
    ("CNI_FREE_CASH_FLOW", "dividend_return"),
]


def rebuild_series(manager: HistoryDataManager, key: str, series: str) -> dict:
    manager.clear_local_data(key, series)
    rows = manager.get_history_data(key, "all", force_update=True, series=series) or []
    meta = manager.history_meta(key, series)
    return {
        "key": key,
        "series": series,
        "rows": len(rows),
        "row_count": meta.get("row_count"),
        "start": meta.get("data_start"),
        "end": meta.get("data_end"),
        "source": meta.get("source"),
    }


def main() -> int:
    manager = HistoryDataManager()
    failures = []
    for key, series in [*REBUILD_SERIES, *DERIVED_SERIES]:
        print(f"rebuild {key} {series}", flush=True)
        result = rebuild_series(manager, key, series)
        print(
            f"  rows={result['row_count']} start={result['start']} end={result['end']} source={result['source']}",
            flush=True,
        )
        if not result["row_count"]:
            failures.append((key, series))

    if failures:
        print("failed series:")
        for key, series in failures:
            print(f"  {key} {series}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
