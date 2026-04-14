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

CACHE_TTL = 3600 * 24


async def _score_and_store(
    match_id: str, resume_info, job_description: str, cache_key: str
) -> None:
    """Background task: score resume and store result in Redis."""
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
    """Start an async match job; returns match_id immediately."""
    if not session_id or not await session_owns_resume(session_id, resume_id):
        raise HTTPException(status_code=404, detail="Resume not found")

    redis = await get_redis()

    resume_data = await redis.get(f"resume:id:{resume_id}")
    if not resume_data:
        raise HTTPException(
            status_code=404, detail="Resume not found or not yet parsed"
        )

    from app.models.resume import ResumeAnalysisResponse

    resume_response = ResumeAnalysisResponse(**json.loads(resume_data))

    jd_hash = hashlib.sha256(job_description.encode()).hexdigest()
    cache_key = f"match:{resume_id}:{jd_hash}"

    # Check result cache — if hit, create a match_id pointing to cached result
    cached_raw = await redis.get(cache_key)
    match_id = str(uuid.uuid4())
    status_key = f"match:status:{match_id}"

    if cached_raw:
        logger.info("[match:%s] cache hit for resume=%s", match_id, resume_id)
        await redis.setex(
            status_key,
            CACHE_TTL,
            json.dumps({"status": "done", "match_id": match_id, "cached": True}),
        )
        # Store a reference so GET can find the result
        await redis.setex(f"match:ref:{match_id}", CACHE_TTL, cache_key)
    else:
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
    """Poll match job status and result."""
    if not session_id or not await session_owns_resume(session_id, resume_id):
        raise HTTPException(status_code=404, detail="Resume not found")

    redis = await get_redis()
    status_raw = await redis.get(f"match:status:{match_id}")
    if not status_raw:
        raise HTTPException(status_code=404, detail="Match job not found")

    status_data = json.loads(status_raw)
    status = status_data.get("status", "pending")

    if status == "done":
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
