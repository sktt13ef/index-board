"""Audit dashboard history curves and write CURVE_QUALITY_REPORT.md."""

from __future__ import annotations

import argparse
import math
from datetime import datetime
from pathlib import Path

from history_data_manager import HistoryDataManager
from market_sources import get_source_entry


REPORT_PATH = Path(__file__).parent / "CURVE_QUALITY_REPORT.md"
PERIODS = ["1mo", "3mo", "6mo", "1y", "3y", "5y", "10y", "all"]


def parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d")
    except Exception:
        return None


def pct_change(prev: float, curr: float) -> float | None:
    if prev in (None, 0) or curr is None:
        return None
    try:
        return (float(curr) / float(prev) - 1) * 100
    except Exception:
        return None


def mark(status: str, new_status: str) -> str:
    order = {"PASS": 0, "WARN": 1, "FAIL": 2}
    return new_status if order[new_status] > order[status] else status


def source_quality(series: str, label: str, source: str, registry_entry: dict) -> tuple[str, str]:
    if series != "total_return":
        return "PASS", "价格/指数收益口径"
    if "代理" in label or "同源" in label or "复权" in label:
        return "FAIL", "proxy/same_source/adjusted close 误挂为 total_return"
    if not registry_entry.get("supports_total_return"):
        return "FAIL", "registry 不允许该标的展示 total_return"
    expected_code = registry_entry.get("total_return_index_code")
    if not expected_code:
        return "FAIL", "缺少官方全收益代码"
    if source not in {"csindex_perf", "yahoo_chart", "tx"}:
        return "WARN", f"total_return 来源需复核：{source}"
    return "PASS", f"官方全收益代码 {expected_code}"


def period_availability(manager: HistoryDataManager, key: str, series: str) -> dict[str, int]:
    result = {}
    for period in PERIODS:
        rows = manager.get_history_data(key, period, series=series) or []
        result[period] = len(rows)
    return result


def analyze_rows(
    manager: HistoryDataManager,
    key: str,
    series: str,
    label: str,
    source: str,
    symbol: str,
    rows: list[dict],
    price_rows: list[dict] | None = None,
) -> dict:
    status = "PASS"
    warnings: list[str] = []
    errors: list[str] = []
    registry = get_source_entry(key) or {}

    if not rows:
        return {
            "status": "FAIL",
            "rows": 0,
            "start_date": "-",
            "end_date": "-",
            "source_signature": manager._source_signature(key, series),
            "warnings": "",
            "errors": "无历史数据",
            "periods": {},
        }

    date_strings = [str(row.get("date")) for row in rows]
    parsed_dates = [parse_date(value) for value in date_strings]
    values = [float(row.get("close") or 0) for row in rows]

    if any(not date for date in parsed_dates):
        errors.append("存在无法解析日期")
        status = "FAIL"
    if parsed_dates != sorted(parsed_dates):
        errors.append("日期乱序")
        status = "FAIL"
    duplicate_count = len(date_strings) - len(set(date_strings))
    if duplicate_count:
        errors.append(f"日期重复 {duplicate_count} 个")
        status = "FAIL"
    if any(value <= 0 or math.isnan(value) for value in values):
        errors.append("存在非正数/NaN")
        status = "FAIL"
    if "1990-01-01" in date_strings:
        errors.append("存在 1990-01-01 假基准行")
        status = "FAIL"

    valid_dates = [date for date in parsed_dates if date]
    max_gap = 0
    if len(valid_dates) > 1:
        max_gap = max((valid_dates[i] - valid_dates[i - 1]).days for i in range(1, len(valid_dates)))
        if max_gap > 14:
            warnings.append(f"最大自然日缺口 {max_gap} 天")
            status = mark(status, "WARN")

    jumps = []
    for idx in range(1, len(values)):
        change = pct_change(values[idx - 1], values[idx])
        threshold = 50 if key in {"CN10Y", "US10Y", "OIL_WTI", "GOLD"} else 25
        if change is not None and abs(change) >= threshold:
            jumps.append(f"{date_strings[idx]} {change:+.2f}%")
    if jumps:
        warnings.append(f"异常单日跳变 {len(jumps)} 个：" + ", ".join(jumps[:3]))
        status = mark(status, "WARN")

    start_date = date_strings[0]
    end_date = date_strings[-1]
    first_year = parse_date(start_date).year if parse_date(start_date) else None
    if registry.get("supports_chart") and first_year and first_year > datetime.now().year:
        errors.append(f"成立以来首日异常：{start_date}")
        status = "FAIL"
    if key.startswith("CSI") and "DIVIDEND" in key and start_date > "2007-01-01":
        warnings.append(f"中证红利低波系列起点偏晚：{start_date}")
        status = mark(status, "WARN")

    source_status, source_note = source_quality(series, label, source, registry)
    if source_status == "FAIL":
        errors.append(source_note)
        status = "FAIL"
    elif source_status == "WARN":
        warnings.append(source_note)
        status = mark(status, "WARN")
    else:
        warnings.append(source_note)

    if series == "total_return" and price_rows:
        try:
            price_return = float(price_rows[-1]["close"]) / float(price_rows[0]["close"])
            total_return = float(rows[-1]["close"]) / float(rows[0]["close"])
            if total_return < price_return * 0.85:
                warnings.append(f"total_return 明显低于 price：{total_return:.2f} vs {price_return:.2f}")
                status = mark(status, "WARN")
        except Exception:
            pass

    return {
        "status": status,
        "rows": len(rows),
        "start_date": start_date,
        "end_date": end_date,
        "source_signature": manager._source_signature(key, series),
        "warnings": "；".join(warnings),
        "errors": "；".join(errors),
        "periods": period_availability(manager, key, series),
        "max_gap": max_gap,
        "source": source,
        "symbol": symbol,
    }


