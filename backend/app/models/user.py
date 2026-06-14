"""
用户模型 (users)

系统用户表，存储用户账户信息和角色。
"""

from datetime import datetime

from sqlalchemy import Integer, DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """系统用户

    支持 RBAC 角色：ADMIN / PI / RESEARCHER / VIEWER
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="RESEARCHER")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="owner", lazy="selectin")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", lazy="selectin")
