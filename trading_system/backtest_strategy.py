#!/usr/bin/env python3
"""
策略回测框架 - 验证策略有效性
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

sys.path.insert(0, str(Path(__file__).parent))

from data.binance import BinanceAPI
from strategies.multi_timeframe import MultiTimeframeStrategy
from core.tracker import SignalTracker


class Backtester:
    """策略回测器"""
    
    def __init__(self, initial_capital: float = 100000):
        """
        初始化回测器
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.api = BinanceAPI()
        self.strategy = MultiTimeframeStrategy()
        
        # 回测结果
        self.trades = []
        self.equity_curve = []
        
    def get_historical_data(self, symbol: str, timeframe: str, days: int = 30) -> Optional[pd.DataFrame]:
        """
        获取历史数据
        
        Args:
            symbol: 交易对
            timeframe: 时间周期
            days: 天数
        
        Returns:
            K 线数据 DataFrame
        """
        try:
            # 根据时间周期计算 limit
            if timeframe == '1D':
                limit = days
            elif timeframe == '4H':
                limit = days * 6
            elif timeframe == '1H':
                limit = days * 24
            else:
                limit = 100
            
            klines = self.api.get_klines(symbol, timeframe, limit=limit)
            if klines is not None and len(klines) > 0:
                return klines
        except Exception as e:
            print(f"⚠️  获取 {symbol} 数据失败：{e}")
        
        return None
    
    def run_backtest(self, symbols: List[str], days: int = 30) -> Dict:
        """
        运行回测
        
        Args:
            symbols: 交易对列表
            days: 回测天数
        
        Returns:
            回测结果字典
        """
        print("=" * 80)
        print("🧪 策略回测")
        print("=" * 80)
        print(f"回测周期：{days} 天")
        print(f"交易对数量：{len(symbols)}")
        print(f"初始资金：${self.initial_capital:,.2f}")
        print("=" * 80)
        
        self.trades = []
        total_signals = 0
        winning_trades = 0
        losing_trades = 0
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] 回测 {symbol}...")
            
            # 获取多周期数据
            data_1d = self.get_historical_data(symbol, '1D', days)
            data_4h = self.get_historical_data(symbol, '4H', days * 2)
            data_1h = self.get_historical_data(symbol, '1H', days * 3)
            
            if data_1d is None or data_4h is None or data_1h is None:
                print(f"  ⚠️  数据不足，跳过")
                continue
            
            # 模拟逐日回测
            data_dict = {
                '1D': data_1d,
                '4H': data_4h,
                '1H': data_1h
            }
            
            # 生成信号
            signal = self.strategy.generate_signal(data_dict, symbol)
            
            if signal:
                total_signals += 1
                print(f"  📊 生成信号：{signal['action']} {signal['direction']}")
                print(f"     置信度：{signal['confidence']}%")
                print(f"     入场：${float(signal['entry_price']):.2f}")
                print(f"     止损：${float(signal['stop_loss_price']):.2f} ({signal['stop_loss_pct']}%)")
                print(f"     止盈：${float(signal['take_profit_price']):.2f} ({signal['take_profit_pct']}%)")
                
                # 模拟持仓结果（简化：用最新价格计算盈亏）
                latest_price = data_1h['close'].iloc[-1]
                entry_price = float(signal['entry_price'])
                
                if signal['direction'] == 'LONG':
                    pnl_pct = (latest_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - latest_price) / entry_price * 100
                
                # 检查是否止损或止盈
                stop_loss = float(signal['stop_loss_price'])
                take_profit = float(signal['take_profit_price'])
                
                if signal['direction'] == 'LONG':
                    if latest_price <= stop_loss:
                        pnl_pct = -signal['stop_loss_pct']
                        status = 'STOP_LOSS'
                    elif latest_price >= take_profit:
                        pnl_pct = signal['take_profit_pct']
                        status = 'TAKE_PROFIT'
                    else:
                        status = 'OPEN'
                else:
                    if latest_price >= stop_loss:
                        pnl_pct = -signal['stop_loss_pct']
                        status = 'STOP_LOSS'
                    elif latest_price <= take_profit:
                        pnl_pct = signal['take_profit_pct']
                        status = 'TAKE_PROFIT'
                    else:
                        status = 'OPEN'
                
                trade = {
                    'symbol': symbol,
                    'direction': signal['direction'],
                    'entry_price': entry_price,
                    'current_price': latest_price,
                    'pnl_pct': pnl_pct,
                    'status': status,
                    'timestamp': signal['timestamp']
                }
                
                self.trades.append(trade)
                
                if pnl_pct > 0:
                    winning_trades += 1
                    print(f"  ✅ 盈利：+{pnl_pct:.2f}%")
                elif pnl_pct < 0:
                    losing_trades += 1
                    print(f"  ❌ 亏损：{pnl_pct:.2f}%")
                else:
                    print(f"  ➖ 持平")
            else:
                print(f"  ⏭️  无信号")
        
        # 计算回测统计
        print("\n" + "=" * 80)
        print("📊 回测统计")
        print("=" * 80)
        
        total_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_pnl = np.mean([t['pnl_pct'] for t in self.trades]) if self.trades else 0
        max_win = max([t['pnl_pct'] for t in self.trades]) if self.trades else 0
        max_loss = min([t['pnl_pct'] for t in self.trades]) if self.trades else 0
        
        # 计算最终资金
        final_capital = self.initial_capital
        for trade in self.trades:
            if trade['status'] != 'OPEN':
                pnl_amount = final_capital * (trade['pnl_pct'] / 100)
                final_capital += pnl_amount
        
        total_pnl_pct = ((final_capital - self.initial_capital) / self.initial_capital * 100)
        
        stats = {
            'total_signals': total_signals,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'max_win': max_win,
            'max_loss': max_loss,
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_pnl_pct': total_pnl_pct,
            'trades': self.trades
        }
        
        print(f"总信号数：{total_signals}")
        print(f"总交易数：{total_trades}")
        print(f"盈利：{winning_trades} | 亏损：{losing_trades}")
        print(f"胜率：{win_rate:.2f}%")
        print(f"平均盈亏：{avg_pnl:.2f}%")
        print(f"最大盈利：+{max_win:.2f}%")
        print(f"最大亏损：{max_loss:.2f}%")
        print()
        print(f"初始资金：${self.initial_capital:,.2f}")
        print(f"最终资金：${final_capital:,.2f}")
        print(f"总收益率：{total_pnl_pct:.2f}%")
        print("=" * 80)
        
        return stats
    
    def save_results(self, filename: str = 'backtest_results.json'):
        """保存回测结果"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'strategy': self.strategy.name,
            'initial_capital': self.initial_capital,
            'trades': self.trades
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"📄 回测结果已保存：{filename}")


def main():
    """主函数"""
    # 测试交易对（选择活跃的）
    test_symbols = [
        'BTC/USDT', 'ETH/USDT',
        'BCH/USDT', 'XRP/USDT', 'DOGE/USDT',
        'ADA/USDT', 'SOL/USDT', 'DOT/USDT',
        'MATIC/USDT', 'LINK/USDT'
    ]
    
    # 创建回测器
    backtester = Backtester(initial_capital=100000)
    
    # 运行回测
    stats = backtester.run_backtest(test_symbols, days=7)
    
    # 保存结果
    backtester.save_results('backtest_results.json')
    
    # 评估策略表现
    print("\n" + "=" * 80)
    print("📈 策略评估")
    print("=" * 80)
    
    if stats['win_rate'] >= 50:
        print("✅ 胜率良好 (≥50%)")
    elif stats['win_rate'] >= 40:
        print("⚠️  胜率一般 (40-50%)，需要优化")
    else:
        print("❌ 胜率较低 (<40%)，需要大幅优化")
    
    if stats['total_pnl_pct'] > 0:
        print("✅ 总体盈利")
    else:
        print("❌ 总体亏损")
    
    if abs(stats['max_loss']) > 5:
        print(f"⚠️  单笔最大亏损过大 ({stats['max_loss']:.2f}%)，建议降低止损")
    
    print("=" * 80)


if __name__ == '__main__':
    main()
