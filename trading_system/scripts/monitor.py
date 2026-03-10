#!/usr/bin/env python3
"""
信号监控脚本 - 新系统入口
每 5 分钟运行一次，检查平仓条件
"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.monitor import SignalMonitor
from config.settings import Settings

def main():
    """主函数"""
    print("=" * 80)
    print("🔍 信号监控 - 新系统")
    print("=" * 80)
    print(f"监控时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    start_time = time.time()
    
    # 初始化组件（使用新系统）
    settings = Settings()
    
    # 获取配置
    notify_on_exit = settings.get('tracker.notify_on_exit', True)
    feishu_webhook = settings.get('notification.feishu.webhook', '')
    feishu_enabled = settings.get('notification.feishu.enabled', True)
    
    # 初始化监控器（向后兼容，使用原有组件）
    monitor = SignalMonitor()
    
    print(f"追踪状态：✅ 已启用")
    print(f"平仓通知：{'✅ 启用' if notify_on_exit and feishu_enabled else '❌ 禁用'}")
    print("=" * 80)
    
    # 执行监控
    try:
        result = monitor.check_all_exits()
        print(f"检查平仓条件... {'✅ 无平仓信号' if not result else f'🔔 {len(result)} 个平仓信号'}")
        
        # 推送平仓通知
        if result and feishu_enabled and feishu_webhook:
            from notification.feishu import FeishuNotifier
            notifier = FeishuNotifier(feishu_webhook)
            for exit_signal in result:
                notifier.send_exit_signal(exit_signal)
    except Exception as e:
        print(f"❌ 监控失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    
    elapsed = time.time() - start_time
    print("=" * 80)
    print(f"✅ 监控完成！总耗时：{elapsed:.1f}秒")
    print("=" * 80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
