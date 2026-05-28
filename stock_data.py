import json
import re
import time
import sys
from io import BytesIO
from datetime import datetime, timedelta
from threading import Thread

import akshare as ak
import pandas as pd
import requests
from flask_socketio import SocketIO

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 导入实时估值模块
from stock_data_realtime import RealtimeValuationProvider

# 导入本地估值计算器
from local_valuation_calculator import get_calculator

# 导入历史数据管理器
from history_data_manager import get_history_manager


class StockDataProvider:
    SNAPSHOT_TTL_SECONDS = 600
    MAX_STALE_SECONDS = 86400
    DAILY_SOURCE_TTL_SECONDS = 3600
    VALUATION_REFRESH_SECONDS = 3600
    REALTIME_VALUATION_KEYS = {"CSI300", "CSI500"}
    DAILY_VALUATION_KEYS = {"CSI_DIVIDEND", "STAR50", "STAR100", "CSI_BAIJIU"}
    # 用10年价格/收益率分位（无官方PE的指数）
    PRICE_PERCENTILE_KEYS = {
        "CHINEXT", "HSTECH", "HSI", "NDX", "DAX",
        "GOLD", "OIL_WTI", "XOP",
        "CN10Y", "US10Y", "WANJIA_GOLD",
    }
    # 用月频 PE-TTM 历史计算近10年滚动市盈率分位（multpl.com 推导，基于标普官方EPS）
    MULTPL_PE_KEYS = {"SPX"}
    MULTPL_PE_CACHE_TTL_HOURS = 12
    SOURCE_TYPE_BY_SOURCE = {
        "csindex_official": "官方",
        "csindex": "官方",
        "hsi_daily_bulletin": "官方",
        "us_treasury": "官方",
        "deutsche_boerse": "官方",
        "nasdaq_official": "官方",
        "chinabond": "准官方",
        "sina": "第三方",
        "eastmoney": "第三方",
        "eastmoney_quote": "第三方",
        "fund_nav": "第三方",
        "dax_etf": "第三方",
        "etf_estimate": "项目计算",
        "etf_to_index": "项目计算",
    }
    """股票数据提供者 - 使用新浪财经和东方财富API"""

    # 指数配置
    INDICES = {
        "CSI300": {
            "name": "沪深300",
            "symbol": "000300",
            "type": "cn",
            "currency": "点",
            "source": "csindex_official",
            "sina_code": "sh000300",
            "fallback_source": "sina",
            "csindex_code": "000300",  # 中证指数代码
            "update_frequency": "realtime",
            "source_label": "中证指数官网",
            "source_url": "https://www.csindex.com.cn/#/indices/family/detail?indexCode=000300",
            "data_note": "官方日内快照；以中证官网返回的交易日期和交易时间为准。",
            "base_pe": 12.26,  # Wind数据：2025年4月16日PE-TTM约12.26，全历史百分位38.75%
            "base_pe_percentile": 38.75,  # Wind：全历史分位约38.75%
            "base_dividend_yield": 3.49,  # Wind：2025年4月16日股息率约3.49%，处于近10年99.41%分位
        },
        "HSTECH": {
            "name": "恒生科技指数",
            "symbol": "HSTECH",
            "sina_code": "rt_hkHSTECH",
            "type": "hk",
            "currency": "点",
            "source": "sina",
            "update_frequency": "daily",
            "source_label": "新浪财经港股指数快照",
            "source_url": "https://finance.sina.com.cn/stock/hkstock/",
            "data_note": "按收盘后日更口径展示；如果你更看重精确时点，这个免费快照比官方日更报表更适合当前看板。",
            "etf_code": "sh513130",  # 恒生科技ETF，用于估算PE
            "base_pe": 20.9,  # Wind数据：2025年4月28日PE-TTM约20.9，近10年分位约13%
            "base_pe_percentile": 13.0,  # Wind：近10年分位约13%，处于历史低位
            "base_dividend_yield": 1.15,  # 雪球数据：2025年5月16日股息率约1.15%
        },
        "HSI": {
            "name": "恒生指数",
            "symbol": "HSI",
            "type": "hk",
            "currency": "点",
            "source": "hsi_daily_bulletin",
            "hsi_series_code": "hsi",
            "update_frequency": "daily",
            "source_label": "恒生指数公司公开日更报表",
            "source_url": "https://www.hsi.com.hk/index360/eng/indexes?id=00001.00",
            "data_note": "按收盘后日更口径展示；使用恒生指数公司官方 daily bulletin。",
        },
        "OIL_WTI": {
            "name": "WTI原油",
            "symbol": "OIL_WTI",
            "sina_code": "hf_CL",
            "type": "commodity",
            "currency": "美元/桶",
            "source": "sina",
            "update_frequency": "delayed",
            "source_label": "新浪财经外盘期货快照",
            "source_url": "https://finance.sina.com.cn/futures/quotes/CL.shtml",
            "data_note": "免费延迟快照；CME官网免费延迟报价页标注至少延迟10分钟，但后端直连会被403拦截。",
        },
        "GOLD": {
            "name": "黄金",
            "symbol": "GOLD",
            "sina_code": "hf_GC",
            "type": "commodity",
            "currency": "美元/盎司",
            "source": "sina",
            "update_frequency": "delayed",
            "source_label": "新浪财经外盘期货快照",
            "source_url": "https://finance.sina.com.cn/futures/quotes/GC.shtml",
            "data_note": "免费延迟快照；CME官网免费延迟报价页标注至少延迟10分钟，但后端直连会被403拦截。",
        },
        "CSI500": {
            "name": "中证A500",
            "symbol": "000510",
            "type": "cn",
            "currency": "点",
            "source": "csindex_official",
            "sina_code": "sh000510",
            "fallback_source": "sina",
            "csindex_code": "000510",
            "update_frequency": "realtime",
            "source_label": "中证指数官网",
            "source_url": "https://www.csindex.com.cn/#/indices/family/detail?indexCode=000510",
            "data_note": "官方日内快照；以中证官网返回的交易日期和交易时间为准。",
            "etf_code": "sh510500",  # 中证500ETF，用于估算PE
            "base_pe": 14.17,  # Wind数据：2025年4月30日PE-TTM约14.17，历史分位约41.9%
            "base_pe_percentile": 41.9,  # Wind：历史分位约41.9%，处于合理区间
            "base_dividend_yield": 3.35,  # Wind：近1年股息率约3.35%
        },
        "CSI_DIVIDEND": {
            "name": "中证红利低波动",
            "symbol": "H30269",
            "type": "cn",
            "currency": "点",
            "source": "csindex_official",
            "enabled": True,
            "csindex_code": "H30269",  # 用于获取PE数据
            "fallback_source": "eastmoney_quote",
            "eastmoney_secid": "2.H30269",
            "update_frequency": "daily",
            "source_label": "中证指数官网",
            "source_url": "https://www.csindex.com.cn/#/indices/family/detail?indexCode=H30269",
            "history_etf_proxy": "sh560150",
            "history_source_type": "ETF_PROXY",
            "chart_badge": "ETF代理",
            "history_note": "历史走势使用 ETF 代理数据，仅供趋势参考，不等同于中证指数官方历史点位。",
            "data_note": "官方日更快照；按收盘后数据展示。",
            "base_pe": 7.74,  # 雪球数据：2025年PE-TTM约7.74，近十年百分位73.73%
            "base_pe_percentile": 73.73,  # 雪球：近十年百分位73.73%
            "base_dividend_yield": 4.57,  # 雪球：当前股息率约4.57%
        },
        "CSI_BAIJIU": {
            "name": "中证白酒指数",
            "symbol": "399997",
            "type": "cn",
            "currency": "点",
            "source": "sina",
            "sina_code": "sz399997",
            "fallback_source": "eastmoney_quote",
            "eastmoney_secid": "0.399997",
            "csindex_code": "399997",
            "update_frequency": "realtime",
            "source_label": "新浪财经",
            "source_url": "https://finance.sina.com.cn/stock/stockindex/",
            "data_note": "免费实时快照优先使用新浪；历史图使用免费日线行情。",
        },
        "CHINEXT": {
            "name": "创业板指",
            "symbol": "399006",
            "type": "cn",
            "currency": "点",
            "source": "sina",
            "sina_code": "sz399006",
            "fallback_source": "eastmoney_quote",
            "eastmoney_secid": "0.399006",
            "update_frequency": "realtime",
            "source_label": "新浪财经",
            "source_url": "https://finance.sina.com.cn/stock/stockindex/",
            "data_note": "深交所创业板综合指数，免费实时快照。",
        },
        "STAR50": {
            "name": "科创50",
            "symbol": "000688",
            "type": "cn",
            "currency": "点",
            "source": "sina",
            "sina_code": "sh000688",
            "fallback_source": "eastmoney_quote",
            "eastmoney_secid": "1.000688",
            "csindex_code": "000688",
            "update_frequency": "realtime",
            "source_label": "新浪财经",
            "source_url": "https://finance.sina.com.cn/stock/stockindex/",
            "data_note": "上交所科创板50指数，免费实时快照。",
        },
        "STAR100": {
            "name": "科创100",
            "symbol": "000698",
            "type": "cn",
            "currency": "点",
            "source": "sina",
            "sina_code": "sh000698",
            "fallback_source": "eastmoney_quote",
            "eastmoney_secid": "1.000698",
            "csindex_code": "000698",
            "update_frequency": "realtime",
            "source_label": "新浪财经",
            "source_url": "https://finance.sina.com.cn/stock/stockindex/",
            "data_note": "上交所科创板100指数，免费实时快照。",
        },
        "CN10Y": {
            "name": "中国国债十年收益率",
            "symbol": "CN10Y",
            "type": "bond",
            "currency": "%",
            "source": "chinabond",
            "update_frequency": "daily",
            "source_label": "中国债券信息网",
            "source_url": "https://yield.chinabond.com.cn/",
            "data_note": "中国债券信息网公开国债收益率曲线，按工作日更新。",
        },
        "US10Y": {
            "name": "美国国债十年收益率",
            "symbol": "US10Y",
            "type": "bond",
            "currency": "%",
            "source": "us_treasury",
            "update_frequency": "daily",
            "source_label": "U.S. Treasury",
            "source_url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates",
            "data_note": "U.S. Treasury daily yield curve 官方公开数据，按发布日期更新。",
        },
        "DAX": {
            "name": "德国DAX指数",
            "symbol": "DAX",
            "type": "global",
            "currency": "点",
            "source": "deutsche_boerse",
            "enabled": True,
            "isin": "DE0008469008",
            "mic": "XETR",
            "update_frequency": "daily",
            "source_label": "Deutsche Börse",
            "source_url": "https://live.deutsche-boerse.com/indices/dax",
            "history_available": True,
            "history_note": "德交所官方页面负责最新收盘快照；官方公开历史仅能稳定获取 STOXX 近3个月免费文件，6月/1年暂不开放。",
            "data_note": "德交所官方页面快照；按收盘后日更口径展示。",
            "base_pe": 18.6,  # 数据：2025年11月PE-TTM约18.6，近10年分位约62.57%
            "base_pe_percentile": 62.57,  # 近10年分位约62.57%，处于合理偏高区间
            "base_dividend_yield": 3.2,  # 估算股息率约3.2%
        },
        "NDX": {
            "name": "纳斯达克100",
            "symbol": "NDX",
            "type": "us",
            "currency": "点",
            "source": "nasdaq_official",
            "update_frequency": "delayed",
            "source_label": "Nasdaq Global Indexes",
            "source_url": "https://indexes.nasdaq.com/Index/Overview/NDX",
            "data_note": "Nasdaq官网指数页快照；页面以DATA AS OF日期为准，按延迟/收盘时点展示。",
            "base_pe": 29.99,
            "base_pe_percentile": 58.76,
            "base_dividend_yield": 0.5,
        },
        "SPX": {
            "name": "标普500",
            "symbol": "SPX",
            "sina_code": "gb_$inx",
            "type": "us",
            "currency": "点",
            "source": "sina",
            "update_frequency": "delayed",
            "source_label": "新浪财经美股指数快照",
            "source_url": "https://finance.sina.com.cn/stock/usstock/",
            "data_note": "标普500（S&P 500）免费延迟快照；以新浪美股行情返回的时间为准。",
            "base_pe": 26.5,
            "base_pe_percentile": 75.0,
            "base_dividend_yield": 1.3,
        },
        "XOP": {
            "name": "标普油气ETF",
            "symbol": "XOP",
            "sina_code": "gb_xop",
            "type": "us",
            "currency": "美元",
            "source": "sina",
            "update_frequency": "delayed",
            "source_label": "新浪财经美股快照",
            "source_url": "https://finance.sina.com.cn/stock/usstock/",
            "data_note": "SPDR S&P Oil & Gas E&P ETF，追踪标普油气勘探指数(SPSIOP)，免费延迟快照。",
        },
        "WANJIA_GOLD": {
            "name": "万家周期视野C",
            "symbol": "025446",
            "type": "cn",
            "currency": "元",
            "source": "fund_nav",
            "update_frequency": "daily",
            "source_label": "东方财富基金净值",
            "source_url": "https://fund.eastmoney.com/025446.html",
            "data_note": "万家周期视野股票发起式C，重仓黄金股，按交易日日更净值。",
        },
    }

    # 估值数据缓存
    _valuation_cache = {}
    _valuation_cache_time = None
    _price_pct_cache = {}
    _price_pct_cache_time = None

    def __init__(self, socketio: SocketIO = None):
        self.socketio = socketio
        self.running = False
        self.update_thread = None
        self.cache = {}
        self.last_update = None
        self._last_valuation_refresh = None
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://finance.sina.com.cn",
        })
        # 禁用代理
        self.session.proxies = {
            "http": None,
            "https": None,
        }

    def _source_type_for(self, source: str) -> str | None:
        return self.SOURCE_TYPE_BY_SOURCE.get(source)

    def _delay_note_for(self, source_type: str | None, update_frequency: str | None) -> str | None:
        if update_frequency == "delayed":
            return "延迟行情，仅供参考"
        if source_type == "第三方":
            return "第三方免费行情，仅供参考"
        return None

    def _sample_window_label(self, years: float | int | None) -> str | None:
        if years in (None, ""):
            return None
        try:
            value = float(years)
        except Exception:
            return None
        if value >= 9.5:
            return "样本近10年"
        if value <= 0:
            return "样本区间有限"
        return f"样本约{value:.1f}年"

    def _metric_type_for(self, key: str, valuation: dict) -> str | None:
        if not valuation:
            return None
        if valuation.get("is_price_percentile"):
            if key in {"CN10Y", "US10Y"}:
                return "收益率分位"
            if key == "WANJIA_GOLD":
                return "净值分位"
            return "价格分位"
        if key in self.MULTPL_PE_KEYS:
            return "月频PE分位"
        if valuation.get("pe_percentile") is not None:
            return "PE分位"
        return None

    def _enrich_valuation_metadata(self, key: str, valuation: dict | None) -> dict | None:
        if not valuation:
            return valuation

        valuation = dict(valuation)
        metric_type = valuation.get("percentile_type") or self._metric_type_for(key, valuation)
        window = valuation.get("percentile_window") or self._sample_window_label(valuation.get("years_of_data"))
        source = valuation.get("source")
        source_type = "项目计算" if valuation.get("is_price_percentile") else None
        if key in self.MULTPL_PE_KEYS:
            source_type = "第三方"
        elif source == "中证指数官网":
            source_type = "官方"

        valuation.setdefault("percentile_type", metric_type)
        valuation.setdefault("percentile_window", window or "样本区间有限")
        if metric_type:
            valuation.setdefault(
                "percentile_label",
                f"{metric_type}，{valuation['percentile_window']}",
            )
        valuation.setdefault("is_calculated_metric", metric_type is not None)
        valuation.setdefault(
            "metric_note",
            "分位和提示由本项目基于历史序列计算，不是官方评级或投资建议。"
            if metric_type else None,
        )
        valuation.setdefault("source_type", source_type)
        valuation.setdefault("is_official_source", source_type == "官方")
        valuation.setdefault("signal_rule_note", "项目规则生成，不是官方评级，不构成投资建议。")
        return valuation

    def _is_snapshot_fresh(self) -> bool:
        if not self.cache or not self.last_update:
            return False
        return (datetime.now() - self.last_update).total_seconds() < self.SNAPSHOT_TTL_SECONDS

    def _can_use_cached_record(self, cached: dict) -> bool:
        if not cached:
            return False
        try:
            timestamp = datetime.fromisoformat(cached["timestamp"])
        except (KeyError, TypeError, ValueError):
            return False
        return (datetime.now() - timestamp).total_seconds() < self.MAX_STALE_SECONDS

    def _can_use_daily_cached_record(self, cached: dict) -> bool:
        if not cached:
            return False
        try:
            timestamp = datetime.fromisoformat(cached["timestamp"])
        except (KeyError, TypeError, ValueError):
            return False
        return (datetime.now() - timestamp).total_seconds() < self.DAILY_SOURCE_TTL_SECONDS

    def _build_index_result(self, key: str, config: dict, data: dict) -> dict:
        result = {
            **config,
            **data,
        }
        # 配置中指定的 name 始终优先（避免 API 返回的原始名覆盖中文简称）
        if config.get("name"):
            result["name"] = config["name"]
        result.pop("enabled", None)
        for field in list(result):
            if field.startswith("base_") or field in {"etf_code", "etf_index_ratio"}:
                result.pop(field, None)
        result.setdefault("source_label", {
            "sina": "新浪财经",
            "eastmoney": "东方财富",
            "eastmoney_quote": "东方财富",
            "csindex_official": "中证指数官网",
            "hsi_daily_bulletin": "恒生指数公司公开日更报表",
            "chinabond": "中国债券信息网",
            "us_treasury": "U.S. Treasury",
            "deutsche_boerse": "Deutsche Börse",
            "nasdaq_official": "Nasdaq Global Indexes",
        }.get(result.get("source")))
        result.setdefault("update_frequency", "realtime")
        result.setdefault("update_label", {
            "realtime": "实时",
            "daily": "日更",
            "delayed": "延迟",
        }.get(result.get("update_frequency"), result.get("update_frequency")))
        result.setdefault("fetched_at", result.get("timestamp"))
        source_type = self._source_type_for(result.get("source"))
        result.setdefault("source_type", source_type)
        result.setdefault("is_official_source", source_type == "官方")
        result.setdefault("delay_note", self._delay_note_for(source_type, result.get("update_frequency")))
        result.setdefault("is_calculated_metric", False)
        if key in self._valuation_cache:
            result["valuation"] = self._enrich_valuation_metadata(key, self._valuation_cache[key])
            result["is_calculated_metric"] = bool(result["valuation"].get("is_calculated_metric"))
        return result

    def _fetch_index_data(self, config: dict) -> dict:
        source = config.get("source", "sina")

        if source == "sina":
            data = self.get_sina_data(config["sina_code"])
            if not data and config.get("em_code"):
                print("  新浪失败，尝试东方财富...")
                data = self.get_eastmoney_global_data(config["em_code"])
            return data

        if source == "eastmoney":
            return self.get_eastmoney_global_data(config["em_code"])

        if source == "eastmoney_quote":
            return self.get_eastmoney_quote_data(config)

        if source == "csindex":
            return self.get_csindex_data(config["symbol"])

        if source == "csindex_official":
            return self.get_csindex_official_data(config)

        if source == "hsi_daily_bulletin":
            return self._fetch_hsi_daily_bulletin_snapshot(config)

        if source == "chinabond":
            return self._fetch_chinabond_yield_snapshot(config)

        if source == "us_treasury":
            return self._fetch_us_treasury_yield_snapshot(config)

        if source == "deutsche_boerse":
            return self.get_deutsche_boerse_index_data(config)

        if source == "nasdaq_official":
            return self.get_nasdaq_index_data(config)

        if source == "fund_nav":
            return self._fetch_fund_nav(config)

        if source == "dax_etf":
            return self.get_dax_data()

        if source == "etf_estimate":
            return self.get_etf_estimate_data(config["etf_code"], config["base_price"], config["name"])

        if source == "etf_to_index":
            return self.get_etf_to_index_data(config["etf_code"], config["etf_index_ratio"], config["name"])

        return None

    def _fetch_fallback_data(self, config: dict) -> dict:
        fallback_source = config.get("fallback_source")
        if not fallback_source:
            return None

        fallback_config = {**config, "source": fallback_source}
        if fallback_source == "sina":
            data = self.get_sina_data(fallback_config["sina_code"])
            if data:
                data["source"] = "sina"
                data["actual_source_label"] = "新浪财经备用源"
                data["actual_source_url"] = "https://finance.sina.com.cn/"
                data["data_note"] = (
                    f"{config.get('source_label', '主源')}暂不可用，"
                    "本次使用免费备用行情源；数据时点仍以返回字段为准。"
                )
            return data

        if fallback_source == "eastmoney_quote":
            data = self.get_eastmoney_quote_data(fallback_config)
            if data:
                data["source"] = "eastmoney_quote"
                data["actual_source_label"] = "东方财富备用源"
                data["actual_source_url"] = "https://quote.eastmoney.com/"
                data["data_note"] = (
                    f"{config.get('source_label', '主源')}暂不可用，"
                    "本次使用免费备用行情源；数据时点仍以返回字段为准。"
                )
            return data

        return self._fetch_index_data(fallback_config)

    def _join_sina_datetime(self, date_part: str = None, time_part: str = None) -> str:
        if not date_part:
            return None
        date_text = str(date_part).strip().replace("/", "-")
        time_text = str(time_part or "").strip()
        if time_text:
            return f"{date_text} {time_text}"
        return date_text

    def _build_daily_snapshot_from_history(self, key: str, config: dict, history: list) -> dict | None:
        if not history:
            return None

        closes = []
        for item in history:
            value = item.get("close")
            if value in (None, ""):
                continue
            closes.append(float(value))

        if not closes:
            return None

        latest = history[-1]
        previous = history[-2] if len(history) >= 2 else latest
        price = float(latest.get("close", 0) or 0)
        prev_close = float(previous.get("close", price) or price)
        change = round(price - prev_close, 2)
        change_pct = round((change / prev_close * 100) if prev_close else 0, 2)
        open_value = latest.get("open", history[0].get("open", history[0].get("close", price)))

        return {
            "name": config.get("name", key),
            "price": round(price, 2),
            "change": change,
            "change_pct": change_pct,
            "prev_close": round(prev_close, 2),
            "open": round(float(open_value or price), 2),
            "high": round(float(max(closes)), 2),
            "low": round(float(min(closes)), 2),
            "volume": int(float(latest.get("volume", 0) or 0)),
            "timestamp": datetime.now().isoformat(),
            "data_as_of": latest.get("date"),
            "trade_date": latest.get("date"),
        }

    def _fetch_chinabond_yield_snapshot(self, config: dict) -> dict | None:
        manager = get_history_manager()
        history = manager.get_history_data("CN10Y", "1mo")
        return self._build_daily_snapshot_from_history("CN10Y", config, history)

    def _fetch_us_treasury_yield_snapshot(self, config: dict) -> dict | None:
        manager = get_history_manager()
        history = manager.get_history_data("US10Y", "1mo")
        return self._build_daily_snapshot_from_history("US10Y", config, history)

    def _parse_market_number(self, value) -> float:
        if value is None:
            return 0
        text = str(value).strip().replace(",", "").replace("%", "")
        text = text.replace("\u2212", "-").replace("&minus;", "-")
        if not text or text in {"-", "--", "N/A"}:
            return 0
        return float(text)

    def _extract_nasdaq_value(self, html: str, label: str) -> str:
        pattern = (
            rf"<td[^>]*>\s*{re.escape(label)}\s*</td>\s*"
            rf"<td[^>]*>\s*([^<]+?)\s*</td>"
        )
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
        return None

    def _fetch_hsi_daily_bulletin_snapshot(self, config: dict) -> dict:
        """从恒生指数公司公开 daily bulletin 获取收盘快照。"""
        series_code = config.get("hsi_series_code")
        if not series_code:
            return None

        bulletin_url = "https://www.hsi.com.hk/data/eng/download/daily-bulletin.json"
        try:
            response = self.session.get(
                bulletin_url,
                headers={
                    **self.session.headers,
                    "Referer": config.get("source_url", bulletin_url),
                    "Accept": "application/json, text/plain, */*",
                },
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()

            series_item = next(
                (item for item in payload.get("indexSeriesList", []) if item.get("seriesCode") == series_code),
                None,
            )
            if not series_item:
                return None

            report = next((item for item in series_item.get("reportList", []) if item.get("reportType") == "idx"), None)
            if not report:
                return None

            report_dates = report.get("reportDate") or []
            if not report_dates:
                return None

            latest_entry = max(report_dates, key=lambda item: item.get("date", ""))
            csv_url = latest_entry.get("url")
            if not csv_url:
                return None

            csv_response = self.session.get(
                f"https://www.hsi.com.hk{csv_url}",
                headers={
                    **self.session.headers,
                    "Referer": bulletin_url,
                    "Accept": "text/csv, text/plain, */*",
                },
                timeout=15,
            )
            csv_response.raise_for_status()
            df = pd.read_csv(BytesIO(csv_response.content), encoding="utf-16", sep="\t", header=1)
            if df is None or df.empty:
                return None

            row = df.iloc[0]
            trade_date_raw = str(row.get("Trade Date") or "").strip()
            trade_date = None
            if trade_date_raw:
                try:
                    trade_date = datetime.strptime(trade_date_raw, "%Y%m%d").strftime("%Y-%m-%d")
                except ValueError:
                    trade_date = trade_date_raw

            price = self._parse_market_number(row.get("Index Close"))
            high = self._parse_market_number(row.get("Daily High"))
            low = self._parse_market_number(row.get("Daily Low"))
            change = self._parse_market_number(row.get("Point Change"))
            change_pct = self._parse_market_number(row.get("% Change"))

            if price is None:
                return None

            prev_close = price - change
            timestamp = datetime.now().isoformat()
            return {
                "name": config["name"],
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "prev_close": round(prev_close, 2),
                "high": round(high, 2) if high is not None else round(price, 2),
                "low": round(low, 2) if low is not None else round(price, 2),
                "open": round(prev_close, 2),
                "volume": 0,
                "timestamp": timestamp,
                "data_as_of": trade_date or latest_entry.get("date"),
                "trade_date": trade_date,
                "fetched_at": timestamp,
                "source": "hsi_daily_bulletin",
                "source_label": "恒生指数公司公开日更报表",
                "source_url": bulletin_url,
                "report_url": f"https://www.hsi.com.hk{csv_url}",
            }
        except Exception as e:
            print(f"  恒生指数公司官方日更报表获取失败: {e}")
            return None

    def get_sina_data(self, sina_code: str) -> dict:
        """从新浪财经获取数据"""
        try:
            url = f"https://hq.sinajs.cn/list={sina_code}"
            response = self.session.get(url, timeout=10)
            response.encoding = "gb2312"

            data = response.text
            if "var hq_str_" not in data:
                return None

            # 提取引号内的内容
            start = data.find('"') + 1
            end = data.rfind('"')
            if start <= 0 or end <= start:
                return None

            content = data[start:end]
            if not content:
                return None

            parts = content.split(",")

            # 根据市场类型解析数据
            if sina_code.startswith("sh") or sina_code.startswith("sz"):
                # A股格式: 名称,今日开盘价,昨日收盘价,当前价格,今日最高价,今日最低价,竞买价,竞卖价,成交股票数,成交金额,...
                if len(parts) < 10:
                    return None
                name = parts[0]
                open_price = float(parts[1])
                prev_close = float(parts[2])
                price = float(parts[3])
                high = float(parts[4])
                low = float(parts[5])
                volume = int(float(parts[8]))
                data_as_of = self._join_sina_datetime(
                    parts[30] if len(parts) > 30 else None,
                    parts[31] if len(parts) > 31 else None,
                )

            elif sina_code.startswith("hk") or sina_code.startswith("rt_hk"):
                # 港股指数格式: 代码,名称,今开,昨收,最高,最低,最新价,涨跌额,涨跌幅,...
                if len(parts) < 9:
                    return None
                name = parts[1] if len(parts) > 1 else sina_code
                open_price = float(parts[2]) if parts[2] else 0
                prev_close = float(parts[3]) if parts[3] else 0
                high = float(parts[4]) if parts[4] else 0
                low = float(parts[5]) if parts[5] else 0
                price = float(parts[6]) if len(parts) > 6 and parts[6] else 0
                change = float(parts[7]) if len(parts) > 7 and parts[7] else (price - prev_close)
                change_pct = float(parts[8]) if len(parts) > 8 and parts[8] else ((change / prev_close * 100) if prev_close else 0)
                volume = int(float(parts[11])) if len(parts) > 11 and parts[11] else 0
                data_as_of = self._join_sina_datetime(
                    parts[17] if len(parts) > 17 else None,
                    parts[18] if len(parts) > 18 else None,
                )

                return {
                    "name": name,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "prev_close": round(prev_close, 2),
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "volume": volume,
                    "timestamp": datetime.now().isoformat(),
                    "data_as_of": data_as_of,
                    "trade_date": data_as_of[:10] if data_as_of else None,
                }

            elif sina_code.startswith("gb_"):
                # 美股格式: 名称,当前价格,涨跌幅百分比,时间,涨跌额,昨收,最高,最低,开盘价,成交量,...
                if len(parts) < 6:
                    return None
                name = parts[0]
                price = float(parts[1]) if parts[1] else 0
                # [2]是涨跌幅百分比，[4]是涨跌额
                # 自己计算涨跌额和涨跌幅以确保一致性
                prev_close = float(parts[26]) if len(parts) > 26 and parts[26] else 0
                change = price - prev_close if price and prev_close else 0
                change_pct = (change / prev_close * 100) if prev_close else 0
                high = float(parts[6]) if len(parts) > 6 and parts[6] else 0
                low = float(parts[7]) if len(parts) > 7 and parts[7] else 0
                open_price = float(parts[8]) if len(parts) > 8 and parts[8] else price
                volume = 0
                data_as_of = parts[3] if len(parts) > 3 and parts[3] else None

                return {
                    "name": name,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "prev_close": round(prev_close, 2),
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "volume": volume,
                    "timestamp": datetime.now().isoformat(),
                    "data_as_of": data_as_of,
                    "trade_date": data_as_of[:10] if data_as_of else None,
                }

            elif sina_code.startswith("hf_"):
                # 期货格式: 最新价,未知,昨收,今开,最高,最低,时间,买一,卖一,未知,买量,卖量,日期,名称,未知
                if len(parts) < 14:
                    return None
                if "GC" in sina_code:
                    name = "黄金"
                elif "CL" in sina_code:
                    name = "WTI原油"
                else:
                    name = "期货"
                price = float(parts[0]) if parts[0] else 0
                prev_close = float(parts[2]) if parts[2] else 0
                open_price = float(parts[3]) if parts[3] else 0
                high = float(parts[4]) if parts[4] else 0
                low = float(parts[5]) if parts[5] else 0
                change = price - prev_close if price and prev_close else 0
                change_pct = (change / prev_close * 100) if prev_close else 0
                volume = 0
                data_as_of = self._join_sina_datetime(
                    parts[12] if len(parts) > 12 else None,
                    parts[6] if len(parts) > 6 else None,
                )

                return {
                    "name": name,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "prev_close": round(prev_close, 2),
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "volume": volume,
                    "timestamp": datetime.now().isoformat(),
                    "data_as_of": data_as_of,
                    "trade_date": data_as_of[:10] if data_as_of else None,
                }
            else:
                return None

            # 计算涨跌幅
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            return {
                "name": name,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "prev_close": round(prev_close, 2),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "volume": volume,
                "timestamp": datetime.now().isoformat(),
                "data_as_of": data_as_of,
                "trade_date": data_as_of[:10] if data_as_of else None,
            }

        except Exception as e:
            print(f"新浪获取数据失败 {sina_code}: {e}")
            return None

    def get_eastmoney_global_data(self, em_code: str) -> dict:
        """从东方财富获取国际指数数据"""
        try:
            url = f"https://push2.eastmoney.com/api/qt/ulist.np/get"
            params = {
                "secids": f"100.{em_code}",
                "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f19,f20,f21,f22,f23,f24,f25,f26,f27,f28,f29,f30,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100",
            }

            response = self.session.get(url, params=params, timeout=15)
            data = response.json()

            if data.get("data") and data["data"].get("diff"):
                d = data["data"]["diff"][0]
                # 解析东方财富字段
                # f2: 当前价格 (需要除以100)
                # f3: 涨跌幅 (需要除以100)
                # f4: 涨跌额 (需要除以100)
                # f12: 代码
                # f14: 名称
                # f15: 最高
                # f16: 最低
                # f17: 开盘
                # f18: 昨收
                price = d.get("f2", 0) / 100 if d.get("f2") else 0
                change_pct = d.get("f3", 0) / 100 if d.get("f3") else 0
                change = d.get("f4", 0) / 100 if d.get("f4") else 0
                name = d.get("f14", "")
                high = d.get("f15", 0) / 100 if d.get("f15") else 0
                low = d.get("f16", 0) / 100 if d.get("f16") else 0
                open_price = d.get("f17", 0) / 100 if d.get("f17") else 0
                prev_close = d.get("f18", 0) / 100 if d.get("f18") else 0

                return {
                    "name": name,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "prev_close": round(prev_close, 2),
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "volume": 0,
                    "timestamp": datetime.now().isoformat(),
                }
            return None
        except Exception as e:
            print(f"东方财富获取数据失败 {em_code}: {e}")
            return None

    def get_eastmoney_quote_data(self, config: dict) -> dict:
        """从东方财富免费快照接口获取指数数据。"""
        secid = config.get("eastmoney_secid")
        if not secid:
            return None

        try:
            response = self.session.get(
                "https://push2.eastmoney.com/api/qt/ulist.np/get",
                params={
                    "secids": secid,
                    "fields": "f12,f13,f14,f2,f3,f4,f15,f16,f17,f18,f86,f124",
                },
                headers={
                    **self.session.headers,
                    "Referer": "https://quote.eastmoney.com/",
                },
                timeout=15,
            )
            payload = response.json()
            rows = payload.get("data", {}).get("diff") or []
            if not rows:
                return None

            row = rows[0]
            price = (row.get("f2") or 0) / 100
            if price <= 0:
                return self.get_eastmoney_kline_snapshot(config)

            change_pct = (row.get("f3") or 0) / 100
            change = (row.get("f4") or 0) / 100
            prev_close = (row.get("f18") or 0) / 100
            open_price = (row.get("f17") or 0) / 100
            high = (row.get("f15") or 0) / 100
            low = (row.get("f16") or 0) / 100
            ts = row.get("f124")
            data_as_of = (
                datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                if ts else None
            )

            return {
                "name": config.get("name") or row.get("f14") or config.get("symbol"),
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "prev_close": round(prev_close, 2),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "volume": 0,
                "timestamp": datetime.now().isoformat(),
                "data_as_of": data_as_of,
                "trade_date": data_as_of[:10] if data_as_of else None,
            }
        except Exception as e:
            print(f"东方财富快照获取失败 {secid}: {e}")
            return None

    def get_eastmoney_kline_snapshot(self, config: dict) -> dict:
        """从东方财富日K接口提取最后一个交易日快照。"""
        secid = config.get("eastmoney_secid")
        if not secid:
            return None

        try:
            response = self.session.get(
                "https://push2his.eastmoney.com/api/qt/stock/kline/get",
                params={
                    "secid": secid,
                    "klt": "101",
                    "fqt": "0",
                    "lmt": "5",
                    "end": "20500000",
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                },
                headers={
                    **self.session.headers,
                    "Referer": "https://quote.eastmoney.com/",
                },
                timeout=15,
            )
            payload = response.json()
            klines = payload.get("data", {}).get("klines") or []
            if not klines:
                return None

            latest = klines[-1].split(",")
            previous = klines[-2].split(",") if len(klines) >= 2 else None
            if len(latest) < 6:
                return None

            trade_date = latest[0]
            open_price = float(latest[1])
            close = float(latest[2])
            high = float(latest[3])
            low = float(latest[4])
            volume = int(float(latest[5] or 0))
            prev_close = float(previous[2]) if previous and len(previous) >= 3 else 0
            change = close - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            if close <= 0:
                return None

            return {
                "name": config.get("name") or payload.get("data", {}).get("name") or config.get("symbol"),
                "price": round(close, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "prev_close": round(prev_close, 2),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "volume": volume,
                "timestamp": datetime.now().isoformat(),
                "data_as_of": trade_date,
                "trade_date": trade_date,
            }
        except Exception as e:
            print(f"东方财富日K快照获取失败 {secid}: {e}")
            return None

    def get_csindex_data(self, symbol: str) -> dict:
        """从中证指数获取数据 - 使用akshare"""
        try:
            # 使用akshare获取中证指数最新数据
            import akshare as ak
            df = ak.stock_zh_index_hist_csindex(symbol=symbol)
            if df is not None and len(df) > 0:
                # 获取最新一条数据
                latest = df.iloc[-1]
                return {
                    "name": latest.get('指数中文简称', symbol),
                    "price": round(float(latest.get('收盘', 0)), 2),
                    "change": round(float(latest.get('涨跌', 0)), 2),
                    "change_pct": round(float(latest.get('涨跌幅', 0)), 2),
                    "prev_close": round(float(latest.get('收盘', 0)) - float(latest.get('涨跌', 0)), 2),
                    "open": round(float(latest.get('开盘', 0)), 2),
                    "high": round(float(latest.get('最高', 0)), 2),
                    "low": round(float(latest.get('最低', 0)), 2),
                    "volume": int(float(latest.get('成交量', 0))),
                    "timestamp": datetime.now().isoformat(),
                }
            return None
        except Exception as e:
            print(f"中证指数获取数据失败 {symbol}: {e}")
            return None

    def get_csindex_official_data(self, config: dict) -> dict:
        """从中证官网公开接口获取指数最新数据"""
        symbol = config["symbol"]
        try:
            response = self.session.get(
                "https://www.csindex.com.cn/csindex-home/perf/index-perf-oneday",
                params={"indexCode": symbol},
                headers={
                    **self.session.headers,
                    "Referer": config.get("source_url", "https://www.csindex.com.cn/"),
                },
                timeout=15,
            )
            payload = response.json()
            header = payload.get("data", {}).get("intraDayHeader") or {}
            perf_list = payload.get("data", {}).get("intraDayPerfList") or []
            if not header:
                return None

            high = max((float(item.get("high", 0) or 0) for item in perf_list), default=0)
            low_candidates = [
                float(item.get("low", 0) or 0)
                for item in perf_list
                if item.get("low") not in (None, "")
            ]
            low = min(low_candidates) if low_candidates else 0
            trade_date = header.get("tradeDate")
            trade_time = header.get("tradeTime")
            data_as_of = " ".join(part for part in [trade_date, trade_time] if part)

            return {
                "name": config.get("name", symbol),
                "price": round(float(header.get("current") or 0), 2),
                "change": round(float(header.get("change") or 0), 2),
                "change_pct": round(float(header.get("changePct") or 0), 2),
                "prev_close": round(float(header.get("closePre") or 0), 2),
                "open": round(float(header.get("openToday") or 0), 2),
                "high": round(high, 2) if high else None,
                "low": round(low, 2) if low else None,
                "volume": float(header.get("tradingVol") or 0),
                "timestamp": datetime.now().isoformat(),
                "data_as_of": data_as_of or None,
                "trade_date": trade_date,
            }
        except Exception as e:
            print(f"中证官网数据获取失败 {symbol}: {e}")
            return None

    def get_deutsche_boerse_index_data(self, config: dict) -> dict:
        """从德交所官方页面提取DAX最新快照"""
        try:
            response = self.session.get(
                config["source_url"],
                headers={
                    **self.session.headers,
                    "Referer": config["source_url"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                timeout=15,
            )
            response.raise_for_status()

            match = re.search(
                r'<script id="serverApp-state" type="application/json">(.*?)</script>',
                response.text,
                re.S,
            )
            if not match:
                match = re.search(
                    r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
                    response.text,
                    re.S,
                )
            if not match:
                return None

            state = json.loads(match.group(1))
            key = (
                f'path_/data/price_information/single_params_isin={config["isin"]}'
                f'&mic={config["mic"]}'
            )
            price_info = state.get(key) or {}
            if not price_info:
                return None

            last_price = price_info.get("lastPrice")
            change_abs = price_info.get("changeToPrevDayAbsolute")
            prev_close = price_info.get("closingPricePrevTradingDay")
            if last_price is None:
                return None
            if change_abs is not None:
                prev_close = float(last_price) - float(change_abs)
            elif prev_close is None:
                return None

            data_as_of = price_info.get("timestampLastPrice")
            trade_date = data_as_of[:10] if data_as_of else None

            return {
                "name": config.get("name", "DAX"),
                "price": round(float(last_price), 2),
                "change": round(float(price_info.get("changeToPrevDayAbsolute") or 0), 2),
                "change_pct": round(float(price_info.get("changeToPrevDayInPercent") or 0), 2),
                "prev_close": round(float(prev_close), 2),
                "open": None,
                "high": round(float(price_info.get("dayHigh") or 0), 2) if price_info.get("dayHigh") else None,
                "low": round(float(price_info.get("dayLow") or 0), 2) if price_info.get("dayLow") else None,
                "volume": 0,
                "timestamp": datetime.now().isoformat(),
                "data_as_of": data_as_of,
                "trade_date": trade_date,
            }
        except Exception as e:
            print(f"德交所DAX数据获取失败: {e}")
            return None

    def _fetch_fund_nav(self, config: dict) -> dict | None:
        """从东方财富获取公募基金每日净值（日更）。"""
        fund_code = config["symbol"]
        try:
            response = self.session.get(
                "https://api.fund.eastmoney.com/f10/lsjz",
                params={
                    "callback": "jQuery",
                    "fundCode": fund_code,
                    "pageIndex": 1,
                    "pageSize": 3,
                    "_": int(datetime.now().timestamp() * 1000),
                },
                headers={
                    **self.session.headers,
                    "Referer": f"https://fund.eastmoney.com/{fund_code}.html",
                    "Host": "api.fund.eastmoney.com",
                },
                timeout=15,
            )
            text = response.text
            # 去掉 JSONP 包装
            start = text.find("(")
            end = text.rfind(")")
            if start < 0 or end <= start:
                return None
            payload = json.loads(text[start + 1 : end])
            records = payload.get("Data", {}).get("LSJZList") or []
            if not records:
                return None

            latest = records[0]
            previous = records[1] if len(records) >= 2 else None

            price = float(latest.get("DWJZ") or 0)
            trade_date = str(latest.get("FSRQ") or "")
            if price <= 0:
                return None

            prev_price = float(previous.get("DWJZ") or price) if previous else price
            change = round(price - prev_price, 4)
            change_pct = round((change / prev_price * 100) if prev_price else 0, 2)

            return {
                "name": config.get("name", fund_code),
                "price": round(price, 4),
                "change": round(change, 4),
                "change_pct": round(change_pct, 2),
                "prev_close": round(prev_price, 4),
                "open": round(price, 4),
                "high": round(price, 4),
                "low": round(price, 4),
                "volume": 0,
                "timestamp": datetime.now().isoformat(),
                "data_as_of": trade_date,
                "trade_date": trade_date,
            }
        except Exception as e:
            print(f"基金净值获取失败 {fund_code}: {e}")
            return None

    def get_nasdaq_index_data(self, config: dict) -> dict:
        """从Nasdaq官方指数页面提取指数快照。"""
        try:
            response = self.session.get(
                config["source_url"],
                headers={
                    **self.session.headers,
                    "Referer": config["source_url"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                timeout=15,
            )
            response.raise_for_status()
            html = response.text

            date_match = re.search(r"DATA AS OF\s+(\d{1,2}/\d{1,2}/\d{4})", html, re.I)
            data_as_of = None
            trade_date = None
            if date_match:
                parsed_date = datetime.strptime(date_match.group(1), "%m/%d/%Y")
                trade_date = parsed_date.strftime("%Y-%m-%d")
                data_as_of = trade_date

            last = self._parse_market_number(self._extract_nasdaq_value(html, "Last"))
            change = self._parse_market_number(self._extract_nasdaq_value(html, "Net Change"))
            high = self._parse_market_number(self._extract_nasdaq_value(html, "Day High"))
            low = self._parse_market_number(self._extract_nasdaq_value(html, "Day Low"))
            prev_close = last - change if last else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            if not last:
                return None

            return {
                "name": config.get("name", config["symbol"]),
                "price": round(last, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "prev_close": round(prev_close, 2),
                "open": None,
                "high": round(high, 2) if high else None,
                "low": round(low, 2) if low else None,
                "volume": 0,
                "timestamp": datetime.now().isoformat(),
                "data_as_of": data_as_of,
                "trade_date": trade_date,
            }
        except Exception as e:
            print(f"Nasdaq指数数据获取失败 {config.get('symbol')}: {e}")
            return None

    def get_dax_data(self) -> dict:
        """获取德国DAX指数数据 - 通过DAX ETF换算"""
        try:
            # 使用新浪获取DAX ETF数据
            url = "https://hq.sinajs.cn/list=gb_dax"
            response = self.session.get(url, timeout=10)
            response.encoding = "gb2312"
            
            import re
            match = re.search(r'"([^"]*)"', response.text)
            if match:
                data = match.group(1).split(",")
                if len(data) >= 4:
                    etf_price = float(data[1])
                    change_pct = float(data[2])
                    
                    # DAX ETF与DAX指数的换算比例 (约536.5)
                    ratio = 536.5
                    index_price = etf_price * ratio
                    
                    # 计算涨跌
                    prev_close = index_price / (1 + change_pct / 100)
                    change = index_price - prev_close
                    
                    return {
                        "name": "德国DAX指数",
                        "price": round(index_price, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "prev_close": round(prev_close, 2),
                        "open": round(index_price, 2),  # 使用当前价作为近似
                        "high": round(index_price * 1.005, 2),
                        "low": round(index_price * 0.995, 2),
                        "volume": 0,
                        "timestamp": datetime.now().isoformat(),
                    }
            return None
        except Exception as e:
            print(f"DAX数据获取失败: {e}")
            return None

    def get_etf_estimate_data(self, etf_code: str, base_price: float, index_name: str) -> dict:
        """通过ETF数据估算指数"""
        try:
            # 使用新浪获取ETF数据
            url = f"https://hq.sinajs.cn/list={etf_code}"
            response = self.session.get(url, timeout=10)
            response.encoding = "gb2312"
            
            import re
            match = re.search(r'"([^"]*)"', response.text)
            if match:
                data = match.group(1).split(",")
                if len(data) >= 6:
                    # ETF格式: 名称,今日开盘价,昨日收盘价,当前价格,今日最高价,今日最低价,...
                    etf_price = float(data[3]) if data[3] else 0
                    prev_close = float(data[2]) if data[2] else 0
                    open_price = float(data[1]) if data[1] else 0
                    high = float(data[4]) if data[4] else 0
                    low = float(data[5]) if data[5] else 0
                    
                    # 计算涨跌幅
                    change = etf_price - prev_close
                    change_pct = (change / prev_close * 100) if prev_close else 0
                    
                    # 使用ETF涨跌幅估算指数价格
                    # 假设指数与ETF涨跌幅相同
                    index_price = base_price * (1 + change_pct / 100)
                    index_change = index_price - base_price
                    
                    return {
                        "name": index_name,
                        "price": round(index_price, 2),
                        "change": round(index_change, 2),
                        "change_pct": round(change_pct, 2),
                        "prev_close": round(base_price, 2),
                        "open": round(base_price * (1 + (open_price - prev_close) / prev_close * 100) if prev_close else base_price, 2),
                        "high": round(base_price * (1 + (high - prev_close) / prev_close * 100) if prev_close else base_price, 2),
                        "low": round(base_price * (1 + (low - prev_close) / prev_close * 100) if prev_close else base_price, 2),
                        "volume": 0,
                        "timestamp": datetime.now().isoformat(),
                    }
            return None
        except Exception as e:
            print(f"ETF估算数据获取失败 {etf_code}: {e}")
            return None

    def get_etf_to_index_data(self, etf_code: str, ratio: float, index_name: str) -> dict:
        """通过ETF价格换算指数点位"""
        try:
            # 使用新浪获取ETF数据
            url = f"https://hq.sinajs.cn/list={etf_code}"
            response = self.session.get(url, timeout=10)
            response.encoding = "gb2312"
            
            import re
            match = re.search(r'"([^"]*)"', response.text)
            if match:
                data = match.group(1).split(",")
                if len(data) >= 6:
                    # 判断是A股ETF还是美股ETF格式
                    if etf_code.startswith("gb_"):
                        # 美股ETF格式: 名称,当前价格,涨跌幅,日期时间,涨跌额,昨收,今开,最高,最低,...
                        etf_price = float(data[1]) if data[1] else 0
                        change_pct = float(data[2]) if data[2] else 0
                        prev_close = float(data[5]) if data[5] else 0
                        open_price = float(data[6]) if data[6] else 0
                        high = float(data[7]) if data[7] else 0
                        low = float(data[8]) if data[8] else 0
                    else:
                        # A股ETF格式: 名称,今日开盘价,昨日收盘价,当前价格,今日最高价,今日最低价,...
                        etf_price = float(data[3]) if data[3] else 0
                        prev_close = float(data[2]) if data[2] else 0
                        open_price = float(data[1]) if data[1] else 0
                        high = float(data[4]) if data[4] else 0
                        low = float(data[5]) if data[5] else 0
                        change_pct = ((etf_price - prev_close) / prev_close * 100) if prev_close else 0
                    
                    # 通过换算比例计算指数点位
                    index_price = etf_price * ratio
                    index_prev_close = prev_close * ratio
                    index_open = open_price * ratio
                    index_high = high * ratio
                    index_low = low * ratio
                    
                    # 计算涨跌幅（统一计算，不依赖数据源返回的涨跌幅）
                    change = index_price - index_prev_close
                    change_pct = (change / index_prev_close * 100) if index_prev_close else 0
                    
                    return {
                        "name": index_name,
                        "price": round(index_price, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "prev_close": round(index_prev_close, 2),
                        "open": round(index_open, 2),
                        "high": round(index_high, 2),
                        "low": round(index_low, 2),
                        "volume": 0,
                        "timestamp": datetime.now().isoformat(),
                    }
            return None
        except Exception as e:
            print(f"ETF换算指数数据获取失败 {etf_code}: {e}")
            return None

    def _fetch_usdcny_rate(self) -> float | None:
        """从新浪财经获取实时美元/人民币中间价。"""
        try:
            r = self.session.get("https://hq.sinajs.cn/list=fx_susdcny", timeout=8)
            r.encoding = "gb2312"
            start = r.text.find('"') + 1
            end = r.text.rfind('"')
            if start <= 0 or end <= start:
                return None
            parts = r.text[start:end].split(",")
            # 第4字段(index 3)为最新价
            rate = float(parts[3]) if len(parts) > 3 and parts[3] else None
            return rate if rate and rate > 1 else None
        except Exception:
            return None

    def refresh_market_snapshot(self, force: bool = False) -> dict:
        """刷新实时行情快照，只保留真实数据"""
        if not force and self._is_snapshot_fresh():
            return self.cache

        result = dict(self.cache)

        for key, config in self.INDICES.items():
            if config.get("enabled", True) is False:
                continue

            cached = self.cache.get(key)
            if (
                config.get("update_frequency") == "daily"
                and not force
                and self._can_use_daily_cached_record(cached)
            ):
                result[key] = cached
                print(f"  [DAILY-CACHE] {config['name']}: 使用当日已验证快照")
                continue

            print(f"正在获取: {config['name']}")
            data = self._fetch_index_data(config)

            if not data:
                data = self._fetch_fallback_data(config)

            if data:
                result[key] = self._build_index_result(key, config, data)
                print(f"  [OK] {config['name']}: {data['price']}")
                continue

            if cached:
                result[key] = cached
                cached["data_note"] = (
                    cached.get("data_note") or ""
                ) + " 当前刷新失败，暂保留最近一次成功快照，避免标的从看板消失。"
                print(f"  [STALE] {config['name']}: 保留最近一次成功快照")
            else:
                print(f"  [SKIP] {config['name']}: 暂无可验证的实时数据")

        if result:
            self.cache = result
            self.last_update = datetime.now()

            # 为黄金附加人民币克价
            if "GOLD" in self.cache and self.cache["GOLD"].get("price"):
                usd_cny = self._fetch_usdcny_rate()
                if usd_cny:
                    self.cache["GOLD"]["cny_per_gram"] = round(
                        self.cache["GOLD"]["price"] / 31.1035 * usd_cny, 2
                    )
                    self.cache["GOLD"]["usd_cny"] = round(usd_cny, 4)
                    result = self.cache

        return self.cache

    def get_all_indices(self, force_refresh: bool = False) -> dict:
        """获取所有指数数据"""
        return self.refresh_market_snapshot(force=force_refresh)

    def _fetch_10y_closes(self, key: str) -> list | None:
        """从 AKShare 拉近10年收盘价，用于历史分位计算。"""
        config = self.INDICES.get(key, {})
        ten_years_ago = pd.Timestamp.now() - pd.DateOffset(years=10)
        try:
            df = None
            source   = config.get("source", "")
            sina_code = config.get("sina_code", "")

            if source == "sina":
                if sina_code.startswith(("sh", "sz")):
                    df = ak.stock_zh_index_daily_tx(symbol=sina_code)
                elif sina_code.startswith("gb_"):
                    sym = sina_code.replace("gb_", "").upper()
                    # 新浪美股指数代码以 $ 开头（如 gb_$inx），akshare 接口约定为 . 前缀
                    if sym.startswith("$"):
                        sym = "." + sym[1:]
                    df = ak.index_us_stock_sina(symbol=sym)
                elif sina_code.startswith("hf_"):
                    sym = "GC" if "GC" in sina_code else "CL"
                    df = ak.futures_foreign_hist(symbol=sym)
            elif source == "hsi_daily_bulletin":
                df = ak.stock_hk_index_daily_sina(symbol="HSI")
            elif source == "nasdaq_official":
                df = ak.index_us_stock_sina(symbol=".NDX")
            elif source == "deutsche_boerse":
                # 使用 DAX ETF 历史价格做分位代理（走势与指数一致）
                df = ak.index_us_stock_sina(symbol="DAX")
            elif source in ("fund_nav", "chinabond", "us_treasury"):
                mgr = get_history_manager()
                rows = mgr.get_history_data(key, "10y")
                if rows:
                    return [{"date": r["date"], "close": r["close"]} for r in rows if r.get("close")]
                return None

            # 港股指数兜底
            if df is None and config.get("type") == "hk" and config.get("symbol"):
                df = ak.stock_hk_index_daily_sina(symbol=config["symbol"])

            if df is None or len(df) == 0:
                return None

            date_col  = next((c for c in ["date", "Date", "日期"] if c in df.columns), None)
            close_col = next((c for c in ["close", "Close", "收盘", "收盤"] if c in df.columns), None)
            if not date_col or not close_col:
                return None

            df["_d"] = pd.to_datetime(df[date_col])
            df = df[df["_d"] >= ten_years_ago].sort_values("_d")
            return [
                {"date": row["_d"].strftime("%Y-%m-%d"), "close": float(row[close_col])}
                for _, row in df.iterrows()
                if row[close_col] and float(row[close_col]) > 0
            ] or None
        except Exception as e:
            print(f"  [{key}] 10年历史获取失败: {e}")
            return None

    def _compute_price_percentile_valuation(self, key: str) -> dict | None:
        """基于近10年收盘价/净值/收益率计算历史分位。"""
        rows = self._fetch_10y_closes(key)
        if not rows or len(rows) < 30:
            return None

        closes  = pd.Series([r["close"] for r in rows])
        current = float(closes.iloc[-1])
        pct     = round(float((closes < current).mean() * 100), 2)
        years   = round(len(rows) / 252, 1)

        # 债券收益率：高收益率 = 债便宜（信号逻辑反向）
        is_yield = key in {"CN10Y", "US10Y"}
        if is_yield:
            if pct >= 80:
                tone, label = "danger", "收益率高位"
            elif pct >= 40:
                tone, label = "warn",   "收益率中位"
            else:
                tone, label = "muted",  "收益率低位"
        else:
            if pct <= 20:
                tone, label = "danger", "历史低位"
            elif pct <= 60:
                tone, label = "warn",   "历史中位"
            else:
                tone, label = "muted",  "历史高位"

        config = self.INDICES.get(key, {})
        return {
            "price_percentile": pct,
            "price_min":    round(float(closes.min()), 4),
            "price_max":    round(float(closes.max()), 4),
            "data_points":  len(rows),
            "years_of_data": years,
            "data_start":   rows[0]["date"],
            "data_end":     rows[-1]["date"],
            "source":       config.get("source_label", "行情数据"),
            "source_url":   config.get("source_url", ""),
            "is_price_percentile": True,
            "signal_tone":  tone,
            "signal_label": label,
            "signal_note":  f"当前{'收益率' if is_yield else '价格'}处于近{years:.0f}年历史{pct:.1f}%分位",
        }

    def _decorate_valuation_signal(self, valuation: dict) -> dict:
        """Attach a simple DCA signal based on the 10Y PE percentile.

        This is a presentation rule, not a trading recommendation.
        """
        if not valuation:
            return valuation

        percentile = valuation.get("pe_percentile")
        if percentile is None:
            return valuation

        try:
            percentile = float(percentile)
        except Exception:
            return valuation

        if percentile <= 20:
            valuation["signal_tone"] = "danger"
            valuation["signal_label"] = "加倍定投"
            valuation["signal_note"] = f"PE历史分位 {percentile:.2f}% ，处于低位区"
        elif percentile <= 60:
            valuation["signal_tone"] = "warn"
            valuation["signal_label"] = "正常定投"
            valuation["signal_note"] = f"PE历史分位 {percentile:.2f}% ，处于中位区"
        else:
            valuation["signal_tone"] = "muted"
            valuation["signal_label"] = "谨慎定投"
            valuation["signal_note"] = f"PE历史分位 {percentile:.2f}% ，处于高位区"

        return valuation

    def get_valuation_data(self, key: str, current_price: float = None) -> dict:
        """只返回可验证的真实估值数据"""
        if key in self.DAILY_VALUATION_KEYS:
            return self._enrich_valuation_metadata(
                key,
                self._decorate_valuation_signal(self.get_csindex_pe_valuation(key)),
            )

        if key in self.MULTPL_PE_KEYS:
            return self._enrich_valuation_metadata(
                key,
                self._decorate_valuation_signal(self.get_spx_pe_valuation()),
            )

        if key in self.PRICE_PERCENTILE_KEYS:
            return self._enrich_valuation_metadata(key, self._compute_price_percentile_valuation(key))

        if key not in self.REALTIME_VALUATION_KEYS:
            return None

        try:
            config = self.INDICES.get(key, {})
            csindex_code = config.get("csindex_code")
            name = config.get("name", key)

            official_daily_data = self.get_csindex_pe_valuation(key)
            if official_daily_data:
                return self._enrich_valuation_metadata(
                    key,
                    self._decorate_valuation_signal(official_daily_data),
                )

            print(f"  [{name}] 尝试实时获取估值数据...")
            realtime_data = RealtimeValuationProvider.get_realtime_valuation(key, config)
            if not realtime_data or realtime_data.get("pe", 0) <= 0:
                return None

            realtime_data["is_realtime"] = True

            if csindex_code:
                try:
                    df = ak.stock_zh_index_hist_csindex(symbol=csindex_code)
                    if df is not None and len(df) > 0:
                        pe_data = df[["日期", "滚动市盈率"]].dropna()
                        if len(pe_data) > 0:
                            pe_values = pe_data["滚动市盈率"].astype(float)
                            current_pe = float(realtime_data["pe"])
                            data_start = pd.to_datetime(pe_data["日期"].min())
                            years_of_data = (datetime.now() - data_start).days / 365
                            realtime_data["pe_min"] = round(float(pe_values.min()), 2)
                            realtime_data["pe_max"] = round(float(pe_values.max()), 2)
                            realtime_data["pe_median"] = round(float(pe_values.median()), 2)
                            realtime_data["pe_percentile"] = round((pe_values < current_pe).mean() * 100, 2)
                            realtime_data["data_start"] = str(pe_data["日期"].min())
                            realtime_data["data_end"] = str(pe_data["日期"].max())
                            realtime_data["data_points"] = len(pe_data)
                            realtime_data["years_of_data"] = round(years_of_data, 1)
                except Exception as exc:
                    print(f"  [{name}] 历史PE范围补全失败: {exc}")

            return self._enrich_valuation_metadata(
                key,
                self._decorate_valuation_signal(realtime_data),
            )
        except Exception as e:
            print(f"获取估值数据失败 {key}: {e}")
            return None

    def get_csindex_pe_valuation(self, key: str) -> dict:
        """使用中证官网日频PE序列计算官方估值"""
        config = self.INDICES.get(key, {})
        csindex_code = config.get("csindex_code")
        if not csindex_code:
            return None

        try:
            response = self.session.get(
                "https://www.csindex.com.cn/csindex-home/perf/indexCsiDsPe",
                params={"indexCode": csindex_code},
                headers={
                    **self.session.headers,
                    "Referer": config.get("source_url", "https://www.csindex.com.cn/"),
                },
                timeout=20,
            )
            payload = response.json()
            rows = payload.get("data") or []
            if not rows:
                return None

            pe_values = pd.Series(
                [float(row["peg"]) for row in rows if row.get("peg") not in (None, "")],
                dtype="float64",
            )
            if pe_values.empty:
                return None

            latest = rows[-1]
            current_pe = float(latest["peg"])
            data_start = datetime.strptime(rows[0]["tradeDate"], "%Y%m%d")
            data_end = datetime.strptime(latest["tradeDate"], "%Y%m%d")

            return {
                "pe": round(current_pe, 2),
                "pe_min": round(float(pe_values.min()), 2),
                "pe_max": round(float(pe_values.max()), 2),
                "pe_median": round(float(pe_values.median()), 2),
                "pe_percentile": round((pe_values < current_pe).mean() * 100, 2),
                "data_start": data_start.strftime("%Y-%m-%d"),
                "data_end": data_end.strftime("%Y-%m-%d"),
                "data_points": len(pe_values),
                "years_of_data": round((data_end - data_start).days / 365, 1),
                "source": "中证指数官网",
                "source_url": config.get("source_url", "https://www.csindex.com.cn/"),
                "is_realtime": False,
                "is_simulated": False,
                "note": f"官方日频PE，截至 {data_end.strftime('%Y-%m-%d')}",
            }
        except Exception as e:
            print(f"中证官网PE数据获取失败 {key}: {e}")
            return None

    def _multpl_pe_cache_path(self) -> "Path":
        """SPX 月频 PE-TTM 序列的本地缓存路径。"""
        from pathlib import Path
        cache_dir = Path(__file__).parent / "valuation_data"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "SPX_pe_history.csv"

    def _is_multpl_pe_cache_fresh(self) -> bool:
        path = self._multpl_pe_cache_path()
        if not path.exists():
            return False
        age_hours = (time.time() - path.stat().st_mtime) / 3600
        return age_hours < self.MULTPL_PE_CACHE_TTL_HOURS

    def _parse_multpl_pe_table(self, html: str) -> list[dict] | None:
        """解析 multpl 的 by-month 表格为 [{date, pe}] 列表（按日期降序，第一行为当日估算）。"""
        table_match = re.search(r"<table[^>]*>(.*?)</table>", html, re.S | re.I)
        if not table_match:
            return None

        rows = re.findall(
            r"<td>\s*([A-Za-z]{3}\s*\d{1,2},\s*\d{4})\s*</td>\s*"
            r"<td[^>]*>\s*(?:<abbr[^>]*>[^<]*</abbr>|&\#x2002;|&nbsp;|\s)*\s*"
            r"([0-9]+\.?[0-9]*)\s*</td>",
            table_match.group(1),
            re.S,
        )
        if not rows:
            return None

        parsed = []
        for date_str, pe_str in rows:
            try:
                date_obj = datetime.strptime(date_str.strip().replace("  ", " "), "%b %d, %Y")
                pe_value = float(pe_str)
            except ValueError:
                continue
            if pe_value <= 0:
                continue
            parsed.append({"date": date_obj.strftime("%Y-%m-%d"), "pe": round(pe_value, 4)})
        return parsed or None

    def _fetch_multpl_pe_history(self) -> list[dict] | None:
        """从 multpl.com 拉取标普500月频 PE-TTM 历史（包含当月当日估算）。"""
        try:
            response = self.session.get(
                "https://www.multpl.com/s-p-500-pe-ratio/table/by-month",
                headers={
                    **self.session.headers,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Referer": "https://www.multpl.com/s-p-500-pe-ratio",
                },
                timeout=20,
            )
            response.raise_for_status()
            return self._parse_multpl_pe_table(response.text)
        except Exception as e:
            print(f"  multpl PE 历史获取失败: {e}")
            return None

    def _load_multpl_pe_cache(self) -> list[dict] | None:
        path = self._multpl_pe_cache_path()
        if not path.exists():
            return None
        try:
            df = pd.read_csv(path)
            if df is None or df.empty:
                return None
            df = df.sort_values("date", ascending=False)
            return [{"date": str(r["date"]), "pe": float(r["pe"])} for _, r in df.iterrows()]
        except Exception:
            return None

    def _save_multpl_pe_cache(self, rows: list[dict]):
        try:
            df = pd.DataFrame(rows)
            df.to_csv(self._multpl_pe_cache_path(), index=False)
        except Exception as e:
            print(f"  multpl PE 缓存写入失败: {e}")

    def _get_multpl_pe_series(self, force_refresh: bool = False) -> list[dict] | None:
        """获取 SPX 月频 PE-TTM 序列；优先本地缓存，过期或失效时回源 multpl.com。"""
        if not force_refresh and self._is_multpl_pe_cache_fresh():
            cached = self._load_multpl_pe_cache()
            if cached:
                return cached

        remote = self._fetch_multpl_pe_history()
        if remote:
            self._save_multpl_pe_cache(remote)
            return remote

        return self._load_multpl_pe_cache()

    def get_spx_pe_valuation(self) -> dict | None:
        """基于 multpl.com 月频 PE-TTM 序列，计算近10年滚动 PE 分位。

        - 当前PE：取序列第一行（multpl 当日基于 TTM EPS × 实时价格估算）。
        - 历史样本：取自第一行起最近 120 个月度数据点（每月 1 号），近似10年滚动 PE-TTM 历史。
        """
        rows = self._get_multpl_pe_series()
        if not rows or len(rows) < 30:
            return None

        try:
            current_pe = float(rows[0]["pe"])
            current_date = rows[0]["date"]
        except (KeyError, ValueError, IndexError):
            return None

        ten_years_ago = (datetime.now() - timedelta(days=365 * 10)).strftime("%Y-%m-%d")
        history_pool = [r for r in rows[1:] if r["date"] >= ten_years_ago]
        if len(history_pool) < 60:
            history_pool = rows[1:121] if len(rows) > 1 else rows[:]

        pe_values = pd.Series([float(r["pe"]) for r in history_pool], dtype="float64")
        if pe_values.empty:
            return None

        data_start = min(r["date"] for r in history_pool)
        data_end = max(r["date"] for r in history_pool)
        try:
            years_of_data = round(
                (datetime.strptime(data_end, "%Y-%m-%d") - datetime.strptime(data_start, "%Y-%m-%d")).days / 365,
                1,
            )
        except ValueError:
            years_of_data = round(len(history_pool) / 12, 1)

        return {
            "pe": round(current_pe, 2),
            "pe_min": round(float(pe_values.min()), 2),
            "pe_max": round(float(pe_values.max()), 2),
            "pe_median": round(float(pe_values.median()), 2),
            "pe_percentile": round(float((pe_values < current_pe).mean() * 100), 2),
            "data_start": data_start,
            "data_end": data_end,
            "data_points": len(history_pool),
            "years_of_data": years_of_data,
            "source": "multpl.com（标普官方EPS推导）",
            "source_url": "https://www.multpl.com/s-p-500-pe-ratio",
            "is_realtime": False,
            "is_simulated": False,
            "note": (
                f"基于标普官方TTM EPS与价格推导的月频PE历史；当前值 {current_pe:.2f} 取自 {current_date} 估算。"
            ),
        }

    def _estimate_pe_from_etf(self, key: str, etf_code: str, name: str) -> dict:
        """通过ETF价格走势估算PE"""
        try:
            config = self.INDICES.get(key, {})
            base_pe = config.get('base_pe', 15)
            
            # 获取ETF历史数据
            df = ak.stock_zh_index_daily_tx(symbol=etf_code)
            if df is not None and len(df) > 0:
                df['date'] = pd.to_datetime(df['date'])
                
                # 获取最近10年数据
                ten_years_ago = datetime.now() - timedelta(days=365*10)
                df_10y = df[df['date'] >= ten_years_ago]
                
                if len(df_10y) > 0:
                    # 计算价格分位数
                    latest_price = df_10y['close'].iloc[-1]
                    price_min = df_10y['close'].min()
                    price_max = df_10y['close'].max()
                    price_median = df_10y['close'].median()
                    price_percentile = (df_10y['close'] < latest_price).mean() * 100
                    
                    # 基于价格走势估算PE（简化模型）
                    # 假设PE与价格正相关，但受盈利增长影响
                    pe_estimate = base_pe * (0.7 + 0.6 * price_percentile / 100)
                    pe_min = base_pe * 0.6
                    pe_max = base_pe * 1.4
                    
                    result = {
                        'pe': round(pe_estimate, 2),
                        'pe_min': round(pe_min, 2),
                        'pe_max': round(pe_max, 2),
                        'pe_median': base_pe,
                        'pe_percentile': round(price_percentile, 1),
                        'data_start': str(df_10y['date'].min().date()),
                        'data_end': str(df_10y['date'].max().date()),
                        'data_points': len(df_10y),
                        'years_of_data': 10,
                        'source': f'ETF({etf_code})推断',
                        'is_simulated': True,
                        'note': '基于ETF价格走势估算，仅供参考（模拟数据）'
                    }
                    
                    # 添加股息率估算
                    base_dividend_yield = config.get('base_dividend_yield')
                    if base_dividend_yield:
                        # 基于PE倒数估算股息率
                        payout_ratio = 0.4
                        estimated_dividend_yield = (1 / pe_estimate * 100) * payout_ratio
                        dividend_yield = (estimated_dividend_yield + base_dividend_yield) / 2
                        result['dividend_yield'] = round(dividend_yield, 2)
                        result['dividend_yield_note'] = '基于PE估算'
                    
                    return result
        except Exception as e:
            print(f"  ETF推断PE失败 {name}: {e}")
        
        return None
    
    def _estimate_pe_from_base(self, key: str, name: str) -> dict:
        """基于历史平均PE和当前价格分位数估算PE"""
        try:
            config = self.INDICES.get(key, {})
            base_pe = config.get('base_pe', 15)
            sina_code = config.get('sina_code')
            
            if not sina_code:
                return None
            
            # 获取指数历史数据来计算价格分位数
            # 使用akshare获取历史数据
            if sina_code.startswith('sh') or sina_code.startswith('sz'):
                df = ak.stock_zh_index_daily_tx(symbol=sina_code)
            elif sina_code.startswith('hk'):
                # 港股指数
                df = ak.stock_hk_index_daily_sina(symbol=sina_code.replace('hk', ''))
            elif sina_code.startswith('gb_'):
                # 美股指数 - 使用新浪美股数据
                df = ak.index_us_stock_sina(symbol=sina_code.replace('gb_', '').upper())
            else:
                return None
            
            if df is not None and len(df) > 0:
                df['date'] = pd.to_datetime(df['date'])
                
                # 获取最近10年数据
                ten_years_ago = datetime.now() - timedelta(days=365*10)
                df_10y = df[df['date'] >= ten_years_ago]
                
                if len(df_10y) > 0:
                    # 获取当前价格
                    current_price = df_10y['close'].iloc[-1]
                    
                    # 计算价格分位数
                    price_percentile = (df_10y['close'] < current_price).mean() * 100
                    
                    # 基于价格分位数估算PE
                    pe_estimate = base_pe * (0.7 + 0.6 * price_percentile / 100)
                    pe_min = base_pe * 0.6
                    pe_max = base_pe * 1.4
                    
                    result = {
                        'pe': round(pe_estimate, 2),
                        'pe_min': round(pe_min, 2),
                        'pe_max': round(pe_max, 2),
                        'pe_median': base_pe,
                        'pe_percentile': round(price_percentile, 1),
                        'data_start': str(df_10y['date'].min().date()),
                        'data_end': str(df_10y['date'].max().date()),
                        'data_points': len(df_10y),
                        'years_of_data': 10,
                        'source': '历史数据推断',
                        'is_simulated': True,
                        'note': '基于历史平均PE和价格走势估算（模拟数据）'
                    }
                    
                    # 添加股息率估算
                    base_dividend_yield = config.get('base_dividend_yield')
                    if base_dividend_yield:
                        payout_ratio = 0.4
                        estimated_dividend_yield = (1 / pe_estimate * 100) * payout_ratio
                        dividend_yield = (estimated_dividend_yield + base_dividend_yield) / 2
                        result['dividend_yield'] = round(dividend_yield, 2)
                        result['dividend_yield_note'] = '基于PE估算'
                    
                    return result
        except Exception as e:
            print(f"  历史PE推断失败 {name}: {e}")
        
        return None

    def update_valuation_cache(self):
        """更新估值数据缓存"""
        try:
            print("正在更新估值数据缓存...")
            updated_cache = {}
            all_keys = (
                self.REALTIME_VALUATION_KEYS
                | self.DAILY_VALUATION_KEYS
                | self.PRICE_PERCENTILE_KEYS
                | self.MULTPL_PE_KEYS
            )
            for key, config in self.INDICES.items():
                if config.get("enabled", True) is False or key not in all_keys:
                    continue
                valuation = self.get_valuation_data(key, self.cache.get(key, {}).get("price"))
                if valuation:
                    updated_cache[key] = valuation
                    if valuation.get("is_price_percentile"):
                        print(f"  {config['name']}: {valuation.get('years_of_data')}年分位={valuation.get('price_percentile')}%")
                    else:
                        mark = " [实时]" if valuation.get("is_realtime") else ""
                        print(f"  {config['name']}: PE={valuation.get('pe')}, 分位={valuation.get('pe_percentile', 0):.1f}%{mark}")
            self._valuation_cache = updated_cache
            for key, cached in self.cache.items():
                if key in self._valuation_cache:
                    cached["valuation"] = self._valuation_cache[key]
                else:
                    cached.pop("valuation", None)
            self._valuation_cache_time = datetime.now()
            self._last_valuation_refresh = self._valuation_cache_time
            print("估值数据缓存更新完成")
        except Exception as e:
            print(f"更新估值缓存失败: {e}")

    def _generate_mock_data(self, config: dict) -> dict:
        """生成模拟实时数据"""
        import random

        # 合理的默认价格
        default_prices = {
            "CSI300": 4736,
            "HSTECH": 5200,
            "HSI": 22000,
            "OIL_WTI": 92,
            "GOLD": 2400,
            "CSI500": 5914,
            "DAX": 24132,
            "NDX": 26200,
            "SPX": 7470,
        }

        base_price = default_prices.get(config["symbol"], 1000)

        # 添加随机波动
        change_pct = random.uniform(-0.02, 0.02)
        price = base_price * (1 + change_pct)
        prev_close = base_price
        change = price - prev_close

        return {
            "name": config["name"],
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct * 100, 2),
            "prev_close": round(prev_close, 2),
            "open": round(base_price * random.uniform(0.995, 1.005), 2),
            "high": round(price * random.uniform(1.001, 1.01), 2),
            "low": round(price * random.uniform(0.99, 0.999), 2),
            "volume": int(random.uniform(1000000, 10000000)),
            "timestamp": datetime.now().isoformat(),
            "is_mock": True,
        }

    def get_akshare_history(self, key: str, period: str = "1mo", target_price: float = None) -> list:
        """使用akshare获取真实历史数据
        
        Args:
            key: 指数代码
            period: 时间周期
            target_price: 目标价格（用于校准ETF-based指数）
        """
        try:
            # 计算日期范围 - 使用当前日期
            days_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}
            days = days_map.get(period, 90)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            df = None
            is_etf_based = False  # 标记是否基于ETF数据换算

            # 根据指数类型选择不同的akshare接口
            if key == "CSI300":
                # 沪深300 - 使用腾讯接口（更稳定）
                df = ak.stock_zh_index_daily_tx(symbol="sh000300")
            elif key == "CSI500":
                # 中证A500 - 使用腾讯接口
                df = ak.stock_zh_index_daily_tx(symbol="sh000510")
            elif key == "CSI_DIVIDEND":
                # 中证红利低波动 - 使用ETF数据来估算走势
                df = ak.stock_zh_index_daily_tx(symbol="sh560150")
                is_etf_based = True
            elif key == "CSI_BAIJIU":
                # 中证白酒指数 - 新浪实时快照对应的免费日线
                df = ak.stock_zh_index_daily_tx(symbol="sz399997")
            elif key == "HSTECH":
                # 恒生科技 - 使用新浪港股接口
                df = ak.stock_hk_index_daily_sina(symbol="HSTECH")
            elif key == "NDX":
                # 纳斯达克100 - 使用新浪美股接口
                df = ak.index_us_stock_sina(symbol=".NDX")
            elif key == "SPX":
                # 标普500 - 使用新浪美股接口
                df = ak.index_us_stock_sina(symbol=".INX")
            elif key == "DAX":
                # 德国DAX - 使用DAX ETF来估算走势
                df = ak.index_us_stock_sina(symbol="DAX")
                is_etf_based = True
            elif key == "GOLD":
                # 黄金 - 使用COMEX黄金期货(GC)，与新浪hf_GC对应
                df = ak.futures_foreign_hist(symbol="GC")
            elif key == "OIL_WTI":
                # 原油 - 使用新浪外盘期货接口
                df = ak.futures_foreign_hist(symbol="CL")
            elif key == "XOP":
                # 标普油气ETF - 使用新浪美股接口
                df = ak.index_us_stock_sina(symbol="XOP")
            elif key == "WANJIA_GOLD":
                # 万家周期视野 - 使用akshare基金净值接口
                nav_df = ak.fund_open_fund_info_em(fund="025446", indicator="单位净值走势")
                if nav_df is not None and len(nav_df) > 0:
                    nav_df = nav_df.rename(columns={"净值日期": "date", "单位净值": "close"})
                    nav_df["open"] = nav_df["close"]
                    nav_df["high"] = nav_df["close"]
                    nav_df["low"] = nav_df["close"]
                    nav_df["volume"] = 0
                    df = nav_df[["date", "open", "high", "low", "close", "volume"]]

            if df is not None and len(df) > 0:
                # 转换数据格式
                # 统一列名 - 处理不同数据源的列名差异
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                elif 'Date' in df.columns:
                    df['date'] = pd.to_datetime(df['Date'])
                elif '日期' in df.columns:
                    df['date'] = pd.to_datetime(df['日期'])

                # 过滤日期范围 - 确保日期格式一致
                df['date'] = pd.to_datetime(df['date'])
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)
                df = df[df['date'] >= start_date]
                df = df[df['date'] <= end_date]

                # 如果是基于ETF的数据，需要根据目标价格校准
                if is_etf_based and target_price and len(df) > 0:
                    etf_latest = float(df.iloc[-1]['close'] if 'close' in df.columns else df.iloc[-1]['Close'])
                    ratio = target_price / etf_latest
                    
                    # 校准所有价格列
                    price_cols = ['open', 'close', 'high', 'low', 'Open', 'Close', 'High', 'Low']
                    for col in price_cols:
                        if col in df.columns:
                            df[col] = df[col] * ratio

                # 转换为列表格式
                result = []
                for _, row in df.iterrows():
                    # 根据数据源选择正确的列名
                    if '开盘' in df.columns:  # 中证指数数据
                        result.append({
                            "date": row['date'].strftime("%Y-%m-%d"),
                            "open": round(float(row.get('开盘', 0)), 2),
                            "high": round(float(row.get('最高', 0)), 2),
                            "low": round(float(row.get('最低', 0)), 2),
                            "close": round(float(row.get('收盘', 0)), 2),
                            "volume": int(float(row.get('成交量', 0))),
                        })
                    else:  # 其他数据源
                        result.append({
                            "date": row['date'].strftime("%Y-%m-%d"),
                            "open": round(float(row.get('open', row.get('Open', 0))), 2),
                            "high": round(float(row.get('high', row.get('High', 0))), 2),
                            "low": round(float(row.get('low', row.get('Low', 0))), 2),
                            "close": round(float(row.get('close', row.get('Close', 0))), 2),
                            "volume": int(float(row.get('volume', row.get('Volume', 0)))),
                        })
                return result
            return None
        except Exception as e:
            print(f"akshare获取历史数据失败 {key}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_historical_data(self, key: str, period: str = "1mo", realtime_price: float = None) -> list:
        """获取历史数据用于图表 - 带缓存机制
        
        Args:
            key: 指数代码
            period: 时间周期
            realtime_price: 实时价格（用于校准ETF-based指数的历史数据）
        """
        try:
            config = self.INDICES.get(key)
            if not config or config.get("enabled", True) is False:
                return []
            if config.get("history_available") is False:
                return []

            if key not in self.cache:
                data = self._fetch_index_data(config) or self._fetch_fallback_data(config)
                if data:
                    self.cache[key] = self._build_index_result(key, config, data)

            # 使用本地历史数据管理器获取数据（优先本地CSV，必要时从网络更新）
            manager = get_history_manager()
            data = manager.get_history_data(key, period)

            if data and len(data) > 0:
                # ETF 代理品校准：把 ETF 价格乘以比值还原为指数点位
                if config.get("history_etf_proxy") and self.cache.get(key):
                    index_price = self.cache[key].get("price")
                    if index_price and data[-1].get("close"):
                        ratio = index_price / data[-1]["close"]
                        data = [
                            {
                                **row,
                                "open": round(row["open"] * ratio, 2),
                                "high": round(row["high"] * ratio, 2),
                                "low": round(row["low"] * ratio, 2),
                                "close": round(row["close"] * ratio, 2),
                            }
                            for row in data
                        ]
                return self._decorate_history_rows(
                    key,
                    self._merge_realtime_snapshot_into_history(key, data),
                )
            return []
            return []
        except Exception as e:
            print(f"获取历史数据失败 {key}: {e}")
            return []

    def _decorate_history_rows(self, key: str, data: list) -> list:
        """Attach chart-level metadata while keeping the API response as an array."""
        if not data:
            return data
        config = self.INDICES.get(key, {})
        if config.get("history_source_type") != "ETF_PROXY":
            return data

        note = "历史走势使用 ETF 代理数据，仅供趋势参考，不等同于中证指数官方历史点位。"
        meta = {
            "history_source_type": "ETF_PROXY",
            "chart_badge": "ETF代理",
            "data_note": note,
            "history_note": note,
            "history_proxy_symbol": config.get("history_etf_proxy"),
        }
        return [{**row, **meta} for row in data]

    def _merge_realtime_snapshot_into_history(self, key: str, data: list) -> list:
        """用当前已验证快照补齐图表最后一个交易日，避免卡片和图表不同步。"""
        snapshot = self.cache.get(key)
        if not snapshot or not snapshot.get("trade_date") or snapshot.get("price") is None:
            return data

        trade_date = snapshot["trade_date"]
        existing_row = next((item for item in data if item.get("date") == trade_date), None)

        def pick_number(primary, fallback):
            return primary if primary not in (None, "") else fallback

        open_value = pick_number(
            existing_row.get("open") if existing_row else None,
            pick_number(snapshot.get("open"), snapshot["price"]),
        )
        high_candidates = [
            value for value in [
                existing_row.get("high") if existing_row else None,
                snapshot.get("high"),
                snapshot["price"],
            ]
            if value not in (None, "")
        ]
        low_candidates = [
            value for value in [
                existing_row.get("low") if existing_row else None,
                snapshot.get("low"),
                snapshot["price"],
            ]
            if value not in (None, "")
        ]
        volume_value = pick_number(
            existing_row.get("volume") if existing_row else None,
            snapshot.get("volume") or 0,
        )
        row = {
            "date": trade_date,
            "open": round(float(open_value), 2),
            "high": round(float(max(high_candidates)), 2),
            "low": round(float(min(low_candidates)), 2),
            "close": round(float(snapshot["price"]), 2),
            "volume": int(float(volume_value or 0)),
        }

        merged = [item for item in data if item.get("date") != trade_date]
        merged.append(row)
        merged.sort(key=lambda item: item["date"])
        return merged

    def get_akshare_history_with_calibration(self, key: str, period: str = "1mo", target_price: float = None) -> list:
        """获取历史数据并根据目标价格校准（用于ETF-based指数）"""
        try:
            # 计算日期范围
            days_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}
            days = days_map.get(period, 90)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            df = None
            is_etf_based = False

            if key == "CSI_DIVIDEND":
                # 使用红利低波ETF
                df = ak.stock_zh_index_daily_tx(symbol="sh560150")
                is_etf_based = True
            elif key == "DAX":
                # 使用DAX ETF
                df = ak.index_us_stock_sina(symbol="DAX")
                is_etf_based = True
            else:
                # 其他指数使用标准方法
                return self.get_akshare_history(key, period)

            if df is not None and len(df) > 0:
                # 处理日期列
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                elif 'Date' in df.columns:
                    df['date'] = pd.to_datetime(df['Date'])

                # 过滤日期
                df['date'] = pd.to_datetime(df['date'])
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)
                df = df[df['date'] >= start_date]
                df = df[df['date'] <= end_date]

                # 根据目标价格校准
                if is_etf_based and target_price and len(df) > 0:
                    etf_latest = float(df.iloc[-1]['close'] if 'close' in df.columns else df.iloc[-1]['Close'])
                    ratio = target_price / etf_latest
                    
                    # 校准所有价格列
                    price_cols = ['open', 'close', 'high', 'low', 'Open', 'Close', 'High', 'Low']
                    for col in price_cols:
                        if col in df.columns:
                            df[col] = df[col] * ratio

                # 转换为列表
                result = []
                for _, row in df.iterrows():
                    result.append({
                        "date": row['date'].strftime("%Y-%m-%d"),
                        "open": round(float(row.get('open', row.get('Open', 0))), 2),
                        "high": round(float(row.get('high', row.get('High', 0))), 2),
                        "low": round(float(row.get('low', row.get('Low', 0))), 2),
                        "close": round(float(row.get('close', row.get('Close', 0))), 2),
                        "volume": int(float(row.get('volume', row.get('Volume', 0)))),
                    })
                return result
            return None
        except Exception as e:
            print(f"校准历史数据失败 {key}: {e}")
            return None

    def _calibrate_data(self, data: list, target_price: float) -> list:
        """根据目标价格校准历史数据（用于ETF-based指数）

        Args:
            data: 原始历史数据
            target_price: 目标价格（当前实时价格）

        Returns:
            校准后的历史数据
        """
        if not data or len(data) == 0:
            return data

        # 获取最新价格
        latest_price = data[-1]['close']
        ratio = target_price / latest_price

        # 校准所有价格
        for item in data:
            item['open'] = round(item['open'] * ratio, 2)
            item['high'] = round(item['high'] * ratio, 2)
            item['low'] = round(item['low'] * ratio, 2)
            item['close'] = round(item['close'] * ratio, 2)

        return data

    def _generate_mock_historical_data(self, config: dict, period: str) -> list:
        """生成模拟历史数据用于展示"""
        import random

        # 合理的默认价格
        default_prices = {
            "CSI300": 4736,
            "HSTECH": 5200,
            "HSI": 22000,
            "OIL_WTI": 92,
            "GOLD": 2400,
            "CSI500": 5914,
            "DAX": 24132,
            "NDX": 26200,
            "SPX": 7470,
        }

        base_price = default_prices.get(config["symbol"], 1000)

        # 计算数据点数量
        days_map = {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 252}
        num_days = days_map.get(period, 66)

        # 生成随机游走数据
        data = []
        price = base_price * 0.9  # 从较低点开始
        end_date = datetime(2025, 4, 16)

        for i in range(num_days):
            date = end_date - timedelta(days=num_days - i - 1)

            # 随机涨跌幅 (-2% 到 +2%)
            change_pct = random.uniform(-0.02, 0.02)
            price = price * (1 + change_pct)

            # 生成OHLC数据
            open_price = price * random.uniform(0.995, 1.005)
            high = max(open_price, price) * random.uniform(1.001, 1.01)
            low = min(open_price, price) * random.uniform(0.99, 0.999)
            close = price
            volume = int(random.uniform(1000000, 10000000))

            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": volume,
            })

        return data

    def start_auto_update(self, interval: int = 30):
        """启动自动更新"""
        self.running = True

        def update_loop():
            while self.running:
                try:
                    data = self.refresh_market_snapshot(force=False)
                    if (
                        self._last_valuation_refresh is None
                        or (datetime.now() - self._last_valuation_refresh).total_seconds() >= self.VALUATION_REFRESH_SECONDS
                    ):
                        self.update_valuation_cache()
                        data = self.cache
                    if self.socketio:
                        self.socketio.emit("stock_update", data)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 数据更新完成\n")
                except Exception as e:
                    print(f"更新失败: {e}")
                time.sleep(interval)

        self.update_thread = Thread(target=update_loop, daemon=True)
        self.update_thread.start()
        print(f"自动更新已启动，间隔 {interval} 秒")

    def stop_auto_update(self):
        """停止自动更新"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        print("自动更新已停止")
