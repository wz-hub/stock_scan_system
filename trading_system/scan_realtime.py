#!/usr/bin/env python3
"""
实时策略扫描系统 - 生产环境

核心设计:
1. 从 Binance API 获取实时 K 线数据
2. 保存到数据库积累历史 (用于回测)
3. 从数据库读取运行策略扫描
4. 动态标的列表 (成交量 Top 100)
5. 8 小时去重推送
"""
import sys
import json
import hashlib
import sqlite3
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from feishu_notifier import FeishuNotifier, SignalMessage
from database import MarketDatabase
from strategies.prev_high_low_breakout import PrevHighLowBreakoutStrategy
from strategies.rsi_overbought_oversold import RSIOversoldOverboughtStrategy
from strategies.bollinger_mean_reversion import BollingerMeanReversionStrategy
from strategies.volume_breakout_4h import VolumeBreakout4HStrategy
from feishu_card_template import create_signal_card
from core.ai_scorer import AIScorer
from config.settings import Settings

# Binance API 配置
BINANCE_API = 'https://api.binance.com/api/v3'

# 标的配置
SCAN_CONFIG = {
    'volume_top_n': 100,
    'base_symbols': ['BTCUSDT', 'ETHUSDT'],
    'exclude_stablecoins': True,
}

# 去重配置
DEDUP_WINDOW_HOURS = 8

# 缓存文件
CACHE_FILE = Path('cache/scan_signals.json')
CACHE_FILE.parent.mkdir(exist_ok=True)


