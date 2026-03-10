#!/usr/bin/env python3
"""
数据库自动备份脚本
每天运行一次，备份数据库
"""

import shutil
from pathlib import Path
from datetime import datetime

def backup_database():
    """备份数据库"""
    db_path = Path('cache/trading.db')
    backup_dir = Path('cache/backups')
    backup_dir.mkdir(exist_ok=True)
    
    if not db_path.exists():
        print("❌ 数据库不存在")
        return
    
    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f'trading_{timestamp}.db'
    
    # 复制数据库
    shutil.copy2(db_path, backup_file)
    
    print(f"✅ 数据库已备份：{backup_file}")
    
    # 清理旧备份（保留 7 天）
    cutoff = datetime.now() - timedelta(days=7)
    for old_backup in backup_dir.glob('trading_*.db'):
        backup_time = datetime.fromtimestamp(old_backup.stat().st_mtime)
        if backup_time < cutoff:
            old_backup.unlink()
            print(f"🗑️  删除旧备份：{old_backup}")


if __name__ == '__main__':
    backup_database()
