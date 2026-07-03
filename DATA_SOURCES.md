# Stock Dashboard Data Sources

**Updated**: 2026-06-30

Principles:
- Official first.
- Use free stable official sources where possible.
- Daily and delayed symbols must show source and data time clearly.
- Every card exposes a trust label: `官方`, `官方延迟`, `第三方`, or `备用源`.
- Every chart series exposes its own trust label. `ETF代理收益`, `同源价格/收益`, and `复权收益` must never be described as official total return.

Trust policy:
- `官方`: data comes from the index provider, exchange, treasury, or official bond yield publisher.
- `官方延迟`: official publisher, but delayed or end-of-day.
- `第三方`: free market-data relay such as Sina, Tencent, Yahoo, or Eastmoney; values are real market snapshots but not the primary official publisher.
- `代理`: ETF or investable-product series used only as a comparable return proxy.
- `同源`: repeated same-source price line, not a real total-return series.

## Current Display Paths

| Symbol | Cadence | Primary source | Fallback | Chart |
|---|---|---|---|---|
| CSI300 沪深300 | 实时/官方日内快照 | 中证指数官网 `index-perf-oneday?indexCode=000300` | 新浪 `sh000300` | 启用，最后一日 close 与卡片快照对齐 |
| CSI500 中证A500 | 实时/官方日内快照 | 中证指数官网 `index-perf-oneday?indexCode=000510` | 新浪 `sh000510` | 启用，最后一日 close 与卡片快照对齐 |
| CSI500_INDEX 中证500 | 实时/官方日内快照 | 中证指数官网 `index-perf-oneday?indexCode=000905` | 新浪 `sh000905` | 启用，中证官网官方日线；支持指数收益 `000905` 与全收益 `H00905` |
| CSI_DIVIDEND 中证红利低波动 | 日更/收盘后 | 中证指数官网 `index-perf-oneday?indexCode=H30269` | 东方财富 `2.H30269` | 启用，中证官网官方日线；支持指数收益/全收益/红利回报；官方股息率 D/P 每日追加入库 |
| CSI_DIVIDEND_100 中证红利低波100 | 日更/收盘后 | 中证指数官网 `index-perf-oneday?indexCode=930955` | 东方财富 `2.930955` | 启用，中证官网官方日线；支持指数收益/全收益/红利回报；官方股息率 D/P 每日追加入库 |
| CSI300_DIVIDEND_LOW_VOL 沪深300红利低波 | 日更/收盘后 | 中证指数官网 `index-perf-oneday?indexCode=930740` | 东方财富 `2.930740` | 启用，中证官网官方日线；支持指数收益/全收益/红利回报；官方股息率 D/P 每日追加入库 |
| CSI_DIVIDEND_QUALITY 红利质量 | 日更/收盘后 | 中证指数官网 `index-perf?indexCode=931468` | 东方财富 `2.931468` | 启用，中证官网官方日线；全收益 `921468`；红利回报由价格/全收益指数反推；官方股息率 D/P 每日追加入库 |
| CSI_ALL_DIVIDEND_QUALITY 中证红利质量 | 日更/收盘后 | 中证指数官网 `index-perf?indexCode=932315` | 东方财富 `2.932315` | 启用，中证官网官方日线；全收益 `932315CNY010`；红利回报由价格/全收益指数反推；官方股息率 D/P 每日追加入库 |
| CSI_CASH_FLOW 中证现金流 | 日更/收盘后 | 中证指数官网 `index-perf?indexCode=932365` | 东方财富 `2.932365` | 启用，中证官网官方日线；全收益 `932365CNY010`；红利回报由价格/全收益指数反推；官方股息率 D/P 每日追加入库 |
| CNI_FREE_CASH_FLOW 国证自由现金流 | 日更/收盘后 | 国证指数网 `index_hist_cni(980092)` | 东方财富 `0.980092` | 启用，国证官方日线；收益指数 `480092`；红利回报由价格/收益指数反推；暂不展示官方股息率 |
| CSI_BAIJIU 中证白酒指数 | 实时/新浪快照 | 新浪财经 `sz399997` | 东方财富 `0.399997` | 启用，历史图使用 `sz399997` 免费日线 |
| CHINEXT 创业板指 | 实时/新浪快照 | 新浪财经 `sz399006` | 东方财富 `0.399006` | 启用，历史图使用腾讯免费日线 |
| STAR50 科创50 | 实时/新浪快照 | 新浪财经 `sh000688` | 东方财富 `1.000688` | 启用，估值优先使用中证指数官网日频 PE |
| STAR100 科创100 | 实时/新浪快照 | 新浪财经 `sh000698` | 东方财富 `1.000698` | 启用，估值优先使用中证指数官网日频 PE |
| CN10Y 中国国债十年收益率 | 日更/官方曲线 | 中国债券信息网 `historyQuery` | 无 | 启用，卡片与历史都来自官方国债收益率曲线 |
| US10Y 美国国债十年收益率 | 日更/官方曲线 | U.S. Treasury `daily_treasury_yield_curve` | 无 | 启用，卡片与历史都来自官方 10 Yr 曲线 |
| HSTECH 恒生科技 | 日更/收盘后 | 新浪财经港股指数快照 `rt_hkHSTECH` | 无 | 启用，最后一日 close 与卡片快照对齐 |
| HSI 恒生指数 | 日更/官方报表 | 恒生指数公司 daily bulletin `hsi` | 无 | 启用，收盘后官方 daily bulletin 日更 |
| DAX 德国DAX | 日更/收盘后 | Deutsche Börse 官方页面 + STOXX 官方 3个月历史文件 | 3个月 | 启用，1月/3月可展示，6月/1年暂不开放 |
| NDX 纳斯达克100 | 延迟/收盘时点 | Nasdaq Global Indexes 官方页面 | 无 | 启用，最后一日 close 与卡片快照对齐 |
| SPX 标普500 | 延迟/收盘时点 | 新浪美股指数快照 `gb_$inx` | 无 | 启用，历史用 akshare `index_us_stock_sina(.INX)` |
| XOP 标普油气ETF | 延迟/收盘时点 | 新浪美股快照 `gb_xop` | 无 | 启用，历史用 akshare `index_us_stock_sina(XOP)` |
| WANJIA_GOLD 万家周期视野C | 日更/基金净值 | 东方财富基金净值 `025446` | 无 | 启用，按交易日日更净值 |
| BTCUSD 比特币 | 实时 | Coinbase Exchange `BTC-USD` | Binance 公共市场数据 | 启用，Coinbase 断连时清楚标记备用源 |
| ETHUSD 以太币 | 实时 | Coinbase Exchange `ETH-USD` | Binance 公共市场数据 | 启用，Coinbase 断连时清楚标记备用源 |
| GOLD 黄金 | 延迟 | 新浪外盘期货快照 `hf_GC` | 无 | 启用，最后一日 close 与卡片快照对齐 |
| OIL_WTI WTI原油 | 延迟 | 新浪外盘期货快照 `hf_CL` | 无 | 启用，最后一日 close 与卡片快照对齐 |

