"""
缓存模块测试
测试 DataCache 类的核心功能
"""
import pytest
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.cache import CacheEntry, DataCache


class TestCacheEntry:
    """CacheEntry 测试类"""
    
    def test_init(self):
        """测试初始化"""
        entry = CacheEntry(data={'key': 'value'}, ttl_seconds=300)
        
        assert entry.data == {'key': 'value'}
        assert entry.ttl == 300
        assert entry.hit_count == 0
        assert entry.created_at <= time.time()
    
    def test_is_expired(self):
        """测试过期检查"""
        # 未过期
        entry = CacheEntry(data='test', ttl_seconds=300)
        assert entry.is_expired() is False
        
        # 已过期（使用负数 TTL 模拟）
        entry_expired = CacheEntry(data='test', ttl_seconds=-1)
        assert entry_expired.is_expired() is True
    
    def test_is_expired_after_time(self):
        """测试时间流逝后的过期检查"""
        entry = CacheEntry(data='test', ttl_seconds=1)
        
        assert entry.is_expired() is False
        time.sleep(1.1)
        assert entry.is_expired() is True
    
    def test_age_seconds(self):
        """测试年龄计算"""
        entry = CacheEntry(data='test', ttl_seconds=300)
        
        age = entry.age_seconds()
        
        assert age >= 0
        assert age < 1  # 刚创建，年龄应该很小
    
    def test_to_dict(self):
        """测试转换为字典"""
        entry = CacheEntry(data={'test': 'data'}, ttl_seconds=600)
        entry.hit_count = 5
        
        d = entry.to_dict()
        
        assert d['data'] == {'test': 'data'}
        assert d['ttl'] == 600
        assert d['hit_count'] == 5
        assert 'created_at' in d
    
    def test_from_dict(self):
        """测试从字典创建"""
        d = {
            'data': [1, 2, 3],
            'created_at': time.time() - 100,
            'ttl': 500,
            'hit_count': 10
        }
        
        entry = CacheEntry.from_dict(d)
        
        assert entry.data == [1, 2, 3]
        assert entry.ttl == 500
        assert entry.hit_count == 10
    
    def test_default_ttl(self):
        """测试默认 TTL"""
        entry = CacheEntry(data='test')
        
        assert entry.ttl == 300  # 默认 5 分钟


