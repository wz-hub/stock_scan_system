"""
成交量突破策略 - 4H 专用

核心逻辑:
- 成交量突然放大 (>3 倍) + 价格上涨 → 做多
- 成交量突然放大 (>3 倍) + 价格下跌 → 做空
- 成交量是真实信号

4H 优化参数
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime

from .base import BaseStrategy


class VolumeBreakout4HStrategy(BaseStrategy):
    """成交量突破策略 4H 专用"""
    
    def __init__(self):
        super().__init__(name="Volume Breakout 4H", category="Breakout")
        
        # 成交量参数 - 放宽
        self.volume_ratio = 2.0       # 成交量>2 倍 (从 3 倍降到 2 倍)
        self.volume_lookback = 30     # 看 30 根 K 线 (从 50 降到 30)
        
        # 价格确认 - 放宽
        self.price_change_min = 1.0   # 价格变化>1% (从 1.5% 降到 1%)
        
        # ATR 止损
        self.atr_period = 14
        self.atr_multiplier = 2.5     # 2.5 倍 ATR 止损
        
        # 止盈
        self.take_profit_atr = 7.5    # 7.5 倍 ATR 止盈 (3:1)
        
        # 置信度
        self.min_confidence = 65
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算 ATR"""
        if len(df) < period:
            return df['close'].iloc[-1] * 0.02
        
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(period).mean()
        
        return atr.iloc[-1] if not np.isnan(atr.iloc[-1]) else df['close'].iloc[-1] * 0.02
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """分析成交量突破"""
        if len(df) < 100:
            return {'status': 'INSUFFICIENT_DATA', 'signal': 'WAIT'}
        
        current_close = df['close'].iloc[-1]
        current_open = df['open'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        current_volume = df['volume'].iloc[-1]
        
        # 计算平均成交量
        avg_volume = df['volume'].iloc[-self.volume_lookback:-1].mean()
        
        # 成交量比率
        volume_ratio = current_volume / avg_volume
        
        # 价格变化
        price_change = (current_close - current_open) / current_open * 100
        
        # 计算 ATR
        atr = self._calculate_atr(df, self.atr_period)
        
        # 成交量放大确认
        if volume_ratio < self.volume_ratio:
            return {'status': 'NO_SIGNAL', 'signal': 'WAIT', 'reason': f'成交量{volume_ratio:.1f}x < {self.volume_ratio}x'}
        
        # 价格上涨 + 成交量放大 → 做多
        if price_change > self.price_change_min:
            confidence = min(90, 65 + (volume_ratio - self.volume_ratio) * 10 + (price_change - self.price_change_min) * 5)
            stop_loss = current_close - atr * self.atr_multiplier
            take_profit = current_close + atr * self.take_profit_atr
            
            return {
                'status': 'SIGNAL',
                'signal': 'BUY',
                'volume_ratio': volume_ratio,
                'price_change': price_change,
                'atr': atr,
                'current_price': current_close,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': confidence,
                'reason': f"放量{volume_ratio:.1f}x + 上涨{price_change:.1f}%"
            }
        
        # 价格下跌 + 成交量放大 → 做空
        if price_change < -self.price_change_min:
            confidence = min(90, 65 + (volume_ratio - self.volume_ratio) * 10 + (abs(price_change) - self.price_change_min) * 5)
            stop_loss = current_close + atr * self.atr_multiplier
            take_profit = current_close - atr * self.take_profit_atr
            
            return {
                'status': 'SIGNAL',
                'signal': 'SELL',
                'volume_ratio': volume_ratio,
                'price_change': price_change,
                'atr': atr,
                'current_price': current_close,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': confidence,
                'reason': f"放量{volume_ratio:.1f}x + 下跌{abs(price_change):.1f}%"
            }
        
        return {'status': 'NO_SIGNAL', 'signal': 'WAIT', 'reason': '价格变化不足'}
    
    def generate_signal(self, data_dict: Dict[str, pd.DataFrame], symbol: str) -> Optional[Dict]:
        """生成交易信号"""
        if '1D' not in data_dict and '1d' not in data_dict:
            return None
        
        df = data_dict.get('1D', data_dict.get('1d'))
        if df is None or len(df) < 100:
            return None
        
        analysis = self.analyze(df)
        
        if analysis.get('signal') == 'WAIT':
            return None
        
        current_price = analysis['current_price']
        direction = 'LONG' if analysis['signal'] == 'BUY' else 'SHORT'
        
        # 止损止盈
        stop_loss = analysis.get('stop_loss', current_price * 0.965)
        take_profit = analysis.get('take_profit', current_price * 1.105)
        
        # 计算实际止损止盈百分比
        if direction == 'LONG':
            stop_loss_pct = (current_price - stop_loss) / current_price * 100
            take_profit_pct = (take_profit - current_price) / current_price * 100
        else:
            stop_loss_pct = (stop_loss - current_price) / current_price * 100
            take_profit_pct = (current_price - take_profit) / current_price * 100
        
        confidence = analysis.get('confidence', 70)
        if confidence < self.min_confidence:
            return None
        
        return {
            'strategy_name': self.name,
            'strategy_category': self.category,
            'symbol': symbol,
            'action': analysis['signal'],
            'direction': direction,
            'current_price': str(current_price),
            'entry_price': current_price,
            'entry_type': 'MARKET',
            'stop_loss_price': stop_loss,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_price': take_profit,
            'take_profit_pct': take_profit_pct,
            'risk_reward_ratio': take_profit_pct / stop_loss_pct,
            'position_size_pct': 10.0,
            'confidence': confidence,
            'reason': analysis['reason'],
            'pattern': 'Volume Breakout',
            'timeframe': '4H',
            'timestamp': datetime.now().isoformat()
        }


def get_volume_breakout_4h_strategy() -> VolumeBreakout4HStrategy:
    return VolumeBreakout4HStrategy()
