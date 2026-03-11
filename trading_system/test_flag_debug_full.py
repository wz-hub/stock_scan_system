#!/usr/bin/env python3
"""
旗形策略调试 - 完整流程
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategies.flag_pattern import FlagPatternStrategy

def generate_test_data_bull_flag() -> pd.DataFrame:
    """生成牛市旗测试数据"""
    data = []
    base_date = datetime(2024, 1, 1)
    
    # 平稳期（10 根 K 线）
    for i in range(10):
        date = base_date + timedelta(days=i)
        data.append({
            'date': date,
            'open': 100,
            'high': 101,
            'low': 99,
            'close': 100,
            'volume': 1000000
        })
    
    # 旗杆（8 根 K 线，强劲上涨）
    for i in range(8):
        date = base_date + timedelta(days=10 + i)
        price = 100 + (i + 1) * 2.5
        data.append({
            'date': date,
            'open': price,
            'high': price + 0.5,
            'low': price - 0.3,
            'close': price + 0.2,
            'volume': 2000000 + i * 100000
        })
    
    # 旗面（10 根 K 线，向下倾斜整理）
    for i in range(10):
        date = base_date + timedelta(days=18 + i)
        price = 120 - i * 0.5
        data.append({
            'date': date,
            'open': price,
            'high': price + 0.4,
            'low': price - 0.3,
            'close': price - 0.2,
            'volume': 1500000 - i * 50000
        })
    
    # 突破 K 线
    date = base_date + timedelta(days=28)
    data.append({
        'date': date,
        'open': 115,
        'high': 123,  # 突破旗面高点
        'low': 114,
        'close': 121,
        'volume': 3000000
    })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df


def debug_full():
    """完整调试"""
    print("=" * 80)
    print("🔍 旗形策略完整调试")
    print("=" * 80)
    
    strategy = FlagPatternStrategy()
    df = generate_test_data_bull_flag()
    
    print(f"\n数据长度：{len(df)}")
    print(f"价格范围：{df['close'].min():.2f} - {df['close'].max():.2f}")
    
    # 打印关键位置的价格
    print("\n关键位置价格:")
    for i in range(len(df)):
        marker = ""
        if i == 9: marker = " ← 平稳期结束"
        elif i == 17: marker = " ← 旗杆顶部"
        elif i == 27: marker = " ← 旗面结束"
        elif i == 28: marker = " ← 突破 K 线"
        print(f"  K{i:2d}: close={df['close'].iloc[i]:6.2f}, high={df['high'].iloc[i]:6.2f}, low={df['low'].iloc[i]:6.2f}{marker}")
    
    # 测试完整分析
    print("\n" + "-" * 80)
    print("完整分析 (全部数据):")
    analysis = strategy.analyze(df)
    print(f"状态：{analysis['status']}")
    print(f"信号：{analysis['signal']}")
    if 'reason' in analysis:
        print(f"原因：{analysis['reason']}")
    if 'pole' in analysis:
        pole = analysis['pole']
        print(f"\n旗杆:")
        print(f"  起始：K{pole['start_idx']} ({pole['start_price']:.2f})")
        print(f"  结束：K{pole['end_idx']} ({pole['end_price']:.2f})")
        print(f"  涨幅：{pole['change_pct']:.2f}%")
    if 'flag' in analysis:
        flag = analysis['flag']
        print(f"\n旗面:")
        print(f"  起始：K{flag['start_idx']}")
        print(f"  结束：K{flag['end_idx']}")
        print(f"  高点：{flag['high']:.2f}")
        print(f"  低点：{flag['low']:.2f}")
        print(f"  回撤：{flag['retrace_pct']:.2f}%")
    if 'breakout' in analysis:
        breakout = analysis['breakout']
        print(f"\n突破:")
        print(f"  类型：{breakout['type']}")
        print(f"  突破位：{breakout['level']:.2f}")
        print(f"  强度：{breakout['strength']:.2f}%")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    debug_full()