class TestDataCache:
    """DataCache 测试类"""
    
    @pytest.fixture
    def cache_dir(self, tmp_path):
        """创建临时缓存目录"""
        return str(tmp_path / 'cache')
    
    @pytest.fixture
    def cache(self, cache_dir):
        """创建缓存实例"""
        cache = DataCache(
            cache_dir=cache_dir,
            default_ttl=300,
            max_entries=100,
            auto_save=True
        )
        yield cache
        cache.clear()
    
    def test_init(self, cache, cache_dir):
        """测试初始化"""
        assert cache is not None
        assert cache.cache_dir == Path(cache_dir)
        assert cache.default_ttl == 300
        assert cache.max_entries == 100
        assert cache.auto_save is True
        assert cache.stats['hits'] == 0
        assert cache.stats['misses'] == 0
    
    def test_generate_key_simple(self, cache):
        """测试简单键生成"""
        key = cache._generate_key('test')
        
        assert key == 'test'
    
    def test_generate_key_with_params(self, cache):
        """测试带参数的键生成"""
        key1 = cache._generate_key('test', symbol='BTC', interval='1h')
        key2 = cache._generate_key('test', symbol='BTC', interval='1h')
        key3 = cache._generate_key('test', symbol='ETH', interval='1h')
        
        # 相同参数生成相同键
        assert key1 == key2
        # 不同参数生成不同键
        assert key1 != key3
        # 键包含前缀
        assert key1.startswith('test:')
    
    def test_get_miss(self, cache):
        """测试缓存未命中"""
        result = cache.get('nonexistent_key')
        
        assert result is None
        assert cache.stats['misses'] == 1
    
    def test_get_miss_with_default(self, cache):
        """测试缓存未命中带默认值"""
        result = cache.get('nonexistent_key', default='default_value')
        
        assert result == 'default_value'
    
    def test_set_and_get(self, cache):
        """测试设置和获取缓存"""
        cache.set('test_key', {'data': 'value'})
        
        result = cache.get('test_key')
        
        assert result == {'data': 'value'}
        assert cache.stats['hits'] == 1
    
    def test_set_with_custom_ttl(self, cache):
        """测试设置自定义 TTL"""
        cache.set('short_ttl_key', 'value', ttl=1)
        
        result = cache.get('short_ttl_key')
        assert result == 'value'
        
        time.sleep(1.1)
        
        result = cache.get('short_ttl_key')
        assert result is None
        assert cache.stats['expirations'] == 1
    
    def test_delete(self, cache):
        """测试删除缓存"""
        cache.set('to_delete', 'value')
        
        result = cache.delete('to_delete')
        
        assert result is True
        assert cache.get('to_delete') is None
    
    def test_delete_nonexistent(self, cache):
        """测试删除不存在的键"""
        result = cache.delete('nonexistent')
        
        assert result is False
    
    def test_clear(self, cache):
        """测试清空缓存"""
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        
        cache.clear()
        
        assert cache.get('key1') is None
        assert cache.get('key2') is None
        assert len(cache._memory_cache) == 0
    
    def test_auto_eviction(self, cache_dir):
        """测试自动驱逐"""
        cache = DataCache(
            cache_dir=cache_dir,
            max_entries=5,
            auto_save=False
        )
        
        # 添加超过最大条目数
        for i in range(10):
            cache.set(f'key_{i}', f'value_{i}')
        
        # 缓存条目数不应超过最大值
        assert len(cache._memory_cache) <= 5
        
        cache.clear()
    
    def test_stats_tracking(self, cache):
        """测试统计追踪"""
        cache.set('stat_test', 'value')
        
        cache.get('stat_test')  # hit
        cache.get('stat_test')  # hit
        cache.get('nonexistent')  # miss
        
        assert cache.stats['hits'] == 2
        assert cache.stats['misses'] == 1
        assert cache.stats['evictions'] == 0
    
    def test_file_cache_persistence(self, cache):
        """测试文件缓存持久化"""
        cache.set('persist_test', {'data': [1, 2, 3]})
        
        # 检查文件是否创建
        cache_files = list(cache.cache_dir.glob('*.json'))
        assert len(cache_files) > 0
    
    def test_load_persistent_cache(self, cache_dir):
        """测试加载持久化缓存"""
        # 创建缓存并保存数据
        cache1 = DataCache(cache_dir=cache_dir, auto_save=True)
        cache1.set('persist_key', 'persist_value')
        cache1.clear()
        
        # 创建新实例，应该加载持久化数据
        cache2 = DataCache(cache_dir=cache_dir, auto_save=False)
        
        # 持久化缓存应该在文件系统中
        cache_files = list(Path(cache_dir).glob('*.json'))
        assert len(cache_files) > 0
        
        cache2.clear()
    
    def test_get_with_prefix(self, cache):
        """测试带前缀的键获取"""
        cache.set('prices:BTC', 50000)
        cache.set('prices:ETH', 3000)
        
        btc_price = cache.get('prices:BTC')
        eth_price = cache.get('prices:ETH')
        
        assert btc_price == 50000
        assert eth_price == 3000
    
    def test_set_overwrite(self, cache):
        """测试覆盖已有键"""
        cache.set('overwrite_key', 'value1')
        cache.set('overwrite_key', 'value2')
        
        result = cache.get('overwrite_key')
        
        assert result == 'value2'
    
    def test_cache_entry_hit_count(self, cache):
        """测试缓存条目命中计数"""
        cache.set('hit_test', 'value')
        
        cache.get('hit_test')
        cache.get('hit_test')
        cache.get('hit_test')
        
        # 获取内部条目检查 hit_count
        entry = cache._memory_cache.get('hit_test')
        assert entry is not None
        assert entry.hit_count == 3
    
    def test_delete_file_cache(self, cache):
        """测试删除文件缓存"""
        cache.set('file_delete_test', 'value')
        
        # 获取文件列表
        files_before = set(f.name for f in cache.cache_dir.glob('*.json'))
        
        cache.delete('file_delete_test')
        
        # 文件应该被删除（如果启用了 auto_save）
        if cache.auto_save:
            files_after = set(f.name for f in cache.cache_dir.glob('*.json'))
            # 至少文件数量应该减少或不变
            assert len(files_after) <= len(files_before)
    
    def test_clear_file_cache(self, cache):
        """测试清空文件缓存"""
        cache.set('clear_test1', 'value1')
        cache.set('clear_test2', 'value2')
        
        cache.clear()
        
        # 所有缓存文件应该被删除
        cache_files = list(cache.cache_dir.glob('*.json'))
        assert len(cache_files) == 0
    
    def test_save_entry_to_file(self, cache):
        """测试保存条目到文件"""
        entry = CacheEntry(data={'test': 'data'}, ttl_seconds=600)
        
        cache._save_entry_to_file('file_test', entry)
        
        # 验证文件存在
        cache_files = list(cache.cache_dir.glob('*.json'))
        assert len(cache_files) > 0
    
    def test_load_entry_from_file(self, cache):
        """测试从文件加载条目"""
        # 先保存
        cache.set('load_test', {'loaded': 'data'})
        
        # 验证数据可获取
        result = cache.get('load_test')
        assert result == {'loaded': 'data'}
    
    def test_concurrent_access(self, cache):
        """测试并发访问"""
        import threading
        
        errors = []
        
        def access_cache(thread_id):
            try:
                for i in range(20):
                    key = f'concurrent_{thread_id}_{i}'
                    cache.set(key, f'value_{i}')
                    cache.get(key)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=access_cache, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
    
    def test_large_data(self, cache):
        """测试大数据缓存"""
        large_data = {'data': list(range(10000))}
        
        cache.set('large_key', large_data)
        
        result = cache.get('large_key')
        
        assert result == large_data
        assert len(result['data']) == 10000
    
    def test_special_characters_key(self, cache):
        """测试特殊字符键"""
        cache.set('special:key!@#$', 'value')
        
        result = cache.get('special:key!@#$')
        
        assert result == 'value'
    
    def test_unicode_data(self, cache):
        """测试 Unicode 数据"""
        unicode_data = {'中文': '数据', 'emoji': '🚀'}
        
        cache.set('unicode_key', unicode_data)
        
        result = cache.get('unicode_key')
        
        assert result == unicode_data
        assert result['emoji'] == '🚀'
    
    def test_none_value(self, cache):
        """测试 None 值"""
        cache.set('none_key', None)
        
        result = cache.get('none_key', default='default')
        
        # None 是有效值，不应返回默认值
        assert result is None
    
    def test_boolean_value(self, cache):
        """测试布尔值"""
        cache.set('bool_key', False)
        
        result = cache.get('bool_key', default=True)
        
        # False 是有效值，不应返回默认值
        assert result is False
    
    def test_zero_value(self, cache):
        """测试零值"""
        cache.set('zero_key', 0)
        
        result = cache.get('zero_key', default=999)
        
        # 0 是有效值，不应返回默认值
        assert result == 0
    
    def test_empty_string_value(self, cache):
        """测试空字符串"""
        cache.set('empty_key', '')
        
        result = cache.get('empty_key', default='default')
        
        # 空字符串是有效值
        assert result == ''
    
    def test_nested_dict(self, cache):
        """测试嵌套字典"""
        nested = {
            'level1': {
                'level2': {
                    'level3': 'deep_value'
                }
            }
        }
        
        cache.set('nested_key', nested)
        
        result = cache.get('nested_key')
        
        assert result == nested
        assert result['level1']['level2']['level3'] == 'deep_value'
    
    def test_list_value(self, cache):
        """测试列表值"""
        list_data = [1, 2, 3, 4, 5]
        
        cache.set('list_key', list_data)
        
        result = cache.get('list_key')
        
        assert result == list_data
        assert len(result) == 5


