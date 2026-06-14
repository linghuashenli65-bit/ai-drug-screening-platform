"""
FastAPI 应用入口

初始化所有基础设施服务，注册路由和中间件，配置全局异常处理。
生命周期管理：启动时初始化 DB/Redis/Milvus/MinIO，关闭时释放资源。
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.constants import ERROR_CODES
from app.core.database import close_db, init_db
from app.core.exceptions import AppException
from app.core.logger import logger, setup_logger
from app.core.milvus import close_milvus, init_milvus
from app.core.minio import close_minio, init_minio
from app.core.redis import close_redis, init_redis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理

    Startup:
        1. 初始化结构化日志
        2. 初始化 MySQL 连接池 + 创建表
        3. 初始化 Redis 连接池
        4. 初始化 Milvus 连接 + 创建 Collection
        5. 初始化 MinIO 客户端 + 创建 Bucket

    Shutdown:
        1. 关闭 MinIO
        2. 关闭 Milvus
        3. 关闭 Redis
        4. 关闭 MySQL 连接池
    """
    # ── Startup ──
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} ...")

    setup_logger()
    logger.info("日志系统已初始化")

    try:
        await init_db()
        logger.info("MySQL 连接池已初始化")
    except Exception as e:
        logger.warning(f"MySQL 初始化失败 (非致命): {e}")

    try:
        await init_redis()
        logger.info("Redis 连接池已初始化")
    except Exception as e:
        logger.warning(f"Redis 初始化失败 (非致命): {e}")

    try:
        init_milvus()
        logger.info("Milvus 已连接")
    except Exception as e:
        logger.warning(f"Milvus 初始化失败 (非致命): {e}")

    try:
        init_minio()
        logger.info("MinIO 已连接")
    except Exception as e:
        logger.warning(f"MinIO 初始化失败 (非致命): {e}")

    logger.info("所有服务已就绪，开始接收请求")

    yield

    # ── Shutdown ──
    logger.info("正在关闭服务...")

    close_minio()
    close_milvus()
    await close_redis()
    await close_db()

    logger.info("所有服务已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 Agent 的自动化高通量药物虚拟筛选平台",
    lifespan=lifespan,
)

# ── CORS 中间件 ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 请求日志中间件 ──
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """记录每个请求的方法、路径和响应状态码

    成功响应 (2xx/3xx) 用 DEBUG 级别，避免生产日志噪音。
    错误响应 (4xx/5xx) 用 INFO/WARNING 级别。
    """
    response = await call_next(request)
    log_fn = logger.debug if response.status_code < 400 else logger.warning
    log_fn(
        f"{request.method} {request.url.path} → {response.status_code}",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    return response


# ── 全局异常处理器 ──


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """统一处理业务异常，转换为标准 JSON 响应格式

    响应格式:
        {
            "code": 1000,
            "message": "错误描述",
            "detail": null
        }
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底处理未捕获异常

    返回 500 错误，不暴露内部错误详情给客户端。
    错误码使用 5000 系列（工作流/系统级错误）。
    """
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": 5000,
            "message": "服务器内部错误",
            "detail": None,
        },
    )


# ── 健康检查 ──


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """系统健康检查端点"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# ── 注册路由 ──
from app.api import admin, auth, libraries, molecule, project, receptor, report, screening

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(project.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(screening.router, prefix="/api/v1/screenings", tags=["Screening"])
app.include_router(report.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(molecule.router, prefix="/api/v1/molecules", tags=["Molecules"])
app.include_router(receptor.router, prefix="/api/v1/receptors", tags=["Receptors"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(libraries.router, prefix="/api/v1/libraries", tags=["Libraries"])
