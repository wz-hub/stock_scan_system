# 交易系统重构方案

**文档版本：** 1.0  
**创建时间：** 2026-03-09  
**状态：** 待审核

---

## 📊 一、现状分析

### 1.1 当前文件结构

```
trading_system/
├── 核心功能
│   ├── signal_generator.py        # 信号生成（32KB）
│   ├── scan_half_hourly_v3.py     # 扫描脚本（当前使用）
│   ├── signal_tracker.py          # 信号追踪（新增）
│   ├── signal_monitor.py          # 价格监控（新增）
│   ├── signal_report.py           # 统计报表（新增）
│   └── feishu_notifier.py         # 飞书推送
│
├── 策略模块
│   ├── strategies/
│   │   ├── multi_timeframe.py     # 多周期共振
│   │   ├── volatility_squeeze.py  # 波动率收缩
│   │   ├── money_flow.py          # 资金流追踪
│   │   └── liquidity_hunt.py      # 流动性猎杀
│   └── ...
│
├── 数据模块
│   ├── realtime_data.py           # 实时数据
│   ├── database.py                # 数据库（K 线缓存）
│   └── money_flow.py              # 资金流监控
│
├── 缓存与数据库
│   ├── cache/
│   │   ├── signals.db             # 信号数据库
│   │   ├── market_data.db         # K 线缓存
│   │   └── klines_cache.json      # K 线 JSON 缓存
│   └── signals/                   # 信号 JSON 文件
│
├── 配置文件
│   └── config/
│       ├── notification.json      # 通知配置
│       └── ai_config.json         # AI 配置
│
├── Web 界面
│   ├── web_app_v11.py             # 当前使用
│   ├── web_app_v10.py
│   ├── web_app_v9.py
│   └── ... (v2-v8 共 9 个旧版本)
│
├── 扫描脚本（历史版本）
│   ├── scan_half_hourly_v3.py     # 当前使用
│   ├── scan_half_hourly_v2.py
│   ├── scan_half_hourly.py
│   └── scan_all_symbols.py
│
├── 回测模块
│   ├── backtest/
│   ├── backtest_new_strategies.py
│   └── run_backtest.py
│
├── 测试文件
│   ├── test_ai.py
│   ├── test_boss_api.py
│   ├── test_feishu.py
│   └── debug_ai.py
│
└── 其他工具
    ├── ai_scorer.py
    ├── technical_analyzer.py
    ├── get_top_symbols.py
    └── ...
```

---

### 1.2 问题分析

#### 1.2.1 文件冗余
- ❌ **9 个 web_app 版本**（v2-v11），只使用 v11
- ❌ **3 个 scan 版本**，只使用 v3
- ❌ **多个测试文件**，分散各处
- ❌ **回测代码**与生产代码混在一起

#### 1.2.2 代码耦合
- ⚠️ **signal_generator.py** 32KB，功能过多
- ⚠️ **scan_half_hourly_v3.py** 包含扫描、推送、追踪
- ⚠️ **策略模块**与扫描逻辑耦合

#### 1.2.3 配置分散
- ⚠️ **notification.json** - 通知配置
- ⚠️ **ai_config.json** - AI 配置
- ⚠️ **scan_config.json** - 扫描配置
- ❌ 缺少统一配置管理

#### 1.2.4 数据库混乱
- ❌ **signals.db** - 信号数据
- ❌ **market_data.db** - K 线缓存
- ❌ **klines_cache.json** - K 线 JSON（重复）
- ❌ 缺少数据库管理工具

---

## 🎯 二、重构目标

### 2.1 核心原则

1. **单一职责** - 每个模块只做一件事
2. **低耦合** - 模块间通过接口通信
3. **可配置** - 所有配置集中管理
4. **可测试** - 每个模块可独立测试
5. **易扩展** - 新增策略/功能不影响现有代码

### 2.2 预期效果

| 指标 | 当前 | 重构后 |
|------|------|--------|
| **核心文件数** | 40+ | ~15 |
| **最大文件大小** | 32KB | <10KB |
| **配置文件** | 3 个 | 1 个 |
| **数据库** | 3 个 | 1 个 |
| **代码重复** | 高 | 低 |
| **可维护性** | 中 | 高 |

---

## 🏗️ 三、新架构设计

### 3.1 目录结构

