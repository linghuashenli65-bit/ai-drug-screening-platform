"""
报告模型 (reports)

最终筛选结果报告，支持 PDF/HTML/Markdown 三种格式。
报告文件存储于 MinIO，MySQL 只保存 URI。
"""

from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Report(Base):
    """筛选结果报告

    每个 screening_job 可生成多个报告（不同格式）。
    文件存储于 MinIO，uri 格式: minio://reports/{job_id}/{filename}
    """

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("screening_jobs.id"), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    report_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    job: Mapped["ScreeningJob"] = relationship("ScreeningJob", back_populates="reports", lazy="selectin")
