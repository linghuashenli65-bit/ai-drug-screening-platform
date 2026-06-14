"""
任务调度器 — 分发、重试、失败恢复

职责：
- 当新 screening_job 创建后，将子任务分发给 worker 队列
- 监控任务状态，触发重试
- 检测 Worker 崩溃并重新分配任务
- 更新 job 级进度到 Redis 和 MySQL
"""

import asyncio
import json
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.constants import JobStatus, DockingTaskStatus
from app.core.database import AsyncSessionLocal
from app.core.logger import get_logger
from app.core.redis import (
    cache_job_progress,
    get_redis,
    stream_add,
    stream_ack,
    stream_claim_pending,
    stream_create_consumer_group,
    stream_pending,
)

settings = get_settings()
logger = get_logger("worker.scheduler")


class Scheduler:
    """任务调度器

    监控所有活跃任务，负责分发、重试、进度更新。
    """

    def __init__(self):
        self.running = True
        self.poll_interval = 5  # 轮询间隔 (秒)

    async def start(self):
        """启动调度器主循环"""
        logger.info("Scheduler 启动中...")

        # 创建所有消费者组
        for stream in [settings.REDIS_STREAM_DOCKING, settings.REDIS_STREAM_ANALYSIS, settings.REDIS_STREAM_REPORT]:
            await stream_create_consumer_group(stream, settings.REDIS_CONSUMER_GROUP)

        logger.info("Scheduler 开始调度")

        while self.running:
            try:
                await self._tick()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"调度器异常: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

        logger.info("Scheduler 已停止")

    async def _tick(self):
        """单次调度周期"""
        # 1. 检查超时的 Docking 任务并重新分配
        await self._handle_timeout_tasks()

        # 2. 更新所有活跃 job 的进度汇总
        await self._sync_job_progress()

        # 3. 检查是否需要重试失败任务
        await self._handle_retry_tasks()

    async def _handle_timeout_tasks(self):
        """处理超时未确认的任务（Worker 崩溃恢复）

        将超时任务认领到新的消费者名下重新处理。
        """
        pending = await stream_pending(settings.REDIS_STREAM_DOCKING, settings.REDIS_CONSUMER_GROUP, count=50)

        timeout_ids = [p for p in pending if p.get("idle_ms", 0) > 60000]
        if timeout_ids:
            logger.info(f"发现 {len(timeout_ids)} 个超时 Docking 任务，将重新分配")

            claimed = await stream_claim_pending(
                settings.REDIS_STREAM_DOCKING,
                settings.REDIS_CONSUMER_GROUP,
                "scheduler-recovery",
                min_idle_ms=60000,
            )
            logger.info(f"已重新分配 {len(claimed)} 个超时任务")

    async def _sync_job_progress(self):
        """同步所有活跃 Job 的进度到 Redis，并在 Docking 完成后推进状态"""
        from sqlalchemy import select, func

        async with AsyncSessionLocal() as session:
            from app.models.screening import ScreeningJob
            from app.models.docking import DockingTask
            from app.core.redis import cache_top_hits

            result = await session.execute(
                select(ScreeningJob).where(
                    ScreeningJob.status.notin_(["COMPLETED", "FAILED", "CANCELLED"])
                )
            )
            active_jobs = result.scalars().all()

            for job in active_jobs:
                finished = await session.execute(
                    select(func.count(DockingTask.id)).where(
                        DockingTask.job_id == job.id,
                        DockingTask.status.in_(["SUCCESS", "FAILED"]),
                    )
                )
                total = await session.execute(
                    select(func.count(DockingTask.id)).where(DockingTask.job_id == job.id)
                )

                finished_count = finished.scalar() or 0
                total_count = total.scalar() or 0
                progress = int(finished_count / total_count * 100) if total_count > 0 else 0

                # 更新 MySQL
                job.finished_drugs = finished_count
                job.total_drugs = total_count
                job.progress = progress

                # 检查 Docking 是否全部完成 → 推进状态到 COMPLETED
                if job.status in ("CREATED", "PREPARING", "DOCKING") and total_count > 0 and finished_count >= total_count:
                    job.status = "COMPLETED"
                    job.progress = 100
                    logger.info(f"Job {job.id}: Docking 全部完成 ({finished_count}/{total_count})，状态更新为 COMPLETED")

                    # 缓存 Top Hits
                    top_results = await session.execute(
                        select(DockingTask).where(
                            DockingTask.job_id == job.id,
                            DockingTask.status == "SUCCESS",
                            DockingTask.affinity_score.isnot(None),
                        ).order_by(DockingTask.affinity_score.asc()).limit(20)
                    )
                    top_tasks = top_results.scalars().all()
                    hits = []
                    for rank, t in enumerate(top_tasks, 1):
                        hits.append({
                            "rank": rank,
                            "drug_id": t.drug_id,
                            "drug_name": t.drug.drug_name if t.drug else f"Drug-{t.drug_id}",
                            "affinity_score": float(t.affinity_score) if t.affinity_score is not None else None,
                        })
                    if hits:
                        await cache_top_hits(job.id, hits, ttl=86400)

                    # 写入后续节点的日志
                    r = get_redis()
                    for node_id in ["ranking", "analysis", "report"]:
                        log_key = f"job:{job.id}:node:{node_id}:logs"
                        await r.rpush(log_key, f"[自动完成] 任务已完成，共处理 {finished_count} 个药物")
                        await r.expire(log_key, 86400)

                # 更新 Redis
                await cache_job_progress(job.id, {
                    "status": job.status,
                    "progress": job.progress,
                    "finished_drugs": finished_count,
                    "total_drugs": total_count,
                })

            await session.commit()

    async def _handle_retry_tasks(self):
        """处理需要重试的失败任务"""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            from app.models.docking import DockingTask
            from app.models.molecule import DrugLibrary
            from app.models.screening import ScreeningJob

            # 查询失败且未超过最大重试次数的任务（关联加载 drug 信息）
            result = await session.execute(
                select(DockingTask)
                .options(selectinload(DockingTask.drug))
                .where(
                    DockingTask.status == "FAILED",
                    DockingTask.retry_count < settings.TASK_MAX_RETRIES,
                )
            )
            retry_tasks = result.scalars().all()

            for task in retry_tasks:
                task.status = "RETRYING"
                task.retry_count += 1

                # 构造完整 task_data（包含 smiles、pdbqt_uri 等）
                drug = task.drug
                task_payload = {
                    "drug_id": task.drug_id,
                    "job_id": task.job_id,
                    "drug_name": drug.drug_name if drug else "",
                    "smiles": drug.smiles if drug else "",
                    "ligand_pdbqt": drug.pdbqt_uri or "" if drug else "",
                    "receptor_id": task.job.receptor_id if task.job else 0,
                }

                await stream_add(
                    settings.REDIS_STREAM_DOCKING,
                    {
                        "job_id": str(task.job_id),
                        "drug_id": str(task.drug_id),
                        "drug_name": task_payload["drug_name"],
                        "task_data": json.dumps(task_payload, ensure_ascii=False),
                    },
                )
                logger.info(f"重试 Docking 任务: job={task.job_id}, drug={task.drug_id}, retry={task.retry_count}")

            await session.commit()

    async def dispatch_job(self, job_id: int, tasks: list[dict]):
        """分发一个新 Job 的全部子任务到队列

        Args:
            job_id: 筛选任务 ID
            tasks: Docking 子任务列表
        """
        for task in tasks:
            await stream_add(
                settings.REDIS_STREAM_DOCKING,
                {
                    "job_id": str(job_id),
                    "drug_id": str(task["drug_id"]),
                    "drug_name": task.get("drug_name", ""),
                    "task_data": json.dumps(task, ensure_ascii=False),
                },
            )

        logger.info(f"Job {job_id}: 已分发 {len(tasks)} 个 Docking 子任务")

    def stop(self):
        """停止调度器"""
        self.running = False


async def main():
    """Scheduler 入口"""
    import signal
    from app.core.database import init_db
    from app.core.redis import init_redis
    from app.core.logger import setup_logger

    setup_logger()
    await init_redis()
    await init_db()

    scheduler = Scheduler()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, scheduler.stop)

    await scheduler.start()


if __name__ == "__main__":
    asyncio.run(main())
