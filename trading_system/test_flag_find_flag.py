#!/usr/bin/env python3
"""
旗形策略调试 - 专门调试旗面查找
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

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
        'high': 123,
        'low': 114,
        'close': 121,
        'volume': 3000000
    })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df


def debug_find_flag():
    """调试旗面查找"""
    print("=" * 80)
    print("🔍 旗面查找调试")
    print("=" * 80)
    
    df = generate_test_data_bull_flag()
    
    # 手动定义旗杆
    pole = {
        'end_idx': 17,  # K17 是旗杆顶部
        'end_price': 120.20,
        'direction': 'BULL'
    }
    
    flag_start = pole['end_idx'] + 1  # K18
    flag_min_bars = 4
    flag_max_bars = 20
    flag_max_retrace = 61.8
    
    print(f"\n旗杆结束：K{pole['end_idx']} ({pole['end_price']:.2f})")
    print(f"旗面起始：K{flag_start}")
    print(f"数据长度：{len(df)}")
    
    # 手动遍历
    print("\n遍历可能的旗面:")
    for flag_end in range(flag_start + flag_min_bars - 1, min(flag_start + flag_max_bars, len(df) - 1)):
        flag_df = df.iloc[flag_start:flag_end + 1]
        
        flag_high = flag_df['high'].max()
        flag_low = flag_df['low'].min()
        flag_open = df['open'].iloc[flag_start]
        
        retrace_pct = (pole['end_price'] - flag_low) / pole['end_price'] * 100
        advance_pct = (flag_high - pole['end_price']) / pole['end_price'] * 100
        flag_range = (flag_high - flag_low) / flag_open * 100
        
        print(f"\nK{flag_start}-K{flag_end} ({len(flag_df)}根):")
        print(f"  高点：{flag_high:.2f}, 低点：{flag_low:.2f}")
        print(f"  回撤：{retrace_pct:.2f}%, 反弹：{advance_pct:.2f}%, 波动：{flag_range:.2f}%")
        
        # 检查条件
        if retrace_pct > flag_max_retrace:
            print(f"  ❌ 回撤过大")
            continue
        if advance_pct > 10:
            print(f"  ❌ 反弹过大")
            continue
        if flag_range > 8:
            print(f"  ❌ 波动过大")
            continue
        
        print(f"  ✅ 符合条件!")
        break
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    debug_find_flag()
