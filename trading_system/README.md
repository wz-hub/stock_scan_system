# 交易策略回测系统

## 📦 安装

```bash
pip install pandas numpy yfinance scipy
```

## 🚀 快速开始

### 1. 使用模拟数据测试

```bash
cd trading_system
python run_backtest.py --synthetic
```

### 2. 下载真实数据回测

```bash
# 比特币
python run_backtest.py --symbol BTC-USD --start 2020-01-01 --end 2024-12-31

# 股票
python run_backtest.py --symbol AAPL --start 2020-01-01 --end 2024-12-31

# 以太坊
python run_backtest.py --symbol ETH-USD --start 2020-01-01 --end 2024-12-31
```

### 3. 使用本地 CSV 数据

```bash
python run_backtest.py --data data/btc.csv
```

## 📊 支持的策略

1. **趋势跟踪 (海龟)** - Donchian 通道突破
2. **123/2B 反转** - 趋势反转形态
3. **支撑阻力** - 关键价位交易
4. **形态交易** - 头肩顶/双顶等
5. **均线交叉** - EMA 金叉死叉
6. **波动率突破** - ATR/布林带突破
7. **布林带** - 均值回归/突破
8. **RSI** - 超买超卖/背离
9. **突破策略** - N 日高低点突破

## 📁 目录结构

```
trading_system/
├── backtest/
│   ├── engine.py          # 回测引擎
│   └── data_loader.py     # 数据加载
├── strategies/
│   ├── trend_following.py
│   ├── reversal_123.py
│   ├── support_resistance.py
│   ├── pattern_trading.py
│   ├── ma_cross.py
│   ├── volatility_breakout.py
│   ├── pairs_trading.py
│   ├── bollinger_bands.py
│   ├── rsi_strategy.py
│   └── breakout_strategy.py
├── data/                   # 数据存储
├── results/                # 回测结果
├── run_backtest.py        # 主脚本
└── README.md
```

## 📈 输出指标

- 总收益 (Total Return)
- 胜率 (Win Rate)
- 盈亏比 (Profit Factor)
- 最大回撤 (Max Drawdown)
- 夏普比率 (Sharpe Ratio)
- 交易次数 (Total Trades)

## ⚠️ 风险提示

- 历史回测不代表未来表现
- 未考虑滑点和手续费的精确影响
- 仅供学习研究，不构成投资建议
