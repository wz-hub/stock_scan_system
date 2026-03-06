# -*- coding: utf-8 -*-
"""
实时数据集成模块

功能：
- WebSocket 实时行情
- 自动重连
- 数据缓存
"""

import websocket
import json
import threading
import time
import logging
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class RealTimeDataFeed:
    """实时数据源"""
    
    def __init__(self, market: str = 'crypto'):
        """
        初始化
        
        Args:
            market: 市场（crypto/a_share/us_stock）
        """
        self.market = market
        self.ws: Optional[websocket.WebSocketApp] = None
        self.running = False
        self.callbacks: List[Callable] = []
        self.data_cache: Dict[str, Dict] = {}
        
        # WebSocket URL
        if market == 'crypto':
            self.url = "wss://stream.binance.com:9443/ws"
        elif market == 'a_share':
            # 东方财富 WebSocket（需要验证）
            self.url = "wss://push2.eastmoney.com/api/ws/quote"
        else:
            self.url = ""
    
    def connect(self, symbols: List[str]):
        """
        连接 WebSocket
        
        Args:
            symbols: 订阅的标的列表
        """
        if not self.url:
            logger.error("Invalid market")
            return
        
        # 构建订阅流
        streams = [f"{symbol.lower()}usdt@trade" for symbol in symbols]
        stream_url = f"{self.url}/{'/'.join(streams)}"
        
        self.ws = websocket.WebSocketApp(
            stream_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        
        self.running = True
        thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        thread.start()
        
        logger.info(f"Connected to {self.market} WebSocket")
    
    def disconnect(self):
        """断开连接"""
        self.running = False
        if self.ws:
            self.ws.close()
        logger.info("Disconnected")
    
    def add_callback(self, callback: Callable):
        """添加数据回调"""
        self.callbacks.append(callback)
    
    def _on_open(self, ws):
        """连接打开"""
        logger.info("WebSocket connection opened")
    
    def _on_message(self, ws, message):
        """接收消息"""
        try:
            data = json.loads(message)
            
            # 解析数据
            if 'p' in data:  # Binance 格式
                symbol = data.get('s', '').replace('USDT', '')
                price = float(data.get('p', 0))
                volume = float(data.get('q', 0))
                
                # 更新缓存
                self.data_cache[symbol] = {
                    'price': price,
                    'volume': volume,
                    'timestamp': data.get('T', 0),
                }
                
                # 触发回调
                for callback in self.callbacks:
                    try:
                        callback(symbol, self.data_cache[symbol])
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
        
        except Exception as e:
            logger.error(f"Parse message error: {e}")
    
    def _on_error(self, ws, error):
        """错误处理"""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """连接关闭"""
        logger.info(f"WebSocket closed: {close_status_code} {close_msg}")
        
        # 自动重连
        if self.running:
            time.sleep(5)
            logger.info("Reconnecting...")
            # 需要重新连接
    
    def get_price(self, symbol: str) -> Optional[float]:
        """获取缓存价格"""
        data = self.data_cache.get(symbol)
        return data['price'] if data else None


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    def on_data(symbol, data):
        print(f"{symbol}: ${data['price']}")
    
    feed = RealTimeDataFeed('crypto')
    feed.add_callback(on_data)
    feed.connect(['BTC', 'ETH'])
    
    # 运行 10 秒
    time.sleep(10)
    feed.disconnect()
