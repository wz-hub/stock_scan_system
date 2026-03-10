"""
数据加载器 - 用于回测和历史数据分析
"""
import pandas as pd
from pathlib import Path
from typing import Optional


class DataLoader:
    """数据加载器 - 支持 CSV 加载和 Yahoo Finance 下载"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """初始化数据加载器"""
        self.cache_dir = Path(cache_dir) if cache_dir else Path('data')
        self.cache_dir.mkdir(exist_ok=True)
    
    def load_csv(self, file_path: str, **kwargs) -> pd.DataFrame:
        """
        从 CSV 文件加载数据
        
        Args:
            file_path: CSV 文件路径
            **kwargs: 传递给 pd.read_csv 的参数
            
        Returns:
            DataFrame，索引为日期
        """
        df = pd.read_csv(file_path, **kwargs)
        
        # 尝试解析日期列
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        
        # 确保索引是 DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        return df
    
    def download_yahoo(self, symbol: str, start_date: str, end_date: str, **kwargs) -> pd.DataFrame:
        """
        从 Yahoo Finance 下载数据
        
        Args:
            symbol: 交易标的符号
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            **kwargs: 额外参数
            
        Returns:
            DataFrame，包含 OHLCV 数据
        """
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, **kwargs)
            
            if df.empty:
                raise ValueError(f"No data found for symbol: {symbol}")
            
            return df
            
        except ImportError:
            raise ImportError("yfinance not installed. Install with: pip install yfinance")
        except Exception as e:
            raise RuntimeError(f"Failed to download data for {symbol}: {e}")
    
    def save_csv(self, df: pd.DataFrame, file_path: str, **kwargs):
        """
        保存 DataFrame 到 CSV 文件
        
        Args:
            df: 要保存的 DataFrame
            file_path: 输出文件路径
            **kwargs: 传递给 df.to_csv 的参数
        """
        Path(file_path).parent.mkdir(exist_ok=True, parents=True)
        df.to_csv(file_path, **kwargs)
