"""
缓存管理模块

提供内存缓存和文件缓存功能，支持自动过期和清理。
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List
import hashlib


class CacheEntry:
    """缓存条目"""
    
    def __init__(self, data: Any, ttl_seconds: int = 300):
        """
        初始化缓存条目
        
        Args:
            data: 缓存数据
            ttl_seconds: 生存时间（秒），默认 5 分钟
        """
        self.data = data
        self.created_at = time.time()
        self.ttl = ttl_seconds
        self.hit_count = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return (time.time() - self.created_at) > self.ttl
    
    def age_seconds(self) -> float:
        """获取缓存年龄（秒）"""
        return time.time() - self.created_at
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'data': self.data,
            'created_at': self.created_at,
            'ttl': self.ttl,
            'hit_count': self.hit_count
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'CacheEntry':
        """从字典创建"""
        entry = cls(d['data'], d['ttl'])
        entry.created_at = d['created_at']
        entry.hit_count = d.get('hit_count', 0)
        return entry


class DataCache:
    """数据缓存管理器"""
    
    def __init__(
        self, 
        cache_dir: str = "cache",
        default_ttl: int = 300,
        max_entries: int = 1000,
        auto_save: bool = True
    ):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
            default_ttl: 默认生存时间（秒）
            max_entries: 最大缓存条目数
            auto_save: 是否自动保存到文件
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self.auto_save = auto_save
        
        # 内存缓存
        self._memory_cache: Dict[str, CacheEntry] = {}
        
        # 缓存统计
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }
        
        # 加载持久化缓存
        self._load_persistent_cache()
    
    def _generate_key(self, prefix: str, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            prefix: 键前缀
            **kwargs: 参数
        
        Returns:
            缓存键字符串
        """
        if not kwargs:
            return prefix
        
        # 对参数排序并生成哈希
        sorted_items = sorted(kwargs.items())
        param_str = json.dumps(sorted_items, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
        
        return f"{prefix}:{param_hash}"
    
    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            default: 默认值（缓存未命中时返回）
        
        Returns:
            缓存数据，未命中返回 default
        """
        if key not in self._memory_cache:
            self.stats['misses'] += 1
            return default
        
        entry = self._memory_cache[key]
        
        # 检查是否过期
        if entry.is_expired():
            del self._memory_cache[key]
            self.stats['expirations'] += 1
            self.stats['misses'] += 1
            return default
        
        # 命中
        entry.hit_count += 1
        self.stats['hits'] += 1
        
        return entry.data
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = None,
        save_to_file: bool = None
    ):
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None 使用默认值
            save_to_file: 是否保存到文件，None 使用 auto_save 设置
        """
        # 如果缓存已满，清理最旧的条目
        if len(self._memory_cache) >= self.max_entries:
            self._evict_oldest()
        
        ttl = ttl if ttl is not None else self.default_ttl
        entry = CacheEntry(value, ttl)
        self._memory_cache[key] = entry
        
        # 自动保存
        if save_to_file is None:
            save_to_file = self.auto_save
        
        if save_to_file:
            self._save_entry_to_file(key, entry)
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            True 表示删除成功
        """
        if key in self._memory_cache:
            del self._memory_cache[key]
            self._delete_file_cache(key)
            return True
        return False
    
    def clear(self):
        """清空所有缓存"""
        self._memory_cache.clear()
        self._clear_file_cache()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }
    
    def cleanup_expired(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的条目数
        """
        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._memory_cache[key]
            self._delete_file_cache(key)
        
        self.stats['expirations'] += len(expired_keys)
        return len(expired_keys)
    
    def cleanup_old_data(self, max_age_days: int = 7):
        """
        清理旧数据文件
        
        Args:
            max_age_days: 最大保存天数
        """
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                if cache_file.stat().st_mtime < cutoff_time:
                    cache_file.unlink()
            except Exception as e:
                print(f"⚠️ 删除缓存文件失败 {cache_file}: {e}")
    
    def get_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate': round(hit_rate, 2),
            'cache_size': len(self._memory_cache),
            'max_entries': self.max_entries
        }
    
    def _evict_oldest(self):
        """淘汰最旧的缓存条目"""
        if not self._memory_cache:
            return
        
        # 找到最旧的条目
        oldest_key = min(
            self._memory_cache.keys(),
            key=lambda k: self._memory_cache[k].created_at
        )
        
        del self._memory_cache[oldest_key]
        self._delete_file_cache(oldest_key)
        self.stats['evictions'] += 1
    
    def _save_entry_to_file(self, key: str, entry: CacheEntry):
        """保存条目到文件"""
        try:
            safe_key = hashlib.md5(key.encode()).hexdigest()
            cache_file = self.cache_dir / f"{safe_key}.cache"
            
            with open(cache_file, 'w') as f:
                json.dump(entry.to_dict(), f)
        
        except Exception as e:
            print(f"⚠️ 保存缓存失败 {key}: {e}")
    
    def _load_persistent_cache(self):
        """从文件加载缓存"""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'r') as f:
                        entry_dict = json.load(f)
                        entry = CacheEntry.from_dict(entry_dict)
                        
                        # 只加载未过期的缓存
                        if not entry.is_expired():
                            # 从文件名恢复键（简化处理，实际使用时可通过元数据恢复）
                            self._memory_cache[cache_file.stem] = entry
                
                except Exception:
                    continue
        
        except Exception as e:
            print(f"⚠️ 加载持久化缓存失败：{e}")
    
    def _delete_file_cache(self, key: str):
        """删除文件缓存"""
        try:
            safe_key = hashlib.md5(key.encode()).hexdigest()
            cache_file = self.cache_dir / f"{safe_key}.cache"
            if cache_file.exists():
                cache_file.unlink()
        except Exception:
            pass
    
    def _clear_file_cache(self):
        """清空文件缓存"""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
        except Exception:
            pass
    
    # 便捷方法：K 线缓存
    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> Optional[Any]:
        """获取 K 线缓存"""
        key = self._generate_key("klines", symbol=symbol, interval=interval, limit=limit)
        return self.get(key)
    
    def set_klines(self, symbol: str, interval: str, limit: int, data: Any, ttl: int = None):
        """设置 K 线缓存"""
        key = self._generate_key("klines", symbol=symbol, interval=interval, limit=limit)
        ttl = ttl or 300  # 默认 5 分钟
        self.set(key, data, ttl=ttl)
    
    # 便捷方法：行情缓存
    def get_ticker(self, symbol: str) -> Optional[Any]:
        """获取行情缓存"""
        key = self._generate_key("ticker", symbol=symbol)
        return self.get(key)
    
    def set_ticker(self, symbol: str, data: Any, ttl: int = 60):
        """设置行情缓存"""
        key = self._generate_key("ticker", symbol=symbol)
        self.set(key, data, ttl=ttl)  # 行情缓存默认 1 分钟


