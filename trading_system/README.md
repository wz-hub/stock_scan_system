# 交易系统 v2.0

重构后的模块化交易系统，采用清晰的业务分层架构。

## 📁 目录结构

```
trading_system/
├── business/                 # 业务逻辑层
│   ├── signal/              # 信号生成业务
│   ├── scan/                # 扫描业务
│   └── trade/               # 交易业务
├── core/                     # 核心引擎层
│   ├── scanner.py           # 扫描器
│   ├── monitor.py           # 监控器
│   ├── reporter.py          # 报告器
│   └── tracker.py           # 追踪器
├── data/                     # 数据访问层
│   ├── database.py          # 数据库操作
│   ├── cache.py             # 缓存管理
│   └── binance.py           # 币安数据源
├── strategies/               # 策略模块
│   ├── base.py              # 策略基类
│   ├── money_flow.py        # 资金流策略
│   ├── liquidity_hunt.py    # 流动性猎杀策略
│   └── ...
├── notification/             # 通知模块
│   ├── feishu.py            # 飞书通知
│   └── templates.py         # 通知模板
├── scripts/                  # 工具脚本
│   ├── realtime_data.py     # 实时数据
│   ├── visual_report.py     # 可视化报告
│   └── industry_compare.py  # 行业对比
├── tests/                    # 测试目录
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   └── test_*.py            # 测试文件
├── config/                   # 配置目录
│   └── config.yaml          # 主配置文件
├── cache/                    # 缓存目录
├── signals/                  # 信号输出目录
├── results/                  # 回测结果目录
├── web_app.py               # Web 应用 (v11 是当前版本)
├── web_app_v11.py           # Web 应用 v11
├── scan_half_hourly_v3.py   # 半小时扫描 v3
├── signal_generator.py      # 信号生成器
├── signal_tracker.py        # 信号追踪器
├── database.py              # 数据库 (兼容层)
└── README.md
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd trading_system
pip install -r requirements.txt
```

### 2. 配置系统

编辑 `config/config.yaml` 配置你的 API 密钥和参数。

### 3. 运行扫描

```bash
# 半小时扫描
python scan_half_hourly_v3.py

# 实时数据监控
python scripts/realtime_data.py
```

### 4. 启动 Web 界面

```bash
python web_app.py
# 或
python web_app_v11.py
```

访问 http://localhost:5000

## 📊 核心模块

### 业务层 (business/)
- 信号生成、扫描、交易的业务逻辑
- 与具体技术实现解耦

### 核心层 (core/)
- Scanner: 扫描引擎
- Monitor: 实时监控
- Reporter: 报告生成
- Tracker: 信号追踪

### 数据层 (data/)
- 统一的数据库访问
- 缓存管理
- 多数据源支持

### 策略层 (strategies/)
- 所有交易策略实现
- 统一的策略接口

## 🧪 测试

```bash
# 运行所有测试
cd tests
pytest

# 运行特定测试
pytest test_strategies.py
pytest test_database.py
```

## 📝 配置文件

`config/config.yaml` 是主配置文件，包含：
- API 密钥配置
- 扫描参数
- 通知设置
- 数据库配置

## ⚠️ 注意事项

- 旧版本文件已清理 (web_app_v2-v10, 旧测试文件等)
- 回测模块已迁移到独立项目
- 配置已统一迁移到 config.yaml
- tests/ 目录包含所有测试文件

## 📈 支持的策略

1. **资金流策略** - 主力资金流向分析
2. **流动性猎杀** - 识别流动性猎杀形态
3. **多时间框架** - 多周期共振分析
4. **波动率挤压** - 波动率突破策略
5. **配对交易** - 统计套利

## 🔧 开发

```bash
# 添加新策略
# 1. 在 strategies/ 创建新策略类
# 2. 继承 base.py 的 Strategy 基类
# 3. 实现 generate_signals() 方法

# 运行测试
pytest tests/ -v
```

## 📚 文档

- [重构计划](REFACTOR_PLAN.md)
- [重构进度](REFACTOR_PROGRESS.json)
- [策略说明](STRATEGY_SUMMARY.md)
- [信号格式](SIGNAL_FORMAT.md)
