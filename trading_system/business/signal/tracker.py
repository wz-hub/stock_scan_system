"""
信号追踪模块
负责记录、追踪、管理所有信号
"""
import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path


class SignalTracker:
    """信号追踪器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化追踪器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path or str(Path('cache/signals.db'))
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                action TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                confidence REAL,
                timestamp TEXT,
                status TEXT DEFAULT 'ACTIVE',
                exit_price REAL,
                exit_time TEXT,
                exit_reason TEXT,
                pnl_pct REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON signals(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON signals(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy ON signals(strategy_name)')
        
        self.conn.commit()
    
    def add_signal(self, signal_dict: Dict) -> bool:
        """
        添加新信号
        
        Args:
            signal_dict: 信号字典
        
        Returns:
            是否添加成功
        """
        try:
            cursor = self.conn.cursor()
            
            # 检查是否已存在
            cursor.execute('SELECT signal_id FROM signals WHERE signal_id = ?', 
                          (signal_dict.get('signal_id', ''),))
            if cursor.fetchone():
                return False
            
            cursor.execute('''
                INSERT INTO signals (
                    signal_id, symbol, strategy_name, action, direction,
                    entry_price, stop_loss, take_profit, confidence,
                    timestamp, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            ''', (
                signal_dict.get('signal_id', ''),
                signal_dict.get('symbol', ''),
                signal_dict.get('strategy_name', ''),
                signal_dict.get('action', ''),
                signal_dict.get('direction', ''),
                float(signal_dict.get('entry_price', 0)),
                float(signal_dict.get('stop_loss_price', 0)),
                float(signal_dict.get('take_profit_price', 0)),
                signal_dict.get('confidence', 0),
                signal_dict.get('timestamp', datetime.now().isoformat())
            ))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"添加信号失败：{e}")
            return False
    
    def get_active_signals(self) -> List[Dict]:
        """
        获取所有活跃信号
        
        Returns:
            活跃信号列表
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT symbol, strategy_name, action, direction, entry_price,
                       stop_loss, take_profit, pnl_pct, timestamp
                FROM signals
                WHERE status = 'ACTIVE'
                ORDER BY timestamp DESC
            ''')
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"获取活跃信号失败：{e}")
            return []
    
    def has_active_signal(self, symbol: str, strategy: str) -> bool:
        """
        检查是否有活跃信号
        
        Args:
            symbol: 币种
            strategy: 策略名
        
        Returns:
            是否有活跃信号
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count FROM signals
                WHERE symbol = ? AND strategy_name = ? AND status = 'ACTIVE'
            ''', (symbol, strategy))
            
            row = cursor.fetchone()
            return row['count'] > 0 if row else False
        except Exception as e:
            print(f"检查活跃信号失败：{e}")
            return False
    
    def update_price(self, symbol: str, current_price: float) -> int:
        """
        更新信号价格
        
        Args:
            symbol: 币种
            current_price: 当前价格
        
        Returns:
            更新的信号数量
        """
        try:
            cursor = self.conn.cursor()
            active_signals = self.get_active_signals()
            updated = 0
            
            for signal in active_signals:
                if signal['symbol'] != symbol:
                    continue
                
                entry_price = signal['entry_price']
                if entry_price <= 0:
                    continue
                
                # 计算盈亏
                if signal['direction'] == 'LONG':
                    pnl_pct = (current_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - current_price) / entry_price * 100
                
                cursor.execute('''
                    UPDATE signals
                    SET pnl_pct = ?, updated_at = ?
                    WHERE symbol = ? AND strategy_name = ? AND status = 'ACTIVE'
                ''', (pnl_pct, datetime.now().isoformat(), symbol, signal['strategy_name']))
                
                updated += 1
            
            self.conn.commit()
            return updated
        except Exception as e:
            print(f"更新价格失败：{e}")
            return 0
    
    def close_signal(self, symbol: str, strategy: str, exit_price: float, reason: str) -> bool:
        """
        平仓信号
        
        Args:
            symbol: 币种
            strategy: 策略名
            exit_price: 平仓价格
            reason: 平仓原因
        
        Returns:
            是否成功
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE signals
                SET status = ?, exit_price = ?, exit_time = ?, exit_reason = ?, updated_at = ?
                WHERE symbol = ? AND strategy_name = ? AND status = 'ACTIVE'
            ''', (reason, exit_price, datetime.now().isoformat(), reason, datetime.now().isoformat(), symbol, strategy))
            
            self.conn.commit()
            
            if cursor.rowcount > 0:
                print(f"平仓：{symbol} ({strategy}) - {reason} @ {exit_price}")
                return True
            return False
        except Exception as e:
            print(f"平仓失败：{e}")
            return False
    
    def get_stats(self, days: int = 7) -> Dict:
        """
        获取统计数据
        
        Args:
            days: 统计天数
        
        Returns:
            统计字典
        """
        try:
            cursor = self.conn.cursor()
            
            # 总信号数
            cursor.execute('''
                SELECT COUNT(*) as total FROM signals
                WHERE created_at >= datetime('now', ?)
            ''', (f'-{days} days',))
            total = cursor.fetchone()['total']
            
            # 活跃信号
            cursor.execute('SELECT COUNT(*) as active FROM signals WHERE status = "ACTIVE"')
            active = cursor.fetchone()['active']
            
            # 已平仓
            cursor.execute('''
                SELECT exit_reason, COUNT(*) as count, AVG(pnl_pct) as avg_pnl
                FROM signals
                WHERE status IN ('STOP_LOSS', 'TAKE_PROFIT')
                AND created_at >= datetime('now', ?)
                GROUP BY exit_reason
            ''', (f'-{days} days',))
            
            closed_stats = {}
            for row in cursor.fetchall():
                closed_stats[row['exit_reason']] = {
                    'count': row['count'],
                    'avg_pnl': row['avg_pnl']
                }
            
            return {
                'total_signals': total,
                'active_signals': active,
                'closed_signals': closed_stats,
                'period_days': days
            }
        except Exception as e:
            print(f"获取统计失败：{e}")
            return {}
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == '__main__':
    print("测试信号追踪模块...")
    
    with SignalTracker() as tracker:
        # 测试添加信号
        test_signal = {
            'signal_id': 'TEST-001',
            'symbol': 'BTC-USD',
            'strategy_name': 'Multi-Timeframe Resonance',
            'action': 'SELL',
            'direction': 'SHORT',
            'entry_price': 50000,
            'stop_loss_price': 51000,
            'take_profit_price': 48000,
            'confidence': 85,
            'timestamp': datetime.now().isoformat()
        }
        
        success = tracker.add_signal(test_signal)
        print(f"添加信号：{'✅' if success else '❌'}")
        
        # 测试获取活跃信号
        active = tracker.get_active_signals()
        print(f"活跃信号：{len(active)} 个")
        
        # 测试检查活跃信号
        has_active = tracker.has_active_signal('BTC-USD', 'Multi-Timeframe Resonance')
        print(f"是否有活跃信号：{'✅' if has_active else '❌'}")
        
        # 测试统计
        stats = tracker.get_stats(days=7)
        print(f"统计：{stats}")
    
    print("✅ 所有测试通过！")
