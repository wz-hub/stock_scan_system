"""
数据库管理模块 - 统一的 SQLite 数据库

合并 signals.db 和 market_data.db 到一个统一的数据库。
提供统一的数据库接口，支持自动清理旧数据。
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import threading


class Database:
    """统一的数据库管理类"""
    
    def __init__(self, db_path: str = "cache/trading.db"):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        self._local = threading.local()
        self._connect()
        self._create_tables()
        self._migrate_old_databases()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _connect(self):
        """连接数据库"""
        conn = self._get_connection()
        # 启用 WAL 模式提高并发性能
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
    
    def _create_tables(self):
        """创建所有表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. K 线数据表
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
        
        # 2. 信号表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                signal_hash TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                action TEXT NOT NULL,
                direction TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL DEFAULT 0,
                stop_loss REAL DEFAULT 0,
                take_profit REAL DEFAULT 0,
                position_size REAL DEFAULT 0,
                signal_data TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT,
                pnl REAL DEFAULT 0
            )
        ''')
        
        # 3. 扫描记录表
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
        
        # 4. 策略配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_configs (
                strategy_name TEXT PRIMARY KEY,
                config_data TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 5. 系统设置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 6. 资金流向数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS money_flow (
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                volume_24h REAL NOT NULL,
                change_pct REAL NOT NULL,
                net_flow REAL NOT NULL,
                direction TEXT NOT NULL,
                price REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, timestamp)
            ) WITHOUT ROWID
        ''')
        
        # 创建索引
        self._create_indexes(cursor)
        
        conn.commit()
    
    def _create_indexes(self, cursor):
        """创建索引"""
        # K 线索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_klines_symbol_interval_time 
            ON klines(symbol, interval, timestamp DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_klines_time 
            ON klines(timestamp DESC)
        ''')
        
        # 信号索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_signals_symbol 
            ON signals(symbol)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_signals_strategy 
            ON signals(strategy_name)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_signals_time 
            ON signals(timestamp DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_signals_status 
            ON signals(status)
        ''')
        
        # 扫描日志索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_scan_logs_time 
            ON scan_logs(scan_time DESC)
        ''')
        
        # 资金流向索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_money_flow_symbol_time 
            ON money_flow(symbol, timestamp DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_money_flow_time 
            ON money_flow(timestamp DESC)
        ''')
    
    def _migrate_old_databases(self):
        """迁移旧数据库数据"""
        old_market_db = Path("cache/market_data.db")
        old_signals_db = Path("cache/signals.db")
        
        if old_market_db.exists():
            self._migrate_database(old_market_db, "klines", ["klines"])
            print(f"✅ 已迁移 {old_market_db} 数据")
        
        if old_signals_db.exists():
            self._migrate_database(old_signals_db, "signals", ["signals"])
            print(f"✅ 已迁移 {old_signals_db} 数据")
    
    def _migrate_database(self, old_db_path: Path, table_prefix: str, tables: List[str]):
        """迁移单个数据库"""
        try:
            old_conn = sqlite3.connect(str(old_db_path))
            old_conn.row_factory = sqlite3.Row
            new_conn = self._get_connection()
            
            for table in tables:
                # 检查旧表是否存在
                cursor = old_conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,)
                )
                if not cursor.fetchone():
                    continue
                
                # 读取旧数据
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                
                if not rows:
                    continue
                
                # 插入新数据库
                new_cursor = new_conn.cursor()
                columns = rows[0].keys()
                placeholders = ','.join(['?' for _ in columns])
                column_names = ','.join(columns)
                
                for row in rows:
                    try:
                        values = [row[col] for col in columns]
                        new_cursor.execute(
                            f"INSERT OR IGNORE INTO {table} ({column_names}) VALUES ({placeholders})",
                            values
                        )
                    except sqlite3.IntegrityError:
                        # 主键冲突，跳过
                        continue
                
                new_conn.commit()
            
            old_conn.close()
        
        except Exception as e:
            print(f"⚠️ 迁移数据库失败 {old_db_path}: {e}")
    
    # ==================== K 线数据操作 ====================
    
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
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
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
        
        conn.commit()
    
    def get_klines(
        self, 
        symbol: str, 
        interval: str, 
        limit: int = 200,
        since: int = None
    ) -> Optional[pd.DataFrame]:
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if since:
            cursor.execute('''
                SELECT timestamp, open, high, low, close, volume, quote_volume
                FROM klines 
                WHERE symbol=? AND interval=? AND timestamp >= ?
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (symbol, interval, since, limit))
        else:
            cursor.execute('''
                SELECT timestamp, open, high, low, close, volume, quote_volume
                FROM klines 
                WHERE symbol=? AND interval=?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (symbol, interval, limit))
        
        rows = cursor.fetchall()
        
        if not rows:
            return None
        
        # 转换为 DataFrame
        df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume'])
        
        # 强制转换为数值类型
        for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 转换时间戳
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)
        
        # 按时间升序排列
        df = df.sort_index()
        
        return df
    
    def is_klines_fresh(self, symbol: str, interval: str, max_age_seconds: int = 300) -> bool:
        """
        检查 K 线数据是否新鲜
        
        Args:
            symbol: 交易对
            interval: 时间周期
            max_age_seconds: 最大年龄（秒）
        
        Returns:
            True 表示数据新鲜
        """
        conn = self._get_connection()
        cursor = conn.cursor()
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
    
    # ==================== 信号操作 ====================
    
    def save_signal(self, signal_dict: Dict):
        """
        保存信号
        
        Args:
            signal_dict: 信号字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        signal_hash = signal_dict.get('signal_hash', '')
        if not signal_hash:
            # 生成哈希
            import hashlib
            signal_str = f"{signal_dict.get('symbol', '')}{signal_dict.get('timestamp', '')}{signal_dict.get('strategy_name', '')}"
            signal_hash = hashlib.md5(signal_str.encode()).hexdigest()
        
        cursor.execute('''
            INSERT OR REPLACE INTO signals 
            (signal_hash, symbol, strategy_name, action, direction, confidence, 
             timestamp, price, stop_loss, take_profit, position_size, signal_data, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal_hash,
            signal_dict.get('symbol', ''),
            signal_dict.get('strategy_name', ''),
            signal_dict.get('action', ''),
            signal_dict.get('direction', ''),
            signal_dict.get('confidence', 0),
            signal_dict.get('timestamp', ''),
            signal_dict.get('price', 0),
            signal_dict.get('stop_loss', 0),
            signal_dict.get('take_profit', 0),
            signal_dict.get('position_size', 0),
            json.dumps(signal_dict),
            signal_dict.get('status', 'active')
        ))
        
        conn.commit()
        return signal_hash
    
    def get_signals(
        self, 
        symbol: str = None,
        strategy: str = None,
        status: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取信号列表
        
        Args:
            symbol: 交易对过滤
            strategy: 策略过滤
            status: 状态过滤
            limit: 数量限制
        
        Returns:
            信号字典列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM signals WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol=?"
            params.append(symbol)
        if strategy:
            query += " AND strategy_name=?"
            params.append(strategy)
        if status:
            query += " AND status=?"
            params.append(status)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def update_signal_status(self, signal_hash: str, status: str, pnl: float = 0):
        """
        更新信号状态
        
        Args:
            signal_hash: 信号哈希
            status: 新状态
            pnl: 盈亏
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE signals 
            SET status=?, pnl=?, closed_at=?
            WHERE signal_hash=?
        ''', (status, pnl, datetime.now().isoformat(), signal_hash))
        
        conn.commit()
    
    # ==================== 扫描日志操作 ====================
    
    def log_scan(
        self, 
        symbols_count: int, 
        signals_count: int,
        new_signals_count: int, 
        duration: float,
        status: str = 'success', 
        error_message: str = None
    ):
        """记录扫描日志"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
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
        
        conn.commit()
    
    def get_scan_stats(self, days: int = 7) -> Dict:
        """获取扫描统计"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
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
    
    # ==================== 资金流向操作 ====================
    
    def save_money_flow(self, data: List[Dict]):
        """
        保存资金流向数据
        
        Args:
            data: 资金流向数据列表
        """
        if not data:
            return
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        rows = []
        for item in data:
            rows.append((
                item.get('symbol', ''),
                item.get('timestamp', datetime.now().isoformat()),
                item.get('volume_24h', 0),
                item.get('change_pct', 0),
                item.get('net_flow', 0),
                item.get('direction', ''),
                item.get('price', 0)
            ))
        
        cursor.executemany('''
            INSERT OR REPLACE INTO money_flow 
            (symbol, timestamp, volume_24h, change_pct, net_flow, direction, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', rows)
        
        conn.commit()
    
    def get_money_flow_ranking(self, limit: int = 50) -> List[Dict]:
        """获取资金流向排行"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM money_flow
            ORDER BY timestamp DESC, net_flow DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # ==================== 配置管理 ====================
    
    def save_strategy_config(self, strategy_name: str, config: Dict, enabled: bool = True):
        """保存策略配置"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO strategy_configs 
            (strategy_name, config_data, enabled, last_updated)
            VALUES (?, ?, ?, ?)
        ''', (
            strategy_name,
            json.dumps(config),
            1 if enabled else 0,
            datetime.now().isoformat()
        ))
        
        conn.commit()
    
    def get_strategy_config(self, strategy_name: str) -> Optional[Dict]:
        """获取策略配置"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT config_data, enabled FROM strategy_configs 
            WHERE strategy_name=?
        ''', (strategy_name,))
        
        row = cursor.fetchone()
        if row:
            return {
                'config': json.loads(row['config_data']),
                'enabled': bool(row['enabled'])
            }
        return None
    
    def save_setting(self, key: str, value: str):
        """保存系统设置"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO system_settings (key, value, updated_at)
            VALUES (?, ?, ?)
        ''', (key, value, datetime.now().isoformat()))
        
        conn.commit()
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """获取系统设置"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM system_settings WHERE key=?', (key,))
        row = cursor.fetchone()
        
        return row['value'] if row else default
    
    # ==================== 数据清理 ====================
    
    def cleanup_old_data(
        self, 
        klines_days: int = 30,
        signals_days: int = 90,
        logs_days: int = 30,
        money_flow_days: int = 7
    ):
        """
        清理旧数据
        
        Args:
            klines_days: K 线数据保留天数
            signals_days: 信号数据保留天数
            logs_days: 日志保留天数
            money_flow_days: 资金流向数据保留天数
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 清理旧 K 线
        klines_cutoff = f"datetime('now', '-{klines_days} days')"
        cursor.execute(f'''
            DELETE FROM klines 
            WHERE timestamp < strftime('%s', {klines_cutoff})
        ''')
        
        # 清理旧信号
        signals_cutoff = f"datetime('now', '-{signals_days} days')"
        cursor.execute(f'''
            DELETE FROM signals 
            WHERE timestamp < {signals_cutoff} AND status != 'active'
        ''')
        
        # 清理旧日志
        logs_cutoff = f"datetime('now', '-{logs_days} days')"
        cursor.execute(f'''
            DELETE FROM scan_logs 
            WHERE scan_time < {logs_cutoff}
        ''')
        
        # 清理旧资金流向
        mf_cutoff = f"datetime('now', '-{money_flow_days} days')"
        cursor.execute(f'''
            DELETE FROM money_flow 
            WHERE timestamp < {mf_cutoff}
        ''')
        
        conn.commit()
        
        # 优化数据库
        cursor.execute('VACUUM')
        conn.commit()
        
        print(f"✅ 数据清理完成：K 线>{klines_days}天，信号>{signals_days}天，日志>{logs_days}天")
    
    def get_table_stats(self) -> Dict:
        """获取各表统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        tables = ['klines', 'signals', 'scan_logs', 'money_flow', 'strategy_configs']
        
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
            row = cursor.fetchone()
            stats[table] = row['count'] if row else 0
        
        return stats
    
    # ==================== 关闭连接 ====================
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
_db_instance = None

