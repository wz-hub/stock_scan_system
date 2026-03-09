#!/usr/bin/env python3
"""
信号监控脚本 - 每 5 分钟运行
- 更新活跃信号价格
- 计算盈亏
- 检查止盈止损
- 自动平仓并推送通知
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from signal_tracker import SignalTracker
from realtime_data import RealtimeData
from feishu_notifier import FeishuNotifier

# 加载配置
config_file = Path('config/notification.json')
if config_file.exists():
    with open(config_file) as f:
        config = json.load(f)
else:
    config = {}

feishu_config = config.get('feishu', {})
tracking_config = config.get('signal_tracking', {})

webhook_url = feishu_config.get('webhook_url', '')
enabled = tracking_config.get('enabled', True)
notify_on_exit = tracking_config.get('notify_on_exit', False)

print("="*80)
print("🔍 信号监控")
print("="*80)
print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"追踪状态：{'✅ 已启用' if enabled else '❌ 已禁用'}")
print(f"平仓通知：{'✅ 已启用' if notify_on_exit else '❌ 已禁用'}")
print("="*80)

if not enabled:
    print("⚠️ 追踪已禁用，跳过")
    sys.exit(0)

# 初始化
tracker = SignalTracker()
rt = RealtimeData()
notifier = FeishuNotifier(webhook_url) if webhook_url else None

# 获取活跃信号
active_signals = tracker.get_active_signals()
print(f"\n活跃信号：{len(active_signals)} 个")

if not active_signals:
    print("✅ 无活跃信号")
    tracker.close()
    sys.exit(0)

# 更新价格和检查平仓
print("\n检查平仓条件...")
closed_signals = tracker.check_exit_conditions()

if closed_signals:
    print(f"平仓信号：{len(closed_signals)} 个")
    
    # 推送平仓通知
    if notify_on_exit and notifier:
        for closed in closed_signals:
            emoji = "🎯" if closed['exit_reason'] == 'TAKE_PROFIT' else "❌"
            reason_cn = "止盈" if closed['exit_reason'] == 'TAKE_PROFIT' else "止损"
            
            message = f"""
{emoji}【{reason_cn}通知】{closed['symbol']}

策略：{closed['strategy']}
方向：{'做空' if 'SELL' in closed.get('action', '') else '做多'}
平仓价：${closed['exit_price']:.4f}
原因：{closed['exit_reason']}

时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━
"""
            try:
                result = notifier.send_text(message)
                if result.get('success'):
                    print(f"  ✅ 推送平仓通知：{closed['symbol']}")
                else:
                    print(f"  ❌ 推送失败：{result}")
            except Exception as e:
                print(f"  ❌ 推送异常：{e}")
else:
    print("✅ 无平仓信号")

# 统计
stats = tracker.get_stats(days=7)
print(f"\n📊 近 7 天统计:")
print(f"  总信号：{stats.get('total_signals', 0)}")
print(f"  活跃：{stats.get('active_signals', 0)}")

closed_stats = stats.get('closed_signals', {})
if closed_stats:
    print(f"  止盈：{closed_stats.get('TAKE_PROFIT', {}).get('count', 0)}")
    print(f"  止损：{closed_stats.get('STOP_LOSS', {}).get('count', 0)}")

tracker.close()
print("\n" + "="*80)
print("✅ 监控完成")
print("="*80)
