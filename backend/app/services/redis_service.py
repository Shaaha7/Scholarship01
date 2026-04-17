"""
Redis Service – Caching layer for queries and sessions
=======================================================
Provides caching for:
- Scholarship search results
- User sessions
- API responses
- Embedding cache
"""
import json
import logging
from typing import Optional, Any, List
from datetime import timedelta

import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """Redis service for caching and session management."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        
    async def connect(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            await self.redis_client.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis_client:
            return None
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        if not self.redis_client:
            return False
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await self.redis_client.setex(key, ttl, serialized)
            else:
                await self.redis_client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis_client:
            return False
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        if not self.redis_client:
            return 0
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.error(f"Redis delete_pattern error: {e}")
            return 0
    
    async def cache_scholarship_search(
        self,
        query_hash: str,
        results: List[Any],
        ttl: int = 3600
    ) -> bool:
        """Cache scholarship search results."""
        key = f"scholarship_search:{query_hash}"
        return await self.set(key, results, ttl)
    
    async def get_cached_scholarship_search(
        self,
        query_hash: str
    ) -> Optional[List[Any]]:
        """Get cached scholarship search results."""
        key = f"scholarship_search:{query_hash}"
        return await self.get(key)
    
    async def cache_embedding(
        self,
        text_hash: str,
        embedding: List[float],
        ttl: int = 86400
    ) -> bool:
        """Cache text embedding."""
        key = f"embedding:{text_hash}"
        return await self.set(key, embedding, ttl)
    
    async def get_cached_embedding(
        self,
        text_hash: str
    ) -> Optional[List[float]]:
        """Get cached text embedding."""
        key = f"embedding:{text_hash}"
        return await self.get(key)
    
    async def cache_llm_response(
        self,
        prompt_hash: str,
        response: str,
        ttl: int = 1800
    ) -> bool:
        """Cache LLM response."""
        key = f"llm_response:{prompt_hash}"
        return await self.set(key, response, ttl)
    
    async def get_cached_llm_response(
        self,
        prompt_hash: str
    ) -> Optional[str]:
        """Get cached LLM response."""
        key = f"llm_response:{prompt_hash}"
        return await self.get(key)
    
    async def invalidate_user_cache(self, user_id: str) -> int:
        """Invalidate all cache entries for a user."""
        patterns = [
            f"user_sessions:{user_id}:*",
            f"user_profile:{user_id}",
            f"user_searches:{user_id}:*",
        ]
        count = 0
        for pattern in patterns:
            count += await self.delete_pattern(pattern)
        return count
    
    async def get_stats(self) -> dict:
        """Get Redis statistics."""
        if not self.redis_client:
            return {"connected": False}
        try:
            info = await self.redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "total_keys": info.get("db0", {}).get("keys", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"connected": True, "error": str(e)}


# Global Redis service instance
redis_service = RedisService()
