#!/usr/bin/env python3
"""
旗形策略调试 - 查看每一步的分析结果
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategies.flag_pattern import FlagPatternStrategy

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


def debug_strategy():
    """调试策略"""
    print("=" * 80)
    print("🔍 旗形策略调试")
    print("=" * 80)
    
    strategy = FlagPatternStrategy()
    df = generate_test_data_bull_flag()
    
    print(f"\n数据长度：{len(df)}")
    print(f"价格范围：{df['close'].min():.2f} - {df['close'].max():.2f}")
    
    # 测试_find_pole
    print("\n" + "-" * 80)
    print("测试 1: 寻找旗杆")
    print("-" * 80)
    pole = strategy._find_pole(df)
    if pole:
        print(f"✅ 找到旗杆:")
        print(f"   起始索引：{pole['start_idx']}")
        print(f"   结束索引：{pole['end_idx']}")
        print(f"   涨幅：{pole['change_pct']:.2f}%")
        print(f"   方向：{pole['direction']}")
        print(f"   起始价格：{pole['start_price']:.2f}")
        print(f"   结束价格：{pole['end_price']:.2f}")
    else:
        print("❌ 未找到旗杆")
    
    # 测试_find_flag
    if pole:
        print("\n" + "-" * 80)
        print("测试 2: 寻找旗面")
        print("-" * 80)
        flag = strategy._find_flag(df, pole)
        if flag:
            print(f"✅ 找到旗面:")
            print(f"   起始索引：{flag['start_idx']}")
            print(f"   结束索引：{flag['end_idx']}")
            print(f"   回撤：{flag['retrace_pct']:.2f}%")
            print(f"   趋势：{flag['trend']}")
            print(f"   高点：{flag['high']:.2f}")
            print(f"   低点：{flag['low']:.2f}")
        else:
            print("❌ 未找到旗面")
        
        # 测试_check_breakout
        if flag:
            print("\n" + "-" * 80)
            print("测试 3: 检查突破")
            print("-" * 80)
            breakout = strategy._check_breakout(df, pole, flag)
            if breakout:
                print(f"✅ 发现突破:")
                print(f"   类型：{breakout['type']}")
                print(f"   突破位：{breakout['level']:.2f}")
                print(f"   强度：{breakout['strength']:.2f}%")
            else:
                print("❌ 未发现突破")
    
    # 完整分析
    print("\n" + "-" * 80)
    print("测试 4: 完整分析")
    print("-" * 80)
    analysis = strategy.analyze(df)
    print(f"状态：{analysis['status']}")
    print(f"信号：{analysis['signal']}")
    if 'reason' in analysis:
        print(f"原因：{analysis['reason']}")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    debug_strategy()
