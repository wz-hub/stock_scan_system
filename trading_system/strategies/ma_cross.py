"""
策略 5: 均线交叉策略
来源：《期货市场技术分析》
"""
import pandas as pd
import numpy as np
from typing import Dict


class MACrossStrategy:
    """
    移动平均线交叉策略
    
    双均线系统：
    - 快线金叉慢线 → 做多
    - 快线死叉慢线 → 做空
    
    三均线系统：
    - 三线同向排列时入场
    """
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, 
                 signal_period: int = 9, use_ema: bool = True,
                 filter_ma: int = 200):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.use_ema = use_ema
        self.filter_ma = filter_ma  # 200 日均线过滤
        
        self.name = "均线交叉"
    
    def calculate_ma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """计算移动平均线"""
        if self.use_ema:
            return df['close'].ewm(span=period, adjust=False).mean()
        else:
            return df['close'].rolling(period).mean()
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = df.copy()
        
        # 计算均线
        df['fast_ma'] = self.calculate_ma(df, self.fast_period)
        df['slow_ma'] = self.calculate_ma(df, self.slow_period)
        df['signal_ma'] = self.calculate_ma(df, self.signal_period)
        df['filter_ma'] = self.calculate_ma(df, self.filter_ma)
        
        df['signal'] = 0
        df['position'] = 0
        df['ma_alignment'] = ''
        
        position = 0
        
        for i in range(self.filter_ma, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            
            # 判断均线排列
            bull_alignment = (row['fast_ma'] > row['slow_ma'] > row['filter_ma'])
            bear_alignment = (row['fast_ma'] < row['slow_ma'] < row['filter_ma'])
            
            if bull_alignment:
                df.loc[df.index[i], 'ma_alignment'] = 'bull'
            elif bear_alignment:
                df.loc[df.index[i], 'ma_alignment'] = 'bear'
            else:
                df.loc[df.index[i], 'ma_alignment'] = 'neutral'
            
            # 双均线金叉
            if (prev['fast_ma'] <= prev['slow_ma'] and 
                row['fast_ma'] > row['slow_ma']):
                # 在 200 日均线上方只做多
                if row['close'] > row['filter_ma']:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    position = 1
            
            # 双均线死叉
            elif (prev['fast_ma'] >= prev['slow_ma'] and 
                  row['fast_ma'] < row['slow_ma']):
                # 在 200 日均线下方只做空
                if row['close'] < row['filter_ma']:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    position = -1
            
            # 三均线系统：完全排列时入场
            if position == 0:
                # 多头排列
                if (row['fast_ma'] > row['slow_ma'] > row['signal_ma'] > row['filter_ma'] and
                    prev['fast_ma'] <= prev['slow_ma']):
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    position = 1
                
                # 空头排列
                elif (row['fast_ma'] < row['slow_ma'] < row['signal_ma'] < row['filter_ma'] and
                      prev['fast_ma'] >= prev['slow_ma']):
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    position = -1
            
            # 出场：均线反向交叉或价格远离
            if position == 1:
                if row['close'] < row['filter_ma'] * 0.95:  # 跌破过滤均线 5%
                    df.loc[df.index[i], 'signal'] = -1
                    position = 0
            
            if position == -1:
                if row['close'] > row['filter_ma'] * 1.05:  # 突破过滤均线 5%
                    df.loc[df.index[i], 'signal'] = 1
                    position = 0
        
        return df
