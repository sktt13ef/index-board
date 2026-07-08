"""Hard-gate validation for stock_dashboard data credibility."""

from __future__ import annotations

import inspect
import math
import sys
from datetime import datetime
from pathlib import Path

from history_data_manager import get_history_manager
from market_sources import (
    OFFICIAL_TOTAL_RETURN_CODES,
    get_source_entry,
    get_source_registry,
    validate_source_registry,
)
from stock_data import StockDataProvider


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


REPORT_PATH = Path(__file__).parent / "VALIDATION_REPORT.md"
VISIBLE_KEYS = list(get_source_registry().keys())
CARD_REQUIRED_FIELDS = [
    "update_label",
    "source_label",
    "source_url",
    "data_as_of",
    "fetched_at",
    "data_note",
]
MAX_STALE_BY_FREQUENCY = {
    "realtime": 15 * 60,
    "delayed": 24 * 60 * 60,
    "daily": 36 * 60 * 60,
}
CSI_DIVIDEND_CODES = {
    "CSI_DIVIDEND": ("H30269", "H20269"),
    "CSI_DIVIDEND_100": ("930955", "H20955"),
    "CSI300_DIVIDEND_LOW_VOL": ("930740", "H20740"),
    "CSI_DIVIDEND_QUALITY": ("931468", "921468"),
    "CSI_ALL_DIVIDEND_QUALITY": ("932315", "932315CNY010"),
    "CSI_CASH_FLOW": ("932365", "932365CNY010"),
    "CNI_FREE_CASH_FLOW": ("980092", "480092"),
}
OFFICIAL_DERIVED_DIVIDEND_RETURN_KEYS = {
    "CSI_DIVIDEND",
    "CSI_DIVIDEND_100",
    "CSI300_DIVIDEND_LOW_VOL",
    "CSI_DIVIDEND_QUALITY",
    "CSI_ALL_DIVIDEND_QUALITY",
    "CSI_CASH_FLOW",
    "CNI_FREE_CASH_FLOW",
}
CSI_OFFICIAL_DIVIDEND_YIELD_KEYS = {
    "CSI_DIVIDEND",
    "CSI_DIVIDEND_100",
    "CSI300_DIVIDEND_LOW_VOL",
    "CSI_DIVIDEND_QUALITY",
    "CSI_ALL_DIVIDEND_QUALITY",
    "CSI_CASH_FLOW",
}


class Recorder:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, status: str, key: str, check: str, message: str):
        self.rows.append({"status": status, "key": key, "check": check, "message": message})

    def pass_(self, key: str, check: str, message: str = "OK"):
        self.add("PASS", key, check, message)

    def warn(self, key: str, check: str, message: str):
        self.add("WARN", key, check, message)

    def fail(self, key: str, check: str, message: str):
        self.add("FAIL", key, check, message)

    def counts(self) -> dict[str, int]:
        return {
            "PASS": sum(row["status"] == "PASS" for row in self.rows),
            "WARN": sum(row["status"] == "WARN" for row in self.rows),
            "FAIL": sum(row["status"] == "FAIL" for row in self.rows),
        }


def near(left, right, tolerance=0.08) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except Exception:
        return False


def pct_near(price, prev_close, change_pct, tolerance=0.08) -> bool:
    try:
        prev = float(prev_close)
        if prev == 0:
            return True
        implied = (float(price) - prev) / prev * 100
        return abs(implied - float(change_pct)) <= tolerance
    except Exception:
        return False


def seconds_old(timestamp: str) -> float | None:
    try:
        return (datetime.now() - datetime.fromisoformat(timestamp)).total_seconds()
    except Exception:
        return None


def check_parser_contracts(rec: Recorder):
    source = inspect.getsource(StockDataProvider.get_sina_data)
    parser_checks = {
        "SPX": [
            'price = float(parts[1])',
            'open_price = float(parts[5])',
            'high = float(parts[6])',
            'low = float(parts[7])',
            'prev_close = float(parts[26])',
        ],
        "HSTECH": [
            'price = float(parts[6])',
            'change = float(parts[7])',
            'change_pct = float(parts[8])',
            'parts[17]',
            'parts[18]',
        ],
    }
    for key, snippets in parser_checks.items():
        for snippet in snippets:
            if snippet in source:
                rec.pass_(key, "parser_contract", snippet)
            else:
                rec.fail(key, "parser_contract", f"missing parser snippet: {snippet}")


