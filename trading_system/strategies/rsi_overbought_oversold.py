"""
RSI 超买超卖策略

核心逻辑:
- RSI < 30 → 超卖 → 做多
- RSI > 70 → 超买 → 做空
- RSI 回到 50 → 平仓

经典均值回归策略
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime

from .base import BaseStrategy


class RSIOversoldOverboughtStrategy(BaseStrategy):
    """RSI 超买超卖策略"""
    
    def __init__(self):
        super().__init__(name="RSI Overbought/Oversold", category="Mean Reversion")
        
        # RSI 参数 - 放宽
        self.rsi_period = 14
        self.oversold_threshold = 35  # RSI < 35 超卖 (从 30 放宽到 35)
        self.overbought_threshold = 65  # RSI > 65 超买 (从 70 放宽到 65)
        self.exit_threshold = 50  # RSI 回到 50 平仓
        
        # ADX 过滤 - 放宽
        self.adx_period = 14
        self.adx_max = 30  # ADX < 30 就可以 (从 25 放宽到 30)
        
        # 止损止盈
        self.stop_loss_pct = 3.0
        self.take_profit_pct = 6.0
        
        # 置信度
        self.min_confidence = 65
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算 RSI"""
        if len(df) < period + 1:
            return 50.0
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not np.isnan(rsi.iloc[-1]) else 50.0
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算 ADX"""
        if len(df) < period * 2:
            return 0.0
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        plus_dm[(plus_dm <= minus_dm) & (minus_dm > 0)] = 0
        minus_dm[(minus_dm <= plus_dm) & (plus_dm > 0)] = 0
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        ranges = pd.concat([tr1, tr2, tr3], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(period).mean()
        
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        
        return adx.iloc[-1] if not np.isnan(adx.iloc[-1]) else 0.0
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """分析 RSI 信号"""
        if len(df) < 50:
            return {'status': 'INSUFFICIENT_DATA', 'signal': 'WAIT'}
        
        current_close = df['close'].iloc[-1]
        
        # 计算 RSI 和 ADX
        rsi = self._calculate_rsi(df, self.rsi_period)
        adx = self._calculate_adx(df, self.adx_period)
        
        # ADX 过滤 - 只在震荡市使用
        if adx > self.adx_max:
            return {'status': 'NO_SIGNAL', 'signal': 'WAIT', 'reason': f'ADX {adx:.1f} > {self.adx_max} (趋势市，不适合)'}
        
        # 检查超卖 (做多)
        if rsi < self.oversold_threshold:
            confidence = min(90, 65 + (self.oversold_threshold - rsi) * 2)
            return {
                'status': 'SIGNAL',
                'signal': 'BUY',
                'rsi': rsi,
                'adx': adx,
                'current_price': current_close,
                'confidence': confidence,
                'reason': f"RSI 超卖 {rsi:.1f} (ADX:{adx:.1f} 震荡市)"
            }
        
        # 检查超买 (做空)
        if rsi > self.overbought_threshold:
            confidence = min(90, 65 + (rsi - self.overbought_threshold) * 2)
            return {
                'status': 'SIGNAL',
                'signal': 'SELL',
                'rsi': rsi,
                'adx': adx,
                'current_price': current_close,
                'confidence': confidence,
                'reason': f"RSI 超买 {rsi:.1f} (ADX:{adx:.1f} 震荡市)"
            }
        
        return {'status': 'NO_SIGNAL', 'signal': 'WAIT', 'reason': f'RSI {rsi:.1f} 中性区域'}
    
    def generate_signal(self, data_dict: Dict[str, pd.DataFrame], symbol: str) -> Optional[Dict]:
        """生成交易信号"""
        if '1D' not in data_dict and '1d' not in data_dict:
            return None
        
        df = data_dict.get('1D', data_dict.get('1d'))
        if df is None or len(df) < 50:
            return None
        
        analysis = self.analyze(df)
        
        if analysis.get('signal') == 'WAIT':
            return None
        
        current_price = analysis['current_price']
        direction = 'LONG' if analysis['signal'] == 'BUY' else 'SHORT'
        
        # 止损止盈
        if direction == 'LONG':
            stop_loss = current_price * (1 - self.stop_loss_pct / 100)
            take_profit = current_price * (1 + self.take_profit_pct / 100)
        else:
            stop_loss = current_price * (1 + self.stop_loss_pct / 100)
            take_profit = current_price * (1 - self.take_profit_pct / 100)
        
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
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_price': take_profit,
            'take_profit_pct': self.take_profit_pct,
            'risk_reward_ratio': self.take_profit_pct / self.stop_loss_pct,
            'position_size_pct': 10.0,
            'confidence': confidence,
            'reason': analysis['reason'],
            'pattern': f"RSI {analysis['rsi']:.1f}",
            'timeframe': '1D',
            'timestamp': datetime.now().isoformat()
        }


def get_rsi_strategy() -> RSIOversoldOverboughtStrategy:
    return RSIOversoldOverboughtStrategy()
