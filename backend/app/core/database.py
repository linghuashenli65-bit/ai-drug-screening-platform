"""
MySQL 数据库连接管理

使用 SQLAlchemy 2.0 异步引擎，提供 session 依赖注入和生命周期管理。
MySQL 是任务状态的真相来源（source of truth）。
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# 异步引擎
async_engine = create_async_engine(
    settings.MYSQL_URL_ASYNC,
    pool_size=settings.MYSQL_POOL_SIZE,
    max_overflow=settings.MYSQL_MAX_OVERFLOW,
    pool_recycle=settings.MYSQL_POOL_RECYCLE,
    echo=settings.MYSQL_ECHO,
    pool_pre_ping=True,  # 连接前检测有效性
)

# 会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类

    所有 ORM 模型均继承此类，自动获得:
    - 声明式映射
    - metadata 集中管理
    """

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：获取数据库会话

    每个请求获取一个独立 session，请求结束后自动关闭。
    async with 退出时 __aexit__ 自动关闭 session，无需手动 close。
    所有 Repository 通过此依赖获得数据库连接。

    Yields:
        AsyncSession: SQLAlchemy 异步会话
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


async def init_db() -> None:
    """初始化数据库表结构

    在应用启动时调用，自动创建所有 ORM 模型对应的表。
    不会删除已有表或数据。
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接池

    在应用关闭时调用，释放所有连接资源。
    """
    await async_engine.dispose()
