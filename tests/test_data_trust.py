import inspect
import subprocess
import sys

from history_data_manager import HistoryDataManager
from market_cache import MarketCache
from market_sources import (
    OFFICIAL_TOTAL_RETURN_CODES,
    get_source_registry,
    validate_source_registry,
)
from stock_data import StockDataProvider


def test_source_registry_required_fields():
    assert validate_source_registry() == []


def test_total_return_must_be_official():
    manager = HistoryDataManager()
    registry = get_source_registry()
    for key, entry in registry.items():
        series = (manager.INDICES.get(key, {}) or {}).get("series") or {}
        total = series.get("total_return")
        if entry["supports_total_return"]:
            assert total, key
            assert total["symbol"] == entry["total_return_index_code"]
            effective_source = total.get("source") or (manager.INDICES.get(key, {}) or {}).get("source")
            assert effective_source in {"csindex_perf", "cni_official", "stoxx_dax", "lse_dory"}
        else:
            assert total is None, key


def test_csi_dividend_series_codes():
    manager = HistoryDataManager()
    expected = {
        "CSI_DIVIDEND": ("H30269", "H20269"),
        "CSI_DIVIDEND_100": ("930955", "H20955"),
        "CSI300_DIVIDEND_LOW_VOL": ("930740", "H20740"),
        "CSI_DIVIDEND_QUALITY": ("931468", "921468"),
        "CSI_ALL_DIVIDEND_QUALITY": ("932315", "932315CNY010"),
        "CSI_CASH_FLOW": ("932365", "932365CNY010"),
        "CNI_FREE_CASH_FLOW": ("980092", "480092"),
    }
    for key, (price_code, total_code) in expected.items():
        series = manager.INDICES[key]["series"]
        assert series["price"]["symbol"] == price_code
        assert series["total_return"]["symbol"] == total_code


def test_csi500_index_is_not_a500():
    manager = HistoryDataManager()
    registry = get_source_registry()
    series = manager.INDICES["CSI500_INDEX"]["series"]
    assert registry["CSI500"]["display_name"] == "中证A500"
    assert registry["CSI500_INDEX"]["display_name"] == "中证500"
    assert series["price"]["symbol"] == "000905"
    assert series["total_return"]["symbol"] == "H00905"


def test_dividend_return_uses_official_total_return_derivation():
    manager = HistoryDataManager()
    derived_return_keys = {
        "CSI_DIVIDEND",
        "CSI_DIVIDEND_100",
        "CSI300_DIVIDEND_LOW_VOL",
        "CSI_DIVIDEND_QUALITY",
        "CSI_ALL_DIVIDEND_QUALITY",
        "CSI_CASH_FLOW",
        "CNI_FREE_CASH_FLOW",
    }
    for key in derived_return_keys:
        series = manager.INDICES[key]["series"]
        assert series["dividend_return"]["source"] == "computed_dividend_yield"
        assert series["dividend_return"]["components"] == ["price", "total_return"]
        assert series["dividend_return"]["rolling_days"] == 252


def test_csi_official_dividend_yield_uses_indicator_source():
    manager = HistoryDataManager()
    csi_indicator_keys = {
        "CSI_DIVIDEND",
        "CSI_DIVIDEND_100",
        "CSI300_DIVIDEND_LOW_VOL",
        "CSI_DIVIDEND_QUALITY",
        "CSI_ALL_DIVIDEND_QUALITY",
        "CSI_CASH_FLOW",
    }
    for key in csi_indicator_keys:
        series = manager.INDICES[key]["series"]
        assert series["dividend_yield"]["source"] == "csindex_indicator"
        assert series["dividend_yield"]["value_field"] == "股息率1"
        assert series["dividend_yield"]["limited_history"] is True

    assert "dividend_yield" not in manager.INDICES["CNI_FREE_CASH_FLOW"]["series"]


def test_no_proxy_as_total_return():
    manager = HistoryDataManager()
    forbidden = ("代理", "同源", "复权")
    for key, config in manager.INDICES.items():
        total = (config.get("series") or {}).get("total_return")
        if total:
            assert not any(word in total.get("label", "") for word in forbidden), key


def test_dax_allowed_periods():
    registry = get_source_registry()
    assert registry["DAX"]["allowed_periods"] == ["1mo", "3mo"]
    manager = HistoryDataManager()
    config = manager._get_series_config("DAX", "price")
    assert manager._is_period_supported(config, "1mo")
    assert manager._is_period_supported(config, "3mo")
    assert not manager._is_period_supported(config, "6mo")
    assert not manager._is_period_supported(config, "1y")
    assert not manager._is_period_supported(config, "all")
    total_config = manager._get_series_config("DAX", "total_return")
    assert total_config["symbol"] == "DAX"
    assert manager._is_period_supported(total_config, "3mo")
    assert not manager._is_period_supported(total_config, "6mo")


def test_hstech_parser():
    source = inspect.getsource(StockDataProvider.get_sina_data)
    assert "price = float(parts[6])" in source
    assert "change = float(parts[7])" in source
    assert "change_pct = float(parts[8])" in source
    assert "parts[17]" in source
    assert "parts[18]" in source


def test_spx_parser():
    source = inspect.getsource(StockDataProvider.get_sina_data)
    assert "price = float(parts[1])" in source
    assert "open_price = float(parts[5])" in source
    assert "high = float(parts[6])" in source
    assert "low = float(parts[7])" in source
    assert "prev_close = float(parts[26])" in source


def test_cache_source_signature_invalidation(tmp_path):
    cache = MarketCache(tmp_path / "cache.sqlite3")
    rows = [{"date": "2026-01-01", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 0}]
    cache.save_history("T", "price", rows, source="unit", source_symbol="T", source_signature="sig-a")
    assert cache.load_history("T", "price", source_signature="sig-a")
    assert cache.load_history("T", "price", source_signature="sig-b") is None


def test_history_merge_marks_snapshot():
    provider = StockDataProvider()
    provider.cache["UNIT"] = {
        "trade_date": "2026-01-02",
        "price": 12,
        "open": 10,
        "high": 13,
        "low": 9,
        "volume": 1,
        "fetched_at": "2026-01-02T15:00:00",
        "data_as_of": "2026-01-02 15:00:00",
    }
    rows = [
        {
            "date": "2026-01-02",
            "open": 10,
            "high": 11,
            "low": 9,
            "close": 10,
            "volume": 1,
            "series": "price",
            "source_signature": "sig",
        }
    ]
    merged = provider._merge_realtime_snapshot_into_history("UNIT", rows)
    assert merged[-1]["close"] == 12
    assert merged[-1]["is_merged_snapshot"] is True
    assert merged[-1]["merged_from_snapshot_at"] == "2026-01-02T15:00:00"
    assert "overwrite close only" in merged[-1]["merge_rule"]


def test_validate_data_quality_exit_code():
    result = subprocess.run(
        [sys.executable, "validate_data_quality.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAIL=0" in result.stdout
