"""
数据库模块测试
测试 Database 类的核心功能
"""
import pytest
import sys
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import tempfile
import os
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import Database


class TestDatabase:
    """Database 测试类"""
    
    @pytest.fixture
    def db_path(self, tmp_path):
        """创建临时数据库路径"""
        return str(tmp_path / 'test_trading.db')
    
    @pytest.fixture
    def db(self, db_path):
        """创建数据库实例"""
        database = Database(db_path=db_path)
        yield database
        database.close()
    
    def test_init(self, db, db_path):
        """测试初始化"""
        assert db is not None
        assert str(db.db_path) == db_path
        assert db._get_connection() is not None
    
    def test_create_tables(self, db):
        """测试表创建"""
        conn = db._get_connection()
        cursor = conn.cursor()
        
        # 检查所有表是否存在
        tables = ['klines', 'signals', 'scan_logs', 'strategy_configs', 'system_settings', 'money_flow']
        
        for table in tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            result = cursor.fetchone()
            assert result is not None, f"Table {table} should exist"
    
    def test_create_indexes(self, db):
        """测试索引创建"""
        conn = db._get_connection()
        cursor = conn.cursor()
        
        # 检查关键索引
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        assert len(indexes) > 0
        assert any('klines' in idx for idx in indexes)
        assert any('signals' in idx for idx in indexes)
    
    def test_save_klines(self, db):
        """测试保存 K 线数据"""
        klines_data = [
            {
                'symbol': 'BTCUSDT',
                'interval': '1h',
                'timestamp': int((datetime.now() - timedelta(hours=i)).timestamp() * 1000),
                'open': 50000 + i * 10,
                'high': 50100 + i * 10,
                'low': 49900 + i * 10,
                'close': 50050 + i * 10,
                'volume': 1000 + i,
                'quote_volume': 50000000,
                'trades_count': 5000
            }
            for i in range(10)
        ]
        
        result = db.save_klines(klines_data)
        
        assert result == 10
        
        # 验证数据已保存
        cursor = db._get_connection().cursor()
        cursor.execute("SELECT COUNT(*) FROM klines WHERE symbol='BTCUSDT'")
        count = cursor.fetchone()[0]
        assert count == 10
    
    def test_save_klines_duplicate(self, db):
        """测试保存重复 K 线数据"""
        klines_data = [
            {
                'symbol': 'ETHUSDT',
                'interval': '1h',
                'timestamp': 1234567890000,
                'open': 3000,
                'high': 3010,
                'low': 2990,
                'close': 3005,
                'volume': 500,
                'quote_volume': 1500000,
                'trades_count': 2000
            }
        ]
        
        # 第一次保存
        result1 = db.save_klines(klines_data)
        assert result1 == 1
        
        # 第二次保存（重复）
        result2 = db.save_klines(klines_data)
        assert result2 == 0  # 应该更新而不是插入
    
    def test_get_klines(self, db):
        """测试获取 K 线数据"""
        # 先保存数据
        klines_data = [
            {
                'symbol': 'BTCUSDT',
                'interval': '1h',
                'timestamp': int((datetime.now() - timedelta(hours=i)).timestamp() * 1000),
                'open': 50000,
                'high': 50100,
                'low': 49900,
                'close': 50050,
                'volume': 1000,
                'quote_volume': 50000000,
                'trades_count': 5000
            }
            for i in range(20)
        ]
        db.save_klines(klines_data)
        
        # 获取数据
        df = db.get_klines('BTCUSDT', '1h', limit=10)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert 'close' in df.columns
    
    def test_get_klines_as_dataframe(self, db):
        """测试获取 DataFrame 格式 K 线"""
        klines_data = [
            {
                'symbol': 'ETHUSDT',
                'interval': '1d',
                'timestamp': int((datetime.now() - timedelta(days=i)).timestamp() * 1000),
                'open': 3000,
                'high': 3050,
                'low': 2950,
                'close': 3020,
                'volume': 10000,
                'quote_volume': 30000000,
                'trades_count': 50000
            }
            for i in range(30)
        ]
        db.save_klines(klines_data)
        
        df = db.get_klines_as_dataframe('ETHUSDT', '1d', limit=20)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 20
    
    def test_save_signal(self, db):
        """测试保存信号"""
        signal_data = {
            'strategy_name': 'Multi-Timeframe Resonance',
            'symbol': 'BTCUSDT',
            'action': 'BUY',
            'direction': 'LONG',
            'confidence': 75,
            'timestamp': datetime.now().isoformat(),
            'price': 50000,
            'stop_loss': 49000,
            'take_profit': 52000,
            'position_size': 10
        }
        
        signal_hash = 'test_signal_hash_001'
        result = db.save_signal(signal_hash, signal_data)
        
        assert result is True
        
        # 验证信号已保存
        cursor = db._get_connection().cursor()
        cursor.execute("SELECT * FROM signals WHERE signal_hash=?", (signal_hash,))
        row = cursor.fetchone()
        assert row is not None
        assert row['symbol'] == 'BTCUSDT'
    
    def test_save_signal_duplicate(self, db):
        """测试保存重复信号"""
        signal_data = {
            'strategy_name': 'Test Strategy',
            'symbol': 'ETHUSDT',
            'action': 'SELL',
            'direction': 'SHORT',
            'confidence': 70,
            'timestamp': datetime.now().isoformat()
        }
        
        signal_hash = 'test_signal_hash_002'
        
        # 第一次保存
        result1 = db.save_signal(signal_hash, signal_data)
        assert result1 is True
        
        # 第二次保存（更新）
        result2 = db.save_signal(signal_hash, signal_data)
        assert result2 is True  # 更新成功
    
    def test_get_signals(self, db):
        """测试获取信号"""
        # 保存多个信号
        for i in range(5):
            signal_data = {
                'strategy_name': 'Test Strategy',
                'symbol': f'BTC{i}USDT',
                'action': 'BUY',
                'direction': 'LONG',
                'confidence': 70 + i,
                'timestamp': datetime.now().isoformat()
            }
            db.save_signal(f'test_hash_{i}', signal_data)
        
        signals = db.get_signals(limit=3)
        
        assert len(signals) == 3
        assert isinstance(signals, list)
    
    def test_get_signals_by_status(self, db):
        """测试按状态获取信号"""
        # 保存不同状态的信号
        for status in ['active', 'closed', 'stopped']:
            signal_data = {
                'strategy_name': 'Test Strategy',
                'symbol': 'BTCUSDT',
                'action': 'BUY',
                'direction': 'LONG',
                'confidence': 75,
                'timestamp': datetime.now().isoformat()
            }
            db.save_signal(f'status_hash_{status}', signal_data)
            if status != 'active':
                db.update_signal_status(f'status_hash_{status}', status)
        
        active_signals = db.get_signals_by_status('active')
        
        assert len(active_signals) >= 1
    
    def test_update_signal_status(self, db):
        """测试更新信号状态"""
        signal_data = {
            'strategy_name': 'Test Strategy',
            'symbol': 'BTCUSDT',
            'action': 'BUY',
            'direction': 'LONG',
            'confidence': 75,
            'timestamp': datetime.now().isoformat()
        }
        
        signal_hash = 'status_test_hash'
        db.save_signal(signal_hash, signal_data)
        
        # 更新状态
        db.update_signal_status(signal_hash, 'closed')
        
        # 验证状态已更新
        signals = db.get_signals(signal_hash=signal_hash)
        assert len(signals) == 1
        assert signals[0]['status'] == 'closed'
    
    def test_log_scan(self, db):
        """测试记录扫描日志"""
        result = db.log_scan(
            symbols_count=100,
            signals_count=10,
            new_signals_count=5,
            duration=30.5
        )
        
        assert result is True
        
        # 验证日志已保存
        cursor = db._get_connection().cursor()
        cursor.execute("SELECT COUNT(*) FROM scan_logs")
        count = cursor.fetchone()[0]
        assert count >= 1
    
    def test_get_scan_logs(self, db):
        """测试获取扫描日志"""
        # 记录多次扫描
        for i in range(5):
            db.log_scan(
                symbols_count=100,
                signals_count=i * 2,
                new_signals_count=i,
                duration=30.0
            )
        
        logs = db.get_scan_logs(limit=3)
        
        assert len(logs) == 3
        assert 'scan_time' in logs[0]
        assert 'symbols_count' in logs[0]
    
    def test_save_strategy_config(self, db):
        """测试保存策略配置"""
        config = {
            'enabled': True,
            'parameters': {
                'fast_ma': 20,
                'slow_ma': 50
            }
        }
        
        result = db.save_strategy_config('Test Strategy', config)
        
        assert result is True
        
        # 验证配置已保存
        saved_config = db.get_strategy_config('Test Strategy')
        assert saved_config is not None
        assert saved_config['enabled'] is True
    
    def test_get_strategy_config(self, db):
        """测试获取策略配置"""
        config = {'param1': 'value1', 'param2': 123}
        db.save_strategy_config('Config Test Strategy', config)
        
        retrieved = db.get_strategy_config('Config Test Strategy')
        
        assert retrieved == config
    
    def test_get_strategy_config_not_found(self, db):
        """测试获取不存在的策略配置"""
        config = db.get_strategy_config('Nonexistent Strategy')
        
        assert config is None
    
    def test_save_system_setting(self, db):
        """测试保存系统设置"""
        result = db.save_system_setting('test_key', 'test_value')
        
        assert result is True
        
        # 验证设置已保存
        value = db.get_system_setting('test_key')
        assert value == 'test_value'
    
    def test_get_system_setting(self, db):
        """测试获取系统设置"""
        db.save_system_setting('setting_key', 'setting_value')
        
        value = db.get_system_setting('setting_key')
        default = db.get_system_setting('nonexistent_key', 'default')
        
        assert value == 'setting_value'
        assert default == 'default'
    
    def test_save_money_flow(self, db):
        """测试保存资金流数据"""
        flow_data = {
            'symbol': 'BTCUSDT',
            'timestamp': datetime.now().isoformat(),
            'volume_24h': 1000000000,
            'change_pct': 2.5,
            'net_flow': 5000000,
            'direction': 'INFLOW',
            'price': 50000
        }
        
        result = db.save_money_flow(flow_data)
        
        assert result is True
        
        # 验证数据已保存
        cursor = db._get_connection().cursor()
        cursor.execute("SELECT * FROM money_flow WHERE symbol='BTCUSDT'")
        row = cursor.fetchone()
        assert row is not None
    
    def test_get_money_flow_history(self, db):
        """测试获取资金流历史"""
        # 保存多条资金流数据
        for i in range(10):
            flow_data = {
                'symbol': 'ETHUSDT',
                'timestamp': (datetime.now() - timedelta(hours=i)).isoformat(),
                'volume_24h': 500000000,
                'change_pct': 1.0,
                'net_flow': 1000000 * (i - 5),
                'direction': 'INFLOW' if i > 5 else 'OUTFLOW',
                'price': 3000
            }
            db.save_money_flow(flow_data)
        
        history = db.get_money_flow_history('ETHUSDT', limit=5)
        
        assert len(history) == 5
    
    def test_cleanup_old_data(self, db):
        """测试清理旧数据"""
        # 保存一些数据
        for i in range(20):
            klines_data = [{
                'symbol': 'BTCUSDT',
                'interval': '1h',
                'timestamp': int((datetime.now() - timedelta(hours=i)).timestamp() * 1000),
                'open': 50000,
                'high': 50100,
                'low': 49900,
                'close': 50050,
                'volume': 1000,
                'quote_volume': 50000000,
                'trades_count': 5000
            }]
            db.save_klines(klines_data)
        
        # 清理 10 小时前的数据
        cutoff = int((datetime.now() - timedelta(hours=10)).timestamp() * 1000)
        deleted = db.cleanup_old_data('klines', cutoff)
        
        assert deleted >= 0
    
    def test_get_table_stats(self, db):
        """测试获取表统计信息"""
        # 保存一些数据
        for i in range(5):
            db.log_scan(symbols_count=100, signals_count=5, new_signals_count=2, duration=30.0)
        
        stats = db.get_table_stats('scan_logs')
        
        assert 'count' in stats
        assert stats['count'] == 5
    
    def test_close(self, db):
        """测试关闭数据库"""
        conn = db._get_connection()
        db.close()
        
        # 验证连接已关闭
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")
    
    def test_context_manager(self, db_path):
        """测试上下文管理器"""
        with Database(db_path=db_path) as db:
            cursor = db._get_connection().cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        
        # 退出上下文后数据库应关闭
    
    def test_thread_safety(self, db):
        """测试线程安全性"""
        import threading
        
        errors = []
        
        def save_data(thread_id):
            try:
                for i in range(10):
                    klines_data = [{
                        'symbol': f'BTC{thread_id}USDT',
                        'interval': '1h',
                        'timestamp': int((datetime.now() - timedelta(hours=i)).timestamp() * 1000),
                        'open': 50000,
                        'high': 50100,
                        'low': 49900,
                        'close': 50050,
                        'volume': 1000,
                        'quote_volume': 50000000,
                        'trades_count': 5000
                    }]
                    db.save_klines(klines_data)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=save_data, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0


class TestDatabaseEdgeCases:
    """Database 边界测试"""
    
    def test_empty_klines_list(self, db):
        """测试空 K 线列表"""
        result = db.save_klines([])
        assert result == 0
    
    def test_invalid_signal_hash(self, db):
        """测试无效信号哈希"""
        signal_data = {
            'strategy_name': 'Test',
            'symbol': 'BTCUSDT',
            'action': 'BUY',
            'direction': 'LONG',
            'confidence': 75,
            'timestamp': datetime.now().isoformat()
        }
        
        result = db.save_signal('', signal_data)
        assert result is True  # 应该能处理空哈希
    
    def test_database_auto_create_directory(self, tmp_path):
        """测试自动创建目录"""
        db_path = str(tmp_path / 'subdir' / 'test.db')
        
        db = Database(db_path=db_path)
        
        assert os.path.exists(db_path)
        db.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
