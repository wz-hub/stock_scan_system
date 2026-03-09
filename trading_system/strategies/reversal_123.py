"""
策略 2: 123/2B 反转策略
来源：《专业投机原理》
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


class Reversal123Strategy:
    """
    123 法则和 2B 法则反转策略
    
    123 法则：
    1. 趋势线被突破
    2. 测试前高/前低失败
    3. 跌破前低/突破前高
    
    2B 法则：
    - 创新高后迅速回落至前高之下 → 做空
    - 创新低后迅速反弹至前低之上 → 做多
    """
    
    def __init__(self, lookback_period: int = 20, confirmation_bars: int = 3):
        self.lookback_period = lookback_period
        self.confirmation_bars = confirmation_bars
        
        self.name = "123/2B 反转"
    
    def find_pivot_high(self, df: pd.DataFrame, idx: int) -> Optional[int]:
        """查找前一个枢轴高点"""
        window = df['high'].iloc[max(0, idx-self.lookback_period):idx]
        if len(window) < 3:
            return None
        pivot_idx = window.idxmax()
        return df.index.get_loc(pivot_idx)
    
    def find_pivot_low(self, df: pd.DataFrame, idx: int) -> Optional[int]:
        """查找前一个枢轴低点"""
        window = df['low'].iloc[max(0, idx-self.lookback_period):idx]
        if len(window) < 3:
            return None
        pivot_idx = window.idxmin()
        return df.index.get_loc(pivot_idx)
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = df.copy()
        df['signal'] = 0
        df['position'] = 0
        df['pattern'] = ''
        
        position = 0
        entry_price = 0.0
        stop_loss = 0.0
        
        for i in range(self.lookback_period + 10, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i-1] if i > 0 else row
            
            # 保持持仓状态
            df.loc[df.index[i], 'position'] = position
            
            # 出场逻辑：止损
            if position == 1:
                if row['low'] < stop_loss:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = 0
                    position = 0
                    entry_price = 0.0
                    stop_loss = 0.0
                else:
                    df.loc[df.index[i], 'position'] = 1
            
            if position == -1:
                if row['high'] > stop_loss:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 0
                    position = 0
                    entry_price = 0.0
                    stop_loss = 0.0
                else:
                    df.loc[df.index[i], 'position'] = -1
            
            # 123 法则 - 底部反转（做多信号）
            if position == 0:
                pivot_low_idx = self.find_pivot_low(df, i)
                if pivot_low_idx is not None and pivot_low_idx >= 0:
                    prev_low = df['low'].iloc[pivot_low_idx]
                    
                    # 创新低后反弹
                    if row['low'] < prev_low and row['close'] > prev_low:
                        df.loc[df.index[i], 'signal'] = 1
                        df.loc[df.index[i], 'position'] = 1
                        df.loc[df.index[i], 'pattern'] = '123_bottom'
                        position = 1
                        entry_price = row['close']
                        stop_loss = prev_low * 0.98
            
            # 123 法则 - 顶部反转（做空信号 - 仅平仓）
            if position == 0:
                pivot_high_idx = self.find_pivot_high(df, i)
                if pivot_high_idx is not None and pivot_high_idx >= 0:
                    prev_high = df['high'].iloc[pivot_high_idx]
                    
                    # 创新高后回落
                    if row['high'] > prev_high and row['close'] < prev_high:
                        # 只做多，不做空
                        pass
            
            # 2B 法则 - 假突破做多
            if position == 0:
                pivot_low_idx = self.find_pivot_low(df, i)
                if pivot_low_idx is not None and pivot_low_idx >= 0:
                    prev_low = df['low'].iloc[pivot_low_idx]
                    
                    # 创新低后迅速反弹
                    if row['low'] < prev_low and row['close'] > prev_low:
                        if i > 1 and df['low'].iloc[i-1] < prev_low:
                            df.loc[df.index[i], 'signal'] = 1
                            df.loc[df.index[i], 'position'] = 1
                            df.loc[df.index[i], 'pattern'] = '2B_bottom'
                            position = 1
                            entry_price = row['close']
                            stop_loss = prev_low * 0.98
        
        return df
