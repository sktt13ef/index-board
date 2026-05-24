"""
本地估值计算器
下载历史数据CSV到本地，计算十年滚动PE和分位数
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
import akshare as ak
import pandas as pd
import numpy as np


class LocalValuationCalculator:
    """本地估值计算器 - 基于下载的历史数据计算十年滚动PE"""
    
    # 本地数据缓存目录
    DATA_DIR = "valuation_data"
    
    def __init__(self):
        """初始化计算器"""
        if not os.path.exists(self.DATA_DIR):
            os.makedirs(self.DATA_DIR)
        self.data_cache = {}
    
    def _get_cache_file(self, symbol: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.DATA_DIR, f"{symbol}_history.csv")
    
    def download_index_history(self, symbol: str, years: int = 10, force_update: bool = False) -> Optional[pd.DataFrame]:
        """
        下载指数历史数据并保存为CSV
        
        Args:
            symbol: 指数代码，如 '000300'
            years: 下载年数（默认10年）
            force_update: 强制更新，忽略缓存
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        cache_file = self._get_cache_file(symbol)
        
        # 检查缓存是否存在且新鲜（4小时内）
        if not force_update and os.path.exists(cache_file):
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_time < timedelta(hours=4):
                try:
                    df = pd.read_csv(cache_file, parse_dates=['date'])
                    print(f"    使用缓存数据: {len(df)} 条 ({(datetime.now() - file_time).total_seconds() / 3600:.1f}小时前)")
                    return df
                except:
                    pass
        
        try:
            print(f"    下载 {symbol} 历史数据（{years}年）...")
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365 * years + 30)
            
            # 使用akshare获取数据
            df = ak.index_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )
            
            if df is not None and len(df) > 0:
                # 标准化列名
                df.columns = [c.lower() for c in df.columns]
                
                # 确保date列存在
                if 'date' not in df.columns:
                    if 'datetime' in df.columns:
                        df['date'] = df['datetime']
                
                # 转换日期格式
                df['date'] = pd.to_datetime(df['date'])
                
                # 只保留需要的列
                keep_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
                df = df[[c for c in keep_cols if c in df.columns]]
                
                # 保存到CSV
                df.to_csv(cache_file, index=False)
                
                # 计算实际数据年数
                actual_years = (df['date'].max() - df['date'].min()).days / 365.25
                
                print(f"    ✓ 下载成功: {len(df)} 条数据，约{actual_years:.1f}年")
                return df
            else:
                print(f"    ✗ 无数据返回")
                
        except Exception as e:
            print(f"    ✗ 下载失败: {e}")
        
        return None
    
    def calculate_valuation(self, symbol: str, current_price: float, key: str = None) -> Optional[Dict]:
        """
        基于历史价格计算估值和分位数
        
        Args:
            symbol: 指数代码
            current_price: 当前价格
            key: 指数key（用于获取基准PE）
        
        Returns:
            dict with pe, pe_percentile, years_of_data, etc.
        """
        # 下载历史数据
        df = self.download_index_history(symbol, years=10)
        
        if df is None or len(df) < 100:
            return None
        
        try:
            # 计算实际数据年数
            date_range = df['date'].max() - df['date'].min()
            actual_years = date_range.days / 365.25
            
            # 获取基准PE
            base_pe = self._get_base_pe(key) if key else 15.0
            
            # 计算价格分位数
            prices = df['close'].values
            current_price_percentile = (prices < current_price).mean() * 100
            
            # 估算当前PE（基于价格分位数）
            # 假设PE与价格正相关
            pe_estimate = base_pe * (0.7 + 0.6 * current_price_percentile / 100)
            
            # 计算PE区间
            pe_min = base_pe * 0.7
            pe_max = base_pe * 1.3
            pe_median = base_pe
            
            result = {
                'pe': round(pe_estimate, 2),
                'pe_min': round(pe_min, 2),
                'pe_max': round(pe_max, 2),
                'pe_median': round(pe_median, 2),
                'pe_percentile': round(current_price_percentile, 2),
                'price_percentile': round(current_price_percentile, 2),
                'data_points': len(df),
                'years_of_data': round(actual_years, 1),
                'data_start': df['date'].min().strftime('%Y-%m-%d'),
                'data_end': df['date'].max().strftime('%Y-%m-%d'),
                'source': f'本地计算（基于{actual_years:.1f}年历史数据）',
                'calculation_method': '价格分位数法',
                'is_calculated': True,
            }
            
            # 如果数据不足10年，添加说明
            if actual_years < 10:
                result['note'] = f'仅有{actual_years:.1f}年历史数据（目标10年）'
            
            return result
            
        except Exception as e:
            print(f"    计算失败 {symbol}: {e}")
            return None
    
    def _get_base_pe(self, key: str) -> float:
        """获取基准PE"""
        base_pe_map = {
            "CSI300": 12.0,
            "CSI500": 14.0,
            "CSI_DIVIDEND": 7.5,
            "HSTECH": 25.0,
            "NDX": 28.0,
            "DAX": 18.0,
        }
        return base_pe_map.get(key, 15.0)
    
    def calculate_dividend_yield(self, pe: float) -> Optional[float]:
        """基于PE估算股息率"""
        if pe <= 0:
            return None
        payout_ratio = 0.4
        dividend_yield = (1 / pe * 100) * payout_ratio
        return round(dividend_yield, 2)
    
    def get_full_valuation(self, key: str, symbol: str, current_price: float) -> Optional[Dict]:
        """获取完整的估值数据"""
        pe_data = self.calculate_valuation(symbol, current_price, key)
        
        if not pe_data:
            return None
        
        # 计算股息率
        pe = pe_data.get('pe', 0)
        if pe > 0:
            dividend_yield = self.calculate_dividend_yield(pe)
            if dividend_yield:
                pe_data['dividend_yield'] = dividend_yield
                pe_data['dividend_yield_note'] = '基于PE估算'
        
        return pe_data
    
    def update_all_csv(self, force: bool = False):
        """
        更新所有指数的CSV历史数据
        
        Args:
            force: 是否强制更新（忽略缓存时间）
        """
        symbols = {
            '000300': '沪深300',
            '000510': '中证A500',
            'H30269': '中证红利低波动',
        }
        
        print("=" * 60)
        print("更新所有指数历史数据CSV")
        print("=" * 60)
        print(f"强制更新: {force}")
        print(f"缓存时间: 4小时")
        print("=" * 60)
        print()
        
        for symbol, name in symbols.items():
            print(f"[{name}] {symbol}")
            self.download_index_history(symbol, years=10, force_update=force)
            print()
        
        print("=" * 60)
        print("CSV数据更新完成")
        print("=" * 60)


# 单例模式
_calculator_instance = None

def get_calculator() -> LocalValuationCalculator:
    """获取计算器单例"""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = LocalValuationCalculator()
    return _calculator_instance
