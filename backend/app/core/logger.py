"""
结构化日志模块

使用 structlog 提供结构化 JSON 日志输出，支持：
- 请求追踪 ID (correlation_id)
- Agent 运行日志
- Tool 调用日志
- Worker 日志
"""

import logging
import sys
from datetime import datetime, timezone

import structlog


def setup_logger() -> structlog.BoundLogger:
    """配置结构化日志

    在应用启动时调用一次。

    Returns:
        配置好的 structlog logger
    """
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer() if sys.stderr.isatty() else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 设置日志级别
    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=logging.INFO)

    return structlog.get_logger()


# 全局 logger 实例
logger = structlog.get_logger()


def get_logger(name: str = None) -> structlog.BoundLogger:
    """获取带名称的 logger 实例

    Args:
        name: Logger 名称（如 "agent.docking", "worker.analysis"）

    Returns:
        BoundLogger 实例
    """
    if name:
        return logger.bind(logger_name=name)
    return logger
