"""
Binance API 封装模块

提供统一的 Binance API 访问接口，支持 K 线数据、行情数据获取。
"""

import requests
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import time


class BinanceAPI:
    """Binance API 客户端"""
    
    def __init__(self, base_url: str = None, timeout: int = 10):
        """
        初始化 Binance API 客户端
        
        Args:
            base_url: API 基础 URL，默认使用官方 API
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        # 多个 API 端点用于容错
        self.base_urls = [
            base_url or "https://api.binance.com",
            "https://api1.binance.com",
            "https://api2.binance.com",
            "https://api3.binance.com",
        ]
        self.api_v3 = "/api/v3"
    
    def _request(self, endpoint: str, params: Dict = None, method: str = "GET") -> Optional[Dict]:
        """
        发送 HTTP 请求（带重试机制）
        
        Args:
            endpoint: API 端点
            params: 请求参数
            method: HTTP 方法
        
        Returns:
            响应数据字典，失败返回 None
        """
        for base_url in self.base_urls:
            try:
                url = f"{base_url}{endpoint}"
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                
            except requests.exceptions.RequestException:
                continue
        
        print(f"⚠️ 所有 Binance API 端点都无法访问：{endpoint}")
        return None
    
    def get_klines(
        self, 
        symbol: str, 
        interval: str = "1d", 
        limit: int = 500,
        start_time: int = None,
        end_time: int = None
    ) -> pd.DataFrame:
        """
        获取 K 线数据
        
        Args:
            symbol: 交易对 (BTCUSDT, ETHUSDT)
            interval: 时间周期 (1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            limit: 返回数量 (最多 1000)
            start_time: 起始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
        
        Returns:
            DataFrame，包含 OHLCV 数据
        """
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1000)
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        data = self._request(f"{self.api_v3}/klines", params)
        
        if not data:
            return pd.DataFrame()
        
        # 转换为 DataFrame
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
            'taker_quote_volume', 'ignore'
        ])
        
        # 转换时间戳
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # 转换数值类型
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 
                       'quote_volume', 'taker_buy_volume', 'taker_quote_volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 保留常用列
        return df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']]
    
    def get_ticker_24hr(self, symbol: str = None) -> Dict:
        """
        获取 24 小时行情
        
        Args:
            symbol: 交易对，None 返回所有交易对
        
        Returns:
            行情数据字典
        """
        endpoint = f"{self.api_v3}/ticker/24hr"
        params = {"symbol": symbol.upper()} if symbol else {}
        
        return self._request(endpoint, params) or {}
    
    def get_ticker_price(self, symbol: str = None) -> Dict:
        """
        获取最新价格
        
        Args:
            symbol: 交易对，None 返回所有交易对价格
        
        Returns:
            价格数据字典
        """
        endpoint = f"{self.api_v3}/ticker/price"
        params = {"symbol": symbol.upper()} if symbol else {}
        
        return self._request(endpoint, params) or {}
    
    def get_top_volume_symbols(self, limit: int = 100, exclude_stablecoins: bool = True) -> List[str]:
        """
        获取成交量前 N 的交易对
        
        Args:
            limit: 返回数量
            exclude_stablecoins: 是否排除稳定币
        
        Returns:
            交易对符号列表
        """
        data = self._request(f"{self.api_v3}/ticker/24hr")
        
        if not data:
            return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
        
        # 只保留 USDT 交易对
        usdt_pairs = [item for item in data if item.get('symbol', '').endswith('USDT')]
        
        if not usdt_pairs:
            return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
        
        # 转换为 DataFrame 并排序
        df = pd.DataFrame(usdt_pairs)
        df['quoteVolume'] = pd.to_numeric(df['quoteVolume'], errors='coerce')
        df = df.sort_values('quoteVolume', ascending=False)
        
        # 排除稳定币
        if exclude_stablecoins:
            stablecoins = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'FDUSD', 'USD1']
            df = df[~df['symbol'].str.replace('USDT', '').isin(stablecoins)]
        
        return df.head(limit)['symbol'].tolist()
    
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """
        获取订单簿深度数据
        
        Args:
            symbol: 交易对
            limit: 深度 (5, 10, 20, 50, 100, 500, 1000)
        
        Returns:
            订单簿数据 {bids: [], asks: []}
        """
        params = {"symbol": symbol.upper(), "limit": limit}
        return self._request(f"{self.api_v3}/depth", params) or {}
    
    def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Dict]:
        """
        获取最近成交记录
        
        Args:
            symbol: 交易对
            limit: 数量 (最多 1000)
        
        Returns:
            成交记录列表
        """
        params = {"symbol": symbol.upper(), "limit": min(limit, 1000)}
        return self._request(f"{self.api_v3}/trades", params) or []
    
    def get_server_time(self) -> Optional[int]:
        """
        获取服务器时间
        
        Returns:
            服务器时间戳（毫秒），失败返回 None
        """
        data = self._request(f"{self.api_v3}/time")
        return data.get('serverTime') if data else None
    
    def get_exchange_info(self) -> Dict:
        """
        获取交易所信息
        
        Returns:
            交易所信息字典
        """
        return self._request(f"{self.api_v3}/exchangeInfo") or {}
    
    def symbol_exists(self, symbol: str) -> bool:
        """
        检查交易对是否存在
        
        Args:
            symbol: 交易对符号
        
        Returns:
            True 表示存在
        """
        info = self.get_exchange_info()
        symbols = [s['symbol'] for s in info.get('symbols', [])]
        return symbol.upper() in symbols


# 便捷函数
_client_instance = None

def get_binance_client(base_url: str = None, timeout: int = 10) -> BinanceAPI:
    """
    获取 Binance API 客户端实例（单例模式）
    
    Args:
        base_url: API 基础 URL
        timeout: 请求超时时间
    
    Returns:
        BinanceAPI 实例
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = BinanceAPI(base_url=base_url, timeout=timeout)
    return _client_instance


# 测试
if __name__ == "__main__":
    print("📊 测试 Binance API...")
    
    api = BinanceAPI()
    
    # 测试 K 线数据
    print("\n1. 测试 K 线数据获取...")
    df = api.get_klines("BTCUSDT", interval="1d", limit=10)
    if not df.empty:
        print(f"   ✅ 获取到 {len(df)} 条 K 线")
        print(f"   最新价格：${df['close'].iloc[-1]:,.2f}")
        print(f"   时间范围：{df.index[0]} 至 {df.index[-1]}")
    else:
        print("   ❌ 获取 K 线失败")
    
    # 测试 24 小时行情
    print("\n2. 测试 24 小时行情...")
    ticker = api.get_ticker_24hr("BTCUSDT")
    if ticker:
        print(f"   ✅ BTCUSDT 24h 涨跌：{ticker.get('priceChangePercent', 0):+.2f}%")
        print(f"   24h 成交量：${float(ticker.get('quoteVolume', 0)):,.0f}")
    else:
        print("   ❌ 获取行情失败")
    
    # 测试成交量排行
    print("\n3. 测试成交量排行...")
    top_symbols = api.get_top_volume_symbols(limit=10)
    print(f"   ✅ 成交量 Top10: {', '.join(top_symbols[:5])}...")
    
    # 测试服务器时间
    print("\n4. 测试服务器时间...")
    server_time = api.get_server_time()
    if server_time:
        print(f"   ✅ 服务器时间：{datetime.fromtimestamp(server_time/1000)}")
    else:
        print("   ❌ 获取时间失败")
    
    print("\n✅ Binance API 测试完成！")
