"""
信号追踪模块测试
测试 SignalTracker 类的核心功能
"""
import pytest
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tracker import SignalTracker


class TestSignalTracker:
    """SignalTracker 测试类"""
    
    @pytest.fixture
    def tracker_db_path(self, tmp_path):
        """创建临时数据库路径"""
        return str(tmp_path / 'test_signals.db')
    
    @pytest.fixture
    def tracker(self, tracker_db_path):
        """创建追踪器实例"""
        tracker = SignalTracker(db_path=tracker_db_path)
        yield tracker
        tracker.close()
    
    def test_init(self, tracker, tracker_db_path):
        """测试初始化"""
        assert tracker is not None
        assert tracker.db_path == tracker_db_path
        assert tracker.conn is not None
    
    def test_create_tables(self, tracker):
        """测试表创建"""
        cursor = tracker.conn.cursor()
        
        # 检查 signals 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals'")
        result = cursor.fetchone()
        assert result is not None
        
        # 检查索引是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_status'")
        assert cursor.fetchone() is not None
    
    def test_add_signal(self, tracker):
        """测试添加信号"""
        signal = {
            'signal_id': 'test_001',
            'symbol': 'BTC-USD',
            'strategy_name': 'Multi-Timeframe Resonance',
            'action': 'BUY',
            'direction': 'LONG',
            'entry_price': 50000.0,
            'stop_loss_price': 49000.0,
            'take_profit_price': 52000.0,
            'confidence': 75.0,
            'timestamp': datetime.now().isoformat()
        }
        
        result = tracker.add_signal(signal)
        
        assert result is True
        
        # 验证信号已保存
        active_signals = tracker.get_active_signals()
        assert len(active_signals) == 1
        assert active_signals[0]['symbol'] == 'BTC-USD'
        assert active_signals[0]['strategy_name'] == 'Multi-Timeframe Resonance'
    
    def test_add_duplicate_signal(self, tracker):
        """测试添加重复信号"""
        signal = {
            'signal_id': 'test_002',
            'symbol': 'ETH-USD',
            'strategy_name': 'Money Flow Tracker',
            'action': 'SELL',
            'direction': 'SHORT',
            'entry_price': 3000.0,
            'stop_loss_price': 3100.0,
            'take_profit_price': 2800.0,
            'confidence': 70.0,
            'timestamp': datetime.now().isoformat()
        }
        
        # 第一次添加
        result1 = tracker.add_signal(signal)
        assert result1 is True
        
        # 第二次添加（重复）
        result2 = tracker.add_signal(signal)
        assert result2 is False
        
        # 验证只有一个信号
        active_signals = tracker.get_active_signals()
        assert len(active_signals) == 1
    
    def test_get_active_signals(self, tracker):
        """测试获取活跃信号"""
        # 添加多个信号
        signals = [
            {
                'signal_id': f'test_{i}',
                'symbol': f'BTC-{i}',
                'strategy_name': 'Test Strategy',
                'action': 'BUY',
                'direction': 'LONG',
                'entry_price': 50000.0,
                'stop_loss_price': 49000.0,
                'take_profit_price': 52000.0,
                'confidence': 75.0,
                'timestamp': datetime.now().isoformat()
            }
            for i in range(3)
        ]
        
        for signal in signals:
            tracker.add_signal(signal)
        
        active = tracker.get_active_signals()
        
        assert len(active) == 3
        # 验证按时间倒序
        assert active[0]['symbol'] == 'BTC-2'
    
    def test_update_price(self, tracker):
        """测试更新价格"""
        signal = {
            'signal_id': 'test_price',
            'symbol': 'BTC-USD',
            'strategy_name': 'Test Strategy',
            'action': 'BUY',
            'direction': 'LONG',
            'entry_price': 50000.0,
            'stop_loss_price': 49000.0,
            'take_profit_price': 52000.0,
            'confidence': 75.0,
            'timestamp': datetime.now().isoformat()
        }
        tracker.add_signal(signal)
        
        # 价格上涨 2%
        updated = tracker.update_price('BTC-USD', 51000.0)
        
        assert updated == 1
        
        active_signals = tracker.get_active_signals()
        assert abs(active_signals[0]['pnl_pct'] - 2.0) < 0.01
    
    def test_update_price_short(self, tracker):
        """测试更新空头信号价格"""
        signal = {
            'signal_id': 'test_short',
            'symbol': 'ETH-USD',
            'strategy_name': 'Test Strategy',
            'action': 'SELL',
            'direction': 'SHORT',
            'entry_price': 3000.0,
            'stop_loss_price': 3100.0,
            'take_profit_price': 2800.0,
            'confidence': 70.0,
            'timestamp': datetime.now().isoformat()
        }
        tracker.add_signal(signal)
        
        # 价格下跌 3%（空头盈利）
        updated = tracker.update_price('ETH-USD', 2910.0)
        
        assert updated == 1
        
        active_signals = tracker.get_active_signals()
        assert abs(active_signals[0]['pnl_pct'] - 3.0) < 0.01
    
    def test_check_exit_conditions_stop_loss(self, tracker):
        """测试止损平仓"""
        signal = {
            'signal_id': 'test_sl',
            'symbol': 'BTC-USD',
            'strategy_name': 'Test Strategy',
            'action': 'BUY',
            'direction': 'LONG',
            'entry_price': 50000.0,
            'stop_loss': 49800.0,  # 止损价
            'take_profit': 55000.0,  # 止盈价设高一些
            'confidence': 75.0,
            'timestamp': datetime.now().isoformat()
        }
        tracker.add_signal(signal)
        
        # Mock 实时数据 - 价格低于止损
        import pandas as pd
        mock_df = pd.DataFrame({
            'close': [49700.0]  # 低于止损价 49800
        })
        
        with patch('realtime_data.RealtimeData') as MockRT:
            mock_rt = Mock()
            # Mock get_active_signals 返回我们的信号
            mock_rt.get_binance_klines.return_value = mock_df
            MockRT.return_value = mock_rt
            
            closed = tracker.check_exit_conditions()
            
            # 应该有平仓信号
            assert len(closed) >= 1
            assert closed[0]['symbol'] == 'BTC-USD'
    
    def test_check_exit_conditions_take_profit(self, tracker):
        """测试止盈平仓"""
        signal = {
            'signal_id': 'test_tp',
            'symbol': 'ETH-USD',
            'strategy_name': 'Test Strategy',
            'action': 'BUY',
            'direction': 'LONG',
            'entry_price': 3000.0,
            'stop_loss': 2900.0,
            'take_profit': 3300.0,
            'confidence': 75.0,
            'timestamp': datetime.now().isoformat()
        }
        tracker.add_signal(signal)
        
        # Mock 实时数据
        import pandas as pd
        mock_df = pd.DataFrame({
            'close': [3350.0]  # 高于止盈价
        })
        
        with patch('realtime_data.RealtimeData') as MockRT:
            mock_rt = Mock()
            mock_rt.get_binance_klines.return_value = mock_df
            MockRT.return_value = mock_rt
            
            closed = tracker.check_exit_conditions()
            
            assert len(closed) == 1
            assert closed[0]['exit_reason'] == 'TAKE_PROFIT'
    
    def test_close_signal(self, tracker):
        """测试手动平仓"""
        signal = {
            'signal_id': 'test_manual',
            'symbol': 'BTC-USD',
            'strategy_name': 'Test Strategy',
            'action': 'BUY',
            'direction': 'LONG',
            'entry_price': 50000.0,
            'stop_loss': 49000.0,
            'take_profit': 52000.0,
            'confidence': 75.0,
            'timestamp': datetime.now().isoformat()
        }
        tracker.add_signal(signal)
        
        # 手动平仓
        tracker.close_signal('BTC-USD', 'Test Strategy', 51000.0, 'MANUAL')
        
        # 验证信号已平仓
        active_signals = tracker.get_active_signals()
        assert len(active_signals) == 0
    
    def test_get_stats(self, tracker):
        """测试获取统计数据"""
        # 添加多个信号
        for i in range(5):
            signal = {
                'signal_id': f'stats_{i}',
                'symbol': f'BTC-{i}',
                'strategy_name': 'Test Strategy',
                'action': 'BUY',
                'direction': 'LONG',
                'entry_price': 50000.0,
                'stop_loss': 49000.0,
                'take_profit': 52000.0,
                'confidence': 75.0,
                'timestamp': datetime.now().isoformat()
            }
            tracker.add_signal(signal)
        
        stats = tracker.get_stats(days=7)
        
        assert 'total_signals' in stats
        assert 'active_signals' in stats
        assert 'closed_signals' in stats
        assert 'period_days' in stats
        assert stats['total_signals'] == 5
        assert stats['active_signals'] == 5
    
    def test_context_manager(self, tracker_db_path):
        """测试上下文管理器"""
        with SignalTracker(db_path=tracker_db_path) as tracker:
            signal = {
                'signal_id': 'ctx_test',
                'symbol': 'BTC-USD',
                'strategy_name': 'Test Strategy',
                'action': 'BUY',
                'direction': 'LONG',
                'entry_price': 50000.0,
                'stop_loss': 49000.0,
                'take_profit': 52000.0,
                'confidence': 75.0,
                'timestamp': datetime.now().isoformat()
            }
            tracker.add_signal(signal)
            
            active = tracker.get_active_signals()
            assert len(active) == 1
        
        # 退出上下文后数据库应关闭
        # 验证文件存在
        assert os.path.exists(tracker_db_path)


