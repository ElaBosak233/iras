import json
import logging
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    File,
    HTTPException,
    Response,
    UploadFile,
)

from app.core.cache import get_redis
from app.core.session import (
    add_resume_to_session,
    create_session,
    list_session_resumes,
    session_exists,
    session_owns_resume,
)
from app.models.resume import (
    ResumeAnalysisResponse,
    ResumeStatusResponse,
    ResumeSubmitResponse,
)
from app.services.extraction_service import extract_resume_info
from app.services.pdf_service import parse_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])

CACHE_TTL = 3600 * 24  # 24 hours


async def _get_or_create_session(session_id: str | None, response: Response) -> str:
    if session_id and await session_exists(session_id):
        return session_id
    new_id = await create_session()
    response.set_cookie(
        key="session_id",
        value=new_id,
        max_age=3600 * 24 * 7,
        httponly=True,
        samesite="lax",
    )
    return new_id


async def _parse_and_store(session_id: str, resume_id: str, pdf_bytes: bytes) -> None:
    """Background task: parse PDF and store result in Redis."""
    logger.info("[%s] background task started, pdf_size=%d", resume_id, len(pdf_bytes))
    redis = await get_redis()
    status_key = f"resume:status:{resume_id}"
    try:
        logger.info("[%s] parsing PDF...", resume_id)
        text, pdf_hash = await parse_pdf(pdf_bytes)
        logger.info(
            "[%s] PDF parsed, text_len=%d, hash=%s", resume_id, len(text), pdf_hash[:8]
        )

        # Check parse cache by PDF hash — scoped to session for isolation
        cache_key = f"session:{session_id}:parse:{pdf_hash}"
        cached = await redis.get(cache_key)
        if cached:
            logger.info("[%s] cache hit, reusing previous result", resume_id)
            try:
                data = json.loads(cached)
                data["cached"] = True
                result = ResumeAnalysisResponse(**data)
                result.resume_id = resume_id
                await redis.setex(
                    f"resume:id:{resume_id}", CACHE_TTL, result.model_dump_json()
                )
                await redis.setex(
                    status_key,
                    CACHE_TTL,
                    json.dumps(
                        {"status": "done", "resume_id": resume_id, "cached": True}
                    ),
                )
                logger.info("[%s] done (from cache)", resume_id)
                return
            except Exception as cache_err:
                logger.warning(
                    "[%s] cache parse failed, discarding: %s", resume_id, cache_err
                )
                await redis.delete(cache_key)

        if not text.strip():
            logger.error("[%s] no text extracted from PDF", resume_id)
            await redis.setex(
                status_key,
                CACHE_TTL,
                json.dumps(
                    {"status": "error", "error": "Could not extract text from PDF"}
                ),
            )
            return

        logger.info("[%s] calling LLM for extraction...", resume_id)
        resume_info = await extract_resume_info(text)
        logger.info("[%s] LLM extraction done", resume_id)

        result = ResumeAnalysisResponse(
            resume_id=resume_id, resume_info=resume_info, cached=False
        )

        result_json = result.model_dump_json()
        await redis.setex(cache_key, CACHE_TTL, result_json)
        await redis.setex(f"resume:id:{resume_id}", CACHE_TTL, result_json)
        await redis.setex(
            status_key,
            CACHE_TTL,
            json.dumps({"status": "done", "resume_id": resume_id, "cached": False}),
        )
        logger.info("[%s] done", resume_id)
    except Exception as e:
        logger.exception("[%s] unhandled error: %s", resume_id, e)
        await redis.setex(
            status_key, CACHE_TTL, json.dumps({"status": "error", "error": str(e)})
        )


@router.post("", response_model=ResumeSubmitResponse, status_code=202)
async def submit_resume(
    background_tasks: BackgroundTasks,
    response: Response,
    file: UploadFile = File(...),
    session_id: str | None = Cookie(default=None),
):
    """Upload a PDF resume; returns resume_id immediately and parses in background."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

    sid = await _get_or_create_session(session_id, response)
    resume_id = str(uuid.uuid4())

    redis = await get_redis()
    await redis.setex(
        f"resume:status:{resume_id}",
        CACHE_TTL,
        json.dumps({"status": "pending", "resume_id": resume_id}),
    )

    await add_resume_to_session(sid, resume_id)
    background_tasks.add_task(_parse_and_store, sid, resume_id, pdf_bytes)

    return ResumeSubmitResponse(resume_id=resume_id)


@router.get("", response_model=list[str])
async def list_resumes(session_id: str | None = Cookie(default=None)):
    """List all resume IDs belonging to the current session."""
    if not session_id or not await session_exists(session_id):
        return []
    return await list_session_resumes(session_id)


@router.get("/{resume_id}", response_model=ResumeStatusResponse)
async def get_resume(
    resume_id: str,
    session_id: str | None = Cookie(default=None),
):
    """Get parsing status and result for a resume."""
    if not session_id or not await session_owns_resume(session_id, resume_id):
        raise HTTPException(status_code=404, detail="Resume not found")

    redis = await get_redis()
    status_raw = await redis.get(f"resume:status:{resume_id}")
    if not status_raw:
        raise HTTPException(status_code=404, detail="Resume not found")

    status_data = json.loads(status_raw)
    status = status_data.get("status", "pending")

    if status == "done":
        result_raw = await redis.get(f"resume:id:{resume_id}")
        if result_raw:
            result = ResumeAnalysisResponse(**json.loads(result_raw))
            return ResumeStatusResponse(
                resume_id=resume_id,
                status="done",
                resume_info=result.resume_info,
                cached=status_data.get("cached", False),
            )

    if status == "error":
        return ResumeStatusResponse(
            resume_id=resume_id,
            status="error",
            error=status_data.get("error"),
        )

    return ResumeStatusResponse(resume_id=resume_id, status="pending")
