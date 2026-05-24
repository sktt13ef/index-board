# index-board

多市场指数看板：实时/日更行情、十年 PE 分位、历史走势、卡片拖拽排序。

## 运行

```bash
pip install -r requirements.txt
python app.py
```

浏览器打开 `http://127.0.0.1:5000`

## 功能

- 沪深300、A500、红利低波、白酒、创业板、科创50/100
- 恒生、恒科、纳指、DAX、黄金、原油、XOP、万家周期视野C
- 中/美十年期国债收益率
- 卡片估值指标（官方 PE 或 10 年价格/收益率分位）
- 按估值便宜→贵排序
- 底部抽屉历史图

## 数据说明

详见 [DATA_SOURCES.md](DATA_SOURCES.md)