def get_database(db_path: str = "cache/trading.db") -> Database:
    """
    获取数据库实例（单例模式）
    
    Args:
        db_path: 数据库路径
    
    Returns:
        Database 实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path=db_path)
    return _db_instance


# 测试
if __name__ == '__main__':
    import numpy as np
    
    print("🗄️ 测试数据库...")
    
    with Database("cache/test_trading.db") as db:
        # 测试 K 线数据
        print("\n1. 测试 K 线数据...")
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        test_df = pd.DataFrame({
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(110, 120, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        }, index=dates)
        
        db.save_klines('TESTUSDT', '1d', test_df)
        print(f"   ✅ 保存 K 线成功")
        
        df = db.get_klines('TESTUSDT', '1d', limit=50)
        print(f"   ✅ 读取 K 线：{len(df)} 行")
        
        # 测试信号
        print("\n2. 测试信号...")
        signal = {
            'symbol': 'BTCUSDT',
            'strategy_name': 'test_strategy',
            'action': 'buy',
            'direction': 'long',
            'confidence': 0.85,
            'timestamp': datetime.now().isoformat(),
            'price': 50000,
            'status': 'active'
        }
        signal_hash = db.save_signal(signal)
        print(f"   ✅ 保存信号：{signal_hash[:8]}...")
        
        signals = db.get_signals(limit=10)
        print(f"   ✅ 读取信号：{len(signals)} 个")
        
        # 测试扫描日志
        print("\n3. 测试扫描日志...")
        db.log_scan(100, 5, 3, 12.5)
        stats = db.get_scan_stats()
        print(f"   ✅ 扫描统计：{stats}")
        
        # 测试配置
        print("\n4. 测试配置管理...")
        db.save_strategy_config('test_strategy', {'param1': 10, 'param2': 20})
        config = db.get_strategy_config('test_strategy')
        print(f"   ✅ 策略配置：{config}")
        
        # 测试表统计
        print("\n5. 测试表统计...")
        table_stats = db.get_table_stats()
        print(f"   ✅ 表统计：{table_stats}")
        
        # 测试数据清理
        print("\n6. 测试数据清理...")
        db.cleanup_old_data()
        print(f"   ✅ 数据清理完成")
    
    # 清理测试数据库
    Path("cache/test_trading.db").unlink(missing_ok=True)
    Path("cache/test_trading.db-shm").unlink(missing_ok=True)
    Path("cache/test_trading.db-wal").unlink(missing_ok=True)
    
    print("\n✅ 所有数据库测试通过！")
