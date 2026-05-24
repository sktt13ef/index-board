# Stock Dashboard Data Sources

**Updated**: 2026-04-22

Principles:
- Official first.
- Use free stable official sources where possible.
- Daily and delayed symbols must show source and data time clearly.

## Current Display Paths

| Symbol | Cadence | Primary source | Fallback | Chart |
|---|---|---|---|---|
| CSI300 沪深300 | 实时/官方日内快照 | 中证指数官网 `index-perf-oneday?indexCode=000300` | 新浪 `sh000300` | 启用，最后一日 close 与卡片快照对齐 |
| CSI500 中证A500 | 实时/官方日内快照 | 中证指数官网 `index-perf-oneday?indexCode=000510` | 新浪 `sh000510` | 启用，最后一日 close 与卡片快照对齐 |
| CSI_DIVIDEND 中证红利低波动 | 日更/收盘后 | 中证指数官网 `index-perf-oneday?indexCode=H30269` | 东方财富 `2.H30269` | 禁用，历史图不展示 ETF 替代品 |
| CSI_BAIJIU 中证白酒指数 | 实时/新浪快照 | 新浪财经 `sz399997` | 东方财富 `0.399997` | 启用，历史图使用 `sz399997` 免费日线 |
| CN10Y 中国国债十年收益率 | 日更/官方曲线 | 中国债券信息网 `historyQuery` | 无 | 启用，卡片与历史都来自官方国债收益率曲线 |
| US10Y 美国国债十年收益率 | 日更/官方曲线 | U.S. Treasury `daily_treasury_yield_curve` | 无 | 启用，卡片与历史都来自官方 10 Yr 曲线 |
| HSTECH 恒生科技 | 日更/收盘后 | 新浪财经港股指数快照 `rt_hkHSTECH` | 无 | 启用，最后一日 close 与卡片快照对齐 |
| HSI 恒生指数 | 日更/官方报表 | 恒生指数公司 daily bulletin `hsi` | 无 | 启用，收盘后官方 daily bulletin 日更 |
| DAX 德国DAX | 日更/收盘后 | Deutsche Börse 官方页面 + STOXX 官方 3个月历史文件 | 3个月 | 启用，1月/3月可展示，6月/1年暂不开放 |
| NDX 纳斯达克100 | 延迟/收盘时点 | Nasdaq Global Indexes 官方页面 | 无 | 启用，最后一日 close 与卡片快照对齐 |
| SPX 标普500 | 延迟/收盘时点 | 新浪美股指数快照 `gb_$inx` | 无 | 启用，历史用 akshare `index_us_stock_sina(.INX)` |
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

### DAX

Deutsche Börse official page still provides the live close snapshot. For history charts, the backend uses the official STOXX public 3-month text file and keeps the chart limited to the supported free window.

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

Only show charts when we have a real historical series and the last point can align with the card snapshot:
- Enabled: `CSI300`, `CSI500`, `CSI_BAIJIU`, `CN10Y`, `US10Y`, `HSTECH`, `HSI`, `DAX`, `NDX`, `SPX`, `GOLD`, `OIL_WTI`
- Disabled: `CSI_DIVIDEND`

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
