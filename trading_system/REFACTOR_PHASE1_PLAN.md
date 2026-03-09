# 重构执行计划 - Phase 1

**阶段：** Phase 1 - 基础重构  
**时间：** 2026-03-10 至 2026-03-16（7 天）  
**目标：** 核心模块重构，保持功能完全一致  
**测试覆盖率：** 100%

---

## ⚠️ 核心原则

### 1. 功能一致性
```
✅ 保留所有现有功能
✅ 不删除任何功能
✅ 不修改业务逻辑
✅ 只重构代码结构，不改行为
```

### 2. 测试先行
```
✅ 重构前先写测试
✅ 测试覆盖率 100%
✅ 测试通过才重构
✅ 重构后测试必须通过
```

### 3. 渐进式重构
```
✅ 一次重构一个模块
✅ 重构完立即测试
✅ 测试通过立即提交
✅ 随时可回滚
```

### 4. 不影响现有功能
```
✅ 重构在 refactor 分支
✅ master 分支保持正常运行
✅ 每天同步 master 到 refactor
✅ 重构完成前不影响生产
```

---

## 📊 现有功能清单（必须全部保留）

### 功能 1：信号扫描
```
功能描述：每 30 分钟扫描全市场，生成交易信号

输入：
- Binance API 数据（109 个币种）
- 4 个策略（多周期/波动率收缩/资金流/流动性猎杀）

处理：
1. 获取成交量 Top100
2. 获取资金流 Top20
3. 4 个策略生成信号
4. 置信度过滤（>=80%）
5. 去重检查（活跃信号不重复）

输出：
- 推送新信号到飞书
- 记录信号到数据库

现有文件：
- scan_half_hourly_v3.py
- signal_generator.py
- strategies/*.py

验收标准：
- 每 30 分钟执行一次
- 扫描 109 个币种
- 4 个策略正常工作
- 置信度>=80% 才推送
- 同币种同策略平仓前不重复
```

### 功能 2：信号追踪
```
功能描述：记录所有推送信号，追踪表现

输入：
- 新信号（来自扫描）

处理：
1. 记录信号到数据库
2. 检查是否有活跃信号
3. 更新信号状态

输出：
- signals.db 数据库记录

现有文件：
- signal_tracker.py

验收标准：
- 每个信号都记录
- 状态正确（ACTIVE/CLOSED）
- 可查询活跃信号
- 可查询历史信号
```

### 功能 3：价格监控
```
功能描述：每 5 分钟更新活跃信号价格，检查止盈止损

输入：
- 活跃信号列表（来自 database）
- Binance 实时价格

处理：
1. 获取所有活跃信号
2. 获取最新价格
3. 计算盈亏
4. 检查止盈止损
5. 触发平仓

输出：
- 更新数据库
- 推送平仓通知（如触发）

现有文件：
- signal_monitor.py

验收标准：
- 每 5 分钟执行一次
- 价格更新准确
- 止盈止损检测正确
- 平仓通知推送正常
```

### 功能 4：统计报表
```
功能描述：每天 20:00 生成统计报表

输入：
- 信号数据库

处理：
1. 获取统计数据
2. 生成日报/周报
3. 推送到飞书

输出：
- 日报（每天）
- 周报（每周一）

现有文件：
- signal_report.py

验收标准：
- 每天 20:00 执行
- 统计数据准确
- 推送正常
```

### 功能 5：飞书推送
```
功能描述：推送各种通知到飞书

输入：
- 消息内容

处理：
1. 格式化消息
2. 调用飞书 API

输出：
- 飞书消息

现有文件：
- feishu_notifier.py

验收标准：
- 新信号推送正常
- 平仓通知推送正常
- 报表推送正常
- 消息格式正确
```

### 功能 6：数据缓存
```
功能描述：缓存 K 线数据，减少 API 调用

输入：
- Binance API 数据

处理：
1. 保存到数据库/文件
2. 检查缓存新鲜度
3. 返回缓存数据

输出：
- K 线数据

现有文件：
- database.py
- realtime_data.py

验收标准：
- 缓存命中正确
- 缓存过期处理正确
- 数据准确
```

