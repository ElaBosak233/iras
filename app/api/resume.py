# 简历上传与解析 API
# 提供三个端点：
#   POST /api/resumes        — 上传 PDF，立即返回 resume_id，后台异步解析
#   GET  /api/resumes        — 列出当前会话下所有 resume_id
#   GET  /api/resumes/{id}   — 查询解析状态和结果（前端轮询此接口）
#
# 缓存策略：
#   以 session_id + PDF 哈希为 key，相同 PDF 在同一会话内命中缓存直接返回，
#   不重复调用 LLM，节省 API 费用。
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

CACHE_TTL = 3600 * 24  # 简历数据缓存 24 小时


async def _get_or_create_session(session_id: str | None, response: Response) -> str:
    """获取现有会话或创建新会话，并在响应中设置 session_id Cookie。"""
    if session_id and await session_exists(session_id):
        return session_id
    new_id = await create_session()
    response.set_cookie(
        key="session_id",
        value=new_id,
        max_age=3600 * 24 * 7,
        httponly=True,   # 防止 JS 读取，降低 XSS 风险
        samesite="lax",
    )
    return new_id


async def _parse_and_store(session_id: str, resume_id: str, pdf_bytes: bytes) -> None:
    """后台任务：解析 PDF 并将结果存入 Redis。

    流程：
    1. 调用 parse_pdf 提取文本并计算 PDF 哈希
    2. 检查 session 级别的解析缓存（同一 PDF 不重复调用 LLM）
    3. 缓存未命中时调用 LLM 提取结构化信息
    4. 将结果写入 Redis（resume:id:{id} 和 resume:status:{id}）
    """
    logger.info("[%s] background task started, pdf_size=%d", resume_id, len(pdf_bytes))
    redis = await get_redis()
    status_key = f"resume:status:{resume_id}"
    try:
        logger.info("[%s] parsing PDF...", resume_id)
        text, pdf_hash = await parse_pdf(pdf_bytes)
        logger.info(
            "[%s] PDF parsed, text_len=%d, hash=%s", resume_id, len(text), pdf_hash[:8]
        )

        # 以 session + PDF 哈希为 key 检查缓存，避免同一 PDF 重复调用 LLM
        cache_key = f"session:{session_id}:parse:{pdf_hash}"
        cached = await redis.get(cache_key)
        if cached:
            logger.info("[%s] cache hit, reusing previous result", resume_id)
            try:
                data = json.loads(cached)
                data["cached"] = True
                result = ResumeAnalysisResponse(**data)
                result.resume_id = resume_id  # 更新为当前 resume_id
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
                # 缓存数据损坏时删除并重新解析
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
        # 同时写入解析缓存（按 PDF 哈希）和结果缓存（按 resume_id）
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
    """上传 PDF 简历。立即返回 resume_id（202 Accepted），后台异步解析。
    前端应轮询 GET /api/resumes/{resume_id} 获取解析状态。
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

    sid = await _get_or_create_session(session_id, response)
    resume_id = str(uuid.uuid4())

    # 立即写入 pending 状态，前端可立即开始轮询
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
    """列出当前会话下所有 resume_id，用于页面刷新后恢复历史记录。"""
    if not session_id or not await session_exists(session_id):
        return []
    return await list_session_resumes(session_id)


@router.get("/{resume_id}", response_model=ResumeStatusResponse)
async def get_resume(
    resume_id: str,
    session_id: str | None = Cookie(default=None),
):
    """查询简历解析状态和结果。前端通过轮询此接口等待解析完成。
    若会话不拥有该简历，返回 404（防止越权访问）。
    """
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
