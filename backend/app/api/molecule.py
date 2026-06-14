"""
分子管理 API

POST   /api/v1/molecules/upload      — 上传分子（SMILES）
GET    /api/v1/molecules/{id}        — 获取分子详情
DELETE /api/v1/molecules/{id}        — 删除分子
GET    /api/v1/molecules             — 查询分子列表
GET    /api/v1/drug-library          — 302 重定向至 /api/v1/libraries/drugs (已废弃)
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDenied, ResourceNotFound
from app.core.security import get_current_user
from app.models.molecule import Molecule
from app.models.project import Project
from app.schemas.molecule import (
    MoleculeResponse,
    MoleculeUploadRequest,
)

router = APIRouter()


@router.post("/upload", response_model=MoleculeResponse, status_code=201)
async def upload_molecule(
    req: MoleculeUploadRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传分子（SMILES 字符串）

    创建分子记录，后续由 Molecule Agent 完成标准化和 3D 构象生成。
    """
    mol = Molecule(
        project_id=req.project_id,
        smiles=req.smiles,
    )
    db.add(mol)
    await db.flush()
    await db.refresh(mol)

    return MoleculeResponse(
        id=mol.id,
        project_id=mol.project_id,
        smiles=mol.smiles,
        created_at=str(mol.created_at) if mol.created_at else None,
    )


@router.get("/{molecule_id}", response_model=MoleculeResponse)
async def get_molecule(
    molecule_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取分子详情"""
    result = await db.execute(select(Molecule).where(Molecule.id == molecule_id))
    mol = result.scalar_one_or_none()

    if not mol:
        raise ResourceNotFound(message=f"分子 ID={molecule_id} 不存在")

    return MoleculeResponse(
        id=mol.id,
        project_id=mol.project_id,
        smiles=mol.smiles,
        molecular_weight=float(mol.molecular_weight) if mol.molecular_weight else None,
        logp=float(mol.logp) if mol.logp else None,
        tpsa=float(mol.tpsa) if mol.tpsa else None,
        source_file_uri=mol.source_file_uri,
        created_at=str(mol.created_at) if mol.created_at else None,
    )


@router.get("/", response_model=list[MoleculeResponse])
async def list_molecules(
    project_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询分子列表"""
    query = select(Molecule)

    if project_id:
        query = query.where(Molecule.project_id == project_id)

    query = query.order_by(Molecule.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    mols = result.scalars().all()

    return [
        MoleculeResponse(
            id=m.id,
            project_id=m.project_id,
            smiles=m.smiles,
            molecular_weight=float(m.molecular_weight) if m.molecular_weight else None,
            logp=float(m.logp) if m.logp else None,
            tpsa=float(m.tpsa) if m.tpsa else None,
            created_at=str(m.created_at) if m.created_at else None,
        )
        for m in mols
    ]


@router.delete("/{molecule_id}")
async def delete_molecule(
    molecule_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除分子（需项目 Owner 或 ADMIN 权限）"""
    result = await db.execute(select(Molecule).where(Molecule.id == molecule_id))
    mol = result.scalar_one_or_none()

    if not mol:
        raise ResourceNotFound(message=f"分子 ID={molecule_id} 不存在")

    # 检查权限：ADMIN 可删除；普通用户需是项目 Owner
    if current_user["role"] != "ADMIN":
        project_result = await db.execute(select(Project).where(Project.id == mol.project_id))
        project = project_result.scalar_one_or_none()
        if not project or project.owner_id != current_user["user_id"]:
            raise PermissionDenied(message="无权删除此分子，仅项目 Owner 或 ADMIN 可操作")

    await db.delete(mol)
    await db.flush()

    return {"molecule_id": molecule_id, "message": "分子已删除"}


@router.get("/drug-library", deprecated=True)
async def list_drug_library():
    """已废弃：请使用 /api/v1/libraries/drugs"""
    return RedirectResponse(url="/api/v1/libraries/drugs", status_code=301)