---

## 📝 Phase 1 详细任务分解

### Day 1: 准备工作（2026-03-10）

**任务 1.1：创建分支和备份**
```bash
# 创建重构分支
git checkout master
git pull
git checkout -b refactor

# 创建备份分支
git checkout -b backup-20260310
git push origin backup-20260310

# 切换回重构分支
git checkout refactor
```

**验收：**
- [ ] refactor 分支创建
- [ ] backup-20260310 分支创建并推送
- [ ] 当前在 refactor 分支

**任务 1.2：创建新目录结构**
```bash
mkdir -p business/signal
mkdir -p business/strategy
mkdir -p business/notification
mkdir -p data/sources
mkdir -p data/repositories
mkdir -p infrastructure
mkdir -p interfaces/web
mkdir -p scripts
mkdir -p tests/unit
mkdir -p tests/integration
```

**验收：**
- [ ] 所有目录创建成功
- [ ] 每个目录有.gitkeep 文件

**任务 1.3：创建测试框架**
```python
# tests/conftest.py - pytest 配置
# tests/unit/test_scanner.py - 扫描测试
# tests/unit/test_tracker.py - 追踪测试
```

**验收：**
- [ ] pytest 可以运行
- [ ] 有基础测试框架

**任务 1.4：提交 Day 1 工作**
```bash
git add -A
git commit -m "Phase 1 Day 1: 准备工作"
git push origin refactor
```

**验收：**
- [ ] 代码已提交
- [ ] 代码已推送

---

### Day 2: 信号模块重构（2026-03-11）

**任务 2.1：编写信号模块测试**
```python
# tests/unit/test_signal.py
def test_signal_creation():
    """测试信号创建"""
    pass

def test_signal_validation():
    """测试信号验证"""
    pass

def test_signal_deduplication():
    """测试信号去重"""
    pass
```

**验收：**
- [ ] 测试用例编写完成
- [ ] 测试覆盖所有信号功能

**任务 2.2：创建 business/signal/generator.py**
```python
# 从 scan_half_hourly_v3.py 提取扫描逻辑
class SignalGenerator:
    def scan_all_symbols() -> List[Signal]
    def filter_signals(signals, min_confidence) -> List[Signal]
    def deduplicate_signals(signals, active_signals) -> List[Signal]
```

**验收：**
- [ ] 代码重构完成
- [ ] 所有测试通过
- [ ] 功能与原代码一致

**任务 2.3：创建 business/signal/tracker.py**
```python
# 从 signal_tracker.py 重构
class SignalTracker:
    def add_signal(signal) -> bool
    def get_active_signals() -> List[Signal]
    def has_active_signal(symbol, strategy) -> bool
```

**验收：**
- [ ] 代码重构完成
- [ ] 所有测试通过
- [ ] 功能与原代码一致

**任务 2.4：提交 Day 2 工作**
```bash
git add -A
git commit -m "Phase 1 Day 2: 信号模块重构"
git push origin refactor
```

**验收：**
- [ ] 代码已提交
- [ ] 代码已推送
- [ ] 测试通过率 100%

---

### Day 3: 策略模块重构（2026-03-12）

**任务 3.1：编写策略模块测试**
```python
# tests/unit/test_strategies.py
def test_multi_timeframe_strategy():
    """测试多周期策略"""
    pass

def test_volatility_squeeze_strategy():
    """测试波动率收缩策略"""
    pass

def test_money_flow_strategy():
    """测试资金流策略"""
    pass

def test_liquidity_hunt_strategy():
    """测试流动性猎杀策略"""
    pass
```

**验收：**
- [ ] 测试用例编写完成
- [ ] 测试覆盖所有策略

**任务 3.2：创建 business/strategy/base.py**
```python
# 策略基类
class BaseStrategy:
    def generate_signal(data) -> Optional[Signal]
    def get_name() -> str
    def get_min_confidence() -> int
```

**验收：**
- [ ] 基类定义完成
- [ ] 接口定义清晰

