"""
策略 9: RSI 策略
来源：《技术分析》
"""
import pandas as pd
import numpy as np
from typing import Dict


class RSIStrategy:
    """
    RSI 相对强弱指标策略
    
    规则：
    - RSI < 30 超卖 → 做多
    - RSI > 70 超买 → 做空
    - RSI 背离 → 反转信号
    """
    
    def __init__(self, rsi_period: int = 14, oversold: float = 30, 
                 overbought: float = 70, divergence_lookback: int = 20):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.divergence_lookback = divergence_lookback
        
        self.name = "RSI"
    
    def calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
        """计算 RSI"""
        delta = df['close'].diff()
        
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        avg_gain = gain.rolling(self.rsi_period).mean()
        avg_loss = loss.rolling(self.rsi_period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def detect_bullish_divergence(self, df: pd.DataFrame, idx: int) -> bool:
        """检测看涨背离"""
        if idx < self.divergence_lookback:
            return False
        
        window = df.iloc[idx-self.divergence_lookback:idx+1]
        
        # 价格创新低
        price_low = window['low'].min()
        price_low_idx = window['low'].idxmin()
        
        # RSI 未创新低
        rsi_at_price_low = df.loc[price_low_idx, 'rsi']
        current_rsi = df.iloc[idx]['rsi']
        
        # 当前价格接近低点但 RSI 更高
        if (df.iloc[idx]['low'] <= price_low * 1.02 and 
            current_rsi > rsi_at_price_low and
            rsi_at_price_low < self.oversold):
            return True
        
        return False
    
    def detect_bearish_divergence(self, df: pd.DataFrame, idx: int) -> bool:
        """检测看跌背离"""
        if idx < self.divergence_lookback:
            return False
        
        window = df.iloc[idx-self.divergence_lookback:idx+1]
        
        # 价格创新高
        price_high = window['high'].max()
        price_high_idx = window['high'].idxmax()
        
        # RSI 未创新高
        rsi_at_price_high = df.loc[price_high_idx, 'rsi']
        current_rsi = df.iloc[idx]['rsi']
        
        # 当前价格接近高点但 RSI 更低
        if (df.iloc[idx]['high'] >= price_high * 0.98 and 
            current_rsi < rsi_at_price_high and
            rsi_at_price_high > self.overbought):
            return True
        
        return False
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = df.copy()
        
        # 计算 RSI
        df['rsi'] = self.calculate_rsi(df)
        
        df['signal'] = 0
        df['position'] = 0
        df['rsi_signal_type'] = ''
        
        position = 0
        
        for i in range(self.rsi_period + 10, len(df)):
            row = df.iloc[i]
            
            # 策略 1: 超卖超买
            if position == 0:
                # RSI 超卖
                if row['rsi'] < self.oversold:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    df.loc[df.index[i], 'rsi_signal_type'] = 'oversold'
                    position = 1
                
                # RSI 超买
                elif row['rsi'] > self.overbought:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    df.loc[df.index[i], 'rsi_signal_type'] = 'overbought'
                    position = -1
            
            # 策略 2: RSI 背离
            if position == 0:
                if self.detect_bullish_divergence(df, i):
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    df.loc[df.index[i], 'rsi_signal_type'] = 'bullish_divergence'
                    position = 1
                
                elif self.detect_bearish_divergence(df, i):
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    df.loc[df.index[i], 'rsi_signal_type'] = 'bearish_divergence'
                    position = -1
            
            # 策略 3: RSI 中线交叉
            if position == 0:
                prev = df.iloc[i-1]
                # RSI 上穿 50
                if prev['rsi'] < 50 and row['rsi'] > 50:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    df.loc[df.index[i], 'rsi_signal_type'] = 'bullish_cross'
                    position = 1
                
                # RSI 下穿 50
                elif prev['rsi'] > 50 and row['rsi'] < 50:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    df.loc[df.index[i], 'rsi_signal_type'] = 'bearish_cross'
                    position = -1
            
            # 出场逻辑
            if position == 1:
                # RSI 回到中性或超买
                if row['rsi'] > 60 or row['rsi'] < 40:
                    df.loc[df.index[i], 'signal'] = -1
                    position = 0
            
            if position == -1:
                # RSI 回到中性或超卖
                if row['rsi'] < 40 or row['rsi'] > 60:
                    df.loc[df.index[i], 'signal'] = 1
                    position = 0
        
        return df
