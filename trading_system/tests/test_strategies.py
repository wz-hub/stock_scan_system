"""
策略模块测试
测试所有 4 个策略的实现
"""
import pytest
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.base import BaseStrategy
from strategies.multi_timeframe import MultiTimeframeStrategy
from strategies.money_flow import MoneyFlowStrategy
from strategies.volatility_squeeze import VolatilitySqueezeStrategy
from strategies.liquidity_hunt import LiquidityHuntStrategy


def generate_test_data(rows=500, base_price=50000):
    """生成测试 K 线数据"""
    np.random.seed(42)
    
    # 生成随机游走价格
    returns = np.random.randn(rows) * 0.02
    prices = base_price * np.cumprod(1 + returns)
    
    # 生成 OHLCV 数据
    data = {
        'open': prices * (1 + np.random.randn(rows) * 0.005),
        'high': prices * (1 + np.abs(np.random.randn(rows) * 0.01)),
        'low': prices * (1 - np.abs(np.random.randn(rows) * 0.01)),
        'close': prices,
        'volume': np.random.randint(1000, 10000, rows)
    }
    
    return pd.DataFrame(data)


class TestBaseStrategy:
    """基类测试"""
    
    def test_base_strategy_abstract(self):
        """测试基类是抽象类"""
        with pytest.raises(TypeError):
            BaseStrategy()
    
    def test_concrete_strategy(self):
        """测试具体策略实现"""
        class TestStrategy(BaseStrategy):
            def analyze(self, df, **kwargs):
                return {'status': 'OK'}
            
            def generate_signal(self, df, symbol, **kwargs):
                return {'signal': 'test'}
        
        strategy = TestStrategy(name="Test", category="Test")
        assert strategy.name == "Test"
        assert strategy.category == "Test"
    
    def test_calculate_atr(self):
        """测试 ATR 计算"""
        class TestStrategy(BaseStrategy):
            def analyze(self, df, **kwargs):
                return {}
            def generate_signal(self, df, symbol, **kwargs):
                return None
        
        strategy = TestStrategy()
        df = generate_test_data(rows=100)
        
        atr = strategy._calculate_atr(df, period=14)
        
        assert atr > 0
        assert isinstance(atr, float)
    
    def test_calculate_ma(self):
        """测试均线计算"""
        class TestStrategy(BaseStrategy):
            def analyze(self, df, **kwargs):
                return {}
            def generate_signal(self, df, symbol, **kwargs):
                return None
        
        strategy = TestStrategy()
        df = generate_test_data(rows=100)
        
        ma20 = strategy._calculate_ma(df, period=20)
        
        assert ma20 is not None
        assert ma20 > 0
    
    def test_calculate_ma_insufficient_data(self):
        """测试数据不足时的均线计算"""
        class TestStrategy(BaseStrategy):
            def analyze(self, df, **kwargs):
                return {}
            def generate_signal(self, df, symbol, **kwargs):
                return None
        
        strategy = TestStrategy()
        df = generate_test_data(rows=10)
        
        ma50 = strategy._calculate_ma(df, period=50)
        
        assert ma50 is None
    
    def test_check_trend(self):
        """测试趋势判断"""
        class TestStrategy(BaseStrategy):
            def analyze(self, df, **kwargs):
                return {}
            def generate_signal(self, df, symbol, **kwargs):
                return None
        
        strategy = TestStrategy()
        df = generate_test_data(rows=500)
        
        trend = strategy._check_trend(df)
        
        assert trend in ['BULL', 'BEAR', 'NEUTRAL']
    
    def test_get_info(self):
        """测试获取策略信息"""
        class TestStrategy(BaseStrategy):
            def analyze(self, df, **kwargs):
                return {}
            def generate_signal(self, df, symbol, **kwargs):
                return None
        
        strategy = TestStrategy(name="Test Strat", category="Test")
        info = strategy.get_info()
        
        assert info['name'] == "Test Strat"
        assert info['category'] == "Test"
        assert 'class_name' in info
        assert 'initialized_at' in info