# 便捷函数
_cache_instance = None

def get_cache(
    cache_dir: str = "cache",
    default_ttl: int = 300,
    max_entries: int = 1000
) -> DataCache:
    """
    获取缓存实例（单例模式）
    
    Args:
        cache_dir: 缓存目录
        default_ttl: 默认生存时间
        max_entries: 最大缓存条目数
    
    Returns:
        DataCache 实例
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DataCache(
            cache_dir=cache_dir,
            default_ttl=default_ttl,
            max_entries=max_entries
        )
    return _cache_instance


# 测试
if __name__ == "__main__":
    print("📦 测试缓存管理...")
    
    cache = DataCache(cache_dir="cache", default_ttl=10, max_entries=100)
    
    # 测试基本缓存
    print("\n1. 测试基本缓存操作...")
    cache.set("test_key", {"value": 123})
    result = cache.get("test_key")
    print(f"   ✅ 缓存读取：{result}")
    
    # 测试缓存命中统计
    print("\n2. 测试缓存统计...")
    cache.get("test_key")
    cache.get("test_key")
    cache.get("nonexistent", default="default")
    stats = cache.get_stats()
    print(f"   命中：{stats['hits']}, 未命中：{stats['misses']}")
    print(f"   命中率：{stats['hit_rate']}%")
    
    # 测试 K 线缓存
    print("\n3. 测试 K 线缓存...")
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    test_df = pd.DataFrame({
        'open': np.random.uniform(100, 110, 100),
        'high': np.random.uniform(110, 120, 100),
        'low': np.random.uniform(90, 100, 100),
        'close': np.random.uniform(100, 110, 100),
        'volume': np.random.uniform(1000, 10000, 100)
    }, index=dates)
    
    cache.set_klines("BTCUSDT", "1d", 100, test_df)
    cached_df = cache.get_klines("BTCUSDT", "1d", 100)
    print(f"   ✅ K 线缓存：{len(cached_df) if cached_df is not None else 0} 条")
    
    # 测试过期清理
    print("\n4. 测试过期清理...")
    time.sleep(11)  # 等待过期
    expired_count = cache.cleanup_expired()
    print(f"   ✅ 清理过期条目：{expired_count}")
    
    # 测试旧数据清理
    print("\n5. 测试旧数据清理...")
    cache.cleanup_old_data(max_age_days=7)
    print(f"   ✅ 旧数据清理完成")
    
    print("\n✅ 缓存管理测试完成！")
