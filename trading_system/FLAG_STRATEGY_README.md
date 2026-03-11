# 旗形形态策略 (Flag Pattern Strategy)

## 策略概述

旗形是经典的中继形态，表示趋势暂停后继续：

- **🐂 牛市旗 (Bull Flag)**: 急涨 → 小幅回调 → 突破继续涨
- **🐻 熊市旗 (Bear Flag)**: 急跌 → 小幅反弹 → 突破继续跌

## 形态识别规则

### 旗杆 (Pole)
- **长度**: 5-12 根 K 线
- **涨幅/跌幅**: ≥ 4%
- **走势**: 相对平稳，无大幅回调（回撤 < 20%）

### 旗面 (Flag)
- **长度**: 4-20 根 K 线
- **方向**: 与旗杆相反（牛市旗向下，熊市旗向上）
- **回撤**: 不超过旗杆的 61.8%（斐波那契）
- **波动**: 整理区间波动 < 8%

### 突破 (Breakout)
- **牛市旗**: 价格突破旗面高点
- **熊市旗**: 价格突破旗面低点
- **强度**: 突破幅度越大，置信度越高

## 参数配置

```python
# 旗杆参数
pole_min_bars = 5          # 最少 K 线数
pole_max_bars = 12         # 最多 K 线数
pole_min_change = 4.0      # 最小涨幅/跌幅 (%)

# 旗面参数
flag_min_bars = 4          # 最少 K 线数
flag_max_bars = 20         # 最多 K 线数
flag_max_retrace = 61.8    # 最大回撤 (%)

# 止损止盈
stop_loss_pct = 3.0        # 3% 止损
take_profit_pct = 9.0      # 9% 止盈 (3:1 盈亏比)
```

## 使用方法

### 1. 单独使用

```python
from strategies.flag_pattern import FlagPatternStrategy

strategy = FlagPatternStrategy()
signal = strategy.generate_signal({'1D': df}, 'BTCUSDT')

if signal:
    print(f"形态：{signal['pattern']}")
    print(f"方向：{signal['direction']}")
    print(f"入场价：{signal['entry_price']}")
    print(f"止损：{signal['stop_loss_price']}")
    print(f"止盈：{signal['take_profit_price']}")
    print(f"置信度：{signal['confidence']}%")
```

### 2. 扫描脚本

```bash
cd /home/wz/.openclaw/workspace/trading_system
python3 scan_flag_pattern.py
```

### 3. 添加到定时任务

```bash
# 每 30 分钟扫描一次
*/30 * * * * cd /home/wz/.openclaw/workspace/trading_system && python3 scan_flag_pattern.py
```

## 信号示例

```
🐂 BTCUSDT BUY LONG
   形态：Bull Flag
   价格：42500
   止损：41225 (-3%)
   止盈：46325 (+9%)
   盈亏比：3.0:1
   置信度：78%
   理由：牛市旗突破 (旗杆：12.5%, 突破强度：3.2%)
```

## 回测建议

1. **时间周期**: 日线 (1D) 效果最佳
2. **标的**: 高流动性币种/股票
3. **过滤**: 配合成交量、ADX 等指标
4. **风控**: 单笔风险 ≤ 2%

## 文件结构

```
trading_system/
├── strategies/
│   └── flag_pattern.py       # 策略核心
├── scan_flag_pattern.py       # 扫描脚本
├── test_flag_strategy.py      # 测试脚本
└── FLAG_STRATEGY_README.md    # 文档
```

## 注意事项

⚠️ **假突破**: 旗形可能失败，务必设置止损
⚠️ **成交量**: 突破时应伴随放量
⚠️ **市场环境**: 趋势市中效果更好，震荡市容易失败
⚠️ **多时间周期**: 可结合 4H/1D 多周期确认

## 优化方向

1. 增加成交量确认
2. 添加 ADX 趋势强度过滤
3. 结合 RSI 超买超卖
4. 多时间周期共振
