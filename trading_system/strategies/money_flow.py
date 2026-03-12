"""
资金流追踪策略
核心逻辑：追踪大单动向，发现主力吸筹/出货
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime

from .base import BaseStrategy


class MoneyFlowStrategy(BaseStrategy):
    """资金流追踪策略"""
    
    def __init__(self):
        super().__init__(name="Money Flow Tracker", category="Money Flow")
        
        # 大单阈值（USDT）
        self.large_order_threshold = 10000  # 1 万 USDT 以上算大单
        
        # 分析窗口
        self.lookback_periods = 100  # 分析最近 100 根 K 线
        
        # 净流入阈值
        self.net_flow_threshold = 500000  # 50 万 USDT 净流入
        
        # 价格变化阈值
        self.price_change_threshold = 2.0  # 2% 价格变化
    
    def _analyze_order_flow(self, df: pd.DataFrame) -> Dict:
        """
        分析订单流
        通过价格和成交量变化推断大单动向
        """
        result = {
            'large_buy_volume': 0,
            'large_sell_volume': 0,
            'net_flow': 0,
            'accumulation': False,
            'distribution': False
        }
        
        if len(df) < self.lookback_periods or 'volume' not in df.columns:
            return result
        
        # 计算每根 K 线的资金流向
        recent = df.iloc[-self.lookback_periods:]
        
        large_buys = []
        large_sells = []
        
        for idx, row in recent.iterrows():
            volume_usdt = row['close'] * row['volume'] if 'volume' in row else 0
            
            # 判断是大单还是小单
            is_large = volume_usdt > self.large_order_threshold
            
            # 判断买卖方向
            if 'close' in row and 'open' in row:
                if row['close'] > row['open']:
                    # 阳线，买方主导
                    if is_large:
                        large_buys.append(volume_usdt)
                elif row['close'] < row['open']:
                    # 阴线，卖方主导
                    if is_large:
                        large_sells.append(volume_usdt)
        
        result['large_buy_volume'] = sum(large_buys)
        result['large_sell_volume'] = sum(large_sells)
        result['net_flow'] = result['large_buy_volume'] - result['large_sell_volume']
        
        return result
    
    def _detect_accumulation(self, df: pd.DataFrame, flow_data: Dict) -> bool:
        """
        检测吸筹
        特征：大单净流入 + 价格涨幅不大
        """
        net_flow = flow_data['net_flow']
        
        # 计算近期价格变化
        if len(df) < 20:
            return False
        
        recent_price_change = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100
        
        # 大单净流入超过阈值，但价格涨幅小于阈值 → 吸筹
        if net_flow > self.net_flow_threshold and recent_price_change < self.price_change_threshold:
            return True
        
        return False
    
    def _detect_distribution(self, df: pd.DataFrame, flow_data: Dict) -> bool:
        """
        检测出货
        特征：大单净流出 + 价格跌幅不大（或上涨）
        """
        net_flow = flow_data['net_flow']
        
        # 计算近期价格变化
        if len(df) < 20:
            return False
        
        recent_price_change = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100
        
        # 大单净流出超过阈值，但价格跌幅小于阈值（甚至上涨）→ 出货
        if net_flow < -self.net_flow_threshold and recent_price_change > -self.price_change_threshold:
            return True
        
        return False
    
    def _calculate_money_flow_indicators(self, df: pd.DataFrame) -> Dict:
        """
        计算资金流指标
        """
        result = {
            'mfi': 50,  # 资金流量指标
            'obv_trend': 'NEUTRAL',  # OBV 趋势
            'accumulation_line': 0  # 累积线
        }
        
        if len(df) < 14:
            return result
        
        # 计算 MFI (Money Flow Index)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        
        positive_flow = []
        negative_flow = []
        
        for i in range(1, len(df)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.append(money_flow.iloc[i])
                negative_flow.append(0)
            else:
                positive_flow.append(0)
                negative_flow.append(money_flow.iloc[i])
        
        if len(positive_flow) >= 14:
            avg_positive = pd.Series(positive_flow[-14:]).mean()
            avg_negative = pd.Series(negative_flow[-14:]).mean()
            
            if avg_negative > 0:
                money_ratio = avg_positive / avg_negative
                mfi = 100 - (100 / (1 + money_ratio))
            else:
                mfi = 100
            
            result['mfi'] = mfi
        
        # 计算 OBV 趋势
        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        # 比较 OBV 和价格的趋势
        price_trend = df['close'].iloc[-1] > df['close'].iloc[-20]
        obv_trend = obv[-1] > obv[-20]
        
        if obv_trend and not price_trend:
            result['obv_trend'] = 'BULL_DIVERGENCE'  # OBV 向上，价格向下 → 潜在底部
        elif not obv_trend and price_trend:
            result['obv_trend'] = 'BEAR_DIVERGENCE'  # OBV 向下，价格向上 → 潜在顶部
        elif obv_trend:
            result['obv_trend'] = 'BULL'
        else:
            result['obv_trend'] = 'BEAR'
        
        return result
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        分析资金流信号
        
        Returns:
            分析结果字典
        """
        result = {
            'strategy_name': self.name,
            'timestamp': datetime.now().isoformat(),
            'status': 'NO_SIGNAL'
        }
        
        if len(df) < self.lookback_periods:
            result['status'] = 'INSUFFICIENT_DATA'
            return result
        
        # 分析订单流
        flow_data = self._analyze_order_flow(df)
        result['flow_data'] = flow_data
        
        # 计算资金流指标
        mf_indicators = self._calculate_money_flow_indicators(df)
        result['indicators'] = mf_indicators
        
        # 检测吸筹/出货
        accumulation = self._detect_accumulation(df, flow_data)
        distribution = self._detect_distribution(df, flow_data)
        
        result['accumulation'] = accumulation
        result['distribution'] = distribution
        
        # 生成信号
        if accumulation:
            result['status'] = 'SIGNAL'
            result['action'] = 'BUY'
            result['direction'] = 'LONG'
            result['signal_type'] = 'ACCUMULATION'
            
            # 计算置信度
            confidence = 50.0
            
            # 净流入越大，置信度越高
            flow_ratio = flow_data['net_flow'] / self.net_flow_threshold
            confidence += min(20, flow_ratio * 10)
            
            # MFI 超卖 → 加分
            if mf_indicators['mfi'] < 30:
                confidence += 15
            elif mf_indicators['mfi'] < 40:
                confidence += 10
            
            # OBV  bullish divergence → 加分
            if mf_indicators['obv_trend'] == 'BULL_DIVERGENCE':
                confidence += 20
            elif mf_indicators['obv_trend'] == 'BULL':
                confidence += 10
            
            result['confidence'] = min(confidence, 95.0)
            
            # 生成理由
            reasons = [
                f"大单净流入 ${flow_data['net_flow']/1e6:.2f}M",
                "主力吸筹迹象",
            ]
            if mf_indicators['mfi'] < 30:
                reasons.append(f"MFI 超卖 ({mf_indicators['mfi']:.1f})")
            if mf_indicators['obv_trend'] == 'BULL_DIVERGENCE':
                reasons.append("OBV  bullish divergence")
            
            result['reasons'] = reasons
            
        elif distribution:
            result['status'] = 'SIGNAL'
            result['action'] = 'SELL'
            result['direction'] = 'SHORT'
            result['signal_type'] = 'DISTRIBUTION'
            
            # 计算置信度
            confidence = 50.0
            
            # 净流出越大，置信度越高
            flow_ratio = abs(flow_data['net_flow']) / self.net_flow_threshold
            confidence += min(20, flow_ratio * 10)
            
            # MFI 超买 → 加分
            if mf_indicators['mfi'] > 70:
                confidence += 15
            elif mf_indicators['mfi'] > 60:
                confidence += 10
            
            # OBV  bearish divergence → 加分
            if mf_indicators['obv_trend'] == 'BEAR_DIVERGENCE':
                confidence += 20
            elif mf_indicators['obv_trend'] == 'BEAR':
                confidence += 10
            
            result['confidence'] = min(confidence, 95.0)
            
            # 生成理由
            reasons = [
                f"大单净流出 ${abs(flow_data['net_flow'])/1e6:.2f}M",
                "主力出货迹象",
            ]
            if mf_indicators['mfi'] > 70:
                reasons.append(f"MFI 超买 ({mf_indicators['mfi']:.1f})")
            if mf_indicators['obv_trend'] == 'BEAR_DIVERGENCE':
                reasons.append("OBV  bearish divergence")
            
            result['reasons'] = reasons
        
        # 计算风险管理参数
        if result['status'] == 'SIGNAL':
            current_price = df['close'].iloc[-1]
            atr = self._calculate_atr(df)
            
            result['current_price'] = current_price
            result['entry_price'] = current_price
            
            if result['direction'] == 'LONG':
                result['stop_loss_price'] = current_price - 2.5 * atr
                result['take_profit_price'] = current_price + 4.0 * atr
            else:
                result['stop_loss_price'] = current_price + 2.5 * atr
                result['take_profit_price'] = current_price - 4.0 * atr
            
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
        atr = self._calculate_atr(df)
        
        # 动态止损止盈
        levels = self._find_swing_levels(df)
        
        if levels['lows'] and analysis['direction'] == 'LONG':
            stop_level = levels['lows'][0][1] * 0.99
            stop_loss_price = stop_level
            stop_loss_pct = abs(current_price - stop_loss_price) / current_price * 100
        elif levels['highs'] and analysis['direction'] == 'SHORT':
            stop_level = levels['highs'][0][1] * 1.01
            stop_loss_price = stop_level
            stop_loss_pct = abs(current_price - stop_loss_price) / current_price * 100
        else:
            if analysis['direction'] == 'LONG':
                stop_loss_price = current_price - 2.5 * atr
            else:
                stop_loss_price = current_price + 2.5 * atr
            stop_loss_pct = abs(current_price - stop_loss_price) / current_price * 100
        
        # 止盈：主力吸筹/出货需要时间，给更大空间
        min_rr = 2.5
        if levels['highs'] and analysis['direction'] == 'LONG':
            take_profit_price = levels['highs'][0][1]
            tp_pct = abs(take_profit_price - current_price) / current_price * 100
            if tp_pct / stop_loss_pct < min_rr:
                take_profit_price = current_price * (1 + stop_loss_pct * min_rr / 100)
                tp_pct = stop_loss_pct * min_rr
        elif levels['lows'] and analysis['direction'] == 'SHORT':
            take_profit_price = levels['lows'][0][1]
            tp_pct = abs(take_profit_price - current_price) / current_price * 100
            if tp_pct / stop_loss_pct < min_rr:
                take_profit_price = current_price * (1 - stop_loss_pct * min_rr / 100)
                tp_pct = stop_loss_pct * min_rr
        else:
            tp_pct = stop_loss_pct * 4  # 主力行情给 4R
            take_profit_price = current_price * (1 + tp_pct / 100 * (1 if analysis['direction'] == 'LONG' else -1))
        
        take_profit_pct = abs(take_profit_price - current_price) / current_price * 100
        risk_reward_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 0
        
        # 持仓周期：主力建仓需要时间
        holding_period = {
            'min_days': 3,
            'max_days': 10,
            'expected_days': 5,
            'type': 'swing'
        }
        
        return {
            'strategy_name': analysis['strategy_name'],
            'strategy_category': self.category,
            'symbol': symbol.replace('USDT', '-USD'),
            'action': analysis['action'],
            'direction': analysis['direction'],
            'current_price': str(current_price),
            'entry_price': analysis['entry_price'],
            'entry_type': 'MARKET',
            'stop_loss_price': stop_loss_price,
            'stop_loss_pct': round(stop_loss_pct, 2),
            'take_profit_price': take_profit_price,
            'take_profit_pct': round(take_profit_pct, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'position_size_pct': min(20.0, analysis['confidence'] / 5),
            'confidence': analysis['confidence'],
            'reason': '；'.join(analysis['reasons']),
            'pattern': analysis.get('signal_type', 'Money Flow'),
            'timeframe': '1D',
            'timestamp': datetime.now().isoformat(),
            'net_flow': analysis['flow_data']['net_flow'],
            'accumulation': analysis['accumulation'],
            'distribution': analysis['distribution'],
            'stop_type': 'technical' if (levels['lows'] or levels['highs']) else 'ATR',
            'take_profit_type': 'technical' if (levels['highs'] or levels['lows']) else 'multiple_R',
            'holding_period': holding_period
        }


# 便捷函数
def get_money_flow_strategy() -> MoneyFlowStrategy:
    """获取策略实例"""
    return MoneyFlowStrategy()


def analyze_money_flow(df: pd.DataFrame) -> Dict:
    """分析资金流（便捷函数）"""
    strategy = get_money_flow_strategy()
    return strategy.analyze(df)


def generate_money_flow_signal(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """生成资金流信号（便捷函数）"""
    strategy = get_money_flow_strategy()
    return strategy.generate_signal(df, symbol)
