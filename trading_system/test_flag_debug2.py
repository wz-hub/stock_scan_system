#!/usr/bin/env python3
"""
旗形策略调试 - 详细查看旗面查找过程
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_test_data_bull_flag() -> pd.DataFrame:
    """生成牛市旗测试数据"""
    data = []
    base_date = datetime(2024, 1, 1)
    
    # 旗杆前奏（平稳期）
    for i in range(10):
        date = base_date + timedelta(days=i)
        data.append({
            'date': date,
            'open': 100 + i * 0.2,
            'high': 100 + i * 0.2 + 0.5,
            'low': 100 + i * 0.2 - 0.3,
            'close': 100 + i * 0.2 + 0.3,
            'volume': 1000000
        })
    
    # 旗杆（强劲上涨）
    for i in range(10):
        date = base_date + timedelta(days=10 + i)
        start_price = 103
        end_price = 125
        progress = i / 9
        price = start_price + (end_price - start_price) * progress
        data.append({
            'date': date,
            'open': price,
            'high': price + 1.5,
            'low': price - 0.5,
            'close': price + 1,
            'volume': 2000000 + i * 100000
        })
    
    # 旗面（向下倾斜整理）
    for i in range(10):
        date = base_date + timedelta(days=20 + i)
        start_price = 125
        end_price = 118
        progress = i / 9
        price = start_price - (start_price - end_price) * progress
        data.append({
            'date': date,
            'open': price,
            'high': price + 0.8,
            'low': price - 0.5,
            'close': price - 0.3,
            'volume': 1500000 - i * 50000
        })
    
    # 突破 K 线
    date = base_date + timedelta(days=30)
    data.append({
        'date': date,
        'open': 118,
        'high': 128,
        'low': 117,
        'close': 126,
        'volume': 3000000
    })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df


def debug_flag():
    """调试旗面查找"""
    print("=" * 80)
    print("🔍 旗面查找调试")
    print("=" * 80)
    
    df = generate_test_data_bull_flag()
    
    # 手动模拟旗杆
    pole = {
        'start_idx': 13,
        'end_idx': 22,  # 旗杆结束
        'change_pct': 15.0,
        'direction': 'BULL',
        'start_price': 103,
        'end_price': 124  # 旗杆顶部价格
    }
    
    pole_end = pole['end_idx']
    flag_start = pole_end + 1
    flag_min_bars = 5
    flag_max_bars = 20
    flag_max_retrace = 61.8
    
    print(f"\n旗杆结束索引：{pole_end}")
    print(f"旗面起始索引：{flag_start}")
    print(f"数据总长度：{len(df)}")
    
    print(f"\n旗杆顶部价格：{pole['end_price']:.2f}")
    
    # 遍历可能的旗面
    for flag_end in range(flag_start + flag_min_bars - 1, min(flag_start + flag_max_bars, len(df))):
        flag_df = df.iloc[flag_start:flag_end + 1]
        
        flag_high = flag_df['high'].max()
        flag_low = flag_df['low'].min()
        flag_open = df['open'].iloc[flag_start]
        flag_close = df['close'].iloc[flag_end]
        
        retrace_pct = (pole['end_price'] - flag_low) / pole['end_price'] * 100
        advance_pct = (flag_high - pole['end_price']) / pole['end_price'] * 100
        flag_range = (flag_high - flag_low) / flag_open * 100
        
        print(f"\nflag_end={flag_end}, bars={len(flag_df)}:")
        print(f"  高点：{flag_high:.2f}, 低点：{flag_low:.2f}")
        print(f"  回撤：{retrace_pct:.2f}%, 反弹：{advance_pct:.2f}%")
        print(f"  波动范围：{flag_range:.2f}%")
        
        # 检查条件
        if retrace_pct > flag_max_retrace:
            print(f"  ❌ 回撤过大 ({retrace_pct:.2f}% > {flag_max_retrace}%)")
            continue
        if advance_pct > 10:
            print(f"  ❌ 反弹过大 ({advance_pct:.2f}% > 10%)")
            continue
        if flag_range > 8:
            print(f"  ❌ 波动过大 ({flag_range:.2f}% > 8%)")
            continue
        
        print(f"  ✅ 符合条件!")
        break
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    debug_flag()
