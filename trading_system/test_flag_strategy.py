#!/usr/bin/env python3
"""
旗形策略测试 - 使用模拟数据验证策略逻辑
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategies.flag_pattern import FlagPatternStrategy

def generate_test_data_bull_flag() -> pd.DataFrame:
    """
    生成牛市旗测试数据
    
    结构：
    1. 平稳期：10 根 K 线，100 附近震荡
    2. 旗杆：8 根 K 线，从 100 涨到 120 (+20%)
    3. 旗面：8 根 K 线，从 120 回调到 114 (-5%)
    4. 突破：1 根 K 线，突破 120
    """
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
        price = 100 + (i + 1) * 2.5  # 每根涨 2.5%
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
        price = 120 - i * 0.5  # 每根跌 0.5%
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
        'high': 123,  # 突破旗面高点 120
        'low': 114,
        'close': 121,
        'volume': 3000000
    })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df


def generate_test_data_bear_flag() -> pd.DataFrame:
    """
    生成熊市旗测试数据
    
    结构：
    1. 平稳期：10 根 K 线，100 附近震荡
    2. 旗杆：8 根 K 线，从 100 跌到 80 (-20%)
    3. 旗面：8 根 K 线，从 80 反弹到 84 (+5%)
    4. 突破：1 根 K 线，突破 80
    """
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
    
    # 旗杆（8 根 K 线，强劲下跌）
    for i in range(8):
        date = base_date + timedelta(days=10 + i)
        price = 100 - (i + 1) * 2.5  # 每根跌 2.5%
        data.append({
            'date': date,
            'open': price,
            'high': price + 0.3,
            'low': price - 0.5,
            'close': price - 0.2,
            'volume': 2000000 + i * 100000
        })
    
    # 旗面（8 根 K 线，向上倾斜整理）
    for i in range(8):
        date = base_date + timedelta(days=18 + i)
        price = 80 + i * 0.5  # 每根涨 0.5%
        data.append({
            'date': date,
            'open': price,
            'high': price + 0.3,
            'low': price - 0.4,
            'close': price + 0.2,
            'volume': 1500000 - i * 50000
        })
    
    # 突破 K 线
    date = base_date + timedelta(days=26)
    data.append({
        'date': date,
        'open': 84,
        'high': 85,
        'low': 78,  # 突破旗面低点 80
        'close': 79,
        'volume': 3000000
    })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df


def test_strategy():
    """测试策略"""
    print("=" * 80)
    print("🚩 旗形策略测试")
    print("=" * 80)
    
    strategy = FlagPatternStrategy()
    
    # 测试牛市旗
    print("\n📈 测试 1: 牛市旗 (Bull Flag)")
    print("-" * 80)
    bull_df = generate_test_data_bull_flag()
    print(f"数据范围：{bull_df.index[0]} 到 {bull_df.index[-1]}")
    print(f"起始价格：{bull_df['close'].iloc[0]:.2f}")
    print(f"旗杆顶部：{bull_df['close'].iloc[17]:.2f}")
    print(f"旗面底部：{bull_df['close'].iloc[25]:.2f}")
    print(f"突破价格：{bull_df['close'].iloc[26]:.2f}")
    
    # 逐步测试
    for i in range(22, 27):
        test_df = bull_df.iloc[:i+1]
        signal = strategy.generate_signal({'1D': test_df}, 'TESTUSDT')
        if signal:
            print(f"\n✅ K 线 {i}: 发现信号!")
            print(f"   形态：{signal['pattern']}")
            print(f"   方向：{signal['direction']}")
            print(f"   价格：{signal['entry_price']}")
            print(f"   置信度：{signal['confidence']:.0f}%")
            print(f"   理由：{signal['reason']}")
            break
        else:
            print(f"K 线 {i}: 无信号")
    
    # 测试熊市旗
    print("\n\n📉 测试 2: 熊市旗 (Bear Flag)")
    print("-" * 80)
    bear_df = generate_test_data_bear_flag()
    print(f"数据范围：{bear_df.index[0]} 到 {bear_df.index[-1]}")
    print(f"起始价格：{bear_df['close'].iloc[0]:.2f}")
    print(f"旗杆底部：{bear_df['close'].iloc[17]:.2f}")
    print(f"旗面顶部：{bear_df['close'].iloc[25]:.2f}")
    print(f"突破价格：{bear_df['close'].iloc[26]:.2f}")
    
    # 逐步测试
    for i in range(22, 27):
        test_df = bear_df.iloc[:i+1]
        signal = strategy.generate_signal({'1D': test_df}, 'TESTUSDT')
        if signal:
            print(f"\n✅ K 线 {i}: 发现信号!")
            print(f"   形态：{signal['pattern']}")
            print(f"   方向：{signal['direction']}")
            print(f"   价格：{signal['entry_price']}")
            print(f"   置信度：{signal['confidence']:.0f}%")
            print(f"   理由：{signal['reason']}")
            break
        else:
            print(f"K 线 {i}: 无信号")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成!")
    print("=" * 80)


if __name__ == '__main__':
    test_strategy()
