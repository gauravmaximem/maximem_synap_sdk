"""Cache backend interface and implementations."""

from abc import ABC, abstractmethod
from typing import Optional


class CacheBackend(ABC):
    """Abstract cache backend interface.

    Implementations:
    - SQLiteCacheBackend (MVP)
    - RedisCacheBackend (post-MVP)
    - NullCacheBackend (disabled)
    """

    @abstractmethod
    def get(self, key: str) -> Optional[bytes]:
        """Get value by key. Returns None if not found or expired."""
        pass

    @abstractmethod
    def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        """Set value with TTL."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a specific key."""
        pass

    @abstractmethod
    def clear_scope(self, scope_prefix: str) -> int:
        """Delete all keys matching scope prefix. Returns count deleted."""
        pass

    @abstractmethod
    def clear_all(self) -> None:
        """Delete all cached data."""
        pass

    @abstractmethod
    def stats(self) -> dict:
        """Get cache statistics."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connections and cleanup."""
        pass


class NullCacheBackend(CacheBackend):
    """No-op cache backend for serverless or disabled cache."""

    def get(self, key: str) -> Optional[bytes]:
        return None

    def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        pass

    def delete(self, key: str) -> None:
        pass

    def clear_scope(self, scope_prefix: str) -> int:
        return 0

    def clear_all(self) -> None:
        pass

    def stats(self) -> dict:
        return {"backend": "null", "enabled": False}

    def close(self) -> None:
        pass
