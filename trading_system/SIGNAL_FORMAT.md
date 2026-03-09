# 交易信号格式规范 - v1.0

## 📋 概述

本系统生成**纯信号推送**，不包含自动下单功能。信号包含完整的风险管理信息，供人工决策参考。

---

## 🎯 核心设计理念

1. **完整性** - 包含决策所需的所有信息
2. **简洁性** - 推送消息一目了然
3. **可追溯** - 每个信号有唯一 ID
4. **风险管理** - 强制包含止损/止盈/仓位

---

## 📊 信号数据结构 (JSON)

### 完整字段说明

```json
{
  // === 基础信息 (5 个字段) ===
  "signal_id": "SIG-20241229-BTC-RSI-004",     // 唯一标识
  "timestamp": "2024-12-29T00:00:00Z",          // 生成时间
  "symbol": "BTC-USD",                          // 交易标的
  "timeframe": "1D",                            // 时间周期
  "strategy_name": "RSI",                       // 策略名称
  
  // === 策略分类 (1 个字段) ===
  "strategy_category": "rsi",                   // 策略类型
  
  // === 价格信息 (2 个字段) ===
  "current_price": 93530.23,                    // 当前价格
  "price_change_24h": -1.72,                    // 24h 涨跌幅 %
  
  // === 核心信号 (5 个字段) ===
  "action": "BUY",                              // BUY/SELL/WATCH
  "direction": "LONG",                          // LONG/SHORT/NEUTRAL
  "signal_type": "OPEN",                        // OPEN/CLOSE/ADD
  "priority": "LOW",                            // HIGH/MEDIUM/LOW
  "confidence": 64.0,                           // 置信度 0-100
  
  // === 信号理由 (2 个字段) ===
  "reason": "RSI 信号，超买超卖",                // 文字说明
  "pattern": "",                                // 形态名称
  
  // === 入场信息 (2 个字段) ===
  "entry_price": 93530.23,                      // 建议入场价
  "entry_type": "MARKET",                       // MARKET/LIMIT
  
  // === 风险管理 (6 个字段) ⭐核心 ===
  "position_size_pct": 23.1,                    // 建议仓位 %
  "stop_loss_price": 85429.55,                  // 止损价
  "stop_loss_pct": 8.66,                        // 止损幅度 %
  "take_profit_price": 105681.24,               // 目标价
  "take_profit_pct": 12.99,                     // 目标幅度 %
  "risk_reward_ratio": 1.5,                     // 盈亏比
  
  // === 市场背景 (4 个字段) ===
  "trend_short": "BEARISH",                     // 短期趋势
  "trend_medium": "BEARISH",                    // 中期趋势
  "volatility": "MEDIUM",                       // 波动率
  "volume_status": "NORMAL",                    // 成交量
  
  // === 策略表现 (3 个字段) ===
  "strategy_win_rate": 54.0,                    // 策略胜率 %
  "strategy_last_10": "+4.3%",                  // 近 10 笔表现
  "strategy_sharpe": 0.38,                      // 夏普比率
  
  // === 风险提示 (2 个字段) ===
  "max_risk_amount": 2000.0,                    // 最大风险金额
  "warnings": ["仓位较重"],                     // 风险警告
  
  // === 有效期 (1 个字段) ===
  "valid_until": "2024-12-30T00:00:00Z"        // 信号有效期
}
```

**总计：33 个字段**

---

## 📱 推送消息格式

### 模板

```
🟢【{strategy_name}】{symbol} {action}

📅 时间：{timestamp}
💰 价格：${current_price}
📊 方向：{direction}
🎯 类型：{signal_type}

💡 信号理由:
{reason}

📐 风险管理:
├ 仓位：{position_size_pct}%
├ 止损：${stop_loss_price} ({stop_loss_pct}%)
├ 目标：${take_profit_price} ({take_profit_pct}%)
└ 盈亏比：{risk_reward_ratio}:1

📈 信号质量:
├ 置信度：{confidence}%
├ 策略胜率：{strategy_win_rate}%
└ 夏普比率：{strategy_sharpe}

🌍 市场环境:
├ 趋势：{trend_short} / {trend_medium}
├ 波动率：{volatility}
└ 成交量：{volume_status}

⚠️ 风险：单笔最大亏损 ${max_risk_amount}
{warnings}

━━━━━━━━━━━━━━━━━━━━━━
ID: {signal_id}
有效：{valid_until}
```

### 实际示例

