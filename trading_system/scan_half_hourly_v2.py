#!/usr/bin/env python3
"""
全市场信号扫描 - 优化版（并行扫描 + 缓存）
- 10 线程并行扫描
- K 线数据 5 分钟缓存
- 只推送高置信度信号（>75%）
"""
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

sys.path.insert(0, str(Path(__file__).parent))

from signal_generator import SignalGenerator
from realtime_data import RealtimeData
from money_flow import MoneyFlowMonitor
from feishu_notifier import FeishuNotifier, SignalMessage

# 缓存文件
CACHE_FILE = Path('cache/last_signals.json')
CACHE_FILE.parent.mkdir(exist_ok=True)

# 缓存过期时间（小时）
CACHE_EXPIRY_HOURS = 24

# 导入数据库
from database import MarketDatabase

# 加载配置
scan_config_file = Path('config/scan_config.json')
if scan_config_file.exists():
    with open(scan_config_file) as f:
        scan_config = json.load(f)
else:
    scan_config = {"scan_symbols": {}}

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

print("📊 全市场信号扫描 - 并行优化版")
print("="*80)
print(f"扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"扫描策略:")
print(f"  - 成交量 Top{volume_top_n}")
print(f"  - 资金流入 Top{inflow_top}")
print(f"  - 资金流出 Top{outflow_top}")
print(f"最低置信度：{min_confidence}%")
print(f"扫描线程：10 个并行")
print(f"数据缓存：SQLite 数据库")
print("="*80)

# 加载缓存
def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            data = json.load(f)
            # 清理超过 24 小时的缓存
            cutoff = datetime.now() - timedelta(hours=CACHE_EXPIRY_HOURS)
            if 'signals' in data and isinstance(data['signals'], list):
                # 过滤过期信号
                valid_signals = []
                for sig_hash in data['signals']:
                    if isinstance(sig_hash, str):
                        valid_signals.append(sig_hash)
                data['signals'] = valid_signals
            return data
    return {'signals': [], 'last_scan': None}

def save_cache(data):
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_cached_klines(rt, symbol, interval='1d', limit=200, max_age=300):
    """获取 K 线（带数据库缓存）"""
    # 检查数据库是否有新鲜数据
    if db.is_fresh(symbol, interval, max_age_seconds=max_age):
        df = db.get_klines(symbol, interval, limit=limit)
        if df is not None and len(df) >= limit:
            return df
    
    # 获取新数据
    try:
        df = rt.get_binance_klines(symbol, interval=interval, limit=limit)
        if not df.empty:
            # 保存到数据库
            db.save_klines(symbol, interval, df)
        return df
    except Exception as e:
        return None

def signal_hash(signal_dict):
    """生成信号唯一标识"""
    key = f"{signal_dict['symbol']}-{signal_dict['strategy_name']}-{signal_dict['action']}-{signal_dict['direction']}"
    return hashlib.md5(key.encode()).hexdigest()[:12]

def scan_symbol_mtf(args):
    """扫描单个币种的多周期策略"""
    symbol, rt_data = args
    try:
        generator = SignalGenerator()
        
        # 获取多周期数据（带缓存）
        data_dict = {}
        for tf in ['1d', '4h', '1h']:
            df = get_cached_klines(rt_data, symbol, interval=tf, limit=200)
            if df is None or df.empty:
                return None
            data_dict[tf.upper()] = df
        
        # 生成信号
        signal = generator.scan_multi_timeframe(symbol, rt_data)
        
        if signal and signal.confidence >= min_confidence:
            return signal.to_dict()
        return None
    except Exception as e:
        return None

# 初始化数据库
print(f"\n💾 初始化数据库...")
db = MarketDatabase()

# 加载缓存
cache = load_cache()

# 兼容旧缓存格式
cached_signals = cache.get('signals', [])
if cached_signals and isinstance(cached_signals[0], str):
    old_signal_hashes = set(cached_signals)
else:
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
generator = SignalGenerator(capital=100000, enable_notification=False)

total_signals = 0
new_signals = []
repeated_signals = []
scanned_count = 0
mtf_signals_count = 0

# 加载飞书通知
notifier = FeishuNotifier(feishu_webhook) if feishu_webhook else None

# 并行扫描所有策略
print(f"\n📡 并行扫描全部策略（10 线程）...")
print(f"   策略：13 个（多周期 + 经典 9 个 + 新 3 个）")
start_time = time.time()

def scan_all_strategies_for_symbol(symbol):
    """扫描单个币种的所有策略"""
    try:
        generator = SignalGenerator()
        signals = []
        
        # 1. 多周期策略（需要单独获取数据）
        try:
            mtf_signal = generator.scan_multi_timeframe(symbol, rt)
            if mtf_signal and mtf_signal.confidence >= min_confidence:
                signals.append(mtf_signal.to_dict())
        except Exception as e:
            pass
        
        # 2. 其他策略（需要日 K 数据）
        try:
            df = get_cached_klines(rt, symbol, interval='1d', limit=500)
            if df is not None and not df.empty:
                # 强制转换数据类型，修复类型错误
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                symbol_short = symbol.replace('USDT', '-USD')
                strategy_signals = generator.scan_all_strategies(df, symbol_short, scan_last_days=7)
                for signal in strategy_signals:
                    if signal.confidence >= min_confidence:
                        signals.append(signal.to_dict())
        except Exception as e:
            pass
        
        return signals if signals else None
    except Exception as e:
        return None

# 准备扫描任务
scan_tasks = list(sorted(scan_symbols))

# 并行执行
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(scan_all_strategies_for_symbol, symbol): symbol for symbol in scan_tasks}
    
    for i, future in enumerate(as_completed(futures), 1):
        symbol = futures[future]
        try:
            signal_dicts = future.result(timeout=60)
            scanned_count += 1
            
            if signal_dicts:
                for signal_dict in signal_dicts:
                    sig_hash = signal_hash(signal_dict)
                    total_signals += 1
                    
                    # 检查是否重复
                    if sig_hash in old_signal_hashes:
                        repeated_signals.append(signal_dict)
                    else:
                        new_signals.append(signal_dict)
                        mtf_signals_count += 1
                
                if i % 10 == 0:
                    print(f"  进度：{i}/{len(scan_symbols)} - 发现 {total_signals} 个信号 ({mtf_signals_count} 新)")
        
        except Exception as e:
            scanned_count += 1
            if i % 20 == 0:
                print(f"  进度：{i}/{len(scan_symbols)} - 错误：{e}")

