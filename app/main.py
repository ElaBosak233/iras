# FastAPI 应用入口
# 负责：日志配置、应用生命周期管理（lifespan）、CORS 中间件、路由注册、
# 以及会话创建端点。
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
    """应用生命周期：启动时无需初始化（Redis 懒加载），关闭时释放连接。"""
    yield
    await close_redis()


app = FastAPI(
    title="IRAS - Intelligent Resume Analysis System",
    description="AI-powered resume parsing, extraction, and job matching",
    version="1.0.0",
    lifespan=lifespan,
)

# 允许本地前端开发服务器跨域访问，生产环境需替换为实际域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,  # 必须为 True，否则 Cookie 无法跨域传递
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router, prefix="/api")
app.include_router(match.router, prefix="/api")


@app.post("/api/sessions", status_code=201)
async def create_session_endpoint(response: Response):
    """显式创建新会话（可选）。首次上传简历时也会自动创建会话。"""
    from app.core.session import create_session

    session_id = await create_session()
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=3600 * 24 * 7,
        httponly=True,   # 防止 JS 读取 Cookie，降低 XSS 风险
        samesite="lax",  # 允许同站跳转携带 Cookie，阻止跨站请求伪造
    )
    return {"session_id": session_id}


@app.get("/health")
async def health():
    """健康检查端点，供负载均衡器或监控系统探活。"""
    return {"status": "ok"}
