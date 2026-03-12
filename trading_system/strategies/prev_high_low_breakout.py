"""
前高前低突破策略 (Previous High/Low Breakout)

核心逻辑:
1. 价格突破前一日高点 + 成交量放大 → 做多
2. 价格跌破前一日低点 + 成交量放大 → 做空

简单直接，经典突破策略
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime

from .base import BaseStrategy


class PrevHighLowBreakoutStrategy(BaseStrategy):
    """前高前低突破策略"""
    
    def __init__(self):
        super().__init__(name="Prev High/Low Breakout", category="Breakout")
        
        # 突破参数 - 放宽
        self.volume_ratio = 1.3           # 成交量放大倍数 (从 1.8 降到 1.3)
        self.breakout_min_gain = 0.01     # 最小突破幅度 1% (从 1.5% 降到 1%)
        
        # ADX 趋势过滤 - 放宽
        self.adx_period = 14
        self.adx_min = 20                 # ADX > 20 就有趋势 (从 25 降到 20)
        
        # 止损止盈
        self.stop_loss_pct = 3.0
        self.take_profit_pct = 9.0
        
        # 置信度
        self.min_confidence = 65
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算 ADX (趋势强度)"""
        if len(df) < period * 2:
            return 0.0
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 计算 +DM 和 -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        plus_dm[(plus_dm <= minus_dm) & (minus_dm > 0)] = 0
        minus_dm[(minus_dm <= plus_dm) & (plus_dm > 0)] = 0
        
        # 计算 ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        ranges = pd.concat([tr1, tr2, tr3], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(period).mean()
        
        # 计算 +DI 和 -DI
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        # 计算 DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # 计算 ADX
        adx = dx.rolling(period).mean()
        
        return adx.iloc[-1] if not np.isnan(adx.iloc[-1]) else 0.0
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """分析前高前低突破"""
        if len(df) < 50:
            return {'status': 'INSUFFICIENT_DATA', 'signal': 'WAIT'}
        
        current_close = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        current_volume = df['volume'].iloc[-1]
        
        # 前一日高低点
        prev_high = df['high'].iloc[-2]
        prev_low = df['low'].iloc[-2]
        
        # 平均成交量
        avg_volume = df['volume'].iloc[-20:-1].mean()
        
        # 计算 ADX
        adx = self._calculate_adx(df, self.adx_period)
        
        # 检查向上突破
        if current_high > prev_high * (1 + self.breakout_min_gain):
            if current_volume > avg_volume * self.volume_ratio:
                # ADX 过滤 - 只在有趋势时交易
                if adx < self.adx_min:
                    return {'status': 'NO_SIGNAL', 'signal': 'WAIT', 'reason': f'ADX {adx:.1f} < {self.adx_min} (无趋势)'}
                
                # 成交量确认
                confidence = min(95, 65 + (current_volume / avg_volume - 1) * 20 + (adx - self.adx_min) * 2)
                return {
                    'status': 'SIGNAL',
                    'signal': 'BUY',
                    'breakout_type': 'PREV_HIGH',
                    'breakout_level': prev_high,
                    'current_price': current_close,
                    'adx': adx,
                    'confidence': confidence,
                    'reason': f"突破前高 {prev_high:,.2f} (ADX:{adx:.1f}, 成交量：{current_volume/avg_volume:.1f}x)"
                }
        
        # 检查向下突破
        if current_low < prev_low * (1 - self.breakout_min_gain):
            if current_volume > avg_volume * self.volume_ratio:
                # ADX 过滤
                if adx < self.adx_min:
                    return {'status': 'NO_SIGNAL', 'signal': 'WAIT', 'reason': f'ADX {adx:.1f} < {self.adx_min} (无趋势)'}
                
                # 成交量确认
                confidence = min(95, 65 + (current_volume / avg_volume - 1) * 20 + (adx - self.adx_min) * 2)
                return {
                    'status': 'SIGNAL',
                    'signal': 'SELL',
                    'breakout_type': 'PREV_LOW',
                    'breakout_level': prev_low,
                    'current_price': current_close,
                    'adx': adx,
                    'confidence': confidence,
                    'reason': f"跌破前低 {prev_low:,.2f} (ADX:{adx:.1f}, 成交量：{current_volume/avg_volume:.1f}x)"
                }
        
        return {'status': 'NO_SIGNAL', 'signal': 'WAIT', 'reason': '无突破'}
    
    def generate_signal(self, data_dict: Dict[str, pd.DataFrame], symbol: str) -> Optional[Dict]:
        """生成交易信号"""
        if '1D' not in data_dict and '1d' not in data_dict:
            return None
        
        df = data_dict.get('1D', data_dict.get('1d'))
        if df is None or len(df) < 30:
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
        
        confidence = analysis.get('confidence', 65)
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
            'pattern': analysis['breakout_type'],
            'timeframe': '1D',
            'timestamp': datetime.now().isoformat()
        }


def get_prev_high_low_strategy() -> PrevHighLowBreakoutStrategy:
    return PrevHighLowBreakoutStrategy()