```
🟢【形态交易】BTC-USD BUY

📅 时间：2024-12-04 00:00
💰 价格：$98,768.53
📊 方向：LONG 📈
🎯 类型：OPEN

💡 信号理由:
图表形态突破，symmetric_triangle

📐 风险管理:
├ 仓位：24.4%
├ 止损：$90,667.86 (8.2%)
├ 目标：$110,919.54 (12.3%)
└ 盈亏比：1.5:1

📈 信号质量:
├ 置信度：65% 🟢
├ 策略胜率：58.0%
└ 夏普比率：0.80

🌍 市场环境:
├ 趋势：BEARISH / BEARISH
├ 波动率：MEDIUM
└ 成交量：NORMAL

⚠️ 风险：单笔最大亏损 $2,000
❗ 警告：仓位较重
━━━━━━━━━━━━━━━━━━━━━━
ID: SIG-20241204-BTC-PATT-000
有效：2024-12-05 00:00
```

---

## 🔧 使用方法

### 1. 生成信号

```bash
cd trading_system

# 扫描最近 30 天信号
python3 signal_generator.py --symbol BTC-USD --capital 100000

# 扫描指定天数
python3 signal_generator.py --symbol ETH-USD --capital 50000 --scan-days 7

# 只输出 JSON
python3 signal_generator.py --symbol BTC-USD --format json

# 只输出推送消息
python3 signal_generator.py --symbol BTC-USD --format message
```

### 2. 输出文件

```
signals/
├── signal_SIG-20241229-BTC-RSI-004.json    # 单个信号 JSON
├── signal_SIG-20241224-BTC-RSI-003.json
└── signals_20260308_095000.json            # 汇总文件
```

### 3. 集成到推送系统

```python
from signal_generator import SignalGenerator
from backtest.data_loader import DataLoader

# 加载数据
loader = DataLoader()
df = loader.download_yahoo('BTC-USD', '2024-01-01', '2024-12-31')

# 生成信号
generator = SignalGenerator(capital=100000)
signals = generator.scan_all_strategies(df, 'BTC-USD')

# 发送推送（以飞书为例）
for signal in signals:
    if signal.priority == 'HIGH':
        send_feishu_message(signal.to_message())
```

---

## 📏 信号生成规则

### 优先级判定

| 优先级 | 条件 |
|--------|------|
| **HIGH** | 盈亏比 ≥ 2.5 且 胜率 > 50% |
| **MEDIUM** | 盈亏比 ≥ 2.0 |
| **LOW** | 其他 |

### 置信度计算

```
置信度 = min(85, 策略胜率 + 20)  # HIGH 优先级
置信度 = min(75, 策略胜率 + 15)  # MEDIUM 优先级
置信度 = min(65, 策略胜率 + 10)  # LOW 优先级
```

### 仓位计算

```
风险金额 = 总资金 × 2%
仓位 % = 风险金额 / (价格 × 止损 %)
最大仓位 = 25%
```

### 止损/止盈

```
止损 = 入场价 ± 2 × ATR
止盈 = 入场价 ∓ 3 × ATR
盈亏比 = 止盈% / 止损%
```

---

## ⚠️ 重要说明

1. **仅供人工参考** - 不自动下单
2. **信号有效期** - 默认 24 小时
3. **风险提示** - 高波动率/重仓会触发警告
4. **历史回测** - 策略表现基于历史数据

---

## 📝 字段详解

### 核心信号字段

| 字段 | 取值 | 说明 |
|------|------|------|
| `action` | BUY/SELL/WATCH | 操作建议 |
| `direction` | LONG/SHORT/NEUTRAL | 方向 |
| `signal_type` | OPEN/CLOSE/ADD | 开仓/平仓/加仓 |
| `priority` | HIGH/MEDIUM/LOW | 优先级 |
| `confidence` | 0-100 | 置信度百分比 |

### 风险管理字段

| 字段 | 说明 | 计算方式 |
|------|------|----------|
| `position_size_pct` | 建议仓位 | 基于 2% 风险 |
| `stop_loss_price` | 止损价 | ±2×ATR |
| `take_profit_price` | 目标价 | ∓3×ATR |
| `risk_reward_ratio` | 盈亏比 | 止盈%/止损% |
| `max_risk_amount` | 最大风险 | 资金×2% |

---

## 🔄 版本历史

- **v1.0** (2024-03-08) - 初始版本
  - 33 个字段
  - JSON + 推送消息双格式
  - 9 个策略支持

---

**文档维护**: 交易信号系统
**最后更新**: 2024-03-08