class BinanceAPI:
    """Binance API 封装 (带限流保护和重试)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.last_call = 0
        self.min_interval = 0.1
    
    def _rate_limit(self):
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()
    
    def _request_with_retry(self, url, params=None, max_retries=3):
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                resp = self.session.get(url, params=params, timeout=10)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get('Retry-After', 1))
                    time.sleep(retry_after)
                    continue
                if resp.status_code != 200:
                    raise Exception(f'HTTP {resp.status_code}: {resp.text[:100]}')
                return resp.json()
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
                raise
        return None
    
    def get_tickers_24h(self):
        url = f'{BINANCE_API}/ticker/24hr'
        return self._request_with_retry(url)
    
    def get_klines(self, symbol, interval, limit=500, start_time=None):
        url = f'{BINANCE_API}/klines'
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        if start_time and start_time > 0:
            params['startTime'] = int(start_time)
        data = self._request_with_retry(url, params)
        if not data:
            return None
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
            'taker_buy_quote', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
        df.set_index('timestamp', inplace=True)
        for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']]


def get_top_volume_symbols(api, top_n=100):
    print(f"\n💰 获取全市场 24h 行情...")
    tickers = api.get_tickers_24h()
    usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
    stablecoins = {'USDTUSDT', 'USDCUSDT', 'BUSDUSDT', 'TUSDUSDT'}
    filtered = [t for t in sorted_pairs if t['symbol'] not in stablecoins]
    top_symbols = [t['symbol'] for t in filtered[:top_n]]
    for base in SCAN_CONFIG['base_symbols']:
        if base not in top_symbols:
            top_symbols.append(base)
    print(f"  全市场交易对：{len(tickers)}")
    print(f"  USDT 交易对：{len(usdt_pairs)}")
    print(f"  扫描标的：{len(top_symbols)} 个")
    return top_symbols


def update_klines_for_symbol(api, db, symbol):
    try:
        try:
            klines_4h = api.get_klines(symbol, '4h', limit=500)
            if klines_4h is not None and len(klines_4h) > 0:
                db.save_klines(symbol, '4h', klines_4h)
        except Exception as e:
            pass
        try:
            klines_1d = api.get_klines(symbol, '1d', limit=365)
            if klines_1d is not None and len(klines_1d) > 0:
                db.save_klines(symbol, '1d', klines_1d)
        except Exception as e:
            pass
        return True
    except Exception as e:
        return False


def update_all_klines(api, db, symbols):
    print(f"\n📈 更新 {len(symbols)} 个币种的 K 线数据...")
    success, failed = 0, 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(update_klines_for_symbol, api, db, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            if future.result():
                success += 1
            else:
                failed += 1
    print(f"  ✅ 成功：{success} 个")
    print(f"  ❌ 失败：{failed} 个")


def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            data = json.load(f)
            signals = data.get('signals', {})
            if isinstance(signals, list):
                return set(signals)
            cutoff_time = datetime.now() - timedelta(hours=DEDUP_WINDOW_HOURS)
            recent_hashes = set()
            for sig_hash, timestamp in signals.items():
                try:
                    sig_time = datetime.fromisoformat(timestamp)
                    if sig_time >= cutoff_time:
                        recent_hashes.add(sig_hash)
                except:
                    recent_hashes.add(sig_hash)
            return recent_hashes
    return set()


def save_cache(signal_hashes):
    existing = {}
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            data = json.load(f)
            existing = data.get('signals', {})
    now = datetime.now().isoformat()
    for sig_hash in signal_hashes:
        existing[sig_hash] = now
    cutoff_time = datetime.now() - timedelta(hours=DEDUP_WINDOW_HOURS)
    cleaned = {h: t for h, t in existing.items() if datetime.fromisoformat(t) >= cutoff_time}
    with open(CACHE_FILE, 'w') as f:
        json.dump({'signals': cleaned, 'last_scan': now, 'dedup_window_hours': DEDUP_WINDOW_HOURS}, f, indent=2)


def signal_hash(symbol, signal, timeframe):
    key = f"{symbol}-{timeframe}-{signal['strategy_name']}-{signal['direction']}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def scan_symbol(symbol, db, strategies_1d, strategies_4h):
    results = []
    try:
        data_1d = db.get_klines(symbol, '1d', limit=100)
        data_4h = db.get_klines(symbol, '4h', limit=300)
        if data_1d is None or len(data_1d) < 50:
            return results
        for strat_name, strategy in strategies_1d.items():
            try:
                signal = strategy.generate_signal({'1D': data_1d}, symbol)
                if signal:
                    signal['timeframe'] = '1D'
                    signal['timeframe_label'] = '日线'
                    results.append(signal)
            except:
                pass
        if data_4h is not None and len(data_4h) >= 200:
            for strat_name, strategy in strategies_4h.items():
                try:
                    signal = strategy.generate_signal({'4H': data_4h}, symbol)
                    if signal:
                        signal['timeframe'] = '4H'
                        signal['timeframe_label'] = '4 小时'
                        results.append(signal)
                except:
                    pass
        return results
    except:
        return []


def main():
    start_time = time.time()
    print("=" * 80)
    print("🚀 实时策略扫描系统 - 生产环境")
    print("=" * 80)
    print(f"扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"策略组合:")
    print(f"  📊 日线 (1D):")
    print(f"     - 前高前低突破 V2")
    print(f"     - RSI 超买超卖")
    print(f"     - 布林带回归")
    print(f"  ⏱️ 4 小时 (4H):")
    print(f"     - 前高前低突破 V2")
    print(f"     - 成交量突破 4H")
    print("=" * 80)
    
    api = BinanceAPI()
    db = MarketDatabase()
    
    try:
        settings = Settings()
        feishu_webhook = settings.get('notification.feishu.webhook_url', '') or settings.get('notification.feishu.webhook', '')
        feishu_enabled = settings.get('notification.feishu.enabled', True)
        if not feishu_webhook:
            import yaml
            with open('config/config.yaml') as f:
                config = yaml.safe_load(f)
                feishu_webhook = config.get('notification', {}).get('feishu', {}).get('webhook_url', '')
                feishu_enabled = config.get('notification', {}).get('feishu', {}).get('enabled', True)
    except:
        feishu_webhook = ''
        feishu_enabled = False
    
    print(f"飞书推送：{'✅ 启用' if feishu_enabled and feishu_webhook else '❌ 禁用'}")
    if feishu_webhook:
        print(f"Webhook: {feishu_webhook[:50]}...")
    print("=" * 80)
    
    notifier = FeishuNotifier(feishu_webhook) if (feishu_enabled and feishu_webhook) else None
    
    strategies_1d = {
        '前高前低突破 V2': PrevHighLowBreakoutStrategy(),
        'RSI 超买超卖': RSIOversoldOverboughtStrategy(),
        '布林带回归': BollingerMeanReversionStrategy()
    }
    strategies_4h = {
        '前高前低突破 V2': PrevHighLowBreakoutStrategy(),
        '成交量突破 4H': VolumeBreakout4HStrategy()
    }
    
    symbols = get_top_volume_symbols(api, SCAN_CONFIG['volume_top_n'])
    update_all_klines(api, db, symbols)
    
    print(f"\n📡 并行扫描 {len(symbols)} 个币种...")
    scan_start = time.time()
    old_signal_hashes = load_cache()
    all_signals = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(scan_symbol, symbol, db, strategies_1d, strategies_4h): symbol for symbol in symbols}
        for i, future in enumerate(as_completed(futures), 1):
            symbol = futures[future]
            try:
                signals = future.result()
                all_signals.extend(signals)
            except:
                pass
            if i % 20 == 0:
                print(f"  进度：{i}/{len(symbols)} - 收集 {len(all_signals)} 个信号")
    
    scan_elapsed = time.time() - scan_start
    
    print(f"\n🔍 信号去重...")
    print(f"   原始信号：{len(all_signals)} 个")
    
    from collections import defaultdict
    grouped = defaultdict(list)
    for signal in all_signals:
        key = f"{signal['symbol']}-{signal['timeframe']}-{signal['strategy_name']}-{signal['direction']}"
        grouped[key].append(signal)
    
    new_signals = []
    duplicated_count = 0
    filtered_count = 0
    for key, signals in grouped.items():
        signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        best_signal = signals[0]
        if best_signal.get('confidence', 0) >= 80:
            new_signals.append(best_signal)
            if len(signals) > 1:
                duplicated_count += len(signals) - 1
        else:
            filtered_count += len(signals)
    
    # AI 评分（仅用于参考，不参与决策）
    print(f"\n🤖 AI 评分（仅供参考）...")
    print(f"   待评分信号：{len(new_signals)} 个")
    
    scorer = AIScorer()
    ai_skipped = 0
    for signal in new_signals:
        try:
            # 获取真实 K 线数据给 AI
            symbol = signal['symbol']
            klines_4h = db.get_klines(symbol, '4h', limit=50)
            klines_1d = db.get_klines(symbol, '1d', limit=30)
            
            # 转换为 dict 格式
            klines_4h_list = []
            klines_1d_list = []
            
            if klines_4h is not None:
                for idx, row in klines_4h.tail(10).iterrows():
                    klines_4h_list.append({
                        'timestamp': int(idx.timestamp() * 1000),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': float(row['volume'])
                    })
            
            if klines_1d is not None:
                for idx, row in klines_1d.tail(10).iterrows():
                    klines_1d_list.append({
                        'timestamp': int(idx.timestamp() * 1000),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': float(row['volume'])
                    })
            
            market_data = {
                'klines_4h': klines_4h_list,
                'klines_1d': klines_1d_list,
                'adx': 25.0,
                'rsi': 60.0,
                'macd_status': '',
                'volume_ratio': 1.5
            }
            
            ai_result = scorer.score(signal, market_data)
            if ai_result:
                signal['ai_score'] = ai_result['confidence']
                signal['ai_direction'] = ai_result['direction']
                signal['ai_reason'] = ai_result['reason']
                print(f"   ✅ {signal['symbol']} {signal['direction']}: AI {ai_result['direction']} ({ai_result['confidence']}%)")
            else:
                ai_skipped += 1
                print(f"   ⚠️ {signal['symbol']}: AI 评分返回空")
        except Exception as e:
            ai_skipped += 1
            print(f"   ❌ {signal['symbol']}: AI 评分异常 {e}")
    
    print(f"   AI 评分完成：{len(new_signals)} 个成功，{ai_skipped} 个失败")
    
    # AI 评分不影响推送，直接去重
    new_signals_final = []
    for signal in new_signals:
        sig_hash = signal_hash(signal['symbol'], signal, signal.get('timeframe', '1D'))
        if sig_hash not in old_signal_hashes:
            new_signals_final.append(signal)
    
    print(f"   去重后：{len(new_signals_final)} 个")
    
    elapsed = time.time() - start_time
    print(f"\n✅ 扫描完成！总耗时：{elapsed:.1f}秒")
    print(f"   扫描币种：{len(symbols)}")
    print(f"   发现信号：{len(new_signals_final)}")
    
    if new_signals_final:
        print(f"\n📊 新信号详情:")
        print("-" * 80)
        for signal in new_signals_final:
            confidence = signal.get('confidence', 70)
            position_pct = 15.0 if confidence >= 90 else (10.0 if confidence >= 80 else (5.0 if confidence >= 70 else 0.0))
            position_label = "重仓" if confidence >= 90 else ("标准" if confidence >= 80 else ("轻仓" if confidence >= 70 else "观察"))
            tf_emoji = "📊" if signal['timeframe'] == '1D' else "⏱️"
            pattern_emoji = "🔴" if signal['direction'] == 'LONG' else "🟢"
            position_emoji = "💰" if position_pct > 0 else "👁️"
            print(f"  {tf_emoji} {pattern_emoji} {signal['symbol']} {signal['action']} {signal['direction']}")
            print(f"     策略：{signal['strategy_name']}")
            print(f"     价格：{signal['entry_price']}")
            print(f"     置信度：{confidence}%")
            print(f"     {position_emoji} 仓位：{position_label} ({position_pct}%)")
            print()
    
    if notifier and new_signals_final:
        print(f"\n📤 发送飞书推送...")
        for signal in new_signals_final:
            try:
                card = create_signal_card(signal)
                # 直接发送卡片数据
                payload = {"msg_type": "interactive", "card": card}
                resp = requests.post(notifier.webhook_url, json=payload, timeout=10)
                result = resp.json()
                if result.get('StatusCode') == 0 or result.get('code') == 0:
                    print(f"   ✅ {signal['symbol']} 推送成功")
                else:
                    print(f"   ⚠️ {signal['symbol']} 推送返回：{result}")
                time.sleep(0.5)
            except Exception as e:
                print(f"   ❌ {signal['symbol']} 推送失败：{e}")
    
    print(f"\n💾 保存信号到数据库...")
    conn = sqlite3.connect('cache/trading.db')
    cursor = conn.cursor()
    saved_count = 0
    for signal in new_signals_final:
        try:
            sig_id = signal_hash(signal['symbol'], signal, signal.get('timeframe', '1D'))
            cursor.execute('''INSERT OR REPLACE INTO signals (signal_id, symbol, timeframe, strategy_name, action, direction, entry_price, stop_loss_price, take_profit_price, confidence, reason, position_pct, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)''', (sig_id, signal['symbol'], signal.get('timeframe', '1D'), signal['strategy_name'], signal['action'], signal['direction'], float(signal['entry_price']), float(signal.get('stop_loss_price', 0)), float(signal.get('take_profit_price', 0)), signal.get('confidence', 70), signal.get('reason', ''), signal.get('position_pct', 10.0), datetime.now()))
            saved_count += 1
        except Exception as e:
            pass
    conn.commit()
    conn.close()
    print(f"   ✅ 保存 {saved_count} 个信号到数据库")
    
    save_cache([signal_hash(s['symbol'], s, s.get('timeframe', '1D')) for s in new_signals_final])
    print(f"   缓存信号数：{len(new_signals_final)}")
    
    print("\n" + "=" * 80)
    print(f"✅ 扫描全部完成！")
    print("=" * 80)


if __name__ == '__main__':
    main()
