#!/usr/bin/env python3
"""
旗形策略调试 - 专门调试旗杆查找
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
        'high': 123,
        'low': 114,
        'close': 121,
        'volume': 3000000
    })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df


def debug_find_pole():
    """调试旗杆查找"""
    print("=" * 80)
    print("🔍 旗杆查找调试")
    print("=" * 80)
    
    strategy = FlagPatternStrategy()
    df = generate_test_data_bull_flag()
    
    print(f"\n数据长度：{len(df)}")
    
    # 调用_find_pole
    pole = strategy._find_pole(df)
    
    if pole:
        print(f"\n✅ 找到旗杆:")
        print(f"   起始索引：K{pole['start_idx']}")
        print(f"   结束索引：K{pole['end_idx']}")
        print(f"   起始价格：{pole['start_price']:.2f}")
        print(f"   结束价格：{pole['end_price']:.2f}")
        print(f"   涨幅：{pole['change_pct']:.2f}%")
        
        # 检查旗杆结束后是否有足够空间给旗面
        flag_start = pole['end_idx'] + 1
        remaining_bars = len(df) - flag_start
        print(f"\n   旗面起始：K{flag_start}")
        print(f"   剩余 K 线数：{remaining_bars}")
        print(f"   旗面最小要求：{strategy.flag_min_bars}")
        print(f"   是否足够：{'✅ 是' if remaining_bars >= strategy.flag_min_bars + 1 else '❌ 否'}")
    else:
        print("\n❌ 未找到旗杆")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    debug_find_pole()
