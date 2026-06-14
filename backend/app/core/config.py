"""
统一配置管理

使用 pydantic-settings 管理所有环境变量和应用配置。
配置来源优先级：环境变量 > .env 文件 > 默认值
"""

import logging
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 应用 ──
    APP_NAME: str = "AI Drug Screening Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-a-strong-random-secret"

    @property
    def validated_secret_key(self) -> str:
        """验证 SECRET_KEY 安全性

        非 DEBUG 模式下使用默认 SECRET_KEY 会记录严重警告。
        """
        if not self.DEBUG and self.SECRET_KEY == "change-me-in-production-use-a-strong-random-secret":
            logging.getLogger(__name__).critical(
                "生产环境使用了默认 SECRET_KEY！请立即设置环境变量 SECRET_KEY。"
            )
        return self.SECRET_KEY

    # ── 服务器 ──
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── MySQL ──
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_DATABASE: str = "drug_screening"
    MYSQL_POOL_SIZE: int = 20
    MYSQL_MAX_OVERFLOW: int = 40
    MYSQL_POOL_RECYCLE: int = 3600
    MYSQL_ECHO: bool = False

    @property
    def MYSQL_URL(self) -> str:
        """同步 MySQL 连接 URL (SQLAlchemy 1.x style)"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @property
    def MYSQL_URL_ASYNC(self) -> str:
        """异步 MySQL 连接 URL"""
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    # ── Redis ──
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 10

    # Redis Streams
    REDIS_STREAM_DOCKING: str = "stream:docking"
    REDIS_STREAM_ANALYSIS: str = "stream:analysis"
    REDIS_STREAM_REPORT: str = "stream:report"
    REDIS_STREAM_AGENT: str = "stream:agent"
    REDIS_CONSUMER_GROUP: str = "worker-group"

    # Redis 运行态缓存 TTL (秒)
    REDIS_PROGRESS_TTL: int = 86400  # 24h
    REDIS_LOCK_TTL: int = 300  # 5min

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── Milvus ──
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "drug_embeddings"
    MILVUS_VECTOR_DIM: int = 2048  # Morgan fingerprint 2048-bit
    MILVUS_INDEX_TYPE: str = "IVF_FLAT"
    MILVUS_METRIC_TYPE: str = "L2"
    MILVUS_NLIST: int = 1024

    # ── MinIO (对象存储) ──
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_MOLECULES: str = "molecules"
    MINIO_BUCKET_DOCKING: str = "docking-results"
    MINIO_BUCKET_REPORTS: str = "reports"

    # ── JWT ──
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── LLM ──
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"
    LLM_FALLBACK_MODEL: str = "gpt-4o-mini"
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT: int = 60

    # ── AutoDock Vina ──
    VINA_EXECUTABLE: str = "vina"
    VINA_EXHAUSTIVENESS: int = 8
    VINA_NUM_MODES: int = 9
    VINA_ENERGY_RANGE: int = 3
    VINA_TIMEOUT: int = 300  # 每个 docking 任务超时(秒)
    DOCKING_SIMULATION_MODE: bool = True  # 当 Vina/RDKit 不可用时使用模拟结果

    # ── Worker ──
    DOCKING_WORKER_CONCURRENCY: int = 4
    ANALYSIS_WORKER_CONCURRENCY: int = 2
    REPORT_WORKER_CONCURRENCY: int = 2
    TASK_MAX_RETRIES: int = 3
    TASK_RETRY_BACKOFF_BASE: int = 2  # 指数退避基数(秒)

    # ── 文件上传 ──
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_UPLOAD_EXTENSIONS: list[str] = [".sdf", ".mol2", ".pdb", ".pdbqt", ".smi", ".csv"]

    # ── 安全 ──
    PROMPT_INJECTION_PATTERNS: list[str] = [
        "ignore previous instructions",
        "ignore all previous",
        "system prompt",
        "<|im_start|>",
        "<|im_end|>",
        "DAN mode",
        "jailbreak",
    ]

    # ── 业务配置 ──
    DRUG_LIBRARY_MAX_SIZE: int = 50000
    SCREENING_TOP_N: int = 100
    ANALYSIS_TOP_N: int = 20
    REPORT_DEFAULT_FORMAT: str = "pdf"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例（缓存）"""
    return Settings()
