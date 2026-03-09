"""
策略 4: 形态交易策略
来源：《日本蜡烛图技术》
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


class PatternTradingStrategy:
    """
    图表形态交易策略
    
    形态包括：
    - 头肩顶/底
    - 双顶/双底
    - 三角形
    - 旗形/楔形
    """
    
    def __init__(self, lookback_period: int = 60):
        self.lookback_period = lookback_period
        
        self.name = "形态交易"
    
    def detect_double_top(self, df: pd.DataFrame, idx: int) -> bool:
        """检测双顶形态"""
        if idx < 30:
            return False
        
        window = df.iloc[idx-30:idx+1]
        highs = window['high'].values
        
        # 寻找两个相近的高点
        peak1_idx = np.argmax(highs[:len(highs)//2])
        peak2_idx = len(highs)//2 + np.argmax(highs[len(highs)//2:])
        
        peak1 = highs[peak1_idx]
        peak2 = highs[peak2_idx]
        
        # 两个高点相差不超过 2%
        if abs(peak1 - peak2) / peak1 < 0.02:
            # 中间有回调
            trough = np.min(highs[peak1_idx:peak2_idx+1])
            if trough < peak1 * 0.95:
                return True
        
        return False
    
    def detect_double_bottom(self, df: pd.DataFrame, idx: int) -> bool:
        """检测双底形态"""
        if idx < 30:
            return False
        
        window = df.iloc[idx-30:idx+1]
        lows = window['low'].values
        
        # 寻找两个相近的低点
        trough1_idx = np.argmin(lows[:len(lows)//2])
        trough2_idx = len(lows)//2 + np.argmin(lows[len(lows)//2:])
        
        trough1 = lows[trough1_idx]
        trough2 = lows[trough2_idx]
        
        # 两个低点相差不超过 2%
        if abs(trough1 - trough2) / trough1 < 0.02:
            # 中间有反弹
            peak = np.max(lows[trough1_idx:trough2_idx+1])
            if peak > trough1 * 1.05:
                return True
        
        return False
    
    def detect_head_shoulders(self, df: pd.DataFrame, idx: int) -> Optional[str]:
        """检测头肩形态"""
        if idx < 40:
            return None
        
        window = df.iloc[idx-40:idx+1]
        highs = window['high'].values
        lows = window['low'].values
        
        # 寻找三个峰值
        from scipy.signal import argrelextrema
        
        try:
            peak_indices = argrelextrema(highs, np.greater, order=5)[0]
            
            if len(peak_indices) >= 3:
                # 取最近的三个峰值
                peaks = peak_indices[-3:]
                peak_values = highs[peaks]
                
                # 中间最高，两边较低且相近
                if (peak_values[1] > peak_values[0] and 
                    peak_values[1] > peak_values[2] and
                    abs(peak_values[0] - peak_values[2]) / peak_values[0] < 0.05):
                    return 'head_shoulders_top'
                
                # 头肩底
                trough_indices = argrelextrema(lows, np.less, order=5)[0]
                if len(trough_indices) >= 3:
                    troughs = trough_indices[-3:]
                    trough_values = lows[troughs]
                    
                    if (trough_values[1] < trough_values[0] and 
                        trough_values[1] < trough_values[2] and
                        abs(trough_values[0] - trough_values[2]) / trough_values[0] < 0.05):
                        return 'head_shoulders_bottom'
        except:
            pass
        
        return None
    
    def detect_triangle(self, df: pd.DataFrame, idx: int) -> Optional[str]:
        """检测三角形形态"""
        if idx < 30:
            return None
        
        window = df.iloc[idx-30:idx+1]
        highs = window['high'].values
        lows = window['low'].values
        
        # 检查高点是否收敛
        recent_highs = highs[-15:]
        recent_lows = lows[-15:]
        
        high_slope = np.polyfit(range(len(recent_highs)), recent_highs, 1)[0]
        low_slope = np.polyfit(range(len(recent_lows)), recent_lows, 1)[0]
        
        # 对称三角形：高点下降，低点上升
        if high_slope < 0 and low_slope > 0:
            return 'symmetric_triangle'
        
        # 上升三角形：高点水平，低点上升
        if abs(high_slope) < 0.001 and low_slope > 0:
            return 'ascending_triangle'
        
        # 下降三角形：高点下降，低点水平
        if high_slope < 0 and abs(low_slope) < 0.001:
            return 'descending_triangle'
        
        return None
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = df.copy()
        df['signal'] = 0
        df['position'] = 0
        df['pattern'] = ''
        
        position = 0
        
        for i in range(self.lookback_period, len(df)):
            row = df.iloc[i]
            pattern = ''
            
            # 检测双顶
            if self.detect_double_top(df, i):
                pattern = 'double_top'
                if position == 0:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'position'] = -1
                    position = -1
            
            # 检测双底
            elif self.detect_double_bottom(df, i):
                pattern = 'double_bottom'
                if position == 0:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'position'] = 1
                    position = 1
            
            # 检测头肩形态
            else:
                hs_pattern = self.detect_head_shoulders(df, i)
                if hs_pattern == 'head_shoulders_top':
                    pattern = 'head_shoulders_top'
                    if position == 0:
                        df.loc[df.index[i], 'signal'] = -1
                        df.loc[df.index[i], 'position'] = -1
                        position = -1
                elif hs_pattern == 'head_shoulders_bottom':
                    pattern = 'head_shoulders_bottom'
                    if position == 0:
                        df.loc[df.index[i], 'signal'] = 1
                        df.loc[df.index[i], 'position'] = 1
                        position = 1
            
            # 检测三角形突破
            triangle = self.detect_triangle(df, i)
            if triangle:
                pattern = triangle
                # 等待突破
                if i > 0:
                    if row['close'] > df['high'].iloc[i-5:i].max():
                        df.loc[df.index[i], 'signal'] = 1
                        df.loc[df.index[i], 'position'] = 1
                        position = 1
                    elif row['close'] < df['low'].iloc[i-5:i].min():
                        df.loc[df.index[i], 'signal'] = -1
                        df.loc[df.index[i], 'position'] = -1
                        position = -1
            
            df.loc[df.index[i], 'pattern'] = pattern
            
            # 简单出场逻辑
            if position != 0 and df['signal'].iloc[i] != 0 and df['signal'].iloc[i] != position:
                position = 0
        
        return df