class TestMultiTimeframeStrategy:
    """多周期共振策略测试"""
    
    @pytest.fixture
    def strategy(self):
        return MultiTimeframeStrategy()
    
    def test_init(self, strategy):
        """测试初始化"""
        assert strategy.name == "Multi-Timeframe Resonance"
        assert strategy.category == "Multi-Timeframe"
        assert strategy.trend_timeframe == '1D'
        assert strategy.signal_timeframe == '4H'
        assert strategy.entry_timeframe == '1H'
    
    def test_analyze_with_data(self, strategy):
        """测试有数据时的分析"""
        data_dict = {
            '1D': generate_test_data(rows=500),
            '4H': generate_test_data(rows=500),
            '1H': generate_test_data(rows=500)
        }
        
        result = strategy.analyze(data_dict)
        
        assert result['strategy_name'] == strategy.name
        assert 'final_action' in result
        assert 'final_direction' in result
        assert 'confidence' in result
        assert 'reasons' in result
        assert result['final_action'] in ['BUY', 'SELL', 'WAIT', 'WATCH']
    
    def test_analyze_no_data(self, strategy):
        """测试无数据时的分析"""
        data_dict = {}
        
        result = strategy.analyze(data_dict)
        
        assert result['timeframes']['1D']['status'] == 'NO_DATA'
        assert result['timeframes']['4H']['status'] == 'NO_DATA'
        assert result['timeframes']['1H']['status'] == 'NO_DATA'
    
    def test_generate_signal_no_signal(self, strategy):
        """测试无信号时的信号生成"""
        data_dict = {
            '1D': generate_test_data(rows=500),
            '4H': generate_test_data(rows=500),
            '1H': generate_test_data(rows=500)
        }
        
        # Mock 分析结果返回 WAIT
        with patch.object(strategy, 'analyze') as mock_analyze:
            mock_analyze.return_value = {
                'final_action': 'WAIT',
                'strategy_name': strategy.name
            }
            
            signal = strategy.generate_signal(data_dict, 'BTCUSDT')
            
            assert signal is None
    
    def test_generate_signal_with_signal(self, strategy):
        """测试有信号时的信号生成"""
        data_dict = {
            '1D': generate_test_data(rows=500),
            '4H': generate_test_data(rows=500),
            '1H': generate_test_data(rows=500)
        }
        
        # Mock 分析结果返回 BUY
        with patch.object(strategy, 'analyze') as mock_analyze:
            mock_analyze.return_value = {
                'final_action': 'BUY',
                'final_direction': 'LONG',
                'strategy_name': strategy.name,
                'confidence': 75.0,
                'reasons': ['Test reason'],
                'timeframes': {
                    '1H': {'close': 50000}
                }
            }
            
            signal = strategy.generate_signal(data_dict, 'BTCUSDT')
            
            assert signal is not None
            assert signal['action'] == 'BUY'
            assert signal['direction'] == 'LONG'
            assert 'stop_loss_price' in signal
            assert 'take_profit_price' in signal
            assert 'risk_reward_ratio' in signal
    
    def test_get_trend(self, strategy):
        """测试趋势判断"""
        df = generate_test_data(rows=500)
        
        trend = strategy._get_trend(df)
        
        assert trend in ['BULL', 'BEAR', 'NEUTRAL']
    
    def test_get_signal(self, strategy):
        """测试信号获取"""
        df = generate_test_data(rows=500)
        
        signal = strategy._get_signal(df)
        
        assert signal in ['BUY', 'SELL', 'WAIT']
    
    def test_get_entry(self, strategy):
        """测试入场点获取"""
        df = generate_test_data(rows=500)
        
        entry = strategy._get_entry(df)
        
        assert entry in ['GO', 'WAIT']


