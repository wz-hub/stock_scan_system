"""
查看策略信号输出格式
"""
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backtest.data_loader import DataLoader
from strategies import (
    TrendFollowingStrategy,
    MACrossStrategy,
    RSIStrategy,
    BreakoutStrategy
)

# 加载数据
import pandas as pd
df = pd.read_csv('data/BTC-USD.csv', index_col=0, parse_dates=True)

print("=" * 80)
print("策略信号格式示例 - BTC-USD 数据")
print("=" * 80)
print(f"\n数据列：{list(df.columns)}")
print(f"数据范围：{df.index[0]} 至 {df.index[-1]}")
print(f"总行数：{len(df)}")

# 测试的策略
strategies = [
    TrendFollowingStrategy(),
    MACrossStrategy(),
    RSIStrategy(),
    BreakoutStrategy()
]

for strategy in strategies:
    print(f"\n{'='*80}")
    print(f"策略：{strategy.name}")
    print(f"{'='*80}")
    
    # 生成信号
    signals_df = strategy.generate_signals(df)
    
    # 显示输出的列
    print(f"\n输出列：{list(signals_df.columns)}")
    
    # 显示有信号的行
    signal_rows = signals_df[signals_df['signal'] != 0]
    
    print(f"\n总信号数：{len(signal_rows)}")
    
    if len(signal_rows) > 0:
        print(f"\n前 5 个交易信号:")
        print("-" * 80)
        
        for idx, row in signal_rows.head(5).iterrows():
            signal_type = "做多" if row['signal'] == 1 else "做空" if row['signal'] == -1 else "平仓"
            position = row.get('position', 0)
            
            print(f"\n日期：{idx.date()}")
            print(f"  信号：{signal_type} (signal={row['signal']})")
            print(f"  目标仓位：{position}")
            print(f"  收盘价：${row['close']:.2f}")
            
            # 显示策略特定字段
            if 'pattern' in row and row['pattern']:
                print(f"  形态：{row['pattern']}")
            if 'breakout_type' in row and row['breakout_type']:
                print(f"  突破类型：{row['breakout_type']}")
            if 'rsi_signal_type' in row and row['rsi_signal_type']:
                print(f"  RSI 信号：{row['rsi_signal_type']}")
            if 'bb_signal_type' in row and row['bb_signal_type']:
                print(f"  布林带信号：{row['bb_signal_type']}")
            if 'ma_alignment' in row and row['ma_alignment']:
                print(f"  均线排列：{row['ma_alignment']}")
            if 'stop_loss' in row and not pd.isna(row['stop_loss']) and row['stop_loss'] != 0:
                print(f"  止损价：${row['stop_loss']:.2f}")

print("\n" + "=" * 80)
print("信号字段说明")
print("=" * 80)
print("""
通用字段:
  - signal: 交易信号
      1  = 做多/平空
      -1 = 做空/平多
      0  = 无操作
  
  - position: 目标仓位
      1  = 持有多单
      -1 = 持有空单
      0  = 空仓
  
  - close: 当前收盘价
  - date: 交易日期

策略特定字段:
  - pattern: K 线/图表形态 (123 反转、支撑阻力等)
  - breakout_type: 突破类型 (ATR/布林带/价格突破)
  - rsi_signal_type: RSI 信号类型 (超买/超卖/背离)
  - bb_signal_type: 布林带信号 (均值回归/挤压突破)
  - ma_alignment: 均线排列 (多头/空头/中性)
  - stop_loss: 止损价格
  - atr: ATR 波动率值
""")
