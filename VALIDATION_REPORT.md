# 数据质量硬门槛报告

生成时间：2026-07-09 00:22:21

结果汇总：PASS 681，WARN 1，FAIL 0。

| 状态 | 标的 | 检查项 | 说明 |
|---|---|---|---|
| PASS | registry | required_fields | source registry complete |
| PASS | CSI_DIVIDEND | csi_dividend_codes | H30269/H20269 |
| PASS | CSI_DIVIDEND_100 | csi_dividend_codes | 930955/H20955 |
| PASS | CSI300_DIVIDEND_LOW_VOL | csi_dividend_codes | 930740/H20740 |
| PASS | CSI_DIVIDEND_QUALITY | csi_dividend_codes | 931468/921468 |
| PASS | CSI_ALL_DIVIDEND_QUALITY | csi_dividend_codes | 932315/932315CNY010 |
| PASS | CSI_CASH_FLOW | csi_dividend_codes | 932365/932365CNY010 |
| PASS | CNI_FREE_CASH_FLOW | csi_dividend_codes | 980092/480092 |
| PASS | DAX | allowed_periods | 1mo/3mo only |
| PASS | SPX | parser_contract | price = float(parts[1]) |
| PASS | SPX | parser_contract | open_price = float(parts[5]) |
| PASS | SPX | parser_contract | high = float(parts[6]) |
| PASS | SPX | parser_contract | low = float(parts[7]) |
| PASS | SPX | parser_contract | prev_close = float(parts[26]) |
| PASS | HSTECH | parser_contract | price = float(parts[6]) |
| PASS | HSTECH | parser_contract | change = float(parts[7]) |
| PASS | HSTECH | parser_contract | change_pct = float(parts[8]) |
| PASS | HSTECH | parser_contract | parts[17] |
| PASS | HSTECH | parser_contract | parts[18] |
| WARN | cards | visible_symbols | temporarily unavailable snapshots: DAX |
| PASS | CSI300 | card_field:update_label | OK |
| PASS | CSI300 | card_field:source_label | OK |
| PASS | CSI300 | card_field:source_url | OK |
| PASS | CSI300 | card_field:data_as_of | OK |
| PASS | CSI300 | card_field:fetched_at | OK |
| PASS | CSI300 | card_field:data_note | OK |
| PASS | CSI300 | positive_price | OK |
| PASS | CSI300 | change_math | OK |
| PASS | CSI300 | change_pct_math | OK |
| PASS | CSI300 | source_trust | 备用源 |
| PASS | CSI300 | freshness | 82s |
| PASS | CSI300 | valuation_scope | OK |
| PASS | CSI500 | card_field:update_label | OK |
| PASS | CSI500 | card_field:source_label | OK |
| PASS | CSI500 | card_field:source_url | OK |
| PASS | CSI500 | card_field:data_as_of | OK |
| PASS | CSI500 | card_field:fetched_at | OK |
| PASS | CSI500 | card_field:data_note | OK |
| PASS | CSI500 | positive_price | OK |
| PASS | CSI500 | change_math | OK |
| PASS | CSI500 | change_pct_math | OK |
| PASS | CSI500 | source_trust | 备用源 |
| PASS | CSI500 | freshness | 75s |
| PASS | CSI500 | valuation_scope | OK |
| PASS | CSI500_INDEX | card_field:update_label | OK |
| PASS | CSI500_INDEX | card_field:source_label | OK |
| PASS | CSI500_INDEX | card_field:source_url | OK |
| PASS | CSI500_INDEX | card_field:data_as_of | OK |
| PASS | CSI500_INDEX | card_field:fetched_at | OK |
| PASS | CSI500_INDEX | card_field:data_note | OK |
| PASS | CSI500_INDEX | positive_price | OK |
| PASS | CSI500_INDEX | change_math | OK |
| PASS | CSI500_INDEX | change_pct_math | OK |
| PASS | CSI500_INDEX | source_trust | 备用源 |
| PASS | CSI500_INDEX | freshness | 74s |
| PASS | CSI500_INDEX | valuation_scope | OK |
| PASS | CSI_DIVIDEND | card_field:update_label | OK |
| PASS | CSI_DIVIDEND | card_field:source_label | OK |
| PASS | CSI_DIVIDEND | card_field:source_url | OK |
| PASS | CSI_DIVIDEND | card_field:data_as_of | OK |
| PASS | CSI_DIVIDEND | card_field:fetched_at | OK |
| PASS | CSI_DIVIDEND | card_field:data_note | OK |
| PASS | CSI_DIVIDEND | positive_price | OK |
| PASS | CSI_DIVIDEND | change_math | OK |
| PASS | CSI_DIVIDEND | change_pct_math | OK |
| PASS | CSI_DIVIDEND | source_trust | 官方 |
| PASS | CSI_DIVIDEND | freshness | 545s |
| PASS | CSI_DIVIDEND | valuation_scope | OK |
| PASS | CSI_DIVIDEND_100 | card_field:update_label | OK |
| PASS | CSI_DIVIDEND_100 | card_field:source_label | OK |
| PASS | CSI_DIVIDEND_100 | card_field:source_url | OK |
| PASS | CSI_DIVIDEND_100 | card_field:data_as_of | OK |
| PASS | CSI_DIVIDEND_100 | card_field:fetched_at | OK |
| PASS | CSI_DIVIDEND_100 | card_field:data_note | OK |
| PASS | CSI_DIVIDEND_100 | positive_price | OK |
| PASS | CSI_DIVIDEND_100 | change_math | OK |
| PASS | CSI_DIVIDEND_100 | change_pct_math | OK |
| PASS | CSI_DIVIDEND_100 | source_trust | 官方 |
| PASS | CSI_DIVIDEND_100 | freshness | 544s |
| PASS | CSI_DIVIDEND_100 | valuation_scope | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | card_field:update_label | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | card_field:source_label | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | card_field:source_url | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | card_field:data_as_of | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | card_field:fetched_at | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | card_field:data_note | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | positive_price | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | change_math | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | change_pct_math | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | source_trust | 官方 |
| PASS | CSI300_DIVIDEND_LOW_VOL | freshness | 542s |
| PASS | CSI300_DIVIDEND_LOW_VOL | valuation_scope | OK |
| PASS | CSI_DIVIDEND_QUALITY | card_field:update_label | OK |
| PASS | CSI_DIVIDEND_QUALITY | card_field:source_label | OK |
| PASS | CSI_DIVIDEND_QUALITY | card_field:source_url | OK |
| PASS | CSI_DIVIDEND_QUALITY | card_field:data_as_of | OK |
| PASS | CSI_DIVIDEND_QUALITY | card_field:fetched_at | OK |
| PASS | CSI_DIVIDEND_QUALITY | card_field:data_note | OK |
| PASS | CSI_DIVIDEND_QUALITY | positive_price | OK |
| PASS | CSI_DIVIDEND_QUALITY | change_math | OK |
| PASS | CSI_DIVIDEND_QUALITY | change_pct_math | OK |
| PASS | CSI_DIVIDEND_QUALITY | source_trust | 官方 |
| PASS | CSI_DIVIDEND_QUALITY | freshness | 540s |
| PASS | CSI_DIVIDEND_QUALITY | valuation_scope | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | card_field:update_label | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | card_field:source_label | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | card_field:source_url | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | card_field:data_as_of | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | card_field:fetched_at | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | card_field:data_note | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | positive_price | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | change_math | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | change_pct_math | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | source_trust | 官方 |
| PASS | CSI_ALL_DIVIDEND_QUALITY | freshness | 538s |
| PASS | CSI_ALL_DIVIDEND_QUALITY | valuation_scope | OK |
| PASS | CSI_CASH_FLOW | card_field:update_label | OK |
| PASS | CSI_CASH_FLOW | card_field:source_label | OK |
| PASS | CSI_CASH_FLOW | card_field:source_url | OK |
| PASS | CSI_CASH_FLOW | card_field:data_as_of | OK |
| PASS | CSI_CASH_FLOW | card_field:fetched_at | OK |
| PASS | CSI_CASH_FLOW | card_field:data_note | OK |
| PASS | CSI_CASH_FLOW | positive_price | OK |
| PASS | CSI_CASH_FLOW | change_math | OK |
| PASS | CSI_CASH_FLOW | change_pct_math | OK |
| PASS | CSI_CASH_FLOW | source_trust | 官方 |
| PASS | CSI_CASH_FLOW | freshness | 537s |
| PASS | CSI_CASH_FLOW | valuation_scope | OK |
| PASS | CNI_FREE_CASH_FLOW | card_field:update_label | OK |
| PASS | CNI_FREE_CASH_FLOW | card_field:source_label | OK |
| PASS | CNI_FREE_CASH_FLOW | card_field:source_url | OK |
| PASS | CNI_FREE_CASH_FLOW | card_field:data_as_of | OK |
| PASS | CNI_FREE_CASH_FLOW | card_field:fetched_at | OK |
| PASS | CNI_FREE_CASH_FLOW | card_field:data_note | OK |
| PASS | CNI_FREE_CASH_FLOW | positive_price | OK |
| PASS | CNI_FREE_CASH_FLOW | change_math | OK |
| PASS | CNI_FREE_CASH_FLOW | change_pct_math | OK |
| PASS | CNI_FREE_CASH_FLOW | source_trust | 官方 |
| PASS | CNI_FREE_CASH_FLOW | freshness | 40s |
| PASS | CNI_FREE_CASH_FLOW | valuation_scope | OK |
| PASS | CSI_BAIJIU | card_field:update_label | OK |
| PASS | CSI_BAIJIU | card_field:source_label | OK |
| PASS | CSI_BAIJIU | card_field:source_url | OK |
| PASS | CSI_BAIJIU | card_field:data_as_of | OK |
| PASS | CSI_BAIJIU | card_field:fetched_at | OK |
| PASS | CSI_BAIJIU | card_field:data_note | OK |
| PASS | CSI_BAIJIU | positive_price | OK |
| PASS | CSI_BAIJIU | change_math | OK |
| PASS | CSI_BAIJIU | change_pct_math | OK |
| PASS | CSI_BAIJIU | source_trust | 第三方 |
| PASS | CSI_BAIJIU | freshness | 39s |
| PASS | CSI_BAIJIU | valuation_scope | OK |
| PASS | CHINEXT | card_field:update_label | OK |
| PASS | CHINEXT | card_field:source_label | OK |
| PASS | CHINEXT | card_field:source_url | OK |
| PASS | CHINEXT | card_field:data_as_of | OK |
| PASS | CHINEXT | card_field:fetched_at | OK |
| PASS | CHINEXT | card_field:data_note | OK |
| PASS | CHINEXT | positive_price | OK |
| PASS | CHINEXT | change_math | OK |
| PASS | CHINEXT | change_pct_math | OK |
| PASS | CHINEXT | source_trust | 第三方 |
| PASS | CHINEXT | freshness | 39s |
| PASS | CHINEXT | valuation_scope | OK |
| PASS | STAR50 | card_field:update_label | OK |
| PASS | STAR50 | card_field:source_label | OK |
| PASS | STAR50 | card_field:source_url | OK |
| PASS | STAR50 | card_field:data_as_of | OK |
| PASS | STAR50 | card_field:fetched_at | OK |
| PASS | STAR50 | card_field:data_note | OK |
| PASS | STAR50 | positive_price | OK |
| PASS | STAR50 | change_math | OK |
| PASS | STAR50 | change_pct_math | OK |
| PASS | STAR50 | source_trust | 第三方 |
| PASS | STAR50 | freshness | 39s |
| PASS | STAR50 | valuation_scope | OK |
| PASS | STAR100 | card_field:update_label | OK |
| PASS | STAR100 | card_field:source_label | OK |
| PASS | STAR100 | card_field:source_url | OK |
| PASS | STAR100 | card_field:data_as_of | OK |
| PASS | STAR100 | card_field:fetched_at | OK |
| PASS | STAR100 | card_field:data_note | OK |
| PASS | STAR100 | positive_price | OK |
| PASS | STAR100 | change_math | OK |
| PASS | STAR100 | change_pct_math | OK |
| PASS | STAR100 | source_trust | 第三方 |
| PASS | STAR100 | freshness | 39s |
| PASS | STAR100 | valuation_scope | OK |
| PASS | CN10Y | card_field:update_label | OK |
| PASS | CN10Y | card_field:source_label | OK |
| PASS | CN10Y | card_field:source_url | OK |
| PASS | CN10Y | card_field:data_as_of | OK |
| PASS | CN10Y | card_field:fetched_at | OK |
| PASS | CN10Y | card_field:data_note | OK |
| PASS | CN10Y | positive_price | OK |
| PASS | CN10Y | change_math | OK |
| PASS | CN10Y | change_pct_math | yield/spread pct may use source-specific point-change convention |
| PASS | CN10Y | source_trust | 官方 |
| PASS | CN10Y | freshness | 39s |
| PASS | CN10Y | valuation_scope | OK |
| PASS | US10Y | card_field:update_label | OK |
| PASS | US10Y | card_field:source_label | OK |
| PASS | US10Y | card_field:source_url | OK |
| PASS | US10Y | card_field:data_as_of | OK |
| PASS | US10Y | card_field:fetched_at | OK |
| PASS | US10Y | card_field:data_note | OK |
| PASS | US10Y | positive_price | OK |
| PASS | US10Y | change_math | OK |
| PASS | US10Y | change_pct_math | yield/spread pct may use source-specific point-change convention |
| PASS | US10Y | source_trust | 官方 |
| PASS | US10Y | freshness | 39s |
| PASS | US10Y | valuation_scope | OK |
| PASS | HSTECH | card_field:update_label | OK |
| PASS | HSTECH | card_field:source_label | OK |
| PASS | HSTECH | card_field:source_url | OK |
| PASS | HSTECH | card_field:data_as_of | OK |
| PASS | HSTECH | card_field:fetched_at | OK |
| PASS | HSTECH | card_field:data_note | OK |
| PASS | HSTECH | positive_price | OK |
| PASS | HSTECH | change_math | OK |
| PASS | HSTECH | change_pct_math | OK |
| PASS | HSTECH | source_trust | 第三方 |
| PASS | HSTECH | freshness | 82s |
| PASS | HSTECH | valuation_scope | OK |
| PASS | HSI | card_field:update_label | OK |
| PASS | HSI | card_field:source_label | OK |
| PASS | HSI | card_field:source_url | OK |
| PASS | HSI | card_field:data_as_of | OK |
| PASS | HSI | card_field:fetched_at | OK |
| PASS | HSI | card_field:data_note | OK |
| PASS | HSI | positive_price | OK |
| PASS | HSI | change_math | OK |
| PASS | HSI | change_pct_math | OK |
| PASS | HSI | source_trust | 官方 |
| PASS | HSI | freshness | 75s |
| PASS | HSI | valuation_scope | OK |
| PASS | NDX | card_field:update_label | OK |
| PASS | NDX | card_field:source_label | OK |
| PASS | NDX | card_field:source_url | OK |
| PASS | NDX | card_field:data_as_of | OK |
| PASS | NDX | card_field:fetched_at | OK |
| PASS | NDX | card_field:data_note | OK |
| PASS | NDX | positive_price | OK |
| PASS | NDX | change_math | OK |
| PASS | NDX | change_pct_math | OK |
| PASS | NDX | source_trust | 官方延迟 |
| PASS | NDX | freshness | 3s |
| PASS | NDX | valuation_scope | OK |
| PASS | SPX | card_field:update_label | OK |
| PASS | SPX | card_field:source_label | OK |
| PASS | SPX | card_field:source_url | OK |
| PASS | SPX | card_field:data_as_of | OK |
| PASS | SPX | card_field:fetched_at | OK |
| PASS | SPX | card_field:data_note | OK |
| PASS | SPX | positive_price | OK |
| PASS | SPX | change_math | OK |
| PASS | SPX | change_pct_math | OK |
| PASS | SPX | source_trust | 第三方 |
| PASS | SPX | freshness | 2s |
| PASS | SPX | valuation_scope | OK |
| PASS | SPX | spx_valuation_trust | multpl.com（标普官方EPS推导） |
| PASS | XOP | card_field:update_label | OK |
| PASS | XOP | card_field:source_label | OK |
| PASS | XOP | card_field:source_url | OK |
| PASS | XOP | card_field:data_as_of | OK |
| PASS | XOP | card_field:fetched_at | OK |
| PASS | XOP | card_field:data_note | OK |
| PASS | XOP | positive_price | OK |
| PASS | XOP | change_math | OK |
| PASS | XOP | change_pct_math | OK |
| PASS | XOP | source_trust | 第三方 |
| PASS | XOP | freshness | 2s |
| PASS | XOP | valuation_scope | OK |
| PASS | WANJIA_GOLD | card_field:update_label | OK |
| PASS | WANJIA_GOLD | card_field:source_label | OK |
| PASS | WANJIA_GOLD | card_field:source_url | OK |
| PASS | WANJIA_GOLD | card_field:data_as_of | OK |
| PASS | WANJIA_GOLD | card_field:fetched_at | OK |
| PASS | WANJIA_GOLD | card_field:data_note | OK |
| PASS | WANJIA_GOLD | positive_price | OK |
| PASS | WANJIA_GOLD | change_math | OK |
| PASS | WANJIA_GOLD | change_pct_math | OK |
| PASS | WANJIA_GOLD | source_trust | 第三方 |
| PASS | WANJIA_GOLD | freshness | 0s |
| PASS | WANJIA_GOLD | valuation_scope | OK |
| PASS | GOLD | card_field:update_label | OK |
| PASS | GOLD | card_field:source_label | OK |
| PASS | GOLD | card_field:source_url | OK |
| PASS | GOLD | card_field:data_as_of | OK |
| PASS | GOLD | card_field:fetched_at | OK |
| PASS | GOLD | card_field:data_note | OK |
| PASS | GOLD | positive_price | OK |
| PASS | GOLD | change_math | OK |
| PASS | GOLD | change_pct_math | OK |
| PASS | GOLD | source_trust | 第三方 |
| PASS | GOLD | freshness | 75s |
| PASS | GOLD | valuation_scope | OK |
| PASS | OIL_WTI | card_field:update_label | OK |
| PASS | OIL_WTI | card_field:source_label | OK |
| PASS | OIL_WTI | card_field:source_url | OK |
| PASS | OIL_WTI | card_field:data_as_of | OK |
| PASS | OIL_WTI | card_field:fetched_at | OK |
| PASS | OIL_WTI | card_field:data_note | OK |
| PASS | OIL_WTI | positive_price | OK |
| PASS | OIL_WTI | change_math | OK |
| PASS | OIL_WTI | change_pct_math | OK |
| PASS | OIL_WTI | source_trust | 第三方 |
| PASS | OIL_WTI | freshness | 75s |
| PASS | OIL_WTI | valuation_scope | OK |
| PASS | CSI_ALL_SHARE | card_field:update_label | OK |
| PASS | CSI_ALL_SHARE | card_field:source_label | OK |
| PASS | CSI_ALL_SHARE | card_field:source_url | OK |
| PASS | CSI_ALL_SHARE | card_field:data_as_of | OK |
| PASS | CSI_ALL_SHARE | card_field:fetched_at | OK |
| PASS | CSI_ALL_SHARE | card_field:data_note | OK |
| PASS | CSI_ALL_SHARE | positive_price | OK |
| PASS | CSI_ALL_SHARE | change_math | OK |
| PASS | CSI_ALL_SHARE | change_pct_math | OK |
| PASS | CSI_ALL_SHARE | source_trust | 官方 |
| PASS | CSI_ALL_SHARE | freshness | 550s |
| PASS | CSI_ALL_SHARE | valuation_scope | OK |
| PASS | CSI1000 | card_field:update_label | OK |
| PASS | CSI1000 | card_field:source_label | OK |
| PASS | CSI1000 | card_field:source_url | OK |
| PASS | CSI1000 | card_field:data_as_of | OK |
| PASS | CSI1000 | card_field:fetched_at | OK |
| PASS | CSI1000 | card_field:data_note | OK |
| PASS | CSI1000 | positive_price | OK |
| PASS | CSI1000 | change_math | OK |
| PASS | CSI1000 | change_pct_math | OK |
| PASS | CSI1000 | source_trust | 官方 |
| PASS | CSI1000 | freshness | 549s |
| PASS | CSI1000 | valuation_scope | OK |
| PASS | CSI2000 | card_field:update_label | OK |
| PASS | CSI2000 | card_field:source_label | OK |
| PASS | CSI2000 | card_field:source_url | OK |
| PASS | CSI2000 | card_field:data_as_of | OK |
| PASS | CSI2000 | card_field:fetched_at | OK |
| PASS | CSI2000 | card_field:data_note | OK |
| PASS | CSI2000 | positive_price | OK |
| PASS | CSI2000 | change_math | OK |
| PASS | CSI2000 | change_pct_math | OK |
| PASS | CSI2000 | source_trust | 官方 |
| PASS | CSI2000 | freshness | 547s |
| PASS | CSI2000 | valuation_scope | OK |
| PASS | EU10Y | card_field:update_label | OK |
| PASS | EU10Y | card_field:source_label | OK |
| PASS | EU10Y | card_field:source_url | OK |
| PASS | EU10Y | card_field:data_as_of | OK |
| PASS | EU10Y | card_field:fetched_at | OK |
| PASS | EU10Y | card_field:data_note | OK |
| PASS | EU10Y | positive_price | OK |
| PASS | EU10Y | change_math | OK |
| PASS | EU10Y | change_pct_math | yield/spread pct may use source-specific point-change convention |
| PASS | EU10Y | source_trust | 官方 |
| PASS | EU10Y | freshness | 39s |
| PASS | EU10Y | valuation_scope | OK |
| PASS | VIX | card_field:update_label | OK |
| PASS | VIX | card_field:source_label | OK |
| PASS | VIX | card_field:source_url | OK |
| PASS | VIX | card_field:data_as_of | OK |
| PASS | VIX | card_field:fetched_at | OK |
| PASS | VIX | card_field:data_note | OK |
| PASS | VIX | positive_price | OK |
| PASS | VIX | change_math | OK |
| PASS | VIX | change_pct_math | OK |
| PASS | VIX | source_trust | 官方 |
| PASS | VIX | freshness | 39s |
| PASS | VIX | valuation_scope | OK |
| PASS | USDCNY | card_field:update_label | OK |
| PASS | USDCNY | card_field:source_label | OK |
| PASS | USDCNY | card_field:source_url | OK |
| PASS | USDCNY | card_field:data_as_of | OK |
| PASS | USDCNY | card_field:fetched_at | OK |
| PASS | USDCNY | card_field:data_note | OK |
| PASS | USDCNY | positive_price | OK |
| PASS | USDCNY | change_math | OK |
| PASS | USDCNY | change_pct_math | OK |
| PASS | USDCNY | source_trust | 第三方 |
| PASS | USDCNY | freshness | 39s |
| PASS | USDCNY | valuation_scope | OK |
| PASS | BTCUSD | card_field:update_label | OK |
| PASS | BTCUSD | card_field:source_label | OK |
| PASS | BTCUSD | card_field:source_url | OK |
| PASS | BTCUSD | card_field:data_as_of | OK |
| PASS | BTCUSD | card_field:fetched_at | OK |
| PASS | BTCUSD | card_field:data_note | OK |
| PASS | BTCUSD | positive_price | OK |
| PASS | BTCUSD | change_math | OK |
| PASS | BTCUSD | change_pct_math | OK |
| PASS | BTCUSD | source_trust | 备用源 |
| PASS | BTCUSD | freshness | 26s |
| PASS | BTCUSD | valuation_scope | OK |
| PASS | ETHUSD | card_field:update_label | OK |
| PASS | ETHUSD | card_field:source_label | OK |
| PASS | ETHUSD | card_field:source_url | OK |
| PASS | ETHUSD | card_field:data_as_of | OK |
| PASS | ETHUSD | card_field:fetched_at | OK |
| PASS | ETHUSD | card_field:data_note | OK |
| PASS | ETHUSD | positive_price | OK |
| PASS | ETHUSD | change_math | OK |
| PASS | ETHUSD | change_pct_math | OK |
| PASS | ETHUSD | source_trust | 备用源 |
| PASS | ETHUSD | freshness | 16s |
| PASS | ETHUSD | valuation_scope | OK |
| PASS | CAC40 | card_field:update_label | OK |
| PASS | CAC40 | card_field:source_label | OK |
| PASS | CAC40 | card_field:source_url | OK |
| PASS | CAC40 | card_field:data_as_of | OK |
| PASS | CAC40 | card_field:fetched_at | OK |
| PASS | CAC40 | card_field:data_note | OK |
| PASS | CAC40 | positive_price | OK |
| PASS | CAC40 | change_math | OK |
| PASS | CAC40 | change_pct_math | OK |
| PASS | CAC40 | source_trust | 第三方 |
| PASS | CAC40 | freshness | 11s |
| PASS | CAC40 | valuation_scope | OK |
| PASS | FTSE100 | card_field:update_label | OK |
| PASS | FTSE100 | card_field:source_label | OK |
| PASS | FTSE100 | card_field:source_url | OK |
| PASS | FTSE100 | card_field:data_as_of | OK |
| PASS | FTSE100 | card_field:fetched_at | OK |
| PASS | FTSE100 | card_field:data_note | OK |
| PASS | FTSE100 | positive_price | OK |
| PASS | FTSE100 | change_math | OK |
| PASS | FTSE100 | change_pct_math | OK |
| PASS | FTSE100 | source_trust | 官方延迟 |
| PASS | FTSE100 | freshness | 11s |
| PASS | FTSE100 | valuation_scope | OK |
| PASS | CSI300 | price_history | 21 rows |
| PASS | CSI300 | history_provenance:series | OK |
| PASS | CSI300 | history_provenance:source_signature | OK |
| PASS | CSI300 | history_merge_marks_snapshot | merged row marked |
| PASS | CSI300 | total_return_code | H00300 |
| PASS | CSI300 | total_return_history | 20 rows |
| PASS | CSI300 | total_return_not_snapshot_merged | OK |
| PASS | CSI500 | price_history | 21 rows |
| PASS | CSI500 | history_provenance:series | OK |
| PASS | CSI500 | history_provenance:source_signature | OK |
| PASS | CSI500 | history_merge_marks_snapshot | merged row marked |
| PASS | CSI500 | total_return_code | 000510CNY010 |
| PASS | CSI500 | total_return_history | 20 rows |
| PASS | CSI500 | total_return_not_snapshot_merged | OK |
| PASS | CSI500_INDEX | price_history | 21 rows |
| PASS | CSI500_INDEX | history_provenance:series | OK |
| PASS | CSI500_INDEX | history_provenance:source_signature | OK |
| PASS | CSI500_INDEX | history_merge_marks_snapshot | merged row marked |
| PASS | CSI500_INDEX | total_return_code | H00905 |
| PASS | CSI500_INDEX | total_return_history | 20 rows |
| PASS | CSI500_INDEX | total_return_not_snapshot_merged | OK |
| PASS | CSI_DIVIDEND | price_history | 21 rows |
| PASS | CSI_DIVIDEND | history_provenance:series | OK |
| PASS | CSI_DIVIDEND | history_provenance:source_signature | OK |
| PASS | CSI_DIVIDEND | history_merge_marks_snapshot | merged row marked |
| PASS | CSI_DIVIDEND | total_return_code | H20269 |
| PASS | CSI_DIVIDEND | total_return_history | 20 rows |
| PASS | CSI_DIVIDEND | total_return_not_snapshot_merged | OK |
| PASS | CSI_DIVIDEND_100 | price_history | 21 rows |
| PASS | CSI_DIVIDEND_100 | history_provenance:series | OK |
| PASS | CSI_DIVIDEND_100 | history_provenance:source_signature | OK |
| PASS | CSI_DIVIDEND_100 | history_merge_marks_snapshot | merged row marked |
| PASS | CSI_DIVIDEND_100 | total_return_code | H20955 |
| PASS | CSI_DIVIDEND_100 | total_return_history | 20 rows |
| PASS | CSI_DIVIDEND_100 | total_return_not_snapshot_merged | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | price_history | 21 rows |
| PASS | CSI300_DIVIDEND_LOW_VOL | history_provenance:series | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | history_provenance:source_signature | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | history_merge_marks_snapshot | merged row marked |
| PASS | CSI300_DIVIDEND_LOW_VOL | total_return_code | H20740 |
| PASS | CSI300_DIVIDEND_LOW_VOL | total_return_history | 20 rows |
| PASS | CSI300_DIVIDEND_LOW_VOL | total_return_not_snapshot_merged | OK |
| PASS | CSI_DIVIDEND_QUALITY | price_history | 21 rows |
| PASS | CSI_DIVIDEND_QUALITY | history_provenance:series | OK |
| PASS | CSI_DIVIDEND_QUALITY | history_provenance:source_signature | OK |
| PASS | CSI_DIVIDEND_QUALITY | history_merge_marks_snapshot | merged row marked |
| PASS | CSI_DIVIDEND_QUALITY | total_return_code | 921468 |
| PASS | CSI_DIVIDEND_QUALITY | total_return_history | 20 rows |
| PASS | CSI_DIVIDEND_QUALITY | total_return_not_snapshot_merged | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | price_history | 21 rows |
| PASS | CSI_ALL_DIVIDEND_QUALITY | history_provenance:series | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | history_provenance:source_signature | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | history_merge_marks_snapshot | merged row marked |
| PASS | CSI_ALL_DIVIDEND_QUALITY | total_return_code | 932315CNY010 |
| PASS | CSI_ALL_DIVIDEND_QUALITY | total_return_history | 20 rows |
| PASS | CSI_ALL_DIVIDEND_QUALITY | total_return_not_snapshot_merged | OK |
| PASS | CSI_CASH_FLOW | price_history | 21 rows |
| PASS | CSI_CASH_FLOW | history_provenance:series | OK |
| PASS | CSI_CASH_FLOW | history_provenance:source_signature | OK |
| PASS | CSI_CASH_FLOW | history_merge_marks_snapshot | merged row marked |
| PASS | CSI_CASH_FLOW | total_return_code | 932365CNY010 |
| PASS | CSI_CASH_FLOW | total_return_history | 20 rows |
| PASS | CSI_CASH_FLOW | total_return_not_snapshot_merged | OK |
| PASS | CNI_FREE_CASH_FLOW | price_history | 21 rows |
| PASS | CNI_FREE_CASH_FLOW | history_provenance:series | OK |
| PASS | CNI_FREE_CASH_FLOW | history_provenance:source_signature | OK |
| PASS | CNI_FREE_CASH_FLOW | history_merge_marks_snapshot | merged row marked |
| PASS | CNI_FREE_CASH_FLOW | total_return_code | 480092 |
| PASS | CNI_FREE_CASH_FLOW | total_return_history | 20 rows |
| PASS | CNI_FREE_CASH_FLOW | total_return_not_snapshot_merged | OK |
| PASS | CSI_BAIJIU | price_history | 21 rows |
| PASS | CSI_BAIJIU | history_provenance:series | OK |
| PASS | CSI_BAIJIU | history_provenance:source_signature | OK |
| PASS | CSI_BAIJIU | history_merge_marks_snapshot | merged row marked |
| PASS | CSI_BAIJIU | total_return_code | H20539 |
| PASS | CSI_BAIJIU | total_return_history | 20 rows |
| PASS | CSI_BAIJIU | total_return_not_snapshot_merged | OK |
| PASS | CHINEXT | price_history | 21 rows |
| PASS | CHINEXT | history_provenance:series | OK |
| PASS | CHINEXT | history_provenance:source_signature | OK |
| PASS | CHINEXT | history_merge_marks_snapshot | merged row marked |
| PASS | CHINEXT | no_proxy_as_total_return | OK |
| PASS | STAR50 | price_history | 21 rows |
| PASS | STAR50 | history_provenance:series | OK |
| PASS | STAR50 | history_provenance:source_signature | OK |
| PASS | STAR50 | history_merge_marks_snapshot | merged row marked |
| PASS | STAR50 | total_return_code | 000688CNY01 |
| PASS | STAR50 | total_return_history | 20 rows |
| PASS | STAR50 | total_return_not_snapshot_merged | OK |
| PASS | STAR100 | price_history | 21 rows |
| PASS | STAR100 | history_provenance:series | OK |
| PASS | STAR100 | history_provenance:source_signature | OK |
| PASS | STAR100 | history_merge_marks_snapshot | merged row marked |
| PASS | STAR100 | total_return_code | 000698CNY010 |
| PASS | STAR100 | total_return_history | 20 rows |
| PASS | STAR100 | total_return_not_snapshot_merged | OK |
| PASS | CN10Y | price_history | 20 rows |
| PASS | CN10Y | history_provenance:series | OK |
| PASS | CN10Y | history_provenance:source_signature | OK |
| PASS | CN10Y | history_merge_marks_snapshot | merged row marked |
| PASS | CN10Y | no_proxy_as_total_return | OK |
| PASS | US10Y | price_history | 19 rows |
| PASS | US10Y | history_provenance:series | OK |
| PASS | US10Y | history_provenance:source_signature | OK |
| PASS | US10Y | history_merge_marks_snapshot | merged row marked |
| PASS | US10Y | no_proxy_as_total_return | OK |
| PASS | HSTECH | price_history | 20 rows |
| PASS | HSTECH | history_provenance:series | OK |
| PASS | HSTECH | history_provenance:source_signature | OK |
| PASS | HSTECH | history_merge_marks_snapshot | merged row marked |
| PASS | HSTECH | no_proxy_as_total_return | OK |
| PASS | HSI | price_history | 20 rows |
| PASS | HSI | history_provenance:series | OK |
| PASS | HSI | history_provenance:source_signature | OK |
| PASS | HSI | history_merge_marks_snapshot | merged row marked |
| PASS | HSI | no_proxy_as_total_return | OK |
| PASS | DAX | price_history | 21 rows |
| PASS | DAX | history_provenance:series | OK |
| PASS | DAX | history_provenance:source_signature | OK |
| PASS | DAX | dax_disallows:6mo | OK |
| PASS | DAX | dax_disallows:1y | OK |
| PASS | DAX | dax_disallows:all | OK |
| PASS | DAX | total_return_code | DAX |
| PASS | DAX | total_return_history | 21 rows |
| PASS | DAX | total_return_not_snapshot_merged | OK |
| PASS | NDX | price_history | 16 rows |
| PASS | NDX | history_provenance:series | OK |
| PASS | NDX | history_provenance:source_signature | OK |
| PASS | NDX | history_merge_marks_snapshot | merged row marked |
| PASS | NDX | no_proxy_as_total_return | OK |
| PASS | SPX | price_history | 16 rows |
| PASS | SPX | history_provenance:series | OK |
| PASS | SPX | history_provenance:source_signature | OK |
| PASS | SPX | history_merge_marks_snapshot | merged row marked |
| PASS | SPX | no_proxy_as_total_return | OK |
| PASS | XOP | price_history | 16 rows |
| PASS | XOP | history_provenance:series | OK |
| PASS | XOP | history_provenance:source_signature | OK |
| PASS | XOP | history_merge_marks_snapshot | merged row marked |
| PASS | XOP | no_proxy_as_total_return | OK |
| PASS | WANJIA_GOLD | price_history | 21 rows |
| PASS | WANJIA_GOLD | history_provenance:series | OK |
| PASS | WANJIA_GOLD | history_provenance:source_signature | OK |
| PASS | WANJIA_GOLD | history_merge_marks_snapshot | merged row marked |
| PASS | WANJIA_GOLD | no_proxy_as_total_return | OK |
| PASS | GOLD | price_history | 18 rows |
| PASS | GOLD | history_provenance:series | OK |
| PASS | GOLD | history_provenance:source_signature | OK |
| PASS | GOLD | history_merge_marks_snapshot | merged row marked |
| PASS | GOLD | no_proxy_as_total_return | OK |
| PASS | OIL_WTI | price_history | 18 rows |
| PASS | OIL_WTI | history_provenance:series | OK |
| PASS | OIL_WTI | history_provenance:source_signature | OK |
| PASS | OIL_WTI | history_merge_marks_snapshot | merged row marked |
| PASS | OIL_WTI | no_proxy_as_total_return | OK |
| PASS | CSI_ALL_SHARE | price_history | 21 rows |
| PASS | CSI_ALL_SHARE | history_provenance:series | OK |
| PASS | CSI_ALL_SHARE | history_provenance:source_signature | OK |
| PASS | CSI_ALL_SHARE | history_merge_marks_snapshot | merged row marked |
| PASS | CSI_ALL_SHARE | total_return_code | H00985 |
| PASS | CSI_ALL_SHARE | total_return_history | 20 rows |
| PASS | CSI_ALL_SHARE | total_return_not_snapshot_merged | OK |
| PASS | CSI1000 | price_history | 21 rows |
| PASS | CSI1000 | history_provenance:series | OK |
| PASS | CSI1000 | history_provenance:source_signature | OK |
| PASS | CSI1000 | history_merge_marks_snapshot | merged row marked |
| PASS | CSI1000 | total_return_code | H00852 |
| PASS | CSI1000 | total_return_history | 20 rows |
| PASS | CSI1000 | total_return_not_snapshot_merged | OK |
| PASS | CSI2000 | price_history | 21 rows |
| PASS | CSI2000 | history_provenance:series | OK |
| PASS | CSI2000 | history_provenance:source_signature | OK |
| PASS | CSI2000 | history_merge_marks_snapshot | merged row marked |
| PASS | CSI2000 | total_return_code | 932000CNY010 |
| PASS | CSI2000 | total_return_history | 20 rows |
| PASS | CSI2000 | total_return_not_snapshot_merged | OK |
| PASS | EU10Y | price_history | 20 rows |
| PASS | EU10Y | history_provenance:series | OK |
| PASS | EU10Y | history_provenance:source_signature | OK |
| PASS | EU10Y | history_merge_marks_snapshot | merged row marked |
| PASS | EU10Y | no_proxy_as_total_return | OK |
| PASS | VIX | price_history | 21 rows |
| PASS | VIX | history_provenance:series | OK |
| PASS | VIX | history_provenance:source_signature | OK |
| PASS | VIX | history_merge_marks_snapshot | merged row marked |
| PASS | VIX | no_proxy_as_total_return | OK |
| PASS | USDCNY | price_history | 22 rows |
| PASS | USDCNY | history_provenance:series | OK |
| PASS | USDCNY | history_provenance:source_signature | OK |
| PASS | USDCNY | history_merge_marks_snapshot | merged row marked |
| PASS | USDCNY | no_proxy_as_total_return | OK |
| PASS | BTCUSD | price_history | 24 rows |
| PASS | BTCUSD | history_provenance:series | OK |
| PASS | BTCUSD | history_provenance:source_signature | OK |
| PASS | BTCUSD | history_merge_marks_snapshot | merged row marked |
| PASS | BTCUSD | no_proxy_as_total_return | OK |
| PASS | ETHUSD | price_history | 24 rows |
| PASS | ETHUSD | history_provenance:series | OK |
| PASS | ETHUSD | history_provenance:source_signature | OK |
| PASS | ETHUSD | history_merge_marks_snapshot | merged row marked |
| PASS | ETHUSD | no_proxy_as_total_return | OK |
| PASS | CAC40 | price_history | 17 rows |
| PASS | CAC40 | history_provenance:series | OK |
| PASS | CAC40 | history_provenance:source_signature | OK |
| PASS | CAC40 | history_merge_marks_snapshot | merged row marked |
| PASS | CAC40 | no_proxy_as_total_return | OK |
| PASS | FTSE100 | price_history | 21 rows |
| PASS | FTSE100 | history_provenance:series | OK |
| PASS | FTSE100 | history_provenance:source_signature | OK |
| PASS | FTSE100 | history_merge_marks_snapshot | merged row marked |
| PASS | FTSE100 | total_return_code | .TRIUKX |
| PASS | FTSE100 | total_return_history | 22 rows |
| PASS | FTSE100 | total_return_not_snapshot_merged | OK |
| PASS | CSI_DIVIDEND | csi_dividend_no_proxy | OK |
| PASS | CSI_DIVIDEND | dividend_return_source | computed_dividend_yield |
| PASS | CSI_DIVIDEND | dividend_return_history | 2426 rows, latest=5.19% |
| PASS | CSI_DIVIDEND | official_dividend_yield_source | csindex_indicator/股息率1 |
| PASS | CSI_DIVIDEND | official_dividend_yield_history | 21 rows, latest=5.20% |
| PASS | CSI_DIVIDEND_100 | csi_dividend_no_proxy | OK |
| PASS | CSI_DIVIDEND_100 | dividend_return_source | computed_dividend_yield |
| PASS | CSI_DIVIDEND_100 | dividend_return_history | 2426 rows, latest=4.70% |
| PASS | CSI_DIVIDEND_100 | official_dividend_yield_source | csindex_indicator/股息率1 |
| PASS | CSI_DIVIDEND_100 | official_dividend_yield_history | 21 rows, latest=5.12% |
| PASS | CSI300_DIVIDEND_LOW_VOL | csi_dividend_no_proxy | OK |
| PASS | CSI300_DIVIDEND_LOW_VOL | dividend_return_source | computed_dividend_yield |
| PASS | CSI300_DIVIDEND_LOW_VOL | dividend_return_history | 2425 rows, latest=4.67% |
| PASS | CSI300_DIVIDEND_LOW_VOL | official_dividend_yield_source | csindex_indicator/股息率1 |
| PASS | CSI300_DIVIDEND_LOW_VOL | official_dividend_yield_history | 21 rows, latest=4.84% |
| PASS | CSI_DIVIDEND_QUALITY | csi_dividend_no_proxy | OK |
| PASS | CSI_DIVIDEND_QUALITY | dividend_return_source | computed_dividend_yield |
| PASS | CSI_DIVIDEND_QUALITY | dividend_return_history | 2425 rows, latest=2.86% |
| PASS | CSI_DIVIDEND_QUALITY | official_dividend_yield_source | csindex_indicator/股息率1 |
| PASS | CSI_DIVIDEND_QUALITY | official_dividend_yield_history | 21 rows, latest=2.93% |
| PASS | CSI_ALL_DIVIDEND_QUALITY | csi_dividend_no_proxy | OK |
| PASS | CSI_ALL_DIVIDEND_QUALITY | dividend_return_source | computed_dividend_yield |
| PASS | CSI_ALL_DIVIDEND_QUALITY | dividend_return_history | 2425 rows, latest=4.13% |
| PASS | CSI_ALL_DIVIDEND_QUALITY | official_dividend_yield_source | csindex_indicator/股息率1 |
| PASS | CSI_ALL_DIVIDEND_QUALITY | official_dividend_yield_history | 21 rows, latest=3.93% |
| PASS | CSI_CASH_FLOW | csi_dividend_no_proxy | OK |
| PASS | CSI_CASH_FLOW | dividend_return_source | computed_dividend_yield |
| PASS | CSI_CASH_FLOW | dividend_return_history | 2425 rows, latest=4.64% |
| PASS | CSI_CASH_FLOW | official_dividend_yield_source | csindex_indicator/股息率1 |
| PASS | CSI_CASH_FLOW | official_dividend_yield_history | 21 rows, latest=3.85% |
| PASS | CNI_FREE_CASH_FLOW | csi_dividend_no_proxy | OK |
| PASS | CNI_FREE_CASH_FLOW | dividend_return_source | computed_dividend_yield |
| PASS | CNI_FREE_CASH_FLOW | dividend_return_history | 2425 rows, latest=3.28% |
| PASS | CNI_FREE_CASH_FLOW | official_dividend_yield_source | not configured without CSI official D/P source |
| PASS | CN_US_10Y_SPREAD | spread_negative_history | 969 negative rows |
| PASS | CN_US_10Y_SPREAD | spread_history_freshness | 2026-07-02 |
| PASS | US10Y_2Y_SPREAD | spread_negative_history | 544 negative rows |
| PASS | US10Y_2Y_SPREAD | spread_history_freshness | 2026-07-02 |
| PASS | CN10Y_1Y_SPREAD | spread_negative_history | 10 negative rows |
| PASS | CN10Y_1Y_SPREAD | spread_history_freshness | 2026-07-02 |