"""
信号扫描模块测试
测试 SignalScanner 类的核心功能
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.scanner import SignalScanner


class TestSignalScanner:
    """SignalScanner 测试类"""
    
    @pytest.fixture
    def scanner(self):
        """创建扫描器实例"""
        with patch('core.scanner.MarketDatabase'), \
             patch('core.scanner.RealtimeData'), \
             patch('core.scanner.SignalGenerator'), \
             patch('core.scanner.FeishuNotifier'):
            scanner = SignalScanner(
                config_path='config/scan_config.json',
                notification_path='config/notification.json',
                cache_file='cache/test_signals.json',
                min_confidence=60,
                max_workers=2
            )
            yield scanner
            scanner.close()
    
    def test_init(self, scanner):
        """测试初始化"""
        assert scanner is not None
        assert scanner.min_confidence == 60
        assert scanner.max_workers == 2
        assert scanner.cache_file.exists() or scanner.cache_file.parent.exists()
    
    def test_signal_hash(self, scanner):
        """测试信号哈希生成"""
        signal1 = {
            'symbol': 'BTCUSDT',
            'strategy_name': 'Multi-Timeframe Resonance',
            'action': 'BUY',
            'direction': 'LONG'
        }
        
        signal2 = {
            'symbol': 'ETHUSDT',
            'strategy_name': 'Multi-Timeframe Resonance',
            'action': 'BUY',
            'direction': 'LONG'
        }
        
        hash1 = scanner._signal_hash(signal1)
        hash2 = scanner._signal_hash(signal2)
        
        # 相同信号生成相同哈希
        assert hash1 == scanner._signal_hash(signal1)
        # 不同信号生成不同哈希
        assert hash1 != hash2
        # 哈希长度为 12
        assert len(hash1) == 12
    
    def test_cache_operations(self, scanner, tmp_path):
        """测试缓存操作"""
        cache_file = tmp_path / 'test_cache.json'
        scanner.cache_file = cache_file
        
        # 测试保存和加载缓存
        test_data = {
            'signals': ['hash1', 'hash2', 'hash3'],
            'last_scan': datetime.now().isoformat()
        }
        
        scanner._save_cache(test_data)
        loaded_data = scanner._load_cache()
        
        assert loaded_data['signals'] == ['hash1', 'hash2', 'hash3']
        assert 'last_scan' in loaded_data
    
    def test_load_cache_empty(self, scanner, tmp_path):
        """测试加载空缓存"""
        cache_file = tmp_path / 'nonexistent.json'
        scanner.cache_file = cache_file
        
        cache = scanner._load_cache()
        
        assert cache == {'signals': [], 'last_scan': None}
    
    def test_scan_symbol_strategies(self, scanner):
        """测试单个币种策略扫描"""
        mock_rt = Mock()
        mock_db = Mock()
        
        # Mock klines 数据
        import pandas as pd
        mock_df = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'close': [101, 102, 103, 104, 105],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        mock_rt.get_binance_klines.return_value = mock_df
        
        with patch.object(scanner, 'rt', mock_rt):
            result = scanner._scan_symbol_strategies(('BTCUSDT', mock_rt, mock_db))
            
            # 应该返回信号列表或 None
            assert result is None or isinstance(result, list)
    
    def test_scan_symbol_strategies_insufficient_data(self, scanner):
        """测试数据不足时的扫描"""
        mock_rt = Mock()
        mock_db = Mock()
        
        # Mock 空数据
        import pandas as pd
        mock_df = pd.DataFrame()
        mock_rt.get_binance_klines.return_value = mock_df
        
        with patch.object(scanner, 'rt', mock_rt):
            result = scanner._scan_symbol_strategies(('BTCUSDT', mock_rt, mock_db))
            
            # 数据不足应返回 None
            assert result is None
    
    def test_get_scan_symbols(self, scanner):
        """测试获取扫描标的列表"""
        with patch.object(scanner, 'rt') as mock_rt, \
             patch('core.scanner.MoneyFlowMonitor') as MockMonitor:
            
            # Mock 成交量 Top 列表
            mock_rt.get_top_volume_symbols.return_value = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            
            # Mock 资金流向
            mock_monitor = Mock()
            mock_monitor.get_money_flow_ranking.return_value = {
                'inflow_top20': [{'symbol': 'BTCUSDT'}, {'symbol': 'ETHUSDT'}],
                'outflow_top20': [{'symbol': 'BNBUSDT'}]
            }
            MockMonitor.return_value = mock_monitor
            
            symbols = scanner._get_scan_symbols()
            
            assert isinstance(symbols, set)
            assert 'BTCUSDT' in symbols
            assert 'ETHUSDT' in symbols
    
    def test_push_signals(self, scanner):
        """测试信号推送"""
        new_signals = [
            {
                'symbol': 'BTCUSDT',
                'strategy_name': 'Multi-Timeframe Resonance',
                'action': 'BUY',
                'direction': 'LONG',
                'current_price': 50000,
                'confidence': 75,
                'stop_loss_price': 49000,
                'take_profit_price': 52000,
                'signal_id': 'test_signal_1',
                'timestamp': datetime.now().isoformat(),
                'reason': 'Test signal'
            }
        ]
        
        mock_notifier = Mock()
        mock_notifier.send_text.return_value = {'success': True}
        scanner.notifier = mock_notifier
        
        mock_tracker = Mock()
        mock_tracker.get_active_signals.return_value = []
        scanner.tracker = mock_tracker
        
        # 推送信号
        scanner._push_signals(new_signals)
        
        # 验证通知器被调用
        mock_notifier.send_text.assert_called_once()
    
    def test_push_signals_with_dedup(self, scanner):
        """测试信号去重推送"""
        new_signals = [
            {
                'symbol': 'BTCUSDT',
                'strategy_name': 'Multi-Timeframe Resonance',
                'action': 'BUY',
                'direction': 'LONG',
                'current_price': 50000,
                'confidence': 75,
                'stop_loss_price': 49000,
                'take_profit_price': 52000,
                'signal_id': 'test_signal_1',
                'timestamp': datetime.now().isoformat(),
                'reason': 'Test signal'
            }
        ]
        
        # Mock 已有活跃信号
        mock_tracker = Mock()
        mock_tracker.get_active_signals.return_value = [
            {
                'symbol': 'BTCUSDT',
                'strategy_name': 'Multi-Timeframe Resonance',
                'action': 'BUY',
                'direction': 'LONG'
            }
        ]
        scanner.tracker = mock_tracker
        
        mock_notifier = Mock()
        scanner.notifier = mock_notifier
        
        # 推送信号（应该因为去重而不发送）
        scanner._push_signals(new_signals)
        
        # 验证通知器未被调用（去重）
        mock_notifier.send_text.assert_not_called()
    
    def test_close(self, scanner):
        """测试关闭资源"""
        mock_db = Mock()
        mock_tracker = Mock()
        scanner.db = mock_db
        scanner.tracker = mock_tracker
        
        scanner.close()
        
        mock_db.close.assert_called_once()
        mock_tracker.close.assert_called_once()


class TestSignalScannerIntegration:
    """SignalScanner 集成测试"""
    
    @pytest.mark.integration
    def test_full_scan_workflow(self):
        """测试完整扫描流程"""
        with patch('core.scanner.MarketDatabase'), \
             patch('core.scanner.RealtimeData'), \
             patch('core.scanner.SignalGenerator'), \
             patch('core.scanner.FeishuNotifier'), \
             patch('core.scanner.MoneyFlowMonitor'):
            
            scanner = SignalScanner(
                cache_file='cache/test_full_scan.json',
                max_workers=1
            )
            
            # Mock 扫描结果
            with patch.object(scanner, '_scan_symbol_strategies') as mock_scan:
                mock_scan.return_value = None  # 无信号
                
                result = scanner.scan(enable_notification=False)
                
                assert 'scanned_count' in result
                assert 'total_signals' in result
                assert 'new_signals' in result
                assert 'repeated_signals' in result
            
            scanner.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
