#!/usr/bin/env python3
"""
测试信号推送
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from feishu_notifier import FeishuNotifier, SignalMessage

# 测试 webhook
webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/555c2a9b-538a-478e-8a4a-9eb3953fe54b"

print("=" * 80)
print("🧪 测试信号推送")
print("=" * 80)
print(f"Webhook: {webhook_url[:60]}...")
print("=" * 80)

# 创建测试信号
test_signal = {
    'signal_id': 'TEST-001',
    'symbol': 'BTC/USDT',
    'strategy_name': 'Multi-Timeframe Resonance',
    'action': 'BUY',
    'direction': 'LONG',
    'entry_price': '67500.00',
    'stop_loss_price': '65000.00',
    'take_profit_price': '72000.00',
    'stop_loss_pct': 3.7,
    'take_profit_pct': 6.7,
    'risk_reward_ratio': 1.8,
    'confidence': 85,
    'reason': '日线趋势向上 + 4H 金叉 + 1H 入场条件满足 → 强共振',
    'timestamp': datetime.now().isoformat()
}

# 创建通知器
notifier = FeishuNotifier(webhook_url)

# 创建信号消息
signal_msg = SignalMessage(
    signal_id=test_signal['signal_id'],
    strategy_name=test_signal['strategy_name'],
    symbol=test_signal['symbol'],
    action=test_signal['action'],
    direction=test_signal['direction'],
    price=float(test_signal['entry_price']),
    stop_loss=float(test_signal['stop_loss_price']),
    take_profit=float(test_signal['take_profit_price']),
    risk_reward_ratio=test_signal['risk_reward_ratio'],
    confidence=test_signal['confidence'],
    reason=test_signal['reason'],
    timestamp=test_signal['timestamp']
)

# 发送推送
print("\n📤 发送测试信号...")
try:
    # send_card 可以直接接收 SignalMessage
    result = notifier.send_card(signal_msg)
    if result:
        print("✅ 推送成功！")
        print(f"信号：{test_signal['symbol']} {test_signal['action']} {test_signal['direction']}")
        print(f"价格：${test_signal['entry_price']}")
        print(f"置信度：{test_signal['confidence']}%")
    else:
        print("❌ 推送失败")
except Exception as e:
    print(f"❌ 推送失败：{e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