class TestMoneyFlowStrategy:
    """资金流追踪策略测试"""
    
    @pytest.fixture
    def strategy(self):
        return MoneyFlowStrategy()
    
    def test_init(self, strategy):
        """测试初始化"""
        assert strategy.name == "Money Flow Tracker"
        assert strategy.category == "Money Flow"
        assert strategy.large_order_threshold == 10000
        assert strategy.lookback_periods == 100
    
    def test_analyze_with_data(self, strategy):
        """测试有数据时的分析"""
        df = generate_test_data(rows=500)
        
        result = strategy.analyze(df)
        
        assert result['strategy_name'] == strategy.name
        assert result['status'] in ['SIGNAL', 'NO_SIGNAL', 'INSUFFICIENT_DATA']
        assert 'flow_data' in result
        assert 'indicators' in result
    
    def test_analyze_insufficient_data(self, strategy):
        """测试数据不足时的分析"""
        df = generate_test_data(rows=50)
        
        result = strategy.analyze(df)
        
        assert result['status'] == 'INSUFFICIENT_DATA'
    
    def test_analyze_order_flow(self, strategy):
        """测试订单流分析"""
        df = generate_test_data(rows=500)
        
        flow_data = strategy._analyze_order_flow(df)
        
        assert 'large_buy_volume' in flow_data
        assert 'large_sell_volume' in flow_data
        assert 'net_flow' in flow_data
        assert 'accumulation' in flow_data
        assert 'distribution' in flow_data
    
    def test_calculate_money_flow_indicators(self, strategy):
        """测试资金流指标计算"""
        df = generate_test_data(rows=500)
        
        indicators = strategy._calculate_money_flow_indicators(df)
        
        assert 'mfi' in indicators
        assert 'obv_trend' in indicators
        assert 'accumulation_line' in indicators
        assert 0 <= indicators['mfi'] <= 100
    
    def test_detect_accumulation(self, strategy):
        """测试吸筹检测"""
        df = generate_test_data(rows=500)
        flow_data = {'net_flow': 1000000}  # 大净流入
        
        accumulation = strategy._detect_accumulation(df, flow_data)
        
        assert isinstance(accumulation, bool)
    
    def test_detect_distribution(self, strategy):
        """测试出货检测"""
        df = generate_test_data(rows=500)
        flow_data = {'net_flow': -1000000}  # 大净流出
        
        distribution = strategy._detect_distribution(df, flow_data)
        
        assert isinstance(distribution, bool)
    
    def test_generate_signal(self, strategy):
        """测试信号生成"""
        df = generate_test_data(rows=500)
        
        # Mock 分析结果返回 SIGNAL
        with patch.object(strategy, 'analyze') as mock_analyze:
            mock_analyze.return_value = {
                'status': 'SIGNAL',
                'action': 'BUY',
                'direction': 'LONG',
                'strategy_name': strategy.name,
                'confidence': 70.0,
                'reasons': ['大单净流入'],
                'current_price': 50000,
                'entry_price': 50000,
                'flow_data': {'net_flow': 1000000},
                'accumulation': True,
                'distribution': False
            }
            
            signal = strategy.generate_signal(df, 'BTCUSDT')
            
            assert signal is not None
            assert signal['action'] == 'BUY'
            assert signal['direction'] == 'LONG'
            assert 'net_flow' in signal


class TestVolatilitySqueezeStrategy:
    """波动率收缩突破策略测试"""
    
    @pytest.fixture
    def strategy(self):
        return VolatilitySqueezeStrategy()
    
    def test_init(self, strategy):
        """测试初始化"""
        assert strategy.name == "Volatility Squeeze Breakout"
        assert strategy.category == "Volatility"
        assert strategy.bb_period == 20
        assert strategy.bb_std == 2.0
    
    def test_calculate_bollinger(self, strategy):
        """测试布林带计算"""
        df = generate_test_data(rows=500)
        
        bb = strategy._calculate_bollinger(df)
        
        assert 'upper' in bb
        assert 'middle' in bb
        assert 'lower' in bb
        assert 'width' in bb
        assert 'std' in bb
        assert len(bb['upper']) == len(df)
    
    def test_is_squeeze(self, strategy):
        """测试波动率收缩判断"""
        df = generate_test_data(rows=500)
        bb = strategy._calculate_bollinger(df)
        
        is_squeeze = strategy._is_squeeze(df, bb)
        
        assert isinstance(is_squeeze, bool)
    
    def test_check_breakout(self, strategy):
        """测试突破检查"""
        df = generate_test_data(rows=500)
        bb = strategy._calculate_bollinger(df)
        
        breakout = strategy._check_breakout(df, bb)
        
        assert breakout is None or breakout in ['LONG', 'SHORT']
    
    def test_check_volume(self, strategy):
        """测试成交量确认"""
        df = generate_test_data(rows=500)
        
        confirmed, ratio = strategy._check_volume(df)
        
        assert isinstance(confirmed, bool)
        assert isinstance(ratio, float)
        assert ratio > 0
    
    def test_analyze(self, strategy):
        """测试分析"""
        df = generate_test_data(rows=500)
        
        result = strategy.analyze(df)
        
        assert result['strategy_name'] == strategy.name
        assert 'is_squeeze' in result
        assert 'status' in result
    
    def test_generate_signal(self, strategy):
        """测试信号生成"""
        df = generate_test_data(rows=500)
        
        # Mock 分析结果
        with patch.object(strategy, 'analyze') as mock_analyze:
            mock_analyze.return_value = {
                'status': 'SIGNAL',
                'action': 'BUY',
                'direction': 'LONG',
                'strategy_name': strategy.name,
                'confidence': 75.0,
                'reasons': ['波动率收缩突破'],
                'current_price': 50000,
                'entry_price': 50000,
                'stop_loss_price': 49000,
                'take_profit_price': 52000,
                'stop_loss_pct': 2.0,
                'take_profit_pct': 4.0,
                'risk_reward_ratio': 2.0
            }
            
            signal = strategy.generate_signal(df, 'BTCUSDT')
            
            assert signal is not None
            assert signal['strategy_name'] == strategy.name
            assert 'volume_ratio' in signal


