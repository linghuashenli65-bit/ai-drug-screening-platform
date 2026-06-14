"""
Report Worker — 消费报告生成任务队列

消费 Redis Stream stream:report，执行报告生成。
支持 PDF/Markdown/HTML 三种格式。
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
)


class ReportWorker:
    """报告生成 Worker"""

    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"report-worker-{uuid.uuid4().hex[:8]}"
        self.running = True

    async def start(self):
        """启动 Worker 主循环"""
        from app.core.config import get_settings
        from app.core.logger import get_logger

        settings = get_settings()
        logger = get_logger("worker.report")

        await init_redis()
        await stream_create_consumer_group(settings.REDIS_STREAM_REPORT, settings.REDIS_CONSUMER_GROUP)

        logger.info(f"ReportWorker [{self.worker_id}] 开始消费")

        while self.running:
            try:
                messages = await stream_read_group(
                    settings.REDIS_STREAM_REPORT,
                    settings.REDIS_CONSUMER_GROUP,
                    self.worker_id,
                    count=1,
                    block=5000,
                )

                for msg in messages:
                    task_data = msg["data"]
                    job_id = task_data.get("job_id", "")
                    report_format = task_data.get("format", "pdf")

                    logger.info(f"Report 任务处理: job={job_id}, format={report_format}")
                    # 实际报告生成由 ReportAgent 驱动
                    logger.info("Report Worker: 报告生成占位 - 实际由 ReportAgent 驱动")

                    await stream_ack(settings.REDIS_STREAM_REPORT, settings.REDIS_CONSUMER_GROUP, msg["id"])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Report Worker 异常: {e}", exc_info=True)
                await asyncio.sleep(1)

    def stop(self):
        self.running = False
