"""
受体/靶点蛋白 API

GET    /api/v1/receptors        — 查询受体列表
GET    /api/v1/receptors/{id}   — 获取受体详情
POST   /api/v1/receptors        — 添加受体
DELETE /api/v1/receptors/{id}   — 删除受体
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ConflictError, PermissionDenied, ResourceNotFound
from app.core.security import PermissionChecker, get_current_user
from app.models.receptor import Receptor
from app.schemas.molecule import ReceptorCreateRequest, ReceptorResponse

router = APIRouter()


@router.get("/", response_model=list[ReceptorResponse])
async def list_receptors(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询受体列表"""
    query = select(Receptor)

    if search:
        query = query.where(
            Receptor.receptor_name.ilike(f"%{search}%") |
            Receptor.pdb_code.ilike(f"%{search}%")
        )

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    receptors = result.scalars().all()

    return [
        ReceptorResponse(
            id=r.id,
            receptor_name=r.receptor_name,
            pdb_code=r.pdb_code,
            pdbqt_uri=r.pdbqt_uri,
            description=r.description,
        )
        for r in receptors
    ]


@router.post("/", response_model=ReceptorResponse, status_code=201)
async def create_receptor(
    req: ReceptorCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新受体"""
    # 检查同名受体是否已存在
    existing = await db.execute(
        select(Receptor).where(Receptor.receptor_name == req.receptor_name)
    )
    if existing.scalar_one_or_none():
        raise ConflictError(message=f"受体 '{req.receptor_name}' 已存在")

    receptor = Receptor(
        receptor_name=req.receptor_name,
        pdb_code=req.pdb_code,
        pdbqt_uri=req.pdbqt_uri,
        description=req.description,
    )
    db.add(receptor)
    await db.flush()
    await db.refresh(receptor)

    return ReceptorResponse(
        id=receptor.id,
        receptor_name=receptor.receptor_name,
        pdb_code=receptor.pdb_code,
        pdbqt_uri=receptor.pdbqt_uri,
        description=receptor.description,
    )


@router.get("/{receptor_id}", response_model=ReceptorResponse)
async def get_receptor(
    receptor_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取受体详情"""
    result = await db.execute(select(Receptor).where(Receptor.id == receptor_id))
    receptor = result.scalar_one_or_none()

    if not receptor:
        raise ResourceNotFound(message=f"受体 ID={receptor_id} 不存在")

    return ReceptorResponse(
        id=receptor.id,
        receptor_name=receptor.receptor_name,
        pdb_code=receptor.pdb_code,
        pdbqt_uri=receptor.pdbqt_uri,
        description=receptor.description,
    )


@router.delete("/{receptor_id}")
async def delete_receptor(
    receptor_id: int,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(PermissionChecker.require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """删除受体（仅限 ADMIN）

    删除前将引用了该受体的 screening_jobs 的 receptor_id 置为 NULL。
    """
    from sqlalchemy import update as sql_update
    from app.models.screening import ScreeningJob

    result = await db.execute(select(Receptor).where(Receptor.id == receptor_id))
    receptor = result.scalar_one_or_none()

    if not receptor:
        raise ResourceNotFound(message=f"受体 ID={receptor_id} 不存在")

    # 先删除所有引用此受体的 screening_jobs（级联删除其子表）
    jobs_result = await db.execute(
        select(ScreeningJob).where(ScreeningJob.receptor_id == receptor_id)
    )
    jobs = jobs_result.scalars().all()
    for job in jobs:
        await db.delete(job)

    await db.delete(receptor)
    await db.flush()

    return {"receptor_id": receptor_id, "message": "受体已删除"}
