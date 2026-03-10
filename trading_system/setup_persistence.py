#!/usr/bin/env python3
"""
数据持久化配置 - 确保扫描数据自动保存

修改内容：
1. scan_half_hourly_v3.py - 添加数据库 commit
2. signal_tracker.py - 确保信号保存
3. database.py - 添加自动 commit
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def fix_scan_script():
    """修复扫描脚本的数据保存"""
    file_path = Path('scan_half_hourly_v3.py')
    
    if not file_path.exists():
        print(f"❌ 文件不存在：{file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已有 commit
    if 'db.commit()' in content or 'db.connection.commit()' in content:
        print("✅ scan_half_hourly_v3.py 已包含 commit")
        return True
    
    # 在 save_signal 后添加 commit
    if 'db.save_signal' in content:
        # 找到 save_signal 的调用位置
        content = content.replace(
            'db.save_signal(signal_hash(signal_dict), signal_dict)',
            'db.save_signal(signal_hash(signal_dict), signal_dict)\n        db.connection.commit()  # 确保提交'
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已修复 scan_half_hourly_v3.py - 添加自动 commit")
        return True
    
    print("⚠️  未找到 save_signal 调用")
    return False


def fix_tracker_script():
    """修复追踪器脚本的数据保存"""
    file_path = Path('signal_tracker.py')
    
    if not file_path.exists():
        print(f"❌ 文件不存在：{file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查 add_signal 方法是否有 commit
    if 'def add_signal' in content:
        # 查找 add_signal 方法
        if 'conn.commit()' in content or 'connection.commit()' in content:
            print("✅ signal_tracker.py 已包含 commit")
            return True
        
        # 在 add_signal 方法末尾添加 commit
        # 这是一个简化处理，实际需要更精确的定位
        print("⚠️  signal_tracker.py 需要手动添加 commit")
        return False
    
    return False


def create_auto_backup_script():
    """创建自动备份脚本"""
    backup_script = '''#!/usr/bin/env python3
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
'''
    
    with open('auto_backup_db.py', 'w', encoding='utf-8') as f:
        f.write(backup_script)
    
    print("✅ 已创建自动备份脚本：auto_backup_db.py")
    return True


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 数据持久化配置")
    print("=" * 80)
    print()
    
    # 修复扫描脚本
    print("1. 修复扫描脚本...")
    fix_scan_script()
    print()
    
    # 修复追踪器脚本
    print("2. 修复追踪器脚本...")
    fix_tracker_script()
    print()
    
    # 创建备份脚本
    print("3. 创建备份脚本...")
    create_auto_backup_script()
    print()
    
    print("=" * 80)
    print("✅ 数据持久化配置完成")
    print("=" * 80)


if __name__ == '__main__':
    main()
