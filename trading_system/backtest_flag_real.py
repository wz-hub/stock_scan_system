#!/usr/bin/env python3
"""
旗形策略真实历史数据回测
使用数据库中的历史 K 线数据
"""
import sys
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from strategies.flag_pattern import FlagPatternStrategy


def load_klines_from_db(db_path: str, symbol: str, days: int = 60) -> pd.DataFrame:
    """从数据库加载 K 线数据"""
    
    conn = sqlite3.connect(db_path)
    
    # 计算起始时间戳
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)
    
    query = """
        SELECT timestamp, open, high, low, close, volume
        FROM klines
        WHERE symbol = ? AND timestamp >= ? AND timestamp <= ? AND interval = '1d'
        ORDER BY timestamp ASC
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol, start_ts, end_ts))
    conn.close()
    
    if len(df) > 0:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df['open'] = pd.to_numeric(df['open'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])
    
    return df


def backtest_strategy(strategy, symbol: str, df: pd.DataFrame) -> List[Dict]:
    """回测策略"""
    
    trades = []
    in_position = False
    position_price = 0
    position_type = None
    
    # 滚动回测
    for i in range(50, len(df)):  # 至少需要 50 根 K 线
        test_df = df.iloc[:i+1].copy()
        
        try:
            signal = strategy.generate_signal({'1D': test_df}, symbol)
            
            if signal and not in_position:
                # 开仓
                in_position = True
                position_price = float(signal['entry_price'])
                position_type = signal['direction']
                entry_date = test_df.index[-1]
                
                trades.append({
                    'entry_date': entry_date,
                    'symbol': symbol,
                    'pattern': signal['pattern'],
                    'direction': position_type,
                    'entry_price': position_price,
                    'stop_loss': float(signal['stop_loss_price']),
                    'take_profit': float(signal['take_profit_price']),
                    'exit_date': None,
                    'exit_price': None,
                    'exit_reason': None,
                    'pnl_pct': None,
                    'result': 'OPEN'
                })
            
            elif in_position and len(trades) > 0:
                last_trade = trades[-1]
                current_price = df['close'].iloc[i]
                current_date = df.index[i]
                
                # 检查止损止盈
                if position_type == 'LONG':
                    if current_price <= last_trade['stop_loss']:
                        # 止损
                        pnl = (current_price - position_price) / position_price * 100
                        last_trade.update({
                            'exit_date': current_date,
                            'exit_price': current_price,
                            'exit_reason': 'STOP_LOSS',
                            'pnl_pct': pnl,
                            'result': 'LOSS' if pnl < 0 else 'WIN'
                        })
                        in_position = False
                    
                    elif current_price >= last_trade['take_profit']:
                        # 止盈
                        pnl = (current_price - position_price) / position_price * 100
                        last_trade.update({
                            'exit_date': current_date,
                            'exit_price': current_price,
                            'exit_reason': 'TAKE_PROFIT',
                            'pnl_pct': pnl,
                            'result': 'WIN'
                        })
                        in_position = False
                
                else:  # SHORT
                    if current_price >= last_trade['stop_loss']:
                        # 止损
                        pnl = (position_price - current_price) / position_price * 100
                        last_trade.update({
                            'exit_date': current_date,
                            'exit_price': current_price,
                            'exit_reason': 'STOP_LOSS',
                            'pnl_pct': pnl,
                            'result': 'LOSS' if pnl < 0 else 'WIN'
                        })
                        in_position = False
                    
                    elif current_price <= last_trade['take_profit']:
                        # 止盈
                        pnl = (position_price - current_price) / position_price * 100
                        last_trade.update({
                            'exit_date': current_date,
                            'exit_price': current_price,
                            'exit_reason': 'TAKE_PROFIT',
                            'pnl_pct': pnl,
                            'result': 'WIN'
                        })
                        in_position = False
        
        except Exception as e:
            continue
    
    return trades


def calculate_metrics(trades: List[Dict]) -> Dict:
    """计算回测指标"""
    
    closed_trades = [t for t in trades if t['result'] != 'OPEN']
    winning_trades = [t for t in closed_trades if t['result'] == 'WIN']
    losing_trades = [t for t in closed_trades if t['result'] == 'LOSS']
    
    total_trades = len(closed_trades)
    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    
    avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
    avg_loss = abs(np.mean([t['pnl_pct'] for t in losing_trades])) if losing_trades else 0
    
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
    
    total_pnl = sum([t['pnl_pct'] for t in closed_trades])
    
    return {
        'total_signals': len(trades),
        'closed_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'open_trades': len(trades) - total_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'total_pnl': total_pnl,
        'expectancy': total_pnl / total_trades if total_trades > 0 else 0
    }


def main():
    """主函数"""
    
    print("=" * 80)
    print("🚩 旗形策略 - 真实历史数据回测")
    print("=" * 80)
    
    db_path = 'cache/trading.db'
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT']
    days = 365
    
    strategy = FlagPatternStrategy()
    all_trades = []
    
    print(f"\n📥 加载 {len(symbols)} 个币种的历史数据 ({days} 天)...")
    
    for symbol in symbols:
        print(f"\n回测 {symbol}...")
        
        df = load_klines_from_db(db_path, symbol, days)
        
        if len(df) < 50:
            print(f"  ⚠️ 数据不足 ({len(df)} 条)，跳过")
            continue
        
        print(f"  加载 {len(df)} 条 K 线")
        
        trades = backtest_strategy(strategy, symbol, df)
        all_trades.extend(trades)
        
        print(f"  发现 {len(trades)} 个信号")
    
    print("\n" + "=" * 80)
    
    if len(all_trades) == 0:
        print("\n⚠️ 未发现任何旗形信号")
        print("\n可能原因:")
        print("  1. 历史数据时间范围太短")
        print("  2. 近期市场没有明显的旗形形态")
        print("  3. 策略参数过于严格")
        print("\n建议:")
        print("  - 增加回测天数 (--days 90)")
        print("  - 放宽旗杆/旗面参数")
        print("  - 检查数据质量")
        return
    
    # 计算指标
    metrics = calculate_metrics(all_trades)
    
    print("\n📊 回测统计:")
    print("-" * 80)
    print(f"  总信号数：{metrics['total_signals']}")
    print(f"  已平仓：{metrics['closed_trades']}")
    print(f"    └─ 盈利：{metrics['winning_trades']}")
    print(f"    └─ 亏损：{metrics['losing_trades']}")
    print(f"  持仓中：{metrics['open_trades']}")
    
    print("\n📈 性能指标:")
    print("-" * 80)
    print(f"  胜率：{metrics['win_rate']:.1f}%")
    print(f"  平均盈利：{metrics['avg_win']:.2f}%")
    print(f"  平均亏损：{metrics['avg_loss']:.2f}%")
    print(f"  盈亏比：{metrics['profit_factor']:.2f}")
    print(f"  总收益率：{metrics['total_pnl']:.2f}%")
    print(f"  期望值：{metrics['expectancy']:.2f}% / 交易")
    
    print("\n📝 交易明细:")
    print("-" * 80)
    print(f"{'日期':<12} {'标的':<10} {'形态':<12} {'方向':<6} {'入场':>12} {'出场':>12} {'盈亏':>10} {'结果':<6}")
    print("-" * 80)
    
    for trade in all_trades:
        entry_date = trade['entry_date'].strftime('%Y-%m-%d') if hasattr(trade['entry_date'], 'strftime') else str(trade['entry_date'])
        exit_date = trade['exit_date'].strftime('%Y-%m-%d') if trade['exit_date'] and hasattr(trade['exit_date'], 'strftime') else "持仓中"
        exit_price = f"{trade['exit_price']:.2f}" if trade['exit_price'] else "持仓中"
        pnl = f"{trade['pnl_pct']:+.2f}%" if trade['pnl_pct'] is not None else "-"
        result = trade['result']
        
        pattern_emoji = "🐂" if "Bull" in trade['pattern'] else "🐻"
        direction_emoji = "📈" if trade['direction'] == "LONG" else "📉"
        
        print(f"{entry_date:<12} {trade['symbol']:<10} {pattern_emoji} {trade['pattern']:<8} {direction_emoji} {trade['direction']:<4} "
              f"{trade['entry_price']:>12.2f} {exit_price:>12} {pnl:>10} {result:<6}")
    
    print("-" * 80)
    
    # 保存结果
    output_file = Path('cache/flag_backtest_real.json')
    
    # 序列化 trades
    serializable_trades = []
    for t in all_trades:
        st = t.copy()
        if st['entry_date'] and hasattr(st['entry_date'], 'isoformat'):
            st['entry_date'] = st['entry_date'].isoformat()
        if st['exit_date'] and hasattr(st['exit_date'], 'isoformat'):
            st['exit_date'] = st['exit_date'].isoformat()
        serializable_trades.append(st)
    
    with open(output_file, 'w') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'strategy': 'Flag Pattern',
            'symbols': symbols,
            'days': days,
            'metrics': metrics,
            'trades': serializable_trades
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 报告已保存到：{output_file}")
    print("\n" + "=" * 80)


if __name__ == '__main__':
    import json
    main()
