"""
Docking Agent — AutoDock 任务调度

职责：
- 任务拆分：将药库拆分为独立的 Docking 子任务
- 调度 Docking Worker：将子任务推入 Redis Stream
- 结果汇总：收集所有 Worker 返回的结果
- 失败重试：检测失败任务并重新调度

输入: {"drug_list": [...], "receptor_id": 1, "ligand_pdbqt": "minio://..."}
输出: {"docking_results": [...], "total_docked": 5000}
"""

import asyncio
import json
from typing import Any

from app.agents.base import BaseAgent
from app.core.config import get_settings
from app.core.constants import DockingTaskStatus
from app.core.redis import stream_add, get_redis
from app.tools.autodock.task_builder import AutoDockTaskBuilder

settings = get_settings()


class DockingAgent(BaseAgent):
    """Docking 调度 Agent

    将药物库拆分为独立子任务，推入 Redis Stream 队列。
    Worker 集群消费队列并执行 AutoDock Vina 计算。
    """

    name = "DockingAgent"
    description = "任务拆分、Worker 调度、结果汇总、失败重试"

    def __init__(self):
        super().__init__()
        self.task_builder = AutoDockTaskBuilder()

    def _validate_input(self, state: dict[str, Any]) -> None:
        drug_list = state.get("drug_list", [])
        if not drug_list:
            raise ValueError("DockingAgent: drug_list 为空，无法创建对接任务")

    async def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        drug_list = state["drug_list"]
        job_id = state["task_id"]
        receptor_id = state.get("receptor_id")

        # Step 1: 拆分任务
        build_result = self.task_builder.build_tasks(
            drug_list=drug_list,
            job_id=job_id,
            receptor_id=receptor_id,
            batch_size=100,
        )

        tasks = build_result.data["tasks"]
        batches = build_result.data["batches"]
        total_tasks = build_result.data["total_tasks"]

        self.logger.info(f"创建 {total_tasks} 个 Docking 子任务，{len(batches)} 个批次")

        # Step 2: 在 MySQL 中创建 DockingTask 记录
        await self._create_db_records(tasks, job_id)

        # Step 3: 将子任务推入 Redis Stream
        enqueued = await self._enqueue_tasks(tasks, job_id)

        # Step 4: 等待所有任务完成（轮询 MySQL）
        self.logger.info(f"等待 {total_tasks} 个 Docking 任务完成...")
        await self._wait_for_completion(job_id, total_tasks, timeout=7200)

        # Step 5: 从 MySQL 加载完成的结果
        docking_results = await self._load_results(job_id)
        self.logger.info(f"加载 {len(docking_results)} 个 Docking 结果")

        return {
            "docking_tasks": tasks,
            "docking_results": docking_results,
            "total_docked": len(docking_results),
            "total_tasks": total_tasks,
            "enqueued_count": enqueued,
            "job_id": job_id,
        }

    async def _wait_for_completion(self, job_id: int, total: int, timeout: int = 7200):
        """轮询 MySQL 等待所有 Docking 任务完成"""
        from sqlalchemy import select, func
        from app.core.database import AsyncSessionLocal
        from app.models.docking import DockingTask

        start = asyncio.get_event_loop().time()
        while True:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(func.count(DockingTask.id)).where(
                        DockingTask.job_id == job_id,
                        DockingTask.status.in_(["SUCCESS", "FAILED"]),
                    )
                )
                finished = result.scalar() or 0

            if finished >= total:
                self.logger.info(f"Job {job_id}: 所有 Docking 任务完成 ({finished}/{total})")
                break

            elapsed = asyncio.get_event_loop().time() - start
            if elapsed > timeout:
                self.logger.warning(f"Job {job_id}: Docking 超时，已完成 {finished}/{total}")
                break

            if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                self.logger.info(f"Job {job_id}: Docking 进度 {finished}/{total}")

            await asyncio.sleep(5)

    async def _load_results(self, job_id: int) -> list[dict]:
        """从 MySQL 加载已完成的 Docking 结果"""
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.docking import DockingTask
        from app.models.molecule import DrugLibrary

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(DockingTask, DrugLibrary.drug_name)
                .outerjoin(DrugLibrary, DockingTask.drug_id == DrugLibrary.id)
                .where(
                    DockingTask.job_id == job_id,
                    DockingTask.status == "SUCCESS",
                )
            )
            rows = result.all()

        return [
            {
                "drug_id": task.drug_id,
                "drug_name": drug_name or "",
                "affinity_score": float(task.affinity_score) if task.affinity_score else None,
            }
            for task, drug_name in rows
        ]

    async def _create_db_records(self, tasks: list[dict], job_id: int):
        """在 MySQL 中批量创建 DockingTask 记录（状态 PENDING）

        去重逻辑：跳过已存在的 (job_id, drug_id) 组合，防止工作流重试时重复插入。
        """
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.docking import DockingTask

        async with AsyncSessionLocal() as session:
            existing = await session.execute(
                select(DockingTask.drug_id).where(DockingTask.job_id == job_id)
            )
            existing_drug_ids = {row[0] for row in existing.all()}

            created = 0
            for task in tasks:
                if task["drug_id"] in existing_drug_ids:
                    continue
                record = DockingTask(
                    job_id=job_id,
                    drug_id=task["drug_id"],
                    status="PENDING",
                )
                session.add(record)
                created += 1
            await session.commit()

        self.logger.info(f"已创建 {created} 条 DockingTask 记录 (跳过 {len(tasks) - created} 条已存在)")

    async def _enqueue_tasks(self, tasks: list[dict], job_id: int) -> int:
        """将子任务推入 Redis Stream

        Args:
            tasks: 子任务列表
            job_id: 任务 ID

        Returns:
            入队任务数
        """
        count = 0
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
            count += 1

        self.logger.info(f"{count} 个 Docking 任务已入队: {settings.REDIS_STREAM_DOCKING}")
        return count

    async def collect_results(self, job_id: int, timeout: int = 3600) -> dict[str, Any]:
        """收集 Docking Worker 返回的结果（轮询模式）

        实际生产环境建议使用异步回调或 SSE 推送，
        此方法用于 demo/测试场景。

        Args:
            job_id: 筛选任务 ID
            timeout: 最大等待时间 (秒)

        Returns:
            汇总结果
        """
        r = get_redis()
        status_key = f"job:{job_id}:progress"
        start_time = asyncio.get_event_loop().time()

        while True:
            progress = await r.hgetall(status_key)
            finished = int(progress.get("finished_drugs", 0))
            total = int(progress.get("total_drugs", 0))

            if total > 0 and finished >= total:
                break

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                self.logger.warning(f"Docking 收集超时: finished={finished}/{total}")
                break

            await asyncio.sleep(2)

        return {
            "total_drugs": total,
            "finished_drugs": finished,
            "status": "completed" if finished >= total else "timeout",
        }

    def _format_output(self, output: dict[str, Any]) -> dict[str, Any]:
        return {
            "total_tasks": output.get("total_tasks", 0),
            "enqueued_count": output.get("enqueued_count", 0),
            "docking_results": output.get("docking_results", []),
            "total_docked": output.get("total_docked", 0),
            "docking_started": True,
        }
