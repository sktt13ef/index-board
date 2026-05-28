"""
Validate dashboard market data against the user-facing data contract.

The script separates hard errors from warnings:
- errors mean the page may misrepresent source, timestamp, calculation, or ETF
  proxy status;
- warnings mean the data is still usable but should be reviewed manually.
"""

import sys

from stock_data import StockDataProvider

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


THIRD_PARTY_HINTS = ("第三方", "延迟")
INVESTMENT_LABELS = {"加倍定投", "正常定投", "谨慎定投"}


def near(left, right, tolerance=0.05):
    return abs(float(left) - float(right)) <= tolerance


def add_error(errors, key, message):
    errors.append(f"{key}: {message}")


def add_warning(warnings, key, message):
    warnings.append(f"{key}: {message}")


def validate_card_contract(key, item, errors, warnings):
    for field in ["price", "change", "change_pct", "prev_close", "timestamp", "source_label", "update_label"]:
        if item.get(field) in (None, ""):
            add_error(errors, key, f"missing {field}")

    if item.get("data_as_of") in (None, "") and item.get("fetched_at") in (None, ""):
        add_error(errors, key, "missing both data_as_of and fetched_at")

    if item.get("source_url") in (None, ""):
        add_warning(warnings, key, "missing source_url")

    if item.get("source_type") in (None, ""):
        add_error(errors, key, "missing source_type")

    if item.get("is_official_source") is None:
        add_error(errors, key, "missing is_official_source")

    if item.get("price", 0) <= 0:
        add_error(errors, key, f"non-positive price {item.get('price')}")

    if item.get("prev_close"):
        implied_change = round(float(item["price"]) - float(item["prev_close"]), 2)
        if not near(implied_change, item["change"], 0.08):
            add_error(
                errors,
                key,
                f"change mismatch, price-prev_close={implied_change}, change={item['change']}",
            )

    if item.get("source_type") == "第三方":
        hint_text = " ".join(
            str(item.get(name) or "")
            for name in ["source_type", "delay_note", "data_note", "update_label"]
        )
        if not any(hint in hint_text for hint in THIRD_PARTY_HINTS):
            add_error(errors, key, "third-party source missing third-party/delay hint")


def validate_valuation_contract(key, valuation, errors, warnings):
    if not valuation:
        add_warning(warnings, key, "missing valuation metadata")
        return

    is_price_like = bool(valuation.get("is_price_percentile"))
    has_pe = valuation.get("pe_percentile") is not None
    has_price = valuation.get("price_percentile") is not None

    if is_price_like and has_pe:
        add_error(errors, key, "price/收益率/净值分位 must not use pe_percentile")
    if not is_price_like and has_price:
        add_error(errors, key, "PE valuation must not use price_percentile")

    if valuation.get("is_calculated_metric"):
        if not valuation.get("percentile_type"):
            add_error(errors, key, "calculated percentile missing percentile_type")
        if not valuation.get("percentile_window"):
            add_error(errors, key, "calculated percentile missing percentile_window")

    if has_pe and valuation.get("percentile_type") not in ("PE分位", "月频PE分位"):
        add_error(errors, key, f"PE percentile has wrong percentile_type={valuation.get('percentile_type')}")

    if is_price_like:
        expected = "收益率分位" if key in {"CN10Y", "US10Y"} else "净值分位" if key == "WANJIA_GOLD" else "价格分位"
        if valuation.get("percentile_type") != expected:
            add_error(errors, key, f"price-like percentile has wrong percentile_type={valuation.get('percentile_type')}")

    if valuation.get("signal_label") in INVESTMENT_LABELS and not valuation.get("signal_rule_note"):
        add_error(errors, key, "investment-style label missing project-rule disclaimer")

    if valuation.get("source_url") in (None, ""):
        add_warning(warnings, key, "valuation missing source_url")


def normalize_history_payload(payload):
    if isinstance(payload, dict):
        return payload.get("rows") or [], payload.get("meta") or {}
    if isinstance(payload, list):
        return payload, payload[0] if payload else {}
    return [], {}


def validate_history_contract(provider, key, item, errors, warnings):
    payload = provider.get_historical_data(key, "1mo")
    history, meta = normalize_history_payload(payload)

    if key == "CSI_DIVIDEND":
        if history:
            row = history[0]
            if row.get("history_source_type") != "ETF_PROXY":
                add_error(errors, key, "ETF proxy history missing history_source_type=ETF_PROXY")
            if row.get("chart_badge") != "ETF代理":
                add_error(errors, key, "ETF proxy history missing chart_badge=ETF代理")
            note = row.get("data_note") or row.get("history_note") or ""
            if "ETF 代理数据" not in note or "仅供趋势参考" not in note:
                add_error(errors, key, "ETF proxy history missing explicit risk note")
        elif not meta.get("chart_disabled") and not item.get("chart_disabled"):
            add_error(errors, key, "CSI_DIVIDEND history must be ETF_PROXY or explicitly chart_disabled")
        return

    if not history:
        add_error(errors, key, "missing chart history")
        return

    latest = history[-1]
    trade_date = item.get("trade_date") if item else None
    if trade_date and latest.get("date") != trade_date:
        add_error(errors, key, f"chart last date {latest.get('date')} != card trade date {trade_date}")

    if item and not near(latest.get("close"), item.get("price"), 0.05):
        add_error(errors, key, f"chart last close {latest.get('close')} != card price {item.get('price')}")


def main():
    provider = StockDataProvider()
    stocks = provider.get_all_indices(force_refresh=True)
    provider.update_valuation_cache()
    stocks = provider.get_all_indices()

    expected_keys = [
        key
        for key, config in provider.INDICES.items()
        if config.get("enabled", True) is not False
    ]
    errors = []
    warnings = []

    missing = [key for key in expected_keys if key not in stocks]
    if missing:
        errors.append(f"missing card snapshots: {', '.join(missing)}")

    for key in expected_keys:
        item = stocks.get(key)
        if not item:
            continue
        validate_card_contract(key, item, errors, warnings)
        validate_valuation_contract(key, item.get("valuation"), errors, warnings)
        validate_history_contract(provider, key, item, errors, warnings)

    print("DATA QUALITY CHECK SUMMARY")
    print(f"checked cards: {len(expected_keys)}")
    print(f"errors: {len(errors)}")
    print(f"warnings: {len(warnings)}")

    if errors:
        print("\nERRORS")
        for error in errors:
            print(f"- {error}")

    if warnings:
        print("\nWARNINGS")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        return 1

    print("\nDATA QUALITY CHECK PASSED")
    for key in expected_keys:
        item = stocks[key]
        valuation = item.get("valuation") or {}
        print(
            f"{key}: {item['price']} {item['change']} {item['change_pct']}% | "
            f"{item['update_label']} | {item['source_type']} | {item['source_label']} | "
            f"{item.get('data_as_of') or item.get('fetched_at')} | "
            f"{valuation.get('percentile_label') or 'no percentile'}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
