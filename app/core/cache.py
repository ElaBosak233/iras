# Redis 连接管理模块
# 使用单例模式维护一个全局异步 Redis 连接，避免每次请求重复建立连接。
# 应用关闭时通过 close_redis() 优雅释放连接。
import redis.asyncio as aioredis
from app.core.config import settings

# 全局 Redis 客户端实例，首次调用 get_redis() 时懒加载初始化
_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """获取全局 Redis 客户端（懒加载单例）。"""
    global _redis
    if _redis is None:
        # decode_responses=True 使所有返回值自动解码为字符串，无需手动 decode
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis():
    """关闭 Redis 连接，在应用 lifespan 结束时调用。"""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
