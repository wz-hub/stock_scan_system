#!/usr/bin/env python3
"""
完整策略回测框架

功能：
- 多策略回测
- 多时间周期支持
- 完整的性能指标
- 可视化报告
- 参数优化
"""

import sys
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Optional, Tuple
import json
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from strategies.multi_timeframe import MultiTimeframeStrategy
from strategies.volatility_squeeze import VolatilitySqueezeStrategy
from strategies.money_flow import MoneyFlowStrategy
from strategies.liquidity_hunt import LiquidityHuntStrategy
from strategies.flag_pattern import FlagPatternStrategy
from strategies.trend_follow import TrendFollowStrategy
from strategies.rsi_reversal import RSIMeanReversionStrategy
from strategies.donchian_breakout import DonchianBreakoutStrategy


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000, commission: float = 0.001):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金
            commission: 手续费率 (默认 0.1%)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        
        # 策略库
        self.strategies = {
            'multi_timeframe': MultiTimeframeStrategy(),
            'trend_follow': TrendFollowStrategy(),
            'rsi_reversal': RSIMeanReversionStrategy(),
            'donchian_breakout': DonchianBreakoutStrategy(),
            'volatility_squeeze': VolatilitySqueezeStrategy(),
            'money_flow': MoneyFlowStrategy(),
            'liquidity_hunt': LiquidityHuntStrategy(),
            'flag_pattern': FlagPatternStrategy()
        }
        
        # 回测结果
        self.trades = []
        self.equity_curve = []
        self.metrics = {}
    
    def load_data(self, db_path: str, symbols: List[str], intervals: List[str],
                  start_date: str, end_date: str) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        从数据库加载历史数据
        
        Args:
            db_path: SQLite 数据库路径
            symbols: 交易对列表
            intervals: 时间周期列表
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            嵌套字典：{symbol: {interval: DataFrame}}
        """
        conn = sqlite3.connect(db_path)
        
        start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        
        data = defaultdict(lambda: defaultdict(pd.DataFrame))
        
        for symbol in symbols:
            for interval in intervals:
                query = """
                    SELECT timestamp, open, high, low, close, volume
                    FROM klines
                    WHERE symbol = ? AND interval = ?
                    AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp ASC
                """
                
                df = pd.read_sql_query(query, conn, params=(symbol, interval, start_ts, end_ts))
                
                if len(df) > 0:
                    # 检查时间戳是秒还是毫秒
                    if df['timestamp'].iloc[0] > 1e12:
                        # 毫秒
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    else:
                        # 秒
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    
                    df.set_index('timestamp', inplace=True)
                    data[symbol][interval] = df
        
        conn.close()
        return data
    
    def run_backtest(self, data: Dict, strategy_name: str, 
                     symbols: List[str], start_date: str, end_date: str) -> Dict:
        """
        运行回测 - 使用历史数据逐日回测
        
        Args:
            data: 历史数据
            strategy_name: 策略名称
            symbols: 交易对列表
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            回测结果字典
        """
        if strategy_name not in self.strategies:
            print(f"❌ 策略不存在：{strategy_name}")
            return {}
        
        strategy = self.strategies[strategy_name]
        
        print("=" * 80)
        print(f"🧪 策略回测：{strategy_name}")
        print("=" * 80)
        print(f"回测周期：{start_date} ~ {end_date}")
        print(f"交易对数量：{len(symbols)}")
        print(f"初始资金：${self.initial_capital:,.2f}")
        print("=" * 80)
        print()
        
        self.trades = []
        capital = self.initial_capital
        
        # 按日期回测
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        total_days = len(dates)
        signals_generated = 0
        
        print(f"开始回测 {total_days} 天...")
        print()
        
        for i, date in enumerate(dates, 1):
            date_str = date.strftime('%Y-%m-%d')
            
            if i % 100 == 0:
                print(f"进度：{i}/{total_days} 天 ({i/total_days*100:.1f}%) - {len(self.trades)} 个信号")
            
            for symbol in symbols:
                if symbol not in data:
                    continue
                
                symbol_data = data[symbol]
                
                # 准备多周期数据（统一为大写，匹配策略配置）
                data_dict = {}
                interval_map = {'1d': '1D', '4h': '4H', '1h': '1H'}
                
                for db_interval, strategy_interval in interval_map.items():
                    if db_interval in symbol_data:
                        df = symbol_data[db_interval]
                        # 使用截止到昨天的数据（避免使用当天数据）
                        yesterday = date - timedelta(days=1)
                        mask = df.index <= yesterday
                        if mask.sum() > 100:  # 至少需要 100 根 K 线
                            data_dict[strategy_interval] = df[mask]
                
                # 数据不足则跳过
                if len(data_dict) < 3:
                    continue
                
                # 生成信号
                signal = strategy.generate_signal(data_dict, symbol)
                
                if signal:
                    signals_generated += 1
                    
                    # 检查置信度过滤
                    if signal.get('confidence', 0) < strategy.min_confidence:
                        continue
                    
                    # 执行交易
                    entry_price = float(signal['entry_price'])
                    position_size_pct = float(signal.get('position_size_pct', 10))
                    position_size = capital * position_size_pct / 100
                    quantity = position_size / entry_price
                    
                    # 计算手续费
                    commission = position_size * self.commission
                    
                    trade = {
                        'date': date_str,
                        'symbol': symbol,
                        'strategy': strategy_name,
                        'direction': signal['direction'],
                        'entry_price': entry_price,
                        'quantity': quantity,
                        'position_size': position_size,
                        'commission': commission,
                        'stop_loss': float(signal['stop_loss_price']),
                        'take_profit': float(signal['take_profit_price']),
                        'stop_loss_pct': float(signal.get('stop_loss_pct', 0)),
                        'take_profit_pct': float(signal.get('take_profit_pct', 0)),
                        'confidence': signal.get('confidence', 0),
                        'status': 'OPEN'
                    }
                    
                    self.trades.append(trade)
        
        print()
        print(f"回测完成！共 {signals_generated} 个信号")
        print()
        
        # 计算平仓和最终结果
        results = self._calculate_results(symbols, data, end_date)
        
        return results
    
    def _calculate_results(self, symbols: List[str], data: Dict, end_date: str) -> Dict:
        """计算回测结果 - 模拟止损止盈"""
        if not self.trades:
            print("❌ 没有交易记录")
            return {}
        
        closed_trades = []
        open_trades = []
        
        for trade in self.trades:
            symbol = trade['symbol']
            entry_price = trade['entry_price']
            stop_loss = trade['stop_loss']
            take_profit = trade['take_profit']
            direction = trade['direction']
            
            # 获取该交易后的价格数据
            if symbol in data and '1d' in data[symbol]:
                df = data[symbol]['1d']
                trade_date = datetime.strptime(trade['date'], '%Y-%m-%d')
                mask = df.index >= pd.Timestamp(trade_date)
                
                if mask.sum() > 0:
                    post_trade_data = df[mask]
                    
                    # 模拟止损止盈
                    exited = False
                    for idx, row in post_trade_data.iterrows():
                        low = row['low']
                        high = row['high']
                        close = row['close']
                        
                        # 检查止损
                        if direction == 'LONG' and low <= stop_loss:
                            exit_price = stop_loss
                            exited = True
                        elif direction == 'SHORT' and high >= stop_loss:
                            exit_price = stop_loss
                            exited = True
                        # 检查止盈
                        elif direction == 'LONG' and high >= take_profit:
                            exit_price = take_profit
                            exited = True
                        elif direction == 'SHORT' and low <= take_profit:
                            exit_price = take_profit
                            exited = True
                        
                        if exited:
                            # 计算盈亏
                            if direction == 'LONG':
                                pnl = (exit_price - entry_price) * trade['quantity']
                            else:
                                pnl = (entry_price - exit_price) * trade['quantity']
                            
                            pnl_pct = pnl / trade['position_size'] * 100
                            
                            trade['exit_price'] = exit_price
                            trade['pnl'] = pnl
                            trade['pnl_pct'] = pnl_pct
                            trade['exit_date'] = idx.strftime('%Y-%m-%d')
                            trade['exit_reason'] = 'TAKE_PROFIT' if pnl > 0 else 'STOP_LOSS'
                            trade['status'] = 'CLOSED'
                            
                            closed_trades.append(trade)
                            break
                    
                    # 如果没有触发止损止盈，用最后价格计算浮盈浮亏
                    if not exited:
                        last_price = post_trade_data['close'].iloc[-1]
                        last_date = post_trade_data.index[-1]
                        
                        if direction == 'LONG':
                            pnl = (last_price - entry_price) * trade['quantity']
                        else:
                            pnl = (entry_price - last_price) * trade['quantity']
                        
                        pnl_pct = pnl / trade['position_size'] * 100
                        
                        trade['exit_price'] = last_price
                        trade['pnl'] = pnl
                        trade['pnl_pct'] = pnl_pct
                        trade['exit_date'] = last_date.strftime('%Y-%m-%d')
                        trade['exit_reason'] = 'OPEN'
                        trade['status'] = 'OPEN'
                        
                        open_trades.append(trade)
                else:
                    open_trades.append(trade)
            else:
                open_trades.append(trade)
        
        # 计算统计指标
        total_trades = len(closed_trades)
        winning_trades = len([t for t in closed_trades if t['pnl'] > 0])
        losing_trades = len([t for t in closed_trades if t['pnl'] < 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = sum([t['pnl'] for t in closed_trades])
        total_commission = sum([t['commission'] for t in closed_trades])
        net_pnl = total_pnl - total_commission
        
        avg_win = np.mean([t['pnl'] for t in closed_trades if t['pnl'] > 0]) if winning_trades > 0 else 0
        avg_loss = np.mean([t['pnl'] for t in closed_trades if t['pnl'] < 0]) if losing_trades > 0 else 0
        
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        final_capital = self.initial_capital + net_pnl
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100
        
        # 打印结果
        print("=" * 80)
        print("📊 回测结果")
        print("=" * 80)
        print(f"总交易数：{total_trades}")
        print(f"盈利：{winning_trades} | 亏损：{losing_trades}")
        print(f"胜率：{win_rate:.2f}%")
        print()
        print(f"总盈亏：${total_pnl:,.2f}")
        print(f"总手续费：${total_commission:,.2f}")
        print(f"净盈亏：${net_pnl:,.2f}")
        print(f"总收益率：{total_return:.2f}%")
        print()
        print(f"平均盈利：${avg_win:,.2f}")
        print(f"平均亏损：${avg_loss:,.2f}")
        print(f"盈亏比：{profit_factor:.2f}")
        print()
        print(f"初始资金：${self.initial_capital:,.2f}")
        print(f"最终资金：${final_capital:,.2f}")
        print("=" * 80)
        
        results = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_commission': total_commission,
            'net_pnl': net_pnl,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'trades': closed_trades,
            'open_trades': open_trades
        }
        
        return results
    
    def save_results(self, results: Dict, filename: str = 'backtest_results.json'):
        """保存回测结果"""
        # 转换 numpy 类型
        def convert(obj):
            if isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        results_json = {k: convert(v) for k, v in results.items()}
        results_json['timestamp'] = datetime.now().isoformat()
        
        with open(filename, 'w') as f:
            json.dump(results_json, f, indent=2, ensure_ascii=False)
        
        print(f"📄 结果已保存：{filename}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='策略回测框架')
    parser.add_argument('--strategy', type=str, default='multi_timeframe',
                       choices=['multi_timeframe', 'trend_follow', 'rsi_reversal', 'donchian_breakout', 'volatility_squeeze', 'money_flow', 'liquidity_hunt', 'flag_pattern'],
                       help='策略名称')
    parser.add_argument('--symbols', type=str, default='BTCUSDT,ETHUSDT,BCHUSDT,XRPUSDT,DOGEUSDT',
                       help='交易对列表，逗号分隔')
    parser.add_argument('--start', type=str, default=(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
                       help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=datetime.now().strftime('%Y-%m-%d'),
                       help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--db', type=str, default='cache/trading.db',
                       help='数据库路径')
    parser.add_argument('--capital', type=float, default=100000,
                       help='初始资金')
    parser.add_argument('--output', type=str, default='backtest_results.json',
                       help='输出文件路径')
    
    args = parser.parse_args()
    
    # 解析参数
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    # 创建回测引擎
    engine = BacktestEngine(initial_capital=args.capital)
    
    # 加载数据
    print("📥 加载历史数据...")
    data = engine.load_data(
        db_path=args.db,
        symbols=symbols,
        intervals=['1h', '4h', '1d'],
        start_date=args.start,
        end_date=args.end
    )
    
    # 检查数据
    total_klines = sum([len(df) for symbol_data in data.values() for df in symbol_data.values()])
    print(f"✅ 加载 {total_klines:,} 条 K 线")
    print()
    
    if not data:
        print("❌ 没有数据，请先运行 download_history.py 下载历史数据")
        return
    
    # 运行回测
    results = engine.run_backtest(
        data=data,
        strategy_name=args.strategy,
        symbols=symbols,
        start_date=args.start,
        end_date=args.end
    )
    
    # 保存结果
    if results:
        engine.save_results(results, args.output)


if __name__ == '__main__':
    main()
