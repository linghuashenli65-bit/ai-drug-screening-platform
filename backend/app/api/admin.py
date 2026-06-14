"""
管理后台 API（需要 ADMIN 权限）

GET  /api/v1/admin/stats      — 系统统计
GET  /api/v1/admin/users      — 用户管理
GET  /api/v1/admin/audit-logs — 审计日志
"""

from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import JobStatus
from app.core.database import get_db
from app.core.security import PermissionChecker, get_current_user
from app.models.screening import ScreeningJob
from app.models.docking import DockingTask
from app.models.user import User
from app.models.audit import AuditLog

router = APIRouter()

# 所有接口需要 ADMIN 权限
require_admin = PermissionChecker.require_role("ADMIN")

# 活动任务状态（非终态）
ACTIVE_JOB_STATUSES = [
    JobStatus.CREATED.value,
    JobStatus.PREPARING.value,
    JobStatus.DOCKING.value,
    JobStatus.ANALYZING.value,
    JobStatus.REPORTING.value,
]

# ── 响应模型 ──


class AdminUserItem(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    status: int
    created_at: Optional[str] = None


class AuditLogItem(BaseModel):
    id: int
    user_id: int
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[str] = None


@router.get("/stats")
async def system_stats(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """系统统计信息"""
    # 用户数
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0

    # 活跃任务数
    active_jobs = (await db.execute(
        select(func.count(ScreeningJob.id)).where(ScreeningJob.status.in_(ACTIVE_JOB_STATUSES))
    )).scalar() or 0

    # 已完成任务数
    completed_jobs = (await db.execute(
        select(func.count(ScreeningJob.id)).where(ScreeningJob.status == "COMPLETED")
    )).scalar() or 0

    # Docking 统计
    total_dockings = (await db.execute(select(func.count(DockingTask.id)))).scalar() or 0
    success_dockings = (await db.execute(
        select(func.count(DockingTask.id)).where(DockingTask.status == "SUCCESS")
    )).scalar() or 0

    return {
        "users": {"total": user_count},
        "jobs": {"active": active_jobs, "completed": completed_jobs},
        "docking": {
            "total": total_dockings,
            "success": success_dockings,
            "success_rate": success_dockings / total_dockings if total_dockings > 0 else 0,
        },
    }


@router.get("/users", response_model=list[AdminUserItem])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """用户列表"""
    query = select(User).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    return [
        AdminUserItem(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role,
            status=u.status,
            created_at=str(u.created_at) if u.created_at else None,
        )
        for u in users
    ]


@router.get("/audit-logs", response_model=list[AuditLogItem])
async def audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: int = Query(None),
    action: str = Query(None),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """审计日志查询"""
    query = select(AuditLog)

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)

    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        AuditLogItem(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            ip_address=log.ip_address,
            created_at=str(log.created_at) if log.created_at else None,
        )
        for log in logs
    ]
