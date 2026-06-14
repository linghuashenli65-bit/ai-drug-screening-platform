"""
药物库管理 API

POST   /api/v1/libraries/import      — 导入 e-drug3d.sdf 药物库
GET    /api/v1/libraries/drugs       — 分页查询药物库
GET    /api/v1/libraries/drugs/{id}  — 查询单个药物
GET    /api/v1/libraries/stats       — 药物库统计信息
"""

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import FileFormatError, ResourceNotFound, ValidationError
from app.core.security import PermissionChecker, get_current_user
from app.models.molecule import DrugLibrary
from app.schemas.molecule import (
    DrugLibraryImportRequest,
    DrugLibraryImportResponse,
    DrugLibraryListResponse,
    DrugLibraryResponse,
)

router = APIRouter()


@router.post("/import", response_model=DrugLibraryImportResponse)
async def import_drug_library(
    req: DrugLibraryImportRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(PermissionChecker.require_role("ADMIN")),
):
    """导入 e-drug3d.sdf 药物库

    仅限 ADMIN 角色。解析 SDF 文件并批量写入 drug_library 表。
    导入前清空已有数据（幂等操作）。
    """
    sdf_path = Path(req.sdf_path)
    if not sdf_path.exists():
        raise ValidationError(
            message=f"SDF 文件不存在: {req.sdf_path}",
            detail={"path": req.sdf_path},
        )

    # 1. 解析 SDF 文件（延迟导入避免启动依赖 rdkit）
    from app.scripts.import_drugbank import import_to_database, parse_sdf_file

    try:
        drugs = parse_sdf_file(str(sdf_path))
    except Exception as e:
        raise FileFormatError(
            message="SDF 文件解析失败",
            detail={"error": str(e), "path": str(sdf_path)},
        )

    if not drugs:
        raise FileFormatError(
            message="SDF 文件中未解析到任何有效分子",
            detail={"path": str(sdf_path)},
        )

    # 2. 统计
    normal_count = sum(1 for d in drugs if d["status"] == "正常")
    discontinued_count = sum(1 for d in drugs if d["status"] == "DISCONTINUED")
    errors = 0  # parse_sdf_file already filtered out parse failures

    # 3. 导入数据库（同步操作，放到线程池避免阻塞事件循环）
    # 注意: import_to_database 创建独立的 sync engine，因为 SDF 解析 + 批量 INSERT
    # 为一次性运维操作，使用独立连接池避免与主 async pool 竞争。
    inserted = await asyncio.to_thread(import_to_database, drugs)

    return DrugLibraryImportResponse(
        total_parsed=len(drugs),
        total_inserted=inserted,
        normal_count=normal_count,
        discontinued_count=discontinued_count,
        errors=errors,
    )


@router.get("/drugs", response_model=DrugLibraryListResponse)
async def list_drugs(
    query: Optional[str] = Query(None, description="搜索关键词（药物名/DrugBank ID/CAS）"),
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """分页查询药物库"""
    base_query = select(DrugLibrary)

    if query:
        base_query = base_query.where(
            DrugLibrary.drug_name.ilike(f"%{query}%") |
            DrugLibrary.drugbank_id.ilike(f"%{query}%") |
            DrugLibrary.cas.ilike(f"%{query}%")
        )
    if status:
        base_query = base_query.where(DrugLibrary.status == status)

    # 总数
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    base_query = base_query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(base_query)
    drugs = result.scalars().all()

    items = [
        DrugLibraryResponse(
            id=d.id,
            drug_name=d.drug_name,
            smiles=d.smiles,
            drugbank_id=d.drugbank_id,
            cas=d.cas,
            status=d.status or "正常",
            indication=d.indication,
            molecular_weight=float(d.molecular_weight) if d.molecular_weight else None,
            logp=float(d.logp) if d.logp else None,
            pdbqt_uri=d.pdbqt_uri,
        )
        for d in drugs
    ]

    return DrugLibraryListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/drugs/{drug_id}", response_model=DrugLibraryResponse)
async def get_drug(
    drug_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个药物库条目详情"""
    result = await db.execute(select(DrugLibrary).where(DrugLibrary.id == drug_id))
    drug = result.scalar_one_or_none()

    if not drug:
        raise ResourceNotFound(message=f"药物 ID={drug_id} 不存在")

    return DrugLibraryResponse(
        id=drug.id,
        drug_name=drug.drug_name,
        smiles=drug.smiles,
        drugbank_id=drug.drugbank_id,
        cas=drug.cas,
        status=drug.status or "正常",
        indication=drug.indication,
        molecular_weight=float(drug.molecular_weight) if drug.molecular_weight else None,
        logp=float(drug.logp) if drug.logp else None,
        pdbqt_uri=drug.pdbqt_uri,
    )


@router.get("/stats")
async def get_library_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取药物库统计信息"""
    total_result = await db.execute(select(func.count()).select_from(DrugLibrary))
    total = total_result.scalar() or 0

    normal_result = await db.execute(
        select(func.count()).where(DrugLibrary.status == "正常")
    )
    normal = normal_result.scalar() or 0

    discontinued_result = await db.execute(
        select(func.count()).where(DrugLibrary.status == "DISCONTINUED")
    )
    discontinued = discontinued_result.scalar() or 0

    return {
        "total": total,
        "normal": normal,
        "discontinued": discontinued,
    }
