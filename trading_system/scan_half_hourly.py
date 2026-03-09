#!/usr/bin/env python3
"""
全市场信号扫描 - 半小时版
- 每半小时扫描一次
- 只推送新信号（去重）
- 无信号时不推送
"""
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from signal_generator import SignalGenerator
from realtime_data import RealtimeData
from money_flow import MoneyFlowMonitor
from feishu_notifier import FeishuNotifier

# 缓存文件
CACHE_FILE = Path('cache/last_signals.json')
CACHE_FILE.parent.mkdir(exist_ok=True)

# 缓存过期时间（小时）
CACHE_EXPIRY_HOURS = 24

# 加载扫描配置
scan_config_file = Path('config/scan_config.json')
if scan_config_file.exists():
    with open(scan_config_file) as f:
        scan_config = json.load(f)
else:
    scan_config = {
        "scan_symbols": {
            "volume_top_n": 100,
            "money_flow_inflow_top": 20,
            "money_flow_outflow_top": 20
        }
    }

# 加载通知配置
notification_config_file = Path('config/notification.json')
if notification_config_file.exists():
    with open(notification_config_file) as f:
        notification_config = json.load(f)
else:
    notification_config = {"feishu": {"webhook_url": "", "enabled": False}}

scan_symbols_config = scan_config.get('scan_symbols', {})
feishu_config = notification_config.get('feishu', {})
filters_config = notification_config.get('filters', {})

volume_top_n = scan_symbols_config.get('volume_top_n', 100)
inflow_top = scan_symbols_config.get('money_flow_inflow_top', 20)
outflow_top = scan_symbols_config.get('money_flow_outflow_top', 20)
base_symbols = scan_symbols_config.get('base_symbols', ['BTCUSDT', 'ETHUSDT'])
min_confidence = filters_config.get('min_confidence', 60)
feishu_webhook = feishu_config.get('webhook_url', '')

