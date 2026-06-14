"""
Analysis Worker — 消费分析任务队列

消费 Redis Stream stream:analysis，执行 AI 分析。
与 Docking Worker 架构相同，消费者组模式。
"""

import asyncio
import json
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.redis import (
    init_redis,
    stream_read_group,
    stream_ack,
    stream_create_consumer_group,
    get_redis,
)
from app.tools.llm.chains import LLMChain


class AnalysisWorker:
    """AI 分析 Worker"""

    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"analysis-worker-{uuid.uuid4().hex[:8]}"
        self.llm_chain = LLMChain()
        self.running = True

    async def start(self):
        """启动 Worker 主循环"""
        from app.core.config import get_settings
        from app.core.logger import get_logger

        settings = get_settings()
        logger = get_logger("worker.analysis")

        await init_redis()
        await stream_create_consumer_group(settings.REDIS_STREAM_ANALYSIS, settings.REDIS_CONSUMER_GROUP)

        logger.info(f"AnalysisWorker [{self.worker_id}] 开始消费")

        while self.running:
            try:
                messages = await stream_read_group(
                    settings.REDIS_STREAM_ANALYSIS,
                    settings.REDIS_CONSUMER_GROUP,
                    self.worker_id,
                    count=1,
                    block=5000,
                )

                for msg in messages:
                    task_data = msg["data"]
                    job_id = task_data.get("job_id", "")

                    # 执行 AI 分析
                    # 实际数据从 MySQL 和 MinIO 获取
                    logger.info(f"Analysis 任务处理: job={job_id}")
                    logger.info("Analysis Worker: AI 分析任务占位 - 实际分析由 AnalysisAgent 驱动")

                    await stream_ack(settings.REDIS_STREAM_ANALYSIS, settings.REDIS_CONSUMER_GROUP, msg["id"])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Analysis Worker 异常: {e}", exc_info=True)
                await asyncio.sleep(1)

    def stop(self):
        self.running = False
