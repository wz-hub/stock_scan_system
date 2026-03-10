"""
测试新的通知模块
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from notification import TemplateManager, FeishuChannel
from notification.feishu import send_signal_notification, send_close_position_notification
from datetime import datetime
import json

# 加载配置
config_file = Path('config/notification.json')
with open(config_file) as f:
    config = json.load(f)

webhook_url = config['feishu']['webhook_url']
use_card = config['feishu'].get('send_card', True)

print("📡 测试新的通知模块...")
print(f"Webhook: {webhook_url[:50]}...")
print(f"消息格式：{'卡片' if use_card else '文本'}")

# 测试模板管理器
print("\n1️⃣ 测试模板管理器...")
manager = TemplateManager()

# 测试信号模板
signal_data = {
    'signal_id': 'TEST-20260310-001',
    'strategy_name': '新通知模块测试',
    'symbol': 'BTC-USD',
    'action': 'BUY',
    'direction': 'LONG',
    'price': 95000.0,
    'timestamp': datetime.now().isoformat(),
    'confidence': 85.0,
    'stop_loss': 90000.0,
    'take_profit': 105000.0,
    'risk_reward_ratio': 2.0,
    'reason': '新通知模块功能测试 - 验证模板系统正常工作'
}

format = "card" if use_card else "text"
content = manager.render('signal', signal_data, format)
print(f"✅ 信号模板渲染成功")

# 测试飞书渠道
print("\n2️⃣ 测试飞书渠道...")
channel = FeishuChannel(webhook_url)

result = channel.send(content, format)
if result.get('success'):
    print("✅ 飞书推送成功！")
    print(f"消息 ID: {result.get('message_id')}")
else:
    print(f"❌ 推送失败：{result.get('error')}")

# 测试便捷函数
print("\n3️⃣ 测试便捷函数...")
result2 = send_signal_notification(webhook_url, signal_data, use_card)
if result2.get('success'):
    print("✅ 便捷函数发送成功！")
    print(f"消息 ID: {result2.get('message_id')}")
else:
    print(f"❌ 发送失败：{result2.get('error')}")

# 测试平仓通知
print("\n4️⃣ 测试平仓通知...")
position_data = {
    'signal_id': 'TEST-20260310-001',
    'strategy_name': '新通知模块测试',
    'symbol': 'BTC-USD',
    'action': 'BUY',
    'direction': 'LONG',
    'entry_price': 95000.0,
    'exit_price': 97000.0,
    'close_timestamp': datetime.now().isoformat(),
    'pnl': 2000.0,
    'pnl_percent': 2.11,
    'holding_period': '2 小时 30 分',
    'exit_reason': '达到止盈目标'
}

result3 = send_close_position_notification(webhook_url, position_data, use_card)
if result3.get('success'):
    print("✅ 平仓通知发送成功！")
    print(f"消息 ID: {result3.get('message_id')}")
else:
    print(f"❌ 发送失败：{result3.get('error')}")

# 测试日报模板
print("\n5️⃣ 测试日报模板...")
report_data = {
    'report_type': 'daily',
    'date': datetime.now().strftime('%Y-%m-%d'),
    'total_signals': 5,
    'closed_positions': 3,
    'total_pnl': 5000.0,
    'total_pnl_percent': 3.5,
    'win_rate': 66.7,
    'best_trade': {'symbol': 'BTC-USD', 'pnl': 3000.0},
    'worst_trade': {'symbol': 'ETH-USD', 'pnl': -500.0}
}

report_content = manager.render('daily_report', report_data, format)
print(f"✅ 日报模板渲染成功")
print(f"报告标题：{report_content['header']['title']['content']}")

print("\n✅ 所有测试完成！查看飞书群消息确认。")
print("\n📋 新通知模块功能:")
print("  - TemplateManager: 统一模板管理")
print("  - SignalTemplate: 新信号模板")
print("  - ClosePositionTemplate: 平仓通知模板")
print("  - DailyReportTemplate: 日报/周报模板")
print("  - FeishuChannel: 飞书推送渠道")
print("  - 便捷函数：send_signal_notification, send_close_position_notification")
print("  - 兼容旧版 FeishuNotifier 接口")
