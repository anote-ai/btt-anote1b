"""
Caching layer for leaderboard queries

Uses in-memory caching with TTL to reduce database load for frequently accessed
leaderboards. In production, consider Redis for distributed caching.
"""
from typing import Optional, Callable
from functools import wraps
from cachetools import TTLCache
import hashlib

# In-memory cache with 5-minute TTL and max 1000 entries
leaderboard_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes


def _leaderboard_cache_key(func_name: str, kwargs: dict) -> str:
    """
    Stable cache key from primitive params only (no Request / DB session).
    Avoids json.dumps failures on Starlette Request / SQLAlchemy Session.
    """
    parts = [func_name]
    if kwargs.get("task_type") is not None:
        parts.append(f"task={kwargs['task_type']}")
    if kwargs.get("dataset_id") is not None:
        parts.append(f"ds={kwargs['dataset_id']}")
    if "include_internal" in kwargs:
        parts.append(f"inc={kwargs['include_internal']}")
    key_str = "|".join(parts)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached_leaderboard(func: Callable) -> Callable:
    """
    Decorator to cache leaderboard query results
    
    Usage:
        @cached_leaderboard
        async def get_leaderboard(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Generate cache key
        key = f"{func.__name__}:{_leaderboard_cache_key(func.__name__, kwargs)}"
        
        # Check cache
        if key in leaderboard_cache:
            return leaderboard_cache[key]
        
        # Execute function
        result = await func(*args, **kwargs)
        
        # Store in cache
        leaderboard_cache[key] = result
        
        return result
    
    return wrapper


def invalidate_leaderboard_cache(dataset_id: Optional[str] = None):
    """
    Invalidate cached leaderboard data
    
    Args:
        dataset_id: If provided, only invalidate caches for this dataset.
                   If None, clear all leaderboard caches.
    """
    if dataset_id is None:
        leaderboard_cache.clear()
        print("🗑️  Cleared all leaderboard caches")
    else:
        # Clear entries that contain this dataset_id
        keys_to_remove = [
            k for k in leaderboard_cache.keys()
            if dataset_id in str(k)
        ]
        for key in keys_to_remove:
            leaderboard_cache.pop(key, None)
        print(f"🗑️  Cleared cache for dataset {dataset_id}")


def get_cache_stats() -> dict:
    """Get cache statistics for monitoring"""
    return {
        "size": len(leaderboard_cache),
        "maxsize": leaderboard_cache.maxsize,
        "ttl": leaderboard_cache.ttl,
        "hits": getattr(leaderboard_cache, "hits", 0),
        "misses": getattr(leaderboard_cache, "misses", 0),
    }

