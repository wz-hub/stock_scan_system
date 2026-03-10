#!/usr/bin/env python3
"""
简单回测 - 基于数据库中的历史信号

直接分析已有信号的表现，不依赖实时 API
"""

import sys
import sqlite3
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))


def backtest_from_signals_db():
    """从 signals.db 回测历史信号"""
    print("=" * 80)
    print("🧪 历史信号回测报告")
    print("=" * 80)
    print(f"回测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print("=" * 80)
    print()
    
    # 连接数据库
    signals_db = Path('cache/signals.db')
    if not signals_db.exists():
        print("❌ signals.db 不存在")
        return
    
    conn = sqlite3.connect(str(signals_db))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查询所有信号
    cursor.execute('SELECT * FROM signals ORDER BY timestamp')
    signals = [dict(row) for row in cursor.fetchall()]
    
    if not signals:
        print("❌ 没有信号数据")
        return
    
    print(f"信号总数：{len(signals)}")
    print(f"时间范围：{signals[0]['timestamp'][:10]} ~ {signals[-1]['timestamp'][:10]}")
    print()
    
    # 解析 signal_data
    for sig in signals:
        if sig.get('signal_data'):
            try:
                data = json.loads(sig['signal_data'])
                sig.update(data)
            except:
                pass
    
    # 分类统计
    active = [s for s in signals if s['status'] == 'ACTIVE']
    stopped_loss = [s for s in signals if s['status'] == 'STOP_LOSS']
    
    print("=== 信号状态 ===")
    print(f"活跃：{len(active)} 个")
    print(f"止损：{len(stopped_loss)} 个")
    print()
    
    # 按策略统计
    by_strategy = defaultdict(list)
    for sig in signals:
        strategy = sig.get('strategy_name', 'Unknown')
        by_strategy[strategy].append(sig)
    
    print("=== 按策略统计 ===")
    for strategy, sigs in sorted(by_strategy.items()):
        total = len(sigs)
        active_count = len([s for s in sigs if s['status'] == 'ACTIVE'])
        sl_count = len([s for s in sigs if s['status'] == 'STOP_LOSS'])
        
        # 计算平均盈亏
        pnls = [s.get('pnl', 0) for s in sigs if s.get('pnl') is not None]
        avg_pnl = np.mean(pnls) if pnls else 0
        
        # 计算胜率
        profitable = len([p for p in pnls if p > 0])
        losing = len([p for p in pnls if p < 0])
        total_closed = profitable + losing
        win_rate = (profitable / total_closed * 100) if total_closed > 0 else 0
        
        print(f"\n{strategy}:")
        print(f"  总信号：{total} (活跃：{active_count}, 止损：{sl_count})")
        if pnls:
            print(f"  胜率：{win_rate:.1f}% ({profitable}盈/{losing}亏)")
            print(f"  平均盈亏：{avg_pnl:.2f}%")
            print(f"  最大盈利：{max(pnls):.2f}%")
            print(f"  最大亏损：{min(pnls):.2f}%")
    
    # 方向统计
    long_signals = [s for s in signals if s.get('direction') == 'LONG']
    short_signals = [s for s in signals if s.get('direction') == 'SHORT']
    
    print()
    print("=== 方向统计 ===")
    print(f"LONG: {len(long_signals)} 个")
    print(f"SHORT: {len(short_signals)} 个")
    
    # 优化后模拟
    print()
    print("=" * 80)
    print("📈 优化后模拟回测")
    print("=" * 80)
    
    filtered = []
    filtered_reasons = defaultdict(int)
    
    for sig in signals:
        # 趋势过滤（假设 BULL 市场）
        if sig.get('direction') == 'SHORT':
            filtered_reasons['trend_filter'] += 1
            continue
        
        # 置信度过滤
        if sig.get('confidence', 0) < 85:
            filtered_reasons['confidence'] += 1
            continue
        
        filtered.append(sig)
    
    print(f"趋势过滤：{filtered_reasons['trend_filter']} 个 (逆势 SHORT)")
    print(f"置信度过滤：{filtered_reasons['confidence']} 个 (<85%)")
    print(f"优化后剩余：{len(filtered)} 个")
    
    if filtered:
        pnls = [s.get('pnl', 0) for s in filtered if s.get('pnl') is not None]
        profitable = len([p for p in pnls if p > 0])
        losing = len([p for p in pnls if p < 0])
        win_rate = (profitable / (profitable + losing) * 100) if (profitable + losing) > 0 else 0
        avg_pnl = np.mean(pnls) if pnls else 0
        
        print()
        print("优化后表现:")
        print(f"  胜率：{win_rate:.1f}%")
        print(f"  平均盈亏：{avg_pnl:.2f}%")
    else:
        print()
        print("✅ 所有历史信号都被过滤了")
        print("说明优化生效：不再逆势交易")
    
    print()
    print("=" * 80)
    print("💡 结论")
    print("=" * 80)
    
    if len(stopped_loss) > 0:
        sl_short = len([s for s in stopped_loss if s.get('direction') == 'SHORT'])
        print(f"止损信号中 SHORT 占比：{sl_short / len(stopped_loss) * 100:.1f}%")
        if sl_short / len(stopped_loss) > 0.8:
            print("⚠️  大部分亏损来自逆势 SHORT")
            print("✅ 优化后已过滤逆势信号")
    
    print()
    print("需要更多历史数据才能进行有效回测")
    print("建议积累 30-90 天实盘数据后再回测")
    
    print("=" * 80)
    
    conn.close()


def backtest_from_trading_db():
    """从 trading.db 回测（如果有信号记录）"""
    print()
    print("=" * 80)
    print("🧪 trading.db 回测")
    print("=" * 80)
    
    conn = sqlite3.connect('cache/trading.db')
    cursor = conn.cursor()
    
    # 检查 signals 表
    cursor.execute('SELECT COUNT(*) FROM signals')
    count = cursor.fetchone()[0]
    print(f"signals 表记录数：{count}")
    
    if count > 0:
        cursor.execute('''
            SELECT direction, status, COUNT(*) 
            FROM signals 
            GROUP BY direction, status
        ''')
        for row in cursor.fetchall():
            print(f"  {row[0]} {row[1]}: {row[2]} 个")
    else:
        print("  ❌ 没有信号记录")
    
    conn.close()


def main():
    """主函数"""
    # 回测 signals.db
    backtest_from_signals_db()
    
    # 回测 trading.db
    backtest_from_trading_db()


if __name__ == '__main__':
    main()
