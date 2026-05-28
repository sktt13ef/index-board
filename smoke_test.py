"""
Minimal HTTP smoke tests for the market dashboard.

Run while the local Flask app is listening on http://127.0.0.1:5000.
No browser or third-party test framework is required.
"""

from __future__ import annotations

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


BASE_URL = "http://127.0.0.1:5000"
EXPECTED_CARD_COUNT = 18
REQUIRED_CARD_FIELDS = [
    "source_label",
    "source_type",
    "is_official_source",
    "is_calculated_metric",
]
REQUIRED_VALUATION_FIELDS = [
    "percentile_type",
    "percentile_window",
]


def fetch(path: str):
    url = f"{BASE_URL}{path}"
    with urlopen(url, timeout=30) as response:
        body = response.read()
        content_type = response.headers.get("Content-Type", "")
        return response.status, body, content_type


def fetch_json(path: str):
    status, body, _ = fetch(path)
    if status != 200:
        raise AssertionError(f"{path}: expected HTTP 200, got {status}")
    return json.loads(body.decode("utf-8"))


def normalize_history(payload):
    if isinstance(payload, list):
        return payload, payload[0] if payload else {}
    if isinstance(payload, dict):
        rows = payload.get("rows") or []
        meta = payload.get("meta") or (rows[0] if rows else {})
        return rows, meta
    return [], {}


def check(condition: bool, message: str, errors: list[str]):
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []

    try:
        status, _, _ = fetch("/")
        check(status == 200, f"/: expected HTTP 200, got {status}", errors)

        stocks = fetch_json("/api/stocks")
        check(isinstance(stocks, dict), "/api/stocks: expected object", errors)
        if isinstance(stocks, dict):
            check(
                len(stocks) == EXPECTED_CARD_COUNT,
                f"/api/stocks: expected {EXPECTED_CARD_COUNT} cards, got {len(stocks)}",
                errors,
            )
            for key, card in stocks.items():
                for field in REQUIRED_CARD_FIELDS:
                    check(field in card, f"{key}: missing card field {field}", errors)
                valuation = card.get("valuation") or {}
                for field in REQUIRED_VALUATION_FIELDS:
                    check(field in valuation, f"{key}: missing valuation field {field}", errors)

        history_payload = fetch_json("/api/history/CSI_DIVIDEND")
        rows, meta = normalize_history(history_payload)
        check(bool(rows), "/api/history/CSI_DIVIDEND: expected non-empty history", errors)
        check(
            meta.get("history_source_type") == "ETF_PROXY",
            "CSI_DIVIDEND history: missing history_source_type=ETF_PROXY",
            errors,
        )
        check(
            meta.get("chart_badge") == "ETF代理",
            "CSI_DIVIDEND history: missing chart_badge=ETF代理",
            errors,
        )
        note = str(meta.get("data_note") or meta.get("history_note") or "")
        check(
            "ETF 代理" in note or "仅供趋势参考" in note,
            "CSI_DIVIDEND history: missing ETF proxy risk note",
            errors,
        )
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, AssertionError) as exc:
        errors.append(str(exc))

    print("SMOKE TEST SUMMARY")
    print(f"errors: {len(errors)}")
    if errors:
        print("\nFAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS")
    print(f"checked cards: {EXPECTED_CARD_COUNT}")
    print("checked endpoints: /, /api/stocks, /api/history/CSI_DIVIDEND")
    return 0


if __name__ == "__main__":
    sys.exit(main())
