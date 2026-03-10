"""
策略模块单元测试
测试 4 个策略的功能
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestMultiTimeframeStrategy(unittest.TestCase):
    """测试多周期共振策略"""
    
    def test_strategy_exists(self):
        """测试策略模块存在"""
        from strategies.multi_timeframe import MultiTimeframeStrategy
        strategy = MultiTimeframeStrategy()
        self.assertIsNotNone(strategy)
    
    def test_strategy_name(self):
        """测试策略名称"""
        from strategies.multi_timeframe import MultiTimeframeStrategy
        strategy = MultiTimeframeStrategy()
        self.assertEqual(strategy.__class__.__name__, 'MultiTimeframeStrategy')


class TestVolatilitySqueezeStrategy(unittest.TestCase):
    """测试波动率收缩策略"""
    
    def test_strategy_exists(self):
        """测试策略模块存在"""
        from strategies.volatility_squeeze import VolatilitySqueezeStrategy
        strategy = VolatilitySqueezeStrategy()
        self.assertIsNotNone(strategy)
    
    def test_strategy_name(self):
        """测试策略名称"""
        from strategies.volatility_squeeze import VolatilitySqueezeStrategy
        strategy = VolatilitySqueezeStrategy()
        self.assertEqual(strategy.__class__.__name__, 'VolatilitySqueezeStrategy')


class TestMoneyFlowStrategy(unittest.TestCase):
    """测试资金流追踪策略"""
    
    def test_strategy_exists(self):
        """测试策略模块存在"""
        from strategies.money_flow import MoneyFlowStrategy
        strategy = MoneyFlowStrategy()
        self.assertIsNotNone(strategy)
    
    def test_strategy_name(self):
        """测试策略名称"""
        from strategies.money_flow import MoneyFlowStrategy
        strategy = MoneyFlowStrategy()
        self.assertEqual(strategy.__class__.__name__, 'MoneyFlowStrategy')


class TestLiquidityHuntStrategy(unittest.TestCase):
    """测试流动性猎杀策略"""
    
    def test_strategy_exists(self):
        """测试策略模块存在"""
        from strategies.liquidity_hunt import LiquidityHuntStrategy
        strategy = LiquidityHuntStrategy()
        self.assertIsNotNone(strategy)
    
    def test_strategy_name(self):
        """测试策略名称"""
        from strategies.liquidity_hunt import LiquidityHuntStrategy
        strategy = LiquidityHuntStrategy()
        self.assertEqual(strategy.__class__.__name__, 'LiquidityHuntStrategy')


class TestStrategyIntegration(unittest.TestCase):
    """测试策略集成"""
    
    def test_all_strategies_importable(self):
        """测试所有策略可导入"""
        from strategies import (
            MultiTimeframeStrategy,
            VolatilitySqueezeStrategy,
            MoneyFlowStrategy,
            LiquidityHuntStrategy
        )
        
        strategies = [
            MultiTimeframeStrategy(),
            VolatilitySqueezeStrategy(),
            MoneyFlowStrategy(),
            LiquidityHuntStrategy()
        ]
        
        self.assertEqual(len(strategies), 4)
    
    def test_strategies_list(self):
        """测试策略列表"""
        from strategies import __all__
        
        expected = [
            'MultiTimeframeStrategy',
            'VolatilitySqueezeStrategy',
            'MoneyFlowStrategy',
            'LiquidityHuntStrategy'
        ]
        
        for name in expected:
            self.assertIn(name, __all__)


if __name__ == '__main__':
    unittest.main()
