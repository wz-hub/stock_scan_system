"""
策略 8: 布林带策略
来源：《期货市场技术分析》
"""
import pandas as pd
import numpy as np
from typing import Dict


class BollingerBandsStrategy:
    """
    布林带交易策略
    
    规则：
    - 价格触及下轨 + 反转信号 → 做多
    - 价格触及上轨 + 反转信号 → 做空
    - 布林带收缩后突破 → 趋势开始
    """
    
    def __init__(self, period: int = 20, std_dev: float = 2.0,
                 squeeze_threshold: float = 0.05):
        self.period = period
        self.std_dev = std_dev
        self.squeeze_threshold = squeeze_threshold
        
        self.name = "布林带"
    
    def calculate_bollinger_bands(self, df: pd.DataFrame) -> tuple:
        """计算布林带"""
        middle = df['close'].rolling(self.period).mean()
        std = df['close'].rolling(self.period).std()
        upper = middle + self.std_dev * std
        lower = middle - self.std_dev * std
        
        # 布林带宽度
        bandwidth = (upper - lower) / middle
        
        # 布林带位置 (%B)
        percent_b = (df['close'] - lower) / (upper - lower)
        
        return upper, middle, lower, bandwidth, percent_b
    
    def detect_squeeze(self, df: pd.DataFrame) -> pd.Series:
        """检测布林带挤压"""
        _, _, _, bandwidth, _ = self.calculate_bollinger_bands(df)
        
        # 布林带宽度处于历史低位
        bandwidth_percentile = bandwidth.rolling(60).rank(pct=True)
        squeeze = bandwidth_percentile < self.squeeze_threshold
        
        return squeeze
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = df.copy()
        
        # 计算布林带
        df['bb_upper'], df['bb_middle'], df['bb_lower'], df['bb_bandwidth'], df['bb_percent_b'] = \
            self.calculate_bollinger_bands(df)
        
        # 检测挤压
        df['bb_squeeze'] = self.detect_squeeze(df)
        
        df['signal'] = 0
        df['position'] = 0
        df['bb_signal_type'] = ''
        
        position = 0
        
        for i in range(self.period + 10, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            
            # 策略 1: 均值回归（触及边界后回归）
            if position == 0:
                # 触及下轨后反弹
                if (prev['close'] <= prev['bb_lower'] and 
                    row['close'] > row['bb_lower'] and
                    row['bb_percent_b'] < 0.2):
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    df.loc[df.index[i], 'bb_signal_type'] = 'mean_reversion_long'
                    position = 1
                
                # 触及上轨后回落
                elif (prev['close'] >= prev['bb_upper'] and 
                      row['close'] < row['bb_upper'] and
                      row['bb_percent_b'] > 0.8):
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    df.loc[df.index[i], 'bb_signal_type'] = 'mean_reversion_short'
                    position = -1
            
            # 策略 2: 布林带挤压后突破
            if position == 0 and prev['bb_squeeze']:
                # 向上突破
                if row['close'] > prev['bb_upper'] and row['close'] > prev['high']:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    df.loc[df.index[i], 'bb_signal_type'] = 'squeeze_breakout_up'
                    position = 1
                
                # 向下突破
                elif row['close'] < prev['bb_lower'] and row['close'] < prev['low']:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    df.loc[df.index[i], 'bb_signal_type'] = 'squeeze_breakout_down'
                    position = -1
            
            # 出场逻辑
            if position == 1:
                # 触及上轨或中线
                if row['close'] >= row['bb_upper'] or row['close'] < row['bb_middle'] * 0.98:
                    df.loc[df.index[i], 'signal'] = -1
                    position = 0
            
            if position == -1:
                # 触及下轨或中线
                if row['close'] <= row['bb_lower'] or row['close'] > row['bb_middle'] * 1.02:
                    df.loc[df.index[i], 'signal'] = 1
                    position = 0
        
        return df
