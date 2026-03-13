#!/usr/bin/env python3
"""
初始化 signals 表结构
"""
import sqlite3
from pathlib import Path

db_path = Path('cache/trading.db')
db_path.parent.mkdir(exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 创建 signals 表
cursor.execute('''
CREATE TABLE IF NOT EXISTS signals (
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
    
    -- 时间戳
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# 创建索引
cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON signals(symbol)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON signals(timestamp)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON signals(status)')

conn.commit()
conn.close()

print("✅ signals 表创建成功！")
print(f"📁 数据库位置：{db_path.absolute()}")
