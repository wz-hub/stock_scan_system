#!/usr/bin/env python3
"""
信号扫描脚本 - 新系统入口
每 30 分钟运行一次，扫描全市场信号
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

# 北京时间 (UTC+8)
def beijing_time():
    return datetime.utcnow() + timedelta(hours=8)

from core.scanner import SignalScanner
from config.settings import Settings

def main():
    """主函数"""
    print("=" * 80)
    print("📊 信号扫描 - 新系统")
    print("=" * 80)
    print(f"扫描时间：{beijing_time().strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print("=" * 80)
    
    start_time = time.time()
    
    # 初始化组件（使用新系统）
    settings = Settings()
    
    # 获取配置
    min_confidence = settings.get('scanner.min_confidence', 80)
    feishu_webhook = settings.get('notification.feishu.webhook_url', '')
    feishu_enabled = settings.get('notification.feishu.enabled', True)
    
    # 初始化扫描器（向后兼容，使用原有组件）
    scanner = SignalScanner(min_confidence=min_confidence)
    
    print(f"最低置信度：{min_confidence}%")
    print(f"飞书推送：{'✅ 启用' if feishu_enabled and feishu_webhook else '❌ 禁用'}")
    print("=" * 80)
    
    # 执行扫描
    try:
        result = scanner.scan(enable_notification=feishu_enabled)
        print(f"扫描币种：{result['scanned_count']}")
        print(f"发现信号：{result['total_signals']}")
        print(f"  └─ 新信号：{len(result['new_signals'])} 个 ⭐")
        print(f"  └─ 重复信号：{len(result['repeated_signals'])} 个")
    except Exception as e:
        print(f"❌ 扫描失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    
    elapsed = time.time() - start_time
    print("=" * 80)
    print(f"✅ 扫描完成！总耗时：{elapsed:.1f}秒")
    print("=" * 80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