def check_registry(rec: Recorder):
    issues = validate_source_registry()
    if not issues:
        rec.pass_("registry", "required_fields", "source registry complete")
    else:
        for issue in issues:
            rec.fail("registry", "required_fields", issue)

    registry = get_source_registry()
    for key, (price_code, total_code) in CSI_DIVIDEND_CODES.items():
        entry = registry.get(key) or {}
        if entry.get("price_index_code") == price_code and entry.get("total_return_index_code") == total_code:
            rec.pass_(key, "csi_dividend_codes", f"{price_code}/{total_code}")
        else:
            rec.fail(key, "csi_dividend_codes", f"expected {price_code}/{total_code}, got {entry}")

    dax = registry.get("DAX") or {}
    if dax.get("allowed_periods") == ["1mo", "3mo"]:
        rec.pass_("DAX", "allowed_periods", "1mo/3mo only")
    else:
        rec.fail("DAX", "allowed_periods", f"unexpected periods: {dax.get('allowed_periods')}")


def check_cards(rec: Recorder, provider: StockDataProvider, stocks: dict):
    missing = [key for key in VISIBLE_KEYS if key not in stocks]
    tolerated_missing = []
    hard_missing = []
    for key in missing:
        entry = get_source_entry(key) or {}
        if key == "DAX" and entry.get("allowed_periods") == ["1mo", "3mo"]:
            tolerated_missing.append(key)
        else:
            hard_missing.append(key)
    if hard_missing:
        rec.fail("cards", "visible_symbols", f"missing card snapshots: {', '.join(hard_missing)}")
    elif tolerated_missing:
        rec.warn("cards", "visible_symbols", f"temporarily unavailable snapshots: {', '.join(tolerated_missing)}")
    else:
        rec.pass_("cards", "visible_symbols", f"{len(VISIBLE_KEYS)} visible symbols returned")

    for key in VISIBLE_KEYS:
        item = stocks.get(key)
        if not item:
            continue
        entry = get_source_entry(key) or {}
        for field in CARD_REQUIRED_FIELDS:
            if item.get(field) in (None, ""):
                rec.fail(key, "card_required_fields", f"missing {field}")
            else:
                rec.pass_(key, f"card_field:{field}")

        try:
            price_value = float(item.get("price"))
            price_is_finite = math.isfinite(price_value)
        except Exception:
            price_value = None
            price_is_finite = False
        if not price_is_finite:
            rec.fail(key, "positive_price", f"invalid price {item.get('price')}")
        elif str(entry.get("asset_type") or "").endswith("_spread"):
            rec.pass_(key, "positive_price", "spread may be negative")
        elif price_value <= 0:
            rec.fail(key, "positive_price", f"non-positive price {item.get('price')}")
        else:
            rec.pass_(key, "positive_price")

        if not near(float(item["price"]) - float(item["prev_close"]), item["change"]):
            rec.fail(key, "change_math", f"price-prev_close != change ({item.get('price')}, {item.get('prev_close')}, {item.get('change')})")
        else:
            rec.pass_(key, "change_math")

        asset_type = str(entry.get("asset_type") or "")
        if asset_type in {"bond_yield", "yield_spread"}:
            rec.pass_(key, "change_pct_math", "yield/spread pct may use source-specific point-change convention")
        elif not pct_near(item["price"], item["prev_close"], item["change_pct"]):
            rec.fail(key, "change_pct_math", f"change_pct mismatch: {item.get('change_pct')}")
        else:
            rec.pass_(key, "change_pct_math")

        trust = item.get("source_trust") or {}
        if not trust.get("label") or trust.get("label") not in {"官方", "官方延迟", "第三方", "备用源"}:
            rec.fail(key, "source_trust", f"invalid source_trust: {trust}")
        else:
            rec.pass_(key, "source_trust", trust.get("label"))

        age = seconds_old(item.get("fetched_at") or item.get("timestamp"))
        max_age = MAX_STALE_BY_FREQUENCY.get(item.get("update_frequency"), 24 * 3600)
        if age is None:
            rec.fail(key, "freshness", "invalid fetched_at")
        elif age > max_age:
            rec.fail(key, "freshness", f"stale snapshot: {age:.0f}s > {max_age}s")
        else:
            rec.pass_(key, "freshness", f"{age:.0f}s")

        valuation = item.get("valuation")
        if valuation and valuation.get("is_simulated"):
            rec.fail(key, "valuation_real", "simulated valuation leaked")
        elif key == "DAX" and valuation:
            rec.fail(key, "valuation_scope", "DAX short official history must not display 10-year/ETF price percentile")
        elif key in {"XOP", "WANJIA_GOLD", "GOLD", "OIL_WTI", "CN10Y", "US10Y"} and valuation and not valuation.get("is_price_percentile"):
            rec.fail(key, "valuation_scope", "PE tile leaked to non-equity-index asset")
        elif key in {"XOP", "WANJIA_GOLD"} and valuation:
            rec.fail(key, "valuation_scope", "valuation tile should not display for XOP/WANJIA_GOLD")
        else:
            rec.pass_(key, "valuation_scope")

        if key == "SPX" and valuation:
            source_text = str(valuation.get("source") or "")
            if "官方" in source_text and "multpl" not in source_text.lower():
                rec.fail(key, "spx_valuation_trust", f"SPX valuation must not claim official: {source_text}")
            else:
                rec.pass_(key, "spx_valuation_trust", source_text)

        if entry.get("trust_label") == "官方" and item.get("source_trust", {}).get("label") not in {"官方", "备用源"}:
            rec.warn(key, "registry_vs_runtime_trust", f"runtime {item.get('source_trust')} differs from registry official source")


