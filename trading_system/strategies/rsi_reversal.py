"""
RSI 反转策略

核心逻辑：
- RSI < 30 → 超卖 → 买入
- RSI > 70 → 超买 → 卖出
- 适合震荡市
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime

from .base import BaseStrategy


class RSIMeanReversionStrategy(BaseStrategy):
    """RSI 反转策略"""
    
    def __init__(self):
        super().__init__(name="RSI Mean Reversion", category="Mean Reversion")
        
        # RSI 配置
        self.rsi_period = 14
        self.oversold = 30    # 超卖线
        self.overbought = 70  # 超买线
        
        # 置信度
        self.min_confidence = 70  # 最低置信度
        
        # 止损止盈
        self.stop_loss_pct = 2.5   # 2.5% 止损
        self.take_profit_pct = 5.0  # 5% 止盈 (2:1 盈亏比)
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """分析 RSI"""
        if len(df) < self.rsi_period + 10:
            return {
                'status': 'INSUFFICIENT_DATA',
                'rsi': None,
                'signal': 'WAIT'
            }
        
        # 计算 RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        
        # 判断信号
        if current_rsi < self.oversold:
            signal = 'BUY'
        elif current_rsi > self.overbought:
            signal = 'SELL'
        else:
            signal = 'WAIT'
        
        return {
            'status': 'SIGNAL' if signal != 'WAIT' else 'NO_SIGNAL',
            'rsi': current_rsi,
            'signal': signal,
            'close': df['close'].iloc[-1]
        }
    
    def generate_signal(self, data_dict: Dict[str, pd.DataFrame], symbol: str) -> Optional[Dict]:
        """生成交易信号"""
        # 使用日线数据
        if '1D' not in data_dict and '1d' not in data_dict:
            return None
        
        df = data_dict.get('1D', data_dict.get('1d'))
        if df is None or len(df) < self.rsi_period + 10:
            return None
        
        analysis = self.analyze(df)
        
        if analysis['signal'] == 'WAIT' or analysis['rsi'] is None:
            return None
        
        current_price = analysis['close']
        rsi = analysis['rsi']
        direction = 'LONG' if analysis['signal'] == 'BUY' else 'SHORT'
        
        # 根据 RSI 强度调整置信度
        if direction == 'LONG':
            confidence = min(90, 50 + (self.oversold - rsi))
        else:
            confidence = min(90, 50 + (rsi - self.overbought))
        
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
            'reason': f"RSI={rsi:.1f} ({'超卖' if direction == 'LONG' else '超买'})",
            'pattern': 'RSI Reversal',
            'timeframe': '1D',
            'timestamp': datetime.now().isoformat()
        }


# 便捷函数
def get_rsi_strategy() -> RSIMeanReversionStrategy:
    """获取策略实例"""
    return RSIMeanReversionStrategy()


def generate_rsi_signal(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """生成 RSI 信号"""
    strategy = get_rsi_strategy()
    return strategy.generate_signal({'1D': df}, symbol)