```
trading_system/
│
├── core/                        # 核心模块
│   ├── __init__.py
│   ├── scanner.py               # 扫描引擎
│   ├── tracker.py               # 追踪引擎
│   ├── monitor.py               # 监控引擎
│   └── reporter.py              # 报表引擎
│
├── strategies/                  # 策略模块
│   ├── __init__.py
│   ├── base.py                  # 策略基类
│   ├── multi_timeframe.py       # 多周期
│   ├── volatility_squeeze.py    # 波动率
│   ├── money_flow.py            # 资金流
│   └── liquidity_hunt.py        # 流动性
│
├── data/                        # 数据模块
│   ├── __init__.py
│   ├── binance.py               # Binance API
│   ├── cache.py                 # 缓存管理
│   └── database.py              # 数据库管理
│
├── notification/                # 通知模块
│   ├── __init__.py
│   ├── feishu.py                # 飞书推送
│   └── templates.py             # 消息模板
│
├── config/                      # 配置模块
│   ├── __init__.py
│   ├── settings.py              # 配置管理
│   └── default.yaml             # 默认配置
│
├── web/                         # Web 界面
│   ├── __init__.py
│   ├── app.py                   # Streamlit 应用
│   └── components/              # UI 组件
│
├── scripts/                     # 脚本入口
│   ├── scan.py                  # 扫描脚本
│   ├── monitor.py               # 监控脚本
│   └── report.py                # 报表脚本
│
├── tests/                       # 测试目录
│   ├── test_scanner.py
│   ├── test_tracker.py
│   └── test_strategies.py
│
├── cache/                       # 缓存目录
│   ├── signals.db
│   └── klines.db
│
├── config.yaml                  # 统一配置文件
├── requirements.txt             # 依赖
└── README.md                    # 文档
```

---

### 3.2 模块职责

#### 3.2.1 core/ - 核心引擎

```python
# scanner.py - 扫描引擎
class Scanner:
    def scan_all_symbols() -> List[Signal]
    def filter_signals(signals, min_confidence) -> List[Signal]
    def deduplicate_signals(signals) -> List[Signal]

# tracker.py - 追踪引擎
class Tracker:
    def add_signal(signal) -> bool
    def get_active_signals() -> List[Signal]
    def has_active_signal(symbol, strategy) -> bool
    def update_prices()
    def check_exit_conditions() -> List[Signal]

# monitor.py - 监控引擎
class Monitor:
    def start()
    def stop()
    def update_interval(minutes)

# reporter.py - 报表引擎
class Reporter:
    def generate_daily_report() -> str
    def generate_weekly_report() -> str
    def send_report(report)
```

#### 3.2.2 strategies/ - 策略模块

```python
# base.py - 策略基类
class BaseStrategy:
    def generate_signal(data) -> Optional[Signal]
    def get_name() -> str
    def get_confidence() -> float

# 所有策略继承 BaseStrategy
class MultiTimeframeStrategy(BaseStrategy):
    def generate_signal(self, data):
        # 实现
```

**优点：**
- 统一接口
- 易于新增策略
- 可独立测试

#### 3.2.3 data/ - 数据模块

```python
# binance.py - Binance API
class BinanceClient:
    def get_klines(symbol, interval, limit) -> DataFrame
    def get_ticker(symbol) -> dict
    def get_volume_ranking(limit) -> List[str]

# cache.py - 缓存管理
class CacheManager:
    def get_klines(symbol, interval) -> DataFrame
    def set_klines(symbol, interval, data)
    def is_fresh(symbol, interval, max_age) -> bool

# database.py - 数据库管理
class DatabaseManager:
    def init_database()
    def save_signal(signal)
    def update_signal_status(signal_id, status)
    def cleanup_old_data(days)
```

#### 3.2.4 notification/ - 通知模块

```python
# feishu.py - 飞书推送
class FeishuNotifier:
    def send_text(message) -> bool
    def send_card(card_data) -> bool

# templates.py - 消息模板
class MessageTemplates:
    def new_signal_template(signal) -> str
    def exit_signal_template(signal, reason) -> str
    def daily_report_template(stats) -> str
```

#### 3.2.5 config/ - 配置模块

```python
# settings.py - 配置管理
class Settings:
    def __init__(self, config_file='config.yaml')
    def get(key, default=None)
    def reload()
    
# 使用示例
settings = Settings()
min_confidence = settings.get('scanner.min_confidence', 80)
webhook = settings.get('notification.feishu.webhook')
```

**config.yaml 示例：**
```yaml
scanner:
  enabled: true
  interval_minutes: 30
  min_confidence: 80
  symbols:
    volume_top_n: 100
    money_flow_top: 20

tracker:
  enabled: true
  update_interval_minutes: 5
  auto_close: true
  notify_on_exit: true

notification:
  feishu:
    enabled: true
    webhook: "https://..."
  daily_report:
    enabled: true
    time: "20:00"

database:
  path: "cache/signals.db"
  cleanup_days: 90
```

