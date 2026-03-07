# -*- coding: utf-8 -*-
"""
增强版回测系统

功能：
- 多策略回测
- 绩效分析（夏普比率/最大回撤/胜率）
- 参数优化
- 可视化报告
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class EnhancedBacktester:
    """增强版回测引擎"""
    
    def __init__(self, initial_capital: float = 100000):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.results = {}
    
    def run(self, strategy, data: pd.DataFrame, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        执行回测
        
        Args:
            strategy: 策略实例
            data: 历史数据（包含 open/high/low/close/volume）
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            回测结果字典
        """
        logger.info(f"Starting backtest for {strategy.name} from {start_date} to {end_date}")
        
        # 过滤日期范围
        data = data[(data['date'] >= start_date) & (data['date'] <= end_date)].copy()
        
        if len(data) == 0:
            return {'error': 'No data in date range'}
        
        # 初始化
        capital = self.initial_capital
        position = 0
        trades = []
        equity_curve = []
        
        # 逐日回测
        for i in range(1, len(data)):
            current_data = {
                'open': data.iloc[i]['open'],
                'high': data.iloc[i]['high'],
                'low': data.iloc[i]['low'],
                'close': data.iloc[i]['close'],
                'volume': data.iloc[i]['volume'],
            }
            
            # 生成信号
            signal = strategy.scan(data.iloc[:i], current_data)
            
            # 执行交易
            if signal:
                if signal.get('signal') == 'buy' and position == 0:
                    # 买入
                    entry_price = current_data['close']
                    shares = int(capital * 0.95 / entry_price)  # 95% 仓位
                    if shares > 0:
                        position = shares
                        capital -= shares * entry_price
                        trades.append({
                            'type': 'buy',
                            'date': data.iloc[i]['date'],
                            'price': entry_price,
                            'shares': shares,
                            'signal': signal.get('description', ''),
                        })
                
                elif signal.get('signal') == 'sell' and position > 0:
                    # 卖出
                    exit_price = current_data['close']
                    capital += position * exit_price
                    trades.append({
                        'type': 'sell',
                        'date': data.iloc[i]['date'],
                        'price': exit_price,
                        'shares': position,
                        'signal': signal.get('description', ''),
                    })
                    position = 0
            
            # 记录资金曲线
            total_value = capital + (position * current_data['close'] if position > 0 else 0)
            equity_curve.append({
                'date': data.iloc[i]['date'],
                'equity': total_value,
                'capital': capital,
                'position_value': position * current_data['close'] if position > 0 else 0,
            })
        
        # 平仓（回测结束）
        if position > 0:
            final_price = data.iloc[-1]['close']
            capital += position * final_price
            trades.append({
                'type': 'sell (end)',
                'date': data.iloc[-1]['date'],
                'price': final_price,
                'shares': position,
            })
        
        # 计算绩效指标
        metrics = self._calculate_metrics(equity_curve, trades)
        
        result = {
            'strategy': strategy.name,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': self.initial_capital,
            'final_capital': capital,
            'total_return': (capital - self.initial_capital) / self.initial_capital * 100,
            'trades': len(trades),
            'metrics': metrics,
            'trade_log': trades,
            'equity_curve': equity_curve,
        }
        
        self.results[strategy.name] = result
        logger.info(f"Backtest completed: Total Return = {result['total_return']:.2f}%")
        
        return result
    
    def _calculate_metrics(self, equity_curve: List[Dict], trades: List[Dict]) -> Dict[str, Any]:
        """
        计算绩效指标
        
        Args:
            equity_curve: 资金曲线
            trades: 交易记录
            
        Returns:
            绩效指标字典
        """
        if len(equity_curve) == 0:
            return {}
        
        # 转换为 DataFrame
        df = pd.DataFrame(equity_curve)
        
        # 计算日收益率
        df['daily_return'] = df['equity'].pct_change().fillna(0)
        
        # 总收益率
        total_return = (df['equity'].iloc[-1] - df['equity'].iloc[0]) / df['equity'].iloc[0]
        
        # 年化收益率（假设 252 个交易日）
        days = len(df)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        
        # 波动率
        volatility = df['daily_return'].std() * np.sqrt(252)
        
        # 夏普比率（假设无风险利率 3%）
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 最大回撤
        df['peak'] = df['equity'].cummax()
        df['drawdown'] = (df['equity'] - df['peak']) / df['peak']
        max_drawdown = df['drawdown'].min()
        
        # 胜率
        buy_trades = [t for t in trades if t['type'] == 'buy']
        sell_trades = [t for t in trades if t['type'] == 'sell' and t.get('type') != 'sell (end)']
        
        winning_trades = 0
        total_round_trades = min(len(buy_trades), len(sell_trades))
        
        for i in range(total_round_trades):
            if sell_trades[i]['price'] > buy_trades[i]['price']:
                winning_trades += 1
        
        win_rate = winning_trades / total_round_trades if total_round_trades > 0 else 0
        
        # 盈亏比
        if total_round_trades > 0:
            avg_win = 0
            avg_loss = 0
            win_count = 0
            loss_count = 0
            
            for i in range(total_round_trades):
                profit = sell_trades[i]['price'] - buy_trades[i]['price']
                if profit > 0:
                    avg_win += profit
                    win_count += 1
                else:
                    avg_loss += abs(profit)
                    loss_count += 1
            
            avg_win = avg_win / win_count if win_count > 0 else 0
            avg_loss = avg_loss / loss_count if loss_count > 0 else 0
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
        else:
            profit_factor = 0
        
        return {
            'total_return': total_return * 100,
            'annual_return': annual_return * 100,
            'volatility': volatility * 100,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown * 100,
            'win_rate': win_rate * 100,
            'profit_factor': profit_factor,
            'total_trades': len(trades),
            'round_trades': total_round_trades,
        }
    
    def compare_strategies(self, results: Optional[Dict[str, Dict]] = None) -> pd.DataFrame:
        """
        对比多个策略的回测结果
        
        Args:
            results: 回测结果字典（如果不传则使用 self.results）
            
        Returns:
            对比 DataFrame
        """
        if results is None:
            results = self.results
        
        comparison_data = []
        for strategy_name, result in results.items():
            metrics = result.get('metrics', {})
            comparison_data.append({
                '策略': strategy_name,
                '总收益 (%)': metrics.get('total_return', 0),
                '年化收益 (%)': metrics.get('annual_return', 0),
                '夏普比率': metrics.get('sharpe_ratio', 0),
                '最大回撤 (%)': metrics.get('max_drawdown', 0),
                '胜率 (%)': metrics.get('win_rate', 0),
                '盈亏比': metrics.get('profit_factor', 0),
                '交易次数': result.get('trades', 0),
            })
        
        return pd.DataFrame(comparison_data).set_index('策略')
    
    def generate_report(self, result: Dict[str, Any]) -> str:
        """
        生成回测报告（文本格式）
        
        Args:
            result: 回测结果
            
        Returns:
            报告文本
        """
        report = []
        report.append("=" * 60)
        report.append(f"回测报告 - {result['strategy']}")
        report.append("=" * 60)
        report.append(f"回测区间：{result['start_date']} 至 {result['end_date']}")
        report.append(f"初始资金：¥{result['initial_capital']:,.2f}")
        report.append(f"最终资金：¥{result['final_capital']:,.2f}")
        report.append(f"总收益率：{result['total_return']:.2f}%")
        report.append(f"交易次数：{result['trades']}")
        report.append("")
        report.append("绩效指标:")
        metrics = result.get('metrics', {})
        report.append(f"  年化收益：{metrics.get('annual_return', 0):.2f}%")
        report.append(f"  夏普比率：{metrics.get('sharpe_ratio', 0):.2f}")
        report.append(f"  最大回撤：{metrics.get('max_drawdown', 0):.2f}%")
        report.append(f"  胜率：{metrics.get('win_rate', 0):.2f}%")
        report.append(f"  盈亏比：{metrics.get('profit_factor', 0):.2f}")
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    # 创建一个简单的测试策略
    class TestStrategy:
        name = "test_ma_cross"
        
        def scan(self, history, current):
            if len(history) < 20:
                return None
            
            ma5 = history['close'].rolling(5).mean().iloc[-1]
            ma20 = history['close'].rolling(20).mean().iloc[-1]
            ma5_prev = history['close'].rolling(5).mean().iloc[-2]
            ma20_prev = history['close'].rolling(20).mean().iloc[-2]
            
            if ma5 > ma20 and ma5_prev <= ma20_prev:
                return {'signal': 'buy', 'description': 'MA 金叉'}
            elif ma5 < ma20 and ma5_prev >= ma20_prev:
                return {'signal': 'sell', 'description': 'MA 死叉'}
            return None
    
    # 生成测试数据
    dates = pd.date_range('2025-01-01', periods=100, freq='D')
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(100))
    
    test_data = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': prices + np.random.randn(100) * 2,
        'low': prices - np.random.randn(100) * 2,
        'close': prices,
        'volume': np.random.randint(1000, 10000, 100),
    })
    
    # 运行回测
    backtester = EnhancedBacktester(initial_capital=100000)
    result = backtester.run(TestStrategy(), test_data, '2025-01-01', '2025-04-10')
    
    # 打印报告
    print(backtester.generate_report(result))
