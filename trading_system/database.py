"""
数据库管理模块 - SQLite 存储 K 线数据
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import json

DB_FILE = Path('cache/market_data.db')
DB_FILE.parent.mkdir(exist_ok=True)


class MarketDatabase:
    """市场数据数据库"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_FILE)
        self.conn = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
    
    def _create_tables(self):
        """创建表"""
        cursor = self.conn.cursor()
        
        # K 线数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS klines (
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                quote_volume REAL DEFAULT 0,
                trades_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, interval, timestamp)
            ) WITHOUT ROWID
        ''')
        
        # 信号缓存表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                signal_hash TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                action TEXT NOT NULL,
                direction TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp TEXT NOT NULL,
                signal_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 扫描记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_time TEXT NOT NULL,
                symbols_count INTEGER,
                signals_count INTEGER,
                new_signals_count INTEGER,
                duration_seconds REAL,
                status TEXT DEFAULT 'success',
                error_message TEXT
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_klines_symbol_time 
            ON klines(symbol, interval, timestamp DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_signals_time 
            ON signals(timestamp DESC)
        ''')
        
        self.conn.commit()
    
    def save_klines(self, symbol: str, interval: str, df: pd.DataFrame):
        """
        保存 K 线数据
        
        Args:
            symbol: 交易对
            interval: 时间周期
            df: K 线 DataFrame
        """
        if df.empty:
            return
        
        cursor = self.conn.cursor()
        
        # 准备数据
        rows = []
        for _, row in df.iterrows():
            timestamp = int(row.name.timestamp()) if hasattr(row.name, 'timestamp') else int(row.name)
            rows.append((
                symbol,
                interval,
                timestamp,
                float(row.get('open', 0)),
                float(row.get('high', 0)),
                float(row.get('low', 0)),
                float(row.get('close', 0)),
                float(row.get('volume', 0)),
                float(row.get('quote_volume', 0)),
                int(row.get('trades', 0))
            ))
        
        # 批量插入/更新
        cursor.executemany('''
            INSERT OR REPLACE INTO klines 
            (symbol, interval, timestamp, open, high, low, close, volume, quote_volume, trades_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', rows)
        
        self.conn.commit()
    
    def get_klines(self, symbol: str, interval: str, limit: int = 200, 
                   since: int = None) -> Optional[pd.DataFrame]:
        """
        获取 K 线数据
        
        Args:
            symbol: 交易对
            interval: 时间周期
            limit: 数量限制
            since: 起始时间戳
        
        Returns:
            DataFrame 或 None
        """
        cursor = self.conn.cursor()
        
        if since:
            cursor.execute('''
                SELECT timestamp, open, high, low, close, volume 
                FROM klines 
                WHERE symbol=? AND interval=? AND timestamp >= ?
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (symbol, interval, since, limit))
        else:
            cursor.execute('''
                SELECT timestamp, open, high, low, close, volume 
                FROM klines 
                WHERE symbol=? AND interval=?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (symbol, interval, limit))
        
        rows = cursor.fetchall()
        
        if not rows:
            return None
        
        # 转换为 DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 强制转换为数值类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 转换时间戳
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)
        
        # 按时间升序排列
        df = df.sort_index()
        
        return df
    
    def is_fresh(self, symbol: str, interval: str, max_age_seconds: int = 300) -> bool:
        """
        检查数据是否新鲜
        
        Args:
            symbol: 交易对
            interval: 时间周期
            max_age_seconds: 最大年龄（秒）
        
        Returns:
            True 表示数据新鲜
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT MAX(timestamp) as latest 
            FROM klines 
            WHERE symbol=? AND interval=?
        ''', (symbol, interval))
        
        row = cursor.fetchone()
        if not row or not row['latest']:
            return False
        
        latest_time = row['latest']
        now = int(datetime.now().timestamp())
        
        return (now - latest_time) < max_age_seconds
    
    def save_signal(self, signal_hash: str, signal_dict: dict):
        """保存信号"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO signals 
            (signal_hash, symbol, strategy_name, action, direction, confidence, timestamp, signal_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal_hash,
            signal_dict.get('symbol', ''),
            signal_dict.get('strategy_name', ''),
            signal_dict.get('action', ''),
            signal_dict.get('direction', ''),
            signal_dict.get('confidence', 0),
            signal_dict.get('timestamp', ''),
            json.dumps(signal_dict)
        ))
        self.conn.commit()
    
    def get_recent_signals(self, limit: int = 100) -> List[dict]:
        """获取最近的信号"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT signal_data FROM signals 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        return [json.loads(row['signal_data']) for row in rows]
    
    def log_scan(self, symbols_count: int, signals_count: int, 
                 new_signals_count: int, duration: float, 
                 status: str = 'success', error_message: str = None):
        """记录扫描日志"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO scan_logs 
            (scan_time, symbols_count, signals_count, new_signals_count, duration_seconds, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            symbols_count,
            signals_count,
            new_signals_count,
            duration,
            status,
            error_message
        ))
        self.conn.commit()
    
    def get_scan_stats(self, days: int = 7) -> dict:
        """获取扫描统计"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_scans,
                AVG(symbols_count) as avg_symbols,
                AVG(signals_count) as avg_signals,
                AVG(duration_seconds) as avg_duration,
                MIN(duration_seconds) as min_duration,
                MAX(duration_seconds) as max_duration
            FROM scan_logs 
            WHERE scan_time >= datetime('now', ?)
        ''', (f'-{days} days',))
        
        row = cursor.fetchone()
        return dict(row) if row else {}
    
    def cleanup_old_data(self, days: int = 30):
        """清理旧数据"""
        cursor = self.conn.cursor()
        cutoff = f"datetime('now', '-{days} days')"
        
        # 清理旧 K 线
        cursor.execute(f'''
            DELETE FROM klines 
            WHERE timestamp < strftime('%s', {cutoff})
        ''')
        
        # 清理旧信号
        cursor.execute(f'''
            DELETE FROM signals 
            WHERE timestamp < {cutoff}
        ''')
        
        # 清理旧日志
        cursor.execute(f'''
            DELETE FROM scan_logs 
            WHERE scan_time < {cutoff}
        ''')
        
        self.conn.commit()
        
        # 优化数据库
        cursor.execute('VACUUM')
        self.conn.commit()
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def get_database() -> MarketDatabase:
    """获取数据库实例"""
    return MarketDatabase()


# 测试
if __name__ == '__main__':
    import numpy as np
    
    print("测试数据库...")
    
    with MarketDatabase() as db:
        # 创建测试数据
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        test_df = pd.DataFrame({
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(110, 120, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        }, index=dates)
        
        # 保存
        db.save_klines('TESTUSDT', '1d', test_df)
        print("✅ 保存测试数据成功")
        
        # 读取
        df = db.get_klines('TESTUSDT', '1d', limit=50)
        print(f"✅ 读取数据成功：{len(df)} 行")
        
        # 检查新鲜度
        is_fresh = db.is_fresh('TESTUSDT', '1d')
        print(f"✅ 数据新鲜度：{is_fresh}")
        
        # 统计
        stats = db.get_scan_stats()
        print(f"✅ 数据库统计：{stats}")
    
    print("\n✅ 所有测试通过！")