print("📊 全市场信号扫描 - 半小时版")
print("="*80)
print(f"扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"扫描策略:")
print(f"  - 成交量 Top{volume_top_n}")
print(f"  - 资金流入 Top{inflow_top}")
print(f"  - 资金流出 Top{outflow_top}")
print(f"最低置信度：{min_confidence}%")
print("="*80)

# 加载缓存
def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {'signals': [], 'last_scan': None}

def save_cache(data):
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def signal_hash(signal_dict):
    """生成信号唯一标识"""
    key = f"{signal_dict['symbol']}-{signal_dict['strategy_name']}-{signal_dict['action']}-{signal_dict['direction']}"
    return hashlib.md5(key.encode()).hexdigest()[:12]

cache = load_cache()
# 兼容旧缓存格式
cached_signals = cache.get('signals', [])
if cached_signals and isinstance(cached_signals[0], str):
    # 旧格式：直接是 hash 列表
    old_signal_hashes = set(cached_signals)
else:
    # 新格式：字典列表
    old_signal_hashes = {s['hash'] for s in cached_signals if isinstance(s, dict)}

# 获取成交量 Top100
print(f"\n📊 获取成交量 Top{volume_top_n}...")
rt = RealtimeData()
volume_symbols = rt.get_top_volume_symbols(limit=volume_top_n)
print(f"  获取到 {len(volume_symbols)} 个币种")

# 获取资金流向数据
print(f"\n💰 获取资金流向数据...")
flow_monitor = MoneyFlowMonitor()
flow_ranking = flow_monitor.get_money_flow_ranking(top_n=50)

# 构建扫描列表
scan_symbols = set(base_symbols)

# 添加成交量 Top100
for symbol in volume_symbols:
    scan_symbols.add(symbol)

# 添加流入 Top20
print(f"\n🟢 资金流入 Top{inflow_top}:")
for i, item in enumerate(flow_ranking['inflow_top20'][:inflow_top], 1):
    scan_symbols.add(item['symbol'])
    print(f"  {i}. {item['symbol_short']} (+${item['net_flow']/1e6:.1f}M)")

# 添加流出 Top20
print(f"\n🔴 资金流出 Top{outflow_top}:")
for i, item in enumerate(flow_ranking['outflow_top20'][:outflow_top], 1):
    scan_symbols.add(item['symbol'])
    print(f"  {i}. {item['symbol_short']} (-${abs(item['net_flow'])/1e6:.1f}M)")

print(f"\n✅ 扫描标的统计:")
print(f"   去重后总计：{len(scan_symbols)}")
print("\n" + "="*80)

# 生成信号
generator = SignalGenerator(capital=100000, enable_notification=False)  # 关闭自动通知，手动控制

total_signals = 0
new_signals = []
repeated_signals = []
scanned_count = 0
mtf_signals_count = 0

# 加载飞书通知
feishu_webhook = config.get('feishu_webhook', '')
notifier = FeishuNotifier(feishu_webhook) if feishu_webhook else None

# 先扫描多周期策略
print(f"\n📡 扫描多周期共振策略...")
for i, symbol in enumerate(sorted(scan_symbols), 1):
    try:
        mtf_signal = generator.scan_multi_timeframe(symbol, rt)
        if mtf_signal:
            signal_dict = mtf_signal.to_dict()
            sig_hash = signal_hash(signal_dict)
            
            # 检查置信度
            if signal_dict['confidence'] < min_confidence:
                continue
            
            total_signals += 1
            
            # 检查是否重复
            if sig_hash in old_signal_hashes:
                repeated_signals.append(signal_dict)
            else:
                new_signals.append(signal_dict)
                mtf_signals_count += 1
    except Exception as e:
        pass
    
    import time
    time.sleep(0.3)

print(f"  多周期信号：{mtf_signals_count} 个新信号")

# 扫描其他策略
print(f"\n📊 扫描其他策略...")
for i, symbol in enumerate(sorted(scan_symbols), 1):
    print(f"\n[{i}/{len(scan_symbols)}] 扫描 {symbol}...")
    scanned_count += 1
    
    try:
        df = rt.get_binance_klines(symbol, interval='1d', limit=500)
        
        if df.empty:
            continue
        
        symbol_short = symbol.replace('USDT', '-USD')
        signals = generator.scan_all_strategies(df, symbol_short, scan_last_days=7)
        
        for signal in signals:
            signal_dict = signal.to_dict()
            sig_hash = signal_hash(signal_dict)
            
            # 检查置信度
            if signal_dict['confidence'] < min_confidence:
                continue
            
            total_signals += 1
            
            # 检查是否重复
            if sig_hash in old_signal_hashes:
                repeated_signals.append(signal_dict)
            else:
                new_signals.append(signal_dict)
    
    except Exception as e:
        continue
    
    import time
    time.sleep(0.5)

# 统计
print("\n" + "="*80)
print(f"✅ 扫描完成！")
print(f"   扫描币种：{scanned_count}")
print(f"   发现信号：{total_signals}")
print(f"   └─ 新信号：{len(new_signals)} 个 ⭐")
print(f"   └─ 重复信号：{len(repeated_signals)} 个")

# 推送新信号
if new_signals and notifier:
    print(f"\n📤 推送 {len(new_signals)} 个新信号...")
    
    for signal_dict in new_signals:
        # 重建 Signal 对象
        from signal_generator import Signal
        signal = Signal(**signal_dict)
        message = signal.to_message()
        
        # 推送
        try:
            notifier.send_message(message)
            print(f"  ✅ 推送：{signal_dict['symbol']} {signal_dict['action']}")
        except Exception as e:
            print(f"  ❌ 推送失败：{e}")
        
        import time
        time.sleep(0.5)  # 避免飞书限流
elif new_signals:
    print(f"\n⚠️ 未配置飞书 webhook，跳过推送")
    print(f"   新信号：{len(new_signals)} 个")
else:
    print(f"\n✅ 无新信号，不推送")

# 保存缓存
cache['signals'] = [signal_hash(s) for s in new_signals]
cache['last_scan'] = datetime.now().isoformat()
save_cache(cache)

print(f"\n💾 缓存已保存：{CACHE_FILE}")
print(f"   缓存信号数：{len(cache['signals'])}")

print(f"\n💾 缓存已保存：{CACHE_FILE}")
print("="*80)