## Field Contract

Frontend cards always display:
- `update_label`: `实时` / `日更` / `延迟`
- `source_label`: data source
- `source_url`: source link
- `data_as_of`: source-provided data timestamp
- `fetched_at`: time this service fetched it
- `data_note`: current source note or fallback note

## Local SQLite Cache

The dashboard uses a local SQLite database to avoid pulling every remote source on each page load:

- DB path: `data/market_cache.sqlite3`
- Snapshot table: `snapshots`, storing the latest verified card payload for each symbol.
- History tables: `history_meta` and `history_points`, storing daily OHLC rows by `key + series`.
- Valuation table: `valuations`, storing PE / percentile payloads.
- Status endpoint: `/api/cache/status`

Cache TTL:

- Realtime / delayed snapshots: 10 minutes.
- Daily snapshots: 1 hour.
- Historical series: 24 hours.
- Valuations: 1 hour.

History rows include a `source_signature` derived from source type, source symbol, and series code. If a symbol is moved to a different source, old local rows are treated as stale and refreshed instead of being reused under the new source label.

## Chart Performance Policy

The chart API supports full-history data with `period=all`. The frontend uses this for the `成立以来` button.

To keep rendering fast:

- The backend keeps full raw rows in SQLite.
- The frontend requests chart-sized payloads with `max_points`.
- Server-side downsampling keeps first/last points and each bucket's high/low close points, so large moves remain visible.
- The browser caches chart responses by `symbol + period + series`, so switching away and back does not re-request the same curve.

Use no `max_points` parameter only for data audit or export, not normal page rendering.

## Curve Audit

Run:

```powershell
cd C:\Users\ka\Documents\trae_projects\huangxiade\stock_dashboard
python audit_history_curves.py --force
```

The script writes `CURVE_QUALITY_REPORT.md` and checks:

