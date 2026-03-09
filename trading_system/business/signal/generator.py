"""
信号生成模块
负责扫描全市场、生成信号、过滤和去重
"""
from typing import List, Dict, Optional, Set
from datetime import datetime
import hashlib


class SignalGenerator:
    """信号生成器"""
    
    def __init__(self, min_confidence: int = 80):
        """
        初始化信号生成器
        
        Args:
            min_confidence: 最小置信度（默认 80）
        """
        self.min_confidence = min_confidence
    
    def scan_all_symbols(self, symbols: List[str], strategies: List) -> List[Dict]:
        """
        扫描所有币种生成信号
        
        Args:
            symbols: 币种列表
            strategies: 策略列表
        
        Returns:
            信号列表
        """
        all_signals = []
        
        for symbol in symbols:
            for strategy in strategies:
                try:
                    signal = strategy.generate_signal(symbol)
                    if signal:
                        all_signals.append(signal)
                except Exception as e:
                    # 策略执行失败，记录日志但不中断
                    print(f"策略 {strategy.get_name()} 扫描 {symbol} 失败：{e}")
        
        return all_signals
    
    def filter_signals(self, signals: List[Dict], min_confidence: int = None) -> List[Dict]:
        """
        过滤低置信度信号
        
        Args:
            signals: 信号列表
            min_confidence: 最小置信度（使用实例值或传入值）
        
        Returns:
            过滤后的信号列表
        """
        threshold = min_confidence if min_confidence is not None else self.min_confidence
        
        filtered = []
        for signal in signals:
            confidence = signal.get('confidence', 0)
            if confidence >= threshold:
                filtered.append(signal)
        
        return filtered
    
    def deduplicate_signals(self, signals: List[Dict], active_signals: List[Dict]) -> List[Dict]:
        """
        去重信号（同币种同策略平仓前不重复）
        
        Args:
            signals: 新信号列表
            active_signals: 活跃信号列表
        
        Returns:
            去重后的信号列表
        """
        # 生成活跃信号 keys
        active_keys: Set[str] = set()
        for signal in active_signals:
            key = self._generate_signal_key(signal)
            active_keys.add(key)
        
        # 去重
        deduplicated = []
        seen_keys: Set[str] = set()
        
        for signal in signals:
            key = self._generate_signal_key(signal)
            
            # 检查是否有活跃信号
            if key in active_keys:
                print(f"跳过重复信号：{signal['symbol']} ({signal['strategy_name']}) - 已有活跃信号")
                continue
            
            # 检查本次是否已添加
            if key in seen_keys:
                print(f"跳过重复信号：{signal['symbol']} - 本次已添加")
                continue
            
            deduplicated.append(signal)
            seen_keys.add(key)
        
        return deduplicated
    
    def _generate_signal_key(self, signal: Dict) -> str:
        """
        生成信号唯一 key（用于去重）
        
        Args:
            signal: 信号字典
        
        Returns:
            信号 key
        """
        symbol = signal.get('symbol', '')
        strategy = signal.get('strategy_name', '')
        return f"{symbol}-{strategy}"
    
    def signal_hash(self, signal: Dict) -> str:
        """
        生成信号 hash（用于缓存）
        
        Args:
            signal: 信号字典
        
        Returns:
            信号 hash
        """
        key = f"{signal.get('symbol', '')}-{signal.get('strategy_name', '')}-{signal.get('action', '')}-{signal.get('direction', '')}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


class Signal:
    """信号数据类"""
    
    def __init__(
        self,
        signal_id: str,
        symbol: str,
        strategy_name: str,
        action: str,
        direction: str,
        current_price: str,
        confidence: float,
        stop_loss_price: str,
        take_profit_price: str,
        risk_reward_ratio: float,
        position_size_pct: float,
        reason: str,
        timestamp: str = None
    ):
        self.signal_id = signal_id
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.action = action
        self.direction = direction
        self.current_price = current_price
        self.confidence = confidence
        self.stop_loss_price = stop_loss_price
        self.take_profit_price = take_profit_price
        self.risk_reward_ratio = risk_reward_ratio
        self.position_size_pct = position_size_pct
        self.reason = reason
        self.timestamp = timestamp or datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'strategy_name': self.strategy_name,
            'action': self.action,
            'direction': self.direction,
            'current_price': self.current_price,
            'confidence': self.confidence,
            'stop_loss_price': self.stop_loss_price,
            'take_profit_price': self.take_profit_price,
            'risk_reward_ratio': self.risk_reward_ratio,
            'position_size_pct': self.position_size_pct,
            'reason': self.reason,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Signal':
        """从字典创建"""
        return cls(**data)


if __name__ == '__main__':
    # 测试
    print("测试信号生成模块...")
    
    generator = SignalGenerator(min_confidence=80)
    
    # 测试过滤
    test_signals = [
        {'symbol': 'BTC-USD', 'confidence': 85.0},
        {'symbol': 'ETH-USD', 'confidence': 75.0},
        {'symbol': 'XRP-USD', 'confidence': 90.0}
    ]
    
    filtered = generator.filter_signals(test_signals)
    print(f"过滤前：{len(test_signals)} 个")
    print(f"过滤后：{len(filtered)} 个")
    assert len(filtered) == 2, "应该只保留>=80 的信号"
    
    # 测试去重
    active = [
        {'symbol': 'XRP-USD', 'strategy_name': 'Multi-Timeframe'}
    ]
    
    new_signals = [
        {'symbol': 'XRP-USD', 'strategy_name': 'Multi-Timeframe'},
        {'symbol': 'BTC-USD', 'strategy_name': 'Multi-Timeframe'}
    ]
    
    deduplicated = generator.deduplicate_signals(new_signals, active)
    print(f"去重前：{len(new_signals)} 个")
    print(f"去重后：{len(deduplicated)} 个")
    assert len(deduplicated) == 1, "应该去重 1 个"
    
    print("✅ 所有测试通过！")
