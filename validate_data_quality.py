"""
Validate dashboard market data against the provider contract.

This script checks the user-facing invariants:
- every configured visible symbol returns a card snapshot;
- price/change/previous-close are internally consistent;
- chart history last close matches the card snapshot for chart-enabled symbols;
- chart-disabled symbols do not leak ETF/proxy history.
"""

import sys

from stock_data import StockDataProvider

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


EXPECTED_KEYS = [
    "CSI300",
    "CSI500",
    "CSI_DIVIDEND",
    "CSI_BAIJIU",
    "CN10Y",
    "US10Y",
    "HSTECH",
    "HSI",
    "DAX",
    "NDX",
    "SPX",
    "GOLD",
    "OIL_WTI",
]

HISTORY_DISABLED = {"CSI_DIVIDEND"}


def near(left, right, tolerance=0.05):
    return abs(float(left) - float(right)) <= tolerance


def main():
    provider = StockDataProvider()
    stocks = provider.get_all_indices(force_refresh=True)
    failures = []

    missing = [key for key in EXPECTED_KEYS if key not in stocks]
    if missing:
        failures.append(f"missing card snapshots: {', '.join(missing)}")

    for key in EXPECTED_KEYS:
        item = stocks.get(key)
        if not item:
            continue

        for field in ["price", "change", "change_pct", "prev_close", "timestamp", "data_as_of", "source_label", "update_label"]:
            if item.get(field) in (None, ""):
                failures.append(f"{key}: missing {field}")

        if item.get("price", 0) <= 0:
            failures.append(f"{key}: non-positive price {item.get('price')}")

        if item.get("prev_close"):
            implied_change = round(float(item["price"]) - float(item["prev_close"]), 2)
            if not near(implied_change, item["change"], 0.08):
                failures.append(
                    f"{key}: change mismatch, price-prev_close={implied_change}, change={item['change']}"
                )

    for key in EXPECTED_KEYS:
        history = provider.get_historical_data(key, "1mo")
        item = stocks.get(key)

        if key in HISTORY_DISABLED:
            if history:
                failures.append(f"{key}: chart should be disabled but returned {len(history)} rows")
            continue

        if not history:
            failures.append(f"{key}: missing chart history")
            continue

        latest = history[-1]
        trade_date = item.get("trade_date") if item else None
        if trade_date and latest.get("date") != trade_date:
            failures.append(f"{key}: chart last date {latest.get('date')} != card trade date {trade_date}")

        if item and not near(latest.get("close"), item.get("price"), 0.05):
            failures.append(f"{key}: chart last close {latest.get('close')} != card price {item.get('price')}")

    if failures:
        print("DATA QUALITY CHECK FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("DATA QUALITY CHECK PASSED")
    for key in EXPECTED_KEYS:
        item = stocks[key]
        print(
            f"{key}: {item['price']} {item['change']} {item['change_pct']}% | "
            f"{item['update_label']} | {item['source_label']} | {item['data_as_of']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
