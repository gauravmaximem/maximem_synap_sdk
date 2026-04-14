"""Client-side caching layer."""

from .backend import CacheBackend, NullCacheBackend
from .sqlite_backend import SQLiteCacheBackend
from .manager import CacheManager, CacheScope

# Deprecated - kept for backward compatibility
from .cache_manager import CacheEntry

__all__ = [
    "CacheBackend",
    "NullCacheBackend",
    "SQLiteCacheBackend",
    "CacheManager",
    "CacheScope",
    # Deprecated
    "CacheEntry",
]
