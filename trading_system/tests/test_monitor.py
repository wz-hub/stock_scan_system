"""
信号监控模块测试
测试 SignalMonitor 类的核心功能
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.monitor import SignalMonitor


class TestSignalMonitor:
    """SignalMonitor 测试类"""
    
    @pytest.fixture
    def mock_tracker(self):
        """创建 Mock 追踪器"""
        tracker = Mock()
        tracker.get_active_signals.return_value = []
        tracker.update_price.return_value = 0
        tracker.check_exit_conditions.return_value = []
        tracker.get_stats.return_value = {
            'total_signals': 0,
            'active_signals': 0,
            'closed_signals': {},
            'period_days': 7
        }
        return tracker
    
    @pytest.fixture
    def monitor(self, mock_tracker):
        """创建监控器实例"""
        monitor = SignalMonitor(tracker=mock_tracker)
        yield monitor
        monitor.close()
    
    def test_init_with_tracker(self, mock_tracker):
        """测试使用现有追踪器初始化"""
        monitor = SignalMonitor(tracker=mock_tracker)
        
        assert monitor.tracker == mock_tracker
        assert monitor._own_tracker is False
    
    def test_init_without_tracker(self):
        """测试自动创建追踪器初始化"""
        with patch('core.monitor.SignalTracker') as MockTracker:
            mock_tracker = Mock()
            MockTracker.return_value = mock_tracker
            
            monitor = SignalMonitor()
            
            assert monitor.tracker == mock_tracker
            assert monitor._own_tracker is True
            monitor.close()
    
    def test_monitor_symbols(self, monitor, mock_tracker):
        """测试监控交易对价格"""
        symbols = ['BTC-USD', 'ETH-USD']
        
        # Mock 实时数据
        mock_df = pd.DataFrame({
            'close': [50000.0, 3000.0]
        })
        
        with patch('core.monitor.RealtimeData') as MockRT:
            mock_rt = Mock()
            mock_rt.get_binance_klines.side_effect = [
                pd.DataFrame({'close': [50000.0]}),
                pd.DataFrame({'close': [3000.0]})
            ]
            MockRT.return_value = mock_rt
            
            mock_tracker.update_price.return_value = 1
            
            results = monitor.monitor_symbols(symbols)
            
            assert 'BTC-USD' in results
            assert 'ETH-USD' in results
            assert results['BTC-USD']['price'] == 50000.0
            assert results['ETH-USD']['price'] == 3000.0
            assert 'timestamp' in results['BTC-USD']
    
    def test_monitor_symbols_error_handling(self, monitor, mock_tracker):
        """测试监控错误处理"""
        symbols = ['INVALID-SYMBOL']
        
        with patch('core.monitor.RealtimeData') as MockRT:
            mock_rt = Mock()
            mock_rt.get_binance_klines.side_effect = Exception("API Error")
            MockRT.return_value = mock_rt
            
            results = monitor.monitor_symbols(symbols)
            
            assert 'INVALID-SYMBOL' in results
            assert 'error' in results['INVALID-SYMBOL']
    
    def test_check_all_exits(self, monitor, mock_tracker):
        """测试检查所有平仓条件"""
        mock_closed = [
            {
                'symbol': 'BTC-USD',
                'strategy': 'Test Strategy',
                'exit_reason': 'STOP_LOSS',
                'exit_price': 49000.0
            }
        ]
        mock_tracker.check_exit_conditions.return_value = mock_closed
        
        closed = monitor.check_all_exits()
        
        assert len(closed) == 1
        assert closed[0]['exit_reason'] == 'STOP_LOSS'
    
    def test_get_active_summary_empty(self, monitor, mock_tracker):
        """测试获取空活跃信号摘要"""
        mock_tracker.get_active_signals.return_value = []
        
        summary = monitor.get_active_summary()
        
        assert summary['total_active'] == 0
        assert summary['signals'] == []
        assert summary['total_pnl'] == 0
        assert 'timestamp' in summary
    
    def test_get_active_summary_with_signals(self, monitor, mock_tracker):
        """测试获取有信号的活跃摘要"""
        mock_tracker.get_active_signals.return_value = [
            {
                'symbol': 'BTC-USD',
                'strategy_name': 'Multi-Timeframe Resonance',
                'action': 'BUY',
                'direction': 'LONG',
                'entry_price': 50000.0,
                'pnl_pct': 2.5
            },
            {
                'symbol': 'ETH-USD',
                'strategy_name': 'Money Flow Tracker',
                'action': 'SELL',
                'direction': 'SHORT',
                'entry_price': 3000.0,
                'pnl_pct': -1.0
            }
        ]
        
        summary = monitor.get_active_summary()
        
        assert summary['total_active'] == 2
        assert summary['total_pnl'] == 1.5
        assert abs(summary['avg_pnl'] - 0.75) < 0.01
        assert 'by_strategy' in summary
        assert len(summary['by_strategy']) == 2
    
    def test_get_risk_alerts_loss_warning(self, monitor, mock_tracker):
        """测试获取亏损预警"""
        mock_tracker.get_active_signals.return_value = [
            {
                'symbol': 'BTC-USD',
                'strategy_name': 'Test Strategy',
                'direction': 'LONG',
                'entry_price': 50000.0,
                'pnl_pct': -6.0,
                'stop_loss': 49000.0
            }
        ]
        
        alerts = monitor.get_risk_alerts(threshold=-5.0)
        
        assert len(alerts) == 1
        assert alerts[0]['alert_type'] == 'LOSS_WARNING'
        assert alerts[0]['pnl_pct'] == -6.0
    
    def test_get_risk_alerts_profit_warning(self, monitor, mock_tracker):
        """测试获取止盈预警"""
        mock_tracker.get_active_signals.return_value = [
            {
                'symbol': 'ETH-USD',
                'strategy_name': 'Test Strategy',
                'direction': 'LONG',
                'entry_price': 3000.0,
                'pnl_pct': 8.0,
                'take_profit': 3300.0  # 10% 止盈
            }
        ]
        
        alerts = monitor.get_risk_alerts()
        
        # 达到止盈的 90% 应触发预警
        assert len(alerts) == 1
        assert alerts[0]['alert_type'] == 'PROFIT_WARNING'
    
    def test_get_risk_alerts_short_position(self, monitor, mock_tracker):
        """测试空头头寸预警"""
        mock_tracker.get_active_signals.return_value = [
            {
                'symbol': 'BTC-USD',
                'strategy_name': 'Test Strategy',
                'direction': 'SHORT',
                'entry_price': 50000.0,
                'pnl_pct': 4.5,  # 空头盈利 4.5%
            }
        ]
        
        alerts = monitor.get_risk_alerts(threshold=-5.0)
        
        # 空头盈利达到止盈 90% 应触发预警
        assert len(alerts) == 1
        assert alerts[0]['alert_type'] == 'PROFIT_WARNING'
    
    def test_get_performance_report(self, monitor, mock_tracker):
        """测试获取性能报告"""
        mock_tracker.get_stats.return_value = {
            'total_signals': 20,
            'active_signals': 5,
            'closed_signals': {
                'TAKE_PROFIT': {'count': 10, 'avg_pnl': 5.0},
                'STOP_LOSS': {'count': 5, 'avg_pnl': -3.0}
            }
        }
        
        report = monitor.get_performance_report(days=7)
        
        assert report['period_days'] == 7
        assert report['total_signals'] == 20
        assert report['active_signals'] == 5
        assert report['closed_signals'] == 15
        assert report['take_profit'] == 10
        assert report['stop_loss'] == 5
        assert abs(report['win_rate'] - 66.67) < 0.01
        assert report['avg_tp_pnl'] == 5.0
        assert report['avg_sl_pnl'] == -3.0
    
    def test_get_performance_report_no_closed(self, monitor, mock_tracker):
        """测试无平仓时的性能报告"""
        mock_tracker.get_stats.return_value = {
            'total_signals': 5,
            'active_signals': 5,
            'closed_signals': {}
        }
        
        report = monitor.get_performance_report()
        
        assert report['win_rate'] == 0
        assert report['closed_signals'] == 0
    
    def test_close_with_own_tracker(self):
        """测试关闭自有追踪器"""
        with patch('core.monitor.SignalTracker') as MockTracker:
            mock_tracker = Mock()
            MockTracker.return_value = mock_tracker
            
            monitor = SignalMonitor()
            monitor.close()
            
            mock_tracker.close.assert_called_once()
    
    def test_close_without_own_tracker(self, mock_tracker):
        """测试关闭非自有追踪器"""
        monitor = SignalMonitor(tracker=mock_tracker)
        monitor.close()
        
        # 不应调用 close（因为不是自有追踪器）
        mock_tracker.close.assert_not_called()


class TestSignalMonitorIntegration:
    """SignalMonitor 集成测试"""
    
    @pytest.mark.integration
    def test_full_monitoring_workflow(self):
        """测试完整监控流程"""
        with patch('core.monitor.SignalTracker') as MockTracker:
            mock_tracker = Mock()
            mock_tracker.get_active_signals.return_value = [
                {
                    'symbol': 'BTC-USD',
                    'strategy_name': 'Multi-Timeframe Resonance',
                    'direction': 'LONG',
                    'entry_price': 50000.0,
                    'pnl_pct': 1.5,
                    'stop_loss': 49000.0,
                    'take_profit': 52000.0
                }
            ]
            mock_tracker.update_price.return_value = 1
            MockTracker.return_value = mock_tracker
            
            monitor = SignalMonitor()
            
            # 监控价格
            with patch('core.monitor.RealtimeData') as MockRT:
                mock_rt = Mock()
                mock_rt.get_binance_klines.return_value = pd.DataFrame({'close': [50500.0]})
                MockRT.return_value = mock_rt
                
                results = monitor.monitor_symbols(['BTC-USD'])
                assert results['BTC-USD']['price'] == 50500.0
            
            # 获取摘要
            summary = monitor.get_active_summary()
            assert summary['total_active'] == 1
            
            # 获取性能报告
            mock_tracker.get_stats.return_value = {
                'total_signals': 1,
                'active_signals': 1,
                'closed_signals': {}
            }
            report = monitor.get_performance_report()
            assert report['total_signals'] == 1
            
            monitor.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
