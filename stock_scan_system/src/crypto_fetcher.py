# -*- coding: utf-8 -*-
"""
加密货币数据获取模块

支持：
- Binance API（主）
- CoinGecko API（备用）
"""

import requests
import time
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CryptoFetcher:
    """加密货币数据获取器"""
    
    def __init__(self):
        self.binance_base = "https://api.binance.com/api/v3"
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.cache = {}
        self.cache_ttl = 60  # 1 分钟缓存（加密货币波动大）
    
    def get_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取加密货币价格
        
        Args:
            symbol: 币种符号（BTC、ETH 等）
            
        Returns:
            价格数据字典
        """
        # 检查缓存
        cache_key = f"crypto:{symbol}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data
        
        # 尝试 Binance
        data = self._fetch_from_binance(symbol)
        if data:
            self.cache[cache_key] = (time.time(), data)
            return data
        
        # 备用 CoinGecko
        data = self._fetch_from_coingecko(symbol)
        if data:
            self.cache[cache_key] = (time.time(), data)
            return data
        
        return None
    
    def _fetch_from_binance(self, symbol: str) -> Optional[Dict]:
        """从 Binance 获取数据"""
        try:
            # 24 小时行情
            url = f"{self.binance_base}/ticker/24hr"
            params = {"symbol": f"{symbol}USDT"}
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            return {
                'symbol': symbol,
                'price': float(data['lastPrice']),
                'change_24h': float(data['priceChangePercent']),
                'volume_24h': float(data['volume']),
                'turnover_24h': float(data['quoteVolume']),
                'high_24h': float(data['highPrice']),
                'low_24h': float(data['lowPrice']),
                'funding_rate': self._get_funding_rate(symbol),
                'timestamp': datetime.now(),
                'source': 'binance'
            }
        except Exception as e:
            logger.error(f"Binance fetch failed for {symbol}: {e}")
            return None
    
    def _fetch_from_coingecko(self, symbol: str) -> Optional[Dict]:
        """从 CoinGecko 获取数据"""
        try:
            coin_id = symbol.lower()
            url = f"{self.coingecko_base}/coins/{coin_id}"
            params = {"localization": "false", "tickers": "false"}
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            market_data = data.get('market_data', {})
            
            return {
                'symbol': symbol,
                'price': market_data.get('current_price', {}).get('usd', 0),
                'change_24h': market_data.get('price_change_percentage_24h', 0),
                'volume_24h': market_data.get('total_volume', {}).get('usd', 0),
                'market_cap': market_data.get('market_cap', {}).get('usd', 0),
                'high_24h': market_data.get('high_24h', {}).get('usd', 0),
                'low_24h': market_data.get('low_24h', {}).get('usd', 0),
                'timestamp': datetime.now(),
                'source': 'coingecko'
            }
        except Exception as e:
            logger.error(f"CoinGecko fetch failed for {symbol}: {e}")
            return None
    
    def _get_funding_rate(self, symbol: str) -> float:
        """获取资金费率（仅 Binance 合约）"""
        try:
            url = f"{self.binance_base}/fundingRate"
            params = {"symbol": f"{symbol}USDT", "limit": 1}
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return float(data[0]['fundingRate'])
        except:
            pass
        return 0.0
    
    def get_top_gainers(self, limit: int = 10) -> List[Dict]:
        """获取 24 小时涨幅榜"""
        try:
            url = f"{self.binance_base}/ticker/24hr"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                # 过滤 USDT 交易对
                usdt_pairs = [x for x in data if x['symbol'].endswith('USDT')]
                # 按涨幅排序
                sorted_data = sorted(usdt_pairs, key=lambda x: float(x['priceChangePercent']), reverse=True)
                
                return [
                    {
                        'symbol': x['symbol'].replace('USDT', ''),
                        'price': float(x['lastPrice']),
                        'change_24h': float(x['priceChangePercent']),
                        'volume_24h': float(x['volume']),
                    }
                    for x in sorted_data[:limit]
                ]
        except Exception as e:
            logger.error(f"Get top gainers failed: {e}")
        return []
    
    def get_top_losers(self, limit: int = 10) -> List[Dict]:
        """获取 24 小时跌幅榜"""
        try:
            url = f"{self.binance_base}/ticker/24hr"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                usdt_pairs = [x for x in data if x['symbol'].endswith('USDT')]
                sorted_data = sorted(usdt_pairs, key=lambda x: float(x['priceChangePercent']))
                
                return [
                    {
                        'symbol': x['symbol'].replace('USDT', ''),
                        'price': float(x['lastPrice']),
                        'change_24h': float(x['priceChangePercent']),
                        'volume_24h': float(x['volume']),
                    }
                    for x in sorted_data[:limit]
                ]
        except Exception as e:
            logger.error(f"Get top losers failed: {e}")
        return []
    
    def get_whale_alerts(self, threshold_usd: float = 1000000) -> List[Dict]:
        """
        获取大额转账预警（简化版，实际应该链上数据）
        
        Args:
            threshold_usd: 阈值（美元）
        """
        # 这里简化实现，实际应该对接 Whale Alert API 或链上数据
        logger.info(f"Checking whale alerts (threshold: ${threshold_usd:,})")
        return []


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    fetcher = CryptoFetcher()
    
    # 测试 BTC
    print("Testing BTC...")
    data = fetcher.get_price('BTC')
    print(f"BTC Price: ${data['price'] if data else 'N/A'}")
    
    # 测试涨幅榜
    print("\nTop Gainers:")
    gainers = fetcher.get_top_gainers(5)
    for g in gainers:
        print(f"  {g['symbol']}: ${g['price']} ({g['change_24h']:+.2f}%)")
