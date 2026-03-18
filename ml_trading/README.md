# 🤖 ML Trading - 机器学习交易系统

基于 XGBoost 的加密货币价格预测系统

## 项目结构

```
ml_trading/
├── ml/
│   ├── features.py      # 特征工程（50+ 特征）
│   ├── train.py         # 模型训练
│   ├── predict.py       # 实时预测
│   └── models/          # 保存的模型
├── data/                # 数据缓存
├── backtest/            # 回测结果
├── logs/                # 日志
└── README.md
```

## 核心思路

**输入：** 历史 K 线数据（OHLCV）
**特征：** 50+ 个技术指标 + 价量特征 + 市场结构
**输出：** 预测未来 4H 涨跌概率

## 使用现有数据

数据源：`../trading_system/cache/trading.db`
- 10 万 + 条 K 线
- 365 天历史
- 100+ 币种

## 预期效果

| 指标 | 目标 |
|------|------|
| 回测准确率 | 55-60% |
| 实盘准确率 | 50-55% |
| 盈亏比 | 1.5-2.0 |
| 信号频率 | 每天数个 |

## 快速开始

```bash
# 1. 安装依赖
pip install xgboost scikit-learn joblib pandas numpy

# 2. 训练模型
python ml/train.py --symbol BTCUSDT

# 3. 回测验证
python backtest/run_backtest.py

# 4. 实时预测
python ml/predict.py --symbol BTCUSDT
```

## 特征列表（50+）

### 技术指标
- RSI(14)
- MACD(12,26,9)
- 布林带宽
- ATR(14)
- CCI(20)
- ...

### 价量特征
- 1H/4H/12H/24H 收益率
- 成交量比率
- 波动率比率
- ...

### 市场结构
- 距离 24H 高点 %
- 距离 24H 低点 %
- 支撑阻力位置
- ...

### 时间特征
- 小时
- 星期几
- 月份
- ...

---

**🚀 边做边学，实战驱动**
