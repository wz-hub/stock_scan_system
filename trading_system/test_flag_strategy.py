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
    1. 旗杆：10 根 K 线，从 100 涨到 120 (+20%)
    2. 旗面：10 根 K 线，从 120 回调到 115 (-4%)
    3. 突破：1 根 K 线，突破 120
    """
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
        'high': 128,  # 突破旗面高点 125
        'low': 117,
        'close': 126,
        'volume': 3000000
    })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df


def generate_test_data_bear_flag() -> pd.DataFrame:
    """
    生成熊市旗测试数据
    
    结构：
    1. 旗杆：10 根 K 线，从 100 跌到 80 (-20%)
    2. 旗面：10 根 K 线，从 80 反弹到 85 (+6%)
    3. 突破：1 根 K 线，突破 80
    """
    data = []
    base_date = datetime(2024, 1, 1)
    
    # 旗杆前奏（平稳期）
    for i in range(10):
        date = base_date + timedelta(days=i)
        data.append({
            'date': date,
            'open': 100 - i * 0.2,
            'high': 100 - i * 0.2 + 0.5,
            'low': 100 - i * 0.2 - 0.3,
            'close': 100 - i * 0.2 - 0.3,
            'volume': 1000000
        })
    
    # 旗杆（强劲下跌）
    for i in range(10):
        date = base_date + timedelta(days=10 + i)
        start_price = 98
        end_price = 78
        progress = i / 9
        price = start_price - (start_price - end_price) * progress
        data.append({
            'date': date,
            'open': price,
            'high': price + 0.5,
            'low': price - 1.5,
            'close': price - 1,
            'volume': 2000000 + i * 100000
        })
    
    # 旗面（向上倾斜整理）
    for i in range(10):
        date = base_date + timedelta(days=20 + i)
        start_price = 78
        end_price = 83
        progress = i / 9
        price = start_price + (end_price - start_price) * progress
        data.append({
            'date': date,
            'open': price,
            'high': price + 0.5,
            'low': price - 0.8,
            'close': price + 0.3,
            'volume': 1500000 - i * 50000
        })
    
    # 突破 K 线
    date = base_date + timedelta(days=30)
    data.append({
        'date': date,
        'open': 83,
        'high': 84,
        'low': 76,  # 突破旗面低点 78
        'close': 77,
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
    print(f"旗杆顶部：{bull_df['close'].iloc[19]:.2f}")
    print(f"旗面底部：{bull_df['close'].iloc[29]:.2f}")
    print(f"突破价格：{bull_df['close'].iloc[30]:.2f}")
    
    # 逐步测试
    for i in range(25, 31):
        test_df = bull_df.iloc[:i+1]
        signal = strategy.generate_signal({'1D': test_df}, 'TESTUSDT')
        if signal:
            print(f"\n✅ K 线 {i}: 发现信号!")
            print(f"   形态：{signal['pattern']}")
            print(f"   方向：{signal['direction']}")
            print(f"   价格：{signal['entry_price']}")
            print(f"   置信度：{signal['confidence']:.0f}%")
            print(f"   理由：{signal['reason']}")
    
    # 测试熊市旗
    print("\n\n📉 测试 2: 熊市旗 (Bear Flag)")
    print("-" * 80)
    bear_df = generate_test_data_bear_flag()
    print(f"数据范围：{bear_df.index[0]} 到 {bear_df.index[-1]}")
    print(f"起始价格：{bear_df['close'].iloc[0]:.2f}")
    print(f"旗杆底部：{bear_df['close'].iloc[19]:.2f}")
    print(f"旗面顶部：{bear_df['close'].iloc[29]:.2f}")
    print(f"突破价格：{bear_df['close'].iloc[30]:.2f}")
    
    # 逐步测试
    for i in range(25, 31):
        test_df = bear_df.iloc[:i+1]
        signal = strategy.generate_signal({'1D': test_df}, 'TESTUSDT')
        if signal:
            print(f"\n✅ K 线 {i}: 发现信号!")
            print(f"   形态：{signal['pattern']}")
            print(f"   方向：{signal['direction']}")
            print(f"   价格：{signal['entry_price']}")
            print(f"   置信度：{signal['confidence']:.0f}%")
            print(f"   理由：{signal['reason']}")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成!")
    print("=" * 80)


if __name__ == '__main__':
    test_strategy()
