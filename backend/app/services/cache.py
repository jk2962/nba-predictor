"""
NBA Player Performance Prediction - In-Memory Cache Service
"""
from typing import Any, Optional
from datetime import datetime, timedelta
from threading import Lock
from app.config import get_settings


class SimpleCache:
    """Thread-safe in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: Optional[int] = None):
        """
        Initialize the cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (uses config if not provided)
        """
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._lock = Lock()
        self._default_ttl = default_ttl or get_settings().cache_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expires_at = self._cache[key]
            
            if datetime.utcnow() > expires_at:
                # Entry expired, remove it
                del self._cache[key]
                return None
            
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not provided)
        """
        ttl = ttl or self._default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        with self._lock:
            self._cache[key] = (value, expires_at)
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        now = datetime.utcnow()
        removed = 0
        
        with self._lock:
            expired_keys = [
                key for key, (_, expires_at) in self._cache.items()
                if now > expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
                removed += 1
        
        return removed
    
    def size(self) -> int:
        """Get the number of items in the cache."""
        with self._lock:
            return len(self._cache)


# Global cache instances
prediction_cache = SimpleCache()
player_cache = SimpleCache(default_ttl=600)  # 10 minutes for player data
