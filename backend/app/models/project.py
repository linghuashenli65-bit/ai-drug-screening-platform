"""
项目模型 (projects, project_members)

项目表用于组织科研实验集合，成员表实现项目级权限控制。
"""

from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Project(Base):
    """科研项目管理

    每个项目属于一个 Owner，可拥有多个成员和多个筛选任务。
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    owner: Mapped["User"] = relationship("User", back_populates="projects", lazy="selectin")
    members: Mapped[list["ProjectMember"]] = relationship("ProjectMember", back_populates="project", lazy="selectin")
    molecules: Mapped[list["Molecule"]] = relationship("Molecule", back_populates="project", lazy="selectin")
    screening_jobs: Mapped[list["ScreeningJob"]] = relationship("ScreeningJob", back_populates="project", lazy="selectin")


class ProjectMember(Base):
    """项目成员权限

    角色：OWNER / ADMIN / RESEARCHER / VIEWER
    """

    __tablename__ = "project_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="RESEARCHER")

    # 关系
    project: Mapped["Project"] = relationship("Project", back_populates="members", lazy="selectin")
