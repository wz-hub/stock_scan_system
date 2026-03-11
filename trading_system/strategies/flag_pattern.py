"""
旗形形态策略 (Flag Pattern)

核心逻辑：
- 牛市旗 (Bull Flag): 急涨 + 向下倾斜整理 + 突破上轨 → 做多
- 熊市旗 (Bear Flag): 急跌 + 向上倾斜整理 + 突破下轨 → 做空

形态识别：
1. 旗杆：5-10 根 K 线的强劲走势 (>5%)
2. 旗面：5-20 根 K 线的反向整理 (<3%)
3. 突破：突破旗面边界
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime

from .base import BaseStrategy


class FlagPatternStrategy(BaseStrategy):
    """旗形形态策略"""
    
    def __init__(self):
        super().__init__(name="Flag Pattern", category="Pattern")
        
        # 旗杆参数
        self.pole_min_bars = 5       # 旗杆最少 K 线数
        self.pole_max_bars = 12      # 旗杆最多 K 线数
        self.pole_min_change = 4.0   # 旗杆最小涨幅/跌幅 (%)
        
        # 旗面参数
        self.flag_min_bars = 5       # 旗面最少 K 线数
        self.flag_max_bars = 20      # 旗面最多 K 线数
        self.flag_max_retrace = 61.8 # 旗面最大回撤 (%) - 斐波那契 0.618
        self.flag_max_advance = 50.0 # 旗面最大反弹 (%)
        
        # 突破确认
        self.breakout_confirm_bars = 1  # 突破确认 K 线数
        
        # 止损止盈
        self.stop_loss_pct = 3.0    # 3% 止损
        self.take_profit_pct = 9.0  # 9% 止盈 (3:1 盈亏比)
        
        # 置信度
        self.min_confidence = 65
    
    def _find_pole(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        寻找旗杆
        
        Returns:
            {'start_idx': int, 'end_idx': int, 'change_pct': float, 'direction': str}
            或 None
        """
        if len(df) < self.pole_min_bars + self.flag_min_bars:
            return None
        
        # 从后往前找最近的强劲走势
        for pole_end in range(len(df) - self.flag_min_bars - 1, self.pole_min_bars - 1, -1):
            for pole_start in range(pole_end - self.pole_max_bars, pole_end - self.pole_min_bars + 1):
                if pole_start < 0:
                    continue
                
                start_price = df['close'].iloc[pole_start]
                end_price = df['close'].iloc[pole_end]
                change_pct = (end_price - start_price) / start_price * 100
                
                # 检查是否满足旗杆条件
                if abs(change_pct) >= self.pole_min_change:
                    # 检查旗杆期间的走势是否相对平稳（没有大幅回调）
                    pole_df = df.iloc[pole_start:pole_end + 1]
                    if change_pct > 0:
                        # 牛市旗杆：期间最低点不能低于起点的太多
                        min_price = pole_df['low'].min()
                        max_retrace = (start_price - min_price) / start_price * 100
                        if max_retrace > 20:  # 旗杆期间回撤不能超过 20%
                            continue
                    else:
                        # 熊市旗杆：期间最高点不能高于起点的太多
                        max_price = pole_df['high'].max()
                        max_advance = (max_price - start_price) / start_price * 100
                        if max_advance > 20:  # 旗杆期间反弹不能超过 20%
                            continue
                    
                    direction = 'BULL' if change_pct > 0 else 'BEAR'
                    return {
                        'start_idx': pole_start,
                        'end_idx': pole_end,
                        'change_pct': abs(change_pct),
                        'direction': direction,
                        'start_price': start_price,
                        'end_price': end_price
                    }
        
        return None
    
    def _find_flag(self, df: pd.DataFrame, pole: Dict) -> Optional[Dict]:
        """
        寻找旗面（整理区间）
        
        Args:
            df: K 线数据
            pole: 旗杆信息
        
        Returns:
            {'start_idx': int, 'end_idx': int, 'retrace_pct': float, 'trend': str}
            或 None
        """
        pole_end = pole['end_idx']
        flag_start = pole_end + 1
        
        if flag_start >= len(df) - self.flag_min_bars + 1:
            return None
        
        # 从旗杆结束后开始找整理区间
        for flag_end in range(flag_start + self.flag_min_bars - 1, 
                             min(flag_start + self.flag_max_bars, len(df))):
            flag_df = df.iloc[flag_start:flag_end + 1]
            
            flag_high = flag_df['high'].max()
            flag_low = flag_df['low'].min()
            flag_open = df['open'].iloc[flag_start]
            flag_close = df['close'].iloc[flag_end]
            
            # 计算旗面相对于旗杆的幅度
            if pole['direction'] == 'BULL':
                # 牛市旗：旗面应该向下倾斜（回调）
                retrace_pct = (pole['end_price'] - flag_low) / pole['end_price'] * 100
                advance_pct = (flag_high - pole['end_price']) / pole['end_price'] * 100
                
                # 旗面不能超过旗杆的 61.8% 回撤，也不能反弹太多
                if retrace_pct > self.flag_max_retrace:
                    continue
                if advance_pct > 10:  # 放宽反弹限制
                    continue
                
                flag_trend = 'DOWN'
            else:
                # 熊市旗：旗面应该向上倾斜（反弹）
                advance_pct = (flag_high - pole['end_price']) / abs(pole['end_price']) * 100
                retrace_pct = (pole['end_price'] - flag_low) / abs(pole['end_price']) * 100
                
                # 旗面不能超过旗杆的 61.8% 反弹，也不能回撤太多
                if advance_pct > self.flag_max_retrace:
                    continue
                if abs(retrace_pct) > 10:  # 放宽回撤限制
                    continue
                
                flag_trend = 'UP'
            
            # 检查旗面是否形成通道（高低点逐渐收敛）
            # 放宽波动限制
            flag_range = (flag_high - flag_low) / flag_open * 100
            if flag_range > 8:  # 放宽到 8%
                continue
            
            return {
                'start_idx': flag_start,
                'end_idx': flag_end,
                'retrace_pct': retrace_pct if pole['direction'] == 'BULL' else advance_pct,
                'trend': flag_trend,
                'high': flag_high,
                'low': flag_low,
                'open': flag_open,
                'close': flag_close
            }
        
        return None
    
    def _check_breakout(self, df: pd.DataFrame, pole: Dict, flag: Dict) -> Optional[Dict]:
        """
        检查是否突破
        
        Args:
            df: K 线数据
            pole: 旗杆信息
            flag: 旗面信息
        
        Returns:
            突破信息或 None
        """
        if len(df) <= flag['end_idx']:
            return None
        
        # 获取突破 K 线（旗面结束后的 K 线）
        breakout_idx = flag['end_idx'] + 1
        if breakout_idx >= len(df):
            return None
        
        breakout_k = df.iloc[breakout_idx]
        current_k = df.iloc[-1]
        
        if pole['direction'] == 'BULL':
            # 牛市旗：突破旗面高点
            breakout_level = flag['high']
            if current_k['high'] > breakout_level:
                breakout_strength = (current_k['high'] - breakout_level) / breakout_level * 100
                return {
                    'type': 'BULLISH',
                    'level': breakout_level,
                    'strength': breakout_strength,
                    'confirmed': True
                }
        else:
            # 熊市旗：突破旗面低点
            breakout_level = flag['low']
            if current_k['low'] < breakout_level:
                breakout_strength = (breakout_level - current_k['low']) / breakout_level * 100
                return {
                    'type': 'BEARISH',
                    'level': breakout_level,
                    'strength': breakout_strength,
                    'confirmed': True
                }
        
        return None
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """分析旗形形态"""
        if len(df) < self.pole_min_bars + self.flag_min_bars:
            return {
                'status': 'INSUFFICIENT_DATA',
                'signal': 'WAIT'
            }
        
        # 寻找旗杆
        pole = self._find_pole(df)
        if not pole:
            return {
                'status': 'NO_SIGNAL',
                'signal': 'WAIT',
                'reason': '未找到符合条件的旗杆'
            }
        
        # 寻找旗面
        flag = self._find_flag(df, pole)
        if not flag:
            return {
                'status': 'NO_SIGNAL',
                'signal': 'WAIT',
                'reason': '未找到符合条件的旗面'
            }
        
        # 检查突破
        breakout = self._check_breakout(df, pole, flag)
        if not breakout:
            return {
                'status': 'NO_SIGNAL',
                'signal': 'WAIT',
                'pole': pole,
                'flag': flag,
                'reason': '等待突破'
            }
        
        # 生成信号
        signal = 'BUY' if breakout['type'] == 'BULLISH' else 'SELL'
        
        return {
            'status': 'SIGNAL',
            'signal': signal,
            'pole': pole,
            'flag': flag,
            'breakout': breakout,
            'current_price': df['close'].iloc[-1],
            'reason': f"{'牛市旗' if pole['direction'] == 'BULL' else '熊市旗'}突破 (旗杆：{pole['change_pct']:.1f}%, 突破强度：{breakout['strength']:.2f}%)"
        }
    
    def generate_signal(self, data_dict: Dict[str, pd.DataFrame], symbol: str) -> Optional[Dict]:
        """生成交易信号"""
        # 使用日线数据
        if '1D' not in data_dict and '1d' not in data_dict:
            return None
        
        df = data_dict.get('1D', data_dict.get('1d'))
        if df is None or len(df) < self.pole_min_bars + self.flag_min_bars:
            return None
        
        analysis = self.analyze(df)
        
        if analysis['signal'] == 'WAIT':
            return None
        
        current_price = analysis['current_price']
        direction = 'LONG' if analysis['signal'] == 'BUY' else 'SHORT'
        
        # 根据旗杆强度和突破强度计算置信度
        pole = analysis['pole']
        breakout = analysis['breakout']
        base_confidence = 65
        confidence = min(90, base_confidence + pole['change_pct'] * 2 + breakout['strength'] * 5)
        
        if confidence < self.min_confidence:
            return None
        
        # 计算止损止盈
        if direction == 'LONG':
            stop_loss_price = current_price * (1 - self.stop_loss_pct / 100)
            take_profit_price = current_price * (1 + self.take_profit_pct / 100)
        else:
            stop_loss_price = current_price * (1 + self.stop_loss_pct / 100)
            take_profit_price = current_price * (1 - self.take_profit_pct / 100)
        
        pattern_name = 'Bull Flag' if direction == 'LONG' else 'Bear Flag'
        
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
            'reason': analysis['reason'],
            'pattern': pattern_name,
            'timeframe': '1D',
            'timestamp': datetime.now().isoformat(),
            'pattern_details': {
                'pole_change_pct': pole['change_pct'],
                'flag_retrace_pct': pole['retrace_pct'] if 'retrace_pct' in pole else 0,
                'breakout_strength': breakout['strength']
            }
        }


# 便捷函数
def get_flag_strategy() -> FlagPatternStrategy:
    """获取策略实例"""
    return FlagPatternStrategy()


def generate_flag_signal(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """生成旗形信号"""
    strategy = get_flag_strategy()
    return strategy.generate_signal({'1D': df}, symbol)
