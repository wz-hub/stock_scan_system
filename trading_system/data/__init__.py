"""
数据模块 - 统一的数据访问接口

提供 Binance API 封装、缓存管理、数据库管理功能。
"""

from .binance import BinanceAPI, get_binance_client
from .cache import DataCache, get_cache
from .database import Database, get_database

__all__ = [
    'BinanceAPI',
    'get_binance_client',
    'DataCache',
    'get_cache',
    'Database',
    'get_database',
]

__version__ = '1.0.0'
