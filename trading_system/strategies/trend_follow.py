"""
简单趋势跟踪策略 - MA 交叉

核心逻辑：
- 快线上穿慢线 → 买入（金叉）
- 快线下穿慢线 → 卖出（死叉）
- 简单直接，不复杂
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime

from .base import BaseStrategy


class TrendFollowStrategy(BaseStrategy):
    """简单趋势跟踪策略"""
    
    def __init__(self):
        super().__init__(name="Trend Follow", category="Trend")
        
        # MA 配置
        self.fast_ma = 20    # 快线
        self.slow_ma = 50    # 慢线
        
        # 置信度
        self.min_confidence = 70  # 最低置信度
        
        # 止损止盈
        self.stop_loss_pct = 3.0   # 3% 止损
        self.take_profit_pct = 9.0  # 9% 止盈 (3:1 盈亏比)
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """分析趋势"""
        if len(df) < self.slow_ma:
            return {
                'status': 'INSUFFICIENT_DATA',
                'trend': 'NEUTRAL',
                'signal': 'WAIT'
            }
        
        close = df['close'].iloc[-1]
        ma_fast = df['close'].rolling(self.fast_ma).mean().iloc[-1]
        ma_slow = df['close'].rolling(self.slow_ma).mean().iloc[-1]
        
        # 判断趋势
        if close > ma_fast > ma_slow:
            trend = 'BULL'
        elif close < ma_fast < ma_slow:
            trend = 'BEAR'
        else:
            trend = 'NEUTRAL'
        
        # 判断信号
        prev_ma_fast = df['close'].rolling(self.fast_ma).mean().iloc[-2]
        prev_ma_slow = df['close'].rolling(self.slow_ma).mean().iloc[-2]
        
        # 金叉：快线上穿慢线
        if prev_ma_fast <= prev_ma_slow and ma_fast > ma_slow:
            signal = 'BUY'
        # 死叉：快线下穿慢线
        elif prev_ma_fast >= prev_ma_slow and ma_fast < ma_slow:
            signal = 'SELL'
        else:
            signal = 'WAIT'
        
        return {
            'status': 'SIGNAL' if signal != 'WAIT' else 'NO_SIGNAL',
            'trend': trend,
            'signal': signal,
            'ma_fast': ma_fast,
            'ma_slow': ma_slow,
            'close': close
        }
    
    def generate_signal(self, data_dict: Dict[str, pd.DataFrame], symbol: str) -> Optional[Dict]:
        """生成交易信号"""
        # 使用日线数据
        if '1D' not in data_dict and '1d' not in data_dict:
            return None
        
        df = data_dict.get('1D', data_dict.get('1d'))
        if df is None or len(df) < self.slow_ma:
            return None
        
        analysis = self.analyze(df)
        
        if analysis['signal'] == 'WAIT':
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
            'confidence': 75.0,
            'reason': f"MA 交叉：{self.fast_ma}上穿{self.slow_ma}" if direction == 'LONG' else f"MA 交叉：{self.fast_ma}下穿{self.slow_ma}",
            'pattern': 'MA Cross',
            'timeframe': '1D',
            'timestamp': datetime.now().isoformat()
        }


# 便捷函数
def get_trend_follow_strategy() -> TrendFollowStrategy:
    """获取策略实例"""
    return TrendFollowStrategy()


def generate_trend_follow_signal(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """生成趋势跟踪信号"""
    strategy = get_trend_follow_strategy()
    return strategy.generate_signal({'1D': df}, symbol)