**任务 3.3：迁移现有策略**
```python
# business/strategy/multi_timeframe.py
# business/strategy/volatility_squeeze.py
# business/strategy/money_flow.py
# business/strategy/liquidity_hunt.py
```

**验收：**
- [ ] 4 个策略全部迁移
- [ ] 所有策略继承 BaseStrategy
- [ ] 所有测试通过

**任务 3.4：提交 Day 3 工作**
```bash
git add -A
git commit -m "Phase 1 Day 3: 策略模块重构"
git push origin refactor
```

**验收：**
- [ ] 代码已提交
- [ ] 代码已推送
- [ ] 测试通过率 100%

---

### Day 4: 数据模块重构（2026-03-13）

**任务 4.1：编写数据模块测试**
```python
# tests/unit/test_data.py
def test_binance_client():
    """测试 Binance API 客户端"""
    pass

def test_cache_manager():
    """测试缓存管理"""
    pass

def test_database_manager():
    """测试数据库管理"""
    pass
```

**验收：**
- [ ] 测试用例编写完成
- [ ] 测试覆盖所有数据功能

**任务 4.2：创建 data/sources/binance.py**
```python
# 从 realtime_data.py 重构
class BinanceClient:
    def get_klines(symbol, interval, limit) -> DataFrame
    def get_ticker(symbol) -> dict
    def get_volume_ranking(limit) -> List[str]
```

**验收：**
- [ ] 代码重构完成
- [ ] 所有测试通过
- [ ] API 调用正常

**任务 4.3：创建 data/repositories/signal_repo.py**
```python
# 从 signal_tracker.py 提取数据库操作
class SignalRepository:
    def save(signal) -> bool
    def find_active() -> List[Signal]
    def update_status(signal_id, status)
```

**验收：**
- [ ] 代码重构完成
- [ ] 所有测试通过
- [ ] 数据库操作正常

**任务 4.4：合并数据库**
```python
# 将 signals.db 和 market_data.db 合并为 trading.db
# 创建 data/database.py 统一管理
```

**验收：**
- [ ] 数据库合并完成
- [ ] 数据迁移成功
- [ ] 所有功能正常

**任务 4.5：提交 Day 4 工作**
```bash
git add -A
git commit -m "Phase 1 Day 4: 数据模块重构"
git push origin refactor
```

**验收：**
- [ ] 代码已提交
- [ ] 代码已推送
- [ ] 测试通过率 100%

---

### Day 5: 通知模块重构（2026-03-14）

**任务 5.1：编写通知模块测试**
```python
# tests/unit/test_notification.py
def test_feishu_sender():
    """测试飞书推送"""
    pass

def test_message_templates():
    """测试消息模板"""
    pass
```

**验收：**
- [ ] 测试用例编写完成

**任务 5.2：创建 business/notification/sender.py**
```python
# 从 feishu_notifier.py 重构
class NotificationSender:
    def send_new_signal(signal) -> bool
    def send_exit_signal(signal, reason) -> bool
    def send_report(report) -> bool
```

**验收：**
- [ ] 代码重构完成
- [ ] 所有测试通过

**任务 5.3：创建 business/notification/templates.py**
```python
# 统一消息模板
class MessageTemplates:
    def new_signal_template(signal) -> str
    def exit_signal_template(signal, reason) -> str
    def daily_report_template(stats) -> str
```

**验收：**
- [ ] 模板定义完成
- [ ] 所有模板测试通过

**任务 5.4：提交 Day 5 工作**
```bash
git add -A
git commit -m "Phase 1 Day 5: 通知模块重构"
git push origin refactor
```

**验收：**
- [ ] 代码已提交
- [ ] 代码已推送
- [ ] 测试通过率 100%

---

### Day 6: 配置统一管理（2026-03-15）

**任务 6.1：创建 config.yaml**
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
  path: "cache/trading.db"
  cleanup_days: 90
```

**验收：**
- [ ] 所有配置项迁移到 config.yaml

**任务 6.2：创建 infrastructure/config.py**
```python
# 配置管理
class Config:
    def __init__(self, config_file='config.yaml')
    def get(key, default=None)
    def reload()
