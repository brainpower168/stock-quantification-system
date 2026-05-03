# -*- coding: utf-8 -*-
"""
缓存系统 - Cache System
支持内存缓存和 Redis 缓存
"""

import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from pathlib import Path
from functools import wraps
import threading

from .logger import get_logger
from .exceptions import CacheException

logger = get_logger('cache')


class MemoryCache:
    """内存缓存实现"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self._cache: Dict[str, Dict] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                logger.debug(f"Cache miss: {key}")
                return default
            
            entry = self._cache[key]
            if entry['expires'] and entry['expires'] < time.time():
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Cache expired: {key}")
                return default
            
            self._hits += 1
            logger.debug(f"Cache hit: {key}")
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        with self._lock:
            if len(self._cache) >= self._max_size:
                self._evict_oldest()
            
            expires = time.time() + (ttl or self._default_ttl) if ttl != -1 else None
            self._cache[key] = {
                'value': value,
                'expires': expires,
                'created_at': time.time(),
            }
            logger.debug(f"Cache set: {key}")
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted: {key}")
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    def _evict_oldest(self) -> None:
        """淘汰最旧的缓存"""
        if not self._cache:
            return
        
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k]['created_at']
        )
        del self._cache[oldest_key]
        logger.debug(f"Cache evicted: {oldest_key}")
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 3),
                'size': len(self._cache),
                'max_size': self._max_size,
            }


class FileCache:
    """文件缓存实现"""
    
    def __init__(self, cache_dir: str = 'data/cache', default_ttl: int = 86400):
        """
        Args:
            cache_dir: 缓存目录
            default_ttl: 默认过期时间（秒）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        logger.info(f"File cache initialized: {cache_dir}")
    
    def _get_file_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存"""
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            logger.debug(f"File cache miss: {key}")
            return default
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('expires') and data['expires'] < time.time():
                file_path.unlink()
                logger.debug(f"File cache expired: {key}")
                return default
            
            logger.debug(f"File cache hit: {key}")
            return data['value']
        except Exception as e:
            logger.error(f"读取文件缓存失败：{e}")
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        file_path = self._get_file_path(key)
        ttl = ttl or self.default_ttl
        
        data = {
            'value': value,
            'expires': time.time() + ttl if ttl != -1 else None,
            'created_at': time.time(),
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"File cache set: {key}")
        except Exception as e:
            logger.error(f"写入文件缓存失败：{e}")
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        file_path = self._get_file_path(key)
        
        if file_path.exists():
            try:
                file_path.unlink()
                logger.debug(f"File cache deleted: {key}")
                return True
            except Exception as e:
                logger.error(f"删除文件缓存失败：{e}")
        return False
    
    def clear(self) -> None:
        """清空缓存"""
        try:
            for file_path in self.cache_dir.glob('*.json'):
                file_path.unlink()
            logger.info("File cache cleared")
        except Exception as e:
            logger.error(f"清空文件缓存失败：{e}")


class CacheManager:
    """缓存管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        use_memory: bool = True,
        use_file: bool = True,
        use_redis: bool = False,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        memory_ttl: int = 3600,
        file_ttl: int = 86400,
    ):
        """
        Args:
            use_memory: 是否启用内存缓存
            use_file: 是否启用文件缓存
            use_redis: 是否启用 Redis 缓存
            redis_host: Redis 主机
            redis_port: Redis 端口
            memory_ttl: 内存缓存 TTL（秒）
            file_ttl: 文件缓存 TTL（秒）
        """
        if CacheManager._initialized:
            return
        
        self.use_memory = use_memory
        self.use_file = use_file
        self.use_redis = use_redis
        
        # 初始化缓存层
        if use_memory:
            self.memory_cache = MemoryCache(default_ttl=memory_ttl)
            logger.info("Memory cache enabled")
        else:
            self.memory_cache = None
        
        if use_file:
            self.file_cache = FileCache(default_ttl=file_ttl)
            logger.info("File cache enabled")
        else:
            self.file_cache = None
        
        if use_redis:
            self._init_redis_cache(redis_host, redis_port)
        else:
            self.redis_cache = None
        
        CacheManager._initialized = True
    
    def _init_redis_cache(self, host: str, port: int) -> None:
        """初始化 Redis 缓存"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                decode_responses=True,
                db=0
            )
            self.redis_client.ping()
            self.redis_cache = True
            logger.info(f"Redis cache connected: {host}:{port}")
        except ImportError:
            logger.warning("Redis 未安装，使用文件缓存代替")
            self.redis_cache = None
        except Exception as e:
            logger.warning(f"Redis 连接失败：{e}")
            self.redis_cache = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存（多级缓存）"""
        # Redis -> Memory -> File
        if self.redis_cache:
            try:
                value = self.redis_client.get(key)
                if value:
                    logger.debug(f"Redis cache hit: {key}")
                    return json.loads(value)
            except Exception:
                pass
        
        if self.memory_cache:
            value = self.memory_cache.get(key)
            if value is not None:
                return value
        
        if self.file_cache:
            return self.file_cache.get(key, default)
        
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, level: str = 'all') -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            level: 缓存级别 ('redis', 'memory', 'file', 'all')
        """
        if level in ['redis', 'all'] and self.redis_cache:
            try:
                json_value = json.dumps(value, ensure_ascii=False)
                if ttl:
                    self.redis_client.setex(key, ttl, json_value)
                else:
                    self.redis_client.set(key, json_value)
            except Exception as e:
                logger.error(f"Redis 缓存设置失败：{e}")
        
        if level in ['memory', 'all'] and self.memory_cache:
            self.memory_cache.set(key, value, ttl)
        
        if level in ['file', 'all'] and self.file_cache:
            self.file_cache.set(key, value, ttl)
    
    def delete(self, key: str) -> None:
        """删除缓存"""
        if self.redis_cache:
            try:
                self.redis_client.delete(key)
            except Exception:
                pass
        
        if self.memory_cache:
            self.memory_cache.delete(key)
        
        if self.file_cache:
            self.file_cache.delete(key)
    
    def clear(self) -> None:
        """清空所有缓存"""
        if self.memory_cache:
            self.memory_cache.clear()
        if self.file_cache:
            self.file_cache.clear()
        if self.redis_cache:
            try:
                self.redis_client.flushdb()
            except Exception:
                pass
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        stats = {}
        if self.memory_cache:
            stats['memory'] = self.memory_cache.get_stats()
        if self.file_cache:
            stats['file'] = {
                'size': len(list(self.file_cache.cache_dir.glob('*.json'))),
                'dir': str(self.file_cache.cache_dir),
            }
        return stats


def cached(ttl: int = 3600, level: str = 'all', key_prefix: str = ''):
    """
    缓存装饰器
    
    Args:
        ttl: 过期时间（秒）
        level: 缓存级别
        key_prefix: 键前缀
    
    Usage:
        @cached(ttl=3600)
        def fetch_data(code: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_mgr = CacheManager()
            
            # 生成缓存键
            key_parts = [key_prefix, func.__name__]
            
            # 添加参数到键
            for arg in args:
                if isinstance(arg, (str, int, float)):
                    key_parts.append(str(arg))
            
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (str, int, float)):
                    key_parts.append(f"{k}={v}")
            
            cache_key = ':'.join(key_parts)
            
            # 尝试从缓存获取
            cached_value = cache_mgr.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_mgr.set(cache_key, result, ttl, level)
            
            return result
        return wrapper
    return decorator


# 创建全局缓存管理器实例
cache_manager = CacheManager(
    use_memory=True,
    use_file=True,
    use_redis=False,
    memory_ttl=3600,
    file_ttl=86400,
)
