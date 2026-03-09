"""
列出所有策略的详细信息
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from strategies import (
    TrendFollowingStrategy,
    Reversal123Strategy,
    SupportResistanceStrategy,
    PatternTradingStrategy,
    MACrossStrategy,
    VolatilityBreakoutStrategy,
    PairsTradingStrategy,
    BollingerBandsStrategy,
    RSIStrategy,
    BreakoutStrategy
)

strategies = [
    ("趋势跟踪 (海龟)", TrendFollowingStrategy()),
    ("123/2B 反转", Reversal123Strategy()),
    ("支撑阻力", SupportResistanceStrategy()),
    ("形态交易", PatternTradingStrategy()),
    ("均线交叉", MACrossStrategy()),
    ("波动率突破", VolatilityBreakoutStrategy()),
    ("配对交易", PairsTradingStrategy()),
    ("布林带", BollingerBandsStrategy()),
    ("RSI", RSIStrategy()),
    ("突破策略", BreakoutStrategy())
]

print("="*80)
print("交易策略系统 - 所有策略列表")
print("="*80)
print(f"总策略数：{len(strategies)}\n")

for i, (name, strategy) in enumerate(strategies, 1):
    print(f"{i}. {name}")
    print(f"   类名：{strategy.__class__.__name__}")
    print(f"   内部名称：{strategy.name}")
    print()

print("="*80)
print("策略详细参数")
print("="*80)

for name, strategy in strategies:
    print(f"\n{name}")
    print("-"*60)
    params = strategy.__dict__
    if params:
        for key, value in params.items():
            if not key.startswith('_'):
                print(f"   {key}: {value}")
    else:
        print("   无自定义参数")
