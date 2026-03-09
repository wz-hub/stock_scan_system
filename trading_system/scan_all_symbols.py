"""
全市场信号扫描 - 完整版
每小时扫描：
- 成交量 Top100
- 资金流入 Top20
- 资金流出 Top20
总计约 120-140 个币种
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from signal_generator import SignalGenerator
from realtime_data import RealtimeData
from money_flow import MoneyFlowMonitor

# 加载配置
config_file = Path('config/scan_config.json')
if config_file.exists():
    with open(config_file) as f:
        config = json.load(f)
else:
    config = {
        "scan_symbols": {
            "volume_top_n": 100,
            "money_flow_inflow_top": 20,
            "money_flow_outflow_top": 20
        }
    }

scan_config = config.get('scan_symbols', {})
volume_top_n = scan_config.get('volume_top_n', 100)
inflow_top = scan_config.get('money_flow_inflow_top', 20)
outflow_top = scan_config.get('money_flow_outflow_top', 20)
base_symbols = scan_config.get('base_symbols', ['BTCUSDT', 'ETHUSDT'])

print("📊 全市场信号扫描 - 完整版")
print("="*80)
print(f"扫描策略:")
print(f"  - 成交量 Top{volume_top_n}")
print(f"  - 资金流入 Top{inflow_top}")
print(f"  - 资金流出 Top{outflow_top}")
print("="*80)

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
print(f"   基础币种：{len(base_symbols)}")
print(f"   成交量 Top{volume_top_n}: {volume_top_n}")
print(f"   流入 Top{inflow_top}: {inflow_top}")
print(f"   流出 Top{outflow_top}: {outflow_top}")
print(f"   去重后总计：{len(scan_symbols)}")

print("\n" + "="*80)

# 生成信号
generator = SignalGenerator(capital=100000, enable_notification=True)

total_signals = 0
all_signals = []
scanned_count = 0
mtf_signals_count = 0

# 先扫描多周期策略（需要单独获取多周期数据）
print(f"\n📡 扫描多周期共振策略...")
for i, symbol in enumerate(sorted(scan_symbols), 1):
    try:
        mtf_signal = generator.scan_multi_timeframe(symbol, rt)
        if mtf_signal:
            print(f"  [{i}] ✅ {symbol}: {mtf_signal.action} {mtf_signal.direction} (置信度：{mtf_signal.confidence})")
            all_signals.append(mtf_signal)
            total_signals += 1
            mtf_signals_count += 1
    except Exception as e:
        pass
    
    # 避免 API 限流
    import time
    time.sleep(0.3)

print(f"  多周期信号：{mtf_signals_count} 个")

# 扫描其他策略
print(f"\n📊 扫描其他策略...")
for i, symbol in enumerate(sorted(scan_symbols), 1):
    print(f"\n[{i}/{len(scan_symbols)}] 扫描 {symbol}...")
    scanned_count += 1
    
    try:
        # 获取 K 线数据
        df = rt.get_binance_klines(symbol, interval='1d', limit=500)
        
        if df.empty:
            print(f"  ⚠️ 无数据，跳过")
            continue
        
        latest_price = df['close'].iloc[-1]
        print(f"  最新价格：${latest_price:,.2f}")
        
        # 扫描信号
        symbol_short = symbol.replace('USDT', '-USD')
        signals = generator.scan_all_strategies(df, symbol_short, scan_last_days=7)
        
        if signals:
            print(f"  ✅ 发现 {len(signals)} 个信号")
            for signal in signals:
                print(f"    - {signal.strategy_name}: {signal.action} @ ${signal.current_price:,.2f}")
                total_signals += 1
                all_signals.append(signal)
        else:
            print(f"  暂无信号")
    
    except Exception as e:
        print(f"  ❌ 错误：{e}")
        continue
    
    # 避免 API 限流
    time.sleep(0.5)

print("\n" + "="*80)
print(f"✅ 扫描完成！")
print(f"   扫描币种：{scanned_count}")
print(f"   发现信号：{total_signals}")
print(f"   └─ 多周期共振：{mtf_signals_count} 个")
print(f"   └─ 其他策略：{total_signals - mtf_signals_count} 个")

# 保存信号
if all_signals:
    signals_dir = Path('signals')
    signals_dir.mkdir(exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for signal in all_signals:
        signal_file = signals_dir / f"signal_{signal.signal_id}.json"
        with open(signal_file, 'w', encoding='utf-8') as f:
            json.dump(signal.to_dict(), f, indent=2, ensure_ascii=False)
    
    print(f"💾 信号已保存至 signals/ 目录")

print("="*80)
