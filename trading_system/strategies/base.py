"""
策略基类
定义所有策略的统一接口
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime


class BaseStrategy(ABC):
    """策略基类 - 所有策略必须继承此类"""
    
    def __init__(self, name: str = "Base Strategy", category: str = "Generic"):
        """
        初始化策略基类
        
        Args:
            name: 策略名称
            category: 策略类别
        """
        self.name = name
        self.category = category
        self.initialized_at = datetime.now()
    
    @abstractmethod
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict:
        """
        分析市场数据，生成分析结果
        
        Args:
            df: K 线数据 (必须包含 open, high, low, close, volume 列)
            **kwargs: 策略特定的额外参数
        
        Returns:
            分析结果字典，必须包含:
            - status: 'SIGNAL' / 'NO_SIGNAL' / 'INSUFFICIENT_DATA'
            - strategy_name: 策略名称
            - timestamp: 分析时间戳
        """
        pass
    
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, symbol: str, **kwargs) -> Optional[Dict]:
        """
        生成交易信号
        
        Args:
            df: K 线数据
            symbol: 交易标的 (如 'BTCUSDT')
            **kwargs: 策略特定的额外参数
        
        Returns:
            信号字典或 None (无信号时)
            
            信号字典标准格式:
            - strategy_name: 策略名称
            - strategy_category: 策略类别
            - symbol: 交易标的
            - action: 'BUY' / 'SELL'
            - direction: 'LONG' / 'SHORT'
            - current_price: 当前价格
            - entry_price: 入场价格
            - entry_type: 'MARKET' / 'LIMIT'
            - stop_loss_price: 止损价格
            - stop_loss_pct: 止损百分比
            - take_profit_price: 止盈价格
            - take_profit_pct: 止盈百分比
            - risk_reward_ratio: 盈亏比
            - position_size_pct: 建议仓位百分比
            - confidence: 置信度 (0-100)
            - reason: 信号理由
            - pattern: 形态/模式名称
            - timeframe: 时间周期
            - timestamp: 信号时间戳
        """
        pass
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        计算 ATR (Average True Range)
        
        Args:
            df: K 线数据
            period: ATR 周期
        
        Returns:
            ATR 值
        """
        if len(df) < period:
            return df['close'].iloc[-1] * 0.02 if len(df) > 0 else 0.0
        
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(period).mean()
        return atr.iloc[-1]
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        计算 ADX (Average Directional Index) - 趋势强度指标
        
        Args:
            df: K 线数据
            period: ADX 周期
        
        Returns:
            ADX 值 (0-100)
            ADX > 25: 强趋势
            ADX < 20: 震荡
        """
        if len(df) < period * 2:
            return 0.0
        
        # 计算 +DM 和 -DM
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # 当 +DM > -DM 时，-DM = 0；反之亦然
        plus_dm[(plus_dm <= minus_dm) & (minus_dm > 0)] = 0
        minus_dm[(minus_dm <= plus_dm) & (plus_dm > 0)] = 0
        
        # 计算 ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        # 计算 +DI 和 -DI
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        # 计算 DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # 计算 ADX
        adx = dx.rolling(period).mean()
        
        return adx.iloc[-1] if not np.isnan(adx.iloc[-1]) else 0.0
        
        return atr.iloc[-1] if len(atr) > 0 and not pd.isna(atr.iloc[-1]) else df['close'].iloc[-1] * 0.02
    
    def _calculate_ma(self, df: pd.DataFrame, period: int) -> Optional[float]:
        """
        计算简单移动平均线
        
        Args:
            df: K 线数据
            period: 均线周期
        
        Returns:
            均线值或 None (数据不足时)
        """
        if len(df) < period:
            return None
        return df['close'].iloc[-period:].mean()
    
    def _find_swing_levels(self, df: pd.DataFrame, lookback: int = 100) -> Dict:
        """
        找出最近的 Swing 高低点
        
        Args:
            df: K 线数据
            lookback: 回溯 K 线数量
        
        Returns:
            {'highs': [(index, price), ...], 'lows': [(index, price), ...]}
        """
        swing_lookback = 20
        swing_highs = []
        swing_lows = []
        
        start_idx = max(swing_lookback, len(df) - lookback)
        
        for i in range(start_idx, len(df) - swing_lookback):
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            
            left_highs = df['high'].iloc[i-swing_lookback:i].max()
            right_highs = df['high'].iloc[i+1:i+swing_lookback+1].max()
            left_lows = df['low'].iloc[i-swing_lookback:i].min()
            right_lows = df['low'].iloc[i+1:i+swing_lookback+1].min()
            
            if high > left_highs and high > right_highs:
                swing_highs.append((i, high))
            if low < left_lows and low < right_lows:
                swing_lows.append((i, low))
        
        swing_highs.sort(key=lambda x: x[1], reverse=True)
        swing_lows.sort(key=lambda x: x[1])
        
        return {
            'highs': swing_highs[:5],
            'lows': swing_lows[:5]
        }
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算 RSI 指标
        
        Args:
            df: K 线数据
            period: RSI 周期
        
        Returns:
            RSI 序列
        """
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _check_trend(self, df: pd.DataFrame, fast_ma: int = 20, slow_ma: int = 50) -> str:
        """
        检查趋势方向
        
        Args:
            df: K 线数据
            fast_ma: 快线周期
            slow_ma: 慢线周期
        
        Returns:
            'BULL' / 'BEAR' / 'NEUTRAL'
        """
        if len(df) < slow_ma:
            return 'NEUTRAL'
        
        close = df['close'].iloc[-1]
        ma_fast = df['close'].rolling(fast_ma).mean().iloc[-1]
        ma_slow = df['close'].rolling(slow_ma).mean().iloc[-1]
        
        if close > ma_fast > ma_slow:
            return 'BULL'
        elif close < ma_fast < ma_slow:
            return 'BEAR'
        else:
            return 'NEUTRAL'
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        兼容老接口的批量信号生成方法
        
        默认返回空 DataFrame，子类可以按需实现
        
        Args:
            df: K 线数据
        
        Returns:
            信号 DataFrame
        """
        return pd.DataFrame()
    
    def get_info(self) -> Dict:
        """
        获取策略信息
        
        Returns:
            策略信息字典
        """
        return {
            'name': self.name,
            'category': self.category,
            'initialized_at': self.initialized_at.isoformat(),
            'class_name': self.__class__.__name__
        }
