"""
信号报告模块

生成信号统计报告和性能分析。
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


class SignalReporter:
    """
    信号报告生成器
    
    生成信号统计、性能分析和历史回顾报告。
    """
    
    def __init__(self, tracker=None, db=None):
        """
        初始化报告生成器
        
        Args:
            tracker: SignalTracker 实例
            db: MarketDatabase 实例
        """
        if tracker is None:
            from .tracker import SignalTracker
            self.tracker = SignalTracker()
            self._own_tracker = True
        else:
            self.tracker = tracker
            self._own_tracker = False
        
        self.db = db
    
    def generate_daily_report(self, date: str = None) -> Dict:
        """
        生成日报
        
        Args:
            date: 日期字符串 (YYYY-MM-DD)，默认为今天
        
        Returns:
            日报字典
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        target_date = datetime.strptime(date, '%Y-%m-%d')
        start_str = target_date.strftime('%Y-%m-%d 00:00:00')
        end_str = target_date.strftime('%Y-%m-%d 23:59:59')
        
        active_signals = self.tracker.get_active_signals()
        stats = self.tracker.get_stats(days=1)
        
        # 筛选今日信号
        today_signals = []
        for signal in active_signals:
            try:
                signal_time = datetime.fromisoformat(signal.get('timestamp', ''))
                if target_date.date() == signal_time.date():
                    today_signals.append(signal)
            except Exception:
                pass
        
        closed_stats = stats.get('closed_signals', {})
        tp_stats = closed_stats.get('TAKE_PROFIT', {})
        sl_stats = closed_stats.get('STOP_LOSS', {})
        
        return {
            'report_type': 'daily',
            'date': date,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'new_signals': len(today_signals),
                'active_signals': stats.get('active_signals', 0),
                'closed_today': tp_stats.get('count', 0) + sl_stats.get('count', 0),
                'take_profit': tp_stats.get('count', 0),
                'stop_loss': sl_stats.get('count', 0)
            },
            'signals': today_signals,
            'performance': {
                'win_rate': self._calculate_win_rate(closed_stats),
                'avg_tp_pnl': tp_stats.get('avg_pnl', 0),
                'avg_sl_pnl': sl_stats.get('avg_pnl', 0)
            }
        }
    
    def generate_weekly_report(self) -> Dict:
        """
        生成周报
        
        Returns:
            周报字典
        """
        stats = self.tracker.get_stats(days=7)
        closed_stats = stats.get('closed_signals', {})
        
        tp_stats = closed_stats.get('TAKE_PROFIT', {})
        sl_stats = closed_stats.get('STOP_LOSS', {})
        
        return {
            'report_type': 'weekly',
            'period': 'last_7_days',
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_signals': stats.get('total_signals', 0),
                'active_signals': stats.get('active_signals', 0),
                'closed_signals': tp_stats.get('count', 0) + sl_stats.get('count', 0),
                'take_profit': tp_stats.get('count', 0),
                'stop_loss': sl_stats.get('count', 0)
            },
            'performance': {
                'win_rate': self._calculate_win_rate(closed_stats),
                'avg_tp_pnl': tp_stats.get('avg_pnl', 0),
                'avg_sl_pnl': sl_stats.get('avg_pnl', 0),
                'profit_factor': self._calculate_profit_factor(tp_stats, sl_stats)
            },
            'by_strategy': self._get_strategy_breakdown(7)
        }
    
    def generate_monthly_report(self) -> Dict:
        """
        生成月报
        
        Returns:
            月报字典
        """
        stats = self.tracker.get_stats(days=30)
        closed_stats = stats.get('closed_signals', {})
        
        tp_stats = closed_stats.get('TAKE_PROFIT', {})
        sl_stats = closed_stats.get('STOP_LOSS', {})
        
        return {
            'report_type': 'monthly',
            'period': 'last_30_days',
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_signals': stats.get('total_signals', 0),
                'active_signals': stats.get('active_signals', 0),
                'closed_signals': tp_stats.get('count', 0) + sl_stats.get('count', 0),
                'take_profit': tp_stats.get('count', 0),
                'stop_loss': sl_stats.get('count', 0)
            },
            'performance': {
                'win_rate': self._calculate_win_rate(closed_stats),
                'avg_tp_pnl': tp_stats.get('avg_pnl', 0),
                'avg_sl_pnl': sl_stats.get('avg_pnl', 0),
                'profit_factor': self._calculate_profit_factor(tp_stats, sl_stats),
                'total_pnl': self._calculate_total_pnl()
            },
            'by_strategy': self._get_strategy_breakdown(30),
            'trend': self._get_weekly_trend()
        }
    
    def _calculate_win_rate(self, closed_stats: Dict) -> float:
        """计算胜率"""
        tp_count = closed_stats.get('TAKE_PROFIT', {}).get('count', 0)
        sl_count = closed_stats.get('STOP_LOSS', {}).get('count', 0)
        total = tp_count + sl_count
        return (tp_count / total * 100) if total > 0 else 0
    
    def _calculate_profit_factor(self, tp_stats: Dict, sl_stats: Dict) -> float:
        """计算盈亏比"""
        tp_avg = tp_stats.get('avg_pnl', 0) or 0
        sl_avg = abs(sl_stats.get('avg_pnl', 0) or 0)
        
        if sl_avg == 0:
            return 0
        
        return tp_avg / sl_avg
    
    def _calculate_total_pnl(self) -> float:
        """计算总盈亏"""
        active_signals = self.tracker.get_active_signals()
        return sum(s.get('pnl_pct', 0) for s in active_signals)
    
    def _get_strategy_breakdown(self, days: int) -> Dict:
        """获取策略分类统计"""
        try:
            cursor = self.conn.cursor() if hasattr(self, 'conn') else None
            
            # 简化实现：从活跃信号中统计
            active_signals = self.tracker.get_active_signals()
            breakdown = {}
            
            for signal in active_signals:
                strategy = signal.get('strategy_name', 'Unknown')
                if strategy not in breakdown:
                    breakdown[strategy] = {
                        'count': 0,
                        'total_pnl': 0,
                        'signals': []
                    }
                
                breakdown[strategy]['count'] += 1
                breakdown[strategy]['total_pnl'] += signal.get('pnl_pct', 0)
                breakdown[strategy]['signals'].append(signal['symbol'])
            
            # 计算平均盈亏
            for strategy in breakdown:
                count = breakdown[strategy]['count']
                if count > 0:
                    breakdown[strategy]['avg_pnl'] = breakdown[strategy]['total_pnl'] / count
            
            return breakdown
        except Exception:
            return {}
    
    def _get_weekly_trend(self) -> List[Dict]:
        """获取周趋势"""
        trend = []
        today = datetime.now()
        
        for i in range(4):
            week_start = today - timedelta(days=(i + 1) * 7)
            week_end = today - timedelta(days=i * 7)
            
            stats = self.tracker.get_stats(days=(i + 1) * 7)
            closed_stats = stats.get('closed_signals', {})
            
            trend.append({
                'week': i + 1,
                'start_date': week_start.strftime('%Y-%m-%d'),
                'end_date': week_end.strftime('%Y-%m-%d'),
                'total_signals': stats.get('total_signals', 0),
                'closed': closed_stats.get('TAKE_PROFIT', {}).get('count', 0) + 
                         closed_stats.get('STOP_LOSS', {}).get('count', 0),
                'win_rate': self._calculate_win_rate(closed_stats)
            })
        
        return trend
    
    def export_report(self, report: Dict, output_path: str = None) -> str:
        """
        导出报告到文件
        
        Args:
            report: 报告字典
            output_path: 输出路径，默认为 reports/ 目录
        
        Returns:
            保存的文件路径
        """
        if output_path is None:
            output_dir = Path('reports')
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = output_dir / f"report_{report['report_type']}_{timestamp}.json"
        else:
            output_path = Path(output_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return str(output_path)
    
    def print_summary(self, report: Dict):
        """
        打印报告摘要
        
        Args:
            report: 报告字典
        """
        print(f"\n{'='*60}")
        print(f"{report['report_type'].upper()} REPORT")
        print(f"Generated: {report.get('generated_at', 'N/A')}")
        print(f"{'='*60}")
        
        summary = report.get('summary', {})
        print(f"\n📊 SUMMARY:")
        print(f"   Total Signals: {summary.get('total_signals', summary.get('new_signals', 0))}")
        print(f"   Active: {summary.get('active_signals', 0)}")
        print(f"   Closed: {summary.get('closed_signals', 0)}")
        print(f"   └─ Take Profit: {summary.get('take_profit', 0)}")
        print(f"   └─ Stop Loss: {summary.get('stop_loss', 0)}")
        
        perf = report.get('performance', {})
        if perf:
            print(f"\n📈 PERFORMANCE:")
            print(f"   Win Rate: {perf.get('win_rate', 0):.1f}%")
            if 'avg_tp_pnl' in perf:
                print(f"   Avg TP: {perf.get('avg_tp_pnl', 0):.2f}%")
            if 'avg_sl_pnl' in perf:
                print(f"   Avg SL: {perf.get('avg_sl_pnl', 0):.2f}%")
            if 'profit_factor' in perf:
                print(f"   Profit Factor: {perf.get('profit_factor', 0):.2f}")
        
        print(f"{'='*60}\n")
    
    def close(self):
        """关闭资源"""
        if self._own_tracker and self.tracker:
            self.tracker.close()
