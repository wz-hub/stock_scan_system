"""
信号监控模块

监控活跃信号的价格变化和盈亏状态。
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


class SignalMonitor:
    """
    信号监控器
    
    实时监控活跃信号的价格、盈亏和状态变化。
    """
    
    def __init__(self, tracker=None):
        """
        初始化监控器
        
        Args:
            tracker: SignalTracker 实例，如果为 None 则自动创建
        """
        if tracker is None:
            from .tracker import SignalTracker
            self.tracker = SignalTracker()
            self._own_tracker = True
        else:
            self.tracker = tracker
            self._own_tracker = False
        
        self._last_prices = {}
    
    def monitor_symbols(self, symbols: List[str]) -> Dict:
        """
        监控指定交易对的价格
        
        Args:
            symbols: 交易对列表
        
        Returns:
            价格更新结果
        """
        from realtime_data import RealtimeData
        rt = RealtimeData()
        
        results = {}
        for symbol in symbols:
            try:
                # 获取最新价格
                binance_symbol = symbol.replace('-USD', 'USDT')
                df = rt.get_binance_klines(binance_symbol, interval='1m', limit=1)
                
                if df.empty:
                    continue
                
                current_price = float(df['close'].iloc[-1])
                self._last_prices[symbol] = current_price
                
                # 更新追踪器中的价格
                updated = self.tracker.update_price(symbol, current_price)
                
                results[symbol] = {
                    'price': current_price,
                    'updated_signals': updated,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                results[symbol] = {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        return results
    
    def check_all_exits(self) -> List[Dict]:
        """
        检查所有信号的平仓条件
        
        Returns:
            平仓信号列表
        """
        return self.tracker.check_exit_conditions()
    
    def get_active_summary(self) -> Dict:
        """
        获取活跃信号摘要
        
        Returns:
            活跃信号摘要字典
        """
        active_signals = self.tracker.get_active_signals()
        
        if not active_signals:
            return {
                'total_active': 0,
                'signals': [],
                'total_pnl': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # 按策略分组
        by_strategy = {}
        total_pnl = 0
        
        for signal in active_signals:
            strategy = signal.get('strategy_name', 'Unknown')
            if strategy not in by_strategy:
                by_strategy[strategy] = []
            
            by_strategy[strategy].append(signal)
            total_pnl += signal.get('pnl_pct', 0)
        
        avg_pnl = total_pnl / len(active_signals) if active_signals else 0
        
        return {
            'total_active': len(active_signals),
            'by_strategy': {k: len(v) for k, v in by_strategy.items()},
            'signals': active_signals,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_risk_alerts(self, threshold: float = -5.0) -> List[Dict]:
        """
        获取风险预警信号
        
        Args:
            threshold: 盈亏阈值，低于此值触发预警
        
        Returns:
            风险信号列表
        """
        active_signals = self.tracker.get_active_signals()
        alerts = []
        
        for signal in active_signals:
            pnl_pct = signal.get('pnl_pct', 0)
            
            # 检查是否接近止损
            if pnl_pct <= threshold:
                alerts.append({
                    'symbol': signal['symbol'],
                    'strategy': signal['strategy_name'],
                    'pnl_pct': pnl_pct,
                    'direction': signal['direction'],
                    'entry_price': signal['entry_price'],
                    'stop_loss': signal['stop_loss'],
                    'alert_type': 'LOSS_WARNING'
                })
            
            # 检查是否接近止盈
            entry_price = signal['entry_price']
            take_profit = signal['take_profit']
            
            if entry_price > 0 and take_profit > 0:
                if signal['direction'] == 'LONG':
                    current_ratio = (signal.get('pnl_pct', 0) + 100) / 100
                    target_ratio = take_profit / entry_price
                    if current_ratio >= target_ratio * 0.9:  # 达到止盈的 90%
                        alerts.append({
                            'symbol': signal['symbol'],
                            'strategy': signal['strategy_name'],
                            'pnl_pct': pnl_pct,
                            'direction': signal['direction'],
                            'alert_type': 'PROFIT_WARNING'
                        })
                else:
                    # SHORT 方向
                    if pnl_pct >= abs(threshold) * 0.9:  # 达到止盈的 90%
                        alerts.append({
                            'symbol': signal['symbol'],
                            'strategy': signal['strategy_name'],
                            'pnl_pct': pnl_pct,
                            'direction': signal['direction'],
                            'alert_type': 'PROFIT_WARNING'
                        })
        
        return alerts
    
    def get_performance_report(self, days: int = 7) -> Dict:
        """
        获取性能报告
        
        Args:
            days: 统计天数
        
        Returns:
            性能报告字典
        """
        stats = self.tracker.get_stats(days)
        
        closed_signals = stats.get('closed_signals', {})
        take_profit_stats = closed_signals.get('TAKE_PROFIT', {})
        stop_loss_stats = closed_signals.get('STOP_LOSS', {})
        
        tp_count = take_profit_stats.get('count', 0)
        sl_count = stop_loss_stats.get('count', 0)
        total_closed = tp_count + sl_count
        
        win_rate = (tp_count / total_closed * 100) if total_closed > 0 else 0
        
        return {
            'period_days': days,
            'total_signals': stats.get('total_signals', 0),
            'active_signals': stats.get('active_signals', 0),
            'closed_signals': total_closed,
            'take_profit': tp_count,
            'stop_loss': sl_count,
            'win_rate': win_rate,
            'avg_tp_pnl': take_profit_stats.get('avg_pnl', 0),
            'avg_sl_pnl': stop_loss_stats.get('avg_pnl', 0),
            'timestamp': datetime.now().isoformat()
        }
    
    def close(self):
        """关闭资源"""
        if self._own_tracker and self.tracker:
            self.tracker.close()
