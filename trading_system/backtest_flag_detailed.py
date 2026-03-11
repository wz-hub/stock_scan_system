#!/usr/bin/env python3
"""
旗形策略详细回测 - 记录每个信号的详细信息
"""
import sys
import sqlite3
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from strategies.flag_pattern import FlagPatternStrategy


def load_klines_from_db(db_path: str, symbol: str, days: int = 365) -> pd.DataFrame:
    """从数据库加载 K 线数据"""
    
    conn = sqlite3.connect(db_path)
    
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
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
    
    return df


def backtest_detailed(strategy, symbol: str, df: pd.DataFrame) -> List[Dict]:
    """详细回测，记录每个信号"""
    
    signals = []
    in_position = False
    position_price = 0
    position_type = None
    current_signal = None
    
    # 滚动回测，记录每个信号
    for i in range(50, len(df)):
        test_df = df.iloc[:i+1].copy()
        current_date = df.index[i]
        current_price = df['close'].iloc[i]
        
        try:
            signal = strategy.generate_signal({'1D': test_df}, symbol)
            
            # 检测到新信号
            if signal and not in_position:
                in_position = True
                position_price = float(signal['entry_price'])
                position_type = signal['direction']
                current_signal = {
                    'signal_id': f"{symbol}_{len(signals)+1}",
                    'entry_date': current_date,
                    'entry_time': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': symbol,
                    'pattern': signal['pattern'],
                    'direction': position_type,
                    'entry_price': position_price,
                    'stop_loss': float(signal['stop_loss_price']),
                    'take_profit': float(signal['take_profit_price']),
                    'confidence': signal.get('confidence', 0),
                    'reason': signal.get('reason', ''),
                    'exit_date': None,
                    'exit_time': None,
                    'exit_price': None,
                    'exit_reason': None,
                    'pnl_pct': None,
                    'result': 'OPEN',
                    'holding_days': 0,
                    'pole_change_pct': signal.get('pattern_details', {}).get('pole_change_pct', 0),
                    'breakout_strength': signal.get('pattern_details', {}).get('breakout_strength', 0)
                }
            
            # 检查持仓
            elif in_position and current_signal:
                current_signal['holding_days'] += 1
                
                # 检查止损止盈
                if position_type == 'LONG':
                    if current_price <= current_signal['stop_loss']:
                        pnl = (current_price - position_price) / position_price * 100
                        current_signal.update({
                            'exit_date': current_date,
                            'exit_time': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'exit_price': current_price,
                            'exit_reason': 'STOP_LOSS',
                            'pnl_pct': round(pnl, 2),
                            'result': 'LOSS' if pnl < 0 else 'WIN',
                            'holding_days': current_signal['holding_days']
                        })
                        signals.append(current_signal)
                        in_position = False
                        current_signal = None
                    
                    elif current_price >= current_signal['take_profit']:
                        pnl = (current_price - position_price) / position_price * 100
                        current_signal.update({
                            'exit_date': current_date,
                            'exit_time': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'exit_price': current_price,
                            'exit_reason': 'TAKE_PROFIT',
                            'pnl_pct': round(pnl, 2),
                            'result': 'WIN',
                            'holding_days': current_signal['holding_days']
                        })
                        signals.append(current_signal)
                        in_position = False
                        current_signal = None
                
                else:  # SHORT
                    if current_price >= current_signal['stop_loss']:
                        pnl = (position_price - current_price) / position_price * 100
                        current_signal.update({
                            'exit_date': current_date,
                            'exit_time': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'exit_price': current_price,
                            'exit_reason': 'STOP_LOSS',
                            'pnl_pct': round(pnl, 2),
                            'result': 'LOSS' if pnl < 0 else 'WIN',
                            'holding_days': current_signal['holding_days']
                        })
                        signals.append(current_signal)
                        in_position = False
                        current_signal = None
                    
                    elif current_price <= current_signal['take_profit']:
                        pnl = (position_price - current_price) / position_price * 100
                        current_signal.update({
                            'exit_date': current_date,
                            'exit_time': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                            'exit_price': current_price,
                            'exit_reason': 'TAKE_PROFIT',
                            'pnl_pct': round(pnl, 2),
                            'result': 'WIN',
                            'holding_days': current_signal['holding_days']
                        })
                        signals.append(current_signal)
                        in_position = False
                        current_signal = None
        
        except Exception as e:
            continue
    
    # 添加未平仓信号
    if current_signal:
        current_signal['holding_days'] = (df.index[-1] - current_signal['entry_date']).days
        signals.append(current_signal)
    
    return signals