class TestSignalTrackerEdgeCases:
    """SignalTracker 边界测试"""
    
    @pytest.fixture
    def tracker(self, tmp_path):
        """创建追踪器实例"""
        tracker_path = str(tmp_path / 'test_edge.db')
        tracker = SignalTracker(db_path=tracker_path)
        yield tracker
        tracker.close()
    
    def test_empty_active_signals(self, tracker):
        """测试空活跃信号列表"""
        active = tracker.get_active_signals()
        assert active == []
    
    def test_update_nonexistent_symbol(self, tracker):
        """测试更新不存在的交易对"""
        updated = tracker.update_price('NONEXISTENT', 1000.0)
        assert updated == 0
    
    def test_add_signal_with_missing_fields(self, tracker):
        """测试添加缺少字段的信号"""
        signal = {
            'signal_id': 'incomplete',
            'symbol': 'BTC-USD'
            # 缺少其他字段
        }
        
        # 应该能处理（使用默认值）
        result = tracker.add_signal(signal)
        assert result is True
    
    def test_database_connection_error(self, tmp_path):
        """测试数据库连接错误处理"""
        invalid_path = str(tmp_path / 'nonexistent' / 'test.db')
        
        # 应该自动创建目录
        tracker = SignalTracker(db_path=invalid_path)
        assert tracker is not None
        tracker.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
