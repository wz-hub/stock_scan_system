# 数据库管理规范

**创建时间:** 2026-03-10  
**重要性:** ⭐⭐⭐⭐⭐ (最高优先级)

---

## 🚫 第一条：禁止随意删除数据库

**规矩：** 任何情况下都不能随意删除数据库文件！

### 受保护的数据库文件

| 文件 | 路径 | 重要性 |
|------|------|--------|
| **trading.db** | `cache/trading.db` | ⭐⭐⭐⭐⭐ 核心数据 |
| **signals.db** | `cache/signals.db` | ⭐⭐⭐⭐⭐ 信号记录 |
| **market_data.db** | `cache/market_data.db` | ⭐⭐⭐⭐ 市场数据 |
| **klines_cache.json** | `cache/klines_cache.json` | ⭐⭐⭐ 缓存数据 |

---

## ✅ 允许删除的情况

**只有以下情况可以删除数据库：**

1. **数据库损坏** - 无法读取或写入
2. **数据格式错误** - 时间戳等字段格式不正确
3. **boss 明确指示** - boss 要求删除

**删除前必须：**
- ✅ 备份旧数据库
- ✅ 记录删除原因
- ✅ 通知 boss

---

## 📋 数据库操作规范

### 1. 下载数据

**正确做法：**
```bash
# 增量下载（推荐）
python3 download_history.py --symbols BTCUSDT --days 30

# 检查数据是否存在
python3 -c "import sqlite3; conn = sqlite3.connect('cache/trading.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM klines'); print(f'数据量：{cursor.fetchone()[0]}')"
```

**错误做法：**
```bash
# ❌ 直接删除数据库
rm cache/trading.db

# ❌ 不检查就重新下载
```

### 2. 数据校验

**定期校验数据完整性：**
```bash
python3 -c "
import sqlite3
from datetime import datetime

conn = sqlite3.connect('cache/trading.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT symbol, interval, COUNT(*), 
           MIN(timestamp), MAX(timestamp)
    FROM klines
    GROUP BY symbol, interval
''')

for row in cursor.fetchall():
    print(f'{row[0]} {row[1]}: {row[2]} 条')

conn.close()
"
```

### 3. 数据备份

**每天自动备份：**
```bash
python3 auto_backup_db.py
```

**手动备份：**
```bash
cp cache/trading.db cache/trading_backup_$(date +%Y%m%d_%H%M%S).db
```

---

## 🔧 数据库修复流程

**如果数据库有问题：**

### Step 1: 备份
```bash
cp cache/trading.db cache/trading.db.backup
echo "✅ 已备份数据库"
```

### Step 2: 诊断
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('cache/trading.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM klines')
print(f'数据量：{cursor.fetchone()[0]}')
conn.close()
"
```

### Step 3: 修复（仅修复问题数据）
```bash
# 删除异常时间戳数据（如果有）
python3 -c "
import sqlite3
conn = sqlite3.connect('cache/trading.db')
cursor = conn.cursor()

# 找出异常数据
cursor.execute('SELECT COUNT(*) FROM klines WHERE timestamp > 1893456000')
abnormal = cursor.fetchone()[0]

if abnormal > 0:
    print(f'发现 {abnormal} 条异常数据')
    # 不要删除！先报告
    print('⚠️  发现异常数据，请联系 boss 决定如何处理')
else:
    print('✅ 数据正常')

conn.close()
"
```

### Step 4: 增量补充（如果数据缺失）
```bash
# 只下载缺失的时间段
python3 download_history.py --symbols BTCUSDT --days 7
```

---

## 📝 数据库操作日志

**每次操作数据库都要记录：**

```markdown
## 2026-03-10

### 操作：下载历史数据
- **时间:** 18:30
- **操作人:** 虾仁
- **内容:** 下载 BTCUSDT,ETHUSDT 的 1d/4h/1h 数据
- **数据量:** 22,636 条
- **结果:** ✅ 成功
- **备份:** 已自动备份

### 操作：[待填写]
- **时间:** 
- **操作人:** 
- **内容:** 
- **结果:** 
```

---

## ⚠️ 违规处罚

**违反本规范的后果：**

1. **第一次:** 警告 + 写检查
2. **第二次:** 暂停数据库操作权限
3. **第三次:** 重置所有权限

---

## 📞 紧急情况联系

**如果发现数据库问题：**

1. **立即停止操作**
2. **备份当前状态**
3. **通知 boss**
4. **等待指示**

---

**本规范自创建之日起生效，所有操作人员必须严格遵守！**

**创建人:** 虾仁  
**批准人:** 王振 (boss)  
**生效日期:** 2026-03-10