---

### 3.3 数据流

```
定时任务 (cron)
    ↓
scripts/scan.py
    ↓
core/scanner.scan_all_symbols()
    ↓
data/binance.get_klines() → data/cache (缓存)
    ↓
strategies/*.generate_signal() → List[Signal]
    ↓
core/scanner.filter_signals() → 过滤低置信度
    ↓
core/tracker.has_active_signal() → 检查重复
    ↓
notification/feishu.send_text() → 推送
    ↓
core/tracker.add_signal() → 数据库
```

**监控流程：**
```
定时任务 (每 5 分钟)
    ↓
scripts/monitor.py
    ↓
core/monitor.start()
    ↓
core/tracker.get_active_signals()
    ↓
data/binance.get_ticker() → 获取最新价格
    ↓
core/tracker.update_prices() → 更新盈亏
    ↓
core/tracker.check_exit_conditions() → 检查止盈止损
    ↓
[如果触发平仓]
    ↓
core/tracker.close_signal() → 更新状态
    ↓
notification/feishu.send_text() → 推送平仓通知
```

---

## 📝 四、实施计划

### 4.1 阶段划分

| 阶段 | 内容 | 预计时间 | 风险 |
|------|------|----------|------|
| **Phase 0** | 准备工作 | 30 分钟 | 低 |
| **Phase 1** | 核心模块重构 | 2 小时 | 中 |
| **Phase 2** | 策略模块重构 | 1 小时 | 低 |
| **Phase 3** | 数据模块重构 | 1 小时 | 低 |
| **Phase 4** | 通知模块重构 | 30 分钟 | 低 |
| **Phase 5** | 配置统一管理 | 30 分钟 | 低 |
| **Phase 6** | 测试验证 | 1 小时 | 中 |
| **Phase 7** | 清理旧文件 | 30 分钟 | 低 |

**总计：** 约 7 小时

---

### 4.2 Phase 0: 准备工作

1. **创建新目录结构**
   ```bash
   mkdir -p core strategies data notification config web scripts tests
   ```

2. **备份当前代码**
   ```bash
   git checkout -b backup-before-refactor
   git push origin backup-before-refactor
   ```

3. **创建 requirements.txt**
   ```
   pandas>=2.0
   numpy>=1.24
   sqlite3
   requests
   pyyaml
   streamlit
   ```

---

### 4.3 Phase 1: 核心模块重构

**任务：**
1. 创建 `core/__init__.py`
2. 提取 `scanner.py`（从 scan_half_hourly_v3.py）
3. 提取 `tracker.py`（从 signal_tracker.py）
4. 创建 `monitor.py`
5. 创建 `reporter.py`

**验收标准：**
- [ ] 每个文件 < 300 行
- [ ] 有完整的 docstring
- [ ] 可独立 import 测试

---

### 4.4 Phase 2: 策略模块重构

**任务：**
1. 创建 `strategies/base.py`（策略基类）
2. 迁移现有 4 个策略
3. 更新 `strategies/__init__.py`

**验收标准：**
- [ ] 所有策略继承 BaseStrategy
- [ ] 统一接口 generate_signal()
- [ ] 可独立测试每个策略

---

### 4.5 Phase 3: 数据模块重构

**任务：**
1. 创建 `data/binance.py`（Binance API）
2. 创建 `data/cache.py`（缓存管理）
3. 创建 `data/database.py`（数据库管理）
4. 合并 signals.db 和 market_data.db

**验收标准：**
- [ ] 统一的数据库接口
- [ ] 缓存命中可配置
- [ ] 自动清理旧数据

---

### 4.6 Phase 4: 通知模块重构

**任务：**
1. 创建 `notification/feishu.py`
2. 创建 `notification/templates.py`
3. 统一消息模板

**验收标准：**
- [ ] 所有推送使用 templates
- [ ] 模板可配置
- [ ] 支持多种通知渠道（预留）

---

### 4.7 Phase 5: 配置统一管理

**任务：**
1. 创建 `config.yaml`（统一配置）
2. 创建 `config/settings.py`（配置管理）
3. 迁移所有配置项

**验收标准：**
- [ ] 所有配置在一个文件
- [ ] 有默认值
- [ ] 支持环境变量覆盖

---

### 4.8 Phase 6: 测试验证

**任务：**
1. 创建测试框架
2. 编写核心模块测试
3. 编写策略模块测试
4. 端到端测试

