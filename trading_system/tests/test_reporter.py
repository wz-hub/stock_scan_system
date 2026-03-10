"""
信号报告模块测试
测试 SignalReporter 类的核心功能
"""
import pytest
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.reporter import SignalReporter


class TestSignalReporter:
    """SignalReporter 测试类"""
    
    @pytest.fixture
    def mock_tracker(self):
        """创建 Mock 追踪器"""
        tracker = Mock()
        tracker.get_active_signals.return_value = []
        tracker.get_stats.return_value = {
            'total_signals': 0,
            'active_signals': 0,
            'closed_signals': {},
            'period_days': 7
        }
        return tracker
    
    @pytest.fixture
    def mock_db(self):
        """创建 Mock 数据库"""
        db = Mock()
        return db
    
    @pytest.fixture
    def reporter(self, mock_tracker, mock_db):
        """创建报告生成器实例"""
        reporter = SignalReporter(tracker=mock_tracker, db=mock_db)
        yield reporter
        reporter.close()
    
    def test_init_with_tracker(self, mock_tracker, mock_db):
        """测试使用现有追踪器初始化"""
        reporter = SignalReporter(tracker=mock_tracker, db=mock_db)
        
        assert reporter.tracker == mock_tracker
        assert reporter.db == mock_db
        assert reporter._own_tracker is False
    
    def test_init_without_tracker(self):
        """测试自动创建追踪器初始化"""
        with patch('core.reporter.SignalTracker') as MockTracker:
            mock_tracker = Mock()
            MockTracker.return_value = mock_tracker
            
            reporter = SignalReporter()
            
            assert reporter.tracker == mock_tracker
            assert reporter._own_tracker is True
            reporter.close()
    
    def test_generate_daily_report(self, reporter, mock_tracker):
        """测试生成日报"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        mock_tracker.get_active_signals.return_value = [
            {
                'symbol': 'BTC-USD',
                'strategy_name': 'Multi-Timeframe Resonance',
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        mock_tracker.get_stats.return_value = {
            'total_signals': 5,
            'active_signals': 3,
            'closed_signals': {
                'TAKE_PROFIT': {'count': 1, 'avg_pnl': 5.0},
                'STOP_LOSS': {'count': 1, 'avg_pnl': -3.0}
            }
        }
        
        report = reporter.generate_daily_report(date=today)
        
        assert report['report_type'] == 'daily'
        assert report['date'] == today
        assert 'generated_at' in report
        assert 'summary' in report
        assert 'performance' in report
        assert 'signals' in report
    
    def test_generate_daily_report_today(self, reporter, mock_tracker):
        """测试生成今日日报（不指定日期）"""
        mock_tracker.get_active_signals.return_value = []
        mock_tracker.get_stats.return_value = {
            'total_signals': 0,
            'active_signals': 0,
            'closed_signals': {}
        }
        
        report = reporter.generate_daily_report()
        
        today = datetime.now().strftime('%Y-%m-%d')
        assert report['date'] == today
        assert report['report_type'] == 'daily'
    
    def test_generate_weekly_report(self, reporter, mock_tracker):
        """测试生成周报"""
        mock_tracker.get_stats.return_value = {
            'total_signals': 20,
            'active_signals': 5,
            'closed_signals': {
                'TAKE_PROFIT': {'count': 10, 'avg_pnl': 5.0},
                'STOP_LOSS': {'count': 5, 'avg_pnl': -3.0}
            }
        }
        
        report = reporter.generate_weekly_report()
        
        assert report['report_type'] == 'weekly'
        assert report['period'] == 'last_7_days'
        assert report['summary']['total_signals'] == 20
        assert report['summary']['active_signals'] == 5
        assert report['performance']['win_rate'] > 0
    
    def test_generate_monthly_report(self, reporter, mock_tracker):
        """测试生成月报"""
        mock_tracker.get_active_signals.return_value = [
            {
                'symbol': 'BTC-USD',
                'strategy_name': 'Multi-Timeframe Resonance',
                'pnl_pct': 2.5
            }
        ]
        
        mock_tracker.get_stats.return_value = {
            'total_signals': 50,
            'active_signals': 10,
            'closed_signals': {
                'TAKE_PROFIT': {'count': 25, 'avg_pnl': 6.0},
                'STOP_LOSS': {'count': 15, 'avg_pnl': -3.5}
            }
        }
        
        report = reporter.generate_monthly_report()
        
        assert report['report_type'] == 'monthly'
        assert report['period'] == 'last_30_days'
        assert report['summary']['total_signals'] == 50
        assert 'trend' in report
        assert len(report['trend']) == 4  # 4 周趋势
    
    def test_calculate_win_rate(self, reporter):
        """测试胜率计算"""
        closed_stats = {
            'TAKE_PROFIT': {'count': 8, 'avg_pnl': 5.0},
            'STOP_LOSS': {'count': 2, 'avg_pnl': -3.0}
        }
        
        win_rate = reporter._calculate_win_rate(closed_stats)
        
        assert abs(win_rate - 80.0) < 0.01
    
    def test_calculate_win_rate_no_closed(self, reporter):
        """测试无平仓时的胜率"""
        closed_stats = {}
        
        win_rate = reporter._calculate_win_rate(closed_stats)
        
        assert win_rate == 0
    
    def test_calculate_profit_factor(self, reporter):
        """测试盈亏比计算"""
        tp_stats = {'avg_pnl': 5.0}
        sl_stats = {'avg_pnl': -2.5}
        
        pf = reporter._calculate_profit_factor(tp_stats, sl_stats)
        
        assert abs(pf - 2.0) < 0.01
    
    def test_calculate_profit_factor_zero_loss(self, reporter):
        """测试零亏损时的盈亏比"""
        tp_stats = {'avg_pnl': 5.0}
        sl_stats = {'avg_pnl': 0}
        
        pf = reporter._calculate_profit_factor(tp_stats, sl_stats)
        
        assert pf == 0
    
    def test_calculate_total_pnl(self, reporter, mock_tracker):
        """测试总盈亏计算"""
        mock_tracker.get_active_signals.return_value = [
            {'pnl_pct': 2.5},
            {'pnl_pct': -1.0},
            {'pnl_pct': 3.5}
        ]
        
        total_pnl = reporter._calculate_total_pnl()
        
        assert abs(total_pnl - 5.0) < 0.01
    
    def test_get_strategy_breakdown(self, reporter, mock_tracker):
        """测试策略分类统计"""
        mock_tracker.get_active_signals.return_value = [
            {'strategy_name': 'Multi-Timeframe Resonance', 'symbol': 'BTC-USD', 'pnl_pct': 2.0},
            {'strategy_name': 'Multi-Timeframe Resonance', 'symbol': 'ETH-USD', 'pnl_pct': 3.0},
            {'strategy_name': 'Money Flow Tracker', 'symbol': 'BNB-USD', 'pnl_pct': -1.0}
        ]
        
        breakdown = reporter._get_strategy_breakdown(days=7)
        
        assert 'Multi-Timeframe Resonance' in breakdown
        assert 'Money Flow Tracker' in breakdown
        assert breakdown['Multi-Timeframe Resonance']['count'] == 2
        assert breakdown['Multi-Timeframe Resonance']['count'] == 2
    
    def test_get_weekly_trend(self, reporter, mock_tracker):
        """测试周趋势获取"""
        mock_tracker.get_stats.return_value = {
            'total_signals': 10,
            'active_signals': 5,
            'closed_signals': {
                'TAKE_PROFIT': {'count': 3, 'avg_pnl': 5.0},
                'STOP_LOSS': {'count': 2, 'avg_pnl': -3.0}
            }
        }
        
        trend = reporter._get_weekly_trend()
        
        assert len(trend) == 4
        assert 'week' in trend[0]
        assert 'start_date' in trend[0]
        assert 'end_date' in trend[0]
        assert 'win_rate' in trend[0]
    
    def test_export_report(self, reporter, tmp_path):
        """测试导出报告到文件"""
        report = {
            'report_type': 'test',
            'generated_at': datetime.now().isoformat(),
            'summary': {'total_signals': 10}
        }
        
        output_path = str(tmp_path / 'test_report.json')
        result_path = reporter.export_report(report, output_path)
        
        assert os.path.exists(result_path)
        
        with open(result_path) as f:
            loaded_report = json.load(f)
        
        assert loaded_report['report_type'] == 'test'
        assert loaded_report['summary']['total_signals'] == 10
    
    def test_export_report_default_path(self, reporter):
        """测试默认路径导出报告"""
        report = {
            'report_type': 'daily',
            'generated_at': datetime.now().isoformat(),
            'summary': {'total_signals': 5}
        }
        
        # 在临时目录测试
        import tempfile
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            
            try:
                result_path = reporter.export_report(report)
                assert os.path.exists(result_path)
                assert 'reports' in result_path
            finally:
                os.chdir(original_cwd)
    
    def test_print_summary(self, reporter, capsys):
        """测试打印报告摘要"""
        report = {
            'report_type': 'weekly',
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_signals': 20,
                'active_signals': 5,
                'closed_signals': 15,
                'take_profit': 10,
                'stop_loss': 5
            },
            'performance': {
                'win_rate': 66.67,
                'avg_tp_pnl': 5.0,
                'avg_sl_pnl': -3.0,
                'profit_factor': 1.67
            }
        }
        
        reporter.print_summary(report)
        
        captured = capsys.readouterr()
        assert 'WEEKLY REPORT' in captured.out
        assert 'Total Signals' in captured.out
        assert 'Win Rate' in captured.out
    
    def test_close_with_own_tracker(self):
        """测试关闭自有追踪器"""
        with patch('core.reporter.SignalTracker') as MockTracker:
            mock_tracker = Mock()
            MockTracker.return_value = mock_tracker
            
            reporter = SignalReporter()
            reporter.close()
            
            mock_tracker.close.assert_called_once()
    
    def test_close_without_own_tracker(self, mock_tracker):
        """测试关闭非自有追踪器"""
        mock_db = Mock()
        reporter = SignalReporter(tracker=mock_tracker, db=mock_db)
        reporter.close()
        
        # 不应调用 close
        mock_tracker.close.assert_not_called()


class TestSignalReporterIntegration:
    """SignalReporter 集成测试"""
    
    @pytest.mark.integration
    def test_full_report_generation(self):
        """测试完整报告生成流程"""
        with patch('core.reporter.SignalTracker') as MockTracker:
            mock_tracker = Mock()
            mock_tracker.get_active_signals.return_value = [
                {
                    'symbol': 'BTC-USD',
                    'strategy_name': 'Multi-Timeframe Resonance',
                    'pnl_pct': 2.5,
                    'timestamp': datetime.now().isoformat()
                }
            ]
            mock_tracker.get_stats.return_value = {
                'total_signals': 10,
                'active_signals': 1,
                'closed_signals': {
                    'TAKE_PROFIT': {'count': 6, 'avg_pnl': 5.0},
                    'STOP_LOSS': {'count': 3, 'avg_pnl': -3.0}
                }
            }
            MockTracker.return_value = mock_tracker
            
            reporter = SignalReporter()
            
            # 生成日报
            daily = reporter.generate_daily_report()
            assert daily['report_type'] == 'daily'
            
            # 生成周报
            weekly = reporter.generate_weekly_report()
            assert weekly['report_type'] == 'weekly'
            
            # 生成月报
            monthly = reporter.generate_monthly_report()
            assert monthly['report_type'] == 'monthly'
            
            # 导出报告
            import tempfile
            with tempfile.TemporaryDirectory() as tmp_dir:
                output_path = os.path.join(tmp_dir, 'test_report.json')
                result_path = reporter.export_report(monthly, output_path)
                assert os.path.exists(result_path)
            
            reporter.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
