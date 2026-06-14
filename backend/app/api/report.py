"""
报告 API

GET /api/v1/reports              — 查询报告列表
GET /api/v1/reports/{job_id}         — 获取报告信息
GET /api/v1/reports/{job_id}/download — 下载报告文件
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDenied, ResourceNotFound
from app.core.minio import download_file, parse_minio_uri
from app.core.security import get_current_user
from app.models.report import Report
from app.models.screening import ScreeningJob

import os
import tempfile
from pathlib import Path

router = APIRouter()

# file:// 协议仅允许访问此目录及其子目录，防止路径遍历攻击
ALLOWED_FILE_ROOT = Path(tempfile.gettempdir()).resolve()


@router.get("/")
async def list_reports(
    job_id: Optional[int] = Query(None, description="按任务 ID 筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询报告列表（支持按任务筛选和分页）"""
    base_query = select(Report)

    if job_id:
        base_query = base_query.where(Report.job_id == job_id)

    # 总数
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    base_query = base_query.order_by(Report.generated_at.desc())
    base_query = base_query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(base_query)
    reports = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "reports": [
            {
                "id": r.id,
                "job_id": r.job_id,
                "report_type": r.report_type,
                "report_uri": r.report_uri,
                "generated_at": str(r.generated_at) if r.generated_at else None,
            }
            for r in reports
        ],
    }


@router.get("/{job_id}")
async def get_report(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定任务的报告列表"""
    result = await db.execute(
        select(Report).where(Report.job_id == job_id).order_by(Report.generated_at.desc())
    )
    reports = result.scalars().all()

    return {
        "job_id": job_id,
        "reports": [
            {
                "id": r.id,
                "report_type": r.report_type,
                "report_uri": r.report_uri,
                "generated_at": str(r.generated_at) if r.generated_at else None,
            }
            for r in reports
        ],
    }


@router.get("/{job_id}/download")
async def download_report(
    job_id: int,
    report_type: str = "pdf",
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """下载报告文件"""
    # 权限检查：验证用户有权限访问此任务
    job_result = await db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise ResourceNotFound(message=f"任务 ID={job_id} 不存在")
    if current_user["role"] not in ("ADMIN", "PI") and job.created_by != current_user["user_id"]:
        raise PermissionDenied(message="无权访问此任务")

    result = await db.execute(
        select(Report)
        .where(Report.job_id == job_id, Report.report_type.ilike(f"%{report_type}%"))
        .order_by(Report.generated_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise ResourceNotFound(message=f"任务 ID={job_id} 的 {report_type} 报告不存在")

    uri = report.report_uri

    # MinIO 下载
    if uri.startswith("minio://"):
        bucket, obj_name = parse_minio_uri(uri)
        tmp_path = os.path.join(tempfile.gettempdir(), f"report_{job_id}.{report_type}")
        await download_file(bucket, obj_name, tmp_path)
        mime_map = {"pdf": "application/pdf", "markdown": "text/markdown", "html": "text/html"}
        media_type = mime_map.get(report_type, "application/octet-stream")
        return FileResponse(
            tmp_path,
            media_type=media_type,
            filename=f"screening_report_{job_id}.{report.report_type.lower()}",
        )

    # 本地文件 — 仅允许 ALLOWED_FILE_ROOT 目录内的文件
    if uri.startswith("file://"):
        local_path = uri.replace("file://", "")
        resolved = Path(local_path).resolve()
        if not str(resolved).startswith(str(ALLOWED_FILE_ROOT)):
            raise ResourceNotFound(message="报告文件路径不合法")
        if resolved.exists() and resolved.is_file():
            return FileResponse(
                str(resolved),
                filename=resolved.name,
            )

    raise ResourceNotFound(message="报告文件不可用")