def audit(force: bool = False) -> list[dict]:
    manager = HistoryDataManager()
    records = []
    for key, config in manager.INDICES.items():
        series_map = config.get("series") or {"price": {"label": "指数收益"}}
        price_rows = manager.get_history_data(key, "all", force_update=force, series="price") or []
        for series, series_config in series_map.items():
            merged = manager._get_series_config(key, series) or {}
            label = series_config.get("label", series)
            rows = price_rows if series == "price" else manager.get_history_data(key, "all", force_update=force, series=series) or []
            analysis = analyze_rows(
                manager,
                key,
                series,
                label,
                merged.get("source", config.get("source", "")),
                merged.get("symbol", config.get("symbol", "")),
                rows,
                price_rows=price_rows,
            )
            records.append({
                "key": key,
                "name": config.get("name", key),
                "series": series,
                "label": label,
                **analysis,
            })
    return records


def write_report(records: list[dict]) -> None:
    counts = {
        "PASS": sum(row["status"] == "PASS" for row in records),
        "WARN": sum(row["status"] == "WARN" for row in records),
        "FAIL": sum(row["status"] == "FAIL" for row in records),
    }
    lines = [
        "# 曲线质量审计报告",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"结果汇总：PASS {counts['PASS']}，WARN {counts['WARN']}，FAIL {counts['FAIL']}。",
        "",
        "| 状态 | 标的 | 曲线 | 行数 | 起点 | 终点 | 来源 | 代码 | source_signature | warnings | errors | periods |",
        "|---|---|---|---:|---|---|---|---|---|---|---|---|",
    ]
    for row in records:
        periods = ", ".join(f"{k}:{v}" for k, v in row.get("periods", {}).items())
        lines.append(
            "| {status} | {name} ({key}) | {label} | {rows} | {start_date} | {end_date} | {source} | {symbol} | `{source_signature}` | {warnings} | {errors} | {periods} |".format(
                periods=periods,
                **row,
            )
        )
    lines.extend([
        "",
        "## 说明",
        "",
        "- `FAIL` 表示该曲线不能被视为可信展示数据。",
        "- `WARN` 表示口径、缺口、代理或异常波动需要页面明确提示。",
        "- period 行数为当前 API 可返回数量；DAX 只能允许 1mo/3mo。",
    ])
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="ignore local cache and refetch remote series")
    args = parser.parse_args()
    records = audit(force=args.force)
    write_report(records)
    counts = {
        "PASS": sum(row["status"] == "PASS" for row in records),
        "WARN": sum(row["status"] == "WARN" for row in records),
        "FAIL": sum(row["status"] == "FAIL" for row in records),
    }
    print(f"report={REPORT_PATH}")
    print(f"pass={counts['PASS']} warn={counts['WARN']} fail={counts['FAIL']}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
