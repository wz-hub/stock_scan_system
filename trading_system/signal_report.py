#!/usr/bin/env python3
"""
信号统计报表 - 每天 20:00 运行
- 生成日报/周报
- 推送到飞书
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from signal_tracker import SignalTracker
from feishu_notifier import FeishuNotifier

# 加载配置
config_file = Path('config/notification.json')
with open(config_file) as f:
    config = json.load(f)

feishu_config = config.get('feishu', {})
webhook_url = feishu_config.get('webhook_url', '')

print("="*80)
print("📊 信号统计报表")
print("="*80)
print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# 初始化
tracker = SignalTracker()
notifier = FeishuNotifier(webhook_url) if webhook_url else None

# 获取统计
stats_daily = tracker.get_stats(days=1)
stats_weekly = tracker.get_stats(days=7)

# 生成日报
daily_report = f"""
📊 信号日报 ({datetime.now().strftime('%Y-%m-%d')})

【总体统计】
总信号：{stats_daily['total_signals']}
活跃：{stats_daily['active_signals']}

【平仓统计】
"""

closed = stats_daily.get('closed_signals', {})
if closed:
    for reason, data in closed.items():
        reason_cn = "止盈" if reason == 'TAKE_PROFIT' else "止损"
        daily_report += f"{reason_cn}: {data['count']} (平均盈亏：{data['avg_pnl']:.2f}%)\n"
else:
    daily_report += "今日无平仓信号\n"

daily_report += f"""
【时间】{datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━
"""

# 生成周报
weekly_report = f"""
📊 信号周报 ({(datetime.now() - timedelta(days=7)).strftime('%m-%d')} ~ {datetime.now().strftime('%m-%d')})

【总体统计】
总信号：{stats_weekly['total_signals']}
活跃：{stats_weekly['active_signals']}

【平仓统计】
"""

closed = stats_weekly.get('closed_signals', {})
if closed:
    for reason, data in closed.items():
        reason_cn = "止盈" if reason == 'TAKE_PROFIT' else "止损"
        weekly_report += f"{reason_cn}: {data['count']} (平均盈亏：{data['avg_pnl']:.2f}%)\n"
else:
    weekly_report += "本周无平仓信号\n"

weekly_report += f"""
【时间】{datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━
"""

# 推送日报
if notifier:
    print("\n📤 推送日报...")
    try:
        result = notifier.send_text(daily_report)
        if result.get('success'):
            print("  ✅ 日报推送成功")
        else:
            print(f"  ❌ 推送失败：{result}")
    except Exception as e:
        print(f"  ❌ 推送异常：{e}")

# 每周一推送周报
if datetime.now().weekday() == 0:  # 周一
    print("\n📤 推送周报...")
    try:
        result = notifier.send_text(weekly_report)
        if result.get('success'):
            print("  ✅ 周报推送成功")
        else:
            print(f"  ❌ 推送失败：{result}")
    except Exception as e:
        print(f"  ❌ 推送异常：{e}")

tracker.close()
print("\n" + "="*80)
print("✅ 报表生成完成")
print("="*80)
