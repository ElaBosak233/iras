import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import resume, match
from app.core.cache import close_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="IRAS - Intelligent Resume Analysis System",
    description="AI-powered resume parsing, extraction, and job matching",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router, prefix="/api")
app.include_router(match.router, prefix="/api")


@app.post("/api/sessions", status_code=201)
async def create_session_endpoint(response: Response):
    """Explicitly create a new session (optional — sessions are also auto-created on first upload)."""
    from app.core.session import create_session

    session_id = await create_session()
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=3600 * 24 * 7,
        httponly=True,
        samesite="lax",
    )
    return {"session_id": session_id}


@app.get("/health")
async def health():
    return {"status": "ok"}
