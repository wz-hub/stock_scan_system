#!/usr/bin/env python3
"""
旗形形态策略信号扫描
扫描牛市旗和熊市旗形态
"""
import sys
import json
import hashlib
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

sys.path.insert(0, str(Path(__file__).parent))

from data.binance import BinanceAPI
from feishu_notifier import FeishuNotifier, SignalMessage
from database import MarketDatabase
from strategies.flag_pattern import FlagPatternStrategy
from config.settings import Settings

# 缓存文件
CACHE_FILE = Path('cache/flag_signals.json')
CACHE_FILE.parent.mkdir(exist_ok=True)
CACHE_EXPIRY_HOURS = 24

print("=" * 80)
print("🚩 旗形形态策略信号扫描")
print("=" * 80)
print(f"扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
print(f"策略：Flag Pattern (旗形形态)")
print(f"  - 牛市旗 (Bull Flag): 急涨 → 回调 → 突破")
print(f"  - 熊市旗 (Bear Flag): 急跌 → 反弹 → 突破")
print("=" * 80)

# 加载配置
try:
    settings = Settings()
    volume_top_n = settings.get('scanner.symbols.volume_top_n', 100)
    feishu_webhook = settings.get('notification.feishu.webhook', '')
    feishu_enabled = settings.get('notification.feishu.enabled', True)
except:
    volume_top_n = 100
    feishu_webhook = ''
    feishu_enabled = False

print(f"扫描币种：Top {volume_top_n}")
print(f"飞书推送：{'✅ 启用' if feishu_enabled and feishu_webhook else '❌ 禁用'}")
print("=" * 80)

# 初始化组件
db = MarketDatabase()
api = BinanceAPI()
strategy = FlagPatternStrategy()
notifier = FeishuNotifier(feishu_webhook) if (feishu_enabled and feishu_webhook) else None

# 获取扫描标的
print("\n💰 获取扫描标的...")
try:
    symbols = api.get_top_volume_symbols(volume_top_n)
    print(f"  获取到 {len(symbols)} 个交易对")
except Exception as e:
    print(f"  ⚠️  获取交易对失败：{e}")
    symbols = ['BTCUSDT', 'ETHUSDT', 'BCHUSDT', 'XRPUSDT', 'DOGEUSDT']
    print(f"  使用默认交易对：{len(symbols)} 个")

# 加载缓存
def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            data = json.load(f)
            return data.get('signals', [])
    return []

def save_cache(signal_hashes):
    with open(CACHE_FILE, 'w') as f:
        json.dump({
            'signals': signal_hashes,
            'last_scan': datetime.now().isoformat()
        }, f, indent=2)

def signal_hash(symbol, signal):
    """生成信号唯一标识"""
    key = f"{symbol}-{signal['action']}-{signal['direction']}-{signal['pattern']}"
    return hashlib.md5(key.encode()).hexdigest()[:12]

def scan_symbol(symbol):
    """扫描单个币种"""
    try:
        # 获取日线数据
        data_1d = api.get_klines(symbol, '1D', limit=50)
        
        if data_1d is None or len(data_1d) < 30:
            return None
        
        # 生成信号
        signal = strategy.generate_signal({'1D': data_1d}, symbol)
        
        return signal
    except Exception as e:
        return None

# 并行扫描
print(f"\n📡 并行扫描 {len(symbols)} 个币种...")
start_time = time.time()

old_signal_hashes = set(load_cache())
new_signals = []
repeated_signals = []

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(scan_symbol, symbol): symbol for symbol in symbols}
    
    for i, future in enumerate(as_completed(futures), 1):
        symbol = futures[future]
        try:
            signal = future.result()
            
            if signal:
                sig_hash = signal_hash(symbol, signal)
                
                if sig_hash in old_signal_hashes:
                    repeated_signals.append(signal)
                else:
                    new_signals.append(signal)
                    
        except Exception as e:
            pass
        
        if i % 20 == 0:
            print(f"  进度：{i}/{len(symbols)} - 发现 {len(new_signals)} 个新信号")

elapsed = time.time() - start_time

print(f"\n✅ 扫描完成！总耗时：{elapsed:.1f}秒")
print(f"   扫描币种：{len(symbols)}")
print(f"   发现信号：{len(new_signals) + len(repeated_signals)}")
print(f"   └─ 新信号：{len(new_signals)} 个 ⭐")
print(f"   └─ 重复信号：{len(repeated_signals)} 个")

# 显示信号详情
if new_signals:
    print(f"\n📊 新信号详情:")
    print("-" * 80)
    for signal in new_signals:
        pattern_emoji = "🐂" if signal['pattern'] == 'Bull Flag' else "🐻"
        print(f"  {pattern_emoji} {signal['symbol']} {signal['action']} {signal['direction']}")
        print(f"     形态：{signal['pattern']}")
        print(f"     价格：{signal['entry_price']}")
        print(f"     止损：{signal['stop_loss_price']} ({signal['stop_loss_pct']}%)")
        print(f"     止盈：{signal['take_profit_price']} ({signal['take_profit_pct']}%)")
        print(f"     盈亏比：{signal['risk_reward_ratio']:.1f}:1")
        print(f"     置信度：{signal['confidence']:.0f}%")
        print(f"     理由：{signal['reason']}")
        if 'pattern_details' in signal:
            details = signal['pattern_details']
            print(f"     旗杆：{details.get('pole_change_pct', 0):.1f}% | 回调：{details.get('flag_retrace_pct', 0):.1f}% | 突破：{details.get('breakout_strength', 0):.2f}%")
        print()

# 推送新信号
if new_signals and notifier:
    print(f"\n📤 推送 {len(new_signals)} 个新信号...")
    
    for signal in new_signals:
        try:
            signal_msg = SignalMessage(
                signal_id=signal_hash(signal['symbol'], signal),
                strategy_name=signal['strategy_name'],
                symbol=signal['symbol'],
                action=signal['action'],
                direction=signal['direction'],
                entry_price=float(signal['entry_price']),
                stop_loss=float(signal['stop_loss_price']),
                take_profit=float(signal['take_profit_price']),
                risk_reward_ratio=signal['risk_reward_ratio'],
                confidence=signal['confidence'],
                reason=signal['reason'],
                timestamp=signal['timestamp']
            )
            
            notifier.send_card(signal_msg.to_feishu_card())
            print(f"  ✅ {signal['symbol']} {signal['action']}")
        except Exception as e:
            print(f"  ❌ {signal['symbol']} 推送失败：{e}")
elif new_signals:
    print(f"\n⚠️  未配置飞书 webhook，跳过推送")

# 保存信号到数据库
print(f"\n💾 保存信号到数据库...")
for signal in new_signals:
    try:
        sig_hash = signal_hash(signal['symbol'], signal)
        db.save_signal(sig_hash, signal)
    except Exception as e:
        print(f"  ⚠️  {signal['symbol']} 保存失败：{e}")

# 更新缓存
save_cache([signal_hash(s['symbol'], s) for s in new_signals])
print(f"   缓存信号数：{len(new_signals)}")
print(f"   数据库大小：{Path('cache/trading.db').stat().st_size / 1024 / 1024:.2f}MB")

print("\n" + "=" * 80)
print(f"✅ 扫描全部完成！")
print("=" * 80)
