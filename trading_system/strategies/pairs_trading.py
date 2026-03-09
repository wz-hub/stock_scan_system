"""
策略 7: 配对交易策略
来源：《配对交易》《量化交易》
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple


class PairsTradingStrategy:
    """
    配对交易/统计套利策略
    
    核心逻辑：
    - 两只高度相关的资产
    - 价差偏离均值时入场
    - 价差回归均值时平仓
    """
    
    def __init__(self, lookback_period: int = 60, entry_zscore: float = 2.0, 
                 exit_zscore: float = 0.5):
        self.lookback_period = lookback_period
        self.entry_zscore = entry_zscore
        self.exit_zscore = exit_zscore
        
        self.name = "配对交易"
    
    def calculate_spread(self, price1: pd.Series, price2: pd.Series, 
                         hedge_ratio: float = None) -> pd.Series:
        """计算价差"""
        if hedge_ratio is None:
            # 简单价格比率
            spread = price1 / price2
        else:
            # 对冲比率调整
            spread = price1 - hedge_ratio * price2
        return spread
    
    def calculate_hedge_ratio(self, price1: pd.Series, price2: pd.Series) -> float:
        """计算最优对冲比率（OLS）"""
        # 使用滚动回归计算对冲比率
        returns1 = price1.pct_change().dropna()
        returns2 = price2.pct_change().dropna()
        
        # 简单 OLS
        cov = returns1.cov(returns2)
        var = returns2.var()
        
        if var > 0:
            hedge_ratio = cov / var
        else:
            hedge_ratio = 1.0
        
        return hedge_ratio
    
    def calculate_zscore(self, spread: pd.Series) -> pd.Series:
        """计算 Z-Score"""
        rolling_mean = spread.rolling(self.lookback_period).mean()
        rolling_std = spread.rolling(self.lookback_period).std()
        zscore = (spread - rolling_mean) / rolling_std
        return zscore
    
    def generate_signals(self, df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        参数:
            df1: 资产 1 的数据
            df2: 资产 2 的数据
        
        返回:
            包含信号的数据框
        """
        # 对齐日期
        df = pd.merge(df1[['close']].rename(columns={'close': 'price1'}), 
                      df2[['close']].rename(columns={'close': 'price2'}), 
                      left_index=True, right_index=True, how='inner')
        
        if len(df) < self.lookback_period + 10:
            df['signal'] = 0
            df['position'] = 0
            df['zscore'] = np.nan
            df['spread'] = np.nan
            return df
        
        # 计算对冲比率
        hedge_ratio = self.calculate_hedge_ratio(df['price1'], df['price2'])
        
        # 计算价差
        df['spread'] = df['price1'] - hedge_ratio * df['price2']
        
        # 计算 Z-Score
        df['zscore'] = self.calculate_zscore(df['spread'])
        
        df['signal'] = 0
        df['position'] = 0
        df['trade_type'] = ''
        
        position = 0  # 0: 空仓，1: 多价差，-1: 空价差
        
        for i in range(self.lookback_period, len(df)):
            row = df.iloc[i]
            
            # 开仓：Z-Score 超过阈值
            if position == 0:
                if row['zscore'] > self.entry_zscore:
                    # 价差过高，做空价差（卖 1 买 2）
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    df.loc[df.index[i], 'trade_type'] = 'short_spread'
                    position = -1
                
                elif row['zscore'] < -self.entry_zscore:
                    # 价差过低，做多价差（买 1 卖 2）
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    df.loc[df.index[i], 'trade_type'] = 'long_spread'
                    position = 1
            
            # 平仓：Z-Score 回归均值
            elif position == 1:
                if row['zscore'] > -self.exit_zscore:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = 0
                    position = 0
            
            elif position == -1:
                if row['zscore'] < self.exit_zscore:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 0
                    position = 0
            
            # 止损：Z-Score 继续扩大
            if position == 1 and row['zscore'] < -3.0:
                df.loc[df.index[i], 'signal'] = -1
                df.loc[df.index[i], 'position'] = 0
                position = 0
            
            if position == -1 and row['zscore'] > 3.0:
                df.loc[df.index[i], 'signal'] = 1
                df.loc[df.index[i], 'position'] = 0
                position = 0
        
        return df
