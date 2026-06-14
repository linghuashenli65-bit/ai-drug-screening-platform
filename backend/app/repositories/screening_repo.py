"""
Screening Repository — 筛选任务数据访问

封装 screening_jobs 和 docking_tasks 的 CRUD。
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.screening import ScreeningJob
from app.models.docking import DockingTask
from app.core.constants import JobStatus


class ScreeningRepository:
    """筛选任务数据访问"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> ScreeningJob:
        """创建筛选任务"""
        job = ScreeningJob(**kwargs)
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def find_by_id(self, job_id: int) -> Optional[ScreeningJob]:
        """按 ID 查询"""
        result = await self.db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
        return result.scalar_one_or_none()

    async def update_status(self, job_id: int, status: JobStatus, **kwargs) -> Optional[ScreeningJob]:
        """更新任务状态"""
        job = await self.find_by_id(job_id)
        if job:
            job.status = status
            for key, value in kwargs.items():
                setattr(job, key, value)
            await self.db.flush()
        return job

    async def update_progress(self, job_id: int, finished: int, total: int) -> None:
        """更新进度"""
        job = await self.find_by_id(job_id)
        if job:
            job.finished_drugs = finished
            job.total_drugs = total
            job.progress = int(finished / total * 100) if total > 0 else 0
            await self.db.flush()

    async def list_by_project(self, project_id: int, status: str = None, page: int = 1, page_size: int = 20) -> list[ScreeningJob]:
        """按项目查询任务列表"""
        query = select(ScreeningJob).where(ScreeningJob.project_id == project_id)
        if status:
            query = query.where(ScreeningJob.status == status)
        query = query.order_by(ScreeningJob.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_count(self) -> int:
        """活跃任务数"""
        result = await self.db.execute(
            select(func.count(ScreeningJob.id)).where(
                ScreeningJob.status.in_(["CREATED", "PREPARING", "DOCKING", "ANALYZING", "REPORTING"])
            )
        )
        return result.scalar() or 0


class DockingTaskRepository:
    """Docking 子任务数据访问"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def batch_create(self, tasks: list[dict]) -> list[DockingTask]:
        """批量创建 Docking 子任务"""
        entities = [DockingTask(**t) for t in tasks]
        self.db.add_all(entities)
        await self.db.flush()
        return entities

    async def update_result(self, task_id: int, affinity: float, status: str, result_uri: str = "") -> Optional[DockingTask]:
        """更新 Docking 结果"""
        result = await self.db.execute(select(DockingTask).where(DockingTask.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.affinity_score = affinity
            task.status = status
            task.finished_at = datetime.now(timezone.utc)
            if result_uri:
                task.docking_result_uri = result_uri
            await self.db.flush()
        return task

    async def get_top_n(self, job_id: int, n: int = 100) -> list[DockingTask]:
        """获取 Top-N 结果（按 affinity 升序）"""
        result = await self.db.execute(
            select(DockingTask)
            .where(DockingTask.job_id == job_id, DockingTask.affinity_score.isnot(None))
            .order_by(DockingTask.affinity_score.asc())
            .limit(n)
        )
        return list(result.scalars().all())

    async def get_stats(self, job_id: int) -> dict:
        """获取 Docking 统计"""
        total = await self.db.execute(
            select(func.count(DockingTask.id)).where(DockingTask.job_id == job_id)
        )
        success = await self.db.execute(
            select(func.count(DockingTask.id)).where(
                DockingTask.job_id == job_id, DockingTask.status == "SUCCESS"
            )
        )
        failed = await self.db.execute(
            select(func.count(DockingTask.id)).where(
                DockingTask.job_id == job_id, DockingTask.status == "FAILED"
            )
        )
        return {
            "total": total.scalar() or 0,
            "success": success.scalar() or 0,
            "failed": failed.scalar() or 0,
        }
