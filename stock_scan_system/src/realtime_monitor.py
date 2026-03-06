# -*- coding: utf-8 -*-
"""
实时监控模块

功能：
- 价格实时监控
- 成交量异动预警
- 大额转账监控（加密货币）
- 突发新闻推送
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PriceAlert:
    """价格预警配置"""
    symbol: str
    market: str
    target_price: float
    condition: str  # 'above' or 'below'
    triggered: bool = False


@dataclass
class VolumeAlert:
    """成交量异动预警"""
    symbol: str
    market: str
    threshold_multiplier: float  # 阈值倍数（如 3 倍）
    triggered: bool = False


class RealTimeMonitor:
    """实时监控器"""
    
    def __init__(self, data_fetcher, pusher=None):
        """
        初始化监控器
        
        Args:
            data_fetcher: 数据获取器实例
            pusher: 推送器实例（可选）
        """
        self.data_fetcher = data_fetcher
        self.pusher = pusher
        self.price_alerts: List[PriceAlert] = []
        self.volume_alerts: List[VolumeAlert] = []
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.callbacks: List[Callable] = []
        
        # 监控配置
        self.check_interval = 30  # 检查间隔（秒）
        self.volume_window = 20  # 成交量对比窗口（K 线数）
    
    def add_price_alert(self, symbol: str, market: str, target_price: float, condition: str):
        """
        添加价格预警
        
        Args:
            symbol: 股票代码
            market: 市场（a_share/us_stock/crypto）
            target_price: 目标价格
            condition: 条件（'above' 或 'below'）
        """
        alert = PriceAlert(
            symbol=symbol,
            market=market,
            target_price=target_price,
            condition=condition
        )
        self.price_alerts.append(alert)
        logger.info(f"Added price alert: {symbol} {condition} {target_price}")
    
    def add_volume_alert(self, symbol: str, market: str, threshold_multiplier: float = 3.0):
        """
        添加成交量异动预警
        
        Args:
            symbol: 股票代码
            market: 市场
            threshold_multiplier: 阈值倍数（默认 3 倍）
        """
        alert = VolumeAlert(
            symbol=symbol,
            market=market,
            threshold_multiplier=threshold_multiplier
        )
        self.volume_alerts.append(alert)
        logger.info(f"Added volume alert: {symbol} threshold={threshold_multiplier}x")
    
    def add_callback(self, callback: Callable):
        """添加回调函数（触发预警时调用）"""
        self.callbacks.append(callback)
    
    def start(self):
        """启动监控"""
        if self.running:
            logger.warning("Monitor already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Real-time monitor started")
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Real-time monitor stopped")
    
    def _monitor_loop(self):
        """监控主循环"""
        while self.running:
            try:
                # 检查价格预警
                self._check_price_alerts()
                
                # 检查成交量预警
                self._check_volume_alerts()
                
                # 等待下一次检查
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(5)
    
    def _check_price_alerts(self):
        """检查价格预警"""
        for alert in self.price_alerts:
            if alert.triggered:
                continue
            
            # 获取当前价格
            data = self.data_fetcher.fetch_price(alert.symbol, alert.market)
            if not data:
                continue
            
            current_price = data.get('price', 0)
            
            # 检查条件
            triggered = False
            if alert.condition == 'above' and current_price >= alert.target_price:
                triggered = True
            elif alert.condition == 'below' and current_price <= alert.target_price:
                triggered = True
            
            if triggered:
                alert.triggered = True
                message = (
                    f"🚨 价格预警\n"
                    f"标的：{alert.symbol}\n"
                    f"当前价：¥{current_price:.2f}\n"
                    f"触发价：¥{alert.target_price:.2f}\n"
                    f"条件：{alert.condition}"
                )
                logger.warning(message)
                self._trigger_alert(message, {
                    'type': 'price_alert',
                    'symbol': alert.symbol,
                    'current_price': current_price,
                    'target_price': alert.target_price,
                    'condition': alert.condition,
                })
    
    def _check_volume_alerts(self):
        """检查成交量异动"""
        for alert in self.volume_alerts:
            if alert.triggered:
                continue
            
            # 获取历史数据
            history = self.data_fetcher.get_history(alert.symbol, alert.market, days=1)
            if not history or len(history) < self.volume_window:
                continue
            
            current_volume = history[-1].get('volume', 0)
            avg_volume = sum(h.get('volume', 0) for h in history[-self.volume_window:-1]) / self.volume_window
            
            if avg_volume == 0:
                continue
            
            volume_ratio = current_volume / avg_volume
            
            if volume_ratio >= alert.threshold_multiplier:
                alert.triggered = True
                message = (
                    f"📊 成交量异动\n"
                    f"标的：{alert.symbol}\n"
                    f"当前量：{current_volume:,.0f}\n"
                    f"平均量：{avg_volume:,.0f}\n"
                    f"倍数：{volume_ratio:.1f}x"
                )
                logger.warning(message)
                self._trigger_alert(message, {
                    'type': 'volume_alert',
                    'symbol': alert.symbol,
                    'current_volume': current_volume,
                    'avg_volume': avg_volume,
                    'volume_ratio': volume_ratio,
                })
    
    def _trigger_alert(self, message: str, data: Dict):
        """触发预警"""
        # 推送消息
        if self.pusher:
            self.pusher.push(message, title="🚨 实时预警")
        
        # 调用回调函数
        for callback in self.callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        return {
            'running': self.running,
            'price_alerts': len(self.price_alerts),
            'volume_alerts': len(self.volume_alerts),
            'triggered_price': sum(1 for a in self.price_alerts if a.triggered),
            'triggered_volume': sum(1 for a in self.volume_alerts if a.triggered),
            'check_interval': self.check_interval,
        }


class CryptoWhaleMonitor:
    """加密货币大额转账监控"""
    
    def __init__(self, threshold_usd: float = 1000000):
        """
        初始化
        
        Args:
            threshold_usd: 阈值（美元）
        """
        self.threshold_usd = threshold_usd
        self.alerts = []
    
    def check_whale_alerts(self) -> List[Dict]:
        """
        检查大额转账
        
        Returns:
            大额转账列表
        """
        # 简化实现，实际应该对接 Whale Alert API
        logger.info(f"Checking whale alerts (threshold: ${self.threshold_usd:,})")
        return []
    
    def add_alert(self, alert_data: Dict):
        """添加预警记录"""
        self.alerts.append({
            'timestamp': datetime.now(),
            'data': alert_data,
        })
        logger.warning(f"Whale alert: {alert_data}")


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    # 模拟数据获取器
    class MockFetcher:
        def fetch_price(self, symbol, market):
            return {'price': 100.0}
        
        def get_history(self, symbol, market, days):
            return [{'volume': 1000} for _ in range(30)]
    
    # 创建监控器
    fetcher = MockFetcher()
    monitor = RealTimeMonitor(fetcher)
    
    # 添加预警
    monitor.add_price_alert('601138', 'a_share', 30.0, 'above')
    monitor.add_volume_alert('601138', 'a_share', 3.0)
    
    # 启动监控
    monitor.start()
    
    # 运行 10 秒
    time.sleep(10)
    
    # 查看状态
    print(f"Monitor status: {monitor.get_status()}")
    
    # 停止
    monitor.stop()
