"""
策略 1: 趋势跟踪策略 (Trend Following)
来源：《海龟交易法则》《期货市场技术分析》
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


class TrendFollowingStrategy:
    """
    海龟交易法则趋势跟踪策略
    
    规则：
    - 入场：突破 N 日高点做多，跌破 N 日低点做空
    - 出场：反向突破或移动止损
    - 仓位：基于 ATR 动态调整
    """
    
    def __init__(self, entry_period: int = 20, exit_period: int = 10, 
                 atr_period: int = 14, atr_multiplier: float = 2.0):
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        
        self.name = "趋势跟踪 (海龟)"
        self.position = None
        self.entry_price = 0
        self.stop_loss = 0
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """计算 ATR"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()
        return atr
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号 - 带交易量过滤"""
        df = df.copy()
        df['atr'] = self.calculate_atr(df)
        df['donchian_high'] = df['high'].rolling(self.entry_period).max()
        df['donchian_low'] = df['low'].rolling(self.entry_period).min()
        df['exit_high'] = df['high'].rolling(self.exit_period).max()
        df['exit_low'] = df['low'].rolling(self.exit_period).min()
        
        # 交易量分析
        if 'volume' in df.columns:
            df['volume_sma20'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma20']
            df['volume_trend'] = df['volume'].rolling(5).mean() / df['volume_sma20']
        else:
            df['volume_ratio'] = 1.0
            df['volume_trend'] = 1.0
        
        df['signal'] = 0
        df['position'] = 0
        df['stop_loss'] = 0.0
        df['volume_confirmed'] = False
        
        position = 0
        entry_price = 0.0
        stop_loss = 0.0
        
        for i in range(self.entry_period + 1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # 跳过 ATR 为 NaN 的行
            if pd.isna(row['atr']) or pd.isna(prev_row['donchian_high']):
                continue
            
            # 交易量过滤
            volume_confirmed = row.get('volume_ratio', 1.0) >= 1.5
            
            # 开多信号：突破 N 日高点 + 放量
            if position == 0 and row['close'] > prev_row['donchian_high']:
                if volume_confirmed:  # 交易量确认
                    position = 1
                    entry_price = row['close']
                    stop_loss = entry_price - self.atr_multiplier * row['atr']
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    df.loc[df.index[i], 'stop_loss'] = stop_loss
                    df.loc[df.index[i], 'volume_confirmed'] = True
            
            # 持有多单
            elif position == 1:
                df.loc[df.index[i], 'position'] = 1
                # 更新移动止损
                stop_loss = max(stop_loss, row['close'] - self.atr_multiplier * row['atr'])
                df.loc[df.index[i], 'stop_loss'] = stop_loss
                
                # 出场信号：跌破 exit_low 或止损
                if row['close'] < prev_row['exit_low'] or row['low'] < stop_loss:
                    df.loc[df.index[i], 'signal'] = -1
                    position = 0
                    entry_price = 0.0
                    stop_loss = 0.0
            
            # 开空信号（可选）
            elif position == 0 and row['close'] < prev_row['donchian_low']:
                if volume_confirmed:  # 交易量确认
                    position = -1
                    entry_price = row['close']
                    stop_loss = entry_price + self.atr_multiplier * row['atr']
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    df.loc[df.index[i], 'stop_loss'] = stop_loss
                    df.loc[df.index[i], 'volume_confirmed'] = True
            
            # 持有空单
            elif position == -1:
                df.loc[df.index[i], 'position'] = -1
                stop_loss = min(stop_loss, row['close'] + self.atr_multiplier * row['atr'])
                df.loc[df.index[i], 'stop_loss'] = stop_loss
                
                if row['close'] > prev_row['exit_high'] or row['high'] > stop_loss:
                    df.loc[df.index[i], 'signal'] = 1
                    position = 0
                    entry_price = 0.0
                    stop_loss = 0.0
        
        return df
