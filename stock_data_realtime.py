"""
实时估值数据获取模块
通过网络API实时获取PE、股息率等估值数据
"""
import requests
import json
import re
from datetime import datetime


class RealtimeValuationProvider:
    """实时估值数据提供者"""
    
    # PE合理范围配置
    PE_RANGES = {
        '000300': (8, 25),    # 沪深300: 8-25
        '000510': (10, 30),   # 中证A500: 10-30
        'H30269': (5, 15),    # 红利低波: 5-15
    }
    
    @staticmethod
    def is_pe_valid(index_code, pe):
        """验证PE是否在合理范围内"""
        if pe is None or pe <= 0:
            return False
        
        # 获取该指数的PE合理范围
        pe_range = RealtimeValuationProvider.PE_RANGES.get(index_code)
        if pe_range:
            min_pe, max_pe = pe_range
            if not (min_pe <= pe <= max_pe):
                print(f"    PE {pe} 超出合理范围 [{min_pe}, {max_pe}]")
                return False
        
        return True
    
    @staticmethod
    def fetch_akshare_valuation(index_code):
        """
        使用akshare获取指数估值数据（最可靠）
        """
        try:
            import akshare as ak
            
            # 使用中证指数历史数据获取最新PE
            df = ak.stock_zh_index_hist_csindex(symbol=index_code)
            if df is not None and len(df) > 0:
                latest = df.iloc[-1]
                pe = latest.get('滚动市盈率')
                dividend_yield = latest.get('股息率')
                
                if pe and RealtimeValuationProvider.is_pe_valid(index_code, float(pe)):
                    result = {
                        'pe': round(float(pe), 2),
                        'source': 'akshare/中证指数',
                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    # 添加股息率
                    if dividend_yield and float(dividend_yield) > 0:
                        result['dividend_yield'] = round(float(dividend_yield), 2)
                    return result
        except Exception as e:
            print(f"    akshare获取失败 {index_code}: {e}")
        return None
    
    @staticmethod
    def fetch_eastmoney_valuation(index_code):
        """
        从东方财富获取指数实时估值数据
        """
        try:
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                'sortColumns': 'TRADE_DATE',
                'sortTypes': '-1',
                'pageSize': '1',
                'pageNumber': '1',
                'reportName': 'RPT_INDEX_VALUATION',
                'columns': 'ALL',
                'filter': f'(INDEX_CODE="{index_code}")'
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('result') and data['result'].get('data'):
                d = data['result']['data'][0]
                result = {}
                
                # PE-TTM
                pe = d.get('PE_TTM')
                if pe and RealtimeValuationProvider.is_pe_valid(index_code, float(pe)):
                    result['pe'] = round(float(pe), 2)
                
                # PB
                pb = d.get('PB_MRQ')
                if pb and float(pb) > 0:
                    result['pb'] = round(float(pb), 2)
                
                # 股息率
                dy = d.get('DIVIDEND_YIELD')
                if dy and float(dy) > 0:
                    result['dividend_yield'] = round(float(dy), 2)
                
                # 10年分位数
                pe_pct = d.get('PE_TTM_PERCENTILE_10Y')
                if pe_pct and float(pe_pct) > 0:
                    result['pe_percentile'] = round(float(pe_pct) * 100, 2)
                
                if result and result.get('pe'):
                    result['source'] = '东方财富实时'
                    result['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    return result
        except Exception as e:
            print(f"    东方财富获取失败 {index_code}: {e}")
        return None
    
    @staticmethod
    def fetch_csindex_valuation(index_code):
        """
        从中证指数官网获取估值数据
        """
        try:
            url = f"https://www.csindex.com.cn/csindex-home/index/api/index_details/info/{index_code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.csindex.com.cn/',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200 and data.get('data'):
                    d = data['data']
                    result = {}
                    
                    # 提取PE-TTM
                    if d.get('pe'):
                        pe = float(d['pe'])
                        if RealtimeValuationProvider.is_pe_valid(index_code, pe):
                            result['pe'] = round(pe, 2)
                    
                    # 提取股息率
                    if d.get('dividendYield'):
                        result['dividend_yield'] = round(float(d['dividendYield']), 2)
                    
                    if result and result.get('pe'):
                        result['source'] = '中证指数官网'
                        result['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        return result
        except Exception as e:
            print(f"    中证指数官网获取失败 {index_code}: {e}")
        return None
    
    @staticmethod
    def get_realtime_valuation(key, config):
        """
        获取指数的实时估值数据
        按优先级尝试多个数据源
        """
        index_code = config.get('symbol', '')
        name = config.get('name', key)
        
        # 只处理A股指数
        if index_code not in ['000300', '000510', 'H30269']:
            return None
        
        # 1. 尝试akshare（最可靠）
        data = RealtimeValuationProvider.fetch_akshare_valuation(index_code)
        if data and data.get('pe', 0) > 0:
            return data
        
        # 2. 尝试中证指数官网
        data = RealtimeValuationProvider.fetch_csindex_valuation(index_code)
        if data and data.get('pe', 0) > 0:
            return data
        
        # 3. 尝试东方财富
        data = RealtimeValuationProvider.fetch_eastmoney_valuation(index_code)
        if data and data.get('pe', 0) > 0:
            return data
        
        return None


# 兼容性导入
if __name__ == "__main__":
    # 测试
    provider = RealtimeValuationProvider()
    
    test_indices = {
        'CSI300': {'name': '沪深300', 'symbol': '000300'},
        'CSI500': {'name': '中证A500', 'symbol': '000510'},
    }
    
    for key, config in test_indices.items():
        data = provider.get_realtime_valuation(key, config)
        print(f"{key}: {data}")
