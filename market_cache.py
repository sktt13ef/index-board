"""SQLite cache for dashboard market data.

The dashboard reads many free public sources. This cache keeps verified
snapshots and history locally so normal page loads do not repeatedly hit every
remote endpoint.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class MarketCache:
    """Small SQLite-backed cache for snapshots, history, and valuations."""

    DB_PATH = Path(__file__).parent / "data" / "market_cache.sqlite3"
    SCHEMA_VERSION = 1

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else self.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    source TEXT,
                    source_label TEXT,
                    data_as_of TEXT,
                    trade_date TEXT,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history_meta (
                    key TEXT NOT NULL,
                    series TEXT NOT NULL,
                    source TEXT,
                    source_symbol TEXT,
                    source_signature TEXT,
                    updated_at REAL NOT NULL,
                    row_count INTEGER NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    PRIMARY KEY (key, series)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history_points (
                    key TEXT NOT NULL,
                    series TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL DEFAULT 0,
                    source_signature TEXT,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (key, series, date)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS valuations (
                    key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    source TEXT,
                    data_end TEXT,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT OR REPLACE INTO cache_settings(key, value) VALUES (?, ?)",
                ("schema_version", str(self.SCHEMA_VERSION)),
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_lookup ON history_points(key, series, date)"
            )

    @staticmethod
    def _json_dumps(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)

    @staticmethod
    def _json_loads(value: str) -> dict[str, Any]:
        try:
            return json.loads(value)
        except Exception:
            return {}

    @staticmethod
    def _is_fresh(updated_at: float | None, max_age_seconds: int | float | None) -> bool:
        if not updated_at:
            return False
        if max_age_seconds is None:
            return True
        return (time.time() - float(updated_at)) <= max_age_seconds

    @staticmethod
    def _iso_from_epoch(value: float) -> str:
        return datetime.fromtimestamp(value).isoformat()

    def save_snapshot(self, key: str, payload: dict[str, Any]) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO snapshots(
                    key, payload, source, source_label, data_as_of, trade_date, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    payload=excluded.payload,
                    source=excluded.source,
                    source_label=excluded.source_label,
                    data_as_of=excluded.data_as_of,
                    trade_date=excluded.trade_date,
                    updated_at=excluded.updated_at
                """,
                (
                    key,
                    self._json_dumps(payload),
                    payload.get("source"),
                    payload.get("actual_source_label") or payload.get("source_label"),
                    payload.get("data_as_of"),
                    payload.get("trade_date"),
                    now,
                ),
            )

    def load_snapshot(self, key: str, max_age_seconds: int | float | None = None) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM snapshots WHERE key = ?", (key,)).fetchone()
        if not row or not self._is_fresh(row["updated_at"], max_age_seconds):
            return None
        payload = self._json_loads(row["payload"])
        payload["_cache_updated_at"] = self._iso_from_epoch(row["updated_at"])
        return payload

    def load_all_snapshots(self, max_age_seconds: int | float | None = None) -> dict[str, dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM snapshots").fetchall()
        result = {}
        for row in rows:
            if not self._is_fresh(row["updated_at"], max_age_seconds):
                continue
            payload = self._json_loads(row["payload"])
            payload["_cache_updated_at"] = self._iso_from_epoch(row["updated_at"])
            result[row["key"]] = payload
        return result

    @staticmethod
    def _number(value: Any, fallback: float = 0.0) -> float:
        try:
            if value in (None, ""):
                return fallback
            return float(value)
        except Exception:
            return fallback

    def save_history(
        self,
        key: str,
        series: str,
        rows: list[dict[str, Any]],
        *,
        source: str | None = None,
        source_symbol: str | None = None,
        source_signature: str | None = None,
        value_domain: str | None = None,
        allow_negative: bool | None = None,
    ) -> None:
        domain = (value_domain or "").strip().lower()
        permits_non_positive = bool(allow_negative) or domain in {"spread", "rate", "yield"}
        normalized = []
        for row in rows or []:
            date = str(row.get("date") or "").strip()
            close = self._number(row.get("close"), None)
            if not date or close is None:
                continue
            if source == "csindex_perf" and date == "1990-01-01":
                continue
            if not permits_non_positive and close <= 0:
                continue
            open_value = self._number(row.get("open"), close)
            high = self._number(row.get("high"), close)
            low = self._number(row.get("low"), close)
            volume = int(self._number(row.get("volume"), 0))
            normalized.append(
                (
                    key,
                    series,
                    date,
                    open_value,
                    high,
                    low,
                    close,
                    volume,
                    source_signature,
                )
            )

        if not normalized:
            return

        normalized.sort(key=lambda item: item[2])
        now = time.time()
        start_date = normalized[0][2]
        end_date = normalized[-1][2]
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM history_points WHERE key = ? AND series = ?",
                (key, series),
            )
            conn.executemany(
                """
                INSERT INTO history_points(
                    key, series, date, open, high, low, close, volume, source_signature, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [item + (now,) for item in normalized],
            )
            conn.execute(
                """
                INSERT INTO history_meta(
                    key, series, source, source_symbol, source_signature,
                    updated_at, row_count, start_date, end_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key, series) DO UPDATE SET
                    source=excluded.source,
                    source_symbol=excluded.source_symbol,
                    source_signature=excluded.source_signature,
                    updated_at=excluded.updated_at,
                    row_count=excluded.row_count,
                    start_date=excluded.start_date,
                    end_date=excluded.end_date
                """,
                (
                    key,
                    series,
                    source,
                    source_symbol,
                    source_signature,
                    now,
                    len(normalized),
                    start_date,
                    end_date,
                ),
            )

    def clear_history(self, key: str, series: str | None = None) -> None:
        """Remove cached history rows/meta for one symbol or one symbol+series."""
        with self._connect() as conn:
            if series is None:
                conn.execute("DELETE FROM history_points WHERE key = ?", (key,))
                conn.execute("DELETE FROM history_meta WHERE key = ?", (key,))
            else:
                conn.execute(
                    "DELETE FROM history_points WHERE key = ? AND series = ?",
                    (key, series),
                )
                conn.execute(
                    "DELETE FROM history_meta WHERE key = ? AND series = ?",
                    (key, series),
                )

    def get_history_meta(self, key: str, series: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM history_meta WHERE key = ? AND series = ?",
                (key, series),
            ).fetchone()
        return dict(row) if row else None

    def is_history_fresh(
        self,
        key: str,
        series: str,
        source_signature: str | None,
        ttl_hours: int | float,
    ) -> bool:
        meta = self.get_history_meta(key, series)
        if not meta or meta.get("row_count", 0) <= 0:
            return False
        if source_signature and meta.get("source_signature") != source_signature:
            return False
        return self._is_fresh(float(meta.get("updated_at") or 0), ttl_hours * 3600)

    def load_history(
        self,
        key: str,
        series: str,
        *,
        period_days: int | None = None,
        source_signature: str | None = None,
    ) -> list[dict[str, Any]] | None:
        meta = self.get_history_meta(key, series)
        if not meta:
            return None
        if source_signature and meta.get("source_signature") != source_signature:
            return None

        params: list[Any] = [key, series]
        where = "WHERE key = ? AND series = ?"
        if period_days:
            start_date = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")
            where += " AND date >= ?"
            params.append(start_date)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT date, open, high, low, close, volume, source_signature, updated_at
                FROM history_points
                {where}
                ORDER BY date
                """,
                params,
            ).fetchall()

        if not rows:
            return None
        return [
            {
                "date": row["date"],
                "open": round(float(row["open"]), 4),
                "high": round(float(row["high"]), 4),
                "low": round(float(row["low"]), 4),
                "close": round(float(row["close"]), 4),
                "volume": int(row["volume"] or 0),
                "source_signature": row["source_signature"],
                "fetched_at": self._iso_from_epoch(float(row["updated_at"])),
            }
            for row in rows
        ]

    def save_valuation(self, key: str, payload: dict[str, Any]) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO valuations(key, payload, source, data_end, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    payload=excluded.payload,
                    source=excluded.source,
                    data_end=excluded.data_end,
                    updated_at=excluded.updated_at
                """,
                (
                    key,
                    self._json_dumps(payload),
                    payload.get("source"),
                    payload.get("data_end"),
                    now,
                ),
            )

    def clear_valuation(self, key: str | None = None) -> None:
        """Remove one valuation payload, or all valuation payloads."""
        with self._connect() as conn:
            if key is None:
                conn.execute("DELETE FROM valuations")
            else:
                conn.execute("DELETE FROM valuations WHERE key = ?", (key,))

    def load_valuation(self, key: str, max_age_seconds: int | float | None = None) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM valuations WHERE key = ?", (key,)).fetchone()
        if not row or not self._is_fresh(row["updated_at"], max_age_seconds):
            return None
        payload = self._json_loads(row["payload"])
        payload["_cache_updated_at"] = self._iso_from_epoch(row["updated_at"])
        return payload

    def load_all_valuations(self, max_age_seconds: int | float | None = None) -> dict[str, dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM valuations").fetchall()
        result = {}
        for row in rows:
            if not self._is_fresh(row["updated_at"], max_age_seconds):
                continue
            payload = self._json_loads(row["payload"])
            payload["_cache_updated_at"] = self._iso_from_epoch(row["updated_at"])
            result[row["key"]] = payload
        return result

    def status(self) -> dict[str, Any]:
        with self._connect() as conn:
            snapshot_count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
            history_series_count = conn.execute("SELECT COUNT(*) FROM history_meta").fetchone()[0]
            history_point_count = conn.execute("SELECT COUNT(*) FROM history_points").fetchone()[0]
            valuation_count = conn.execute("SELECT COUNT(*) FROM valuations").fetchone()[0]
            snapshots = [dict(row) for row in conn.execute("SELECT * FROM snapshots").fetchall()]
            history_meta = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT key, series, source, source_symbol, source_signature, updated_at, row_count, start_date, end_date
                    FROM history_meta
                    ORDER BY key, series
                    """
                ).fetchall()
            ]
            valuations = [dict(row) for row in conn.execute("SELECT * FROM valuations").fetchall()]

        for row in history_meta:
            row["updated_at"] = self._iso_from_epoch(float(row["updated_at"]))

        now = time.time()
        by_symbol: dict[str, dict[str, Any]] = {}
        for row in snapshots:
            payload = self._json_loads(row.get("payload") or "{}")
            age = max(0, now - float(row["updated_at"]))
            note = payload.get("data_note") or ""
            by_symbol.setdefault(row["key"], {})
            by_symbol[row["key"]].update({
                "symbol": row["key"],
                "snapshot_age": round(age, 1),
                "snapshot_updated_at": self._iso_from_epoch(float(row["updated_at"])),
                "snapshot_source": row.get("source"),
                "source_label": row.get("source_label"),
                "data_as_of": row.get("data_as_of"),
                "fallback_used": bool(payload.get("actual_source_label")) or "备用" in note or "fallback" in note.lower(),
                "last_error": note if "失败" in note or "failed" in note.lower() else None,
                "last_success_at": self._iso_from_epoch(float(row["updated_at"])),
            })

        for row in history_meta:
            age = max(0, now - datetime.fromisoformat(row["updated_at"]).timestamp())
            item = by_symbol.setdefault(row["key"], {"symbol": row["key"]})
            histories = item.setdefault("history", {})
            histories[row["series"]] = {
                "history_age": round(age, 1),
                "history_updated_at": row["updated_at"],
                "source_signature": row.get("source_signature"),
                "source": row.get("source"),
                "source_symbol": row.get("source_symbol"),
                "row_count": row.get("row_count"),
                "start_date": row.get("start_date"),
                "end_date": row.get("end_date"),
            }

        for row in valuations:
            age = max(0, now - float(row["updated_at"]))
            item = by_symbol.setdefault(row["key"], {"symbol": row["key"]})
            item["valuation_age"] = round(age, 1)
            item["valuation_updated_at"] = self._iso_from_epoch(float(row["updated_at"]))
            item["valuation_source"] = row.get("source")

        size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
        return {
            "db_path": str(self.db_path),
            "size_mb": round(size_mb, 2),
            "snapshot_count": snapshot_count,
            "history_series_count": history_series_count,
            "history_point_count": history_point_count,
            "valuation_count": valuation_count,
            "history": history_meta,
            "symbols": [by_symbol[key] for key in sorted(by_symbol)],
        }


_market_cache: MarketCache | None = None


def get_market_cache() -> MarketCache:
    global _market_cache
    if _market_cache is None:
        _market_cache = MarketCache()
    return _market_cache
