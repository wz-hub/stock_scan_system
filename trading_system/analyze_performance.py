#!/usr/bin/env python3
"""
策略表现分析报告
基于现有活跃信号和历史平仓记录
"""
import sys
from pathlib import Path
from datetime import datetime
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from core.tracker import SignalTracker


def analyze_strategy_performance():
    """分析策略表现"""
    print("=" * 80)
    print("📊 策略表现分析报告")
    print("=" * 80)
    print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print("=" * 80)
    
    tracker = SignalTracker()
    
    # 获取活跃信号
    active = tracker.get_active_signals()
    
    # 获取统计
    stats = tracker.get_stats(days=7)
    
    print()
    print("=== 总体统计 (近 7 天) ===")
    print(f"总信号数：{stats['total_signals']}")
    print(f"活跃信号：{stats['active_signals']}")
    
    closed = stats.get('closed_signals', {})
    if isinstance(closed, dict):
        tp = closed.get('TAKE_PROFIT', {}).get('count', 0)
        sl = closed.get('STOP_LOSS', {}).get('count', 0)
        print(f"已平仓：{tp + sl}")
        print(f"  └─ 止盈：{tp}")
        print(f"  └─ 止损：{sl}")
    print()
    
    # 活跃信号分析
    if active:
        print("=== 活跃信号分析 ===")
        
        # 方向分布
        long_count = len([s for s in active if s.get('direction') == 'LONG'])
        short_count = len([s for s in active if s.get('direction') == 'SHORT'])
        
        print(f"LONG: {long_count} 个 ({long_count/len(active)*100:.1f}%)")
        print(f"SHORT: {short_count} 个 ({short_count/len(active)*100:.1f}%)")
        print()
        
        # 盈亏分布
        profitable = [s for s in active if s.get('pnl_pct', 0) > 0]
        losing = [s for s in active if s.get('pnl_pct', 0) < 0]
        neutral = [s for s in active if abs(s.get('pnl_pct', 0)) < 0.1]
        
        print(f"盈利：{len(profitable)} 个 ({len(profitable)/len(active)*100:.1f}%)")
        print(f"亏损：{len(losing)} 个 ({len(losing)/len(active)*100:.1f}%)")
        print(f"持平：{len(neutral)} 个")
        print()
        
        # 平均盈亏
        avg_pnl = np.mean([s.get('pnl_pct', 0) for s in active])
        median_pnl = np.median([s.get('pnl_pct', 0) for s in active])
        
        print(f"平均盈亏：{avg_pnl:.2f}%")
        print(f"中位数盈亏：{median_pnl:.2f}%")
        print()
        
        # 按策略统计
        by_strategy = {}
        for s in active:
            strategy = s.get('strategy_name', 'Unknown')
            if strategy not in by_strategy:
                by_strategy[strategy] = []
            by_strategy[strategy].append(s)
        
        print("=== 按策略统计 ===")
        for strategy, signals in sorted(by_strategy.items()):
            avg = np.mean([s.get('pnl_pct', 0) for s in signals])
            win_rate = len([s for s in signals if s.get('pnl_pct', 0) > 0]) / len(signals) * 100
            long_sig = len([s for s in signals if s.get('direction') == 'LONG'])
            short_sig = len([s for s in signals if s.get('direction') == 'SHORT'])
            
            print(f"\n{strategy}:")
            print(f"  信号数：{len(signals)} (LONG: {long_sig}, SHORT: {short_sig})")
            print(f"  胜率：{win_rate:.1f}%")
            print(f"  平均盈亏：{avg:.2f}%")
        print()
        
        # 最佳/最差信号
        sorted_by_pnl = sorted(active, key=lambda x: x.get('pnl_pct', 0), reverse=True)
        
        print("=== 最佳信号 TOP 5 ===")
        for i, sig in enumerate(sorted_by_pnl[:5], 1):
            print(f"{i}. {sig['symbol']} {sig['direction']}: +{sig.get('pnl_pct', 0):.2f}%")
        print()
        
        print("=== 最差信号 TOP 5 ===")
        for i, sig in enumerate(sorted_by_pnl[-5:], 1):
            pnl = sig.get('pnl_pct', 0)
            print(f"{i}. {sig['symbol']} {sig['direction']}: {pnl:.2f}%")
        print()
        
        # 亏损信号特征分析
        big_losers = [s for s in active if s.get('pnl_pct', 0) < -2.0]
        if big_losers:
            print("=== 大额亏损信号分析 (>2%) ===")
            print(f"数量：{len(big_losers)} 个")
            
            long_losers = len([s for s in big_losers if s.get('direction') == 'LONG'])
            short_losers = len([s for s in big_losers if s.get('direction') == 'SHORT'])
            
            print(f"LONG: {long_losers} 个")
            print(f"SHORT: {short_losers} 个")
            
            if short_losers > long_losers * 2:
                print()
                print("⚠️  发现问题：大部分亏损来自 SHORT 信号")
                print("   可能原因：市场是上涨趋势，策略逆势做空")
                print("   建议：添加趋势过滤，避免逆势交易")
        print()
        
        # 评估
        print("=" * 80)
        print("📈 策略评估")
        print("=" * 80)
        
        current_win_rate = len(profitable) / len(active) * 100
        
        if current_win_rate >= 50:
            print("✅ 胜率良好 (≥50%)")
        elif current_win_rate >= 40:
            print("⚠️  胜率一般 (40-50%)")
        else:
            print("❌ 胜率较低 (<40%)")
        
        if avg_pnl > 0:
            print("✅ 平均盈利为正")
        else:
            print("❌ 平均盈利为负")
        
        if len(big_losers) > 0:
            print(f"⚠️  有 {len(big_losers)} 个大额亏损信号 (>2%)")
        
        # 优化建议
        print()
        print("=" * 80)
        print("💡 优化建议")
        print("=" * 80)
        
        if short_losers > long_losers * 2:
            print("1. 添加趋势过滤 - 避免在上涨趋势中做空")
            print("2. 添加 ADX 指标 - 只在强趋势时交易")
        
        if avg_pnl < -1:
            print("3. 降低止损倍数 - 从 2ATR 降至 1.5ATR")
            print("4. 降低止盈目标 - 从 3R 降至 2R")
        
        if current_win_rate < 40:
            print("5. 提高置信度门槛 - 从 80% 提至 85%")
            print("6. 添加持仓时间限制 - 避免长期亏损")
        
        print("=" * 80)
        
        return {
            'total_signals': len(active),
            'long_signals': long_count,
            'short_signals': short_count,
            'profitable': len(profitable),
            'losing': len(losing),
            'win_rate': current_win_rate,
            'avg_pnl': avg_pnl,
            'big_losers': len(big_losers)
        }
    else:
        print("❌ 没有活跃信号")
        return {}


def main():
    """主函数"""
    stats = analyze_strategy_performance()
    
    if stats:
        # 保存结果
        import json
        results = {
            'timestamp': datetime.now().isoformat(),
            'type': 'strategy_performance_analysis',
            'stats': stats
        }
        
        with open('strategy_performance_report.json', 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 报告已保存：strategy_performance_report.json")


if __name__ == '__main__':
    main()