- missing series;
- non-positive values;
- duplicated or unordered dates;
- large calendar gaps;
- abnormal daily jumps;
- proxy / same-source "total return" labels.

The CSI official history endpoint can return a `1990-01-01` placeholder/base row for some series. The parser filters that row so all-history charts do not get visually distorted by a fake early date.

## Key Parsing Rules

### HSTECH `rt_hkHSTECH`

Sina HK index snapshot fields are not ordinary stock fields:

```text
0  code
1  name
2  open
3  prev_close
4  high
5  low
6  last
7  change
8  change_pct
11 volume
17 date
18 time
```

Key fields:
- `price` uses `parts[6]`
- `change` uses `parts[7]`
- `change_pct` uses `parts[8]`
- `data_as_of` uses `parts[17] + " " + parts[18]`

### HSI `hsi`

Official daily bulletin snapshot for Hang Seng Index:
- source series code: `hsi`
- official page: `https://www.hsi.com.hk/index360/eng/indexes?id=00001.00`
- report type: `idx`

### CSI_BAIJIU `sz399997`

- Current snapshot uses Sina `sz399997`.
- History uses `ak.stock_zh_index_daily_tx(symbol="sz399997")`.
- This is 中证白酒指数, not 医药.

### CSI Dividend Low Volatility Family

- `CSI_DIVIDEND`: 中证红利低波动，价格指数 `H30269`，全收益指数 `H20269`。
- `CSI_DIVIDEND_100`: 中证红利低波动100，价格指数 `930955`，全收益指数 `H20955`。
- `CSI300_DIVIDEND_LOW_VOL`: 沪深300红利低波动，价格指数 `930740`，全收益指数 `H20740`。
- `CSI_DIVIDEND_QUALITY`: 红利质量，价格指数 `931468`，全收益指数 `921468`。
- `CSI_ALL_DIVIDEND_QUALITY`: 中证红利质量，价格指数 `932315`，全收益指数 `932315CNY010`。
- `CSI_CASH_FLOW`: 中证现金流，价格指数 `932365`，全收益指数 `932365CNY010`。
- `CNI_FREE_CASH_FLOW`: 国证自由现金流，价格指数 `980092`，收益指数 `480092`。
- Card snapshots use CSI official `index-perf-oneday`.
- Charts use CSI official `index-perf` daily history. `series=price` aligns the latest price-index chart point to the card snapshot; `series=total_return` stays on the official total-return daily series and is not overwritten by the price-index snapshot.
- Ten-year charts are available from the official `index-perf` endpoint when the endpoint returns enough history.
- `dividend_return` 显示为“滚动一年红利回报率”，由官方价格指数和官方全收益/收益指数逐日计算分红贡献，再滚动 252 个交易日复利。
- 日分红贡献因子：`(全收益指数_t / 全收益指数_t-1) / (价格指数_t / 价格指数_t-1) - 1`；滚动一年贡献率：`product(1 + 日分红贡献因子, 252个交易日) - 1`。
- 该曲线不是指数公司直接发布的点位估值 `D/P` 字段，也不等同于成分股当前静态股息率；它反映过去一年实际进入全收益指数的红利回报。原始价格指数和全收益指数均可追溯；本地 SQLite 保存推导后的每日曲线，后续每日增量更新。
- `dividend_yield` 显示为“官方股息率”，来自中证官网估值指标文件 `oss-ch.csindex.com.cn/.../indicator/{indexCode}indicator.xls` 的 `股息率1` 字段。该文件当前只返回近期约 20 个交易日，因此本地 SQLite/CSV 只在来源签名一致时合并并每日追加，逐步积累长期 D/P 曲线。
- `CNI_FREE_CASH_FLOW` 暂无可稳定复用的官方股息率字段，只展示由国证价格指数与收益指数反推的红利回报率。

### CHINEXT / STAR50 / STAR100

- 创业板指 uses Sina `sz399006` as the free realtime card source and Tencent history for charts.
- 科创50 / 科创100 use Sina realtime snapshots with Eastmoney fallback.
- For STAR50 / STAR100 valuation, the backend can reuse official CSI daily PE history because both are CSI indices with published daily PE series.

### CN10Y

- Current and history both come from ChinaBond public yield curve.
- Use `tenYear` as the card and chart value.

### US10Y

- Current and history both come from U.S. Treasury daily yield curve.
- Use `BC_10YEAR` as the card and chart value.

### Nasdaq NDX

