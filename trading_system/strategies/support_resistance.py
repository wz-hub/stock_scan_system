"""
策略 3: 支撑阻力交易法
来源：《日本蜡烛图技术》《股市趋势技术分析》
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class SupportResistanceStrategy:
    """
    支撑阻力位交易策略
    
    规则：
    - 识别关键支撑阻力位
    - 在支撑位出现看涨 K 线做多
    - 在阻力位出现看跌 K 线做空
    """
    
    def __init__(self, lookback_period: int = 50, touch_tolerance: float = 0.02):
        self.lookback_period = lookback_period
        self.touch_tolerance = touch_tolerance  # 2% 容差
        
        self.name = "支撑阻力"
        self.support_levels: List[float] = []
        self.resistance_levels: List[float] = []
    
    def find_levels(self, df: pd.DataFrame, idx: int) -> Tuple[List[float], List[float]]:
        """查找支撑阻力位"""
        window = df.iloc[max(0, idx-self.lookback_period):idx]
        
        if len(window) < 10:
            return [], []
        
        # 寻找局部高点和低点
        resistance_levels = []
        support_levels = []
        
        for i in range(2, len(window)-2):
            # 阻力位：局部高点
            if (window['high'].iloc[i] > window['high'].iloc[i-1] and
                window['high'].iloc[i] > window['high'].iloc[i+1] and
                window['high'].iloc[i] > window['high'].iloc[i-2] and
                window['high'].iloc[i] > window['high'].iloc[i+2]):
                resistance_levels.append(window['high'].iloc[i])
            
            # 支撑位：局部低点
            if (window['low'].iloc[i] < window['low'].iloc[i-1] and
                window['low'].iloc[i] < window['low'].iloc[i+1] and
                window['low'].iloc[i] < window['low'].iloc[i-2] and
                window['low'].iloc[i] < window['low'].iloc[i+2]):
                support_levels.append(window['low'].iloc[i])
        
        # 合并相近的水平
        def merge_close_levels(levels: List[float], tolerance: float = 0.01) -> List[float]:
            if not levels:
                return []
            levels = sorted(levels)
            merged = [levels[0]]
            for level in levels[1:]:
                if level - merged[-1] > merged[-1] * tolerance:
                    merged.append(level)
            return merged
        
        return merge_close_levels(support_levels), merge_close_levels(resistance_levels)
    
    def is_near_level(self, price: float, levels: List[float], tolerance: float = None) -> bool:
        """检查价格是否接近某个水平"""
        if tolerance is None:
            tolerance = self.touch_tolerance
        for level in levels:
            if abs(price - level) / level < tolerance:
                return True
        return False
    
    def detect_candlestick_pattern(self, df: pd.DataFrame, idx: int) -> str:
        """检测 K 线形态"""
        row = df.iloc[idx]
        prev = df.iloc[idx-1] if idx > 0 else row
        
        body = row['close'] - row['open']
        body_size = abs(body)
        range_size = row['high'] - row['low']
        
        upper_shadow = row['high'] - max(row['open'], row['close'])
        lower_shadow = min(row['open'], row['close']) - row['low']
        
        # 锤子线
        if (lower_shadow > body_size * 2 and 
            upper_shadow < body_size * 0.5 and
            range_size > 0):
            return 'hammer'
        
        # 流星线
        if (upper_shadow > body_size * 2 and 
            lower_shadow < body_size * 0.5 and
            range_size > 0):
            return 'shooting_star'
        
        # 看涨吞没
        if (idx > 0 and 
            prev['close'] < prev['open'] and
            row['close'] > row['open'] and
            row['open'] < prev['close'] and
            row['close'] > prev['open']):
            return 'bullish_engulfing'
        
        # 看跌吞没
        if (idx > 0 and 
            prev['close'] > prev['open'] and
            row['close'] < row['open'] and
            row['open'] > prev['close'] and
            row['close'] < prev['open']):
            return 'bearish_engulfing'
        
        return ''
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = df.copy()
        df['signal'] = 0
        df['position'] = 0
        df['pattern'] = ''
        df['support'] = np.nan
        df['resistance'] = np.nan
        
        position = 0
        
        for i in range(self.lookback_period, len(df)):
            row = df.iloc[i]
            
            # 更新支撑阻力位
            supports, resistances = self.find_levels(df, i)
            self.support_levels = supports
            self.resistance_levels = resistances
            
            # 记录最近的支撑阻力
            if supports:
                df.loc[df.index[i], 'support'] = max([s for s in supports if s < row['close']], default=np.nan)
            if resistances:
                df.loc[df.index[i], 'resistance'] = min([r for r in resistances if r > row['close']], default=np.nan)
            
            # 检测 K 线形态
            pattern = self.detect_candlestick_pattern(df, i)
            df.loc[df.index[i], 'pattern'] = pattern
            
            # 在支撑位出现看涨信号做多
            if position == 0 and pattern in ['hammer', 'bullish_engulfing']:
                if self.is_near_level(row['low'], self.support_levels):
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    position = 1
            
            # 在阻力位出现看跌信号做空
            if position == 0 and pattern in ['shooting_star', 'bearish_engulfing']:
                if self.is_near_level(row['high'], self.resistance_levels):
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    position = -1
            
            # 简单出场：反向信号或突破支撑阻力
            if position == 1:
                if df['signal'].iloc[i] == -1 or row['close'] < df.loc[df.index[i], 'support'] * 0.98:
                    df.loc[df.index[i], 'signal'] = -1
                    position = 0
            
            if position == -1:
                if df['signal'].iloc[i] == 1 or row['close'] > df.loc[df.index[i], 'resistance'] * 1.02:
                    df.loc[df.index[i], 'signal'] = 1
                    position = 0
        
        return df
