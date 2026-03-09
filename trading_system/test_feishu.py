"""
测试飞书推送
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from feishu_notifier import FeishuNotifier, SignalMessage
from datetime import datetime
import json

# 加载配置
config_file = Path('config/notification.json')
with open(config_file) as f:
    config = json.load(f)

webhook_url = config['feishu']['webhook_url']

print("📡 测试飞书推送...")
print(f"Webhook: {webhook_url[:50]}...")

notifier = FeishuNotifier(webhook_url)

# 测试连接
print("\n🔍 测试连接...")
test_signal = SignalMessage(
    signal_id="TEST-20260308-001",
    strategy_name="系统测试",
    symbol="BTC-USD",
    action="BUY",
    direction="LONG",
    price=95000.0,
    timestamp=datetime.now().isoformat(),
    confidence=80.0,
    stop_loss=90000.0,
    take_profit=105000.0,
    risk_reward_ratio=2.0,
    reason="系统连接测试 - 飞书推送功能验证"
)

result = notifier.send_text(test_signal)  # 改用文本消息

if result.get('success'):
    print("✅ 飞书推送成功！")
    print(f"消息 ID: {result.get('message_id')}")
else:
    print(f"❌ 推送失败：{result.get('error')}")

# 再发一个真实信号示例
print("\n📊 发送示例交易信号...")

real_signal = SignalMessage(
    signal_id="SIG-20260308-BTC-MA-001",
    strategy_name="均线交叉",
    symbol="BTC-USD",
    action="BUY",
    direction="LONG",
    price=95234.56,
    timestamp=datetime.now().isoformat(),
    confidence=78.5,
    stop_loss=88000.0,
    take_profit=108000.0,
    risk_reward_ratio=2.3,
    reason="12 日 EMA 上穿 26 日 EMA，价格站稳 200 日均线上方，成交量放大"
)

result2 = notifier.send_text(real_signal)  # 改用文本消息

if result2.get('success'):
    print("✅ 示例信号发送成功！")
    print(f"消息 ID: {result2.get('message_id')}")
else:
    print(f"❌ 发送失败：{result2.get('error')}")

print("\n✅ 测试完成！查看飞书群消息确认。")
