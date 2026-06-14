"""
审计日志模型 (audit_logs)

记录所有用户操作：登录、创建任务、删除报告、上传分子等。
用于安全审计和合规追踪。
"""

from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditLog(Base):
    """用户操作审计日志

    记录谁(who)、何时(when)、做了什么(what)：
    - 操作类型 (action): create_screening, delete_report, upload_molecule, login 等
    - 资源类型 (resource_type): screening, report, molecule, user 等
    - 资源 ID (resource_id): 被操作资源的 ID
    - IP 地址 (ip_address): 请求来源 IP
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[int] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="audit_logs", lazy="selectin")