def check_history(rec: Recorder, provider: StockDataProvider):
    manager = get_history_manager()
    registry = get_source_registry()
    for key, entry in registry.items():
        if not entry.get("supports_chart"):
            continue
        price_history = provider.get_historical_data(key, "1mo", series="price")
        if not price_history:
            rec.fail(key, "price_history", "missing 1mo price history")
            continue
        rec.pass_(key, "price_history", f"{len(price_history)} rows")
        latest = price_history[-1]
        for field in ["series", "source_signature"]:
            if latest.get(field) in (None, ""):
                rec.fail(key, "history_provenance", f"latest row missing {field}")
            else:
                rec.pass_(key, f"history_provenance:{field}")

        if latest.get("is_merged_snapshot"):
            if latest.get("merge_rule") and latest.get("merged_from_snapshot_at"):
                rec.pass_(key, "history_merge_marks_snapshot", "merged row marked")
            else:
                rec.fail(key, "history_merge_marks_snapshot", "merged row missing merge metadata")

        if key == "DAX":
            for period in ["6mo", "1y", "all"]:
                rows = provider.get_historical_data("DAX", period, series="price")
                if rows:
                    rec.fail("DAX", "dax_allowed_periods", f"{period} returned {len(rows)} rows")
                else:
                    rec.pass_("DAX", f"dax_disallows:{period}")

        series_map = (manager.INDICES.get(key, {}) or {}).get("series") or {}
        total_cfg = series_map.get("total_return")
        if entry.get("supports_total_return"):
            if not total_cfg:
                rec.fail(key, "total_return_config", "registry requires total_return but history config missing")
                continue
            expected_code = entry.get("total_return_index_code")
            if total_cfg.get("symbol") != expected_code:
                rec.fail(key, "total_return_code", f"expected {expected_code}, got {total_cfg.get('symbol')}")
            else:
                rec.pass_(key, "total_return_code", expected_code)
            total_history = provider.get_historical_data(key, "1mo", series="total_return")
            if not total_history:
                rec.fail(key, "total_return_history", "missing total_return history")
            else:
                rec.pass_(key, "total_return_history", f"{len(total_history)} rows")
                if total_history[-1].get("is_merged_snapshot"):
                    rec.fail(key, "total_return_not_snapshot_merged", "total_return was overwritten by price snapshot")
                else:
                    rec.pass_(key, "total_return_not_snapshot_merged")
        else:
            if total_cfg:
                rec.fail(key, "no_proxy_as_total_return", f"non-official total_return configured: {total_cfg}")
            else:
                rec.pass_(key, "no_proxy_as_total_return")

    for key in CSI_DIVIDEND_CODES:
        series_map = (manager.INDICES.get(key, {}) or {}).get("series") or {}
        total = series_map.get("total_return") or {}
        label = total.get("label", "")
        if any(word in label for word in ("代理", "同源", "复权")):
            rec.fail(key, "csi_dividend_no_proxy", f"bad total_return label: {label}")
        else:
            rec.pass_(key, "csi_dividend_no_proxy")

        dividend_return = series_map.get("dividend_return") or {}
        if key in OFFICIAL_DERIVED_DIVIDEND_RETURN_KEYS:
            if dividend_return.get("source") != "computed_dividend_yield":
                rec.fail(key, "dividend_return_source", f"expected computed_dividend_yield, got {dividend_return}")
                continue
            if dividend_return.get("components") != ["price", "total_return"]:
                rec.fail(key, "dividend_return_components", f"bad components: {dividend_return.get('components')}")
                continue
            rec.pass_(key, "dividend_return_source", "computed_dividend_yield")
            rows = provider.get_historical_data(key, "10y", series="dividend_return")
            if not rows:
                rec.fail(key, "dividend_return_history", "missing derived dividend-return history")
                continue
            values = [float(row["close"]) for row in rows if row.get("close") not in (None, "")]
            if len(values) >= 250 and all(0 <= value <= 20 for value in values):
                rec.pass_(key, "dividend_return_history", f"{len(rows)} rows, latest={values[-1]:.2f}%")
            else:
                rec.fail(key, "dividend_return_history", f"abnormal dividend-return values: {values[-5:]}")
        elif dividend_return:
            rec.fail(key, "dividend_return_source", f"unexpected unsupported dividend_return config: {dividend_return}")
        else:
            rec.pass_(key, "dividend_return_source", "not configured without official source")

        dividend_yield = series_map.get("dividend_yield") or {}
        if key in CSI_OFFICIAL_DIVIDEND_YIELD_KEYS:
            if dividend_yield.get("source") != "csindex_indicator":
                rec.fail(key, "official_dividend_yield_source", f"expected csindex_indicator, got {dividend_yield}")
                continue
            if dividend_yield.get("value_field") != "股息率1":
                rec.fail(key, "official_dividend_yield_field", f"expected 股息率1, got {dividend_yield.get('value_field')}")
                continue
            rec.pass_(key, "official_dividend_yield_source", "csindex_indicator/股息率1")
            rows = provider.get_historical_data(key, "1mo", series="dividend_yield")
            if not rows:
                rec.fail(key, "official_dividend_yield_history", "missing CSI official D/P rows")
                continue
            values = [float(row["close"]) for row in rows if row.get("close") not in (None, "")]
            if values and all(0 <= value <= 20 for value in values):
                rec.pass_(key, "official_dividend_yield_history", f"{len(rows)} rows, latest={values[-1]:.2f}%")
            else:
                rec.fail(key, "official_dividend_yield_history", f"abnormal official D/P values: {values[-5:]}")
        elif dividend_yield:
            rec.fail(key, "official_dividend_yield_source", f"unexpected unsupported dividend_yield config: {dividend_yield}")
        else:
            rec.pass_(key, "official_dividend_yield_source", "not configured without CSI official D/P source")

    for key in ("CN_US_10Y_SPREAD", "US10Y_2Y_SPREAD", "CN10Y_1Y_SPREAD"):
        rows = manager.db.load_history(
            key,
            "price",
            period_days=None,
            source_signature=manager._source_signature(key, "price"),
        ) or []
        negatives = [row for row in rows if float(row.get("close") or 0) < 0]
        if negatives:
            rec.pass_(key, "spread_negative_history", f"{len(negatives)} negative rows")
        else:
            rec.fail(key, "spread_negative_history", "spread history has no negative rows; cache may be polluted")
        if key == "CN_US_10Y_SPREAD" and rows and rows[-1].get("date", "") <= "2022-08-04":
            rec.fail(key, "spread_history_freshness", f"stopped at {rows[-1].get('date')}")
        else:
            rec.pass_(key, "spread_history_freshness", rows[-1].get("date") if rows else "no rows")


def write_report(rows: list[dict], counts: dict[str, int]):
    lines = [
        "# 数据质量硬门槛报告",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"结果汇总：PASS {counts['PASS']}，WARN {counts['WARN']}，FAIL {counts['FAIL']}。",
        "",
        "| 状态 | 标的 | 检查项 | 说明 |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['status']} | {row['key']} | {row['check']} | {row['message']} |")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    rec = Recorder()
    check_registry(rec)
    check_parser_contracts(rec)
    provider = StockDataProvider()
    stocks = provider.get_all_indices(force_refresh=True)
    check_cards(rec, provider, stocks)
    check_history(rec, provider)
    counts = rec.counts()
    write_report(rec.rows, counts)
    print(f"VALIDATION_REPORT={REPORT_PATH}")
    print(f"PASS={counts['PASS']} WARN={counts['WARN']} FAIL={counts['FAIL']}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
