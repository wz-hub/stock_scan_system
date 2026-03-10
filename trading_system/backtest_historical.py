#!/usr/bin/env python3
"""
基于本地数据库的历史回测
"""
import sys
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from strategies.multi_timeframe import MultiTimeframeStrategy


def load_klines_from_db(symbol: str, timeframe: str = '1D', limit: int = 100) -> pd.DataFrame:
    """从数据库加载 K 线数据"""
    db_path = Path('cache/trading.db')
    if not db_path.exists():
        return None
    
    conn = sqlite3.connect(str(db_path))
    
    # 查询 K 线数据
    query = """
    SELECT timestamp, open, high, low, close, volume
    FROM klines
    WHERE symbol = ? AND timeframe = ?
    ORDER BY timestamp DESC
    LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))
    conn.close()
    
    if len(df) > 0:
        df = df.iloc[::-1]  # 正序排列
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    return None


def get_active_signals_from_db() -> List[Dict]:
    """从数据库获取活跃信号"""
    db_path = Path('cache/trading.db')
    if not db_path.exists():
        return []
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    query = """
    SELECT symbol, strategy_name, direction, price as entry_price, 
           stop_loss, take_profit, pnl as pnl_pct, timestamp, status, signal_data
    FROM signals
    WHERE status = 'ACTIVE'
    ORDER BY timestamp DESC
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    signals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # 解析 signal_data 中的详细信息
    import json
    for sig in signals:
        if sig['signal_data']:
            try:
                data = json.loads(sig['signal_data'])
                sig['stop_loss_pct'] = data.get('stop_loss_pct', 0)
                sig['take_profit_pct'] = data.get('take_profit_pct', 0)
            except:
                sig['stop_loss_pct'] = 0
                sig['take_profit_pct'] = 0
    
    return signals


def backtest_existing_signals() -> Dict:
    """回测现有活跃信号的表现"""
    print("=" * 80)
    print("🧪 历史信号回测（基于数据库）")
    print("=" * 80)
    
    signals = get_active_signals_from_db()
    
    if not signals:
        print("❌ 数据库中没有活跃信号")
        return {}
    
    print(f"活跃信号数量：{len(signals)}")
    print()
    
    # 分类统计
    long_signals = [s for s in signals if s['direction'] == 'LONG']
    short_signals = [s for s in signals if s['direction'] == 'SHORT']
    
    profitable = [s for s in signals if s['pnl_pct'] > 0]
    losing = [s for s in signals if s['pnl_pct'] < 0]
    
    print("=== 方向分布 ===")
    print(f"LONG: {len(long_signals)} 个")
    print(f"SHORT: {len(short_signals)} 个")
    print()
    
    print("=== 盈亏分布 ===")
    print(f"盈利：{len(profitable)} 个 ({len(profitable)/len(signals)*100:.1f}%)")
    print(f"亏损：{len(losing)} 个 ({len(losing)/len(signals)*100:.1f}%)")
    print()
    
    # 平均盈亏
    avg_pnl = np.mean([s['pnl_pct'] for s in signals])
    print(f"平均盈亏：{avg_pnl:.2f}%")
    print()
    
    # 按策略统计
    by_strategy = {}
    for s in signals:
        strategy = s['strategy_name']
        if strategy not in by_strategy:
            by_strategy[strategy] = []
        by_strategy[strategy].append(s)
    
    print("=== 按策略统计 ===")
    for strategy, sigs in sorted(by_strategy.items()):
        avg = np.mean([s['pnl_pct'] for s in sigs])
        win_rate = len([s for s in sigs if s['pnl_pct'] > 0]) / len(sigs) * 100
        print(f"{strategy}:")
        print(f"  信号数：{len(sigs)}")
        print(f"  胜率：{win_rate:.1f}%")
        print(f"  平均盈亏：{avg:.2f}%")
    print()
    
    # 最大盈利和亏损
    max_win = max(signals, key=lambda x: x['pnl_pct'])
    max_loss = min(signals, key=lambda x: x['pnl_pct'])
    
    print("=== 最佳/最差信号 ===")
    print(f"最佳：{max_win['symbol']} {max_win['direction']} +{max_win['pnl_pct']:.2f}%")
    print(f"最差：{max_loss['symbol']} {max_loss['direction']} {max_loss['pnl_pct']:.2f}%")
    print()
    
    # 评估
    print("=" * 80)
    print("📈 策略评估")
    print("=" * 80)
    
    win_rate = len(profitable) / len(signals) * 100
    
    if win_rate >= 50:
        print("✅ 胜率良好 (≥50%)")
    elif win_rate >= 40:
        print("⚠️  胜率一般 (40-50%)")
    else:
        print("❌ 胜率较低 (<40%)")
    
    if avg_pnl > 0:
        print("✅ 平均盈利为正")
    else:
        print("❌ 平均盈利为负")
    
    if max_loss['pnl_pct'] < -5:
        print(f"⚠️  单笔最大亏损过大 ({max_loss['pnl_pct']:.2f}%)")
    
    print("=" * 80)
    
    return {
        'total_signals': len(signals),
        'long_signals': len(long_signals),
        'short_signals': len(short_signals),
        'profitable': len(profitable),
        'losing': len(losing),
        'win_rate': win_rate,
        'avg_pnl': avg_pnl,
        'max_win': max_win['pnl_pct'],
        'max_loss': max_loss['pnl_pct']
    }


def main():
    """主函数"""
    # 回测现有信号
    stats = backtest_existing_signals()
    
    if stats:
        # 保存结果
        import json
        results = {
            'timestamp': datetime.now().isoformat(),
            'type': 'historical_backtest',
            'stats': stats
        }
        
        with open('backtest_historical_results.json', 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 回测结果已保存：backtest_historical_results.json")


if __name__ == '__main__':
    main()
