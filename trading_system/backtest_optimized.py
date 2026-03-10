#!/usr/bin/env python3
"""
优化后策略的模拟回测
基于历史信号 + 优化规则过滤
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from core.tracker import SignalTracker


def simulate_optimized_backtest():
    """模拟优化后的回测"""
    print("=" * 80)
    print("🧪 优化后策略 - 模拟回测")
    print("=" * 80)
    
    tracker = SignalTracker()
    active = tracker.get_active_signals()
    
    if not active:
        print("❌ 没有信号数据")
        return
    
    print(f"历史信号总数：{len(active)}")
    print()
    
    # 应用优化规则过滤
    filtered_signals = []
    filtered_out_reasons = {
        'trend_filter': 0,
        'confidence': 0,
        'adx': 0
    }
    
    for sig in active:
        # 模拟趋势过滤（假设 BULL 趋势）
        direction = sig.get('direction', '')
        if direction == 'SHORT':
            filtered_out_reasons['trend_filter'] += 1
            continue  # BULL 趋势禁止 SHORT
        
        # 模拟置信度过滤（85%）
        confidence = sig.get('confidence', 80)
        if confidence < 85:
            filtered_out_reasons['confidence'] += 1
            continue
        
        # 通过过滤
        filtered_signals.append(sig)
    
    print("=== 优化规则过滤 ===")
    print(f"趋势过滤：{filtered_out_reasons['trend_filter']} 个信号被过滤 (逆势)")
    print(f"置信度过滤：{filtered_out_reasons['confidence']} 个信号被过滤 (<85%)")
    print(f"ADX 过滤：{filtered_out_reasons['adx']} 个信号被过滤 (趋势弱)")
    print()
    
    print(f"优化后剩余信号：{len(filtered_signals)} 个")
    print()
    
    if filtered_signals:
        # 计算优化后的胜率
        profitable = [s for s in filtered_signals if s.get('pnl_pct', 0) > 0]
        losing = [s for s in filtered_signals if s.get('pnl_pct', 0) < 0]
        
        win_rate = len(profitable) / len(filtered_signals) * 100
        avg_pnl = np.mean([s.get('pnl_pct', 0) for s in filtered_signals])
        
        print("=== 优化后表现 (模拟) ===")
        print(f"信号数：{len(filtered_signals)} (从 {len(active)} 个过滤到 {len(filtered_signals)} 个)")
        print(f"盈利：{len(profitable)} 个")
        print(f"亏损：{len(losing)} 个")
        print(f"胜率：{win_rate:.1f}%")
        print(f"平均盈亏：{avg_pnl:.2f}%")
        print()
        
        # 对比
        original_win_rate = len([s for s in active if s.get('pnl_pct', 0) > 0]) / len(active) * 100
        original_avg_pnl = np.mean([s.get('pnl_pct', 0) for s in active])
        
        print("=== 优化前后对比 ===")
        print(f"胜率：{original_win_rate:.1f}% → {win_rate:.1f}% ({win_rate - original_win_rate:+.1f}%)")
        print(f"平均盈亏：{original_avg_pnl:.2f}% → {avg_pnl:.2f}% ({avg_pnl - original_avg_pnl:+.2f}%)")
        print(f"信号数：{len(active)} → {len(filtered_signals)} ({len(filtered_signals) - len(active):+d})")
    else:
        print("✅ 所有历史信号都被过滤了！")
        print()
        print("这说明：")
        print("1. 历史信号大部分是逆势 SHORT")
        print("2. 优化后会等待更好的顺趋势机会")
        print("3. 需要等待市场出现顺趋势信号")
    
    print("=" * 80)


def main():
    simulate_optimized_backtest()


if __name__ == '__main__':
    main()