class TestLiquidityHuntStrategy:
    """流动性猎杀策略测试"""
    
    @pytest.fixture
    def strategy(self):
        return LiquidityHuntStrategy()
    
    def test_init(self, strategy):
        """测试初始化"""
        assert strategy.name == "Liquidity Hunt"
        assert strategy.category == "Market Structure"
        assert strategy.swing_lookback == 20
    
    def test_find_swing_highs(self, strategy):
        """测试 Swing 高点查找"""
        df = generate_test_data(rows=500)
        
        swing_highs = strategy._find_swing_highs(df)
        
        assert isinstance(swing_highs, list)
        if swing_highs:
            assert len(swing_highs[0]) == 2  # (index, price)
    
    def test_find_swing_lows(self, strategy):
        """测试 Swing 低点查找"""
        df = generate_test_data(rows=500)
        
        swing_lows = strategy._find_swing_lows(df)
        
        assert isinstance(swing_lows, list)
        if swing_lows:
            assert len(swing_lows[0]) == 2  # (index, price)
    
    def test_find_recent_swing_levels(self, strategy):
        """测试最近 Swing 水平查找"""
        df = generate_test_data(rows=500)
        
        levels = strategy._find_recent_swing_levels(df)
        
        assert 'highs' in levels
        assert 'lows' in levels
        assert isinstance(levels['highs'], list)
        assert isinstance(levels['lows'], list)
    
    def test_check_liquidity_grab(self, strategy):
        """测试流动性猎杀检查"""
        df = generate_test_data(rows=500)
        
        # 测试高点猎杀
        grab = strategy._check_liquidity_grab(df, 49000, 'high')
        assert grab is None or grab == 'GRAB_HIGH'
        
        # 测试低点猎杀
        grab = strategy._check_liquidity_grab(df, 51000, 'low')
        assert grab is None or grab == 'GRAB_LOW'
    
    def test_analyze(self, strategy):
        """测试分析"""
        df = generate_test_data(rows=500)
        
        result = strategy.analyze(df)
        
        assert result['strategy_name'] == strategy.name
        assert 'swing_levels' in result
        assert 'grab_signals' in result
        assert 'status' in result
    
    def test_generate_signal(self, strategy):
        """测试信号生成"""
        df = generate_test_data(rows=500)
        
        # Mock 分析结果
        with patch.object(strategy, 'analyze') as mock_analyze:
            mock_analyze.return_value = {
                'status': 'SIGNAL',
                'action': 'BUY',
                'direction': 'LONG',
                'strategy_name': strategy.name,
                'confidence': 70.0,
                'reasons': ['流动性猎杀'],
                'current_price': 50000,
                'entry_price': 50000,
                'swing_levels': {'highs': [], 'lows': [(100, 49000)]},
                'grab_signals': [{'type': 'GRAB_LOW', 'level': 49000, 'distance_pct': 2.0}]
            }
            
            signal = strategy.generate_signal(df, 'BTCUSDT')
            
            assert signal is not None
            assert signal['strategy_name'] == strategy.name
            assert 'swing_levels' in signal
            assert 'grab_signals' in signal


class TestStrategiesIntegration:
    """策略集成测试"""
    
    def test_all_strategies_basic_workflow(self):
        """测试所有策略的基本工作流"""
        strategies = [
            MultiTimeframeStrategy(),
            MoneyFlowStrategy(),
            VolatilitySqueezeStrategy(),
            LiquidityHuntStrategy()
        ]
        
        df = generate_test_data(rows=500)
        data_dict = {
            '1D': df,
            '4H': df,
            '1H': df
        }
        
        for strategy in strategies:
            # 测试分析
            if isinstance(strategy, MultiTimeframeStrategy):
                result = strategy.analyze(data_dict)
            else:
                result = strategy.analyze(df)
            
            assert result is not None
            assert 'strategy_name' in result
            
            # 测试信号生成（可能返回 None）
            if isinstance(strategy, MultiTimeframeStrategy):
                signal = strategy.generate_signal(data_dict, 'BTCUSDT')
            else:
                signal = strategy.generate_signal(df, 'BTCUSDT')
            
            # 信号可能为 None（无交易机会）
            if signal is not None:
                assert 'strategy_name' in signal
                assert 'symbol' in signal
                assert 'action' in signal
                assert 'direction' in signal


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
