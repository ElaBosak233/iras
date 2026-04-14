import uuid
import json
from app.core.cache import get_redis

SESSION_TTL = 3600 * 24 * 7  # 7 days
RESUME_TTL = 3600 * 24  # 24 hours


async def create_session() -> str:
    session_id = str(uuid.uuid4())
    redis = await get_redis()
    await redis.setex(
        f"session:{session_id}", SESSION_TTL, json.dumps({"resume_ids": []})
    )
    return session_id


async def session_exists(session_id: str) -> bool:
    redis = await get_redis()
    return bool(await redis.exists(f"session:{session_id}"))


async def add_resume_to_session(session_id: str, resume_id: str) -> None:
    redis = await get_redis()
    key = f"session:{session_id}"
    raw = await redis.get(key)
    if not raw:
        return
    data = json.loads(raw)
    if resume_id not in data["resume_ids"]:
        data["resume_ids"].append(resume_id)
    # Refresh TTL on activity
    await redis.setex(key, SESSION_TTL, json.dumps(data))


async def session_owns_resume(session_id: str, resume_id: str) -> bool:
    redis = await get_redis()
    raw = await redis.get(f"session:{session_id}")
    if not raw:
        return False
    data = json.loads(raw)
    return resume_id in data["resume_ids"]


async def list_session_resumes(session_id: str) -> list[str]:
    redis = await get_redis()
    raw = await redis.get(f"session:{session_id}")
    if not raw:
        return []
    return json.loads(raw)["resume_ids"]