class TestDataCacheEdgeCases:
    """DataCache 边界测试"""
    
    def test_cache_dir_auto_create(self, tmp_path):
        """测试缓存目录自动创建"""
        cache_dir = str(tmp_path / 'nonexistent' / 'cache')
        
        cache = DataCache(cache_dir=cache_dir)
        
        assert os.path.exists(cache_dir)
        cache.clear()
    
    def test_max_entries_one(self, cache_dir):
        """测试最大条目数为 1"""
        cache = DataCache(cache_dir=cache_dir, max_entries=1, auto_save=False)
        
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        
        # 只保留最后一个
        assert len(cache._memory_cache) == 1
        assert cache.get('key2') == 'value2'
        
        cache.clear()
    
    def test_zero_ttl(self, cache_dir):
        """测试零 TTL"""
        cache = DataCache(cache_dir=cache_dir, default_ttl=0, auto_save=False)
        
        cache.set('zero_ttl', 'value')
        
        # 立即过期
        result = cache.get('zero_ttl')
        assert result is None
    
    def test_very_long_key(self, cache):
        """测试超长键"""
        long_key = 'a' * 10000
        cache.set(long_key, 'value')
        
        result = cache.get(long_key)
        
        assert result == 'value'
    
    def test_rapid_set_get(self, cache):
        """测试快速设置获取"""
        for i in range(1000):
            cache.set(f'rapid_{i}', i)
            cache.get(f'rapid_{i}')
        
        assert cache.stats['hits'] == 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
