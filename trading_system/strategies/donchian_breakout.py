"""
唐奇安通道突破策略

核心逻辑：
- 突破 N 日高点 → 买入
- 跌破 N 日低点 → 卖出
- 经典趋势跟踪策略
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime

from .base import BaseStrategy


class DonchianBreakoutStrategy(BaseStrategy):
    """唐奇安通道突破策略"""
    
    def __init__(self):
        super().__init__(name="Donchian Breakout", category="Breakout")
        
        # 通道周期
        self.channel_period = 20  # 20 日突破
        
        # 置信度
        self.min_confidence = 70
        
        # 止损止盈
        self.stop_loss_pct = 2.5   # 2.5% 止损
        self.take_profit_pct = 7.5  # 7.5% 止盈 (3:1 盈亏比)
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """分析突破信号"""
        if len(df) < self.channel_period + 1:
            return {
                'status': 'INSUFFICIENT_DATA',
                'signal': 'WAIT'
            }
        
        current_close = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        # 计算通道（不包含当前 K 线）
        upper_channel = df['high'].iloc[-self.channel_period-1:-1].max()
        lower_channel = df['low'].iloc[-self.channel_period-1:-1].min()
        
        # 判断突破
        if current_high > upper_channel:
            signal = 'BUY'
            breakout_strength = (current_high - upper_channel) / upper_channel * 100
        elif current_low < lower_channel:
            signal = 'SELL'
            breakout_strength = (lower_channel - current_low) / lower_channel * 100
        else:
            signal = 'WAIT'
            breakout_strength = 0
        
        return {
            'status': 'SIGNAL' if signal != 'WAIT' else 'NO_SIGNAL',
            'signal': signal,
            'upper_channel': upper_channel,
            'lower_channel': lower_channel,
            'close': current_close,
            'breakout_strength': breakout_strength
        }
    
    def generate_signal(self, data_dict: Dict[str, pd.DataFrame], symbol: str) -> Optional[Dict]:
        """生成交易信号"""
        # 使用日线数据
        if '1D' not in data_dict and '1d' not in data_dict:
            return None
        
        df = data_dict.get('1D', data_dict.get('1d'))
        if df is None or len(df) < self.channel_period + 1:
            return None
        
        analysis = self.analyze(df)
        
        if analysis['signal'] == 'WAIT':
            return None
        
        # 根据突破强度调整置信度
        base_confidence = 70
        confidence = min(90, base_confidence + analysis['breakout_strength'] * 10)
        
        if confidence < self.min_confidence:
            return None
        
        current_price = analysis['close']
        direction = 'LONG' if analysis['signal'] == 'BUY' else 'SHORT'
        
        # 计算止损止盈
        stop_loss_price = current_price * (1 - self.stop_loss_pct / 100) if direction == 'LONG' else current_price * (1 + self.stop_loss_pct / 100)
        take_profit_price = current_price * (1 + self.take_profit_pct / 100) if direction == 'LONG' else current_price * (1 - self.take_profit_pct / 100)
        
        return {
            'strategy_name': self.name,
            'strategy_category': self.category,
            'symbol': symbol,
            'action': analysis['signal'],
            'direction': direction,
            'current_price': str(current_price),
            'entry_price': str(current_price),
            'entry_type': 'MARKET',
            'stop_loss_price': str(stop_loss_price),
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_price': str(take_profit_price),
            'take_profit_pct': self.take_profit_pct,
            'risk_reward_ratio': self.take_profit_pct / self.stop_loss_pct,
            'position_size_pct': 10.0,
            'confidence': confidence,
            'reason': f"突破{self.channel_period}日通道 (强度：{analysis['breakout_strength']:.2f}%)",
            'pattern': 'Donchian Breakout',
            'timeframe': '1D',
            'timestamp': datetime.now().isoformat()
        }


# 便捷函数
def get_donchian_strategy() -> DonchianBreakoutStrategy:
    """获取策略实例"""
    return DonchianBreakoutStrategy()


def generate_donchian_signal(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """生成突破信号"""
    strategy = get_donchian_strategy()
    return strategy.generate_signal({'1D': df}, symbol)
