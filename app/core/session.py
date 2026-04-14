# 会话管理模块
# 使用 Redis 实现无状态的轻量级会话，通过 Cookie 中的 session_id 标识用户。
# 每个会话维护一个 resume_ids 列表，用于隔离不同用户上传的简历，
# 防止用户通过猜测 resume_id 访问他人数据。
import uuid
import json
from app.core.cache import get_redis

# 会话 TTL：7 天，每次活动时刷新
SESSION_TTL = 3600 * 24 * 7  # 7 days
# 简历数据 TTL：24 小时
RESUME_TTL = 3600 * 24  # 24 hours


async def create_session() -> str:
    """创建新会话，返回 session_id。"""
    session_id = str(uuid.uuid4())
    redis = await get_redis()
    await redis.setex(
        f"session:{session_id}", SESSION_TTL, json.dumps({"resume_ids": []})
    )
    return session_id


async def session_exists(session_id: str) -> bool:
    """检查会话是否存在（未过期）。"""
    redis = await get_redis()
    return bool(await redis.exists(f"session:{session_id}"))


async def add_resume_to_session(session_id: str, resume_id: str) -> None:
    """将 resume_id 关联到指定会话，并刷新会话 TTL。"""
    redis = await get_redis()
    key = f"session:{session_id}"
    raw = await redis.get(key)
    if not raw:
        return
    data = json.loads(raw)
    if resume_id not in data["resume_ids"]:
        data["resume_ids"].append(resume_id)
    # 每次有活动时刷新 TTL，保持活跃会话不过期
    await redis.setex(key, SESSION_TTL, json.dumps(data))


async def session_owns_resume(session_id: str, resume_id: str) -> bool:
    """校验指定会话是否拥有该简历（用于访问控制）。"""
    redis = await get_redis()
    raw = await redis.get(f"session:{session_id}")
    if not raw:
        return False
    data = json.loads(raw)
    return resume_id in data["resume_ids"]


async def list_session_resumes(session_id: str) -> list[str]:
    """返回会话下所有 resume_id 列表。"""
    redis = await get_redis()
    raw = await redis.get(f"session:{session_id}")
    if not raw:
        return []
    return json.loads(raw)["resume_ids"]
