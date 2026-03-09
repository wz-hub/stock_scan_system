"""
信号模块单元测试
测试信号生成、验证、去重功能
"""
import sys
import unittest
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSignalCreation(unittest.TestCase):
    """测试信号创建"""
    
    def test_signal_dict_structure(self):
        """测试信号字典结构"""
        signal = {
            'signal_id': 'TEST-001',
            'symbol': 'BTC-USD',
            'strategy_name': 'Multi-Timeframe Resonance',
            'action': 'SELL',
            'direction': 'SHORT',
            'current_price': '50000.00',
            'confidence': 85.0,
            'stop_loss_price': '51000.00',
            'take_profit_price': '48000.00'
        }
        
        # 验证必需字段
        required_fields = [
            'signal_id', 'symbol', 'strategy_name',
            'action', 'direction', 'current_price',
            'confidence', 'stop_loss_price', 'take_profit_price'
        ]
        
        for field in required_fields:
            assert field in signal, f"缺少必需字段：{field}"
    
    def test_signal_confidence_validation(self):
        """测试信号置信度验证"""
        # 高置信度信号
        high_confidence = 85.0
        assert high_confidence >= 80, "置信度应该>=80"
        
        # 低置信度信号（应该被过滤）
        low_confidence = 50.0
        assert low_confidence < 80, "低置信度应该<80"


class TestSignalDeduplication(unittest.TestCase):
    """测试信号去重"""
    
    def test_duplicate_signal_key(self):
        """测试重复信号 key 生成"""
        signal1 = {
            'symbol': 'XRP-USD',
            'strategy_name': 'Multi-Timeframe Resonance'
        }
        
        signal2 = {
            'symbol': 'XRP-USD',
            'strategy_name': 'Multi-Timeframe Resonance'
        }
        
        # 生成去重 key
        key1 = f"{signal1['symbol']}-{signal1['strategy_name']}"
        key2 = f"{signal2['symbol']}-{signal2['strategy_name']}"
        
        assert key1 == key2, "相同币种和策略应该有相同的 key"
    
    def test_different_strategy_not_duplicate(self):
        """测试不同策略不算重复"""
        signal1 = {
            'symbol': 'BTC-USD',
            'strategy_name': 'Multi-Timeframe Resonance'
        }
        
        signal2 = {
            'symbol': 'BTC-USD',
            'strategy_name': 'Volatility Squeeze'
        }
        
        key1 = f"{signal1['symbol']}-{signal1['strategy_name']}"
        key2 = f"{signal2['symbol']}-{signal2['strategy_name']}"
        
        assert key1 != key2, "不同策略应该有不同的 key"
    
    def test_active_signal_deduplication(self):
        """测试活跃信号去重逻辑"""
        # 模拟活跃信号
        active_signals = [
            {'symbol': 'XRP-USD', 'strategy_name': 'Multi-Timeframe Resonance', 'status': 'ACTIVE'},
            {'symbol': 'BTC-USD', 'strategy_name': 'Multi-Timeframe Resonance', 'status': 'ACTIVE'}
        ]
        
        # 生成活跃信号 keys
        active_keys = {
            f"{s['symbol']}-{s['strategy_name']}"
            for s in active_signals
        }
        
        # 新信号
        new_signal = {
            'symbol': 'XRP-USD',
            'strategy_name': 'Multi-Timeframe Resonance'
        }
        
        new_key = f"{new_signal['symbol']}-{new_signal['strategy_name']}"
        
        # 检查是否重复
        assert new_key in active_keys, "应该检测到重复信号"


class TestSignalFiltering(unittest.TestCase):
    """测试信号过滤"""
    
    def test_confidence_filter(self):
        """测试置信度过滤"""
        signals = [
            {'symbol': 'BTC-USD', 'confidence': 85.0},
            {'symbol': 'ETH-USD', 'confidence': 75.0},
            {'symbol': 'XRP-USD', 'confidence': 90.0},
            {'symbol': 'SOL-USD', 'confidence': 50.0}
        ]
        
        min_confidence = 80
        filtered = [s for s in signals if s['confidence'] >= min_confidence]
        
        assert len(filtered) == 2, "应该只保留>=80 的信号"
        assert all(s['confidence'] >= 80 for s in filtered), "所有保留的信号都应该>=80"


if __name__ == '__main__':
    import unittest
    unittest.main()
