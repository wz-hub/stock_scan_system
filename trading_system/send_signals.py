"""
信号推送 - 使用实时数据扫描并推送到飞书
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from signal_generator import SignalGenerator
from realtime_data import RealtimeData

# 加载实时数据
print("📊 加载实时数据...")
rt = RealtimeData()

# 获取 BTC 实时 K 线（日线，最近 500 天）
df = rt.get_binance_klines('BTCUSDT', interval='1d', limit=500)

if df.empty:
    print("❌ 无法获取实时数据，退出")
    sys.exit(1)

print(f"数据：{len(df)} 行")
print(f"最新价格：${df['close'].iloc[-1]:,.2f}")
print(f"数据范围：{df.index[0]} 至 {df.index[-1]}")

# 生成信号（自动推送）
print("\n🔍 扫描信号...")
generator = SignalGenerator(capital=100000, enable_notification=True)
signals = generator.scan_all_strategies(df, 'BTC-USD', scan_last_days=7)

print(f"\n✅ 生成 {len(signals)} 个信号")

for signal in signals:
    print(f"\n{'='*60}")
    print(f"信号 ID: {signal.signal_id}")
    print(f"策略：{signal.strategy_name}")
    print(f"标的：{signal.symbol}")
    print(f"操作：{signal.action} {signal.direction}")
    print(f"价格：${signal.current_price:,.2f}")
    print(f"置信度：{signal.confidence}%")
    print(f"优先级：{signal.priority}")
    print(f"{'='*60}")

print("\n✅ 完成！检查飞书消息。")
