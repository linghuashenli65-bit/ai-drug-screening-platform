"""
Docking 子任务模型 (docking_tasks)

高通量筛选的核心表。一对多的子任务拆分：一个 screening_job 拆分为 N 个 docking_task。
这张表是调度、重试、统计、恢复的关键。
"""

from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DockingTask(Base):
    """Docking 子任务

    每个 DockingTask 对应一个药物与一个靶点的单次对接计算。
    状态：PENDING → QUEUED → RUNNING → SUCCESS / FAILED
    失败可自动重试（retry_count ≤ 3）。
    """

    __tablename__ = "docking_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("screening_jobs.id"), nullable=False, index=True)
    drug_id: Mapped[int] = mapped_column(Integer, ForeignKey("drug_library.id"), nullable=False, index=True)
    affinity_score: Mapped[float] = mapped_column(Numeric(8, 3), nullable=True)
    docking_result_uri: Mapped[str] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 关系
    job: Mapped["ScreeningJob"] = relationship("ScreeningJob", back_populates="docking_tasks", lazy="selectin")
    drug: Mapped["DrugLibrary"] = relationship("DrugLibrary", back_populates="docking_tasks", lazy="selectin")
