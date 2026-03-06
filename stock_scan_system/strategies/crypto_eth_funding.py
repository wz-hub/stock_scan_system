# -*- coding: utf-8 -*-
"""
ETH 资金费率套利策略

策略逻辑：
- 当资金费率极低（< -0.01%）时，做多 ETH
- 当资金费率极高（> 0.01%）时，做空 ETH
- 赚取资金费率收益
"""

from src.strategy_base import BaseStrategy
from typing import Dict, Optional, Any


class ETHFundingStrategy(BaseStrategy):
    """ETH 资金费率策略"""
    
    @property
    def name(self) -> str:
        return "eth_funding_rate"
    
    @property
    def description(self) -> str:
        return "ETH 资金费率套利策略"
    
    def scan(self, history: Dict, current: Dict) -> Optional[Dict[str, Any]]:
        """
        扫描资金费率套利机会
        
        Args:
            history: 历史资金费率数据
            current: 当前数据（包含 funding_rate）
            
        Returns:
            信号字典或 None
        """
        funding_rate = current.get('funding_rate', 0)
        current_price = current.get('price', 0)
        
        # 资金费率极低，做多
        if funding_rate < -0.0001:  # -0.01%
            return {
                'type': '做多信号',
                'signal': 'buy',
                'strategy': 'eth_funding_rate',
                'description': f'ETH 资金费率极低（{funding_rate*100:.4f}%），做多赚取费率',
                'confidence': 80,
                'entry_price': current_price,
                'stop_loss': current_price * 0.97,
                'target_price': current_price * 1.05,
                'expected_funding_yield': abs(funding_rate) * 3,  # 每日 3 次结算
            }
        
        # 资金费率极高，做空
        if funding_rate > 0.0001:  # 0.01%
            return {
                'type': '做空信号',
                'signal': 'sell',
                'strategy': 'eth_funding_rate',
                'description': f'ETH 资金费率极高（{funding_rate*100:.4f}%），做空赚取费率',
                'confidence': 80,
                'entry_price': current_price,
                'stop_loss': current_price * 1.03,
                'target_price': current_price * 0.95,
                'expected_funding_yield': funding_rate * 3,
            }
        
        return None


# 实例化策略
strategy = ETHFundingStrategy()