```

**验收：**
- [ ] 配置管理完成
- [ ] 所有配置可正确读取

**任务 6.3：迁移所有配置读取**
```python
# 所有模块使用 Config 读取配置
# 不再直接读取 JSON 文件
```

**验收：**
- [ ] 所有模块配置读取完成
- [ ] 测试通过

**任务 6.4：提交 Day 6 工作**
```bash
git add -A
git commit -m "Phase 1 Day 6: 配置统一管理"
git push origin refactor
```

**验收：**
- [ ] 代码已提交
- [ ] 代码已推送
- [ ] 测试通过率 100%

---

### Day 7: 集成测试与验收（2026-03-16）

**任务 7.1：编写集成测试**
```python
# tests/integration/test_scan_flow.py
def test_full_scan_flow():
    """测试完整扫描流程"""
    pass

def test_tracking_flow():
    """测试完整追踪流程"""
    pass

def test_monitor_flow():
    """测试完整监控流程"""
    pass
```

**验收：**
- [ ] 集成测试编写完成

**任务 7.2：端到端测试**
```python
# tests/e2e/test_system.py
def test_system_e2e():
    """测试整个系统"""
    pass
```

**验收：**
- [ ] 端到端测试通过

**任务 7.3：测试覆盖率检查**
```bash
pytest --cov=business --cov=data --cov=infrastructure --cov-report=html
```

**验收：**
- [ ] 测试覆盖率 100%
- [ ] 生成覆盖率报告

**任务 7.4：Phase 1 验收报告**
```markdown
# Phase 1 验收报告

完成内容：
- 信号模块重构
- 策略模块重构
- 数据模块重构
- 通知模块重构
- 配置统一管理

测试结果：
- 单元测试：XX 个通过
- 集成测试：XX 个通过
- 覆盖率：100%

功能验证：
- 信号扫描：✅ 正常
- 信号追踪：✅ 正常
- 价格监控：✅ 正常
- 统计报表：✅ 正常
- 飞书推送：✅ 正常

交付物：
- 重构后的代码
- 测试报告
- 覆盖率报告
- 文档更新

下一步：
- 等待 boss 验收
- 准备 Phase 2
```

**任务 7.5：提交 Phase 1 全部工作**
```bash
git add -A
git commit -m "Phase 1 完成：基础重构"
git push origin refactor
```

**验收：**
- [ ] 代码已提交
- [ ] 代码已推送
- [ ] 等待 boss 验收

---

## 📊 每日汇报模板

```markdown
【重构进度日报】Phase 1 Day X

日期：2026-03-XX
进度：X/7 (XX%)

今日完成：
- [ ] 任务 1
- [ ] 任务 2
- [ ] 任务 3

测试结果：
- 单元测试：XX 个通过
- 测试覆盖率：XX%

遇到问题：
- 问题 1（已解决/待决策）

明日计划：
- 任务 1
- 任务 2

需要确认：
- 决策点 1（如有）

代码提交：
- [x] 已提交到 refactor 分支
- [x] 已推送到 GitHub
```

---

## ⚠️ 风险控制

### 风险 1：功能不一致
```
预防：
- 重构前先写测试
- 测试覆盖所有功能
- 重构后测试必须通过

检测：
- 每日功能验证
- 与 master 分支对比

回滚：
- 切换到 master 分支
- 恢复系统运行
```

### 风险 2：测试覆盖率不达标
```
预防：
- 测试先行
- 每行代码都有测试

检测：
- 每日覆盖率检查
- 低于 100% 不提交

回滚：
- 补充测试
- 测试通过再提交
```

### 风险 3：进度延迟
```
预防：
- 每日汇报进度
- 问题及时暴露

检测：
- 每日检查任务完成

回滚：
- 调整任务优先级
- 必要时延长 Phase 1 时间
```

---

## ✅ Phase 1 验收标准

**必须全部满足才能进入 Phase 2：**

- [ ] 所有功能正常工作
- [ ] 测试覆盖率 100%
- [ ] 代码规范通过（flake8/mypy）
- [ ] 文档完整
- [ ] boss 验收确认

---

_文档结束_
