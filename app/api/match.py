# 岗位匹配 API
# 提供两个端点：
#   POST /api/resumes/{resume_id}/matches          — 提交匹配任务，立即返回 match_id
#   GET  /api/resumes/{resume_id}/matches/{match_id} — 查询匹配状态和结果（前端轮询）
#
# 缓存策略：
#   以 resume_id + JD 内容的 SHA-256 哈希为 key，相同简历+相同 JD 命中缓存直接返回，
#   不重复调用 LLM。match_id 通过 match:ref:{match_id} 间接指向缓存 key，
#   支持多次提交相同组合时各自返回独立的 match_id。
import hashlib
import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Body, Cookie, HTTPException

from app.core.cache import get_redis
from app.core.session import session_owns_resume
from app.models.resume import MatchStatusResponse, MatchSubmitResponse
from app.services.scoring_service import score_resume

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])

CACHE_TTL = 3600 * 24  # 匹配结果缓存 24 小时


async def _score_and_store(
    match_id: str, resume_info, job_description: str, cache_key: str
) -> None:
    """后台任务：调用 LLM 评分并将结果存入 Redis。

    结果同时写入：
    - cache_key（按 resume_id + JD 哈希）：供后续相同组合命中缓存
    - match:status:{match_id}：供前端轮询状态
    """
    redis = await get_redis()
    status_key = f"match:status:{match_id}"
    try:
        match_result = await score_resume(resume_info, job_description)
        result_data = {
            "match_id": match_id,
            "match_result": match_result.model_dump(),
            "cached": False,
        }
        result_json = json.dumps(result_data)
        await redis.setex(cache_key, CACHE_TTL, result_json)
        await redis.setex(
            status_key,
            CACHE_TTL,
            json.dumps({"status": "done", "match_id": match_id, "cached": False}),
        )
        logger.info("[match:%s] done", match_id)
    except Exception as e:
        logger.exception("[match:%s] unhandled error: %s", match_id, e)
        await redis.setex(
            status_key, CACHE_TTL, json.dumps({"status": "error", "error": str(e)})
        )


@router.post(
    "/{resume_id}/matches", response_model=MatchSubmitResponse, status_code=202
)
async def submit_match(
    resume_id: str,
    background_tasks: BackgroundTasks,
    job_description: str = Body(..., embed=True),
    session_id: str | None = Cookie(default=None),
):
    """提交岗位匹配任务。立即返回 match_id（202 Accepted），后台异步评分。
    前端应轮询 GET /api/resumes/{resume_id}/matches/{match_id} 获取结果。
    """
    if not session_id or not await session_owns_resume(session_id, resume_id):
        raise HTTPException(status_code=404, detail="Resume not found")

    redis = await get_redis()

    # 确认简历已解析完成（resume:id:{id} 存在）
    resume_data = await redis.get(f"resume:id:{resume_id}")
    if not resume_data:
        raise HTTPException(
            status_code=404, detail="Resume not found or not yet parsed"
        )

    from app.models.resume import ResumeAnalysisResponse

    resume_response = ResumeAnalysisResponse(**json.loads(resume_data))

    # 以 JD 内容的 SHA-256 哈希构造缓存 key，相同 JD 命中缓存
    jd_hash = hashlib.sha256(job_description.encode()).hexdigest()
    cache_key = f"match:{resume_id}:{jd_hash}"

    match_id = str(uuid.uuid4())
    status_key = f"match:status:{match_id}"

    cached_raw = await redis.get(cache_key)
    if cached_raw:
        # 缓存命中：直接将状态标记为 done，通过 ref 指向缓存结果
        logger.info("[match:%s] cache hit for resume=%s", match_id, resume_id)
        await redis.setex(
            status_key,
            CACHE_TTL,
            json.dumps({"status": "done", "match_id": match_id, "cached": True}),
        )
        # match:ref:{match_id} 存储指向实际结果的 cache_key，供 GET 接口查询
        await redis.setex(f"match:ref:{match_id}", CACHE_TTL, cache_key)
    else:
        # 缓存未命中：写入 pending 状态并启动后台评分任务
        await redis.setex(
            status_key,
            CACHE_TTL,
            json.dumps({"status": "pending", "match_id": match_id}),
        )
        await redis.setex(f"match:ref:{match_id}", CACHE_TTL, cache_key)
        background_tasks.add_task(
            _score_and_store,
            match_id,
            resume_response.resume_info,
            job_description,
            cache_key,
        )

    return MatchSubmitResponse(match_id=match_id)


@router.get("/{resume_id}/matches/{match_id}", response_model=MatchStatusResponse)
async def get_match(
    resume_id: str,
    match_id: str,
    session_id: str | None = Cookie(default=None),
):
    """查询匹配任务状态和结果。前端通过轮询此接口等待评分完成。"""
    if not session_id or not await session_owns_resume(session_id, resume_id):
        raise HTTPException(status_code=404, detail="Resume not found")

    redis = await get_redis()
    status_raw = await redis.get(f"match:status:{match_id}")
    if not status_raw:
        raise HTTPException(status_code=404, detail="Match job not found")

    status_data = json.loads(status_raw)
    status = status_data.get("status", "pending")

    if status == "done":
        # 通过 ref key 找到实际结果（间接引用设计，支持缓存复用）
        ref_key = await redis.get(f"match:ref:{match_id}")
        if ref_key:
            result_raw = await redis.get(ref_key)
            if result_raw:
                data = json.loads(result_raw)
                from app.models.resume import MatchResult

                return MatchStatusResponse(
                    match_id=match_id,
                    status="done",
                    match_result=MatchResult(**data["match_result"]),
                    cached=status_data.get("cached", False),
                )

    if status == "error":
        return MatchStatusResponse(
            match_id=match_id,
            status="error",
            error=status_data.get("error"),
        )

    return MatchStatusResponse(match_id=match_id, status="pending")
