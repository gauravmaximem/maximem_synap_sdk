"""DEPRECATED: Old cache manager stub - use manager.py instead.

This module is kept for backward compatibility only.
Use cache.manager.CacheManager for the new implementation.
"""

import warnings
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
from threading import Lock
import hashlib

if TYPE_CHECKING:
    from ..models.config import CacheConfig


@dataclass
class CacheEntry:
    """DEPRECATED: Cache entry with metadata.
    
    This class is kept for backward compatibility only.
    The new cache implementation uses bytes directly.
    """
    
    key: str
    data: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    hits: int = 0


class OldCacheManager:
    """DEPRECATED: Old cache manager stub.
    
    This class is kept for backward compatibility only.
    Use cache.manager.CacheManager for the new implementation.
    """
    
    def __init__(self, config: "CacheConfig"):
        """Initialize cache manager.
        
        Args:
            config: Cache configuration
        """
        warnings.warn(
            "OldCacheManager is deprecated. Use cache.manager.CacheManager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.config = config
        self._lock = Lock()
        self._cache: Dict[str, CacheEntry] = {}
    
    def get(self, cache_key: str) -> Optional[CacheEntry]:
        """Retrieve entry from cache.
        
        Args:
            cache_key: Cache key to retrieve
            
        Returns:
            Cache entry if found and valid, None otherwise
        """
        raise NotImplementedError("Use cache.manager.CacheManager instead")
    
    def set(self, cache_key: str, data: Dict[str, Any], ttl: int) -> None:
        """Store entry in cache.
        
        Args:
            cache_key: Cache key
            data: Data to cache
            ttl: Time-to-live in seconds
        """
        raise NotImplementedError("Use cache.manager.CacheManager instead")
    
    def invalidate(self, cache_key: str) -> None:
        """Invalidate cache entry.
        
        Args:
            cache_key: Cache key to invalidate
        """
        raise NotImplementedError("Use cache.manager.CacheManager instead")
    
    def build_cache_key(
        self,
        scope: str,
        entity_id: str,
        types: Optional[List[str]] = None
    ) -> str:
        """Build deterministic cache key.
        
        Args:
            scope: Scope (e.g., "conversation", "user")
            entity_id: Entity identifier
            types: Optional list of context types
            
        Returns:
            Deterministic cache key
        """
        components = [scope, entity_id]
        if types:
            components.extend(sorted(types))
        key_input = ":".join(components)
        return hashlib.sha256(key_input.encode()).hexdigest()
    
    def cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        raise NotImplementedError("Use cache.manager.CacheManager instead")


class CacheManager:
    """Backward-compatible cache manager shim for legacy tests/imports."""

    def __init__(self, config: "CacheConfig"):
        self.config = config

    def build_cache_key(
        self,
        scope: str,
        entity_id: str,
        types: Optional[List[str]] = None,
    ) -> str:
        components = [scope, entity_id]
        if types:
            components.extend(sorted(types))
        key_input = ":".join(components)
        return hashlib.sha256(key_input.encode()).hexdigest()
