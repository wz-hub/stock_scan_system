#!/usr/bin/env python3
"""
旗形策略调试 - 查看旗杆查找逻辑
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
    
    # 旗面（8 根 K 线，向下倾斜整理）
    for i in range(8):
        date = base_date + timedelta(days=18 + i)
        price = 120 - i * 0.75
        data.append({
            'date': date,
            'open': price,
            'high': price + 0.4,
            'low': price - 0.3,
            'close': price - 0.2,
            'volume': 1500000 - i * 50000
        })
    
    # 突破 K 线
    date = base_date + timedelta(days=26)
    data.append({
        'date': date,
        'open': 115,
        'high': 123,
        'low': 114,
        'close': 121,
        'volume': 3000000
    })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df


def debug_pole():
    """调试旗杆查找"""
    print("=" * 80)
    print("🔍 旗杆查找调试")
    print("=" * 80)
    
    strategy = FlagPatternStrategy()
    df = generate_test_data_bull_flag()
    
    print(f"\n数据长度：{len(df)}")
    print(f"价格范围：{df['close'].min():.2f} - {df['close'].max():.2f}")
    
    # 打印关键位置的价格
    print("\n关键位置价格:")
    for i in [9, 10, 15, 17, 18, 25, 26]:
        if i < len(df):
            print(f"  K{i}: close={df['close'].iloc[i]:.2f}, high={df['high'].iloc[i]:.2f}, low={df['low'].iloc[i]:.2f}")
    
    # 手动测试_find_pole
    print("\n" + "-" * 80)
    print("测试_find_pole:")
    pole = strategy._find_pole(df)
    if pole:
        print(f"✅ 找到旗杆:")
        print(f"   起始索引：{pole['start_idx']} (close={df['close'].iloc[pole['start_idx']]:.2f})")
        print(f"   结束索引：{pole['end_idx']} (close={df['close'].iloc[pole['end_idx']]:.2f})")
        print(f"   涨幅：{pole['change_pct']:.2f}%")
        print(f"   方向：{pole['direction']}")
    else:
        print("❌ 未找到旗杆")
        
        # 手动检查可能的旗杆
        print("\n手动检查可能的旗杆:")
        for start in range(5, 15):
            for end in range(start + 5, min(start + 12, len(df))):
                start_price = df['close'].iloc[start]
                end_price = df['close'].iloc[end]
                change = (end_price - start_price) / start_price * 100
                if abs(change) >= 4:
                    print(f"  K{start}→K{end}: {start_price:.2f}→{end_price:.2f} ({change:+.2f}%)")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    debug_pole()
