# 🪙 Crypto Scanner - 加密货币扫描器

> 基于 Python + Binance API 的加密货币策略扫描系统

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/wz-hub/crypto-scanner)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-red.svg)]()

---

## ✨ 功能特性

- **实时行情** - Binance WebSocket 实时价格推送
- **策略扫描** - 均线/RSI/MACD/布林带/资金费率
- **多交易所** - Binance（主）+ CoinGecko（备用）
- **鲸鱼监控** - 大额转账实时预警
- **套利机会** - 资金费率套利监控
- **多渠道推送** - 飞书/Telegram/Discord/邮件

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config/config.ini`:

```ini
[binance]
api_key = your_api_key
api_secret = your_secret

[notification]
feishu_webhook = https://open.feishu.cn/open-apis/bot/v2/hook/xxx
telegram_bot = your_bot_token
telegram_chat_id = your_chat_id
```

### 3. 运行

```bash
# 扫描所有主流币种
python run.py --all

# 扫描单个币种
python run.py --symbol BTC

# 监控大额转账
python run.py --whale

# 监控资金费率套利
python run.py --funding
```

---

## 📁 项目结构

```
crypto-scanner/
├── run.py                      # 主程序 ⭐
├── requirements.txt            # Python 依赖
├── README.md                   # 本文件
├── GUIDE.md                    # 使用指南
│
├── src/
│   ├── crypto_fetcher.py       # 数据获取 ⭐
│   ├── scanner.py              # 扫描引擎
│   ├── realtime_monitor.py     # 实时监控
│   ├── risk_manager.py         # 风险管理
│   └── push_multi.py           # 多渠道推送
│
├── strategies/
│   ├── btc_ma_cross.py         # BTC 均线策略
│   ├── eth_funding_rate.py     # ETH 资金费率
│   ├── whale_alert.py          # 大额转账监控
│   ├── rsi_strategy.py         # RSI 超买超卖
│   └── momentum.py             # 动量策略
│
├── config/
│   └── config.ini              # 配置文件
│
└── logs/
    └── scan.log                # 运行日志
```

---

## 📊 已实现策略

| 策略 | 币种 | 周期 | 说明 |
|------|------|------|------|
| **BTC 均线金叉** | BTC | 日线 | 5 日/20 日均线交叉 |
| **ETH 资金费率** | ETH | 实时 | 资金费率套利 |
| **RSI 超买超卖** | 所有 | 4H | RSI>70 卖出，<30 买入 |
| **大额转账监控** | 所有 | 实时 | 鲸鱼动向追踪 |
| **动量策略** | 所有 | 1H | 24h 涨幅榜追踪 |

---

## 📈 使用示例

### 扫描 BTC 机会

```bash
python run.py --symbol BTC
```

**输出：**
```
==================================================
BTC - $68,144.38
24h Change: -4.29%
24h Volume: $28,456,789,012
==================================================

📊 策略信号:
  ✅ BTC 均线策略：持有
     当前价格低于 MA5，等待金叉信号
  
  ⚠️  RSI 策略：观望
     RSI=45，中性区域
```

### 监控涨幅榜

```bash
python run.py --top-gainers
```

**输出：**
```
📈 24h 涨幅榜 Top 10:
  1. CREAM: $2.10 (+65.35%)
  2. SIGN: $0.05 (+48.03%)
  3. PNT: $0.04 (+45.23%)
  ...
```

### 监控大额转账

```bash
python run.py --whale
```

**输出：**
```
🐋 大额转账监控中...
  [15:30:45] BTC: 500 BTC ($34,072,190) 转移
  [15:32:10] ETH: 10000 ETH ($19,800,000) 转移
```

---

## 🔔 推送通知

### 配置飞书

1. 创建飞书群机器人
2. 获取 Webhook URL
3. 添加到 `config/config.ini`

```ini
[notification]
feishu_webhook = https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

### 配置 Telegram

1. @BotFather 创建 Bot
2. 获取 Token 和 Chat ID
3. 添加到配置

```ini
telegram_bot = 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
telegram_chat_id = -1001234567890
```

---

## 🛠️ 添加新策略

### 1. 创建策略文件

在 `strategies/` 目录创建 `your_strategy.py`:

```python
from src.strategy_base import BaseStrategy
import pandas as pd
from typing import Dict, Optional, Any

class YourStrategy(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "your_strategy"
    
    @property
    def description(self) -> str:
        return "策略描述"
    
    def scan(self, history: pd.DataFrame, current: Dict) -> Optional[Dict[str, Any]]:
        # 你的策略逻辑
        if 满足条件:
            return {
                'type': '买入信号',
                'signal': 'buy',
                'confidence': 75,
                'description': '信号描述'
            }
        return None

strategy = YourStrategy()
```

### 2. 在 `run.py` 中启用

```python
from strategies.your_strategy import strategy
```

---

## ⚙️ 高级配置

### 实时监控间隔

编辑 `src/realtime_monitor.py`:

```python
self.check_interval = 30  # 检查间隔（秒）
```

### 价格预警

```python
monitor.add_price_alert('BTC', 'crypto', 70000, 'above')
monitor.add_price_alert('BTC', 'crypto', 60000, 'below')
```

### 仓位管理

```python
from src.risk_manager import PositionConfig

config = PositionConfig(
    total_capital=100000,      # 总资金
    max_position_pct=0.25,     # 单标的最大 25%
    risk_per_trade=0.02,       # 单笔风险 2%
)
```

---

## 📝 风险提示

⚠️ **加密货币风险极高，请注意：**

- 市场波动大，可能瞬间爆仓
- 24/7 交易，无涨跌停限制
- 交易所风险（黑客/跑路）
- 监管政策风险
- **本工具仅供参考，不构成投资建议**

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 License

MIT License

---

## 📞 支持

- **GitHub Issues**: https://github.com/wz-hub/crypto-scanner/issues
- **Telegram 群**: [邀请链接]
- **飞书群**: [邀请链接]

---

*创建时间：2026-03-06*  
*版本：1.0.0*  
*作者：wz-hub*