def calculate_metrics(signals: List[Dict]) -> Dict:
    """计算回测指标"""
    
    closed_signals = [s for s in signals if s['result'] != 'OPEN']
    winning_trades = [s for s in closed_signals if s['result'] == 'WIN']
    losing_trades = [s for s in closed_signals if s['result'] == 'LOSS']
    
    total_trades = len(closed_signals)
    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    
    avg_win = np.mean([s['pnl_pct'] for s in winning_trades]) if winning_trades else 0
    avg_loss = abs(np.mean([s['pnl_pct'] for s in losing_trades])) if losing_trades else 0
    
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
    
    total_pnl = sum([s['pnl_pct'] for s in closed_signals])
    
    avg_holding = np.mean([s['holding_days'] for s in closed_signals]) if closed_signals else 0
    
    return {
        'total_signals': len(signals),
        'closed_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'open_trades': len(signals) - total_trades,
        'win_rate': round(win_rate, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'profit_factor': round(profit_factor, 2),
        'total_pnl': round(total_pnl, 2),
        'expectancy': round(total_pnl / total_trades, 3) if total_trades > 0 else 0,
        'avg_holding_days': round(avg_holding, 1)
    }


def generate_feishu_report(signals: List[Dict], metrics: Dict, symbols: List[str], days: int) -> str:
    """生成飞书文档报告"""
    
    report = f"""# 🚩 旗形策略详细回测报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (北京时间)

---

## 📊 回测概览

| 项目 | 数值 |
|------|------|
| 回测周期 | {days} 天 |
| 交易品种 | {', '.join(symbols)} |
| 策略类型 | 旗形形态突破 |
| 止损/止盈 | 3% / 9% (3:1 盈亏比) |

---

## 📈 核心指标

| 指标 | 数值 | 评价 |
|------|------|------|
| 总信号数 | {metrics['total_signals']} | {'✅ 活跃' if metrics['total_signals'] > 50 else '⚠️ 较少'} |
| 已平仓 | {metrics['closed_trades']} ({metrics['winning_trades']}赢 {metrics['losing_trades']}亏) | - |
| 持仓中 | {metrics['open_trades']} | - |
| 胜率 | {metrics['win_rate']}% | {'✅ 优秀' if metrics['win_rate'] >= 50 else '⚠️ 偏低'} |
| 平均盈利 | {metrics['avg_win']}% | {'✅ 优秀' if metrics['avg_win'] >= 8 else '⭕ 一般'} |
| 平均亏损 | {metrics['avg_loss']}% | {'⚠️ 偏大' if metrics['avg_loss'] > 4 else '✅ 可控'} |
| 盈亏比 | {metrics['profit_factor']} | {'✅ 良好' if metrics['profit_factor'] >= 2 else '⚠️ 需改进'} |
| 总收益率 | {metrics['total_pnl']}% | {'✅ 正收益' if metrics['total_pnl'] > 0 else '❌ 亏损'} |
| 期望值 | {metrics['expectancy']}%/交易 | {'✅ 正期望' if metrics['expectancy'] > 0 else '❌ 负期望'} |
| 平均持仓 | {metrics['avg_holding_days']} 天 | - |

---

## 📊 各币种表现

| 币种 | 总交易 | 盈利 | 亏损 | 胜率 | 净收益 | 评价 |
|------|--------|------|------|------|--------|------|
"""
    
    # 按币种统计
    symbol_stats = {}
    for s in signals:
        sym = s['symbol']
        if sym not in symbol_stats:
            symbol_stats[sym] = {'total': 0, 'win': 0, 'loss': 0, 'pnl': 0}
        if s['result'] != 'OPEN':
            symbol_stats[sym]['total'] += 1
            if s['result'] == 'WIN':
                symbol_stats[sym]['win'] += 1
                symbol_stats[sym]['pnl'] += s['pnl_pct']
            else:
                symbol_stats[sym]['loss'] += 1
                symbol_stats[sym]['pnl'] += s['pnl_pct']
    
    for sym in sorted(symbol_stats.keys()):
        stats = symbol_stats[sym]
        wr = stats['win'] / stats['total'] * 100 if stats['total'] > 0 else 0
        evaluation = '✅' if stats['pnl'] > 0 else '⚠️'
        report += f"| {sym} | {stats['total']} | {stats['win']} | {stats['loss']} | {wr:.1f}% | {stats['pnl']:+.2f}% | {evaluation} |\n"
    
    report += f"""
---

## 📝 完整交易明细

| # | 入场时间 | 币种 | 形态 | 方向 | 入场价 | 出场时间 | 出场价 | 盈亏 | 结果 | 持仓 |
|---|----------|------|------|------|--------|----------|--------|------|------|------|
"""
    
    for i, s in enumerate(signals, 1):
        entry_time = s['entry_time'][:10] if s['entry_time'] else '-'
        exit_time = s['exit_time'][:10] if s['exit_time'] else '持仓中'
        exit_price = f"{s['exit_price']:.2f}" if s['exit_price'] else '持仓中'
        pnl = f"{s['pnl_pct']:+.2f}%" if s['pnl_pct'] is not None else '-'
        pattern_emoji = '🐂' if 'Bull' in s['pattern'] else '🐻'
        direction_emoji = '📈' if s['direction'] == 'LONG' else '📉'
        
        report += f"| {i} | {entry_time} | {s['symbol']} | {pattern_emoji} {s['pattern']} | {direction_emoji} {s['direction']} | {s['entry_price']:,.2f} | {exit_time} | {exit_price} | {pnl} | {s['result']} | {s['holding_days']}天 |\n"
    
    report += f"""
---

## 💡 策略评价

### ✅ 优势

- 盈亏比 {metrics['profit_factor']} {'> 2，策略有效' if metrics['profit_factor'] >= 2 else '需改进'}
- 平均盈利 {metrics['avg_win']}% {'接近止盈目标，形态识别准确' if metrics['avg_win'] >= 8 else '有提升空间'}
- 总收益 {metrics['total_pnl']}% {'正收益，期望值为正' if metrics['total_pnl'] > 0 else '需优化'}

### ⚠️ 不足

- 胜率 {metrics['win_rate']}% {'偏低' if metrics['win_rate'] < 45 else '良好'}
- 部分亏损超过 3% 止损
- 震荡市中容易失败

### 📌 建议

1. 配合趋势指标 (ADX/均线) 过滤
2. 严格执行止损纪律
3. 单笔风险不超过总资金 2%
4. 优先选择高流动性币种

---

## ⚠️ 风险提示

1. 回测基于历史数据，实盘表现可能不同
2. 旗形策略在震荡市中容易失败
3. 严格执行止损，避免单笔大额亏损
4. 建议配合其他技术指标综合判断

---

**📄 完整数据**: `cache/flag_backtest_detailed.json`

**🔧 策略文件**: `strategies/flag_pattern.py`

**📚 策略文档**: `FLAG_STRATEGY_README.md`
"""
    
    return report


def main():
    """主函数"""
    
    print("=" * 80)
    print("🚩 旗形策略详细回测")
    print("=" * 80)
    
    db_path = 'cache/trading.db'
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT']
    days = 365
    
    strategy = FlagPatternStrategy()
    all_signals = []
    
    print(f"\n📥 回测 {len(symbols)} 个币种 ({days} 天)...")
    
    for symbol in symbols:
        print(f"\n回测 {symbol}...")
        
        df = load_klines_from_db(db_path, symbol, days)
        
        if len(df) < 50:
            print(f"  ⚠️ 数据不足 ({len(df)} 条)，跳过")
            continue
        
        print(f"  加载 {len(df)} 条 K 线")
        
        signals = backtest_detailed(strategy, symbol, df)
        all_signals.extend(signals)
        
        print(f"  发现 {len(signals)} 个信号")
    
    print("\n" + "=" * 80)
    
    if len(all_signals) == 0:
        print("\n⚠️ 未发现任何旗形信号")
        return
    
    # 计算指标
    metrics = calculate_metrics(all_signals)
    
    print("\n📊 回测统计:")
    print(f"  总信号数：{metrics['total_signals']}")
    print(f"  已平仓：{metrics['closed_trades']} ({metrics['winning_trades']}赢 {metrics['losing_trades']}亏)")
    print(f"  持仓中：{metrics['open_trades']}")
    print(f"  胜率：{metrics['win_rate']}%")
    print(f"  盈亏比：{metrics['profit_factor']}")
    print(f"  总收益：{metrics['total_pnl']}%")
    print(f"  期望值：{metrics['expectancy']}%/交易")
    print(f"  平均持仓：{metrics['avg_holding_days']} 天")
    
    # 生成飞书报告
    print("\n📝 生成飞书报告...")
    report = generate_feishu_report(all_signals, metrics, symbols, days)
    
    # 保存报告
    with open('flag_backtest_detailed_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 保存详细数据
    serializable_signals = []
    for s in all_signals:
        ss = s.copy()
        if ss['entry_date'] and hasattr(ss['entry_date'], 'isoformat'):
            ss['entry_date'] = ss['entry_date'].isoformat()
        if ss['exit_date'] and hasattr(ss['exit_date'], 'isoformat'):
            ss['exit_date'] = ss['exit_date'].isoformat()
        serializable_signals.append(ss)
    
    with open('cache/flag_backtest_detailed.json', 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'strategy': 'Flag Pattern',
            'symbols': symbols,
            'days': days,
            'metrics': metrics,
            'signals': serializable_signals
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 报告已保存到：flag_backtest_detailed_report.md")
    print(f"✅ 数据已保存到：cache/flag_backtest_detailed.json")
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
