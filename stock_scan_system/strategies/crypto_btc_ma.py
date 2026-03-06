# -*- coding: utf-8 -*-
"""
BTC 均线金叉策略

策略逻辑：
- 当 BTC 短期均线上穿长期均线时，产生买入信号
- 当短期均线下穿长期均线时，产生卖出信号
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from src.strategy_base import BaseStrategy
except:
    from strategy_base import BaseStrategy
import pandas as pd
from typing import Dict, Optional, Any


class BTCMAStrategy(BaseStrategy):
    """BTC 均线金叉策略"""
    
    @property
    def name(self) -> str:
        return "btc_ma_cross"
    
    @property
    def description(self) -> str:
        return "BTC 均线金叉策略（5 日/20 日）"
    
    def scan(self, history: pd.DataFrame, current: Dict) -> Optional[Dict[str, Any]]:
        """
        扫描买入信号
        
        Args:
            history: 历史数据（包含 open/high/low/close/volume）
            current: 当前数据
            
        Returns:
            信号字典或 None
        """
        if len(history) < 20:
            return None
        
        # 计算均线
        history['ma5'] = history['close'].rolling(5).mean()
        history['ma20'] = history['close'].rolling(20).mean()
        
        # 获取最新数据
        ma5_current = history['ma5'].iloc[-1]
        ma20_current = history['ma20'].iloc[-1]
        ma5_prev = history['ma5'].iloc[-2]
        ma20_prev = history['ma20'].iloc[-2]
        
        # 判断金叉（短期上穿长期）
        if ma5_current > ma20_current and ma5_prev <= ma20_prev:
            return {
                'type': '买入信号',
                'signal': 'buy',
                'strategy': 'btc_ma_cross',
                'description': f'BTC 均线金叉（MA5={ma5_current:.2f} 上穿 MA20={ma20_current:.2f}）',
                'confidence': 75,
                'entry_price': current.get('price', 0),
                'stop_loss': current.get('price', 0) * 0.95,  # 5% 止损
                'target_price': current.get('price', 0) * 1.10,  # 10% 目标
            }
        
        # 判断死叉（短期下穿长期）
        if ma5_current < ma20_current and ma5_prev >= ma20_prev:
            return {
                'type': '卖出信号',
                'signal': 'sell',
                'strategy': 'btc_ma_cross',
                'description': f'BTC 均线死叉（MA5={ma5_current:.2f} 下穿 MA20={ma20_current:.2f}）',
                'confidence': 75,
                'exit_price': current.get('price', 0),
            }
        
        return None


# 实例化策略
strategy = BTCMAStrategy()
