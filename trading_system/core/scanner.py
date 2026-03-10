"""
信号扫描模块 - 从 scan_half_hourly_v3.py 提取
"""
import sys, json, hashlib, pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from signal_generator import SignalGenerator
from realtime_data import RealtimeData
from money_flow import MoneyFlowMonitor
from feishu_notifier import FeishuNotifier, SignalMessage
from database import MarketDatabase


class SignalScanner:
    """信号扫描器 - 全市场信号扫描，支持多线程并行和去重"""
    
    def __init__(self, config_path='config/scan_config.json', notification_path='config/notification.json',
                 cache_file='cache/last_signals.json', cache_expiry_hours=24, min_confidence=60, max_workers=10):
        """初始化扫描器"""
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(exist_ok=True)
        self.cache_expiry_hours = cache_expiry_hours
        self.min_confidence = min_confidence
        self.max_workers = max_workers
        
        # 加载配置
        self.scan_config = self._load_config(config_path)
        self.notification_config = self._load_config(notification_path)
        
        # 初始化组件
        self.db = MarketDatabase()
        self.rt = RealtimeData()
        self.generator = SignalGenerator(capital=100000, enable_notification=False)
        
        # 初始化通知器
        feishu_webhook = self.notification_config.get('feishu', {}).get('webhook_url', '')
        self.notifier = FeishuNotifier(feishu_webhook) if feishu_webhook else None
        
        # 初始化追踪器
        try:
            from signal_tracker import SignalTracker
            self.tracker = SignalTracker()
        except Exception as e:
            print(f"⚠️ 追踪器初始化失败：{e}")
            self.tracker = None
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}
    
    def _load_cache(self) -> dict:
        """加载缓存"""
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                data = json.load(f)
                # 确保 signals 是 hash 列表
                if 'signals' in data and isinstance(data['signals'], list):
                    data['signals'] = [s for s in data['signals'] if isinstance(s, str)]
                return data
        return {'signals': [], 'last_scan': None}
    
    def _save_cache(self, data: dict):
        """保存缓存"""
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _signal_hash(self, signal_dict: dict) -> str:
        """生成信号 hash"""
        key = f"{signal_dict['symbol']}-{signal_dict['strategy_name']}-{signal_dict['action']}-{signal_dict['direction']}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def _get_scan_symbols(self) -> Set[str]:
        """获取扫描标的列表"""
        scan_config = self.scan_config.get('scan_symbols', {})
        volume_top_n = scan_config.get('volume_top_n', 100)
        inflow_top = scan_config.get('money_flow_inflow_top', 20)
        outflow_top = scan_config.get('money_flow_outflow_top', 20)
        base_symbols = scan_config.get('base_symbols', ['BTCUSDT', 'ETHUSDT'])
        
        scan_symbols = set(base_symbols)
        
        # 添加成交量 Top N
        volume_symbols = self.rt.get_top_volume_symbols(limit=volume_top_n)
        scan_symbols.update(volume_symbols)
        
        # 添加资金流向
        flow_monitor = MoneyFlowMonitor()
        flow_ranking = flow_monitor.get_money_flow_ranking(top_n=50)
        
        for item in flow_ranking.get('inflow_top20', [])[:inflow_top]:
            scan_symbols.add(item['symbol'])
        
        for item in flow_ranking.get('outflow_top20', [])[:outflow_top]:
            scan_symbols.add(item['symbol'])
        
        return scan_symbols
    
    def _scan_symbol_strategies(self, args: Tuple) -> Optional[List[dict]]:
        """
        扫描单个币种的所有策略
        
        Args:
            args: (symbol, rt_data, db_instance)
        
        Returns:
            信号列表，如果无信号返回 None
        """
        symbol, rt_data, db_instance = args
        try:
            generator = SignalGenerator()
            signals = []
            
            # 1. 多周期策略
            try:
                mtf_signal = generator.scan_multi_timeframe(symbol, rt_data)
                if mtf_signal and mtf_signal.confidence >= self.min_confidence:
                    signals.append(mtf_signal.to_dict())
            except Exception:
                pass
            
            # 2. 其他策略
            try:
                df = rt_data.get_binance_klines(symbol, interval='1d', limit=500)
                if df is not None and not df.empty:
                    # 强制转换数据类型
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    symbol_short = symbol.replace('USDT', '-USD')
                    strategy_signals = generator.scan_all_strategies(df, symbol_short, scan_last_days=7)
                    for signal in strategy_signals:
                        if signal.confidence >= self.min_confidence:
                            signals.append(signal.to_dict())
            except Exception:
                pass
            
            return signals if signals else None
        except Exception:
            return None
    
    def scan(
        self,
        enable_notification: bool = True
    ) -> Dict:
        """
        执行全市场扫描
        
        Args:
            enable_notification: 是否启用通知
        
        Returns:
            扫描结果字典
        """
        # 加载缓存
        cache = self._load_cache()
        old_signal_hashes = set(cache.get('signals', []))
        
        # 获取扫描列表
        scan_symbols = self._get_scan_symbols()
        
        # 准备扫描任务
        scan_tasks = [(symbol, self.rt, self.db) for symbol in sorted(scan_symbols)]
        
        # 并行扫描
        total_signals = 0
        new_signals = []
        repeated_signals = []
        scanned_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._scan_symbol_strategies, task): task[0] for task in scan_tasks}
            
            for i, future in enumerate(as_completed(futures), 1):
                try:
                    signal_dicts = future.result(timeout=90)
                    scanned_count += 1
                    
                    if signal_dicts:
                        for signal_dict in signal_dicts:
                            sig_hash = self._signal_hash(signal_dict)
                            total_signals += 1
                            
                            if sig_hash in old_signal_hashes:
                                repeated_signals.append(signal_dict)
                            else:
                                new_signals.append(signal_dict)
                except Exception:
                    scanned_count += 1
        
        # 推送新信号
        if new_signals and enable_notification and self.notifier:
            self._push_signals(new_signals)
        
        # 保存缓存
        cache['signals'] = [self._signal_hash(s) for s in new_signals]
        cache['last_scan'] = datetime.now().isoformat()
        self._save_cache(cache)
        
        # 保存数据库
        for signal_dict in new_signals:
            try:
                self.db.save_signal(self._signal_hash(signal_dict), signal_dict)
            except Exception:
                pass
        
        self.db.log_scan(
            symbols_count=scanned_count,
            signals_count=total_signals,
            new_signals_count=len(new_signals),
            duration=0
        )
        
        return {
            'scanned_count': scanned_count,
            'total_signals': total_signals,
            'new_signals': new_signals,
            'repeated_signals': repeated_signals
        }
    
    def _push_signals(self, new_signals: List[dict]):
        """推送新信号"""
        active_keys = set()
        if self.tracker:
            try:
                active_signals = self.tracker.get_active_signals()
                active_keys = {f"{s['symbol']}-{s['strategy_name']}" for s in active_signals}
            except Exception:
                pass
        
        pushed_signals = set()
        for signal_dict in new_signals:
            dedup_key = f"{signal_dict['symbol']}-{signal_dict['strategy_name']}"
            if dedup_key in active_keys or dedup_key in pushed_signals:
                continue
            
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
            try:
                result = self.notifier.send_text(signal_msg)
                if result.get('success'):
                    pushed_signals.add(dedup_key)
                    if self.tracker:
                        try:
                            self.tracker.add_signal(signal_dict)
                        except Exception:
                            pass
            except Exception:
                pass
    
    def close(self):
        """关闭资源"""
        if self.db:
            self.db.close()
        if self.tracker:
            self.tracker.close()