scan_duration = time.time() - start_time
print(f"\n✅ 全部策略扫描完成！")
print(f"   耗时：{scan_duration:.1f}秒")
print(f"   扫描币种：{scanned_count}")
print(f"   发现信号：{total_signals}")
print(f"   └─ 新信号：{mtf_signals_count} 个 ⭐")
print(f"   └─ 重复信号：{len(repeated_signals)} 个")

# 推送新信号
if new_signals and notifier:
    print(f"\n📤 推送 {len(new_signals)} 个新信号...")
    
    for signal_dict in new_signals:
        # 转换为 SignalMessage 格式
        signal_msg = SignalMessage(
            signal_id=signal_dict.get('signal_id', 'UNKNOWN'),
            strategy_name=signal_dict['strategy_name'],
            symbol=signal_dict['symbol'],
            action=signal_dict['action'],
            direction=signal_dict['direction'],
            price=float(signal_dict['current_price']),
            timestamp=signal_dict.get('timestamp', datetime.now().isoformat()),
            confidence=signal_dict.get('confidence', 0),
            stop_loss=float(signal_dict.get('stop_loss_price', 0)),
            take_profit=float(signal_dict.get('take_profit_price', 0)),
            risk_reward_ratio=signal_dict.get('risk_reward_ratio', 2.0),
            reason=signal_dict.get('reason', '')
        )
        
        # 推送
        try:
            result = notifier.send_text(signal_msg)
            if result.get('success'):
                print(f"  ✅ 推送：{signal_dict['symbol']} {signal_dict['action']}")
            else:
                print(f"  ❌ 推送失败：{result}")
        except Exception as e:
            print(f"  ❌ 推送异常：{e}")
        
        time.sleep(0.3)  # 避免飞书限流

elif new_signals:
    print(f"\n⚠️ 未配置飞书 webhook，跳过推送")
    print(f"   新信号：{len(new_signals)} 个")
else:
    print(f"\n✅ 无新信号，不推送")

# 保存缓存和新信号
cache['signals'] = [signal_hash(s) for s in new_signals]
cache['last_scan'] = datetime.now().isoformat()
save_cache(cache)

# 保存信号到数据库
for signal_dict in new_signals:
    db.save_signal(signal_hash(signal_dict), signal_dict)

# 记录扫描日志
db.log_scan(
    symbols_count=scanned_count,
    signals_count=total_signals,
    new_signals_count=mtf_signals_count,
    duration=scan_duration
)

# 打印统计
stats = db.get_scan_stats(days=1)
print(f"\n💾 数据已保存")
print(f"   缓存信号数：{len(cache['signals'])}")
print(f"   平均扫描时间：{stats.get('avg_duration', 0):.1f}秒")
print(f"   数据库大小：{Path(db.db_path).stat().st_size / 1024 / 1024:.2f}MB")
print("="*80)
print(f"\n✅ 扫描完成！总耗时：{scan_duration:.1f}秒")

# 关闭数据库
db.close()