**验收标准：**
- [ ] 所有核心功能有测试
- [ ] 测试通过率 100%
- [ ] 扫描、追踪、推送正常工作

---

### 4.9 Phase 7: 清理旧文件

**任务：**
1. 删除旧版本文件（web_app_v2-v10, scan_v1-v2 等）
2. 删除测试文件
3. 删除回测模块（或移至独立目录）
4. 更新 README

**验收标准：**
- [ ] 只保留必要的文件
- [ ] 目录结构清晰
- [ ] README 完整

---

## ⚠️ 五、风险评估

### 5.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 重构引入 bug | 中 | 高 | 完整测试 + 备份 |
| 数据丢失 | 低 | 高 | 数据库备份 + 迁移脚本 |
| 推送中断 | 中 | 中 | 渐进式切换 |
| 配置错误 | 低 | 中 | 配置验证 + 默认值 |

### 5.2 缓解策略

1. **分支开发**
   ```bash
   git checkout -b refactor
   # 在 refactor 分支开发
   # 测试通过后再合并到 master
   ```

2. **渐进式切换**
   - 先重构核心模块
   - 保持旧扫描脚本可用
   - 逐个模块切换

3. **完整测试**
   - 单元测试
   - 集成测试
   - 端到端测试

4. **回滚方案**
   ```bash
   # 如果出现问题
   git checkout master
   # 恢复到重构前版本
   ```

---

## 📊 六、重构前后对比

### 6.1 代码质量

| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| 最大文件 | 32KB | <10KB | -69% |
| 平均文件 | 8KB | 3KB | -62% |
| 代码重复 | 高 | 低 | -80% |
| 耦合度 | 高 | 低 | -70% |

### 6.2 可维护性

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| 新增策略 | 修改多处 | 实现接口 |
| 修改配置 | 编辑多文件 | 编辑 config.yaml |
| 定位问题 | 困难 | 容易 |
| 测试覆盖 | 0% | 80%+ |

### 6.3 性能

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| 扫描时间 | 45 秒 | 45 秒（不变） |
| 内存占用 | 中 | 低 |
| 数据库查询 | 慢 | 快（索引优化） |

---

## ✅ 七、验收标准

### 7.1 功能验收

- [ ] 信号扫描正常（每 30 分钟）
- [ ] 信号去重生效（平仓前不重复）
- [ ] 价格监控正常（每 5 分钟）
- [ ] 止盈止损检测正常
- [ ] 平仓推送正常
- [ ] 日报/周报正常
- [ ] Web 界面正常

### 7.2 代码验收

- [ ] 所有文件 < 300 行
- [ ] 有完整的 docstring
- [ ] 有类型注解
- [ ] 通过 flake8 检查
- [ ] 测试覆盖率 > 80%

### 7.3 文档验收

- [ ] README 完整
- [ ] 配置说明完整
- [ ] API 文档完整
- [ ] 部署文档完整

---

## 📋 八、决策点

**需要 boss 确认的事项：**

1. **是否保留回测模块？**
   - 方案 A：移至独立目录 `backtest/`
   - 方案 B：删除（需要时从 git 恢复）
   - **建议：方案 A**

2. **是否保留旧 Web 界面？**
   - 方案 A：只保留 web_app_v11.py
   - 方案 B：全部删除，用新 web/
   - **建议：方案 B**

3. **数据库合并？**
   - 方案 A：signals.db + market_data.db → trading.db
   - 方案 B：保持独立
   - **建议：方案 A**

4. **配置文件格式？**
   - 方案 A：YAML（推荐）
   - 方案 B：JSON
   - 方案 C：Python 模块
   - **建议：方案 A**

5. **重构时间？**
   - 方案 A：今晚完成（7 小时）
   - 方案 B：分 2-3 天完成
   - **建议：方案 B（更稳妥）**

---

## 🎯 九、建议

**我的建议：**

1. **先测试验证现有功能** - 确保去重、追踪都正常
2. **分阶段重构** - 不要一次性完成，降低风险
3. **保留备份** - 重构前备份，随时可回滚
4. **完整测试** - 每个阶段都要测试
5. **文档先行** - 先写文档，再写代码

**推荐时间表：**
```
今晚（3 月 9 日）:
- ✅ 验证现有功能（已完成）
- ✅ 出重构方案（进行中）
- ⏳ boss 审核方案

明天（3 月 10 日）:
- Phase 0-2: 核心 + 策略模块
- 测试验证

后天（3 月 11 日）:
- Phase 3-7: 数据 + 通知 + 配置 + 清理
- 完整测试
- 上线
```

---

**文档结束**

_等待 boss 审核..._
