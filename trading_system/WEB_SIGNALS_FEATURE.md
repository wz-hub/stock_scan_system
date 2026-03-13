# Web 信号中心功能 - 2026-03-13

## 🎯 功能概述

新增独立的 Web 信号中心，完整展示所有历史信号及 AI 评分对比。

---

## 📁 新增文件

| 文件 | 说明 |
|------|------|
| `web_signals.py` | 信号中心 Web 界面主程序 |
| `scripts/init_signals_table.py` | 数据库表初始化脚本 |
| `scripts/run_web_signals.sh` | 快速启动脚本 |

---

## 🚀 启动方式

### 方式 1：独立启动（推荐）

```bash
cd /home/wz/.openclaw/workspace/trading_system
chmod +x scripts/run_web_signals.sh
./scripts/run_web_signals.sh
```

**访问地址**: http://localhost:8502

### 方式 2：手动启动

```bash
cd /home/wz/.openclaw/workspace/trading_system
streamlit run web_signals.py --server.port 8502 --server.address localhost
```

---

## ✨ 功能特性

### 1️⃣ **信号列表表格**

- ✅ 显示最近 100 个信号
- ✅ 支持多列排序
- ✅ 支持筛选（币种、策略、方向、AI 判断）
- ✅ 实时刷新（60 秒缓存）

### 2️⃣ **AI 判断对比**

| 状态 | 说明 | 标识 |
|------|------|------|
| ✅ AI 同意 | AI 与策略方向一致 | 绿色 |
| ❌ AI 反对 | AI 与策略方向相反 | 红色 |
| ⏸️ AI 观望 | AI 建议等待 | 橙色 |
| ⚪ 未评分 | 无 AI 评分数据 | 灰色 |

### 3️⃣ **筛选功能**

**侧边栏筛选器**:
- 币种多选
- 策略单选
- 方向单选（全部/LONG/SHORT）
- AI 判断筛选（全部/一致/分歧/AI 观望）

### 4️⃣ **信号详情卡片**

每个信号显示：
- 基本信息（币种、策略、方向）
- 价格信息（入场价、置信度、时间）
- AI 评分（分数、方向、理由）
- 信号理由（可展开）
- AI 分析（可展开）
- 风险管理（止损、止盈）

---

## 📊 统计指标

**顶部 5 个统计卡片**:
1. 📊 总信号数
2. 🟢 做多信号数
3. 🔴 做空信号数
4. 🤝 AI 一致数
5. ⚠️ AI 分歧数

---

## 💾 数据库结构

### signals 表

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT UNIQUE,
    symbol TEXT NOT NULL,
    timeframe TEXT,
    strategy_name TEXT,
    action TEXT,
    direction TEXT,
    entry_price REAL,
    stop_loss_price REAL,
    take_profit_price REAL,
    confidence REAL,
    reason TEXT,
    position_pct REAL,
    status TEXT DEFAULT 'OPEN',
    
    -- AI 评分字段
    ai_score INTEGER,
    ai_direction TEXT,
    ai_reason TEXT,
    
    timestamp DATETIME,
    created_at DATETIME,
    updated_at DATETIME
)
```

---

## 🎨 界面预览

### 顶部统计区
```
┌─────────┬─────────┬─────────┬─────────┬─────────┐
│ 📊 总信号│ 🟢 做多 │ 🔴 做空 │ 🤝 AI 一致│ ⚠️ AI 分歧│
│   100   │   45    │   55    │   20    │   15    │
└─────────┴─────────┴─────────┴─────────┴─────────┘
```

### 筛选器（侧边栏）
```
🔍 筛选条件
├─ 币种：[BTCUSDT] [ETHUSDT] ...
├─ 策略：[全部 ▼]
├─ 方向：○ 全部 ○ LONG ○ SHORT
└─ AI 判断：[全部 ▼]
```

### 信号卡片
```
╔═══════════════════════════════════════════════╗
║ 🟢【布林带回归】TURBOUSDT LONG                ║
╠═══════════════════════════════════════════════╣
║ 💰 价格：$0.001221   📈 置信度：90%           ║
║ 📅 时间：2026-03-13  🤖 AI 评分：65%          ║
║                                               ║
║ ✅ AI 同意                                    ║
║                                               ║
║ [💡 信号理由 ▼]                               ║
║ [🤖 AI 分析 ▼]                                ║
║                                               ║
║ 🛑 止损：$0.001099  🎯 止盈：$0.001343        ║
╚═══════════════════════════════════════════════╝
```

---

## 📈 使用场景

### 1. 复盘历史信号

查看所有历史信号，分析策略表现。

### 2. AI 与策略对比

筛选"AI 分歧"信号，研究 AI 与策略的不同判断。

### 3. 策略效果分析

按策略筛选，对比不同策略的表现。

### 4. 币种分析

筛选特定币种，查看该币种的所有信号。

---

## ⚙️ 配置说明

### 端口配置

默认端口：`8502`

修改端口：
```bash
streamlit run web_signals.py --server.port 8503
```

### 数据刷新

- 缓存时间：60 秒
- 自动刷新：浏览器刷新或等待缓存过期

### 显示数量

- 默认显示：最近 100 个信号
- 卡片详情：最近 20 个信号

修改数量：编辑 `web_signals.py` 中的 `load_signals(limit=100)`

---

## 🔗 与主 Web 应用集成

**主应用** (`web_app_v11.py`) 已添加快捷链接：

侧边栏 → 快捷链接 → 📡 完整信号中心

点击即可跳转到独立信号中心页面。

---

## 🧪 测试步骤

1. **初始化数据库**
   ```bash
   python3 scripts/init_signals_table.py
   ```

2. **运行一次扫描**
   ```bash
   python3 scan_realtime.py
   ```

3. **启动 Web 界面**
   ```bash
   ./scripts/run_web_signals.sh
   ```

4. **访问页面**
   
   浏览器打开：http://localhost:8502

---

## 📝 后续优化建议

1. **信号跟踪** - 添加信号后续走势跟踪
2. **胜率统计** - 统计策略/AI 的准确率
3. **图表展示** - 添加信号分布图、胜率图
4. **导出功能** - 支持导出 CSV/Excel
5. **实时监控** - WebSocket 实时推送新信号

---

**版本**: v1.0  
**创建时间**: 2026-03-13  
**状态**: ✅ 已完成
