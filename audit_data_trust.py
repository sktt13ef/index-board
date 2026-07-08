"""Read-only audit for dashboard data trust.

Default behavior prints a Markdown report to stdout. Use --write to update
DATA_TRUST_AUDIT.md after a repair.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from history_data_manager import get_history_manager
from market_cache import get_market_cache


REPORT_PATH = Path(__file__).with_name("DATA_TRUST_AUDIT.md")


def load_valuations(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = conn.execute("SELECT key, payload, source, data_end FROM valuations").fetchall()
    result = {}
    for key, payload, source, data_end in rows:
        try:
            parsed = json.loads(payload or "{}")
        except Exception:
            parsed = {}
        parsed.setdefault("source", source)
        parsed.setdefault("data_end", data_end)
        result[key] = parsed
    return result


def history_stats(conn: sqlite3.Connection, key: str, series: str) -> dict:
    row = conn.execute(
        """
        SELECT COUNT(*) AS row_count,
               MIN(date) AS data_start,
               MAX(date) AS data_end,
               SUM(CASE WHEN close < 0 THEN 1 ELSE 0 END) AS negative_count
        FROM history_points
        WHERE key = ? AND series = ?
        """,
        (key, series),
    ).fetchone()
    return {
        "row_count": int(row[0] or 0),
        "data_start": row[1] or "",
        "data_end": row[2] or "",
        "negative_count": int(row[3] or 0),
    }


def valuation_type(payload: dict | None) -> str:
    if not payload:
        return "none"
    if payload.get("pe") is not None:
        return "pe_percentile"
    if payload.get("valuation_type"):
        return str(payload["valuation_type"])
    if payload.get("is_price_percentile"):
        return "price_percentile"
    return "unknown"


def build_report() -> str:
    manager = get_history_manager()
    db = get_market_cache()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(db.db_path) as conn:
        valuations = load_valuations(conn)
        lines = [
            "# 数据可信度审计报告",
            "",
            f"生成时间：{generated_at}",
            "",
            "| 标的 | 序列 | 行数 | 起止日期 | 负值 | 收益口径 | 估值类型 | 可十年分位 | 可对比图 |",
            "| --- | --- | ---: | --- | ---: | --- | --- | --- | --- |",
        ]
        for key in sorted(manager.INDICES):
            series_map = (manager.INDICES.get(key, {}) or {}).get("series") or {"price": {}}
            for series in sorted(series_map):
                meta = manager.history_meta(key, series)
                stats = history_stats(conn, key, series)
                row_count = stats["row_count"] or meta.get("row_count", 0)
                data_start = stats["data_start"] or meta.get("data_start") or ""
                data_end = stats["data_end"] or meta.get("data_end") or ""
                vtype = valuation_type(valuations.get(key)) if series == "price" else ""
                lines.append(
                    "| {key} | {series} | {rows} | {start} - {end} | {neg} | {return_kind} | {vtype} | {ten_year} | {compare} |".format(
                        key=key,
                        series=series,
                        rows=row_count,
                        start=data_start or "--",
                        end=data_end or "--",
                        neg=stats["negative_count"],
                        return_kind=meta.get("return_kind_label") or meta.get("return_kind") or "",
                        vtype=vtype,
                        ten_year="yes" if meta.get("can_show_ten_year") else "no",
                        compare="yes" if meta.get("can_compare_total_return") and row_count else "no",
                    )
                )

        return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write DATA_TRUST_AUDIT.md")
    args = parser.parse_args()
    report = build_report()
    if args.write:
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(f"wrote {REPORT_PATH.name}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