Nasdaq official page provides:
- `DATA AS OF`
- `Last`
- `Net Change`
- `Day High`
- `Day Low`

Because `Previous Close` and `Net Change(%)` can drift in some windows, the backend uses:

```text
prev_close = Last - Net Change
change_pct = Net Change / prev_close * 100
```

### SPX 标普500

- Card snapshot uses Sina US index `gb_$inx`. Sina returns a 30-field row whose layout is index-specific:
  - `[1]` last price
  - `[5]` open, `[6]` day high, `[7]` day low
  - `[26]` previous close
- The shared Sina parser computes `change = price - prev_close` and `change_pct` directly from those fields.
- History uses akshare `index_us_stock_sina(symbol=".INX")`, which is the same series as the Sina card.
- Valuation tile uses **monthly TTM PE history from multpl.com** (derived from S&P Dow Jones official EPS):
  - URL: `https://www.multpl.com/s-p-500-pe-ratio/table/by-month`
  - Current PE comes from the table's first row (multpl's same-day estimate based on TTM EPS × live price).
  - Historical samples: 120 month-start rows (~10 years), giving a true rolling 10y PE percentile.
  - Local cache: `valuation_data/SPX_pe_history.csv`, refreshed every 12 h.
  - Output fields are isomorphic with the CSI路径 (`pe`, `pe_min/max/median`, `pe_percentile`, `data_points`, `years_of_data`).

### XOP 标普油气ETF

- Card snapshot uses Sina US quote `gb_xop`.
- History uses `ak.index_us_stock_sina(symbol="XOP")`.
- This is an ETF, not a broad equity index, so the current dashboard does not attach a PE tile.

### WANJIA_GOLD 万家周期视野C

- Card snapshot uses Eastmoney public fund NAV path for code `025446`.
- History uses the same daily NAV series, so the card and chart stay on one truth source.
- This is a fund NAV series, not an index PE series, so the current dashboard does not attach a PE tile.

### DAX

Deutsche Börse official page still provides the live close snapshot. For history charts, the backend uses the official STOXX public 3-month text file and keeps the chart limited to the supported free window.

Current total-return policy, updated 2026-07-02:
- DAX chart price series uses STOXX public `h_3mdaxk.txt` (`DAXK`, price index).
- DAX chart total-return series uses STOXX public `h_3mdax.txt` (`DAX`, performance/total-return index).
- FTSE100 chart price series uses the LSE page Refinitiv widget RIC `.FTSE`.
- FTSE100 chart total-return series uses the LSE page Refinitiv widget RIC `.TRIUKX`; available history starts from the first returned date, currently 2017-10-06.
- CAC40 remains price-only in the dashboard. Free CAC40 GR candidates tested so far are unstable, protected, or return only a single point/short window, so the dashboard does not fabricate a total-return line.

### Valuation Signal

For wide indices with real PE history, the card shows:
- current trailing PE
- 10-year PE percentile
- a DCA prompt badge

Default rule:
- `pe_percentile <= 20`: red badge, show `加倍定投`
- `20 < pe_percentile <= 60`: amber badge, show `正常定投`
- `pe_percentile > 60`: muted badge, show `谨慎定投`

This is a display rule for long-term DCA, not a trading recommendation.

## Chart Policy

Only show charts when we have a real historical series. Price-index charts align the last point with the card snapshot when the card source provides a newer same-day snapshot:
- Enabled: `CSI300`, `CSI500`, `CSI500_INDEX`, `CSI_DIVIDEND`, `CSI_DIVIDEND_100`, `CSI300_DIVIDEND_LOW_VOL`, `CSI_BAIJIU`, `CHINEXT`, `STAR50`, `STAR100`, `CN10Y`, `US10Y`, `HSTECH`, `HSI`, `DAX`, `NDX`, `SPX`, `XOP`, `WANJIA_GOLD`, `GOLD`, `OIL_WTI`
- Disabled: none by default

The history endpoint first merges the current snapshot into the latest day, then merges with local CSV. If the last day already exists, keep history-source `open/high/low/volume`, overwrite only `close` with the card snapshot, and correct the day's range using the snapshot values.

## Validation

Run:

```powershell
cd C:\Users\ka\Documents\trae_projects\huangxiade\stock_dashboard
python validate_data_quality.py
```

Checks:
- All visible symbols return a card snapshot.
- `price - prev_close` matches `change`.
- Enabled chart symbols have history whose last close matches the card price.
- `CSI_DIVIDEND` does not leak proxy history.
