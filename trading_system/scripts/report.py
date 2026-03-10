#!/usr/bin/env python3
"""
信号报告脚本 - 新系统入口
每天 20:00 运行一次，生成日报/周报
"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.reporter import SignalReporter
from config.settings import Settings

def main():
    """主函数"""
    print("=" * 80)
    print("📈 信号报告 - 新系统")
    print("=" * 80)
    print(f"报告时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    start_time = time.time()
    
    # 初始化组件（使用新系统）
    settings = Settings()
    
    # 获取配置
    feishu_webhook = settings.get('notification.feishu.webhook', '')
    feishu_enabled = settings.get('notification.feishu.enabled', True)
    daily_report_enabled = settings.get('notification.daily_report.enabled', True)
    
    # 初始化报告器（向后兼容，使用原有组件）
    reporter = SignalReporter()
    
    print(f"日报启用：{'✅' if daily_report_enabled else '❌'}")
    print(f"飞书推送：{'✅ 启用' if feishu_enabled and feishu_webhook else '❌ 禁用'}")
    print("=" * 80)
    
    # 生成报告
    try:
        # 日报
        if daily_report_enabled:
            print("📊 生成日报...")
            daily_report = reporter.generate_daily_report()
            print(daily_report)
            
            # 推送日报
            if feishu_enabled and feishu_webhook:
                reporter.send_report(daily_report, webhook_url=feishu_webhook)
        
        # 周报（每周一生成）
        if datetime.now().weekday() == 0:  # 周一
            print("\n📊 生成周报...")
            weekly_report = reporter.generate_weekly_report()
            print(weekly_report)
            
            if feishu_enabled and feishu_webhook:
                reporter.send_report(weekly_report, webhook_url=feishu_webhook)
        
    except Exception as e:
        print(f"❌ 报告生成失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    
    elapsed = time.time() - start_time
    print("=" * 80)
    print(f"✅ 报告完成！总耗时：{elapsed:.1f}秒")
    print("=" * 80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
