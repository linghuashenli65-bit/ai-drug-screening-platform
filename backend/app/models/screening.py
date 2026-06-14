"""
筛选任务模型 (screening_jobs)

一次完整筛选任务（用户视角），是整个系统核心业务实体。
状态机：CREATED→PREPARING→DOCKING→ANALYZING→REPORTING→COMPLETED
"""

from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScreeningJob(Base):
    """筛选任务主表

    一次筛选任务 = 一个配体分子 × 一个靶点受体 × 整个药物库。
    状态机流转由 LangGraph 工作流驱动。
    """

    __tablename__ = "screening_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    molecule_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("molecules.id"), nullable=True, index=True)
    receptor_id: Mapped[int] = mapped_column(Integer, ForeignKey("receptors.id"), nullable=False, index=True)
    job_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CREATED", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_drugs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    finished_drugs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    project: Mapped["Project"] = relationship("Project", back_populates="screening_jobs", lazy="selectin")
    molecule: Mapped["Molecule"] = relationship("Molecule", back_populates="screening_jobs", lazy="selectin")
    receptor: Mapped["Receptor"] = relationship("Receptor", back_populates="screening_jobs", lazy="selectin")
    docking_tasks: Mapped[list["DockingTask"]] = relationship("DockingTask", back_populates="job", lazy="selectin")
    interaction_analyses: Mapped[list["InteractionAnalysis"]] = relationship("InteractionAnalysis", back_populates="job", lazy="selectin")
    ai_analysis_results: Mapped[list["AIAnalysisResult"]] = relationship("AIAnalysisResult", back_populates="job", lazy="selectin")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="job", lazy="selectin")
    agent_runs: Mapped[list["AgentRun"]] = relationship("AgentRun", back_populates="job", lazy="selectin")
