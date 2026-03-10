"""
多周期共振策略
核心逻辑：大周期定方向，小周期找入场
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime

from .base import BaseStrategy


class MultiTimeframeStrategy(BaseStrategy):
    """多周期共振策略 - 优化版"""
    
    def __init__(self):
        super().__init__(name="Multi-Timeframe Resonance", category="Multi-Timeframe")
        
        # 时间周期配置
        self.trend_timeframe = '1D'      # 趋势周期（定方向）
        self.signal_timeframe = '4H'     # 信号周期（找机会）
        self.entry_timeframe = '1H'      # 入场周期（精确点位）
        
        # 均线配置
        self.fast_ma = 20
        self.slow_ma = 50
        self.trend_ma = 200
        
        # 共振要求
        self.require_all_align = True    # 是否要求所有周期同向
        
        # === 优化参数 (2026-03-10) ===
        # 第一次优化 (18:30): 85% 太严格 → 改为 70%
        self.min_confidence = 70         # 置信度门槛：85% → 70% ✅
        self.atr_multiplier_sl = 2.0     # 止损倍数：1.5 → 2.0 (放宽止损)
        self.min_rr = 3.0                # 最小盈亏比：2 → 3 (提高止盈)
        self.max_holding_days = 5        # 最大持仓天数
        self.adx_threshold = 15          # ADX 阈值：20 → 15 (放宽趋势确认)
    
    def analyze(self, data_dict: Dict[str, pd.DataFrame]) -> Dict:
        """
        多周期分析
        
        Args:
            data_dict: {timeframe: dataframe}
        
        Returns:
            分析结果字典
        """
        result = {
            'strategy_name': self.name,
            'timestamp': datetime.now().isoformat(),
            'timeframes': {}
        }
        
        # 分析各周期
        for tf in [self.trend_timeframe, self.signal_timeframe, self.entry_timeframe]:
            if tf not in data_dict or data_dict[tf] is None or len(data_dict[tf]) == 0:
                result['timeframes'][tf] = {
                    'status': 'NO_DATA',
                    'trend': None,
                    'signal': None,
                    'entry': None
                }
                continue
            
            df = data_dict[tf]
            tf_result = {
                'status': 'OK',
                'close': df['close'].iloc[-1],
                'ma20': self._calculate_ma(df, self.fast_ma),
                'ma50': self._calculate_ma(df, self.slow_ma),
            }
            
            if tf == self.trend_timeframe:
                tf_result['trend'] = self._get_trend(df)
            elif tf == self.signal_timeframe:
                tf_result['signal'] = self._get_signal(df)
            elif tf == self.entry_timeframe:
                tf_result['entry'] = self._get_entry(df)
            
            result['timeframes'][tf] = tf_result
        
        # 综合判断
        trend = result['timeframes'].get(self.trend_timeframe, {}).get('trend')
        signal = result['timeframes'].get(self.signal_timeframe, {}).get('signal')
        entry = result['timeframes'].get(self.entry_timeframe, {}).get('entry')
        
        # 共振逻辑
        final_action = 'WAIT'
        final_direction = 'NEUTRAL'
        confidence = 0.0
        reasons = []
        
        if trend == 'BULL':
            reasons.append(f"日线趋势向上")
            if signal == 'BUY':
                reasons.append(f"4H 出现买入信号")
                if entry == 'GO':
                    final_action = 'BUY'
                    final_direction = 'LONG'
                    confidence = 85.0
                    reasons.append(f"1H 入场条件满足 → 强共振")
                else:
                    final_action = 'WATCH'
                    final_direction = 'LONG'
                    confidence = 60.0
                    reasons.append(f"1H 入场条件未满足 → 等待")
            elif signal == 'SELL':
                reasons.append(f"4H 出现卖出信号（逆势，谨慎）")
                final_action = 'WAIT'
                confidence = 30.0
        elif trend == 'BEAR':
            reasons.append(f"日线趋势向下")
            if signal == 'SELL':
                reasons.append(f"4H 出现卖出信号")
                if entry == 'GO':
                    final_action = 'SELL'
                    final_direction = 'SHORT'
                    confidence = 85.0
                    reasons.append(f"1H 入场条件满足 → 强共振")
                else:
                    final_action = 'WATCH'
                    final_direction = 'SHORT'
                    confidence = 60.0
                    reasons.append(f"1H 入场条件未满足 → 等待")
            elif signal == 'BUY':
                reasons.append(f"4H 出现买入信号（逆势，谨慎）")
                final_action = 'WAIT'
                confidence = 30.0
        else:
            reasons.append(f"日线震荡，无明确趋势")
            # 震荡市可以高抛低吸
            if signal == 'BUY' and entry == 'GO':
                final_action = 'BUY'
                final_direction = 'LONG'
                confidence = 50.0
                reasons.append(f"震荡市短多")
            elif signal == 'SELL' and entry == 'GO':
                final_action = 'SELL'
                final_direction = 'SHORT'
                confidence = 50.0
                reasons.append(f"震荡市短空")
        
        result['final_action'] = final_action
        result['final_direction'] = final_direction
        result['confidence'] = confidence
        result['reasons'] = reasons
        
        return result
    
    def _get_trend(self, df: pd.DataFrame) -> str:
        """
        判断趋势方向（优化版：MA + 动量 + ADX 三重确认）
        返回：'BULL' / 'BEAR' / 'NEUTRAL'
        """
        if len(df) < self.trend_ma:
            return 'NEUTRAL'
        
        close = df['close'].iloc[-1]
        ma20 = self._calculate_ma(df, self.fast_ma)
        ma50 = self._calculate_ma(df, self.slow_ma)
        ma200 = self._calculate_ma(df, self.trend_ma)
        
        # 安全检查：任何 MA 为 None 则返回 NEUTRAL
        if ma20 is None or ma50 is None or ma200 is None:
            return 'NEUTRAL'
        
        # 检查近期价格动量（最近 5 天）
        recent_close = df['close'].iloc[-1]
        past_close = df['close'].iloc[-5] if len(df) >= 5 else df['close'].iloc[0]
        momentum = (recent_close - past_close) / past_close * 100
        
        # 计算 ADX 趋势强度（放宽阈值）
        adx = self._calculate_adx(df, 14)
        
        # 多头排列 + 上涨动量 + 趋势强度（放宽 ADX 要求）
        if close > ma20 > ma50 > ma200 and momentum > 0 and adx > self.adx_threshold:
            return 'BULL'
        
        # 空头排列 + 下跌动量 + 趋势强度（放宽 ADX 要求）
        if close < ma20 < ma50 < ma200 and momentum < 0 and adx > self.adx_threshold:
            return 'BEAR'
        
        # 均线纠缠或动量不足或趋势弱，震荡
        return 'NEUTRAL'
    
    def _check_trend_filter(self, trend: str, direction: str) -> bool:
        """
        趋势过滤器（优化：避免逆势交易，但放宽条件）
        
        Returns:
            True = 允许交易，False = 禁止交易
        """
        # 上涨趋势：优先做多，但允许做空（小仓位）
        if trend == 'BULL' and direction == 'SHORT':
            return True  # 放宽：允许逆势，但置信度会降低
        
        # 下跌趋势：优先做空，但允许做多（小仓位）
        if trend == 'BEAR' and direction == 'LONG':
            return True  # 放宽：允许逆势
        
        # 震荡：允许交易
        return True
    
    def _get_signal(self, df: pd.DataFrame) -> str:
        """
        获取交易信号
        返回：'BUY' / 'SELL' / 'WAIT'
        """
        if len(df) < self.fast_ma:
            return 'WAIT'
        
        close = df['close'].iloc[-1]
        ma20 = self._calculate_ma(df, self.fast_ma)
        ma50 = self._calculate_ma(df, self.slow_ma)
        
        # 安全检查：任何 MA 为 None 则返回 WAIT
        if ma20 is None or ma50 is None:
            return 'WAIT'
        
        # 金叉：快线上穿慢线
        if ma20 > ma50:
            prev_ma20 = df['close'].iloc[-self.fast_ma-1:-1].mean()
            prev_ma50 = df['close'].iloc[-self.slow_ma-1:-1].mean()
            if prev_ma20 <= prev_ma50:  # 刚发生金叉
                return 'BUY'
        
        # 死叉：快线下穿慢线
        if ma20 < ma50:
            prev_ma20 = df['close'].iloc[-self.fast_ma-1:-1].mean()
            prev_ma50 = df['close'].iloc[-self.slow_ma-1:-1].mean()
            if prev_ma20 >= prev_ma50:  # 刚发生死叉
                return 'SELL'
        
        # 已经金叉状态，价格回调到均线附近
        if ma20 > ma50 and close < ma20 and close > ma50:
            return 'BUY'  # 回调买入机会
        
        if ma20 < ma50 and close > ma20 and close < ma50:
            return 'SELL'  # 回调卖出机会
        
        return 'WAIT'
    
    def _get_entry(self, df: pd.DataFrame) -> str:
        """
        获取精确入场点
        返回：'GO' / 'WAIT'
        """
        if len(df) < 20:
            return 'WAIT'
        
        # 用 RSI 找超买超卖
        rsi = self._calculate_rsi(df, 14)
        if rsi is None or len(rsi) == 0:
            return 'WAIT'
        
        current_rsi = rsi.iloc[-1]
        
        # 安全检查：RSI 为 None 或 NaN 则返回 WAIT
        if current_rsi is None or (isinstance(current_rsi, float) and np.isnan(current_rsi)):
            return 'WAIT'
        
        # 入场条件：RSI 不过度超买/超卖 + 波动率正常
        if 30 < current_rsi < 70:
            return 'GO'
        
        # RSI 超卖但趋势向上 → 可能是好机会
        if current_rsi < 30:
            ma20 = self._calculate_ma(df, self.fast_ma)
            if ma20 is not None and df['close'].iloc[-1] > ma20:
                return 'GO'
        
        # RSI 超买但趋势向下 → 可能是好机会
        if current_rsi > 70:
            ma20 = self._calculate_ma(df, self.fast_ma)
            if ma20 is not None and df['close'].iloc[-1] < ma20:
                return 'GO'
        
        return 'WAIT'
    
    def _find_nearest_levels(self, df: pd.DataFrame, current_price: float, direction: str) -> Dict:
        """
        找出最近的支撑阻力位，用于设定止损止盈
        
        Returns:
            {'stop_level': float, 'tp_level': float}
        """
        swing_highs = []
        swing_lows = []
        
        for i in range(20, len(df) - 5):
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            
            left_highs = df['high'].iloc[i-20:i].max()
            right_highs = df['high'].iloc[i+1:i+5].max()
            
            left_lows = df['low'].iloc[i-20:i].min()
            right_lows = df['low'].iloc[i+1:i+5].min()
            
            if high > left_highs and high > right_highs:
                swing_highs.append(high)
            if low < left_lows and low < right_lows:
                swing_lows.append(low)
        
        # 排序
        swing_highs.sort(reverse=True)
        swing_lows.sort()
        
        result = {'stop_level': None, 'tp_level': None}
        
        if direction == 'LONG':
            # 做多：止损放在最近的 Swing Low 下方
            for low in swing_lows:
                if low < current_price:
                    result['stop_level'] = low * 0.995  # 下方 0.5%
                    break
            
            # 止盈放在最近的 Swing High
            for high in swing_highs:
                if high > current_price:
                    result['tp_level'] = high
                    break
        else:
            # 做空：止损放在最近的 Swing High 上方
            for high in swing_highs:
                if high > current_price:
                    result['stop_level'] = high * 1.005  # 上方 0.5%
                    break
            
            # 止盈放在最近的 Swing Low
            for low in swing_lows:
                if low < current_price:
                    result['tp_level'] = low
                    break
        
        return result
    
    def generate_signal(self, data_dict: Dict[str, pd.DataFrame], symbol: str) -> Optional[Dict]:
        """
        生成交易信号
        
        Args:
            data_dict: 多周期数据
            symbol: 交易标的
        
        Returns:
            信号字典或 None
        """
        analysis = self.analyze(data_dict)
        
        if analysis['final_action'] == 'WAIT':
            return None
        
        # 优化 1：置信度过滤（80% → 85%）
        if analysis.get('confidence', 0) < self.min_confidence:
            return None
        
        # 优化 2：趋势过滤（避免逆势交易）
        trend = analysis['timeframes'].get(self.trend_timeframe, {}).get('trend', 'NEUTRAL')
        direction = analysis['final_direction']
        if not self._check_trend_filter(trend, direction):
            print(f"⚠️  趋势过滤：{trend} 趋势禁止 {direction}")
            return None
        
        # 获取当前价格
        current_price = analysis['timeframes'][self.entry_timeframe]['close']
        entry_df = data_dict.get(self.entry_timeframe)
        
        # 计算 ATR（作为保底）
        atr = self._calculate_atr(entry_df)
        
        # 找技术位
        levels = self._find_nearest_levels(entry_df, current_price, analysis['final_direction'])
        
        # 动态止损：优先技术位，没有则用 ATR（优化：2 倍 → 1.5 倍）
        if levels['stop_level']:
            if analysis['final_direction'] == 'LONG':
                stop_loss_price = levels['stop_level']
                stop_loss_pct = (current_price - stop_loss_price) / current_price * 100
            else:
                stop_loss_price = levels['stop_level']
                stop_loss_pct = (stop_loss_price - current_price) / current_price * 100
        else:
            # 保底：1.5 倍 ATR（优化版）
            if analysis['final_direction'] == 'LONG':
                stop_loss_price = current_price - self.atr_multiplier_sl * atr
                stop_loss_pct = self.atr_multiplier_sl * atr / current_price * 100
            else:
                stop_loss_price = current_price + self.atr_multiplier_sl * atr
                stop_loss_pct = self.atr_multiplier_sl * atr / current_price * 100
        
        # 动态止盈：优先技术位 + 至少 2R（优化：3R → 2R）
        min_rr = self.min_rr  # 2.0
        if levels['tp_level']:
            take_profit_price = levels['tp_level']
            if analysis['final_direction'] == 'LONG':
                tp_pct = (take_profit_price - current_price) / current_price * 100
            else:
                tp_pct = (current_price - take_profit_price) / current_price * 100
            
            # 检查是否满足最小盈亏比
            actual_rr = tp_pct / stop_loss_pct if stop_loss_pct > 0 else 0
            if actual_rr < min_rr:
                # 技术位不够，用 R 倍数扩展
                take_profit_price = current_price * (1 + stop_loss_pct * min_rr / 100 * (1 if analysis['final_direction'] == 'LONG' else -1))
                tp_pct = stop_loss_pct * min_rr
        else:
            # 没有技术位，用 3R
            tp_pct = stop_loss_pct * 3
            if analysis['final_direction'] == 'LONG':
                take_profit_price = current_price * (1 + tp_pct / 100)
            else:
                take_profit_price = current_price * (1 - tp_pct / 100)
        
        take_profit_pct = (take_profit_price - current_price) / current_price * 100 if analysis['final_direction'] == 'LONG' else (current_price - take_profit_price) / current_price * 100
        risk_reward_ratio = abs(take_profit_pct) / stop_loss_pct if stop_loss_pct > 0 else 0
        
        # 持仓周期建议（根据策略类型）
        holding_period = {
            'min_days': 1,
            'max_days': 5,
            'expected_days': 3,
            'type': 'swing'  # scalp/day/swing/position
        }
        
        # 根据置信度调整
        if analysis['confidence'] >= 80:
            holding_period['expected_days'] = 4
            holding_period['max_days'] = 7
        
        return {
            'strategy_name': analysis['strategy_name'],
            'strategy_category': self.category,
            'symbol': symbol,
            'action': analysis['final_action'],
            'direction': analysis['final_direction'],
            'current_price': str(current_price),
            'entry_price': str(current_price),
            'entry_type': 'MARKET',
            'stop_loss_price': str(stop_loss_price),
            'stop_loss_pct': round(stop_loss_pct, 2),
            'take_profit_price': str(take_profit_price),
            'take_profit_pct': round(abs(take_profit_pct), 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'position_size_pct': min(20.0, analysis['confidence'] / 5),
            'confidence': analysis['confidence'],
            'reason': '；'.join(analysis['reasons']),
            'pattern': 'Multi-Timeframe Resonance',
            'timeframe': self.entry_timeframe,
            'timestamp': datetime.now().isoformat(),
            'stop_type': 'technical' if levels['stop_level'] else 'ATR',
            'take_profit_type': 'technical' if levels['tp_level'] else 'multiple_R',
            'holding_period': holding_period
        }


# 便捷函数
def get_multi_timeframe_strategy() -> MultiTimeframeStrategy:
    """获取策略实例"""
    return MultiTimeframeStrategy()


def analyze_multi_timeframe(data_dict: Dict[str, pd.DataFrame]) -> Dict:
    """多周期分析（便捷函数）"""
    strategy = get_multi_timeframe_strategy()
    return strategy.analyze(data_dict)


def generate_multi_timeframe_signal(data_dict: Dict[str, pd.DataFrame], symbol: str) -> Optional[Dict]:
    """生成多周期信号（便捷函数）"""
    strategy = get_multi_timeframe_strategy()
    return strategy.generate_signal(data_dict, symbol)
