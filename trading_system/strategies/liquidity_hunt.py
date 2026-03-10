"""
市场结构 + 流动性猎杀策略
核心逻辑：价格总是去有流动性的地方，止损密集区就是猎杀目标
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime

from .base import BaseStrategy


class LiquidityHuntStrategy(BaseStrategy):
    """流动性猎杀策略"""
    
    def __init__(self):
        super().__init__(name="Liquidity Hunt", category="Market Structure")
        
        # Swing 高低点检测参数
        self.swing_lookback = 20  # 前后各看 20 根 K 线
        
        # 流动性区域阈值
        self.liquidity_threshold = 0.005  # 0.5% 以内算流动性区域
        
        # 确认 K 线数量
        self.confirmation_candles = 3
    
    def _find_swing_highs(self, df: pd.DataFrame) -> List[Tuple[int, float]]:
        """
        找出 Swing Highs（局部高点）
        返回：[(index, price), ...]
        """
        swing_highs = []
        
        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            high = df['high'].iloc[i]
            
            # 左边的高点都比它低
            left_highs = df['high'].iloc[i-self.swing_lookback:i].max()
            # 右边的高点都比它低
            right_highs = df['high'].iloc[i+1:i+self.swing_lookback+1].max()
            
            if high > left_highs and high > right_highs:
                swing_highs.append((i, high))
        
        return swing_highs
    
    def _find_swing_lows(self, df: pd.DataFrame) -> List[Tuple[int, float]]:
        """
        找出 Swing Lows（局部低点）
        返回：[(index, price), ...]
        """
        swing_lows = []
        
        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            low = df['low'].iloc[i]
            
            # 左边的低点都比它高
            left_lows = df['low'].iloc[i-self.swing_lookback:i].min()
            # 右边的低点都比它高
            right_lows = df['low'].iloc[i+1:i+self.swing_lookback+1].min()
            
            if low < left_lows and low < right_lows:
                swing_lows.append((i, low))
        
        return swing_lows
    
    def _find_recent_swing_levels(self, df: pd.DataFrame, lookback: int = 100) -> Dict:
        """
        找出最近的 Swing 高低点
        """
        swing_highs = self._find_swing_highs(df)
        swing_lows = self._find_swing_lows(df)
        
        # 只保留最近 lookback 根 K 线内的
        current_idx = len(df) - 1
        cutoff_idx = current_idx - lookback
        
        recent_highs = [(i, p) for i, p in swing_highs if i > cutoff_idx]
        recent_lows = [(i, p) for i, p in swing_lows if i > cutoff_idx]
        
        # 按价格排序
        recent_highs.sort(key=lambda x: x[1], reverse=True)
        recent_lows.sort(key=lambda x: x[1])
        
        return {
            'highs': recent_highs[:5],  # 最近的 5 个高点
            'lows': recent_lows[:5]     # 最近的 5 个低点
        }
    
    def _check_liquidity_grab(self, df: pd.DataFrame, level: float, level_type: str) -> Optional[str]:
        """
        检查是否有流动性猎杀
        
        Args:
            level: 流动性水平（高点或低点）
            level_type: 'high' 或 'low'
        
        Returns:
            'GRAB_HIGH' / 'GRAB_LOW' / None
        """
        if len(df) < self.confirmation_candles + 1:
            return None
        
        current_close = df['close'].iloc[-1]
        
        if level_type == 'high':
            # 检查是否突破高点后收回
            recent_high = df['high'].iloc[-self.confirmation_candles:].max()
            
            # 突破了高点
            if recent_high > level:
                # 但收盘价回到高点之下
                if current_close < level:
                    return 'GRAB_HIGH'  # 猎杀多头止损
        
        elif level_type == 'low':
            # 检查是否跌破低点后收回
            recent_low = df['low'].iloc[-self.confirmation_candles:].min()
            
            # 跌破了低点
            if recent_low < level:
                # 但收盘价回到低点之上
                if current_close > level:
                    return 'GRAB_LOW'  # 猎杀空头止损
        
        return None
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        分析流动性猎杀信号
        
        Returns:
            分析结果字典
        """
        result = {
            'strategy_name': self.name,
            'timestamp': datetime.now().isoformat(),
            'status': 'NO_SIGNAL'
        }
        
        if len(df) < 100:
            result['status'] = 'INSUFFICIENT_DATA'
            return result
        
        # 找出最近的 Swing 高低点
        swing_levels = self._find_recent_swing_levels(df)
        result['swing_levels'] = swing_levels
        
        current_price = df['close'].iloc[-1]
        
        # 检查每个高点是否有猎杀
        grab_signals = []
        
        for idx, high_price in swing_levels['highs']:
            grab = self._check_liquidity_grab(df, high_price, 'high')
            if grab == 'GRAB_HIGH':
                grab_signals.append({
                    'type': 'GRAB_HIGH',
                    'level': high_price,
                    'distance_pct': (high_price - current_price) / current_price * 100
                })
        
        # 检查每个低点是否有猎杀
        for idx, low_price in swing_levels['lows']:
            grab = self._check_liquidity_grab(df, low_price, 'low')
            if grab == 'GRAB_LOW':
                grab_signals.append({
                    'type': 'GRAB_LOW',
                    'level': low_price,
                    'distance_pct': (current_price - low_price) / current_price * 100
                })
        
        result['grab_signals'] = grab_signals
        
        if not grab_signals:
            return result
        
        # 有猎杀信号，生成交易信号
        # 选择最近的/最强的信号
        best_signal = max(grab_signals, key=lambda x: x['distance_pct'])
        
        if best_signal['type'] == 'GRAB_HIGH':
            # 猎杀高点 → 做空
            result['status'] = 'SIGNAL'
            result['action'] = 'SELL'
            result['direction'] = 'SHORT'
            result['signal_type'] = 'LIQUIDITY_GRAB_HIGH'
            
            # 计算置信度
            confidence = 50.0
            
            # 猎杀幅度越大，置信度越高
            distance_bonus = min(20, best_signal['distance_pct'] * 5)
            confidence += distance_bonus
            
            # 如果有多重猎杀 → 加分
            if len(grab_signals) > 1:
                confidence += 15
            
            # 检查是否是关键位置（前高/前低）
            if best_signal['level'] == swing_levels['highs'][0][1]:  # 最近的高点
                confidence += 10
            
            result['confidence'] = min(confidence, 90.0)
            
            # 生成理由
            reasons = [
                f"猎杀多头止损 @ {best_signal['level']:.2f}",
                f"价格突破后迅速收回",
            ]
            if len(grab_signals) > 1:
                reasons.append(f"多重猎杀信号 ({len(grab_signals)}个)")
            
            result['reasons'] = reasons
            
        elif best_signal['type'] == 'GRAB_LOW':
            # 猎杀低点 → 做多
            result['status'] = 'SIGNAL'
            result['action'] = 'BUY'
            result['direction'] = 'LONG'
            result['signal_type'] = 'LIQUIDITY_GRAB_LOW'
            
            # 计算置信度
            confidence = 50.0
            
            # 猎杀幅度越大，置信度越高
            distance_bonus = min(20, best_signal['distance_pct'] * 5)
            confidence += distance_bonus
            
            # 如果有多重猎杀 → 加分
            if len(grab_signals) > 1:
                confidence += 15
            
            # 检查是否是关键位置（前高/前低）
            if best_signal['level'] == swing_levels['lows'][0][1]:  # 最近的低点
                confidence += 10
            
            result['confidence'] = min(confidence, 90.0)
            
            # 生成理由
            reasons = [
                f"猎杀空头止损 @ {best_signal['level']:.2f}",
                f"价格跌破后迅速收回",
            ]
            if len(grab_signals) > 1:
                reasons.append(f"多重猎杀信号 ({len(grab_signals)}个)")
            
            result['reasons'] = reasons
        
        # 计算风险管理参数
        atr = self._calculate_atr(df)
        
        result['current_price'] = current_price
        result['entry_price'] = current_price
        
        if result['direction'] == 'LONG':
            result['stop_loss_price'] = current_price - 2.0 * atr
            result['take_profit_price'] = current_price + 3.5 * atr
        else:
            result['stop_loss_price'] = current_price + 2.0 * atr
            result['take_profit_price'] = current_price - 3.5 * atr
        
        result['stop_loss_pct'] = abs(current_price - result['stop_loss_price']) / current_price * 100
        result['take_profit_pct'] = abs(result['take_profit_price'] - current_price) / current_price * 100
        result['risk_reward_ratio'] = result['take_profit_pct'] / result['stop_loss_pct']
        
        return result
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """
        生成交易信号
        """
        analysis = self.analyze(df)
        
        if analysis['status'] != 'SIGNAL':
            return None
        
        current_price = analysis['current_price']
        swing_levels = analysis.get('swing_levels', {})
        grab_signals = analysis.get('grab_signals', [])
        best_signal = grab_signals[0] if grab_signals else None
        
        if best_signal and best_signal['type'] == 'GRAB_HIGH':
            # 做空：止损放在猎杀高点上方
            stop_loss_price = best_signal['level'] * 1.01
            stop_loss_pct = (stop_loss_price - current_price) / current_price * 100
            
            # 止盈：找下方支撑
            for low in swing_levels.get('lows', []):
                if low[1] < current_price:
                    take_profit_price = low[1]
                    break
            else:
                atr = self._calculate_atr(df)
                take_profit_price = current_price - 3.5 * atr
        else:
            # 做多：止损放在猎杀低点下方
            stop_loss_price = best_signal['level'] * 0.99 if best_signal else current_price - 2 * self._calculate_atr(df)
            stop_loss_pct = (current_price - stop_loss_price) / current_price * 100
            
            # 止盈：找上方阻力
            for high in swing_levels.get('highs', []):
                if high[1] > current_price:
                    take_profit_price = high[1]
                    break
            else:
                atr = self._calculate_atr(df)
                take_profit_price = current_price + 3.5 * atr
        
        take_profit_pct = abs(take_profit_price - current_price) / current_price * 100
        risk_reward_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 0
        
        # 确保最小 2R
        if risk_reward_ratio < 2.0:
            if analysis['direction'] == 'LONG':
                take_profit_price = current_price * (1 + stop_loss_pct * 2.5 / 100)
            else:
                take_profit_price = current_price * (1 - stop_loss_pct * 2.5 / 100)
            take_profit_pct = stop_loss_pct * 2.5
            risk_reward_ratio = 2.5
        
        # 持仓周期：猎杀反转比较快
        holding_period = {
            'min_days': 1,
            'max_days': 3,
            'expected_days': 2,
            'type': 'swing'
        }
        
        return {
            'strategy_name': analysis['strategy_name'],
            'strategy_category': self.category,
            'symbol': symbol.replace('USDT', '-USD'),
            'action': analysis['action'],
            'direction': analysis['direction'],
            'current_price': str(current_price),
            'entry_price': str(analysis['entry_price']),
            'entry_type': 'MARKET',
            'stop_loss_price': str(stop_loss_price),
            'stop_loss_pct': round(stop_loss_pct, 2),
            'take_profit_price': str(take_profit_price),
            'take_profit_pct': round(take_profit_pct, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'position_size_pct': min(20.0, analysis['confidence'] / 5),
            'confidence': analysis['confidence'],
            'reason': '；'.join(analysis['reasons']),
            'pattern': analysis.get('signal_type', 'Liquidity Hunt'),
            'timeframe': '1D',
            'timestamp': datetime.now().isoformat(),
            'swing_levels': analysis.get('swing_levels', {}),
            'grab_signals': analysis.get('grab_signals', []),
            'stop_type': 'liquidity_grab',
            'take_profit_type': 'technical',
            'holding_period': holding_period
        }


# 便捷函数
def get_liquidity_hunt_strategy() -> LiquidityHuntStrategy:
    """获取策略实例"""
    return LiquidityHuntStrategy()


def analyze_liquidity_hunt(df: pd.DataFrame) -> Dict:
    """分析流动性猎杀（便捷函数）"""
    strategy = get_liquidity_hunt_strategy()
    return strategy.analyze(df)


def generate_liquidity_hunt_signal(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """生成流动性猎杀信号（便捷函数）"""
    strategy = get_liquidity_hunt_strategy()
    return strategy.generate_signal(df, symbol)
