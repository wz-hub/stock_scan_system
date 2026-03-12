"""
波动率收缩突破策略
核心逻辑：波动率收缩到极点后，突破力度很大
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime

from .base import BaseStrategy


class VolatilitySqueezeStrategy(BaseStrategy):
    """波动率收缩突破策略"""
    
    def __init__(self):
        super().__init__(name="Volatility Squeeze Breakout", category="Volatility")
        
        # 布林带参数
        self.bb_period = 20
        self.bb_std = 2.0
        
        # 波动率收缩阈值
        self.squeeze_lookback = 100
        self.squeeze_percentile = 0.10  # 带宽处于历史 10% 分位以下（更严格）
        
        # 突破确认
        self.volume_multiplier = 2.0  # 成交量需要放大 2 倍（从 1.5 提高）
        self.volume_lookback = 20
        
        # 多周期过滤（新增）
        self.require_uptrend_for_long = True  # 只做多上涨趋势
    
    def _calculate_bollinger(self, df: pd.DataFrame) -> Dict:
        """计算布林带"""
        close = df['close']
        
        # 中轨
        middle = close.rolling(self.bb_period).mean()
        
        # 标准差
        std = close.rolling(self.bb_period).std()
        
        # 上下轨
        upper = middle + self.bb_std * std
        lower = middle - self.bb_std * std
        
        # 带宽
        width = (upper - lower) / middle
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'width': width,
            'std': std
        }
    
    def _is_squeeze(self, df: pd.DataFrame, bb: Dict) -> bool:
        """
        判断是否处于波动率收缩状态
        """
        if len(df) < self.squeeze_lookback:
            return False
        
        current_width = bb['width'].iloc[-1]
        
        # 计算历史带宽分位
        historical_widths = bb['width'].iloc[-self.squeeze_lookback:-1]
        percentile = historical_widths.quantile(self.squeeze_percentile)
        
        return current_width < percentile
    
    def _check_breakout(self, df: pd.DataFrame, bb: Dict) -> Optional[str]:
        """
        检查是否有突破信号
        返回：'LONG' / 'SHORT' / None
        """
        current_close = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        upper = bb['upper'].iloc[-1]
        lower = bb['lower'].iloc[-1]
        
        # 向上突破
        if current_high > upper:
            # 确认收盘价也在上轨之上（更强信号）
            if current_close > upper:
                return 'LONG'
            # 或者虽然回落但仍在中轨之上
            elif current_close > bb['middle'].iloc[-1]:
                return 'LONG'
        
        # 向下突破
        if current_low < lower:
            # 确认收盘价也在下轨之下（更强信号）
            if current_close < lower:
                return 'SHORT'
            # 或者虽然反弹但仍在中轨之下
            elif current_close < bb['middle'].iloc[-1]:
                return 'SHORT'
        
        return None
    
    def _check_volume(self, df: pd.DataFrame) -> tuple:
        """
        检查成交量是否确认突破
        返回：(是否确认，成交量比率)
        """
        if 'volume' not in df.columns:
            return True, 1.0  # 没有成交量数据，默认确认
        
        current_vol = df['volume'].iloc[-1]
        avg_vol = df['volume'].rolling(self.volume_lookback).mean().iloc[-1]
        
        if pd.isna(avg_vol) or avg_vol == 0:
            return True, 1.0
        
        volume_ratio = current_vol / avg_vol
        
        # 成交量放大确认突破
        confirmed = volume_ratio >= self.volume_multiplier
        
        return confirmed, volume_ratio
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        分析波动率收缩突破信号
        
        Returns:
            分析结果字典
        """
        result = {
            'strategy_name': self.name,
            'timestamp': datetime.now().isoformat(),
            'status': 'NO_SIGNAL'
        }
        
        if len(df) < self.squeeze_lookback:
            result['status'] = 'INSUFFICIENT_DATA'
            return result
        
        # 计算布林带
        bb = self._calculate_bollinger(df)
        
        # 判断是否收缩
        squeeze = self._is_squeeze(df, bb)
        result['is_squeeze'] = squeeze
        
        if not squeeze:
            result['status'] = 'NO_SQUEEZE'
            result['current_width'] = bb['width'].iloc[-1]
            result['width_percentile'] = self._get_width_percentile(bb)
            return result
        
        # 检查突破
        breakout = self._check_breakout(df, bb)
        result['breakout_direction'] = breakout
        
        if breakout is None:
            result['status'] = 'SQUEEZE_NO_BREAKOUT'
            return result
        
        # 多周期过滤（新增）- 只做多上涨趋势
        trend = self._check_trend(df)
        result['trend'] = trend
        
        if self.require_uptrend_for_long and breakout == 'LONG' and trend != 'BULL':
            result['status'] = 'FILTERED_BY_TREND'
            return result
        
        # 检查成交量确认
        volume_confirmed, volume_ratio = self._check_volume(df)
        result['volume_confirmed'] = volume_confirmed
        result['volume_ratio'] = volume_ratio
        
        # 计算信号强度
        confidence = 50.0
        
        # 收盘价确认突破 → +15 分
        if breakout == 'LONG' and df['close'].iloc[-1] > bb['upper'].iloc[-1]:
            confidence += 15
        elif breakout == 'SHORT' and df['close'].iloc[-1] < bb['lower'].iloc[-1]:
            confidence += 15
        
        # 成交量确认 → +15 分
        if volume_confirmed:
            confidence += 15
            if volume_ratio >= 2.0:
                confidence += 10  # 成交量放大 2 倍以上额外加分
        
        # 带宽收缩越厉害，突破力度越大 → 最多加 20 分
        width_percentile = self._get_width_percentile(bb)
        squeeze_bonus = (0.15 - width_percentile) / 0.15 * 20
        confidence += max(0, squeeze_bonus)
        
        result['confidence'] = min(confidence, 100.0)
        result['status'] = 'SIGNAL'
        
        # 生成交易信号
        current_price = df['close'].iloc[-1]
        
        # 用 ATR 计算止损止盈
        atr = self._calculate_atr(df)
        
        if breakout == 'LONG':
            stop_loss = current_price - 2.5 * atr
            take_profit = current_price + 4.0 * atr
            result['action'] = 'BUY'
            result['direction'] = 'LONG'
        else:
            stop_loss = current_price + 2.5 * atr
            take_profit = current_price - 4.0 * atr
            result['action'] = 'SELL'
            result['direction'] = 'SHORT'
        
        result['current_price'] = current_price
        result['entry_price'] = current_price
        result['stop_loss_price'] = stop_loss
        result['take_profit_price'] = take_profit
        result['stop_loss_pct'] = abs(current_price - stop_loss) / current_price * 100
        result['take_profit_pct'] = abs(take_profit - current_price) / current_price * 100
        result['risk_reward_ratio'] = result['take_profit_pct'] / result['stop_loss_pct']
        
        # 生成理由
        reasons = [
            f"波动率收缩至{width_percentile*100:.1f}%分位",
            f"{'向上' if breakout == 'LONG' else '向下'}突破布林带",
        ]
        if volume_confirmed:
            reasons.append(f"成交量放大{volume_ratio:.1f}倍确认")
        else:
            reasons.append(f"成交量未确认 (仅{volume_ratio:.1f}倍)")
        
        result['reasons'] = reasons
        
        return result
    
    def _get_width_percentile(self, bb: Dict) -> float:
        """获取当前带宽的历史分位"""
        current_width = bb['width'].iloc[-1]
        historical_widths = bb['width'].iloc[-self.squeeze_lookback:-1]
        
        if len(historical_widths) == 0:
            return 0.5
        
        return (historical_widths < current_width).sum() / len(historical_widths)
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """
        生成交易信号
        
        Args:
            df: K 线数据
            symbol: 交易标的
        
        Returns:
            信号字典或 None
        """
        analysis = self.analyze(df)
        
        if analysis['status'] != 'SIGNAL':
            return None
        
        return {
            'strategy_name': analysis['strategy_name'],
            'strategy_category': self.category,
            'symbol': symbol.replace('USDT', '-USD'),
            'action': analysis['action'],
            'direction': analysis['direction'],
            'current_price': str(analysis['current_price']),
            'entry_price': analysis['entry_price'],
            'entry_type': 'MARKET',
            'stop_loss_price': analysis['stop_loss_price'],
            'stop_loss_pct': analysis['stop_loss_pct'],
            'take_profit_price': analysis['take_profit_price'],
            'take_profit_pct': analysis['take_profit_pct'],
            'risk_reward_ratio': analysis['risk_reward_ratio'],
            'position_size_pct': min(20.0, analysis['confidence'] / 5),
            'confidence': analysis['confidence'],
            'reason': '；'.join(analysis['reasons']),
            'pattern': 'Volatility Squeeze Breakout',
            'timeframe': '1D',
            'timestamp': datetime.now().isoformat(),
            'volume_ratio': analysis.get('volume_ratio', 1.0),
            'volume_confirmed': analysis.get('volume_confirmed', False)
        }


# 便捷函数
def get_volatility_squeeze_strategy() -> VolatilitySqueezeStrategy:
    """获取策略实例"""
    return VolatilitySqueezeStrategy()


def analyze_volatility_squeeze(df: pd.DataFrame) -> Dict:
    """分析波动率收缩（便捷函数）"""
    strategy = get_volatility_squeeze_strategy()
    return strategy.analyze(df)


def generate_volatility_squeeze_signal(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """生成波动率收缩信号（便捷函数）"""
    strategy = get_volatility_squeeze_strategy()
    return strategy.generate_signal(df, symbol)
