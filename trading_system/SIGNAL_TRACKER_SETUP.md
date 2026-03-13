# 信号跟踪模块修复报告 - 2026-03-13

## ❌ 问题发现

**Boss 反馈**: 从来没有见过信号跟踪模块推送止盈止损内容

**检查结果**:
1. ❌ **没有运行** - 没有配置定时任务，没有后台进程
2. ❌ **日志为空** - `logs/signal_tracker.log` 0 字节
3. ❌ **数据库分离** - tracker 用 `signals.db`，扫描用 `trading.db`
4. ❌ **字段不匹配** - 数据库字段名不一致

---

## ✅ 修复内容

### 1️⃣ **数据库统一**

**修改前**: 
- Tracker: `cache/signals.db`
- Scanner: `cache/trading.db`

**修改后**: 
- 统一使用 `cache/trading.db`

---

### 2️⃣ **表结构完善**

**新增字段**:
```sql
ALTER TABLE signals ADD COLUMN stop_loss REAL;
ALTER TABLE signals ADD COLUMN take_profit REAL;
ALTER TABLE signals ADD COLUMN exit_price REAL;
ALTER TABLE signals ADD COLUMN exit_time TEXT;
ALTER TABLE signals ADD COLUMN exit_reason TEXT;
ALTER TABLE signals ADD COLUMN pnl_pct REAL DEFAULT 0;
```

---

### 3️⃣ **字段名兼容**

数据库字段名不一致问题：
- `stop_loss` ↔ `stop_loss_price`
- `take_profit` ↔ `take_profit_price`

**修复**: 代码中兼容两种字段名

```python
stop_loss = signal.get('stop_loss') or signal.get('stop_loss_price', 0)
take_profit = signal.get('take_profit') or signal.get('take_profit_price', 0)
```

---

### 4️⃣ **守护进程脚本**

**新增**: `scripts/run_signal_tracker.py`

**功能**:
- ✅ 每 5 分钟检查一次止盈止损
- ✅ 自动平仓触发条件的信号
- ✅ 飞书推送平仓通知
- ✅ 显示活跃信号盈亏

**运行方式**:
```bash
# 后台运行
nohup python3 scripts/run_signal_tracker.py > logs/signal_tracker.log 2>&1 &

# 查看日志
tail -f logs/signal_tracker.log
```

---

### 5️⃣ **进程状态**

```bash
# 检查进程
ps aux | grep signal_tracker

# 输出
python3 scripts/run_signal_tracker.py  ✅ 运行中
```

---

## 📊 工作流程

```
scan_realtime.py (扫描)
    ↓
保存信号到 trading.db (status=OPEN)
    ↓
signal_tracker.py (每 5 分钟检查)
    ↓
获取实时价格 (Binance API)
    ↓
检查止盈止损条件
    ↓
触发 → 平仓 + 飞书推送
    ↓
更新 status = STOP_LOSS / TAKE_PROFIT
```

---

## 🎯 平仓逻辑

### LONG 信号
- **止损**: 当前价格 ≤ 止损价 → 平仓
- **止盈**: 当前价格 ≥ 止盈价 → 平仓

### SHORT 信号
- **止损**: 当前价格 ≥ 止损价 → 平仓
- **止盈**: 当前价格 ≤ 止盈价 → 平仓

---

## 📤 飞书推送内容

平仓时会推送：

```
🔴【布林带回归】TURBOUSDT 平仓

📊 方向：SHORT
💰 入场：$0.001221
🏁 出场：$0.001099
📈 盈亏：+10.00%

🎯 平仓原因：TAKE_PROFIT

━━━━━━━━━━━━━━━━━━━━━━
ID: SIG-20260313-TURBO-BOLL-001
```

---

## 🧪 测试步骤

### 1. 查看当前活跃信号

```bash
cd /home/wz/.openclaw/workspace/trading_system
python3 -c "
from signal_tracker import SignalTracker
t = SignalTracker()
active = t.get_active_signals()
print(f'活跃信号：{len(active)} 个')
for sig in active:
    print(f'  - {sig[\"symbol\"]} {sig[\"direction\"]}: {sig.get(\"pnl_pct\", 0):+.2f}%')
"
```

### 2. 手动触发检查

```bash
python3 scripts/run_signal_tracker.py
# 运行一次完整检查
```

### 3. 查看日志

```bash
tail -f logs/signal_tracker.log
```

---

## ⚙️ 配置说明

### 检查间隔

**默认**: 5 分钟

修改：编辑 `scripts/run_signal_tracker.py`
```python
check_interval = 300  # 秒
```

### 飞书推送

**配置**: `config/config.yaml`
```yaml
notification:
  feishu:
    webhook_url: "https://..."
    enabled: true
```

---

## 📈 后续优化建议

1. **Web 界面展示** - 在 Web 应用添加"活跃信号"页面
2. **历史统计** - 统计胜率、平均盈亏比
3. ** trailing stop** - 移动止盈功能
4. **部分止盈** - 支持分批平仓
5. **性能跟踪** - 记录每个策略的表现

---

## ✅ 当前状态

| 项目 | 状态 |
|------|------|
| 数据库统一 | ✅ |
| 表结构完善 | ✅ |
| 字段兼容 | ✅ |
| 守护进程 | ✅ 运行中 |
| 检查间隔 | ✅ 5 分钟 |
| 飞书推送 | ✅ 已配置 |

---

**修复时间**: 2026-03-13 14:45  
**状态**: ✅ 已完成并运行  
**下次检查**: 5 分钟后
