# Market Dashboard Data Sources

Updated: 2026-05-29

Principles:

- Official or quasi-official sources are preferred where free public access is available.
- Third-party free quotes are labelled as third-party and, where relevant, delayed.
- Percentiles and DCA-style labels are calculated by this project. They are not official ratings and are not investment advice.
- Do not invent missing source metadata. Unknown fields should be empty/null or explicitly described as limited.

## Field Contract

Frontend cards should expose these fields when available:

| Field | Meaning |
|---|---|
| `source_label` | Human-readable data source name |
| `source_url` | Source page link; missing URL is a warning, not a hard failure |
| `source_type` | `官方` / `准官方` / `第三方` / `项目计算` |
| `is_official_source` | `true` only for official quote sources |
| `data_as_of` | Source-provided data date/time |
| `fetched_at` | Time this service fetched or built the card |
| `data_note` | Source limitation or field interpretation note |
| `delay_note` | Delay/third-party reminder where applicable |
| `percentile_type` | `PE分位` / `月频PE分位` / `价格分位` / `收益率分位` / `净值分位` |
| `percentile_window` | Dynamic sample-window label, such as `样本近10年` or `样本约5.6年` |
| `is_calculated_metric` | Whether the percentile/label is calculated by this project |

## Current Display Paths

| Symbol | Snapshot source | Source type | Valuation / percentile | Chart policy |
|---|---|---|---|---|
| CSI300 沪深300 | 中证指数官网 `index-perf-oneday?indexCode=000300` | 官方 | 中证指数官网日频 PE 序列；项目计算 PE 分位 | Official/akshare history, last point aligned to card |
| CSI500 中证A500 | 中证指数官网 `index-perf-oneday?indexCode=000510` | 官方 | 中证指数官网日频 PE 序列；样本较短，约 1.7 年 | Official/akshare history, last point aligned to card |
| CSI_DIVIDEND 中证红利低波动 | 中证指数官网 `index-perf-oneday?indexCode=H30269` | 官方 | 中证指数官网日频 PE 序列 | Current point and PE are official; chart uses ETF proxy `sh560150` and must show `ETF代理` |
| CSI_BAIJIU 中证白酒指数 | 新浪财经 `sz399997` | 第三方 | 中证指数官网日频 PE 序列 | Free daily history, last point aligned to card |
| CHINEXT 创业板指 | 新浪财经 `sz399006` | 第三方 | Project-calculated price percentile | Free daily history, last point aligned to card |
| STAR50 科创50 | 新浪财经 `sh000688` | 第三方 | 中证指数官网日频 PE 序列；样本约 5.9 年 | Free daily history, last point aligned to card |
| STAR100 科创100 | 新浪财经 `sh000698` | 第三方 | 中证指数官网日频 PE 序列；样本约 2.9 年 | Free daily history, last point aligned to card |
| HSTECH 恒生科技 | 新浪财经港股指数快照 `rt_hkHSTECH` | 第三方 | Project-calculated price percentile, sample since index launch | Free daily history, last point aligned to card |
| HSI 恒生指数 | 恒生指数公司 Daily Bulletin | 官方 | Project-calculated price percentile | Official daily bulletin history |
| NDX 纳斯达克100 | Nasdaq Global Indexes official page | 官方 | Project-calculated price percentile | Free history via akshare/Sina series, last point aligned to card |
| SPX 标普500 | 新浪财经美股指数快照 `gb_$inx` | 第三方 | multpl.com monthly PE table; project-calculated monthly PE percentile | Free history via akshare/Sina series, last point aligned to card |
| XOP 标普油气ETF | 新浪财经美股快照 `gb_xop` | 第三方 | Project-calculated price percentile | Free history via akshare/Sina series, last point aligned to card |
| DAX 德国DAX | Deutsche Boerse official page | 官方 | Project-calculated price percentile | STOXX public free history is limited to about 3 months |
| GOLD 黄金 | 新浪财经外盘期货快照 `hf_GC` | 第三方 | Project-calculated price percentile | Third-party delayed reference quote/history |
| OIL_WTI WTI原油 | 新浪财经外盘期货快照 `hf_CL` | 第三方 | Project-calculated price percentile | Third-party delayed reference quote/history |
| CN10Y 中国十年国债收益率 | 中国债券信息网收益率曲线 | 准官方 | Project-calculated yield percentile | ChinaBond public yield curve |
| US10Y 美国十年国债收益率 | U.S. Treasury Daily Treasury Yield Curve | 官方 | Project-calculated yield percentile | U.S. Treasury official daily yield curve |
| WANJIA_GOLD 万家周期视野C | 东方财富基金净值 | 第三方 | Project-calculated NAV percentile | Eastmoney fund NAV history |

## CSI_DIVIDEND ETF Proxy Rule

`CSI_DIVIDEND` keeps its historical chart, but the chart is not official index history.

Required API/chart metadata:

```json
{
  "history_source_type": "ETF_PROXY",
  "chart_badge": "ETF代理",
  "data_note": "历史走势使用 ETF 代理数据，仅供趋势参考，不等同于中证指数官方历史点位。"
}
```

The frontend must show: `ETF代理历史，仅供趋势参考`.

## Percentile Rules

- PE percentile: calculated by this project from PE history, even when the PE series itself comes from an official source.
- Monthly PE percentile: used for SPX via multpl.com monthly table.
- Price percentile: calculated from historical closes.
- Yield percentile: calculated from historical 10-year yield values.
- NAV percentile: calculated from historical fund NAV.

Sample windows must be dynamic. Do not hardcode `十年分位` when the available sample is shorter, for example:

- `PE分位，样本约1.7年`
- `PE分位，样本约2.9年`
- `价格分位，样本约5.6年`
- `月频PE分位，样本近10年`

## Validation

Run:

```powershell
.\.runtime\python\python.exe validate_data_quality.py
```

The validator checks:

- every visible card returns a snapshot;
- every card has source labels and either source time or fetch time;
- third-party sources carry a third-party or delay reminder;
- calculated percentiles have `percentile_type` and `percentile_window`;
- `CSI_DIVIDEND` history is either `ETF_PROXY` or explicitly disabled;
- PE percentile and price/yield/NAV percentile fields are not mixed;
- project-generated DCA-style labels are disclosed as project rules;
- missing `source_url` is a warning, not a hard failure.
