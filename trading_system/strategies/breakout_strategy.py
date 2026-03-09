"""
策略 10: 突破策略
来源：《海龟交易法则》《专业投机原理》
"""
import pandas as pd
import numpy as np
from typing import Dict


class BreakoutStrategy:
    """
    价格突破策略
    
    规则：
    - 突破 N 日高点做多
    - 跌破 N 日低点做空
    - 成交量确认突破有效性
    """
    
    def __init__(self, breakout_period: int = 20, volume_multiplier: float = 1.5,
                 use_volume_filter: bool = True):
        self.breakout_period = breakout_period
        self.volume_multiplier = volume_multiplier
        self.use_volume_filter = use_volume_filter
        
        self.name = "突破策略"
    
    def calculate_volume_sma(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """计算成交量均线"""
        return df['volume'].rolling(period).mean()
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = df.copy()
        
        # 计算突破区间
        df['high_n'] = df['high'].rolling(self.breakout_period).max()
        df['low_n'] = df['low'].rolling(self.breakout_period).min()
        
        # 成交量均线
        if 'volume' in df.columns:
            df['volume_sma'] = self.calculate_volume_sma(df)
            df['volume_ratio'] = df['volume'] / df['volume_sma']
        else:
            df['volume_ratio'] = 1.0  # 无成交量数据时忽略过滤
        
        # 前一日突破区间
        df['prev_high_n'] = df['high_n'].shift(1)
        df['prev_low_n'] = df['low_n'].shift(1)
        
        df['signal'] = 0
        df['position'] = 0
        df['breakout_type'] = ''
        
        position = 0
        entry_price = 0
        stop_loss = 0
        
        for i in range(self.breakout_period + 5, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            
            # 成交量过滤
            volume_ok = True
            if self.use_volume_filter and 'volume' in df.columns:
                volume_ok = row['volume_ratio'] >= self.volume_multiplier
            
            # 向上突破
            if position == 0:
                if row['close'] > prev['prev_high_n'] and volume_ok:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    df.loc[df.index[i], 'breakout_type'] = 'breakout_up'
                    entry_price = row['close']
                    stop_loss = prev['prev_low_n']
                    position = 1
            
            # 向下突破
            if position == 0:
                if row['close'] < prev['prev_low_n'] and volume_ok:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    df.loc[df.index[i], 'breakout_type'] = 'breakout_down'
                    entry_price = row['close']
                    stop_loss = prev['prev_high_n']
                    position = -1
            
            # 移动止损
            if position == 1:
                # 更新止损为新的区间低点
                new_stop = df['low_n'].iloc[i]
                stop_loss = max(stop_loss, new_stop)
                
                # 出场：跌破止损或反向突破
                if row['low'] < stop_loss or row['close'] < df['low_n'].iloc[i]:
                    df.loc[df.index[i], 'signal'] = -1
                    position = 0
            
            if position == -1:
                # 更新止损为新的区间高点
                new_stop = df['high_n'].iloc[i]
                stop_loss = min(stop_loss, new_stop)
                
                # 出场：突破止损或反向突破
                if row['high'] > stop_loss or row['close'] > df['high_n'].iloc[i]:
                    df.loc[df.index[i], 'signal'] = 1
                    position = 0
        
        return df
