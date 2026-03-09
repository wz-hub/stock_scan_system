"""
数据获取模块
支持从 CSV 文件或 API 获取数据
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import yfinance as yf


class DataLoader:
    """数据加载器"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_csv(self, filepath: str, **kwargs) -> pd.DataFrame:
        """从 CSV 加载数据"""
        # 尝试自动检测日期列
        df = pd.read_csv(filepath, index_col=0, parse_dates=True, **kwargs)
        return self._standardize_columns(df)
    
    def download_yahoo(self, symbol: str, start_date: str, end_date: str, 
                       save: bool = True) -> pd.DataFrame:
        """从 Yahoo Finance 下载数据"""
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
            raise ValueError(f"No data found for {symbol}")
        
        df = self._standardize_columns(df)
        
        if save:
            filepath = self.data_dir / f"{symbol.replace('/', '_')}.csv"
            df.to_csv(filepath)
            print(f"Data saved to {filepath}")
        
        return df
    
    def generate_synthetic(self, days: int = 500, start_price: float = 100.0,
                          volatility: float = 0.02, trend: float = 0.0001) -> pd.DataFrame:
        """生成模拟数据用于测试"""
        dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq='D')
        
        # 生成价格序列（几何布朗运动）
        returns = np.random.normal(trend, volatility, days)
        close = start_price * np.cumprod(1 + returns)
        
        # 生成 OHLC
        df = pd.DataFrame(index=dates)
        df['close'] = close
        df['open'] = close * (1 + np.random.uniform(-0.01, 0.01, days))
        df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.01, days)))
        df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.01, days)))
        df['volume'] = np.random.randint(100000, 1000000, days)
        
        return self._standardize_columns(df)
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        # 重命名列
        column_mapping = {
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adj_close'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 确保有小写列名
        required_columns = ['open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in df.columns:
                # 尝试找大写版本
                upper_col = col.upper()
                if upper_col in df.columns:
                    df[col] = df[upper_col]
                else:
                    raise ValueError(f"Missing required column: {col}")
        
        # 确保有成交量（如果没有则填充）
        if 'volume' not in df.columns:
            df['volume'] = 100000
        
        # 按日期排序
        df = df.sort_index()
        
        # 删除空值
        df = df.dropna()
        
        return df


def load_data(symbol: str = None, start_date: str = '2020-01-01', 
              end_date: str = '2024-12-31', use_synthetic: bool = False) -> pd.DataFrame:
    """便捷函数加载数据"""
    loader = DataLoader()
    
    if use_synthetic:
        print("Using synthetic data...")
        return loader.generate_synthetic(days=500)
    
    if symbol:
        print(f"Downloading data for {symbol}...")
        return loader.download_yahoo(symbol, start_date, end_date)
    
    # 默认加载本地 CSV
    csv_files = list(loader.data_dir.glob('*.csv'))
    if csv_files:
        print(f"Loading {csv_files[0]}...")
        return loader.load_csv(str(csv_files[0]))
    
    # 没有数据则生成模拟数据
    print("No data found, generating synthetic data...")
    return loader.generate_synthetic(days=500)
