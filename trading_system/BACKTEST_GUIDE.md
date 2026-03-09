# 新策略回测指南

## 回测脚本

### 1. 综合回测（所有新策略）
```bash
cd /home/wz/.openclaw/workspace/trading_system
python3 backtest_new_strategies.py
```

**回测策略：**
- Volatility Squeeze (波动率收缩)
- Money Flow (资金流追踪)
- Liquidity Hunt (流动性猎杀)
- Multi-Timeframe Resonance (多周期共振) - 需要实时 API

**默认配置：**
- 初始资金：$100,000
- 回测期间：2023-01-01 到 2026-03-09
- 测试标的：BTC-USD, ETH-USD
- 仓位：每笔 20%

---

## 回测结果查看

回测结果保存在：
```
backtest/results/new_strategies_backtest_YYYYMMDD_HHMMSS.json
```

### 关键指标

| 指标 | 含义 | 好坏标准 |
|------|------|----------|
| **总收益率** | 整体赚了多少 | >20% 优秀 |
| **夏普比率** | 风险调整后收益 | >1.0 良好，>1.5 优秀 |
| **最大回撤** | 最大亏损幅度 | <20% 安全 |
| **胜率** | 盈利交易占比 | >50% 良好 |
| **盈亏比** | 平均盈利/平均亏损 | >2.0 优秀 |
| **总交易次数** | 交易频率 | 50-200 适中 |

---

## 单个策略回测

### 波动率收缩策略
```python
from strategies import VolatilitySqueezeStrategy
from backtest.data_loader import load_data

df = load_data('BTC-USD', start_date='2023-01-01', end_date='2026-03-09')
strategy = VolatilitySqueezeStrategy()

# 生成信号
signals = []
for i in range(len(df)):
    signal = strategy.generate_signal(df.iloc[:i+1], 'BTC-USD')
    if signal:
        signals.append(signal)

print(f"生成 {len(signals)} 个信号")
```

### 资金流追踪策略
```python
from strategies import MoneyFlowStrategy

strategy = MoneyFlowStrategy()
signal = strategy.generate_signal(df, 'BTC-USD')
```

### 流动性猎杀策略
```python
from strategies import LiquidityHuntStrategy

strategy = LiquidityHuntStrategy()
signal = strategy.generate_signal(df, 'BTC-USD')
```

---

## 参数优化

每个策略的参数可以在策略文件中调整：

### 波动率收缩
```python
# strategies/volatility_squeeze.py
self.squeeze_percentile = 0.15  # 调低更敏感，调高更严格
self.volume_multiplier = 1.5    # 成交量确认倍数
```

### 资金流追踪
```python
# strategies/money_flow.py
self.large_order_threshold = 10000  # 大单阈值
self.net_flow_threshold = 500000     # 净流入阈值
```

### 流动性猎杀
```python
# strategies/liquidity_hunt.py
self.swing_lookback = 20  # Swing 检测窗口
self.confirmation_candles = 3  # 确认 K 线数
```

### 多周期共振
```python
# strategies/multi_timeframe.py
self.trend_timeframe = '1D'    # 趋势周期
self.signal_timeframe = '4H'   # 信号周期
self.entry_timeframe = '1H'    # 入场周期
```

---

## 回测注意事项

### 1. 未来函数
确保策略不使用未来数据：
- ✅ 用 `df.iloc[:i+1]` 获取历史数据
- ❌ 不要用 `df.iloc[-1]` 在整个数据集上

### 2. 幸存者偏差
- 回测时包含已下架币种会导致结果偏乐观
- 使用当前活跃币种列表

### 3. 滑点和手续费
回测引擎已包含：
- 手续费：0.1% (买卖各一次)
- 滑点：0.05%

### 4. 多周期策略特殊性
多周期共振需要实时获取多时间周期数据，回测时：
- 速度较慢（需要调用 API）
- 建议单独回测
- 可以用历史 K 线模拟（需要修改策略）

---

## 预期结果

根据策略特性，预期回测结果：

| 策略 | 预期胜率 | 预期盈亏比 | 预期夏普 |
|------|----------|------------|----------|
| 多周期共振 | 55-60% | 2.0-2.5 | 1.0-1.3 |
| 波动率收缩 | 50-55% | 2.5-3.5 | 1.2-1.5 |
| 资金流追踪 | 55-60% | 2.0-3.0 | 1.1-1.4 |
| 流动性猎杀 | 55-60% | 2.0-3.0 | 1.2-1.5 |

**注意：** 实际结果会因市场条件、参数选择而异。

---

## 下一步

1. **运行回测** - 看历史表现
2. **参数优化** - 调整参数提高收益
3. **对比基准** - 和买入持有对比
4. **实盘测试** - 小资金验证

---

_最后更新：2026-03-09_
