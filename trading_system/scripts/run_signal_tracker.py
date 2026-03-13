#!/usr/bin/env python3
"""
信号跟踪守护进程
每 5 分钟检查一次止盈止损
"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from signal_tracker import SignalTracker
from feishu_notifier import FeishuNotifier
from config.settings import Settings

def main():
    """主循环"""
    print("=" * 80)
    print("🎯 信号跟踪守护进程")
    print("=" * 80)
    print(f"启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("检查间隔：5 分钟")
    print("=" * 80)
    
    # 初始化
    tracker = SignalTracker()
    
    # 加载飞书配置
    try:
        settings = Settings()
        webhook = settings.get('notification.feishu.webhook_url', '')
        notifier = FeishuNotifier(webhook) if webhook else None
        print(f"飞书推送：{'✅ 启用' if notifier else '❌ 禁用'}")
    except:
        notifier = None
        print("⚠️ 飞书配置加载失败")
    
    print("=" * 80)
    
    # 主循环
    check_interval = 300  # 5 分钟
    
    while True:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始检查...")
            
            # 检查平仓条件
            closed_signals = tracker.check_exit_conditions()
            
            if closed_signals:
                print(f"  ✅ 发现 {len(closed_signals)} 个平仓信号:")
                for sig in closed_signals:
                    print(f"    - {sig['symbol']} ({sig['strategy']}): {sig['exit_reason']} @ {sig['exit_price']}")
                    
                    # 发送飞书推送
                    if notifier:
                        try:
                            from feishu_card_template import create_signal_card
                            # 构造平仓信号
                            exit_signal = {
                                'symbol': sig['symbol'].replace('USDT', '-USD'),
                                'action': 'CLOSE',
                                'direction': sig.get('direction', 'LONG'),
                                'entry_price': sig.get('entry_price', 0),
                                'exit_price': sig['exit_price'],
                                'strategy_name': sig['strategy'],
                                'reason': f"平仓：{sig['exit_reason']}"
                            }
                            card = create_signal_card(exit_signal)
                            notifier.send_card(card)
                            print(f"      📤 飞书推送成功")
                        except Exception as e:
                            print(f"      ⚠️ 飞书推送失败：{e}")
            else:
                print(f"  ℹ️ 无平仓信号")
            
            # 显示活跃信号
            active = tracker.get_active_signals()
            if active:
                print(f"  📊 当前活跃信号：{len(active)} 个")
                for sig in active[:5]:  # 只显示前 5 个
                    pnl = sig.get('pnl_pct', 0)
                    pnl_icon = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                    print(f"    {pnl_icon} {sig['symbol']} {sig['direction']}: {pnl:+.2f}%")
            
            # 等待下次检查
            print(f"  ⏱️  下次检查：{check_interval // 60} 分钟后")
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  收到中断信号，退出...")
            break
        except Exception as e:
            print(f"  ❌ 错误：{e}")
            time.sleep(60)  # 出错后等待 1 分钟

if __name__ == '__main__':
    main()
