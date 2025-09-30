"""
Redis Cache Service for Agent-Chat
High-performance caching layer
"""

import redis.asyncio as redis
import json
import pickle
from typing import Optional, Any, Union
from datetime import timedelta
import logging
from core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache service with async support"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = settings.enable_caching
        self.default_ttl = settings.cache_ttl_seconds
        
    async def connect(self):
        """Connect to Redis server"""
        if not self.enabled:
            logger.info("Caching is disabled")
            return
            
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=False
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self.enabled = False
            self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis cache")
    
    async def get(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value is None:
                return None
            
            if deserialize:
                # Try JSON first, then pickle
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    try:
                        return pickle.loads(value)
                    except:
                        return value.decode('utf-8') if isinstance(value, bytes) else value
            
            return value.decode('utf-8') if isinstance(value, bytes) else value
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """Set value in cache with optional TTL"""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            
            if serialize:
                # Try JSON first for better compatibility
                try:
                    value = json.dumps(value)
                except (TypeError, ValueError):
                    # Fall back to pickle for complex objects
                    value = pickle.dumps(value)
            elif isinstance(value, str):
                value = value.encode('utf-8')
            
            await self.redis_client.set(key, value, ex=ttl)
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.enabled or not self.redis_client:
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in cache"""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for a key"""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            ttl = await self.redis_client.ttl(key)
            return ttl if ttl >= 0 else None
        except Exception as e:
            logger.error(f"Cache get TTL error for key {key}: {e}")
            return None
    
    def cache_key(self, *parts: str) -> str:
        """Generate cache key from parts"""
        return ":".join(["bpchat"] + list(parts))


# Global cache instance
cache_service = CacheService()


# Decorator for caching function results
def cached(ttl: int = None, key_prefix: str = None):
    """Decorator to cache async function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_parts = [key_prefix or func.__name__]
            
            # Add arguments to key
            if args:
                cache_key_parts.extend(str(arg) for arg in args)
            if kwargs:
                cache_key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            
            cache_key = cache_service.cache_key(*cache_key_parts)
            
            # Try to get from cache
            cached_value = await cache_service.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
