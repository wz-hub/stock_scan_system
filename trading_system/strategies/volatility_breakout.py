"""
策略 6: 波动率突破策略
来源：《海龟交易法则》《量化交易》
"""
import pandas as pd
import numpy as np
from typing import Dict


class VolatilityBreakoutStrategy:
    """
    波动率突破策略
    
    使用 ATR 或布林带识别波动率
    突破波动区间时入场
    """
    
    def __init__(self, atr_period: int = 14, atr_multiplier: float = 2.0,
                 bb_period: int = 20, bb_std: float = 2.0):
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.bb_period = bb_period
        self.bb_std = bb_std
        
        self.name = "波动率突破"
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """计算 ATR"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()
        return atr
    
    def calculate_bollinger_bands(self, df: pd.DataFrame) -> tuple:
        """计算布林带"""
        middle = df['close'].rolling(self.bb_period).mean()
        std = df['close'].rolling(self.bb_period).std()
        upper = middle + self.bb_std * std
        lower = middle - self.bb_std * std
        return upper, middle, lower
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = df.copy()
        
        # 计算指标
        df['atr'] = self.calculate_atr(df)
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self.calculate_bollinger_bands(df)
        
        # ATR 通道
        df['atr_upper'] = df['close'].shift(1) + self.atr_multiplier * df['atr']
        df['atr_lower'] = df['close'].shift(1) - self.atr_multiplier * df['atr']
        
        # 布林带宽度
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_width_pct'] = df['bb_width'].rolling(20).rank(pct=True)
        
        df['signal'] = 0
        df['position'] = 0
        df['breakout_type'] = ''
        
        position = 0
        entry_price = 0
        stop_loss = 0
        
        for i in range(self.bb_period + 10, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            
            # ATR 突破策略
            if position == 0:
                # 向上突破
                if row['close'] > prev['atr_upper']:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    df.loc[df.index[i], 'breakout_type'] = 'atr_up'
                    entry_price = row['close']
                    stop_loss = entry_price - self.atr_multiplier * row['atr']
                    position = 1
                
                # 向下突破
                elif row['close'] < prev['atr_lower']:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    df.loc[df.index[i], 'breakout_type'] = 'atr_down'
                    entry_price = row['close']
                    stop_loss = entry_price + self.atr_multiplier * row['atr']
                    position = -1
            
            # 布林带突破策略（低波动后突破）
            if position == 0 and prev['bb_width_pct'] < 0.3:  # 布林带收窄
                # 向上突破
                if row['close'] > prev['bb_upper'] and row['close'] > prev['high']:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    df.loc[df.index[i], 'breakout_type'] = 'bb_up'
                    entry_price = row['close']
                    stop_loss = prev['bb_middle']
                    position = 1
                
                # 向下突破
                elif row['close'] < prev['bb_lower'] and row['close'] < prev['low']:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    df.loc[df.index[i], 'breakout_type'] = 'bb_down'
                    entry_price = row['close']
                    stop_loss = prev['bb_middle']
                    position = -1
            
            # 移动止损
            if position == 1:
                stop_loss = max(stop_loss, row['close'] - self.atr_multiplier * row['atr'])
                if row['low'] < stop_loss:
                    df.loc[df.index[i], 'signal'] = -1
                    position = 0
            
            if position == -1:
                stop_loss = min(stop_loss, row['close'] + self.atr_multiplier * row['atr'])
                if row['high'] > stop_loss:
                    df.loc[df.index[i], 'signal'] = 1
                    position = 0
        
        return df
